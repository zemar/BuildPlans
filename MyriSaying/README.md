# MyriSaying

`MyriSaying.py` is the only Python script. Run it **inside Autodesk Fusion**:

1. Open **Utilities → Scripts and Add-Ins → Scripts**.
2. Add this `MyriSaying` folder, select **MyriSaying**, and click **Run**.
3. Save the new design in Fusion. The script also writes four 3MF files listed below.

Keep `MyriSaying.manifest` beside the script so Fusion can discover it. No package installation, external font files, assets folder, or exports folder is required. The exact cursive geometry is embedded. The structural panel and both feet are native Fusion solids; the brown rope frame and white lettering are separate colored mesh bodies.

Each Fusion run appends timestamped inputs, dimension and joint checks, creation stages, and errors to **`MyriSaying.log`**, and refreshes **`mockup.png`** from the Fusion viewport. It creates no support scripts or output folders.

Current design:

- **200 × 100 mm face, 15 mm panel**, black background. Decorative relief is additional to the panel thickness.
- **7 mm outer corner radius** on the plaque outline and exposed upper/rear corners of the feet. The rope follows the rounded plaque outline. The flat bearing faces and small mating-joint edges retain their functional geometry.
- **Brown twisted-rope border**, 6 mm wide, projecting up to approximately 2.5 mm beyond the face.
- **White Snell Roundhand Bold lettering**, raised 1.2 mm, with a larger saying and smaller name/date.
- **15° backward lean from vertical** with two removable black feet, each **15 mm thick across X**. The soles remain flat; the rear tip is rounded within the 65 mm design envelope.
- **The same open ridged tongue-and-groove as `CamelandPanda.py`:** two continuous T-shaped rails on the feet slide into matching grooves in the plaque's back. The grooves are open to the back and bottom, with closed upper seating stops at 75 mm along the plaque. There are no transverse locking teeth or enclosed loading pockets.

The tongues copy CamelandPanda's **11 mm neck, 15 mm head, 1.5 mm step, and 3.6 mm depth**. The two longitudinal side ridges engage behind the groove lips. Matching grooves allow **0.30 mm per mating side**; nominal head width is 15.6 mm, neck width 11.6 mm, and depth 3.9 mm. Joint corners have the same **0.40 mm radii**, and each rail engages from **5 to 75 mm** along the plaque (70 mm engagement). The foot web retains the 0.4 mm back clearance and 0.5 mm easing beside the joint; its exposed upper/rear outline has R7 corners. At least **11.1 mm** of solid panel remains in front of the rear channels. The joint geometry is copied into this self-contained script; it does not import or require CamelandPanda at runtime.

Slide each foot's tongue into its groove from the plaque's lower edge until it reaches the closed upper stop. The black structure continues behind a 2 mm-deep brown frame inlay, so the bottom entries do not cut through the visible rope decoration.

The **MyriSaying - assembled display** parent contains three printable parent components: **Plaque - three colors - Save as Mesh**, **Left foot - Black - Save as Mesh**, and **Right foot - Black - Save as Mesh**. Select one of these components to export that complete printable object. Keep the plaque's black, brown, and white bodies together for multicolor printing.

> The super power that you'll
> never lose is being the
> best daddy ever.
>
> Myriam Howard
> March 19, 2023

Thickness, relief, lean, rope settings, support dimensions, and colors can be changed in the constants near the top of the script. The embedded lettering preserves this specific inscription, font, layout, face dimensions, and border width; those settings must remain matched to the embedded geometry.

Verified in Fusion: exact 200 × 100 × 15 mm panel stock, 15 mm foot widths, actual 15° panel face angle, single connected solid per foot, and two flat soles at Z = 0. Solid-kernel checks found no interference at insertion offsets of 0, 10, 30, 70, and 76 mm; positive interference beyond the upper stop and across the retaining lips confirms both features engage. Male and female profile coordinates and joint constants were also compared directly with `CamelandPanda.py` and match exactly. The equal-density center of mass lies inside the support footprint. Matte black/brown/white appearances and the refreshed mockup were inspected. Physical printing and fit have not been tested; the clearance is an initial manufacturing allowance.

## Mesh files and Bambu Studio

Each successful run regenerates these four files directly in this folder:

- **MyriSaying.3mf** — the complete print plate, with exactly three top-level objects: one plaque and the separate left and right feet. The plaque contains registered black, brown, and white parts. The plaque is laid on its back with the writing facing up and measures **200 × 100 × 17.5 mm**, including the rope relief above the 15 mm structural panel.
- **plaque.3mf** — just the plaque as one multipart object with its three color parts.
- **left_foot.3mf** and **right_foot.3mf** — one foot object apiece, laid on their broad sides and 15 mm high for printing.

All files explicitly declare **millimeter** units. Import `MyriSaying.3mf` to bring in three objects; keep the plaque's black, brown, and white parts together as one multipart object, while the left and right feet remain separate objects. Assign the corresponding filaments to the plaque's parts in Bambu Studio. The Fusion design also has three named printable parent components. For manual **Save as Mesh**, select the complete parent component and use millimeters. Use the generated 3MF rather than Fusion's direct 3MF export to preserve the plaque's single-object grouping.

The script verifies that the complete 3MF contains exactly three build objects: the plaque with three color parts and each foot as one separate object. The native solids and each decorative mesh pass closed-mesh/winding checks before export. Bambu Studio's importer previously read the plaque as manifold at 200 × 100 × 17.5 mm, with zero repaired/removed/reversed facets. In Bambu's generic import, the plaque parts appear in this order: black plaque, brown rope, white writing; assign filament colors in that order if names are replaced. Its reported mesh shell count includes disconnected lettering regions; that is distinct from the single top-level plaque object.

`MyriSaying.scad` is an earlier reference snapshot and does **not** include this rounded 15 mm revision. `MyriSaying.py` is the current source. `mockup.png` is refreshed from Fusion on each successful run.
