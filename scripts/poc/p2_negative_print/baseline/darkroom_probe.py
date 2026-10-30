"""Darkroom controls on portraits. Panels: spektrafilm | current options | each entry of SETS.
Output: build/tmp/baseline/darkroom/ (local), and chroma and L* statistics against spektrafilm."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
OUT = BASE / "darkroom"
OUT.mkdir(exist_ok=True)
FILES = ["se002.cr2", "se086.cr2", "se163.cr2", "se019.arw", "se231.nef", "se127.dng", "nikon_zf_DSC_1535.NEF", "fuji_xt5_DSCF1787.RAF"]
SPATIAL = dict(scatter_um=10.0, halation=(0.03, 0.008, 0.0), adjacency_gain=0.25, enlarger_flare=0.01)
SETS = {"current": fp.FilmOptions(),
        "print": fp.FilmOptions(interlayer_gain=0.1, print_flash=0.02, print_contrast=0.92, viewing_flare=0.003, **SPATIAL),
        "soft": fp.FilmOptions(interlayer_gain=0.05, print_flash=0.04, print_contrast=0.85, viewing_flare=0.005, **SPATIAL)}
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


previews = {k: fp.FilmPreview(o) for k, o in SETS.items()}
for n in FILES:
    ap1 = np.load(BASE / f"input/{n}.npy").astype(np.float64)
    ref = np.asarray(Image.open(BASE / f"out_spektrafilm/{n}.png").convert("RGB"), dtype=np.float64) / 255
    gap = np.ones((ref.shape[0], 8, 3))
    row = [ref]
    b = lab(ref)
    m = (b[:, 0] > 20) & (b[:, 0] < 80)
    report = {}
    for k, p in previews.items():
        image = np.clip(p.render(ap1 * fp.center_weighted_exposure(ap1, p.c))[0], 0, 1)
        row += [gap, image]
        a = lab(image)
        report[k] = {"C": round(float(np.hypot(*a[m, 1:].T).mean() / np.hypot(*b[m, 1:].T).mean()), 2), "L": np.percentile(a[:, 0], [5, 50, 95]).round(0).tolist()}
    Image.fromarray((np.concatenate(row, axis=1) * 255).astype(np.uint8)).save(OUT / f"{n}.png")
    print(n, "ref L", np.percentile(b[:, 0], [5, 50, 95]).round(0).tolist(), report, flush=True)
