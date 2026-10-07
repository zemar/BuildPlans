"""Python-generated plaque; run in Fusion or with `python3 MyriSaying.py`.

Standard library only. The bundled cursive outlines are made by prepare_text.py.
Coordinates in millimeters: X right, +Y rearward, +Z up; front face Y=0.
"""
import hashlib
import json
import logging
import math
from pathlib import Path
import struct
import time
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / 'MyriSaying.log'
LOGGER = logging.getLogger('MyriSaying')
WIDTH_MM = 200.0
HEIGHT_MM = 100.0
THICKNESS_MM = 10.0
FRAME_MM = 4.0
RAISED_MM = 1.2
FOOT_WIDTH_MM = 8.0
FOOT_DEPTH_MM = 40.0
FOOT_HEIGHT_MM = 65.0
FOOT_CENTERS_MM = (-65.0, 65.0)
FONT_NAME = 'Brush Script MT'
# Text, visible outline height, center height. All values are millimeters.
LINES = [
    ("The super power that you'll", 11.0, 81.0),
    ('never lose is being the', 11.0, 64.5),
    ('best daddy ever.', 13.0, 47.5),
    ('Myriam Howard', 9.0, 25.5),
    ('March 19, 2023', 7.5, 12.0),
]
COLORS = {'Brown': '#80451FFF', 'Black': '#101010FF', 'White': '#FFFFFFFF'}


def start_log():
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    handler = logging.FileHandler(LOG_PATH, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)sZ %(levelname)s %(message)s')
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.info('=== RUN START; UTC; script=%s ===', __file__)


def close_log():
    for handler in list(LOGGER.handlers):
        handler.flush()
        handler.close()
        LOGGER.removeHandler(handler)


def text_spec():
    return {'width': WIDTH_MM, 'height': HEIGHT_MM, 'frame': FRAME_MM,
            'font': FONT_NAME, 'lines': [list(line) for line in LINES]}


def extrude(vertices, faces, depth, transform):
    """Extrude CCW triangulated planar regions, including holes and islands."""
    edges = {}
    for a, b, c in faces:
        for u, v in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((u, v)))
            if key in edges:
                edges[key] = None
            else:
                edges[key] = (u, v)
    n = len(vertices)
    points = [transform(x, y, h) for h in (0, depth) for x, y in vertices]
    triangles = [(c, b, a) for a, b, c in faces]
    triangles += [(a+n, b+n, c+n) for a, b, c in faces]
    for edge in edges.values():
        if edge:
            a, b = edge
            triangles.extend(((a, b, b+n), (a, b+n, a+n)))
    return points, triangles


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [(0, 1, 2), (0, 2, 3)]


def build():
    dimensions = (WIDTH_MM, HEIGHT_MM, THICKNESS_MM, FRAME_MM, RAISED_MM,
                  FOOT_WIDTH_MM, FOOT_DEPTH_MM, FOOT_HEIGHT_MM)
    if not all(math.isfinite(v) and v > 0 for v in dimensions):
        raise ValueError('Dimensions must be finite positive millimeters.')
    if FRAME_MM * 2 >= min(WIDTH_MM, HEIGHT_MM):
        raise ValueError('Frame is too wide.')
    if len(FOOT_CENTERS_MM) != 2 or FOOT_HEIGHT_MM > HEIGHT_MM:
        raise ValueError('Exactly two supports must fit the plaque height.')
    if any(abs(x) + FOOT_WIDTH_MM/2 >= WIDTH_MM/2 for x in FOOT_CENTERS_MM):
        raise ValueError('Supports extend past the plaque sides.')
    if abs(FOOT_CENTERS_MM[1] - FOOT_CENTERS_MM[0]) <= FOOT_WIDTH_MM:
        raise ValueError('Rear supports must be separated.')
    asset = HERE / 'assets' / 'lettering.json'
    data = json.loads(asset.read_text(encoding='utf-8'))
    if data['spec'] != text_spec():
        raise ValueError('Text layout changed. Run prepare_text.py to rebuild the outlines.')
    LOGGER.info('Inputs: %s; panel thickness=%s; relief=%s; supports=%s x %s x %s',
                text_spec(), THICKNESS_MM, RAISED_MM,
                FOOT_WIDTH_MM, FOOT_DEPTH_MM, FOOT_HEIGHT_MM)
    LOGGER.info('Font outlines: %s; sha256=%s', data['font'],
                hashlib.sha256(asset.read_bytes()).hexdigest())
    w, h, f, d = WIDTH_MM/2, HEIGHT_MM, FRAME_MM, THICKNESS_MM
    # (u,v,height) -> (u,-height,v) is a proper rotation. Extrude toward viewer.
    panel_map = lambda u, v, t: (u, d-t, v)
    brown = extrude(*rect(-w+f, f, w-f, h-f), d, panel_map)
    outer = [(-w, 0), (w, 0), (w, h), (-w, h)]
    inner = [(-w+f, f), (w-f, f), (w-f, h-f), (-w+f, h-f)]
    ring_faces = []
    for i in range(4):
        j = (i+1) % 4
        ring_faces.extend(((i, j, j+4), (i, j+4, i+4)))
    frame = extrude(outer+inner, ring_faces, d, panel_map)
    parts = [('Plaque - Brown', 'Brown', brown), ('Frame - Black', 'Black', frame)]
    for label, x in zip(('Left', 'Right'), FOOT_CENTERS_MM):
        # A YZ triangle extruded along X, with its entire front edge on the back.
        triangle = [(d, 0), (d+FOOT_DEPTH_MM, 0), (d, FOOT_HEIGHT_MM)]
        foot = extrude(triangle, [(0, 1, 2)], FOOT_WIDTH_MM,
                       lambda u, v, t, x=x: (x-FOOT_WIDTH_MM/2+t, u, v))
        parts.append((label+' support - Black', 'Black', foot))
    writing = extrude(data['vertices'], data['faces'], RAISED_MM,
                      lambda u, v, t: (u, -t, v))
    parts.append(('Writing - White', 'White', writing))
    return parts, data


def audit(mesh):
    vertices, faces = mesh
    edges, volume6, centroid = {}, 0.0, [0.0]*3
    for a, b, c in faces:
        p, q, r = vertices[a], vertices[b], vertices[c]
        u = [q[i]-p[i] for i in range(3)]
        v = [r[i]-p[i] for i in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        if sum(x*x for x in cross) < 1e-20:
            raise ValueError('Degenerate triangle detected.')
        det = (p[0]*(q[1]*r[2]-q[2]*r[1]) + p[1]*(q[2]*r[0]-q[0]*r[2])
               + p[2]*(q[0]*r[1]-q[1]*r[0]))
        volume6 += det
        for i in range(3):
            centroid[i] += det*(p[i]+q[i]+r[i])/4
        for a1, b1 in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((a1, b1)))
            count, winding = edges.get(key, (0, 0))
            edges[key] = count+1, winding+(1 if a1 < b1 else -1)
    if not faces or volume6 <= 0 or any(e != (2, 0) for e in edges.values()):
        raise ValueError('Mesh is not a closed, outward-facing solid.')
    bounds = [[min(p[i] for p in vertices) for i in range(3)],
              [max(p[i] for p in vertices) for i in range(3)]]
    return {'vertices': len(vertices), 'triangles': len(faces), 'watertight': True,
            'consistent_winding': True, 'volume_mm3': volume6/6,
            'center_of_mass_mm': [v/volume6 for v in centroid], 'bounds_mm': bounds}


def write_stl(path, mesh):
    vertices, faces = mesh
    with path.open('wb') as out:
        out.write(b'MyriSaying; millimeters'.ljust(80, b'\0'))
        out.write(struct.pack('<I', len(faces)))
        for face in faces:
            out.write(struct.pack('<12fH', 0, 0, 0,
                                  *(v for index in face for v in vertices[index]), 0))


def write_3mf(path, parts):
    ns = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    ET.register_namespace('', ns)
    tag = lambda s: '{'+ns+'}'+s
    model = ET.Element(tag('model'), unit='millimeter', attrib={'xml:lang': 'en-US'})
    ET.SubElement(model, tag('metadata'), name='Title').text = 'MyriSaying'
    resources = ET.SubElement(model, tag('resources'))
    materials = ET.SubElement(resources, tag('basematerials'), id='1')
    for name, color in COLORS.items():
        ET.SubElement(materials, tag('base'), name=name, displaycolor=color)
    for ident, (name, color, (points, faces)) in enumerate(parts, 2):
        obj = ET.SubElement(resources, tag('object'), id=str(ident), name=name,
                            type='model', pid='1', pindex=str(list(COLORS).index(color)))
        mesh = ET.SubElement(obj, tag('mesh'))
        vertices = ET.SubElement(mesh, tag('vertices'))
        for p in points:
            ET.SubElement(vertices, tag('vertex'), **dict(zip(('x','y','z'),
                          (format(v, '.8f') for v in p))))
        triangles = ET.SubElement(mesh, tag('triangles'))
        for face in faces:
            ET.SubElement(triangles, tag('triangle'),
                          **dict(zip(('v1','v2','v3'), map(str, face))))
    assembly_id = str(len(parts)+2)
    assembly = ET.SubElement(resources, tag('object'), id=assembly_id,
                             name='MyriSaying', type='model')
    components = ET.SubElement(assembly, tag('components'))
    for ident in range(2, len(parts)+2):
        ET.SubElement(components, tag('component'), objectid=str(ident))
    build = ET.SubElement(model, tag('build'))
    ET.SubElement(build, tag('item'), objectid=assembly_id)
    content = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
               '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content)
        archive.writestr('_rels/.rels', rels)
        archive.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))


def write_preview(data):
    """Vector preview of actual outlines, plus a dimensioned side elevation."""
    import html
    w, h, f = WIDTH_MM, HEIGHT_MM, FRAME_MM
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="820" viewBox="-12 -12 224 154">',
           '<rect x="-12" y="-12" width="224" height="154" fill="#ebe8e2"/>',
           '<g transform="translate(0 100) scale(1 -1)">',
           '<rect width="200" height="100" fill="'+COLORS['Black'][:7]+'"/>',
           '<rect x="4" y="4" width="192" height="92" fill="'+COLORS['Brown'][:7]+'"/>']
    for line in data['outlines']:
        path = ' '.join('M '+' L '.join(f'{x+w/2:.5f},{y:.5f}' for x,y in ring)+' Z'
                        for ring in line['rings'])
        svg.append('<path fill="white" fill-rule="evenodd" d="'+path+'"><title>'
                   +html.escape(line['text'])+'</title></path>')
    svg += ['</g>', '<g font-family="sans-serif" fill="#333" font-size="3.6">',
            '<text x="0" y="108">Front: 200 × 100 mm · 4 mm black frame · raised cursive lettering</text>',
            '<text x="0" y="117">Panel: 10 mm thick · lettering: +1.2 mm</text>',
            '<text x="0" y="125">Two rear triangles: 8 mm wide × 40 mm deep × 65 mm tall</text>',
            '<text x="0" y="133">Side view →</text></g>',
            '<g transform="translate(172 137) scale(.22 -.22)">',
            '<rect x="0" y="0" width="10" height="100" fill="#80451f"/>',
            '<path d="M 10,0 L 50,0 L 10,65 Z" fill="#101010"/>',
            '<path d="M -1.2,7 L -1.2,90" stroke="white" stroke-width="1.2"/>',
            '</g></svg>']
    (HERE / 'preview.svg').write_text('\n'.join(svg), encoding='utf-8')


def generate():
    parts, data = build()
    reports = {name: audit(mesh) for name, color, mesh in parts}
    total_volume = sum(r['volume_mm3'] for r in reports.values())
    com = [sum(r['volume_mm3']*r['center_of_mass_mm'][i] for r in reports.values())/total_volume
           for i in range(3)]
    # Conservative interior rectangle of the table-contact polygon.
    if not (min(FOOT_CENTERS_MM) < com[0] < max(FOOT_CENTERS_MM)
            and 0 < com[1] < THICKNESS_MM+FOOT_DEPTH_MM):
        raise ValueError('Center of mass is outside the support footprint.')
    reports['assembly'] = {'center_of_mass_mm_equal_density': com,
        'static_stability_check': 'inside support footprint (equal-density solid model)',
        'panel_dimensions_mm': [WIDTH_MM, HEIGHT_MM, THICKNESS_MM],
        'overall_xyz_mm': [WIDTH_MM, THICKNESS_MM+FOOT_DEPTH_MM+RAISED_MM, HEIGHT_MM],
        'text': [line[0] for line in LINES], 'font': FONT_NAME,
        'fusion_execution_verified': False, 'physical_print_verified': False}
    output = HERE / 'exports'
    output.mkdir(exist_ok=True)
    for index, (name, color, mesh) in enumerate(parts, 1):
        path = output / (f'{index:02d}_'+name.replace(' ', '_')+'.stl')
        write_stl(path, mesh)
        LOGGER.info('PART %s: %s; output=%s', name, reports[name], path)
    write_3mf(output/'MyriSaying.3mf', parts)
    (output/'validation.json').write_text(json.dumps(reports, indent=2)+'\n', encoding='utf-8')
    write_preview(data)
    LOGGER.info('SUCCESS: generated five color-separated parts; center of mass=%s; '
                'Fusion execution and physical printing not verified.', com)
    return parts


def appearance(design, seed, name, rgba):
    import adsk.core
    rgb = tuple(int(rgba[i:i+2], 16) for i in (1, 3, 5))
    color = adsk.core.Color.create(*rgb, 255)
    result = design.appearances.addByCopy(seed, 'MyriSaying - '+name)
    for key in ('opaque_albedo', 'generic_diffuse', 'metal_f0'):
        prop = adsk.core.ColorProperty.cast(result.appearanceProperties.itemById(key))
        if prop:
            if prop.hasConnectedTexture:
                prop.hasConnectedTexture = False
            prop.value = color
            return result
    raise RuntimeError('Could not apply the '+name+' appearance.')


def run(context):
    """Fusion entry point. Regenerates exports and opens a new unsaved design."""
    import adsk.core
    import adsk.fusion
    app = adsk.core.Application.get()
    start_log()
    started = time.monotonic()
    try:
        LOGGER.info('Fusion version: %s', app.version)
        parts = generate()
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name = 'MyriSaying'
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        design.unitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        component = design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()).component
        component.name = 'MyriSaying'
        appearances = {}
        for index, (name, color, mesh) in enumerate(parts, 1):
            path = HERE/'exports'/(f'{index:02d}_'+name.replace(' ', '_')+'.stl')
            bodies = component.meshBodies.add(str(path), adsk.fusion.MeshUnits.MillimeterMeshUnit)
            if not bodies or bodies.count != 1:
                raise RuntimeError('Expected one imported mesh body for '+name)
            body = bodies.item(0)
            body.name = name
            if color not in appearances:
                appearances[color] = appearance(design, body.appearance, color, COLORS[color])
            body.appearance = appearances[color]
            body.displayOverrides.isSuppressFaceGroupColors = True
            body.displayOverrides.isSuppressTriangleEdges = True
            LOGGER.info('Imported and colored: %s; facets=%s', name, len(mesh[1]))
        camera = app.activeViewport.camera
        camera.target = adsk.core.Point3D.create(0, 1, 5)
        camera.eye = adsk.core.Point3D.create(14, -30, 15)
        camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
        camera.isFitView = True
        app.activeViewport.camera = camera
        app.activeViewport.refresh()
        LOGGER.info('FUSION SUCCESS: five mesh bodies; save the new design manually.')
        app.userInterface.messageBox(
            'Created MyriSaying: 200 × 100 × 10 mm panel, 1.2 mm raised cursive, '
            'and two rear triangular supports.\n\n'
            'Brown plaque, black frame/supports, white lettering.\n'
            'Save the new Fusion design.\n\n3MF: '+str(HERE/'exports'/'MyriSaying.3mf')+
            '\nLog: '+str(LOG_PATH), 'MyriSaying')
    except Exception:
        LOGGER.exception('Fusion generation failed')
        app.userInterface.messageBox('MyriSaying failed. See the full traceback in:\n'+str(LOG_PATH))
        raise
    finally:
        LOGGER.info('RUN END elapsed=%.2fs', time.monotonic()-started)
        close_log()


if __name__ == '__main__':
    start_log()
    try:
        generate()
        print('Generated:', HERE/'exports'/'MyriSaying.3mf')
        print('Log sidecar:', LOG_PATH)
    except Exception:
        LOGGER.exception('Local generation failed')
        raise
    finally:
        close_log()
