"""Run inside Autodesk Fusion: Utilities > Scripts and Add-Ins > Scripts.

Creates a 127 mm trophy with separate volleyball, base, stand, and text bodies.
All dimensions below are millimeters; Fusion geometry uses centimeters.
Uses Fusion's bundled API and Python's standard library. Native 3MF export
uses the locally installed Bambu Studio application and its H2D profiles.
"""
import math
import json
import re
import shutil
import subprocess
import tempfile
import traceback
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import adsk.core
import adsk.fusion


PLAYER_NAME = "Myriam Howard"  # Change this and rerun for each player.
FONT_NAME = "Arial"
TOTAL_HEIGHT_MM = 127.0
BALL_RADIUS_MM = 25.0
SEAM_RADIUS_MM = 0.65  # Rounded grooves: approximately 1.3 mm wide.
ENGRAVE_DEPTH_MM = 1.2  # Flush contrasting text inlays, embedded into the base.
EXPORT_BAMBU_PROJECT = False
# Z-up is required for direct Fusion Save As Mesh exports to slicers.
CAD_Y_UP = False
BAMBU_EXECUTABLE = '/Applications/BambuStudio.app/Contents/MacOS/BambuStudio'
BAMBU_MACHINE_PROFILE = 'Bambu Lab H2D 0.4 nozzle'
BAMBU_PROCESS_PROFILE = '0.16mm Standard @BBL H2D'
BAMBU_FILAMENT_PROFILE = 'Generic PLA @BBL H2D'


def closed_mesh(coordinates, indices, name):
    """Stitch Fusion's per-face vertices into an indexed, closed solid mesh."""
    vertices, remap, lookup = [], [], {}
    # One-millionth mm is far below printing precision but absorbs floating
    # point residue at coincident face boundaries. Serialize these same points.
    for p in coordinates:
        key = tuple(round(value * 1000000) for value in ((p.x * 10, -p.z * 10, p.y * 10) if CAD_Y_UP
                                    else (p.x * 10, p.y * 10, p.z * 10)))
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(tuple(value / 1000000 for value in key))
        remap.append(lookup[key])
    if len(indices) % 3:
        raise RuntimeError('Invalid triangle indices: ' + name)
    triangles, edges, neighbors = [], {}, {}
    volume6 = 0.0
    for i in range(0, len(indices), 3):
        triangle = tuple(remap[indices[i + j]] for j in range(3))
        if len(set(triangle)) != 3:
            # A triangle collapsed onto a welded seam carries no surface.
            # Discard it; the edge audit below still requires a closed mesh.
            continue
        a, b, c = triangle
        pa, pb, pc = vertices[a], vertices[b], vertices[c]
        volume6 += (pa[0] * (pb[1] * pc[2] - pb[2] * pc[1])
                    + pa[1] * (pb[2] * pc[0] - pb[0] * pc[2])
                    + pa[2] * (pb[0] * pc[1] - pb[1] * pc[0]))
        for start, end in ((a, b), (b, c), (c, a)):
            key = (min(start, end), max(start, end))
            count, winding = edges.get(key, (0, 0))
            edges[key] = (count + 1, winding + (1 if start < end else -1))
            neighbors.setdefault(start, set()).add(end)
            neighbors.setdefault(end, set()).add(start)
        triangles.append(triangle)
    invalid = sum(count != 2 or winding != 0 for count, winding in edges.values())
    if invalid or not triangles:
        raise RuntimeError('Mesh is not a closed, consistently wound solid: {} ({} invalid edges)'
                           .format(name, invalid))
    if volume6 <= 0:
        raise RuntimeError('Mesh has inward faces or zero volume: ' + name)
    # Each Fusion body must remain a single shell. The Writing part combines
    # multiple individually validated bodies afterward, keeping each glyph.
    visited = set()
    queue = [triangles[0][0]]
    while queue:
        vertex = queue.pop()
        if vertex not in visited:
            visited.add(vertex)
            queue.extend(neighbors[vertex] - visited)
    if len(visited) != len(neighbors):
        raise RuntimeError('Disconnected shells in body mesh: ' + name)
    return vertices, triangles


def write_assembled_mesh(path, groups, title):
    """Four named parts, with all letters grouped; mesh rotates CAD Y-up to Z-up."""
    core = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
    material = 'http://schemas.microsoft.com/3dmanufacturing/material/2015/02'
    ET.register_namespace('', core)
    ET.register_namespace('m', material)
    tag = lambda name: '{' + core + '}' + name
    model = ET.Element(tag('model'), unit='millimeter', attrib={'xml:lang': 'en-US'})
    ET.SubElement(model, tag('metadata'), name='Title').text = title
    resources = ET.SubElement(model, tag('resources'))
    colors = ET.SubElement(resources, '{' + material + '}colorgroup', id='10')
    for color in ('#000000FF', '#FFFFFFFF'):
        ET.SubElement(colors, '{' + material + '}color', color=color)
    config = ET.Element('config')
    config_object = ET.SubElement(config, 'object', id='5')
    ET.SubElement(config_object, 'metadata', key='name', value=title)
    for part_id, (name, bodies, filament) in enumerate(groups, 1):
        obj = ET.SubElement(resources, tag('object'), id=str(part_id), name=name,
                            type='model', pid='10', pindex=str(filament - 1))
        mesh = ET.SubElement(obj, tag('mesh'))
        vertices = ET.SubElement(mesh, tag('vertices'))
        triangles = ET.SubElement(mesh, tag('triangles'))
        offset = 0
        for body in bodies:
            calculator = body.meshManager.createMeshCalculator()
            calculator.surfaceTolerance = 0.002  # cm: 0.02 mm surface tolerance.
            mesh_data = calculator.calculate()
            if mesh_data is None:
                raise RuntimeError('Could not mesh body: ' + body.name)
            coordinates, body_triangles = closed_mesh(
                mesh_data.nodeCoordinates, mesh_data.nodeIndices, body.name)
            for x, y, z in coordinates:
                ET.SubElement(vertices, tag('vertex'),
                              x=format(x, '.9f'), y=format(y, '.9f'), z=format(z, '.9f'))
            for a, b, c in body_triangles:
                ET.SubElement(triangles, tag('triangle'),
                              v1=str(a + offset), v2=str(b + offset), v3=str(c + offset))
            offset += len(coordinates)
        if not offset or not len(triangles):
            raise RuntimeError('No printable mesh for ' + name)
        part = ET.SubElement(config_object, 'part', id=str(part_id), subtype='normal_part')
        ET.SubElement(part, 'metadata', key='name', value=name)
        ET.SubElement(part, 'metadata', key='extruder', value=str(filament))
        write_run_log('MESH: {}; vertices={}; triangles={}; filament={}'.format(
            name, offset, len(triangles), filament))
    assembly = ET.SubElement(resources, tag('object'), id='5', name=title, type='model')
    components = ET.SubElement(assembly, tag('components'))
    for part_id in range(1, 5):
        ET.SubElement(components, tag('component'), objectid=str(part_id))
    build = ET.SubElement(model, tag('build'))
    ET.SubElement(build, tag('item'), objectid='5',
                  transform='1 0 0 0 1 0 0 0 1 175 160 0')
    content_types = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                     '<Default Extension="config" ContentType="application/xml"/></Types>')
    relationships = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
                     'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', relationships)
        archive.writestr('3D/3dmodel.model', ET.tostring(model, encoding='utf-8', xml_declaration=True))
        archive.writestr('Metadata/model_settings.config',
                         ET.tostring(config, encoding='utf-8', xml_declaration=True))


def configure_h2d_project(path):
    """Supply the physical nozzle inventory omitted by Bambu's CLI exporter."""
    pending = path.with_suffix('.configured.3mf')
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(pending, 'w', zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == 'Metadata/project_settings.config':
                settings = json.loads(data)
                settings.update(extruder_nozzle_stats=['Standard#1', 'Standard#1'],
                                filament_map=['1', '2'], filament_map_2=['1', '2'],
                                filament_nozzle_map=['1', '2'], filament_map_mode='Manual',
                                wipe_tower_x=['80'], wipe_tower_y=['230'])
                data = json.dumps(settings).encode('utf-8')
            elif item.filename == 'Metadata/model_settings.config':
                config = ET.fromstring(data)
                for entry in config.findall('plate/metadata'):
                    if entry.get('key') == 'filament_map_mode':
                        entry.set('value', 'Manual')
                data = ET.tostring(config, encoding='utf-8', xml_declaration=True)
            target.writestr(item, data)
    pending.replace(path)


def export_bambu_project(groups, player_name):
    """Use installed Bambu Studio to generate its own complete native config."""
    executable = Path(BAMBU_EXECUTABLE)
    if not executable.is_file():
        raise RuntimeError('Bambu Studio not found. Set BAMBU_EXECUTABLE, or set '
                           'EXPORT_BAMBU_PROJECT=False to generate just the Fusion design.')
    profile_root = executable.parent.parent / 'Resources' / 'profiles' / 'BBL'
    index = {p.stem: p for p in profile_root.rglob('*.json')}

    def resolve(name, ancestry=()):
        if name in ancestry:
            raise RuntimeError('Bambu profile inheritance cycle: ' + name)
        if name not in index:
            raise RuntimeError('Bambu profile not installed: ' + name)
        data = json.loads(index[name].read_text(encoding='utf-8'))
        result = {}
        if data.get('inherits'):
            result.update(resolve(data['inherits'], ancestry + (name,)))
        for include in data.get('include', []):
            result.update(resolve(include, ancestry + (name,)))
        result.update(data)
        result.pop('inherits', None)
        result.pop('include', None)
        return result

    output = Path(__file__).resolve().with_name('Trophy.3mf')
    write_run_log('BAMBU EXPORT: {}; {}; {}; {}'.format(
        output, BAMBU_MACHINE_PROFILE, BAMBU_PROCESS_PROFILE, BAMBU_FILAMENT_PROFILE))
    with tempfile.TemporaryDirectory(prefix='trophy-bambu-') as directory:
        temporary = Path(directory)
        assembled = temporary / 'assembled.3mf'
        write_assembled_mesh(assembled, groups, 'Valley Catholic 2026 - ' + player_name)
        machine = resolve(BAMBU_MACHINE_PROFILE)
        process = resolve(BAMBU_PROCESS_PROFILE)
        process.update(enable_support='1', support_type='tree(auto)',
                       support_on_build_plate_only='0')
        filament = resolve(BAMBU_FILAMENT_PROFILE)
        for filename, data in (('machine', machine), ('process', process),
                               ('black', dict(filament, filament_colour=['#000000'])),
                               ('white', dict(filament, filament_colour=['#FFFFFF']))):
            (temporary / (filename + '.json')).write_text(json.dumps(data), encoding='utf-8')
        native = temporary / 'project.3mf'
        command = [str(executable), '--datadir', str(temporary / 'settings'),
                   '--arrange', '0', '--orient', '0',
                   '--load-settings', str(temporary / 'machine.json') + ';' + str(temporary / 'process.json'),
                   '--load-filaments', str(temporary / 'black.json') + ';' + str(temporary / 'white.json'),
                   '--export-3mf', str(native), str(assembled)]
        result = subprocess.run(command, cwd=str(temporary), capture_output=True,
                                text=True, errors='replace', timeout=120)
        if result.stdout.strip():
            write_run_log('BAMBU STDOUT:\n' + result.stdout.strip())
        if result.stderr.strip():
            write_run_log('BAMBU STDERR:\n' + result.stderr.strip())
        if result.returncode or not native.is_file():
            raise RuntimeError('Bambu project export failed (exit {}). See sidecar log.'.format(result.returncode))
        configure_h2d_project(native)
        with zipfile.ZipFile(native) as archive:
            if archive.testzip():
                raise RuntimeError('Bambu output archive failed its integrity check.')
            settings = json.loads(archive.read('Metadata/project_settings.config'))
            if settings.get('printer_model') != 'Bambu Lab H2D':
                raise RuntimeError('Exported project has the wrong printer profile.')
            if settings.get('filament_colour') != ['#000000', '#FFFFFF']:
                raise RuntimeError('Exported project does not have the requested two filament colors.')
            if settings.get('extruder_nozzle_stats') != ['Standard#1', 'Standard#1']:
                raise RuntimeError('Missing H2D standard nozzle inventory.')
            config = ET.fromstring(archive.read('Metadata/model_settings.config'))
            parts = config.findall('object/part')
            if len(parts) != 4:
                raise RuntimeError('Expected four assembled filament parts in exported project.')
            for part in parts:
                meta = {p.get('key'): p.get('value') for p in part.findall('metadata')}
                if meta.get('extruder') != ('2' if 'White' in meta.get('name', '') else '1'):
                    raise RuntimeError('Wrong filament assignment for ' + meta.get('name', 'unnamed part'))
        # Export success alone does not prove the file will import correctly.
        # Reopen it through Bambu Studio and require intact, watertight parts.
        check = subprocess.run([str(executable), '--datadir', str(temporary / 'settings'),
                                '--info', str(native)], cwd=str(temporary),
                               capture_output=True, text=True, errors='replace', timeout=120)
        report = check.stdout + '\n' + check.stderr
        write_run_log('BAMBU REIMPORT:\n' + report.strip())
        if check.returncode or 'manifold = yes' not in report:
            raise RuntimeError('Bambu Studio could not reload the exported trophy as a solid.')
        open_edges = re.findall(r'^open_edges\s*=\s*(\d+)', report, re.MULTILINE)
        if any(int(count) for count in open_edges):
            raise RuntimeError('Bambu Studio found open edges in the exported trophy.')
        part_counts = re.findall(r'^number_of_parts\s*=\s*(\d+)', report, re.MULTILINE)
        expected_shells = sum(len(bodies) for _, bodies, _ in groups)
        if part_counts != [str(expected_shells)]:
            raise RuntimeError('Bambu import changed the connected parts: expected {}, got {}.'
                               .format(expected_shells, part_counts))
        heights = re.findall(r'^size_z\s*=\s*([\d.]+)', report, re.MULTILINE)
        if len(heights) != 1 or abs(float(heights[0]) - TOTAL_HEIGHT_MM) > 0.1:
            raise RuntimeError('Bambu import changed the trophy height or assembly orientation.')
        # Verify model layers separately from printer startup templates. This
        # CLI version rejects official H2D T1001/T65535/T65279 template commands.
        # Never publish this diagnostic project or its G-code.
        diagnostic = temporary / 'layers-only.3mf'
        with zipfile.ZipFile(native) as source, zipfile.ZipFile(diagnostic, 'w', zipfile.ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == 'Metadata/project_settings.config':
                    config = json.loads(data)
                    for key in ('machine_start_gcode', 'machine_end_gcode', 'change_filament_gcode',
                                'layer_change_gcode', 'time_lapse_gcode', 'before_layer_change_gcode'):
                        config[key] = ''
                    data = json.dumps(config).encode('utf-8')
                target.writestr(item, data)
        sliced = subprocess.run([str(executable), '--datadir', str(temporary / 'settings'),
                                 '--arrange', '0', '--orient', '0', '--slice', '0',
                                 '--outputdir', str(temporary), str(diagnostic)],
                                cwd=str(temporary), capture_output=True, text=True,
                                errors='replace', timeout=120)
        write_run_log('BAMBU LAYER CHECK (printer templates excluded):\n' +
                      (sliced.stdout + '\n' + sliced.stderr).strip())
        if sliced.returncode or not (temporary / 'plate_1.gcode').is_file():
            raise RuntimeError('Bambu could not slice the trophy layers. See sidecar log.')
        # Replace the prior export only after the new project passes checks.
        pending = output.with_suffix('.3mf.tmp')
        try:
            shutil.copyfile(native, pending)
            pending.replace(output)
        finally:
            if pending.exists():
                pending.unlink()
    write_run_log('BAMBU EXPORT OK: ' + str(output))
    return output


def write_run_log(message, reset=False):
    """Persist Fusion results beside this script so they can be read externally."""
    try:
        log_path = Path(__file__).resolve().with_suffix('.log')
        with log_path.open('w' if reset else 'a', encoding='utf-8') as log:
            log.write(datetime.now(timezone.utc).isoformat() + ' ' + message + '\n')
    except OSError as error:
        print('Could not write trophy log: {}'.format(error))


def point(x, y, z):
    return adsk.core.Point3D.create(x / 10, y / 10, z / 10)


def filament_appearance(design, seed, name, rgb):
    """Create a visible filament color across current and older Fusion APIs."""
    color = adsk.core.Color.create(*rgb, 255)
    # Current Fusion can create a plain opaque appearance directly.
    if hasattr(design.appearances, 'add'):
        try:
            appearance = design.appearances.add(name)
            appearance.color = color
            return appearance
        except (AttributeError, RuntimeError):
            pass
    # Older versions can copy an existing appearance and change its color.
    appearance = design.appearances.addByCopy(seed, name + ' - compatible')
    for property_id in ('opaque_albedo', 'generic_diffuse', 'metal_f0'):
        prop = adsk.core.ColorProperty.cast(
            appearance.appearanceProperties.itemById(property_id))
        if prop:
            if prop.hasConnectedTexture:
                prop.hasConnectedTexture = False
            prop.value = color
            return appearance
    raise RuntimeError('Could not set filament appearance: ' + name)


def vector(x, y, z):
    return adsk.core.Vector3D.create(x, y, z)


def boolean(manager, target, tool, operation, label):
    if tool is None or not manager.booleanOperation(target, tool, operation):
        raise RuntimeError("Geometry operation failed: " + label)
    return target


def box(manager, center, sizes):
    bounds = adsk.core.OrientedBoundingBox3D.create(
        point(*center), vector(1, 0, 0), vector(0, 1, 0),
        sizes[0] / 10, sizes[1] / 10, sizes[2] / 10)
    return manager.createBox(bounds)


def clip_halfspace(manager, body, normal, center):
    """Keep dot(position - center, normal) >= 0, using a large box."""
    n = vector(*normal)
    n.normalize()
    helper = vector(0, 0, 1) if abs(n.z) < 0.9 else vector(0, 1, 0)
    u = n.crossProduct(helper)
    u.normalize()
    v = n.crossProduct(u)
    v.normalize()
    # u cross v = n; box extends from the cutting plane 200 mm outward.
    origin = point(center[0] + 100 * n.x,
                   center[1] + 100 * n.y,
                   center[2] + 100 * n.z)
    bounds = adsk.core.OrientedBoundingBox3D.create(origin, u, v, 20, 20, 20)
    return boolean(manager, body, manager.createBox(bounds),
                   adsk.fusion.BooleanTypes.IntersectionBooleanType,
                   "clip volleyball seam")


def volleyball(manager, center):
    """Six spherical panel groups, each split into three curved strips.

    Panel boundaries follow the projected edges of a cube. Alternating
    stripe directions produce a stylized 18-panel volleyball, not merely
    latitude/longitude rings. All seams are actual recessed geometry.
    """
    r = BALL_RADIUS_MM
    ball = manager.createSphere(point(*center), r / 10)
    cut = adsk.fusion.BooleanTypes.DifferenceBooleanType

    # Twelve boundary arcs. For each axis pair, keep only the portion
    # where those two signed coordinates dominate the remaining axis.
    for a, b in ((0, 1), (0, 2), (1, 2)):
        other = 3 - a - b
        for sa in (-1, 1):
            for sb in (-1, 1):
                normal = [0, 0, 0]
                normal[a], normal[b] = sa, -sb
                seam = manager.createTorus(point(*center), vector(*normal),
                                          r / 10, SEAM_RADIUS_MM / 10)
                positive = [0, 0, 0]
                positive[a] = sa
                clip_halfspace(manager, seam, positive, center)
                for sign in (-1, 1):
                    limit = positive[:]
                    limit[other] = sign
                    clip_halfspace(manager, seam, limit, center)
                boolean(manager, ball, seam, cut, "panel boundary")
                adsk.doEvents()

    # Two small-circle arcs within each of the six dominant-axis cells.
    for axis in range(3):
        stripe_axis = (axis + 1) % 3
        remaining = [i for i in range(3) if i != axis]
        for side in (-1, 1):
            for offset in (-7.0, 7.0):
                ring_center = list(center)
                ring_center[stripe_axis] += offset
                normal = [0, 0, 0]
                normal[stripe_axis] = 1
                seam = manager.createTorus(
                    point(*ring_center), vector(*normal),
                    math.sqrt(r * r - offset * offset) / 10,
                    SEAM_RADIUS_MM / 10)
                for other in remaining:
                    for sign in (-1, 1):
                        limit = [0, 0, 0]
                        limit[axis], limit[other] = side, sign
                        clip_halfspace(manager, seam, limit, center)
                boolean(manager, ball, seam, cut, "panel stripe")
                adsk.doEvents()

    # Tilt the panels for a more natural presentation.
    rotation = adsk.core.Matrix3D.create()
    rotation.setToRotation(math.radians(27), vector(1, 2, 0.3), point(*center))
    if not manager.transform(ball, rotation):
        raise RuntimeError("Could not orient volleyball.")
    return ball


def inlay_line(root, target, label, text, z_low, z_high, height):
    write_run_log("INLAY: {}: {!r}".format(label, text))
    # Build readable text in the ordinary XY plane. Move its solid cutting
    # tools afterward; no face-sketch transform or inferred axes are needed.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = label
    texts = sketch.sketchTexts
    # Current Fusion uses a quoted text expression and a ValueInput.
    # Older Fusion versions expose createInput2 instead.
    if hasattr(texts, "createInput3"):
        expression = "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"
        text_input = texts.createInput3(
            expression, adsk.core.ValueInput.createByReal(height / 10))
    else:
        text_input = texts.createInput2(text, height / 10)
    text_input.fontName = FONT_NAME
    text_input.isHorizontalFlip = False
    text_input.isVerticalFlip = False
    low = point(-37, z_low, 0)
    high = point(37, z_high, 0)
    text_input.setAsMultiLine(
        low, high,
        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
        adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    entity = texts.add(text_input)
    if not entity:
        raise RuntimeError("Could not create " + label)
    extrudes = root.features.extrudeFeatures
    extrusion = extrudes.createInput(
        entity, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extent = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(ENGRAVE_DEPTH_MM / 10))
    extrusion.setOneSideExtent(
        extent, adsk.fusion.ExtentDirections.NegativeExtentDirection)
    feature = extrudes.add(extrusion)
    cutters = adsk.core.ObjectCollection.create()
    for index, body in enumerate(feature.bodies, 1):
        body.name = "Writing - White - {} - {:02d}".format(label, index)
        cutters.add(body)
    if cutters.count == 0:
        raise RuntimeError("No letter cutting bodies were generated for " + label)

    # XY text -> vertical front: X stays right, Y becomes up (+Z), and
    # negative extrusion Z goes into the base (+Y). Translation is in cm.
    placement = adsk.core.Matrix3D.create()
    placement.setToRotation(math.pi / 2, vector(1, 0, 0), point(0, 0, 0))
    placement.translation = vector(0, -2.9, 0)
    moves = root.features.moveFeatures
    move_input = moves.createInput2(cutters)
    if not move_input.defineAsFreeMove(placement):
        raise RuntimeError("Could not position letter cutting bodies.")
    moves.add(move_input)

    # Check actual solids before cutting, including the text's line bounds.
    for cutter in cutters:
        bounds = cutter.boundingBox
        if (abs(bounds.minPoint.y + 2.9) > 1e-5
                or abs(bounds.maxPoint.y - (-2.9 + ENGRAVE_DEPTH_MM / 10)) > 1e-5
                or bounds.minPoint.x < -3.8 or bounds.maxPoint.x > 3.8
                or bounds.minPoint.z < z_low / 10 - 0.1
                or bounds.maxPoint.z > z_high / 10 + 0.1):
            raise RuntimeError("Letter cutting body lies outside its front-face panel: " + label)
    combines = root.features.combineFeatures
    cut_input = combines.createInput(target, cutters)
    cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    cut_input.isKeepToolBodies = True
    body_count_before = root.bRepBodies.count
    volume_before = target.volume
    inlay_volume = sum(body.volume for body in cutters)
    cut = combines.add(cut_input)
    # Autodesk documents a None return for a non-parametric combine, even
    # when it succeeds. Validate the solid rather than the feature handle.
    if cut is not None:
        cut.name = label + " engraving"
    if root.bRepBodies.count != body_count_before:
        raise RuntimeError("Text inlay bodies were not retained: " + label)
    if not target.isSolid or volume_before - target.volume <= 1e-8:
        raise RuntimeError("Engraving did not remove material from the trophy: " + label)
    removed_volume = volume_before - target.volume
    if abs(removed_volume - inlay_volume) > max(1e-6, inlay_volume * 1e-5):
        raise RuntimeError("Text inlay does not exactly fill its base pocket: " + label)
    write_run_log("INLAY OK: {}; bodies={}; volume={:.3f} mm^3".format(
        label, cutters.count, inlay_volume * 1000))
    sketch.isVisible = False
    return list(cutters)


def join_writing(root, manager, base, glyphs):
    """Connect every letter through a white backing hidden inside the base."""
    front = -29 + ENGRAVE_DEPTH_MM - 0.05  # Small overlap gives a robust solid join.
    thickness = 0.6
    backing_shape = box(manager, (0, front + thickness / 2, 16.5), (74, thickness, 24))
    backing = root.bRepBodies.add(backing_shape)
    backing.name = 'Writing - White'
    glyph_volume = sum(glyph.volume for glyph in glyphs)
    tools = adsk.core.ObjectCollection.create()
    for glyph in glyphs:
        tools.add(glyph)
    combines = root.features.combineFeatures
    joining = combines.createInput(backing, tools)
    joining.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    joining.isKeepToolBodies = False
    combines.add(joining)
    if not backing.isSolid or backing.lumps.count != 1 or root.bRepBodies.count != 4:
        raise RuntimeError('Could not connect all lettering into one Writing body.')
    # The glyph pockets already exist; only the hidden backing plate is new
    # material to remove from the black base. Keep the joined white solid.
    tools = adsk.core.ObjectCollection.create()
    tools.add(backing)
    pocket = combines.createInput(base, tools)
    pocket.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    pocket.isKeepToolBodies = True
    before = base.volume
    existing = list(root.bRepBodies)
    combines.add(pocket)
    # The backing can otherwise isolate the black centers of enclosed letters.
    # Extend those centers through holes in the white backing and reconnect
    # them to the main black base, preserving the visible glyph outlines.
    counters = [body for body in root.bRepBodies
                if not any(body == known for known in existing)]
    black_pieces = [base] + counters
    base = max(black_pieces, key=lambda body: body.volume)
    counters = [body for body in black_pieces if body != base]
    if counters:
        bridges = adsk.core.ObjectCollection.create()
        shift = adsk.core.Matrix3D.create()
        shift.translation = vector(0, (thickness + 0.05) / 10, 0)
        for counter in counters:
            bridge_shape = manager.copy(counter)
            if not manager.transform(bridge_shape, shift):
                raise RuntimeError('Could not connect a black letter center.')
            bridges.add(root.bRepBodies.add(bridge_shape))
        holes = combines.createInput(backing, bridges)
        holes.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        holes.isKeepToolBodies = True
        combines.add(holes)
        for counter in counters:
            bridges.add(counter)
        reconnect = combines.createInput(base, bridges)
        reconnect.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        reconnect.isKeepToolBodies = False
        combines.add(reconnect)
    new_material_volume = backing.volume - glyph_volume
    if abs((before - base.volume) - new_material_volume) > max(1e-6, new_material_volume * 1e-5):
        raise RuntimeError('Hidden writing backing does not match its base pocket.')
    if root.bRepBodies.count != 4 or backing.lumps.count != 1 or base.lumps.count != 1:
        raise RuntimeError('Writing or base contains disconnected material after backing construction.')
    base.name = 'Base - Black'
    backing.name = 'Writing - White'
    write_run_log('WRITING JOIN OK: {} glyph bodies connected with a hidden 0.6 mm plate.'
                  .format(len(glyphs)))
    return base, backing


def run(context):
    ui = None
    automated = isinstance(context, dict) and context.get("automated", False)
    stage = "initialization"
    write_run_log('START: ' + str(Path(__file__).resolve()), reset=True)
    write_run_log("CONFIG: player={!r}; height={} mm; inlay depth={} mm; separate bodies"
                  .format(PLAYER_NAME, TOTAL_HEIGHT_MM, ENGRAVE_DEPTH_MM))
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        name = PLAYER_NAME.strip()
        if not name or len(name) > 24 or any(c in name for c in "\r\n"):
            raise ValueError("PLAYER_NAME must contain 1–24 characters on one line.")
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        # Direct modeling allows reliable insertion of temporary BRep solids.
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        assembly = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        root = assembly.component
        root.name = "Trophy"
        # All four material bodies belong to one exportable component.
        manager = adsk.fusion.TemporaryBRepManager.get()
        union = adsk.fusion.BooleanTypes.UnionBooleanType

        stage = "separate base and stand"
        write_run_log("STAGE: " + stage)
        base_shape = box(manager, (0, 0, 2), (88, 64, 4))
        boolean(manager, base_shape, box(manager, (0, 0, 16.5), (82, 58, 27)),
                union, "name plinth")
        # Stand begins exactly on the base's top face; no shared volume.
        stand_shape = manager.createCylinderOrCone(point(0, 0, 30), 1.588679245283,
                                                  point(0, 0, 82), 1.0)
        collar = manager.createCylinderOrCone(point(0, 0, 76), 1.0,
                                             point(0, 0, 86), 1.6)
        boolean(manager, stand_shape, collar, union, "ball cradle")

        stage = "volleyball seams (may take a minute)"
        write_run_log("STAGE: " + stage)
        center = (0, 0, TOTAL_HEIGHT_MM - BALL_RADIUS_MM)
        ball_shape = volleyball(manager, center)
        # Keep the complete volleyball. Its matching seat is removed from
        # the stand, so two filaments never compete for the same volume.
        boolean(manager, stand_shape, ball_shape,
                adsk.fusion.BooleanTypes.DifferenceBooleanType, "ball seat in stand")
        base = root.bRepBodies.add(base_shape)
        base.name = "Base - Black"
        stand = root.bRepBodies.add(stand_shape)
        stand.name = "Stand - Black"
        ball = root.bRepBodies.add(ball_shape)
        ball.name = "Volleyball - White"

        stage = "separate contrasting lettering inlays"
        write_run_log("STAGE: " + stage)
        name_height = min(5.0, 74.0 / (max(len(name), 1) * 0.95))
        lettering = []
        lettering.extend(inlay_line(root, base, "Player name", name, 20, 28, name_height))
        lettering.extend(inlay_line(root, base, "Organization line 1",
                                    "Valley Catholic 2026", 12.5, 19.5, 3.8))
        lettering.extend(inlay_line(root, base, "Organization line 2",
                                    "Catholic Youth Organization", 5, 12, 3.5))
        stage = "joining all writing into one solid"
        write_run_log("STAGE: " + stage)
        base, writing = join_writing(root, manager, base, lettering)
        lettering = [writing]
        base.name = "Base - Black"

        if CAD_Y_UP:
            stage = "orienting trophy Y-up, front toward +Z"
            write_run_log("STAGE: " + stage)
            # Rotate the completed solid, including all engraved surfaces.
            # (x, y, z) -> (x, z, -y): original +Z becomes +Y, front -Y becomes +Z.
            upright = adsk.core.Matrix3D.create()
            upright.setToRotation(-math.pi / 2, vector(1, 0, 0), point(0, 0, 0))
            entities = adsk.core.ObjectCollection.create()
            for body in root.bRepBodies:
                entities.add(body)
            moves = root.features.moveFeatures
            move_input = moves.createInput2(entities)
            if not move_input.defineAsFreeMove(upright):
                raise RuntimeError("Could not define the Y-up orientation.")
            moves.add(move_input)

        stage = "final multipart validation"
        write_run_log("STAGE: " + stage)
        expected_count = 3 + len(lettering)
        if root.bRepBodies.count != expected_count:
            raise RuntimeError("Expected {} separate bodies, found {}.".format(
                expected_count, root.bRepBodies.count))
        for body in root.bRepBodies:
            if not body.isSolid or body.lumps.count != 1 or body.volume <= 0:
                raise RuntimeError("Invalid printable body: " + body.name)
        axis = "y" if CAD_Y_UP else "z"
        minimum = min(getattr(body.boundingBox.minPoint, axis) for body in root.bRepBodies)
        maximum = max(getattr(body.boundingBox.maxPoint, axis) for body in root.bRepBodies)
        height = (maximum - minimum) * 10
        if abs(minimum * 10) > 0.01:
            raise RuntimeError("The base underside must be on the build plane.")
        if abs(height - TOTAL_HEIGHT_MM) > 0.1:
            raise RuntimeError("Unexpected overall height: {:.3f} mm".format(height))

        stage = "black and white filament appearances"
        write_run_log("STAGE: " + stage)
        white = filament_appearance(design, base.appearance, 'Filament - White', (255, 255, 255))
        black = filament_appearance(design, base.appearance, 'Filament - Black', (0, 0, 0))
        base.appearance = black
        stand.appearance = black
        ball.appearance = white
        for body in lettering:
            body.appearance = white
        write_run_log('COLORS: filament 1 = black (base, stand); '
                      'filament 2 = white (volleyball, all writing).')

        # Look toward the engraved +Z face, with +Y up.
        camera = app.activeViewport.camera
        camera.target = point(0, 63.5, 0) if CAD_Y_UP else point(0, 0, 63.5)
        camera.eye = point(150, 145, 260) if CAD_Y_UP else point(150, -260, 145)
        camera.upVector = vector(0, 1, 0) if CAD_Y_UP else vector(0, 0, 1)
        camera.isFitView = True
        app.activeViewport.camera = camera
        output = None
        if EXPORT_BAMBU_PROJECT:
            stage = "native Bambu project export"
            write_run_log("STAGE: " + stage)
            groups = [('Base - Black', [base], 1), ('Stand - Black', [stand], 1),
                      ('Volleyball - White', [ball], 2), ('Writing - White', lettering, 2)]
            output = export_bambu_project(groups, name)
        write_run_log(
            'SUCCESS: multipart trophy; height={:.3f} mm; export component Trophy. '
            'Bodies: {} structural + {} writing. Export: {}. Print not verified.'
            .format(height, 3, len(lettering), output or 'manual export selected'))
        if not automated:
            export_message = (
                "Bambu project saved beside this script:\n{}\n"
                "Open it directly in Bambu Studio. It has four assembled parts.\n"
                "Profiles: H2D 0.4 mm nozzles, Generic PLA, 0.16 mm layers, tree supports.\n"
                "Verify these match your actual nozzles and filament, then slice.\n"
                .format(output.name) if output else
                "Right-click Trophy > Save As Mesh.\n"
                "Format: 3MF; units: millimeters; structure: One File.\n"
                "Save as trophy.3mf. Import all four bodies as one multipart object.\n")
            ui.messageBox(
                "Created a {:.1f} mm (5 inch) trophy for {}.\n\n".format(height, name) +
                "Separate volleyball, base, stand, and writing; 88 x 64 mm footprint.\n" +
                ("Orientation: +Y up, engraving facing +Z.\n" if CAD_Y_UP else
                 "Orientation: +Z up, engraving facing -Y; ready for manual mesh export.\n") +
                "Colors: BLACK base/stand; WHITE volleyball/writing.\n"
                "Save the Fusion design.\n" + export_message +
                "Assign black parts to your black reel and white parts to your white reel.\n"
                "Run results are saved in Trophy.log beside the script.\n\n"
                "Change PLAYER_NAME at the top of the script and rerun for another player.",
                "Valley Catholic volleyball trophy")
    except Exception:
        message = "Trophy creation stopped during {}.\n\n{}".format(stage, traceback.format_exc())
        write_run_log('ERROR: ' + message)
        if automated:
            raise
        if ui:
            ui.messageBox(message, "Trophy script error")
        else:
            print(message)
