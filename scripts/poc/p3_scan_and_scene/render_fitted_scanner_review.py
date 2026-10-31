"""Review of the scanner models fitted to chart scans. TEST ONLY: the fits use public measurements with no stated license (README U28), so no output may leave the local build directory.

Input: build/tmp/p3/fitted_scanner/fits.json, AP1 arrays of the full review, build/tmp/p3/filmanalyzer/measurements.json.
Output (local only): build/tmp/p3/fitted_scanner/review/<name>.png, overview_*.png, chart.png, with a label on every panel.
Step: P3, README section 8.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from compare_film_analyzer import lab_to_xyz_d50, D50  # noqa: E402
from fit_scanner_to_chart import OUT, SOURCE, STOCK_OPTIONS, WAVELENGTHS, ChartSet, bands, linear_to_lab, predict, scanner_output  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_scanner_light_review import FILES, hue_sweep, load  # noqa: E402

REVIEW = OUT / "review"
PANEL = 340
TITLES = {"print": "打印 Print (P2)", "apd": "反转 + 理想 APD", "xt5_A": "拟合 X-T5 A: 只有曲线", "xt5_C": "拟合 X-T5 C: 灯+串扰", "xt5_D": "拟合 X-T5 D: 灯+串扰+矩阵",
          "xt5_C_plain": "拟合 X-T5 C,不加产品调色", "ls_C": "拟合 CoolScan C: 灯+串扰"}
FOOT = "仅测试 TEST ONLY"


class FittedScan(scan.ScanPreview):
    """The negative through one fitted scanner model. A level with no fitted light uses APD."""

    def __init__(self, options: fp.FilmOptions, name: str, record: dict, shift: float) -> None:
        self.p = {k: np.array(v) for k, v in record["parameters"].items()}
        self.shift = 2.0 ** shift
        scanner = (name, WAVELENGTHS, bands(self.p["peak"], self.p["width"])) if "peak" in self.p else None
        super().__init__(options, scanner=scanner)

    def render(self, ap1: np.ndarray) -> np.ndarray:
        status_m, _ = self.negative.negative_image(np.ascontiguousarray(ap1 * self.shift, dtype=np.float32))
        return fp.srgb_encode(np.clip(scanner_output(self.table_apd(status_m) - self.apd_dmin, self.p), 0.0, 1.0))


def lab_to_rgb8(lab: np.ndarray) -> tuple[int, ...]:
    linear = lab_to_xyz_d50(lab[None]) @ (fp.XYZ_TO_REC709 @ fp.bradford_matrix(D50, fp.XYZ_D65)).T
    return tuple((fp.srgb_encode(np.clip(linear[0], 0.0, 1.0)) * 255.0).astype(int).tolist())


def chart_sheet(data: dict, fits: dict, paths: dict, font) -> None:
    """Each patch at offset 0: the outer square is the real scan and the inner square is the model."""
    columns = [("真实 X-T5 / 模型 A", "5207_xt5", "A"), ("真实 X-T5 / 模型 C", "5207_xt5", "C"), ("真实 X-T5 / 模型 D", "5207_xt5", "D"), ("真实 CoolScan / 模型 C", "5207_ls9000", "C")]
    size, cols = 54, 6
    sheet = Image.new("RGB", ((cols * size + 16) * len(columns) + 8, 4 * size + 60), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for k, (title, set_name, level) in enumerate(columns):
        record = fits[set_name]
        chart = ChartSet("5207", set_name, data, record["film_exposure_shift_stops"], paths[set_name])
        modelled = predict(chart, {a: np.array(b) for a, b in record["levels"][level]["parameters"].items()})
        rows = np.flatnonzero(chart.offsets == 0)
        x0 = 8 + k * (cols * size + 16)
        draw.text((x0, 8), f"{title} | {FOOT}", fill=(255, 225, 150), font=font)
        for i, row in enumerate(rows):
            x, y = x0 + (i % cols) * size, 40 + (i // cols) * size
            draw.rectangle((x, y, x + size - 2, y + size - 2), fill=lab_to_rgb8(chart.target[row]))
            draw.rectangle((x + 14, y + 14, x + size - 16, y + size - 16), fill=lab_to_rgb8(modelled[row]))
    sheet.save(REVIEW / "chart.png")


def main() -> int:
    REVIEW.mkdir(parents=True, exist_ok=True)
    fits = json.loads((OUT / "fits.json").read_text(encoding="utf-8"))
    data = json.loads(SOURCE.read_text(encoding="utf-8"))["sets"]
    stock_id, extra = STOCK_OPTIONS["5207"]
    options = fp.FilmOptions(**{**fp.STOCKS[stock_id], **fp.DARKROOM, **extra})
    xt5, ls = fits["5207_xt5"], fits["5207_ls9000"]

    def make(record: dict, level: str, tag: str) -> FittedScan:
        return FittedScan(options, f"fitted_{tag}_{level}", record["levels"][level], record["film_exposure_shift_stops"])

    print_path, apd = fp.FilmPreview(options), scan.DirectInversionPreview(options)
    models = {"xt5_A": make(xt5, "A", "xt5"), "xt5_C": make(xt5, "C", "xt5"), "xt5_D": make(xt5, "D", "xt5"), "ls_C": make(ls, "C", "ls9000")}
    c = print_path.c
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)
    chart_paths = {"5207_xt5": scan.ScanPreview(options), "5207_ls9000": scan.ScanPreview(options)}
    chart_sheet(data, fits, chart_paths, font)
    # The table path and the direct path must agree on the chart, or the images do not show the fit.
    chart = ChartSet("5207", "5207_xt5", data, xt5["film_exposure_shift_stops"], chart_paths["5207_xt5"])
    reference = lab_to_xyz_d50(np.array([[r["reference_L"], r["reference_a"], r["reference_b"]] for r in data["5207_xt5"]])) @ (c.xyz_to_ap1 @ fp.bradford_matrix(D50, c.ap1_to_xyz @ np.ones(3))).T
    ap1 = reference * 2.0 ** chart.offsets[:, None]
    shown = models["xt5_C"].render(ap1[None])[0]
    linear = np.where(shown <= 0.04045, shown / 12.92, ((shown + 0.055) / 1.055) ** 2.4)
    direct = predict(chart, models["xt5_C"].p)
    difference = np.linalg.norm(linear_to_lab(linear) - direct, axis=1)
    print("table against direct, delta E: median", round(float(np.median(difference)), 3), "max", round(float(difference.max()), 3), flush=True)

    columns = list(TITLES)
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    rows = []
    for name in sys.argv[1:] or FILES:
        source = hue_sweep(c) if name == "hue_sweep" else load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(source * fp.center_weighted_exposure(source, c) @ to_display.T)
        ungraded = source * fp.center_weighted_exposure(source, c)
        images = {"print": print_path.render(graded)[0], "apd": apd.render(graded)[0], "xt5_C_plain": models["xt5_C"].render(ungraded)}
        images.update({k: m.render(graded) for k, m in models.items()})
        rows.append((name, plain, images))
        print(name, flush=True)
    per_sheet = 5
    cw, ch = PANEL + 8, PANEL + LABEL_STRIP + 8
    for start in range(0, len(rows), per_sheet):
        chunk = rows[start:start + per_sheet]
        sheet = Image.new("RGB", (cw * (len(columns) + 1) + 8, ch * len(chunk) + 8), (26, 26, 26))
        for r, (name, plain, images) in enumerate(chunk):
            sheet.paste(sheet_cell(fit(plain, PANEL), f"{name}\n原图 Plain", PANEL, PANEL, font), (8, 8 + ch * r))
            for k, method in enumerate(columns):
                sheet.paste(sheet_cell(fit(images[method], PANEL), f"5207 | {FOOT}\n{TITLES[method]}", PANEL, PANEL, font), (8 + cw * (k + 1), 8 + ch * r))
        sheet.save(REVIEW / f"overview_{start // per_sheet + 1:02d}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
