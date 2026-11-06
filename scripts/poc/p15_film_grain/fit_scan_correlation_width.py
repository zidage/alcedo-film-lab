"""Correlation width of the grain in the 5207 Flextight scans of the user (step P15).

Input: residual blocks of flat areas of the three 5207 scans, made by the grain colour study of Alcedo Studio #660
(build/tmp/p15_grain/study_660/res_00{1,2,3}.npz: 20 blocks of 256 x 256 pixels each, log10 units, zero mean; the
scans and the blocks stay local, AGENTS.md 'Photos and privacy').
Output: results/p15_film_grain/scan_correlation_width.json.

Question: what is the total Gaussian width s of the grain field in the scan, and so the upper limit of the dye-cloud
size sigma_c? The scan field is the film field (clouds of sigma_c) seen through the scanner optics (sigma_s) and
integrated over the pixel (pitch p): s^2 = sigma_c^2 + sigma_s^2 (Gaussian approximation). White scanner noise
changes only lag 0, so the ratio r = C(2p) / C(p) of the covariance at lags 2 and 1 gives s with no knowledge of the
noise or the density scale. The pitch is 3200 dpi (7.94 um): a 24 mm frame side is about 3120 pixels in the scans.

Model: C(d) = integral of tri_p(u) * N(d - u; 0, 2 s^2) du, with tri_p the autocorrelation of the pixel box. Fit: the
s that gives the measured r, per block and channel (bisection, 0.1 to 40 um). Result: the median and the quartiles.

The scanner MTF is not measured: the strips have no sprocket holes or film edges in the focal plane (the black
border is the holder mask). So s is an upper limit of sigma_c, not a value of it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BLOCKS = ROOT / "build" / "tmp" / "p15_grain" / "study_660"
OUTPUT = ROOT / "results" / "p15_film_grain" / "scan_correlation_width.json"
PITCH_UM = 25400.0 / 3200.0


def lag_cov(r: np.ndarray, lag: int) -> np.ndarray:
    """Covariance of each channel at a lag, x and y averaged."""
    a = (r[:, :-lag] * r[:, lag:]).reshape(-1, 3).mean(axis=0)
    b = (r[:-lag] * r[lag:]).reshape(-1, 3).mean(axis=0)
    return (a + b) / 2


def model_ratio(s_um: float, p_um: float = PITCH_UM) -> float:
    u = np.linspace(-p_um, p_um, 2001)
    tri = 1.0 - np.abs(u) / p_um
    var = 2.0 * s_um ** 2

    def c(d: float) -> float:
        return float(np.sum(tri * np.exp(-(d - u) ** 2 / (2 * var))))

    return c(2 * p_um) / c(p_um)


def fit_width(ratio: float) -> float:
    lo, hi = 0.1, 40.0
    if not model_ratio(lo) < ratio < model_ratio(hi):
        return float("nan")
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if model_ratio(mid) < ratio:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main() -> int:
    widths = {c: [] for c in "RGB"}
    ratios = {c: [] for c in "RGB"}
    for scan in ("001", "002", "003"):
        data = np.load(BLOCKS / f"res_{scan}.npz")
        for block in data["res"].astype(np.float64):
            block = block - block.mean(axis=(0, 1))
            r = lag_cov(block, 2) / lag_cov(block, 1)
            for k, c in enumerate("RGB"):
                ratios[c].append(float(r[k]))
                widths[c].append(fit_width(float(r[k])))
    out = {"pitch_um": PITCH_UM, "blocks": len(widths["R"]), "channels": {}}
    for c in "RGB":
        w = np.array(widths[c])
        w = w[np.isfinite(w)]
        out["channels"][c] = {"median_total_width_um": round(float(np.median(w)), 3),
                              "quartiles_um": [round(float(q), 3) for q in np.percentile(w, [25, 75])],
                              "median_ratio_c2_c1": round(float(np.median(ratios[c])), 4), "fitted_blocks": int(w.size)}
        print(c, out["channels"][c])
    out["reading"] = "s is the width of the cloud and the scanner optics together; sigma_c <= s."
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
