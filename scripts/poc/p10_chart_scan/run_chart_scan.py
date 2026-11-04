"""Calibration and checks of rule 'chart_calibrated_scan' (step P10, ROADMAP U87). No photo.

Input: chart_scan.py, the BabelColor chart, the rawtoaces training spectra of P1 (a second set that the fit does not see).
Output: results/p10_chart_scan/chart_scan.json. Descriptive; no limit is set before the run.
Per stock: the kept range of the grey scale per channel, the matrix, CIEDE2000 of the chart and of the second set against their targets
(with and without the matrix), and the chroma of a neutral of the image path (an AP1 grey through the reconstruction, not a flat grey).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import chart_scan as cs  # noqa: E402
import mvp_pipeline as mp  # noqa: E402

RESULT = cs.REPO_ROOT / "results" / "p10_chart_scan" / "chart_scan.json"
STOCKS = ("kodak_5207", "kodak_5219", "kodak_portra_400", "kodak_portra_160", "kodak_ektar_100", "fuji_superia_xtra_400")


def summary(de: np.ndarray) -> dict:
    return {"mean": round(float(de.mean()), 2), "p90": round(float(np.percentile(de, 90)), 2), "max": round(float(de.max()), 2)}


def options(negative: str):
    return mp.film_options(mp.RenderSettings(negative=negative, method="apd"), mp.SCAN_CARRIER_PRINT)


def check(model: cs.ChartScanPreview, reflectance: np.ndarray) -> np.ndarray:
    e, _ = model.equivalent_exposure(model.patch_apd(reflectance))
    return cs.delta_e2000(model.lab_of_ap1(model.patch_ap1(reflectance)), model.lab_of_ap1(e @ model.matrix.T))


def main() -> int:
    chart = cs.babelcolor_chart()
    second = cs.sd.load_rawtoaces_training()
    report = {"chart": chart.name, "second_set": second.name, "second_set_patches": int(len(second.reflectance)), "stocks": {}}
    for negative in STOCKS:
        entry = {}
        for matrix in (False, True):
            model = cs.ChartScanPreview(options(negative), chart, matrix=matrix)
            name = "curves_and_matrix" if matrix else "curves_only"
            stops = np.array([-4.0, -2.0, 0.0, 2.0, 4.0])
            grey = (cs.GREY * 2.0 ** stops)[:, None] * np.ones(3)
            scene, _ = model.scene_ap1(grey.astype(np.float32))
            neutral_lab = model.lab_of_ap1(np.maximum(scene, 1e-9))
            entry[name] = {"chart_de2000": summary(check(model, chart.reflectance)), "second_set_de2000": summary(check(model, second.reflectance)),
                           "image_neutral_chroma_at_stops": dict(zip([f"{s:g}" for s in stops], np.round(np.hypot(neutral_lab[:, 1], neutral_lab[:, 2]), 2).tolist())),
                           "image_neutral_stops_out": np.round(np.log2(scene[:, 1] / cs.GREY), 3).tolist()}
            if matrix:
                entry["matrix"] = np.round(model.matrix, 4).tolist()
                entry["calibration_light"] = model.light_name
                entry["grey_scale_kept_stops"] = {ch: [round(float(s[0]), 3), round(float(s[-1]), 3)] for ch, s in zip("RGB", model.ramp_stops)}
        report["stocks"][negative] = entry
        print(negative, json.dumps(entry), flush=True)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
