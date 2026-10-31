"""W2, W3, W4: numeric checks of the development inhibition, the density timing, and the layer spread.

Input: the P2 and P3 libraries, no photo. Output: results/p4_physical_film_response/film_response.json.
Step: P4, README section 8. Limits set before the first run (P4 report section 4):
- W2: the neutral curve against the published Status M curve, inside the published domain: largest error <= 0.02 density;
- W2: a saturated colour ramp from -3 to +3 stops: largest fall of any Status M record <= 0.001 density;
- W2: the fixed point on an image with INHIBITION_STEPS_IMAGE steps against the array form with no image plane: largest difference <= 0.002 in dye amount on a flat colour field;
- W3: the display of a mid grey under the balance light, per_record_slope False: neutral within 0.002 linear per channel;
- W4: each kernel preserves the mean of a test image within 1e-4 relative, and a flat field changes by at most 1e-4.
Information without a limit: the crossover of each stock (a*, b* of the neutral ramp from -5 to +5 stops), and the chroma against exposure of each chart colour with and without rule 'development_inhibition'.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from trace_colour_error import chart_ap1  # noqa: E402

RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "film_response.json"
STOCKS = {"5207": ("5207_2383", "D55"), "5219": ("5219_2383", "D55"), "portra": ("portra400_endura", "E_ref")}
BALANCE_LIGHT = {"5207": "D55", "5219": "T3200", "portra": "E_ref"}
D65 = np.array([0.95047, 1.0, 1.08883])
REC709_TO_XYZ = np.linalg.inv(fp.XYZ_TO_REC709)


def options(stock: str, light: str, **extra) -> fp.FilmOptions:
    return fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **fp.P4_PHYSICAL[stock], "scene_light": light, **extra})


def srgb_to_lab(srgb: np.ndarray) -> np.ndarray:
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    t = (linear @ REC709_TO_XYZ.T) / D65
    f = np.where(t > (6.0 / 29.0) ** 3, np.cbrt(t), t / (3.0 * (6.0 / 29.0) ** 2) + 4.0 / 29.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def check_inhibition(key: str, stock: str, light: str) -> dict:
    n = fp.FilmPreview(options(stock, light))
    c = n.c
    f = n.film
    # Neutral against the published curve. Domain: the log H range that all three published curves cover.
    log_h = np.linspace(max(s.log_h[0] for s in n.status_curves), min(s.log_h[-1] for s in n.status_curves), 201)
    q = 10.0 ** (log_h[:, None] - f.negative_criterion_log_h)
    status = n.record_to_status_m(n.negative_density(q)[0])
    wanted = np.stack([np.interp(log_h, s.log_h, s.density) for s in n.status_curves], axis=1)
    neutral_error = float(np.abs(status - wanted).max())
    # Saturated colours in AP1: one primary high, the others at 2 % and 25 %.
    stops = np.linspace(-3.0, 3.0, 121)
    falls = {}
    for name, colour in {"red": (1.0, 0.05, 0.02), "green": (0.05, 1.0, 0.02), "blue": (0.02, 0.05, 1.0), "orange": (1.0, 0.45, 0.02), "cyan": (0.02, 0.7, 1.0), "magenta": (1.0, 0.03, 0.8)}.items():
        ramp = 0.18 * 2.0 ** stops[:, None] * np.array(colour)
        record = n.negative_image(ramp[None].astype(np.float32))[0][0].astype(np.float64)
        falls[name] = float(np.maximum(0.0, -np.diff(n.record_to_status_m(record), axis=0)).max())
    # Fixed point on an image against the array form, on flat colour fields.
    field = np.array([[0.4, 0.1, 0.05], [0.05, 0.3, 0.1], [0.05, 0.1, 0.5], [0.18, 0.18, 0.18]])
    difference = 0.0
    for colour in field:
        image = np.full((32, 32, 3), colour, dtype=np.float32)
        on_image = n.negative_image(image)[0][16, 16].astype(np.float64)
        point = n.negative_image(image[:1, :1])[0][0, 0].astype(np.float64)
        difference = max(difference, float(np.abs(on_image - point).max()))
    # Chroma against exposure of the chart colours, through the direct inversion.
    without = replace(n.options, inhibition_total=(0.0, 0.0, 0.0))
    with_rule, without_rule = scan.DirectInversionPreview(n.options, timing=1.0), scan.DirectInversionPreview(without, timing=1.0)
    colours = chart_ap1(c)
    names = list(colours)
    stops_chart = np.arange(-3.0, 3.5, 1.0)
    grid = np.stack([colours[k] * 2.0 ** s for k in names for s in stops_chart]).reshape(len(names), len(stops_chart), 3).astype(np.float32)
    chroma_on = np.hypot(*np.moveaxis(srgb_to_lab(with_rule.render(grid)[0])[..., 1:], -1, 0))
    chroma_off = np.hypot(*np.moveaxis(srgb_to_lab(without_rule.render(grid)[0])[..., 1:], -1, 0))
    return {"neutral_largest_error": neutral_error, "neutral_limit": 0.02, "largest_fall": falls, "fall_limit": 0.001, "image_against_point_largest_difference": difference, "image_against_point_limit": 0.002,
            "k": n.inhibition["k"].round(4).tolist(), "chart_stops": stops_chart.tolist(),
            "chart_chroma": {name: {"with": chroma_on[i].round(1).tolist(), "without": chroma_off[i].round(1).tolist()} for i, name in enumerate(names)}}


def check_crossover(key: str, stock: str, light: str) -> dict:
    out = {}
    balance = BALANCE_LIGHT[key]
    stops = np.arange(-5.0, 5.5, 1.0)
    ramp = np.outer(0.18 * 2.0 ** stops, np.ones(3)).astype(np.float32)
    grey = np.full((1, 1, 3), 0.18, dtype=np.float32)
    for name, slope in (("per record slope", True), ("density timing", False)):
        d = scan.DirectInversionPreview(options(stock, balance), timing=1.0, per_record_slope=slope)
        srgb = d.render(ramp)[0].astype(np.float64)
        lab = srgb_to_lab(srgb)
        out[name] = {"a": lab[:, 1].round(2).tolist(), "b": lab[:, 2].round(2).tolist(), "apd_slope": d.gamma.round(3).tolist()}
        shown = d.render(grey)[0][0, 0].astype(np.float64)
        linear = np.where(shown <= 0.04045, shown / 12.92, ((shown + 0.055) / 1.055) ** 2.4)
        out[name]["grey_display_linear"] = linear.round(4).tolist()
        out[name]["grey_channel_spread"] = float(np.ptp(linear))
    return {"stops": stops.tolist(), "balance_light": balance, **out}


def check_spread(key: str, stock: str, light: str) -> dict:
    n = fp.FilmPreview(options(stock, light))
    rng = np.random.default_rng(20261030)
    image = (0.05 + np.abs(np.cumsum(np.cumsum(rng.normal(size=(512, 768, 3)), axis=0), axis=1))).astype(np.float32)
    image /= image.max()
    pixel = 4.5  # um per pixel: the full-resolution review
    spread = n._spread_layers(image, pixel)
    flat = np.full((64, 64, 3), 0.25, dtype=np.float32)
    return {"mean_relative_error": float(np.abs(spread.mean(axis=(0, 1)) / image.mean(axis=(0, 1)) - 1.0).max()), "flat_largest_change": float(np.abs(n._spread_layers(flat, pixel) - flat).max()), "limit": 1e-4}


def main() -> int:
    result = {"inhibition": {}, "crossover": {}, "spread": {}}
    for key, (stock, light) in STOCKS.items():
        result["inhibition"][key] = check_inhibition(key, stock, light)
        result["crossover"][key] = check_crossover(key, stock, light)
        result["spread"][key] = check_spread(key, stock, light)
    passed = {}
    for key in STOCKS:
        i, x, s = result["inhibition"][key], result["crossover"][key], result["spread"][key]
        passed[key] = {"w2_neutral": i["neutral_largest_error"] <= 0.02, "w2_no_fall": max(i["largest_fall"].values()) <= 0.001, "w2_image_against_point": i["image_against_point_largest_difference"] <= 0.002,
                       "w3_grey": x["density timing"]["grey_channel_spread"] <= 0.002, "w4_mean": s["mean_relative_error"] <= 1e-4, "w4_flat": s["flat_largest_change"] <= 1e-4}
    result["pass"] = passed
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(passed, indent=0))
    for key in STOCKS:
        i = result["inhibition"][key]
        print(key, "neutral", round(i["neutral_largest_error"], 5), "falls", {k: round(v, 5) for k, v in i["largest_fall"].items()}, "image vs point", round(i["image_against_point_largest_difference"], 5))
        print("  spread", result["spread"][key])
        for name in ("per record slope", "density timing"):
            x = result["crossover"][key][name]
            print("  ", name, "a", x["a"], "\n     b", x["b"], "grey spread", round(x["grey_channel_spread"], 5), "slope", x["apd_slope"])
        print("  chroma blue sky with/without", i["chart_chroma"]["blue sky"], "\n  orange", i["chart_chroma"]["orange"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
