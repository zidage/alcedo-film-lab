"""Check of the cine stocks: where does an 18 % grey land on the negative curves, and what does the chain print?
Compares with the exposure 12.5 / ISO lux seconds of the stock (spectral_film_lut definition) and, when
build/tmp/baseline/grey_spektrafilm_cine.json exists, with the same ramp through spektrafilm (external comparison)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])
ramp_path = BASE / "grey_spektrafilm_cine.json"
reference = json.loads(ramp_path.read_text(encoding="utf-8")) if ramp_path.exists() else None


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


grey = np.logspace(-3, 1, 41)
for stock in ("5207_2383", "5219_2383"):
    p = fp.FilmPreview(fp.FilmOptions(**fp.STOCKS[stock], **fp.DARKROOM))
    f = p.film
    q = p.layer_exposure(np.full((1, 3), 0.18))[0][0]
    log_h = f.negative_criterion_log_h + np.log10(q)
    target = f.options.midscale_log_h
    print(stock, "layer gain", p.layer_gain.round(3).tolist(), "criterion log H", f.negative_criterion_log_h.round(3).tolist())
    print("  grey log H on the curves", log_h.round(3).tolist(), "stated", round(target, 3), "error (stops)", ((log_h - target) / np.log10(2)).round(2).tolist())
    print("  grey Status M", p.negative_density(q[None])[0][0].round(3).tolist(), "at stated exposure", [round(float(np.interp(target, c.log_h, c.density)), 3) for c in p.negative_curves])
    ours = lab(np.clip(p.render(np.outer(grey, np.ones(3))[None])[0][0], 0, 1))
    other = lab(np.array(reference[stock[:4]])) if reference else None
    for i in range(10, 41, 5):
        print(f"  {grey[i]:7.3f} ours", ours[i].round(1).tolist(), "spektrafilm", other[i].round(1).tolist() if other is not None else None)
