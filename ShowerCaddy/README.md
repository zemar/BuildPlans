# Shower caddy

Run `ShowerCaddy.py` in Autodesk Fusion via **Utilities > Scripts and Add-Ins > Scripts**. Add this folder as a script, select ShowerCaddy, and click Run. It creates a new unsaved design containing one basket. Save the design from Fusion.

All dimensions below and all script inputs are millimeters.

| Dimension | Value |
| --- | ---: |
| Basket outside width | 259 |
| Basket outside depth | 88.9 |
| Basket height from underside to rim | 101.6 |
| Hook rise from basket underside to bridge underside | 305 |
| Clear backward opening for glass | 25.5 |
| Overall height including hook bridge | 311 |
| Overall depth including backward hook | 120.4 |

Each shelf has two rear-corner uprights and backward hooks with downward returns. The 25.5 dimension is interpreted as the clear throat between the upright and return, not the outside hook envelope. Duplicate the basket in your slicer to print three identical shelves.

Assumed construction dimensions are editable at the top of the script: 3 mm walls and floor, 16 mm wide × 6 mm thick hooks, 30 mm downward returns, and 8 mm square mesh openings with 3 mm webs and at least 6 mm border. The floor contains 154 through-openings. All edges—including basket rims, interior corners, hooks, and drainage openings—are rounded in two stages: vertical corners use `CORNER_RADIUS = 1.0` mm, then horizontal perimeter edges (including the newly curved corners) use `EDGE_RADIUS = 0.75` mm. The corner radius must exceed the rim radius to avoid a collapsed corner during the second operation. If Fusion cannot solve the complete fillet, the script reports an error rather than skipping edges. Dimensions above describe the geometry before edge rounding.

Intended fabrication material is **black PETG**. The script applies a black visual finish and stores the material intent as a component attribute. It does not assign PETG engineering properties or slicer settings. Strength and printability have not been validated in Fusion or by a physical prototype.

Edit constants and rerun to regenerate a new design. Syntax and dimensional calculations were checked locally; Fusion geometry execution requires Fusion.

API references: [ExtrudeFeatures.addSimple](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ExtrudeFeatures_addSimple.htm), [Occurrences.addExistingComponent](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrences_addExistingComponent.htm), [appearance assignment](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MaterialSample_Sample.htm).

Fillet API: [constant-radius edge sets](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_FilletEdgeSetInputs_addConstantRadiusEdgeSet.htm).

Each run appends timestamped diagnostics to `ShowerCaddy.log` beside the script. The log includes inputs, Fusion version, build steps, mesh and fillet edge counts, feature health, elapsed time, and full error tracebacks. Records flush immediately so the last started operation is visible even if Fusion stalls. Timestamps are UTC; previous runs are retained. The completion/error dialog shows the log path.

The previous one-step fillet failed in Fusion with `ASM_INCONS_FACE` on 1,920 edges. The replacement separates vertical corners and horizontal rims, reacquires edges between features, and logs counts, health, and timings for each stage. This geometry change still needs a Fusion rerun for kernel verification.

The script builds the basket and writes its sidecar log. Export your preferred format manually from Fusion.
