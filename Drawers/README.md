# Drawer1 — four independently removable bins

Run `Drawer1.py` in Fusion using the included `Drawer1.manifest`. It creates four
separate solid trays in their drawer positions, with their own floors and walls.
Brown PETG appearance and material labels are retained. There are no shared walls,
split bins, or glued joints.

All dimensions are mm and assume clear internal drawer measurements.

| Item | Width × length × height |
| --- | --- |
| Drawer | 244.475 × 527.05 × 76.2 |
| Four-bin arrangement | 242.475 × 525.05 × 65 |
| Each long bin, exterior | 121.0375 × 360.4 × 65 |
| Each long bin, clear interior | 116.2375 × 355.6 × 63 |
| Each short bin, exterior | 121.0375 × 164.25 × 65 |
| Each short bin, clear interior | 116.2375 × 159.45 × 63 |
| Each long STL at 45°, print envelope | 121.0375 × 300.8032 × 300.8032 |

Two long bins sit side-by-side at the front, two short bins behind them.
Each bin has 2.4 mm walls and a 2 mm floor. There is 0.4 mm between bins,
1 mm clearance around the arrangement, and 11.2 mm above the walls.
The long bins have exactly 355.6 mm clear length, without extra end clearance
for the nominal 14-inch tools. Separate walls reduce the short-bin length from
the previous shared-wall layout. Change the constants in the script and rerun
to adjust dimensions.

## Run and export

1. In Fusion open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add the existing `Drawer1` folder and run **Drawer1**.
3. The script creates a new document and exports to `exports/<timestamp>/`:
   - `Drawer1_Long_Left.stl` and `Drawer1_Long_Right.stl`: already tilted 45°.
   - `Drawer1_Short_Left.stl` and `Drawer1_Short_Right.stl`: flat on their floors.
   - `Drawer1.f3d`: editable archive with all four bins upright in drawer positions.
4. Use the latest export directory; older STLs represent earlier layouts.

Every run appends inputs, geometry checks, export dimensions, warnings, and full
error tracebacks to `Drawer1.log` alongside the script. The Fusion archive remains
upright; the script rotates only the exported STL coordinates and normals, then
places each mesh at Z=0. This rotation does not change the bin dimensions.

## Print in Bambu Studio

Select the H2D single-nozzle profile and your **brown PETG** filament profile.
Import each long STL on a separate plate at 100% scale. **Keep the supplied 45°
orientation**: do not auto-orient or lay it flat. Enable supports, including beneath
the inclined floor, and use a brim for bed adhesion. The tilted bin contacts the
bed along an edge, so supports are essential. Preview the slice and ensure all
unsupported regions are covered and that supports and brim stay within the bed.
Support settings are slicer settings and are NOT embedded in STL files.

The calculated long-bin envelope fits the H2D single-nozzle
[325 × 320 × 325 mm build volume](https://eu.store.bambulab.com/products/h2d),
with an 8 mm allowance on each horizontal side. Actual generated supports may
extend farther; confirm the complete sliced footprint. These parts have not been
sliced or physically print-tested here. Tilted printing consumes additional
support material and leaves support-contact marks.

The short bins print flat without supports; both can fit on one plate side-by-side.
Thus there are four one-piece bins, typically **three plates total** (two long-bin
plates and one plate holding both short bins). Select filament-specific temperatures
and plate preparation for your actual spool and plate. STL files do not store color.

The script requires Fusion's bundled `adsk` modules. Local checks cover dimensions,
Python syntax, and STL rotation; Fusion must be run to verify the new CAD solids.
