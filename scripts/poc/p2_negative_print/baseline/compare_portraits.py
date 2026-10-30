"""Local: portraits, held out from the choice of exposure rule and interlayer gain.
Panels: ours | spektrafilm (Endura Premier) | Fotufilm default (Auto Levels)."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp
BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline"); OUT = BASE / "compare_portraits"; OUT.mkdir(exist_ok=True)
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); WHITE = np.array([0.9505, 1.0, 1.089])
def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)
index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
p = fp.FilmPreview(fp.FilmOptions())
rows, des = {}, []
for n, e in index.items():
    if not e.get("portrait"): continue
    ap1 = np.load(BASE / f"input/{n}.npy").astype(np.float64)
    ours, st = p.render(ap1 * fp.center_weighted_exposure(ap1, p.c))
    ours = np.clip(ours, 0, 1)
    ref = np.asarray(Image.open(BASE / f"out_spektrafilm/{n}.png").convert("RGB"), dtype=np.float64) / 255
    size = (ref.shape[1], ref.shape[0])
    ff = np.asarray(Image.open(BASE / f"out_fotufilm/{n}__auto.png").convert("RGB").resize(size, Image.LANCZOS), dtype=np.float64) / 255
    a, b = lab(ours), lab(ref); m = (b[:, 0] > 20) & (b[:, 0] < 80); de = np.linalg.norm(a - b, axis=1); des.append(de)
    rows[n] = {"dL50": round(float(np.median(a[:, 0]) - np.median(b[:, 0])), 1), "L95": [round(float(np.percentile(a[:, 0], 95)), 1), round(float(np.percentile(b[:, 0], 95)), 1)],
               "chroma_ratio": round(float(np.hypot(*a[m, 1:].T).mean() / np.hypot(*b[m, 1:].T).mean()), 2), "da_db": (a[m, 1:] - b[m, 1:]).mean(axis=0).round(1).tolist(),
               "dE_p50_p95": np.percentile(de, [50, 95]).round(1).tolist(), "clipped_pct": round(100 * st["display_clipped"] / st["pixels"], 2)}
    print(n, rows[n], flush=True)
    gap = np.ones((ref.shape[0], 8, 3))
    Image.fromarray((np.concatenate([ours, gap, ref, gap, ff], axis=1) * 255).astype(np.uint8)).save(OUT / f"{n}.png")
print("all dE p50/p95", np.percentile(np.concatenate(des), [50, 95]).round(1).tolist(), "median chroma ratio", np.median([r["chroma_ratio"] for r in rows.values()]), "|dL50| max", max(abs(r["dL50"]) for r in rows.values()))
(OUT / "stats.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
