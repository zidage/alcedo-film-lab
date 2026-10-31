"""Sheets that put each P5 stock of this lab above the same stock of spektrafilm (external comparison only, README U18).

Input: AP1 arrays as in render_p5_review.py; build/tmp/p5/out_spektrafilm/ from render_spektrafilm_stocks.py. Command line: --inputs-only writes the graded arrays for that script.
Output (local only): build/tmp/p5/input_compare/<name>.npy, build/tmp/p5/review_spektrafilm/<name>.jpg, one sheet per file, with a label on every panel.
Step: P5, README section 8. The two chains have different exposure rules, so the tone level does not compare directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import fp  # noqa: E402
from check_stock_chain import stock_options  # noqa: E402
from render_light_and_detail_review import write_sheet  # noqa: E402
from render_p5_review import PANEL, input_array  # noqa: E402

INPUT = REPO_ROOT / "build" / "tmp" / "p5" / "input_compare"
EXTERNAL = REPO_ROOT / "build" / "tmp" / "p5" / "out_spektrafilm"
OUT = REPO_ROOT / "build" / "tmp" / "p5" / "review_spektrafilm"
FILES = ("se188", "se274", "se345", "se224", "fuji_xt5", "_DSC4196", "5897833591")
STOCKS = {"portra400_endura": ("Portra 400", "kodak_portra_400"), "portra160_endura": ("Portra 160", "kodak_portra_160"), "portra800_endura": ("Portra 800", "kodak_portra_800"),
          "ektar100_endura": ("Ektar 100", "kodak_ektar_100"), "gold200_endura": ("Gold 200", "kodak_gold_200"), "c200_endura": ("C200", "fujifilm_c200")}


def main() -> int:
    c = fp.FilmPreview(stock_options("portra400_endura")).c
    INPUT.mkdir(parents=True, exist_ok=True)
    if "--inputs-only" in sys.argv:
        for name in FILES:
            np.save(INPUT / f"{name}.npy", np.asarray(fp.product_input(input_array(name, c), c), dtype=np.float32))
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    paths = {key: fp.FilmPreview(stock_options(key)) for key in STOCKS}
    for name in FILES:
        graded = np.load(INPUT / f"{name}.npy").astype(np.float64)
        panels = []
        for key, (title, external) in STOCKS.items():
            panels.append((f"{name}\n{title} | 本实验室 This lab | 打印 Endura", paths[key].render(graded)[0]))
        for key, (title, external) in STOCKS.items():
            panels.append((f"{name}\n{title} | spektrafilm 外部对照 | Portra Endura", np.asarray(Image.open(EXTERNAL / f"{name}_{external}.png").convert("RGB"), dtype=np.float32) / 255.0))
        write_sheet(OUT / f"{name}.jpg", panels, 6, PANEL, font)
        print(name, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
