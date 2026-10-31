"""Softer settings of the direct inversion with APD, on 5207, Portra 400, and 5219, on landscape files. Rules 'soft_scan' and 'density_crosstalk' of aces_scan.py.

Input: AP1 arrays of the full review, never committed. Reference scans of build/tmp/p3/refs/ when they exist (public pages with no license for this use; style reference only, README U28).
Output (local only): build/tmp/p3/review_soft/<name>.jpg, one sheet per file, reference_compare.jpg, with a label on every panel.
Step: P3, README section 8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_print_apd_review import FILES, WARM  # noqa: E402
from render_scanner_light_review import STOCKS, load  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review_soft"
REFS = REPO_ROOT / "build" / "tmp" / "p3" / "refs"
PANEL = 1000
SOFT_5207 = {"soft B": dict(display_grey=0.35, black=0.015, log_contrast=0.85, record_saturation=0.9, crosstalk=0.5 * WARM),
             "soft C": dict(display_grey=0.38, black=0.012, log_contrast=0.92, record_saturation=0.85, crosstalk=0.5 * WARM),
             "soft D": dict(display_grey=0.38, black=0.02, log_contrast=0.8, record_saturation=0.8, crosstalk=0.5 * WARM)}
SETTINGS = {"5207": SOFT_5207, "5219": SOFT_5207,
            "portra": {"soft B": dict(display_grey=0.33, black=0.006, log_contrast=0.88, record_saturation=0.95, crosstalk=0.5 * WARM),
                       "soft C": dict(display_grey=0.36, black=0.006, log_contrast=0.95, record_saturation=1.0, crosstalk=0.5 * WARM),
                       "soft D": dict(display_grey=0.36, black=0.012, log_contrast=0.85, record_saturation=0.9, crosstalk=0.5 * WARM)}}
REFERENCE_PAIRS = (("fa_kodak_5207_vision3_250d_456.jpg", "5207"), ("fa_kodak_5207_vision3_250d_454.jpg", "5207"), ("fa_kodak_portra_400_1034.jpg", "portra"), ("fa_kodak_portra_400_1032.jpg", "portra"))
OURS = ("se167", "canon_r", "hasselblad_x1dii", "landscape__DSC0726")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {}
    for label, settings in SETTINGS.items():
        stock, extra = STOCKS[label]
        options = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})
        paths[label] = {"APD 现状 k=0": scan.DirectInversionPreview(options), **{k: scan.DirectInversionPreview(options, **v) for k, v in settings.items()}}
    c = paths["5207"]["APD 现状 k=0"].negative.c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    stock_title = {"5207": "5207 250D", "5219": "5219 500T", "portra": "Portra 400"}
    for name in sys.argv[1:] or FILES:
        source = load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        panels = [("原图 Plain", plain)]
        for label in ("5207", "portra"):
            panels.append((f"{stock_title[label]} | APD 现状 k=0", paths[label]["APD 现状 k=0"].render(graded)[0]))
        for label in ("5207", "portra", "5219"):
            for key in SETTINGS[label]:
                panels.append((f"{stock_title[label]} | APD {key}", paths[label][key].render(graded)[0]))
        first = fit(plain, PANEL)
        w, h = first.size
        cw, ch = w + 8, h + LABEL_STRIP + 12
        sheet = Image.new("RGB", (cw * 3 + 8, ch * 4 + 8), (26, 26, 26))
        for k, (title, image) in enumerate(panels):
            sheet.paste(sheet_cell(fit(image, PANEL), f"{name}\n{title}", w, h, font), (8 + cw * (k % 3), 8 + ch * (k // 3)))
        sheet.save(OUT / f"{name}.jpg", quality=95)
        print(name, sheet.size, flush=True)
    if all((REFS / r).exists() for r, _ in REFERENCE_PAIRS):
        width, height = 960, 640
        sheet = Image.new("RGB", ((width + 8) * 4 + 8, (height + 34) * 2 + 8), (26, 26, 26))
        draw = ImageDraw.Draw(sheet)
        for k, ((reference, label), name) in enumerate(zip(REFERENCE_PAIRS, OURS)):
            x = 8 + k * (width + 8)
            image = Image.open(REFS / reference).convert("RGB")
            image.thumbnail((width, height))
            draw.text((x, 6), f"真实扫描 仅参考 | {stock_title[label]} | {reference[-8:-4]}", fill=(255, 225, 150), font=font)
            sheet.paste(image, (x, 34))
            source = load(name, c)
            ours = fit(paths[label]["soft C"].render(fp.product_input(source, c))[0], width)
            ours.thumbnail((width, height))
            draw.text((x, 34 + height + 6), f"我们 | {stock_title[label]} | soft C | {name}", fill=(255, 225, 150), font=font)
            sheet.paste(ours, (x, 34 + height + 34))
        sheet.save(OUT / "reference_compare.jpg", quality=93)
    return 0


if __name__ == "__main__":
    sys.exit(main())
