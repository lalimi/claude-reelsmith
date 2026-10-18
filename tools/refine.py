"""Clean up Vision cut-outs: temporal alpha smoothing, edge trim + feather, optional sticker outline.
Usage: python3 tools/refine.py <cutouts-dir> <out-dir> [outline-px] [outline-hex]
"""
import sys, pathlib
import cv2
import numpy as np

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
px = int(sys.argv[3]) if len(sys.argv) > 3 else 0
col = sys.argv[4] if len(sys.argv) > 4 else "ffffff"
bgr = np.array([int(col[i:i + 2], 16) for i in (4, 2, 0)], np.float32)
out.mkdir(parents=True, exist_ok=True)
files = sorted(src.glob("*.png"))
imgs = [cv2.imread(str(f), cv2.IMREAD_UNCHANGED) for f in files]
alphas = [im[:, :, 3].astype(np.float32) / 255 for im in imgs]
trim = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
ring = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)) if px else None
for i, (f, im) in enumerate(zip(files, imgs)):
    a = .25 * alphas[max(i - 1, 0)] + .5 * alphas[i] + .25 * alphas[min(i + 1, len(files) - 1)]
    hard = (a > .5).astype(np.uint8)
    hard = cv2.morphologyEx(hard, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))  # drop slivers
    hard = cv2.erode(hard, trim)
    a = cv2.GaussianBlur(hard.astype(np.float32), (0, 0), 1.2)
    rgb = im[:, :, :3].astype(np.float32)
    if px:
        o = cv2.GaussianBlur(cv2.dilate(hard, ring).astype(np.float32), (0, 0), 1.0)
        rgb = rgb * a[..., None] + bgr * (1 - a[..., None])  # outline colour under the subject
        a = np.maximum(a, o)
    cv2.imwrite(str(out / f.name), np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8))
print("refined:", len(files), "outline", px, col if px else "")
