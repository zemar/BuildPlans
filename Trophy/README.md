# Trophy

Run `Trophy.py` inside Autodesk Fusion. Prototype version is recorded in
`Trophy.manifest`; stages and exceptions are saved beside it in `Trophy.log`.

The trophy is 127 mm tall and stands Z-up, with its underside at Z=0. It has:

- A continuous metallic-bronze tapered base, 88 × 64 mm at the bottom and
  76 × 52 mm at the top.
- Raised white lettering: `Myriam Howard` (7 mm tall) and `2026 Valley Catholic`.
- A black hourglass stand with a 120° decorative twist.
- A fine black volleyball net across the center stand, with two posts on the
  base, 0.8 mm strands, and a gentle 1.5 mm wave.
- A white volleyball with raised medium blue `#6` on its front.

The base uses a metallic bronze appearance in Fusion. Use metallic bronze
filament for the printed finish. This design uses four filament colors. All white base letters
are one connected body. The net and its two posts form another connected body.
Matching passages in the stand avoid overlapping net/stand volumes.

Edit `PLAYER_NAME` and `PLAYER_NUMBER` (currently `"#6"`) if needed, then rerun. Right-click **Trophy → Save As Mesh**,
choose **3MF → Millimeter → One File**, and save as `Trophy.3mf`. In Bambu Studio,
import all bodies as one multipart object. Assign metallic bronze to Base; black to Stand
and Net and Posts; white to Volleyball and Writing; medium blue to the Number characters.
Configure your H2D, filaments, and supports, then slice and inspect the result.

The script only creates the Fusion model. It does not automatically export,
create assets/exports/tests folders, or require helper scripts. Revised geometry
must be validated by running in Fusion and inspecting the manual 3MF export.
