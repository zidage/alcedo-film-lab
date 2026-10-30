"""Comparison run of spektrafilm with its Vision3 and 2383 profiles (external, GPLv3; nothing is reused). No grain, default settings."""
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
sys.path.insert(0, str(BASE / "src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
names = sys.argv[1:]
for stock, profile in {"5207": "kodak_vision3_250d", "5219": "kodak_vision3_500t"}.items():
    out = BASE / f"out_spektrafilm_{stock}"
    out.mkdir(exist_ok=True)
    for name in names:
        p = init_params(profile, "kodak_2383")
        p.io.input_color_space = "ACEScg"
        p.film_render.grain.active = False
        srgb = np.clip(simulate(np.load(BASE / f"input/{name}.npy").astype(np.float64), p), 0, 1)
        mpimg.imsave(out / f"{name}.png", srgb.astype(np.float32))
        print(stock, name, flush=True)
