"""W1: what the sources specify about the dyes of each stock: the isolated dye curves against the published neutral, the band split against the isolated curves, and the cause of the largest error of rule 'light_like_spectra'.

Input: the negative profiles, the P2 library. Output: results/p4_physical_film_response/dye_models.json.
Step: P4, README section 8, work item W1. No limit applies: these are measured properties of the sources. Test: if the isolated curves hold the side absorption of analytical dyes with no mask, their sum exceeds the neutral above D-min by the mask that the dyes consumed. If the curves are net of the mask, the sum equals the neutral within the digitization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import lsq_linear

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p2_negative_print"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_preview as fp  # noqa: E402
from check_light_spectra import light_spectra  # noqa: E402

RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "dye_models.json"
WAVELENGTHS = np.arange(420.0, 700.0, 1.0)
REPORT_NM = (420, 450, 500, 550, 600, 650, 690)
DYES = ("cyan_dye", "magenta_dye", "yellow_dye")


def curves_of(profile: str) -> dict:
    return fp.p0.load_profile(profile)["charts"]["spectral_dye_density"]["curves"]


def on_grid(curve: dict) -> np.ndarray:
    return np.interp(WAVELENGTHS, curve["x"], curve["y"])


def neutral_fit(neutral: np.ndarray, dyes: np.ndarray) -> dict:
    fit = lsq_linear(dyes, neutral, bounds=(0.0, 9.0))
    residual = dyes @ fit.x - neutral
    return {"amounts": fit.x.round(3).tolist(), "rms_residual": round(float(np.sqrt(np.mean(residual ** 2))), 4), "largest_residual": round(float(np.abs(residual).max()), 4)}


def main() -> int:
    result: dict = {"isolated_curves_against_neutral": {}, "band_split_against_isolated": {}, "portra_neutral_with_cine_dyes_comparison": {}}
    for name in ("kodak_5207", "kodak_5219"):
        c = curves_of(name)
        neutral = on_grid(c["midscale_neutral"]) - on_grid(c["minimum_density"])
        dyes = np.stack([on_grid(c[d]) for d in DYES], axis=1)
        result["isolated_curves_against_neutral"][name] = {**neutral_fit(neutral, dyes), "lowest_value_per_dye": dyes.min(axis=0).round(3).tolist()}
        split, info = fp.p0.band_split_dyes(WAVELENGTHS, neutral)
        amounts = np.array(neutral_fit(neutral, dyes)["amounts"])
        result["band_split_against_isolated"][name] = {"cut_points": info, **{d: {str(nm): {"band_split": round(float(np.interp(nm, WAVELENGTHS, split[k])), 3), "isolated": round(float(np.interp(nm, WAVELENGTHS, amounts[k] * dyes[:, k])), 3)} for nm in REPORT_NM} for k, d in enumerate(DYES)}}
    portra = curves_of("kodak_portra_400")
    neutral = on_grid(portra["midscale_neutral"]) - on_grid(portra["minimum_density"])
    for name in ("kodak_5207", "kodak_5219"):
        c = curves_of(name)
        result["portra_neutral_with_cine_dyes_comparison"][name] = neutral_fit(neutral, np.stack([on_grid(c[d]) for d in DYES], axis=1))
    # The largest error of rule 'light_like_spectra': with and without the smoothing of the table.
    with_smoothing = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS["5207_2383"], **fp.DARKROOM, "scene_light": "D55", "light_spectra": True}))
    no_smoothing = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS["5207_2383"], **fp.DARKROOM, "scene_light": "D55", "light_spectra": True, "uv_smooth": (0.0, 0.0)}))
    table_error = {}
    c = with_smoothing.c
    d55 = with_smoothing.light("D55")
    wb = fp.bradford_matrix(c.xyz(d55), c.ap1_to_xyz @ np.ones(3))
    for name in ("Planck 1800 K", "Planck 2500 K"):
        spectrum = light_spectra(with_smoothing, d55)[name]
        spectrum = 0.18 * spectrum / c.xyz(spectrum)[1]
        ap1 = c.xyz_to_ap1 @ wb @ c.xyz(spectrum)
        true = with_smoothing.layer_gain * c.layer_exposure(spectrum)
        table_error[name] = {"with_table_smoothing": np.log10(with_smoothing.layer_exposure(ap1[None])[0][0] / true).round(4).tolist(), "no_table_smoothing": np.log10(no_smoothing.layer_exposure(ap1[None])[0][0] / true).round(4).tolist(), "ap1": ap1.round(4).tolist()}
    result["planck_error_and_table_smoothing"] = table_error
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("isolated_curves_against_neutral", "portra_neutral_with_cine_dyes_comparison", "planck_error_and_table_smoothing")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
