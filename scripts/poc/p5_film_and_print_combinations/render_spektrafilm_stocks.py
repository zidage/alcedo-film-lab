"""Comparison run of spektrafilm at 3bb2c2d2 (external, GPLv3, ROADMAP U18; nothing is reused) on the graded input, with its profiles of the six stocks and its Portra Endura paper.

Input: build/tmp/p5/input_compare/<name>.npy, linear AP1 after product_input(), from compare_spektrafilm_sheets.py --inputs-only. Never committed.
Output (local only): build/tmp/p5/out_spektrafilm/<name>_<stock>.png. Default settings, its own automatic exposure, no grain.
Step: P5, ROADMAP section 8. Run it with the Python environment of the baseline (build/tmp/baseline/venv_spektra).
"""

import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "build" / "tmp" / "baseline"
INPUT = REPO_ROOT / "build" / "tmp" / "p5" / "input_compare"
OUT = REPO_ROOT / "build" / "tmp" / "p5" / "out_spektrafilm"
STOCKS = ("kodak_portra_400", "kodak_portra_160", "kodak_portra_800", "kodak_ektar_100", "kodak_gold_200", "fujifilm_c200")
sys.path.insert(0, str(BASE / "src_spektrafilm" / "repo" / "src"))
from spektrafilm import init_params, simulate  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
sources = sorted(INPUT.glob("*.npy"))
if not sources:
    raise FileNotFoundError(f"no input in {INPUT}")
for source in sources:
    image = np.load(source).astype(np.float64)
    for stock in STOCKS:
        target = OUT / f"{source.stem}_{stock}.png"
        if target.exists():
            continue
        params = init_params(stock, "kodak_portra_endura")
        params.io.input_color_space = "ACEScg"
        params.io.input_cctf_decoding = False
        params.io.output_color_space = "sRGB"
        params.io.output_cctf_encoding = True
        params.film_render.grain.active = False
        start = time.time()
        srgb = np.clip(simulate(image, params), 0, 1)
        mpimg.imsave(target, srgb.astype(np.float32))
        print(source.stem, stock, srgb.shape, f"{time.time() - start:.1f} s", flush=True)
