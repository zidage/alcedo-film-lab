"""A neutral ramp through spektrafilm with its Vision3 and 2383 profiles (external comparison): no auto exposure, no spatial effects."""
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
sys.path.insert(0, str(BASE / "src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate  # noqa: E402

grey = np.logspace(-3, 1, 41)
image = np.repeat(np.repeat(grey[None, :, None], 3, axis=2), 8, axis=0)
out = {"input": grey.tolist()}
for stock, profile in {"5207": "kodak_vision3_250d", "5219": "kodak_vision3_500t"}.items():
    p = init_params(profile, "kodak_2383")
    p.io.input_color_space = "ACEScg"
    p.camera.auto_exposure = False
    p.film_render.grain.active = False
    p.film_render.halation.active = False
    out[stock] = np.clip(simulate(image, p), 0, 1)[4].tolist()
(BASE / "grey_spektrafilm_cine.json").write_text(json.dumps(out), encoding="utf-8")
print("ok")
