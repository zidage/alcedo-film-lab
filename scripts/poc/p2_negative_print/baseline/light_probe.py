"""5219 and 5207 under different scene lights (rule 'relight'). Local images in build/tmp/baseline/lights/.
Each image: one panel per entry of RUNS. Printed: where a grey lands on the curves, and the colour of a neutral ramp."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
OUT = BASE / "lights"
OUT.mkdir(exist_ok=True)
FILES = ["se002.cr2", "se086.cr2", "se163.cr2", "se019.arw", "nikon_zf_DSC_1535.NEF", "se127.dng"]
RUNS = {"5219": [("T3200", 1.0), ("D55", 1.0), ("D55", 0.75), ("FL2", 1.0), ("FL11", 1.0), ("FL11", 0.75), ("LED-B3", 1.0), ("LED-RGB1", 1.0)],
        "5207": [("D55", 1.0), ("T3200", 1.0), ("FL11", 1.0)]}
STOCK = {"5219": "5219_2383", "5207": "5207_2383"}
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


previews = {}
grey = np.array([0.01, 0.045, 0.18, 0.72, 2.9])
for stock, runs in RUNS.items():
    for light, timing in runs:
        p = fp.FilmPreview(fp.FilmOptions(**fp.STOCKS[STOCK[stock]], **fp.DARKROOM, scene_light=light, print_timing=timing))
        previews[stock, light, timing] = p
        ramp = lab(np.clip(p.render(np.outer(grey, np.ones(3))[None])[0][0], 0, 1))
        print(stock, light, timing, "grey on curves (stops R G B)", p.scene_grey_stops.round(2).tolist(), "ramp a,b", ramp[:, 1:].round(1).tolist(), "L", ramp[:, 0].round(0).tolist(), flush=True)
for n in FILES:
    ap1 = np.load(BASE / f"input/{n}.npy").astype(np.float64)
    for stock, runs in RUNS.items():
        gap = np.ones((ap1.shape[0], 8, 3))
        row = []
        for light, timing in runs:
            p = previews[stock, light, timing]
            image, st = p.render(ap1 * fp.center_weighted_exposure(ap1, p.c))
            a = lab(np.clip(image, 0, 1))
            print(n, stock, light, timing, "L5/50/95", np.percentile(a[:, 0], [5, 50, 95]).round(0).tolist(), "C50/95", np.percentile(np.hypot(a[:, 1], a[:, 2]), [50, 95]).round(0).tolist(),
                  "above curve", st["negative_above_curve_end"], "after compression", st["display_clipped_after_compression"], flush=True)
            row += [np.clip(image, 0, 1), gap]
        Image.fromarray((np.concatenate(row[:-1], axis=1) * 255).astype(np.uint8)).save(OUT / f"{n}_{stock}.png")
