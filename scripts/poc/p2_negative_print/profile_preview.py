"""Time of each stage of film_preview.py on a synthetic image of about 1 MP, with no photo. Output: the console.

Step: P2, efficiency of the review renderer. The image is reproducible: smooth colour gradients plus noise."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_preview as fp  # noqa: E402


def image(h: int = 800, w: int = 1250) -> np.ndarray:
    rng = np.random.default_rng(20261030)
    yy, xx = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    base = np.stack([0.02 + 0.8 * xx, 0.02 + 0.6 * yy, 0.02 + 0.5 * (1 - xx) * yy], axis=-1)
    return base * np.exp(rng.normal(0.0, 0.25, base.shape))


def timed(name: str, function, *args, repeat: int = 1):
    best = np.inf
    for _ in range(repeat):
        start = time.perf_counter()
        out = function(*args)
        best = min(best, time.perf_counter() - start)
    print(f"{name:28s} {best * 1000:9.1f} ms", flush=True)
    return out


def main() -> None:
    print(f"cpu count {os.cpu_count()}; python {sys.version.split()[0]}; numpy {np.__version__}")
    start = time.perf_counter()
    preview = fp.FilmPreview(fp.FilmOptions(**fp.STOCKS["5219_2383"], **fp.DARKROOM, scene_light="T3200"))
    print(f"constructor (cached tables)  {(time.perf_counter() - start) * 1000:9.1f} ms", flush=True)
    ap1 = image()
    print("pixels", ap1.shape[0] * ap1.shape[1])
    timed("render, first call", preview.render, ap1)
    timed("render, kernels", preview.render, ap1, repeat=5)
    timed("render, array reference", preview.reference_render, ap1)


if __name__ == "__main__":
    main()
