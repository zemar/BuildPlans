"""Fusion script: one glass-panel hanging basket. Inputs are mm.

Run from Fusion's Scripts and Add-Ins dialog. Creates a NEW unsaved design.
X = width, +Y = basket/front, +Z = up; glass occupies negative Y.
Width/depth/side height are external basket dimensions, including the floor.
305 mm is measured from the bottom to the UNDERSIDE of the hook bridge.
25.5 mm is the clear hook throat; hook stock adds to the outside envelope.
Edit constants and rerun to regenerate. Duplicate the basket in your slicer if needed.
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
HOOK_THICKNESS = 6.0
HOOK_RETURN_DROP = 30.0
MESH_OPENING = 8.0
MESH_WEB = 3.0
MESH_BORDER = 6.0
EDGE_RADIUS = 0.75                 # Horizontal rims, including drainage holes
CORNER_RADIUS = 1.0                # Vertical corners; larger than rim radius
SHELF_COUNT = 1
DISPLAY_GAP = 40.0
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



def apply_black_pla(design, component):
    """Black display finish; PLA is a fabrication note, not a simulated material."""
    LOGGER.info('START black PLA appearance')
    body = component.bRepBodies.item(0)
    component.attributes.add('ShowerCaddy', 'FabricationMaterial', 'Black PLA')
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


def ring_area(ring):
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(ring, ring[1:] + ring[:1]))) / 2


def load_inlay():
    data = json.loads(INLAY_ASSET.read_text(encoding='utf-8'))
    scale = INLAY_HEIGHT / data['height_mm']
    width = data['width_mm'] * scale
    if not (0 < INLAY_DEPTH < WALL_THICKNESS - EDGE_RADIUS):
        raise ValueError('Inlay depth must leave solid backing behind the pockets.')
    if not (0 < INLAY_HEIGHT < SIDE_HEIGHT - 2 * (FLOOR_THICKNESS + CORNER_RADIUS)
            and 0 < width < BASKET_WIDTH - 2 * (WALL_THICKNESS + CORNER_RADIUS)):
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


def find_finished_basket(component, expected_inlays):
    """Resolve the basket from current component bodies, independent of feature ordering."""
    baskets = []
    inlays = []
    unknown = []
    for body in component.bRepBodies:
        role = body.attributes.itemByName('ShowerCaddy', 'BodyRole')
        role = role.value if role else None
        LOGGER.info('Finished body: name=%s; role=%s; solid=%s',
                    body.name, role, body.isSolid)
        if not body.isSolid:
            raise RuntimeError('Non-solid body after pocket cut: ' + body.name)
        if role == 'Basket':
            baskets.append(body)
        elif role == 'Inlay':
            inlays.append(body)
        else:
            unknown.append(body.name)
    if len(baskets) != 1 or len(inlays) != expected_inlays or unknown:
        raise RuntimeError('Unexpected pocket-cut bodies: {} baskets, {} inlays '
                           '(expected {}), unclassified={}'.format(
                               len(baskets), len(inlays), expected_inlays, unknown))
    return baskets[0]


def add_front_inlay(design, component):
    """Native colored solids occupy matching 0.6 mm-deep front-wall pockets.

    Outward surfaces are flush with the basket. Colored bodies remain separate
    for slicer material assignment. Negative-space details retain black PLA.
    """
    data, scale, width = load_inlay()
    LOGGER.info('Artwork asset: %s; source SHA256=%s',
                INLAY_ASSET, data.get('source_sha256', 'unknown'))
    basket = component.bRepBodies.item(0)
    basket.name = 'Basket - Black PLA'
    basket.attributes.add('ShowerCaddy', 'BodyRole', 'Basket')
    initial_measurement = measured_volume(basket)
    LOGGER.info('START front inlay: %.3f x %.3f mm; depth=%s mm; regions=%s',
                width, INLAY_HEIGHT, INLAY_DEPTH, len(data['polygons']))
    base_plane = component.xZConstructionPlane
    normal_y = base_plane.geometry.normal.y
    if abs(abs(normal_y) - 1) > 1e-8:
        raise RuntimeError('Expected XZ plane perpendicular to Y.')
    plane_input = component.constructionPlanes.createInput()
    plane_input.setByOffset(base_plane, distance(BASKET_DEPTH / normal_y))
    plane = component.constructionPlanes.add(plane_input)
    plane.name = 'Artwork on outside front wall'
    plane.isLightBulbOn = False
    finishes = {name: make_color_finish(design, basket.appearance,
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
            raise RuntimeError('Inlay sketch normal is not perpendicular to front wall.')
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
    combine_input = component.features.combineFeatures.createInput(basket, tools)
    combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    combine_input.isKeepToolBodies = True
    cut = component.features.combineFeatures.add(combine_input)
    cut.name = 'Recess artwork into front wall - keep color inlays'
    if cut.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError('Artwork pocket cut failed: ' + cut.errorOrWarningMessage)
    LOGGER.info('Pocket-cut feature reports %s bodies; component contains %s bodies',
                cut.bodies.count, component.bRepBodies.count)
    # Combine.bodies is not a target-only collection. Identify the current
    # basket by its persistent role, not feature body count or index.
    basket = find_finished_basket(component, inlay_count)
    removed = check_pocket_volume(initial_measurement, measured_volume(basket), expected_volume)
    LOGGER.info('DONE front inlay: %s colored solids; removed=%.6f cm3; remaining backing=%s mm',
                inlay_count, removed, WALL_THICKNESS - INLAY_DEPTH)


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
        document.name = 'Shower Caddy - Single Basket'
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError('A Fusion design could not be created.')
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        component = occurrence.component
        component.name = 'Black PLA shelf 259 x 88.9 x 101.6 mm'
        build_basket(component, bridge_z)
        round_all_edges(component)
        apply_black_pla(design, component)
        add_front_inlay(design, component)
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
            '\n\nFront artwork: {} mm high, {} mm-deep flush color inlays.'.format(
                INLAY_HEIGHT, INLAY_DEPTH) +
            '\nAssign White, Green, Red and Brown PLA to the named inlay bodies in your slicer.' +
            '\n\nLog: ' + str(LOG_PATH))
    except Exception:
        details = traceback.format_exc()
        if log_ready:
            LOGGER.exception('RUN FAILED; elapsed=%.2f seconds', time.perf_counter() - started)
        ui.messageBox('Shower caddy creation failed:\n' + details +
                      ('\nLog: ' if log_ready else '\nCould not initialize log: ') + str(LOG_PATH))
    finally:
        close_log()
