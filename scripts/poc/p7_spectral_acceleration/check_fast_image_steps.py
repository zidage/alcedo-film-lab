"""Checks of the image-plane rules for speed of step P7, against the forms that they replace. The limits below were written before this script first ran; sweep runs at 6000 pixels had shown the size of the inhibition difference.

Input: RAW files (first arguments), or AP1 arrays of the earlier steps when no argument is given. Output: results/p7_spectral_acceleration/image_steps.json, and a line per check on stdout. Step: P7, ROADMAP U70.
A failed check stays in the results with its value, and the exit code is 1. CPU only. The result is one image of three stocks per input; Ektar 100 has the largest inhibition of the accepted stocks.

| Check | Behaviour and comparison rule | Limit |
| Spread, two passes | Rule spread_per_layer_pass against six Gaussian blurs with one layer taken from each, final sRGB in 8 bit code, per pixel the largest channel difference | largest at most 0.5 |
| Speed rules | Rules inhibition_two_steps and inhibitor_on_half_size against 4 full-size steps, the same difference | mean at most 0.5; p99.9 at most 2.0; largest at most 5.0 |
| Flat neutral | A flat neutral image at -3, 0, and +3 stops: the same difference | largest at most 0.1 |
| Neutral ramp | The ramp of -5 to +5 stops, with no image plane, is not changed: the same difference | 0 |

Time of the negative stage and of the whole render on the CPU is stated with no limit: the product runs on the GPU.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
fk = fp.fk
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "image_steps.json"
ARRAYS = {"se188": "p3/input/se188", "leica_m11": "p3/input/leica_m11", "_DSC4063": "p4/input_shangrila/_DSC4063", "_DSC8148": "baseline/night/_DSC8148_ap1"}
STOCKS = {"5207 on 2383": mp.RenderSettings(), "Portra 400 on Endura": mp.RenderSettings(negative="kodak_portra_400", print_material="kodak_endura_premier"), "Ektar 100 on Endura": mp.RenderSettings(negative="kodak_ektar_100", print_material="kodak_endura_premier")}
LIMITS = {"spread_largest": 0.5, "speed_mean": 0.5, "speed_p999": 2.0, "speed_largest": 5.0, "flat_largest": 0.1, "ramp_largest": 0.0}
LONG_EDGE = 6000
NEW_SPREAD = fp.FilmPreview._spread_layers
NEW_INHIBITED = fp.FilmPreview._inhibited_image
NEW_STEPS = fp.INHIBITION_STEPS_IMAGE
failed: list[str] = []


def six_blur_spread(self, q: np.ndarray, pixel: float) -> np.ndarray:
    """The form of step P4."""
    out = np.empty_like(q)
    for k, length in enumerate(self.options.layer_spread_um):
        out[..., k] = sum(weight * fk.gaussian_blur(q, ratio * length / pixel)[..., k] for weight, ratio in fp.SPREAD_GAUSSIANS)
    return out


def full_size_inhibited(self, q: np.ndarray, amounts: np.ndarray, pixel: float) -> np.ndarray:
    """The form of step P4, with its number of steps set by INHIBITION_STEPS_IMAGE."""
    i = self.inhibition
    for _ in range(fp.INHIBITION_STEPS_IMAGE if pixel else fp.INHIBITION_STEPS_POINT):
        inhibitor = fk.gaussian_blur(amounts, self.options.inhibition_um / pixel) if pixel else amounts
        amounts = fk.inhibited_step(q, inhibitor, self.film.negative_criterion_log_h, i["k"], i["start"], i["free"], i["lengths"], i["step"])
    return amounts


def use(spread, inhibited, steps: int) -> None:
    fp.FilmPreview._spread_layers = spread
    fp.FilmPreview._inhibited_image = inhibited
    fp.INHIBITION_STEPS_IMAGE = steps


def render(model: fp.FilmPreview, image: np.ndarray) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    out = np.asarray(model.render(image)[0], dtype=np.float64)
    return out, time.perf_counter() - start


def difference(a: np.ndarray, b: np.ndarray) -> dict:
    d = np.abs(a - b).max(axis=-1) * 255.0
    return {"mean": round(float(d.mean()), 4), "p99": round(float(np.percentile(d, 99)), 4), "p999": round(float(np.percentile(d, 99.9)), 4), "largest": round(float(d.max()), 4)}


def require(name: str, value: float, limit: float) -> dict:
    passed = bool(value <= limit)
    print(f"{'pass' if passed else 'FAIL'} {name}: {value:.4g} (limit {limit:.4g})", flush=True)
    if not passed:
        failed.append(name)
    return {"value": float(value), "limit": limit, "pass": passed}


def inputs() -> dict[str, np.ndarray]:
    model = fp.FilmPreview(mp.film_options(mp.RenderSettings()))
    if sys.argv[1:]:
        return {Path(a).stem: mp.decode_raw(Path(a), model.c, LONG_EDGE)[0] for a in sys.argv[1:]}
    return {k: np.ascontiguousarray(np.load(REPO_ROOT / "build" / "tmp" / f"{v}.npy"), dtype=np.float32) for k, v in ARRAYS.items()}


def main() -> int:
    results: dict = {"limits": LIMITS, "stocks": {}}
    photos = inputs()
    default = mp.RenderSettings()
    ramp = np.outer(0.18 * 2.0 ** np.linspace(-5.0, 5.0, 241), np.ones(3)).astype(np.float32)[None]
    for title, settings in STOCKS.items():
        model = fp.FilmPreview(mp.film_options(settings))
        entry: dict = {"photos": {}}
        for name, ap1 in photos.items():
            graded = np.ascontiguousarray(fk.product_grade(ap1, float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32)
            use(six_blur_spread, full_size_inhibited, 4)
            old, old_seconds = render(model, graded)
            use(NEW_SPREAD, full_size_inhibited, 4)
            two_pass, _ = render(model, graded)
            use(NEW_SPREAD, NEW_INHIBITED, NEW_STEPS)
            new, new_seconds = render(model, graded)
            new, new_seconds = render(model, graded)
            entry["photos"][name] = {"size": list(ap1.shape[:2]), "spread_two_passes": difference(two_pass, old), "speed_rules": difference(new, two_pass), "all_against_p6": difference(new, old), "seconds_p6_form": round(old_seconds, 2), "seconds_now": round(new_seconds, 2)}
            print(f"  {title} {name}: {entry['photos'][name]}", flush=True)
        entry["spread"] = require(f"{title}, spread two passes", max(v["spread_two_passes"]["largest"] for v in entry["photos"].values()), LIMITS["spread_largest"])
        entry["speed_mean"] = require(f"{title}, speed rules mean", max(v["speed_rules"]["mean"] for v in entry["photos"].values()), LIMITS["speed_mean"])
        entry["speed_p999"] = require(f"{title}, speed rules p99.9", max(v["speed_rules"]["p999"] for v in entry["photos"].values()), LIMITS["speed_p999"])
        entry["speed_largest"] = require(f"{title}, speed rules largest", max(v["speed_rules"]["largest"] for v in entry["photos"].values()), LIMITS["speed_largest"])
        flat_largest = 0.0
        for stops in (-3.0, 0.0, 3.0):
            flat = np.full((256, 384, 3), 0.18 * 2.0 ** stops, dtype=np.float32)
            use(six_blur_spread, full_size_inhibited, 4)
            old_flat, _ = render(model, flat)
            use(NEW_SPREAD, NEW_INHIBITED, NEW_STEPS)
            new_flat, _ = render(model, flat)
            flat_largest = max(flat_largest, difference(new_flat, old_flat)["largest"])
        entry["flat_neutral"] = require(f"{title}, flat neutral", flat_largest, LIMITS["flat_largest"])
        use(six_blur_spread, full_size_inhibited, 4)
        old_ramp, _ = render(model, ramp)
        use(NEW_SPREAD, NEW_INHIBITED, NEW_STEPS)
        new_ramp, _ = render(model, ramp)
        entry["neutral_ramp"] = require(f"{title}, neutral ramp", difference(new_ramp, old_ramp)["largest"], LIMITS["ramp_largest"])
        results["stocks"][title] = entry
    results["failed"] = failed
    RESULT.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(failed)} failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
