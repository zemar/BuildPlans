# MyriSaying

Python-generated freestanding plaque with a **200 × 100 mm face and a 3 mm panel**, a black background, a brown twisted-rope border, white raised cursive, and two black triangular rear supports. The plaque leans backward **10°**; the support bottoms remain flat on the table.

The saying is larger than the name and date, using **Snell Roundhand Bold** for clearer cursive. All five lines are raised **1.2 mm**:

> The super power that you'll
> never lose is being the
> best daddy ever.
>
> Myriam Howard
> March 19, 2023

## Construction

- **Panel:** 3 mm thick, reduced from 10 mm. This is a practical thin starting point for the 200 mm span; the frame and supports reinforce it. Minimum reliable thickness depends on material and print settings, and has not been physically tested.
- **Frame:** 6 mm wide, brown throughout. Two twisting strand profiles form a continuous raised rope pattern on a solid frame backing. The strands are fused into one watertight mesh, with no intersecting strand shells. The rope projects up to about 2.5 mm beyond the face, for about **5.5 mm maximum frame thickness**.
- **Lettering:** white, raised 1.2 mm. Nominal saying outline heights are 14/14/16 mm; name 6.5 mm; date 5 mm. Small strokes are expanded slightly for reproduction while retaining the cursive style.
- **Supports:** exactly two black triangular feet, 8 mm wide and 40 mm deep, centered at X = ±65 mm. They attach along 65 mm of the tilted back. Their vertical rise is about 64 mm.
- **Standing size:** approximately **200 × 44.93 × 99.00 mm** in X/Y/Z. The face itself remains 200 × 100 mm; the standing height changes with the lean. X is right, +Y rearward, +Z upward.

The panel, frame, lettering, and supports meet at shared surfaces without overlapping material volumes. The intended result is one assembled multicolor print.

## Generate or open in Fusion

Run the main script with ordinary Python; no third-party packages are required:

```sh
python3 MyriSaying/MyriSaying.py
```

It regenerates the 3MF, five aligned STLs, SVG layout proof, primary validation report, and appends diagnostics to **`MyriSaying.log`**. Keep the bundled `assets/lettering.json` beside the script. The font geometry is included; the actual font file is not redistributed.

In Autodesk Fusion, open **Utilities → Scripts and Add-Ins → Scripts**, add the `MyriSaying` folder, select **MyriSaying**, and click **Run**. The same script regenerates the exports and opens a new unsaved design containing five colored mesh bodies. Save it from Fusion. These are mesh bodies, not sketch/extrusion features.

Fusion import uses Autodesk's [MeshBodies.add API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodies_add.htm) with explicit millimeter units. If Fusion overrides the colors, disable **Preferences → Material → Apply a different appearance**, following Autodesk's [mesh display instructions](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-INSERT-MESH.htm).

## Outputs

- `exports/MyriSaying.3mf`: assembled model with named black, brown, and white parts.
- `exports/*.stl`: five aligned geometry-only parts, in millimeters.
- `preview.png`, `preview-3d.png`, `preview-rear.png`: front, oblique, and rear views rendered from the actual meshes.
- `preview.svg`: flat typography/layout proof; the rope relief is shown in the PNG renders.
- `exports/validation.json`: geometry and static standing-balance calculations.
- `exports/independent-validation.json`: independent checks of exported files, including checksums.
- `MyriSaying.log`: append-only UTC sidecar with dimensions, font checksum, color/lean settings, mesh checks, output paths, Fusion import stages, and full failure tracebacks. Records flush immediately.

The repository's existing ignore rules exclude `*.log` and `exports` from Git. Those outputs are present locally in this folder.

## Printing

Keep the five parts together as one multipart object. Assign **black** to the panel and both feet, **brown** to the rope frame, and **white** to the writing. If using STL, import all five simultaneously as parts and preserve their relative positions. Do not arrange individual parts independently.

The 3MF stores geometry and material colors, without a printer profile or toolpaths. For a solid 3 mm panel, use 100% infill or enough solid layers/walls to fill that section. Review the lean, raised lettering, and rope overhangs in the slicer's support and layer preview. Actual slicing and a physical print have not been verified.

## Editing and optional checks

Edit dimensions, lean angle, rope settings, or lettering layout at the top of `MyriSaying.py`. Changes to thickness, relief, lean, rope parameters, or support dimensions only need the main script. Changes to text, font, face width/height, or border width require rebuilding the text asset:

```sh
python3 -m venv /tmp/myrisaying-venv
/tmp/myrisaying-venv/bin/python -m pip install -r MyriSaying/requirements.txt
/tmp/myrisaying-venv/bin/python MyriSaying/prepare_text.py
/tmp/myrisaying-venv/bin/python MyriSaying/render_preview.py
/tmp/myrisaying-venv/bin/python MyriSaying/validate_exports.py
```

The font preparation defaults to macOS `SnellRoundhand.ttc`, font index 1 (Bold). On another system use `--font '/path/to/SnellRoundhand.ttc' --font-index 1`; the full font name must match `FONT_NAME`. Outlines use [fontTools](https://fonttools.readthedocs.io/en/latest/pens/basePen.html), HarfBuzz shaping, and [trimesh](https://trimesh.org/trimesh.creation.html)/Earcut triangulation. The preview renderer uses NumPy and Pillow and does not need Blender.

Checks cover face dimensions and true panel thickness after undoing the lean, flat support bottoms, exact colors, text clearance and line separation, closed shells, positive volumes, consistent winding, and nondegenerate triangles. The equal-density model's center of mass falls inside its support footprint. Fusion execution and physical stability have not been tested here.
