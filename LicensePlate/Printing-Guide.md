# Uniform-bar license plate frame — ABS tongue and groove

This revision removes the bottom screw tabs, bottom screw holes, Leafy lettering and panda. The bottom rail is uniformly 12.5 mm tall from left to right. The frame remains 312 × 160 mm overall and 5 mm thick, with 10 mm outside and inside frame corner radii (the smaller screw-tab corners remain 6 mm) and 0.45 mm rounded upper and lower edges. The inside opening is 285 × 135 mm before the top screw tabs intrude into it. Side rails are 13.5 mm wide; top and bottom rails are 12.5 mm high. Only the two upper mounting holes remain.

The center seam divides the frame into equally wide structural halves. Two tongues project exactly 50 mm from the left half, one in each horizontal rail. Continuous side ridges form a stepped/T section adapted from the hanger arms in Duschablage.3mf. Corresponding grooves enter the left-facing edge of the right half. The mating halves slide horizontally together; the ridges capture movement across the rail and through its thickness. This is a sliding joint, not a snap latch. Once mounted, the two upper screws hold the halves in position against axial separation.

## Profile and clearance

- Tongue central web: 8 mm wide.
- Tongue width across side ridges: 11 mm.
- Tongue Z range: 0–3.8 mm. The central stem reaches the exposed underside.
- Side ridges are at the top: their lower shoulders are at Z = 1.4 mm and their top is at Z = 3.8 mm, with a small bevel at the outer lower shoulder.
- Matching groove width: 8.5 mm web / 11.5 mm across ridges.
- The groove is open through the bottom face at Z = 0. The stem opening is 8.5 mm wide, the upper ridge cavity is 11.5 mm wide, and its ceiling is at Z = 4.05 mm. There is no bottom skin across the stem opening.
- Nominal side and thickness clearance: 0.25 mm per face.
- Groove depth leaves 0.5 mm clearance beyond the tongue tip.
- Tongue insertion ends are rounded for easier entry.

## Print the full-length test pair first

Tongue-Groove-Test.3mf contains two separated objects reproducing the 50 mm tongue and groove. Use the same ABS, layer height, orientation and support settings intended for the frame. Let them cool completely before trying the fit. They should slide the full length without bending the tongue or requiring excessive force. Long channels are sensitive to extrusion calibration, shrinkage and support residue. Adjust the groove clearance if necessary; do not globally scale a frame half because that changes mounting-hole locations.

## Printing and assembly

Print plain back down, front up. Use your H2D ABS preset. A starting point is 0.20 mm layers, five walls and a roughly 6 mm brim. The tongue stems now lie on the print bed, and the grooves are open underneath. Inspect the roughly 1.5 mm ridge overhangs in the slicer; add local removable support only if needed. Keep supports out of the grooves. The upper cavity ceiling spans approximately 11.5 mm; check its bridge on the test print.

LicensePlate.3mf contains two independent pink objects in a 210 × 292 mm staggered layout, within the H2D dual-nozzle area. Preserve the object positions on import. Print by layer. Both halves are 5 mm thick; there is no raised artwork.

Align both tongues and slide the halves together evenly until the frame shoulders meet. Install the two upper screws to retain the assembled position.

## Validation and files

Built and inspected in Fusion. Both halves are solid bodies. Their assembled geometry has zero overlapping volume, and the separated print layout has zero intersection. The 3MF was checked for two build objects, a 5 mm height, and bed bounds X 38.5–248.5 mm / Y 14–306 mm. Actual ABS fit has not yet been physically tested.

The folder includes LicensePlate.3mf, the self-contained LicensePlate.py recreation script, its manifest, Mockup.png showing the print layout, Assembled-Mockup.png, LicensePlate.f3d and Tongue-Groove-Test.3mf. Files are overwritten directly; this revision creates no archive folder. Duschablage.3mf was not modified.

To recreate in Fusion, add the LicensePlate folder through Scripts and Add-Ins and run LicensePlate. The script creates a new document and exports generated CAD files and previews to a Generated subfolder without overwriting the main packaged files.

The active Fusion document also has a single mesh-export body containing the two separated frame halves. LicensePlate-Both-Halves.stl and LicensePlate-Both-Halves.3mf are its one-body mesh exports. Both halves remain distinct physical pieces.
