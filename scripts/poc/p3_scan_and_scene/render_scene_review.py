"""Review of the scene choice of step P3 on night files: a global mixture of named CIE spectra in place of one light.

Input: linear AP1 arrays of the night files (build/tmp/baseline/night/, from night_probe.py of P2), never committed.
Output: build/tmp/p3/renders/scene_<name>.png (local only) and results/p3_scan_and_scene/scene_review.json.
Step: P3, ROADMAP section 8, decisions U21 and U22. Stock: 5219 + 2383, print_timing 0.75, the input of product_input().

Grid, row 1: daylight | sodium (one light) | street_mixed | street_sodium; row 2: street_led | interior_warm | interior_office | street_mixed through
the scan and ACES 2.0 (matched to the print grey).

Measured per panel: L*, C*, and the hue change against the daylight panel of the 1 % most chromatic pixels of that panel. These pixels are mostly
signs and lamps in these files, which are the parts that a global light treats wrongly. This is an information value without a limit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_scan_review import INPUTS, NIGHT, OUT, REPO_ROOT, SRGB_TO_XYZ, lab, options  # noqa: E402

RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "scene_review.json"
PANELS = {"daylight": "D55", "sodium": "HP1", "street_mixed": "street_mixed", "street_sodium": "street_sodium", "street_led": "street_led",
          "interior_warm": "interior_warm", "interior_office": "interior_office"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    previews = {k: fp.FilmPreview(options("5219_2383", scene_light=v, print_timing=0.75)) for k, v in PANELS.items()}
    mixed = previews["street_mixed"]
    grey = mixed.render(np.full((1, 1, 3), 0.18, dtype=np.float32))[0][0, 0]
    grey_linear = np.where(grey <= 0.04045, grey / 12.92, ((grey + 0.055) / 1.055) ** 2.4)
    stops = scan.stops_to_display_luminance("aces20", float(grey_linear @ SRGB_TO_XYZ[1]))
    scanned = scan.ScanPreview(mixed.options, "aces20", exposure_stops=stops)
    c = mixed.c
    result = {"scenes": {k: fp.SCENE_PRESETS.get(v, [[v, 1.0]]) for k, v in PANELS.items()},
              "grey_on_curves_stops": {k: p.scene_grey_stops.round(2).tolist() for k, p in previews.items()}, "images": {}}
    for name in sys.argv[1:] or NIGHT:
        graded = fp.product_input(np.load(INPUTS / "night" / f"{name}_ap1.npy").astype(np.float64), c)
        images = {k: p.render(graded)[0] for k, p in previews.items()}
        images["street_mixed_aces20"] = scanned.render(graded)[0]
        base = lab(images["daylight"])
        record = {}
        for k, image in images.items():
            a = lab(image)
            chroma = np.hypot(a[:, 1], a[:, 2])
            top = chroma >= np.percentile(chroma, 99)
            hue = np.arctan2(a[top, 2], a[top, 1]) - np.arctan2(base[top, 2], base[top, 1])
            hue = np.degrees(np.arctan2(np.sin(hue), np.cos(hue)))
            record[k] = {"L_p5_p50_p95": np.percentile(a[:, 0], [5, 50, 95]).round(1).tolist(), "C_p50_p95": np.percentile(chroma, [50, 95]).round(1).tolist(),
                         "hue_change_top_1pct_chroma_abs_p50_p95_deg": np.percentile(np.abs(hue), [50, 95]).round(1).tolist()}
        result["images"][name] = record
        print(name, json.dumps(record), flush=True)
        panels = list(images.values())
        gap = np.ones((panels[0].shape[0], 8, 3))
        rows = [np.concatenate([panels[i], gap, panels[i + 1], gap, panels[i + 2], gap, panels[i + 3]], axis=1) for i in (0, 4)]
        grid = np.concatenate([rows[0], np.ones((8, rows[0].shape[1], 3)), rows[1]], axis=0)
        Image.fromarray((grid * 255 + 0.5).astype(np.uint8)).save(OUT / f"scene_{name}.png")
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
