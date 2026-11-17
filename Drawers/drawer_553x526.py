"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates fourteen separate drawer bins in a NEW Fusion document.
Requested internal sizes are minimums, enlarged for a flush, full-drawer layout.
Ten dining-utensil bins span the front; four storage bins fill the rear.
Save and export the model manually in Fusion; check plate fit in Bambu Studio.
All design inputs are mm; Fusion's internal geometry units are cm.
Brown appearance is cosmetic: select your filament in Bambu Studio.
The drawer dimensions are assumed to be clear INTERNAL dimensions.
"""

from pathlib import Path
import logging
import math
import traceback

import adsk.core
import adsk.fusion


# Drawer and bin dimensions are millimeters; all requested sizes are INTERNAL.
DRAWER_HEIGHT = 80.0
DRAWER_WIDTH = 553.0
DRAWER_DEPTH = 526.0
TOTAL_CLEARANCE = 2.0               # Total reduction in drawer width and depth
EDGE_CLEARANCE = TOTAL_CLEARANCE / 2
HEIGHT = DRAWER_HEIGHT
FLOOR = 2.0
WALL = 2.4
BIN_GAP = 0.0                     # Separate bins touch at their outside walls
CORNER_RADIUS = 0.0              # Square outside corners fill every junction
INSIDE_CORNER_RADIUS = 2.6
EXTRA_INNER_LENGTH = 300.0

# Name, minimum internal length, minimum internal width.
REQUESTED_BINS = (
    ('Tablespoons 1', 210.0, 50.0),
    ('Tablespoons 2', 210.0, 50.0),
    ('Forks 1', 210.0, 30.0),
    ('Forks 2', 210.0, 30.0),
    ('Knives', 250.0, 70.0),
    ('Teaspoons', 160.0, 40.0),
    ('Dessert Forks', 180.0, 40.0),
    ('Serving Spoons', 240.0, 70.0),
    ('Butter Knives', 180.0, 50.0),
    ('Chopsticks', 280.0, 60.0),
    ('Serving Utensils', 280.0, 100.0),
    ('Fancy Chopsticks', 270.0, 70.0),
    ('Napkin Rings', 120.0, 120.0),
)
FRONT_BIN_NAMES = (
    'Tablespoons 1', 'Tablespoons 2', 'Forks 1', 'Forks 2', 'Knives',
    'Teaspoons', 'Dessert Forks', 'Butter Knives', 'Chopsticks', 'Fancy Chopsticks',
)
MINIMUM_SIZES = {name: (length, width) for name, length, width in REQUESTED_BINS}
USABLE_WIDTH = DRAWER_WIDTH - TOTAL_CLEARANCE
USABLE_DEPTH = DRAWER_DEPTH - TOTAL_CLEARANCE
FRONT_INNER_LENGTH = max(MINIMUM_SIZES[name][0] for name in FRONT_BIN_NAMES)
FRONT_OUTER_DEPTH = FRONT_INNER_LENGTH + 2 * WALL
FRONT_WIDTH_EXTRA = (USABLE_WIDTH - sum(MINIMUM_SIZES[name][1] + 2 * WALL
                                     for name in FRONT_BIN_NAMES)) / len(FRONT_BIN_NAMES)
REAR_OUTER_DEPTH = USABLE_DEPTH - FRONT_OUTER_DEPTH
REAR_LEFT_WIDTH = EXTRA_INNER_LENGTH + 2 * WALL
REAR_RIGHT_WIDTH = USABLE_WIDTH - REAR_LEFT_WIDTH
SERVING_UTENSILS_DEPTH = MINIMUM_SIZES['Serving Utensils'][1] + 2 * WALL
NAPKIN_RINGS_DEPTH = MINIMUM_SIZES['Napkin Rings'][1] + 2 * WALL
EXTRA_INNER_WIDTH = REAR_OUTER_DEPTH - SERVING_UTENSILS_DEPTH - 2 * WALL

# Allocated INTERNAL sizes, after expanding minimums to fill each rectangular cell.
BIN_SPECS = tuple((name, FRONT_INNER_LENGTH, MINIMUM_SIZES[name][1] + FRONT_WIDTH_EXTRA)
                  for name in FRONT_BIN_NAMES) + (
    ('Napkins', EXTRA_INNER_LENGTH, EXTRA_INNER_WIDTH),
    ('Serving Utensils', REAR_LEFT_WIDTH - 2 * WALL, SERVING_UTENSILS_DEPTH - 2 * WALL),
    ('Serving Spoons', REAR_RIGHT_WIDTH - 2 * WALL,
     REAR_OUTER_DEPTH - NAPKIN_RINGS_DEPTH - 2 * WALL),
    ('Napkin Rings', REAR_RIGHT_WIDTH - 2 * WALL, NAPKIN_RINGS_DEPTH - 2 * WALL),
)


def bin_placements():
    """X/Y in the inset usable area, and whether to rotate a bin 90 degrees."""
    placements = []
    x = 0.0
    for name in FRONT_BIN_NAMES:
        placements.append((x, 0.0, True))
        x += MINIMUM_SIZES[name][1] + FRONT_WIDTH_EXTRA + 2 * WALL
    placements.extend((
        (0.0, FRONT_OUTER_DEPTH, False),
        (0.0, USABLE_DEPTH - SERVING_UTENSILS_DEPTH, False),
        (REAR_LEFT_WIDTH, FRONT_OUTER_DEPTH, False),
        (REAR_LEFT_WIDTH, USABLE_DEPTH - NAPKIN_RINGS_DEPTH, False),
    ))
    return tuple(placements)


def layout():
    """Return separate bins as (name, inset X/Y, OUTSIDE width and depth)."""
    width = DRAWER_WIDTH - TOTAL_CLEARANCE
    depth = DRAWER_DEPTH - TOTAL_CLEARANCE
    assert 0 < FLOOR < HEIGHT <= DRAWER_HEIGHT
    assert WALL > 0 and EDGE_CLEARANCE >= 0 and BIN_GAP == 0
    assert CORNER_RADIUS == 0 and INSIDE_CORNER_RADIUS > 0
    assert FRONT_WIDTH_EXTRA >= 0 and EXTRA_INNER_WIDTH > 0
    placements = bin_placements()
    assert len(REQUESTED_BINS) == 13 and len(BIN_SPECS) == len(placements) == 14
    assert len({name for name, _, _ in BIN_SPECS}) == len(BIN_SPECS)
    allocated = {name: (length, width) for name, length, width in BIN_SPECS}
    for name, minimum_length, minimum_width in REQUESTED_BINS:
        assert allocated[name][0] >= minimum_length - 1e-7, name
        assert allocated[name][1] >= minimum_width - 1e-7, name
    bins = []
    tolerance = 1e-7
    for (name, inner_length, inner_width), (x, y, rotated) in zip(BIN_SPECS, placements):
        assert min(inner_length, inner_width) > 2 * INSIDE_CORNER_RADIUS, name
        inner_x, inner_y = ((inner_width, inner_length) if rotated
                            else (inner_length, inner_width))
        outer_width = inner_x + 2 * WALL
        outer_depth = inner_y + 2 * WALL
        assert x >= 0 and y >= 0, name
        assert x + outer_width <= width + tolerance, name
        assert y + outer_depth <= depth + tolerance, name
        bins.append((name, x, y, outer_width, outer_depth))
    for i, (name, ax, ay, aw, ad) in enumerate(bins):
        for other, bx, by, bw, bd in bins[i + 1:]:
            assert (ax + aw + BIN_GAP <= bx + tolerance or
                    bx + bw + BIN_GAP <= ax + tolerance or
                    ay + ad + BIN_GAP <= by + tolerance or
                    by + bd + BIN_GAP <= ay + tolerance), (name, other)
    # Rectangles are inside the envelope and disjoint; equal total area proves
    # that their square outside footprints fill it completely.
    assert abs(sum(w * d for _, _, _, w, d in bins) - width * depth) < 0.001
    return width, depth, bins


def point(x, y):
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, 0)


def extrude_rectangle(component, plane, rectangle, height, name, join=False):
    sketch = component.sketches.add(plane)
    sketch.name = name + ' footprint'
    x0, y0, x1, y1 = rectangle
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(point(x0, y0), point(x1, y1))
    if sketch.profiles.count != 1:
        raise RuntimeError('Expected one rectangular profile: ' + name)
    operation = (adsk.fusion.FeatureOperations.JoinFeatureOperation if join else
                 adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    feature = component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), adsk.core.ValueInput.createByReal(height / 10.0), operation)
    feature.name = name
    sketch.isVisible = False
    return feature


def round_outer_corners(component, body, bin_width, length):
    """Fillet the four outside vertical edges."""
    if CORNER_RADIUS == 0:
        return
    corners = ((0.0, 0.0), (bin_width, 0.0),
               (0.0, length), (bin_width, length))
    edges = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        bounds = edge.boundingBox
        x_span = (bounds.maxPoint.x - bounds.minPoint.x) * 10.0
        y_span = (bounds.maxPoint.y - bounds.minPoint.y) * 10.0
        z_span = (bounds.maxPoint.z - bounds.minPoint.z) * 10.0
        if x_span > 0.001 or y_span > 0.001 or z_span < HEIGHT - 0.001:
            continue
        position = (bounds.minPoint.x * 10.0, bounds.minPoint.y * 10.0)
        if any(abs(position[0] - x) < 0.001 and abs(position[1] - y) < 0.001
               for x, y in corners):
            edges.add(edge)
    if edges.count != len(corners):
        raise RuntimeError('Expected four outside corner edges; found %d' % edges.count)
    fillet_input = component.features.filletFeatures.createInput()
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
        edges, adsk.core.ValueInput.createByReal(CORNER_RADIUS / 10.0), False)
    fillet = component.features.filletFeatures.add(fillet_input)
    if not fillet or fillet.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        message = fillet.errorOrWarningMessage if fillet else 'no feature returned'
        raise RuntimeError('Outside corner fillet failed: ' + message)
    fillet.name = 'Outside corners - R%.1f mm' % CORNER_RADIUS


def round_inner_corners(component, body, bin_width, length):
    """Fillet inside vertical edges to preserve the wall thickness at corners."""
    corners = ((WALL, WALL), (bin_width - WALL, WALL),
               (WALL, length - WALL), (bin_width - WALL, length - WALL))
    edges = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        bounds = edge.boundingBox
        x_span = (bounds.maxPoint.x - bounds.minPoint.x) * 10.0
        y_span = (bounds.maxPoint.y - bounds.minPoint.y) * 10.0
        z_span = (bounds.maxPoint.z - bounds.minPoint.z) * 10.0
        if x_span > 0.001 or y_span > 0.001 or z_span < HEIGHT - FLOOR - 0.001:
            continue
        position = (bounds.minPoint.x * 10.0, bounds.minPoint.y * 10.0)
        if any(abs(position[0] - x) < 0.001 and abs(position[1] - y) < 0.001
               for x, y in corners):
            edges.add(edge)
    if edges.count != len(corners):
        raise RuntimeError('Expected four inside corner edges; found %d' % edges.count)
    fillet_input = component.features.filletFeatures.createInput()
    fillet_input.edgeSetInputs.addConstantRadiusEdgeSet(
        edges, adsk.core.ValueInput.createByReal(INSIDE_CORNER_RADIUS / 10.0), False)
    fillet = component.features.filletFeatures.add(fillet_input)
    if not fillet or fillet.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        message = fillet.errorOrWarningMessage if fillet else 'no feature returned'
        raise RuntimeError('Inside corner fillet failed: ' + message)
    fillet.name = 'Inside corners - R%.1f mm' % INSIDE_CORNER_RADIUS


def brown_appearance(app, design):
    """Use an opaque plastic appearance, compatible with older Fusion versions."""
    for library in app.materialLibraries:
        for source in library.appearances:
            if 'plastic' not in source.name.lower():
                continue
            color = adsk.core.ColorProperty.cast(
                source.appearanceProperties.itemById('opaque_albedo'))
            if color:
                appearance = design.appearances.addByCopy(source, 'Brown (visual)')
                prop = adsk.core.ColorProperty.cast(
                    appearance.appearanceProperties.itemById('opaque_albedo'))
                prop.value = adsk.core.Color.create(110, 65, 35, 255)
                return appearance
    raise RuntimeError('No editable opaque plastic appearance found in local libraries.')


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    logger = logging.getLogger('drawer_553x526')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = None
    try:
        # Append across runs so failed and successful attempts can be compared.
        log_path = Path(__file__).resolve().with_suffix('.log')
        handler = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.info('=== drawer_553x526 run started; Fusion %s ===', app.version)
        logger.info('Script: %s', Path(__file__).resolve())
        logger.info('Inputs (mm): %s', {key: value for key, value in globals().items()
                                      if key.isupper()})
        width, depth, bins = layout()
        logger.info('Layout validated: width=%s depth=%s bins=%s', width, depth, bins)
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'drawer_553x526 - Front row preview'
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        # defaultLengthUnits is read-only; use the design's writable enum setting.
        design.fusionUnitsManager.distanceDisplayUnits = (
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits)
        logger.info('Design display units: %s', design.unitsManager.defaultLengthUnits)
        root = design.rootComponent
        # Fusion controls the root component name through the document name.
        # Only child components can be renamed directly in this document.
        logger.info('Root component: %s', root.name)
        warnings = []
        try:
            appearance = brown_appearance(app, design)
        except Exception as exc:
            appearance = None
            warnings.append('Brown appearance not applied: ' + str(exc))
            logger.warning('Brown appearance unavailable', exc_info=True)

        for name, x, y, bin_width, length in bins:
            logger.info('Building %s: width=%s depth=%s height=%s',
                        name, bin_width, length, HEIGHT)
            # Local component geometry begins at (0,0,0) for individual exports.
            # Include the peripheral clearance in actual drawer coordinates.
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(
                (x + EDGE_CLEARANCE) / 10.0, (y + EDGE_CLEARANCE) / 10.0, 0)
            occurrence = root.occurrences.addNewComponent(transform)
            component = occurrence.component
            component.name = name
            component.attributes.add('drawer_553x526', 'Color', 'Brown')
            component.attributes.add('drawer_553x526', 'Contents', name)
            component.attributes.add('drawer_553x526', 'Internal size mm',
                                     '%.3f x %.3f x %.3f' %
                                     (bin_width - 2 * WALL, length - 2 * WALL, HEIGHT - FLOOR))
            extrude_rectangle(component, component.xYConstructionPlane,
                              (0, 0, bin_width, length), FLOOR, 'Floor')
            plane_input = component.constructionPlanes.createInput()
            plane_input.setByOffset(component.xYConstructionPlane,
                                    adsk.core.ValueInput.createByReal(FLOOR / 10.0))
            wall_plane = component.constructionPlanes.add(plane_input)
            wall_plane.name = 'Top of floor'
            # isVisible reports effective visibility and has no setter for planes.
            wall_plane.isLightBulbOn = False
            walls = [(0, 0, WALL, length),
                     (bin_width - WALL, 0, bin_width, length),
                     (0, 0, bin_width, WALL),
                     (0, length - WALL, bin_width, length)]
            for i, rectangle in enumerate(walls):
                logger.info('%s wall %s: rectangle=%s', name, i + 1, rectangle)
                extrude_rectangle(component, wall_plane, rectangle,
                                  HEIGHT - FLOOR, 'Wall %02d' % (i + 1), join=True)
            if component.bRepBodies.count != 1 or not component.bRepBodies.item(0).isSolid:
                raise RuntimeError(name + ' must be one joined solid.')
            body = component.bRepBodies.item(0)
            round_outer_corners(component, body, bin_width, length)
            body = component.bRepBodies.item(0)
            round_inner_corners(component, body, bin_width, length)
            body = component.bRepBodies.item(0)
            bounds = body.boundingBox
            actual_dimensions = ((bounds.maxPoint.x - bounds.minPoint.x) * 10,
                                 (bounds.maxPoint.y - bounds.minPoint.y) * 10,
                                 (bounds.maxPoint.z - bounds.minPoint.z) * 10)
            if any(abs(actual - expected) > 0.001 for actual, expected in
                   zip(actual_dimensions, (bin_width, length, HEIGHT))):
                raise RuntimeError('%s dimensions differ: expected %s, got %s' %
                                   (name, (bin_width, length, HEIGHT), actual_dimensions))
            inner_x, inner_y = bin_width - 2 * WALL, length - 2 * WALL
            outer_area = bin_width * length - (4 - math.pi) * CORNER_RADIUS ** 2
            inner_area = inner_x * inner_y - (4 - math.pi) * INSIDE_CORNER_RADIUS ** 2
            expected_volume = (outer_area * HEIGHT - inner_area * (HEIGHT - FLOOR)) / 1000
            if abs(body.volume - expected_volume) > 0.001:
                raise RuntimeError('Solid volume differs from the specified wall/floor geometry: ' + name)
            logger.info('%s solid validated: volume_cm3=%s outside_mm=%s inside_mm=%s',
                        name, body.volume, actual_dimensions, (inner_x, inner_y, HEIGHT - FLOOR))
            body.name = component.name + '_Brown'
            if appearance:
                body.appearance = appearance
                logger.info('%s appearance applied: %s', name, body.appearance.name)
        app.activeViewport.fit()
        message = (
            '%d separate brown bins created for the %.0f x %.0f x %.0f mm drawer.\n\n'
            'Requested INTERNAL sizes are minimums; bins are enlarged to fill the drawer.\n'
            'Ten dining-utensil bins run left-to-right across the front.\n'
            'Four storage bins fill the rear; square outside walls butt together.\n'
            'Napkins bin inside: %.1f x %.1f mm.\n'
            'Outside height %.1f mm; clear height %.1f mm.\n'
            'Walls %.1f mm; floor %.1f mm; gaps %.1f mm.\n'
            'Drawer clearance: %.1f mm per horizontal side.\n\n'
            'Save the design in Fusion. Select each named component for Save As Mesh.\n'
            'Import at 100%% scale in Bambu Studio and check plate/brim fit.\n'
            'Inside corners have a %.1f mm radius.'
        ) % (len(bins), DRAWER_WIDTH, DRAWER_DEPTH, DRAWER_HEIGHT,
             EXTRA_INNER_LENGTH, EXTRA_INNER_WIDTH, HEIGHT, HEIGHT - FLOOR,
             WALL, FLOOR, BIN_GAP, EDGE_CLEARANCE, INSIDE_CORNER_RADIUS)
        if warnings:
            message += '\n\n' + '\n'.join(warnings)
        message += '\n\nRun log: ' + str(log_path)
        logger.info('Run completed successfully; warnings=%s', warnings)
        ui.messageBox(message)
    except Exception:
        if handler:
            logger.exception('drawer_553x526 run failed')
        ui.messageBox('drawer_553x526 failed. Any partial model is left open for inspection.\n\n'
                      + traceback.format_exc())
    finally:
        if handler:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
