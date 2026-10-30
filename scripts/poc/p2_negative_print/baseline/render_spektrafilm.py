"""Local baseline run of spektrafilm at 3bb2c2d2 (GPLv3): an external comparison only, nothing is reused.
Portra 400 and Endura Premier, default settings except no grain (film grain is outside this lab)."""
import json
import sys
import time
from pathlib import Path

import numpy as np

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
sys.path.insert(0, str(BASE / "src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

OUT = BASE / "out_spektrafilm"
OUT.mkdir(exist_ok=True)
index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
names = sys.argv[1:] or list(index)
for name in names:
    ap1 = np.load(BASE / f"input/{name}.npy").astype(np.float64)
    params = init_params("kodak_portra_400", "kodak_endura_premier")
    params.io.input_color_space = "ACEScg"
    params.io.input_cctf_decoding = False
    params.io.output_color_space = "sRGB"
    params.io.output_cctf_encoding = True
    params.film_render.grain.active = False
    t = time.time()
    # exposure: spektrafilm's own default (auto_exposure, center_weighted), on the unscaled sensor data
    srgb = np.clip(simulate(ap1, params), 0, 1)
    mpimg.imsave(OUT / f"{name}.png", srgb.astype(np.float32))
    print(name, srgb.shape, f"{time.time() - t:.1f} s", "mean", srgb.mean().round(3), flush=True)
