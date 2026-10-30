"""Local: attribution only. spektrafilm with couplers off; statistics of chroma against the default run."""
import json, sys
from pathlib import Path
import numpy as np
BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
sys.path.insert(0, str(BASE / "src_spektrafilm/repo/src"))
from spektrafilm import init_params, simulate
import matplotlib.image as mpimg
OUT = BASE / "out_spektrafilm_nocouplers"; OUT.mkdir(exist_ok=True)
for name in json.loads((BASE / "input/index.json").read_text(encoding="utf-8")):
    p = init_params("kodak_portra_400", "kodak_endura_premier")
    p.io.input_color_space = "ACEScg"; p.film_render.grain.active = False; p.film_render.dir_couplers.active = False
    srgb = np.clip(simulate(np.load(BASE / f"input/{name}.npy").astype(np.float64), p), 0, 1)
    mpimg.imsave(OUT / f"{name}.png", srgb.astype(np.float32)); print(name, flush=True)
