"""Behaviour of the chart-calibrated scan against public scans of real film (step P10, ROADMAP U87), with the method of P3 section 10.3.

Input: build/tmp/p3/filmanalyzer/measurements.json (public measurements of Film Analyzer, license not stated, not committed): a 24-patch chart
in a bracket of -2 to +2 stops, per film and per scanner. The model is not fitted to it; the user states that chart accuracy is not a goal
(P3 section 10.3), so this shows the direction of a behaviour only.
Output: results/p10_chart_scan/lab_scan_compare.json (values of the paths and differences only, no value of the site); the values of the
scans go to build/tmp/p10/real_summary.json (local only, U28).

Per set and variant: the chart patches (reference Lab under D50, to linear AP1) through the current stock options of the viewer (scene light
daylight), no product grade. One exposure shift puts Neutral 5 at the L* of the real scan at offset 0; the bracket is that shift plus the offset.
Measures: Delta E*ab, hue difference and chroma ratio of the 18 colour patches at offset 0; median C* and the b* of the neutrals per offset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import chart_scan as cs  # noqa: E402
import compare_film_analyzer as fa  # noqa: E402  (P3, on the path through chart_scan)
import mvp_pipeline as mp  # noqa: E402

# Option --spectral: the BabelColor spectra of the same 24 patches under D55 go straight to the film (render_spectra), in place of the
# reference Lab through the reconstruction of AP1. A diagnostic of the input path; the real chart is a Calibrite Passport, not the BabelColor Avg.
SPECTRAL = "--spectral" in sys.argv
RESULT = cs.REPO_ROOT / "results" / "p10_chart_scan" / ("lab_scan_compare_spectral.json" if SPECTRAL else "lab_scan_compare.json")
SETS = {"5207, CoolScan 9000": ("kodak_5207", "5207_ls9000"), "5207, X-T5": ("kodak_5207", "5207_xt5"),
        "5219, CoolScan 9000": ("kodak_5219", "5219_ls9000"), "Portra 400, X-T5": ("kodak_portra_400", "portra400_xt5")}
# Name: options of ChartScanPreview. Rounds 2 to 4 of the P10 report.
LOG = dict(matrix=False, inversion="straight", output="log_curve")
VARIANTS = {"curves only": dict(matrix=False, inversion="curves"), "curves + matrix": dict(matrix=True, inversion="curves"),
            "straight line only": dict(matrix=False, inversion="straight"), "straight line + matrix": dict(matrix=True, inversion="straight"),
            "straight line, channel curve": dict(matrix=False, inversion="straight", output="channel_curve"),
            "log curve, APD": LOG, "log curve, Frontier light": {**LOG, "scanner": "frontier"}, "log curve, Status M": {**LOG, "scanner": "status_m"}, "log curve, analytical": {**LOG, "scanner": "analytical"},
            "log curve, APD + unmix": {**LOG, "unmix": True}, "log curve, APD, common slope": {**LOG, "common_slope": True},
            "log curve, Frontier light, common slope": {**LOG, "scanner": "frontier", "common_slope": True},
            "log curve, APD + unmix, common slope": {**LOG, "unmix": True, "common_slope": True},
            "log curve, analytical, common slope": {**LOG, "scanner": "analytical", "common_slope": True},
            "log curve, APD, sensitivity matrix": {**LOG, "sensitivity_matrix": True},
            "log curve, analytical, sensitivity matrix": {**LOG, "scanner": "analytical", "sensitivity_matrix": True},
            "channel curve, APD, sensitivity matrix": dict(matrix=False, inversion="straight", output="channel_curve", sensitivity_matrix=True),
            "log curve, APD, sensitivity matrix, timing 1": {**LOG, "sensitivity_matrix": True, "scan_timing": 1.0},
            "log curve, APD, sensitivity matrix, timing 1, display compression": {**LOG, "sensitivity_matrix": True, "scan_timing": 1.0, "display_compress": True},
            "log curve, Status M, sensitivity matrix, timing 1, display compression": {**LOG, "scanner": "status_m", "sensitivity_matrix": True, "scan_timing": 1.0, "display_compress": True},
            "log curve, APD, sensitivity matrix, timing 1, common slope": {**LOG, "sensitivity_matrix": True, "scan_timing": 1.0, "common_slope": True}}


def main() -> int:
    chart = cs.babelcolor_chart()
    data = json.loads(fa.SOURCE.read_text(encoding="utf-8"))["sets"]
    result: dict = {"source": "https://filmanalyzer.talkativephotographer.com/browse/ (per-patch values not stored here)", "sets": {}}
    for label, (stock, set_name) in SETS.items():
        rows = data[set_name]
        offsets = sorted({r["exposure_offset"] for r in rows})
        names = [r["patch_name"] for r in rows if r["exposure_offset"] == 0]
        real = {o: np.array([[r["mean_L"], r["mean_a"], r["mean_b_lab"]] for r in rows if r["exposure_offset"] == o]) for o in offsets}
        reference = np.array([[r["reference_L"], r["reference_a"], r["reference_b"]] for r in rows if r["exposure_offset"] == 0])
        options = mp.film_options(mp.RenderSettings(negative=stock, method="apd", scene_light="daylight"), mp.SCAN_CARRIER_PRINT)
        n5, colour = names.index("Neutral 5"), [k for k, n in enumerate(names) if n not in fa.NEUTRALS]
        neutral = [names.index(n) for n in fa.NEUTRALS]
        entry = {"real": {"median_C_by_offset": {str(o): round(float(np.median(np.hypot(*real[o][colour, 1:].T))), 1) for o in offsets},
                          "neutral_b_by_offset": {str(o): real[o][neutral, 2].round(1).tolist() for o in offsets}}, "variants": {}}
        for name, kwargs in VARIANTS.items():
            model = cs.ChartScanPreview(options, chart, **kwargs)
            c = model.negative.c
            daylight = model.negative.light("D55")
            # Both charts use the standard order of the 24 patches; the colour names must agree.
            if [k.lower() for k in chart.labels[:18]] != [nm.lower() for nm in names[:18]]:
                raise ValueError("the patch order of the chart and of the scan differ")
            spectra = chart.reflectance
            ap1 = fa.lab_to_xyz_d50(reference) @ (c.xyz_to_ap1 @ cs.fp.bradford_matrix(fa.D50, c.ap1_to_xyz @ np.ones(3))).T

            def shown(stops: float) -> np.ndarray:
                if SPECTRAL:
                    return fa.srgb_to_lab(model.render_spectra(spectra * 2.0 ** stops, daylight))
                return fa.srgb_to_lab(model.render((ap1 * 2.0 ** stops)[None].astype(np.float32))[0][0])

            shifts = np.linspace(-3.0, 3.0, 61)
            levels = np.array([shown(float(s))[n5, 0] for s in shifts])
            shift = float(np.interp(real[0][n5, 0], np.maximum.accumulate(levels), shifts))
            bracket = {o: shown(shift + o) for o in offsets}
            matched = bracket[0]
            hue = (fa.hue_deg(matched[colour]) - fa.hue_deg(real[0][colour]) + 180.0) % 360.0 - 180.0
            ratio = np.hypot(*matched[colour, 1:].T) / np.hypot(*real[0][colour, 1:].T)
            delta = np.linalg.norm(matched[colour] - real[0][colour], axis=1)
            entry["variants"][name] = {"stops_to_real_neutral_5": round(shift, 2), "delta_e_median": round(float(np.median(delta)), 1),
                                       "hue_difference_abs_median_deg": round(float(np.median(np.abs(hue))), 1), "chroma_ratio_median": round(float(np.median(ratio)), 2),
                                       "median_C_by_offset": {str(o): round(float(np.median(np.hypot(*bracket[o][colour, 1:].T))), 1) for o in offsets},
                                       "neutral_L_by_offset": {str(o): bracket[o][neutral, 0].round(1).tolist() for o in offsets},
                                       "neutral_b_by_offset": {str(o): bracket[o][neutral, 2].round(1).tolist() for o in offsets},
                                       "hue_difference_deg_by_patch": dict(zip([names[k] for k in colour], hue.round(0).tolist())),
                                       "chroma_ratio_by_patch": dict(zip([names[k] for k in colour], ratio.round(2).tolist()))}
            v = entry["variants"][name]
            print(label, name, {k: v[k] for k in ("stops_to_real_neutral_5", "delta_e_median", "hue_difference_abs_median_deg", "chroma_ratio_median", "median_C_by_offset")}, flush=True)
        result["sets"][label] = entry
    # U28: the values of the scans stay local; the results file holds the values of the paths only.
    real = {label: entry.pop("real") for label, entry in result["sets"].items()}
    (cs.REPO_ROOT / "build" / "tmp" / "p10" / "real_summary.json").write_text(json.dumps(real, indent=1) + "\n", encoding="utf-8", newline="\n")
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
