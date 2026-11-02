"""Checks of rule 'foliage_spectra' on all negatives of the catalog, with synthetic colours and no photo.

Input: stock_catalog.json and the tables of the model. Output: results/p6_python_mvp/foliage_spectra.json. Step: P6, ROADMAP U73.
Each negative runs on the paper of its medium: 2383 for a cine stock, Endura Premier for another stock. There is no product grade, so the input colour reaches the film directly.

| Check | Comparison rule | Limit |
| Neutral | Final sRGB of a grey ramp, rule on against rule off, 8 bit code, largest channel difference | 0 |
| Colours outside the sector | Final sRGB of red, skin, yellow, blue, sky, and magenta, on against off, 8 bit code, largest channel difference | 1 |
| Table steps | Final sRGB along 13 chroma sweeps through the sector, 256 samples each: largest difference between neighbours, in 8 bit code, on minus off | 2 |
The leaf exposure error is a measured property with no limit: log10 of the exposure of the synthetic leaf spectrum over the exposure of the table at the same XYZ.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import mvp_pipeline as mp  # noqa: E402

RESULT = mp.REPO_ROOT / "results" / "p6_python_mvp" / "foliage_spectra.json"
NEUTRAL_LIMIT = 0
OUTSIDE_LIMIT = 1
STEP_LIMIT = 2
OUTSIDE = {"red": (0.45, 0.06, 0.04), "skin": (0.42, 0.27, 0.19), "yellow": (0.6, 0.5, 0.06), "blue": (0.06, 0.12, 0.45), "sky": (0.3, 0.42, 0.65), "magenta": (0.4, 0.06, 0.35)}
FLAT = dict(exposure_ev=0.0, contrast=0.0, saturation=1.0)


def code(image: np.ndarray) -> np.ndarray:
    return (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.int32)


def leaf_spectrum(wavelengths: np.ndarray) -> np.ndarray:
    return 0.035 + 0.125 * np.exp(-0.5 * ((wavelengths - 552.0) / 32.0) ** 2) + 0.45 / (1.0 + np.exp(-(wavelengths - 712.0) / 11.0))


def chroma_sweeps(model: mp.fp.FilmPreview) -> np.ndarray:
    """AP1 values (13, 256, 3): one Y, from the white along 13 directions of u'v' around the leaf colour, up to a u'v' distance of 0.12."""
    c = model.c
    white = c.xyz(c.e_ref)
    white_uv = np.array([4.0 * white[0], 9.0 * white[1]]) / (white[0] + 15.0 * white[1] + 3.0 * white[2])
    leaf = c.xyz(leaf_spectrum(c.wavelengths) * c.e_ref)
    leaf_uv = np.array([4.0 * leaf[0], 9.0 * leaf[1]]) / (leaf[0] + 15.0 * leaf[1] + 3.0 * leaf[2])
    centre = np.degrees(np.arctan2(*(leaf_uv - white_uv)[::-1]))
    angles = np.radians(centre + np.linspace(-60.0, 60.0, 13))
    radius = np.linspace(0.0, 0.12, 256)
    u = white_uv[0] + np.outer(np.cos(angles), radius)
    v = white_uv[1] + np.outer(np.sin(angles), radius)
    xyz = np.stack([9.0 * u / (4.0 * v), np.ones_like(u), (12.0 - 3.0 * u - 20.0 * v) / (4.0 * v)], axis=-1) * 0.18
    return (xyz @ c.xyz_to_ap1.T).astype(np.float32)


def main() -> None:
    pipeline = mp.Pipeline()
    physics = mp.load_physics()
    ramp = (0.18 * 2.0 ** np.linspace(-6.0, 3.0, 64))[None, :, None].repeat(3, axis=2).astype(np.float32)
    outside = np.array(list(OUTSIDE.values()), dtype=np.float32)[None]
    records = {}
    failed = []
    for negative, entry in mp.CATALOG["negatives"].items():
        if physics.get(negative, {}).get("error"):
            records[negative] = {"not_run": physics[negative]["error"]}
            continue
        paper = "kodak_2383" if entry["medium"].lower() == "cine" else "kodak_endura_premier"
        on = replace(mp.RenderSettings(negative=negative, print_material=paper), **FLAT)
        off = replace(on, foliage=False)
        model_on, model_off = pipeline.print_model(on), pipeline.print_model(off)
        wavelengths = model_on.c.wavelengths
        spectrum = leaf_spectrum(wavelengths) * model_on.scene_spectrum
        ap1 = (model_on.c.xyz_to_ap1 @ model_on.c.xyz(spectrum))[None, None].astype(np.float64)
        real = model_on.c.layer_exposure(spectrum[None])[0] * model_on.layer_gain
        sweeps = chroma_sweeps(model_on)
        step_on = np.abs(np.diff(code(pipeline.render_array(sweeps, on)), axis=1)).max()
        step_off = np.abs(np.diff(code(pipeline.render_array(sweeps, off)), axis=1)).max()
        record = {"paper": paper, "red_peak_nm": float(wavelengths[np.argmax(model_on.c.layer_exposure(np.eye(len(wavelengths)))[:, 0])]),
                  "leaf_log10_exposure_error_off": np.log10(real / model_off.layer_exposure(ap1)[0][0, 0]).round(3).tolist(),
                  "leaf_log10_exposure_error_on": np.log10(real / model_on.layer_exposure(ap1)[0][0, 0]).round(3).tolist(),
                  "neutral_largest_8bit": int(np.abs(code(pipeline.render_array(ramp, on)) - code(pipeline.render_array(ramp, off))).max()),
                  "outside_largest_8bit": int(np.abs(code(pipeline.render_array(outside, on)) - code(pipeline.render_array(outside, off))).max()),
                  "sweep_step_on_8bit": int(step_on), "sweep_step_off_8bit": int(step_off)}
        record["passed"] = bool(record["neutral_largest_8bit"] <= NEUTRAL_LIMIT and record["outside_largest_8bit"] <= OUTSIDE_LIMIT and step_on - step_off <= STEP_LIMIT)
        if not record["passed"]:
            failed.append(negative)
        records[negative] = record
        print(negative, json.dumps(record), flush=True)
    RESULT.write_text(json.dumps({"limits": {"neutral": NEUTRAL_LIMIT, "outside": OUTSIDE_LIMIT, "step_increase": STEP_LIMIT}, "failed": failed, "negatives": records}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("failed:", failed)


if __name__ == "__main__":
    main()
