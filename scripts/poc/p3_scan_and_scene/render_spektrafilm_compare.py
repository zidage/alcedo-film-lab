"""Comparison sheets: spektrafilm (external comparison only, ROADMAP U18), the print path, and soft C of the direct inversion, on the landscape files and three stocks.

Input: build/tmp/baseline/out_spektrafilm_landscape/, build/tmp/p3/review_print/single/ (run render_print_landscape_review.py first), AP1 arrays. None of these are committed.
Output (local only): build/tmp/p3/review_spektrafilm/<name>.jpg, with a label on every panel. spektrafilm has default settings, its own exposure, no grain, and no product grade.
Step: P3, ROADMAP section 8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_print_apd_review import FILES  # noqa: E402
from render_print_landscape_review import ORDER  # noqa: E402
from render_scanner_light_review import STOCKS, load  # noqa: E402
from render_soft_scan_review import PANEL, SETTINGS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review_spektrafilm"
SPEKTRA = REPO_ROOT / "build" / "tmp" / "baseline" / "out_spektrafilm_landscape"
PRINTS = REPO_ROOT / "build" / "tmp" / "p3" / "review_print" / "single"


def read(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    soft = {}
    for label, _ in ORDER:
        stock, extra = STOCKS[label]
        soft[label] = scan.DirectInversionPreview(fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra}), **SETTINGS[label]["soft C"])
    c = soft["5207"].negative.c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    for name in sys.argv[1:] or FILES:
        source = load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        first = fit(plain, PANEL)
        w, h = first.size
        cw, ch = w + 8, h + LABEL_STRIP + 12
        sheet = Image.new("RGB", (cw * 4 + 8, ch * 3 + 8), (26, 26, 26))
        sheet.paste(sheet_cell(first, f"{name}\n原图 Plain", w, h, font), (8, 8))
        for k, (label, title) in enumerate(ORDER):
            x = 8 + cw * (k + 1)
            sheet.paste(sheet_cell(fit(read(SPEKTRA / f"{name}_{label}.png"), PANEL), f"{name}\nspektrafilm 默认 | {title}", w, h, font), (x, 8))
            sheet.paste(sheet_cell(fit(read(PRINTS / f"{name}_{label}_print.jpg"), PANEL), f"{name}\n我们 Print | {title}", w, h, font), (x, 8 + ch))
            sheet.paste(sheet_cell(fit(soft[label].render(graded)[0], PANEL), f"{name}\n我们 APD soft C | {title.split(' + ')[0]}", w, h, font), (x, 8 + 2 * ch))
        sheet.save(OUT / f"{name}.jpg", quality=95)
        print(name, sheet.size, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
