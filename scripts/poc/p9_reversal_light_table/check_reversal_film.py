"""Checks of the reversal films on the light table. Step P9, ROADMAP U86.

Input: the reversal profiles, reversal_physics.json, and optionally one AP1 array (.npy, linear AP1 of a RAW file) as the first argument. Output: results/p9_reversal_light_table/checks.json and a table on stdout.
Each check states the behaviour, the comparison, and the limit; the limits were set before the first run.
- neutral_ramp: the neutral ramp through the curves, rule 'removed_dye_record', and the point form of the inhibition gives the published Status A curve. Largest difference at most 0.01 density, over the published domain.
- clear_film_white: the clear film goes to display white (1, 1, 1) in linear light (rule 'clear_film_white'). Largest difference at most 1e-6.
- light_table_interpolation: the 65^3 table against the direct spectral integral, on 20000 random records, as sRGB code after the surround rule. Largest difference at most 1.0 of an 8 bit code value, p99.9 at most 0.25.
- extreme_input: AP1 values from -1 to 1e4 and a hue sweep give finite output in 0 to 1.
- grey: the display code of an 18 % grey and its Status A on the slide, recorded with no limit (the cast of a film is a property of the stock, ROADMAP U36).
- photo: with an AP1 array, the time of the model and of the render through the viewer pipeline at 2048 pixels, and the count of clipped pixels; recorded with no limit.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parents[0] / "p6_mvp_gui"))
import reversal_film as rf  # noqa: E402

fp = rf.fp
RESULT = rf.REPO_ROOT / "results" / "p9_reversal_light_table" / "checks.json"
LIMITS = {"neutral_ramp_density": 0.01, "clear_film_white": 1e-6, "table_code_largest": 1.0, "table_code_p999": 0.25}


def neutral_ramp(model: rf.ReversalPreview) -> dict:
    f = model.film
    worst = 0.0
    for k, curve in enumerate(model.status_curves):
        log_h = curve.log_h[(curve.log_h >= max(c.log_h[0] for c in model.status_curves)) & (curve.log_h <= min(c.log_h[-1] for c in model.status_curves))]
        q = np.repeat((10.0 ** (log_h - f.negative_criterion_log_h[k]))[:, None], 3, axis=1) * (10.0 ** (f.negative_criterion_log_h[k] - f.negative_criterion_log_h))[None, :]
        status = model.record_to_status_a(model.negative_density(q)[0])
        published = np.stack([np.interp(log_h, c.log_h, c.density) for c in model.status_curves], axis=1)
        worst = max(worst, float(np.abs(status - published).max()))
    return {"largest_density_difference": round(worst, 5), "limit": LIMITS["neutral_ramp_density"], "within_limit": worst <= LIMITS["neutral_ramp_density"]}


def table_against_integral(model: rf.ReversalPreview, count: int = 20000) -> dict:
    rng = np.random.default_rng(9)
    top = np.array([g[-1] for g in model.density_grid])
    record = (rng.random((count, 3)) * top).astype(np.float32)
    table = fp.fk.print_display(record[None], model._print_f32, model._grid_start, model._grid_step, model.xyz_to_display)[0]
    direct = (model.light_table_xyz(record.astype(np.float64)) @ model.xyz_to_display.T).astype(np.float32)

    def code(rgb: np.ndarray) -> np.ndarray:
        return fp.srgb_encode(np.clip(model.surround(rgb[None])[0], 0.0, 1.0)) * 255.0

    difference = np.abs(code(table) - code(direct)).max(axis=1)
    largest, p999 = float(difference.max()), float(np.percentile(difference, 99.9))
    return {"largest_code": round(largest, 4), "p999_code": round(p999, 4), "limits": [LIMITS["table_code_largest"], LIMITS["table_code_p999"]],
            "within_limit": largest <= LIMITS["table_code_largest"] and p999 <= LIMITS["table_code_p999"]}


def extreme_input(model: rf.ReversalPreview) -> dict:
    values = np.array([-1.0, -1e-3, 0.0, 1e-6, 1e-3, 0.18, 1.0, 10.0, 100.0, 1e4])
    grid = np.stack(np.meshgrid(values, values, values, indexing="ij"), axis=-1).reshape(1, -1, 3)
    hue = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    sweep = np.stack([0.18 + 0.17 * np.cos(hue), 0.18 + 0.17 * np.cos(hue - 2.0943951), 0.18 + 0.17 * np.cos(hue + 2.0943951)], axis=-1)[None]
    outputs = [model.render(np.ascontiguousarray(a, dtype=np.float32))[0] for a in (grid, sweep, sweep * 8.0)]
    finite = all(np.isfinite(o).all() for o in outputs)
    inside = all(((o >= 0.0) & (o <= 1.0)).all() for o in outputs)
    return {"finite": bool(finite), "inside_0_1": bool(inside), "within_limit": bool(finite and inside)}


def main() -> int:
    photo = np.ascontiguousarray(np.load(sys.argv[1]), dtype=np.float32) if len(sys.argv) > 1 else None
    result: dict = {"limits": LIMITS, "films": {}}
    import mvp_pipeline as mp

    pipeline = mp.Pipeline()
    for film in rf.CATALOG["films"]:
        model = rf.ReversalPreview(rf.reversal_options(film))
        clear = model.display_linear(model.print_dmin_xyz()[None])[0]
        grey_code = model.render(np.full((1, 3), 0.18, dtype=np.float32))[0][0]
        f = model.film
        grey_record = model.negative_density(model.layer_gain[None] * model.c.layer_exposure(0.18 * model.scene_spectrum)[None])[0]
        entry = {
            "neutral_ramp": neutral_ramp(model),
            "clear_film_white": {"linear_rgb": np.round(clear, 8).tolist(), "within_limit": bool(np.abs(clear - 1.0).max() <= LIMITS["clear_film_white"])},
            "light_table_interpolation": table_against_integral(model),
            "extreme_input": extreme_input(model),
            "grey": {"srgb_code": np.round(grey_code, 4).tolist(), "status_a": np.round(model.record_to_status_a(grey_record)[0], 3).tolist(), "clear_film_xyz": np.round(model.print_dmin_xyz(), 3).tolist(),
                     "dye_curve_info": model.dye_curve_info},
        }
        if photo is not None:
            settings = replace(mp.RenderSettings(), method="light_table", reversal=film)
            start = time.perf_counter()
            pipeline.light_table_model(settings)
            built = time.perf_counter() - start
            start = time.perf_counter()
            image = pipeline.render_array(photo, settings)
            entry["photo"] = {"pixels": list(image.shape[:2]), "model_s": round(built, 2), "render_s": round(time.perf_counter() - start, 2), "finite": bool(np.isfinite(image).all())}
        result["films"][film] = entry
        print(film, json.dumps({k: v.get("within_limit", v) if isinstance(v, dict) else v for k, v in entry.items() if k != "grey"}), "grey", entry["grey"]["srgb_code"], flush=True)
    result["all_within_limits"] = all(v["within_limit"] for e in result["films"].values() for k, v in e.items() if isinstance(v, dict) and "within_limit" in v)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("all within limits:", result["all_within_limits"])
    return 0 if result["all_within_limits"] else 1


if __name__ == "__main__":
    sys.exit(main())
