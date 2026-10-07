# MyriSaying

Python-generated freestanding plaque, **200 mm wide × 100 mm tall × 10 mm body thickness**, with a brown center, a 4 mm black border, white raised cursive lettering, and exactly two black triangular rear supports. Lettering projects another **1.2 mm** beyond the front face. The complete assembly is **51.2 mm deep**, including the rear supports and raised letters.

The inscription is reproduced verbatim, with line breaks for layout:

> The super power that you'll
> never lose is being the
> best daddy ever.
>
> Myriam Howard
> March 19, 2023

All inscription lines use **Brush Script MT**, including the name and date. Outlines are shaped from the installed cursive font, with counters preserved and a small 0.08 mm stroke expansion. The actual font file is not bundled; the prepared geometry is included in `assets/lettering.json`, so the main script does not require an installed font or third-party Python packages.

## Files and generation

- `MyriSaying.py`: main generator and Autodesk Fusion entry point.
- `MyriSaying.log`: append-only UTC log sidecar; logs inputs, font asset checksum, geometry validation, outputs, Fusion import stages, and full error tracebacks. Each entry flushes immediately.
- `exports/MyriSaying.3mf`: assembled model with five named parts and brown/black/white material colors.
- `exports/*.stl`: five aligned geometry-only parts, in millimeters.
- `preview.png`: front proof from the same outlines used for the raised geometry.
- `preview-3d.png`, `preview-rear.png`: rendered views of the actual mesh geometry.
- `preview.svg`: front outline proof and side elevation.
- `exports/validation.json`, `exports/independent-validation.json`: dimension and mesh checks.

Generate the model and append the log using ordinary Python:

```sh
python3 MyriSaying/MyriSaying.py
```

The script regenerates the STL parts, 3MF, SVG, and primary validation report. Keep the `assets` folder beside it. No external Python packages are needed for this command.

## Run in Autodesk Fusion

Open **Utilities → Scripts and Add-Ins → Scripts**, add this `MyriSaying` folder, select **MyriSaying**, and click **Run**. The script regenerates the exports, opens a new unsaved design, and imports five named mesh bodies with the requested appearances. Save the design in Fusion. These are mesh bodies, not editable sketch/extrusion features.

The import uses Autodesk's [MeshBodies.add API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodies_add.htm) with explicit millimeter units and a direct design. If Fusion overrides the colors, uncheck **Preferences → Material → Apply a different appearance**, as described in Autodesk's [mesh display instructions](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-INSERT-MESH.htm).

## Construction and printing

The black frame surrounds the brown panel through its full 10 mm thickness. Each triangular support is **8 mm wide × 40 mm rearward projection × 65 mm tall**, centered 65 mm to either side of the plaque center. Both supports and the bottom border rest on Z = 0. The plaque stands vertically. X is left/right, +Y points backward, +Z points up; the front surface is at Y = 0.

The brown panel, frame, supports, and letters meet at shared surfaces without overlapping material volumes. They are intended to print as one assembled multicolor object. Open the 3MF with the parts kept together; assign brown to the panel, black to the frame and both supports, and white to the writing. Display colors do not select physical filament reels. If importing STLs, load all five together as parts of one object and preserve their relative positions. Do not auto-arrange the individual parts.

The 3MF is a geometry/material assembly, without a printer profile or generated toolpaths. Check orientation, supports for the raised front lettering, and fine cursive strokes in the slicer's layer preview before printing.

## Editing and optional preview rebuilding

Dimensions and text layout are at the top of `MyriSaying.py`. If you change the inscription, font, width, height, or border, regenerate the font outline asset. Changing thickness, relief, or support dimensions only requires the main script.

```sh
python3 -m venv /tmp/myrisaying-venv
/tmp/myrisaying-venv/bin/python -m pip install -r MyriSaying/requirements.txt
/tmp/myrisaying-venv/bin/python MyriSaying/prepare_text.py
/tmp/myrisaying-venv/bin/python MyriSaying/render_preview.py
```

`prepare_text.py` defaults to the macOS Brush Script font. On another system, supply `--font '/path/to/Brush Script.ttf'`. A mismatched font is rejected instead of silently substituting a non-cursive font. Font paths are converted with [fontTools](https://fonttools.readthedocs.io/en/latest/pens/basePen.html); polygon triangulation uses [trimesh](https://trimesh.org/trimesh.creation.html) and Earcut.

## Verification

Local checks passed for the exact panel dimensions, text/frame clearance, line separation, positive solid volumes, watertight meshes, consistent winding, and nondegenerate triangles. Independent checks read the exported STLs and 3MF geometry back from disk. Bambu Studio's CLI reopened the 3MF as manifold geometry measuring **200 × 51.2 × 100 mm** in XYZ, with **35 closed shells** across five material parts (the cursive lettering contains 31 connected pieces).

The equal-density solid model's center of mass is inside the support footprint. This is a static geometry check, not a physical stability test. Fusion execution, actual slicing, and a physical print have not been verified here.

All project files stay in this folder. The repository's existing ignore rules exclude `*.log` and `exports` from Git; those files are generated locally and are present on disk.
