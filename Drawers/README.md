# Drawer1 — removable brown bins

Run `Drawer1.py` in Fusion using `Drawer1.manifest`. The script creates five
independent, complete bins with continuous floors and walls in a new Fusion
document. Save and export them manually in Fusion. Cut the long bins in Bambu
Studio before printing.

Dimensions are mm and assume the drawer measurements are clear internal sizes.

| Bin | Clear width × length | Exterior width × length × height |
| --- | --- | --- |
| Front | 315.2 × 95.2 | 320 × 100 × 80 |
| Long left | 194.8 × 250.00 | 199.6 × 254.80 × 80 |
| Short left | 194.8 × 163.60 | 199.6 × 168.40 × 80 |
| Middle right (`Drawer1_Long_Right`) | 115.2 × 158.2 | 120 × 163 × 80 |
| Short right | 115.2 × 255.4 | 120 × 260.2 × 80 |

The drawer is 322 × 526 × 80 mm. The arrangement occupies 320 × 524 × 80 mm.
The specified 2 mm horizontal clearance is total (1 mm per side), which preserves
the requested 320 mm front-bin outside width. All bins use the full 80 mm height
with no extra height clearance, as requested. The Fusion placements include the
1 mm inset from the drawer origin in both horizontal axes.

The 100 mm-deep front bin spans the full available width. A 0.4 mm gap separates
it from the bins behind it. The left middle bin has a 250 mm clear length; the
left back bin uses the remaining space.
The middle-right bin is 120 mm wide × 163 mm deep outside and sits against the
right edge. Both left bins widen to fill the adjacent space, and the back-right
bin extends behind the middle-right bin to the back of the drawer. Only 0.4 mm
assembly gaps remain between bins. The rear-right bin keeps its component name
`Drawer1_Short_Right`. Walls are 2.4 mm; floors are 2 mm. Outside plan-view corners are rounded to a
5 mm radius and inside corners to a 2.6 mm radius to preserve wall thickness.
Clear height is 78 mm.

## Run and export

1. In Fusion open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this existing `Drawers` folder and run **Drawer1**.
3. Save the new design in Fusion. Right-click an individual bin component in
   the Browser and choose **Save As Mesh** to export it as 3MF or STL in mm.
4. Each run appends inputs, construction details, dimension checks, appearance, and
   error tracebacks to `Drawer1.log`.

## Printing

Import a bin into Bambu Studio and use **Cut** as needed to create printable
sections before arranging the plate. The Fusion models contain no joints or
predefined seams. Choose the cut positions and any connectors in Bambu Studio.
The left long bin is larger than the flat print area so
that you can choose its cut there.

Use the H2D profile, brown filament, and 100% scale. Keep the short bins flat on
their floors. After cutting a long bin, check each section's orientation and
bed contact before slicing. Inspect the sliced preview for support needs and
plate clearance, including any brim.

STL files do not embed filament or support settings. The script creates the
Fusion model and sidecar log; mesh export and printing are manual.
