"""Local: a neutral ramp through spektrafilm (ACEScg input at the ACES white, no auto exposure, no spatial effects), saved for comparison."""
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
sys.path.insert(0, str(BASE / "src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate  # noqa: E402

grey = np.logspace(-4, 1.3, 54)
image = np.repeat(grey[None, :, None], 3, axis=2)
image = np.repeat(image, 8, axis=0)
out = {}
for label, patch in {"defaults": {}, "no_glare_no_couplers": {"glare": False, "couplers": False}}.items():
    params = init_params("kodak_portra_400", "kodak_endura_premier")
    params.io.input_color_space = "ACEScg"
    params.camera.auto_exposure = False
    params.film_render.grain.active = False
    params.film_render.halation.active = False
    if patch.get("glare") is False:
        params.film_render.glare.active = False
        params.print_render.glare.active = False
    if patch.get("couplers") is False:
        params.film_render.dir_couplers.active = False
    srgb = np.clip(simulate(image, params), 0, 1)[4]
    out[label] = srgb.tolist()
out["input"] = grey.tolist()
(BASE / "grey_spektrafilm.json").write_text(json.dumps(out), encoding="utf-8")
print("ok")
