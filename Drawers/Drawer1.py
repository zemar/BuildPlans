"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates four complete drawer bins in a NEW document, then exports four
millimeter STL files and a Fusion archive beside this script in exports/<run>.
Cut the long-bin meshes in Bambu Studio before printing.
All design inputs are mm; Fusion's internal geometry units are cm.
Brown appearance is cosmetic: select your filament in Bambu Studio.
The drawer dimensions are assumed to be clear INTERNAL dimensions.
"""

from datetime import datetime
from pathlib import Path
import logging
import math
import struct
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


def normalize_binary_stl(path):
    """Place the complete upright mesh at the origin and report its mm dimensions.

    Whole bins may exceed the printer envelope: cutting happens in Bambu Studio.
    """
    data = bytearray(path.read_bytes())
    if len(data) < 84:
        raise RuntimeError('Expected a binary STL header: ' + str(path))
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count or not count:
        raise RuntimeError('Expected a nonempty binary STL: ' + str(path))
    minimum = [float('inf')] * 3
    maximum = [-float('inf')] * 3
    for i in range(count):
        offset = 84 + i * 50
        values = list(struct.unpack_from('<12fH', data, offset))
        for j in (3, 6, 9):
            for axis in range(3):
                if not math.isfinite(values[j + axis]):
                    raise RuntimeError('Non-finite STL vertex: ' + str(path))
                minimum[axis] = min(minimum[axis], values[j + axis])
                maximum[axis] = max(maximum[axis], values[j + axis])
    for i in range(count):
        for j in (3, 6, 9):
            offset = 84 + i * 50 + j * 4
            vertex = struct.unpack_from('<3f', data, offset)
            struct.pack_into('<3f', data, offset,
                             *(vertex[k] - minimum[k] for k in range(3)))
    size = tuple(maximum[k] - minimum[k] for k in range(3))
    if any(dimension <= 0 for dimension in size):
        raise RuntimeError('STL has no solid extent: ' + str(size))
    path.write_bytes(data)
    return size


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

        output = Path(__file__).resolve().parent / 'exports' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        output.mkdir(parents=True, exist_ok=False)
        logger.info('Export directory: %s', output)
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
            # Export the native body, not its assembly-context proxy.
            options = design.exportManager.createSTLExportOptions(
                body, str(output / (component.name + '.stl')))
            options.sendToPrintUtility = False
            options.isBinaryFormat = True
            options.unitType = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            if not design.exportManager.execute(options):
                raise RuntimeError('STL export failed: ' + name)
            stl_path = output / (component.name + '.stl')
            size = normalize_binary_stl(stl_path)
            logger.info('Complete bin STL exported: %s; bounds_mm=%s; cut before printing=%s',
                        stl_path, size, name.startswith('Long_'))

        archive = design.exportManager.createFusionArchiveExportOptions(
            str(output / 'Drawer1.f3d'), root)
        if not design.exportManager.execute(archive):
            raise RuntimeError('Fusion archive export failed.')
        logger.info('Fusion archive exported: %s', output / 'Drawer1.f3d')
        app.activeViewport.fit()
        message = (
            'Four complete brown bins created.\n\n'
            'Clear lengths (mm): left long %.2f, left short %.2f;\n'
            'right long %.2f, right short %.2f. Clear width %.3f.\n\n'
            'Four STL files and Fusion archive exported to:\n%s\n\n'
            'Import at 100%% scale in Bambu Studio.\n'
            'Cut the long bins in Bambu Studio before printing.\n'
            'Short bins print flat; choose print settings after cutting the long bins.'
        ) % (LONG_BAY_LENGTH, SHORT_BAY_LENGTH, RIGHT_LONG_BAY_LENGTH,
             RIGHT_SHORT_BAY_LENGTH, LONG_BAY_WIDTH, output)
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
