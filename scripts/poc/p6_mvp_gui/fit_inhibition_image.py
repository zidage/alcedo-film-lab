"""Rule 'inhibition_image_part': the spread and the image part of the inhibition, from the modulation transfer curves at the inhibitor length of the render.

Input: profiles/<negative>.json, stock_physics.json, the accepted values in film_preview.py. Output: inhibition_image.json next to this script, and a table on stdout. Step: P7, ROADMAP U74.
The form is that of fit_mtf.py, with sigma_d fixed at the option inhibition_um. The fits of P4, P5, and P6 have sigma_d free and discard it. On a chart with no rise above 1 they stop at B = 2 with a sigma_d under 7 um, and a render at 35 um then has a rise that the chart does not have.
This script keeps the K of those fits as the total, because K also sets the colour of a flat area and the user accepted those colours (U72). The image part gives this B on the curve F_i of the total. F_i has the slope gamma / (1 - K gamma), and with the point part at the pixel the response at a high frequency grows by the factor 1 + K_image gamma / (1 - K gamma). So K_image = min((B - 1) (1 - K gamma) / gamma, K). With K = (B - 1) / (B gamma), this is the K of those fits. B at its upper bound is an error.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parents[0] / "p4_physical_film_response"))
import mvp_pipeline as mp  # noqa: E402
from fit_mtf import response  # noqa: E402

fp = mp.fp
SPREAD_BOUNDS = (0.5, 15.0)
BOOST_BOUNDS = (1.0, 2.0)


def fit_layer(x: np.ndarray, y: np.ndarray, sigma_um: float) -> tuple[float, float, float]:
    fit = least_squares(lambda p: response(x, p[0], sigma_um, p[1]) - y, (4.0, 1.2), bounds=((SPREAD_BOUNDS[0], BOOST_BOUNDS[0]), (SPREAD_BOUNDS[1], BOOST_BOUNDS[1])))
    return float(fit.x[0]), float(fit.x[1]), float(np.sqrt(np.mean(fit.fun**2)))


def main() -> int:
    result = {}
    for negative in mp.CATALOG["negatives"]:
        if mp.load_physics().get(negative, {}).get("error"):
            continue
        chart = fp.p0.load_profile(negative)["charts"].get("modulation_transfer")
        if not chart:
            continue
        options = mp.film_options(mp.RenderSettings(negative=negative), image_part=False)
        if not any(options.inhibition_total):
            continue
        model = fp.FilmPreview(options)
        middle = model.film.options.midscale_log_h
        names = ("red", "green", "blue") if "red" in chart["curves"] else ("all_layers",) * 3
        spread, image, boosts, residual = [], [], [], 0.0
        for k, name in enumerate(names):
            x, y = np.array(chart["curves"][name]["x"]), np.array(chart["curves"][name]["y"])
            s, boost, rms = fit_layer(x, y, options.inhibition_um)
            if boost >= BOOST_BOUNDS[1] - 1e-3:
                raise ValueError(f"{negative}, {name}: B is at its upper bound {BOOST_BOUNDS[1]}, so the fit at {options.inhibition_um} um failed")
            curve = model.negative_curves[k]
            gamma = float(np.interp(middle + 0.5, curve.log_h, curve.density) - np.interp(middle - 0.5, curve.log_h, curve.density))
            spread.append(round(s, 2))
            total = float(options.inhibition_total[k])
            image.append(round(max(min((boost - 1.0) * (1.0 - total * gamma) / gamma, total), 0.0), 4))
            boosts.append(round(boost, 4))
            residual = max(residual, rms)
        result[negative] = dict(layer_spread_um=spread, inhibition_image=image, boost=boosts, largest_rms_residual=round(residual, 4))
        print(f"{negative:24s} K {[round(v, 3) for v in options.inhibition_total]} image {image} spread {spread} B {boosts} residual {residual:.4f}", flush=True)
    mp.IMAGE_PART_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
