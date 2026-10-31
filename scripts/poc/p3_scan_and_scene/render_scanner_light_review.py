"""Classic scanner styles on the direct inversion: the same negative, with APD, a narrowband Frontier light, the Noritsu LS-600 tone curve, or the Flextight input profile.

Input: AP1 arrays of the full review (build/tmp/p3/input/, build/tmp/baseline/night/), never committed.
Output (local only): build/tmp/p3/review_light/<name>.png, a label on every panel. results/p3_scan_and_scene/scanner_light.json holds the neutral ramp and the
hue change of chart colours for each light.
Step: P3, README section 8, decision U26: the error that a scanner adds is wanted.

Rule 'frontier_sp3000_light_estimate': three bands read by eye from a spectrum picture of the SP3000 on a public forum
(https://forums.negativelabpro.com/t/optimize-nlp-for-rgb-light-sources/4012, source of the picture not stated): peaks 465, 540, 632 nm, widths at half height 16, 34, 16 nm.
Shape: 0.7 Gaussian + 0.3 Lorentzian, for the visible tails. The sensor is taken as flat over each band. These values are estimates. No Fujifilm file is used, and the
software of the scanner (film channels, frame correction, tone) is not modeled.

Rule 'flextight_input_icc' (panel 'X5 ICC', when the local file exists): the positive of the direct inversion, encoded with the gamma 1.8 of the profile, goes through the A2B0 table of
Flextight_Input.icc to Lab, then to the display, with a clip that is counted. The file is the copyrighted input profile of the public FlexColor 4.8.9.1 installer of Hasselblad. It stays in build/tmp and is
not committed. How FlexColor prepares its positive before this table is not reproduced, so this shows the colour of the table and not the output of FlexColor.

Rule 'noritsu_ls600_tone' (panel 'Noritsu', when the local file exists): the 20-point base tone curve of the LS-600 software (variant 00000005), as recovered by noritsu-tool (MIT; the numbers come from
Noritsu software), one curve per channel. Inferred: the curve input is density above the base over a fixed range, and the output is a display code value. The range is set so that the 18 % grey shows the same sRGB value as the
direct inversion, with the grey 0.7 density above the base (the aim of ADX). That software normalizes the range per frame and has later colour stages; neither is reproduced here.
These panels are style simulations and carry no endorsement of a manufacturer (README U27).
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from compare_film_analyzer import D50, srgb_to_lab, lab_to_xyz_d50  # noqa: E402
from render_full_review import CACHE, INPUTS, OVERVIEW_PANEL, fit, sheet_cell, LABEL_STRIP  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review_light"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "scanner_light.json"
X5_ICC = REPO_ROOT / "build" / "tmp" / "p3" / "scanners" / "flexcolor_dl" / "d" / "Flextight_Input.icc"
NORITSU_CURVE = REPO_ROOT / "build" / "tmp" / "p3" / "scanners" / "noritsu-tool" / "noritsu" / "tables" / "base_tone_curve.json"
# Chosen for colour richness: a rank of hue coverage and chroma, then by eye from the contact sheets. Plus one synthetic sweep.
FILES = ["hue_sweep", "se166", "se146", "se355", "se357", "se368", "se346", "se160", "se178", "se101", "se347", "se379", "se128", "se296", "se188",
         "se345", "se259", "se325", "se199", "se245", "se274", "leica_m10", "fuji_gfx100rf", "showcase_DSC_7169"]
PANEL = 400
FRONTIER_BANDS = ((632.0, 16.0), (540.0, 34.0), (465.0, 16.0))
STOCKS = {"5207": ("5207_2383", dict(scene_light="D55")), "5219": ("5219_2383", dict(scene_light="D55", print_timing=0.75)), "portra": ("portra400_endura", {})}
# Reference chart colours (Lab under D50) of the common published chart values, to show the direction of a change.
CHART = {"dark skin": (37.54, 14.37, 14.92), "light skin": (65.71, 18.13, 17.81), "blue sky": (49.93, -4.88, -21.93), "foliage": (43.14, -13.10, 21.91), "orange": (62.66, 36.07, 57.10),
         "yellow": (81.73, 4.04, 79.82), "red": (42.10, 53.38, 28.19), "green": (55.26, -38.34, 31.37), "blue": (28.78, 14.18, -50.30), "magenta": (51.94, 49.99, -14.57), "cyan": (51.04, -28.63, -28.64)}


def frontier_responsivity() -> tuple[str, np.ndarray, np.ndarray]:
    wavelengths = np.arange(400.0, 751.0)
    bands = []
    for peak, width in FRONTIER_BANDS:
        sigma = width / 2.3548
        gaussian = np.exp(-0.5 * ((wavelengths - peak) / sigma) ** 2)
        lorentzian = 1.0 / (1.0 + ((wavelengths - peak) / (width / 2.0)) ** 2)
        bands.append(0.7 * gaussian + 0.3 * lorentzian)
    return "frontier_sp3000_estimate", wavelengths, np.stack(bands)


class IccLookup:
    """The A2B0 table (mft2, ICC v2) of a profile from RGB to Lab: input curves, trilinear table, output curves."""

    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        count = struct.unpack(">I", data[128:132])[0]
        tags = {data[132 + 12 * k:136 + 12 * k]: struct.unpack(">II", data[136 + 12 * k:144 + 12 * k]) for k in range(count)}
        offset, _ = tags[b"A2B0"]
        if data[offset:offset + 4] != b"mft2":
            raise ValueError("the A2B0 tag is not mft2")
        channels_in, channels_out, self.grid = data[offset + 8], data[offset + 9], data[offset + 10]
        n, m = struct.unpack(">HH", data[offset + 48:offset + 52])
        position = offset + 52
        self.input = np.frombuffer(data, ">u2", channels_in * n, position).reshape(channels_in, n) / 65535.0
        position += 2 * channels_in * n
        size = self.grid ** channels_in * channels_out
        self.table = (np.frombuffer(data, ">u2", size, position).reshape(self.grid, self.grid, self.grid, channels_out) / 65535.0).astype(np.float64)
        position += 2 * size
        self.output = np.frombuffer(data, ">u2", channels_out * m, position).reshape(channels_out, m) / 65535.0

    def lab(self, rgb: np.ndarray) -> np.ndarray:
        ramp = np.linspace(0.0, 1.0, self.input.shape[1])
        positions = np.stack([np.interp(rgb[..., k], ramp, self.input[k]) * (self.grid - 1) for k in range(3)])
        out = np.stack([map_coordinates(self.table[..., k], positions, order=1, mode="nearest") for k in range(3)], axis=-1)
        ramp = np.linspace(0.0, 1.0, self.output.shape[1])
        encoded = np.stack([np.interp(out[..., k], ramp, self.output[k]) for k in range(3)], axis=-1)
        # Legacy 16-bit Lab of ICC v2.
        return np.stack([encoded[..., 0] * 65535.0 / 652.8, encoded[..., 1] * 65535.0 / 256.0 - 128.0, encoded[..., 2] * 65535.0 / 256.0 - 128.0], axis=-1)


def through_icc(srgb: np.ndarray, icc: IccLookup) -> tuple[np.ndarray, int]:
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    lab = icc.lab(np.clip(linear, 0.0, 1.0) ** (1.0 / 1.797))
    shape = lab.shape
    xyz = lab_to_xyz_d50(lab.reshape(-1, 3))
    display = xyz @ (fp.XYZ_TO_REC709 @ fp.bradford_matrix(D50, fp.XYZ_D65)).T
    outside = int(((display < 0.0) | (display > 1.0)).any(axis=-1).sum())
    return fp.srgb_encode(display).reshape(shape), outside


def noritsu_tone(display_grey: float = 0.22):
    points = np.array(json.loads(NORITSU_CURVE.read_text(encoding="utf-8"))["variants"]["00000005"], dtype=np.float64) / 65535.0
    inputs = np.linspace(0.0, 1.0, len(points))
    grey_code = float(fp.srgb_encode(np.array(display_grey)))
    grey_input = float(np.interp(grey_code, points, inputs))
    per_log_exposure = grey_input / 0.7 * 0.55  # density range from the grey position; the mean slope of a negative is about 0.55

    def tone(log_exposure: np.ndarray) -> np.ndarray:
        return np.interp(np.clip(grey_input + per_log_exposure * log_exposure, 0.0, 1.0), inputs, points)

    return tone


def load(name: str, c) -> np.ndarray:
    for path in (CACHE / f"{name}.npy", INPUTS / "night" / f"{name}_ap1.npy"):
        if path.exists():
            return np.load(path).astype(np.float64)
    found = list((INPUTS / "signature_edits" / "raw").glob(f"{name}.*"))
    if len(found) != 1:
        raise FileNotFoundError(name)
    ap1, _ = fp.decode_raw_ap1(found[0], 1000, c)
    np.save(CACHE / f"{name}.npy", ap1.astype(np.float32))
    return ap1


def hue_sweep(c) -> np.ndarray:
    """Synthetic image with no photo: hue from left to right, in rows of saturation and of exposure, in linear Rec. 709 at the mean grey of the exposure rule."""
    hue = np.linspace(0.0, 6.0, 960, endpoint=False)
    rows = []
    for saturation, stops in ((0.95, 1.0), (0.95, 0.0), (0.95, -1.0), (0.95, -2.0), (0.6, 1.0), (0.6, 0.0), (0.6, -1.0), (0.3, 0.0)):
        channels = np.stack([np.clip(np.abs(((hue + shift) % 6.0) - 3.0) - 1.0, 0.0, 1.0) for shift in (0.0, 4.0, 2.0)], axis=-1)
        rgb = (1.0 - saturation + saturation * channels) * 0.5 * 2.0 ** stops
        rows.append(np.repeat(rgb[None], 80, axis=0))
    image = np.concatenate(rows, axis=0)
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    return image @ np.linalg.inv(to_display).T


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    frontier = frontier_responsivity()
    paths = {}
    for label, (stock, extra) in STOCKS.items():
        o = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})
        paths[label] = {"print": fp.FilmPreview(o), "apd": scan.DirectInversionPreview(o), "frontier": scan.DirectInversionPreview(o, scanner=frontier), "noritsu": scan.DirectInversionPreview(o, tone=noritsu_tone())}
    c = paths["5207"]["print"].c
    to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(D50, c.ap1_to_xyz @ np.ones(3))
    names = list(CHART)
    icc = IccLookup(X5_ICC) if X5_ICC.exists() else None
    chart = lab_to_xyz_d50(np.array(list(CHART.values()))) @ to_ap1.T
    result: dict = {"bands_nm": FRONTIER_BANDS, "stocks": {}}
    for label, group in paths.items():
        a, b = (srgb_to_lab(group[k].render(chart[None].astype(np.float32))[0][0]) for k in ("apd", "frontier"))
        hue = np.degrees(np.arctan2(b[:, 2], b[:, 1]) - np.arctan2(a[:, 2], a[:, 1]))
        ramp = np.outer(0.18 * 2.0 ** np.arange(-5.0, 6.0), np.ones(3)).astype(np.float32)
        neutral = srgb_to_lab(group["frontier"].render(ramp[None])[0][0])
        result["stocks"][label] = {"apd_dmin": group["apd"].apd_dmin.round(3).tolist(), "frontier_dmin": group["frontier"].apd_dmin.round(3).tolist(),
                                   "apd_slope": group["apd"].gamma.round(3).tolist(), "frontier_slope": group["frontier"].gamma.round(3).tolist(),
                                   "hue_change_deg_frontier_minus_apd": dict(zip(names, ((hue + 180.0) % 360.0 - 180.0).round(1).tolist())),
                                   "chroma_ratio_frontier_to_apd": dict(zip(names, (np.hypot(b[:, 1], b[:, 2]) / np.hypot(a[:, 1], a[:, 2])).round(2).tolist())),
                                   "frontier_neutral_a_b": neutral[:, 1:].round(1).tolist()}
        if icc:
            k = srgb_to_lab(through_icc(group["apd"].render(chart[None].astype(np.float32))[0], icc)[0][0])
            hue_icc = np.degrees(np.arctan2(k[:, 2], k[:, 1]) - np.arctan2(a[:, 2], a[:, 1]))
            icc_neutral = srgb_to_lab(through_icc(group["apd"].render(ramp[None])[0], icc)[0][0])
            result["stocks"][label].update({"hue_change_deg_x5_icc_minus_apd": dict(zip(names, ((hue_icc + 180.0) % 360.0 - 180.0).round(1).tolist())),
                                            "chroma_ratio_x5_icc_to_apd": dict(zip(names, (np.hypot(k[:, 1], k[:, 2]) / np.hypot(a[:, 1], a[:, 2])).round(2).tolist())),
                                            "x5_icc_neutral_L_a_b": icc_neutral.round(1).tolist()})
        print(label, json.dumps(result["stocks"][label]), flush=True)
    columns = ["print", "apd", "frontier", "noritsu"] + (["x5_icc"] if icc else [])
    titles = {"print": "打印 Print (P2)", "apd": "反转 + 理想 APD", "frontier": "反转 + Frontier SP3000 灯谱(估计)", "noritsu": "反转 + Noritsu LS-600 曲线", "x5_icc": "反转 + X5 ICC (FlexColor)"}
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    title_font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 20)
    side = PANEL
    overview_rows = []
    for name in sys.argv[1:] or FILES:
        ap1 = hue_sweep(c) if name == "hue_sweep" else load(name, c)
        graded = fp.product_input(ap1, c)
        to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
        plain = fp.srgb_encode(ap1 * fp.center_weighted_exposure(ap1, c) @ to_display.T)
        images = {label: {method: through_icc(group["apd"].render(graded)[0], icc)[0] if method == "x5_icc" else group[method].render(graded)[0] for method in columns} for label, group in paths.items()}
        first = fit(plain, side)
        w, h = first.size
        cw, ch = w + 8, h + LABEL_STRIP + 8
        sheet = Image.new("RGB", (cw * (len(columns) + 1) + 8, ch * len(paths) + 44), (26, 26, 26))
        ImageDraw.Draw(sheet).text((10, 8), f"{name} | 同一负片,只换扫描方式 | 输入: 产品默认调色后", fill=(255, 225, 150), font=title_font)
        sheet.paste(sheet_cell(first, "原图\nPlain sRGB", w, h, font), (8, 44))
        for r, label in enumerate(paths):
            for k, method in enumerate(columns):
                sheet.paste(sheet_cell(fit(images[label][method], side), f"{label}\n{titles[method]}", w, h, font), (8 + cw * (k + 1), 44 + ch * r))
        sheet.save(OUT / f"{name}.png")
        overview_rows.append((name, plain, images["5207"]))
        print(name, flush=True)
    per_sheet = 5
    for start in range(0, len(overview_rows), per_sheet):
        chunk = overview_rows[start:start + per_sheet]
        cw, ch = side + 8, side + LABEL_STRIP + 8
        sheet = Image.new("RGB", (cw * (len(columns) + 1) + 8, ch * len(chunk) + 8), (26, 26, 26))
        for r, (name, plain, images) in enumerate(chunk):
            sheet.paste(sheet_cell(fit(plain, side), f"{name}\n原图 Plain", side, side, font), (8, 8 + ch * r))
            for k, method in enumerate(columns):
                sheet.paste(sheet_cell(fit(images[method], side), f"5207 250D\n{titles[method]}", side, side, font), (8 + cw * (k + 1), 8 + ch * r))
        sheet.save(OUT / f"overview_5207_{start // per_sheet + 1:02d}.png")
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
