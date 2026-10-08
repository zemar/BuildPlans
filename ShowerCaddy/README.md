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

Assumed construction dimensions are editable at the top of the script: 3 mm walls and floor, 25 mm wide × 6 mm thick hooks, 30 mm downward returns, and 8 mm square mesh openings with 3 mm webs and at least 6 mm border. The floor contains 154 through-openings. All edges—including basket rims, interior corners, hooks, and drainage openings—are rounded in two stages: vertical corners use `CORNER_RADIUS = 1.0` mm, then horizontal perimeter edges (including the newly curved corners) use `EDGE_RADIUS = 0.75` mm. The corner radius must exceed the rim radius to avoid a collapsed corner during the second operation. If Fusion cannot solve the complete fillet, the script reports an error rather than skipping edges. Dimensions above describe the geometry before edge rounding.

Intended fabrication material is **black PLA**. The script applies a black visual finish and stores the material intent as a component attribute. It does not assign PLA engineering properties or slicer settings. Strength and printability have not been validated in Fusion or by a physical prototype.

Edit constants and rerun to regenerate a new design. Syntax and dimensional calculations were checked locally; Fusion geometry execution requires Fusion.

API references: [ExtrudeFeatures.addSimple](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ExtrudeFeatures_addSimple.htm), [Occurrences.addExistingComponent](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrences_addExistingComponent.htm), [appearance assignment](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/MaterialSample_Sample.htm).

Fillet API: [constant-radius edge sets](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_FilletEdgeSetInputs_addConstantRadiusEdgeSet.htm).

Each run appends timestamped diagnostics to `ShowerCaddy.log` beside the script. The log includes inputs, Fusion version, build steps, mesh and fillet edge counts, feature health, elapsed time, and full error tracebacks. Records flush immediately so the last started operation is visible even if Fusion stalls. Timestamps are UTC; previous runs are retained. The completion/error dialog shows the log path.

The previous one-step fillet failed in Fusion with `ASM_INCONS_FACE` on 1,920 edges. The replacement separates vertical corners and horizontal rims, reacquires edges between features, and logs counts, health, and timings for each stage. This geometry change still needs a Fusion rerun for kernel verification.

The script builds the basket and writes its sidecar log. Export your preferred format manually from Fusion.

## Front artwork inlay

Keep `assets/panda_camel_inlay.json` beside the script in its `assets` folder. The artwork is traced from the color-region source used for `CamelandPanda/color-relief-preview.png`: only the central camel and riding panda, including the flag and mouth branch. The two other pandas, surrounding bamboo, and pyramid are excluded.

The centered artwork is approximately **72.97 mm wide × 80 mm high**. Matching pockets extend **0.6 mm** into the 3 mm front wall, leaving **2.4 mm** of backing. Colored solids fill those pockets flush with the outside face. Dark outlines and panda patches remain the black basket material. The camel uses brown; leaves use green; flag, saddle, and tongue use red; panda face/belly and flag center use white. Small source details are simplified for CAD and may still depend on nozzle and slicer resolution.

The model contains one black basket body and 54 separate inlay bodies named by color: 9 White, 9 Green, 8 Red, 28 Brown. These are actual non-overlapping solids, not a decal. The existing basket and hook fillets are created before adding the artwork. `INLAY_HEIGHT`, `INLAY_DEPTH`, and `INLAY_COLORS` control the artwork size, pocket depth, and display palette. Appearance is cosmetic; it does not automatically select filament.

Export the complete component with **all bodies** in Fusion. In Bambu Studio, preserve them as parts of one object so their alignment stays intact, then assign PLA by the color in each body's name. The complete scheme uses **five filament colors including black**. Avoid placing/arranging the individual inlay parts separately on the plate.

[Front-face vector preview](inlay-preview.svg) and [PNG preview](inlay-preview.png) show the planned color regions and placement, not a Fusion screenshot. Local checks passed for contour validity, non-overlap, area calculations, front-view orientation, wall margins, and remaining thickness. The new inlay features still need a Fusion run; their progress and failures are logged to the sidecar. The earlier plain basket geometry was successfully run in Fusion by the user.

`prepare_inlay.py` rebuilds the JSON and SVG from the original color-region data; it requires NumPy, SciPy, Shapely, and Pillow locally. Fusion itself needs only its API and Python's standard library. Source files in `CamelandPanda` are unchanged.

The inlay uses Autodesk's [sketch coordinate conversion](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_Sketch_modelToSketchSpace.htm) and [Combine with retained tool bodies](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_CombineFeatureInput_isKeepToolBodies.htm) to cut matching pockets while retaining separate color solids.

### Pocket-volume validation repair

The 2026-10-08 run built all 49 colored solids and a healthy pocket-cut feature, then failed the script's volume comparison. The old check subtracted two basket-volume readings using a tolerance based only on the much smaller inlay volume and did not log the measured difference. The revised check explicitly requests VeryHigh physical-property accuracy, measures the Combine result body, calculates expected inlay volume from polygon area × depth, and propagates the before/after measurement uncertainty. Actual volumes, discrepancy, and tolerance are now logged. Missing cuts and mismatches outside the uncertainty still fail. Local regression checks passed; a Fusion rerun is needed to confirm this repair. Autodesk documents VeryHigh accuracy as ±0.01% in [CalculationAccuracy](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CalculationAccuracy.htm).

The next run exposed a second validation assumption: `CombineFeature.bodies` did not contain exactly one body. The script now tags the basket and inlays with persistent `BodyRole` attributes and resolves the finished basket from the component's current bodies, independently of the Combine collection's count or order. It verifies one solid basket and all 49 solid inlays before measuring the pocket volume. The log includes feature/component counts and every resulting body's role. Local regression checks cover reordered bodies, missing or split baskets, missing inlays, and unknown/non-solid bodies; Fusion execution still requires a rerun.

The white fur outline has been removed. Restored white eye details and 0.48 mm-diameter highlights remain, at the existing 0.6 mm inlay depth. `EYE_HIGHLIGHT_RADIUS_MM` in `prepare_inlay.py` controls the highlights when rebuilding the asset. A smooth brown oval now sits behind the panda, using the existing brown filament. It preserves the black fur and original artwork in front of it, without a white outline. The oval is approximately 30.8 × 43.1 mm, and uses the existing 0.6 mm inlay depth. Rerun the Fusion script to regenerate the artwork. Both vector and PNG previews have been refreshed; local contour and non-overlap checks passed.
