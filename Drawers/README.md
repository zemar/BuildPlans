# Drawer1 — removable brown bins with snap joints

Run `Drawer1.py` in Fusion using `Drawer1.manifest`. The script creates four bins
as **six separately printable pieces**. Each long bin has a front and rear half
that snap together. Both short bins are single-piece trays. All pieces now print
flat; the previous tilted STLs and 3MF files are obsolete for this revision.

Dimensions are mm and assume the drawer measurements are clear internal sizes.

| Bin | Clear width × length | Assembled exterior width × length × height |
| --- | --- | --- |
| Long left | 116.2375 × 355.6 (14 in) | 121.0375 × 360.4 × 65 |
| Short left | 116.2375 × 159.45 | 121.0375 × 164.25 × 65 |
| Long right | 116.2375 × 304.8 (12 in) | 121.0375 × 309.6 × 65 |
| Short right | 116.2375 × 210.25 (about 8.28 in) | 121.0375 × 215.05 × 65 |

The requested 12 + 8.75 inches equals the drawer's entire 20.75-inch length.
Keeping 12 inches clear in the long-right bin leaves 210.25 mm clear in the
short-right after subtracting four end walls, the gap, and outside clearance.
The arrangement remains 242.475 × 525.05 mm inside the 244.475 × 527.05 mm drawer.
There is 1 mm clearance at each outside edge and 0.4 mm between independent bins.
Walls are 2.4 mm; floors are 2 mm. Standard clear height is 63 mm above the floor.
The snap socket roofs rise to 3.5 mm above the underside locally.

## Snap joint and assembly

Each long bin has a 0.3 mm seam gap and no transverse wall at its seam. Two pairs
of flexible floor fingers slide into covered sockets in the rear half. Tapered
noses compress the fingers inward; shoulders latch into wider pockets. Socket
roofs capture the fingers vertically. The clips stay within the assembled bin's
footprint and do not project into neighboring bins.

Print the mating halves separately, floor down, **supports off**. The socket roofs
have short bridges up to 8.4 mm wide; inspect these in the slicer. Remove any brim
or elephant-foot interference from the fingers and socket mouths. Slide front
and rear together on a flat surface until both joints engage. The seam should
remain approximately 0.3 mm. To release, access the open socket undersides and
squeeze the finger tips inward while separating the halves. Support both halves
when lifting a loaded bin; the joint has not been load-tested.

**Test the fit first:** set `JOINT_TEST_ONLY = True` and rerun to export two small
40 mm-wide test pieces using the same joint geometry. Print them with the same
filament and slicer settings intended for the bins. After checking fit, restore
`JOINT_TEST_ONLY = False` and rerun. These are prototype snap fits; printer/material
variation may require adjustment. Matching parts need clearance, as described in
[Prusa's design guidance](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135).

## Run and export

1. In Fusion open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this existing `Drawers` folder and run **Drawer1**.
3. Use the new timestamped directory under `exports/`. It contains:
   - `Drawer1_Long_Left_Front.stl` and `Drawer1_Long_Left_Rear.stl`
   - `Drawer1_Long_Right_Front.stl` and `Drawer1_Long_Right_Rear.stl`
   - `Drawer1_Short_Left.stl` and `Drawer1_Short_Right.stl`
   - `Drawer1.f3d`, with the pieces shown assembled.
4. Each run appends inputs, construction details, dimensions, export paths, and
   error tracebacks to `Drawer1.log`. Earlier logs and exports are preserved.

## Printing

Use the H2D single-nozzle profile, brown filament, 100% scale, floor down, no supports.
An 8 mm brim allowance is included in the geometry fit checks. Check the actual
brim footprint and socket bridges in the sliced preview before printing.

| Piece | Print envelope: width × length × height (mm) |
| --- | --- |
| Left front, including fingers | 121.0375 × 198.05 × 65 |
| Left rear | 121.0375 × 180.05 × 65 |
| Right front, including fingers | 121.0375 × 172.65 × 65 |
| Right rear | 121.0375 × 154.65 × 65 |
| Short left | 121.0375 × 164.25 × 65 |
| Short right | 121.0375 × 215.05 × 65 |

All six pieces individually fit the H2D flat. Two pieces can generally share a
plate side-by-side; verify spacing and brim clearance in Bambu Studio. STL files
do not embed filament or support settings. The script does not slice or print.
Local checks validate layout and snap geometry; Fusion execution and physical
snap-fit testing are still required for this revision.
