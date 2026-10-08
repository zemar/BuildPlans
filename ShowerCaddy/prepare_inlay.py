"""Trace existing color-region data into CAD polygons; no Fusion dependencies.

Run with NumPy, SciPy and Shapely installed. The Fusion script needs only the
resulting JSON asset. No source artwork or reference previews are modified.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib

import numpy as np
from scipy.ndimage import label
from shapely.geometry import box, Polygon, MultiPolygon, Point
from shapely.ops import unary_union
from shapely.affinity import scale as scale_geometry

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'CamelandPanda/assets/colors.bin.zlib'
HEIGHT = 80.0
EYE_HIGHLIGHT_RADIUS_MM = 0.24
# Source-grid coordinates: smooth oval behind the rider, not around individual limbs.
PANDA_BACKDROP_CENTER = (435, 235)
PANDA_BACKDROP_RADII = (105, 147)


def regions(geometry):
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    return [p for g in geometry.geoms for p in regions(g)]


def mask_polygons(mask, x0, y0, scale):
    runs = []
    for y, row in enumerate(mask):
        changes = np.diff(np.r_[False, row, False].astype(int))
        starts, ends = np.where(changes == 1)[0], np.where(changes == -1)[0]
        for a, b in zip(starts, ends):
            runs.append(box((a-x0)*scale, (y-y0)*scale,
                            (b-x0)*scale, (y+1-y0)*scale))
    return unary_union(runs)


def panda_white_details(colors, silhouette, x0, y0, scale):
    """Restore white eye details without outlining the black fur."""
    rows, cols = np.indices(colors.shape)
    eyes = ((cols >= 420) & (cols <= 432) & (rows >= 161) & (rows <= 179) |
            (cols >= 447) & (cols <= 459) & (rows >= 164) & (rows <= 179))
    eye_white = mask_polygons(eyes & (colors == 2), x0, y0, scale)
    eye_white = eye_white.buffer(0.10, quad_segs=3)
    highlights = [Point((x-x0)*scale,(y-y0)*scale).buffer(
                    EYE_HIGHLIGHT_RADIUS_MM, quad_segs=6)
                  for x,y in [(427.5,167.5),(453.5,170.5)]]
    return unary_union([eye_white] + highlights)


def build():
    raw = zlib.decompress(SOURCE.read_bytes())
    nx, ny = struct.unpack_from('<II', raw)
    colors = np.frombuffer(raw[8:], dtype=np.uint8).reshape(ny, nx)
    labels, count = label(colors != 0)
    # The camel/rider/flag is the largest connected silhouette in this scene.
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    silhouette = labels == sizes.argmax()
    yy, xx = np.where(silhouette)
    x0, y0, x1, y1 = int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)
    scale = HEIGHT / (y1-y0)
    filled = mask_polygons(silhouette, x0, y0, scale)
    dark = mask_polygons(silhouette & (colors == 1), x0, y0, scale)
    # Dark outlines/panda patches remain the black basket material.
    # Broaden outlines slightly so fine lines survive slicing at this scale.
    allowed = filled.difference(dark.buffer(0.10, quad_segs=2))
    white_details = panda_white_details(colors, silhouette, x0, y0, scale)
    cx, cy = PANDA_BACKDROP_CENTER
    rx, ry = PANDA_BACKDROP_RADII
    center = ((cx-x0)*scale, (cy-y0)*scale)
    oval = scale_geometry(Point(*center).buffer(1, quad_segs=48),
                          xfact=rx*scale, yfact=ry*scale, origin=center)
    # Preserve every original silhouette, including the black panda fur.
    backdrop = oval.difference(filled.buffer(0.10, quad_segs=2))
    palette = [('White', [2], '#fafafa'), ('Green', [5], '#70a628'),
               ('Red', [6], '#d21923'), ('Brown', [3,4,7], '#b87c35')]
    records = []
    allocated = Polygon()
    for name, ids, color in palette:
        shape = mask_polygons(silhouette & np.isin(colors, ids), x0, y0, scale)
        shape = shape.intersection(allowed)
        if name == 'Brown':
            shape = unary_union([shape, backdrop])
        shape = shape.buffer(-0.035, quad_segs=2).buffer(0.035, quad_segs=2)
        if name == 'White':
            shape = unary_union([shape, white_details])
        shape = shape.simplify(0.035 if name == 'White' else 0.055, preserve_topology=True).difference(allocated)
        polygons = sorted([p for p in regions(shape) if p.area >= 0.12],
                          key=lambda p: p.area, reverse=True)
        assert all(p.is_valid and not p.is_empty for p in polygons)
        allocated = unary_union([allocated] + polygons)
        def ring(coords):
            return [[round(x, 5), round(y, 5)] for x,y in list(coords)[:-1]]
        records.extend({'color': name, 'outer': ring(p.exterior.coords),
                        'holes': [ring(h.coords) for h in p.interiors]} for p in polygons)
    data = {
        'description': 'Central camel, panda rider, flag and mouth branch; four-color inlay with black negative details',
        'panda_outline_mm': 0.0,
        'panda_backdrop': {'color': 'Brown', 'width_mm': 2*rx*scale, 'height_mm': 2*ry*scale},
        'eye_highlight_radius_mm': EYE_HIGHLIGHT_RADIUS_MM,
        'source': 'CamelandPanda/assets/colors.bin.zlib',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'width_mm': (x1-x0)*scale, 'height_mm': HEIGHT,
        'palette': {name: color for name, ids, color in palette},
        'polygons': records,
    }
    dest = ROOT/'assets/panda_camel_inlay.json'
    dest.write_text(json.dumps(data, separators=(',', ':'))+'\n')
    # CAD vector preview, looking directly at the outside front wall.
    width = data['width_mm']
    def path(r):
        return 'M '+' L '.join(f'{x:.5f},{y:.5f}' for x,y in r)+' Z'
    paths = [(p['color'], ' '.join([path(p['outer'])]+[path(h) for h in p['holes']]))
             for p in data['polygons']]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 259 101.6" width="1036" height="406.4">',
           '<rect width="259" height="101.6" rx="1" fill="#202020"/>',
           f'<g transform="translate({(259-width)/2}, {(101.6-HEIGHT)/2})" fill="#fafafa" fill-rule="evenodd">']
    svg += [f'<path fill="{data["palette"][color]}" d="{d}"/>' for color, d in paths]
    svg += ['</g></svg>']
    (ROOT/'inlay-preview.svg').write_text('\n'.join(svg)+'\n')
    # Rasterize the generated CAD paths for a convenient front-view preview.
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (1295, 508), '#202020')
    draw = ImageDraw.Draw(image)
    def pixels(r):
        return [((x+(259-width)/2)*5, (y+(101.6-HEIGHT)/2)*5) for x,y in r]
    for polygon in records:
        mask = Image.new('L', image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.polygon(pixels(polygon['outer']), fill=255)
        for hole in polygon['holes']:
            mask_draw.polygon(pixels(hole), fill=0)
        image.paste(data['palette'][polygon['color']], (0, 0, image.width, image.height), mask)
    image.save(ROOT/'inlay-preview.png')
    print(f'{len(records)} colored regions; {sum(len(p["outer"])+sum(map(len,p["holes"])) for p in data["polygons"])} vertices; size {width:.2f} x {HEIGHT} mm')


if __name__ == '__main__':
    build()
