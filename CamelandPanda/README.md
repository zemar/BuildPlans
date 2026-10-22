# Camel and Panda

Run **CamelandPanda.py** in Fusion. The single self-contained script creates a **200 × 150 × 10 mm** plaque with **0.4 mm-deep flush vector inlays**, a white base with 3 mm rounded edges, two uniform rear T grooves, and two white rear feet for a 15° lean.

The artwork is embedded into the base, from Z = 9.6 to 10 mm. The colored artwork is not raised. The exposed white background has 4,200 irregularly scattered small sand dimples, 0.08–0.17 mm deep, cleared from the artwork. The camel and riding panda use the exact closed vectors from `Crest/crest.py`, uniformly scaled by 2 and translated into the plaque composition. The small pandas use the central panda's actual face vectors: matching eye patches, pupils, highlights, nose, smile, and red tongue. Their seated bodies are drawn with smooth curves, folded hands, rounded haunches and overlapping feet. Both feet use the central panda's four white paw-pad shapes. The three standing bamboo plants reuse actual leaf shapes from the bamboo in the camel's mouth, with matching black outlines, curved veins, stem nodes, and leafy bases, and the pyramid uses straight geometric vector borders and course lines. All colored regions have mutually exclusive boundaries.

The palette matches Crest exactly: White #FFFFFF, Black #000000, Brown #975721, Red #D21923, Green #70A628. White areas are part of the white base. Each other colored region is a separate native solid in a matching pocket, with no overlapping color volumes.

Select **Plaque - five flush colors - Save as Mesh** in the Fusion browser to export the complete plaque. Each white foot has its own named parent component. Preserve the separate colored bodies when exporting. STL does not store colors.

Use **3MF**, millimeters, and **Structure: One File**. If the slicer displays **Multi-part object detected**, choose **Yes** to load one object with multiple parts. The 120 colored inlays start at Z = 9.6 mm, so they must retain their positions relative to the white base. Loading them as separate objects can drop them independently to the build plate. Export the feet separately.

The current **plaque.3mf** was repaired to contain one assembly build object referencing all 121 original meshes. Mesh coordinates, transforms, names, and the five used colors are unchanged. Bambu Studio 02.08.02.61 imports it as one 200 × 150 × 10 mm plaque with 121 parts and reports a manifold mesh. A fresh Fusion Save as Mesh export may prompt for multipart grouping again; choose Yes.

`CamelandPanda.svg` is the current vector artwork and preview, including an indication of the recessed white sand dimples. It supersedes the PNG preview and is not needed to run the script. Dimple shading in the SVG represents white surface geometry, not an additional material color.

The script writes diagnostics to **CamelandPanda.log**, checks plaque dimensions and solid volumes, and verifies every colored inlay spans exactly Z = 9.6–10 mm. The feet are native solids; no mesh import or temporary mesh files are used. There are no runtime asset folders, Python support files, or automatic export folders.

## Verification status

Verified in Fusion: 200 × 150 × 10 mm, 121 native plaque solids, all five appearances visible, and every colored inlay at Z = 9.6–10 mm. The white background uses 4,200 small, randomly scattered dimples with varied diameters (approximately 0.4–0.9 mm) and depths (0.08–0.17 mm), clear of the artwork. The plaque and two rear feet are grouped under separate named parent components for Save as Mesh.

Offline geometry checks also pass: exact unchanged Crest center vectors after scaling; valid closed vector regions; zero cross-color area overlap; palette identical to Crest. The small pandas and standing bamboo now reuse the central artwork's face, paw-pad and leaf geometry, respectively.

## Rear feet and sliding joinery

Two white feet are each **15 mm wide**, with a rear-only sole that holds the plaque at **15°** while its rounded bottom edge rests on the same tabletop. Each foot and its tongue form one native solid in its own Save as Mesh parent component.

The joint uses ShowerCaddy's rounded open T section, adapted to the plaque thickness: **11 mm neck, 15 mm head, 1.5 mm ridge shoulder depth, 3.6 mm total tongue depth**, **0.4 mm profile corner radius**, and **0.30 mm female clearance per side**. The female groove is 11.6 mm at the mouth, 15.6 mm behind the retaining lips, and 3.9 mm deep, leaving 6.1 mm to the plaque front.

The channels remain centered at X = 50 and 150 mm. Each uses one constant profile from Y = −1 to 75 mm, fully open to the back and through the plaque's bottom edge. There are no enlarged loading bays or changes in section. Insert each foot from the bottom and slide it upward to the closed upper stop. The seated tongue spans Y = 5–75 mm; its upper end seats against the closed channel stop. The wide support web sits 0.4 mm behind the plaque back so it clears the retaining lips throughout insertion.

The runtime checks both 15 mm foot widths, white appearances, single-solid construction, common tabletop contact, and collision-free insertion at five positions from assembled to withdrawn.

## OpenSCAD version

Open **CamelandPanda.scad** directly in OpenSCAD. It is self-contained, with all 120 current vector regions and all 4,200 sand dimples embedded from the Python version. Dimensions, flush inlays, five colors, rounded base, and both 15 mm white feet with bottom-loading rounded T joinery match the Fusion design. Curved surfaces are tessellated for OpenSCAD; their resolution controls are near the top of the file.

The **part** selector offers `assembly`, `plaque`, `feet`, `foot_1`, `foot_2`, `print_layout`, and each of the five material colors. The default assembly stands at 15° on Z = 0; `pose = "design"` shows its original Fusion coordinates. Plaque and individual-color outputs keep the common 200 × 150 mm registration. Foot outputs lie on their sides on Z = 0. `sand_texture` defaults to true.

F5 previews colors and F6 evaluates all geometry. The file was rendered and checked with OpenSCAD 2026.10.11 using the Manifold backend: exact 200 × 150 × 10 mm plaque, closed plaque and foot meshes, five used colors in a temporary 3MF export, 15 mm foot width, and collision-free insertion at five positions. The mesh volume differs from Fusion by 3.61 mm³ (0.0013%) due to tessellation. The current SVG continues to show the artwork.

For multicolor output, use a color-capable 3MF export or export the five material selections in their common registration. STL does not store colors. OpenSCAD writes diagnostics to its console; redirect CLI stderr to `CamelandPanda.scad.log` to retain a per-run sidecar. This file contains the verification results from creation.
