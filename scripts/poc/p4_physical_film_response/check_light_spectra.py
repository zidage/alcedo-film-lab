"""W1: rule 'light_like_spectra': the layer exposure of light-like spectra against the true spectrum, and the cost on measured reflectances.

Input: the P2 library and the P1 reflectance sets, no photo. Output: results/p4_physical_film_response/light_spectra.json.
Step: P4, ROADMAP section 8, work item W1. Limits set before the first run with the rule:
- light-like spectra (daylight 8000, 12000, 20000 K; D55 x lambda^-2, lambda^-4; Planckian 1800, 2500 K; D55 x lambda^+4), each one white balanced by the scene light D55: |reconstruction - true| <= 0.03 log10 in each layer, on 5207;
- ISSA skin: p95 of |reconstruction - true| grows by at most 0.005 log10 in each layer;
- XYZ of the table nodes inside AP1: p99 relative error at most 0.015 (P3 section 13.1 reports 1.2 % at this percentile for the smoothing alone).
No limit applies to the other measured sets. Their change is the stated cost of the rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p2_negative_print"))
import film_preview as fp  # noqa: E402

RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "light_spectra.json"
LIMIT_LIGHT = 0.03
LIMIT_SKIN_GROWTH = 0.005


def light_spectra(n: fp.FilmPreview, d55: np.ndarray) -> dict[str, np.ndarray]:
    wl = n.c.wavelengths
    planck = lambda t: wl ** -5.0 / np.expm1(1.4388e7 / (wl * t))  # noqa: E731
    return {"daylight 8000 K": fp.p0.cie_daylight_relative_spd(8000.0, wl), "daylight 12000 K": fp.p0.cie_daylight_relative_spd(12000.0, wl), "daylight 20000 K": fp.p0.cie_daylight_relative_spd(20000.0, wl),
            "D55 x lambda^-2": d55 * (wl / 550.0) ** -2, "D55 x lambda^-4": d55 * (wl / 550.0) ** -4, "Planck 1800 K": planck(1800.0), "Planck 2500 K": planck(2500.0), "D55 x lambda^+4": d55 * (wl / 550.0) ** 4}


def errors(n: fp.FilmPreview) -> dict:
    c = n.c
    wl = c.wavelengths
    d55 = n.light("D55")
    wb = fp.bradford_matrix(c.xyz(d55), c.ap1_to_xyz @ np.ones(3))
    lights = {}
    for name, spectrum in light_spectra(n, d55).items():
        spectrum = 0.18 * spectrum / c.xyz(spectrum)[1]
        ap1 = c.xyz_to_ap1 @ wb @ c.xyz(spectrum)
        lights[name] = np.log10(n.layer_exposure(ap1[None])[0][0] / (n.layer_gain * c.layer_exposure(spectrum))).round(4).tolist()
    measured = {}
    for name, dataset in fp.sd.load_all_reflectance_sets().items():
        rho = np.array([np.interp(wl, fp.sd.GRID_NM, r) for r in dataset.reflectance])
        radiance = rho * d55[None]
        y = radiance @ c.w_xyz[1]
        keep = y > 1e-3
        radiance = 0.18 * radiance[keep] / y[keep, None]
        ap1 = (radiance @ c.w_xyz.T) @ wb.T @ c.xyz_to_ap1.T
        error = np.log10(n.layer_exposure(ap1)[0] / (n.layer_gain * c.layer_exposure(radiance)))
        measured[name] = {"records": int(keep.sum()), "abs_p50": np.percentile(np.abs(error), 50, axis=0).round(4).tolist(), "abs_p95": np.percentile(np.abs(error), 95, axis=0).round(4).tolist()}
    return {"lights": lights, "measured": measured}


def main() -> int:
    extra = dict(scene_light="D55")
    before = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS["5207_2383"], **fp.DARKROOM, **extra}))
    after = fp.FilmPreview(fp.FilmOptions(**{**fp.STOCKS["5207_2383"], **fp.DARKROOM, **extra, "light_spectra": True}))
    c = after.c
    result = {"before": errors(before), "after": errors(after)}
    # XYZ of the final table under the reference light, at the nodes inside AP1.
    path = fp.CACHE_DIR / f"reflectance_over_uv_light_{after.options.uv_smooth[0]}_{after.options.uv_smooth[1]}.npy"
    rho = np.load(path).astype(np.float64)
    u, v = np.meshgrid(*fp.FilmPreview.uv_axes(), indexing="ij")
    uu, vv = u.ravel(), np.maximum(v.ravel(), 1e-3)
    xyz = np.stack([9 * uu / (4 * vv), np.ones_like(uu), (12 - 3 * uu - 20 * vv) / (4 * vv)], axis=-1)
    inside = ((xyz @ c.xyz_to_ap1.T) >= 0.0).all(axis=1)
    relative = np.abs(rho[inside] @ (c.w_xyz * c.e_ref).T - xyz[inside]).max(axis=1) / np.abs(xyz[inside]).max(axis=1)
    result["table_xyz_relative_error_inside_ap1"] = {"p50": float(np.percentile(relative, 50)), "p99": float(np.percentile(relative, 99)), "max": float(relative.max()), "nodes": int(inside.sum())}
    wl = c.wavelengths
    shape = rho.reshape(fp.UV_NODES, fp.UV_NODES, -1)
    result["family_at_sky_node"] = {}
    d55 = after.light("D55")
    for name, spectrum in (("D55 x lambda^-4", d55 * (wl / 550.0) ** -4),):
        wb = fp.bradford_matrix(c.xyz(d55), c.ap1_to_xyz @ np.ones(3))
        node = wb @ c.xyz(spectrum)
        uv = np.array([4 * node[0], 9 * node[1]]) / (node[0] + 15 * node[1] + 3 * node[2])
        i, j = int(round(uv[0] / fp.UV_MAX[0] * (fp.UV_NODES - 1))), int(round(uv[1] / fp.UV_MAX[1] * (fp.UV_NODES - 1)))
        old = before._load_reflectance_table().reshape(fp.UV_NODES, fp.UV_NODES, -1)[i, j].astype(np.float64)
        shape_true = np.divide(spectrum, d55, out=np.zeros_like(wl), where=d55 > 0.0)
        scale = shape[i, j] @ (c.w_xyz[1] * c.e_ref) / (shape_true @ (c.w_xyz[1] * c.e_ref))
        result["family_at_sky_node"][name] = {str(nm): {"true": round(float(scale * np.interp(nm, wl, shape_true)), 3), "rule": round(float(np.interp(nm, wl, shape[i, j])), 3), "measured_prior": round(float(np.interp(nm, wl, old)), 3)} for nm in (420, 450, 500, 550, 600, 650, 700)}
    light_ok = all(abs(v) <= LIMIT_LIGHT for values in result["after"]["lights"].values() for v in values)
    skin = np.array(result["after"]["measured"]["issa_skin"]["abs_p95"]) - np.array(result["before"]["measured"]["issa_skin"]["abs_p95"])
    result["skin_abs_p95_growth"] = skin.round(4).tolist()
    result["pass"] = {"light_like_spectra": light_ok, "skin": bool((skin <= LIMIT_SKIN_GROWTH).all()), "table_xyz": result["table_xyz_relative_error_inside_ap1"]["p99"] <= 0.015}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=0)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
