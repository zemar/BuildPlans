"""Run in Autodesk Fusion, Utilities > Scripts and Add-Ins > Scripts.

Creates a seven-tier staircase rack for 56 nail polish bottles (7 rows of 8)
in a NEW Fusion document. All design inputs are mm; Fusion works in cm.

The rack is ONE solid printable object: seven steps, each 40 mm higher than
the one in front, with a row of 20 mm deep bottle holes sunk into every step.
The front step is 22 mm thick: the hole depth plus a 2 mm floor. Every vertical outside corner, including the ends of
each riser, is rounded to R10; seen from above, each step has rounded corners. There is
no joinery. The footprint fits the Bambu Lab H2D build plate, inside the
300 x 320 mm area that both nozzles can reach (see the ridges below).

Both side faces carry vertical half-round ridges, 5 mm wide and 1 mm apart,
standing 2.5 mm proud and running from the base to the top of the step they
are on. The front face of the bottom tier carries the same ridges, except
across a flat panel in the middle, which is bordered by a raised frame with
rounded corners. The ridges make the rack 304 mm wide and 296.5 mm deep, so
it goes on the 300 x 320 mm plate area turned a quarter turn. The ridges
are left off the 11 mm strip under each door hinge.

The words "Naked Nails" are inlaid in black, flush with the flat panel on
the front face of the bottom tier. The letters are separate black bodies inside the PolishRack
component, filling matching recesses in the pink body.

A storage compartment runs right through the rack from side to side, in the
dead space under the steps. Its roof slopes up towards the back at 45 degrees,
following the staircase, so it prints without supports. Each end is closed by
a print-in-place door, flush with the side face and carrying the same ridges:
  - The door is a separate body with 0.5 mm clearance all round. It stands on
    the build plate, so the floor is notched under it.
  - It closes against a 3 mm lip inside the opening.
  - Its top edge stops 1 mm below the roof line and is bevelled steeply back
    from the outer face. The hinge axis is outside the wall, so the hinged
    end moves forward, under the falling roof line, as the door starts to
    open; the relief and bevel give it room. The gap along the top of the
    door is therefore about 1.2 mm, against 0.5 mm on the other edges.
  - The hinge is at the back edge, outside the side face: a vertical pin that
    is part of the door turns inside three rings that are part of the rack.
    Every hinge part that starts above the plate has a 45 degree underside.
  - A small fin near the front edge is the handle. There is no latch.
The hinges make the rack 316 mm wide, so it goes on the 300 x 320 mm plate
area turned a quarter turn. Print without a brim so the doors stay free.

Components. Everything is under the one PolishRack component, so selecting
it for Save As Mesh exports the whole object. Inside it are three child
components: PolishRack_Body (the rack body and the black letter bodies),
PolishRack_Door_Left and PolishRack_Door_Right. Each door is tied to the body
by a revolute joint on its hinge pin, limited to 0..180 degrees of opening,
so the doors can be dragged or animated: right-click a joint in the browser
and choose Animate Joint, or use Assemble > Motion Study for both together.

Print flat on its base, no supports. Appearances are cosmetic: assign pink and
black PLA in the slicer. Export the PolishRack component with Save As Mesh.
"""

from pathlib import Path
import logging
import math
import traceback

import adsk.core
import adsk.fusion


# Bottles and layout, in millimeters. Edit and rerun for a new revision.
BOTTLE_WIDTH = 32.0
BOTTLE_HEIGHT = 85.0                # Reference only; bottles stand proud
ROWS = 7                            # One tier (step) per row
COLUMNS = 8
STEP_RISE = 40.0                    # Each step above the one in front of it
HOLE_WIDTH = 34.0
HOLE_CORNER_RADIUS = HOLE_WIDTH / 2  # Plan view: half the width = round hole;
                                     # smaller = rounded square (square bottles)
HOLE_EDGE_RADIUS = 1.0              # Rounded upper rim of every hole
HOLE_GAP = 3.0                      # Between neighbouring holes in a row
ROW_MARGIN = 4.0                    # In front of and behind each hole
END_MARGIN = 3.0                    # Left/right of the end holes
HOLE_DEPTH = 20.0                   # Below the top of each step
BASE_FLOOR = 2.0                    # Left under the front row of holes
TIER_THICKNESS = HOLE_DEPTH + BASE_FLOOR  # Height of the front step
CORNER_RADIUS = 10.0                # Vertical outside corners of every step
MIN_WALL = 2.0                      # Least material between a hole and a corner

# Vertical half-round ridges on both side faces.
RIDGE_WIDTH = 5.0                   # Diameter; each ridge stands half of this proud
RIDGE_GAP = 1.0                     # Flat left between neighbouring ridges
RIDGE_OVERLAP = 0.5                 # Ridge root sunk into the side wall to merge

# Raised frame around the flat text panel on the front face.
FRAME_WIDTH = 106.0                 # Outside of the frame, centred on the face
FRAME_MARGIN = 1.0                  # Frame to the top and bottom of the face
FRAME_BAND = 2.0                    # Width of the raised band
FRAME_HEIGHT = 1.0                  # How far the band stands proud
FRAME_CORNER_RADIUS = 3.0           # Outside corners; inside = this less the band

# Black lettering inlaid flush in the front face of the bottom tier.
TEXT = 'Naked Nails'
TEXT_FONT = 'Arial'
TEXT_HEIGHT = 12.0                  # Font height
TEXT_DEPTH = 0.8                    # Inlay depth behind the front face

# Through compartment under the steps; one door on each side face.
# The door outline, seen from the side: front edge, back (hinge) edge, the
# plate, and a roof line rising 45 degrees towards the back.
DOOR_FRONT = 90.0                   # Y of the door's front edge
DOOR_BACK = 270.0                   # Y of the door's back (hinge) edge
ROOF_DROP = 52.0                    # Roof height = Y - ROOF_DROP
DOOR_THICKNESS = 4.0
DOOR_GAP = 0.5                      # Clearance round the door and behind it
DOOR_LIP = 3.0                      # Stop inside the opening; the tunnel is this much smaller
DOOR_TOP_BEVEL = 3.5                # Top edge drops this much per mm of door thickness
DOOR_TOP_RELIEF = 1.0               # Door top edge and ridges stop this far below the roof line
COMPARTMENT_FLOOR = 3.0
HINGE_PIN_RADIUS = 2.0              # Pin, part of the door
HINGE_GAP = 0.4                     # Radial clearance between pin and rings
HINGE_WALL = 1.6                    # Ring wall thickness
HINGE_STANDOFF = 0.5                # Rings clear of the side face
HINGE_RINGS = 3                     # Rings on the rack, per door
HINGE_RING_HEIGHT = 20.0
HINGE_AXIAL_GAP = 0.5               # Between a ring and the door leaves above and below
HINGE_TOP_MARGIN = 6.0              # Pin top below the top of the door's hinge edge
HANDLE_REACH = 8.0                  # Handle fin: how far it stands out
HANDLE_WIDTH = 4.0
HANDLE_HEIGHT = 30.0
HANDLE_INSET = 9.0                  # Fin centre behind the door's front edge

# Bambu Lab H2D: 300 x 320 mm is reachable by both nozzles (325 x 320 by one).
PLATE_WIDTH = 300.0
PLATE_DEPTH = 320.0
PLATE_HEIGHT = 325.0

ROW_PITCH = HOLE_WIDTH + 2 * ROW_MARGIN
COLUMN_PITCH = HOLE_WIDTH + HOLE_GAP
TOTAL_WIDTH = 2 * END_MARGIN + COLUMNS * HOLE_WIDTH + (COLUMNS - 1) * HOLE_GAP
TOTAL_DEPTH = ROWS * ROW_PITCH
TOTAL_HEIGHT = TIER_THICKNESS + (ROWS - 1) * STEP_RISE
RIDGED_WIDTH = TOTAL_WIDTH + RIDGE_WIDTH           # Across the side ridges
HINGE_RING_RADIUS = HINGE_PIN_RADIUS + HINGE_GAP + HINGE_WALL
HINGE_REACH = HINGE_STANDOFF + 2 * HINGE_RING_RADIUS   # Outside the side face
HINGE_Y = DOOR_BACK + DOOR_GAP / 2                 # Hinge axis, on the gap line
HINGE_STRIP = HINGE_RING_RADIUS + 1.5              # Half width kept clear of ridges
HINGE_TOP = DOOR_BACK - ROOF_DROP - HINGE_TOP_MARGIN   # Top of the pin
OVERALL_WIDTH = TOTAL_WIDTH + 2 * max(HINGE_REACH, HANDLE_REACH, RIDGE_WIDTH / 2)
OVERALL_DEPTH = TOTAL_DEPTH + RIDGE_WIDTH / 2      # Including the front ridges
FRAME_X = ((TOTAL_WIDTH - FRAME_WIDTH) / 2, (TOTAL_WIDTH + FRAME_WIDTH) / 2)
FRAME_Z = (FRAME_MARGIN, TIER_THICKNESS - FRAME_MARGIN)
PINK = (247, 140, 185)
BLACK = (20, 20, 20)

NAME = 'PolishRack'
LOG_PATH = Path(__file__).resolve().with_suffix('.log')
LOGGER = logging.getLogger(NAME)
HEALTHY = adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
NEW_BODY = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
CUT = adsk.fusion.FeatureOperations.CutFeatureOperation


def step_top(row):
    """Height of the top face of a step; row 0 is the front."""
    return TIER_THICKNESS + row * STEP_RISE


def validate():
    values = [BOTTLE_WIDTH, BOTTLE_HEIGHT, TIER_THICKNESS, HOLE_WIDTH,
              HOLE_CORNER_RADIUS, HOLE_EDGE_RADIUS, HOLE_GAP, ROW_MARGIN,
              END_MARGIN, HOLE_DEPTH, STEP_RISE, CORNER_RADIUS]
    assert all(math.isfinite(v) and v > 0 for v in values), 'Dimensions must be positive'
    assert ROWS >= 1 and COLUMNS >= 1
    assert HOLE_WIDTH > BOTTLE_WIDTH, 'Holes must be wider than the bottles'
    assert HOLE_CORNER_RADIUS <= HOLE_WIDTH / 2 + 1e-9
    assert HOLE_EDGE_RADIUS < HOLE_DEPTH < TIER_THICKNESS + STEP_RISE
    assert 0 < BASE_FLOOR < TIER_THICKNESS - HOLE_EDGE_RADIUS
    assert 2 * HOLE_EDGE_RADIUS < min(HOLE_GAP, 2 * ROW_MARGIN, 2 * END_MARGIN,
                                      2 * HOLE_CORNER_RADIUS)
    # Wall left between a rounded corner and the nearest (round) hole rim.
    assert CORNER_RADIUS < min(ROW_PITCH, TOTAL_WIDTH / 2)
    reach = HOLE_WIDTH / 2 + HOLE_EDGE_RADIUS
    wall = min(math.hypot(END_MARGIN + HOLE_WIDTH / 2 - CORNER_RADIUS, ROW_PITCH / 2),
               math.hypot(END_MARGIN + HOLE_WIDTH / 2, ROW_PITCH / 2 - CORNER_RADIUS)) - reach
    assert wall >= MIN_WALL, 'Corner radius leaves only %.2f mm beside the end holes' % wall
    assert TEXT and 0 < TEXT_DEPTH <= ROW_MARGIN - MIN_WALL, 'Text inlay too deep'
    assert RIDGE_WIDTH > 0 and RIDGE_GAP > 0
    # The ridge roots must stay inside the end wall, clear of the hole rims.
    assert 0 < RIDGE_OVERLAP < END_MARGIN - HOLE_EDGE_RADIUS
    # Either way round on the plate.
    assert 0 < FRAME_HEIGHT <= RIDGE_WIDTH / 2 and FRAME_BAND < FRAME_CORNER_RADIUS
    assert FRAME_CORNER_RADIUS < (FRAME_Z[1] - FRAME_Z[0]) / 2
    assert FRAME_X[0] - RIDGE_GAP - RIDGE_WIDTH >= CORNER_RADIUS, 'Frame too wide'
    assert TEXT_HEIGHT <= FRAME_Z[1] - FRAME_Z[0] - 2 * FRAME_BAND, 'Text too tall for frame'
    # Compartment: roof clear of the holes above it, door edges between ridges.
    assert CORNER_RADIUS < DOOR_FRONT < DOOR_BACK < TOTAL_DEPTH - CORNER_RADIUS - HINGE_STRIP
    assert DOOR_FRONT - ROOF_DROP - DOOR_LIP * math.sqrt(2) > COMPARTMENT_FLOOR + 10
    assert 0 < DOOR_GAP < DOOR_LIP and DOOR_THICKNESS + DOOR_GAP < END_MARGIN + HOLE_WIDTH / 2
    for row in range(ROWS):
        y = min((row + 1) * ROW_PITCH - ROW_MARGIN, DOOR_BACK + DOOR_GAP)
        if y > DOOR_FRONT:
            roof = y - ROOF_DROP + DOOR_GAP * math.sqrt(2)
            assert roof <= step_top(row) - HOLE_DEPTH - MIN_WALL, \
                'Compartment roof too close to the row %d holes' % (row + 1)
    assert DOOR_FRONT - ROOF_DROP <= step_top(int(DOOR_FRONT / ROW_PITCH) - 1) - HOLE_DEPTH \
        - MIN_WALL, 'Door front edge too tall for the step in front of it'
    for y in side_ridge_centers():
        for edge in (DOOR_FRONT - DOOR_GAP, DOOR_FRONT, DOOR_BACK, DOOR_BACK + DOOR_GAP):
            assert abs(y - edge) >= RIDGE_WIDTH / 2 - 1e-9, \
                'A side ridge straddles the door edge at Y=%s' % edge
    # Bevel: as the door opens, a point d mm behind the outer face moves up
    # to sqrt(d*d + 2*a*d) forward before it leaves the wall (a = hinge axis
    # offset), and the roof falls 1 mm per mm forward.
    offset = HINGE_STANDOFF + HINGE_RING_RADIUS
    for step in range(1, 41):
        d = DOOR_THICKNESS * step / 40
        assert DOOR_TOP_BEVEL * d + DOOR_GAP * math.sqrt(2) >= math.sqrt(d * d + 2 * offset * d), \
            'Door top bevel too shallow to swing clear of the roof'
    # Door ridges: the nearest one to the hinge moves forward the most.
    nearest = min(HINGE_Y - y for y in side_ridge_centers() if y < DOOR_BACK) - RIDGE_WIDTH / 2
    assert offset * offset / (2 * nearest) <= DOOR_TOP_RELIEF + DOOR_GAP * math.sqrt(2), \
        'Door ridges need more relief to swing clear'
    leaf = (HINGE_TOP - HINGE_RINGS * (HINGE_RING_HEIGHT + 2 * HINGE_AXIAL_GAP)) / (HINGE_RINGS + 1)
    assert leaf >= HINGE_REACH + 4 and HINGE_RING_HEIGHT >= HINGE_REACH + 4, 'Hinge too short'
    assert HANDLE_HEIGHT < DOOR_FRONT - ROOF_DROP
    short, long = sorted((OVERALL_WIDTH, OVERALL_DEPTH))
    assert short <= min(PLATE_WIDTH, PLATE_DEPTH) and long <= max(PLATE_WIDTH, PLATE_DEPTH) \
        and TOTAL_HEIGHT <= PLATE_HEIGHT, 'Rack %s x %s x %s does not fit the build plate' % (
            OVERALL_WIDTH, OVERALL_DEPTH, TOTAL_HEIGHT)


def point(x, y, z=0.0):
    return adsk.core.Point3D.create(x / 10.0, y / 10.0, z / 10.0)


def distance(mm):
    return adsk.core.ValueInput.createByString('{} mm'.format(mm))


def check(feature, name):
    if not feature or feature.healthState != HEALTHY:
        raise RuntimeError('%s failed: %s' % (
            name, feature.errorOrWarningMessage if feature else 'no feature returned'))
    feature.name = name
    return feature


def all_profiles(sketch, expected, name):
    """Every profile of the sketch; expected=None accepts any number."""
    if expected is None:
        expected = max(sketch.profiles.count, 1)
    if sketch.profiles.count != expected:
        raise RuntimeError('%s: expected %d profiles, found %d' % (
            name, expected, sketch.profiles.count))
    profiles = adsk.core.ObjectCollection.create()
    for profile in sketch.profiles:
        profiles.add(profile)
    return profiles


def extrude(component, sketch, expected, length, operation, name, body=None):
    """Extrude every profile of the sketch, acting on one body only: the
    rack unless another body is given.

    Without participantBodies a cut or join also acts on any other visible
    body it touches, including bodies in other components.
    """
    extrudes = component.features.extrudeFeatures
    setup = extrudes.createInput(all_profiles(sketch, expected, name), operation)
    setup.setDistanceExtent(False, distance(length))
    if operation != NEW_BODY:
        setup.participantBodies = [body or component.bRepBodies.item(0)]
    feature = check(extrudes.add(setup), name)
    sketch.isVisible = False
    return feature


def xy_sketch(component, z, name):
    plane = component.xYConstructionPlane
    if z:
        setup = component.constructionPlanes.createInput()
        setup.setByOffset(plane, distance(z))
        plane = component.constructionPlanes.add(setup)
        plane.name = name + ' plane'
        plane.isLightBulbOn = False
    sketch = component.sketches.add(plane)
    sketch.name = name + ' sketch'
    return sketch


def draw_hole(sketch, cx, cy):
    """Round hole, or a rounded square when the corner radius is reduced."""
    half = HOLE_WIDTH / 2
    radius = HOLE_CORNER_RADIUS
    curves = sketch.sketchCurves
    if radius >= half - 1e-6:
        curves.sketchCircles.addByCenterRadius(point(cx, cy), half / 10.0)
        return
    inner = half - radius
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        # Counterclockwise quarter arc, then the straight side that follows it.
        if sx == sy:
            start = (cx + sx * half, cy + sy * inner)
            end = (cx + sx * inner, cy + sy * half)
            side_end = (cx - sx * inner, cy + sy * half)
        else:
            start = (cx + sx * inner, cy + sy * half)
            end = (cx + sx * half, cy + sy * inner)
            side_end = (cx + sx * half, cy - sy * inner)
        curves.sketchArcs.addByCenterStartSweep(
            point(cx + sx * inner, cy + sy * inner), point(*start), math.pi / 2)
        curves.sketchLines.addByTwoPoints(point(*end), point(*side_end))


def cut_holes(component, row):
    """Sink one row of holes into the top of its step."""
    top = step_top(row)
    bottom = max(top - HOLE_DEPTH, BASE_FLOOR) if row == 0 else top - HOLE_DEPTH
    name = 'Row %d holes' % (row + 1)
    sketch = xy_sketch(component, bottom, name)
    sketch.isComputeDeferred = True
    try:
        for column in range(COLUMNS):
            draw_hole(sketch, END_MARGIN + HOLE_WIDTH / 2 + column * COLUMN_PITCH,
                      (row + 0.5) * ROW_PITCH)
    finally:
        sketch.isComputeDeferred = False
    extrude(component, sketch, COLUMNS, top - bottom, CUT,
            '%s - %d x %.0f mm' % (name, COLUMNS, HOLE_WIDTH))


def round_corners(component):
    """Fillet the vertical edges where the two side faces meet the front,
    the back and every riser."""
    edges = adsk.core.ObjectCollection.create()
    eps = 1e-4  # cm
    for edge in component.bRepBodies.item(0).edges:
        low, high = edge.boundingBox.minPoint, edge.boundingBox.maxPoint
        if (high.x - low.x < eps and high.y - low.y < eps and high.z - low.z > eps
                and (low.x < eps or high.x > TOTAL_WIDTH / 10 - eps)):
            edges.add(edge)
    if edges.count != 2 * (ROWS + 1):
        raise RuntimeError('Expected %d corner edges; found %d' % (
            2 * (ROWS + 1), edges.count))
    setup = component.features.filletFeatures.createInput()
    setup.edgeSetInputs.addConstantRadiusEdgeSet(edges, distance(CORNER_RADIUS), False)
    check(component.features.filletFeatures.add(setup),
          'Rounded corners - R%.1f mm' % CORNER_RADIUS)
    LOGGER.info('Rounded %d vertical corner edges', edges.count)


def round_hole_rims(component):
    """Fillet every edge lying in a step's top face, inside that step's outline."""
    edges = adsk.core.ObjectCollection.create()
    eps = 1e-4  # cm
    for edge in component.bRepBodies.item(0).edges:
        low, high = edge.boundingBox.minPoint, edge.boundingBox.maxPoint
        if abs(high.z - low.z) > eps or low.x < eps or high.x > TOTAL_WIDTH / 10 - eps:
            continue
        for row in range(ROWS):
            if (abs(low.z - step_top(row) / 10) < eps
                    and low.y > row * ROW_PITCH / 10 + eps
                    and high.y < (row + 1) * ROW_PITCH / 10 - eps):
                edges.add(edge)
    if edges.count < ROWS * COLUMNS:
        raise RuntimeError('Expected hole rim edges; found %d' % edges.count)
    setup = component.features.filletFeatures.createInput()
    setup.edgeSetInputs.addConstantRadiusEdgeSet(edges, distance(HOLE_EDGE_RADIUS), False)
    check(component.features.filletFeatures.add(setup),
          'Hole rims - R%.1f mm' % HOLE_EDGE_RADIUS)
    LOGGER.info('Rounded %d hole rim edges', edges.count)


def side_ridge_centers():
    """Ridge centres along Y on a side face: on the flat between the rounded
    corners, leaving the strip under the door hinge clear."""
    radius = RIDGE_WIDTH / 2
    centers = spaced_centers(CORNER_RADIUS + radius, TOTAL_DEPTH - CORNER_RADIUS - radius)
    return [y for y in centers if abs(y - HINGE_Y) >= HINGE_STRIP + radius]


def ridge_layout():
    """Side ridge centres grouped by the height each ridge reaches.

    A ridge that would run into the rounded end of a riser stops at the step
    in front of it instead.
    """
    groups = {}
    for y in side_ridge_centers():
        row = min(int(y / ROW_PITCH), ROWS - 1)
        if y - RIDGE_WIDTH / 2 < row * ROW_PITCH + CORNER_RADIUS - 1e-9:
            row -= 1
        if row >= 0:
            groups.setdefault(step_top(row), []).append(y)
    return groups


def spaced_centers(first, last):
    """Ridge centres at the ridge pitch, centred in the span first..last."""
    pitch = RIDGE_WIDTH + RIDGE_GAP
    if last < first:
        return []
    count = int((last - first) / pitch + 1e-9) + 1
    start = (first + last - (count - 1) * pitch) / 2
    return [start + i * pitch for i in range(count)]


def draw_ridge(sketch, along, face, out, vertical_face):
    """Half-round section on a face, with a short root sunk into the wall.

    `along` is the ridge centre along the face, `face` the face position and
    `out` the outward direction (+1 or -1). vertical_face: True for the side
    faces (constant X), False for the front face (constant Y).
    """
    radius = RIDGE_WIDTH / 2
    root = face - out * RIDGE_OVERLAP

    def at(across, position):
        return point(across, position) if vertical_face else point(position, across)

    curves = sketch.sketchCurves
    curves.sketchArcs.addByThreePoints(
        at(face, along - radius), at(face + out * radius, along), at(face, along + radius))
    curves.sketchLines.addByTwoPoints(at(face, along + radius), at(root, along + radius))
    curves.sketchLines.addByTwoPoints(at(root, along + radius), at(root, along - radius))
    curves.sketchLines.addByTwoPoints(at(root, along - radius), at(face, along - radius))


def add_side_ridges(component):
    """Vertical ridges on both side faces, each to the top of its step."""
    total = 0
    for height, centers in sorted(ridge_layout().items()):
        name = 'Side ridges to %.0f mm' % height
        sketch = xy_sketch(component, 0, name)
        sketch.isComputeDeferred = True
        try:
            for y in centers:
                draw_ridge(sketch, y, 0.0, -1, True)
                draw_ridge(sketch, y, TOTAL_WIDTH, 1, True)
        finally:
            sketch.isComputeDeferred = False
        extrude(component, sketch, 2 * len(centers), height, JOIN, name)
        total += 2 * len(centers)
    LOGGER.info('Added %d side ridges (%d per side)', total, total // 2)
    return total


def add_front_ridges(component):
    """Vertical ridges on the front face of the bottom tier, left and right
    of the framed panel and clear of the rounded corners."""
    radius = RIDGE_WIDTH / 2
    left = spaced_centers(CORNER_RADIUS + radius, FRAME_X[0] - RIDGE_GAP - radius)
    centers = left + [TOTAL_WIDTH - x for x in reversed(left)]
    name = 'Front ridges'
    sketch = xy_sketch(component, 0, name)
    sketch.isComputeDeferred = True
    try:
        for x in centers:
            draw_ridge(sketch, x, 0.0, -1, False)
    finally:
        sketch.isComputeDeferred = False
    extrude(component, sketch, len(centers), TIER_THICKNESS, JOIN, name)
    LOGGER.info('Added %d front ridges, x %.1f..%.1f and %.1f..%.1f', len(centers),
                left[0], left[-1], centers[len(left)], centers[-1])
    return len(centers)


def front_sketch(component, name):
    """Sketch on the front face (Y = 0). Also returns the signs that map
    sketch X, sketch Y and the sketch normal onto model +X, +Z and +Y."""
    sketch = component.sketches.add(component.xZConstructionPlane)
    sketch.name = name + ' sketch'
    origin = sketch.sketchToModelSpace(point(0, 0, 0))
    right = sketch.sketchToModelSpace(point(10, 0, 0)).x - origin.x
    up = sketch.sketchToModelSpace(point(0, 10, 0)).z - origin.z
    inward = sketch.sketchToModelSpace(point(0, 0, 10)).y - origin.y
    if min(abs(right), abs(up), abs(inward)) < 1 - 1e-8:
        raise RuntimeError('Unexpected front sketch orientation.')
    return sketch, right, up, inward


def add_text_frame(component):
    """Raised band with rounded corners around the flat text panel."""
    name = 'Text frame'
    sketch, right, up, inward = front_sketch(component, name)
    curves = sketch.sketchCurves

    def at(x, z):
        return sketch.modelToSketchSpace(point(x, 0, z))

    for inset, radius in ((0.0, FRAME_CORNER_RADIUS),
                          (FRAME_BAND, FRAME_CORNER_RADIUS - FRAME_BAND)):
        x0, x1 = FRAME_X[0] + inset, FRAME_X[1] - inset
        z0, z1 = FRAME_Z[0] + inset, FRAME_Z[1] - inset
        bend = radius * (1 - math.sqrt(0.5))
        # Each corner: (corner x, corner z, direction into the rectangle).
        ends = []
        for cx, cz, dx, dz in ((x0, z0, 1, 1), (x1, z0, -1, 1), (x1, z1, -1, -1), (x0, z1, 1, -1)):
            a, b = (cx, cz + dz * radius), (cx + dx * radius, cz)
            if dx * dz < 0:
                a, b = b, a           # Keep the outline running one way round
            curves.sketchArcs.addByThreePoints(
                at(*a), at(cx + dx * bend, cz + dz * bend), at(*b))
            ends.append((a, b))
        for i, (_, b) in enumerate(ends):
            curves.sketchLines.addByTwoPoints(at(*b), at(*ends[(i + 1) % 4][0]))
    rings = [profile for profile in sketch.profiles if profile.profileLoops.count == 2]
    if sketch.profiles.count != 2 or len(rings) != 1:
        raise RuntimeError('Expected one frame band profile; found %d of %d' % (
            len(rings), sketch.profiles.count))
    extrudes = component.features.extrudeFeatures
    setup = extrudes.createInput(rings[0], JOIN)
    setup.setDistanceExtent(False, distance(-FRAME_HEIGHT / inward))   # Out of the face
    setup.participantBodies = [component.bRepBodies.item(0)]
    check(extrudes.add(setup), '%s - %.1f mm proud' % (name, FRAME_HEIGHT))
    sketch.isVisible = False


def side_sketch(component, x, name):
    """Sketch on a plane of constant X. Returns it with the sign of the
    sketch normal along +X."""
    base = component.yZConstructionPlane
    setup = component.constructionPlanes.createInput()
    setup.setByOffset(base, distance(x / base.geometry.normal.x))
    plane = component.constructionPlanes.add(setup)
    plane.name = name + ' plane'
    plane.isLightBulbOn = False
    sketch = component.sketches.add(plane)
    sketch.name = name + ' sketch'
    origin = sketch.sketchToModelSpace(point(0, 0, 0))
    normal = sketch.sketchToModelSpace(point(0, 0, 10)).x - origin.x
    if abs(abs(normal) - 1) > 1e-8:
        raise RuntimeError('Unexpected side sketch orientation.')
    return sketch, normal


def side_outline(grow, floor):
    """Door outline in (Y, Z), grown outward by `grow` (negative shrinks it).
    The bottom edge is put at `floor`."""
    front, back = DOOR_FRONT - grow, DOOR_BACK + grow
    lift = grow * math.sqrt(2)          # Moves the 45 degree roof line by `grow`
    return [(front, floor), (back, floor),
            (back, back - ROOF_DROP + lift), (front, front - ROOF_DROP + lift)]


def side_prism(component, name, outline, x0, x1, operation, body):
    """Extrude a (Y, Z) outline from X = x0 to X = x1, acting on one body."""
    sketch, normal = side_sketch(component, x0, name)
    corners = [sketch.modelToSketchSpace(point(x0, y, z)) for y, z in outline]
    for i, corner in enumerate(corners):
        sketch.sketchCurves.sketchLines.addByTwoPoints(corner, corners[(i + 1) % len(corners)])
    return extrude(component, sketch, 1, (x1 - x0) / normal, operation, name, body)


def bevel_door_top(component, door, name, face, out):
    """Slope the door's top edge down from its outer face to its back face.

    The cut runs along the roof line, so it is extruded from a plane square
    to that line: one that contains the X axis and leans 45 degrees.
    """
    sketch = None
    for angle in ('135 deg', '45 deg'):
        setup = component.constructionPlanes.createInput()
        setup.setByAngle(component.xConstructionAxis, adsk.core.ValueInput.createByString(angle),
                         component.xYConstructionPlane)
        plane = component.constructionPlanes.add(setup)
        plane.name = name + ' plane'
        plane.isLightBulbOn = False
        sketch = component.sketches.add(plane)
        origin = sketch.sketchToModelSpace(point(0, 0, 0))
        tip = sketch.sketchToModelSpace(point(0, 0, 10))
        along = (tip.y - origin.y, tip.z - origin.z)
        if abs(tip.x - origin.x) < 1e-8 and abs(along[0] - along[1]) < 1e-8:
            break                       # Normal runs along the roof line
        sketch.deleteMe()
        plane.deleteMe()
        sketch = None
    if sketch is None:
        raise RuntimeError('Could not build a plane square to the roof line.')
    sketch.name = name + ' sketch'
    direction = 1 if along[0] > 0 else -1

    def at(depth, rise):
        # On the plane Y + Z = 0, `rise` above the roof line, `depth` into the door.
        y = ROOF_DROP / 2 - rise / 2
        return sketch.modelToSketchSpace(point(face - out * depth, y, -y))

    # The door's outer edge and ridges also swing forward, under the rack's
    # ridges above them, so the whole top edge starts a little below the roof.
    deep = DOOR_THICKNESS + DOOR_GAP / 2
    proud = -(RIDGE_WIDTH / 2 + 1)
    corners = [at(proud, 5), at(proud, -DOOR_TOP_RELIEF),
               at(0, -DOOR_TOP_RELIEF),
               at(deep, -DOOR_TOP_RELIEF - DOOR_TOP_BEVEL * deep), at(deep, 5)]
    for i, corner in enumerate(corners):
        sketch.sketchCurves.sketchLines.addByTwoPoints(corner, corners[(i + 1) % len(corners)])
    extrude(component, sketch, 1, direction * (TOTAL_DEPTH + ROOF_DROP) * math.sqrt(2),
            CUT, name, door)


def hinge_part(component, name, face, out, z0, z1, draw, bore, target):
    """Build one hinge piece as its own body, then merge it into `target`.

    draw(sketch) draws the plan outline. A piece that starts above the plate
    gets a 45 degree underside rising away from the side face, so it grows
    out of the wall without supports.
    """
    sketch = xy_sketch(component, z0, name)
    draw(sketch)
    piece = extrude(component, sketch, None, z1 - z0, NEW_BODY, name).bodies.item(0)
    axis = face + out * (HINGE_STANDOFF + HINGE_RING_RADIUS)
    if bore:
        sketch = xy_sketch(component, z0, name + ' bore')
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            point(axis, HINGE_Y), (HINGE_PIN_RADIUS + HINGE_GAP) / 10.0)
        extrude(component, sketch, 1, z1 - z0, CUT, name + ' bore', piece)
    if z0 > 0:
        reach = HINGE_REACH + 4
        sketch, right, up, inward = front_sketch(component, name + ' underside')
        outline = [(face, z0 - 1), (face + out * reach, z0 - 1),
                   (face + out * reach, z0 + reach), (face, z0)]
        corners = [sketch.modelToSketchSpace(point(x, 0, z)) for x, z in outline]
        for i, corner in enumerate(corners):
            sketch.sketchCurves.sketchLines.addByTwoPoints(
                corner, corners[(i + 1) % len(corners)])
        extrude(component, sketch, 1, TOTAL_DEPTH / inward, CUT, name + ' underside', piece)
    tools = adsk.core.ObjectCollection.create()
    tools.add(piece)
    # Look the target up by name: body references go stale after a merge.
    combine = component.features.combineFeatures.createInput(
        component.bRepBodies.itemByName(target), tools)
    combine.operation = JOIN
    check(component.features.combineFeatures.add(combine), name + ' merge')


def add_door(component, side, face, out):
    """Cut the opening in one side face and leave a hinged door in it.
    Returns the name of the door body."""
    rack = component.bRepBodies.itemByName(NAME + '_Pink')
    door_name = '%s_Door_%s_Pink' % (NAME, side)
    label = side + ' door'
    outside = face + out * (HINGE_REACH + 2)      # Beyond the ridges
    inside = face - out * DOOR_THICKNESS          # Back face of the door

    # The door is the piece of the ridged side wall inside the outline.
    copies = component.features.copyPasteBodies.add(rack)
    door = copies.bodies.item(0)
    door.name = door_name
    side_prism(component, label, side_outline(0.0, 0.0), outside, inside,
               adsk.fusion.FeatureOperations.IntersectFeatureOperation, door)
    bevel_door_top(component, component.bRepBodies.itemByName(door_name),
                   label + ' top bevel', face, out)
    side_prism(component, side + ' door opening', side_outline(DOOR_GAP, -1.0),
               outside, inside - out * DOOR_GAP, CUT,
               component.bRepBodies.itemByName(NAME + '_Pink'))
    door, rack = door_name, NAME + '_Pink'      # Hinge parts merge by body name

    axis = face + out * (HINGE_STANDOFF + HINGE_RING_RADIUS)
    root = face - out * RIDGE_OVERLAP               # Sunk into the wall or the door

    def circle(radius):
        return lambda sketch: sketch.sketchCurves.sketchCircles.addByCenterRadius(
            point(axis, HINGE_Y), radius / 10.0)

    def block(x0, x1, y0, y1):
        return lambda sketch: sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            point(x0, y0), point(x1, y1))

    def both(*shapes):
        return lambda sketch: [shape(sketch) for shape in shapes]

    # Pin and leaves belong to the door; the rings belong to the rack.
    leaf = block(axis + out * HINGE_PIN_RADIUS, root, HINGE_Y - HINGE_RING_RADIUS, DOOR_BACK)
    ring = both(circle(HINGE_RING_RADIUS),
                block(axis, root, DOOR_BACK + DOOR_GAP + 0.25, HINGE_Y + HINGE_RING_RADIUS))
    leaf_height = (HINGE_TOP - HINGE_RINGS * (HINGE_RING_HEIGHT + 2 * HINGE_AXIAL_GAP)) \
        / (HINGE_RINGS + 1)
    z = 0.0
    for number in range(HINGE_RINGS + 1):
        hinge_part(component, '%s hinge leaf %d' % (label, number + 1), face, out,
                   z, z + leaf_height, leaf, False, door)
        z += leaf_height + HINGE_AXIAL_GAP
        if number < HINGE_RINGS:
            hinge_part(component, '%s hinge ring %d' % (label, number + 1), face, out,
                       z, z + HINGE_RING_HEIGHT, ring, True, rack)
            z += HINGE_RING_HEIGHT + HINGE_AXIAL_GAP
    # The pin goes in after the leaves: it only touches the door through them.
    hinge_part(component, label + ' hinge pin', face, out, 0.0, HINGE_TOP,
               circle(HINGE_PIN_RADIUS), False, door)
    handle_y = DOOR_FRONT + HANDLE_INSET
    hinge_part(component, label + ' handle', face, out, 0.0, HANDLE_HEIGHT,
               block(face + out * HANDLE_REACH, root,
                     handle_y - HANDLE_WIDTH / 2, handle_y + HANDLE_WIDTH / 2), False, door)
    return door_name


def add_compartment(design, occurrence, appearance):
    """Tunnel through the rack under the steps, with a door at each end."""
    component = occurrence.component
    reach = DOOR_THICKNESS + DOOR_GAP           # Door pocket depth at each end
    side_prism(component, 'Compartment tunnel', side_outline(-DOOR_LIP, COMPARTMENT_FLOOR),
               reach, TOTAL_WIDTH - reach, CUT,
               component.bRepBodies.itemByName(NAME + '_Pink'))
    names = [add_door(component, side, face, out)
             for side, face, out in (('Left', 0.0, -1), ('Right', TOTAL_WIDTH, 1))]
    for name in names:
        if appearance:
            component.bRepBodies.itemByName(name).appearance = appearance
    # Measuring and interference need the bodies as seen from the assembly.
    rack = occurrence.bRepBodies.itemByName(NAME + '_Pink')
    doors = [occurrence.bRepBodies.itemByName(name) for name in names]

    if not rack.isSolid or rack.lumps.count != 1:
        raise RuntimeError('The rack must stay one connected solid.')
    manager = adsk.core.Application.get().measureManager
    for door in doors:
        if not door.isSolid or door.lumps.count != 1:
            raise RuntimeError(door.name + ' must be one connected solid.')
        gap = manager.measureMinimumDistance(door, rack).value * 10
        if gap < min(DOOR_GAP, HINGE_GAP) - 0.06:
            raise RuntimeError('%s is only %.3f mm from the rack' % (door.name, gap))
        low, high = door.boundingBox.minPoint, door.boundingBox.maxPoint
        LOGGER.info('%s: clearance %.3f mm, y %.1f..%.1f, z %.1f..%.1f, volume_cm3=%.2f',
                    door.name, gap, low.y * 10, high.y * 10, low.z * 10, high.z * 10,
                    door.volume)
    bodies = adsk.core.ObjectCollection.create()
    for body in occurrence.bRepBodies:
        bodies.add(body)
    overlaps = design.analyzeInterference(design.createInterferenceInput(bodies)).count
    if overlaps:
        raise RuntimeError('%d overlaps between rack, doors and letters' % overlaps)
    low, high = rack.boundingBox.minPoint, rack.boundingBox.maxPoint
    actual = ((high.x - low.x) * 10, (high.y - low.y) * 10, (high.z - low.z) * 10)
    expected = (OVERALL_WIDTH, OVERALL_DEPTH, TOTAL_HEIGHT)
    if any(abs(a - e) > 0.001 for a, e in zip(actual, expected)):
        raise RuntimeError('Rack dimensions differ: expected %s, got %s' % (expected, actual))
    LOGGER.info('Compartment validated: rack bounds_mm=%s volume_cm3=%.2f',
                tuple(round(a, 3) for a in actual), rack.volume)
    return names


def plastic_appearance(app, design, name, rgb):
    """Use an opaque plastic appearance, compatible with older Fusion versions."""
    for library in app.materialLibraries:
        for source in library.appearances:
            if 'plastic' not in source.name.lower():
                continue
            if adsk.core.ColorProperty.cast(
                    source.appearanceProperties.itemById('opaque_albedo')):
                appearance = design.appearances.addByCopy(source, name)
                prop = adsk.core.ColorProperty.cast(
                    appearance.appearanceProperties.itemById('opaque_albedo'))
                prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
                return appearance
    raise RuntimeError('No editable opaque plastic appearance found in local libraries.')


def front_text(component, name):
    """Sketch the lettering on the front face (Y = 0); return it and the
    sign of the sketch normal along +Y, which points into the rack."""
    sketch, right, up, inward = front_sketch(component, name)
    # The flat panel inside the frame.
    a = sketch.modelToSketchSpace(point(FRAME_X[0] + FRAME_BAND, 0, FRAME_Z[0] + FRAME_BAND))
    b = sketch.modelToSketchSpace(point(FRAME_X[1] - FRAME_BAND, 0, FRAME_Z[1] - FRAME_BAND))
    setup = sketch.sketchTexts.createInput2(TEXT, TEXT_HEIGHT / 10.0)
    setup.setAsMultiLine(
        adsk.core.Point3D.create(min(a.x, b.x), min(a.y, b.y), 0),
        adsk.core.Point3D.create(max(a.x, b.x), max(a.y, b.y), 0),
        adsk.core.HorizontalAlignments.CenterHorizontalAlignment,
        adsk.core.VerticalAlignments.MiddleVerticalAlignment, 0)
    setup.fontName = TEXT_FONT
    setup.textStyle = adsk.fusion.TextStyles.TextStyleBold
    # Read left to right and upright when looking at the front of the rack.
    setup.isHorizontalFlip = right < 0
    setup.isVerticalFlip = up < 0
    return sketch, sketch.sketchTexts.add(setup), inward


def inlay_text(component, appearance):
    """Recess the lettering into the front face and fill it with black bodies."""
    rack = component.bRepBodies.item(0)
    extrudes = component.features.extrudeFeatures
    # One sketch per feature: a second extrude of the same sketch text within
    # one script run is rejected as an invalid argument.
    sketch, text, inward = front_text(component, 'Text recess')
    recess = extrudes.createInput(text, CUT)
    recess.setDistanceExtent(False, distance(TEXT_DEPTH / inward))
    recess.participantBodies = [rack]
    check(extrudes.add(recess), 'Text recess - %.1f mm deep' % TEXT_DEPTH)
    sketch.isVisible = False
    sketch, text, inward = front_text(component, 'Text inlay')
    check(extrudes.addSimple(text, distance(TEXT_DEPTH / inward), NEW_BODY),
          'Text inlay - %.1f mm deep' % TEXT_DEPTH)
    sketch.isVisible = False

    letters = [body for body in component.bRepBodies if body != rack]
    if not letters:
        raise RuntimeError('No text bodies were created.')
    low, high = [1e9] * 3, [-1e9] * 3
    for number, body in enumerate(letters, 1):
        if not body.isSolid:
            raise RuntimeError('Text body is not solid.')
        body.name = '%s_Text_Black_%02d' % (NAME, number)
        if appearance:
            body.appearance = appearance
        low = [min(v, w) for v, w in zip(low, body.boundingBox.minPoint.asArray())]
        high = [max(v, w) for v, w in zip(high, body.boundingBox.maxPoint.asArray())]
    low, high = [v * 10 for v in low], [v * 10 for v in high]
    clear = FRAME_BAND + 0.5    # Letters stay off the frame band
    if (low[0] < FRAME_X[0] + clear or high[0] > FRAME_X[1] - clear
            or low[2] < FRAME_Z[0] + clear or high[2] > FRAME_Z[1] - clear
            or abs(low[1]) > 0.001 or abs(high[1] - TEXT_DEPTH) > 0.001):
        raise RuntimeError('Text does not fit inside the frame: %s .. %s' % (low, high))
    LOGGER.info('Text "%s": %d black bodies, x %.2f..%.2f, z %.2f..%.2f, depth %.2f mm',
                TEXT, len(letters), low[0], high[0], low[2], high[2], high[1] - low[1])
    return len(letters)


def articulate(design, occurrence, door_names):
    """Give the body and each door its own child component and hinge joint.

    The body component is created first and each joint lists the door first:
    that is the arrangement in which Fusion moves the door, not the rack.
    """
    component = occurrence.component
    occurrence.isGrounded = True
    identity = adsk.core.Matrix3D.create()
    body = component.occurrences.addNewComponent(identity)
    body.component.name = NAME + '_Body'
    for name in [b.name for b in component.bRepBodies if b.name not in door_names]:
        component.bRepBodies.itemByName(name).moveToComponent(body)
    doors = []
    for name in door_names:
        side = name.split('_')[2]
        door = component.occurrences.addNewComponent(identity)
        door.component.name = '%s_Door_%s' % (NAME, side)
        component.bRepBodies.itemByName(name).moveToComponent(door)
        pins = [face for face in door.component.bRepBodies.item(0).faces
                if face.geometry.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType
                and abs(face.geometry.radius * 10 - HINGE_PIN_RADIUS) < 1e-3]
        if len(pins) != 1:
            raise RuntimeError('Expected one hinge pin face on %s; found %d' % (name, len(pins)))
        geometry = adsk.fusion.JointGeometry.createByNonPlanarFace(
            pins[0].createForAssemblyContext(door), adsk.fusion.JointKeyPointTypes.MiddleKeyPoint)
        setup = component.asBuiltJoints.createInput(door, body, geometry)
        setup.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        joint = component.asBuiltJoints.add(setup)
        joint.name = side + ' door hinge'
        doors.append((side, door, adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)))
    if component.bRepBodies.count:
        raise RuntimeError('Bodies were left outside the child components.')

    def span(target):
        box = target.createForAssemblyContext(occurrence).bRepBodies.item(0).boundingBox
        return box.minPoint.x * 10, box.maxPoint.x * 10

    rack_span = span(body)
    signs = {}
    for side, door, motion in doors:
        # Find which way is "open": the door must swing out, the rack stay put.
        motion.rotationValue = math.radians(30)
        adsk.doEvents()
        low, high = span(door)
        outward = low < -HINGE_REACH - 1 if side == 'Left' else high > TOTAL_WIDTH + HINGE_REACH + 1
        signs[side] = 1 if outward else -1
        motion.rotationValue = 0
        adsk.doEvents()
        if any(abs(a - b) > 0.001 for a, b in zip(span(body), rack_span)):
            raise RuntimeError('The rack moved instead of the %s door.' % side.lower())
        limits = motion.rotationLimits
        limits.isMinimumValueEnabled = limits.isMaximumValueEnabled = True
        limits.minimumValue = 0 if outward else -math.pi
        limits.maximumValue = math.pi if outward else 0
        LOGGER.info('%s door hinge: opens towards %s180 degrees', side, '+' if outward else '-')

    # Swing check: both doors part open and wide open must not touch the rack.
    bodies = adsk.core.ObjectCollection.create()
    for child in component.occurrences:
        for solid in child.createForAssemblyContext(occurrence).bRepBodies:
            bodies.add(solid)
    try:
        for angle in (15, 90, 175):
            for side, door, motion in doors:
                motion.rotationValue = signs[side] * math.radians(angle)
            adsk.doEvents()
            low, high = span(doors[0][1])
            if angle == 90 and high - low < DOOR_BACK - DOOR_FRONT:
                raise RuntimeError('The doors did not move when their hinges were driven.')
            overlaps = design.analyzeInterference(design.createInterferenceInput(bodies)).count
            if overlaps:
                raise RuntimeError('%d overlaps with the doors open %d degrees' % (overlaps, angle))
            LOGGER.info('Doors open %d degrees: no overlap', angle)
    finally:
        for side, door, motion in doors:
            motion.rotationValue = 0
        adsk.doEvents()


def build_rack(design, root, appearance, text_appearance):
    """One parent component for the whole printable object. Its children hold
    the pink rack body with the black letter bodies, and the two pink doors."""
    occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    component = occurrence.component
    component.name = NAME
    component.attributes.add(NAME, 'FabricationMaterial', 'Pink PLA')
    for row in range(ROWS):
        # Step `row` and everything behind it, from the step in front upward.
        name = 'Tier %d' % (row + 1)
        base = step_top(row - 1) if row else 0.0
        sketch = xy_sketch(component, base, name)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            point(0, row * ROW_PITCH), point(TOTAL_WIDTH, TOTAL_DEPTH))
        extrude(component, sketch, 1, step_top(row) - base,
                JOIN if row else NEW_BODY, name)
    round_corners(component)
    for row in range(ROWS):
        cut_holes(component, row)
    round_hole_rims(component)
    ridges = (add_side_ridges(component), add_front_ridges(component))
    add_text_frame(component)

    if component.bRepBodies.count != 1:
        raise RuntimeError('The rack must be one body.')
    body = component.bRepBodies.item(0)
    if not body.isSolid or body.lumps.count != 1:
        raise RuntimeError('The rack must be one connected solid.')
    low, high = body.boundingBox.minPoint, body.boundingBox.maxPoint
    actual = ((high.x - low.x) * 10, (high.y - low.y) * 10, (high.z - low.z) * 10)
    expected = (RIDGED_WIDTH, OVERALL_DEPTH, TOTAL_HEIGHT)
    if any(abs(a - e) > 0.001 for a, e in zip(actual, expected)):
        raise RuntimeError('Rack dimensions differ: expected %s, got %s' % (expected, actual))
    body.name = NAME + '_Pink'
    if appearance:
        body.appearance = appearance
    LOGGER.info('Rack validated: bounds_mm=%s volume_cm3=%.2f',
                tuple(round(a, 3) for a in actual), body.volume)
    letters = inlay_text(component, text_appearance)
    door_names = add_compartment(design, occurrence, appearance)
    articulate(design, occurrence, door_names)
    return ridges, letters


def execute(app):
    """Build the rack and return the summary text. Raises on any failure."""
    for handler in list(LOGGER.handlers):
        LOGGER.removeHandler(handler)
        handler.close()
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    # Append across runs so failed and successful attempts can be compared.
    handler = logging.FileHandler(str(LOG_PATH), mode='a', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    LOGGER.addHandler(handler)
    try:
        LOGGER.info('=== %s run started; Fusion %s ===', NAME, app.version)
        LOGGER.info('Script: %s', Path(__file__).resolve())
        LOGGER.info('Inputs (mm): %s', {
            key: value for key, value in globals().items()
            if key.isupper() and isinstance(value, (int, float, tuple))})
        validate()
        document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name = NAME + ' - Pink'
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = (
            adsk.fusion.DistanceUnits.MillimeterDistanceUnits)
        warnings = []
        appearances = []
        for label, rgb in (('Pink', PINK), ('Black', BLACK)):
            try:
                appearances.append(plastic_appearance(
                    app, design, label + ' PLA (visual)', rgb))
            except Exception as exc:
                appearances.append(None)
                warnings.append('%s appearance not applied: %s' % (label, exc))
                LOGGER.warning('%s appearance unavailable', label, exc_info=True)
        ridges, letters = build_rack(design, design.rootComponent, appearances[0], appearances[1])
        app.activeViewport.fit()
        message = (
            'One pink rack created: %d bottles in %d rows of %d.\n\n'
            'W x D x H: %g x %g x %g mm; each step is %.0f deep and rises %.0f.\n'
            'Front step is %.0f thick; vertical corners are R%.0f. Fits the H2D volume of %.0f x %.0f x %.0f mm%s.\n'
            'Holes: %.0f mm wide, R%.1f rims, %.0f mm apart, %.0f mm deep '
            '(front row %.0f mm).\n'
            'Ridges: %d on each side and %d on the front, %.1f mm wide, %.1f mm apart.\n'
            'Front panel: %g x %g mm raised frame, flat inside.\n'
            'Compartment: through the rack under the steps, %g mm front to back, '
            '%g to %g mm high inside.\n'
            'Doors: one each side, print-in-place, %g mm clearance, hinged at the back edge.\n'
            'Each door is its own component with a hinge joint (0-180 degrees): '
            'right-click a joint > Animate Joint.\n'
            'Front text "%s": %d black bodies inlaid %.1f mm, flush.\n\n'
            'Print flat on its base, no supports, no brim.\n'
            'Export the %s component with Save As Mesh.'
        ) % (ROWS * COLUMNS, ROWS, COLUMNS, OVERALL_WIDTH, OVERALL_DEPTH, TOTAL_HEIGHT,
             ROW_PITCH, STEP_RISE, TIER_THICKNESS, CORNER_RADIUS, PLATE_WIDTH, PLATE_DEPTH, PLATE_HEIGHT,
             '' if OVERALL_WIDTH <= PLATE_WIDTH else ' turned a quarter turn',
             HOLE_WIDTH, HOLE_EDGE_RADIUS, HOLE_GAP, HOLE_DEPTH,
             min(HOLE_DEPTH, TIER_THICKNESS - BASE_FLOOR),
             ridges[0] // 2, ridges[1], RIDGE_WIDTH, RIDGE_GAP,
             FRAME_WIDTH, FRAME_Z[1] - FRAME_Z[0],
             DOOR_BACK - DOOR_FRONT - 2 * DOOR_LIP,
             round(DOOR_FRONT - ROOF_DROP - DOOR_LIP * math.sqrt(2) - COMPARTMENT_FLOOR, 1),
             round(DOOR_BACK - DOOR_LIP - ROOF_DROP - DOOR_LIP * math.sqrt(2)
                   - COMPARTMENT_FLOOR, 1),
             DOOR_GAP, TEXT, letters, TEXT_DEPTH, NAME)
        if warnings:
            message += '\n\n' + '\n'.join(warnings)
        message += '\n\nRun log: ' + str(LOG_PATH)
        LOGGER.info('Run completed successfully; warnings=%s', warnings)
        return message
    except Exception:
        LOGGER.exception('%s run failed', NAME)
        raise
    finally:
        handler.flush()
        handler.close()
        LOGGER.removeHandler(handler)


def run(context):
    app = adsk.core.Application.get()
    try:
        app.userInterface.messageBox(execute(app))
    except Exception:
        app.userInterface.messageBox(
            NAME + ' failed. Any partial model is left open for inspection.\n\n'
            + traceback.format_exc() + '\nLog: ' + str(LOG_PATH))
