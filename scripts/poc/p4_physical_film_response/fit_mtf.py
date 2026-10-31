"""W2 and W4: limit the optical spread and the development inhibition of each layer from the published modulation transfer curves.

Input: the chart modulation_transfer of the negative profiles, the P2 library for the slope of the dye amount curves. Output: results/p4_physical_film_response/mtf_fit.json.
Step: P4, README section 8, work items W2 and W4.

Model of one record (inferred form; the curves do not separate the two effects by themselves):
    M(f) = 1 / (1 + (2 pi s f)^2) * B / (1 + (B - 1) exp(-2 pi^2 sigma_d^2 f^2))
The first factor is an exponential spread of the light in the layer, with the length s: a turbid layer has long tails, and a Gaussian leaves an RMS residual of 0.03 to 0.07 on these curves. The second is the linear response of a development that an inhibitor of the Gaussian length sigma_d limits: at low f the inhibitor follows the image and at high f it is uniform, so the response grows by the factor B.
With amount a = F(log H - K a), and gamma the published slope d a / d log H: B = 1 + gamma_F K, gamma_F = B gamma, so K = (B - 1) / (B gamma). K is the total inhibition of a layer from all layers, because the test exposure of an MTF chart modulates all of them. Units of K: log10 H per unit of dye amount.
Bounds: s 0.5 to 15 um, sigma_d 3 to 60 um, B 1 to 2. A value at a bound is reported.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p2_negative_print"))
import film_preview as fp  # noqa: E402

RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "mtf_fit.json"
STOCKS = {"5207": ("kodak_5207", "5207_2383", "published"), "5219": ("kodak_5219", "5219_2383", "published"), "portra": ("kodak_portra_400", "portra400_endura", "band_split")}
FREQUENCY_UM = 1e-3  # cycles/mm to cycles/um
BOUNDS = ((0.5, 3.0, 1.0), (15.0, 60.0, 2.0))


def response(f_cycles_per_mm: np.ndarray, spread: float, sigma_d: float, boost: float) -> np.ndarray:
    f = f_cycles_per_mm * FREQUENCY_UM
    return 1.0 / (1.0 + (2.0 * np.pi * spread * f) ** 2) * boost / (1.0 + (boost - 1.0) * np.exp(-2.0 * np.pi ** 2 * sigma_d ** 2 * f ** 2))


def main() -> int:
    result = {}
    for name, (profile, stock, basis) in STOCKS.items():
        curves = fp.p0.load_profile(profile)["charts"]["modulation_transfer"]["curves"]
        n = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, "negative_dye_basis": basis, "negative_record": "dye_amount"}))
        mid = n.options.midscale_log_h
        stock_result = {}
        for k, channel in enumerate(("red", "green", "blue")):
            f, m = np.array(curves[channel]["x"]), np.array(curves[channel]["y"])
            fit = least_squares(lambda p: response(f, *p) - m, (4.0, 15.0, 1.2), bounds=BOUNDS)
            curve = n.negative_curves[k]
            gamma = float((np.interp(mid + 0.5, curve.log_h, curve.density) - np.interp(mid - 0.5, curve.log_h, curve.density)))
            spread, sigma_d, boost = fit.x
            stock_result[channel] = {"spread_um": round(float(spread), 2), "sigma_inhibitor_um": round(float(sigma_d), 2), "boost": round(float(boost), 4), "amount_slope_per_log10_h": round(gamma, 4),
                                     "inhibition_total": round(float((boost - 1.0) / (boost * gamma)), 4), "rms_residual": round(float(np.sqrt(np.mean(fit.fun ** 2))), 4), "at_bound": [bool(abs(v - b) < 1e-3) for v, b in zip(fit.x, BOUNDS[0])] + [bool(abs(v - b) < 1e-3) for v, b in zip(fit.x, BOUNDS[1])],
                                     "mtf_at_20_and_40": [round(float(np.interp(20.0, f, m)), 3), round(float(np.interp(40.0, f, m)), 3)]}
        result[name] = stock_result
        print(name, json.dumps(stock_result))
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
