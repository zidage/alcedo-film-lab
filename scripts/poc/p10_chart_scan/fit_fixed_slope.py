"""Values of rule 'fixed_scan_slope' of chart_scan.py (step P10, round 6, ROADMAP U89).

Input: the viewer of step P6 (mvp_pipeline.py), method chart_scan with slope 'stock', the eight stocks of ACCEPTED_STOCKS, scene light 'reference'.
Output: results/p10_chart_scan/fixed_slope.json: the Status M slope of rule 'chart_straight_line' of each stock, their mean per channel, and the
largest difference of that mean to FIXED_STATUS_M_SLOPE. A difference above 1e-6 (the rounding of the constants) stops with an error.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR.parent / "p6_mvp_gui"))
sys.path.insert(0, str(SCRIPT_DIR))
import chart_scan as cs  # noqa: E402
import mvp_pipeline as mp  # noqa: E402

OUTPUT = REPO_ROOT / "results" / "p10_chart_scan" / "fixed_slope.json"
LIMIT = 1e-6


def main() -> int:
    pipe = mp.Pipeline()
    slopes = {}
    for stock in mp.ACCEPTED_STOCKS:
        settings = replace(mp.RenderSettings(negative=stock, method="chart_scan", scene_light=mp.REFERENCE_LIGHT), chart_scan_slope="stock")
        slopes[stock] = pipe.chart_scan_model(settings).straight_slope.tolist()
        print(stock, np.round(slopes[stock], 5), flush=True)
    mean = np.mean(list(slopes.values()), axis=0)
    difference = float(np.abs(mean - np.array(cs.FIXED_STATUS_M_SLOPE)).max())
    record = {"rule": "fixed_scan_slope", "scene_light": mp.REFERENCE_LIGHT, "unit": "Status M density per stop", "stock_slopes": slopes,
              "mean": mean.tolist(), "constants": list(cs.FIXED_STATUS_M_SLOPE), "largest_difference": difference, "limit": LIMIT}
    OUTPUT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("mean", np.round(mean, 6), "difference", f"{difference:.2g}")
    if difference > LIMIT:
        raise ValueError(f"FIXED_STATUS_M_SLOPE differs from the mean by {difference:.3g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
