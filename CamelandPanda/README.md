# Camel and Panda

Run **CamelandPanda.py** in Fusion. The single self-contained script creates a **200 × 150 × 10 mm** plaque with **0.4 mm-deep flush vector inlays**, a white base with 3 mm rounded edges, two rear dovetail slots, and two white rear feet for a 15° lean.

The artwork is embedded into the base, from Z = 9.6 to 10 mm. The colored artwork is not raised. The exposed white background has 4,200 irregularly scattered small sand dimples, 0.08–0.17 mm deep, cleared from the artwork. The camel and riding panda use the exact closed vectors from `Crest/crest.py`, uniformly scaled by 2 and translated into the plaque composition. The small pandas use the central panda's actual face vectors: matching eye patches, pupils, highlights, nose, smile, and red tongue. Their seated bodies are drawn with smooth curves, folded hands, rounded haunches and overlapping feet. Both feet use the central panda's four white paw-pad shapes. The three standing bamboo plants reuse actual leaf shapes from the bamboo in the camel's mouth, with matching black outlines, curved veins, stem nodes, and leafy bases, and the pyramid uses straight geometric vector borders and course lines. All colored regions have mutually exclusive boundaries.

The palette matches Crest exactly: White #FFFFFF, Black #000000, Brown #975721, Red #D21923, Green #70A628. White areas are part of the white base. Each other colored region is a separate native solid in a matching pocket, with no overlapping color volumes.

Select **Plaque - five flush colors - Save as Mesh** in the Fusion browser to export the complete plaque. Each white foot has its own named parent component. Preserve the separate colored bodies when exporting. STL does not store colors.

`CamelandPanda.svg` is the current vector artwork and preview, including an indication of the recessed white sand dimples. It supersedes the PNG preview and is not needed to run the script. Dimple shading in the SVG represents white surface geometry, not an additional material color.

The script writes diagnostics to **CamelandPanda.log**, checks plaque dimensions and solid volumes, and verifies every colored inlay spans exactly Z = 9.6–10 mm. Temporary foot mesh files are removed automatically. There are no runtime asset folders, Python support files, or automatic export folders.

## Verification status

Verified in Fusion: 200 × 150 × 10 mm, 121 native plaque solids, all five appearances visible, and every colored inlay at Z = 9.6–10 mm. The white background uses 4,200 small, randomly scattered dimples with varied diameters (approximately 0.4–0.9 mm) and depths (0.08–0.17 mm), clear of the artwork. The plaque and two rear feet are grouped under separate named parent components for Save as Mesh.

Offline geometry checks also pass: exact unchanged Crest center vectors after scaling; valid closed vector regions; zero cross-color area overlap; palette identical to Crest. The small pandas and standing bamboo now reuse the central artwork's face, paw-pad and leaf geometry, respectively.
