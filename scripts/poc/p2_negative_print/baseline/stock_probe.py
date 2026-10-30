"""Portra 400 + Endura, 5207 + 2383, 5219 + 2383 with the darkroom options, against the baselines.
Output (local): build/tmp/baseline/stocks/<name>_overview.png (Portra | 5207 | 5219), <name>_<stock>.png (ours | spektrafilm | Fotufilm)."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
OUT = BASE / "stocks"
OUT.mkdir(exist_ok=True)
FILES = sys.argv[1:]
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


def load(path, size):
    return np.asarray(Image.open(path).convert("RGB").resize(size, Image.LANCZOS), dtype=np.float64) / 255


def save(panels, path):
    gap = np.ones((panels[0].shape[0], 8, 3))
    row = []
    for panel in panels:
        row += [panel, gap]
    Image.fromarray((np.concatenate(row[:-1], axis=1) * 255).astype(np.uint8)).save(path)


previews = {k: fp.FilmPreview(fp.FilmOptions(**fp.STOCKS[v], **fp.DARKROOM)) for k, v in {"portra": "portra400_endura", "5207": "5207_2383", "5219": "5219_2383"}.items()}
for k, p in previews.items():
    grey = p.render(np.outer(np.logspace(-3, 1, 41), np.ones(3))[None])[0][0]
    print(k, "grey sRGB at 0.18:", grey[np.argmin(np.abs(np.logspace(-3, 1, 41) - 0.18))].round(3).tolist(), "table counts", p.table_counts, flush=True)
for n in FILES:
    ap1 = np.load(BASE / f"input/{n}.npy").astype(np.float64)
    images = {}
    size = (ap1.shape[1], ap1.shape[0])
    for k, p in previews.items():
        images[k], st = p.render(ap1 * fp.center_weighted_exposure(ap1, p.c))
        images[k] = np.clip(images[k], 0, 1)
        a = lab(images[k])
        print(n, k, "L5/50/95", np.percentile(a[:, 0], [5, 50, 95]).round(0).tolist(), "C50/95", np.percentile(np.hypot(a[:, 1], a[:, 2]), [50, 95]).round(0).tolist(), "outside 709 %", round(100 * st["display_clipped"] / st["pixels"], 1), "after compression %", round(100 * st["display_clipped_after_compression"] / st["pixels"], 2), "distance p99.9", st["gamut_distance_p999"], flush=True)
    save(list(images.values()), OUT / f"{n}_overview.png")
    for stock in ("5207", "5219"):
        ref = load(BASE / f"out_spektrafilm_{stock}/{n}.png", size)
        ff = load(BASE / f"out_fotufilm/{n}__{stock}.png", size)
        save([images[stock], ref, ff], OUT / f"{n}_{stock}.png")
        de = np.linalg.norm(lab(images[stock]) - lab(ref), axis=1)
        print(n, stock, "dE against spektrafilm p50/p95", np.percentile(de, [50, 95]).round(1).tolist(), flush=True)
