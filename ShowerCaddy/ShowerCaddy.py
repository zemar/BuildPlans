"""Fusion script: reinforced three-component shower caddy assembly. Inputs are mm.

Run from Fusion's Scripts and Add-Ins dialog. Creates a NEW unsaved design.
X = width, +Y = basket/front, +Z = up; glass occupies negative Y.
Width/depth/side height are external basket dimensions, including the floor.
305 mm is measured from the bottom to the UNDERSIDE of the hook bridge.
25.5 mm is the clear hook throat; hook stock adds to the outside envelope.
Edit constants and rerun to regenerate. See PRINTING.md for separate-part orientation, hardware, and slicer settings.
Keep assets/panda_camel_inlay.json with the script for the four-color front inlay.
"""

import math
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
INLAY_ASSET = Path(__file__).resolve().parent / 'assets' / 'panda_camel_inlay.json'
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
    data = json.loads(INLAY_ASSET.read_text(encoding='utf-8'))
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
    LOGGER.info('Artwork asset: %s; source SHA256=%s',
                INLAY_ASSET, data.get('source_sha256', 'unknown'))
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
        load_inlay()  # Check the bundled artwork before creating a document.
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
