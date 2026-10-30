"""Compare the compiled kernels with the array implementation of film_preview.py, and report the time.

Input: a synthetic image of 1 MP (no photo), the cached tables. Output: results/p2_negative_print/fast_kernels.json. Limits set before the first run:
- print nodes: 4096 densities, Delta E*ab max <= 0.01, the same counts;
- blur: against scipy.ndimage.gaussian_filter, on the sigma values of the darkroom options: relative max error <= 0.002 of the image range;
- render against reference_render: sRGB difference p99.9 <= 1/255 and max <= 3/255;
- the same counts of moved, not positive, and above the curve end.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fast_kernels as fk  # noqa: E402
import film_preview as fp  # noqa: E402
from profile_preview import image  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
result = {"pass": {}}


def best(function, *args, repeat=3):
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        out = function(*args)
        times.append(time.perf_counter() - start)
    return out, min(times) * 1000.0


preview = fp.FilmPreview(fp.FilmOptions(**fp.STOCKS["5219_2383"], **fp.DARKROOM, scene_light="T3200"))
ap1 = image()
rng = np.random.default_rng(20261030)
nodes = np.stack([rng.uniform(g[0], g[-1], 4096) for g in preview.density_grid], axis=1)
direct, direct_counts = preview.direct_print_xyz(nodes)
fast, fast_counts = preview._print_nodes(nodes)
white = preview.film.white_xyz()
de = np.linalg.norm(fp.sr.xyz_to_lab(direct, white) - fp.sr.xyz_to_lab(fast, white), axis=1)
result["print_nodes"] = {"delta_e_max": float(de.max()), "counts_reference": direct_counts, "counts_kernel": fast_counts}
result["pass"]["print_nodes"] = bool(de.max() <= 0.01 and direct_counts == fast_counts)

test = ap1.astype(np.float32)
blur = {}
for sigma in (0.35, 2.1, 4.2, 8.0, 40.0, 125.0):
    reference = gaussian_filter(test, (sigma, sigma, 0))
    error = float(np.abs(fk.gaussian_blur(test, sigma) - reference).max() / (test.max() - test.min()))
    blur[str(sigma)] = error
result["blur_relative_max_error"] = blur
result["pass"]["blur"] = bool(max(blur.values()) <= 0.002)

(out, stats), fast_ms = best(preview.render, ap1)
(ref, ref_stats), ref_ms = best(preview.reference_render, ap1, repeat=1)
difference = np.abs(out.astype(np.float64) - ref)
result["render"] = {"srgb_difference_p999": float(np.percentile(difference, 99.9)), "srgb_difference_max": float(difference.max()),
                    "counts_kernel": stats, "counts_reference": {k: v for k, v in ref_stats.items() if k != "gamut_distance_p999"}}
result["pass"]["render"] = bool(np.percentile(difference, 99.9) <= 1.0 / 255.0 and difference.max() <= 3.0 / 255.0)
result["pass"]["counts"] = all(stats[k] == ref_stats[k] for k in ("moved_by_rule", "y_not_positive", "negative_above_curve_end"))

# The first image stays inside the spectral locus. This one has out-of-locus colours, negative values, and values above the curve end.
wide = rng.uniform(-0.3, 1.0, (400, 500, 3)) * np.exp(rng.normal(0.0, 1.5, (400, 500, 1)))
out, stats = preview.render(wide)
ref, ref_stats = preview.reference_render(wide)
difference = np.abs(out.astype(np.float64) - ref)
wide_keys = ("moved_by_rule", "y_not_positive", "negative_above_curve_end")
result["render_wide"] = {"srgb_difference_p999": float(np.percentile(difference, 99.9)), "srgb_difference_max": float(difference.max()),
                         "counts_kernel": {k: stats[k] for k in wide_keys}, "counts_reference": {k: ref_stats[k] for k in wide_keys}}
result["pass"]["render_wide"] = bool(np.percentile(difference, 99.9) <= 1.0 / 255.0 and difference.max() <= 3.0 / 255.0 and all(stats[k] == ref_stats[k] for k in wide_keys) and stats["moved_by_rule"] > 0)
result["time_ms"] = {"render_kernels": round(fast_ms, 1), "render_reference": round(ref_ms, 1), "pixels": int(ap1.shape[0] * ap1.shape[1])}
start = time.perf_counter()
grid = np.stack(np.meshgrid(*preview.density_grid, indexing="ij"), axis=-1).reshape(-1, 3)
preview._print_nodes(grid)
result["time_ms"]["print_table_build"] = round((time.perf_counter() - start) * 1000.0, 1)

# Default grade against a separate array form of the product reference (alcedo_studio/tests/edit/runtime/oklab_contrast_reference.hpp
# and the saturation of primary_grade.cl). Limit: max linear error <= 1e-4 of the largest channel, the tolerance of the product GPU tests.
TO_LMS = np.array([[0.6341104672, 0.3489495087, 0.0169400240], [0.2754060131, 0.6327713632, 0.0918226237], [0.1056775254, 0.1971481306, 0.6971743440]])
TO_LAB = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])
FROM_LAB = np.array([[1.0, 0.3963377774, 0.2158037573], [1.0, -0.1055613458, -0.0638541728], [1.0, -0.0894841775, -1.2914855480]])
FROM_LMS = np.array([[2.0693822907, -1.1736821545, 0.1042998638], [-0.8917480677, 2.1537429245, -0.2619948569], [-0.0615064732, -0.4311325686, 1.4926390418]])
samples = np.abs(rng.normal(0.18, 0.5, (200, 300, 3))) + 1e-3
linear = samples.reshape(-1, 3) * 2.0 ** 0.7
slope = 2.0 ** 0.15
lab = np.cbrt(linear @ TO_LMS.T) @ TO_LAB.T
gain = 2.0 ** ((slope - 1.0) * 2.5 * np.tanh(3.0 * np.log2(lab[:, 0] / np.cbrt(0.18)) / 2.5) / 3.0)
lab = lab * np.stack([gain, np.sqrt(slope) * np.minimum(gain, 1.0), np.sqrt(slope) * np.minimum(gain, 1.0)], axis=1)
linear = (lab @ FROM_LAB.T) ** 3 @ FROM_LMS.T
positive = linear.min(axis=1) > 1e-4
code = (np.log2(np.maximum(linear, 1e-30)) + 9.72) / 17.52
luma = code @ np.array([0.272229, 0.674082, 0.053689])
graded_code = luma[:, None] + (code - luma[:, None]) * 1.3
floor = (-16.0 + 9.72) / 17.52
# CeAcesccDecode of the product: a code below the floor is a negative linear value.
expected = np.where(graded_code < floor, graded_code - floor, 2.0 ** (graded_code * 17.52 - 9.72))
kernel = fk.product_grade(samples.astype(np.float32), 0.7, 15.0, 1.3).reshape(-1, 3)
error = float((np.abs(kernel - expected) / expected.max(axis=1, keepdims=True))[positive].max())
result["product_grade"] = {"relative_linear_error_max": error, "samples": int(positive.sum())}
result["pass"]["product_grade"] = bool(error <= 1e-4)
print(json.dumps(result, indent=1))
(REPO_ROOT / "results" / "p2_negative_print" / "fast_kernels.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
