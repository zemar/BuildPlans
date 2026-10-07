"""Convert cleaned-artwork.png into a printable height field and CAD preview.
Requires Pillow, NumPy, SciPy. Fusion consumes the bundled binary height field.
The original user drawing remains untouched in assets/reference.jpg.
"""
from pathlib import Path
import struct
import zlib
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parent
NX, NY = 801, 601


# Physical fur relief at default plaque size, not just a display texture.
FUR_HEIGHT_MM = 0.20
FUR_SEED = 20190209


def add_fur(heights, material, xn, yn):
    panda = (((xn > .45) & (xn < .65) & (yn > .20) & (yn < .60)) |
             ((xn > .15) & (xn < .32) & (yn > .52)))
    panda &= np.isin(material, [1, 2])
    camel = ((xn > .26) & (xn < .83) & (yn > .18) &
             np.isin(material, [3, 4, 7]))
    camel &= ~((xn > .70) & (yn < .47))  # Exclude the pyramid.
    # Keep eyes/muzzles, panda faces and feet, and saddle trim smooth.
    def ellipse(cx, cy, rx, ry):
        return ((xn-cx)/rx)**2+((yn-cy)/ry)**2 < 1
    protected = (ellipse(.551,.288,.060,.061) |
                 ellipse(.247,.593,.046,.050) |
                 ellipse(.243,.809,.049,.051) |
                 ellipse(.322,.295,.075,.075) |
                 ellipse(.51,.56,.037,.035) |
                 ellipse(.27,.684,.05,.04) |
                 ellipse(.265,.901,.055,.047))
    protected |= (yn > .92)
    protected |= ((xn > .46) & (xn < .665) & (yn > .44) & (yn < .65))
    mask = (panda | camel) & ~protected
    # Fade at both silhouette and material boundaries to protect linework.
    clearance = np.zeros_like(heights)
    for color in (1,2,3,4,7):
        region = mask & (material == color)
        clearance = np.maximum(clearance, distance_transform_edt(region))
    fade = np.clip((clearance-1)/3,0,1)
    rng = np.random.default_rng(FUR_SEED)
    # Short, vertically oriented soft tufts: roughly 0.5–1 mm wide,
    # 1–2 mm long. Seeded noise avoids a mechanical repeating pattern.
    grain = gaussian_filter(rng.normal(size=heights.shape), (2.2,.65))
    grain = np.clip((grain/grain.std() + .7)/2.8,0,1)
    # Tall black fur uses shallow grooves to retain the 10 mm envelope.
    grain = np.where(heights > 2.8, grain-1.0, grain)
    delta = FUR_HEIGHT_MM * fade * grain
    result = np.minimum(3.0, heights + delta)
    assert np.array_equal(result[~mask], heights[~mask])
    print('Fur relief: max variation %.3f mm; %d textured samples' %
          (np.abs(result-heights).max(), np.count_nonzero(result!=heights)))
    return result


def build():
    src = Image.open(ROOT / 'assets/cleaned-artwork.png').convert('RGB')
    # Uniform fit within a 3 mm margin on the 200 x 150 mm plaque.
    scale = min(194 / src.width, 144 / src.height)
    size = (round(src.width*scale*4), round(src.height*scale*4))
    src = src.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', (NX, NY), 'white')
    canvas.paste(src, ((NX-size[0])//2, (NY-size[1])//2))
    rgb = np.asarray(canvas, dtype=float)/255
    r, g, b = rgb[:,:,0], rgb[:,:,1], rgb[:,:,2]
    # CAD material IDs: ivory backing, black, white, tan, brown, green, red, gold.
    material = np.full((NY,NX), 3, dtype=np.uint8)
    material[(r > .5) & (g > .4) & (b < .65)] = 7
    material[(r > g*1.25) & (g < .65) & (b < .4)] = 4
    material[(g > r*1.07) & (g > b*1.3)] = 5
    # Carpet purple and all red/pink tongues/flag share a single red material.
    material[((b > r*1.15) & (b > g*1.15)) |
             ((r > g*1.35) & (r > b*1.15)) |
             ((r > .55) & (r > g*1.2) & (b > g*1.05))] = 6
    # Restrict warm camel browns from being mistaken for red.
    warm = (r > g*1.35) & (r > b*1.15) & (g > b*1.6) & (g > .15)
    material[warm] = 3
    material[rgb.max(axis=2) < .40] = 1
    material[rgb.min(axis=2) > .72] = 2
    # Close silhouettes retain white panda faces/bellies and the flag center.
    # Pale off-white background is ignored entirely.
    silhouette = binary_fill_holes(rgb.min(axis=2) < .72)
    material[~silhouette] = 0
    black = rgb.max(axis=2) < .38
    white = rgb.min(axis=2) > .72
    yy, xx = np.mgrid[:NY,:NX]
    xn, yn = xx/(NX-1), yy/(NY-1)
    levels = np.full((NY,NX), 1.35)  # Camel body.
    levels[(g > r*1.07) & (g > b*1.3)] = 1.05  # Bamboo.
    levels[(b > r*1.15) & (b > g*1.15)] = 1.65  # Saddle.
    levels[(r > g*1.8) & (r > b*1.8)] = 2.05  # Flag and small red details.
    levels[(xn > .72) & (yn < .46)] = .95  # Pyramid behind the characters.
    # Three panda areas; only opaque silhouette pixels become raised material.
    panda = (((xn > .45) & (xn < .65) & (yn > .21) & (yn < .60)) |
             ((xn > .15) & (xn < .32) & (yn > .52)))
    levels[white & panda] = 1.95
    levels[white & (yn < .23)] = 1.6  # Flag's white stripe.
    # Give outlines the height of the nearest filled region plus a raised ridge.
    filled = silhouette & ~black
    nearest = distance_transform_edt(~filled, return_distances=False, return_indices=True)
    levels[black] = levels[nearest[0][black], nearest[1][black]]
    levels[black & panda] = 2.25
    levels += black * .45
    heights = gaussian_filter(np.where(silhouette, levels, 0.0), .8)
    heights *= 3.0/heights.max()
    heights = add_fur(heights, material, xn, yn)
    # Color-only correction: camel ears and forelock are tan, not tongue red.
    # Apply after fur calculation so existing relief geometry stays identical.
    camel_ears_hair = (xn > .26) & (xn < .42) & (yn > .16) & (yn < .29)
    material[camel_ears_hair & (material == 6)] = 3
    (ROOT/'assets/colors.bin.zlib').write_bytes(
        zlib.compress(struct.pack('<II',NX,NY)+material.tobytes(),9))
    heights[[0,-1],:] = 0
    heights[:,[0,-1]] = 0
    data = np.rint(heights/3*65535).astype('<u2')
    (ROOT/'assets/relief.bin.zlib').write_bytes(
        zlib.compress(struct.pack('<II', NX, NY)+data.tobytes(),9))
    # Lighting of the actual CAD height field (not a modification of the art).
    dy, dx = np.gradient(heights, 150/(NY-1), 200/(NX-1))
    normals = np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normals /= np.linalg.norm(normals,axis=-1)[:,:,None]
    light = np.array([-.5,.6,1.0]); light /= np.linalg.norm(light)
    shade = np.clip(.30+.65*(normals@light),.12,1)
    colors = shade[:,:,None]*np.array([227,207,168])
    Image.fromarray(colors.astype('uint8')).save(ROOT/'relief-preview.png')
    from CamelandPanda import PALETTE
    palette = np.array([rgb for _, rgb in PALETTE])
    color_preview = palette[material] * (.45 + .55*shade[:,:,None])
    Image.fromarray(color_preview.astype('uint8')).save(ROOT/'color-relief-preview.png')
    print('Clean relief:', NX, NY, 'peak', heights.max())


if __name__ == '__main__':
    build()
