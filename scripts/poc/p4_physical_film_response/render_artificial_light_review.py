"""The P4 print on RAW files under artificial light: 5219 under the scene lights of the product choice, with 5207 and Portra 400 as a comparison of stocks.

Input: a directory of RAW files, first argument (never committed). Decoded arrays are cached in build/tmp/p4/input_artificial/.
Output (local only): build/tmp/p4/review_artificial/<name>.jpg, one sheet per file, with a label on every panel. results/p4_physical_film_response/artificial_light_review.json holds the exposure and the share of pixels that stay clipped.
Step: P4, ROADMAP section 8. The light of a panel is an explicit review choice (ROADMAP U21, U22); no panel detects a light. Portra 400 stays on E_ref, because its options have no grey anchor for another scene light.
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
from render_p4_review import physical  # noqa: E402

OUT = REPO_ROOT / "build" / "tmp" / "p4" / "review_artificial"
CACHE = REPO_ROOT / "build" / "tmp" / "p4" / "input_artificial"
RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "artificial_light_review.json"
PANEL = 1400  # the decode reduces by an integer factor, so the panel is near 1000 pixels on a large sensor


def previews() -> dict:
    timed = lambda stock, light: fp.FilmPreview(physical(stock, scene_light=light, print_timing=1.0))  # noqa: E731
    return {"5219 500T | T3200 钨丝 定时 1": timed("5219", "T3200"),
            "5219 500T | 室内暖光 定时 1": timed("5219", "interior_warm"),
            "5219 500T | 室内办公 定时 1": timed("5219", "interior_office"),
            "5219 500T | LED-B3 定时 1": timed("5219", "LED-B3"),
            "5219 500T | 荧光 FL11 定时 1": timed("5219", "FL11"),
            "5207 250D | T3200 钨丝 定时 1": timed("5207", "T3200"),
            "5207 250D | D55 定时 1": timed("5207", "D55"),
            "Portra 400 | E_ref": fp.FilmPreview(physical("portra"))}


def main() -> int:
    source_dir = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in source_dir.iterdir() if p.suffix.lower() in RAW_SUFFIXES)
    if not files:
        raise FileNotFoundError(f"no RAW file in {source_dir}")
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    paths = previews()
    c = next(iter(paths.values())).c
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
        for title, preview in paths.items():
            image, stats = preview.render(graded)
            panels.append((f"{name} | P4 打印 Print\n{title}", image))
            clipped[title] = round(stats["display_clipped_after_compression"] / stats["pixels"], 5)
        write_sheet(OUT / f"{name}.jpg", panels, 3, PANEL, font)
        record[name] = {"size": list(source.shape[:2]), "exposure_stops": round(float(np.log2(scale)), 2), "share_clipped_after_compression": clipped}
        print(name, source.shape, record[name]["exposure_stops"], max(clipped.values()), flush=True)
    RESULT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
