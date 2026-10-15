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
