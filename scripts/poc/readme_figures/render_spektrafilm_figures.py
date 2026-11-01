"""External comparison for the figures of the root README: run spektrafilm 3bb2c2d2 (GPLv3, profiles CC BY-SA 4.0) on the selected photos.

Input: AP1 arrays of make_readme_figures.py decode, in build/tmp/readme_figures/input/. Output: build/tmp/readme_figures/spektrafilm/*.npy (sRGB code). Nothing is reused: the model of this lab does not read these arrays.
Settings: the default settings of spektrafilm, with no grain, because film grain is outside this lab. Photos use its own automatic exposure.
Run it in the environment of build/tmp/baseline/venv_spektra.
"""
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "build/tmp/baseline/src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate  # noqa: E402

BASE = ROOT / "build/tmp/readme_figures"
OUT = BASE / "spektrafilm"
OUT.mkdir(parents=True, exist_ok=True)
PAIRS = {"5207": ("kodak_vision3_250d", "kodak_2383"), "portra": ("kodak_portra_400", "kodak_endura_premier")}


def run(image: np.ndarray, film: str, paper: str, auto_exposure: bool) -> np.ndarray:
    params = init_params(film, paper)
    params.io.input_color_space = "ACEScg"
    params.io.input_cctf_decoding = False
    params.io.output_color_space = "sRGB"
    params.io.output_cctf_encoding = True
    params.film_render.grain.active = False
    params.camera.auto_exposure = auto_exposure
    return np.clip(simulate(image.astype(np.float64), params), 0.0, 1.0).astype(np.float32)


for key, (film, paper) in PAIRS.items():
    for path in sorted((BASE / "input").glob("*.npy")):
        out = OUT / f"{path.stem}_{key}.npy"
        if out.exists():
            continue
        t = time.perf_counter()
        np.save(out, run(np.load(path), film, paper, True))
        print(out.name, round(time.perf_counter() - t, 1), "s", flush=True)
