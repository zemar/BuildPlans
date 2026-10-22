"""Create the current single-piece license plate frame in Autodesk Fusion.

Run in Fusion, not with a standalone Python interpreter:
    Utilities > Scripts and Add-Ins > Scripts > add this folder > LicensePlate > Run

The script creates a new design; it does not alter an existing document.
Dimensions below are in millimeters. Fusion's API uses centimeters internally,
so conversion is handled by the small helper functions below.

Orientation:
    Z = 0: flat front face, placed on the print bed.
    Z = 3: recessed back of the main frame and screw tabs.
    Z = 7: top of the raised rear perimeter rim.

Optional STL, 3MF, Fusion archive and preview exports go to Generated/ beside
this script. No backup or archive folders are created.
"""

from pathlib import Path

import adsk.core
import adsk.fusion


# ---------------------------------------------------------------------------
# Editable dimensions (millimeters)
# ---------------------------------------------------------------------------
OUTSIDE_WIDTH = 312.0
OUTSIDE_HEIGHT = 160.0
OPENING_WIDTH = 285.0
OPENING_HEIGHT = 135.0  # Opening before the two upper screw tabs extend into it.

FRAME_THICKNESS = 3.0
TOTAL_THICKNESS = 7.0
REAR_RIM_WIDTH = 3.0

FRAME_CORNER_RADIUS = 10.0  # Both the outside and opening corners.
TAB_CORNER_RADIUS = 6.0
EDGE_RADIUS = 0.45          # Softens the front, rear and recessed edges.

TAB_CENTER_X = (-89.0, 89.0)
TAB_WIDTH = 26.0
TAB_BOTTOM_Y = 53.0
HOLE_CENTER_X = (-88.9, 88.9)
HOLE_CENTER_Y = 63.5
HOLE_DIAMETER = 7.0

PINK_RGB = (244, 139, 180)
EXPORT_FILES = True         # Set False to create the Fusion model only.
EXPORT_FOLDER_NAME = "Generated"
EXPORT_FILE_STEM = "LicensePlate-Single-Piece"

# Modeling tolerances and temporary overlap, also in millimeters.
EDGE_POSITION_TOLERANCE = 0.01
DIMENSION_TOLERANCE = 0.05
CONSTRUCTION_OVERLAP = 2.5
CUTTER_MARGIN = 1.0


# ---------------------------------------------------------------------------
# Unit conversion and low-level geometry helpers
# ---------------------------------------------------------------------------
def cm(millimeters):
    """Convert millimeters to Fusion's internal length unit, centimeters."""
    return millimeters / 10.0


def point_mm(x, y, z):
    return adsk.core.Point3D.create(cm(x), cm(y), cm(z))


def length_value(millimeters):
    return adsk.core.ValueInput.createByReal(cm(millimeters))


def make_box(manager, x_min, y_min, x_max, y_max, z_min, z_max):
    """Create a temporary solid box using bounds given in millimeters."""
    center = point_mm(
        (x_min + x_max) / 2.0,
        (y_min + y_max) / 2.0,
        (z_min + z_max) / 2.0,
    )
    bounds = adsk.core.OrientedBoundingBox3D.create(
        center,
        adsk.core.Vector3D.create(1, 0, 0),
        adsk.core.Vector3D.create(0, 1, 0),
        cm(x_max - x_min),
        cm(y_max - y_min),
        cm(z_max - z_min),
    )
    return manager.createBox(bounds)


def combine_solids(manager, target, tool, operation, description):
    """Apply a Boolean to the temporary target; report failures clearly."""
    if not manager.booleanOperation(target, tool, operation):
        raise RuntimeError(f"Could not {description}.")


def same_position(first, second):
    return abs(first - second) < EDGE_POSITION_TOLERANCE


def vertical_edge_position(edge):
    """Return an upright straight edge's XY position in mm, or None."""
    bounds = edge.boundingBox
    x_span = (bounds.maxPoint.x - bounds.minPoint.x) * 10.0
    y_span = (bounds.maxPoint.y - bounds.minPoint.y) * 10.0
    z_span = (bounds.maxPoint.z - bounds.minPoint.z) * 10.0
    if x_span > EDGE_POSITION_TOLERANCE or y_span > EDGE_POSITION_TOLERANCE:
        return None
    if z_span < EDGE_POSITION_TOLERANCE:
        return None
    return bounds.minPoint.x * 10.0, bounds.minPoint.y * 10.0


def round_vertical_corners(component, body, corners, radius):
    """Round the upright edges at the supplied XY corner coordinates."""
    edges = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        position = vertical_edge_position(edge)
        if position is None:
            continue
        x, y = position
        if any(same_position(x, cx) and same_position(y, cy) for cx, cy in corners):
            edges.add(edge)

    if edges.count != len(corners):
        raise RuntimeError(
            f"Expected {len(corners)} corner edges; found {edges.count}. "
            "Check the frame dimensions and corner coordinates."
        )

    fillets = component.features.filletFeatures
    settings = fillets.createInput()
    settings.edgeSetInputs.addConstantRadiusEdgeSet(
        edges, length_value(radius), True
    )
    fillets.add(settings)


def rectangle_corners(half_width, half_height):
    return [
        (x, y)
        for x in (-half_width, half_width)
        for y in (-half_height, half_height)
    ]


# ---------------------------------------------------------------------------
# Main frame: front face, opening, upper tabs and mounting holes
# ---------------------------------------------------------------------------
def build_frame_web(component, manager):
    outer_x = OUTSIDE_WIDTH / 2.0
    outer_y = OUTSIDE_HEIGHT / 2.0
    inner_x = OPENING_WIDTH / 2.0
    inner_y = OPENING_HEIGHT / 2.0
    overlap_y = inner_y + CONSTRUCTION_OVERLAP
    union = adsk.fusion.BooleanTypes.UnionBooleanType
    subtract = adsk.fusion.BooleanTypes.DifferenceBooleanType

    # Join four rails. The overlapping corners become one continuous solid.
    frame = make_box(
        manager, -outer_x, inner_y, outer_x, outer_y, 0, FRAME_THICKNESS
    )
    other_rails = [
        (-outer_x, -outer_y, -inner_x, overlap_y),  # Left rail.
        (inner_x, -outer_y, outer_x, overlap_y),    # Right rail.
        (-outer_x, -outer_y, outer_x, -inner_y),   # Bottom rail.
    ]
    for x_min, y_min, x_max, y_max in other_rails:
        rail = make_box(
            manager, x_min, y_min, x_max, y_max, 0, FRAME_THICKNESS
        )
        combine_solids(manager, frame, rail, union, "join the frame rails")

    # Screw tabs extend down from the top rail into the opening.
    tab_corners = []
    for center_x in TAB_CENTER_X:
        x_min = center_x - TAB_WIDTH / 2.0
        x_max = center_x + TAB_WIDTH / 2.0
        tab = make_box(
            manager, x_min, TAB_BOTTOM_Y, x_max, overlap_y, 0, FRAME_THICKNESS
        )
        combine_solids(manager, frame, tab, union, "join an upper screw tab")
        tab_corners.extend(
            (x, y) for x in (x_min, x_max) for y in (TAB_BOTTOM_Y, inner_y)
        )

    for center_x in HOLE_CENTER_X:
        hole = manager.createCylinderOrCone(
            point_mm(center_x, HOLE_CENTER_Y, -CUTTER_MARGIN),
            cm(HOLE_DIAMETER / 2.0),
            point_mm(center_x, HOLE_CENTER_Y, TOTAL_THICKNESS + CUTTER_MARGIN),
            cm(HOLE_DIAMETER / 2.0),
        )
        combine_solids(manager, frame, hole, subtract, "cut a mounting hole")

    body = component.bRepBodies.add(frame)
    body.name = "Main frame and upper screw tabs"
    frame_corners = rectangle_corners(outer_x, outer_y)
    frame_corners += rectangle_corners(inner_x, inner_y)
    round_vertical_corners(component, body, frame_corners, FRAME_CORNER_RADIUS)
    round_vertical_corners(component, body, tab_corners, TAB_CORNER_RADIUS)
    return body


# ---------------------------------------------------------------------------
# Rear perimeter rim: 3 mm wide, rising 4 mm above the 3 mm web
# ---------------------------------------------------------------------------
def build_rear_rim(component, manager):
    outer_x = OUTSIDE_WIDTH / 2.0
    outer_y = OUTSIDE_HEIGHT / 2.0
    inner_x = outer_x - REAR_RIM_WIDTH
    inner_y = outer_y - REAR_RIM_WIDTH

    rim = make_box(
        manager, -outer_x, -outer_y, outer_x, outer_y,
        FRAME_THICKNESS, TOTAL_THICKNESS,
    )
    opening = make_box(
        manager, -inner_x, -inner_y, inner_x, inner_y,
        FRAME_THICKNESS - CUTTER_MARGIN, TOTAL_THICKNESS + CUTTER_MARGIN,
    )
    combine_solids(
        manager, rim, opening,
        adsk.fusion.BooleanTypes.DifferenceBooleanType,
        "hollow the rear perimeter rim",
    )
    body = component.bRepBodies.add(rim)
    body.name = "Rear perimeter rim"
    round_vertical_corners(
        component, body, rectangle_corners(outer_x, outer_y), FRAME_CORNER_RADIUS
    )
    # Matching offset radii keep the rim 3 mm wide around the rounded corners.
    round_vertical_corners(
        component, body, rectangle_corners(inner_x, inner_y),
        FRAME_CORNER_RADIUS - REAR_RIM_WIDTH,
    )
    return body


def join_web_and_rim(component, manager, web, rim):
    joined = manager.copy(web)
    combine_solids(
        manager, joined, manager.copy(rim),
        adsk.fusion.BooleanTypes.UnionBooleanType,
        "join the frame and rear rim",
    )
    web.deleteMe()
    rim.deleteMe()
    return component.bRepBodies.add(joined)


def soften_horizontal_edges(component, body):
    """Round the front edge, rear rim edge and recessed rear step."""
    edges = adsk.core.ObjectCollection.create()
    for edge in body.edges:
        bounds = edge.boundingBox
        z_span = (bounds.maxPoint.z - bounds.minPoint.z) * 10.0
        if z_span < EDGE_POSITION_TOLERANCE:
            edges.add(edge)

    settings = component.features.filletFeatures.createInput()
    settings.edgeSetInputs.addConstantRadiusEdgeSet(
        edges, length_value(EDGE_RADIUS), True
    )
    component.features.filletFeatures.add(settings)


# ---------------------------------------------------------------------------
# Appearance, verification and optional exports
# ---------------------------------------------------------------------------
def apply_pink_appearance(app, design, body):
    source = None
    for library in app.materialLibraries:
        for appearance in library.appearances:
            if appearance.name == "Plastic - Matte (White)":
                source = appearance
                break
        if source is not None:
            break
    if source is None:
        source = app.materialLibraries.item(0).appearances.item(0)

    pink = design.appearances.addByCopy(source, "Pink ABS")
    for appearance_property in pink.appearanceProperties:
        if appearance_property.objectType == adsk.core.ColorProperty.classType():
            appearance_property.value = adsk.core.Color.create(*PINK_RGB, 255)
    body.appearance = pink


def verify_frame(component, body):
    if not body.isSolid or body.shells.count != 1 or component.bRepBodies.count != 1:
        raise RuntimeError("The finished frame must be one continuous solid body.")

    bounds = body.boundingBox
    dimensions = (
        (bounds.maxPoint.x - bounds.minPoint.x) * 10.0,
        (bounds.maxPoint.y - bounds.minPoint.y) * 10.0,
        (bounds.maxPoint.z - bounds.minPoint.z) * 10.0,
    )
    expected = (OUTSIDE_WIDTH, OUTSIDE_HEIGHT, TOTAL_THICKNESS)
    if any(abs(actual - target) > DIMENSION_TOLERANCE
           for actual, target in zip(dimensions, expected)):
        raise RuntimeError(f"Unexpected finished frame dimensions: {dimensions} mm")

    print(f"Created one continuous solid: {dimensions} mm.")
    print(
        f"Rear rim: {REAR_RIM_WIDTH} mm wide, {TOTAL_THICKNESS} mm total depth; "
        f"recessed frame: {FRAME_THICKNESS} mm thick."
    )


def export_files(app, design, body):
    output = Path(__file__).resolve().parent / EXPORT_FOLDER_NAME
    output.mkdir(parents=True, exist_ok=True)
    manager = design.exportManager
    options = [
        manager.createSTLExportOptions(body, str(output / f"{EXPORT_FILE_STEM}.stl")),
        manager.createC3MFExportOptions(body, str(output / f"{EXPORT_FILE_STEM}.3mf")),
        manager.createFusionArchiveExportOptions(str(output / f"{EXPORT_FILE_STEM}.f3d")),
    ]
    for export_options in options:
        if not manager.execute(export_options):
            raise RuntimeError("Fusion could not complete a requested file export.")
    if not app.activeViewport.saveAsImageFile(
        str(output / f"{EXPORT_FILE_STEM}.png"), 1600, 1000
    ):
        raise RuntimeError("Fusion could not save the preview image.")
    print(f"Exports saved to: {output}")


# ---------------------------------------------------------------------------
# Fusion entry point
# ---------------------------------------------------------------------------
def run(context):
    app = adsk.core.Application.get()
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "License Plate - Single Piece - Rear Rim"
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    component = design.rootComponent
    manager = adsk.fusion.TemporaryBRepManager.get()

    web = build_frame_web(component, manager)
    rim = build_rear_rim(component, manager)
    frame = join_web_and_rim(component, manager, web, rim)
    soften_horizontal_edges(component, frame)
    frame.name = "Single Piece - 7mm Outer Rim - 3mm Rim Width - 3mm Web"
    apply_pink_appearance(app, design, frame)
    verify_frame(component, frame)

    camera = app.activeViewport.camera
    camera.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
    camera.isFitView = True
    app.activeViewport.camera = camera
    app.activeViewport.refresh()

    if EXPORT_FILES:
        export_files(app, design, frame)
