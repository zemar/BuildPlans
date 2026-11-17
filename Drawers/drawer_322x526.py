"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates five complete drawer bins in a NEW Fusion document.
Save and export the model manually in Fusion; cut the long bins in Bambu Studio.
All design inputs are mm; Fusion's internal geometry units are cm.
Brown appearance is cosmetic: select your filament in Bambu Studio.
The drawer dimensions are assumed to be clear INTERNAL dimensions.
"""

from pathlib import Path
import logging
import traceback

import adsk.core
import adsk.fusion


# Clear internal drawer dimensions, in millimeters.
DRAWER_HEIGHT = 80.0
DRAWER_WIDTH = 322.0
DRAWER_DEPTH = 526.0
TOOL_WIDTH = 114.3                  # 4.5 in

# Edit these values and rerun to generate a new revision.
TOTAL_CLEARANCE = 2.0               # Total reduction in width and depth
EDGE_CLEARANCE = TOTAL_CLEARANCE / 2 # 1 mm on each horizontal side
HEIGHT = DRAWER_HEIGHT             # Full 80 mm; no extra height clearance
FLOOR = 2.0
WALL = 2.4
BIN_GAP = 0.4                     # Between independently removable bins
CORNER_RADIUS = 5.0               # Outside plan-view corner radius
INSIDE_CORNER_RADIUS = CORNER_RADIUS - WALL
FRONT_WIDTH = 320.0                # Outside width
FRONT_DEPTH = 100.0                # Outside front-to-back depth
REAR_START = FRONT_DEPTH + BIN_GAP
REAR_DEPTH = DRAWER_DEPTH - TOTAL_CLEARANCE - REAR_START
RIGHT_LONG_WIDTH = 120.0           # Middle-right outside width
BIN_WIDTH = DRAWER_WIDTH - TOTAL_CLEARANCE - BIN_GAP - RIGHT_LONG_WIDTH
LONG_BAY_WIDTH = BIN_WIDTH - 2 * WALL
LONG_BAY_LENGTH = 250.0              # Left middle clear length
RIGHT_LONG_OUTER_LENGTH = 163.0    # Middle-right outside depth
RIGHT_LONG_BAY_WIDTH = RIGHT_LONG_WIDTH - 2 * WALL
RIGHT_LONG_BAY_LENGTH = RIGHT_LONG_OUTER_LENGTH - 2 * WALL
# Rear clear lengths are reduced to leave space for walls and bin clearance.
LONG_OUTER_LENGTH = LONG_BAY_LENGTH + 2 * WALL
SHORT_OUTER_LENGTH = REAR_DEPTH - BIN_GAP - LONG_OUTER_LENGTH
RIGHT_SHORT_OUTER_LENGTH = REAR_DEPTH - BIN_GAP - RIGHT_LONG_OUTER_LENGTH
RIGHT_SHORT_START = REAR_START + RIGHT_LONG_OUTER_LENGTH + BIN_GAP
SHORT_BAY_LENGTH = SHORT_OUTER_LENGTH - 2 * WALL
RIGHT_SHORT_BAY_LENGTH = RIGHT_SHORT_OUTER_LENGTH - 2 * WALL


def layout():
    """Five complete bins: name, inset-area X/Y, outside width and depth."""
    width = DRAWER_WIDTH - 2 * EDGE_CLEARANCE
    depth = DRAWER_DEPTH - 2 * EDGE_CLEARANCE
    assert 0 < FLOOR < HEIGHT <= DRAWER_HEIGHT
    assert WALL > 0 and EDGE_CLEARANCE >= 0 and BIN_GAP > 0
    assert LONG_BAY_WIDTH > TOOL_WIDTH and LONG_BAY_LENGTH > 0
    assert SHORT_BAY_LENGTH > 0 and RIGHT_SHORT_BAY_LENGTH > 0
    assert abs(FRONT_WIDTH - width) < 1e-8
    assert FRONT_DEPTH > 2 * WALL
    bins = [
        ('Front', 0, 0, FRONT_WIDTH, FRONT_DEPTH),
        ('Long_Left', 0, REAR_START, BIN_WIDTH, LONG_OUTER_LENGTH),
        ('Short_Left', 0, REAR_START + LONG_OUTER_LENGTH + BIN_GAP,
         BIN_WIDTH, SHORT_OUTER_LENGTH),
        # Fill the rear area with a wider left column and a 120 mm right column.
        ('Long_Right', width - RIGHT_LONG_WIDTH, REAR_START,
         RIGHT_LONG_WIDTH, RIGHT_LONG_OUTER_LENGTH),
        ('Short_Right', BIN_WIDTH + BIN_GAP, RIGHT_SHORT_START,
         RIGHT_LONG_WIDTH, RIGHT_SHORT_OUTER_LENGTH),
    ]
    for name, x, y, bin_width, length in bins:
        assert x >= 0 and y >= 0 and bin_width > 2 * WALL and length > 2 * WALL, name
        assert x + bin_width <= width + 1e-8 and y + length <= depth + 1e-8, name
    for i, first in enumerate(bins):
        _, ax, ay, aw, ad = first
        for second in bins[i + 1:]:
            _, bx, by, bw, bd = second
            assert (ax + aw <= bx or bx + bw <= ax or
                    ay + ad <= by or by + bd <= ay), (first[0], second[0])
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
    logger = logging.getLogger('drawer_322x526')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = None
    try:
        # Append across runs so failed and successful attempts can be compared.
        log_path = Path(__file__).resolve().with_suffix('.log')
        handler = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.info('=== drawer_322x526 run started; Fusion %s ===', app.version)
        logger.info('Script: %s', Path(__file__).resolve())
        logger.info('Inputs (mm): %s', {key: value for key, value in globals().items()
                                      if key.isupper()})
        width, depth, bins = layout()
        logger.info('Layout validated: width=%s depth=%s bins=%s', width, depth, bins)
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'drawer_322x526 - Brown'
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
            component.name = 'drawer_322x526_' + name
            component.attributes.add('drawer_322x526', 'Color', 'Brown')
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
            logger.info('%s solid validated: volume_cm3=%s bounds_mm=%s', name,
                        body.volume, actual_dimensions)
            body.name = component.name + '_Brown'
            if appearance:
                body.appearance = appearance
                logger.info('%s appearance applied: %s', name, body.appearance.name)
        app.activeViewport.fit()
        message = (
            'Five complete brown bins created.\n\n'
            'Drawer W x D x H: 322 x 526 x 80 mm.\n'
            'Front bin outside W x D x H: %.1f x %.1f x %.1f mm.\n'
            'Horizontal clearance: %.1f mm per side; no extra height clearance.\n'
            'Middle-right outside W x D: %.1f x %.1f mm.\n'
            'Clear lengths (mm): left long %.2f, left short %.2f;\n'
            'right middle %.2f, right rear %.2f.\n'
            'Clear widths: right bins %.1f; left bins %.1f mm.\n\n'
            'Save the design in Fusion. Export the desired bins using Save As Mesh.\n'
            'Import at 100%% scale in Bambu Studio.\n'
            'Make any needed cuts in Bambu Studio before printing.\n'
            'Choose the needed cuts and print settings in Bambu Studio.'
        ) % (FRONT_WIDTH, FRONT_DEPTH, HEIGHT, EDGE_CLEARANCE,
             RIGHT_LONG_WIDTH, RIGHT_LONG_OUTER_LENGTH,
             LONG_BAY_LENGTH, SHORT_BAY_LENGTH, RIGHT_LONG_BAY_LENGTH,
             RIGHT_SHORT_BAY_LENGTH, RIGHT_LONG_BAY_WIDTH, LONG_BAY_WIDTH)
        if warnings:
            message += '\n\n' + '\n'.join(warnings)
        message += '\n\nRun log: ' + str(log_path)
        logger.info('Run completed successfully; warnings=%s', warnings)
        ui.messageBox(message)
    except Exception:
        if handler:
            logger.exception('drawer_322x526 run failed')
        ui.messageBox('drawer_322x526 failed. Any partial model is left open for inspection.\n\n'
                      + traceback.format_exc())
    finally:
        if handler:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
