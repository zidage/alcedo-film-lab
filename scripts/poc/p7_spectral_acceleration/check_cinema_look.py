"""Check of rule 'print_cinema_look' on synthetic colours.

Input: none. Output: results/p7_spectral_acceleration/cinema_look.json. Step: P7, ROADMAP U81. CPU only.
Limits, set before the run:
- Output finite and in 0 to 1 on a grid of 33 ** 3 codes.
- A neutral ramp of 1025 codes: luma of the output falls by at most 1e-3 between neighbours.
- Black: each channel at most 1e-3. White: each channel at least 0.99.
- Only cine_look has the rule, of the print materials in the catalog.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

look = mp.fp.look
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "cinema_look.json"


def main() -> int:
    axis = np.linspace(0.0, 1.0, 33)
    grid = look.cinema_look(np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3))
    ramp = look.cinema_look(np.outer(np.linspace(0.0, 1.0, 1025), np.ones(3)))
    luma = ramp.astype(np.float64) @ look.LUMA
    with_rule = sorted(name for name in mp.CATALOG["prints"] if mp.print_conditions(name).get("cinema_look"))
    record = {"grid_finite": bool(np.isfinite(grid).all()), "grid_low": float(grid.min()), "grid_high": float(grid.max()), "ramp_largest_fall": float(max(0.0, -np.diff(luma).min())), "black": ramp[0].tolist(), "white": ramp[-1].tolist(), "print_materials_with_rule": with_rule}
    passed = record["grid_finite"] and record["grid_low"] >= 0.0 and record["grid_high"] <= 1.0 and record["ramp_largest_fall"] <= 1e-3 and max(record["black"]) <= 1e-3 and min(record["white"]) >= 0.99 and with_rule == ["cine_look"]
    record["passed"] = bool(passed)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(record, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
