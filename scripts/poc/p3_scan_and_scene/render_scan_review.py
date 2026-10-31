"""Review of the two paths of step P3 on portraits and night files: the print model of P2 (path B) and the scan through ADX and ACES (path A).

Input: linear AP1 arrays from dump_portraits.py and night_probe.py of P2 (build/tmp/baseline/), never committed.
Output: build/tmp/p3/renders/*.png (local only) and results/p3_scan_and_scene/scan_review.json.
Step: P3, README section 8, decision U23. Each image goes through product_input() of P2.

Path B uses the same negative as path A. A pixel of the negative has three free dye amounts, so ADX10 and negative Status M
hold the same information where ADX10 does not clip. Therefore a print from the scan is the print from this negative
up to the clipped values, which are counted.

Each image file has the panels: print | ACES 1.3 | ACES 2.0 | ACES 1.3 matched | ACES 2.0 matched, one file for 5207 and one for 5219 (D55,
print_timing 0.75, the tungsten stock in daylight). 'Matched' adds one neutral scanner light (option exposure_stops), so that the
scene grey has the display luminance of the print path. Both forms are reported, because an output transform shows
ACES 0.18 at about 10 % of its peak and the print path shows it at about 22 %. The stock difference is Delta E*ab between the 5207 and 5219 images of one path, with timing 1 (a neutral grey in both),
so that it holds the difference of the stocks and not the cast.
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

REPO_ROOT = Path(__file__).resolve().parents[3]
INPUTS = REPO_ROOT / "build" / "tmp" / "baseline"
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "renders"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "scan_review.json"
PORTRAITS = ["se002", "se009", "se015", "se019", "se076", "se086", "se127", "se159", "se163", "se231", "se325", "se345", "se348", "se376"]
NIGHT = ["_DSC8085", "_DSC8148", "_DSC8159", "_DSC8169", "_DSC8170", "_DSC8175"]
SRGB_TO_XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
SRGB_WHITE = np.array([0.9505, 1.0, 1.089])


def lab(srgb: np.ndarray) -> np.ndarray:
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(linear.reshape(-1, 3) @ SRGB_TO_XYZ.T, SRGB_WHITE)


def options(stock: str, **extra) -> fp.FilmOptions:
    return fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})


def paths(stock: str, **extra) -> dict:
    o = options(stock, **extra)
    printed = fp.FilmPreview(o)
    grey_srgb = printed.render(np.full((1, 1, 3), 0.18, dtype=np.float32))[0][0, 0]
    grey_linear = np.where(grey_srgb <= 0.04045, grey_srgb / 12.92, ((grey_srgb + 0.055) / 1.055) ** 2.4)
    luminance = float(grey_linear @ SRGB_TO_XYZ[1])
    out = {"print": printed, "aces13": scan.ScanPreview(o, "aces13"), "aces20": scan.ScanPreview(o, "aces20")}
    for output in ("aces13", "aces20"):
        out[f"{output}_matched"] = scan.ScanPreview(o, output, exposure_stops=scan.stops_to_display_luminance(output, luminance))
    return out


def measure(image: np.ndarray) -> dict:
    a = lab(image)
    chroma = np.hypot(a[:, 1], a[:, 2])
    return {"L_p5_p50_p95": np.percentile(a[:, 0], [5, 50, 95]).round(1).tolist(), "C_p50_p95": np.percentile(chroma, [50, 95]).round(1).tolist()}


def load_input(name: str) -> np.ndarray:
    found = list((INPUTS / "input").glob(f"{name}.*.npy")) + list((INPUTS / "night").glob(f"{name}_ap1.npy"))
    if len(found) != 1:
        raise FileNotFoundError(f"{name}: {found}")
    return np.load(found[0]).astype(np.float64)


def save_row(panels: list[np.ndarray], path: Path) -> None:
    gap = np.ones((panels[0].shape[0], 8, 3))
    row = []
    for panel in panels:
        row += [panel, gap]
    Image.fromarray((np.concatenate(row[:-1], axis=1) * 255 + 0.5).astype(np.uint8)).save(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    review = {"5207": paths("5207_2383", scene_light="D55", print_timing=0.75), "5219": paths("5219_2383", scene_light="D55", print_timing=0.75)}
    neutral = {"5207": paths("5207_2383", scene_light="D55", print_timing=1.0), "5219": paths("5219_2383", scene_light="D55", print_timing=1.0)}
    portra = paths("portra400_endura")
    c = review["5207"]["print"].c
    result = {"offsets_code_values": {k: {"5207": neutral["5207"][k].offset.round(1).tolist(), "5219": neutral["5219"][k].offset.round(1).tolist()} for k in ("aces13",)},
              "matched_exposure_stops": {stock: {k: review[stock][k].exposure_stops for k in ("aces13_matched", "aces20_matched")} for stock in review}, "images": {}}
    for name in sys.argv[1:] or PORTRAITS + NIGHT:
        graded = fp.product_input(load_input(name), c)
        record: dict = {}
        panels = []
        for stock, group in review.items():
            for path, preview in group.items():
                image, stats = preview.render(graded)
                panels.append(image)
                record[f"{stock}_timing_0.75_{path}"] = {**measure(image), **{k: stats[k] for k in stats if k.startswith("adx10") or k in ("display_outside_0_1", "display_clipped_after_compression", "pixels")}}
        save_row(panels[:5], OUT / f"{name}_5207.png")
        save_row(panels[5:], OUT / f"{name}_5219.png")
        images = {stock: {path: preview.render(graded)[0] for path, preview in group.items()} for stock, group in neutral.items()}
        portra_images = {path: preview.render(graded)[0] for path, preview in portra.items()}
        difference = {}
        for path in ("print", "aces13", "aces20", "aces13_matched", "aces20_matched"):
            for label, first, second in (("5207_5219", images["5207"][path], images["5219"][path]), ("portra_5207", portra_images[path], images["5207"][path])):
                delta = np.linalg.norm(lab(first) - lab(second), axis=1)
                difference[f"{label}_{path}"] = np.percentile(delta, [50, 95]).round(2).tolist()
        record["stock_difference_delta_e_p50_p95"] = difference
        for path in ("aces13_matched", "aces20_matched"):
            path_delta = np.linalg.norm(lab(images["5207"]["print"]) - lab(images["5207"][path]), axis=1)
            record[f"5207_print_against_{path}_delta_e_p50_p95"] = np.percentile(path_delta, [50, 95]).round(1).tolist()
        result["images"][name] = record
        print(name, json.dumps({k: v for k, v in record.items() if k.startswith("5207_timing") or k.startswith("stock")}), flush=True)
    keys = list(result["images"][next(iter(result["images"]))]["stock_difference_delta_e_p50_p95"])
    result["mean_stock_difference_delta_e_p50_p95"] = {k: np.mean([v["stock_difference_delta_e_p50_p95"][k] for v in result["images"].values()], axis=0).round(2).tolist() for k in keys}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["mean_stock_difference_delta_e_p50_p95"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
