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

`Trophy.scad` contains the complete prototype 4.4.3 exported from the latest
Fusion mesh, including exact lettering, hidden connections, texture, seams,
colors and the swirled rolled-net stand. All geometry is embedded; no imports,
fonts, libraries, or helper files are required. It is a fixed mesh snapshot,
not a parametric rewrite. Use `Trophy.py` to change the player or geometry.

Open in OpenSCAD, use F5 to preview and F6 to render. `PART` selects `all`,
`base`, `stand`, `ball`, `writing`, or `number`. Individual parts retain their
assembled coordinates. For separate material exports, import the parts together
in Bambu Studio as one multipart object and assign the reels manually.

Validated with OpenSCAD 2026.10.11 using its Manifold renderer: no geometry
errors; overall bounds 88 × 64.112 × 126.997 mm (nominal 127 mm tall). The
slightly extended depth includes raised lettering. `mockup.png` is the current
OpenSCAD preview. The Fusion source and manifest are unchanged.

Volleyball panel fix (4.4.3): explicit curved stripe grooves are verified on all
six spherical panel groups, including the back. Fusion solid checks and rear
visual inspection passed. Trophy.scad is refreshed from the corrected Fusion
geometry; older manually exported 3MF files must be exported again.
