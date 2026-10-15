# Trophy

Run `Trophy.py` in Autodesk Fusion. Version is tracked in `Trophy.manifest`;
run stages and errors are saved beside the script in `Trophy.log`.

The 127 mm trophy has a medium blue tapered base with shallow diamond grooves on its sides and back and a tightly woven, rolled-net mesh
stand. Thirty-two 1.6 mm spiral strands cross in opposite directions around a
gathered oval sleeve with a narrow waist, curved centerline, and 180° corkscrew swirl to form small diamond openings, joined to a solid foot and ball cradle. The former side net and
posts are removed. Raised white base text reads the configured player name and
`2026 Valley Catholic`. `PLAYER_NUMBER` controls the raised medium blue number
on the white volleyball.

Edit `PLAYER_NAME` and `PLAYER_NUMBER`, then rerun. Export the **Trophy** component
using **Save As Mesh → 3MF → Millimeter → One File**. Import all bodies into Bambu
Studio as one multipart object. Assign black to Mesh Stand, white to
Volleyball and Writing, and medium blue to Base and the Number bodies.

The model stands Z-up with the base underside at Z=0. The upward spiral ribs
avoid the former net's long horizontal strands. Inspect slicing and support
placement around the open weave and ball before printing; the revised stand
has not been physically print-tested.

Only the Fusion model is generated. No helper scripts or assets, exports, or
tests folders are created; export 3MF manually from Fusion.

## OpenSCAD version

`Trophy.scad` is a self-contained editable conversion of prototype 4.4.2.
Open it in OpenSCAD, edit `PLAYER_NAME` and `PLAYER_NUMBER`, preview with F5
and render with F6. It preserves the millimeter dimensions, Z-up orientation,
three colors, recessed texture, grooved ball and swirling mesh geometry.
Text metrics and tessellation differ slightly from Fusion.

Use `PART` to select `base`, `stand`, `ball`, `writing`, or `number` for separate
exports. Import the exported parts together into Bambu Studio as one multipart
object and preserve their assembled positions. Assign the filaments manually;
preview colors alone do not guarantee multicolor 3MF export in every OpenSCAD
version. `Trophy.py` remains the Fusion source, and `Trophy.manifest` tracks the
prototype version. The OpenSCAD file has not been rendered locally because
OpenSCAD is not installed.
