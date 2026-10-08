# Drawer1 — removable brown bins

Run `Drawer1.py` in Fusion using `Drawer1.manifest`. The script creates four
independent, complete bins with continuous floors and walls. Each bin exports
as a flat, unrotated STL. Cut the long bins in Bambu Studio before printing.

Dimensions are mm and assume the drawer measurements are clear internal sizes.

| Bin | Clear width × length | Exterior width × length × height |
| --- | --- | --- |
| Long left | 116.2375 × 355.6 | 121.0375 × 360.4 × 65 |
| Short left | 116.2375 × 159.45 | 121.0375 × 164.25 × 65 |
| Long right | 116.2375 × 304.8 | 121.0375 × 309.6 × 65 |
| Short right | 116.2375 × 210.25 | 121.0375 × 215.05 × 65 |

The requested right-bin clear lengths total the drawer's full 527.05 mm length.
Keeping 304.8 mm clear in the long-right bin leaves 210.25 mm clear in the
short-right after subtracting four end walls, the gap, and outside clearance.
The arrangement is 242.475 × 525.05 mm inside the 244.475 × 527.05 × 76.2 mm
drawer. There is 1 mm clearance at each outside edge and 0.4 mm between bins.
Walls are 2.4 mm; floors are 2 mm. Clear height is 63 mm above the floor.

## Run and export

1. In Fusion open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this existing `Drawers` folder and run **Drawer1**.
3. Use the new timestamped directory under `exports/`. It contains four STLs:
   `Drawer1_Long_Left.stl`, `Drawer1_Long_Right.stl`,
   `Drawer1_Short_Left.stl`, and `Drawer1_Short_Right.stl`, plus `Drawer1.f3d`
   with the bins shown in their drawer positions.
4. Each run appends inputs, construction details, dimensions, export paths, and
   error tracebacks to `Drawer1.log`. Earlier logs and exports are preserved;
   use the newest export directory for this revision.

## Printing

Import each long bin into Bambu Studio and use **Cut** to create printable
sections before arranging the plate. The Fusion models contain no joints or
predefined seams. Choose the cut positions and any connectors in Bambu Studio.
The left long bin intentionally exports larger than the flat print area so
that you can choose its cut there.

Use the H2D profile, brown filament, and 100% scale. Keep the short bins flat on
their floors. After cutting a long bin, check each section's orientation and
bed contact before slicing. Inspect the sliced preview for support needs and
plate clearance, including any brim.

STL files do not embed filament or support settings. The script does not slice
or print. Local checks validate dimensions, drawer packing, and STL
normalization; Fusion execution and physical printing still need verification.
