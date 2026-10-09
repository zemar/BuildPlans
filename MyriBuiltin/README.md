# Myri Built-in — Fusion

Version **3.0.0** builds the **MkIII** bedroom built-in design in Autodesk Fusion.
The model contains 147 individual part components grouped into 17 assemblies.
Each plywood panel is a separate component containing one solid body, with its
applicable dado grooves cut into the geometry.

## Run in Fusion

1. Keep this project in a folder named `MyriBuiltin`.
2. Keep `MyriBuiltin.py`, `MyriBuiltin.manifest`, and `textures/` together in that folder.
3. In Fusion's Design workspace, open **Utilities → Add-Ins → Scripts and Add-Ins**.
4. Use **+** to add an existing script and select the `MyriBuiltin` folder.
5. Select **MyriBuiltin** and click **Run**.
6. Save the resulting design in Fusion when the build completes.

Every run creates a **new, unsaved document**. It does not update an existing
model. The design uses direct modeling, without a parametric timeline. Run the
script inside Fusion; its `adsk` modules are not available in ordinary Python.

## Files

- `MyriBuiltin.py`: Fusion entry point, embedded design data, geometry, and appearances.
- `MyriBuiltin.manifest`: Fusion script registration and version information.
- `textures/`: Original walnut and purpleheart images used by the script.
- `MyriBuiltin.log`: Execution details appended beside the script on each run.
- `SketchUp/`: Earlier Ruby models and live-reload scripts, separate from the Fusion entry point.
- [ASSEMBLIES.md](ASSEMBLIES.md): Earlier assembly notes; consult the current script for exact parts and dimensions.

## Design and materials

The embedded `DATA` in `MyriBuiltin.py` defines assembly membership, part names,
positions, dimensions, material keys, grain direction, dados, and tapered legs.
Dimensions are in inches and are converted to centimeters for Fusion's geometry
API. X runs left to right, negative Y projects into the room, and Z points up.
Changes to the SketchUp Ruby files do not automatically update this snapshot.

Walnut hardwood, walnut plywood, and purpleheart use these original images:

- `textures/walnut_solid.png`
- `textures/walnut_plywood.png`
- `textures/purpleheart_solid.png`

Other materials, including maple, Baltic birch plywood, the mattress, and LED
strips, use the source palette colors. Appearances are visual assignments, not
physical material definitions for mass or structural analysis. Plywood layers,
the photo figure, and simulated light washes are not modeled. Texture mapping
uses each part's grain direction; the image textures do not simulate true end grain.

Set `SHOW_MATTRESS` or `SHOW_LIGHTING` near the top of the script to control the
initial visibility of those components. They remain part of the generated design.

## Troubleshooting

Check `MyriBuiltin.log` after running the script. Each run records the Fusion and
Python versions, material setup, individual part data, geometry checks,
appearance assignments, warnings, and full error tracebacks. Locate the latest
`RUN START` entry to distinguish current errors from previous runs.

A failed build can leave an incomplete new document. After correcting the issue,
run the script again to build a fresh document. Missing required texture images
stop appearance setup; keep the `textures` folder beside the running script.
If you run a copied script, its log is written beside that copy.

The script checks solid geometry and part volumes during execution. There is no
separate test folder or test runner.
