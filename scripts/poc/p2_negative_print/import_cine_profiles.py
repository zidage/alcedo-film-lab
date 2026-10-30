"""Write profiles of KODAK VISION3 250D 5207, VISION3 500T 5219 and VISION 2383 from spectral_film_lut.

Input: the data files of spectral_film_lut (MIT, README U11) at commit bcbcfc68, read as literals. The code
of that project does not run. Path: first argument, the src/spectral_film_lut directory of a local clone.
Output: profiles/kodak_5207.json, kodak_5219.json, kodak_2383.json, with the schema of the P0 profiles.

Step: P2, README U19. The values are the digitization of spectral_film_lut, not of this lab. Rules:
- resampled linearly on 1 nm or 0.01 log10 lux-seconds inside the digitized domain, no extrapolation;
- 5207: its curve axis is in stops around the exposure 12.5 / ISO lux seconds (spectral_film_lut definition);
- a rising curve keeps its running maximum, because a digitized point can fall by a small amount
  (the largest fall is printed).
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
FILES = {"kodak_5207": ("negative_film/kodak_5207.py", "KODAK VISION3 250D Color Negative Film 5207"),
         "kodak_5219": ("negative_film/kodak_5219.py", "KODAK VISION3 500T Color Negative Film 5219"),
         "kodak_2383": ("print_film/kodak_2383.py", "KODAK VISION Color Print Film 2383")}
PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; linearly resampled by this lab"


def literals(path: Path) -> dict:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FilmData":
            return {k.arg: ast.literal_eval(k.value) for k in node.keywords}
    raise ValueError(f"no FilmData in {path}")


def spectral(points: dict) -> dict:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    grid = np.arange(math.ceil(x[0]), math.floor(x[-1]) + 1.0)
    return {"x": grid.tolist(), "y": np.interp(grid, x, y).round(5).tolist()}


def characteristic(points: dict, to_log_h) -> tuple[dict, float]:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    log_h = to_log_h(x)
    grid = np.arange(math.ceil(log_h[0] * 100) / 100, log_h[-1], 0.01)
    values = np.interp(grid, log_h, y)
    rising = np.maximum.accumulate(values)
    return {"x": grid.round(4).tolist(), "y": rising.round(5).tolist()}, float((rising - values).max())


def main() -> int:
    source = Path(sys.argv[1])
    for name, (rel, material) in FILES.items():
        d = literals(source / rel)
        base = d.get("exposure_base", 10)
        reference = math.log10(12.5 / d["iso"]) if "iso" in d else 0.0
        to_log_h = (lambda x: x * math.log10(base) + reference) if base != 10 else (lambda x: x)
        curves, falls = {}, {}
        for channel, points in zip(("red", "green", "blue"), d["sensiometric_curve"]):
            curves[channel], falls[channel] = characteristic(points, to_log_h)
        dyes = [spectral(c) for c in d["spectral_density"]]
        charts = {
            "characteristic": {"source": PROVENANCE, "x_quantity": "log10_exposure_lux_s", "y_quantity": f"{d['density_measure']}_density", "grid_step": 0.01,
                               "provenance": PROVENANCE, "curves": curves},
            "spectral_sensitivity": {"source": PROVENANCE, "x_quantity": "wavelength_nm", "y_quantity": "log10_sensitivity", "grid_step": 1.0, "provenance": PROVENANCE,
                                     "curves": {layer: spectral(c) for layer, c in zip(("cyan_forming_layer", "magenta_forming_layer", "yellow_forming_layer"), d["log_sensitivity"])}},
        }
        if d["stage"] == "camera":
            dye_curves = {"midscale_neutral": spectral(d["d_ref_sd"]), "minimum_density": spectral(d["d_min_sd"])}
            # the same wavelengths on both, as the band split of the P0 model needs
            lo = max(dye_curves["midscale_neutral"]["x"][0], dye_curves["minimum_density"]["x"][0])
            hi = min(dye_curves["midscale_neutral"]["x"][-1], dye_curves["minimum_density"]["x"][-1])
            for curve in dye_curves.values():
                keep = [i for i, w in enumerate(curve["x"]) if lo <= w <= hi]
                curve["x"], curve["y"] = [curve["x"][i] for i in keep], [curve["y"][i] for i in keep]
        else:
            dye_curves = dict(zip(("cyan_dye", "magenta_dye", "yellow_dye"), dyes))
        charts["spectral_dye_density"] = {"source": PROVENANCE, "x_quantity": "wavelength_nm", "y_quantity": "spectral_density", "grid_step": 1.0, "provenance": PROVENANCE, "curves": dye_curves}
        out = {"material": material, "source_document": PROVENANCE, "charts": charts,
               "redistribution_note": "Values from spectral_film_lut (MIT); see THIRD_PARTY_NOTICES.md and profiles/README.md."}
        (REPO_ROOT / "profiles" / f"{name}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(name, "log H range", curves["green"]["x"][0], curves["green"]["x"][-1], "D range", curves["green"]["y"][0], curves["green"]["y"][-1], "largest fall", {k: round(v, 4) for k, v in falls.items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
