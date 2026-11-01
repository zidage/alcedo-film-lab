"""The print path on the landscape files of render_soft_scan_review.py, on 5207, Portra 400, and 5219, with soft C of the direct inversion beside it.

Input: AP1 arrays of the full review, never committed.
Output (local only): build/tmp/p3/review_print/<name>.jpg, one sheet per file with a label on every panel, and build/tmp/p3/review_print/single/<name>_<stock>_print.jpg.
Step: P3, ROADMAP section 8.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_print_apd_review import FILES  # noqa: E402
from render_scanner_light_review import STOCKS, load  # noqa: E402
from render_soft_scan_review import PANEL, SETTINGS  # noqa: E402
from PIL import ImageFont  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review_print"
ORDER = (("5207", "5207 250D + 2383"), ("portra", "Portra 400 + Endura"), ("5219", "5219 500T + 2383"))


def main() -> int:
    (OUT / "single").mkdir(parents=True, exist_ok=True)
    prints, soft = {}, {}
    for label, _ in ORDER:
        stock, extra = STOCKS[label]
        options = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})
        prints[label] = fp.FilmPreview(options)
        soft[label] = scan.DirectInversionPreview(options, **SETTINGS[label]["soft C"])
    c = prints["5207"].c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    for name in sys.argv[1:] or FILES:
        source = load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        first = fit(plain, PANEL)
        w, h = first.size
        cw, ch = w + 8, h + LABEL_STRIP + 12
        sheet = Image.new("RGB", (cw * 4 + 8, ch * 2 + 8), (26, 26, 26))
        sheet.paste(sheet_cell(first, f"{name}\n原图 Plain", w, h, font), (8, 8))
        for k, (label, title) in enumerate(ORDER):
            image = prints[label].render(graded)[0]
            Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(OUT / "single" / f"{name}_{label}_print.jpg", quality=95)
            sheet.paste(sheet_cell(fit(image, PANEL), f"{name}\n打印 Print | {title}", w, h, font), (8 + cw * (k + 1), 8))
            sheet.paste(sheet_cell(fit(soft[label].render(graded)[0], PANEL), f"{name}\nAPD soft C | {title.split(' + ')[0]}", w, h, font), (8 + cw * (k + 1), 8 + ch))
        sheet.save(OUT / f"{name}.jpg", quality=95)
        print(name, sheet.size, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
