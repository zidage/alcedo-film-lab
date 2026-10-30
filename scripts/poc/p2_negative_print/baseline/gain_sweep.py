"""Local: this lab's preview with rule center_weighted_exposure against spektrafilm, for several interlayer gains."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp
BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); WHITE = np.array([0.9505, 1.0, 1.089])
def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)
index = {k: v for k, v in json.loads((BASE / "input/index.json").read_text(encoding="utf-8")).items() if not v.get("portrait")}  # portraits stay held out
def load(d, n): return np.asarray(Image.open(BASE / d / f"{n}.png").convert("RGB"), dtype=np.float64) / 255
for n in index:
    a, b = lab(load("out_spektrafilm", n)), lab(load("out_spektrafilm_nocouplers", n)); m = (a[:, 0] > 20) & (a[:, 0] < 80)
    print("spektra no couplers / default chroma", n[:24].ljust(25), round(float(np.hypot(*b[m, 1:].T).mean() / np.hypot(*a[m, 1:].T).mean()), 2))
for gain in (0.1, 0.15, 0.2, 0.25, 0.3):
    p = fp.FilmPreview(fp.FilmOptions(interlayer_gain=gain))
    des, ratios, dls = [], [], []
    for n in index:
        ap1 = np.load(BASE / f"input/{n}.npy").astype(np.float64)
        ev = fp.center_weighted_exposure(ap1, p.c)
        ours = lab(np.clip(p.render(ap1 * ev)[0], 0, 1)); ref = lab(load("out_spektrafilm", n)); m = (ref[:, 0] > 20) & (ref[:, 0] < 80)
        des.append(np.linalg.norm(ours - ref, axis=1)); ratios.append(np.hypot(*ours[m, 1:].T).mean() / np.hypot(*ref[m, 1:].T).mean()); dls.append(np.median(ours[:, 0]) - np.median(ref[:, 0]))
    print("gain", gain, "dE p50/p95", np.percentile(np.concatenate(des), [50, 95]).round(1).tolist(), "chroma ratios", np.round(ratios, 2).tolist(), "median", round(float(np.median(ratios)), 2), "dL50 max", round(float(np.abs(dls).max()), 1), flush=True)
