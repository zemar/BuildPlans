# Camel and Panda

Run **CamelandPanda.py** in Fusion through **Utilities → Scripts and Add-Ins → Scripts**. It creates a new design containing the plaque and two white rear feet.

To export, right-click the **Plaque** body and choose **Save as Mesh → 3MF → Millimeter**. Repeat for the feet. Use 3MF to retain colors; STL does not store them. Save the Fusion design normally if you want to reopen it later.

## Files needed

- `CamelandPanda.py` — the only Python script; includes the plaque, stand, color packaging, and Fusion import code.
- `CamelandPanda.manifest` — Fusion's script registration file.

Artwork geometry and colors are embedded directly in `CamelandPanda.py`; no assets folder or helper scripts are needed.

The original artwork and preview images are retained as references. They are not required at runtime.

The script appends diagnostics and error tracebacks to **CamelandPanda.log** beside it. It creates mesh-import files in a temporary directory and removes them after import, including after failures. There is no exports directory, no automatic STL/OBJ export, and no command-line export mode. Export finished bodies yourself from Fusion.

## Current design

The plaque is 200 × 150 × 10 mm overall, with 3 mm rounded base edges, textured white backing, textured camel and panda fur, and five colors: white, black, brown, red, and green. The carpet, flag, and tongues share red.

Two rear dovetail channels accept the white feet. The plaque rests on its bottom edge with a 15° backward lean from vertical; the supports remain behind it. The geometry and color assignments are preserved from the version before consolidation.

The working color import uses the 3MF Materials extension's surface color groups. Fusion's default appearance override is temporarily disabled during import and restored afterward. The plaque remains a single mesh body, and each foot is a separate body.

Physical fit and printing depend on printer settings. Assign the corresponding filaments in your slicer and check its preview.

## Refactor verification

Every plaque vertex, triangle, and surface color assignment was compared with the previous generated 3MF. Both foot meshes were compared directly with the previous stand implementation. The temporary-file cleanup was also checked. The consolidated script still needs its first run in Fusion.

Embedded-data verification: decoded geometry and color data match the previous binary assets byte for byte, and the script loads both successfully with the assets folder removed. Reference images and their cleanup prompt are kept alongside the script.

Color-map cleanup: object boundaries now restrict plants to green/black; pandas to black/white with red tongues; camel to brown/black with white eyes and red tongue; pyramid and pole to brown/black; carpet including trim and tassels to red/black; and flag to red/white/black. Stray brown paw-pad pixels, colored edge flecks, and camel-lip red spill were removed. The corrected five-color map is embedded in the single script. Relief geometry is unchanged. See `color-relief-preview.png` for the updated CAD material preview; rerun the script to replace an existing Fusion design.
