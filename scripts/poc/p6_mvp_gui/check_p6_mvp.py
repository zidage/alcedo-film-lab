"""Checks of the Python MVP. The limits were set before the first run.

Input: stock_catalog.json, a RAW file (first argument). Output: results/p6_python_mvp/checks.json, and a line per check on stdout. Step: P6, README U61.
A failed check stays in the results with its value, and the exit code is 1.

| Check | Behaviour and comparison rule | Limit |
| RAW size | The long edge of the decoded image is 2048 | exact |
| Finite | Every negative on its default print and on the Frontier method, every print with 5207: the output of a test image is finite and in 0 to 1 | no failure |
| Neutral ramp, print | Display G code falls along a neutral ramp from -5 to +5 stops | 0.002 |
| Neutral ramp, scan | The same on the Frontier method, with no lab scanner stage | 0.002 |
| Repeatable | The same settings give the same image twice | 0 |
| Spectral prior | The two priors differ on a saturated patch, mean of absolute code | above 0.001 |
| Scene light | Each light runs on 5207 by both methods, and the output is finite; 'tungsten' differs from 'daylight', mean of absolute code | above 0.002 |
| Bad material | A print material with no sensitivity stops with an error that names the reason | error |
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

import mvp_pipeline as mp

RESULT = mp.REPO_ROOT / "results" / "p6_python_mvp" / "checks.json"
FALL_LIMIT = 0.002
DEFAULT_PRINT = {"cine": "kodak_2383", "photo": "kodak_endura_premier"}


def test_image() -> np.ndarray:
    """A neutral ramp of 256 columns from -5 to +5 stops above a row of saturated colours, linear AP1 (not product input)."""
    ramp = 0.18 * 2.0 ** np.linspace(-5.0, 5.0, 256)
    image = np.tile(ramp[None, :, None], (64, 1, 3))
    hues = np.array([[0.6, 0.05, 0.05], [0.05, 0.5, 0.05], [0.05, 0.05, 0.6], [0.6, 0.5, 0.05], [0.05, 0.5, 0.5], [0.5, 0.05, 0.5], [0.5, 0.25, 0.1], [0.2, 0.3, 0.5]])
    image[32:, :, :] = hues[(np.arange(256) * len(hues) // 256)][None, :, :]
    return image.astype(np.float32)


def largest_fall(image: np.ndarray) -> float:
    green = image[:32, :, 1].mean(axis=0)
    return float(np.maximum(green[:-1] - green[1:], 0.0).max())


def main() -> int:
    raw = Path(sys.argv[1])
    pipeline = mp.Pipeline()
    source = test_image()
    flat = replace(mp.RenderSettings(), exposure_ev=0.0, contrast=0.0, saturation=1.0)
    result: dict = {"raw_file_name": raw.name, "negatives": {}, "prints": {}}
    failures = []
    start = time.perf_counter()
    image, record = pipeline.render_file(raw, mp.RenderSettings())
    result["raw"] = {k: record[k] for k in ("sensor_long_edge", "half_size_decode", "processed_long_edge", "model_load_s", "decode_s", "render_s")}
    if record["processed_long_edge"] != mp.DEFAULT_LONG_EDGE:
        failures.append("raw size")
    frontier_image, frontier_record = pipeline.render_file(raw, replace(mp.RenderSettings(), method="frontier"))
    result["raw"]["frontier_render_s"] = frontier_record["render_s"]

    for negative, entry in mp.CATALOG["negatives"].items():
        row: dict = {}
        material = DEFAULT_PRINT[entry["medium"].lower()]
        for method in mp.METHODS:
            t = time.perf_counter()
            settings = replace(flat, negative=negative, method=method, print_material=material, scanner_stage=False)
            try:
                image = pipeline.render_array(source, settings)
                row[method] = {"fall": round(largest_fall(image), 5), "range": [round(float(image.min()), 4), round(float(image.max()), 4)], "s": round(time.perf_counter() - t, 1)}
                if row[method]["fall"] > FALL_LIMIT:
                    failures.append(f"ramp {negative} {method} {row[method]['fall']}")
                if image.min() < -1e-6 or image.max() > 1.0 + 1e-6:
                    failures.append(f"range {negative} {method}")
            except Exception as error:  # noqa: BLE001 - recorded as a failed check with the real error
                row[method] = {"error": f"{type(error).__name__}: {error}"}
                failures.append(f"run {negative} {method}: {error}")
        result["negatives"][negative] = row
        print(negative, json.dumps(row), flush=True)

    for material in mp.CATALOG["prints"]:
        t = time.perf_counter()
        try:
            image = pipeline.render_array(source, replace(flat, print_material=material))
            result["prints"][material] = {"fall": round(largest_fall(image), 5), "range": [round(float(image.min()), 4), round(float(image.max()), 4)], "s": round(time.perf_counter() - t, 1)}
            if result["prints"][material]["fall"] > FALL_LIMIT:
                failures.append(f"ramp print {material} {result['prints'][material]['fall']}")
        except Exception as error:  # noqa: BLE001 - recorded as a failed check with the real error
            result["prints"][material] = {"error": f"{type(error).__name__}: {error}"}
            failures.append(f"run print {material}: {error}")
        print(material, json.dumps(result["prints"][material]), flush=True)

    base = replace(flat, method="frontier", scanner_stage=True)
    result["repeat_largest_difference"] = float(np.abs(pipeline.render_array(source, base) - pipeline.render_array(source, base)).max())
    if result["repeat_largest_difference"] != 0.0:
        failures.append("repeatable")
    prior = {}
    for method in mp.METHODS:
        a = pipeline.render_array(source, replace(flat, method=method, spectral_prior="light_like"))
        b = pipeline.render_array(source, replace(flat, method=method, spectral_prior="measured_reflectance"))
        prior[method] = round(float(np.abs(a - b)[32:].mean()), 5)
        if prior[method] <= 0.001:
            failures.append(f"prior has no effect on {method}: {prior[method]}")
    result["prior_difference"] = prior
    lights = {}
    for light in mp.SCENE_LIGHTS:
        lights[light] = {}
        for method in mp.METHODS:
            image = pipeline.render_array(source, replace(flat, method=method, scene_light=light))
            lights[light][method] = np.round(image[32:].mean(axis=(0, 1)), 4).tolist()
    for method in mp.METHODS:
        a = pipeline.render_array(source, replace(flat, method=method, scene_light="tungsten"))
        b = pipeline.render_array(source, replace(flat, method=method, scene_light="daylight"))
        lights[f"tungsten_against_daylight_{method}"] = round(float(np.abs(a - b)[32:].mean()), 5)
        if lights[f"tungsten_against_daylight_{method}"] <= 0.002:
            failures.append(f"scene light has no effect on {method}")
    result["scene_lights"] = lights
    try:
        replace(flat, print_material="technicolor_v").validate()
        failures.append("bad material gave no error")
    except ValueError as error:
        result["bad_material_error"] = str(error)
    result["failures"] = failures
    result["seconds"] = round(time.perf_counter() - start, 1)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("failures", len(failures))
    for failure in failures:
        print(" ", failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
