"""Where does the colour of the neutral ramp of the cine stocks start? Prints each stage per layer. Input: the ramp of
spektrafilm in build/tmp/baseline/grey_spektrafilm_cine.json (external comparison, optional). Output: the console."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])
path = BASE / "grey_spektrafilm_cine.json"
reference = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def lab(s):
    l = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(l.reshape(-1, 3) @ M.T, WHITE)


grey = np.logspace(-3, 1, 41)
ap1 = np.outer(grey, np.ones(3))
for stock, light in (("5207_2383", "D55"), ("5219_2383", "T3200")):
    for name, extra in (("balance light", dict(scene_light=light)), ("E_ref", {})):
        p = fp.FilmPreview(fp.FilmOptions(**fp.STOCKS[stock], **fp.DARKROOM, **extra))
        f = p.film
        q = p.layer_exposure(ap1)[0]
        d = p.negative_density(q)[0]
        base = f.status_density(f.negative_dmin, f.w_status_m)
        amounts, _ = fp.solve_amounts(d - f.negative_curve_dmin + base, f.negative_dmin, f.negative_dyes, f.w_status_m)
        log_h = f.paper_log_exposure(f.negative_spectral_density(amounts))
        log_h = np.array([c.log_h_at(f.options.print_midscale_status_a) for c in f.paper_curves.values()]) + p.printing_gain * (log_h - np.array([c.log_h_at(f.options.print_midscale_status_a) for c in f.paper_curves.values()]))
        aim = np.array([c.log_h_at(f.options.print_midscale_status_a) for c in f.paper_curves.values()])
        status = np.stack([np.interp(log_h[:, k], c.log_h, c.density) for k, c in enumerate(f.paper_curves.values())], axis=1)
        ours = lab(np.clip(p.render(ap1[None])[0][0], 0, 1))
        other = lab(np.array(reference[stock[:4]])) if reference else None
        white = lab(fp.srgb_encode(p.display_linear(p.paper_white[None])))[0]
        print(f"\n{stock} {name}: printing gain {p.printing_gain.round(3).tolist()}; paper Lab {white.round(1).tolist()}; paper Dmin Status A {[round(float(c.density.min()), 3) for c in f.paper_curves.values()]}; curve log H range of the negative {[(round(float(c.log_h[0]), 2), round(float(c.log_h[-1]), 2)) for c in p.negative_curves]}")
        print("  scene  | neg M - grey            | paper logH - aim        | Status A                | ours Lab             | spektrafilm Lab")
        i18 = int(np.argmin(np.abs(grey - 0.18)))
        for i in range(10, 41, 4):
            print(f"  {grey[i]:6.3f} | {np.round(d[i] - d[i18], 2).tolist()!s:23} | {np.round(log_h[i] - aim, 2).tolist()!s:23} | {status[i].round(2).tolist()!s:23} | {ours[i].round(1).tolist()!s:20} | {other[i].round(1).tolist() if other is not None else None}")
