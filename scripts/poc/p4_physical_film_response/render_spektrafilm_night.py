"""Comparison run of spektrafilm at 3bb2c2d2 (external, GPLv3, ROADMAP U18; nothing is reused) on the night files, with its Vision3 500T and 2383 profiles.

Input: build/tmp/p4/input_night/<name>.npy (linear AP1, as decoded) and <name>_graded.npy (the same after product_input()), from render_night_review.py --inputs-only. Never committed.
Output (local only): build/tmp/baseline/out_spektrafilm_night/<name>_ungraded.png and <name>_graded.png. Default settings, its own automatic exposure, no grain.
Step: P4, ROADMAP section 8. Run it with the Python environment of the baseline (build/tmp/baseline/venv_spektra).
"""

import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "build" / "tmp" / "baseline"
INPUT = REPO_ROOT / "build" / "tmp" / "p4" / "input_night"
OUT = BASE / "out_spektrafilm_night"
sys.path.insert(0, str(BASE / "src_spektrafilm" / "repo" / "src"))
from spektrafilm import init_params, simulate  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

OUT.mkdir(exist_ok=True)
sources = sorted(INPUT.glob("*.npy"))
if not sources:
    raise FileNotFoundError(f"no input in {INPUT}")
for source in sources:
    variant = "graded" if source.stem.endswith("_graded") else "ungraded"
    name = source.stem.removesuffix("_graded")
    params = init_params("kodak_vision3_500t", "kodak_2383")
    params.io.input_color_space = "ACEScg"
    params.io.input_cctf_decoding = False
    params.io.output_color_space = "sRGB"
    params.io.output_cctf_encoding = True
    params.film_render.grain.active = False
    start = time.time()
    srgb = np.clip(simulate(np.load(source).astype(np.float64), params), 0, 1)
    mpimg.imsave(OUT / f"{name}_{variant}.png", srgb.astype(np.float32))
    print(name, variant, srgb.shape, f"{time.time() - start:.1f} s", flush=True)
