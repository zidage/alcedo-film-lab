"""Numeric checks of the five P5 stocks on the Endura print, and the same measurements on the accepted Portra 400 as a comparison.

Input: the P2 to P4 libraries and the P5 profiles, no photo. Output: results/p5_film_and_print_combinations/stock_chain.json.
Step: P5, README section 8, decision U34. Limits set before the first run, the same as P4 (P4 report sections 4 and 5):
- the neutral curve against the published Status M curve, inside the published domain: largest error <= 0.02 density;
- a saturated colour ramp from -3 to +3 stops: largest fall of any Status M record <= 0.001 density;
- the fixed point on an image against the array form on flat colour fields: largest difference <= 0.002 in dye amount;
- each spread kernel preserves the mean of a test image within 1e-4 relative, and a flat field changes by at most 1e-4;
- the hue sweep through the product grade: largest second difference <= 0.02. P4 shows that this limit does not see a band over tens of columns (P4-O13).
Information without a limit: a* and b* of the neutral ramp from -5 to +5 stops on the print; L* and C* of the chart colours on the print; the residual of the dye solve; the counts of the print table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
from aces_scan import fp  # noqa: E402
from check_film_response import srgb_to_lab  # noqa: E402
from render_scanner_light_review import hue_sweep  # noqa: E402
from trace_colour_error import chart_ap1  # noqa: E402

RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "stock_chain.json"
STOCK_KEYS = ("portra400_endura", "portra160_endura", "portra800_endura", "ektar100_endura", "gold200_endura", "c200_endura")
RAMP_COLOURS = {"red": (1.0, 0.05, 0.02), "green": (0.05, 1.0, 0.02), "blue": (0.02, 0.05, 1.0), "orange": (1.0, 0.45, 0.02), "cyan": (0.02, 0.7, 1.0), "magenta": (1.0, 0.03, 0.8)}


def stock_options(key: str, **extra) -> fp.FilmOptions:
    physical = fp.P4_PHYSICAL[key] if key in fp.P4_PHYSICAL else fp.P5_PHYSICAL[key]
    return fp.FilmOptions(**{**fp.STOCKS[key], **fp.DARKROOM, **physical, **extra})


def check_stock(key: str) -> dict:
    n = fp.FilmPreview(stock_options(key))
    c, f = n.c, n.film
    log_h = np.linspace(max(s.log_h[0] for s in n.status_curves), min(s.log_h[-1] for s in n.status_curves), 201)
    q = 10.0 ** (log_h[:, None] - f.negative_criterion_log_h)
    status = n.record_to_status_m(n.negative_density(q)[0])
    wanted = np.stack([np.interp(log_h, s.log_h, s.density) for s in n.status_curves], axis=1)
    stops = np.linspace(-3.0, 3.0, 121)
    falls = {}
    for name, colour in RAMP_COLOURS.items():
        ramp = 0.18 * 2.0 ** stops[:, None] * np.array(colour)
        record = n.negative_image(ramp[None].astype(np.float32))[0][0].astype(np.float64)
        falls[name] = float(np.maximum(0.0, -np.diff(n.record_to_status_m(record), axis=0)).max())
    difference = 0.0
    for colour in ((0.4, 0.1, 0.05), (0.05, 0.3, 0.1), (0.05, 0.1, 0.5), (0.18, 0.18, 0.18)):
        image = np.full((32, 32, 3), colour, dtype=np.float32)
        difference = max(difference, float(np.abs(n.negative_image(image)[0][16, 16].astype(np.float64) - n.negative_image(image[:1, :1])[0][0, 0].astype(np.float64)).max()))
    rng = np.random.default_rng(20261030)
    pattern = (0.05 + np.abs(np.cumsum(np.cumsum(rng.normal(size=(256, 384, 3)), axis=0), axis=1))).astype(np.float32)
    pattern /= pattern.max()
    # A stock with no spread has no kernel to check (Gold 200: no modulation transfer chart).
    has_spread = any(n.options.layer_spread_um)
    spread = n._spread_layers(pattern, 4.5) if has_spread else pattern
    flat = np.full((64, 64, 3), 0.25, dtype=np.float32)
    fine_stops = np.arange(-2.0, 2.01, 0.25)
    fine = srgb_to_lab(n.render(np.outer(0.18 * 2.0 ** fine_stops, np.ones(3)).astype(np.float32)[None])[0][0].astype(np.float64))
    stops_ramp = np.arange(-5.0, 5.5, 1.0)
    neutral = np.outer(0.18 * 2.0 ** stops_ramp, np.ones(3)).astype(np.float32)[None]
    lab = srgb_to_lab(n.render(neutral)[0][0].astype(np.float64))
    colours = chart_ap1(c)
    chart = np.stack(list(colours.values())).astype(np.float32)[None]
    chart_lab = srgb_to_lab(n.render(chart)[0][0].astype(np.float64))
    sweep = fp.product_input(hue_sweep(c).astype(np.float32), c)
    second = float(np.abs(np.diff(n.render(sweep)[0].astype(np.float64), 2, axis=1)).max())
    return {"neutral_largest_error": round(float(np.abs(status - wanted).max()), 5), "largest_fall": max(falls.values()), "image_against_point": difference,
            "spread_mean_error": float(np.abs(spread.mean(axis=(0, 1)) / pattern.mean(axis=(0, 1)) - 1.0).max()), "spread_flat_change": float(np.abs(n._spread_layers(flat, 4.5) - flat).max()) if has_spread else 0.0, "has_spread": has_spread,
            "fine_stops": fine_stops.tolist(), "fine_a": fine[:, 1].round(2).tolist(), "fine_b": fine[:, 2].round(2).tolist(),
            "sweep_second_difference": round(second, 4), "stops": stops_ramp.tolist(), "neutral_L": lab[:, 0].round(1).tolist(), "neutral_a": lab[:, 1].round(1).tolist(), "neutral_b": lab[:, 2].round(1).tolist(),
            "chart_lab": {name: chart_lab[i].round(1).tolist() for i, name in enumerate(colours)}, "chart_mean_chroma": round(float(np.hypot(chart_lab[:, 1], chart_lab[:, 2]).mean()), 1),
            "dye_solve": n.dye_curve_info, "print_table_counts": n.table_counts, "layer_gain_log10": np.log10(n.layer_gain).round(3).tolist()}


def main() -> int:
    result = {"limits": {"neutral": 0.02, "fall": 0.001, "image_against_point": 0.002, "spread": 1e-4, "sweep": 0.02}, "stocks": {}, "pass": {}}
    for key in STOCK_KEYS:
        r = check_stock(key)
        result["stocks"][key] = r
        result["pass"][key] = {"neutral": r["neutral_largest_error"] <= 0.02, "no_fall": r["largest_fall"] <= 0.001, "image_against_point": r["image_against_point"] <= 0.002, "spread": r["spread_mean_error"] <= 1e-4 and r["spread_flat_change"] <= 1e-4, "sweep": r["sweep_second_difference"] <= 0.02}
        print(key, json.dumps(result["pass"][key]), {k: r[k] for k in ("neutral_largest_error", "largest_fall", "image_against_point", "spread_mean_error", "sweep_second_difference", "chart_mean_chroma", "layer_gain_log10")}, flush=True)
        print("  a", r["neutral_a"], "\n  b", r["neutral_b"], "\n  L", r["neutral_L"], "\n  solve", r["dye_solve"], "\n  table", r["print_table_counts"], flush=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
