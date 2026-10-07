"""Fusion: create a 200 x 150 x 10 mm printable relief of the cleaned camel and three pandas artwork.
Run via Scripts and Add-Ins. Creates a NEW unsaved mesh design and an STL plus a colored OBJ/MTL.
Uses Python's standard library; keep the assets folder beside this script.
CLI: python3 CamelandPanda.py --stl-only (does not require Fusion).
"""
from pathlib import Path
import array
import logging
import time
import hashlib
import math
import shutil
import struct
import sys
import traceback
import zlib

WIDTH_MM = 200.0
HEIGHT_MM = 150.0
TOTAL_THICKNESS_MM = 10.0
RELIEF_MM = 3.0  # Base is TOTAL_THICKNESS_MM - RELIEF_MM (7 mm by default).
ROOT = Path(__file__).resolve().parent
ASSET = ROOT / 'assets' / 'relief.bin.zlib'
OUTPUT = ROOT / 'exports' / 'CamelandPanda.stl'
COLOR_ASSET = ROOT / 'assets' / 'colors.bin.zlib'
COLOR_OUTPUT = ROOT / 'exports' / 'CamelandPanda.obj'
# RGB colors (0–255). Carpet, flag and tongues all use the same Red entry.
PALETTE = (
    ('Ivory_base', (242, 234, 215)),
    ('Panda_black', (25, 25, 25)),
    ('Panda_white', (250, 250, 247)),
    ('Camel_tan', (221, 157, 66)),
    ('Camel_brown', (151, 87, 33)),
    ('Bamboo_green', (112, 166, 40)),
    ('Red', (210, 25, 35)),
    ('Pyramid_gold', (239, 189, 80)),
)
LOG_PATH = ROOT / 'CamelandPanda.log'


def load_heights():
    raw = zlib.decompress(ASSET.read_bytes())
    nx, ny = struct.unpack_from('<II', raw)
    if nx < 2 or ny < 2 or len(raw) != 8 + 2 * nx * ny:
        raise ValueError('Invalid relief height field.')
    values = array.array('H')
    values.frombytes(raw[8:])
    if sys.byteorder != 'little':
        values.byteswap()
    if min(values) != 0 or max(values) != 65535:
        raise ValueError('Height field must span the full relief range.')
    return nx, ny, values


def mesh_triangles(nx, ny, values):
    """Outward-wound closed surface; bottom fan shares all perimeter vertices."""
    base = TOTAL_THICKNESS_MM - RELIEF_MM
    def top(x, y):
        # Reverse image rows: image top is +Y, so lettering is not mirrored.
        h = values[(ny - 1 - y) * nx + x] / 65535
        return (WIDTH_MM*x/(nx-1), HEIGHT_MM*y/(ny-1), base + RELIEF_MM*h)
    for y in range(ny - 1):
        for x in range(nx - 1):
            a, b, c, d = top(x,y), top(x+1,y), top(x+1,y+1), top(x,y+1)
            yield a, b, c
            yield a, c, d
    perimeter = ([(x,0) for x in range(nx)] +
                 [(nx-1,y) for y in range(1,ny)] +
                 [(x,ny-1) for x in range(nx-2,-1,-1)] +
                 [(0,y) for y in range(ny-2,0,-1)])
    center = (WIDTH_MM/2, HEIGHT_MM/2, 0.0)
    for i, xy in enumerate(perimeter):
        a, b = top(*xy), top(*perimeter[(i+1) % len(perimeter)])
        low_a, low_b = (a[0],a[1],0.0), (b[0],b[1],0.0)
        yield a, low_a, low_b
        yield a, low_b, b
        yield center, low_b, low_a


def write_stl(path=OUTPUT):
    dims = (WIDTH_MM, HEIGHT_MM, TOTAL_THICKNESS_MM, RELIEF_MM)
    if not all(math.isfinite(v) and v > 0 for v in dims):
        raise ValueError('Dimensions must be finite and positive.')
    if RELIEF_MM >= TOTAL_THICKNESS_MM:
        raise ValueError('Relief must be less than total thickness.')
    nx, ny, values = load_heights()
    count = 2*(nx-1)*(ny-1) + 3*(2*nx+2*ny-4)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.stl.tmp')
    pack = struct.Struct('<12fH').pack
    try:
        with temporary.open('wb') as stream:
            stream.write(b'CamelandPanda; millimeters; closed raised relief'.ljust(80,b' '))
            stream.write(struct.pack('<I', count))
            written = 0
            for a,b,c in mesh_triangles(nx,ny,values):
                u = tuple(b[i]-a[i] for i in range(3))
                v = tuple(c[i]-a[i] for i in range(3))
                n = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                length = math.sqrt(sum(t*t for t in n))
                if length == 0:
                    raise ValueError('Degenerate mesh triangle.')
                n = tuple(t/length for t in n)
                stream.write(pack(*(n+a+b+c),0))
                written += 1
            if written != count:
                raise ValueError('Unexpected triangle count.')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path, count


def write_palette_png(path):
    """Small RGB PNG texture, using only the standard library."""
    width, height = len(PALETTE)*32, 32
    row = b''.join(bytes(rgb)*32 for _, rgb in PALETTE)
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+
        chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
        chunk(b'IDAT',zlib.compress((b'\0'+row)*height)) + chunk(b'IEND',b''))


def log_mesh_state(logger, body, stage):
    """Read diagnostics defensively across Fusion versions."""
    for label, obj, names in (
        ('body',body,('appearanceSourceType','isClosed','isOriented','isValid')),
        ('display',getattr(body,'displayOverrides',None),
         ('isSuppressFaceGroupColors','isSuppressTriangleEdges')),
        ('displayMesh',getattr(body,'displayMesh',None),
         ('nodeCount','triangleCount','textureCount'))):
        for name in names:
            try:
                logger.info('%s %s.%s=%s',stage,label,name,getattr(obj,name))
            except Exception as exc:
                logger.info('%s %s.%s unavailable: %s',stage,label,name,exc)


def write_colored_obj(path=COLOR_OUTPUT):
    """Export the same closed mesh with per-face OBJ/MTL material assignments."""
    nx, ny, values = load_heights()
    raw = zlib.decompress(COLOR_ASSET.read_bytes())
    if struct.unpack_from('<II', raw) != (nx, ny) or len(raw) != 8+nx*ny:
        raise ValueError('Color grid does not match relief grid.')
    colors = raw[8:]
    if max(colors) >= len(PALETTE):
        raise ValueError('Unknown color material ID.')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mtl = path.with_suffix('.mtl')
    faces = path.with_suffix('.faces.tmp')
    vertices = {}
    previous = None
    write_palette_png(path.with_name('CamelandPanda-palette.png'))
    try:
        with faces.open('w', encoding='ascii') as stream:
            for triangle in mesh_triangles(nx, ny, values):
                indices = []
                for vertex in triangle:
                    if vertex not in vertices:
                        vertices[vertex] = len(vertices)+1
                    indices.append(vertices[vertex])
                color = 0
                if all(v[2] > 0 for v in triangle):
                    x = sum(v[0] for v in triangle)/3
                    y = sum(v[1] for v in triangle)/3
                    ix = min(nx-1,max(0,round(x/WIDTH_MM*(nx-1))))
                    iy = min(ny-1,max(0,round((1-y/HEIGHT_MM)*(ny-1))))
                    color = colors[iy*nx+ix]
                if color != previous:
                    # One texture material; each face samples a palette swatch.
                    if previous is None:
                        stream.write('usemtl Artwork\n')
                    previous = color
                stream.write('f {} {} {}\n'.format(*(str(i)+'/'+str(color+1) for i in indices)))
        with path.open('w', encoding='ascii') as stream:
            stream.write('# Millimeters; closed colored relief\nmtllib '+mtl.name+'\no CamelAndThreePandas\n')
            for v in vertices:
                stream.write('v {:.8f} {:.8f} {:.8f}\n'.format(*v))
            for i in range(len(PALETTE)):
                stream.write('vt {:.8f} 0.5\n'.format((i+.5)/len(PALETTE)))
            with faces.open('r', encoding='ascii') as source:
                shutil.copyfileobj(source, stream)
        with mtl.open('w', encoding='ascii') as stream:
            stream.write('newmtl Artwork\nKd 1 1 1\nKa 0 0 0\nKs 0 0 0\nd 1\nillum 1\n'
                         'map_Kd CamelandPanda-palette.png\n')
    finally:
        faces.unlink(missing_ok=True)
    return path


def run(context):
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    ui = app.userInterface
    logger = logging.getLogger('CamelandPanda')
    logger.setLevel(logging.INFO)
    handler = None
    started = time.monotonic()
    logger.propagate = False
    for old in list(logger.handlers):
        logger.removeHandler(old)
        old.close()
    try:
        handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)sZ %(levelname)s %(message)s')
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.info('=== textured-color-v2 RUN START; UTC timestamps; script=%s ===', __file__)
        logger.info('Start: Fusion %s; dimensions %s; relief %s mm', app.version,
                    (WIDTH_MM, HEIGHT_MM, TOTAL_THICKNESS_MM), RELIEF_MM)
        path, count = write_stl()
        logger.info('STL generated: %s; %d triangles', path, count)
        color_path = write_colored_obj()
        logger.info('Textured OBJ generated: %s', color_path)
        for artifact in (color_path, color_path.with_suffix('.mtl'),
                         color_path.with_name('CamelandPanda-palette.png'), ASSET, COLOR_ASSET):
            logger.info('Asset %s bytes=%d sha256=%s', artifact, artifact.stat().st_size,
                        hashlib.sha256(artifact.read_bytes()).hexdigest())
        logger.info('Palette=%s', PALETTE)
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name = 'Camel and Panda'
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('New Fusion design unavailable.')
        # Direct design avoids the parametric mesh import base-feature limitation.
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        design.unitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        bodies = design.rootComponent.meshBodies.add(
            str(color_path), adsk.fusion.MeshUnits.MillimeterMeshUnit)
        if not bodies or bodies.count != 1:
            raise RuntimeError('Expected one imported mesh body.')
        body = bodies.item(0)
        body.name = 'Camel and Panda — raised relief'
        log_mesh_state(logger, body, 'Before color display setup')
        body.appearance = None
        body.displayOverrides.isSuppressFaceGroupColors = True
        body.displayOverrides.isSuppressTriangleEdges = True
        log_mesh_state(logger, body, 'After color display setup')
        logger.info('Cleared body appearance override; enabled texture display without face-group colors.')
        design.rootComponent.attributes.add('CamelandPanda','dimensions_mm',
            '{} x {} x {}'.format(WIDTH_MM, HEIGHT_MM, TOTAL_THICKNESS_MM))
        app.activeViewport.fit()
        app.activeViewport.refresh()
        logger.info('Imported one mesh body successfully.')
        ui.messageBox('Created {} x {} x {} mm plaque.\n'
                      '{} mm base + up to {} mm raised artwork.\n\n'
                      'Save the new design in Fusion.\n'
                      'Colors: red carpet, flag and tongues.\n'
                      'If colors are hidden, turn off Material > Apply a different appearance\n'
                      'in Fusion Preferences and hide mesh face groups (Shift+F).\n\n'
                      'STL geometry (millimeters; no colors):\n{}\n\nLog sidecar:\n{}'.format(
                          WIDTH_MM, HEIGHT_MM, TOTAL_THICKNESS_MM,
                          TOTAL_THICKNESS_MM-RELIEF_MM, RELIEF_MM, path, LOG_PATH))
    except Exception:
        details = traceback.format_exc()
        logger.error(details)
        ui.messageBox('Plaque creation failed:\n{}\nLog: {}'.format(details,LOG_PATH))
    finally:
        if handler:
            logger.info('RUN END elapsed=%.2fs; sidecar=%s', time.monotonic()-started, LOG_PATH)
            handler.flush()
            logger.removeHandler(handler)
            handler.close()


if __name__ == '__main__' and '--stl-only' in sys.argv:
    path, count = write_stl()
    print('{} ({} triangles; {} x {} x {} mm)'.format(
        path,count,WIDTH_MM,HEIGHT_MM,TOTAL_THICKNESS_MM))

if __name__ == '__main__' and '--color-only' in sys.argv:
    print(write_colored_obj())
