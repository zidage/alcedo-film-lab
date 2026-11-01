"""Inhibition steps, with a full-size or a half-size blur, for every negative of the catalog, at two image sizes, against 4 full-size steps of step P6. The limits are those of check_fast_image_steps.py: mean 0.5, p99.9 2.0, largest 5.0 of an 8 bit code value.

Input: stock_catalog.json, stock_physics.json, an AP1 array at 2048 pixels, and a RAW file (first argument) at 6000 pixels. Output: results/p7_spectral_acceleration/inhibition_steps.json, and a line per negative on stdout. Step: P7, ROADMAP U70.
Each negative uses its default print: 2383 for a cine negative, Endura for a photo negative.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mvp_pipeline as mp  # noqa: E402

from check_fast_image_steps import full_size_inhibited  # noqa: E402

fp = mp.fp
fk = fp.fk
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "inhibition_steps.json"
ARRAY_2048 = "p6_spektrafilm_audit/check_input_2048"
LIMITS = {"mean": 0.5, "p999": 2.0, "largest": 5.0}
CASES = ((1, "half"), (2, "half"), (1, "full"), (2, "full"))
HALF_INHIBITED = fp.FilmPreview._inhibited_image


def default_print(negative: str) -> str:
    return "kodak_2383" if str(mp.CATALOG["negatives"][negative].get("medium", "")).lower() == "cine" else "kodak_endura_premier"


def main() -> int:
    default = mp.RenderSettings()
    start = fp.FilmPreview(mp.film_options(default))
    sources = {"2048": np.ascontiguousarray(np.load(REPO_ROOT / "build" / "tmp" / f"{ARRAY_2048}.npy"), dtype=np.float32), "6000": mp.decode_raw(Path(sys.argv[1]), start.c, 6000)[0]}
    graded = {size: np.ascontiguousarray(fk.product_grade(image, float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32) for size, image in sources.items()}
    physics = mp.load_physics()
    results: dict = {"limits": LIMITS, "negatives": {}}
    for negative in mp.CATALOG["negatives"]:
        if physics.get(negative, {}).get("error"):
            continue
        model = fp.FilmPreview(mp.film_options(replace(default, negative=negative, print_material=default_print(negative))))
        row: dict = {"inhibition_total": [round(float(v), 4) for v in model.options.inhibition_total]}
        for size, image in graded.items():
            fp.FilmPreview._inhibited_image = full_size_inhibited
            fp.INHIBITION_STEPS_IMAGE = 4
            reference = np.asarray(model.render(image)[0], dtype=np.float64)
            for steps, blur in CASES:
                fp.INHIBITION_STEPS_IMAGE = steps
                fp.FilmPreview._inhibited_image = HALF_INHIBITED if blur == "half" else full_size_inhibited
                d = np.abs(np.asarray(model.render(image)[0], dtype=np.float64) - reference).max(axis=-1) * 255.0
                entry = {"mean": round(float(d.mean()), 3), "p999": round(float(np.percentile(d, 99.9)), 3), "largest": round(float(d.max()), 3)}
                entry["pass"] = all(entry[k] <= v for k, v in LIMITS.items())
                row[f"{size} px, {steps} {blur}"] = entry
        results["negatives"][negative] = row
        print(negative, row["inhibition_total"], *(f"| {k.replace(' px,', '')}: {v['mean']}/{v['p999']}/{v['largest']}{'' if v['pass'] else ' F'}" for k, v in row.items() if k != "inhibition_total"), flush=True)
    RESULT.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8", newline="\n")
    for size in graded:
        for steps, blur in CASES:
            key = f"{size} px, {steps} {blur}"
            print(key, "fail:", [n for n, r in results["negatives"].items() if not r[key]["pass"]], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
