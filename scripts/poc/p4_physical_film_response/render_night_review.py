"""The print of 5219 on night RAW files: the P3 chain against the P4 options, under the scene lights that a night photo can need. The direct inversion is not in this review, at the request of the user.

Input: a directory of RAW files, first argument (never committed). Decoded arrays are cached in build/tmp/p4/input_night/.
Comparison panels: spektrafilm (external comparison only, README U18), from render_spektrafilm_night.py. A missing output of that script stops this script. Run order: this script with --inputs-only, render_spektrafilm_night.py, this script.
Output (local only): build/tmp/p4/review_night/<name>.jpg, one sheet per file, with a label on every panel. results/p4_physical_film_response/night_review.json holds the light that the RAW white gives, and the share of pixels that stay clipped.
Step: P4, README section 8, open item P4-O7. The stock is 5219 because the user asked for it. The light of a panel is an explicit review choice (README U21, U22); no panel detects a light.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import fp  # noqa: E402
from render_light_and_detail_review import estimated_light, write_sheet  # noqa: E402
from render_p4_review import path_options, physical  # noqa: E402

OUT = REPO_ROOT / "build" / "tmp" / "p4" / "review_night"
CACHE = REPO_ROOT / "build" / "tmp" / "p4" / "input_night"
SPEKTRA = REPO_ROOT / "build" / "tmp" / "baseline" / "out_spektrafilm_night"
RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "night_review.json"
PANEL = 1000
RAW_SUFFIXES = {".arw", ".rw2", ".nef", ".cr2", ".cr3", ".dng", ".raf"}


def panels_for(light: str) -> dict:
    """Title to path. Print timing 1 removes the cast of the named light at mid grey; the fixed P3 choice is D55 with 0.75."""
    p3 = dict(scene_light="D55", print_timing=0.75)
    paths = {"P3 现状 | D55 定时 0.75 | 打印 Print": fp.FilmPreview(path_options("5219", **p3)),
             "P4 | D55 定时 0.75 | 打印 Print": fp.FilmPreview(physical("5219", **p3))}
    for scene, timing, label in (("T3200", 1.0, "T3200 钨丝 定时 1"), ("T3200", 0.5, "T3200 钨丝 定时 0.5"), ("street_mixed", 1.0, "混合街景 定时 1"), ("street_sodium", 1.0, "钠灯街景 定时 1"), ("street_led", 1.0, "LED 街景 定时 1"), (light, 1.0, f"RAW 白点 {light} 定时 1")):
        paths[f"P4 | {label} | 打印 Print"] = fp.FilmPreview(physical("5219", scene_light=scene, print_timing=timing))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--inputs-only", action="store_true")
    args = parser.parse_args()
    source_dir = args.source_dir
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    files = sorted(p for p in source_dir.iterdir() if p.suffix.lower() in RAW_SUFFIXES)
    if not files:
        raise FileNotFoundError(f"no RAW file in {source_dir}")
    base = fp.FilmPreview(physical("5219"))
    c = base.c
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
        light, cct, xy = estimated_light(path)
        graded = fp.product_input(source, c)
        if args.inputs_only:
            np.save(CACHE / f"{name}_graded.npy", graded)
            continue
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        panels = [(f"{name}\n原图 Plain", plain)]
        for variant, label in (("ungraded", "spektrafilm 默认 | 无产品调色 | 自动曝光"), ("graded", "spektrafilm 默认 | 产品调色后输入 | 自动曝光")):
            panels.append((f"{name} | 5219 500T\n{label}", np.asarray(Image.open(SPEKTRA / f"{name}_{variant}.png").convert("RGB"), dtype=np.float64) / 255.0))
        clipped = {}
        for title, preview in panels_for(light).items():
            image, stats = preview.render(graded)
            panels.append((f"{name} | 5219 500T\n{title}", image))
            if "display_clipped_after_compression" in stats:
                clipped[title] = round(stats["display_clipped_after_compression"] / stats["pixels"], 5)
        write_sheet(OUT / f"{name}.jpg", panels, 3, PANEL, font)
        record[name] = {"light_from_raw_white": light, "cct_k": round(cct), "neutral_xy": np.round(xy, 4).tolist(), "exposure_stops": round(float(np.log2(fp.center_weighted_exposure(source, c))), 2), "share_clipped_after_compression": clipped}
        print(name, source.shape, light, round(cct), record[name]["exposure_stops"], flush=True)
    if args.inputs_only:
        return 0
    RESULT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
