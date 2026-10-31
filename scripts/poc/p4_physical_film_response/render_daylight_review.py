"""The P4 print of 5207 and Portra 400 on daylight RAW files. The review shows only the P4 chain, at the request of the user.

Input: a directory of RAW files, first argument (never committed). Decoded arrays are cached in build/tmp/p4/input_daylight_1400/.
Output (local only): build/tmp/p4/review_daylight/<name>.jpg, one sheet per file, with a label on every panel. results/p4_physical_film_response/daylight_review.json holds the exposure and the share of pixels that stay clipped.
Step: P4, README section 8. The scene light of each stock is the fixed choice of the earlier reviews: D55 for 5207, E_ref for Portra 400. No panel detects a light.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import fp  # noqa: E402
from render_light_and_detail_review import write_sheet  # noqa: E402
from render_night_review import RAW_SUFFIXES  # noqa: E402
from render_p4_review import STOCK_TITLE, physical  # noqa: E402

OUT = REPO_ROOT / "build" / "tmp" / "p4" / "review_daylight"
CACHE = REPO_ROOT / "build" / "tmp" / "p4" / "input_daylight_1400"
RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "daylight_review.json"
PANEL = 1400  # the decode reduces by an integer factor, so this limit gives a panel of about 1000 pixels on these 6000 pixel sensors


def main() -> int:
    source_dir = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source_dir.iterdir() if p.suffix.lower() in RAW_SUFFIXES)
    if not files:
        raise FileNotFoundError(f"no RAW file in {source_dir}")
    if len({p.stem for p in files}) != len(files):
        raise ValueError("two files have the same name, so their outputs would collide")
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    paths = {stock: fp.FilmPreview(physical(stock)) for stock in ("5207", "portra")}
    c = paths["5207"].c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    record = {}
    for path in files:
        name = path.stem
        cached = CACHE / f"{name}.npy"
        if cached.exists():
            source = np.load(cached).astype(np.float64)
        else:
            source = fp.decode_raw_ap1(path, PANEL, c)[0]
            np.save(cached, source.astype(np.float32))
        scale = fp.center_weighted_exposure(source, c)
        graded = fp.product_input(source, c)
        panels = [(f"{name}\n原图 Plain", fp.srgb_encode(np.clip(source * scale @ to_display.T, 0.0, 1.0)))]
        clipped = {}
        for stock, preview in paths.items():
            image, stats = preview.render(graded)
            panels.append((f"{name}\n{STOCK_TITLE[stock]} | P4 | 打印 Print", image))
            clipped[stock] = round(stats["display_clipped_after_compression"] / stats["pixels"], 5)
        write_sheet(OUT / f"{name}.jpg", panels, 3, PANEL, font)
        record[name] = {"exposure_stops": round(float(np.log2(scale)), 2), "share_clipped_after_compression": clipped}
        print(name, source.shape, record[name], flush=True)
    RESULT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
