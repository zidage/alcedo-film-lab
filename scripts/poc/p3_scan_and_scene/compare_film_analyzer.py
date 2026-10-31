"""Compare the paths of step P3 with public scan measurements of real film, on a colour chart in an exposure bracket.

Input: build/tmp/p3/filmanalyzer/measurements.json (public measurements of Film Analyzer, license not stated, not committed).
Output: results/p3_scan_and_scene/film_analyzer_compare.json, with statistics of the paths against the scans; build/tmp/p3/filmanalyzer/real_summary.json (local only), with the values of the scans.
Step: P3, README section 8. The user asked to understand the effect of direct scanning; the data is a reference and the model is not fitted to it.

Method. Each chart patch of the reference (Lab under D50) goes to linear AP1 and through a path, with no product grade, because the
real film had none. The Lab values of the site come from its own process (scanner, lab, inversion, flare, target light), which this script does not model,
so these are comparisons of behaviour and not of error against a truth.
Tone: for each stock and offset, L* of the neutrals. Colour: for each path, one exposure shift puts the patch Neutral 5 at the L* of the real scan at offset 0, so that the tone level
does not dominate; then per colour patch, the hue difference, the chroma ratio, and Delta E*ab. Bracket: C* against the offset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "build" / "tmp" / "p3" / "filmanalyzer" / "measurements.json"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "film_analyzer_compare.json"
SRGB_TO_XYZ = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
SRGB_WHITE = np.array([0.9505, 1.0, 1.089])
D50 = np.array([0.96422, 1.0, 0.82521])
NEUTRALS = ["White", "Neutral 8", "Neutral 6.5", "Neutral 5", "Neutral 3.5", "Black"]
SETS = {"5207": ("5207_2383", "5207_ls9000", dict(scene_light="D55")),
        "5207_second_scanner": ("5207_2383", "5207_xt5", dict(scene_light="D55")),
        "5219": ("5219_2383", "5219_ls9000", dict(scene_light="D55", print_timing=0.75)),
        "portra": ("portra400_endura", "portra400_xt5", {})}


def lab_to_xyz_d50(lab: np.ndarray) -> np.ndarray:
    fy = (lab[:, 0] + 16.0) / 116.0
    f = np.stack([fy + lab[:, 1] / 500.0, fy, fy - lab[:, 2] / 200.0], axis=1)
    return np.where(f > 6.0 / 29.0, f ** 3, 3.0 * (6.0 / 29.0) ** 2 * (f - 4.0 / 29.0)) * D50


def srgb_to_lab(srgb: np.ndarray) -> np.ndarray:
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(linear.reshape(-1, 3) @ SRGB_TO_XYZ.T, SRGB_WHITE)


def build_paths(stock: str, extra: dict) -> dict:
    o = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})
    return {"print": fp.FilmPreview(o), "aces13": scan.ScanPreview(o, "aces13"), "aces20": scan.ScanPreview(o, "aces20"), "direct": scan.DirectInversionPreview(o)}


def hue_deg(lab: np.ndarray) -> np.ndarray:
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1]))


def main() -> int:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))["sets"]
    real_summary: dict = {}
    result: dict = {"source": "https://filmanalyzer.talkativephotographer.com/browse/ (per-patch values not stored here)", "stocks": {}}
    for label, (stock, set_name, extra) in SETS.items():
        rows = data[set_name]
        offsets = sorted({r["exposure_offset"] for r in rows})
        names = [r["patch_name"] for r in rows if r["exposure_offset"] == 0]
        real = {o: np.array([[r["mean_L"], r["mean_a"], r["mean_b_lab"]] for r in rows if r["exposure_offset"] == o]) for o in offsets}
        reference = np.array([[r["reference_L"], r["reference_a"], r["reference_b"]] for r in rows if r["exposure_offset"] == 0])
        paths = build_paths(stock, extra)
        c = paths["print"].c
        to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(D50, c.ap1_to_xyz @ np.ones(3))
        ap1 = lab_to_xyz_d50(reference) @ to_ap1.T
        n5, colour = names.index("Neutral 5"), [k for k, n in enumerate(names) if n not in NEUTRALS]
        neutral = [names.index(n) for n in NEUTRALS]
        real_summary[label] = {"set": set_name, "neutral_L_by_offset": {str(o): real[o][neutral, 0].round(1).tolist() for o in offsets},
                               "neutral_b_by_offset": {str(o): real[o][neutral, 2].round(1).tolist() for o in offsets},
                               "median_C_by_offset": {str(o): float(np.median(np.hypot(*real[o][colour, 1:].T)).round(1)) for o in offsets}}
        stock_result: dict = {"set": set_name, "paths": {}}
        for name, path in paths.items():
            def shown(stops: float) -> np.ndarray:
                return srgb_to_lab(path.render((ap1 * 2.0 ** stops)[None].astype(np.float32))[0][0])
            shifts = np.linspace(-3.0, 3.0, 61)
            levels = np.array([shown(float(s))[n5, 0] for s in shifts])
            shift = float(np.interp(real[0][n5, 0], np.maximum.accumulate(levels), shifts))
            matched = shown(shift)
            hue = hue_deg(matched[colour]) - hue_deg(real[0][colour])
            hue = (hue + 180.0) % 360.0 - 180.0
            ratio = np.hypot(*matched[colour, 1:].T) / np.hypot(*real[0][colour, 1:].T)
            delta = np.linalg.norm(matched[colour] - real[0][colour], axis=1)
            stock_result["paths"][name] = {
                "neutral_L_by_offset_unshifted": {str(o): shown(float(o))[neutral, 0].round(1).tolist() for o in offsets},
                "neutral_b_by_offset_unshifted": {str(o): shown(float(o))[neutral, 2].round(1).tolist() for o in offsets},
                "median_C_by_offset_unshifted": {str(o): float(np.median(np.hypot(*shown(float(o))[colour, 1:].T)).round(1)) for o in offsets},
                "stops_to_real_neutral_5": round(shift, 2), "delta_e_median": float(np.median(delta).round(1)), "hue_difference_abs_median_deg": float(np.median(np.abs(hue)).round(1)),
                "chroma_ratio_median": float(np.median(ratio).round(2)), "hue_difference_deg_by_patch": dict(zip([names[k] for k in colour], hue.round(0).tolist())),
                "chroma_ratio_by_patch": dict(zip([names[k] for k in colour], ratio.round(2).tolist()))}
            s = stock_result["paths"][name]
            print(label, name, {k: s[k] for k in ("stops_to_real_neutral_5", "delta_e_median", "hue_difference_abs_median_deg", "chroma_ratio_median")}, flush=True)
        result["stocks"][label] = stock_result
    # The same film on two scanners: the disagreement of the real scans, for scale.
    rows = {k: {r["patch_name"]: np.array([r["mean_L"], r["mean_a"], r["mean_b_lab"]]) for r in data[k] if r["exposure_offset"] == 0} for k in ("5207_ls9000", "5207_xt5")}
    colour_names = [n for n in rows["5207_xt5"] if n not in NEUTRALS]
    disagreement = np.array([np.linalg.norm(rows["5207_ls9000"][n] - rows["5207_xt5"][n]) for n in colour_names])
    hues = np.array([hue_deg(rows["5207_ls9000"][n]) - hue_deg(rows["5207_xt5"][n]) for n in colour_names])
    result["two_real_scanners_5207"] = {"delta_e_median": float(np.median(disagreement).round(1)), "delta_e_max": float(disagreement.max().round(1)),
                                        "hue_difference_abs_median_deg": float(np.median(np.abs((hues + 180.0) % 360.0 - 180.0)).round(1))}
    print(result["two_real_scanners_5207"], flush=True)
    (SOURCE.parent / "real_summary.json").write_text(json.dumps(real_summary, indent=1) + "\n", encoding="utf-8", newline="\n")
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
