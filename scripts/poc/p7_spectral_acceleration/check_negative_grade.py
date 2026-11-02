"""Check of rule 'negative_show_grade' on synthetic colours.

Input: none. Output: results/p7_spectral_acceleration/negative_grade.json. Step: P7, ROADMAP U82 to U85. CPU only.
Limits, set before the run:
- A grid of 33 ** 3 records: output finite and not negative.
- The same grid, evaluated in one array and per pixel on a sample of 2000 records: largest difference at most 1e-6.
- Record of an 18 % grey: each channel moves by at most 0.005, because the rule keeps the print grey.
- A print of a neutral ramp, 5219 on cine_look, -8 to +5 stops from the grey: luma falls by at most 1e-3 between neighbours.
- With the option off, or with the APD method, the output equals the render with no rule: largest difference 0.
- Noise: a flat dusk blue with relative noise 6 % per channel, 2048 pixels: the luma standard deviation of 5219 on cine_look is at most that of 5219 on kodak_2383.
- Only the stocks of NEGATIVE_GRADE_STOCKS on cine_look have the rule, of each pair of a negative and a print material in the catalog.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
grade = fp.grade
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "negative_grade.json"
LUMA = np.array([0.2126, 0.7152, 0.0722])
SETTINGS = mp.RenderSettings(negative="kodak_5219", print_material=mp.CINE_LOOK_PRINT, exposure_ev=0.0, contrast=0.0)


def main() -> int:
    pipeline = mp.Pipeline()
    model = pipeline.print_model(SETTINGS)
    grey = model._grade_grey
    axis = np.linspace(0.0, 3.0, 33)
    records = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    graded = grade.negative_grade(records, grey)
    sample = np.random.default_rng(1).choice(len(records), 2000, replace=False)
    per_pixel = np.stack([grade.negative_grade(records[i], grey) for i in sample])

    ramp = np.outer(0.18 * 2.0 ** np.linspace(-8.0, 5.0, 1025), np.ones(3)).astype(np.float32)[None]
    print_ramp = pipeline.render_array(ramp, SETTINGS)[0].astype(np.float64) @ LUMA

    off = replace(SETTINGS, negative_grade=False)
    plain = pipeline.print_model(off)
    apd = replace(SETTINGS, method="apd")
    apd_off = replace(apd, negative_grade=False)
    noisy = np.ascontiguousarray(np.array([0.030, 0.060, 0.120], dtype=np.float32) * (1.0 + np.random.default_rng(3).normal(0.0, 0.06, (1200, 2048, 3)).astype(np.float32)), dtype=np.float32)
    noise_plain = float((pipeline.render_array(noisy, replace(SETTINGS, print_material="kodak_2383", exposure_ev=1.5, contrast=15.0)).astype(np.float64)[40:-40, 40:-40] @ LUMA).std() * 255.0)
    noise_rule = float((pipeline.render_array(noisy, replace(SETTINGS, exposure_ev=1.5, contrast=15.0)).astype(np.float64)[40:-40, 40:-40] @ LUMA).std() * 255.0)
    with_rule = sorted(f"{name} on {material}" for name in mp.CATALOG["negatives"] for material in mp.CATALOG["prints"] if mp.film_options(replace(SETTINGS, negative=name, print_material=material)).negative_grade)

    record = {"grey_record": grey.tolist(), "grid_finite": bool(np.isfinite(graded).all()), "grid_low": float(graded.min()), "per_pixel_largest_difference": float(np.abs(graded[sample] - per_pixel).max()),
              "grey_largest_move": float(np.abs(grade.negative_grade(grey, grey).astype(np.float64) - grey).max()), "print_ramp_largest_fall": float(max(0.0, -np.diff(print_ramp).min())),
              "option_off_has_no_grey": plain._grade_grey is None, "apd_largest_difference": float(np.abs(pipeline.render_array(ramp, apd) - pipeline.render_array(ramp, apd_off)).max()), "noise_luma_codes_rule": noise_rule, "noise_luma_codes_plain_2383": noise_plain, "pairs_with_rule": with_rule}
    passed = (record["grid_finite"] and record["grid_low"] >= 0.0 and record["per_pixel_largest_difference"] <= 1e-6 and record["grey_largest_move"] <= 0.005 and record["print_ramp_largest_fall"] <= 1e-3
              and record["option_off_has_no_grey"] and record["apd_largest_difference"] == 0.0 and noise_rule <= noise_plain and with_rule == sorted(f"{name} on {mp.CINE_LOOK_PRINT}" for name in mp.NEGATIVE_GRADE_STOCKS))
    record["passed"] = bool(passed)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(record, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
