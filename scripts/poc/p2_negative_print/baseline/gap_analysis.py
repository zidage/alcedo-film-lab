"""Local: (1) quantify the remaining gap after exposure matching; (2) test independent exposure rules against the matched EV."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp
import render_review_images as rr

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
stats = json.loads((BASE / "match/stats.json").read_text(encoding="utf-8"))
index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
c = fp.FilmPreview(fp.FilmOptions()).c
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(srgb):
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(linear.reshape(-1, 3) @ M.T, WHITE)


qs = [1, 5, 25, 50, 75, 90, 95, 99, 99.9]
print("L* quantiles", qs)
de_all, rows = [], {}
for name in index:
    im = np.asarray(Image.open(BASE / f"match/{name}.png").convert("RGB"), dtype=np.float64) / 255
    w = (im.shape[1] - 8) // 2
    a, b = lab(im[:, :w]), lab(im[:, w + 8:2 * w + 8])  # spektrafilm, ours matched
    de = np.linalg.norm(a - b, axis=1)
    neutral = np.hypot(a[:, 1], a[:, 2]) < 12
    mids = (a[:, 0] > 20) & (a[:, 0] < 80)
    print(name[:26].ljust(27), "S", np.percentile(a[:, 0], qs).round(0).tolist(), "\n", " " * 26, "O", np.percentile(b[:, 0], qs).round(0).tolist(),
          "dE p50/p95", np.percentile(de, [50, 95]).round(1).tolist(),
          "mid da,db", (b[mids, 1:] - a[mids, 1:]).mean(axis=0).round(1).tolist(), "chroma ratio(mids)", round(float(np.hypot(*b[mids, 1:].T).mean() / np.hypot(*a[mids, 1:].T).mean()), 2))
    de_all.append(de)
print("all dE p50/p95", np.percentile(np.concatenate(de_all), [50, 95]).round(1).tolist())

# independent exposure rules: each returns log2 of a statistic of Y; the rule's offset is fitted on these images, leave one out
def rules(y):
    h, w = y.shape
    yy, xx = np.mgrid[0:h, 0:w]
    g = np.exp(-(((xx - w / 2) / (0.35 * w)) ** 2 + ((yy - h / 2) / (0.35 * h)) ** 2) / 2)
    logy = np.log2(np.clip(y, 2 ** -14, None))
    lo, hi = np.percentile(logy, [1, 99])
    keep = (logy >= lo) & (logy <= hi)
    return {"log_average": logy[keep].mean(), "center_log_average": (logy * g)[keep].sum() / g[keep].sum(), "median": np.median(logy),
            "p75": np.percentile(logy, 75), "p90": np.percentile(logy, 90), "mean_linear": np.log2(np.mean(y)), "center_mean_linear": np.log2((y * g).sum() / g.sum())}


table = {}
target = {}
for name in index:
    y = np.load(BASE / f"input/{name}.npy").astype(np.float64) @ c.ap1_to_xyz[1]
    table[name] = rules(y)
    target[name] = stats[name]["matched_ev_vs_sensor"]
names = list(index)
t = np.array([target[n] for n in names])
for rule in next(iter(table.values())):
    s = np.array([table[n][rule] for n in names])
    k = t + s  # EV = k - statistic
    residual = [k[i] - np.delete(k, i).mean() for i in range(len(names))]
    print(rule.ljust(20), "k", round(k.mean(), 2), "LOO rms", round(float(np.sqrt(np.mean(np.square(residual)))), 2), "max", round(float(np.abs(residual).max()), 2))
