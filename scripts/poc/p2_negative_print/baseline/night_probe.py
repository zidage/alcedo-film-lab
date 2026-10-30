"""User night photos through 5219 + 2383 with each product light (U21). Local images: build/tmp/baseline/night/<name>_grid.png.
Grid, row 1: plain encoding | daylight | fluorescent; row 2: LED | sodium | tungsten. The same exposure in all panels."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

SOURCE = Path(sys.argv[1])
OUT = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline/night")
FILES = sys.argv[2:]
PANELS = ["daylight", "fluorescent", "led", "sodium", "tungsten"]
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


previews = {k: fp.FilmPreview(fp.FilmOptions(**fp.STOCKS["5219_2383"], **fp.DARKROOM, scene_light=fp.PRODUCT_LIGHTS[k], print_timing=1.0 if k == "tungsten" else 0.75)) for k in PANELS}
for k, p in previews.items():
    print(k, fp.PRODUCT_LIGHTS[k], "grey on curves (stops)", p.scene_grey_stops.round(2).tolist(), flush=True)
c = previews["daylight"].c
for n in FILES:
    ap1, rec709 = fp.decode_raw_ap1(SOURCE / f"{n}.ARW", 1000, c)
    scale = fp.center_weighted_exposure(ap1, c)
    np.save(OUT / f"{n}_ap1.npy", ap1.astype(np.float32))
    y = ap1 @ c.ap1_to_xyz[1] * scale
    print(n, "exposure stops", round(float(np.log2(scale)), 2), "Y p50/p99", np.percentile(y, [50, 99]).round(3).tolist(), flush=True)
    images = [fp.srgb_encode(rec709 * scale)]
    graded = fp.product_input(ap1, c)
    for k, p in previews.items():
        image, st = p.render(graded)
        images.append(np.clip(image, 0, 1))
        a = lab(images[-1])
        print(" ", k, "L5/50/95", np.percentile(a[:, 0], [5, 50, 95]).round(0).tolist(), "C50/95", np.percentile(np.hypot(a[:, 1], a[:, 2]), [50, 95]).round(0).tolist(),
              "above curve", st["negative_above_curve_end"], "after compression %", round(100 * st["display_clipped_after_compression"] / st["pixels"], 2), flush=True)
    gap_v = np.ones((images[0].shape[0], 8, 3))
    top = np.concatenate([images[0], gap_v, images[1], gap_v, images[2]], axis=1)
    bottom = np.concatenate([images[3], gap_v, images[4], gap_v, images[5]], axis=1)
    grid = np.concatenate([top, np.ones((8, top.shape[1], 3)), bottom], axis=0)
    Image.fromarray((grid * 255).astype(np.uint8)).save(OUT / f"{n}_grid.png")
