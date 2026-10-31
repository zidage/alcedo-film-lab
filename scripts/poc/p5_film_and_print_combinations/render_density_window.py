"""The automatic inversion of NexFilm as a rule on the simulated negative, a check against the output of NexFilm, and a review of all stocks.

Input: AP1 arrays as in render_p5_review.py. Command line: --reference DIR compares with the JPEG files that NexFilm wrote from the Portra 400 TIFF files of render_scan_inversion.py --export, in the sorted order of REFERENCE_ORDER; names of files follow (default: the 8 mountain files and 3 portraits).
Output (local only): build/tmp/p5/review_density_window/<name>.jpg with a label on every panel. results/p5_film_and_print_combinations/density_window.json holds the check, the shadow statistics of the mountain files, and the distance between stocks.
Step: P5, README section 8, decision U38. Limit of the check: mean RMSE at most 6 of 255 on the 11 files. The author set it after a local probe measured 5.14 on the same files, so it guards against a later change and is not an independent test.

Rule 'density_window_inversion'. Reuse with a label: the method of the uncalibrated Auto Invert of NexFilm (https://github.com/BillyDu-TJ/NexFilm, commit fbd7113f4b0d34c0fa84fc8601b6c5a13a742df1, GPL-3.0-only): the file is read as linear sRGB and goes to linear ProPhoto; density per channel; a window per channel whose endpoints come from the same pixels (WINDOW_TAIL of the sorted density luma); the normalized density goes through ProPhoto to sRGB, with no transfer curve. This code is written for this lab. The one change: NexFilm finds the low endpoint in the frame, and here it is the unexposed film. In the files of the user the border of unexposed film fills the low tail, so both give the same value.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_scan_inversion import FILES, OUT_TIFF, REPO_ROOT, STOCKS, auto_inversion, fp, input_array, scan_density, srgb_to_lab, stock_options, stock_scan, tone_statistics, write_sheet  # noqa: E402

OUT_SHEET = REPO_ROOT / "build" / "tmp" / "p5" / "review_density_window"
RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "density_window.json"
REFERENCE_ORDER = ["_DSC4049", "_DSC4063", "_DSC4067", "_DSC4069", "_DSC4071", "_DSC4196", "_DSC4250", "_DSC4306", "se178", "se188", "se274"]
REFERENCE_LIMIT = 6.0
WINDOW_TAIL = 0.02
WINDOW_LONG_EDGE = 512
DENSITY_LUMA = np.array([0.2126, 0.7152, 0.0722])
XYZ_PROPHOTO = np.array([[0.7976749, 0.1351917, 0.0313534], [0.2880402, 0.7118741, 0.0000857], [0.0, 0.0, 0.8252100]])
XYZ_SRGB = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
BRADFORD_D50_TO_D65 = np.array([[0.9555766, -0.0230393, 0.0631636], [-0.0282895, 1.0099416, 0.0210077], [0.0122982, -0.0204830, 1.3299098]])
PROPHOTO_TO_SRGB = np.linalg.inv(XYZ_SRGB) @ BRADFORD_D50_TO_D65 @ XYZ_PROPHOTO
SRGB_TO_PROPHOTO = np.linalg.inv(PROPHOTO_TO_SRGB)


def working_density(density: np.ndarray) -> np.ndarray:
    return -np.log10(10.0 ** -np.asarray(density, dtype=np.float64) @ SRGB_TO_PROPHOTO.T)


def density_window_inversion(density: np.ndarray, dmin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    working = working_density(density)
    low = working_density(dmin)
    step = max(1, round(max(working.shape[:2]) / WINDOW_LONG_EDGE))
    samples = working[::step, ::step].reshape(-1, 3)
    order = np.argsort(samples @ DENSITY_LUMA)
    high = samples[order[-max(1, int(np.ceil(WINDOW_TAIL * len(samples)))) :]].mean(axis=0)
    normalized = np.clip((working - low) / (high - low), 0.0, 1.0)
    return np.clip(normalized @ PROPHOTO_TO_SRGB.T, 0.0, 1.0).astype(np.float32), high


def reference_check(directory: Path, stem_shape: dict) -> dict:
    record: dict = {}
    jpegs = sorted(directory.glob("*.jpg"))
    if len(jpegs) != len(REFERENCE_ORDER):
        raise ValueError(f"{directory} holds {len(jpegs)} JPEG files, not {len(REFERENCE_ORDER)}")
    for name, jpeg in zip(REFERENCE_ORDER, jpegs):
        target = np.asarray(Image.open(jpeg).convert("RGB"), dtype=np.float64) / 255.0
        mine, earlier = stem_shape[name]
        border = [(s - t) // 2 for s, t in zip(target.shape[:2], mine.shape[:2])]
        inner = target[border[0] : border[0] + mine.shape[0], border[1] : border[1] + mine.shape[1]]
        record[name] = {
            "density_window_rmse_of_255": round(float(np.sqrt(((mine - inner) ** 2).mean()) * 255.0), 2),
            "earlier_auto_rule_rmse_of_255": round(float(np.sqrt(((earlier - inner) ** 2).mean()) * 255.0), 2),
        }
    mean = float(np.mean([entry["density_window_rmse_of_255"] for entry in record.values()]))
    return {"limit_of_255": REFERENCE_LIMIT, "mean_rmse_of_255": round(mean, 2), "pass": mean <= REFERENCE_LIMIT, "files": record}


def main() -> int:
    arguments = sys.argv[1:]
    reference = None
    if "--reference" in arguments:
        at = arguments.index("--reference")
        reference = Path(arguments[at + 1])
        del arguments[at : at + 2]
    names = arguments or FILES
    if reference is not None and set(names) != set(REFERENCE_ORDER):
        raise ValueError("--reference needs all 11 files")
    OUT_SHEET.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    extra = {title: dict(scene_light="D55") if key == "5207_2383" else {} for title, key in STOCKS.items()}
    scans = {title: stock_scan(key) for title, key in STOCKS.items()}
    prints = {title: fp.FilmPreview(stock_options(key, **extra[title])) for title, key in STOCKS.items()}
    c = prints["5207"].c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    statistics: dict = {}
    distances: dict = {}
    highs: dict = {}
    checked: dict = {}
    for name in names:
        source = input_array(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        plain_lab = srgb_to_lab(plain.astype(np.float64))
        top = [(f"{name}\n原图 Plain", plain)]
        bottom = [(f"{name}\n原图 Plain", plain)]
        labs: dict = {"print": {}, "window": {}}
        for title, path in scans.items():
            density = scan_density(path, graded)
            printed = prints[title].render(graded)[0]
            inverted, high = density_window_inversion(density, path.apd_dmin)
            if title == "Portra 400":
                checked[name] = (inverted, auto_inversion(density, path.apd_dmin))
            top.append((f"{name}\n{title} | P4 打印", printed))
            bottom.append((f"{name}\n{title} | 密度窗口反转 NexFilm 方法", inverted))
            if name.startswith("_DSC"):
                statistics.setdefault(title, {"print": [], "density_window": []})
                statistics[title]["print"].append(tone_statistics(printed, plain_lab))
                statistics[title]["density_window"].append(tone_statistics(inverted, plain_lab))
                highs.setdefault(title, []).append(high.tolist())
                labs["print"][title] = srgb_to_lab(printed.astype(np.float64))[::4, ::4]
                labs["window"][title] = srgb_to_lab(inverted.astype(np.float64))[::4, ::4]
        if name.startswith("_DSC"):
            for route, entry in labs.items():
                for title, lab in entry.items():
                    if title != "Portra 400":
                        distances.setdefault(route, {}).setdefault(title, []).append(float(np.linalg.norm(lab - entry["Portra 400"], axis=-1).mean()))
        write_sheet(OUT_SHEET / f"{name}.jpg", top + bottom, 8, 620, font)
        print(name, flush=True)
    record: dict = json.loads(RESULT.read_text(encoding="utf-8")) if RESULT.exists() else {}
    if statistics:
        record["shadow_statistics_mean_of_mountain_files"] = {title: {route: dict(zip(("shadow_L", "shadow_share_below_L8", "highlight_L"), np.round(np.nanmean(values, axis=0), 2).tolist())) for route, values in entry.items()} for title, entry in statistics.items()}
        record["mean_lab_distance_to_portra_400"] = {route: {title: round(float(np.mean(values)), 2) for title, values in entry.items()} for route, entry in distances.items()}
        record["high_endpoint_range_between_mountain_files"] = {title: np.round(np.ptp(np.array(values), axis=0), 3).tolist() for title, values in highs.items()}
    if reference is not None:
        record["reference_check"] = reference_check(reference, checked)
    RESULT.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if "reference_check" not in record or record["reference_check"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
