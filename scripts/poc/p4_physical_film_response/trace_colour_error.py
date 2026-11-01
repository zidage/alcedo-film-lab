"""W1: trace the colour error of the direct inversion through the dye chain, for each dye model.

Input: aces_scan.py and the P2 library, no photo. Output: results/p4_physical_film_response/colour_trace.json.
Step: P4, ROADMAP section 8, work item W1. Limits set before the first run (P4 report section 4):
- for each case, the coefficient from AP1 blue to the red record: the sum of the stages equals the total of an end-to-end fit within 0.01;
- the base and a neutral density through the dye model agree with the Status M reconstruction: p95 error <= 0.01 density, over the neutral ramp.
A 3x3 matrix in this script is a comparison measurement of the chain. It is not a candidate transform.

Stages. Each one gives a per-channel exposure estimate, as a matrix fit from AP1 on colours inside Rec. 709 (the method of P3 section 11.1):
- rec709: the true matrix from AP1 to linear Rec. 709 (comparison);
- layer: the layer exposures of the reconstructed spectrum;
- curve: the record of the curve stage, read back through the neutral slope of each record;
- status_m: the Status M of the negative, read back in the same way;
- apd: the APD record, read back in the same way. This is the exposure that the direct inversion shows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_scanner_light_review import CHART  # noqa: E402

RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "colour_trace.json"
RAMP_STOPS = np.linspace(-3.32, 3.32, 21)  # 1 log10 on each side of the grey, as the slope of the direct inversion
NARROW_BANDS_NM = np.arange(420.0, 701.0, 20.0)
CASES = {
    "5207 band_split status_m": ("5207_2383", dict(negative_dye_basis="band_split", negative_record="status_m")),
    "5207 published status_m": ("5207_2383", dict(negative_dye_basis="published", negative_record="status_m")),
    "5207 published dye_amount": ("5207_2383", dict(negative_dye_basis="published", negative_record="dye_amount")),
    "5207 published dye_amount light_spectra": ("5207_2383", dict(negative_dye_basis="published", negative_record="dye_amount", light_spectra=True)),
    "5219 band_split status_m": ("5219_2383", dict(negative_dye_basis="band_split", negative_record="status_m")),
    "5219 published dye_amount": ("5219_2383", dict(negative_dye_basis="published", negative_record="dye_amount")),
    "5219 published dye_amount light_spectra": ("5219_2383", dict(negative_dye_basis="published", negative_record="dye_amount", light_spectra=True)),
    "portra band_split status_m": ("portra400_endura", dict(negative_dye_basis="band_split", negative_record="status_m")),
    "portra band_split dye_amount": ("portra400_endura", dict(negative_dye_basis="band_split", negative_record="dye_amount")),
    "portra band_split dye_amount light_spectra": ("portra400_endura", dict(negative_dye_basis="band_split", negative_record="dye_amount", light_spectra=True)),
}
TESTED_LIGHT = {"5207_2383": "D55", "5219_2383": "T3200", "portra400_endura": "E_ref"}


def chart_ap1(c) -> dict:
    """AP1 of the chart colours, by Lab under D50 through Bradford to the ACES white. The value is a colour and not a measured spectrum."""
    d50 = np.array([0.96422, 1.0, 0.82521])
    white = c.ap1_to_xyz @ np.ones(3)
    out = {}
    for name, (l, a, b) in CHART.items():
        fy = (l + 16.0) / 116.0
        f = np.array([fy + a / 500.0, fy, fy - b / 200.0])
        xyz = d50 * np.where(f > 6.0 / 29.0, f ** 3, 3.0 * (6.0 / 29.0) ** 2 * (f - 4.0 / 29.0))
        out[name] = c.xyz_to_ap1 @ fp.bradford_matrix(d50, white) @ xyz
    return out


def rgb_hue_degrees(x: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(np.sqrt(3.0) * (x[..., 1] - x[..., 2]), 2.0 * x[..., 0] - x[..., 1] - x[..., 2]))


def read_back(values: np.ndarray, neutral: np.ndarray, grey: np.ndarray) -> np.ndarray:
    """Exposure estimate per channel: the distance from the grey, through the slope of the neutral ramp."""
    slope = np.array([np.polyfit(RAMP_STOPS * np.log10(2.0), neutral[:, k], 1)[0] for k in range(3)])
    return 0.18 * 10.0 ** ((values - grey) / slope)


def stages(d: scan.DirectInversionPreview, ap1: np.ndarray) -> dict[str, np.ndarray]:
    """Exposure estimate at each stage for colours (N, 3)."""
    n = d.negative
    ramp = np.outer(0.18 * 2.0 ** RAMP_STOPS, np.ones(3)).astype(np.float32)
    grey = np.full((1, 1, 3), 0.18, dtype=np.float32)

    def measure(image: np.ndarray) -> dict[str, np.ndarray]:
        q = n.layer_exposure(image.reshape(-1, 3).astype(np.float64))[0]
        record = n.negative_image(image.reshape(1, -1, 3).astype(np.float32))[0][0].astype(np.float64)
        status = n.record_to_status_m(record)
        return {"layer": np.log10(np.maximum(q, 1e-30)), "curve": record, "status_m": status, "apd": d.table_apd(record)}

    colours, neutral, centre = measure(ap1), measure(ramp), measure(grey)
    out = {k: read_back(colours[k], neutral[k], centre[k][0]) for k in ("curve", "status_m", "apd")}
    out["layer"] = 0.18 * 10.0 ** (colours["layer"] - centre["layer"][0])
    return out


def trace_case(stock: str, extra: dict) -> dict:
    options = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, "scene_light": TESTED_LIGHT[stock], **extra})
    d = scan.DirectInversionPreview(options, timing=1.0)
    n = d.negative
    c = n.c
    rec709 = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    rng = np.random.default_rng(20261030)
    display = rng.uniform(0.04, 0.7, (4000, 3))
    ap1 = display @ np.linalg.inv(rec709).T
    estimates = stages(d, ap1)
    order = ["layer", "curve", "status_m", "apd"]
    matrices = {"rec709": rec709}
    for name in order:
        matrices[name] = np.linalg.lstsq(ap1, estimates[name], rcond=None)[0].T
    coefficient = {k: float(m[0, 2]) for k, m in matrices.items()}
    steps = {f"{a} to {b}": coefficient[b] - coefficient[a] for a, b in zip(["rec709", *order], order)}
    # End-to-end fit from the render of the direct inversion, by the inverse of its display curve. It does not use the stages above.
    srgb = d.render(ap1[None].astype(np.float32))[0][0].astype(np.float64)
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    inside = ((linear > 0.02) & (linear < 0.98)).all(axis=1)
    y = np.clip(linear[inside], 1e-6, 1.0 - 1e-6)
    shown = 0.18 * (y * (1.0 / d.display_grey - 1.0) / (1.0 - y)) ** (1.0 / d.contrast)
    total = float(np.linalg.lstsq(ap1[inside], shown, rcond=None)[0].T[0, 2])
    colours = chart_ap1(c)
    names = list(colours)
    chart_stages = stages(d, np.stack([colours[k] for k in names]))
    chart_rec709 = np.stack([colours[k] for k in names]) @ rec709.T
    hue = {name: {"rec709": round(float(rgb_hue_degrees(chart_rec709[i])), 1), **{s: round(float(rgb_hue_degrees(chart_stages[s][i])), 1) for s in order}} for i, name in enumerate(names)}
    chroma = {name: {s: round(float(np.ptp(chart_stages[s][i]) / chart_stages[s][i].mean()), 3) for s in order} | {"rec709": round(float(np.ptp(chart_rec709[i]) / chart_rec709[i].mean()), 3)} for i, name in enumerate(names)}
    # Narrow bands of 10 nm width: no reconstruction, the layer sensitivities directly.
    wl = c.wavelengths
    narrow = {}
    balance_q = n.layer_gain * c.layer_exposure(0.18 * n.light(options.balance_light))
    for nm in NARROW_BANDS_NM:
        band = np.exp(-0.5 * ((wl - nm) / 4.25) ** 2)
        band = 0.18 * band / c.xyz(band)[1]
        q = n.layer_gain * c.layer_exposure(band)
        record = n.negative_density(q[None])[0]
        narrow[str(int(nm))] = {"layer_log10_above_grey": np.round(np.log10(np.maximum(q, 1e-30)) - np.log10(balance_q), 3).tolist(), "apd": d.table_apd(record)[0].round(3).tolist()}
    # Base and neutral against the Status M reconstruction.
    f = n.film
    ramp = 0.18 * 2.0 ** np.linspace(-5.0, 5.0, 41)
    q = n.layer_gain * c.layer_exposure(ramp[:, None] * n.light(options.balance_light)[None, :])
    record = n.negative_density(q)[0]
    wanted = np.stack([np.interp(f.negative_criterion_log_h[k] + np.log10(q[:, k]), s.log_h, s.density) for k, s in enumerate(n.status_curves)], axis=1)
    got = n.record_to_status_m(record)
    base = f.status_density(f.negative_dmin, f.w_status_m)
    return {"matrices": {k: np.round(m, 3).tolist() for k, m in matrices.items()}, "blue_to_red_coefficient": {k: round(v, 3) for k, v in coefficient.items()}, "steps": {k: round(v, 3) for k, v in steps.items()},
            "sum_of_steps_above_rec709": round(float(sum(steps.values())), 3), "total_end_to_end_above_rec709": round(total - coefficient["rec709"], 3), "end_to_end_samples": int(inside.sum()),
            "chart_rgb_hue_degrees": hue, "chart_range_over_mean": chroma, "narrow_bands": narrow,
            "neutral_status_m_error": {"p95": float(np.percentile(np.abs(got - wanted), 95)), "max": float(np.abs(got - wanted).max()), "limit_p95": 0.01},
            "base_density_status_m": base.round(4).tolist(), "apd_slope": d.gamma.round(3).tolist(), "dye_curve_info": getattr(n, "dye_curve_info", None)}


def main() -> int:
    result = {"cases": {name: trace_case(stock, extra) for name, (stock, extra) in CASES.items()}}
    result["pass"] = {name: {"sum_of_stages": abs(v["sum_of_steps_above_rec709"] - v["total_end_to_end_above_rec709"]) <= 0.01, "neutral_status_m": v["neutral_status_m_error"]["p95"] <= 0.01} for name, v in result["cases"].items()}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    for name, v in result["cases"].items():
        print(name, v["blue_to_red_coefficient"], "sum", v["sum_of_steps_above_rec709"], "e2e", v["total_end_to_end_above_rec709"], "n", v["end_to_end_samples"], "neutral", round(v["neutral_status_m_error"]["p95"], 5), v["dye_curve_info"])
        print("   sky", v["chart_rgb_hue_degrees"]["blue sky"], "\n   apd", v["matrices"]["apd"])
    print(json.dumps(result["pass"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
