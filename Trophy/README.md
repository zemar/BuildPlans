# Trophy

Run `Trophy.py` in Autodesk Fusion to generate a new 127 mm trophy.

- One continuous tapered base, without a bottom step: 88 × 64 mm at the bottom,
  76 × 52 mm at the top, 30 mm tall.
- An hourglass stand with a narrow middle, flared ends, a 120° decorative
  twist, and a matching ball cradle.
- White base lettering raised 1.2 mm from the sloped front: player name,
  `Valley Catholic`, and `Catholic Youth Organization`.
- `2026` on the volleyball front, in red digits raised 1.2 mm with curved
  outer surfaces following the sphere.

The model is Z-up, with the underside at Z=0. The `Trophy` component contains
Base, Stand, Volleyball, one connected white Writing body, and four red Year
bodies. A hidden backing connects the base letters; their anchors and the year
anchors occupy matching pockets, avoiding overlapping black/white material.

Edit `PLAYER_NAME`, then rerun. Export **Trophy → Save As Mesh → 3MF → Millimeter
→ One File**. In Bambu Studio, import all bodies as one multipart object and
assign black to Base and Stand; assign white to Volleyball and Writing; assign red to
the four Year digits. This version uses three filament colors. Configure the H2D and supports in Bambu Studio before slicing.

The script logs stages and exceptions to `Trophy.log` beside the Python file.
Prototype version is tracked in `Trophy.manifest` and recorded in the log.
The script creates the Fusion model; export 3MF manually from Fusion. It creates
no assets, exports, or tests folders and requires no helper scripts.
