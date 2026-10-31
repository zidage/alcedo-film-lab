"""Review sheets of rule 'contrast_mask': the six stocks and 5207 on the print, without and with the mask, one sheet per file, with a label on every panel.

Input: AP1 arrays as in render_p5_review.py. Command line: names of files (default: the 8 mountain files and 3 portraits).
Output (local only): build/tmp/p5/review_mask/<name>.jpg.
Step: P5, README section 8, decision U35. The options of the mask are inferred, and no default of the model uses them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import fp  # noqa: E402
from check_stock_chain import stock_options  # noqa: E402
from render_light_and_detail_review import write_sheet  # noqa: E402
from render_p5_review import input_array  # noqa: E402
from render_scan_inversion import FILES, STOCKS  # noqa: E402

OUT = REPO_ROOT / "build" / "tmp" / "p5" / "review_mask"
MASK = dict(mask_gamma=0.5)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    pairs = {}
    for title, key in STOCKS.items():
        extra = dict(scene_light="D55") if key == "5207_2383" else {}
        pairs[title] = (fp.FilmPreview(stock_options(key, **extra)), fp.FilmPreview(stock_options(key, **extra, **MASK)))
    c = pairs["5207"][0].c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    for name in sys.argv[1:] or FILES:
        source = input_array(name, c)
        graded = fp.product_input(source, c)
        panels = [(f"{name}\n原图 Plain", fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0)))]
        for title, (plain, masked) in pairs.items():
            panels.append((f"{name}\n{title} | P4 打印", plain.render(graded)[0]))
            panels.append((f"{name}\n{title} | 对比蒙版 0.5", masked.render(graded)[0]))
        write_sheet(OUT / f"{name}.jpg", panels, 5, 1000, font)
        print(name, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
