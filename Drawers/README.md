# Drawer projects — removable brown bins

## drawer_553x526

Run `drawer_553x526.py` using its matching manifest. The drawer is 553 × 526 ×
80 mm. The script creates 14 independently removable bins in a new Fusion
document for preview. The requested internal dimensions are minimum sizes;
the bins are enlarged to fill the 551 × 524 mm usable footprint completely.
Adjacent outside walls butt together with no gap between bins. There is still
1 mm clearance at each drawer edge.

[Fusion preview](mockup.png)

The ten front bins share a 280 mm internal depth (284.8 mm outside). They run
left to right in the order shown below. All dimensions are mm.

| Front component names | Internal width × depth |
| --- | --- |
| Tablespoons 1, Tablespoons 2 | 51.3 × 280 each |
| Forks 1, Forks 2 | 31.3 × 280 each |
| Knives | 71.3 × 280 |
| Teaspoons | 41.3 × 280 |
| Dessert Forks | 41.3 × 280 |
| Butter Knives | 51.3 × 280 |
| Chopsticks | 61.3 × 280 |
| Fancy Chopsticks | 71.3 × 280 |

Four bins fill the rear area in two columns:

| Rear component name | Internal width × depth |
| --- | --- |
| Napkins | 300 × 129.6 |
| Serving Utensils | 300 × 100 |
| Serving Spoons | 241.4 × 109.6 |
| Napkin Rings | 241.4 × 120 |

Each bin has 2.4 mm walls, a 2 mm floor, 80 mm outside height, and 78 mm clear
height. Add 4.8 mm to each listed plan dimension for its outside size. Outside
corners are square so adjoining bins meet fully; inside corners retain a
2.6 mm radius. Internal sizes are the spans between opposing inner walls.

Each bin has one parent component named for its contents for **Save As Mesh**,
with its body named to match. Duplicate bins are numbered. The script
writes `drawer_553x526.log` beside itself when run. It does not export files or
save the new document automatically. Review the preview in Fusion before
saving or exporting individual components with **Save As Mesh**. Placement and
minimum dimensions are checked in the script; no external Python packages are
needed in Fusion.

## drawer_322x526

Run `drawer_322x526.py` in Fusion using `drawer_322x526.manifest`. The script creates five
independent, complete bins with continuous floors and walls in a new Fusion
document. Save and export them manually in Fusion. Cut the long bins in Bambu
Studio before printing.

Dimensions are mm and assume the drawer measurements are clear internal sizes.

| Bin | Clear width × length | Exterior width × length × height |
| --- | --- | --- |
| Front | 315.2 × 95.2 | 320 × 100 × 80 |
| Long left | 194.8 × 250.00 | 199.6 × 254.80 × 80 |
| Short left | 194.8 × 163.60 | 199.6 × 168.40 × 80 |
| Middle right (`drawer_322x526_Long_Right`) | 115.2 × 158.2 | 120 × 163 × 80 |
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
`drawer_322x526_Short_Right`. Walls are 2.4 mm; floors are 2 mm. Outside plan-view corners are rounded to a
5 mm radius and inside corners to a 2.6 mm radius to preserve wall thickness.
Clear height is 78 mm.

## Run and export

1. In Fusion open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this existing `Drawers` folder and run **drawer_322x526**.
3. Save the new design in Fusion. Right-click an individual bin component in
   the Browser and choose **Save As Mesh** to export it as 3MF or STL in mm.
4. Each run appends inputs, construction details, dimension checks, appearance, and
   error tracebacks to `drawer_322x526.log`.

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
