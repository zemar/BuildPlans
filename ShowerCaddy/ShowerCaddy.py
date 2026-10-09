"""Fusion script: reinforced three-component shower caddy assembly. Inputs are mm.

Run from Fusion's Scripts and Add-Ins dialog. Creates a NEW unsaved design.
X = width, +Y = basket/front, +Z = up; glass occupies negative Y.
Width/depth/side height are external basket dimensions, including the floor.
305 mm is measured from the bottom to the UNDERSIDE of the hook bridge.
25.5 mm is the clear hook throat; hook stock adds to the outside envelope.
Edit constants and rerun to regenerate. See PRINTING.md for separate-part orientation, hardware, and slicer settings.
Artwork preparation is consolidated into this file as embedded CAD contours.
Run only in Fusion; no external artwork files or Python packages are needed.
"""

import math
import base64
import hashlib
import zlib
import json
import logging
from pathlib import Path
import time
import traceback

import adsk.core
import adsk.fusion


BASKET_WIDTH = 259.0
BASKET_DEPTH = 88.9
SIDE_HEIGHT = 101.6
HOOK_RISE = 305.0
RISE_FROM_RIM = False
HOOK_CLEARANCE = 25.5

# Assumed construction dimensions, all in mm.
WALL_THICKNESS = 3.0
FLOOR_THICKNESS = 3.0
HOOK_WIDTH = 25.0
HOOK_THICKNESS = 10.0
HOOK_RETURN_DROP = 30.0
MESH_OPENING = 8.0
MESH_WEB = 3.0
MESH_BORDER = 6.0
EDGE_RADIUS = 0.75                 # Horizontal rims, including drainage holes
CORNER_RADIUS = 1.0                # Vertical corners; larger than rim radius
# Independent arm frame, bolted through the basket rear mounting pads.
ASSEMBLY_GAP = 0.0                 # Bolted mating faces contact at Y=0
ARM_BOTTOM = 15.0
CROSSBAR_HEIGHT = 25.0
ROOT_WEB_WIDTH = 20.0
ROOT_TAPER_HEIGHT = 40.0
HOOK_BEND_RADIUS = 4.0
MOUNT_PAD_THICKNESS = 8.0
MOUNT_HEIGHTS = (40.0, 80.0)
BOLT_CLEARANCE = 4.5
BOLT_BLIND_DEPTH = 8.5
NUT_ACROSS_FLATS = 7.3
NUT_POCKET_DEPTH = 3.6
# Separate inset artwork plate, glued into its mating basket recess.
PANEL_THICKNESS = 1.8
PANEL_BORDER = 4.0
PANEL_RADIUS = 3.0
PANEL_CLEARANCE = 0.2
PANEL_ADHESIVE_GAP = 0.15
INLAY_HEIGHT = 80.0
INLAY_DEPTH = 0.6
INLAY_DATA_SHA256 = 'fd130bd0e164642c1410dd2d63c9099271a8a1707c9565104c8939dd9364c71e'
INLAY_COLORS = {
    'White': (250, 250, 250),
    'Green': (112, 166, 40),
    'Red': (210, 25, 35),
    'Brown': (184, 124, 53),
}
LOG_PATH = Path(__file__).resolve().with_suffix('.log')
LOGGER = logging.getLogger('ShowerCaddy')


def start_log():
    """Append runs and flush each record so partial builds remain inspectable."""
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    handler = logging.FileHandler(LOG_PATH, mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(asctime)sZ %(levelname)s %(message)s')
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.info('=== RUN START reinforced-assembly-v2-tangent-fillets (timestamps UTC) ===')
    LOGGER.info('Script: %s', Path(__file__).resolve())
    LOGGER.info('Inputs (dimensions mm): %s', {
        name: value for name, value in globals().items()
        if name.isupper() and isinstance(value, (int, float, bool))})


def close_log():
    for handler in list(LOGGER.handlers):
        handler.flush()
        handler.close()
        LOGGER.removeHandler(handler)


def point(x, y, z=0.0):
    """Fusion geometry uses centimeters internally."""
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0)


def distance(mm):
    return adsk.core.ValueInput.createByString('{} mm'.format(mm))


def rectangle(sketch, x0, y0, x1, y1):
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        point(x0, y0), point(x1, y1))


def xy_sketch(component, z, name):
    plane = component.xYConstructionPlane
    if z != 0:
        plane_input = component.constructionPlanes.createInput()
        plane_input.setByOffset(plane, distance(z))
        plane = component.constructionPlanes.add(plane_input)
        plane.name = name + ' plane'
        plane.isLightBulbOn = False
    sketch = component.sketches.add(plane)
    sketch.name = name + ' sketch'
    return sketch


def box(component, name, x0, y0, z0, x1, y1, z1, first=False):
    LOGGER.info('START %s: bounds mm (%s, %s, %s) -> (%s, %s, %s)',
                name, x0, y0, z0, x1, y1, z1)
    sketch = xy_sketch(component, z0, name)
    rectangle(sketch, x0, y0, x1, y1)
    operation = (adsk.fusion.FeatureOperations.NewBodyFeatureOperation if first
                 else adsk.fusion.FeatureOperations.JoinFeatureOperation)
    feature = component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), distance(z1 - z0), operation)
    feature.name = name
    sketch.isVisible = False
    LOGGER.info('DONE %s; health=%s; message=%s',
                name, feature.healthState, feature.errorOrWarningMessage)
    return feature


def mesh_layout():
    """Center full square openings, retaining at least MESH_BORDER at edges."""
    pitch = MESH_OPENING + MESH_WEB
    nx = math.floor((BASKET_WIDTH - 2 * MESH_BORDER + MESH_WEB) / pitch)
    ny = math.floor((BASKET_DEPTH - 2 * MESH_BORDER + MESH_WEB) / pitch)
    if nx < 1 or ny < 1:
        raise ValueError('Mesh openings do not fit within the basket.')
    x0 = (BASKET_WIDTH - (nx * pitch - MESH_WEB)) / 2
    y0 = (BASKET_DEPTH - (ny * pitch - MESH_WEB)) / 2
    return nx, ny, x0, y0, pitch


def validate():
    dimensions = [BASKET_WIDTH, BASKET_DEPTH, SIDE_HEIGHT, HOOK_RISE,
                  HOOK_CLEARANCE, WALL_THICKNESS, FLOOR_THICKNESS,
                  HOOK_WIDTH, HOOK_THICKNESS, HOOK_RETURN_DROP,
                  MESH_OPENING, MESH_WEB, MESH_BORDER, EDGE_RADIUS, CORNER_RADIUS,
                  ROOT_WEB_WIDTH, ROOT_TAPER_HEIGHT, PANEL_THICKNESS]
    if not all(math.isfinite(v) and v > 0 for v in dimensions):
        raise ValueError('All dimensions must be finite positive millimeters.')
    if not (2 * WALL_THICKNESS < min(BASKET_WIDTH, BASKET_DEPTH)
            and FLOOR_THICKNESS < SIDE_HEIGHT
            and WALL_THICKNESS <= HOOK_WIDTH < BASKET_WIDTH / 2
            and WALL_THICKNESS <= HOOK_THICKNESS < BASKET_DEPTH
            and MESH_BORDER >= WALL_THICKNESS):
        raise ValueError('Wall, hook, floor or mesh dimensions are incompatible.')
    bridge_z = HOOK_RISE + (SIDE_HEIGHT if RISE_FROM_RIM else 0)
    if bridge_z - HOOK_RETURN_DROP <= SIDE_HEIGHT:
        raise ValueError('Hook return must end above the basket rim.')
    if 2 * EDGE_RADIUS >= min(WALL_THICKNESS, FLOOR_THICKNESS, MESH_WEB,
                              HOOK_THICKNESS, HOOK_WIDTH, MESH_OPENING):
        raise ValueError('EDGE_RADIUS must be less than half the smallest wall, '
                         'floor, mesh web, hook section or mesh opening.')
    if not EDGE_RADIUS < CORNER_RADIUS < min(
            WALL_THICKNESS, MESH_WEB, HOOK_THICKNESS, HOOK_WIDTH, MESH_OPENING) / 2:
        raise ValueError('CORNER_RADIUS must exceed EDGE_RADIUS and remain below '
                         'half the narrowest wall, mesh web, hook or opening.')
    if not (math.isfinite(ASSEMBLY_GAP) and ASSEMBLY_GAP >= 0
            and 0 < ROOT_WEB_WIDTH < ROOT_TAPER_HEIGHT
            and 2*(HOOK_WIDTH+ROOT_WEB_WIDTH) < BASKET_WIDTH
            and SIDE_HEIGHT+ROOT_TAPER_HEIGHT < bridge_z-HOOK_RETURN_DROP
            and MOUNT_PAD_THICKNESS > WALL_THICKNESS
            and 0 < NUT_POCKET_DEPTH < BOLT_BLIND_DEPTH < HOOK_THICKNESS-1
            and 2*HOOK_BEND_RADIUS < HOOK_CLEARANCE):
        raise ValueError('Invalid reinforcement, mount, or hook-bend dimensions.')
    for z in MOUNT_HEIGHTS:
        if not ARM_BOTTOM+NUT_ACROSS_FLATS < z < SIDE_HEIGHT-10-NUT_ACROSS_FLATS:
            raise ValueError('Mounting holes must lie within the reinforced pads.')
    if PANEL_THICKNESS+PANEL_ADHESIVE_GAP > WALL_THICKNESS-1.0:
        raise ValueError('Panel recess must leave at least 1 mm of basket wall.')
    mesh_layout()
    return bridge_z


def build_basket(component, bridge_z):
    w, d, h, t = BASKET_WIDTH, BASKET_DEPTH, SIDE_HEIGHT, WALL_THICKNESS
    box(component, 'Floor blank', 0, 0, 0, w, d, FLOOR_THICKNESS, first=True)
    # Walls overlap the floor and each other for reliable solid joins.
    box(component, 'Back wall', 0, 0, 0, w, t, h)
    box(component, 'Front wall', 0, d - t, 0, w, d, h)
    box(component, 'Left wall', 0, 0, 0, t, d, h)
    box(component, 'Right wall', w - t, 0, 0, w, d, h)

    for side, x in [('Left', 0), ('Right', w-HOOK_WIDTH-ROOT_WEB_WIDTH)]:
        box(component, side+' reinforced mounting pad', x,0,ARM_BOTTOM,
            x+HOOK_WIDTH+ROOT_WEB_WIDTH,MOUNT_PAD_THICKNESS,h-10)

    sketch = xy_sketch(component, 0, 'Drainage mesh')
    nx, ny, x0, y0, pitch = mesh_layout()
    LOGGER.info('START drainage mesh: %s x %s openings; pitch=%s mm', nx, ny, pitch)
    sketch.isComputeDeferred = True
    try:
        for ix in range(nx):
            for iy in range(ny):
                x, y = x0 + ix * pitch, y0 + iy * pitch
                rectangle(sketch, x, y, x + MESH_OPENING, y + MESH_OPENING)
    finally:
        sketch.isComputeDeferred = False
    profiles = adsk.core.ObjectCollection.create()
    for profile in sketch.profiles:
        profiles.add(profile)
    if profiles.count != nx * ny:
        raise RuntimeError('Unexpected drainage sketch profile count.')
    LOGGER.info('Cutting %s drainage profiles', profiles.count)
    cut = component.features.extrudeFeatures.addSimple(
        profiles, distance(FLOOR_THICKNESS),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut.name = 'Drainage mesh - {} square openings'.format(nx * ny)
    sketch.isVisible = False
    if component.bRepBodies.count != 1 or not component.bRepBodies.item(0).isSolid:
        raise RuntimeError('Expected one connected basket solid.')
    component.bRepBodies.item(0).name = 'Basket - Black PLA'
    LOGGER.info('DONE basket: bodies=%s; edges=%s',
                component.bRepBodies.count, component.bRepBodies.item(0).edges.count)


def edge_orientation(edge):
    """Classify in component coordinates, using Fusion's internal cm units.

    Bounding boxes also identify horizontal arcs created by the first fillet;
    testing only straight lines would leave the curved hole corners sharp.
    """
    bounds = edge.boundingBox
    dx = bounds.maxPoint.x - bounds.minPoint.x
    dy = bounds.maxPoint.y - bounds.minPoint.y
    dz = bounds.maxPoint.z - bounds.minPoint.z
    tolerance = 1e-6  # cm
    if dz <= tolerance:
        return 'horizontal'
    if dx <= tolerance and dy <= tolerance:
        return 'vertical'
    return 'other'


def fillet_edges(component, edges, radius, label, tangent_chain=False):
    if edges.count == 0:
        raise RuntimeError('No edges selected for ' + label)
    LOGGER.info('START %s: edges=%s; radius=%s mm; tangent_chain=%s',
                label, edges.count, radius, tangent_chain)
    started = time.perf_counter()
    fillets = component.features.filletFeatures
    fillet_input = fillets.createInput()
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(edges, distance(radius), tangent_chain)
    try:
        feature = fillets.add(fillet_input)
    except Exception as exc:
        raise RuntimeError('{} failed at R{} mm with {} edges: {}'.format(
            label, radius, edges.count, exc)) from exc
    if not feature:
        raise RuntimeError('Fusion did not create ' + label)
    feature.name = '{} - R{} mm'.format(label, radius)
    LOGGER.info('%s health=%s; message=%s', label, feature.healthState,
                feature.errorOrWarningMessage)
    if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError(label + ': ' + feature.errorOrWarningMessage)
    if component.bRepBodies.count != 1 or not component.bRepBodies.item(0).isSolid:
        raise RuntimeError('Rounded shelf must remain a single solid.')
    LOGGER.info('DONE %s; elapsed=%.2f seconds', label, time.perf_counter() - started)


def round_all_edges(component):
    """Round vertical corners before the horizontal perimeter edges.

    Avoid asking ASM to solve every three-edge corner in one operation. A
    larger corner radius leaves a nonzero arc when the rim fillet offsets it.
    Reacquire edges after the first feature because it replaces the topology.
    """
    vertical = adsk.core.ObjectCollection.create()
    counts = {'vertical': 0, 'horizontal': 0, 'other': 0}
    for edge in component.bRepBodies.item(0).edges:
        direction = edge_orientation(edge)
        counts[direction] += 1
        if direction == 'vertical':
            vertical.add(edge)
    LOGGER.info('Initial fillet edge classification: %s', counts)
    if counts['other']:
        raise RuntimeError('Unexpected non-orthogonal edges before rounding.')
    fillet_edges(component, vertical, CORNER_RADIUS, 'Vertical corner fillet')

    horizontal = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        if edge_orientation(edge) == 'horizontal':
            horizontal.add(edge)
    fillet_edges(component, horizontal, EDGE_RADIUS, 'Horizontal rim fillet')
    LOGGER.info('DONE all-edge rounding in two stages')



def apply_black_pla(design, component):
    """Black display finish; PLA is a fabrication note, not a simulated material."""
    LOGGER.info('START black PLA appearance')
    body = component.bRepBodies.item(0)
    component.attributes.add('ShowerCaddy', 'FabricationMaterial', 'Black PLA')
    finish = design.appearances.itemByName('Black PLA - visual finish')
    if not finish:
        finish = design.appearances.addByCopy(body.appearance, 'Black PLA - visual finish')
    color_property = adsk.core.ColorProperty.cast(
        finish.appearanceProperties.itemById('generic_diffuse'))
    if not color_property:
        for prop in finish.appearanceProperties:
            candidate = adsk.core.ColorProperty.cast(prop)
            if candidate:
                color_property = candidate
                break
    if not color_property:
        raise RuntimeError('Unable to set the black appearance color.')
    color_property.value = adsk.core.Color.create(20, 20, 20, 255)
    body.appearance = finish
    LOGGER.info('DONE black PLA appearance')


def xz_sketch(component, y, name):
    LOGGER.info('START XZ sketch: %s; Y=%s mm', name, y)
    base = component.xZConstructionPlane
    setup = component.constructionPlanes.createInput()
    setup.setByOffset(base, distance(y / base.geometry.normal.y))
    plane = component.constructionPlanes.add(setup)
    plane.name = name + ' plane'
    plane.isLightBulbOn = False
    sketch = component.sketches.add(plane)
    sketch.name = name + ' sketch'
    return sketch


def xz_point(sketch, x, y, z):
    return sketch.modelToSketchSpace(point(x, y, z))


def extrude_y(component, sketch, delta_y, operation, name):
    LOGGER.info('START Y extrusion: %s; delta=%s mm', name, delta_y)
    origin = sketch.sketchToModelSpace(point(0, 0, 0))
    normal = sketch.sketchToModelSpace(point(0, 0, 10)).y - origin.y
    if abs(abs(normal) - 1) > 1e-8 or sketch.profiles.count != 1:
        raise RuntimeError('Expected one XZ profile for ' + name)
    feature = component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), distance(delta_y / normal), operation)
    feature.name = name
    sketch.isVisible = False
    if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError(name + ': ' + feature.errorOrWarningMessage)
    LOGGER.info('DONE Y extrusion: %s; component bodies=%s', name, component.bRepBodies.count)
    return feature


def rounded_panel(component, name, width, height, y, depth, radius, operation):
    sketch = xz_sketch(component, y, name)
    x0, x1 = (BASKET_WIDTH - width) / 2, (BASKET_WIDTH + width) / 2
    z0, z1 = (SIDE_HEIGHT - height) / 2, (SIDE_HEIGHT + height) / 2
    r, q = radius, radius / math.sqrt(2)
    def p(x, z):
        return xz_point(sketch, x, y, z)
    lines, arcs = sketch.sketchCurves.sketchLines, sketch.sketchCurves.sketchArcs
    lines.addByTwoPoints(p(x0+r,z0), p(x1-r,z0))
    arcs.addByThreePoints(p(x1-r,z0), p(x1-r+q,z0+r-q), p(x1,z0+r))
    lines.addByTwoPoints(p(x1,z0+r), p(x1,z1-r))
    arcs.addByThreePoints(p(x1,z1-r), p(x1-r+q,z1-r+q), p(x1-r,z1))
    lines.addByTwoPoints(p(x1-r,z1), p(x0+r,z1))
    arcs.addByThreePoints(p(x0+r,z1), p(x0+r-q,z1-r+q), p(x0,z1-r))
    lines.addByTwoPoints(p(x0,z1-r), p(x0,z0+r))
    arcs.addByThreePoints(p(x0,z0+r), p(x0+r-q,z0+r-q), p(x0+r,z0))
    return extrude_y(component, sketch, depth, operation, name)


def mount_positions():
    return [(x, z) for x in (HOOK_WIDTH/2, BASKET_WIDTH-HOOK_WIDTH/2)
            for z in MOUNT_HEIGHTS]


def drill_y(component, name, x, z, y, depth, diameter, hexagon=False):
    sketch = xz_sketch(component, y, name)
    if hexagon:
        # diameter is across flats; a regular hex circumradius is AF/sqrt(3).
        r = diameter / math.sqrt(3)
        pts = [xz_point(sketch, x+r*math.cos(i*math.pi/3), y,
                        z+r*math.sin(i*math.pi/3)) for i in range(6)]
        for a, b in zip(pts, pts[1:]+pts[:1]):
            sketch.sketchCurves.sketchLines.addByTwoPoints(a, b)
    else:
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            xz_point(sketch, x, y, z), diameter/20)
    return extrude_y(component, sketch, depth,
                     adsk.fusion.FeatureOperations.CutFeatureOperation, name)


def prepare_basket_mounts_and_panel(component):
    for index, (x, z) in enumerate(mount_positions(), 1):
        drill_y(component, 'M4 basket clearance {}'.format(index), x, z,
                MOUNT_PAD_THICKNESS, -MOUNT_PAD_THICKNESS, BOLT_CLEARANCE)
    _, _, art_width = load_inlay()
    rounded_panel(component, 'Engraving insert recess',
                  art_width + 2*PANEL_BORDER + 2*PANEL_CLEARANCE,
                  INLAY_HEIGHT + 2*PANEL_BORDER + 2*PANEL_CLEARANCE,
                  BASKET_DEPTH, -(PANEL_THICKNESS+PANEL_ADHESIVE_GAP),
                  PANEL_RADIUS+PANEL_CLEARANCE,
                  adsk.fusion.FeatureOperations.CutFeatureOperation)
    component.bRepBodies.item(0).name = 'Basket - Black PLA'


def taper_geometry():
    """Two tangent circular arcs give a smooth 20 mm-wide, 40 mm-high taper."""
    w, h = ROOT_WEB_WIDTH, ROOT_TAPER_HEIGHT
    radius = (w*w+h*h)/(4*w)
    theta = 2*math.atan(w/h)
    return radius, theta


def make_arm_profile(component, right, bridge_z):
    y = -ASSEMBLY_GAP
    sketch = xz_sketch(component, y, ('Right' if right else 'Left') + ' reinforced arm')
    def p(x, z):
        return xz_point(sketch, BASKET_WIDTH-x if right else x, y, z)
    a, h = HOOK_WIDTH+ROOT_WEB_WIDTH, SIDE_HEIGHT
    r, theta = taper_geometry()
    mid = (HOOK_WIDTH+ROOT_WEB_WIDTH/2, h+ROOT_TAPER_HEIGHT/2)
    lines, arcs = sketch.sketchCurves.sketchLines, sketch.sketchCurves.sketchArcs
    lines.addByTwoPoints(p(0,ARM_BOTTOM), p(a,ARM_BOTTOM))
    lines.addByTwoPoints(p(a,ARM_BOTTOM), p(a,h))
    arcs.addByThreePoints(p(a,h), p(a-r+r*math.cos(theta/2),h+r*math.sin(theta/2)), p(*mid))
    arcs.addByThreePoints(p(*mid),
                         p(HOOK_WIDTH+r-r*math.cos(theta/2),h+ROOT_TAPER_HEIGHT-r*math.sin(theta/2)),
                         p(HOOK_WIDTH,h+ROOT_TAPER_HEIGHT))
    lines.addByTwoPoints(p(HOOK_WIDTH,h+ROOT_TAPER_HEIGHT),p(HOOK_WIDTH,bridge_z+HOOK_THICKNESS))
    lines.addByTwoPoints(p(HOOK_WIDTH,bridge_z+HOOK_THICKNESS),p(0,bridge_z+HOOK_THICKNESS))
    lines.addByTwoPoints(p(0,bridge_z+HOOK_THICKNESS),p(0,ARM_BOTTOM))
    extrude_y(component, sketch, -HOOK_THICKNESS,
              adsk.fusion.FeatureOperations.JoinFeatureOperation, sketch.name.replace(' sketch',''))


def sharp_edge(edge):
    """Skip tangent seams left by arcs/fillets when choosing remaining corners."""
    if edge.faces.count != 2:
        return False
    normals = []
    for face in edge.faces:
        ok, normal = face.evaluator.getNormalAtPoint(edge.pointOnEdge)
        if not ok:
            raise RuntimeError('Could not evaluate edge tangency.')
        normal.normalize()
        normals.append(normal)
    return abs(normals[0].dotProduct(normals[1])) < 0.99999


def round_arm_frame(component, bridge_z):
    rear_y = -ASSEMBLY_GAP-HOOK_THICKNESS
    # The inside of each hook gets R4, separate from the small edge rounding.
    inside = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        b = edge.boundingBox
        if (abs(b.maxPoint.z*10-bridge_z)<1e-4 and
                abs(b.minPoint.z*10-bridge_z)<1e-4 and
                b.maxPoint.x-b.minPoint.x > HOOK_WIDTH/20 and
                any(abs(b.minPoint.y*10-y)<1e-4 and abs(b.maxPoint.y*10-y)<1e-4
                    for y in (rear_y,rear_y-HOOK_CLEARANCE))):
            inside.add(edge)
    if inside.count != 4:
        raise RuntimeError('Expected four inside hook-bend edges, found {}'.format(inside.count))
    fillet_edges(component, inside, HOOK_BEND_RADIUS, 'Large inside hook bends')
    # The underside edges now continue tangentially around the R4 hook bends.
    # Propagate through those curves instead of terminating fillets at the
    # straight-edge/arc junction (ASM_BL_END_TOO_CMPLX with chain=False).
    transverse = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        b = edge.boundingBox
        if (abs(b.maxPoint.x-b.minPoint.x)<1e-6 and abs(b.maxPoint.z-b.minPoint.z)<1e-6
                and sharp_edge(edge)):
            transverse.add(edge)
    if transverse.count:
        fillet_edges(component, transverse, CORNER_RADIUS, 'Arm profile corner rounding',
                     tangent_chain=True)
    remaining = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        if sharp_edge(edge):
            remaining.add(edge)
    if remaining.count:
        fillet_edges(component, remaining, EDGE_RADIUS, 'Arm frame edge rounding',
                     tangent_chain=True)


def build_arm_frame(component, bridge_z):
    rear_y = -ASSEMBLY_GAP-HOOK_THICKNESS
    box(component, 'Arm connecting crossbar', 0, rear_y, ARM_BOTTOM,
        BASKET_WIDTH, -ASSEMBLY_GAP, ARM_BOTTOM+CROSSBAR_HEIGHT, first=True)
    for right in (False, True):
        make_arm_profile(component, right, bridge_z)
        x = BASKET_WIDTH-HOOK_WIDTH if right else 0
        side = 'Right' if right else 'Left'
        box(component, side+' hook bridge', x, rear_y-HOOK_CLEARANCE-HOOK_THICKNESS,
            bridge_z, x+HOOK_WIDTH, -ASSEMBLY_GAP, bridge_z+HOOK_THICKNESS)
        box(component, side+' hook return', x, rear_y-HOOK_CLEARANCE-HOOK_THICKNESS,
            bridge_z-HOOK_RETURN_DROP, x+HOOK_WIDTH, rear_y-HOOK_CLEARANCE,
            bridge_z+HOOK_THICKNESS)
    round_arm_frame(component, bridge_z)
    for index, (x, z) in enumerate(mount_positions(), 1):
        drill_y(component, 'M4 blind shaft {}'.format(index), x,z,-ASSEMBLY_GAP,
                -BOLT_BLIND_DEPTH, BOLT_CLEARANCE)
        drill_y(component, 'M4 captive nut {}'.format(index), x,z,-ASSEMBLY_GAP,
                -NUT_POCKET_DEPTH, NUT_ACROSS_FLATS, hexagon=True)
    component.bRepBodies.item(0).name = 'Reinforced arms and crossbar - Black PLA'
    component.attributes.add('ShowerCaddy','PrintWallLoops','6')
    component.attributes.add('ShowerCaddy','PrintRootInfill','100% locally; see PRINTING.md')


def make_engraving_backer(component):
    _, _, width = load_inlay()
    rounded_panel(component, 'Engraving black backing', width+2*PANEL_BORDER,
                  INLAY_HEIGHT+2*PANEL_BORDER, BASKET_DEPTH, -PANEL_THICKNESS,
                  PANEL_RADIUS, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    edges = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        if sharp_edge(edge):
            edges.add(edge)
    if edges.count:
        fillet_edges(component, edges, 0.25, 'Engraving panel edge rounding')


def ring_area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(ring, ring[1:] + ring[:1]))) / 2


def load_inlay():
    raw = zlib.decompress(base64.b85decode(_INLAY_DATA_B85))
    if hashlib.sha256(raw).hexdigest() != INLAY_DATA_SHA256:
        raise ValueError('Embedded inlay data failed its integrity check.')
    data = json.loads(raw)
    scale = INLAY_HEIGHT / data['height_mm']
    width = data['width_mm'] * scale
    if not (0 < INLAY_DEPTH < PANEL_THICKNESS - 0.5):
        raise ValueError('Inlay must leave at least 0.5 mm of panel backing.')
    if not (0 < INLAY_HEIGHT+2*PANEL_BORDER+2*PANEL_CLEARANCE < SIDE_HEIGHT-2*(FLOOR_THICKNESS+CORNER_RADIUS)
            and 0 < width+2*PANEL_BORDER+2*PANEL_CLEARANCE < BASKET_WIDTH-2*(WALL_THICKNESS+CORNER_RADIUS)):
        raise ValueError('Inlay does not fit inside the flat front wall.')
    if not data['polygons']:
        raise ValueError('Inlay artwork is empty.')
    for polygon in data['polygons']:
        if polygon['color'] not in INLAY_COLORS:
            raise ValueError('Unknown inlay color.')
        for ring in [polygon['outer']] + polygon['holes']:
            if len(ring) < 3 or not all(len(p) == 2 and all(math.isfinite(v) for v in p)
                                       for p in ring):
                raise ValueError('Invalid inlay contour.')
            if not all(0 <= x <= data['width_mm'] and 0 <= y <= data['height_mm']
                       for x, y in ring):
                raise ValueError('Inlay contour lies outside artwork bounds.')
    return data, scale, width


def make_color_finish(design, source, name, rgb):
    finish = design.appearances.addByCopy(source, name)
    prop = adsk.core.ColorProperty.cast(finish.appearanceProperties.itemById('generic_diffuse'))
    if not prop:
        for candidate in finish.appearanceProperties:
            prop = adsk.core.ColorProperty.cast(candidate)
            if prop:
                break
    if not prop:
        raise RuntimeError('Unable to set color for ' + name)
    prop.value = adsk.core.Color.create(*rgb, 255)
    return finish


def measured_volume(body):
    """Return cm3 and a conservative error bound for explicit Fusion accuracy."""
    accuracy = adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy
    properties = body.getPhysicalProperties(accuracy)
    if not properties:
        raise RuntimeError('Could not measure volume for ' + body.name)
    if properties.accuracy != accuracy:
        raise RuntimeError('Fusion did not provide the requested volume accuracy.')
    volume = properties.volume
    if not math.isfinite(volume) or volume <= 0:
        raise RuntimeError('Invalid solid volume for ' + body.name)
    # VeryHigh is documented as +/-0.01%. Bound from the measured value.
    return volume, volume * 0.0001 / (1 - 0.0001)


def check_pocket_volume(before, after, expected_volume):
    """Compare a small removed volume with propagated measurement uncertainty."""
    initial, initial_error = before
    final, final_error = after
    removed = initial - final
    tolerance = initial_error + final_error + max(1e-7, expected_volume * 1e-4)
    discrepancy = abs(removed - expected_volume)
    LOGGER.info('Pocket volume check cm3: before=%.9f; after=%.9f; removed=%.9f; '
                'expected=%.9f; discrepancy=%.9f; tolerance=%.9f',
                initial, final, removed, expected_volume, discrepancy, tolerance)
    if expected_volume <= tolerance:
        raise RuntimeError('Pocket volume is too small to verify at Fusion measurement accuracy.')
    if removed <= 0 or discrepancy > tolerance:
        raise RuntimeError('Pocket volume mismatch: removed {:.9f} cm3; expected {:.9f} cm3; '
                           'tolerance {:.9f} cm3.'.format(removed, expected_volume, tolerance))
    return removed


def find_finished_backer(component, expected_inlays):
    """Resolve the backer from current component bodies, independent of feature ordering."""
    backers = []
    inlays = []
    unknown = []
    for body in component.bRepBodies:
        role = body.attributes.itemByName('ShowerCaddy', 'BodyRole')
        role = role.value if role else None
        LOGGER.info('Finished body: name=%s; role=%s; solid=%s',
                    body.name, role, body.isSolid)
        if not body.isSolid:
            raise RuntimeError('Non-solid body after pocket cut: ' + body.name)
        if role == 'EngravingBacker':
            backers.append(body)
        elif role == 'Inlay':
            inlays.append(body)
        else:
            unknown.append(body.name)
    if len(backers) != 1 or len(inlays) != expected_inlays or unknown:
        raise RuntimeError('Unexpected pocket-cut bodies: {} backers, {} inlays '
                           '(expected {}), unclassified={}'.format(
                               len(backers), len(inlays), expected_inlays, unknown))
    return backers[0]


def add_front_inlay(design, component):
    """Native colored solids occupy matching 0.6 mm-deep engraving-panel pockets.

    Outward surfaces are flush with the panel. Colored bodies remain separate
    for slicer material assignment. Negative-space details retain black PLA.
    """
    data, scale, width = load_inlay()
    LOGGER.info('Artwork: embedded CAD contours; data SHA256=%s; source SHA256=%s',
                INLAY_DATA_SHA256, data.get('source_sha256', 'unknown'))
    backer = component.bRepBodies.item(0)
    backer.name = 'Engraving backing - Black PLA'
    backer.attributes.add('ShowerCaddy', 'BodyRole', 'EngravingBacker')
    initial_measurement = measured_volume(backer)
    LOGGER.info('START front inlay: %.3f x %.3f mm; depth=%s mm; regions=%s',
                width, INLAY_HEIGHT, INLAY_DEPTH, len(data['polygons']))
    base_plane = component.xZConstructionPlane
    normal_y = base_plane.geometry.normal.y
    if abs(abs(normal_y) - 1) > 1e-8:
        raise RuntimeError('Expected XZ plane perpendicular to Y.')
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(base_plane, distance(BASKET_DEPTH / normal_y))
    plane = component.constructionPlanes.add(plane_input)
    plane.name = 'Artwork on engraving panel face'
    plane.isLightBulbOn = False
    finishes = {name: make_color_finish(design, backer.appearance,
                                        'Inlay - ' + name + ' PLA', rgb)
                for name, rgb in INLAY_COLORS.items()}
    tools = adsk.core.ObjectCollection.create()
    expected_volume = 0.0
    for index, polygon in enumerate(data['polygons'], 1):
        name = 'Inlay - {} PLA - {:02d}'.format(polygon['color'], index)
        LOGGER.info('START %s; vertices=%s', name,
                    sum(len(r) for r in [polygon['outer']] + polygon['holes']))
        sketch = component.sketches.add(plane)
        sketch.name = name + ' outline'
        sketch.isComputeDeferred = True
        try:
            for ring in [polygon['outer']] + polygon['holes']:
                # Viewed from +Y with +Z up, screen-right is model -X.
                points = [sketch.modelToSketchSpace(point(
                    (BASKET_WIDTH + width) / 2 - x * scale,
                    BASKET_DEPTH,
                    (SIDE_HEIGHT + INLAY_HEIGHT) / 2 - y * scale)) for x, y in ring]
                lines = sketch.sketchCurves.sketchLines
                first = lines.addByTwoPoints(points[0], points[1])
                last = first
                for pt in points[2:]:
                    last = lines.addByTwoPoints(last.endSketchPoint, pt)
                lines.addByTwoPoints(last.endSketchPoint, first.startSketchPoint)
        finally:
            sketch.isComputeDeferred = False
        # Match area AND loop count, so enclosed dark holes are not filled.
        expected_area = (ring_area(polygon['outer']) -
                         sum(ring_area(h) for h in polygon['holes'])) * scale**2 / 100
        candidates = []
        for profile in sketch.profiles:
            if profile.profileLoops.count == 1 + len(polygon['holes']):
                area = profile.areaProperties().area
                candidates.append((abs(area - expected_area), profile))
        if not candidates:
            raise RuntimeError('No closed profile with correct holes for ' + name)
        error, profile = min(candidates, key=lambda item: item[0])
        if error > max(1e-7, expected_area * 1e-4):
            raise RuntimeError('Profile area mismatch for {}: expected {} cm2, error {}'.format(
                name, expected_area, error))
        origin = sketch.sketchToModelSpace(point(0, 0, 0))
        along_normal = sketch.sketchToModelSpace(point(0, 0, 10))
        normal_y = along_normal.y - origin.y
        if abs(abs(normal_y) - 1) > 1e-8:
            raise RuntimeError('Inlay sketch normal is not perpendicular to engraving panel.')
        feature = component.features.extrudeFeatures.addSimple(
            profile, distance(-INLAY_DEPTH / normal_y),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        feature.name = name
        if feature.bodies.count != 1:
            raise RuntimeError('Expected one solid for ' + name)
        body = feature.bodies.item(0)
        body.name = name
        body.appearance = finishes[polygon['color']]
        body.attributes.add('ShowerCaddy', 'Filament', polygon['color'] + ' PLA')
        body.attributes.add('ShowerCaddy', 'BodyRole', 'Inlay')
        bounds = body.boundingBox
        if (abs(bounds.maxPoint.y * 10 - BASKET_DEPTH) > 1e-4 or
                abs(bounds.minPoint.y * 10 - (BASKET_DEPTH - INLAY_DEPTH)) > 1e-4):
            raise RuntimeError('Inlay extruded in the wrong direction: ' + name)
        if (not body.isSolid or
                feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState):
            raise RuntimeError('Invalid inlay extrusion: ' + name)
        # Polygon area is analytical for these straight-edged prisms.
        expected_volume += expected_area * INLAY_DEPTH / 10
        tools.add(body)
        sketch.isVisible = False
        LOGGER.info('DONE %s; volume=%.6f cm3', name, body.volume)

    LOGGER.info('Cutting %s matching pockets; retaining colored inlay bodies', tools.count)
    inlay_count = tools.count  # Snapshot before the feature changes topology.
    combine_input = component.features.combineFeatures.createInput(backer, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = True
    cut = component.features.combineFeatures.add(combine_input)
    cut.name = 'Recess artwork into engraving panel - keep color inlays'
    if cut.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError('Artwork pocket cut failed: ' + cut.errorOrWarningMessage)
    LOGGER.info('Pocket-cut feature reports %s bodies; component contains %s bodies',
                cut.bodies.count, component.bRepBodies.count)
    # Combine.bodies is not a target-only collection. Identify the current
    # backer by its persistent role, not feature body count or index.
    backer = find_finished_backer(component, inlay_count)
    removed = check_pocket_volume(initial_measurement, measured_volume(backer), expected_volume)
    LOGGER.info('DONE front inlay: %s colored solids; removed=%.6f cm3; remaining backing=%s mm',
                inlay_count, removed, PANEL_THICKNESS - INLAY_DEPTH)


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    started = time.perf_counter()
    log_ready = False
    try:
        start_log()
        log_ready = True
        LOGGER.info('Fusion version: %s', app.version)
        bridge_z = validate()
        load_inlay()  # Validate embedded artwork before creating a document.
        LOGGER.info('Validation passed; bridge underside=%s mm', bridge_z)
        LOGGER.info('Creating new Fusion document')
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'Shower Caddy - Reinforced Assembly'
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('A Fusion design could not be created.')
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        occurrences = []
        components = []
        for name in ('01 Basket', '02 Engraving - multicolor', '03 Reinforced arms'):
            occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name = name
            occurrences.append(occurrence)
            components.append(occurrence.component)
        basket, engraving, arms = components
        LOGGER.info('Building basket and reinforced mounting pads')
        build_basket(basket, bridge_z)
        round_all_edges(basket)
        prepare_basket_mounts_and_panel(basket)
        apply_black_pla(design, basket)
        LOGGER.info('Building independent reinforced arm frame')
        build_arm_frame(arms, bridge_z)
        apply_black_pla(design, arms)
        LOGGER.info('Building independent engraving plate and colored inlays')
        make_engraving_backer(engraving)
        apply_black_pla(design, engraving)
        add_front_inlay(design, engraving)
        expected_regions = len(load_inlay()[0]['polygons'])
        for component, expected in ((basket,1),(arms,1),(engraving,expected_regions+1)):
            if component.bRepBodies.count != expected:
                raise RuntimeError('Unexpected body count in '+component.name)
            for body in component.bRepBodies:
                if not body.isSolid or body.lumps.count != 1:
                    raise RuntimeError('Expected a connected solid: '+body.name)
            LOGGER.info('Assembly component %s: %s connected solids', component.name, expected)
        group = adsk.core.ObjectCollection.create()
        for occurrence in occurrences:
            group.add(occurrence)
        root.rigidGroups.add(group, True)
        app.activeViewport.fit()
        LOGGER.info('RUN SUCCESS: three assembly components; elapsed=%.2f seconds',
                    time.perf_counter() - started)
        ui.messageBox(
            'Created a three-component shower caddy assembly. Dimensions are mm.\n'
            'Basket: 259 x 88.9 x 101.6; one body.\n'
            'Arms: 25 wide x 10 thick; one connected frame.\n'
            'Reinforcement tapers over 40 mm above the rim.\n'
            'Engraving: separate backed plate with named color bodies.\n\n'
            'Assembly: four M4 x 16 mm bolts, four M4 nuts, four ~1 mm washers; '
            'glue engraving plate into front recess.\n'
            'Print arm frame with its basket-facing flat face on the bed.\n'
            'Set 6 walls and solid root modifiers in Bambu Studio; see PRINTING.md.\n'
            'No mesh files were exported. Save the Fusion design when ready.\n\n'
            'Log: '+str(LOG_PATH))
    except Exception:
        details = traceback.format_exc()
        if log_ready:
            LOGGER.exception('RUN FAILED; elapsed=%.2f seconds', time.perf_counter() - started)
        ui.messageBox('Shower caddy creation failed:\n' + details +
                      ('\nLog: ' if log_ready else '\nCould not initialize log: ') + str(LOG_PATH))
    finally:
        close_log()


# Prepared four-color artwork, embedded to keep this Fusion script self-contained.
# Base85-encoded, zlib-compressed JSON; original contours are preserved exactly.
_INLAY_DATA_B85 = (
    'c-oY`%g!~~l^pgeL}_~bYu_*JnLO~+@Wg{gqfsP_&4Q}Q21&Ug3wn32h!tz+&QGdRu^S-%itpq(nLGDoT_gV6cfbGPufO}tkN@_!'
    'AOHNP@BZPt|Ko>0{p~N`|MZ*RegCgN{Pg+FzkUCw-+%v`zx??7AO7<B%^!aH{$GA$z;FKb&;R9bfBemF|MLBxe)q@!{WpL3^MCov'
    '|Mt5-|Mcg-{N~3${q+5R{msAsh`;{y{qO$sZ~pYdzkL6<AOGJUe)Ibu{`UQkKmGN)&v*RFf3|P<>Bm3)@X!DHuiyPc`j!IztzGo{'
    'zx?^%zWay&_8q^{Zs|Y$<<I~AC%f?9fBgO5{>Tez`ZmWdHR*rn=es}t@Z-Py@o)TVtKZW7=k?z|-~I4kfB5G=+9!VEr~dN&?|=L+'
    'f7Nf7_WACw_6WcG0gsQzwmbR1a5w+)`@jD6hrj*xKk`QY`t7$r{^{HQ_tTHR{VqQL&wu^n_oWZJY>walzW;Wvk@EMcw35DWe@NvI'
    '-~TY$sI#>{{O%8H{;vP<+p&K8yHt7}zis(<%dqeNuxFXCr<>*59y8Sv|NDBnrP2E7hrj*p2Mp8y^T!|YkMI7&AHK)`+gJUcfBE4D'
    'yvzSE)Ayq+L;mj{evkkDeaSW;_TN6FhWyrUq4w`=g#PW%KmFH#`SYLt`rSYL<1_UB-JkF5ZT(>X{g40H^0zj6`IK*?ruI)C05z|%'
    'fXq_I4b^X>kN8xcB@aM*-9Y<R*Bbhajm&5UwVK9_^lxR%Nhp0=bLV1EO?%cG8sAb%RiB!*3?Qx4`a<lpZ8_5IeJz7_$*tee{5I_$'
    '*`Zc<9|o<I`n;j_ZLU^yVc9kw2CXtmzM=hXj9PVJ=HTsbGxfMFhqC>2D{VWL_}{C=U8QW}@W~kawwfNN?CjX=N!P93_XgGj%eGK*'
    'tH4IF8**&dJqNHkRwh=y)t1)!f;AiU3~W8vuC?<w?B_QhtA5Mb=G7;cZ)xN#tj>!21E%My-+Iq&0V`OVj;&nq8^CtTj_sXo<P57e'
    'D8$;g(o30+^<Euo$zBt%wv)fq_HCrWOM96<7aFGA1~mLNv~O$g#t)5Yv(GX6%}s2s+6yq7VwKme;*;2b)ixi%UTt7~rp*W4E&H75'
    '_HtUcFXKkkhhw{Rn_3y8RU5Ch>6vY!0V~+294py|gqXd|A#Ah^sE$BdPiYcb8uDSoJ2QXP_Lp27TebptsRqrEo-%)PjN%J#ezT>7'
    '35M0V{o$ug%vyLKEA2cStJSUnwtFATv0iO*5VI%L=Y~zSPj26A-s;;{*{c((JL$@8Pu+l(wkAKfzU5NzvJ6}PWy=Pn*9FK{U1^Rr'
    'n|%BQyUDCeZFpM&)?1#scBZu_v8i3gmT0my2W+fWcq{u`TC?%{YyehwtTelQV5>HLtl97K>(<OeSnmtZ&l%K(*^EimF?$@x?2D^i'
    '+ie6Erb$nD!^07qI}Wuv@nE*&tu~5dc29XY*13c`w!GOkuvT-%gY}Frp2e}kt;4WlU(H|b#RtzYn-L=ud#<%}s{7|`qaBXfL)PNh'
    ';!-!vCQ9Px#`Hn%<y-EYW59H+VS8kL&Xz)6j@b~e`~_Q+>$TgE39GgP6=8OIG-39*)$h4-z8i)W%kOLUW9^06i|mUhO>edXX|mWY'
    'af^8{eDPkxF`G$^t6<j2xAtJRx^2Bx$7<)KvYYSr8opqu_%2{rPrdn8Irr#au&nLA<5o-JHk<8;sV~eXMA~sLcBj1pt7GnZV>Sz6'
    '2065CZ|DZKwN}2NW#5|pM!GF|o2`J-=2m<lJN#@js16mpF+-}KeSz36va3&7Zi)k^@9KVx0<u?)!<IWzJovKx)u1-wd0NW7f3TO8'
    'd4_v8d{=uumF?B@Q?{h^;%$3b<qh>z?C2Y26&%R^k#Vaw@%?e^CFZdKVMpl>wVrLM8kC054LgZu8QUz3ZMHzxwD0z9fU0Jxtqz-r'
    ')u3f>ayw*CYhMqj#CoxhS6C}!u2i%n?TPSRwx^$!YxlT5T#((@_nfQXtJ*%>fEh3awh#{??G`rX_$u3=w13oH2EM7_tvF<7GjG%;'
    'RM&OMP8NJs!gA5}WRH)BPRj=nyI2}9&}{Ow;)ortHjfNStLwU+YsaVNj*ZTS#ink<GETbA%(n!?&SrIu9XD@VFj$kl`@Xy<KGJcf'
    'YxB0(P+<-ZU&;mzJB(;F+Ukv?z%07*;YwXP3Cgk+{K3@eTc5J$H1h`QepH=4yH$L<O`N7f$_$XzKHNm6&M4b3$~MT3imkH^b`tiD'
    '>bBpsX}Ik4#I`Z2F0=PIY3<sR>-Tc*_C{@{F5hr)?3zha3~DwvvQFn>(*uy*oQwps^k__1JAJoKe>*0CloIEBv3ti?W!to64%mY0'
    '_*AyJD-&eT1SGY@Z2*>v*=|6JPUVg@+q0STwp_EWvo~z-3j3YC5<z*^4~!*^6i&&!;Re_!xM_sfU2U3~EoNUX$mVB*`(UHshK9X3'
    'Tb1JjBW_H6Dw|1F37remn4O=pXD@Ch+7`YFq3VFGf`(ftx+z+#W_H|&8R!k)Q#8%Z2*fvjaAd`2Mlw$ZNY6#yicQlz-;f<h6_Bl%'
    '@lXF`PTHS;`T_3KKk}v3y=iuvJDBut`|dbP(l?s`J8U)^wgGI}CMb(?4Qvp=!X?1**cZ=(v1N9{9I)-|D`ro_Yr7y@tY&w}!<a1x'
    'X7&rP63&TPA$e}zUTGuiHDgU>J4<Zh)O!DdLAF`RPPRLr^>%Au(%6I3`O(6O@5fQq(ztKUAnb{PCj1pyUoo@zp@L;C#Kr};mA1P`'
    'u-lS75Dd8z9)oSUX1~kcbEumE=Z@RX`aOG!HF-3)edg#K@a0A;Ltk&RsNw*vBk%A>vMo46V0;KNXQF;&u*O7g_&u9!X$Mm1PMTSk'
    '<O1!!=yYzJ{{h(|x{l)W?Ql(dE%!aZ+|Kd!a#qcGOg)^WV%xxTGGb)b7@1Is2|*vpHkLX@ix*)=3y<Qp>+K_H(#EUDS*f|LtpSet'
    'M@vAvjO{ptu$9HeGitfN9`1WD`wK(|>H0;T-3E<#9)sW>!L=V}H?-3k$XZQXX0-zzV`WRGwAe-M`~<XeI7f{xlx^weEw5O$*_OFM'
    'W`^kZMzUf0_)&20(JzD>0LFOM@Vv|g!JXTziaX~G;+QYB=;**ysb3(o_i)U2Yz#VJ%&>Q8uiH1%SnFW2f8*OZ)`C`<un)`&>^i<U'
    'S3b11X+<<msP~1OcJHsBV~+f~2R}e{h6u_nzaD4V@v|!K)K>W3g3PkOJrsQBePV0B(Yc-`%^hwo4w*fMALQO5#15VP(cU7fq1tKv'
    '(XJ=REX++~Y7||FAQDY3?0Ij<ydHmvW~K1EFf-lk1Jum;xfhSwK&@yhk7E{@&0g<CXPYB-)q9RS&<Rs%zof}MWSDWg#KeVZtZ!el'
    'H_qif;~u6Nz8}qk+ojbk5XAT?UR}?+2kfdJx#!^?+pc==WAV_}X7@m}$aLXsUjU9M-jaJFxKA2~{wm{PTIu|`b5FyTJHDH<B8I9|'
    '?A)9?GGcKieKf<uuI(*<G!Nx=H$7l3d>TN*{_nceuG8{^u!0+BT_L%TCQta%wwMXIp?5(WW|K_*U5H?SgshbEb*RA!u>ECSCm%g}'
    'J6^8y(e7byv+%D|w9A|@2-c78l$Haao|ild8W`8P%?o$BPxtfnml1I80+<az53IW{8evO1C~3Rx(fnLS?1DdW*(exnyo;|`he=DD'
    'C&iq$V`P+<ZG^iYel73)ULaXFA8yH543F|guX&v{(D%g7dLQ=+&xm5r)bFXC<<G^nO;OqFC+xsx%n&xm*;i`uNN6r2HWvCZh^(5C'
    'vLb$!ilVI}R+&3Dh{__Qe(!?7^6uIh5!k4&$Zzbt#A@pI2F-h3tK8do*2KMc`|L9}4wLPX3)>#!>v&AQhV;Y;-xyD;dzi6#>HE$w'
    'AIyd-0>n5Eiy|w{qbN5v&AQP6kL{6=4S^8sp^VeumB!HxNB)h;2EQ+@@v-X%xN$Su+;wJXe<ubn`-S1%>RrHysLkIkq6RN_AT!;O'
    'Z#&}5vw!-h|Ni-fY)pltIc&!(xY17Q=fNtS*CC8CHDKoK)GwIr{ae@Cs)sWKx7cIIz$Rj{hE;8t6-GmWhX(Vqbzy_Cw}KeF@7ooV'
    '3vsr>_yA3A!)#p4A~kFwp6b|UoUL?w%f7c(+r=4ED+p#xZjy#&8?{1gHV#_FS%O$u=_d$gSnDve3vDLO8eoi-6~-xxexq-5F@c%g'
    'mvyb3`klWU`=Vic+0T87*_zl`fNeW#ZI>Zt_FQ$W)NG5c3_4cJG20>GJ0f01d&i(rY)}ay$Ku#TMhsZDJ+3%rZp!3O*eI6B4w)xn'
    '$jmhhX{}6Qtt<P~x7`4+g%FZ*MmD(?u{9$9WSiLHwc9phdA14B%uhiMz$dyb(gHULP;Y6<0WQV%XT$8QSo)l~Ex6%{sM`$8p3y&N'
    '`?H*GbN|~H$QERMUs}z&u!r=YC;`=kSvC=|D{}l15G{_aq6AdKe)0MVMv;5@f|*U&_LraCcBH<ata*UYM?jxz2msgDt-x)<a8B%C'
    'z26@5J;bnmSK^CZBS&}!53z~av8YVa>T{IWs~yP9bbf9kb|sIe+L`g1D6&WI35ETS8_Y8o0nI)*18mbPXY2G|jaf`5#2lx41)P{x'
    'f$KJl_VvQh*R^_p4Tg*8W5m8*d3FFRHT({bq+P2q;%(QWMKXz}m|-mvu!flh%uS$}-5<UO9Sy@WtWIHOOmIW8g+Fw9Cb}BHwE5sf'
    'wPUGsGuv~>_DABLm^timYTK;Y(>F(@$z<FD%Vwo~#msjs`rV2>ksI)C^#x&pl-ypI7Ej%M!E8D1`MNzEMlG&ASc22^dbEs1IQ4xQ'
    'TQ)E=7TS0XRpx<LUPEdpxlOA18hShNN6qW?ip(anLq@Z}CJ+`gl2<7!^EhZ|7&c%GYGxpl2Fwn|zFxB>nR$`I|FoeW6<Aq{D4p47'
    'yX30<tReGtKiM{RJ5+^@4*NSJqMTd3BcFzK+lu!c`UGY+u&#wMQ-Rs(6)`F<dqOA4Y(Fpnm9vGIr-U3cpqUjRvUST(*#z~yp?dn@'
    '3uYz~GQ~Dm&2tlGZ>M#~&gVP?n(alIKR6W5L}A8P47CaOrNx$ip6&G$h>6->^SYJT&fl1AlgO1{PiC`W(Oxoat~d(P+MCxRm=#qE'
    'FvU1_*ny*1qfdTcA4(y|iFUspWXEdRuUBg`#HKKR!;XTj3W|)-39(@lSVwwYY2Q-?Sb}?cO{vEmc%~k(j_|=XMJrrDB-wzO#ql;d'
    'p6LzD+%-;7`}x#gCd{*3fMqSoSXPxDF%GMYYKg3CZ95)Ze${t^$C|R$Yz{<zSzYEfv>jHVtTV&Rs;Vz5F5B|=v-Gj{Y(6Y^8y>5$'
    'APj9o{|<oL*0*dbVs9Hmabo2D5yC7iMrh~w%`nvLTsJdiXtHmcOn_p)tFZ1fFD>a{JJA-b-%$3WOPAY+NcGJWUpIK~`}x$&M5e8('
    'rgeiHBr&+ovNX)!AU2AeG{eTm%fo6J@%`D>VdLmT9QI%t0of|71cn_!*Or-mUt4By#~Ow;!AWD@u1aDW^8B1!ZN)tg7%`lzwn}=8'
    '6GB57<pxT~Av4xcc|wP}j5`mLQL3;a8gF+c=p<syB0;r}U0RfhLG&$G$IO~qk%~ZJjNJ+|H!^Wn@7&tW6>i!(nLh<)uPH@g%*<)L'
    '9v8W*#3!3gH5D*B5DLZ;X(e1J<j)F5G}U%uzr&|*u|+Kh&kW1yFQa&Y0*oWZgRw*++=tw>mWUk+5&fkzhw~E_s|+SObC~(_*klKr'
    'X`X8XTlL8S`A;A#S0f0lTd9~+yT5K3iS6)7{lTuqW5YBv*AAiydOKL%Ts#Zzoes9a4418#i2ETH+I>M?*qYOS)K>Wr)+P<w>o+1B'
    'QaA(6iZqaCKuVjgV{gSD7ilvjYJlZ2@8UCfe+Z!5$IKfuk0aCT+z&QU(?HC&!7dDc|MIzQrlNl?DSv`eERHCCLm|?NH1f>1cj`L<'
    'pTb<FxODU)TQH)Q$8BJCdW}1`1I(ss4J>tj-!$7_Kf(MmZ!fQLHnT;)){c{0!&|9t4ckae<vf{Vrs<nY(H_DiGcntz^<>O4)Bo*j'
    '>L-{$rggmof;YgQMRiis;2}Fqqdu~)h83E9SaChg82Bbvx2n_*yC=;)%-`(hoLQ(TyK7Qc4ZEV@pL9)7l^`2}1)*Osyyw@oC>%w#'
    'Cx4?3d9gShhJ2VP@3aH5?$>jmY<MlY_K~+v$RZc_O?qB3HO$zo9C^C4GCx?Tc#mlE_xyT8W+jwe`MDG?H=(R$&`ChCuPl<q0|$$)'
    'Wc@^9%_J~$m{xfEqwvy+QdmU=${6%v%wyz!RuSo~ZTWo6`wPV1iaSY!O7oJg#?xcE2lEuYx(!vBPi!w+tFS~P*BB^$-%w%{A-*~u'
    '2zvu>1@Uzp-_2KxVcll(>zGHVgsv!d$B_it$PRwYRu`wJn_q4C3EpH?O%!|Zu%5P;$RbNNNACk10iVSH*K>eZ+V+e4xt~+~6hmVf'
    'cIwop77BKF*w`cJ7tE*{I+V6THa6ScE15dZfVJ80QxA`2R;*)fC%rJ+22;5Yc|?WQ_Cs0c1qRbzT_=V;NK?Yz7(ZuLPfT{7Vj0Pk'
    'eO@+aV#esJ>;>_7Y-PZ7BxRqwfM7pHRLDzf?~i#@h>$!XoSkr@?B+&ks^Yd8zImM6$i&HDGh*{uZT63VR%vcP&!unM9#6vZ(~3Qx'
    '%luV+-NXW<C7X9RB?sG)x`p#HIdQVhTOA<D>px(=wXXdxb(&>oO4ya%&I7l1VXp|230x8L)vhy9u@214@xY3(Focj7DZCGRRJkal'
    'Ix=7lXvOXA6LX9QV}*KQusXL`t;LN}vziXZN`Tw!McLQ*VjLUh_53UovNx@>965{jx*Jr?r0pv#t7?n|+I@QXS&2^D?|WBBdMU)N'
    'q98ZbwLkOEI0Gu;R3*-joZJE#y`>V>I6ObX+PHt?vP#aq7-o-@U-t|vC&z4*0diSBna6=gy`x6nR_7QVuj%EBF=Hpe<@hSpbFQp*'
    '+PG!4Pme@K3EP+ZFgJTFx3<!3ufymu`=TY`_J$HXdcX8|Lzq#T82gzR3w8ON0}rHWw&KOwjl`6l$aCw4W6F-R0GcMxgLEOt$^D94'
    'MJdI$w>o(HCs$!J+#s`c>b%nzb<(JpuUQd$t%$v5?rz8b#OKX*ePt!^$L49`<ImzBwz?xLQOxrOW;S7DKHL|E^ITVZ`O%djvj`C+'
    'dx}lW4j&yVIpy4dHGBCwF6>Th3(@Hk9)07LwdfpcIC$vRk2q!Q_%_E3zhnDHoKIL5yft&P_I<X&uV1a{>&%$5V-e$Eu8+=-glUYy'
    'U-J4l;siDsfvG+p35kXoRhce`d;~H@glsRY*J*^;m1-Q>o2L=pDm?vYYN@pW>*gzJqbWR%fZ0wilL93Q{8e*-VuE(sRF&pk7)xWI'
    'incNy9kVv0M9`ody&uRVcHT+aac0?kF3q9ysfk$&sMUQ(!@fWan%!4oqiX(bcCg4VAGFc$yN#9>U`y>fw(eoE-4Aa&hCP)J5{#p8'
    ')oqwwgNeX$^*f0{hgY_@KdSBIf!SF4%h_AuTCd9Gx-qvxWqzrf4Z^p-RV1N0V6Gec{E2dEG7bA<ly)Jeb1j?G5_2t^rlRG04mU4t'
    '=2X{8LJW2cUtQ);rX3h+9~n(k>5(d|fvuXOn2^Ov9~eW}mR_IRtg2dpA(k3Bvgpo12Mnf~TZ*hk!=-Gi>fuTIt<Y(h<Gy41AU!VS'
    'gV7dRQSKH{3oo_f9JLie>=ebJ^cEM6^8{X?3oNdTGF}+gt=D{4`vSvRbJYZMH&?q#B(`a~<(=<r4~!BtR9)Gg@R%I3tz>XOR#H-2'
    'rE{O~qVBkSxJ-8zCtRj0ixVExogxU2=~a|1S4b(0hAuShG&>5X5}LFC<)Lf^4eH8Sf-=f=*PVy$uHvFp?G%T{FlyJejYaI?MW}*='
    '6-U^8ZQxar()ZZ?*})sl?eUt{+&9~N&3;<%ex}6^4s5@c5<_;Q-7Bus{p;mE(K>_Kexf0q)dEA&3Jy&j&*%k!HNy?uEQ}Rc^ZjZl'
    'Ey11v+gZ2~d3_2R3*yqM9T6DIrYZ{|gml!7Rd~~$hwHwkIxsUKqcEuZl~@IS9CW%uo7ch-c|nLuc#z?_6xL78`Gp};QTOXkP~KhV'
    '>vju!#ro^93U=$gUr&!9)Tx!yC>3ms@4<wBQ)_<>dWJ_FW0DiMT!bWdZm*Y!q9rA-&dWxp$EozQS!#=}Vll-mM52BIsz|$Nf@S0g'
    'D;&HLb%T@jP6e@n9y8r%Ye6H&T=SmQ1+5%23Yl#1V6dWS%9A5!MHF;%v}ls6bvaUYl<pObF~3cz<0vRJ%(mIHHd!i#rzkp_HrjJA'
    'c-SR!-hpvuV^B&{wsNyw4}({fN<|s%!Vu>&qIqOuQUEKk2ZS-lUQtY=+#<{-GzsFB<&vWC%4~gJJ9CLtFQO=b7Cb>gW`Gw?iqs=>'
    'T-lq*iLxU5TM#g<=sED*OJj;=4bHo86lqd!UfNoZ8Y|oA8mF<HJp0L-;*QbJlw+Ihtl|Y`0~Hz4opAaw%-6IN7gU21Lnrykn&Mt6'
    '>Ox}|_g>G+&e5ePH`ZVUX0Iut*OR@Ym2OuQI^*@(J+rkY^*f?n84-<AZcN|?%xs)~7j6Sm!QjaTR7Rensli)kD<e<u7TemMzUgSi'
    't%!@wrc=Dp?r2_!__A!!SkNO`VUAMcPuPt_YXH*J{M?R&<1w;mG7VuJT}{Buc<Z{>j`>B*{uB)fxuS)ovLNKxg>?8Ti=orW>nulP'
    'JL9z=YJ<(PkH{RQUSUr&MtP#N$ShVCX@^q`PyP$UIvYS{bwvQaBkE0TtQ>KXxp-?UK9`Vb^PM~}SX&d_1lRZBTrN1rpP$9CYzwJg'
    '_X`_u>C0MpI;;|ZeLt+j?2mxStSj^0nV;LKMv0b9$;Qvw&Kjj_Y#kw_OD9vEFJm9(@vL1K+JCQH=KsQ}U0$)y&B#_$6qQv}ivojV'
    'sQ6?;?Qo^Z7N4U9!p~K2v7--%C?n2~ePVzfE3CBHl18{BS`;kcibAtqdgGb0vKwuWW5?`TL|&JBcIh<9(zrq<0NZg<fj{egQ*%s)'
    '+;Q1>mPWW-E*lOhHQbS(pz-@kRi#m4$qm1+lpX0H^K2Kt&koLr#&`s!!U`-qf)9ut;C!n}>LZao5!_)syz0`uc=njxS7I6?@lCAO'
    'NO71))%k6<a>tHk(Gst1Yb-5`UeH2{Gf!iJSV#3AMHNVop0bqr6Sia`l4U!AnH2@4!(-}J%n3vqV6mB4i`{HxB!zK;o#b(f&y8qU'
    'C@2a>#EZq}5kN!!15igbkZ#X5>jlgvayiMCgvjN3s5S}<arv{zlIq$#3NI~aiHh(mT7rqGUnG2L!_txyB+r|W21@>UVHHu0DvSa~'
    'g*TSq)ZUje@{keFe0~8K{yXc=FxT^3!?76^lr1Ae^V}?!j@M(ti|}4aghc8ZuV;UXJP?xcv3!a=&_B{=eieB<ujVQ8KsKPw@+$H`'
    'I^fims>lOg%Z%Sukq5dUynv;$#%dOyiM>aCY)V=tviY8f6=S_8isg|l7|AK3SOaI3FZUVMAZGsc=2lgTozZrlMY|I5gL&86(sW(>'
    '*Kdr7DX?`A$#k_M14H{Ag7mdTA!Lq^&2=!FU(?G{W{wJjI)#nvb0b$TP+R9GN_<~?ezs)RqGYs~Y}o~g9gwIK*bjzgMONHwwLCW@'
    'R{WlGdocFjAQRN0#$x%$u*U^tCnYa5S3O$zcK`ZS$?KF2>ng}MED1ZeW(L>TswZg=#wJ1JL1IWMvdrDf8uqDKnMv5VK9^J{Gb0Xs'
    'uD#;G=Qpl+F;dmS%>Rl?*zC{o!b%dhA|j1c<o5c;lhVK#==)Bx;b4f?=l;6XZ1R=gzi`bl!$$I&rW>o%zs+{)V1+4U)xa-AnHa)q'
    '#Zwn{PQ{(Tbm!eAweZ6VbPSoL2V=Vxe^;Z7@AKPh@gf^;-sjzoZP>Sbk+|hwzshjBR=?v?a-?)vbCT!%-`CHbYcl9e4(8GQ%#zhO'
    '>9;>*ZU-Wz5$1F>@}K0^8#8C*b!jj;T|a;l(ly8XQ-Tr-H{wWFDuQi52g}7%g?6^D5t%pE1tio;9;^uKvqX-iF20pFR)t;HDqEJ2'
    'QY`Om*>f+f(XZ{kWkA<XfU|3`?*8l-fIR2?tX(z*q&n^ybYq(I_oZ4I&kwL@CKAk^n4Hgld%19Gkub`U(CMhGdQA;dKlSzNXJY25'
    '<%PG&ZOSMvWu;j2+81E(1MUPg3Oa4i;O8=kp&Xk7PI;zH#if`LfT;5e)H55E*xWS*d08xu-c0KOY3$-<qHqKBu{yynag~JP_ZLbM'
    'u5wabvXINTDuscWHNk5~^6EKUQgdrxuwnC**i2qh7gerbe#1$Bo{Ciz*P>|lb$c|MCUfhldqBsB-E42e(41EsGs|yt?BH;Yz!2m`'
    'F@RYb%dr`so86ny4_3HLnts>r)ARCRaS{aM$V(Nxm7bVaIoMWYN7=8RJM^HF7Y%GrTm@qjZ!Wu25sXcIh~hDh%(@uVS^GP72!u_a'
    'c*TMc1LH6akC<ed06urvQsS6-f~&lyqL~@w#kuDlT-N3_7>W-CTM;K&%sT`;5j4BsY)8Oi44)L5C>;sJRbP{W^=w`PeP%#IQN_xy'
    'iA<iAGGFtZtSWwcC3%e02h@u-&>5ovZD2?wW?!h^Xspp>1;<$Wjb?`>U&gMb^uOzbLf)l#DNPFEJv&F-aEXpX(evG>Hq6lO^&5RX'
    'm~ZmThD7~}Hu=kjVj|st!d`onX0)E0%sXH|_Yh8>cs&H0O{>S{R2@uLyx&o|=%l)Wa!j6V#>>p2<*R`kjw<#mB!|pBic%1L>kL0K'
    '!j0?}%KaF)v~P0P8U1@B`!{*bTV?$p&nKmW_)T`h%OQpY5bg7-M+B=GWJFDIS$-XQott8ZjL)J1#D>d*@uT{MXwBu*m=A(^5xzAL'
    'xSNFBwXP(Y;Ym~Q;yWXg$s2+SJ53o6wcF$dMJm3*FuYlu)30-vx1s{X?Lu<rAudZd+%w!Tbf<@9vzPCn00i9w73P`heL<a88Gh+%'
    'HUfE0VesB&kNd13JoC82lCulipW+datr8-{7CrFNr)u7ubC4kxHSRh;5d+yE@Fb*kFDH|CN2(4Ku^vy&gK;T&;3zyWyvb4TVE2I%'
    '8MpjXUiMA5PsB(nwr6}@g;?LvdrGMIMB|=NnQ<WT7NH5wJVsT9SBs;PaqfNxTHxIkkE$#LM6Q7;3@>@O9o5d29<O<i9zlgE?umuH'
    'JvMfYjK|7iSZJYm6^Ff<x^&~+$IgphD`_@05p0Ve9+~of=cstCWbAYg8Qf5_Xr#Ii9_f$>*-qOy^}N2wBXg|vL%rZioI%-69IX-7'
    'wIOlPwUAi+cBKf=B)PWIOP(P>OF&8EiTwZSeTWgz#5i#Au|xb5^+$+DXD`ZRTocQU2MEs>meV)J=m*2+ESks+&=0jRp|W>uUWR5$'
    'zpS!>5Rf{3kPn1=T~Wxi8FnAwL2881t2hNU&mGvSX#R_Xd?=M24}ISdJO{6KIu{}py?91}l4W^LDAt>J-?-q?dLgLq(_IzP#Ngd1'
    'Ul-j1SH=Z>i{K9dWY1hRqO&ST=p-fwLUO4TzpE5qkFs+AMH|t?nKji0673FG;_nnGJP+ON4(DJPxXkK#&nSa{yYF9rswFat(7Dfn'
    '(=nIVGj?POe7e~>bK*EfPVhj(ExH52ZBH}b7h<OrU0!^BL-k(VL}Q^7is)xA_pQQoGSl+c&t}xlup4*4eHmJcqqiH0oCca_)$d%8'
    'S)E@YFB2U|)f7Kt>`;VLO|pRHOIVeJlZ*|%(9xyDF5xzvmL;}>LQ~j#yR>N(hTPh{wG>*y`PzRF-OSl*sG>5To{&y3?qr3{?OwZ!'
    'rqj;IZl3CiLl@}W4yh9uz3mKl)}lT{loG7zkar)024@V9{!aH*VmBzvXgYPFc9AP48tssU4Q54?%e#@EAZ+K-ZFj7;BZJr27rvVq'
    '<W2{)nM__1@ojmR^oqWa0EQh~MbE-8==_Fsm`})-=XxU@ybF8_INJPC7QGcf+iL-kh3foNPg_&8r|K=<2+#Y|)y%?B)WD6VBhB_B'
    '@8+I5vTa2awtT1lyaxTCy+6IImZtY3#B_v_##j&=?fc)cCTxrb`-9AjRqQvQYpYqPG577EC?UGI`)uDH+}A!C=1lrdzc8c3-}BYJ'
    '7d+`|P>6IQC#h|(fY#uZ`)<RZF*4)~Aks`Y`F50>dacz-%RdGp=xvJUsX=dC9U^PWwc8<Xug5_b&=Qo~#+eFZv)0}t)~HtU+hW4|'
    'Iq>N{Rj)m;8RB<k&RBaH7%cp8YbmF+eMFsWk|s`Nx|Wp!ZqGzT1*<y|m}O;!e^qS?{Wmc^8I%;|x6kNJv<{*tlu5MI0!a$zx9TI>'
    'H>x`DILg5TQt^jvMbm%K40?Y;Gs|`F_EHN!g@ZwmS5cVJ-!wgVQ&&;O=>kVi*YEQ*fj^Ht!B;o3&rw*2e~0}-MpgF4*kR_Tf@l?x'
    'f%k+JARM>ow6VWco#sW<9d#~0fxR8>p&2+mb2y2;crqxlFA4-yvpO$^O@Zwnaz^Znp8;ovvR4_dkwfIB!J1B4X3j>%62Gga?KZ|H'
    'r6>3m)UY&gywB<VN}gK>gtHuXs*Myo1s&jy3US_7uySAQ3Q?$W5i>+R2V0+Z^&P{@KCY)`PkrSxg4@#HEX(e1hLDN*?R*Zqdre}L'
    'niPI%atQ5k(^)j?@cSCRZ9RiC(Zy8>jp3Bq6E;Tj2O2y1r|g|Ac3RnKQT$Vf7$TalPN)CVdv(!FRJC4_g(Eu!ge?udG$*Zinz8u)'
    ')4ZFkP<%eTadG;2gc0WtqKmTGiSetacphNap06IojQ7Ap_~|{&B>t%F?s?3Zfa*g~J5`=&Xxm?qna8Wo5>dMbqDl5yIvpFsam72w'
    '>U2*W!N*B60!F^~VKH7wJEEaK*`tMsY9Zc3%$u$d5ktQ<J0hm1a}bA%Zb>r-mqN0(kq&3I@Y)~564B7}hB|5bKu9#atAiMWHWh9u'
    'ccf^hzuR8%b)$Gs>JZx<0#liH^1|%B&UyF3W|o-c7le`voOgw+n^{=jv_zjK5e(iSY0uODk$DpPz^ng*<IdzzV|%bew&zxFyNhAM'
    ';)!O_;_(N(e>3TdV;XksPHgovf3nAH0x#Y@Uo%t#{L5g2lwUtzu~#lH931l6qvH6gju<SCU{Jt}Pwk_<Y(FbXb^g6rN0=#f`pWV$'
    ';zCk2Z53L$PZ7kShhY{z`R3Hg`a%PuXxD-5!pwVi?w&(3!e$5^O{^dG)P9$J0}rpT`C|B~Y9Cqqw!zO?{}}2><|B=8+5C(NJAF`i'
    '21w<LJ;?Tw?beJ+C%JXf|3-zSj+5{*R5*OOA`en!74-~53EQmLg*FRg`)$ZFCcW2f?rv;e&Qvr+NfUM$AStqhG=e|hSdU2uLp`~Y'
    '1BS7=sUF6B)G}Tce~32tfNC!WU!A)OI?PZuTkoQaa{xVcDX3`PncrknPqWeNxa>tP^PIYi{t`9`9iCLV@M$LVKqo&9!s#>CD-eCg'
    '>TDLNz&-*qaM0_NtycHnv6PTBE88hAw70M|YWnuov@PM!pk@1t`B=c!>>f5P;DJcv?)+ju;uKeaS5SFey?up1#8_C)IUGqt2in<2'
    '87}wjaUk*jcN}uy%bfC+M1}=bf{jL?i~1@fojQGaB+cO*)b<w(8CkMXRd(4T#J2Z{qe6Q4wVj!=D?k8+gfY+eb$zbb3ZMnFi;Jyf'
    'HlJ3fFe@mv{JF=4R?;1&Ai3<PX>P*3Q$gs51c;eOFfl~O$z|)+qKJ|(*GDp2x0Isj^b=h6z>tXo%|??O;ur`b3a}OIcb!!`%P~>M'
    'ba=iE&=waKi}u;z0<3$Cb705#G&xaT?o%?@_2p`*^^SznO&*ylp6q?iFW4e^Gs?t+yDL*}VSK@Cb=hfqUCTDjj<$~%)))c1?uCVM'
    'tF`-<$)Ex@j_YAjp;90g^u{)A;%l5*xarq;9&(Fo+)<3t5JSQH3DPiyG*Btt#wj8Oaj;|J3=2{>vUu&NNuDHb4`wf6usA+VZkpPB'
    '7^i7|UcEYhMA)UuYH#TgXPGLnc@hU<mnyZ{(j&gETUsFax?b%&;^BI=?@UDRgW}6+x|*NMw=zP|bw#U=t-4_0dTBApI#<Cxedgel'
    'dx<^BK7YwZh_x=76>yX~L(1v6p-_e5)oQtDoO$poYIJ`TYGX77z{F2m!J+RxYtc-y5RfG%8taZGEjEZTs9uG!o8{A#H*)O|_RD;N'
    '>quBfc`SKEbgk5`K2h2oSi$2~k~kN~sGjxVa!|-0&FLW4K>?_p3*zXd8rO$v2A;bDW+odJoR@%f=JfDjij4|GS{PW$-b~*m74~8I'
    'r)RDCun;RkB`#WarFW9hV2|?8<ykHY387G}QH`ic-lXz=#r`FTx+uXvDNf`B(t+Tq6wffoX4yDaR?^p*3BQQhkCqx3c2%~cdhcIn'
    'I~&p$V$r<cZDob<2;O4q5;-Hq5nCaFGU}|M@1*Xb$?Tj8NJFn_v(u6Fqv{l5nIEv$M=(ye#on|g$tg4n*#OMzW9SKD->8_$qDd?v'
    'XCbmtEvbQy=BD(rC=98kb&coI+`_nTcim6t2wzWM`|ccRN=)4yAx-(KTP3V9hZ?L*9y@6y9&XyBCb_EEL!a8+5E4`ncS8u8?`sb7'
    'Cb!2L73YGvKOri`8JcQzbx=;{p0%g@19i-8N7tzb#M`CYfg)7SWD+?<@2ux8+anYbxyyFsMIv?CE)5bixS-IYU4kZ9=4fhfm+nb)'
    'aI{MvMG7m#nmb3p7QDi1y~m$@Uy!&<5G6!U@=cV`E<G8x=Hoq@n_cFq2PaWNyEJSV>YdoOYzwMEz{G@Sdo*)2VxQ<qR((C*0I;Ln'
    '!?H*m1ZtPLNkH1AC!};~bl<3$gQXT!JP{iQias!B!LvKli?&v*Sb|t=5gkb?17WpAdz7fWG^Fvkpx2;^6c${>d_IIf+fS+Op{c{i'
    '8(mo{(ZfyxY<dXb(EIvPyVb;DR>$D6x)cMz=7MrVp62;57t6L%ME`1(fg#Y331*{HvSTZVkTYlmUY8=~R=z@Yq71t!v)~w%$KH2L'
    'N2~Vx!N5Wr_Ch?rTGc<Xx5(PeY!#*rv1OE^L7q0Vyd(6{7q?Ovopi`1T_INF9HHx}vE7+AL={#WEu80#!DJq=`hnH;rX>6&3!mz8'
    'F3r~m@79s-(s#KELI9kSdrQ^>Vzs4|8^R6-sS}Fa`8gbszFYSWUM=M@FKs=v_|8^d8hn#kxcbuc1LFfa#BS|B#N;QRprYas5K?)~'
    'u`)fM01OS&l)`H=PpE0riS>}jI~c~nN4!&CF;V<+ggoBCu$OtNs8dO&FQ-$NJRY!4nsl4MTbE*gbHTikXFwz+L?YZ9%sZL)M{zoN'
    'r-^?sRC=f$h4r7PP?KwVV~AsUTTVyz3AQ36CM1p*5L!Eyk0#YL@}l;G#PN6mH6y&@pgRi^6?(jMvWo=i16eOWL<}07%^;_r{+2hh'
    '-q7Q*_2|jhji&f9K1zJ(=PI09l`&{^?1Wiw$jsARZy`Kv2gAik9>~^5uebCbN*WRKy#)G5<WQ(Q(wy7)XO#Vx^#8iIzYr?CFZgTu'
    'B@!6Ix<4-@_$cjO`h%gg`%5Z?5_S0^Z#ea-Ul2i*G{hJ6#C|^Y^CF83aY(S@7HF*JbH5<um``))O9XPB&;5c}<Rgdh5}Iu1bH6A^'
    '2`b0@Rm`%S&;5evW%UlDFM^re2LG4Bn$0_<zKU`#eeM^<J5hOprm0^Wp<z{0FSmFxj-Z7E>m_`QQ*I%?LCjS;Jq*&vEu?%nZEm@b'
    '5M}Pi+<1hW^AT$PS$*gI(3fAr(Di)kXXT^ULrr<<PWSVvpH-*6w8Ji0>v}%*v*Oo}w&x|9-Oq=9R#^K8B0Un_M>gpfRJ$c(_eJiz'
    '>Qg_j2`*u?FIwUwKJ+tk<MrXfyHv`{`d=uSOC<2-!E%wn7fa=FMqmMM)ZMBuNgazF1$K`sLTVATJHH^XMo^z{dtC}UmeaUo4biFB'
    '8H1N=!UpC|okN=Tg2v)^Q?OgpAA#?WS6Ky;U8hp%#Y!?5xUb(l#dQFu2bL8Gmdy{sn{~7s64k6j9YWev3@dZq5V>laE(B{0{*c#x'
    '00dh-1yM<M)7IyTwFb0UjVMc!aToSojvf#=9Hs5-1|r+QA+coUX}_V2!VfS0jOKF}K~lqx_o%x*k!MTP+fLb`V4(~M6*us4e&q&6'
    'B|l_7T{v6LCTg=j%+B<AaY$iZyZ^vA=fqWOxc-PE+zxb0hk*7Gz#@eHS_B8ju0JD7NQlB<s<Z||cB)H+3%5CwOLfhlP4H)V^t@2c'
    '261Ugv)$6|IK`d4j1D(a-H(*kVOEe_(yd)6Ri#V25KTF=9W7F5^Da{T1(^f9P6}?NUT%d$q=U-Jx5A+`$)Z6OO4ibE3kGZuNJy0I'
    'ErEHq`TwaZrbC=;Wxu`*SP=(W{AQLc)=QvXT4i6bUU#_#8F^IYh(Ws|<69{7e-so&)dQN%zF^qsUt*-g>!iP6u8GLi;Ebt{2x?+s'
    '&3s`mVbp^)9m}qc<kC`Y)Kq^-MX9<f(~*q2RGE%s)GsPEVIQ64C_f=e4on<Zgc2PZc$&dxV*Y1#fhaX4!s%@gP+-6&zK-?(Uopna'
    'Xqt&zQYY*eT`Cuc<h47bPh2t>Se-8|tV?d{($+cy^)q@~D?6eYB`r+XO`Cm&$`^`zZY{OYk)*2@k{@8Rs4nu=;zqbvy$mTNiHCpP'
    '(Y->>3<nyt%7Pk2%BrqkHgm|MAVW>*GjXFV+K>EM9NImk)RsGvt4qpav2~}ryxNMdqcp5fo~B=AK`F)Bj^ZQQ2?Vu}h}%<Rp7IP%'
    'GRey=mG4m^4qRhCiQE2i?U7q!z_;*zL8v=^L58j(uI6uS_b;C-k0KsogV(#kjf}EiuT`$m7m2)XyMjv;@0|K21AZ^;?UFtB2GAuK'
    'NUVC1e3!cLuTcMk;N92H*{<#mR%~RhFt{9YrQDwp9Ylw07Is7u8Tfy;%C2YhFhUExc6-HTx%;=u(K=*99C&tJbL=R#U%T=BeX(ob'
    '5{r-{4Q<9orxWwG9=XQ7KBCF~c?Cz-7Z955%cqocJrC-y?Y=L)-23*W-X2eBGvhi9yU(BN$n09$*TH(rU8WiX77&8jp_9pc&m+cs'
    'eOHJv#}7VQ%v}!GExGA0@S`;z;*pEGoZJcmf=CU*A-z2klQcOJs=Aef$;g3gOH$%+BCZN^$=PB6p_|g7)^2IamqzN=ou*(>XY_}m'
    'iWCw7(!;)$R71Y<Qc?|p*GpVFq+1^aYP=RKLeh`qdG9UHKwQu<(6}oN443UI<?Iirn_4V)t@oB8dC2%hHzkh*wPwq$jvRWfmxgj^'
    '-(E_~tS#d>oAVr^xm_WlT+^YeQzU6VI=Z2d3su`MqPgbj)cF?8twAXflAv!*-d38RGJjsV7qoZ|y$4zn(qDvu+tCVk`C!>qKdUHw'
    'bcg$qA`W%p7UX-3fK8V$UWdxgY-1w(J{@Hh-e;%`N@WjO-7mW{6h$lLo@qPY2eO1+?sL0829&1%$4S;gbTm;+8lSDV4ZuiuDz~Z7'
    'nNH{-IZf5;8Cf4xuNB_arAv)gFiBO{{j=)Th?zHiDry=SbnPcV#x%s#J+v^c-1vFjmUEuIZa#r^{{4t<l|ADiHPRO#@$YC%xFo_`'
    'ywl-9IQW4Is2!QmH^d^4OU7B6>9^Q($p2lE&>>-Z2}cK&?4vG?EL*1*e8h8a&2^g&q0p1Id+u9`XTe@85%rs;?+t-?@+}YlKT(Wl'
    'Q0NQ9RwH>DAz}l5x9cWYn$_z4i|`K-Ke-kwqOxFFleI618?3DTa8luZ(%5f3Tv@uwoOLgRv-R%?S$6Cf%!qFn5h4jX>h_WSPLjVk'
    'Nw{pDxt9q8n}|;YE1JSRWKBoJsy+}x8;rC$g94(R)O<zM&R%W_j5RBW9C|thbhG4)YNSH#!NQ)||1GXKr58H{Fu*A{`r%+_AqI9H'
    'T}VD#VzzR25LK<k!UhuAiLH;sS7hxfEeQOUlj%lH1liyrlpW%&cTTf1>M-@QV6xa>K9|XmxY(2+q``l>syd!P*#;?H9j{QCvy8n$'
    'Wg9YUy97ph!N-<6!Lh421z5qeUc}TVJVrvj7SS(^FNv6Ut5?X38XbCrgJM7|!k{|O-!Tc}#<1;_^MivAm3rL&@aJSb;fnhwZyQE3'
    'd#D7@?!(49xrhRi-i`#xD@qZ!-a!u5`+&edK2Jn(vHO$~0sZ`@6CXq5BgTj8DA>^MF#{#!Nd{DBWX66G2q&%ru6I~5;<Ccl_K9VC'
    'Zh8e9N!D0ayQ7Vf)4yYj)jPogBBudZO+4Cj!j0r*%ux}_aN||t6tTst5~@-YRTSl_m?A~!bgJ#8(Zxx%a=mHAE9>IsSE#`$V1&KI'
    'kdXbJ-v$DTz??q)Y!{S(dTkciGp9f1FBMULnUTybgKej<z`%)6sPpGNx<du^z>v0J*?XHoj*_?+0aHyqura;Ly`>z)D%JV*CMa(B'
    'N`WD`>?*)*?jSwEQhvmTks?o1ePI$BW}+*5-)~a;SmycSola&^6y4q=c@2A{O7O2RZR1T+UXw}Qm+f-V1JbhkTp=UmK(AhZalDk_'
    'gs!^fQoUsir-mLaPnPu$svHQyx#vxA&N_>{-lF&vOGmjE0ISn)<&;*VZ8POpWi`bKySG{oUzeF8hLZz|@I`ejBcXZsDgXl~H`@?w'
    '|JCPuCw<t&ko8}^pP^*Q_8sqqn<`y}_7gcgQEw(KW9U8X=4xgtT|H!)=%g8;41^}g;%#~*N}$$O)4I9Wp?KrmB@kANDzi*RY(hG='
    'sf-2d3zt60B&r6y?k+Rgy<ShjgyrU&=qWUC(C=3sy|kYjrT_GoKmYrmzHoJ^T?~~q>ODH`VyF#JkJ4!uW4%DnhtsNimtFH(j;9Um'
    'g^{+2jh)3$ZYr&|$<{t>ero1|{*$-MscC`~wB8yQEp!lvL~qvJLPy3mSeKOf^R9Jj3#;SLT>I!DLu4>S<Ci{{!Pt0<<^ii9#dOhl'
    '=g0!JnhVDD7y&V8@!eK$3rBMtOHzPM?^y-+63b7#w=u32HqPTd*G_Vn<u4fAJ9Vz1U<RB3W-;|QH2sJKR}_nHz(v~2J{Vg|A${O|'
    'q`^JKhOW9(y)n@4)*20iorOT?i=KJZz*v*|u(XF1GMO&m{|4rq9Knt+Eo3&SgYNW(9=eSX7ADJ&sQVwRBBnQj`-~)HU_e?c=NC5F'
    '$5UR{qDsom{Rd-<Kpk-_(`}kPb9~NkZ=(=wkNdfh*zr*Pd3*{D`{8_sF7(yDU}1g-H{5NepI1Q<<vP~=8b!8yzin<0ZZV^qkv*hv'
    'EV_%$1vA(u$dEO|3K$TA3|UxbuZJj`V#Xrr7fl-C&I7C1Czy{#vB$!<U@8`7yOme2iW-5uf8b{T*1bCo7}&=?A$_Zbm#Br}f}Da-'
    '+VBbGTgMh#YnwP1gh4e9*p?B2t*0RWhiX>U8W!p@Y!>wwQCt+3U1S#Uvp3}KL2V*J(w<V`@{?RPwZIU*z8eP$s};PNfD{{dGuG9J'
    'P*_z^S<h&Dm2a0=I1o&at`BbjOWjKx*;y$FLd|#EMQEk5+eKMXw6eD8?J1;00EV)P;!QgW1c#{PCv+izseSqrLMD!}%bM7BfII1@'
    'v*yKbSGuB~sEP+h@}Whn+v#2$Llsp9HeA+}C*879iduZfCi%aBi7gzT8=wJatk|0(iNRh%>{fC2!p7{zMy5U7h9U;$?xto-$85kh'
    'F*MfcTK3ihBjbdAW7As$<|QREu|CncqFWx_FNKRL2o}~yjVlh(z#`PWswFI}PiTbz6YU7cI619&u#*65szi#OQ4Pxe0<G?u*TROc'
    'Mhu=^4Ge0xh}k0{@0j^zn;5pi92n%M`%}Rg9jC;$TStYuYjXo@3YZm^v}|H_>%9kNi}ll?Y>=0JW5coSkkj^BCU&BNJ;t!6pil78'
    '0JA4_Mj+AFd^+3JeN@D50}O=FOBguCfkpW%8d4|rp8k}{6646zQ0cmsU8)}xB}&eo7*qngcpe?I*^r41(KZs}(5r~pu|=Y_&f?Ix'
    '_FyCyaExuP#JrBBP&dG4cT^h#WAtJW+oFmEM&g^OHg>FZcnDE#9GGokpQtu=%&bNX^WtV&zhLl8^t*OM7h(+&4Pm6^LGf;O@xQ_%'
    'Da<r9F}L`>!5|`vVx7i@d~&c%Q927Al`q&X9#1VhB8%GB^>y@`M`E^V+_y5A&zpKQXbAFJ+KTt10aNVd!9a%Sakl4LG+}wEjM!j4'
    '1DyIEmVR!fQ0;HMZW)DJUesHt>T13}uq{$WQP2R3M2Lv*K7(wG9v~6vJFrqDiy=}wV70nC8LTkG#LW@3gutL8K_{NPgg~N_ki>*&'
    'vKip9+WHXr@IHfOqaLE8t7DEMFtB1dR-w!TEcAmbyNeL!MWs)6_CKD4wiS*?l)KWK!VN!`J~42n4xGSc>vzq*osPkE6^2Tq0aZ5j'
    'SU~O*B30v|lL1#Gm|TGcp^Q^XBF*zK%2Xb}qX7#F7H}uo?!AH4&^rN!6Kx=R<|aIB+%y-lAfKt!oj|~v;aU#_ij59fX?|)}syJZe'
    '5ptbzF9QWdz_^mWV2ILA$53`;7}7efZ$^nB2w4o!A&jQy-5Kro19qxAMZm~5F*Ye5`Mab@YmS)<T7@AC2Mj^!=@|I(i1qDkIK(ja'
    '6D^vew3cKMu$;Z>2AI9`3C!%yso%AkQ-}?yO9Y0opAS7&We3(I7W`Pm(3LhHf-I1!f`ST|O*Ic#9;~3lX6ycTLk4itNtrV+v*m%='
    'l^&RfZ3#PjLg~YoGchv;KC>bPp49_hD(vh@XJ*&HF!uA|<OA;_37=>4C}d!^oF|%2MG`LgBw!oelER>}^qHM84t*V~&WJ^+vs9aa'
    'nU$UU>(Su!mUwL%0+1n!jP(rFKn;>ld#ObML(k574LzICUoQx(O6nOpFA|1|?>`56oHS><ZNx(757>Z2=9E&7W0a@@R_!>Lde{y{'
    'v`IY|FM%bQ3*Hart=4XX{#tPi^tr<5;!UKybJja+B<Y?MDQ|BK27>~yAYR2fn2dtg{K8PW?G&TWwcu0ok!q|iUl_Yk^#mVdLCN4$'
    'A}FW^5R;yd0N|k?m{+7dXbR>PkPkY8iI#W8vz_z+0}o+<Kv2RlpX`jptvDu;#L?X1*hR9Zvnd$RNFxH=Ai>B!>^ZUk#RvGj2!u9S'
    '5`Y}M_WkHLyI*YdrA<kw-<h*}QXsmE?if6mz0ODz;r!;)t79P~RDr>%9Ix-A71^R#+6-e3aNkiJO|@LS2#N<s0tGR7f7cN**JDV?'
    'ScwbB<pQgtM`bh8%zWAXNhm=?k_(T2ypvIw6g7hPa2q(C*xjczRs|2s)MMW%u=z;Bo{I9x4!)=|_k<cSmo}sX<*2-LJ*vsB);uq1'
    ';!tazmy&X5)y$)Z9EvtmipNsE8OdyRV4!PPqa&o3d8L<zQ8}!2e>-!fdh2UVwp`ZGLq-qb>xRjp)9=TkbmHVAgm7-9epKg5j3ih{'
    'F-#<@oZS4z&ZdY`J9yp`<T5?0$Ars+n{4!~oQHTs?Ve|S#P32yl;?tq-a<%}nDq5d;&nbcd?6$XEcE(L_H=6J*F?cS;+WIVSD#vd'
    'rl=c3xtZ9gTY1sSJf>j<3PxJngB4R1&l6u~uKx7nvZk2EkXGiYx;zhaT0&=G%a?YU&Cb~g2hzDQBBeDSrsc{eVhlVwEJ|!flg)io'
    '7T-yv^#*Kp&j<ixUmy$yNkvvF`(lqmovO20R5C|oURxzSiSE?S!~CJIJRPf(A?mhb0|k52e0Ung?F=Z`s9kIj1AnPHLB|=fzxfbg'
    'gZzu<@g))k47>JtC>?QraK9hqp3LnF76D-#c|8+4+Ej504ulWA(G;iFf~7Vtt*bc62BVvCGTO$|iS^mW>l7S_v&ve9&<`z1>=ixC'
    'nM_M)P{$(fC1H~UHr2Naj8@b@Zco-U$kA!(V#`yC7#OTFv&8LHWLb@*)&~|Th8trvO4dfACH@dP2AL^61yLJ<{F-JDJc@curh|>L'
    '!<x3qzlkCHy#u31(NVn<R%kZQo>=PIF@SOG8>_)&A=ztK#B9?|Jur?v$kxNyC-*)e#J1$fEH~mo7vQ{?a1;vtEIgw&5n#z3$ZWqV'
    '2c^410h)iw$^!$50({xr+UwFnqUrU*zz{OSr_!ZRT2Pnz`3bZCZGPz|?0DkGLfcHVwe;_+vu?v11H~0E=6Hmm9UCzO#*5_z(rfGD'
    '4t!xaCr5l8owiP{t2JKO6TGRE*+cN=3GxtQ=mL$iIo?I1(}u3twnscz0SWXKggOIo1*;zH>D4|1+Mix+cLHsn>Im99I}xT&M(&|Q'
    '@=G28Xv8`qFrc6~(|dvB-LW(EY?nnbUWI5->^8M+zn9Wgp@E!qn!Fe6bz08$&9%R<4vMhJYeDuo!*IlFBc`Pxr-aY;7*4)rys?Uc'
    'UtlY{a5xSy)ISlkn~J8;Zf7^J9Tg;Gt@C@iu!8D21`lP}9WtvoX6He9T?^tW6k>kCZ1v4`-wQjeT6*0xTdex_M{B`HH4~I+ug7K2'
    '6B1h2P#u!0Ye-RSXC^RTuN`k~-6U1l>p*Uz<GAAMZP7%N&6At=D`x>Aj?-&uuo<ZBdQTx|g{ce|!$Oa47Bfcn7cAqb_Gy~h%~FL~'
    '8VxhSQq`G!4@xTMgX}aEgfs+PI+Z-51eeTNj7OukMPkhMb^JDn)I{wpQpum-bW*bksUyMFR9p13ICo@+-7(vX&8jou_R^v!EmKsH'
    'o3)QhQV}!V0^LE(r26Ir9~~r2ZH4f>E6N88l}gYDOiD!V=MjNtE{2#oYmken5RC}NB~{fU7XvJN(+E2-AmJM1O6nzOa17ZlP(lVB'
    '4f(`Sexc6|h9r<MSR+K`LE}fvexcRCz*}`C5uV?;*di#m;~Q1Hw9YhI^&~>|2xuqOQ5pAC!Bf_z8MRaNBNXyQA+rE|uR~MSh}p|a'
    '`o79YHklN2IjmRP7uE21XD1`l;$m582PGHAn~P<kgGHFVHs3G&i0rKE#8wSK!X_fHjHZt6I#!|(TRHK3NM(vutfNSrc?Opj^A$6g'
    'QkdPxjna!u9wd3*d^*k&bj^Fc60i*ir8B7&UHc$^m^|aA(>?Vl66)~#daw^bOqiIR2R?N|SE{ocq6BqBM*a;%7S+o~fi<23>`4f2'
    '3JBp=W&k`T*J-l*sT|$gokcXBD6l=wTS^RL0dl77h@g^TN8t_iBJP#q5mI!5c{H!HhAQVfhTq9p18d_6;&&$aU=L#F_h|!1o;DL@'
    'imJYDxw-Yk>oJT_yd<`~ZlJ>=r8x*0DGvl936szs2u$W>CnIb1fc<oO9$;?jG9s4rIop9UgZ<NNpA{G?B4FoX&lF1tOca`fp@<L_'
    '5rg);Gk`=z1kB4E^e!xj7<4waXh>KPLA%sLIXwy@20fuJQW>usp`GiVe2;>N0Zv4>n|l;QxZS)~U?_-y&AoaKLKGH6z&6jC+))uR'
    'Sa&-0yIv779#-?N%9$&e-Z!l~#?qxq(W43no``MyVtMfj9(XJ(ulB;87&&Gy-A8yz!<&~6cE!HI8sqLLowo6Uz&hw<GO$PK+_IRa'
    'tQ%?+vC++WH3Ts9j0$u2xw+w~8-WBIFgx#uZp4c}rWi^!oI_FH!(JjOJ76eJ)8~o@F41$5gUzQ<PIwO1N@{Mqg5g9$-EE#83Wf+~'
    'c{c7$?WyYCdkIVu)GRH5;j#7ckeraJ(nHIT-qZJW4`?f@70V3iYsBA**E@C=gjUAsq7J#!`0(hEy`HA;E67_h#^*IgXC+^ut4><0'
    '!El!O)?K>*y4wkXH`F2fYh$o+T|`YJZ(^Xb<s9Tqj6hTAe(am5X(~+i1q1ij&C@g$=?P2^8xiBq#-qx2!C<Gb1tJ2)ShadOj-#na'
    'kJi9I!gz}N>s}WVjU!^#iZwM^7?Ikw^sa0`EYK$z&?R}u$C_SwdX_r^=IuO}ZwrV7HnkDP_HhN}yQCHoA7)5Uzd<Va=^;Vg2ngdR'
    'MZ0ykPAmU{oPC~gYHu$^#u*$0Z>SC!ZM@QnvIm8=$16-dq%O-G$8`Se2Rm<dxWerHQsF=+E_R5~xcuy3e{c3xg3z?EhCSBb3|GW}'
    'q~h`g%eDZ=(3Dp0=<|@2Ft4p{pb*31Hl0=2p-RSuDOTYZMuyz?m0*SS=Ktpxo`!=#b86<-IKkxxL-z9~1_`n~?UUT$9tdizF&q-_'
    'H)9kYLAHHs2y4*#xYuDM!|(MP>F|45BOMNYP9_o12M&z!sXp&5A@bo@<T}#fcjS6V#^E(~Y&7!dyXyakR2=+mdpZNZ09NsPpN!1>'
    'y`K(Rphym!ZTGq1XLlYT6zQI7Kw*3rMjeki4(Gz4;fruFG+w+v<{2pV*bQB4XLX%-zHv~Svh6!B8HUpx3Xg(_I}|?XbPW%MCnq)^'
    '(!NHl8R{L?u~bk7fH*aT=>tRk@D-;X^v<vxpExz_M6!({C=CW%$7V%YB!be@9VTL)5iZENI@FgZlanW5hXkJ)R#pw{kXAjgCe`*E'
    'JL-63BkIh5ho0P!NWAC7bKbAjjmpIx-<N&qu@W-w#diw?hj*o|9h=G(2j<pO8Q+ci;j<f!r_Okg>^&2+PvsgIt1q7TE+Tb<meCX6'
    '9U=We>nly&Nh941jI`!m);AWl(j$ozANJkwXb3S6$41x|k-sc6F!WF!tfP~)Ys0s5rY|>1Wuvg)yNo*=3%jb&Bz?lM#Av!c;n;@*'
    '5KfU3pFSAMXmU^!l2DMQyHC&yiYROF5OM<(i(Np4Wc%&DkU`Y(`Yw3aX}!J+%&GEsgZU6IB*imPF&R*+-r3Zpn9OkMs$t%{vNuk1'
    'pNHZ7eflF|+@%u^D0@?Ur(oWsx7eps=exOwILIPvfov?Z7~sgu+&t!9=l7Lb!h9SVRYhTL9&-=jm&w*`nRX53LZ7fBWwTWTk8#23'
    'x;^^3pRn;{?jfi$*;TJEvpdfW|89ij<?=N~m?`2C2rNf9mwSbuY5VmcW|P(}QMThEP|#tB1!pJ<J_@i17~WVZUX|F{AX`<GnClIp'
    'peY<#U6@(O)xTh69qv-UkBffu+%Ez|C0>`Fi;H`|pB~H$H5`CU3mb8%lG`<wSLN#&@uxu6&2X=_B>}wN-vVD~yVyMAJzrJ1XFfEV'
    'koT;KK%Hh6{bU66M6Y*dVbIv$v-M%>KT|(Q@ox+MqSkkpXpk0{(MwtDJ$UrRmp}`i`UMx2C^#LaQxsETOeVaYZ=^gPQ{kAPUyUH_'
    'MZX%cT3Nq4Ie{{zV2@|#HSN3AH`glS!D1{R29lgcwzvM`Uu`6+o$@lNq0YK_NGslKt4-pHfg$qHq^@{xM4{Vo?N^O5$@SjonzTf3'
    'h{SiXL;7~xnC56N=;^gRSF*7&>(=@}475HKL&wP`=5^VTLi$AIfFCa2a&R?@5L2^9G>XI?%JxY#ALyK`WQK;zAk|xx#zVQRu|~dz'
    'r!Yx*Ojhe6i$LuK49r$p1Z2r+jH5CJFiv-YRKsP#wCz161&K;oN#0%n3*5u8h<;VXG0EWFmaHy&uy>QmC~VW@z~|x>zC%q|cZbE0'
    'h#LvRC2u-tG`4&44E5ImqkJbY+Mxb9s(cDVgB>u6fjU-c@n4gBsB`jO1OqGq^KQc!lJdLTFvcnVm-vQbUi|Oc8;-EO@)Oz{!o2wZ'
    '5x*Fx`d`Tp$5j3Q><c5R|4GT^N&lgq%THuK9D{=CC(<7dQRnm)4jEDXPXZ8U3>i`Vf9--JD*Z`S;u=~H_UyeQD*f9-xO^}V`sdfR'
    'ID5JTsZWOi^11VME1lf>aVu(AKnbdR&(qidliiygZY)wE<Mc_`W|5r;;*2N~bKZAy1|E$A#XHT;3qp{7IyvEak)2BNQ!mY%JxKf8'
    '%QY)NA}mSwGkI`AC+8GAlMGnb%JZp+AbBcv-V-(g=l8_!Y&G5bHnrF&axSc+LJ(2%>U39Up>)>R?0zpOm?&o8YAr4->Dz1}#vvXo'
    '@mN}*jj?-YV852}WhxEzQWBe<JttPZ2Z8c=j<v?l9;xiTu+ty#T>A6}oS#q>=DHCCVUm+(oZH3LI#b+;KdM{BHQ$fwA(D~ry=X9P'
    'H0J#iC`~W(^{l{VZR3TZx@69EU#dXD>+V<(Q)AEvxB{-i`oS);b=TFOcX-v+pLc!L)t@;rK#$pSzvs?i)ls=-;#F0D=Id2fKPYp#'
    'rei&3taoDJ!Iro7VMz>>$l>{&P6i8XPVZb`96<|_&0d3rLu=e?*lSyA{(?nHB6dJPJNe6rE#XQ@43;l?(LcI5s<6RN1(WBH+8#YZ'
    'I2n$yh5c?97}5Q7wF?Xh?%nMIsDH9uY_R0ti3NtV>^^?uK6Eh0+|>=`Rpb{YDtdY2F5eQBSinL`Fe<h_;}IMTho0`Vx*|~kh8Dgz'
    '<O~esQN|uzYn2sLIo=Lx8pm?4TSNeZ8W)*WReYVo*f4Y02ZjVA>6|Ya1(J;XjEBr%kd!R*QXH|mlf<^9%V8hVmIMZ_ydn%MfUi*m'
    '%oyW=qv)!$8d98mP3<$tv{Xhu_w3XCOcZGbzNSj_{amv`!pWa;$@nHQtzNSNb$ks?u)d+Y6mCMm$IH)}8f_8hDc)<seny9=i2aGx'
    '228o5FIYpi=XEXBcQPkvbCYUD!4vMTdh`SsG$}sgAum7#t95_fsXB)ZewOt7<KaS>@Ex1KwCPn~ll*+#+CqdE5RTh>X#=zK)VF}`'
    'HP?)36_2rmhHb>YKI759MU2dhkom$8OM@uZcr<aJfx5mglN^j$PDWGpw62Em^f@8Y$At5ff}QN~>FZ9_&M5B!mR#8O!3qT~^|=bx'
    'IbwEN#7|U4w<-d*JO%JF%3dBA5*HR*SYT?8M=g?51;rn4jO{e9Ytc-~BZN&nyS*?_pS!n(@3T$k)z&t7bYiG7wkw|)31!Zc*zni_'
    'rl>6gLaCQ{LuyTv$0Dpj^iCd&CILf(&p|t-(#{{qGJ4PchQO*b+dcaro4{gQVLq0axa|hhJ%t#v4BCDZ>Ll*pkR0tNoG0z(X4vq_'
    '*uw1?#b#+RB(En%mFjFhP;3bo2GSEo<s_bjt$lM35xs@ZuF(pkceBgzrxjWD-Lg0&_{~_|9O3wQ-!rpMI~*kMdyd4FV}&dxSLx$}'
    'p$a|k{<?OdmEiRgh{)7q3abU%6|7&-@D!aaX7A|6Kb*{ckn{~zTTg|`kT58*<bCu*0;05DyEEzxX}I4NFM|}xt6z07I(dmia!w~N'
    'ZEK_wH10Th8D5K&kdEG~7AH<#_6Dm*Ax>Tz{<VcOL`7h_2hxEX5)K9iMhIOyy~ml`RMQ<(hL~<i%Hf2q=~bS)D~ZMEl$ZCxqSb6n'
    '-s1dJgA(Joqxa5F7R2MHoS`U+8f<n+`K}rr?AO@DLg9xPy@97_3!R1D;`|hMJs64fw^r5g7H7%De!;-cmA_nDy6X)dtUa9m=U&=F'
    '{eSKmeyu(DjOT^nNWSP?Ut<72SxoptI?+_qoFj}g3PoSySZC;)w2t+L*oEH6V)lNM;A?1#3rSI$(Y+n^s!t3+J;g-x3Dii1c06%T'
    'Gz9#*%$k^xA-s3b+YsKn=XVJ2-Rl4pk24&0u9i!a?W{fUT2!yoJZrR3I4IVw?^2h>+u5ZqDLD5;5LHFyWa#TM30pz27@Ho8-G;{i'
    'y-++H5XJzDeDla;Hr9RjdZ%bT7B!U0W!cpyxS5oB+zh@l2G*5Tu25$BgrJ<_Vgv2bAt-mJ+An!Y_>s%iC1L616G3!Bx?m>kZ2NY$'
    '!U{g8JAir--bJO{r#^jSQKC_=l9vb<*Q<mk!q4^T%{*ahlu&msFFxVydR6X3DyLo*K1$`(r>p4%$LrJ8bb{#hN%@{sPJL3o2+CIs'
    'D0SSNY!w)K&OWRdPi5XAe)O!Y-TR%&sZYB2qzq7jZdOQ+^bSI|>iSelVw(+zdiLETA>~<$i&*GnGtlaxs;5YL)F*#@k|R-Ce<xAU'
    'n+;(=<ytz-Zj|p=<v1e$QlA7eGdHk0>&YNTG6#+A%MW1iK!CA|#7e%)+)!=a7tJb1Fjt{Jf7TGJ<9Yh=W`9Z8Z8#_O$uf5?Pt4Bb'
    'f(BldxsVn8)Tb+{Gd|JC7p1PGj?yuZRfrS8%R?7@qEApK2t!Pu?8AACCI`5YB(9o1l<Ir<1V4orr84aI6-yxey)IQL?EM3HAKkxg'
    'sBgcsdt~!R$<1(=?bdYIdrx_<VIbn!SG90`I=oI%F=!IR+}F9W_^Tmx!V$mSd=1SEt$i0W2PMK?^o+Nk-DYONG{tJK8F8?JdupOr'
    'Pb8!FITw#1>}gLw#nC?1<9CI1?^b$Ui=f=7<As5mq=#Uyp6zK@ea7IbG&^JU^sAmBecDw|0d{@bRZjtSecDw!BW_L&I=c1*VCYV+'
    'SG^po@3+&1))X?v3&KyIXvw@QwSmn;h;O@WC1uzt@ngco9Fgchy-K?4RcltzBIDFzwq*`oTEIqqGv%Jz?~76QOwvk9tP%y`9WAzG'
    'o=pcr<@=Rw!kphy54KM)eceR850hbg3W9k?$n2X|0+RqRwcZ`u!DCFV_b-@vA)cxv1K1#jA}i^=IUnT3fqbgd!GYXV=wH#svUqYA'
    '@J%>o&z*?XmP0?TvA3Bb*lX!pn`PZac0FE7XnP)!67$mgED#5z#Ju)FVB<@2F^b|Zx-nqvZI138$>34Sj%r9HB>oP@_8rH}{iu%3'
    '6ta3w*m=>7og({-ZtN7<-#X<DkGtlb4eLP^dS%1lloSM3LW}-|p=N$%Jug<+b|ciuXgsAdXdv1!`Was_Ni(svyfwI!T;^q~MqAiz'
    't9EkLq;=b>K3iJ5ZPm_l_&#o16*FxxnRaZ|&R*iwZeumJ{x{T6y2f9~&c4o8BCvvANxe>?WmgqeR`0Y~Tv@&I3r|vy_lCH@mDIyC'
    'q?XDn+0Wu0cN-$9cVnQR>{`s3UI?}%=TkiU1+Wp@1sXhA#?bc&xsNqSY4*a{OT<gFL>`Z#{elIy#!KWK{Q<H!)k}118Dpa^C>*<Q'
    '`KY`<n!oBVy7hf=R;A&k5>gB9w5jK<DSSbZ=j<fhbMGn=o$xCYDps#V=jl+2KCio@DEhqa!!`Q6?n5~GyzY)7iVDe6jRTS@8L}JB'
    'gOT7cza9hbKnrb}HX!yIYVT4jDNO9UD7;#^Y<fDWU3Js4asO|QnL*p{PBSV*xI_vSfr=Nc^iT^yi8Z%SRzj!Hr-1azC;kya6U!&r'
    'mUv5i4P9&~59``Y(n>_wMyMU>`yPTpmsna#6HA=KFp6MMT4;rahdpM?pXh75v5V{v*LD=f#&o#vIi^FXLV=wp8qC!A=Q<af4#F_e'
    'KQSHDNa!LKnhv32v79K6(?Qx39qv@vJZfLuJM(j}YV>`TrLmX}OWFbxC0xm$t&JO@xQwd+xdwLjky<&ly}0Y#lM0*DL=Pq~X#<7g'
    '`NyY?)E=k+OlWy^Uz2w5>t_S&kG?XuNjPlLP$-ObyH_j+oBgJeM<R_+4h&rGS78}tyWx#L^=FNZR79FN<?##Xq5Xt?rzX^e(x9;K'
    'gy9tXgng%`Rw${l@*tGv5CUYbJcCj*ht>p6*-zMfj-`T(AHJ_d-z-Xr`4B}yzUaeU)%zp8!k>uEvOAQ8D94<c^RtGcEL>M~ym!`K'
    'j%fa+E+bWs=8=YU45h!dOTEGldv6<sT~uBeLvnF1r57h{r1j}oLal5ZCLtraJ(>rFZOKnor0YI$bgHkJ4YFOKgT~{sd&4bGE74<n'
    'X~R?Q(cpowkl`r{c`!^9kNr0?p;eC43<*J4e8|OxkK_E<=<FgC!k74F@3)OkRYKXDT%#)$cBZqIW}1NGg^`}J#Mcc4Gig9eC%Cd{'
    'R+fWfi`v20P7yK^pYV=EI)jKZ-;Pvw>XsHUZ2lxs5HcEhqjQXCRa?j>4ENB4rJU{ya}^I3)rkA<U}uqq&vf<v9$k-XK*Qbo#BnOj'
    'j-7VDpUSGIvhTh3(T9EJqAN6~c~7WHb}=<)KbRR_KJkh|Plpi&Sm`YY1Zb69Plk1zec)r4Ay%9lHp*AY*D`%d#WF(_%DhlMuGza)'
    '+${EBPF)+z7L+J993H72E>A$_l#+dW&o0dxk*SX?06}Cwp<<e-Xqsz`f5N4G(JDM!8A4Mecj8v&z4P$bk*mA6L2~t}*opy*o95&G'
    '-4c`x&nA6XL$1x-x&OSXH#YslLUJ7r2lF8Oyh%-9NQk%eke^VhY6b0^lcZ3qYQ#?nL!?i`7o;nVMcaoC(6Mn$-9zGnL#%tj$%7$c'
    ')k?ofVcI2G9IP2nT)J|PE8~t!AGVU%U~giMcBGVp(xY8^%NIsI2we%yU3#N^2dl{d?;gF@?3NGSMUuaZG~NAr8k6`MxrHOCaYEG?'
    '5t3%pxNkEkK0pH2m=EuocMW-P#{#kk?fh7f(e0ork1|qVjaFZx#^JbE=dC1iVfI5Q-%Iuu6Nx2zD-XqzeUyiSbcssaGvu9nk^)N*'
    '`2j)?>c#S2NzM%kmWyaGIH9g^54Iv#bUFQNgrK)b&XAIBCaU1+x(Ta-r|TxR3ZAY@Tm_U|eFuA-(_~#SutTSHg~}@X)yup?YKNYy'
    'KHZy->d%03$&ne#+h$>XTDqQFzNjJN$)0{-j1wATKfWi&rFvlq;d*81d9j#$sRo~xULuGvbKfy3urd)<AD$&X6Q#1-D&8Y`vSP8^'
    'bXo{{X0Lg9e&XWuJeUe8Ue~@T!2BmJ1~74AUE$oriFJj2v15ZpomeZub(K7q@kEg^7HESZmTGV{*|fv}AVODz&9b@lQDWD*mU@B2'
    '2DKS%$%-I|8HO(yGYqe53xX+izkUNExP8pmy@)*bzGVfdUyl|X!1oY1dGJXq9D?C1`4C_G(eDVN+-}^CV|Ld2J3Q2GXx#!}&QlT5'
    'vDZ`q^Zxw;#}P>dY}wW2dJdH`Fo>t#)XX@IN;`zrsKNj=T}AK^J>%@nUY--#gimmgiaVRdV)f}sEK#LbAIiSss+;3ZP!+bQ%yK8P'
    '3X9Z`XhBDh3#yi=A-oc3g{>s>m5?jU<&Aq?7pC$i(|gg<S(u~q&xI6rVUBJvL_fBde3huvbeT72WLJfAW%*+;+_SRp6C97?(5HES'
    'DRqHszrs|+PMN$lHxyJHE0P+p72X+TPtCn5NYb<>$T_#g1ASlESfEf|-_I31`s+T>WCD_<`+o648Ba%;(@PRdbgJINBo6I6t6Idh'
    'eP>mRIJxhvY7uw$omDNO{dm1aP~ziMzcMYQKyY`AJ0tU8Pr9_QNTU%WZERq$YA_q8b4M5ksx8huGx~g5989EOjx|JJu>Ex3VGi_c'
    'rv*DOUzzICZmh7~w2$jjWZSxTr5=dwp|#xiQ65t32SbeD+=xF{c}TY(tb2>WJx=AR1uo>n!|x&y?4_!OUNRJc5C``-WI-wiC8Gs7'
    'WS>3=0M##unTY<OGD97NZ1WCz&=hJT1@i<Gu;h>pGM_0g$GqSVLMlwj8fIH!2)K}#fRM*(p$D^39f5hTl1E6>bShE3FgQ8XQW7an'
    'R*5|^w@kAt@i9oYcZ9r-Q(A-~h+~;%eNh*WV`$GUKIp%o|Mov<QytGUKP6{am9UfYsW?0Gkr_<MUd$0ngrCe%y&DN45Fpk(e*urW'
    'faD^3A|1{>M5q!!HKZocTtRyBN}K!Bv7T^tT))uh<|p0>a$-{TvYBgJM^@*d)W1+xMy$KN60$wSir0#IoMG@<b~h?Al8U|lH#S;='
    '2D_Iucr>PG?8Gm~HapuU?<?V9qT}+7!A5x9h)slTX1w39XP>FAn*35WODa}2;lUAe2PO)DfUzFLF%}9DYfG07HrD5dCJOCYr6<0B'
    'R-uS@jvGf-v!t|akr^Vk6hT6_H!Nl7EY-4v*(>$=#EKYUP=Emjy-aE2Qc&l<J?ZJZo&r@=#V6i*S{AODPjrt84i_}YXH~U`J&udw'
    '9%YrIy{?VGd{*U*V;OvE_eg<F2)g9=NGXHB5ir+Hmm-4zh%KLzG)D#j*x}-W@;O|Jd~tEHHPKuOszoVToREaI$qkvdwClXDE$UIc'
    'f1{{J@wyc#w`K3JJa>#ObGYi*d9w19-bV5Pm~G-Eq_e4$T{0zo?u0{mN|aA>0o(cXu-bz)<f!)R+ZytzHHiGkT8Q0qD6ky44{Vh?'
    '<g!6Y!mW~`Na7D9hsUKb*Vwq;sS>AfF_^>G$hUCZgTWarIlq1ZF$@pBog@bYg`_Cy+D_e7Cbt(tJVST-P1qfssm_>}2Zb7Ipf^<<'
    'qmKl$Zb31CGMi;w6S1gbQLn4R!NBQUoam&H@*4Nc3`@LyX2F1=_gk-@84F--<aqtaP5@$MwIF0CD0PPlY)z(&j9Vd@d%5R&Q9sFR'
    '9>Of&v%lu6x>)YH4l}>1tv#}EFi+;0|28^_<wj7(seui5&unyt=0BtOz-sYy7%_||iiWDo<hkP2B8FOD-JjW>g)X33??d-z$MJNR'
    'GDSs-89>=RyV2__Hw)*dxIF90;nLCZ*dD@$37XzTO*^VwVHl)%(~dICt-686ZXD&#DGFOuHm~e7I2b=g-8jmflLx%08%K$9a4_;k'
    'q8sO~0JvUmlqCZ*bHoe((BM{*uu~W@KxO9N=h8~3!e(mw{tdNNzV1bhm9KjyoA;Wp8KlNapFt_O5}bbUo-Jyke9ad2$ql~UkT&Ve'
    'n{}TV!)u@qu^{~4oTK*7Sp+!?JgL*!ZI$VL?=5mnF;394Zl1zG31ji%zpP|5d$$(n?K~Wc8zCcC+dVgICd=f8WK(pssQw#JBt?m>'
    'D@}rS(x!an9=%jQvP!`Tx>3s4^=jdPS3jdh*DTvm9E25R1H9^~TEO8$9n_dAtQrSaK<KR5%^H>LypBq|BMSp4%{Y2kTmFU^!Tw~}'
    '7cElp$bpS77<nmx&FON7IHFj)M9f=Z#7qIm)_vWv4Q|_yGJDRtwl}7|fpK2N-fJ&_m`dfHnF2_(^&YC(jA~fl77itCewu_2b#10a'
    '9vi+>+)_(;&3$L4v&wvgCI1*JgkJUy;@v(bj~%3nqnEj)$|PZ6rT`Wl(ZNgstVm(*G09ZvBy$d(V8osrajl3f=BE=Ig+2@YL7Cc)'
    'Q`e@3aCT@IyBW#)CtzR<6~;QLk2H+Kc*U`rRVU_Hrj%Of8q4rS@x>=}jb$LS^&pEqRe4?1^b?Dk1=eI$-U{p8E>h>LLLYHIv*{zN'
    'NXX51vr_QVR7@m{9rf93j*j79iL{4ZdeQKI(t*evOr#a^lfnc`2I%^LT}fPLuzq9Cbe*s4FSxSM>zA)AG2EApx$-3I;0_J6jpZxp'
    'tP(<CS=?YOTm)<K8v|FcUHfF`4-@wrbH?ub+F<s+v0wnd?&UCrU-yh44cYOpXRFlveGS2pR?nj24Fz@-s^y2H0C5`zzw^UUKn!vC'
    'e7FY?%;VurE%Vm$7wmAfhZYYOIG8wI7{r>#k(NgYNn1@QY)pod^V3~*QnvZw|D~V|#1i4`f{XDMnaLOLJveHzdr7u(#|#W7dMHgx'
    'QD#8@Jd~yb+k-xw!~-iEW!znpb|4{iX~TmVp@8BVGnWH{$U%lh1IgNkT*t2tI#4~)T_0P$p*#u6x#xH*>=Vcy(pi4WQpppXK?rVU'
    '@0cnK4Gy=C_KMHhYFvzlZ&#s5h;*{=0CAZi<x!;47$HQHi>~y3w$KZb;3xap>O-|zqBBStniIeE;G%L`CAyZB**MYQ#+HbUGJeNs'
    'vwtGFceFE6*lk<f2$f7WIYt8HgrHF-t^|l<wCsr$7efJNW7B~JQEef0A_pYNI}YRT6WK{c!`XwWB<2Z_qpDlEP6g800S>HrEFkPW'
    'HfL-%48w*c){fkwcb-H1E_q{f*n_}UKk|(>CbfH7>c~8@-~CEUg@t{mrNZ%GT1pbYOfL+U>?7JEIZRrT%t}=+b9RBq$wZ31xk#j>'
    'S(uh$`?V4zY~ZbGzgC`xo!Ie5=`yloTi>A+58IzTfl?&%=<Uy!UxC<er7^Etl3E5E#V;e+dsiwk2oHza3W}#3bIPBi*>+zWnr-)Q'
    'gpl2RFHs|L-*ePbT#p8Sp{Dv80jm1Q+mcOvHulS=W^u~ed>LJ48qSF_n7}HL=sbDY>r&Rbc+*bKXEUW}6fs$8M`Y|W`HvXc<sf3?'
    '<d%3jk}l&l+wBb=aWi1q%lNr>cJICkZ!jXP<q~h4?A><1*-i|7jB;4?z);hsGXW9SLhj&oC#SKuw4)Q{N$kip-5GXB4(FNbt-4gi'
    'Yov7Tf@}G(N*pnza%d$^Nl<7>-y%t&Ieix=0BbEKnHMn>=Tea%(q?ewVU++j6y^z5iAV?+ocb#+^@Q*h5I-VGh!CZA<o?j#h&a+L'
    'N8Pcb9<@Bg2(fK4(m!`p3Ax}&xio%4BdI(ZKOu)yn$w@&Y3PFPp4whQn1yC=d8s>=hqv-5IhL2)kZU>KPo_L7M`gH*MKm1|Q@6*F'
    '>bYWM*buoI3v*p#hPDoyw>tT7=dHJc2ww5c{OIkJhcf5EP->JS)$Qa9g_=t91(lPEITbwRrB&pWKIKsqIC4AX5gvH31jgI)s=Goi'
    'Xde9{$B_4_N4wJNu8{XJ?@8asV+WW`_`0Je2o20x<l9GM)??-5vepoQrXq{-Iz)|7;R!oyNR=~qKk^`<|9z$U|6V_Ey6Mkr%uhRg'
    '=rY0b93zeakdaoow4nsb5~i#!!MkG3Jz9OLu!Ax`4fdF04TSKSe%J^NQ8sSoBb^bYPWfrMKeb<Oc*iXE+OJGbqNou&n2q>s_lkl?'
    'mU^5ia8En^D)mZH<~F$#V6$$hm;%QOUGUzu&9Gpi@?q_7QI4?2@JvZZZTPRYV^7R^KKbd0InO7Hf2!W6?0#X?51LQ98*v2Zjg}|n'
    '!2t7`+PHc1Q62BZ(GPF_shGbMA5Ufd<PFr2-q|Er2gRnpAOyA>r3iq9@{U;qgO|#uIubbZ>Cpo=s_Rjj_m(06oWzsPVpU<8@}sce'
    'Ya}sTDrY{Xwg-h%d$HQHXoZyMJkkWAzLt#G%?oY4LxH5$Tk=7tUuE)ThwzRo;7panUOghW{6R#CZ~23WCSUa5C+h4p@wMI2>6;~='
    'ypm(wgNL~8unq4TV=sV~tmX>+81KWn_{!0*R78m$FSfIOVz@Mcs^CJ_ied`6MrWX~OAtU>SE87Yi12U;QMv1C<tt?Wmb)&DrqQiM'
    'A+4)hfHT_DF8$5Zo_3LwKacx}D~IM3Fj|wsT#Tct4w{XdRB2_MXo}v@L1EqM`)~A%+QvRr3#O<$yVIs>!CqJ)k4t@h9S+U3Uq1nY'
    'pI)QaloD1T?qQKb++K1``5^eg>t-Y9O&nbmbq{KNJuEvxgMt5rJtBV3wU3D3^Ba$d-*YcV#qYW0N5wBj>JsrgDT_<Q@3gjoy|sJ8'
    '5->D;ke%8rs|Y4fHWPtWEUkc$-04jGrEzz*fo37+=oy9wPBEhlMPYTeVS+eaq4=H;hTXD7HYU0D6k6a;=Uoats-0#eU;qEkzAVRf'
    'SV!`|)?ySaS+eZ4Jk(Np@2v<%Nc2GieY1XvJn2aTMaD4CWj9UtAWb%M6R58eW-Ka&-cu+U*;Z@L8vfL!$$kcxA=F(QkoVSHc<W~&'
    'qqK_{@c`%2%L`z;U@CNibAy#|mD4Ocg1<A7W^>j=icUQ`aiX<qgUTdZHLv8+7|gU37~?$Wdzcd~6SW3QR&%1&qii7kCSJzcKoUQq'
    '(H2B+pav~lOv<D0>Z%BmM^8oA#T!e-+Ql0a*ZIR6OSNBEm;x}?Q;m4g=#WxA)sA^6#lIoZL$0%!UTDA^<~pnF4t*F70O@R-bDPG='
    '=1qy~ERGZ>0FtC=GXiTtsgpDk7ye?~mNlAaRjQxPcU_+R-?#==p(<wnd{VUt5Ek7CdA`ZtjI1#v5NzF*XMC7s+Y>W@8{^3uP5V)o'
    '5!zynb+9ikUEv{u&I%QNaS~4lB3)O2{?5^N!W)dci-M@-eGTs@^P5mOwYA_+2hZ=K^wfQYV59k~hvnh*{h@MAWh^6x);LLsA!lUC'
    'SZ$BHgaa`&0J7olFw{i+M>+arXh1SxThM@Hz}9H6a&t+Yo9mU~C!IB_rU?oQfLLYk*ArBeQEE0B9gvLL5QAc3Xp)K7_hOwNBUumZ'
    '5Kk+HB*ee7{!RuPSf?k04YpI;T2iu88#T8FUDN=@syScEj%m)d=$NK{^okJ)aNnO?Yujw>SYf@eWfaXw@+>QscJmYJ*Wqftc74RK'
    'slYdToEr>*V#1(I;96)2kQlOW)lysMvu9iH^<EG&8PQ8^vI$>bH`$4=r8XrwYfz<RXf3rv)Tp%7A|zJanpeqMX3f83L9?cFKImxH'
    '=Yx*dhJ4WR8j=q>X2Ig1vzOIalX#Q}yyjZE#+Dh`*VvBoSf(!-j?MeDi)nOGQ$D<Cz$qVQ3~dZrDd{b%QJd`OgDWrZvu^)WIt^r_'
    'r$%cFS*b~TW%;BIu|C$K6wYi=&8)cvJyfXs9L+$PsT+oMg{RMZE<$%KK>0&TePCzn|K6Y>8h$1;DS@x-6nB2y1+wPIyklH!F!nQ-'
    '=#r09m6hhZ<>ORkr}%xdn;b#lJY#NYE!4<jj4p4o9P(SKJafGKjtgfF81+4}TN|#>n_S&$dG61h?6Wf}cu=rotOb2Wg}!`ruB?^T'
    'o=<0pQEz%%hoJ^XZRzA4R;{fzHm9gc+BO@)Rqmj1=vwV3)VxtBN~hgwne%koMY)#ZkvPP`3_cSB^7pZ*dHy~yc}BM(9d{8Ma`BVz'
    'Sf#xAIkI<Fl|U`$*%?K#YN79K;-~6wJ`>|1h}!3w`1XIB^Q`b4cU7aR6*|AM`C&&%=jqD-(yni4o<D0#N9@&;${$gErL=mizS7v7'
    'vej1_n^T6^JK~MFjDz2HxihjM?ii$8(+PXExY7xmG2RPaVShg@vphl9W9%a~T5yFnj<WX7t-9ngxf+CHi@dEy;`nf5La#BoTdr2+'
    '_%s(o|1r5`R_jC#QW+k_LQfL=XcgmO#R~V#)tRIVW}z9$`-w?+SFK5cNvyk@V_~S}QGgES8+M`LyS3gGL^wzHYYzSE?MS*~M0mNq'
    '7@r7wsH4>DCpN#;8ddz{5Uidf{{4x~AG{?Gp_}YHQ<@ap1$a03vSz&-d`PkSqqa6MXlEGT(sVBm=cGdHQGfG*_KZBzkj2%gHSJd*'
    '!p7%~im>sC?V|kt?JmmiYoK=cyib08(98u^=_iJ>TJ!&-1O#&CaeY2pDl4pJG*a{tmAZ9*NafF~=fQ$X!yU)A9g}rvZk2E2sx=;y'
    '&%&Bl$&X=;@9o;KrbaS%SW_sOKvYYpChw{>C2`c6+s&O(2FawNE?HU_$r{;!M0&)TPusU8RQtxdRKiLMW6v2KwwgtAn>aT~T-UxG'
    'Ra*D?fQyy7!TuQs;SptH#^_vfp-p$`w{u(SQq2uUG*<p_GudU7y0nBVj&8o^VmlL;Q7U0H{ZmF+h!1PfiFOxC$58kS-T%52k+)EQ'
    'f#8Q^^R$5xV}sBWb&ncS?}tVBw2@*qW#O7?0oEjC!Oj02A90+OBqYIyDxLf+%44$CVR!h56)<{36(KU6j&$yg%bo#~$4}2QG<2-y'
    '!5CGiw}qK|hT(J;%=Wr0Ln=+I^>^|N0lz;m6m{8>Z299#$X9sASSGnHlat*ls>=)o-k4!?u@VdnJ|NF?B7#BMwPreD0hal`%&ClA'
    'CkFWYd}2_hFo=jNFXzkE-WB6m?!@fh3zL-VAvO8UxE@jo{e4(BdDTu_2^%K(+=GmIvW~a<ggImx@48HL0CWgKL0#rL#4z24Gld7w'
    '29VX|)x(+DJki3_hbvr6j1&VHUlTV>Js?IK(o}U>32mTRU5-N=X;zmr(L$P4_Dp13|B7b0OpUNr)}pJ9SXRi@yDu+4)LMaVK{;!_'
    '1h$sBJo{F{U<7RJ&~I9|e2X`jpDanfuQ!0$OugGD2B6Bj-U^+QAZP!S=W~f&UfH*@%PVzxo$T_;A_v=)HIs;w>pgIET$Sm<d-iWk'
    'yx#o!?#+YQF&ek~UgFg!1JE3MMfzNCnNIiLj|&z5;{8EyVB47P*vn1f^FC1(>AgF~gcAIc_bGYQ!k=IikAWE7^6k(hpys`OI~-#^'
    'ULcd;2_KUx)rfLTO27L|wdG&eRNlt3nDNx|PxiEoF&p15wrl-JZntZl8C%uZkQ!#s)r(5l2@UY1m9DMh*p_&xwkJZtshrI#E&Y^I'
    '5egeiV;is$K;~7S8cwMQW!4oB0VO;nD`D<;%S9+u5w5GWT!bQ;6GZ=1g~C~TZdr_BM;M<f!tMiBTi)dg1p9#PTY+G^;`&w~==IUQ'
    '6$rLJ#<v22ujOik5+^(I;e`7>W`64u>D&jQni=K!@C=*w#d1#7Dzc$zNsNiES7pX|E)XCVMJ*e~F9Lh6518nl9OD-uKK0fYaX!}('
    'mOnNzd1w86HOKzBY*ZlliPA!$l2CA|S#BtV4(p(0(g~@LJ<@m}p{epyn8tJ5=Ga`A>YIOC_j=A4j7bCg!!cFZFaf@3QzQ$gP=7N;'
    'vLFiqaHeiM5z|75Ig;&2S>&b7kt~bkv~5hvB13U?U^-yFN9IxjlX5<QEf)x=aw!03<HU;jjh*l@iT@WO|KM1Vl$5V=L4`y2Cp#A4'
    '>tPQ56AQi4{9CBGUBUlc*N_4r@8t|#&tehjN|`=ZhG(q2Fb}~j>G4V}_34SD7^OKY4a9kHDS};i8b(M&!F>QNi%_`Fsf(V-mL3;0'
    'Kv;onLXmF7`Y0vF;G9NZA%zBPLgI%v6trt2!l>o{wdD#HZFU<{nftiysESb@PURyOz2R>xTEP|Q@u=YD7&8aGp$p{nx~;Ja^}^2J'
    'zRDl8NMZAkO2_9Tq}#KudR^XA1$jHw;<rT=h6wag5VMt4;ac>RpI9N+F8_87!|kB8hbwa00Mr&)s4yl+t|F(Eqsp8@QvwPkpSLIH'
    'mcx}%O)->Y8I$~`(Q*9P5@98X?hI_FjQT)Y3sB_ty<@C&;zCPoG=+w|A?(1)aKzZiJnFX5n?HSK*3aQOq+wBPR&7BO#fY857zW~1'
    'G7fY&z&hVz-#5+U@U{`LISpUMG>KK4IJ}ieW#R$*#v&(*y*S@<KREsWXvlrIh^`n;OouDxy6$zo)a;m-V(CI65ue9p>Ez;{IpHj<'
    'm&BC4rA-WcWCsBQmz6kiVFC2Me`0eB3Haz7-d(W)ide(~vJ~4ykJtBxPH>ggWW?gIBd5vyrm8acpBOUt{Nk%{I{C#{`M@7me$m!V'
    'Y1Nuib8qpL6sPkeDpLvex$7skfjvu9rfy)*7Ft;i+(?Fi<=x)#Tel@0fXFBw1i`L@QYA5;7+A={`p?j?FY=_%PnKj0pw@zomD@ht'
    'O%&@uag=>3l#v@*N_TeyiH2{)UY6jkSAw!{>M_t|L@^lBAy%t9H1wGx5vm8)C;C<=A+_raOacwLR_mzDlYb@sb?zT=z`)5L9W-PK'
    'Rpqu7Lsfh@S)Ie}&RowxL<bYqz}3|)OWe_w=O&Kn%5w`TLeJ%H8HD-^lkcYYN%VN;ta=7#25co5<}H~iyYk#3CbVRAUUFM;!qK5n'
    '+d5)oI7f_5Zu~&!o)}1X0x)|=l}2e1Kkggz(diQ@Xh88s499hn%dS8hR~gL_8(n+VW#>$fq)`~KDl=HZs!tt?Sh5QJjrDgBK7;FG'
    'A#^s5dnam0{gK*8yk)NpxH}V|pgkJeDyCF(DoM};W~7gFgs@Q|bn6&LB6E?9&h5}ig7Ur*pw91C<6W-~Gp^P*-f%!2iV7W+mccF&'
    't7Rua<Qr@Ki7C~C=(84IhQcl0H*i=_C`$|FyQ55g2)g)LF&19HtZ;p>F(O99O$fh49jvgz75XqCNm_)};XApaON$-zsWmiNB!;t3'
    '4fqhT2qG<?%XQ5k2hjHU?cV$mJ!?Ks!CBZ^e2bZQ<O9rqxT@8cU#gpIw-&lBZsV0Zi{M~szKD0<5-{sXmZW0V@hd6Wtm9XbP{O2U'
    'Su{xl?a43SCB-hXXj3W9t#WVjx<C5AgQi)R_EsF43-L&g_X)IeNLm=pr_wml7HXAT`t3~EDv1#@AGy|gP`LiX0#u=^>g^RRVX#0L'
    'V|=y*o+LCeyHDlw7#3rHy{H=889wY#RbA>bpDlqa*!|fO>>E}#{3{Orm0QAGmrlJqf{!RzFn5j*FyJQ^?|6H2`($!hhf8B6mcFa6'
    'q(E<d&$v~pzz7J@666zenuSUgGO)EdzafKkz230r8T#ak6V}`__#ewD@g>7)Oe+G7$kL0qI8h$9_{t4PQN)y26NvVFz8Ti06YQ;g'
    '2|~hR26<*+U3;NslV=bWB0nep%Cp?dNd+kkrDG5ti)ug%e`3b2IQg%NFU)!0VC1ZduVYCZsggqwOdy~9*Z)KASCmtEVXxsB=Mc}8'
    '6xgg!zU8{TMWMLS;!M732BHoz_69R?y}VpA@Jr4$gTO<7j^v~Xz3=BpuGjtf=>y}fkaJp>uy<T8UkKCqxn&!>B`GK`M0hDKZ%f{c'
    '@3TiU%%Mc0TE8sIDSll5U;DZI&%%i=$z!dXi|yoo(y?N#(j4$MQ>weQUF;%*jI#yyx=5w`h_o>z@@yTY1TI4JEnf8_^H)%FiV6WC'
    'P^yIxrJks7#Q^t2eJcjS*X=5g%XSz!RPrP)AFwHFoR5Q&p#Pk4Y(e9_gD=69o5V3hh)P=NwLt&oI^#(92JoXSDJ9^K1Jkr)1X`YD'
    '{T4@9ODF!%{|7E6Z)2V@9yL$ofqYPO@iInh#h7~~jFwMjIh5KdMtt#57P2cl2JT<=*&$MFF3FeA9fj=WMLzU%Wsc&4vUvm6AqGQ='
    'W2@h;%967A(WvwdFDB@U>;lhz_#0H)b9`d(CN*YF?-FU=7~QdYQDLd84urivj(<#t+m&NrDn5N32tuP28<(JBJ|vjHr&~c8;xJt='
    'V)NKNzA<}!W}-jeUF#pBKf18E=PMz5*qPP66m_;_1OB;Zp8%7#aQf-ooc*zN3CSz#_6A=8!9)G|+@1*ZA6Z(q^L5pif^>;UUP*xL'
    'BXiZ!FlQtDlI3}hflN40o^Sqbl_h<?#&&1qA@dEvw5GDxI(P!fQd-l~vOakjrxcexLsoCgY~fbsnj8{cuYfp)DJID;R5GCuo^{`<'
    '&0Ui`+`=g)895Xc*=w%}7qwz(;Ib!vk#b&pclRi;km$iR^$!7=<b<TS>@_ls5+%pER=D#7lO5t8)v!?+l+(&ED~T0j_B|o)wV#YK'
    '>qZ+qQ4QWT(uKB6g<k*U@M~0z=zv7c#&544!n9_IGe+UEy*8jO*+S5ei&e&SxE}C%GLTP#zv@EpQ8#{mUm~r8D@NCzc7LurV`ueX'
    '(RH`m`@Y6JU6;VwSIV^yQmJRo?eVRFyW1{^K}(XW{=3?R8l=>C^=r|yr5(eulF(g*D4vYX&Cbso|1Y0Zq#?-~g2hoTjO$=^7Yz*c'
    '3l8V77J!C_A9Gmv`~16jF17$j#{<5vK?RBDM{ZlAEa3rwzi9fTA~qDGp^zJ~XSuAP!*Q5aE9HfmS6*ROCK)40QXl5oE*qDdemvya'
    '%GuzejSI{u<((pWXT-*kQUqzBG#F8X_Y#@)Fz-zI6d<!6=BLR(XD++_C)OYqWx8AF_%<X}Ke4&<gd>-K+JJ$m&rb*fk2T-P($GqG'
    'ytKB`li5cyzX7Ou1-WRyDTssJ=jVlnW-mP0lv+uD4AlDkbtusL^!yPaaW;?RJ%4N{p;fH<X`I0HWRB?a8-s|z5v&{Y9Z=7qu}j;='
    'VwGeYc+ZXJw({F41G1{cY^lKo$LM;qYFwk+b+1`nj#_!A2@k=a2(3Itpu>Lzv+3%IDbZMPXirwYqe0y;E#iePV|MjhN_sR{jQ-zJ'
    '+)FNjixv^g`f4dw{2Rt18Nk&l)Xaj%Wh&ttmV>q?q&p4{(zv7kno}bKKiy>(7c`+GX%L$CVKv=(SU+q!mwD~kbP{Of9)6u~f9<&#'
    'jX{4A@lprGIKu1gygsgutgw|ktBE$sPrW@;a~omx=OSXG<kFyrQth*Pg&!+X9wva-uyRGB>pxqe4q2IxPbhYzFmnJSGu&d)o;68$'
    'PSBfXv9FY|8H3~*gtW1eORy9QYey*HnR7hC%(kMgRzLJ-ED&v2!Sc2_?r1W-Wi{oZH_mNa-H=X&HEw-gle0UWBS9(-@*`t(>cf`T'
    'O3egtIOvSn8gpzW;`SOQOWJDXpHCrGb6FP`I#FVLyeovS10}w>qUp<y5JGwhA}K$ywoH`csCl6`7WL+3CwdW1eU~gni`dLkS|(jX'
    '!F_S5=R2Vv&zuydX2-CD_f8KwY=Bj7x<JfRjoqe$a(yjc$JWV(P{nOy?s;0RPqwXCjBD&SbMtN=*<FI~uB^{+vG`}Qwp4u4_I%&_'
    'qxPHB4$|Mjd${F)x7j{RDFU$(>)29?z)P7st{q0%XveD?i*qgOZ;9XAmK)<Fn@umP?rn~=t-6!h^s?$sX43)_XR~R9@ZPi8w5_@^'
    '?&@Rb?@sD`GMlzjcQ%{Gxf-=Z%z*yd<vX0Zp(uF{KiOP@E9cl87EQzAy}1Mw%30Z|n`71rmD#B~n@v{&2E%On3h4H->dt1<Xpr8I'
    '%(sfw9jFzV&8ERhN8PAlsgicEow~ExG-B^VW9g0}*~gC<W%<WTiu{Nr1N!mm=3@EWAFpny{p)cD(D02-ivDDybHoJ6>4wm7F<-j4'
    'vdhKUqgYXZ=63W@9+$m*196hwoaIe>h@qMFyiMfHlv5KvGv(C8P;HMdy}BuG_S{*#JlP5_U)XIcysd1vuP|7NHxA>mv$mSG+Z+90'
    'L~@+Fd7}Xx>Dv<dud&0Qa_Yc8dALi7y)AM-yCun1nfo)hpOELt+*e;c6G<CwJWNat?&~&v-o~!tf`6P{lMOHcY_#c4mcNiet8vHF'
    'zn7veZ9MJOt6UJKc!#C)rLsGqtz}<c<(qSHDiIs@ewZ)gVm?Pfd8My){w89|r0J#jFlU@6uBKSUiQ_OETw1v&{kGrb2Dq#)OfJuk'
    '7}*3D^3%`r{KV#PY~h0I+*kYfPi(%*8qT;rI3bx+uDW94cjn(h6LsibRtznmcIR7xpx}c8Fk=Dh!O^Mr@1sE|??jX58=K#+<u^sg'
    'N~p8u7%ghAn&15P_1j-)iP71RLNQuak_a652plH|jF9QD9F7P(HUiEjT|BhY4;yBDV)q(pkl7nhlmoT82U0u7W~P4)OFs5kL{6De'
    ';j~MAE)Q$R(Bi=VYge%uTX;RnC)u$QcH(!9{xD9|;S)JfsIoyDsq=>&rL$U|4Luxt!oGQa-1iTHv``^KvO%=Q8|8x{-3}ryLTQjl'
    'HmpEsMMIrah_`|-ndHTb74{RT0|I7)61p4wVNtUHjs)2Zh`hNUUY{87ptXH}YcOBFhEs<G{wOv|FRV_D2t_tgHt}S~HnXhI*fk`H'
    '39!w$LaNDM3w}tycl!CPUPEM0h`nW~*AQOuWwTL=tekTT96gvJ>Eij_hk7e>8w{j_&0NqkDQ_)5G1MBa&u?vvkh;hFbKsnNe?Ho7'
    '9z)?Al17Kn4GW|j5ThnxS_`meJ!b%X%ZR^|?GZvy)cpQ866)f=Jw^}%SoHa4`tC>BS|^Cj*%)XY;41~8>@CEmU#aU_xt&ic3gRB`'
    'TPKN1@MpYD0}uGHXP~&&8(t6gjm49Fehayo&r8Qjc#eRzU>(w9RCmwkVM&kM0bjslz+vkaO5}koDId4Kf@#A2wI&B9D`o$Lz~W1v'
    'T9^8KYAM0+n$LaemwZAFc2O{QQ*&bi{D{O3K>RXdG=0)-XB23jopQVS%;Fo+>;9SS<maCyqt2uUnGFUO;x#!86j9Z(!$1i}8_fiI'
    '$l+rM18qRD#5smEnt1Z#Pjv*Oh9f##h}}T|N34u1ybgjGhyix#64>cAnfjZb;os}5umd1gN&0x%qqImy?-Sd$?8^tWZ2R^d3(>&r'
    'QCeUK(%Q$j^yPW!Nd~uYAqkZmN6>7MF`C_N=hie+-I7Ct5-}}%+ro%ySZ3ZKXLpzM9S%-}cYH(h6IUlJEOQ`_e4d^|DCR%b*av|D'
    'x#8>5F9Izzqa>xwg)%ClIfA0m<s!2DY&o#*9Kv~R3|)-GlY`j9)1gLC^}O+7Z`>NzHmlf^LNj6Tzb|~^RbfgIm8<Yp`0jR5D~0Bn'
    'YiKY$QJ4v1wH(6Skz_GaZ&c2~`1R;u1U{QfB)M~J+;n*?*@%Fa*`s71f`RPOz5x-U0e8)g0}r$$?5!N37c7>mX1{?K@;FX5WkCR>'
    'p&a<|WHe?tXD-m3;H}s^R(Ht~KTHHc;Hb?BBRj;1jcQ}vn|UR$68*NZu3|ML?y|Ky_S&m22lj|vA^fKtGLVSybZu^h%#$$1W-H1;'
    'Ijt<4Ty7`Vk0`C2T(fp9u^dvpRgRCO_YP57tD>z07gvDH_a_GIxpUd)Cg_v~A7%V0r;L>ne9j)lGOm<0?7ZOYq80Uq7#uCWB-I@^'
    'aI)9yre+a!`X?rfrUAkJSfMTWST|*}hy#C^GO6qdqJCKp+>RW%him7KxaV%P3bX{Xy0}e0vS(<Kz94V;7O6}6f`|PKK0p`w87Kya'
    'kKBqbgu$ylJ;aeo4p-DrSj?1gnxck+UMWfi+0Dx0!#}Y|`7GU_)QIGtbSu)~``ogG_&$&3^u~@6E1Mhq;@1`8G9}dX4$BcJ6f6(a'
    'aXy5WZ9umOE!(HAh+>{;K5PkGL8G~=(+o=P<&JnT<Sq)c4<LY*j<B^_DJ^{|ChM&&B)(a5Tm0Ps_AC;=@>UBLIp-xo23kLL=fQ6o'
    'iaARGZ=po&sw;&?zDyHZom?Uji8mK|u93sYzqW<Q4`Z+cM@-mQ#DWQevRHFk-GjhKAAt6lz;}hqAK)#z<qOlAvD-reYJL3FbFI8g'
    '=>sEyf<>=i0I;Ot{0Fl3pPJCEQ<$B?E0^T8dx*(zs(Fq9P1LhAH$d|NpvfWQww5w?>eeIHiDXB8FnVw{<^G7K6ZiJC+;T_k#O8zl'
    'XX{v!8BWIP8G0`}21ShCx|O~m)-D%dhp^G`Y1RHFS@4Xvf^*F$b_H!9MAF~Tji)t~wcqF7Qv!_fM7axM>Y+{FKo=X*c_(9=)WI&N'
    '2nnnk=o6t5Pq9gdJ9dSVg`PHyeFeMviP;o*nbR*~(qG(u!=HkEho(ANrEc^I#J18c%Gn*XhIfKF4@WZ%JaI}mm4eY;8Q71yj5xUQ'
    'oPh1E>KglMC(JEegNxLypg<<W4Z5`c_ial8J9Rkp?}F@r@=_H-4H%&h@EBQEWyb`?jAG*zIw+qQG~yoVo77KeCr<7f9_|JGO+r38'
    '-YU_n_KgLPHOX;V%e@k>)^`54eCH$=sz&>Hx~`}yuLW=|A)19!UGZ0p>WH{3@T)4h7vO$u%I6qGW~D&<5m|+N^mF%*$SSZN-5Q4|'
    'tujXCV?7#$O+)Bikp~CLkPGdC3v@8}dDZz9-Af>v4lR%OxkiQy*ogE`vx6Mpu9}o8%S_nPptxA{Kga(&ruvvF)$^XxsE8Q(tRbv('
    '{-s9A&PA}Z?2ug~H~SNNh`I+;*Az`ctuuEFIH}PiO`azV1I!!!R#2cABGw{<>fsJ?Kia{O-qhfo0XHJR`phBYw>d^2I!li#0zC8='
    ';%^_BK$6sOw=jmBXW{;*mjVrU(((Fu%unc~8S>~Gg(95Sqd;LzD{N8E(~q(xtr!BV26d4)6ogEDWNdDSg8x@cq->}dOqv?*a?j;='
    'N0I|gE~NKdq)2wS1Sfum&mA^YG_&e(Sx(=FMmH|YeZCn=aF_!BzVw*p-gcp4Y1pDW^#p}>Y2BhPA>z(*`NcYOFSp$w@7smbo}X8}'
    'GE&Kg4#wTMO%HS?E@9nv6XGo;uAf3L?6AIV{&%ZAx75<Hxb{fvylUj;;lAN-ESjgOp}4xIZYciyJ4P!BKpi}dcyW!sR(GK0&d|6t'
    'X6Nud<qn`liL<M_?US?nyX}(|n>j@2fkBi}-NORvZl{F6<&NSNI$yLg)@9*UZ5{sX_-RmxFlZ2U=1SIv_08egSMw^k97Mai1b=vW'
    'NHJl|k`%{sjG`408x%|myV_Deu@h@bb9?eZ2Hd4ap;$l;Es+K*&;G<llVWp2ilyB0YQQ^P@g?R_-96C=?NVc-0p)$zN!OwK<?TK+'
    'G5brd9|^WZ{j(ob*y}p`XVQp?@RnA7V$_dNayb`(&*xexclxZ$JC0Z%;Zp4#mxjb8t<S@D4cWk_?^3IcvwAAErkHo~O9mbPi=CVZ'
    'mo99>TMS+jnngIq4;&+Ki~_FARhGa5;usYpcgRxC0<J`LaiazaK<j}T?ENiIHr9~TeMXE4Mv%>yEyFKJPA6so%^ZmM{QL8()ZPe{'
    'ehu-1HO1lOLb1T^by6+g<=rwEyTSNY49>hi&_Wvh9-iP4<34xTN?3j~a~<!2S`ku>vO`$fQKF5uS0`cq<Tc(Zdl1!Ka4RD=qt0$t'
    '=VNdsRE%OG>(TywLb=p?!fw%3{|FWCSh?1VNnA81QfypT(b48aS&Fe+aA+)(oH_5d#I2FqrYp`7A4?<@`~Q&tkg$IDPbaHNt#0?b'
    '4BF2<HiP?fFRs!pvDFVBne#jRz88NM?G?yTSnR~H`b59;j`3gx3&w2XxvmQ<sN0Ghx<6U4f1YBuH}}(8px`gn*oSsTb=%-L-C`->'
    'DHf86E~uY7cR~H!D*rS9Jt~o<wfw{uRn)^eYfhoqQ!0rQbJx9}KPharL8%SEP%d})(76cWWeA-jL~rXCSGrVo12*psn(gC0Ab}MT'
    '`hA`M^MC&9{{n#@Uj6'
)
