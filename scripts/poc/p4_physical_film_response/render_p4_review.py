"""Before and after sheets of step P4: the print and the direct inversion with APD, per file, with a label on every panel.

Input: AP1 arrays of the full review of P3 (build/tmp/p3/input/, never committed), the portrait arrays of P2. Command line: --set NAME (a key of SETS), then file names (default: the landscape files and portraits).
Output (local only): build/tmp/p4/review_<set>/<file>.jpg, sweep.png. results/p4_physical_film_response/sweep_<set>.json holds the largest second difference along the hue sweep (limit 0.02, P4 report section 5).
Step: P4, ROADMAP section 8.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_print_apd_review import FILES as LANDSCAPE  # noqa: E402
from render_scanner_light_review import STOCKS, hue_sweep, load  # noqa: E402

PANEL = 1000
SWEEP_LIMIT = 0.02
PORTRAITS = ["se188", "se274", "se345", "se178", "se101", "se259"]
STOCK_TITLE = {"5207": "5207 250D", "5219": "5219 500T", "portra": "Portra 400"}
PUBLISHED = dict(negative_dye_basis="published", negative_record="dye_amount")
AMOUNT = dict(negative_record="dye_amount")


def path_options(stock: str, **extra) -> fp.FilmOptions:
    key, stock_extra = STOCKS[stock]
    return fp.FilmOptions(**{**fp.STOCKS[key], **fp.DARKROOM, **stock_extra, **extra})


def p3_pair(stock: str) -> dict:
    return {f"{STOCK_TITLE[stock]} | P3 现状 | 打印 Print": fp.FilmPreview(path_options(stock)), f"{STOCK_TITLE[stock]} | P3 现状 | APD 反转": scan.DirectInversionPreview(path_options(stock))}


def w1_paths() -> dict:
    light = dict(light_spectra=True)
    paths = {**p3_pair("5207"),
             "5207 250D | W1 光样光谱 | 打印 Print": fp.FilmPreview(path_options("5207", **light)),
             "5207 250D | W1 光样光谱 | APD 反转": scan.DirectInversionPreview(path_options("5207", **light)),
             "5207 250D | W1 光样光谱+发布染料 | 打印 Print": fp.FilmPreview(path_options("5207", **light, **PUBLISHED)),
             "5207 250D | W1 光样光谱+发布染料 | APD 反转": scan.DirectInversionPreview(path_options("5207", **light, **PUBLISHED))}
    return paths


# Tone of the direct inversion with the physical chain. Review controls, chosen by eye. log_contrast takes back the slope of the product grade (P3-O12). The value of black avoids the grey low-key areas of the soft settings of P3.
P4_TONE = dict(display_grey=0.32, black=0.004, log_contrast=0.92, record_saturation=0.95)


def physical(stock: str, **extra) -> fp.FilmOptions:
    return path_options(stock, **{**fp.P4_PHYSICAL[STOCKS[stock][0]], **extra})


def w3_paths() -> dict:
    light = dict(light_spectra=True, **PUBLISHED)
    return {"5207 250D | W1 | APD 反转 每记录斜率": scan.DirectInversionPreview(path_options("5207", **light)),
            "5207 250D | W3 密度定时 固定中性": scan.DirectInversionPreview(path_options("5207", **light), per_record_slope=False),
            "5207 250D | W3 密度定时 图像平衡": scan.DirectInversionPreview(path_options("5207", **light), per_record_slope=False, frame_balance="image"),
            "5207 250D | W3 密度定时 固定中性 + P4 影调": scan.DirectInversionPreview(path_options("5207", **light), per_record_slope=False, **P4_TONE),
            "5207 250D | W3 密度定时 图像平衡 + P4 影调": scan.DirectInversionPreview(path_options("5207", **light), per_record_slope=False, frame_balance="image", **P4_TONE)}


def w2_paths() -> dict:
    off = dict(inhibition_total=(0.0, 0.0, 0.0), layer_spread_um=(0.0, 0.0, 0.0))
    on = dict(layer_spread_um=(0.0, 0.0, 0.0))
    tone = dict(per_record_slope=False, **P4_TONE)
    return {"5207 250D | 无 DIR | 打印 Print": fp.FilmPreview(physical("5207", **off)),
            "5207 250D | 无 DIR | APD 反转": scan.DirectInversionPreview(physical("5207", **off), **tone),
            "5207 250D | W2 DIR | 打印 Print": fp.FilmPreview(physical("5207", **on)),
            "5207 250D | W2 DIR | APD 反转": scan.DirectInversionPreview(physical("5207", **on), **tone),
            "5207 250D | W2 DIR 只自身抑制 | APD 反转": scan.DirectInversionPreview(physical("5207", inhibition_cross_share=0.0, **on), **tone)}


def p4_paths() -> dict:
    tone = dict(per_record_slope=False, **P4_TONE)
    paths = {}
    for stock in ("5207", "portra", "5219"):
        paths.update(p3_pair(stock))
        paths[f"{STOCK_TITLE[stock]} | P4 全部 | 打印 Print"] = fp.FilmPreview(physical(stock))
        paths[f"{STOCK_TITLE[stock]} | P4 全部 | APD 密度定时"] = scan.DirectInversionPreview(physical(stock), **tone)
        paths[f"{STOCK_TITLE[stock]} | P4 全部 | APD 每记录斜率"] = scan.DirectInversionPreview(physical(stock), **P4_TONE)
    return paths


SETS = {"w1": w1_paths, "w2": w2_paths, "w3": w3_paths, "p4": p4_paths}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", required=True, choices=sorted(SETS))
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    out = REPO_ROOT / "build" / "tmp" / "p4" / f"review_{args.set}"
    out.mkdir(parents=True, exist_ok=True)
    paths = SETS[args.set]()
    first = next(iter(paths.values()))
    c = (first.negative if hasattr(first, "negative") else first).c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)

    sweep = hue_sweep(c).astype(np.float32)
    graded_sweep = fp.product_input(sweep, c)
    sweeps = {name: path.render(graded_sweep)[0] for name, path in paths.items()}
    measured = {name: round(float(np.abs(np.diff(image.astype(np.float64), 2, axis=1)).max()), 4) for name, image in sweeps.items()}
    result_path = REPO_ROOT / "results" / "p4_physical_film_response" / f"sweep_{args.set}.json"
    result_path.write_text(json.dumps({"limit": SWEEP_LIMIT, "largest_second_difference": measured, "pass": {k: v <= SWEEP_LIMIT for k, v in measured.items()}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(measured, ensure_ascii=False, indent=0), flush=True)
    h, w = sweep.shape[:2]
    columns = 2
    rows = (len(sweeps) + 1) // columns
    sheet = Image.new("RGB", (columns * (w + 10) + 10, rows * (h + 40) + 10), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for k, (name, image) in enumerate(sweeps.items()):
        x, y = 10 + (k % columns) * (w + 10), 6 + (k // columns) * (h + 40)
        draw.text((x, y), f"hue_sweep | {name}", fill=(255, 225, 150), font=font)
        sheet.paste(Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)), (x, y + 32))
    sheet.save(out / "sweep.png")

    for name in args.names or [*LANDSCAPE, *PORTRAITS]:
        source = load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        panels = [("原图 Plain", fit(plain, PANEL))] + [(title, fit(path.render(graded)[0], PANEL)) for title, path in paths.items()]
        pw, ph = panels[0][1].size
        columns = 4 if len(panels) > 9 else (3 if pw >= ph else 4)
        rows = (len(panels) - 1) // columns + 1
        cw, ch = pw + 8, ph + LABEL_STRIP + 12
        sheet = Image.new("RGB", (cw * columns + 8, ch * rows + 8), (26, 26, 26))
        for k, (title, panel) in enumerate(panels):
            sheet.paste(sheet_cell(panel, f"{name}\n{title}", pw, ph, font), (8 + cw * (k % columns), 8 + ch * (k // columns)))
        sheet.save(out / f"{name}.jpg", quality=95)
        print(name, sheet.size, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
