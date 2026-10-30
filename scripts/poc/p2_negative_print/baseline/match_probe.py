"""Local diagnostic: published curves (no softening), exposure solved per image so that the median L* equals spektrafilm's.
This shows what remains after the exposure difference. Panels: spektrafilm | ours at matched exposure | ours set b at review rule."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
sys.path.insert(0, "D:/Projects/alcedo-film-lab/build/tmp/baseline/scripts")
import film_preview as fp
import render_review_images as rr

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
OUT = BASE / "match"
OUT.mkdir(exist_ok=True)
index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
published = fp.FilmPreview(fp.FilmOptions())
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(srgb):
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(linear.reshape(-1, 3) @ M.T, WHITE)


def summary(srgb):
    v = lab(srgb)
    c = np.hypot(v[:, 1], v[:, 2])
    return [round(float(x), 1) for x in (np.percentile(v[:, 0], 5), np.median(v[:, 0]), np.percentile(v[:, 0], 95), np.median(c), np.percentile(c, 95))]


out = {}
for name, entry in index.items():
    ap1 = np.load(BASE / f"input/{name}.npy").astype(np.float64)
    ref = np.asarray(Image.open(BASE / f"out_spektrafilm/{name}.png").convert("RGB"), dtype=np.float64) / 255
    target = float(np.median(lab(ref)[:, 0]))
    small = ap1[::8, ::8]
    lo, hi = -8.0, 8.0
    for _ in range(9):
        mid = (lo + hi) / 2
        got = float(np.median(lab(np.clip(published.render(small * 2 ** mid)[0], 0, 1))[:, 0]))
        lo, hi = (mid, hi) if got < target else (lo, mid)
    ev = (lo + hi) / 2
    matched = np.clip(published.render(ap1 * 2 ** ev)[0], 0, 1)
    gap = np.ones((ref.shape[0], 8, 3))
    Image.fromarray((np.concatenate([ref, gap, matched], axis=1) * 255).astype(np.uint8)).save(OUT / f"{name}.png")
    out[name] = {"matched_ev_vs_sensor": round(ev, 2), "review_rule_ev": round(float(np.log2(entry["review_scale"])), 2), "spektrafilm": summary(ref), "matched": summary(matched)}
    print(name, out[name], flush=True)
(OUT / "stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
