# Reinforced shower caddy assembly

Run `ShowerCaddy.py` in Fusion through **Utilities → Scripts and Add-Ins → Scripts**. The artwork is embedded in this single Python file; no assets folder, preparation script, package installation, or command-line step is needed. Every run creates a new, unsaved design and appends diagnostics to `ShowerCaddy.log`. Export manually from Fusion; no STL or other mesh export is generated automatically.

The design now has three aligned components in a rigid group:

| Component | Solids | Purpose |
| --- | ---: | --- |
| 01 Basket | 1 | Mesh-bottom basket, rear mounting pads, front artwork recess |
| 02 Engraving - multicolor | 55 | One black backing plus 54 white/green/red/brown inlays; print together as one plate |
| 03 Reinforced arms | 1 | Both hooks, widened arm roots and a connecting crossbar |

The engraving uses separate color bodies within one component as requested. It is not a single-material body. Do not arrange its individual color bodies separately in the slicer.

## Dimensions and reinforcement

All dimensions are millimeters. The basket remains **259 wide × 88.9 deep × 101.6 high**, including its 3 mm floor. Drainage uses 154 square openings, 8 mm wide with 3 mm webs. The hooks rise to a bridge underside at **305 mm from the basket bottom**, with **25.5 mm clear throat** and 30 mm downward returns. With thicker hook bridges the assembly is now **315 mm high**.

Arms are **25 mm wide × 10 mm thick**, increased from 6 mm thickness. Each root expands inward by 20 mm to a 45 mm-wide mounting web. Two tangent R25 arcs taper that web smoothly over **40 mm above the basket rim**. The root extends below the rim to 15 mm above the basket bottom. This removes the former abrupt arm-to-rim transition; the arms now connect mechanically to reinforced pads instead of growing from the basket wall.

The 25 mm-high bottom crossbar connects both arms into one printable frame. Inside hook bends have **4 mm fillets**. Arm edges are rounded in stages, retaining the existing 1 mm corner / 0.75 mm rim rounding where applicable. The frame's basket-facing surface is at Y=0; it occupies negative Y, outside the basket. The glass-contact plane is at Y=-10. The complete assembly depth is 134.4 mm, including hooks; the basket itself remains 88.9 mm deep.

## Mechanical assembly

Use **four M4 × 16 mm bolts, four standard M4 hex nuts, and four approximately 1 mm-thick M4 washers**. Hardware is not modeled as additional bodies. Stainless hardware is suitable for the wet location.

1. Place the nuts into the hexagonal pockets on the basket-facing side of the arm frame.
2. Align the frame against the basket's rear surface. Mount centers are X=12.5 and 246.5, each at Z=40 and 80.
3. From inside the basket, put a washer on each bolt and insert it through the 8 mm-thick reinforced rear pad into its captured nut. Tighten snugly without crushing the plastic.
4. Test-fit the engraving plate in the front recess and secure it with a thin layer of adhesive compatible with the printed plastic and wet use.

Bolt clearance holes are 4.5 mm. Nut pockets are 7.3 mm across flats and 3.6 mm deep. Arm bolt bores are **blind**, 8.5 mm deep, leaving 1.5 mm of plastic at the glass-facing side. With the specified bolts, washers and 8 mm pads, screw insertion into the arm is about 7 mm. Check actual hardware fit before assembling against the glass; printed fit and hardware dimensions vary.

## Engraving plate

The artwork remains approximately **72.97 × 80 mm**, including the central camel, panda rider, flag and mouth branch. The eye highlights and brown oval backdrop are preserved, without the white fur outline. The overall rounded black plate is approximately **80.97 × 88 × 1.8 mm**, with R3 corners. Its 0.6 mm-deep color inlays leave 1.2 mm backing.

A matching basket recess provides 0.2 mm clearance on each side and 0.15 mm adhesive space behind the plate, leaving 1.05 mm of the original front wall. The assembled artwork is flush with the basket front. All color regions are ordinary solid bodies, with names for manual filament assignment. Display appearances do not automatically select AMS slots. Five filament colors are used including black.

The [artwork preview](inlay-preview.png) shows the color layout. It is not a Fusion rendering of the new assembly. The former preparation script's finished CAD contours are embedded in `ShowerCaddy.py`, preserving the artwork exactly. Fusion reads and validates them using Python's standard library. Size, depth, and display colors remain adjustable using the constants at the top of the script.

## Printing and checks

Follow [PRINTING.md](PRINTING.md) for the changed arm orientation, six-wall recommendation and solid mounting-junction modifiers. These are slicer settings you must apply in Bambu Studio; CAD attributes only record the intent.

The script checks component/body counts, connected solids, feature health, artwork fit, and high-accuracy pocket volumes, and logs failures. The embedded artwork was checked against the previous asset byte-for-byte and through the dimension/fit validation. Fusion kernel execution and physical load testing of this redesigned assembly remain unverified. The previous integrated basket and artwork were successfully generated in Fusion; this revision needs a new run.

The first assembly run completed the basket, arm-frame solids and R4 hook bends, then failed the smaller arm fillet with `ASM_BL_END_TOO_CMPLX`. The arm corner and finishing fillets now enable tangent-chain propagation so they follow the curved hook edges instead of stopping at straight-to-arc transitions. Other components retain their existing fillet behavior. The sidecar records the tangent-chain setting and identifies this revision as `reinforced-assembly-v2-tangent-fillets`. Local checks passed; the revised fillets require a Fusion rerun. See Autodesk's [constant-radius tangent-chain option](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_FilletEdgeSetInputs_addConstantRadiusEdgeSet.htm).
