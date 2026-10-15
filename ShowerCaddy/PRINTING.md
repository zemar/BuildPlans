# Printing the sliding-joint caddy

Generate a fresh model by running `ShowerCaddy.py` in Fusion. Export the basket and each arm as separate printable objects. The existing `ShowerCaddy.3mf` is not updated by the script. If Bambu Studio offers to load only geometry from Fusion's 3MF, use that option and configure your printer and filament in Bambu Studio.

## Orientation

Print the basket upright, floor on the build plate, with the socket channels vertical. They are open through their bottom and top; keep support out of the sliding channels.

Print each arm on its **straight outer side face**: X=0 for the left arm and X=259 for the right arm in the Fusion assembly. This puts the long arm and hook profile parallel to the build plate. The hook itself then has no elevated bridge across its throat. The ridged tongue and seating shoulder project sideways from the arm and can require local support in this orientation. Inspect the sliced overhangs and apply manual support only beneath those projections as needed; carefully clean the mating surfaces afterward.

The former basket-facing-face-down orientation no longer applies because the new tongues project from that face. Do not print the arms standing upright as assembled: that recreates the weak layer orientation implicated in the earlier horizontal break.

The arms are mirrored parts. Print one left and one right. Keep them as separate objects for orientation rather than preserving their assembled positions on the plate.

## Strength and fit

Retain the earlier six-wall recommendation and solid local infill at the arm roots, seating shoulders, tongues, and basket sockets. These are manual slicer settings; the Fusion script does not change your Bambu Studio profile. Select the intended PLA filament and map it to the correct AMS reel.

Before committing to full-size parts, make a short fit sample from a common section through a tongue and socket, preserving their original scale and mating surfaces. The modeled clearance is 0.30 mm per side. The joint should slide by hand without forcing the retaining lips apart. Change `JOINT_CLEARANCE` and rerun Fusion if fit requires adjustment.

Both sockets must seat on their arm shoulders. Confirm that neither arm is partially inserted or carrying the entire basket by itself. Start with a light load and check for cracking or permanent deformation. No load rating has been established for the revised printed joint.

Attach the separately printed artwork to the plain front after printing. This script no longer generates artwork or a recess.
