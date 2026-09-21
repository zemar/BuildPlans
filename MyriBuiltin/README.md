# Myri Built-in — VS Code and SketchUp

This project generates the measured bedroom built-in as native SketchUp
components. Every panel, shelf, drawer front, bed part and back panel is a
separate component.

## Start live reload on macOS

1. Put the `MyriBuiltin` folder somewhere permanent on your Mac.
2. Open that folder in VS Code.
3. Open SketchUp and choose **Window → Ruby Console**.
4. Enter the following command, replacing the path with the folder location:

   ```ruby
   load '/Users/your-name/Documents/MyriBuiltin/MyriBuiltin_LiveReload.rb'
   ```

5. Edit and save `MyriBuiltin.rb` in VS Code.

SketchUp checks the file approximately every 0.75 seconds. Each save removes
the previously generated `Myri Built-in` group and rebuilds it without changing
the current camera view.

## Stop live reload

Enter this in the SketchUp Ruby Console:

```ruby
MyriBuiltinLiveReload.stop
```

## Editing the design

- Major dimensions are collected in the `layout` method near the top.
- Parts are organized into room, back/divider, desk, bed and nightstand methods.
- All dimensions and origins are expressed in inches.
- The front elevation is desk-left, bed-center and nightstand-right.
- Upper cabinets and side fillers reach the 96-inch ceiling, with no top fascia.
- The nightstand is 12 inches deep, flush with the shelving above.

If a saved edit contains a Ruby error, the previous successful geometry remains
and the error is printed in SketchUp's Ruby Console. Correct the code and save
again to rebuild.

## Walnut materials and grain

The model uses `Myri Walnut Solid` and `Myri Walnut Plywood`, loaded from
`walnut_solid.png` and `walnut_plywood.png` beside the Ruby script.
Solid walnut is assigned to fillers, desk top, drawer fronts, bed rails
and footboard. Other wood parts use walnut plywood. These are visualization
assignments, not a construction specification.

In `wood_textures`, adjust `width` (image coverage in inches) to change grain
scale. The image aspect ratio is preserved. Current widths are estimates because
these photos have no physical scale. `tint: nil` keeps each image's original
color; use an RGB array such as `tint: [107, 70, 45]` to colorize it.
Missing images fall back to the palette color and print a console warning.

Textures are applied to component faces and positioned again on every rebuild.
Grain follows the longest part dimension by default. Append `grain: :x`,
`grain: :y`, or `grain: :z` to a `part(...)` call to override that direction.
Image U is used for solid walnut and V for plywood; the natural diagonal grain
in the solid walnut photograph remains visible. End faces reuse the same image;
this setup does not simulate end grain or exposed plywood layers.

Use SketchUp's Shaded with Textures face style to see the images. Save the Ruby
file to rebuild after changing material settings. If you replace only a PNG,
run `MyriBuiltinLiveReload.reload_script` in the Ruby Console to refresh it.
