"""Review sheets of step P5: the six stocks on the Endura print, one sheet per file, with a label on every panel.

Input: AP1 arrays, never committed: build/tmp/p3/input/ (landscape files), the portrait arrays of P2, build/tmp/p4/input_daylight_1400/, build/tmp/p4/input_shangrila/. Command line: names of files (default: all of them).
Output (local only): build/tmp/p5/review/<name>.jpg. results/p5_film_and_print_combinations/review.json holds the exposure and the share of pixels that stay clipped.
Step: P5, README section 8, decision U34. The Portra 400 panel has the accepted P4 options. The panel 'Gold 200 | Portra 160 MTF' is a comparison only: it takes the spread and the inhibition of another stock, which no default of the model does.
"""

from __future__ import annotations

import json
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
from render_p4_review import PORTRAITS  # noqa: E402
from render_print_apd_review import FILES as LANDSCAPE  # noqa: E402
from render_scanner_light_review import load  # noqa: E402

OUT = REPO_ROOT / "build" / "tmp" / "p5" / "review"
RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "review.json"
EXTRA_INPUTS = (REPO_ROOT / "build" / "tmp" / "p4" / "input_daylight_1400", REPO_ROOT / "build" / "tmp" / "p4" / "input_shangrila")
PANEL = 1000
TITLES = {"portra400_endura": "Portra 400 | P4 已接受", "portra160_endura": "Portra 160", "portra800_endura": "Portra 800", "ektar100_endura": "Ektar 100", "gold200_endura": "Gold 200 | 无 MTF", "c200_endura": "Fujicolor C200"}


def input_array(name: str, c) -> np.ndarray:
    for folder in EXTRA_INPUTS:
        if (folder / f"{name}.npy").exists():
            return np.load(folder / f"{name}.npy").astype(np.float64)
    return load(name, c)


def all_names() -> list[str]:
    return [*PORTRAITS, *LANDSCAPE, *(p.stem for folder in EXTRA_INPUTS for p in sorted(folder.glob("*.npy")))]


def main() -> int:
    names = sys.argv[1:] or all_names()
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    paths = {title: fp.FilmPreview(stock_options(key)) for key, title in TITLES.items()}
    borrowed = fp.P5_PHYSICAL["portra160_endura"]
    paths["Gold 200 | 借 Portra 160 MTF 对比"] =fp.FilmPreview(stock_options("gold200_endura", layer_spread_um=borrowed["layer_spread_um"], inhibition_total=borrowed["inhibition_total"]))
    c = next(iter(paths.values())).c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    record = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.exists() else {}
    for name in names:
        source = input_array(name, c)
        scale = fp.center_weighted_exposure(source, c)
        graded = fp.product_input(source, c)
        panels = [(f"{name}\n原图 Plain", fp.srgb_encode(np.clip(source * scale @ to_display.T, 0.0, 1.0)))]
        clipped = {}
        for title, preview in paths.items():
            image, stats = preview.render(graded)
            panels.append((f"{name}\n{title} | Endura", image))
            clipped[title] = round(stats["display_clipped_after_compression"] / stats["pixels"], 5)
        write_sheet(OUT / f"{name}.jpg", panels, 4, PANEL, font)
        record[name] = {"exposure_stops": round(float(np.log2(scale)), 2), "share_clipped_after_compression": clipped}
        print(name, source.shape, record[name]["exposure_stops"], max(clipped.values()), flush=True)
    RESULT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
