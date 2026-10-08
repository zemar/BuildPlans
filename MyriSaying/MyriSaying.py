"""Python-generated plaque; run in Fusion or with `python3 MyriSaying.py`.

Standard library only. The bundled cursive outlines are made by prepare_text.py.
Coordinates in millimeters: X right, +Y rearward, +Z up; panel leans back 10 degrees.
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
THICKNESS_MM = 3.0
FRAME_MM = 6.0
RAISED_MM = 1.2
LEAN_DEGREES = 10.0
ROPE_STRAND_RADIUS_MM = 1.65
ROPE_TWIST_RADIUS_MM = 0.85
ROPE_PITCH_MM = 10.0
FOOT_WIDTH_MM = 8.0
FOOT_DEPTH_MM = 40.0
FOOT_HEIGHT_MM = 65.0
FOOT_CENTERS_MM = (-65.0, 65.0)
FONT_NAME = 'Snell Roundhand Bold'
# Text, visible outline height, center height. All values are millimeters.
LINES = [
    ("The super power that you'll", 14.0, 80.0),
    ('never lose is being the', 14.0, 60.0),
    ('best daddy ever.', 16.0, 40.0),
    ('Myriam Howard', 6.5, 21.0),
    ('March 19, 2023', 5.0, 12.0),
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


def lean(point):
    """Rotate the panel backward, keeping its rear bottom edge on the table."""
    x,y,z = point
    angle = math.radians(LEAN_DEGREES)
    c,s = math.cos(angle), math.sin(angle)
    return x, y*c+z*s, z*c-y*s+THICKNESS_MM*s


def rope_frame():
    """Closed brown frame with a fused two-strand twisted-rope front relief.

    The visible surface is the upper envelope of two circular rope strands
    whose centers orbit along the perimeter. A solid backing joins the strands
    and closes the underside, avoiding coincident/intersecting mesh shells.
    """
    w,h,f = WIDTH_MM/2, HEIGHT_MM, FRAME_MM
    outside = [(-w,0),(w,0),(w,h),(-w,h)]
    inside = [(-w+f,f),(w-f,f),(w-f,h-f),(-w+f,h-f)]
    lengths = [WIDTH_MM-f, HEIGHT_MM-f]*2
    perimeter = sum(lengths)
    turns = max(1, round(perimeter/ROPE_PITCH_MM))
    points, relief, faces = [], [], []
    cross_steps = 24
    traveled = 0
    for edge,length in enumerate(lengths):
        nxt = (edge+1)%4
        steps = math.ceil(length/0.65)
        for step in range(steps):
            t = step/steps
            outer = [outside[edge][k]*(1-t)+outside[nxt][k]*t for k in (0,1)]
            inner = [inside[edge][k]*(1-t)+inside[nxt][k]*t for k in (0,1)]
            phase = 2*math.pi*turns*(traveled+length*t)/perimeter
            for j in range(cross_steps+1):
                u = j/cross_steps
                points.append(tuple(outer[k]*(1-u)+inner[k]*u for k in (0,1)))
                across = (u-.5)*f
                height = 0.0
                for sign in (-1,1):
                    center_u = sign*ROPE_TWIST_RADIUS_MM*math.cos(phase)
                    center_h = sign*ROPE_TWIST_RADIUS_MM*math.sin(phase)
                    radicand = ROPE_STRAND_RADIUS_MM**2-(across-center_u)**2
                    if radicand > 0:
                        height = max(height, center_h+math.sqrt(radicand))
                relief.append(height)
        traveled += length
    stride = cross_steps+1
    stations = len(points)//stride
    for i in range(stations):
        nxt = (i+1)%stations
        for j in range(cross_steps):
            a,b,c,d = i*stride+j,nxt*stride+j,nxt*stride+j+1,i*stride+j+1
            faces.extend(((a,b,c),(a,c,d)))
    vertices, triangles = extrude(points, faces, THICKNESS_MM,
                                  lambda u,v,t: (u,THICKNESS_MM-t,v))
    count = len(points)
    for i,value in enumerate(relief):
        x,y,z = vertices[count+i]
        vertices[count+i] = (x,y-value,z)
    return vertices, triangles


def build():
    dimensions = (WIDTH_MM, HEIGHT_MM, THICKNESS_MM, FRAME_MM, RAISED_MM,
                  FOOT_WIDTH_MM, FOOT_DEPTH_MM, FOOT_HEIGHT_MM, ROPE_STRAND_RADIUS_MM,
                  ROPE_TWIST_RADIUS_MM, ROPE_PITCH_MM)
    if not all(math.isfinite(v) and v > 0 for v in dimensions):
        raise ValueError('Dimensions must be finite positive millimeters.')
    if FRAME_MM * 2 >= min(WIDTH_MM, HEIGHT_MM):
        raise ValueError('Frame is too wide.')
    if not 0 <= LEAN_DEGREES <= 20:
        raise ValueError('Lean must be between 0 and 20 degrees.')
    if ROPE_STRAND_RADIUS_MM+ROPE_TWIST_RADIUS_MM >= FRAME_MM/2:
        raise ValueError('Rope must fit inside the frame width.')
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
    panel = extrude(*rect(-w+f, f, w-f, h-f), d, panel_map)
    parts = [('Plaque - Black', 'Black', panel),
             ('Twisted rope frame - Brown', 'Brown', rope_frame())]
    writing = extrude(data['vertices'], data['faces'], RAISED_MM,
                      lambda u, v, t: (u, -t, v))
    parts.append(('Writing - White', 'White', writing))
    parts = [(name,color,([lean(p) for p in mesh[0]],mesh[1]))
             for name,color,mesh in parts]
    angle = math.radians(LEAN_DEGREES)
    rear_bottom = d*math.cos(angle)
    for label, x in zip(('Left', 'Right'), FOOT_CENTERS_MM):
        # A slanted front edge meets the tilted back; the foot stays on Z=0.
        triangle = [(rear_bottom,0), (rear_bottom+FOOT_DEPTH_MM,0),
                    (rear_bottom+FOOT_HEIGHT_MM*math.sin(angle),
                     FOOT_HEIGHT_MM*math.cos(angle))]
        foot = extrude(triangle, [(0, 1, 2)], FOOT_WIDTH_MM,
                       lambda u, v, t, x=x: (x-FOOT_WIDTH_MM/2+t, u, v))
        parts.append((label+' support - Black', 'Black', foot))
    LOGGER.info('Design: black panel, brown twisted-rope frame, white cursive; '
                'backward lean=%s degrees; rope radius=%s, orbit=%s, pitch~%s mm',
                LEAN_DEGREES,ROPE_STRAND_RADIUS_MM,ROPE_TWIST_RADIUS_MM,ROPE_PITCH_MM)
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
           f'<rect width="{w}" height="{h}" fill="'+COLORS['Brown'][:7]+'"/>',
           f'<rect x="{f}" y="{f}" width="{w-2*f}" height="{h-2*f}" fill="'+COLORS['Black'][:7]+'"/>']
    for line in data['outlines']:
        path = ' '.join('M '+' L '.join(f'{x+w/2:.5f},{y:.5f}' for x,y in ring)+' Z'
                        for ring in line['rings'])
        svg.append('<path fill="white" fill-rule="evenodd" d="'+path+'"><title>'
                   +html.escape(line['text'])+'</title></path>')
    svg += ['</g>', '<g font-family="sans-serif" fill="#333" font-size="3.6">',
            f'<text x="0" y="108">Face: {w:g} × {h:g} mm · brown rope frame (see 3D preview)</text>',
            f'<text x="0" y="117">Black panel: {THICKNESS_MM:g} mm · white lettering: +{RAISED_MM:g} mm</text>',
            f'<text x="0" y="125">Backward lean: {LEAN_DEGREES:g}° · two black triangular supports</text>',
            '<text x="0" y="133">Snell Roundhand Bold · larger saying, smaller name and date</text>',
            '</g></svg>']
    (HERE / 'preview.svg').write_text('\n'.join(svg), encoding='utf-8')


def generate():
    parts, data = build()
    reports = {name: audit(mesh) for name, color, mesh in parts}
    total_volume = sum(r['volume_mm3'] for r in reports.values())
    com = [sum(r['volume_mm3']*r['center_of_mass_mm'][i] for r in reports.values())/total_volume
           for i in range(3)]
    rear_bottom = THICKNESS_MM*math.cos(math.radians(LEAN_DEGREES))
    if not (min(FOOT_CENTERS_MM) < com[0] < max(FOOT_CENTERS_MM)
            and rear_bottom < com[1] < rear_bottom+FOOT_DEPTH_MM):
        raise ValueError('Center of mass is outside the support footprint.')
    all_points = [p for _,_,mesh in parts for p in mesh[0]]
    overall = [max(p[i] for p in all_points)-min(p[i] for p in all_points) for i in range(3)]
    reports['assembly'] = {'center_of_mass_mm_equal_density': com,
        'static_stability_check': 'inside support footprint (equal-density solid model)',
        'panel_dimensions_mm': [WIDTH_MM, HEIGHT_MM, THICKNESS_MM],
        'overall_xyz_mm': overall, 'backward_lean_degrees': LEAN_DEGREES,
        'text': [line[0] for line in LINES], 'font': FONT_NAME,
        'fusion_execution_verified': False, 'physical_print_verified': False}
    output = HERE / 'exports'
    output.mkdir(exist_ok=True)
    (output/'independent-validation.json').unlink(missing_ok=True)
    # Remove only earlier generated parts, so changed names cannot leave stale STLs.
    for old in output.glob('[0-9][0-9]_*.stl'):
        old.unlink()
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
            'Created MyriSaying: 200 × 100 × 3 mm panel, 1.2 mm raised cursive, '
            '10 degree backward lean, and two rear triangular supports.\n\n'
            'Black plaque/supports, brown twisted-rope frame, white lettering.\n'
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
