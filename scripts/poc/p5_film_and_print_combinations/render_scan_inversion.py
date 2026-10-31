"""The simulated negative as a scan with its orange base, a 16 bit file for inversion programs, and an automatic inversion of the same kind.

Input: AP1 arrays as in render_p5_review.py. Command line: --export writes TIFF files; names of files follow (default: the 8 mountain files and 3 portraits).
Output (local only): build/tmp/p5/scan_negative/<stock>/<name>_linear.tif and <name>_gamma22.tif; build/tmp/p5/review_inversion/<name>.jpg with a label on every panel. results/p5_film_and_print_combinations/inversion_shadows.json holds the shadow statistics of the mountain files: pixels with L* from 6 to 35 in the plain image, and pixels above L* 85 in the plain image.
Step: P5, README section 8, decision U37. The scan is the APD reading of the negative (ST 2065-2), as linear transmittance, with a border of unexposed film. A real program can read these files.

Rule 'auto_negative_inversion'. This is a model of that kind of program, from general descriptions: it is not a copy of a named program, and no value comes from one. Per channel: density above the film base, D = D_scan - D_base; the range of the frame, lo and hi, at percentiles AUTO_PERCENTILES; t = (D - lo) / (hi - lo), clipped; option 'median': a power per channel moves the median of t to the mean of the three medians; code = t^c / (t^c + (1 - t)^c). The code goes to the display channel, with no matrix. The percentiles and c are review controls, chosen by eye. The range and the balance follow the image, so the same stock can change between frames.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from check_film_response import srgb_to_lab  # noqa: E402
from check_stock_chain import stock_options  # noqa: E402
from render_light_and_detail_review import write_sheet  # noqa: E402
from render_p5_review import input_array  # noqa: E402

OUT_TIFF = REPO_ROOT / "build" / "tmp" / "p5" / "scan_negative"
OUT_SHEET = REPO_ROOT / "build" / "tmp" / "p5" / "review_inversion"
RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "inversion_shadows.json"
FILES = ["_DSC4049", "_DSC4063", "_DSC4067", "_DSC4069", "_DSC4071", "_DSC4196", "_DSC4250", "_DSC4306", "se188", "se274", "se178"]
STOCKS = {"Portra 400": "portra400_endura", "Portra 160": "portra160_endura", "Portra 800": "portra800_endura", "Ektar 100": "ektar100_endura", "Gold 200": "gold200_endura", "C200": "c200_endura", "5207": "5207_2383"}
AUTO_PERCENTILES = (0.1, 99.9)
AUTO_CONTRAST = 1.25
BORDER = 0.03  # share of the long side
BASE_LEVEL = 0.9  # the scanner light puts the brightest channel of the base here


def stock_scan(key: str) -> scan.ScanPreview:
    extra = dict(scene_light="D55") if key == "5207_2383" else {}
    return scan.ScanPreview(stock_options(key, **extra))


def scan_density(path: scan.ScanPreview, graded: np.ndarray) -> np.ndarray:
    return path.table_apd(path.negative.negative_image(np.ascontiguousarray(graded, dtype=np.float32))[0])


def auto_inversion(density: np.ndarray, base: np.ndarray, balance: str = "none") -> np.ndarray:
    above = density - base
    low, high = np.percentile(above.reshape(-1, 3), AUTO_PERCENTILES, axis=0)
    t = np.clip((above - low) / (high - low), 1e-4, 1.0 - 1e-4)
    if balance == "median":
        medians = np.median(t.reshape(-1, 3), axis=0)
        t = t ** (np.log(medians.mean()) / np.log(medians))
    return (t ** AUTO_CONTRAST / (t ** AUTO_CONTRAST + (1.0 - t) ** AUTO_CONTRAST)).astype(np.float32)


def write_tiff(path: scan.ScanPreview, density: np.ndarray, out: Path, name: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    light = BASE_LEVEL * 10.0 ** path.apd_dmin.min()
    border = max(4, int(BORDER * max(density.shape[:2])))
    linear = np.pad(light * 10.0 ** -density, ((border, border), (border, border), (0, 0)), mode="constant")
    linear[:border], linear[-border:], linear[:, :border], linear[:, -border:] = (light * 10.0 ** -path.apd_dmin,) * 4
    linear = np.clip(linear, 0.0, 1.0)
    tifffile.imwrite(out / f"{name}_linear.tif", (linear * 65535.0 + 0.5).astype(np.uint16), photometric="rgb")
    tifffile.imwrite(out / f"{name}_gamma22.tif", (linear ** (1.0 / 2.2) * 65535.0 + 0.5).astype(np.uint16), photometric="rgb")


def tone_statistics(image: np.ndarray, plain_lab: np.ndarray) -> tuple[float, float, float]:
    lightness = srgb_to_lab(np.asarray(image, dtype=np.float64))[..., 0]
    shadow = (plain_lab[..., 0] > 6.0) & (plain_lab[..., 0] < 35.0)
    high = plain_lab[..., 0] > 85.0
    return float(lightness[shadow].mean()), float((lightness[shadow] < 8.0).mean()), float(lightness[high].mean()) if high.any() else float("nan")


def main() -> int:
    arguments = sys.argv[1:]
    export = "--export" in arguments
    names = [a for a in arguments if a != "--export"] or FILES
    OUT_SHEET.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)
    scans = {title: stock_scan(key) for title, key in STOCKS.items()}
    prints = {title: fp.FilmPreview(stock_options(key, **(dict(scene_light="D55") if key == "5207_2383" else {}))) for title, key in STOCKS.items()}
    c = prints["5207"].c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    statistics: dict = {}
    for name in names:
        source = input_array(name, c)
        graded = fp.product_input(source, c)
        panels = [(f"{name}\n原图 Plain", fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0)))]
        plain_lab = srgb_to_lab(panels[0][1].astype(np.float64))
        for title, path in scans.items():
            density = scan_density(path, graded)
            printed = prints[title].render(graded)[0]
            inverted = auto_inversion(density, path.apd_dmin)
            if name.startswith("_DSC"):
                statistics.setdefault(title, {"print": [], "inversion": []})
                statistics[title]["print"].append(tone_statistics(printed, plain_lab))
                statistics[title]["inversion"].append(tone_statistics(inverted, plain_lab))
            panels.append((f"{name}\n{title} | P4 打印 Endura" if title != "5207" else f"{name}\n{title} | P4 打印 2383", printed))
            panels.append((f"{name}\n{title} | 自动反转 逐通道色阶", inverted))
            panels.append((f"{name}\n{title} | 自动反转 + 中值平衡", auto_inversion(density, path.apd_dmin, "median")))
            if export:
                write_tiff(path, density, OUT_TIFF / title.replace(" ", "_"), name)
        write_sheet(OUT_SHEET / f"{name}.jpg", panels, 6, 1000, font)
        print(name, flush=True)
    if statistics:
        mean = {title: {path: dict(zip(("shadow_L", "shadow_share_below_L8", "highlight_L"), np.round(np.nanmean(values, axis=0), 2).tolist())) for path, values in entry.items()} for title, entry in statistics.items()}
        RESULT.write_text(json.dumps(mean, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(mean, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
