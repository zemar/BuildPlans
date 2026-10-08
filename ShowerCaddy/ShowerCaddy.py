"""Fusion script: one glass-panel hanging basket. Inputs are mm.

Run from Fusion's Scripts and Add-Ins dialog. Creates a NEW unsaved design.
X = width, +Y = basket/front, +Z = up; glass occupies negative Y.
Width/depth/side height are external basket dimensions, including the floor.
305 mm is measured from the bottom to the UNDERSIDE of the hook bridge.
25.5 mm is the clear hook throat; hook stock adds to the outside envelope.
Edit constants and rerun to regenerate. Duplicate the basket in your slicer if needed.
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
HOOK_THICKNESS = 6.0
HOOK_RETURN_DROP = 30.0
MESH_OPENING = 8.0
MESH_WEB = 3.0
MESH_BORDER = 6.0
EDGE_RADIUS = 0.75                 # Horizontal rims, including drainage holes
CORNER_RADIUS = 1.0                # Vertical corners; larger than rim radius
SHELF_COUNT = 1
DISPLAY_GAP = 40.0
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
    LOGGER.info('=== RUN START (timestamps UTC) ===')
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
                  MESH_OPENING, MESH_WEB, MESH_BORDER, DISPLAY_GAP, EDGE_RADIUS, CORNER_RADIUS]
    if not all(math.isfinite(v) and v > 0 for v in dimensions):
        raise ValueError('All dimensions must be finite positive millimeters.')
    if not (2 * WALL_THICKNESS < min(BASKET_WIDTH, BASKET_DEPTH)
            and FLOOR_THICKNESS < SIDE_HEIGHT
            and WALL_THICKNESS <= HOOK_WIDTH < BASKET_WIDTH / 2
            and WALL_THICKNESS <= HOOK_THICKNESS < BASKET_DEPTH
            and MESH_BORDER >= max(WALL_THICKNESS, HOOK_THICKNESS)):
        raise ValueError('Wall, hook, floor or mesh dimensions are incompatible.')
    bridge_z = HOOK_RISE + (SIDE_HEIGHT if RISE_FROM_RIM else 0)
    if bridge_z - HOOK_RETURN_DROP <= SIDE_HEIGHT:
        raise ValueError('Hook return must end above the basket rim.')
    if not isinstance(SHELF_COUNT, int) or SHELF_COUNT < 1:
        raise ValueError('SHELF_COUNT must be a positive integer.')
    if 2 * EDGE_RADIUS >= min(WALL_THICKNESS, FLOOR_THICKNESS, MESH_WEB,
                              HOOK_THICKNESS, HOOK_WIDTH, MESH_OPENING):
        raise ValueError('EDGE_RADIUS must be less than half the smallest wall, '
                         'floor, mesh web, hook section or mesh opening.')
    if not EDGE_RADIUS < CORNER_RADIUS < min(
            WALL_THICKNESS, MESH_WEB, HOOK_THICKNESS, HOOK_WIDTH, MESH_OPENING) / 2:
        raise ValueError('CORNER_RADIUS must exceed EDGE_RADIUS and remain below '
                         'half the narrowest wall, mesh web, hook or opening.')
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

    for side, x in [('Left', 0), ('Right', w - HOOK_WIDTH)]:
        # Uprights sit within the rear corners, preserving basket width/depth.
        box(component, side + ' upright', x, 0, 0,
            x + HOOK_WIDTH, HOOK_THICKNESS, bridge_z + HOOK_THICKNESS)
        box(component, side + ' hook bridge',
            x, -HOOK_CLEARANCE - HOOK_THICKNESS, bridge_z,
            x + HOOK_WIDTH, HOOK_THICKNESS, bridge_z + HOOK_THICKNESS)
        box(component, side + ' hook return',
            x, -HOOK_CLEARANCE - HOOK_THICKNESS, bridge_z - HOOK_RETURN_DROP,
            x + HOOK_WIDTH, -HOOK_CLEARANCE, bridge_z + HOOK_THICKNESS)

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
        raise RuntimeError('Expected a single connected solid basket and hooks.')
    component.bRepBodies.item(0).name = 'Basket with twin glass hooks'
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


def fillet_edges(component, edges, radius, label):
    if edges.count == 0:
        raise RuntimeError('No edges selected for ' + label)
    LOGGER.info('START %s: edges=%s; radius=%s mm', label, edges.count, radius)
    started = time.perf_counter()
    fillets = component.features.filletFeatures
    fillet_input = fillets.createInput()
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(edges, distance(radius), False)
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



def apply_black_petg(design, component):
    """Black display finish; PETG is a fabrication note, not a simulated material."""
    LOGGER.info('START black PETG appearance')
    body = component.bRepBodies.item(0)
    component.attributes.add('ShowerCaddy', 'FabricationMaterial', 'Black PETG')
    finish = design.appearances.addByCopy(body.appearance, 'Black PETG - visual finish')
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
    LOGGER.info('DONE black PETG appearance')


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
        document.name = 'Shower Caddy - Single Basket'
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('A Fusion design could not be created.')
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        component = occurrence.component
        component.name = 'Black PETG shelf 259 x 88.9 x 101.6 mm'
        build_basket(component, bridge_z)
        round_all_edges(component)
        apply_black_petg(design, component)
        # Separate side-by-side instances: each shelf has the SAME hook height.
        for index in range(1, SHELF_COUNT):
            LOGGER.info('Creating shelf instance %s of %s', index + 1, SHELF_COUNT)
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(
                index * (BASKET_WIDTH + DISPLAY_GAP) / 10.0, 0, 0)
            root.occurrences.addExistingComponent(component, transform)
        app.activeViewport.fit()
        LOGGER.info('RUN SUCCESS: %s shelves; elapsed=%.2f seconds',
                    SHELF_COUNT, time.perf_counter() - started)
        ui.messageBox(
            'Created {} identical shelves. All dimensions are mm.\n'
            'Basket: {} wide x {} deep x {} high.\n'
            'Hook rise: {} from {} to bridge underside.\n'
            'Clear hook throat: {}. Downward return: {}.\n'
            'Overall height: {}.\n'
            'Edges rounded: rims R{} mm; vertical corners R{} mm.\n\n'
            'Save the new design when ready. Duplicate in your slicer if needed.'
            .format(SHELF_COUNT, BASKET_WIDTH, BASKET_DEPTH, SIDE_HEIGHT,
                    HOOK_RISE, 'rim' if RISE_FROM_RIM else 'bottom',
                    HOOK_CLEARANCE, HOOK_RETURN_DROP, bridge_z + HOOK_THICKNESS,
                    EDGE_RADIUS, CORNER_RADIUS) +
            '\n\nLog: ' + str(LOG_PATH))
    except Exception:
        details = traceback.format_exc()
        if log_ready:
            LOGGER.exception('RUN FAILED; elapsed=%.2f seconds', time.perf_counter() - started)
        ui.messageBox('Shower caddy creation failed:\n' + details +
                      ('\nLog: ' if log_ready else '\nCould not initialize log: ') + str(LOG_PATH))
    finally:
        close_log()
