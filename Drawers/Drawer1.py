"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates four complete drawer bins in a NEW Fusion document.
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


# Converted from H 3 in, W 9 5/8 in, D 20 3/4 in.
DRAWER_HEIGHT = 76.2
DRAWER_WIDTH = 244.475
DRAWER_DEPTH = 527.05
TOOL_LENGTH = 355.6                 # 14 in
TOOL_WIDTH = 114.3                  # 4.5 in

# Edit these values and rerun to generate a new revision.
EDGE_CLEARANCE = 1.0                # On EACH of the four sides
HEIGHT = 65.0                      # Overall, including floor
FLOOR = 2.0
WALL = 2.4
BIN_GAP = 0.4                     # Between independently removable bins
BIN_WIDTH = (DRAWER_WIDTH - 2 * EDGE_CLEARANCE - BIN_GAP) / 2
LONG_BAY_WIDTH = BIN_WIDTH - 2 * WALL
LONG_BAY_LENGTH = 355.6             # Left: 14 inches clear
RIGHT_LONG_BAY_LENGTH = 304.8       # Right: 12 inches clear
# Rear clear lengths are reduced to leave space for walls and bin clearance.
LONG_OUTER_LENGTH = LONG_BAY_LENGTH + 2 * WALL
RIGHT_LONG_OUTER_LENGTH = RIGHT_LONG_BAY_LENGTH + 2 * WALL
SHORT_OUTER_LENGTH = DRAWER_DEPTH - 2 * EDGE_CLEARANCE - BIN_GAP - LONG_OUTER_LENGTH
RIGHT_SHORT_OUTER_LENGTH = DRAWER_DEPTH - 2 * EDGE_CLEARANCE - BIN_GAP - RIGHT_LONG_OUTER_LENGTH
SHORT_BAY_LENGTH = SHORT_OUTER_LENGTH - 2 * WALL
RIGHT_SHORT_BAY_LENGTH = RIGHT_SHORT_OUTER_LENGTH - 2 * WALL


def layout():
    """Four complete bins: name, drawer X/Y, outer length."""
    width = DRAWER_WIDTH - 2 * EDGE_CLEARANCE
    depth = DRAWER_DEPTH - 2 * EDGE_CLEARANCE
    assert 0 < FLOOR < HEIGHT < DRAWER_HEIGHT
    assert WALL > 0 and EDGE_CLEARANCE >= 0 and BIN_GAP > 0
    assert LONG_BAY_WIDTH > TOOL_WIDTH and LONG_BAY_LENGTH >= TOOL_LENGTH
    assert SHORT_BAY_LENGTH > 0 and RIGHT_SHORT_BAY_LENGTH > 0
    bins = []
    for side, x, total, short in (
            ('Left', 0, LONG_OUTER_LENGTH, SHORT_OUTER_LENGTH),
            ('Right', BIN_WIDTH + BIN_GAP, RIGHT_LONG_OUTER_LENGTH, RIGHT_SHORT_OUTER_LENGTH)):
        bins.extend([
            ('Long_' + side, x, 0, total),
            ('Short_' + side, x, total + BIN_GAP, short),
        ])
    for name, x, y, length in bins:
        assert x + BIN_WIDTH <= width + 1e-8 and y + length <= depth + 1e-8
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
    logger = logging.getLogger('Drawer1')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = None
    try:
        # Append across runs so failed and successful attempts can be compared.
        log_path = Path(__file__).resolve().with_suffix('.log')
        handler = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
        logger.info('=== Drawer1 run started; Fusion %s ===', app.version)
        logger.info('Script: %s', Path(__file__).resolve())
        logger.info('Inputs (mm): %s', {key: value for key, value in globals().items()
                                      if key.isupper()})
        width, depth, bins = layout()
        logger.info('Layout validated: width=%s depth=%s bins=%s', width, depth, bins)
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = 'Drawer1 - Brown'
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

        for name, x, y, length in bins:
            logger.info('Building %s: width=%s depth=%s height=%s',
                        name, BIN_WIDTH, length, HEIGHT)
            # Local component geometry begins at (0,0,0) for individual exports.
            # Occurrence translation presents the four bins in their drawer positions.
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(x / 10.0, y / 10.0, 0)
            occurrence = root.occurrences.addNewComponent(transform)
            component = occurrence.component
            component.name = 'Drawer1_' + name
            component.attributes.add('Drawer1', 'Color', 'Brown')
            extrude_rectangle(component, component.xYConstructionPlane,
                              (0, 0, BIN_WIDTH, length), FLOOR, 'Floor')
            plane_input = component.constructionPlanes.createInput()
            plane_input.setByOffset(component.xYConstructionPlane,
                                    adsk.core.ValueInput.createByReal(FLOOR / 10.0))
            wall_plane = component.constructionPlanes.add(plane_input)
            wall_plane.name = 'Top of floor'
            # isVisible reports effective visibility and has no setter for planes.
            wall_plane.isLightBulbOn = False
            walls = [(0, 0, WALL, length),
                     (BIN_WIDTH - WALL, 0, BIN_WIDTH, length),
                     (0, 0, BIN_WIDTH, WALL),
                     (0, length - WALL, BIN_WIDTH, length)]
            for i, rectangle in enumerate(walls):
                logger.info('%s wall %s: rectangle=%s', name, i + 1, rectangle)
                extrude_rectangle(component, wall_plane, rectangle,
                                  HEIGHT - FLOOR, 'Wall %02d' % (i + 1), join=True)
            if component.bRepBodies.count != 1 or not component.bRepBodies.item(0).isSolid:
                raise RuntimeError(name + ' must be one joined solid.')
            body = component.bRepBodies.item(0)
            bounds = body.boundingBox
            logger.info('%s solid validated: volume_cm3=%s bounds_mm=%s', name,
                        body.volume, ((bounds.maxPoint.x - bounds.minPoint.x) * 10,
                                      (bounds.maxPoint.y - bounds.minPoint.y) * 10,
                                      (bounds.maxPoint.z - bounds.minPoint.z) * 10))
            body.name = component.name + '_Brown'
            if appearance:
                body.appearance = appearance
        app.activeViewport.fit()
        message = (
            'Four complete brown bins created.\n\n'
            'Clear lengths (mm): left long %.2f, left short %.2f;\n'
            'right long %.2f, right short %.2f. Clear width %.3f.\n\n'
            'Save the design in Fusion. Export the desired bins using Save As Mesh.\n'
            'Import at 100%% scale in Bambu Studio.\n'
            'Cut the long bins in Bambu Studio before printing.\n'
            'Short bins print flat; choose print settings after cutting the long bins.'
        ) % (LONG_BAY_LENGTH, SHORT_BAY_LENGTH, RIGHT_LONG_BAY_LENGTH,
             RIGHT_SHORT_BAY_LENGTH, LONG_BAY_WIDTH)
        if warnings:
            message += '\n\n' + '\n'.join(warnings)
        message += '\n\nRun log: ' + str(log_path)
        logger.info('Run completed successfully; warnings=%s', warnings)
        ui.messageBox(message)
    except Exception:
        if handler:
            logger.exception('Drawer1 run failed')
        ui.messageBox('Drawer1 failed. Any partial model is left open for inspection.\n\n'
                      + traceback.format_exc())
    finally:
        if handler:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
