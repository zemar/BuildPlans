# Shower caddy with sliding hook arms

Run `ShowerCaddy.py` in Fusion through **Utilities → Scripts and Add-Ins → Scripts**. It is self-contained and creates a new, unsaved design. Each run appends diagnostics to `ShowerCaddy.log`. Save and export manually from Fusion; the script generates no STL or 3MF files.

The assembly contains three components, each with one solid: **01 Basket**, **02 Left arm**, and **03 Right arm**. The front is plain, with its full 3 mm wall thickness. Artwork, colored bodies, and the artwork recess have been removed. The existing artwork preview and previously exported files are not regenerated or deleted.

## Preserved dimensions

All dimensions are millimeters.

| Feature | Dimension |
| --- | --- |
| External basket | 259 wide × 88.9 deep × 101.6 high |
| Floor / walls | 3 |
| Drainage | 154-opening grid, 8 square, with 3 webs; rear access notches interrupt the grid locally |
| Hook bridge underside above basket bottom | 305 |
| Clear glass throat | 25.5 |
| Hook return drop | 30 |
| Arm stock | 25 wide × 10 thick |
| Reinforced root width | 45, widening inward |
| Smooth root taper above basket rim | 40 high, two tangent R25 arcs |
| Overall assembly height | 315 |
| Inside hook bend radius | 4 |

The basket occupies X=0…259, Y=0…88.9, Z=0…101.6. Arms are behind the basket, at Y=-10…0; the hook throat extends to Y=-35.5 and the returns to Y=-45.5. Joint sockets project into the basket interior, preserving its external dimensions. Each socket occupies a 45 mm-wide region at the rear corner and is 12 mm deep.

## Sliding joint

The supplied `Duschablage.3mf` was inspected as mesh geometry and through its included images. Its arm feet have longitudinal retaining ridges and a seating foot. This design adapts that open sliding-joint principle to our larger basket and reinforced arms; it does not copy the reference basket or hook dimensions.

Each arm has a T-shaped tongue: a 25 mm-wide neck, a 33 mm-wide retaining head, and 8 mm projection into the basket. A matching groove opens through the back and both vertical ends of the basket socket. Its lips capture the tongue's wider ridges. **0.30 mm clearance per mating side** is included; adjust `JOINT_CLEARANCE` for your printer if necessary.

The tongue engages over **72.6 mm**, from Z=19 to Z=91.6. A **39 × 10 × 4 mm seating shoulder**, at Z=15…19, supports the socket from below. It is wider and deeper than the groove, preventing the basket from sliding downward past it. Open access notches in the rear wall and floor beneath each socket let the shoulders pass during assembly and removal. The fit is sliding, not a snap fit; there is no latch against deliberate upward removal. Joint profile corners use R0.4 and exposed joint edges R0.2. The basket and arms retain their larger exterior rounding.

1. Hold the two arms parallel, with tongues facing the basket.
2. Position the basket with the lower ends of its grooves just above the tongues. This requires approximately 73 mm of upward travel from the seated position.
3. Lower the basket along both tongues until both sockets rest on their shoulders. Assemble off the glass first if overhead clearance is limited.
4. Hang the assembled caddy over the glass. To remove the basket, lift it clear of the tongues.

No bolts, nuts, crossbar, or adhesive are required for these arm joints. Separate artwork can be attached to the plain front later.

## Verification

Local checks passed for Python syntax, the preserved dimensions, drainage count, closed rounded joint profiles, nominal male/female clearance, and shoulder bearing area. The script checks feature health and verifies that each finished component is one connected solid. Failures and tracebacks go to the sidecar log under revision `sliding-tongue-groove-v3`.

Fusion kernel execution, printed fit, and physical load capacity remain unverified for this revision. The prior exported `ShowerCaddy.3mf` is an older model; rerun this script and export the new design. See [PRINTING.md](PRINTING.md) for part orientation and fit checks.
