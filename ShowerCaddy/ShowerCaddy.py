"""Fusion script: sliding-joint shower caddy assembly. Inputs are mm.

Run from Fusion's Scripts and Add-Ins dialog. Creates a NEW unsaved design.
X = width, +Y = basket/front, +Z = up; glass occupies negative Y.
Width/depth/side height are external basket dimensions, including the floor.
305 mm is measured from the bottom to the UNDERSIDE of the hook bridge.
25.5 mm is the clear hook throat; hook stock adds to the outside envelope.
Edit constants and rerun to regenerate. See PRINTING.md for separate-part orientation and slicer settings.
Run only in Fusion; no external files or Python packages are needed.
"""

import math
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
# Independent arms with open T-grooves, inspired by Duschablage.3mf.
ARM_BOTTOM = 15.0
ROOT_WEB_WIDTH = 20.0
ROOT_TAPER_HEIGHT = 40.0
HOOK_BEND_RADIUS = 4.0
SOCKET_DEPTH = 12.0
SHOULDER_HEIGHT = 4.0
TONGUE_NECK = 25.0
TONGUE_HEAD = 33.0
TONGUE_STEP = 3.3
TONGUE_DEPTH = 8.0
TONGUE_TOP = SIDE_HEIGHT - 10.0
JOINT_CLEARANCE = 0.30             # Per side, not total clearance
JOINT_RADIUS = 0.40
SHOULDER_WIDTH = 39.0
SHOULDER_DEPTH = 10.0
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
    LOGGER.info('=== RUN START sliding-tongue-groove-v3 (timestamps UTC) ===')
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
                  ROOT_WEB_WIDTH, ROOT_TAPER_HEIGHT, SOCKET_DEPTH,
                  SHOULDER_HEIGHT, TONGUE_NECK, TONGUE_HEAD, TONGUE_DEPTH,
                  JOINT_CLEARANCE, JOINT_RADIUS]
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
    if not (0 < ROOT_WEB_WIDTH < ROOT_TAPER_HEIGHT
            and 2*(HOOK_WIDTH+ROOT_WEB_WIDTH) < BASKET_WIDTH
            and SIDE_HEIGHT+ROOT_TAPER_HEIGHT < bridge_z-HOOK_RETURN_DROP
            and 2*HOOK_BEND_RADIUS < HOOK_CLEARANCE
            and TONGUE_NECK+2*JOINT_CLEARANCE < TONGUE_HEAD
            and TONGUE_HEAD+2*JOINT_CLEARANCE+2*WALL_THICKNESS < HOOK_WIDTH+ROOT_WEB_WIDTH
            and 2*JOINT_RADIUS+JOINT_CLEARANCE < TONGUE_STEP < TONGUE_DEPTH-2*JOINT_RADIUS
            and SOCKET_DEPTH-TONGUE_DEPTH-JOINT_CLEARANCE >= WALL_THICKNESS
            and ARM_BOTTOM+SHOULDER_HEIGHT < TONGUE_TOP < SIDE_HEIGHT
            and TONGUE_HEAD+2*JOINT_CLEARANCE+2*JOINT_RADIUS < SHOULDER_WIDTH < HOOK_WIDTH+ROOT_WEB_WIDTH
            and TONGUE_DEPTH+JOINT_CLEARANCE+2*JOINT_RADIUS < SHOULDER_DEPTH < SOCKET_DEPTH):
        raise ValueError('Invalid reinforcement, sliding joint, or hook-bend dimensions.')
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
        box(component, side+' reinforced sliding socket', x,0,ARM_BOTTOM+SHOULDER_HEIGHT,
            x+HOOK_WIDTH+ROOT_WEB_WIDTH,SOCKET_DEPTH,h)

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


def joint_outline(center, clearance=0.0):
    """Open T section; offset each mating face by the per-side clearance.

    The neck exits the rear of the basket. The two wider longitudinal ridges
    are captured behind its lips. No horizontal teeth or friction lock.
    """
    n = TONGUE_NECK/2 + clearance
    h = TONGUE_HEAD/2 + clearance
    step = TONGUE_STEP-clearance
    depth = TONGUE_DEPTH+clearance
    return [(center-n,-1.0), (center+n,-1.0), (center+n,step),
            (center+h,step), (center+h,depth), (center-h,depth),
            (center-h,step), (center-n,step)]


def rounded_xy_profile(sketch, vertices, radius):
    """Round both convex and concave polygon vertices with tangent arcs."""
    corners = []
    for i, v in enumerate(vertices):
        prev, nxt = vertices[i-1], vertices[(i+1) % len(vertices)]
        u = (prev[0]-v[0], prev[1]-v[1])
        w = (nxt[0]-v[0], nxt[1]-v[1])
        lu, lw = math.hypot(*u), math.hypot(*w)
        u, w = (u[0]/lu,u[1]/lu), (w[0]/lw,w[1]/lw)
        if min(lu,lw) <= 2*radius:
            raise ValueError('Joint rounding exceeds a profile segment.')
        # All joint-profile corners are orthogonal.
        a = (v[0]+u[0]*radius,v[1]+u[1]*radius)
        b = (v[0]+w[0]*radius,v[1]+w[1]*radius)
        q = radius*(1-1/math.sqrt(2))
        mid = (v[0]+(u[0]+w[0])*q,v[1]+(u[1]+w[1])*q)
        corners.append((a,mid,b))
    for i, (a,mid,b) in enumerate(corners):
        sketch.sketchCurves.sketchArcs.addByThreePoints(point(*a),point(*mid),point(*b))
        sketch.sketchCurves.sketchLines.addByTwoPoints(point(*b),point(*corners[(i+1)%len(corners)][0]))


def joint_prism(component, name, vertices, z0, z1, operation):
    sketch = xy_sketch(component, z0, name)
    rounded_xy_profile(sketch, vertices, JOINT_RADIUS)
    if sketch.profiles.count != 1:
        raise RuntimeError('Expected one joint profile: '+name)
    feature = component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), distance(z1-z0), operation)
    feature.name = name
    sketch.isVisible = False
    if feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError(name+': '+feature.errorOrWarningMessage)
    LOGGER.info('DONE %s: Z=%s..%s mm; health=%s', name,z0,z1,feature.healthState)


def round_joint_edges(component):
    # Body edges were rounded before adding/cutting the joint. Only newly
    # exposed sharp edges remain; use a small radius to preserve rail fit.
    edges = adsk.core.ObjectCollection.create()
    for edge in component.bRepBodies.item(0).edges:
        if sharp_edge(edge):
            edges.add(edge)
    if edges.count:
        fillet_edges(component, edges, 0.20, 'Sliding joint edge easing',
                     tangent_chain=True)


def cut_sliding_channels(component):
    # Through channels open at both ends and at the back. The arm shoulder
    # supports the socket bottom; a closed bottom would not support gravity.
    for side, center in (('Left',(HOOK_WIDTH+ROOT_WEB_WIDTH)/2),
                         ('Right',BASKET_WIDTH-(HOOK_WIDTH+ROOT_WEB_WIDTH)/2)):
        # Open the rear wall AND floor below the socket so the seating
        # shoulder can pass through during insertion/removal, without
        # intersecting the basket in either the seated or sliding position.
        half = SHOULDER_WIDTH/2+JOINT_CLEARANCE
        joint_prism(component, side+' shoulder access notch',
                    [(center-half,-1),(center+half,-1),
                     (center+half,SHOULDER_DEPTH+JOINT_CLEARANCE),
                     (center-half,SHOULDER_DEPTH+JOINT_CLEARANCE)],
                    -1,ARM_BOTTOM+SHOULDER_HEIGHT,
                    adsk.fusion.FeatureOperations.CutFeatureOperation)
        joint_prism(component, side+' open retaining groove',
                    joint_outline(center,JOINT_CLEARANCE),
                    ARM_BOTTOM+SHOULDER_HEIGHT-1, SIDE_HEIGHT+1,
                    adsk.fusion.FeatureOperations.CutFeatureOperation)
    round_joint_edges(component)
    LOGGER.info('Joint clearance per side=%s mm; engaged length=%s mm',
                JOINT_CLEARANCE,TONGUE_TOP-ARM_BOTTOM-SHOULDER_HEIGHT)


def taper_geometry():
    """Two tangent circular arcs give a smooth 20 mm-wide, 40 mm-high taper."""
    w, h = ROOT_WEB_WIDTH, ROOT_TAPER_HEIGHT
    radius = (w*w+h*h)/(4*w)
    theta = 2*math.atan(w/h)
    return radius, theta


def make_arm_profile(component, right, bridge_z):
    y = 0.0
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
              adsk.fusion.FeatureOperations.NewBodyFeatureOperation, sketch.name.replace(' sketch',''))


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


def round_arm(component, bridge_z):
    rear_y = 0.0-HOOK_THICKNESS
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
    if inside.count != 2:
        raise RuntimeError('Expected two inside hook-bend edges, found {}'.format(inside.count))
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
        fillet_edges(component, remaining, EDGE_RADIUS, 'Arm edge rounding',
                     tangent_chain=True)


def build_arm(component, bridge_z, right):
    rear_y = -HOOK_THICKNESS
    make_arm_profile(component, right, bridge_z)
    x = BASKET_WIDTH-HOOK_WIDTH if right else 0
    side = 'Right' if right else 'Left'
    box(component, side+' hook bridge', x, rear_y-HOOK_CLEARANCE-HOOK_THICKNESS,
        bridge_z, x+HOOK_WIDTH, 0, bridge_z+HOOK_THICKNESS)
    box(component, side+' hook return', x, rear_y-HOOK_CLEARANCE-HOOK_THICKNESS,
        bridge_z-HOOK_RETURN_DROP, x+HOOK_WIDTH, rear_y-HOOK_CLEARANCE,
        bridge_z+HOOK_THICKNESS)
    round_arm(component, bridge_z)
    center = (BASKET_WIDTH-(HOOK_WIDTH+ROOT_WEB_WIDTH)/2 if right
              else (HOOK_WIDTH+ROOT_WEB_WIDTH)/2)
    join = adsk.fusion.FeatureOperations.JoinFeatureOperation
    # The shoulder bears the basket's weight. It is wider/deeper than the
    # groove, so the socket cannot slide past it. Overlap the rounded arm.
    half = SHOULDER_WIDTH/2
    joint_prism(component, side+' load bearing seating shoulder',
                [(center-half,-1),(center+half,-1),
                 (center+half,SHOULDER_DEPTH),(center-half,SHOULDER_DEPTH)],
                ARM_BOTTOM,ARM_BOTTOM+SHOULDER_HEIGHT,join)
    joint_prism(component, side+' ridged sliding tongue',joint_outline(center),
                ARM_BOTTOM+SHOULDER_HEIGHT-0.5,TONGUE_TOP,join)
    round_joint_edges(component)
    component.bRepBodies.item(0).name = side+' reinforced hook arm - Black PLA'
    component.attributes.add('ShowerCaddy','PrintWallLoops','6')
    component.attributes.add('ShowerCaddy','PrintRootInfill','100% locally; see PRINTING.md')


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
        LOGGER.info('Validation passed; bridge underside=%s mm', bridge_z)
        LOGGER.info('Creating new Fusion document')
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'Shower Caddy - Sliding Joint Assembly'
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('A Fusion design could not be created.')
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        occurrences = []
        components = []
        for name in ('01 Basket', '02 Left arm', '03 Right arm'):
            occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name = name
            occurrences.append(occurrence)
            components.append(occurrence.component)
        basket, left, right = components
        LOGGER.info('Building basket with open sliding sockets; plain front')
        build_basket(basket, bridge_z)
        round_all_edges(basket)
        cut_sliding_channels(basket)
        apply_black_pla(design, basket)
        for component, is_right in ((left,False),(right,True)):
            build_arm(component,bridge_z,is_right)
            apply_black_pla(design,component)
        for component, expected in ((basket,1),(left,1),(right,1)):
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
            'Created basket and two separate sliding hook arms. Dimensions are mm.\n'
            'Basket: 259 x 88.9 x 101.6; plain front, no artwork.\n'
            'Arms: 25 wide x 10 thick; reinforced 45 mm roots.\n'
            'Hook rise: 305; clear throat: 25.5.\n\n'
            'Slide basket grooves down over the arm tongues until seated on shoulders.\n'
            'No bolts or nuts required. Joint clearance: 0.30 mm per side.\n'
            'See PRINTING.md for orientation and a joint fit check.\n'
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
