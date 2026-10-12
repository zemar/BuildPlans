"""Run inside Autodesk Fusion: Utilities > Scripts and Add-Ins > Scripts.

Creates a 127 mm trophy with separate volleyball, base, stand, and text bodies.
All dimensions below are millimeters; Fusion geometry uses centimeters.
Creates the Fusion design for manual Save As Mesh export to 3MF.
Prototype version is recorded in Trophy.manifest; run diagnostics in Trophy.log.
"""
import math
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
import adsk.core
import adsk.fusion


PLAYER_NAME = "Myriam Howard"  # Change this and rerun for each player.
PLAYER_NUMBER = "#6"  # Raised medium blue lettering on the volleyball.
FONT_NAME = "Arial"
TOTAL_HEIGHT_MM = 127.0
BALL_RADIUS_MM = 25.0
SEAM_RADIUS_MM = 0.65  # Rounded grooves: approximately 1.3 mm wide.
ENGRAVE_DEPTH_MM = 1.2  # Hidden anchoring depth for contrasting base lettering.
RAISED_TEXT_MM = 1.2
BASE_TAPER = 0.2  # Six millimeters inward over the 30 mm base height.
STAND_TWIST_DEGREES = 120.0
# Z-up is required for direct Fusion Save As Mesh exports to slicers.
CAD_Y_UP = False


def write_run_log(message, reset=False):
    """Persist Fusion results beside this script so they can be read externally."""
    try:
        log_path = Path(__file__).resolve().with_suffix('.log')
        with log_path.open('w' if reset else 'a', encoding='utf-8') as log:
            log.write(datetime.now(timezone.utc).isoformat() + ' ' + message + '\n')
    except OSError as error:
        print('Could not write trophy log: {}'.format(error))


def point(x, y, z):
    return adsk.core.Point3D.create(x / 10, y / 10, z / 10)


def filament_appearance(design, seed, name, rgb):
    """Create a visible filament color across current and older Fusion APIs."""
    color = adsk.core.Color.create(*rgb, 255)
    # Current Fusion can create a plain opaque appearance directly.
    if hasattr(design.appearances, 'add'):
        try:
            appearance = design.appearances.add(name)
            appearance.color = color
            return appearance
        except (AttributeError, RuntimeError):
            pass
    # Older versions can copy an existing appearance and change its color.
    appearance = design.appearances.addByCopy(seed, name + ' - compatible')
    for property_id in ('opaque_albedo', 'generic_diffuse', 'metal_f0'):
        prop = adsk.core.ColorProperty.cast(
            appearance.appearanceProperties.itemById(property_id))
        if prop:
            if prop.hasConnectedTexture:
                prop.hasConnectedTexture = False
            prop.value = color
            return appearance
    raise RuntimeError('Could not set filament appearance: ' + name)


def bronze_appearance(design):
    """Copy a metallic library appearance so the base has metal reflectance."""
    candidates = []
    for library in adsk.core.Application.get().materialLibraries:
        for appearance in library.appearances:
            name = appearance.name.lower()
            if 'bronze' in name:
                candidates.append((0, appearance))
            elif 'copper' in name or 'brass' in name:
                candidates.append((1, appearance))
            elif appearance.appearanceProperties.itemById('metal_f0'):
                candidates.append((2, appearance))
    if not candidates:
        raise RuntimeError("No metallic appearance found in Fusion's material libraries.")
    _, source = min(candidates, key=lambda item: item[0])
    appearance = design.appearances.addByCopy(source, 'Filament - Metallic Bronze')
    tint = adsk.core.ColorProperty.cast(appearance.appearanceProperties.itemById('metal_f0'))
    if tint:
        if tint.hasConnectedTexture:
            tint.hasConnectedTexture = False
        tint.value = adsk.core.Color.create(181, 125, 62, 255)
    return appearance


def vector(x, y, z):
    return adsk.core.Vector3D.create(x, y, z)


def boolean(manager, target, tool, operation, label):
    if tool is None or not manager.booleanOperation(target, tool, operation):
        raise RuntimeError("Geometry operation failed: " + label)
    return target


def box(manager, center, sizes):
    bounds = adsk.core.OrientedBoundingBox3D.create(
        point(*center), vector(1, 0, 0), vector(0, 1, 0),
        sizes[0] / 10, sizes[1] / 10, sizes[2] / 10)
    return manager.createBox(bounds)


def clip_halfspace(manager, body, normal, center):
    """Keep dot(position - center, normal) >= 0, using a large box."""
    n = vector(*normal)
    n.normalize()
    helper = vector(0, 0, 1) if abs(n.z) < 0.9 else vector(0, 1, 0)
    u = n.crossProduct(helper)
    u.normalize()
    v = n.crossProduct(u)
    v.normalize()
    # u cross v = n; box extends from the cutting plane 200 mm outward.
    origin = point(center[0] + 100 * n.x,
                   center[1] + 100 * n.y,
                   center[2] + 100 * n.z)
    bounds = adsk.core.OrientedBoundingBox3D.create(origin, u, v, 20, 20, 20)
    return boolean(manager, body, manager.createBox(bounds),
                   adsk.fusion.BooleanTypes.IntersectionBooleanType,
                   "clip volleyball seam")


def volleyball(manager, center):
    """Six spherical panel groups, each split into three curved strips.

    Panel boundaries follow the projected edges of a cube. Alternating
    stripe directions produce a stylized 18-panel volleyball, not merely
    latitude/longitude rings. All seams are actual recessed geometry.
    """
    r = BALL_RADIUS_MM
    ball = manager.createSphere(point(*center), r / 10)
    cut = adsk.fusion.BooleanTypes.DifferenceBooleanType

    # Twelve boundary arcs. For each axis pair, keep only the portion
    # where those two signed coordinates dominate the remaining axis.
    for a, b in ((0, 1), (0, 2), (1, 2)):
        other = 3 - a - b
        for sa in (-1, 1):
            for sb in (-1, 1):
                normal = [0, 0, 0]
                normal[a], normal[b] = sa, -sb
                seam = manager.createTorus(point(*center), vector(*normal),
                                          r / 10, SEAM_RADIUS_MM / 10)
                positive = [0, 0, 0]
                positive[a] = sa
                clip_halfspace(manager, seam, positive, center)
                for sign in (-1, 1):
                    limit = positive[:]
                    limit[other] = sign
                    clip_halfspace(manager, seam, limit, center)
                boolean(manager, ball, seam, cut, "panel boundary")
                adsk.doEvents()

    # Two small-circle arcs within each of the six dominant-axis cells.
    for axis in range(3):
        stripe_axis = (axis + 1) % 3
        remaining = [i for i in range(3) if i != axis]
        for side in (-1, 1):
            for offset in (-7.0, 7.0):
                ring_center = list(center)
                ring_center[stripe_axis] += offset
                normal = [0, 0, 0]
                normal[stripe_axis] = 1
                seam = manager.createTorus(
                    point(*ring_center), vector(*normal),
                    math.sqrt(r * r - offset * offset) / 10,
                    SEAM_RADIUS_MM / 10)
                for other in remaining:
                    for sign in (-1, 1):
                        limit = [0, 0, 0]
                        limit[axis], limit[other] = side, sign
                        clip_halfspace(manager, seam, limit, center)
                boolean(manager, ball, seam, cut, "panel stripe")
                adsk.doEvents()

    # Tilt the panels for a more natural presentation.
    rotation = adsk.core.Matrix3D.create()
    rotation.setToRotation(math.radians(27), vector(1, 2, 0.3), point(*center))
    if not manager.transform(ball, rotation):
        raise RuntimeError("Could not orient volleyball.")
    return ball


def inlay_line(root, target, label, text, z_low, z_high, height):
    write_run_log("INLAY: {}: {!r}".format(label, text))
    # Build readable letters in XY, then tilt their solids to the tapered front.
    sketch = root.sketches.add(root.xYConstructionPlane)
    sketch.name = label
    texts = sketch.sketchTexts
    # Current Fusion uses a quoted text expression and a ValueInput.
    # Older Fusion versions expose createInput2 instead.
    if hasattr(texts, "createInput3"):
        expression = "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"
        text_input = texts.createInput3(
            expression, adsk.core.ValueInput.createByReal(height / 10))
    else:
        text_input = texts.createInput2(text, height / 10)
    text_input.fontName = FONT_NAME
    text_input.isHorizontalFlip = False
    text_input.isVerticalFlip = False
    low = point(-37, z_low, 0)
    high = point(37, z_high, 0)
    text_input.setAsMultiLine(
        low, high,
        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
        adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    entity = texts.add(text_input)
    if not entity:
        raise RuntimeError("Could not create " + label)
    extrudes = root.features.extrudeFeatures
    extrusion = extrudes.createInput(
        entity, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extent = adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal((ENGRAVE_DEPTH_MM + RAISED_TEXT_MM) / 10))
    extrusion.setOneSideExtent(
        extent, adsk.fusion.ExtentDirections.NegativeExtentDirection)
    feature = extrudes.add(extrusion)
    cutters = adsk.core.ObjectCollection.create()
    for index, body in enumerate(feature.bodies, 1):
        body.name = "Writing - White - {} - {:02d}".format(label, index)
        cutters.add(body)
    if cutters.count == 0:
        raise RuntimeError("No letter cutting bodies were generated for " + label)

    # X stays right; text Y follows the sloped face. The outer tips stand
    # 1.2 mm proud, while the inner ends anchor in the hidden backing.
    placement = adsk.core.Matrix3D.create()
    angle = math.atan(BASE_TAPER)
    placement.setToRotation(math.pi / 2 - angle, vector(1, 0, 0), point(0, 0, 0))
    placement.translation = vector(0, (-32 - RAISED_TEXT_MM * math.cos(angle)) / 10,
                                   RAISED_TEXT_MM * math.sin(angle) / 10)
    moves = root.features.moveFeatures
    move_input = moves.createInput2(cutters)
    if not move_input.defineAsFreeMove(placement):
        raise RuntimeError("Could not position letter cutting bodies.")
    moves.add(move_input)

    combines = root.features.combineFeatures
    cut_input = combines.createInput(target, cutters)
    cut_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    cut_input.isKeepToolBodies = True
    body_count_before = root.bRepBodies.count
    volume_before = target.volume
    inlay_volume = sum(body.volume for body in cutters)
    cut = combines.add(cut_input)
    # Autodesk documents a None return for a non-parametric combine, even
    # when it succeeds. Validate the solid rather than the feature handle.
    if cut is not None:
        cut.name = label + " engraving"
    if root.bRepBodies.count != body_count_before:
        raise RuntimeError("Text inlay bodies were not retained: " + label)
    if not target.isSolid or volume_before - target.volume <= 1e-8:
        raise RuntimeError("Engraving did not remove material from the trophy: " + label)
    removed_volume = volume_before - target.volume
    if removed_volume >= inlay_volume:
        raise RuntimeError("Lettering must project above the base: " + label)
    write_run_log("INLAY OK: {}; bodies={}; volume={:.3f} mm^3".format(
        label, cutters.count, inlay_volume * 1000))
    sketch.isVisible = False
    return list(cutters)


def join_writing(root, manager, base, glyphs):
    """Connect every letter through a white backing hidden inside the base."""
    front = -32 + ENGRAVE_DEPTH_MM - 0.05  # Small overlap gives a robust solid join.
    thickness = 0.6
    backing_shape = box(manager, (0, front + thickness / 2, 16.5), (74, thickness, 24))
    tilt = adsk.core.Matrix3D.create()
    tilt.setToRotation(-math.atan(BASE_TAPER), vector(1, 0, 0), point(0, -32, 0))
    if not manager.transform(backing_shape, tilt):
        raise RuntimeError("Could not align the hidden backing to the tapered base.")
    backing = root.bRepBodies.add(backing_shape)
    backing.name = 'Writing - White'
    tools = adsk.core.ObjectCollection.create()
    for glyph in glyphs:
        tools.add(glyph)
    combines = root.features.combineFeatures
    joining = combines.createInput(backing, tools)
    joining.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    joining.isKeepToolBodies = False
    combines.add(joining)
    if not backing.isSolid or backing.lumps.count != 1 or root.bRepBodies.count != 4:
        raise RuntimeError('Could not connect all lettering into one Writing body.')
    # The glyph anchor pockets already exist; the hidden backing plate is new
    # material to remove from the black base. Keep the joined white solid.
    tools = adsk.core.ObjectCollection.create()
    tools.add(backing)
    pocket = combines.createInput(base, tools)
    pocket.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    pocket.isKeepToolBodies = True
    before = base.volume
    existing = list(root.bRepBodies)
    combines.add(pocket)
    # The backing can otherwise isolate the black centers of enclosed letters.
    # Extend those centers through holes in the white backing and reconnect
    # them to the main black base, preserving the visible glyph outlines.
    counters = [body for body in root.bRepBodies
                if not any(body == known for known in existing)]
    black_pieces = [base] + counters
    base = max(black_pieces, key=lambda body: body.volume)
    counters = [body for body in black_pieces if body != base]
    if counters:
        bridges = adsk.core.ObjectCollection.create()
        shift = adsk.core.Matrix3D.create()
        angle = math.atan(BASE_TAPER)
        shift.translation = vector(0, (thickness + 0.05) * math.cos(angle) / 10,
                                   -(thickness + 0.05) * math.sin(angle) / 10)
        for counter in counters:
            bridge_shape = manager.copy(counter)
            if not manager.transform(bridge_shape, shift):
                raise RuntimeError('Could not connect a black letter center.')
            bridges.add(root.bRepBodies.add(bridge_shape))
        holes = combines.createInput(backing, bridges)
        holes.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        holes.isKeepToolBodies = True
        combines.add(holes)
        for counter in counters:
            bridges.add(counter)
        reconnect = combines.createInput(base, bridges)
        reconnect.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        reconnect.isKeepToolBodies = False
        combines.add(reconnect)
    if before - base.volume <= 0:
        raise RuntimeError("Hidden writing backing did not create its base pocket.")
    if root.bRepBodies.count != 4 or backing.lumps.count != 1 or base.lumps.count != 1:
        raise RuntimeError('Writing or base contains disconnected material after backing construction.')
    base.name = 'Base - Metallic Bronze'
    backing.name = 'Writing - White'
    write_run_log('WRITING JOIN OK: {} glyph bodies connected with a hidden 0.6 mm plate.'
                  .format(len(glyphs)))
    return base, backing


def tapered_base(manager):
    """One uninterrupted plinth: 88x64 bottom, 76x52 top, height 30 mm."""
    shape = box(manager, (0, 0, 15), (88, 64, 30))
    for normal, origin in (((-1, 0, -BASE_TAPER), (44, 0, 0)),
                           ((1, 0, -BASE_TAPER), (-44, 0, 0)),
                           ((0, -1, -BASE_TAPER), (0, 32, 0)),
                           ((0, 1, -BASE_TAPER), (0, -32, 0))):
        clip_halfspace(manager, shape, normal, origin)
    return shape


def twisted_stand(root, manager):
    """Loft a twisted hourglass: wide ends with a smooth central waist."""
    loft = root.features.loftFeatures.createInput(
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    loft.isSolid = True
    sketches, planes = [], []
    for index in range(9):
        fraction = index / 8
        z = 30 + 52 * fraction
        plane_input = root.constructionPlanes.createInput()
        plane_input.setByOffset(root.xYConstructionPlane,
                               adsk.core.ValueInput.createByReal(z / 10))
        plane = root.constructionPlanes.add(plane_input)
        planes.append(plane)
        sketch = root.sketches.add(plane)
        sketch.name = "Twist section {:02d}".format(index)
        sketches.append(sketch)
        angle = math.radians(STAND_TWIST_DEGREES * fraction)
        # A symmetric quadratic flare keeps the waist at mid-height and
        # opens both ends smoothly, while retaining the decorative twist.
        flare = (2 * fraction - 1) ** 2
        rx, ry = 7 + 7 * flare, 6 + 5 * flare
        vertices = []
        for corner in range(8):
            phase = math.pi / 8 + corner * math.pi / 4
            x, y = rx * math.cos(phase), ry * math.sin(phase)
            vertices.append(point(x * math.cos(angle) - y * math.sin(angle),
                                  x * math.sin(angle) + y * math.cos(angle), 0))
        for corner in range(8):
            sketch.sketchCurves.sketchLines.addByTwoPoints(vertices[corner], vertices[(corner + 1) % 8])
        if sketch.profiles.count != 1:
            raise RuntimeError("Twist section did not produce one closed profile.")
        loft.loftSections.add(sketch.profiles.item(0))
    feature = root.features.loftFeatures.add(loft)
    if feature is None or feature.bodies.count != 1:
        raise RuntimeError("Could not create the twisted stand loft.")
    body = feature.bodies.item(0)
    shape = manager.copy(body)
    body.deleteMe()
    for sketch in sketches:
        sketch.isVisible = False
    for plane in planes:
        plane.isLightBulbOn = False
    collar = manager.createCylinderOrCone(point(0, 0, 76), 1.0,
                                         point(0, 0, 86), 1.6)
    boolean(manager, shape, collar, adsk.fusion.BooleanTypes.UnionBooleanType, "twisted stand cradle")
    return shape


def ball_number(root, manager, ball, center):
    """Raised medium blue digits clipped to concentric spheres, attached to the ball."""
    sketch = root.sketches.add(root.xYConstructionPlane)
    number = PLAYER_NUMBER.strip()
    sketch.name = "Volleyball player number " + number
    texts = sketch.sketchTexts
    if hasattr(texts, 'createInput3'):
        text_input = texts.createInput3("'" + number + "'", adsk.core.ValueInput.createByReal(0.7))
    else:
        text_input = texts.createInput2(number, 0.7)
    text_input.fontName = FONT_NAME
    text_input.isHorizontalFlip = False
    text_input.isVerticalFlip = False
    text_input.setAsMultiLine(point(-15, 97, 0), point(15, 107, 0),
        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
        adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    entity = texts.add(text_input)
    extrusion = root.features.extrudeFeatures.createInput(entity,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrusion.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByReal(1.2)), adsk.fusion.ExtentDirections.NegativeExtentDirection)
    feature = root.features.extrudeFeatures.add(extrusion)
    glyphs = list(feature.bodies)
    if not glyphs:
        raise RuntimeError("No raised lettering generated for player number " + number)
    placement = adsk.core.Matrix3D.create()
    placement.setToRotation(math.pi / 2, vector(1, 0, 0), point(0, 0, 0))
    placement.translation = vector(0, -(BALL_RADIUS_MM + RAISED_TEXT_MM + 0.2) / 10, 0)
    # Concentric shells give each numeral the actual spherical curvature.
    outside = manager.createSphere(point(*center), (BALL_RADIUS_MM + RAISED_TEXT_MM) / 10)
    inside = manager.createSphere(point(*center), (BALL_RADIUS_MM - 1.2) / 10)
    digits = []
    for index, glyph in enumerate(glyphs, 1):
        shape = manager.copy(glyph)
        glyph.deleteMe()
        if not manager.transform(shape, placement):
            raise RuntimeError("Could not position volleyball player number.")
        boolean(manager, shape, outside, adsk.fusion.BooleanTypes.IntersectionBooleanType, "curved number outside")
        boolean(manager, shape, inside, adsk.fusion.BooleanTypes.DifferenceBooleanType, "curved number inside")
        # Preserve the digit's embedded anchor and trim the white ball around it.
        # Replace through a feature cut so the original ball reference survives.
        digit = root.bRepBodies.add(shape)
        digit.name = "Number {} - Medium Blue - {:02d}".format(number, index)
        tools = adsk.core.ObjectCollection.create()
        tools.add(digit)
        cut = root.features.combineFeatures.createInput(ball, tools)
        cut.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
        cut.isKeepToolBodies = True
        root.features.combineFeatures.add(cut)
        if not digit.isSolid or digit.lumps.count != 1:
            raise RuntimeError("Number character is not a connected solid.")
        digits.append(digit)
    if not ball.isSolid or ball.lumps.count != 1:
        raise RuntimeError("Player number lettering disconnected the white ball.")
    sketch.isVisible = False
    write_run_log("NUMBER OK: {!r}; {} curved raised medium blue bodies on the volleyball front."
                  .format(number, len(digits)))
    return digits


def volleyball_net(manager):
    """Fine connected weave with a gentle front/back wave between posts."""
    union = adsk.fusion.BooleanTypes.UnionBooleanType
    net = manager.createCylinderOrCone(point(-31, 0, 30), 0.18,
                                       point(-31, 0, 72), 0.18)
    # The wave returns to Y=0 at both posts and crosses the center stand.
    # Sample at half the mesh spacing so each vertical strand meets a joint.
    samples = [(x, 1.5 * math.sin(2 * math.pi * index / 32))
               for index in range(33) for x in (-31 + index * 62 / 32,)]

    def add_wavy_row(z, radius):
        # Build the row independently. Joining individual segments into an
        # existing grid creates tangent/coincident faces at strand crossings.
        # Slightly larger junctions keep the segment connections overlapping.
        x, y = samples[0]
        row = manager.createSphere(point(x, y, z), (radius + 0.06) / 10)
        for index in range(32):
            x0, y0 = samples[index]
            x1, y1 = samples[index + 1]
            strand = manager.createCylinderOrCone(point(x0, y0, z), radius / 10,
                                                  point(x1, y1, z), radius / 10)
            boolean(manager, row, strand, union,
                    "net row {:.2f} segment {}".format(z, index))
            joint = manager.createSphere(point(x1, y1, z), (radius + 0.06) / 10)
            boolean(manager, row, joint, union, "overlapping net joint")
        boolean(manager, net, row, union, "complete net row {:.2f}".format(z))
        adsk.doEvents()

    add_wavy_row(70, 0.65)
    right_post = manager.createCylinderOrCone(point(31, 0, 30), 0.18,
                                              point(31, 0, 72), 0.18)
    boolean(manager, net, right_post, union, "right net post")
    add_wavy_row(44, 0.65)
    for index in range(1, 8):
        add_wavy_row(44 + index * 3.25, 0.4)
    # 3.875 x 3.25 mm mesh, with 0.8 mm diameter strands.
    for index in range(2, 32, 2):
        x, y = samples[index]
        strand = manager.createCylinderOrCone(point(x, y, 44), 0.04,
                                              point(x, y, 70), 0.04)
        boolean(manager, net, strand, union, "fine vertical net strand")
    write_run_log("NET OK: 3.875 x 3.25 mm weave; 0.8 mm strands; 1.5 mm wave amplitude.")
    return net


def run(context):
    ui = None
    automated = isinstance(context, dict) and context.get("automated", False)
    stage = "initialization"
    write_run_log('START: ' + str(Path(__file__).resolve()), reset=True)
    write_run_log("CONFIG: player={!r}; height={} mm; inlay depth={} mm; separate bodies"
                  .format(PLAYER_NAME, TOTAL_HEIGHT_MM, ENGRAVE_DEPTH_MM))
    try:
        manifest = json.loads(Path(__file__).resolve().with_suffix('.manifest').read_text(encoding='utf-8'))
        prototype_version = manifest['version']
        write_run_log('PROTOTYPE VERSION: ' + str(prototype_version))
        app = adsk.core.Application.get()
        ui = app.userInterface
        name = PLAYER_NAME.strip()
        number = PLAYER_NUMBER.strip()
        if not number.startswith("#") or not number[1:].isascii() or not number[1:].isdigit() or len(number) > 4:
            raise ValueError("PLAYER_NUMBER must be # followed by 1–3 digits, such as #6.")
        if not name or len(name) > 24 or any(c in name for c in "\r\n"):
            raise ValueError("PLAYER_NAME must contain 1–24 characters on one line.")
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        # Direct modeling allows reliable insertion of temporary BRep solids.
        design.designType = adsk.fusion.DesignTypes.DirectDesignType
        assembly = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        root = assembly.component
        root.name = "Trophy"
        # All material bodies belong to one exportable component.
        manager = adsk.fusion.TemporaryBRepManager.get()
        union = adsk.fusion.BooleanTypes.UnionBooleanType

        stage = "separate base and stand"
        write_run_log("STAGE: " + stage)
        base_shape = tapered_base(manager)
        stand_shape = twisted_stand(root, manager)

        stage = "volleyball seams (may take a minute)"
        write_run_log("STAGE: " + stage)
        center = (0, 0, TOTAL_HEIGHT_MM - BALL_RADIUS_MM)
        ball_shape = volleyball(manager, center)
        # Keep the complete volleyball. Its matching seat is removed from
        # the stand, so two filaments never compete for the same volume.
        boolean(manager, stand_shape, ball_shape,
                adsk.fusion.BooleanTypes.DifferenceBooleanType, "ball seat in stand")
        stage = "black volleyball net and posts through stand"
        write_run_log("STAGE: " + stage)
        net_shape = volleyball_net(manager)
        boolean(manager, stand_shape, net_shape,
                adsk.fusion.BooleanTypes.DifferenceBooleanType, "net passage through stand")
        base = root.bRepBodies.add(base_shape)
        base.name = "Base - Metallic Bronze"
        stand = root.bRepBodies.add(stand_shape)
        stand.name = "Stand - Black"
        ball = root.bRepBodies.add(ball_shape)
        ball.name = "Volleyball - White"

        stage = "raised white lettering on tapered base"
        write_run_log("STAGE: " + stage)
        name_height = min(7.0, 74.0 / (max(len(name), 1) * 0.62))
        lettering = []
        lettering.extend(inlay_line(root, base, "Player name", name, 15, 28, name_height))
        lettering.extend(inlay_line(root, base, "Organization line 1",
                                    "2026 Valley Catholic", 5, 13, 4.5))
        stage = "joining all writing into one solid"
        write_run_log("STAGE: " + stage)
        base, writing = join_writing(root, manager, base, lettering)
        lettering = [writing]
        base.name = "Base - Metallic Bronze"
        stage = "raised medium blue player number on volleyball"
        write_run_log("STAGE: " + stage)
        number_glyphs = ball_number(root, manager, ball, center)
        net = root.bRepBodies.add(net_shape)
        net.name = "Net and Posts - Black"

        if CAD_Y_UP:
            stage = "orienting trophy Y-up, front toward +Z"
            write_run_log("STAGE: " + stage)
            # Rotate the completed solid, including all engraved surfaces.
            # (x, y, z) -> (x, z, -y): original +Z becomes +Y, front -Y becomes +Z.
            upright = adsk.core.Matrix3D.create()
            upright.setToRotation(-math.pi / 2, vector(1, 0, 0), point(0, 0, 0))
            entities = adsk.core.ObjectCollection.create()
            for body in root.bRepBodies:
                entities.add(body)
            moves = root.features.moveFeatures
            move_input = moves.createInput2(entities)
            if not move_input.defineAsFreeMove(upright):
                raise RuntimeError("Could not define the Y-up orientation.")
            moves.add(move_input)

        stage = "final multipart validation"
        write_run_log("STAGE: " + stage)
        expected_count = 4 + len(lettering) + len(number_glyphs)
        if root.bRepBodies.count != expected_count:
            raise RuntimeError("Expected {} separate bodies, found {}.".format(
                expected_count, root.bRepBodies.count))
        for body in root.bRepBodies:
            if not body.isSolid or body.lumps.count != 1 or body.volume <= 0:
                raise RuntimeError("Invalid printable body: " + body.name)
        axis = "y" if CAD_Y_UP else "z"
        minimum = min(getattr(body.boundingBox.minPoint, axis) for body in root.bRepBodies)
        maximum = max(getattr(body.boundingBox.maxPoint, axis) for body in root.bRepBodies)
        height = (maximum - minimum) * 10
        if abs(minimum * 10) > 0.01:
            raise RuntimeError("The base underside must be on the build plane.")
        if abs(height - TOTAL_HEIGHT_MM) > 0.1:
            raise RuntimeError("Unexpected overall height: {:.3f} mm".format(height))

        stage = "metallic bronze, black, white, and medium blue filament appearances"
        write_run_log("STAGE: " + stage)
        white = filament_appearance(design, base.appearance, 'Filament - White', (255, 255, 255))
        black = filament_appearance(design, base.appearance, 'Filament - Black', (0, 0, 0))
        blue = filament_appearance(design, base.appearance, 'Filament - Medium Blue', (64, 128, 192))
        bronze = bronze_appearance(design)
        base.appearance = bronze
        stand.appearance = black
        net.appearance = black
        ball.appearance = white
        for body in lettering:
            body.appearance = white
        for body in number_glyphs:
            body.appearance = blue
        write_run_log('COLORS: metallic bronze (base); black (stand, net, posts); '
                      'white (volleyball, base writing); medium blue (player number).')

        # Look toward the engraved +Z face, with +Y up.
        camera = app.activeViewport.camera
        camera.target = point(0, 63.5, 0) if CAD_Y_UP else point(0, 0, 63.5)
        camera.eye = point(150, 145, 260) if CAD_Y_UP else point(150, -260, 145)
        camera.upVector = vector(0, 1, 0) if CAD_Y_UP else vector(0, 0, 1)
        camera.isFitView = True
        app.activeViewport.camera = camera
        write_run_log(
            'SUCCESS: height={:.3f} mm; export component Trophy; '
            '4 structural bodies + 1 white writing + {} medium blue number characters. '
            'Ready for manual Fusion 3MF export. Print not verified.'
            .format(height, len(number_glyphs)))
        if not automated:
            export_message = (
                "Right-click Trophy > Save As Mesh.\n"
                "Format: 3MF; units: millimeters; structure: One File.\n"
                "Save as Trophy.3mf. Import all bodies as one multipart object.\n")
            ui.messageBox(
                "Created a {:.1f} mm (5 inch) trophy for {}.\n\n".format(height, name) +
                "Metallic-bronze base, twisted stand, black net/posts, raised name and medium blue {}.\n".format(number) +
                ("Orientation: +Y up, engraving facing +Z.\n" if CAD_Y_UP else
                 "Orientation: +Z up, engraving facing -Y; ready for manual mesh export.\n") +
                "Colors: BRONZE base; BLACK stand/net/posts; WHITE ball/writing; BLUE number.\n"
                "Save the Fusion design.\n" + export_message +
                "Assign metallic bronze, black, white, and medium blue parts to the matching reels.\n"
                "Run results are saved in Trophy.log beside the script.\n\n"
                "Change PLAYER_NAME and PLAYER_NUMBER at the top and rerun for another player.",
                "Valley Catholic volleyball trophy")
    except Exception:
        message = "Trophy creation stopped during {}.\n\n{}".format(stage, traceback.format_exc())
        write_run_log('ERROR: ' + message)
        if automated:
            raise
        if ui:
            ui.messageBox(message, "Trophy script error")
        else:
            print(message)
