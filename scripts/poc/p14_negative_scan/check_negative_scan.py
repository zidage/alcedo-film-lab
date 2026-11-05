"""Checks of method negative_scan (step P14).

Input: the profiles and the tables of P0 to P7 (as the viewer). Output: results/p14_negative_scan/checks.json.
Step: P14. Each check states the behaviour, the comparison, and the tolerance; the tolerances are set before the run.

A. table_reading: the scanner table (trilinear on the record grid) against the direct integral on the 1 nm grid for 4000 random records
   inside the grid, per stock. Tolerance: p99 of |difference| <= 0.002 density, largest <= 0.01 density.
B. grey_at_aim: an 18 % grey under the balance light of the stock gives 0.18 in each channel (rendering defaults: black 1, auto off).
   Tolerance 1e-9 relative.
C. base_is_black: the film base (density 0) gives 0 in each channel with black 1. Tolerance 1e-12.
D. auto_on_balance_grey: a uniform frame of the balance grey gives an auto shift of 0. Tolerance 1e-9 log10.
E. auto_share: a uniform grey frame under T3200 on a daylight stock (and D65 on a tungsten stock): after the auto shift, the cast along the
   light axis is (1 - strength) of the cast before, and across it (1 - strength * 0.5). Tolerance 1e-6 log10.
F. rendering_keeps_table: a change of a rendering control (keys, auto, black) returns the same scan object (no new table).
Recorded with no limit (stock character, not a fault): the neutral ramp of each stock under its balance light from -4 to +4 stops, as the
spread of the three channels in stops (max - min of log2 of the positive).
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402
import negative_scan as ns  # noqa: E402

OUT = REPO_ROOT / "results" / "p14_negative_scan" / "checks.json"
STOCKS = ("kodak_portra_400", "kodak_gold_200", "kodak_ektar_100", "fuji_c200", "kodak_5207", "kodak_5219")


def balance_settings(stock: str, **extra) -> mp.RenderSettings:
    light = "tungsten" if mp.CATALOG["negatives"][stock].get("exposure_kelvin", 5500) < 4500 else "daylight"
    return mp.RenderSettings(method="negative_scan", negative=stock, scene_light=light, **extra)


def grey_frame(model: ns.NegativeScanPreview, light: str) -> np.ndarray:
    return np.broadcast_to(model.read.grey_density(light), (32, 32, 3)).copy()


def main() -> int:
    rng = np.random.default_rng(14)
    pipeline = mp.Pipeline()
    results: dict = {"stocks": {}}
    passed = True
    for stock in STOCKS:
        settings = balance_settings(stock)
        model = pipeline.negative_scan_model(settings)
        scan = model.read.scan
        grid = model.negative.density_grid
        record = np.stack([rng.uniform(g[0], g[-1], 4000) for g in grid], axis=-1)
        amounts, _ = model.negative.table_amounts(record)
        direct = scan.apd(model.negative.film.negative_spectral_density(amounts))
        diff = np.abs(scan.table_apd(record) - direct)
        a = {"p99": float(np.percentile(diff, 99)), "max": float(diff.max())}
        a["pass"] = a["p99"] <= 0.002 and a["max"] <= 0.01

        grey = model.positive(model.read.grey_density(model.balance_light)[None], spatial=False)[0][0]
        b = {"positive": grey.tolist(), "pass": bool(np.all(np.abs(grey / 0.18 - 1.0) <= 1e-9))}
        base = model.positive(np.zeros((1, 3)), spatial=False)[0][0]
        c = {"positive": base.tolist(), "pass": bool(np.all(np.abs(base) <= 1e-12))}

        auto = pipeline.negative_scan_model(replace(settings, neg_scan_auto="neutral"))
        shift, _ = ns.auto_colour_shift(auto.positive_log(grey_frame(auto, auto.balance_light)), auto.light_axis, "neutral", 0.8, 0.0)
        d = {"shift": shift.tolist(), "pass": bool(np.all(np.abs(shift) <= 1e-9))}

        other = "D65" if auto.balance_light == "T3200" else "T3200"
        x = auto.positive_log(grey_frame(auto, other))
        shift, _ = ns.auto_colour_shift(x, auto.light_axis, "neutral", 0.8, 0.0)
        axis = auto.light_axis - auto.light_axis.mean()
        axis = axis / np.linalg.norm(axis)
        before = x[0, 0] - x[0, 0].mean()
        after = before + shift - shift.mean()
        along_before, along_after = before @ axis, after @ axis
        across_before, across_after = before - along_before * axis, after - along_after * axis
        e = {"light": other, "along_before": float(along_before), "along_after": float(along_after), "across_before": across_before.tolist(), "across_after": across_after.tolist()}
        e["pass"] = bool(abs(along_after - 0.2 * along_before) <= 1e-6 and np.all(np.abs(across_after - 0.6 * across_before) <= 1e-6))

        stops = np.arange(-4.0, 4.01, 1.0)
        ramp = np.array([model.read.grey_density(model.balance_light, 0.18 * 2.0 ** s) for s in stops])
        positive = pipeline.negative_scan_model(settings).positive(ramp, spatial=False)[0]
        log2 = np.log2(np.maximum(positive, 1e-12))
        spread = (log2.max(axis=1) - log2.min(axis=1)).round(3).tolist()
        same = pipeline.negative_scan_model(replace(settings, neg_scan_cyan=0.05, neg_scan_auto="warm", neg_scan_black=0.5)) is model
        f = {"pass": bool(same)}

        checks = {"A_table_reading": a, "B_grey_at_aim": b, "C_base_is_black": c, "D_auto_on_balance_grey": d, "E_auto_share": e, "F_rendering_keeps_table": f}
        results["stocks"][stock] = {**checks, "ramp_stops": stops.tolist(), "ramp_channel_spread_stops": spread}
        ok = all(v["pass"] for v in checks.values())
        passed &= ok
        print(stock, "pass" if ok else "FAIL", {k: v["pass"] for k, v in checks.items()}, "table p99", round(a["p99"], 5), "max", round(a["max"], 5), "spread", spread, flush=True)
    for medium in ("photo", "cine"):
        stock = "kodak_portra_400" if medium == "photo" else "kodak_5207"
        m = pipeline.negative_scan_medium(balance_settings(stock))
        results[f"medium_{medium}"] = {"gamma": m["gamma"].round(5).tolist(), "stock_gamma": m["stock_gamma"], "film_primaries_matrix": m["matrix"].round(5).tolist()}
    results["scanner"] = {"centres_nm": [650, 545, 450], "width_nm": 40, "light": "halogen (Planckian 3200 K)"}
    results["pass"] = bool(passed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("all pass" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
