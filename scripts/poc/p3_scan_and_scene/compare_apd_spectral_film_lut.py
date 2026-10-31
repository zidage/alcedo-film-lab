"""Compare the APD responsivities of SMPTE ST 2065-2 with the APD table of spectral_film_lut.

Input: build/tmp/p3/sources/st2065-2/st2065-2a-2020.csv, the local clone build/tmp/baseline/src_sfl/repo at bcbcfc68.
Output: results/p3_scan_and_scene/apd_table_comparison.json.
Step: P3, README section 8. Check (limit set before the run): each table normalized to its sum per channel, max difference <= 1e-4
at the common wavelengths. The file reads the source text and does not import that project.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import read_apd_responsivities  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "build" / "tmp" / "baseline" / "src_sfl" / "repo" / "src" / "spectral_film_lut" / "densiometry.py"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "apd_table_comparison.json"


def main() -> int:
    wavelengths, standard = read_apd_responsivities()
    match = re.search(r"^APD = (\{.*?^\})", SOURCE.read_text(encoding="utf-8"), re.S | re.M)
    table = ast.literal_eval(match.group(1))
    other_wl = np.array(sorted(table), dtype=np.float64)
    other = np.array([table[int(w)] for w in other_wl]).T
    common = np.intersect1d(wavelengths, other_wl)
    a = standard[:, np.isin(wavelengths, common)]
    b = other[:, np.isin(other_wl, common)]
    difference = np.abs(a / a.sum(axis=1, keepdims=True) - b / b.sum(axis=1, keepdims=True)).max()
    peaks = common[a.argmax(axis=1)].tolist()
    result = {"common_nodes": len(common), "range_nm": [float(common[0]), float(common[-1])], "peak_nm_rgb": peaks, "normalized_max_difference": float(difference), "limit": 1e-4, "pass": bool(difference <= 1e-4)}
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
