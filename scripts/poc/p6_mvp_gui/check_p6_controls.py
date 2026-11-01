"""Checks of the user controls of the Python MVP. The limits were set before the first run.

Input: first argument, an AP1 array (.npy) of a photo. Output: results/p6_python_mvp/controls.json, and a line per check on stdout. Step: P6, ROADMAP U62.
A failed check stays in the results with its value, and the exit code is 1. All cases use 5207 on 2383 and the two methods, except the check of the inhibition, which uses all negatives.

| Check | Behaviour and comparison rule | Limit |
| Range of output | Each control at its low and its high end: the output of the photo is finite and in 0 to 1 | no failure |
| Effect | The same cases: mean of absolute code against the default | above 0.0001 |
| Neutral ramp | The same ends, on the ramp of check_p6_mvp.py with no grade and no lab scanner stage: largest fall of G code | 0.002 |
| Other method | A control of one method at its high end, on the other method: largest difference of code | 0 |
| Bad value | A value outside the range stops with an error that names the control | error |
| Inhibition | The high end of the inhibition on each negative: the curves F_i exist | no error |
| LAD aim | Each accepted stock on the APD method: a neutral image of 0.18, with no grade, in ADX10 against code value 445, largest difference per channel | 5 code values (0.01 density) |
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import check_p6_mvp as base_checks
import mvp_pipeline as mp

RESULT = mp.REPO_ROOT / "results" / "p6_python_mvp" / "controls.json"
EFFECT_LIMIT = 0.0001


def main() -> int:
    photo = np.ascontiguousarray(np.load(sys.argv[1]), dtype=np.float32)
    ramp = base_checks.test_image()
    pipeline = mp.Pipeline()
    base = mp.RenderSettings()
    flat = replace(base, exposure_ev=0.0, contrast=0.0, saturation=1.0)
    default = {method: pipeline.render_array(photo, replace(base, method=method)) for method in mp.METHODS}
    result: dict = {"input": Path(sys.argv[1]).name, "controls": {}, "other_method": {}}
    failures = []
    # print_timing has an effect only when the scene light is not the reference light.
    context = {"print_timing": {"scene_light": "tungsten"}}
    extra = {"display_white": {"low": "paper"}, "gamut_compress": {"low": False}}
    cases = [(c.name, c.methods, {"low": c.low, "high": c.high}) for c in mp.CONTROLS] + [(name, mp.PRINT, ends) for name, ends in extra.items()] + [("apd_output", mp.SCAN, {"low": "aces13"}), ("apd_lad_aim", mp.SCAN, {"low": False})]
    for name, methods, ends in cases:
        row: dict = {}
        for method in methods:
            start = replace(base, method=method, **context.get(name, {}))
            reference = default[method] if name not in context else pipeline.render_array(photo, start)
            for end, value in ends.items():
                if value == getattr(base, name):
                    continue
                t = time.perf_counter()
                key = f"{method}_{end}"
                try:
                    image = pipeline.render_array(photo, replace(start, **{name: value}))
                    ramp_image = pipeline.render_array(ramp, replace(flat, method=method, **context.get(name, {}), **{name: value}))
                except Exception as error:  # noqa: BLE001 - recorded as a failed check with the real error
                    row[key] = {"value": value, "error": f"{type(error).__name__}: {error}"}
                    failures.append(f"run {name} {key}: {error}")
                    continue
                effect = float(np.abs(image - reference).mean())
                fall = base_checks.largest_fall(ramp_image)
                row[key] = {"value": value, "effect": round(effect, 5), "fall": round(fall, 5), "range": [round(float(image.min()), 4), round(float(image.max()), 4)], "s": round(time.perf_counter() - t, 1)}
                if not np.isfinite(image).all() or image.min() < -1e-6 or image.max() > 1.0 + 1e-6:
                    failures.append(f"range {name} {key}")
                if effect <= EFFECT_LIMIT:
                    failures.append(f"no effect {name} {key} {effect}")
                if fall > base_checks.FALL_LIMIT:
                    failures.append(f"ramp {name} {key} {fall}")
        result["controls"][name] = row
        print(name, json.dumps(row), flush=True)

    for control in mp.CONTROLS:
        if control.methods == mp.BOTH:
            continue
        other = "apd" if control.methods == mp.PRINT else "print"
        largest = float(np.abs(pipeline.render_array(photo, replace(base, method=other, **{control.name: control.high})) - default[other]).max())
        result["other_method"][control.name] = largest
        if largest != 0.0:
            failures.append(f"other method {control.name} {largest}")

    try:
        replace(base, print_contrast=9.0).validate()
        failures.append("bad value gave no error")
    except ValueError as error:
        result["bad_value_error"] = str(error)

    # The rule needs only the curves, so this check builds no print table for the high end.
    inhibition = next(c for c in mp.CONTROLS if c.name == "inhibition_scale")
    result["inhibition_high_end"] = {}
    for negative, entry in mp.CATALOG["negatives"].items():
        settings = mp.RenderSettings(negative=negative, print_material="kodak_2383" if entry["medium"].lower() == "cine" else "kodak_endura_premier")
        model = mp.fp.FilmPreview(mp.film_options(settings))
        stub = SimpleNamespace(options=mp.film_options(replace(settings, inhibition_scale=inhibition.high)), negative_curves=model.negative_curves)
        try:
            mp.fp.FilmPreview._prepare_inhibition(stub)
            result["inhibition_high_end"][negative] = "ok"
        except ValueError as error:
            result["inhibition_high_end"][negative] = str(error)
            failures.append(f"inhibition {negative}: {error}")
    result["lad_aim"] = {}
    neutral = np.full((32, 32, 3), 0.18, dtype=np.float32)
    for negative in mp.ACCEPTED_STOCKS:
        code = pipeline.scan_model(replace(base, negative=negative, method="apd")).adx10(neutral)[0].mean(axis=(0, 1))
        result["lad_aim"][negative] = np.round(code, 2).tolist()
        print(negative, "ADX10 of a neutral", result["lad_aim"][negative], flush=True)
        if np.abs(code - 445.0).max() > 5.0:
            failures.append(f"LAD aim {negative} {result['lad_aim'][negative]}")
    t = time.perf_counter()
    pipeline.print_model(replace(base, halation_scale=2.0))
    result["model_load_with_cached_table_s"] = round(time.perf_counter() - t, 2)
    result["failures"] = failures
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("failures", len(failures))
    for failure in failures:
        print(" ", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
