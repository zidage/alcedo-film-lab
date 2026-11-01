"""Limit the optical spread and the development inhibition of the P5 stocks from the modulation transfer curves of their profiles.

Input: the chart modulation_transfer of the negative profiles; the model form and the bounds of fit_mtf.py (P4). Output: results/p5_film_and_print_combinations/mtf_fit.json.
Step: P5, ROADMAP section 8, decision U34.

The form, the bounds, and the inference rules are those of P4. C200: the chart has one curve, so the three records use one fit of the spread and the boost, and only the slope of each layer differs. Gold 200: E-7022 has no chart, so the stock has no entry.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
from fit_mtf import BOUNDS, fp, response  # noqa: E402

RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "mtf_fit.json"
STOCKS = {"portra160": ("kodak_portra_160", "portra160_endura"), "portra800": ("kodak_portra_800", "portra800_endura"), "ektar100": ("kodak_ektar_100", "ektar100_endura"), "c200": ("fuji_c200", "c200_endura")}


def main() -> int:
    result = {}
    for name, (profile, stock) in STOCKS.items():
        curves = fp.p0.load_profile(profile)["charts"]["modulation_transfer"]["curves"]
        n = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, "negative_dye_basis": "band_split", "negative_record": "dye_amount", "scene_light": "D55"}))
        mid = n.options.midscale_log_h
        stock_result = {}
        for k, channel in enumerate(("red", "green", "blue")):
            f, m = np.array(curves[channel]["x"]), np.array(curves[channel]["y"])
            fit = least_squares(lambda p: response(f, *p) - m, (4.0, 15.0, 1.2), bounds=BOUNDS)
            curve = n.negative_curves[k]
            gamma = float(np.interp(mid + 0.5, curve.log_h, curve.density) - np.interp(mid - 0.5, curve.log_h, curve.density))
            spread, sigma_d, boost = fit.x
            stock_result[channel] = {"spread_um": round(float(spread), 2), "sigma_inhibitor_um": round(float(sigma_d), 2), "boost": round(float(boost), 4), "amount_slope_per_log10_h": round(gamma, 4), "inhibition_total": round(float((boost - 1.0) / (boost * gamma)), 4),
                                     "rms_residual": round(float(np.sqrt(np.mean(fit.fun ** 2))), 4), "at_bound": [bool(abs(v - b) < 1e-3) for v, b in zip(fit.x, BOUNDS[0])] + [bool(abs(v - b) < 1e-3) for v, b in zip(fit.x, BOUNDS[1])]}
        result[name] = stock_result
        print(name, json.dumps(stock_result), flush=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
