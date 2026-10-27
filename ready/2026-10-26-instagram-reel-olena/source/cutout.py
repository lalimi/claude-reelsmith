"""Cut the plain off-white background out of the fal.ai illustrations.

Usage: python3 source/cutout.py assets/fal/raw/*.png --out assets/fal

Flood-fills the background from the image border (so white areas enclosed by
the ink outline stay), softens the edge band, removes the light halo by
un-mixing the background colour, crops to the object (small previews are also upscaled 2x).
"""
import argparse
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

T_FILL = 26   # colour distance still counted as background for the flood fill
T_LO, T_HI = 18, 70  # soft alpha ramp inside the 2 px edge band


def cutout(src: pathlib.Path) -> Image.Image:
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))

    near = Image.fromarray(np.where(dist < T_FILL, 255, 0).astype(np.uint8)).copy()
    for x, y in [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + \
                [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]:
        if near.getpixel((x, y)) == 255:
            ImageDraw.floodfill(near, (x, y), 128)
    region = np.asarray(near) == 128

    band = np.asarray(Image.fromarray((region * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    band &= ~region
    alpha = np.where(region, 0.0, 1.0)
    ramp = np.clip((dist - T_LO) / (T_HI - T_LO), 0, 1)
    alpha = np.where(band, ramp, alpha)

    a = np.maximum(alpha, 1e-3)[..., None]
    unmixed = np.clip((rgb - (1 - a) * bg) / a, 0, 255)
    out = np.where(band[..., None], unmixed, rgb)
    rgba = np.dstack([out, alpha * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")

    ys, xs = np.nonzero(alpha > 0.05)
    pad = 10
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
    im = im.crop(box)
    if h < 1000:  # small previews get 2x, full-size originals stay as they are
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    for f in map(pathlib.Path, args.files):
        im = cutout(f)
        dst = out / (f.stem + ".png")
        im.save(dst, optimize=True)
        print(f"{dst}  {im.width}x{im.height}")


if __name__ == "__main__":
    main()
