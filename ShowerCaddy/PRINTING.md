# Printing the three components

Export components separately from Fusion. Preserve all bodies in `02 Engraving - multicolor` as parts of one object. Keep the original Fusion assembly in its assembled position; orient the exported components in Bambu Studio. No slicer settings are automatically applied by this script.

## Reinforced arm frame

Use **Lay on Face** on the large, flat **basket-facing face containing the nut-pocket openings**. This face is model +Y, at Y=0. Both long arms and their connecting crossbar should lie along the bed, with the hooks projecting upward. Do not print this frame with its 300 mm-long arms standing upright.

The nominal footprint in this orientation is **259 × 300 mm**, and height is **45.5 mm**. Check your printer's usable area, exclusions and brim space. A 256 × 256 mm bed cannot fit this orientation as described; do not scale the model to force it to fit. The strengthened frame may require a larger plate or a further design split for a smaller printer.

For a 0.4 mm nozzle and 0.20 mm layers, use these starting settings:

| Setting | Value |
| --- | --- |
| Filament | The selected structural PLA profile |
| Wall loops | **6** |
| Top/bottom shell layers | **6** |
| General infill | **30% gyroid** |
| Reinforced root regions | **100% infill using modifiers** |
| Print speed mode | Standard, not Sport/Ludicrous |
| Supports | Tree (auto), Strong, build plate only; inspect hook returns |
| Support material and interface | Same structural PLA |
| Top Z distance | 0.20 mm |

The black support setting is independent of the engraving's color filaments because the arm frame is printed separately. Inspect the sliced preview for support under elevated hook returns; avoid filling the blind bolt/nut pockets with unnecessary supports. This orientation requires much shorter supports than the former upright model.

Add two box modifiers, covering each widened arm root from its bottom through the end of the taper. In the original assembly coordinates these are:

- Left: X=0–45, Y=-10–0, Z=15–141.6.
- Right: X=214–259, Y=-10–0, Z=15–141.6.

Each box is **45 × 10 × 126.6 mm** in assembly coordinates. After orienting the part, position the modifiers over the corresponding root regions using the preview. Set their infill to 100%. As a simpler alternative, make the entire arm frame 100% infill; it consumes more material. Walls and solid infill alone do not establish a load rating.

## Basket

Print with the drainage floor on the plate. Use **6 wall loops** and **6 top/bottom shell layers**. Add 100% infill modifiers over both mounting pads (X=0–45 and 214–259, Y=0–8, Z=15–91.6 in assembly coordinates). Inspect the four horizontal bolt holes, rear pad undersides and front plate recess in the slicer for local support needs. Supports are no longer needed for tall hanging arms in this print.

## Engraving

Print the plate with its **flat back on the bed**, colored face upward. Keep the black backing and all 54 color bodies aligned as one multipart object. Assign black, white, green, red and brown PLA by body name. A 0.20 mm layer height gives three layers of 0.6 mm-deep colored detail. The plate needs no hook supports. Repaint or correct assignments if your exported format does not retain them.

## Fit and loading

Test the nut/bolt fits and the engraving recess before final assembly. The frame uses four M4 × 16 bolts, four M4 nuts and four roughly 1 mm washers. Assemble with the mating faces touching. The arm bores remain closed on the glass side with this hardware. Increase the service load gradually after assembly; the redesign has no measured load rating yet.
