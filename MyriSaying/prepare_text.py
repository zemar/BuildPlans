"""Rebuild the bundled, shaped cursive outlines and front PNG with Python.

Requires requirements.txt. The original font file is never copied into the project.
Usage: python prepare_text.py [--font '/path/to/SnellRoundhand.ttc' --font-index 1]
"""
import argparse
import json
import math
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
import numpy as np
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union
from trimesh.creation import triangulate_polygon
import uharfbuzz as hb

import MyriSaying as model


class OutlinePen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.rings = []
        self.current = []

    def _moveTo(self, point):
        self.current = [point]

    def _lineTo(self, point):
        self.current.append(point)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        length = sum(math.dist(a,b) for a,b in ((p0,p1),(p1,p2),(p2,p3)))
        for t in np.linspace(0, 1, max(12, math.ceil(length/12)))[1:]:
            self.current.append(tuple((1-t)**3*p0[i]+3*(1-t)**2*t*p1[i]
                                      +3*(1-t)*t*t*p2[i]+t**3*p3[i] for i in (0,1)))

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        length = math.dist(p0,p1)+math.dist(p1,p2)
        for t in np.linspace(0, 1, max(12, math.ceil(length/12)))[1:]:
            self.current.append(tuple((1-t)**2*p0[i]+2*(1-t)*t*p1[i]+t*t*p2[i]
                                      for i in (0,1)))

    def _closePath(self):
        if len(self.current) >= 3:
            self.rings.append(self.current)
        self.current = []

    def _endPath(self):
        self._closePath()


def polygons(shape):
    if shape.geom_type == 'Polygon':
        return [shape]
    return [p for p in shape.geoms if p.geom_type == 'Polygon']


def shaped_line(text, font, hbfont):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf)
    glyphs = font.getGlyphSet()
    order = font.getGlyphOrder()
    x, y, shapes = 0, 0, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        if info.codepoint == 0:
            raise ValueError('Font lacks a character in '+text)
        pen = OutlinePen(glyphs)
        glyphs[order[info.codepoint]].draw(pen)
        glyph = Polygon()
        # Even-odd contour fill preserves counters in a/e/o and date numerals.
        for ring in pen.rings:
            contour = Polygon(ring)
            if not contour.is_valid:
                contour = contour.buffer(0)
            glyph = glyph.symmetric_difference(contour)
        if not glyph.is_empty:
            shapes.append(affinity.translate(glyph, x+pos.x_offset, y+pos.y_offset))
        x += pos.x_advance
        y += pos.y_advance
    return unary_union(shapes)


def prepare(font_path, font_index):
    font = TTFont(font_path, fontNumber=font_index)
    actual_name = font['name'].getDebugName(4)
    if actual_name != model.FONT_NAME:
        raise ValueError(f'Expected {model.FONT_NAME}, found {actual_name}')
    hbfont = hb.Font(hb.Face(font_path.read_bytes(), font_index))
    hbfont.scale = (font['head'].unitsPerEm,)*2
    vertices, faces, outlines, rendered = [], [], [], []
    max_width = model.WIDTH_MM-2*model.FRAME_MM-12
    for text, height, center in model.LINES:
        shape = shaped_line(text, font, hbfont)
        x0,y0,x1,y1 = shape.bounds
        scale = min(height/(y1-y0), max_width/(x1-x0))
        shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(0,0))
        # Give the small name/date stronger hairlines without changing the font.
        expansion = 0.16 if height <= 7 else 0.08
        shape = shape.buffer(expansion, quad_segs=3).simplify(0.008, preserve_topology=True)
        x0,y0,x1,y1 = shape.bounds
        if x1-x0 > max_width:
            scale = max_width/(x1-x0)
            shape = affinity.scale(shape, xfact=scale, yfact=scale, origin=(0,0))
            x0,y0,x1,y1 = shape.bounds
        shape = affinity.translate(shape, -(x0+x1)/2, center-(y0+y1)/2)
        x0,y0,x1,y1 = shape.bounds
        if not (-model.WIDTH_MM/2+model.FRAME_MM+2 < x0 < x1
                < model.WIDTH_MM/2-model.FRAME_MM-2
                and model.FRAME_MM+2 < y0 < y1 < model.HEIGHT_MM-model.FRAME_MM-2):
            raise ValueError('Text outside frame clearance: '+text)
        if any(shape.intersects(previous) for previous in rendered):
            raise ValueError('Text lines overlap: '+text)
        rendered.append(shape)
        rings = []
        for polygon in polygons(shape):
            pts, tris = triangulate_polygon(polygon, engine='earcut')
            pts = np.round(pts, 8)
            offset = len(vertices)
            vertices.extend(pts.tolist())
            area = 0
            for a,b,c in tris:
                p,q,r = pts[[a,b,c]]
                signed = (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
                if abs(signed) < 1e-14:
                    raise ValueError('Degenerate glyph triangulation')
                if signed < 0:
                    b,c = c,b
                area += abs(signed)/2
                faces.append([int(a)+offset,int(b)+offset,int(c)+offset])
            if abs(area-polygon.area) > 1e-5:
                raise ValueError('Triangulation did not preserve a glyph area.')
            for ring in [polygon.exterior, *polygon.interiors]:
                rings.append([[round(x,8),round(y,8)] for x,y in ring.coords[:-1]])
        outlines.append({'text':text, 'bounds_mm':list(shape.bounds), 'rings':rings})
        model.LOGGER.info('TEXT %r; bounds mm=%s; connected outlines=%d',
                          text, shape.bounds, len(polygons(shape)))
    data = {'spec':model.text_spec(), 'font':actual_name,
            'stroke_expansion_mm':{'saying':0.08,'name_and_date':0.16}, 'outline_simplification_mm':0.008,
            'vertices':vertices, 'faces':faces, 'outlines':outlines}
    folder = model.HERE/'assets'
    folder.mkdir(exist_ok=True)
    (folder/'lettering.json').write_text(json.dumps(data, separators=(',',':'))+'\n', encoding='utf-8')
    # Raster proof from exactly the polygons used to create the raised mesh.
    scale, margin = 10, 80
    image = Image.new('RGB', (int(model.WIDTH_MM*scale)+2*margin,
                              int(model.HEIGHT_MM*scale)+2*margin), '#e9e5de')
    draw = ImageDraw.Draw(image)
    draw.rectangle((margin,margin,image.width-margin,image.height-margin), fill=model.COLORS['Brown'][:7])
    inset = model.FRAME_MM*scale
    draw.rectangle((margin+inset,margin+inset,image.width-margin-inset,image.height-margin-inset),
                   fill=model.COLORS['Black'][:7])
    def screen(ring):
        return [(margin+(x+model.WIDTH_MM/2)*scale,
                 margin+(model.HEIGHT_MM-y)*scale) for x,y in ring.coords]
    for shape in rendered:
        mask = Image.new('L', image.size, 0)
        painter = ImageDraw.Draw(mask)
        for polygon in polygons(shape):
            painter.polygon(screen(polygon.exterior), fill=255)
            for hole in polygon.interiors:
                painter.polygon(screen(hole), fill=0)
        image.paste('white', (0,0), mask)
    image.resize((1100,580), Image.Resampling.LANCZOS).save(model.HERE/'preview.png')
    model.LOGGER.info('Prepared cursive outline asset and front PNG; font=%s', actual_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path,
                        default=Path('/System/Library/Fonts/Supplemental/SnellRoundhand.ttc'))
    parser.add_argument('--font-index', type=int, default=1)
    args = parser.parse_args()
    model.start_log()
    try:
        prepare(args.font, args.font_index)
        model.generate()
    except Exception:
        model.LOGGER.exception('Font preparation failed')
        raise
    finally:
        model.close_log()
