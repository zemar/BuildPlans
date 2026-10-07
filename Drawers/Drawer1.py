"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates a printable drawer organizer in a NEW document, then exports four
millimeter STL files and a Fusion archive beside this script in exports/<run>.
All design inputs are mm; Fusion's internal geometry units are cm.
Brown appearance is cosmetic: select brown PETG in Bambu Studio.
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
LONG_BAY_LENGTH = 355.6             # Exactly 14 in clear; no extra end clearance
LONG_OUTER_LENGTH = LONG_BAY_LENGTH + 2 * WALL
SHORT_OUTER_LENGTH = DRAWER_DEPTH - 2 * EDGE_CLEARANCE - BIN_GAP - LONG_OUTER_LENGTH
SHORT_BAY_LENGTH = SHORT_OUTER_LENGTH - 2 * WALL
PRINT_TILT_DEGREES = 45.0
BUILD_WIDTH = 325.0                 # H2D single-nozzle envelope
BUILD_DEPTH = 320.0
BUILD_HEIGHT = 325.0
BRIM_ALLOWANCE = 8.0                # Reserve on EACH side for fit check


def print_bounds(width, length, angle):
    radians = math.radians(angle)
    c, s = math.cos(radians), math.sin(radians)
    return width, length * c + HEIGHT * s, length * s + HEIGHT * c


def layout():
    """Four independent bins: name, drawer X/Y, outer length, print tilt."""
    width = DRAWER_WIDTH - 2 * EDGE_CLEARANCE
    depth = DRAWER_DEPTH - 2 * EDGE_CLEARANCE
    assert 0 < FLOOR < HEIGHT < DRAWER_HEIGHT
    assert WALL > 0 and EDGE_CLEARANCE >= 0 and BIN_GAP > 0
    assert LONG_BAY_WIDTH > TOOL_WIDTH and LONG_BAY_LENGTH >= TOOL_LENGTH
    assert SHORT_BAY_LENGTH > 0 and 0 <= PRINT_TILT_DEGREES <= 90
    bins = [
        ('Long_Left', 0, 0, LONG_OUTER_LENGTH, PRINT_TILT_DEGREES),
        ('Long_Right', BIN_WIDTH + BIN_GAP, 0, LONG_OUTER_LENGTH, PRINT_TILT_DEGREES),
        ('Short_Left', 0, LONG_OUTER_LENGTH + BIN_GAP, SHORT_OUTER_LENGTH, 0),
        ('Short_Right', BIN_WIDTH + BIN_GAP, LONG_OUTER_LENGTH + BIN_GAP, SHORT_OUTER_LENGTH, 0),
    ]
    for name, x, y, length, angle in bins:
        assert x + BIN_WIDTH <= width + 1e-8 and y + length <= depth + 1e-8
        px, py, pz = print_bounds(BIN_WIDTH, length, angle)
        assert px + 2 * BRIM_ALLOWANCE <= BUILD_WIDTH, name
        assert py + 2 * BRIM_ALLOWANCE <= BUILD_DEPTH, name
        assert pz <= BUILD_HEIGHT, name
    return width, depth, bins


def tilt_binary_stl(path, angle):
    """Rotate the mm STL about X, then move its minimum corner to the origin.

    Fusion's assembled CAD stays upright. Only exported print geometry is tilted.
    STL cannot enable supports; the user must enable them in the slicer.
    """
    data = bytearray(path.read_bytes())
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count or not count:
        raise RuntimeError('Expected a nonempty binary STL: ' + str(path))
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    def rotate(x, y, z):
        return x, y * c - z * s, y * s + z * c
    minimum = [float('inf')] * 3
    maximum = [-float('inf')] * 3
    for i in range(count):
        offset = 84 + i * 50
        values = list(struct.unpack_from('<12fH', data, offset))
        for j in (0, 3, 6, 9):
            values[j:j + 3] = rotate(*values[j:j + 3])
            if j:
                for axis in range(3):
                    minimum[axis] = min(minimum[axis], values[j + axis])
                    maximum[axis] = max(maximum[axis], values[j + axis])
        struct.pack_into('<12fH', data, offset, *values)
    for i in range(count):
        for j in (3, 6, 9):
            offset = 84 + i * 50 + j * 4
            vertex = struct.unpack_from('<3f', data, offset)
            struct.pack_into('<3f', data, offset,
                             *(vertex[k] - minimum[k] for k in range(3)))
    size = tuple(maximum[k] - minimum[k] for k in range(3))
    if (size[0] + 2 * BRIM_ALLOWANCE > BUILD_WIDTH + 0.001 or
            size[1] + 2 * BRIM_ALLOWANCE > BUILD_DEPTH + 0.001 or
            size[2] > BUILD_HEIGHT + 0.001):
        raise RuntimeError('Export exceeds print envelope: ' + str(size))
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
                appearance = design.appearances.addByCopy(source, 'Brown PETG (visual)')
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
        document.name = 'Drawer1 - Brown PETG'
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
        for name, x, y, length, angle in bins:
            logger.info('Building %s: width=%s depth=%s height=%s',
                        name, BIN_WIDTH, length, HEIGHT)
            # Local component geometry begins at (0,0,0) for individual exports.
            # Occurrence translation presents the four bins assembled in Fusion.
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(x / 10.0, y / 10.0, 0)
            occurrence = root.occurrences.addNewComponent(transform)
            component = occurrence.component
            component.name = 'Drawer1_' + name
            component.attributes.add('Drawer1', 'Print material', 'Brown PETG')
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
            body.name = component.name + '_Brown_PETG'
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
            size = tilt_binary_stl(stl_path, angle)
            logger.info('STL exported: %s; tilt=%s degrees; print bounds_mm=%s; supports=%s',
                        stl_path, angle, size, bool(angle))

        archive = design.exportManager.createFusionArchiveExportOptions(
            str(output / 'Drawer1.f3d'), root)
        if not design.exportManager.execute(archive):
            raise RuntimeError('Fusion archive export failed.')
        logger.info('Fusion archive exported: %s', output / 'Drawer1.f3d')
        app.activeViewport.fit()
        message = (
            'Four independent brown PETG bins created. All dimensions are mm.\n\n'
            'Two long bins, clear: %.3f wide x %.2f long\n'
            'Two short bins, clear: %.3f wide x %.2f long\n'
            'Overall height: %.1f; gap between bins: %.1f\n\n'
            'Four STL files and upright Fusion archive exported to:\n%s\n\n'
            'Long STLs are already tilted %.1f degrees: ENABLE SUPPORTS in Bambu Studio.\n'
            'Preserve their orientation; do not use auto-orient or lay-on-face.\n'
            'Print each long bin separately; short bins print flat without supports.\n'
            'Use 100%% scale and brown PETG. Check support/brim fit in sliced preview.\n'
            'STL does not store support, filament, or color settings.'
        ) % (LONG_BAY_WIDTH, LONG_BAY_LENGTH, LONG_BAY_WIDTH, SHORT_BAY_LENGTH,
             HEIGHT, BIN_GAP, output, PRINT_TILT_DEGREES)
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
