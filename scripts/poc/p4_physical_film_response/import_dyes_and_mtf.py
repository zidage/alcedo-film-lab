"""Add the isolated dye curves and the modulation transfer curves of spectral_film_lut to the negative profiles.

Input: the data files of spectral_film_lut (MIT, ROADMAP U11) at commit bcbcfc68, read as literals; the code of that project does not run.
Path: first argument, the src/spectral_film_lut directory of a local clone.
Output: profiles/kodak_5207.json and kodak_5219.json get the curves cyan_dye, magenta_dye, yellow_dye in the chart spectral_dye_density and a chart modulation_transfer.
profiles/kodak_portra_400.json gets only the chart modulation_transfer, because that project has no isolated dye curves for this stock, and E-4050 does not publish them.
Step: P4, ROADMAP section 8, work items W1 and W4. Run this script after import_cine_profiles.py, which writes the cine profiles again.

Rules: resampled linearly on 1 nm or on 1 cycle/mm inside the digitized domain, no smoothing, no extrapolation. The digitized negative values of a dye curve stay.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; linearly resampled by this lab; not checked against Kodak documents"
FILES = {"kodak_5207": "negative_film/kodak_5207.py", "kodak_5219": "negative_film/kodak_5219.py", "kodak_portra_400": "negative_film/kodak_portra_400.py"}


def literals(path: Path) -> dict:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FilmData":
            return {k.arg: ast.literal_eval(k.value) for k in node.keywords}
    raise ValueError(f"no FilmData in {path}")


def resampled(points: dict) -> dict:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    grid = np.arange(math.ceil(x[0]), math.floor(x[-1]) + 1.0)
    return {"x": grid.tolist(), "y": np.interp(grid, x, y).round(5).tolist()}


def main() -> int:
    source = Path(sys.argv[1])
    for name, relative in FILES.items():
        data = literals(source / relative)
        path = REPO_ROOT / "profiles" / f"{name}.json"
        profile = json.loads(path.read_text(encoding="utf-8"))
        charts = profile["charts"]
        if "spectral_density" in data:
            charts["spectral_dye_density"]["curves"].update(zip(("cyan_dye", "magenta_dye", "yellow_dye"), map(resampled, data["spectral_density"])))
            charts["spectral_dye_density"]["isolated_dye_note"] = "Peak-normalized curves. " + PROVENANCE
        charts["modulation_transfer"] = {"source": PROVENANCE, "x_quantity": "spatial_frequency_cycles_per_mm", "y_quantity": "response", "grid_step": 1.0, "provenance": PROVENANCE,
                                         "curves": dict(zip(("red", "green", "blue"), map(resampled, data["mtf"])))}
        path.write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(name, "dyes" if "spectral_density" in data else "no isolated dyes", "mtf", {k: (v["x"][0], v["x"][-1]) for k, v in charts["modulation_transfer"]["curves"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
