"""Fit the grey placement, the optical spread, and the development inhibition of each reversal film from its own charts.

Input: profiles/<film>.json and reversal_catalog.json; the model form and the bounds of fit_mtf.py (P4). Output: reversal_physics.json next to this script, and a table on stdout. Step: P9, ROADMAP U86.

- Grey placement: an 18 % grey of D55 at the exposure 12.5 / ISO lux seconds, through the layer exposure with the level of the chart, in stops from the exposure of the grey on each curve. This is a record only:
  each film takes rule grey_anchor by rule 'daylight_reversal_balance' (reversal_film.py). grey_status_a is the Status A of the slide at the exposure of the grey, the neutral of the published curves.
- Spread and inhibition, the rules of steps P4 to P7 on the record of rule 'removed_dye_record': a free fit of the spread, the inhibitor length, and the boost B gives the total K = (B - 1) / (B gamma), as fit_stock_physics.py;
  a fit with the inhibitor length fixed at the option inhibition_um gives the spread and the image part K_image = min((B - 1)(1 - K gamma) / gamma, K), as fit_inhibition_image.py; and rule 'inhibition_total_from_image_part' (ROADMAP U80)
  keeps K_image as the total. gamma is the slope of the removed dye per log10 H over 1 log10 H around the grey. One curve for all layers: the three layers use one fit, with their own gamma.
  A film with no modulation transfer chart has no spread and no inhibition, and a value of another film is not used.
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
import reversal_film as rf  # noqa: E402
from fit_mtf import BOUNDS, response  # noqa: E402

SPREAD_BOUNDS = (0.5, 15.0)
BOOST_BOUNDS = (1.0, 2.0)


def main() -> int:
    result = {}
    for film, entry in rf.CATALOG["films"].items():
        model = rf.ReversalPreview(rf.reversal_options(film, physics={film: {"grey_anchor": False}}))
        f = model.film
        grey_stops = np.log2(model.c.layer_exposure(0.18 * model.light("D55")) / 10.0 ** (f.options.midscale_log_h - f.negative_criterion_log_h))
        out = {"grey_stops_at_d55_with_chart_level": np.round(grey_stops, 3).tolist(), "relative_sensitivity": entry["relative_sensitivity"],
               "dye_curve_info": model.dye_curve_info}
        middle = f.options.midscale_log_h
        out["grey_status_a"] = np.round(model.record_to_status_a(model.negative_density(10.0 ** (middle - f.negative_criterion_log_h)[None])[0])[0], 3).tolist()
        chart = rf.p0.load_profile(film)["charts"].get("modulation_transfer")
        if chart:
            names = ("red", "green", "blue") if "red" in chart["curves"] else ("all_layers",) * 3
            spread, totals, image, boosts, residual = [], [], [], [], 0.0
            for k, name in enumerate(names):
                x, y = np.array(chart["curves"][name]["x"]), np.array(chart["curves"][name]["y"])
                curve = model.negative_curves[k]
                gamma = float(np.interp(middle + 0.5, curve.log_h, curve.density) - np.interp(middle - 0.5, curve.log_h, curve.density))
                free = least_squares(lambda p: response(x, *p) - y, (4.0, 15.0, 1.2), bounds=BOUNDS)
                total = float((free.x[2] - 1.0) / (free.x[2] * gamma))
                fixed = least_squares(lambda p: response(x, p[0], model.options.inhibition_um, p[1]) - y, (4.0, 1.2), bounds=((SPREAD_BOUNDS[0], BOOST_BOUNDS[0]), (SPREAD_BOUNDS[1], BOOST_BOUNDS[1])))
                s, boost = float(fixed.x[0]), float(fixed.x[1])
                if boost >= BOOST_BOUNDS[1] - 1e-3:
                    raise ValueError(f"{film}, {name}: B is at its upper bound {BOOST_BOUNDS[1]}, so the fit at {model.options.inhibition_um} um failed")
                spread.append(round(s, 2))
                totals.append(round(total, 4))
                image.append(round(max(min((boost - 1.0) * (1.0 - total * gamma) / gamma, total), 0.0), 4))
                boosts.append(round(boost, 4))
                residual = max(residual, float(np.sqrt(np.mean(fixed.fun ** 2))), float(np.sqrt(np.mean(free.fun ** 2))))
            out.update(layer_spread_um=spread, inhibition_total_free_fit=totals, inhibition_image=image, boost=boosts, largest_rms_residual=round(residual, 4))
        result[film] = out
        print(film, json.dumps({k: v for k, v in out.items() if k != "dye_curve_info"}), flush=True)
    rf.PHYSICS_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
