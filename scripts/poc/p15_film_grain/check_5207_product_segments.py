"""Compare the P15 digitization of the 5207 granularity chart with the 5207 segments of Alcedo Studio (step P15).

Input: results/p15_film_grain/granularity_curves.json, and the literal segments of FilmGrainLayerSigma in
alcedo_studio/src/include/edit/runtime/film/film_grain_math.h (copied below; Alcedo Studio main f28ca394).
Output: results/p15_film_grain/check_5207_product_segments.json.

Measurement: over the density range that both cover, the ratio digitized / product of sigma_D, per layer. The plan of the
product (phase G0, step 1) expected a median absolute difference of at most 3 %. The result is recorded, not a check of
the digitizer: the digitizer is checked by its overlays and axis residuals, and the product segments are an earlier
reading by eye that places the green and blue peaks at higher densities (report P15, section 3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CURVES = ROOT / "results" / "p15_film_grain" / "granularity_curves.json"
OUTPUT = ROOT / "results" / "p15_film_grain" / "check_5207_product_segments.json"
MEDIAN_LIMIT = 0.03

# FilmGrainLayerSigma of film_grain_math.h: (start value, [(d0, d1, delta), ...]) per layer.
PRODUCT = {
    "R": (0.00565, [(0.22, 0.25, 0.00524 - 0.00565), (0.25, 0.42, 0.01085 - 0.00524), (0.42, 0.78, 0.00844 - 0.01085),
                    (0.78, 1.19, 0.00531 - 0.00844), (1.19, 1.58, 0.00486 - 0.00531), (1.94, 2.26, 0.00445 - 0.00486),
                    (2.26, 2.45, 0.00440 - 0.00445), (2.45, 2.52, 0.00474 - 0.00440)]),
    "G": (0.00517, [(0.59, 0.61, 0.00524 - 0.00517), (0.61, 0.66, 0.00625 - 0.00524), (0.66, 0.94, 0.01085 - 0.00625),
                    (0.94, 1.36, 0.00823 - 0.01085), (1.36, 1.76, 0.00617 - 0.00823), (1.76, 2.18, 0.00625 - 0.00617),
                    (2.18, 2.49, 0.00691 - 0.00625), (2.49, 2.61, 0.00602 - 0.00691), (2.61, 2.67, 0.00524 - 0.00602),
                    (2.67, 2.69, 0.00445 - 0.00524)]),
    "B": (0.01185, [(1.00, 1.03, 0.01261 - 0.01185), (1.03, 1.10, 0.01485 - 0.01261), (1.10, 1.32, 0.01581 - 0.01485),
                    (1.32, 1.51, 0.01200 - 0.01581), (1.51, 1.78, 0.01099 - 0.01200), (1.78, 2.05, 0.01127 - 0.01099),
                    (2.05, 2.38, 0.01058 - 0.01127), (2.38, 2.68, 0.00844 - 0.01058), (2.68, 2.91, 0.00641 - 0.00844),
                    (2.91, 3.00, 0.00418 - 0.00641)]),
}


def product_sigma(layer: str, density: np.ndarray) -> np.ndarray:
    start, segments = PRODUCT[layer]
    value = np.full_like(density, start)
    for d0, d1, delta in segments:
        value += delta * np.clip((density - d0) / (d1 - d0), 0.0, 1.0)
    return value


def main() -> int:
    data = json.loads(CURVES.read_text(encoding="utf-8"))["stocks"]["kodak_5207"]["layers"]
    result = {"expected_median_abs_relative": MEDIAN_LIMIT, "layers": {}}
    passed = True
    for layer in "RGB":
        density = np.asarray(data[layer]["density"])
        sigma = np.asarray(data[layer]["sigma_d"])
        start = PRODUCT[layer][1][0][0]
        stop = PRODUCT[layer][1][-1][1]
        keep = (density >= start) & (density <= stop)
        ratio = sigma[keep] / product_sigma(layer, density[keep])
        rel = np.abs(ratio - 1.0)
        record = {"density_range": [float(density[keep].min()), float(density[keep].max())],
                  "median_abs_relative": round(float(np.median(rel)), 4),
                  "largest_abs_relative": round(float(rel.max()), 4),
                  "density_of_largest": round(float(density[keep][int(np.argmax(rel))]), 3),
                  "mean_ratio": round(float(np.mean(ratio)), 4)}
        record["within_expected_3_percent"] = record["median_abs_relative"] <= MEDIAN_LIMIT
        passed &= record["within_expected_3_percent"]
        result["layers"][layer] = record
        print(layer, record)
    result["within_expected_3_percent"] = passed
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, indent=1)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
