"""Clean background plates: remove the cut-out subject from each frame (cheap inpaint).
Usage: python3 tools/plate.py <frames-dir> <cutouts-dir> <out-dir> [count]
"""
import sys, pathlib
import cv2
import numpy as np

src, cut, out = map(pathlib.Path, sys.argv[1:4])
count = int(sys.argv[4]) if len(sys.argv) > 4 else None
out.mkdir(parents=True, exist_ok=True)
frames = sorted(src.glob("*.jpg"))[:count]
k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (71, 71))
for f in frames:
    img = cv2.imread(str(f))
    a = cv2.imread(str(cut / (f.stem + ".png")), cv2.IMREAD_UNCHANGED)[:, :, 3]
    mask = cv2.dilate((a > 8).astype(np.uint8) * 255, k)
    h, w = img.shape[:2]
    small = cv2.inpaint(cv2.resize(img, (w // 4, h // 4)), cv2.resize(mask, (w // 4, h // 4)), 9, cv2.INPAINT_TELEA)
    fill = cv2.GaussianBlur(cv2.resize(small, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 6)
    m = cv2.GaussianBlur(mask, (0, 0), 8)[:, :, None] / 255.0
    cv2.imwrite(str(out / f.name), (img * (1 - m) + fill * m).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92])
print("plates:", len(frames))
