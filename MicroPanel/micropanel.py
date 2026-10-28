"""MicroPanel: honeycomb panel with releasable PETG snap retainers.

All dimensions are millimeters; Fusion API lengths are converted to centimeters.
Run in Fusion Scripts and Add-Ins. Creates a new document, leaving prior designs
untouched. One named parent component contains the complete printable object.
Print flat, clips upward, in PETG. Hook projections are 4.3 mm beyond the tab.
Fit is based on measured exterior dimensions, not on a physical fit test.
Insert one edge beneath its hooks, flex the opposite tabs outward, then seat
the device and release the tabs. Flex the heads outward to remove devices.
The reinforced tabs are intentionally stiffer. Do not pull on boards or wires.
ESP32 USB ends face the bottom panel edge; hub input/power end faces the top.
The Freenove controller is included in the supplied 164 x 54.3 mm footprint.
"""
from pathlib import Path
import logging
import math
import traceback
import adsk.core
import adsk.fusion

PANEL_WIDTH = 250.0
PANEL_HEIGHT = 250.0
BASE_THICKNESS = 4.0
SIDE_CLEARANCE = 0.30
LATCH_CLEARANCE = 0.25
CLIP_THICKNESS = 4.0
CLIP_WIDTH = 30.0
HEAD_WIDTH = 30.0
HOOK_OVERLAP = 4.0
HOOK_TIP_THICKNESS = 2.0
RAMP_HEIGHT = 6.5
ROOT_FILLET = 1.0
GUIDE_WALL = 1.8
GUIDE_LENGTH = 5.0
GUIDE_HEIGHT = 2.5
MOUNT_HOLE_DIAMETER = 4.5
PANEL_CORNER_RADIUS = 8.0
HEX_ACROSS_FLATS = 8.0
HEX_WEB = 2.2
PANEL_BORDER = 5.0
SUPPORT_BORDER = 1.5
CLIP_ROOT_BORDER = 3.0
MOUNT_CENTERS = ((6, 6), (244, 6), (6, 244), (244, 244))
ESP32_PIN_PROTRUSION = 3.75

# name, x, y, X size, Y size, case/edge height, support lift above base, clip sides
# Breadboard clips grip its 9.5 mm plastic edge, clear of the controller on top.
DEVICES = [
    ("ESP32 1", 14.0, 20.0, 33.2, 55.7, 11.7, 10.0, "x"),
    ("ESP32 2", 60.5, 20.0, 33.2, 55.7, 11.7, 10.0, "x"),
    ("ESP32 3", 107.0, 20.0, 33.2, 55.7, 11.7, 10.0, "x"),
    ("ESP32 4", 153.5, 20.0, 33.2, 55.7, 11.7, 10.0, "x"),
    ("ESP32 5", 200.0, 20.0, 33.2, 55.7, 11.7, 10.0, "x"),
    ("Freenove breadboard", 14.0, 102.0, 164.0, 54.3, 9.5, 14.0, "y"),
    ("Raspberry Pi case", 14.0, 181.0, 91.2, 61.35, 22.5, 3.0, "y"),
    ("Anker 10-port USB hub", 196.0, 98.0, 44.5, 145.5, 22.9, 3.0, "x"),
]


def pt(x, y, z):
    return adsk.core.Point3D.create(x/10, y/10, z/10)


def value(mm):
    return adsk.core.ValueInput.createByReal(mm/10)


def box(manager, x0, y0, x1, y1, z0, z1):
    assert x1 > x0 and y1 > y0 and z1 > z0
    return manager.createBox(adsk.core.OrientedBoundingBox3D.create(
        pt((x0+x1)/2, (y0+y1)/2, (z0+z1)/2),
        adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
        (x1-x0)/10, (y1-y0)/10, (z1-z0)/10))


def boolean(manager, target, tool, operation):
    if not manager.booleanOperation(target, tool, operation):
        raise RuntimeError("Panel Boolean failed")


def support_rectangles(d):
    _, x, y, w, h, _, _, _ = d
    if d[0].startswith("ESP32"):
        # Narrow support ledges at the short ends avoid the protruding pin rows.
        yield x, y, x+w, y+1.2
        yield x, y+h-1.2, x+w, y+h
    elif d[0].startswith("Freenove"):
        # Raised rails support the breadboard and give its clips long flex arms.
        for left in (x, x+w/2-1, x+w-2):
            yield left, y, left+2, y+h
    else:
        for left in (x, x+w-5):
            for bottom in (y, y+h-5):
                yield left, bottom, left+5, bottom+5


def guide_rectangles(d):
    _, x, y, w, h, _, _, _ = d
    x0, y0, x1, y1 = x-SIDE_CLEARANCE, y-SIDE_CLEARANCE, x+w+SIDE_CLEARANCE, y+h+SIDE_CLEARANCE
    for corner_x, sx in ((x0, -1), (x1, 1)):
        for corner_y, sy in ((y0, -1), (y1, 1)):
            xa, xb = sorted((corner_x, corner_x+sx*GUIDE_WALL))
            ya, yb = sorted((corner_y, corner_y-sy*GUIDE_LENGTH))
            yield xa, ya, xb, yb
            xa, xb = sorted((corner_x, corner_x-sx*GUIDE_LENGTH))
            ya, yb = sorted((corner_y, corner_y+sy*GUIDE_WALL))
            yield xa, ya, xb, yb
            xa, xb = sorted((corner_x, corner_x+sx*GUIDE_WALL))
            yield xa, ya, xb, yb


def clips(d):
    """Yield inner-face center and inward unit direction for each latch."""
    name, x, y, w, h, _, _, sides = d
    if sides == "x":
        fractions = (0.5,) if name.startswith("ESP32") else (0.18, 0.82)
        for fraction in fractions:
            yield x-SIDE_CLEARANCE, y+h*fraction, 1, 0
            yield x+w+SIDE_CLEARANCE, y+h*fraction, -1, 0
    else:
        # Breadboard clips stay away from the controller at the left end.
        fractions = (0.50, 0.85) if name.startswith("Freenove") else (0.35, 0.70)
        for fraction in fractions:
            yield x+w*fraction, y-SIDE_CLEARANCE, 0, 1
            yield x+w*fraction, y+h+SIDE_CLEARANCE, 0, -1


def beam_rect(x, y, nx, ny, width=CLIP_WIDTH):
    if nx:
        xa, xb = sorted((x, x-nx*CLIP_THICKNESS))
        return xa, y-width/2, xb, y+width/2
    ya, yb = sorted((y, y-ny*CLIP_THICKNESS))
    return x-width/2, ya, x+width/2, yb


def hex_vertices(cx, cy):
    radius = HEX_ACROSS_FLATS/math.sqrt(3)
    return [(cx+radius*math.cos(math.radians(30+60*i)),
             cy+radius*math.sin(math.radians(30+60*i))) for i in range(6)]


def polygon_intersects_rect(vertices, rectangle):
    """Separating-axis test, including the requested solid support border."""
    xa, ya, xb, yb = rectangle
    corners = ((xa, ya), (xb, ya), (xb, yb), (xa, yb))
    axes = [(1, 0), (0, 1)]
    for i in range(3):
        ax, ay = vertices[i]
        bx, by = vertices[i+1]
        axes.append((ay-by, bx-ax))
    for nx, ny in axes:
        polygon_projection = [x*nx+y*ny for x, y in vertices]
        rect_projection = [x*nx+y*ny for x, y in corners]
        if max(polygon_projection) < min(rect_projection) or max(rect_projection) < min(polygon_projection):
            return False
    return True


def protected_rectangles():
    for d in DEVICES:
        for rectangle in list(support_rectangles(d))+list(guide_rectangles(d)):
            xa, ya, xb, yb = rectangle
            yield xa-SUPPORT_BORDER, ya-SUPPORT_BORDER, xb+SUPPORT_BORDER, yb+SUPPORT_BORDER
        for c in clips(d):
            xa, ya, xb, yb = beam_rect(*c)
            yield xa-CLIP_ROOT_BORDER, ya-CLIP_ROOT_BORDER, xb+CLIP_ROOT_BORDER, yb+CLIP_ROOT_BORDER


def inside_panel_border(x, y):
    # Signed distance to the inset rounded rectangle; all hex vertices must fit.
    half_x = PANEL_WIDTH/2-PANEL_BORDER
    half_y = PANEL_HEIGHT/2-PANEL_BORDER
    radius = max(0, PANEL_CORNER_RADIUS-PANEL_BORDER)
    dx = abs(x-PANEL_WIDTH/2)-(half_x-radius)
    dy = abs(y-PANEL_HEIGHT/2)-(half_y-radius)
    return math.hypot(max(dx, 0), max(dy, 0))+min(max(dx, dy), 0) <= radius


def ventilation_centers():
    """Full-panel staggered honeycomb, with intact load-bearing islands."""
    pitch_x = HEX_ACROSS_FLATS+HEX_WEB
    pitch_y = pitch_x*math.sqrt(3)/2
    protected = list(protected_rectangles())
    radius = HEX_ACROSS_FLATS/math.sqrt(3)
    rows = int(PANEL_HEIGHT/pitch_y)+1
    columns = int(PANEL_WIDTH/pitch_x)+1
    for row in range(-rows, rows+1):
        cy = PANEL_HEIGHT/2+row*pitch_y
        for column in range(-columns, columns+1):
            cx = PANEL_WIDTH/2+(column+(row%2)/2)*pitch_x
            vertices = hex_vertices(cx, cy)
            if not all(inside_panel_border(x, y) for x, y in vertices):
                continue
            if any(math.hypot(cx-x, cy-y) < radius+MOUNT_HOLE_DIAMETER/2+2.0 for x, y in MOUNT_CENTERS):
                continue
            if any(polygon_intersects_rect(vertices, rectangle) for rectangle in protected):
                continue
            yield cx, cy


def make_hex_prototype(design, manager):
    occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    sketch = component.sketches.add(component.xYConstructionPlane)
    vertices = hex_vertices(0, 0)
    for i, (x, y) in enumerate(vertices):
        bx, by = vertices[(i+1)%6]
        sketch.sketchCurves.sketchLines.addByTwoPoints(pt(x, y, 0), pt(bx, by, 0))
    settings = component.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    settings.setDistanceExtent(False, value(BASE_THICKNESS+2))
    feature = component.features.extrudeFeatures.add(settings)
    prototype = manager.copy(feature.bodies.item(0))
    occurrence.deleteMe()
    return prototype


def round_panel_corners(component, body):
    edges = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        lo, hi = edge.boundingBox.minPoint, edge.boundingBox.maxPoint
        if (abs((hi.z-lo.z)*10-BASE_THICKNESS) < 0.01
                and abs(hi.x-lo.x) < 0.0001 and abs(hi.y-lo.y) < 0.0001
                and min(abs(lo.x*10), abs(lo.x*10-PANEL_WIDTH)) < 0.01
                and min(abs(lo.y*10), abs(lo.y*10-PANEL_HEIGHT)) < 0.01):
            edges.add(edge)
    if edges.count != 4:
        raise RuntimeError("Expected four outer corner edges; found %d" % edges.count)
    before = body.volume*1000
    settings = component.features.filletFeatures.createInput()
    settings.edgeSetInputs.addConstantRadiusEdgeSet(edges, value(PANEL_CORNER_RADIUS), False)
    component.features.filletFeatures.add(settings)
    expected_removed = (4-math.pi)*PANEL_CORNER_RADIUS**2*BASE_THICKNESS
    if abs(before-body.volume*1000-expected_removed) > 0.1:
        raise RuntimeError("Rounded corner volume mismatch")


def make_ramp_prototype(design, manager):
    """Temporary sketch prism; removed after copying, leaving no extra bodies."""
    occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    sketch = component.sketches.add(component.xYConstructionPlane)
    reach = SIDE_CLEARANCE + HOOK_OVERLAP + 0.2
    vertices = (pt(0, 0, 0), pt(reach, 0, 0),
                pt(reach, HOOK_TIP_THICKNESS, 0), pt(0, RAMP_HEIGHT, 0))
    lines = sketch.sketchCurves.sketchLines
    for index in range(len(vertices)):
        lines.addByTwoPoints(vertices[index], vertices[(index+1)%len(vertices)])
    extrudes = component.features.extrudeFeatures
    settings = extrudes.createInput(sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    settings.setDistanceExtent(False, value(CLIP_WIDTH))
    extrusion = extrudes.add(settings)
    prototype = manager.copy(extrusion.bodies.item(0))
    occurrence.deleteMe()
    return prototype


def ramp_at(manager, prototype, x, y, nx, ny, z):
    # Source X points inward, Y upward, Z along the clip edge (right handed).
    tx, ty = ny, -nx
    origin = pt(x-nx*0.2-tx*CLIP_WIDTH/2, y-ny*0.2-ty*CLIP_WIDTH/2, z)
    transform = adsk.core.Matrix3D.create()
    transform.setWithCoordinateSystem(origin, adsk.core.Vector3D.create(nx, ny, 0),
                                     adsk.core.Vector3D.create(0, 0, 1),
                                     adsk.core.Vector3D.create(tx, ty, 0))
    ramp = manager.copy(prototype)
    if not manager.transform(ramp, transform):
        raise RuntimeError("Could not orient latch ramp")
    return ramp


def round_clip_roots(component, body):
    edges = adsk.core.ObjectCollection.create()
    roots = [beam_rect(*c) for d in DEVICES for c in clips(d)]
    for edge in body.edges:
        bounds = edge.boundingBox
        lo, hi = bounds.minPoint, bounds.maxPoint
        if abs(lo.z*10-BASE_THICKNESS) > 0.01 or abs(hi.z*10-BASE_THICKNESS) > 0.01:
            continue
        for xa, ya, xb, yb in roots:
            if xb-xa < yb-ya:
                matches = any(abs(lo.x*10-x) < 0.01 and abs(hi.x*10-x) < 0.01
                              and abs(lo.y*10-ya) < 0.01 and abs(hi.y*10-yb) < 0.01 for x in (xa, xb))
            else:
                matches = any(abs(lo.y*10-y) < 0.01 and abs(hi.y*10-y) < 0.01
                              and abs(lo.x*10-xa) < 0.01 and abs(hi.x*10-xb) < 0.01 for y in (ya, yb))
            if matches:
                edges.add(edge)
                break
    expected = 2*len(roots)
    if edges.count != expected:
        raise RuntimeError("Expected %d clip root edges, found %d" % (expected, edges.count))
    settings = component.features.filletFeatures.createInput()
    settings.edgeSetInputs.addConstantRadiusEdgeSet(edges, value(ROOT_FILLET), False)
    component.features.filletFeatures.add(settings)
    return len(roots)


def validate_layout():
    assert DEVICES[0][6] - ESP32_PIN_PROTRUSION >= 2
    # A tab must be able to release into a neighboring gap with that neighbor fixed.
    esp_devices = [d for d in DEVICES if d[0].startswith("ESP32")]
    for left, right in zip(esp_devices, esp_devices[1:]):
        gap = right[1]-(left[1]+left[3])-2*(SIDE_CLEARANCE+CLIP_THICKNESS)
        assert gap >= HOOK_OVERLAP+SIDE_CLEARANCE+0.2, "Insufficient ESP32 clip release space"
    for d in DEVICES:
        for rect in list(guide_rectangles(d)) + [beam_rect(*c, width=HEAD_WIDTH) for c in clips(d)]:
            assert 0 < rect[0] < rect[2] < PANEL_WIDTH and 0 < rect[1] < rect[3] < PANEL_HEIGHT, (d[0], rect)
        for x, y, nx, ny in clips(d):
            # Heads must not touch another device; permit outward release travel.
            for other in DEVICES:
                if other is d:
                    continue
                assert not (other[1]-2 < x-nx*3 < other[1]+other[3]+2 and
                            other[2]-2 < y-ny*3 < other[2]+other[4]+2), (d[0], other[0])


def run(context):
    directory = Path(__file__).resolve().parent
    logger = logging.getLogger("MicroPanel")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(directory / "micropanel.log", mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    try:
        validate_layout()
        app = adsk.core.Application.get()
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        doc.name = "MicroPanel - releasable clips - 250 x 250 mm"
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        design.unitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        manager = adsk.fusion.TemporaryBRepManager.get()
        ramp_prototype = make_ramp_prototype(design, manager)
        hex_prototype = make_hex_prototype(design, manager)
        occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        component = occurrence.component
        component.name = "MicroPanel - complete printable organizer"
        union = adsk.fusion.BooleanTypes.UnionBooleanType
        difference = adsk.fusion.BooleanTypes.DifferenceBooleanType
        panel = box(manager, 0, 0, PANEL_WIDTH, PANEL_HEIGHT, 0, BASE_THICKNESS)
        for d in DEVICES:
            name, x, y, w, h, height, lift, _ = d
            support_z = BASE_THICKNESS + lift
            latch_z = support_z + height + LATCH_CLEARANCE
            for rect in support_rectangles(d):
                boolean(manager, panel, box(manager, *rect, BASE_THICKNESS-0.1, support_z), union)
            for rect in guide_rectangles(d):
                boolean(manager, panel, box(manager, *rect, BASE_THICKNESS-0.1, support_z+GUIDE_HEIGHT), union)
            for cx, cy, nx, ny in clips(d):
                boolean(manager, panel, box(manager, *beam_rect(cx, cy, nx, ny),
                        BASE_THICKNESS-0.1, latch_z+RAMP_HEIGHT), union)
                boolean(manager, panel, box(manager, *beam_rect(cx, cy, nx, ny, HEAD_WIDTH),
                        latch_z-3.0, latch_z+RAMP_HEIGHT), union)
                boolean(manager, panel, ramp_at(manager, ramp_prototype, cx, cy, nx, ny, latch_z), union)
            logger.info("%s: footprint %g x %g; height %g; lift %g; %d clips; latch underside Z=%g",
                        name, w, h, height, lift, len(list(clips(d))), latch_z)
        volume_before = panel.volume*1000
        centers = list(ventilation_centers())
        vent_count = len(centers)
        for x, y in centers:
            cutter = manager.copy(hex_prototype)
            transform = adsk.core.Matrix3D.create()
            transform.translation = adsk.core.Vector3D.create(x/10, y/10, -0.1)
            if not manager.transform(cutter, transform):
                raise RuntimeError("Could not position honeycomb cutter")
            boolean(manager, panel, cutter, difference)
        expected_removed = vent_count*math.sqrt(3)/2*HEX_ACROSS_FLATS**2*BASE_THICKNESS
        if abs(volume_before-panel.volume*1000-expected_removed) > 0.1:
            raise RuntimeError("Honeycomb cut volume mismatch: actual %g, expected %g mm3" %
                               (volume_before-panel.volume*1000, expected_removed))
        for x, y in MOUNT_CENTERS:
            cutter = manager.createCylinderOrCone(pt(x, y, -1), MOUNT_HOLE_DIAMETER/20,
                                                 pt(x, y, BASE_THICKNESS+1), MOUNT_HOLE_DIAMETER/20)
            boolean(manager, panel, cutter, difference)
        body = component.bRepBodies.add(panel)
        body.name = "Rounded honeycomb panel with 22 release clips"
        round_panel_corners(component, body)
        clip_count = round_clip_roots(component, body)
        if not body.isSolid or component.bRepBodies.count != 1 or body.lumps.count != 1:
            raise RuntimeError("Expected one connected printable solid")
        bounds = body.boundingBox
        actual = tuple((getattr(bounds.maxPoint, axis)-getattr(bounds.minPoint, axis))*10 for axis in "xyz")
        max_height = max(BASE_THICKNESS+d[6]+d[5]+LATCH_CLEARANCE+RAMP_HEIGHT for d in DEVICES)
        expected = (PANEL_WIDTH, PANEL_HEIGHT, max_height)
        if any(abs(a-b) > 0.01 for a, b in zip(actual, expected)):
            raise RuntimeError("Unexpected panel bounds: %r; expected %r" % (actual, expected))
        logger.info("Verified one connected solid, %d clips, %d full-panel hexagonal through vents", clip_count, vent_count)
        logger.info("Honeycomb: %g across flats, %g webs, %g perimeter border; outer corner radius %g mm",
                    HEX_ACROSS_FLATS, HEX_WEB, PANEL_BORDER, PANEL_CORNER_RADIUS)
        logger.info("Verified bounding dimensions %s mm; ESP32 pin clearance %g mm", actual, DEVICES[0][6]-ESP32_PIN_PROTRUSION)
        logger.info("Clip section: %g wide x %g thick; head %g; hook overlap %g; tip thickness %g; root radius %g mm",
                    CLIP_WIDTH, CLIP_THICKNESS, HEAD_WIDTH, HOOK_OVERLAP, HOOK_TIP_THICKNESS, ROOT_FILLET)
        logger.info("Material assumption: PETG. Physical retention and connector fit require a print fit check.")
        app.activeViewport.visualStyle = adsk.core.VisualStyles.ShadedWithVisibleEdgesOnlyVisualStyle
        camera = app.activeViewport.camera
        camera.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
        camera.isFitView = True
        app.activeViewport.camera = camera
        app.activeViewport.refresh()
        if not app.activeViewport.saveAsImageFile(str(directory / "mockup.png"), 1600, 1400):
            raise RuntimeError("Could not save preview")
        print("MicroPanel verified: %s mm; %d clips; %d hex vents; R%g panel corners." % (actual, clip_count, vent_count, PANEL_CORNER_RADIUS))
    except Exception:
        logger.error(traceback.format_exc())
        raise
    finally:
        handler.close()
        logger.removeHandler(handler)
