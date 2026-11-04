"""Spread between stocks of method chart_scan (step P10, round 6, ROADMAP U89): which step of the scan makes the stocks look alike.

Input: the viewer of step P6 (mvp_pipeline.py), the eight stocks of ACCEPTED_STOCKS, scene light 'reference', product grade at exposure 0,
contrast 0, saturation 1 (no change of the input).
Output: results/p10_chart_scan/stock_spread.json; a labelled sheet build/tmp/p10/stock_spread/sweep_sheet.png (local).

Sweep: CIELab (D65) hues 0 to 345 degrees in 15 degree steps, L* 85, 70, 55, 40, 25, C* 30, in linear AP1 (Bradford D65 to the AP1 white, as
the decode of the viewer); patches outside AP1 are not counted. A neutral ramp of -6 to +6 stops in 0.5 stop steps. Each patch is 48 pixels,
and its centre pixel is read, so the image-plane steps (spread, halation, inhibition) act as on a flat area.

Forms, per stock:
- print: method print on Endura Premier, the same print for all stocks.
- apd: method apd of the viewer.
- lab_scan_stock: method chart_scan with slope 'stock' (the form of U88).
- lab_scan_fixed: method chart_scan with slope 'fixed' (rule 'fixed_scan_slope', U89).
- diagnostics of lab_scan_stock with one step common to all stocks: 'mean_matrix' (the mean sensitivity matrix of the eight stocks),
  'stock_contrast_neutral' (the slopes of each stock scaled to the mean of all slopes, so the contrast of the stock stays and the three
  channels are equal at the grey), and 'single_slope' (one slope for all stocks and channels).
- digital: the input through the display steps of the scan (Rec. 709, compression, log curve) with no film.

Metrics: CIELab (D65) of the display code. Spread: per patch, Delta E*ab of each stock to the mean of the stocks, averaged; the same for L*;
the standard deviation of the hue angle and of the chroma ratio to the mean between stocks; the neutral ramp: mean |L* - mean L*| and mean C*.
"""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR.parent / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
RESULT = REPO_ROOT / "results" / "p10_chart_scan" / "stock_spread.json"
SHEET_DIR = REPO_ROOT / "build" / "tmp" / "p10" / "stock_spread"
STOCKS = tuple(mp.ACCEPTED_STOCKS)
HUES = np.arange(0.0, 360.0, 15.0)
LIGHTNESS = np.array([85.0, 70.0, 55.0, 40.0, 25.0])
CHROMA = 30.0
RAMP = np.arange(-6.0, 6.01, 0.5)
PATCH = 48
WHITE_D65 = np.asarray(fp.XYZ_D65, dtype=np.float64)
REC709_TO_XYZ = np.linalg.inv(fp.XYZ_TO_REC709)
SHEET_FORMS = ("print", "lab_scan_stock", "lab_scan_fixed")


def lab_to_xyz(lab: np.ndarray) -> np.ndarray:
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], axis=-1)
    d = 6 / 29
    return np.where(f > d, f ** 3, 3 * d * d * (f - 4 / 29)) * WHITE_D65


def code_to_lab(code: np.ndarray) -> np.ndarray:
    code = np.asarray(code, dtype=np.float64)
    linear = np.where(code <= 0.04045, code / 12.92, ((code + 0.055) / 1.055) ** 2.4)
    t = (linear @ REC709_TO_XYZ.T) / WHITE_D65
    d = 6 / 29
    f = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def spread(per_stock: dict[str, np.ndarray], in_gamut: np.ndarray, digital: np.ndarray) -> dict:
    labs = np.stack([code_to_lab(per_stock[k]) for k in STOCKS])
    colour, neutral = labs[:, : len(LIGHTNESS), : len(HUES)][:, in_gamut], labs[:, len(LIGHTNESS), : len(RAMP)]
    mean = colour.mean(axis=0)
    chroma = np.hypot(colour[..., 1], colour[..., 2])
    hue = np.degrees(np.arctan2(colour[..., 2], colour[..., 1]))
    mean_hue = np.degrees(np.angle(np.exp(1j * np.radians(hue)).mean(axis=0)))
    to_digital = np.linalg.norm(colour - digital[None], axis=-1)
    return {"spread_delta_e": float(np.linalg.norm(colour - mean, axis=-1).mean()), "spread_l": float(np.abs(colour[..., 0] - mean[..., 0]).mean()),
            "spread_hue_deg_std": float(((hue - mean_hue + 180) % 360 - 180).std(axis=0).mean()), "spread_chroma_ratio_std": float((chroma / chroma.mean(axis=0)).std(axis=0).mean()),
            "neutral_spread_l": float(np.abs(neutral[..., 0] - neutral[..., 0].mean(axis=0)).mean()), "neutral_chroma": float(np.hypot(neutral[..., 1], neutral[..., 2]).mean()),
            "chroma": {k: float(chroma[i].mean()) for i, k in enumerate(STOCKS)}, "to_digital_delta_e": {k: float(to_digital[i].mean()) for i, k in enumerate(STOCKS)}}


def main() -> int:
    base = mp.RenderSettings(exposure_ev=0.0, contrast=0.0, saturation=1.0)
    pipe = mp.Pipeline()
    c = pipe.colorimetry(base)
    to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))
    hue, lightness = np.meshgrid(np.radians(HUES), LIGHTNESS)
    ap1 = lab_to_xyz(np.stack([lightness, CHROMA * np.cos(hue), CHROMA * np.sin(hue)], axis=-1)) @ to_ap1.T
    in_gamut = (ap1 >= 0).all(axis=-1)
    rows = np.zeros((len(LIGHTNESS) + 1, max(len(HUES), len(RAMP)), 3))
    rows[: len(LIGHTNESS), : len(HUES)] = np.maximum(ap1, 0.0)
    rows[len(LIGHTNESS), : len(RAMP)] = (0.18 * 2.0 ** RAMP)[:, None]
    image = np.repeat(np.repeat(rows, PATCH, axis=0), PATCH, axis=1).astype(np.float32)
    graded = np.ascontiguousarray(fp.fk.product_grade(image, 0.0, 0.0, 1.0), dtype=np.float32)
    centre = slice(PATCH // 2, None, PATCH)

    def sample(code: np.ndarray) -> np.ndarray:
        return np.asarray(code, dtype=np.float64)[centre, centre]

    forms: dict[str, dict[str, np.ndarray]] = {}
    models = {}
    for stock in STOCKS:
        s = replace(base, negative=stock)
        forms.setdefault("print", {})[stock] = sample(pipe.render_array(image, replace(s, method="print")))
        forms.setdefault("apd", {})[stock] = sample(pipe.render_array(image, replace(s, method="apd")))
        forms.setdefault("lab_scan_fixed", {})[stock] = sample(pipe.render_array(image, replace(s, method="chart_scan", chart_scan_slope="fixed")))
        forms.setdefault("lab_scan_stock", {})[stock] = sample(pipe.render_array(image, replace(s, method="chart_scan", chart_scan_slope="stock")))
        models[stock] = copy.copy(pipe.chart_scan_model(replace(s, method="chart_scan", chart_scan_slope="stock")))
        print(stock, flush=True)
    mean_matrix = np.mean([models[k].matrix for k in STOCKS], axis=0)
    single = float(np.mean([models[k].straight_slope for k in STOCKS]))
    for stock in STOCKS:
        m = models[stock]
        for name, matrix, slope in (("mean_matrix", mean_matrix, m.straight_slope), ("stock_contrast_neutral", m.matrix, m.straight_slope * single / m.straight_slope.mean()),
                                    ("single_slope", m.matrix, np.full(3, single))):
            variant = copy.copy(m)
            variant.matrix, variant.straight_slope = matrix, slope
            forms.setdefault(name, {})[stock] = sample(variant.render(graded)[0])
    first = models[STOCKS[0]]
    digital = sample(first.display_channels(first.compress_709(graded @ first.ap1_to_rec709.T)))
    digital_lab = code_to_lab(digital)[: len(LIGHTNESS), : len(HUES)][in_gamut]
    record = {"stocks": list(STOCKS), "scene_light": mp.REFERENCE_LIGHT, "chroma": CHROMA, "lightness": LIGHTNESS.tolist(), "hues_deg": HUES.tolist(), "ramp_stops": RAMP.tolist(),
              "patches_in_ap1": int(in_gamut.sum()), "digital_chroma": float(np.hypot(digital_lab[..., 1], digital_lab[..., 2]).mean()),
              "stock_slopes": {k: models[k].straight_slope.tolist() for k in STOCKS}, "forms": {name: spread(per_stock, in_gamut, digital_lab) for name, per_stock in forms.items()}}
    RESULT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    for name, entry in record["forms"].items():
        print(f"{name:24s} spread {entry['spread_delta_e']:.2f}  L {entry['spread_l']:.2f}  hue std {entry['spread_hue_deg_std']:.2f}  chroma ratio std {entry['spread_chroma_ratio_std']:.3f}"
              f"  neutral L {entry['neutral_spread_l']:.2f}  neutral C* {entry['neutral_chroma']:.2f}")

    cell, label = 14, 14
    width, height = len(HUES) * cell, (len(LIGHTNESS) + 1) * cell
    sheet = Image.new("RGB", (len(SHEET_FORMS) * (width + 8) + 8, (len(STOCKS) + 1) * (height + label + 6) + 6), (40, 40, 40))
    draw = ImageDraw.Draw(sheet)

    def panel(code: np.ndarray, x: int, y: int, text: str) -> None:
        tile = Image.fromarray((np.clip(code[:, : len(HUES)], 0, 1) * 255 + 0.5).astype(np.uint8)).resize((width, height), Image.Resampling.NEAREST)
        sheet.paste(tile, (x, y + label))
        draw.text((x, y), text, fill=(230, 230, 230))

    for column, name in enumerate(SHEET_FORMS):
        x = 8 + column * (width + 8)
        panel(digital, x, 6, "digital input, scan display steps")
        for row, stock in enumerate(STOCKS):
            panel(forms[name][stock], x, 6 + (row + 1) * (height + label + 6), f"{stock} / {name}")
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(SHEET_DIR / "sweep_sheet.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
