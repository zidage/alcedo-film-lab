"""Write profiles/printer_filters.json: density curves of the filters of the printer light, from spectral_film_lut.

Input: wratten_filters.py of spectral_film_lut (MIT, ROADMAP U11) at commit bcbcfc68, read as literals. The code of that project does not run. Path: first argument, the src/spectral_film_lut directory of a local clone.
Output: profiles/printer_filters.json, on 1 nm.

Rules: a wavelength with several digitized points takes their mean, and a falling density curve is the running minimum, so a digitized point cannot make the filter denser at a longer wavelength.
Why this filter: the KODAK VISION Color Print Film 2383 data sheet states "Overall filtration should include a UV-absorbing filter, such as a KODAK WRATTEN 2 Filter No. 2B".
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; resampled by this lab"
FILTERS = ("2B",)


def literals(path: Path) -> dict:
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "WRATTEN" and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise ValueError(f"no WRATTEN table in {path}")


def resampled(points: dict) -> dict:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    grid = np.arange(math.ceil(x[0]), math.floor(x[-1]) + 1.0)
    falling = np.minimum.accumulate(np.interp(grid, x, y))
    return {"x": grid.tolist(), "y": falling.round(5).tolist()}


def main() -> int:
    table = literals(Path(sys.argv[1]) / "wratten_filters.py")
    filters = {f"wratten_{name.lower()}": resampled(table[name]) for name in FILTERS}
    out = {"source_document": PROVENANCE, "x_quantity": "wavelength_nm", "y_quantity": "spectral_density", "filters": filters}
    (REPO_ROOT / "profiles" / "printer_filters.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    for name, curve in filters.items():
        x, y = np.array(curve["x"]), np.array(curve["y"])
        print(name, "domain", x[0], x[-1], "density at", {n: round(float(np.interp(n, x, y)), 3) for n in (381, 385, 390, 395, 400, 405, 410, 420, 450, 500, 600, 700)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
