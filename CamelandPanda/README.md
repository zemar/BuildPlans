# Camel and Panda plaque

`CamelandPanda.py` creates a new, unsaved Autodesk Fusion design with a single printable relief mesh of a cleaned version of the supplied drawing. The plaque is **200 mm wide × 150 mm high × 10 mm overall thickness**: a flat 7 mm backing plus up to 3 mm of raised artwork. X is width, Y is picture height, and Z is thickness. The back is at Z = 0.

## Run in Fusion

1. Open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this `CamelandPanda` folder, select **CamelandPanda**, and click **Run**.
3. Save the new design. Each run also generates `exports/CamelandPanda.stl`, using millimeter coordinates, ready to open in a slicer.

Keep the script and the complete `assets` folder together (both relief and color data are required). No Python packages need to be installed in Fusion. The script logs progress and errors to `CamelandPanda.log`. Each run creates a new design and replaces the generated STL; it does not start a printer.

The result is a mesh body, not an editable collection of sketch/extrusion features. The dense mesh preserves the pencil drawing's details; converting its approximately 968,400 triangles to a faceted solid is unnecessary for printing.

## Artwork and dimensions

The original JPG is preserved in `assets/reference.jpg`. The cleaned illustration is `assets/cleaned-artwork.png`: **one camel and exactly three pandas**, one riding and two sitting beside it. It retains the Canadian flag, purple saddle, pyramid, and bamboo. Smooth outlines and solid shapes replace pencil scribbles; the signature and background texture are omitted. The cleaned artwork was created with the built-in image generation tool; its exact prompt is saved in `assets/cleanup-prompt.txt`.

The artwork is fitted proportionally inside the plaque with at least 3 mm of margin. Color regions and closed silhouettes determine raised surfaces, including the pandas' white faces and bellies. Black patches and outlines add raised detail. This is a shallow artistic relief, not a fully sculpted 3D scene. The STL contains no color information; the Fusion design imports the colored OBJ/MTL described below.

See `relief-preview.png` for an orthographic shaded preview of the actual height field. The surface is sampled every 0.25 mm; the backing and artwork form one connected, closed shell. Fine facial details depend on printer resolution.

Edit `WIDTH_MM`, `HEIGHT_MM`, `TOTAL_THICKNESS_MM`, and `RELIEF_MM` at the top of the Fusion script to change dimensions. The supplied defaults make 10 mm the **total** thickness. For a 10 mm backing plus 3 mm artwork, set total thickness to 13 mm. Changing width/height independently changes the artwork's aspect ratio.

Print with the flat back on the bed and the relief facing upward. A 0.12–0.16 mm layer height is a reasonable starting point for resolving the shallow detail. The relief has no overhangs. Review the slicer's preview before printing.

## Local generation and validation

Generate an STL without Fusion using Python's standard library:

```sh
python3 CamelandPanda/CamelandPanda.py --stl-only
```

`prepare_relief.py` is an optional asset rebuilding utility requiring Pillow, NumPy, and SciPy. It converts the cleaned artwork's closed silhouettes and color regions into smooth raised surfaces, writes the normalized compressed height field, and generates the preview. It is not required to run the Fusion script.

The generated default STL was checked with trimesh: exact bounds of 200 × 150 × 10 mm, one connected component, watertight edges, consistent winding, positive volume, and no zero-area triangles. Python syntax and the Fusion manifest were also checked. Detailed results are in `exports/validation.json`. Fusion execution and a physical print have not been tested here.

The Fusion import follows Autodesk's [MeshBodies.add API](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodies_add.htm), using a new direct design and explicit [millimeter mesh units](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshUnits.htm).

## Colors in Fusion

Run the same `CamelandPanda.py` script. It now generates and imports `exports/CamelandPanda.obj` with its companion `CamelandPanda.mtl` and `CamelandPanda-palette.png` texture, preserving one closed relief mesh with per-face colors. The carpet, Canadian flag, and tongues share the same red material. Pandas are black and white, the camel is tan/brown, bamboo is green, the pyramid is gold, and the backing is ivory. Edit `PALETTE` in the script to change the RGB colors. `assets/colors.bin.zlib` holds the aligned material map; no extra packages are needed in Fusion.

See `color-relief-preview.png` for the material-colored CAD preview. The cleaned reference illustration still has its original purple carpet; the relief's material map changes that region to red.

If Fusion displays a single color, disable **Preferences → Material → Apply a different appearance**, then rerun. Hide mesh face groups with **Shift+F** if they obscure the colors. These are Autodesk's documented [mesh color display settings](https://help.autodesk.com/cloudhelp/ENU/Fusion-Mesh/files/MESH-INSERT-MESH.htm).

The OBJ, MTL, and palette PNG must stay together. The STL remains a geometry-only export. Display colors do not automatically assign printer filaments; configure multicolor printing in your slicer. Local export can also be run with `python3 CamelandPanda/CamelandPanda.py --color-only`.

The colored OBJ was checked locally for dimensions, closed topology, consistent winding, positive volume, and one connected shell. Actual color display in Fusion still needs a Fusion run.

### Color import repair and sidecar log

The first colored run imported successfully but did not visibly show colors in Fusion. Its log only proved mesh import, so the cause was not established. The revised export uses one explicit PNG palette texture with per-face UV coordinates instead of multiple diffuse MTL materials. After import, the script clears the body appearance override and suppresses face-group colors and triangle edges using Fusion's display overrides. This repair needs a Fusion rerun to verify the visible result.

`CamelandPanda.log` is the persistent sidecar beside the script. Previous entries are retained. New runs append UTC timestamps, a `textured-color-v2` marker, Fusion version, dimensions, generated asset paths/sizes/checksums, palette colors, before/after body display settings, elapsed time, and full error tracebacks. Each logging record flushes immediately; the completion and error dialogs show the log path. Earlier entries were recorded in local time and have no `Z` suffix. The log remains local and is excluded from Git.

Local verification passed for the generated PNG palette, all eight UV material assignments, 968,400 exported faces, and Python syntax. Fusion appearance and display controls follow [MeshBody.appearance](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBody_appearance.htm) and [MeshBodyDisplayOverrides](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodyDisplayOverrides.htm).

### Fur texture

The bundled relief now has subtle directional fur on the camel and three pandas. Short irregular tufts vary the actual surface height by up to 0.20 mm, fading out at color boundaries and outlines. Faces, muzzles, paw pads, carpet, flag, bamboo, and pyramid stay smooth. The tallest fur regions use shallow grooves to preserve the 10 mm overall thickness. Colors remain unchanged. Both STL and textured OBJ include the fur geometry. Rerun `CamelandPanda.py` in Fusion to load it. `FUR_HEIGHT_MM` and `FUR_SEED` in the optional asset-preparation utility control the texture. Local mesh checks passed; physical texture reproduction depends on print resolution.
