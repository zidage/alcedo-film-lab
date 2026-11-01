"""Numeric checks of the scanned-negative path and of the scene mixtures.

Input: aces_scan.py, the P2 library, no photo. Output: results/p3_scan_and_scene/scan_checks.json.
Step: P3, ROADMAP section 8. Limits set before the first run:
- encoding: APD above D-min 0 and 1 give code values (95, 95, 95) and (595, 555, 570), error <= 1e-9;
- the ported ADX10 to ACES transform against the OpenColorIO built-in ADX10_to_ACES2065-1: relative error <= 1e-3 where |ACES| > 1e-3;
- code value 445 gives ACES 0.18, relative error <= 1e-4;
- APD table against the direct stages, 2,000 random Status M densities: |error| p95 <= 0.002 density (1 code value), max <= 0.01;
- neutral ramp: ADX10 through the table against the direct stages, max error <= 1 code value; finite values;
- with rule 'adx_lad_aim', timing 1: an 18 % grey under the scene light is at 445 +- 0.5 in each channel;
- scene mixture: the layer exposure of a mixture equals the weighted sum of the layer exposures, relative error <= 1e-9;
- direct inversion, timing 1: an 18 % grey shows the display value 0.22 +- 0.002 in each channel; on a neutral ramp the display luminance does not fall and the values are finite.
Information without a limit: the neutral ramp, grey without the offset, share of the red responsivity above 700 nm, the output
of each transform at ACES 0.18, the effect of another density rule outside the published range.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402

RESULT = Path(__file__).resolve().parents[3] / "results" / "p3_scan_and_scene" / "scan_checks.json"
STOCKS = ["portra400_endura", "5207_2383", "5219_2383"]
TESTED_LIGHT = {"portra400_endura": "E_ref", "5207_2383": "D55", "5219_2383": "D55"}
RAMP = 0.18 * 2.0 ** np.arange(-6.0, 7.0)


def options(stock: str, **extra) -> fp.FilmOptions:
    return fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})


def check_transforms() -> dict:
    rng = np.random.default_rng(20261030)
    code = np.vstack([np.outer(np.linspace(0.0, 1023.0, 1024), np.ones(3)), rng.uniform(0.0, 1023.0, (20000, 3))])
    ported = scan.adx10_to_aces(code)
    reference = scan.apply_processor(scan.builtin_processor("ADX10_to_ACES2065-1"), code / 1023.0).astype(np.float64)
    above = np.abs(reference) > 1e-3
    relative = np.abs(ported[above] / reference[above] - 1.0)
    grey = scan.adx10_to_aces(np.full((1, 3), 445.0))[0]
    encoded = scan.adx10_from_apd(np.array([[0.1, 0.2, 0.3], [1.1, 1.2, 1.3]]), np.array([0.1, 0.2, 0.3]))
    aces_grey = np.full((1, 3), 0.18)
    output = {}
    for name, style in scan.OUTPUT_TRANSFORMS.items():
        xyz = scan.apply_processor(scan.builtin_processor(style), aces_grey)[0]
        srgb = scan.apply_processor(scan.builtin_processor(style, scan.DISPLAY_TRANSFORM), aces_grey)[0]
        output[name] = {"style": style, "luminance_share_of_peak_at_aces_0.18": float(xyz[1]), "srgb_at_aces_0.18": srgb.round(4).tolist()}
    return {"encoding": {"values": encoded.tolist(), "max_error": float(np.abs(encoded - np.array([[95.0] * 3, [595.0, 555.0, 570.0]])).max()), "limit": 1e-9},
            "port_against_ocio": {"samples": int(above.sum()), "relative_error_max": float(relative.max()), "limit": 1e-3},
            "code_445": {"aces": grey.tolist(), "relative_error_max": float(np.abs(grey / 0.18 - 1.0).max()), "limit": 1e-4},
            "output_transforms": output}


def check_stock(stock: str) -> dict:
    light = TESTED_LIGHT[stock]
    extra = {"scene_light": light} if light != "E_ref" else {}
    s = scan.ScanPreview(options(stock, **extra), timing=1.0)
    n = s.negative
    rng = np.random.default_rng(20261030)
    density = np.stack([rng.uniform(g[0], g[-1], 2000) for g in n.density_grid], axis=1)
    direct, residual = s.direct_apd(density)
    error = np.abs(direct - s.table_apd(density))
    q = n.layer_gain * n.c.layer_exposure(RAMP[:, None] * n.light(n.options.scene_light)[None, :])
    status_m, _ = n.negative_density(q)
    ramp_direct = scan.adx10_from_apd(s.direct_apd(status_m)[0], s.apd_dmin)
    ramp_table = scan.adx10_from_apd(s.table_apd(status_m), s.apd_dmin)
    weight = s.apd_weights[0]
    wavelengths = n.film.grid.wavelengths[s.apd_nodes]
    transmission = 10.0 ** -n.film.negative_midscale[s.apd_nodes]
    return {"scene_light": n.options.scene_light, "apd_dmin": s.apd_dmin.round(4).tolist(),
            "table_against_stages": {"p95": float(np.percentile(error, 95)), "max": float(error.max()), "limit_p95": 0.002, "limit_max": 0.01,
                                     "samples_with_unreached_dye_solve": int((residual > 1e-4).sum())},
            "ramp_scene_values": RAMP.round(5).tolist(), "ramp_adx10_without_offset": ramp_table.round(1).tolist(),
            "ramp_table_against_stages_max_code_values": float(np.abs(ramp_table - ramp_direct).max()), "ramp_finite": bool(np.isfinite(ramp_direct).all()),
            "ramp_aces_with_offset": scan.adx10_to_aces(np.clip(ramp_table + s.offset, 0.0, 1023.0)).round(4).tolist(),
            "offset_code_values": s.offset.round(1).tolist(),
            "grey_with_offset": (s.grey_adx(n.options.scene_light) + s.offset).round(2).tolist(), "grey_balance_light_without_offset": s.grey_adx(n.options.balance_light).round(1).tolist(),
            "grey_scene_light_without_offset": s.grey_adx(n.options.scene_light).round(1).tolist(),
            "red_signal_share_above_700_nm_midscale": float((weight * transmission)[wavelengths > 700.0].sum() / (weight * transmission).sum())}


def check_mixture() -> dict:
    n = fp.FilmPreview(options("5219_2383"))
    rho = n._load_reflectance_table()[::4001].astype(np.float64)
    out = {}
    for name, parts in fp.SCENE_PRESETS.items():
        if abs(sum(w for _, w in parts) - 1.0) > 1e-12:
            raise ValueError(f"{name}: the weights do not sum to 1")
        mixture = n.c.layer_exposure(rho * n.light(name)[None, :])
        parts_sum = sum(w * n.c.layer_exposure(rho * n.light(light)[None, :]) for light, w in parts)
        positive = parts_sum > 0
        out[name] = {"parts": parts, "relative_error_max": float(np.abs(mixture[positive] / parts_sum[positive] - 1.0).max()), "limit": 1e-9,
                     "y_of_mixture": float(n.c.xyz(n.light(name))[1])}
    return out


def check_direct(stock: str) -> dict:
    light = TESTED_LIGHT[stock]
    d = scan.DirectInversionPreview(options(stock, **({"scene_light": light} if light != "E_ref" else {})), timing=1.0)
    srgb, _ = d.render(np.full((1, 1, 3), 0.18, dtype=np.float32))
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)[0, 0]
    ramp, _ = d.render(np.outer(0.18 * 2.0 ** np.linspace(-8.0, 8.0, 65), np.ones(3)).astype(np.float32))
    ramp_linear = np.where(ramp <= 0.04045, ramp / 12.92, ((ramp + 0.055) / 1.055) ** 2.4)
    luminance = ramp_linear @ np.array([0.2126, 0.7152, 0.0722])
    return {"apd_slope": d.gamma.round(3).tolist(), "grey_display_linear": linear.round(4).tolist(), "ramp_finite": bool(np.isfinite(ramp).all()), "ramp_largest_fall": float(np.maximum(0.0, -np.diff(luminance)).max()),
            "ramp_srgb_max_channel_spread": float((ramp.max(axis=-1) - ramp.min(axis=-1)).max())}


def tail_sensitivity(stock: str) -> dict:
    # The negative density outside the published range is a rule (P0). A second rule shows how much the record depends on it.
    a = scan.ScanPreview(options(stock), timing=1.0)
    b = scan.ScanPreview(options(stock, density_outside="hold"), timing=1.0)
    return {"grey_adx10_gaussian_tail": a.grey_adx(a.negative.options.balance_light).round(1).tolist(), "grey_adx10_hold": b.grey_adx(b.negative.options.balance_light).round(1).tolist(),
            "apd_dmin_gaussian_tail": a.apd_dmin.round(3).tolist(), "apd_dmin_hold": b.apd_dmin.round(3).tolist()}


def main() -> int:
    result = {"transforms": check_transforms(), "stocks": {k: check_stock(k) for k in STOCKS}, "scene_mixtures": check_mixture(),
              "density_rule_outside_published_range": {k: tail_sensitivity(k) for k in STOCKS}, "direct_inversion": {k: check_direct(k) for k in STOCKS}}
    t = result["transforms"]
    passed = {"encoding": t["encoding"]["max_error"] <= 1e-9, "port_against_ocio": t["port_against_ocio"]["relative_error_max"] <= 1e-3, "code_445": t["code_445"]["relative_error_max"] <= 1e-4,
              "scene_mixture": all(v["relative_error_max"] <= 1e-9 for v in result["scene_mixtures"].values())}
    for k, v in result["stocks"].items():
        passed[f"{k}_table"] = v["table_against_stages"]["p95"] <= 0.002 and v["table_against_stages"]["max"] <= 0.01
        passed[f"{k}_ramp"] = v["ramp_finite"] and v["ramp_table_against_stages_max_code_values"] <= 1.0
        passed[f"{k}_grey"] = bool(np.abs(np.array(v["grey_with_offset"]) - 445.0).max() <= 0.5)
    for k, v in result["direct_inversion"].items():
        passed[f"{k}_direct"] = bool(np.abs(np.array(v["grey_display_linear"]) - 0.22).max() <= 0.002) and v["ramp_finite"] and v["ramp_largest_fall"] == 0.0
    result["pass"] = passed
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["pass"], indent=1))
    keys = ("apd_dmin", "table_against_stages", "ramp_table_against_stages_max_code_values", "offset_code_values", "grey_balance_light_without_offset", "grey_scene_light_without_offset", "red_signal_share_above_700_nm_midscale", "ramp_aces_with_offset")
    print(json.dumps({k: {x: v[x] for x in keys} for k, v in result["stocks"].items()}))
    print(json.dumps(result["transforms"]))
    print(json.dumps(result["density_rule_outside_published_range"]))
    print(json.dumps(result["direct_inversion"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
