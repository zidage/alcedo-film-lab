"""Neutral exposure and density checks, source-uncertainty variants, and the dense-integration
convergence study of step P0.

Input: the profiles and sources that film_spectral_reference.py reads.
Output: results/p0_data_and_reference/
- checks.json: each check with its rule, tolerance, measured values, and result.
- uncertainty.json: the effect of each inferred field on the checks.
- negative_dye_basis.json: the inferred negative dye basis and the cyan peak scan.
- neutral_ramp.json: the end-to-end neutral exposure ramp (camera to viewed print).
- integration_convergence.json: error against the 0.1 nm reference for each wavelength step.

Step: P0 (data and reference). The tolerances below were set before the first run of this script.
"""

from __future__ import annotations

import itertools
import json
import platform
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import scipy

# The scripts run with python -I, which does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_spectral_reference as ref  # noqa: E402

RESULT_DIR = ref.REPO_ROOT / "results" / "p0_data_and_reference"

# Tolerances (set before the evaluation).
TOL_LINEARITY_REL = 1e-12  # one stop more exposure doubles each layer exposure
TOL_SPEED_POINT_LOG_H = 0.10  # 1/3 stop: sensitivity chart against characteristic chart
TOL_DMIN_STATUS_M = 0.03  # Status M of the D-min spectrum against the curve D-min
TOL_MIDSCALE_LOG_H_SPREAD = 0.10  # same exposure for the three channels of the midscale neutral
TOL_PRINT_NEUTRAL_CHROMA = 2.0  # C*ab of a Status A neutral print under D50
TOL_DAYLIGHT_FORMULA_REL = 2e-3  # D65 by the daylight formula against the CIE D65 table (380-780 nm)
TOL_BASE_ONCE = 1e-12
TOL_INTEGRATION_DENSITY = 1e-3  # density or log10 exposure
TOL_INTEGRATION_DELTA_E = 0.1  # Delta E*ab

REFERENCE_STEP_NM = 0.1
TEST_STEPS_NM = [1.0, 2.0, 5.0, 10.0, 20.0]
RAMP_LOG_H = np.round(np.arange(-3.3, 0.41, 0.1), 2)


def jsonable(value):
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, (np.floating, float)):
        return float(f"{float(value):.7g}")
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def write(name: str, data: dict) -> None:
    (RESULT_DIR / name).write_text(json.dumps(jsonable(data), indent=1) + "\n", encoding="utf-8", newline="\n")


def daylight_speed_point(model: ref.ReferenceModel, relative_spd: np.ndarray) -> np.ndarray:
    """log10 lux-seconds at which Q_i = 1 for an exposure with this spectrum (R, G, B layers)."""
    exposure = model.spectral_exposure_for_luminous_exposure(relative_spd, np.array([1.0]))
    return -np.log10(model.negative_layer_exposure(exposure)[0])


def midscale_matched_log_h(model: ref.ReferenceModel, status_m: np.ndarray) -> np.ndarray:
    return np.array([c.log_h_at(float(d)) for c, d in zip(model.negative_curves.values(), status_m)])


def neutral_checks(model: ref.ReferenceModel) -> dict:
    checks = {}

    # C1: linearity of the layer exposure.
    exposure = model.spectral_exposure_for_luminous_exposure(model.camera_light, np.array([0.01, 0.02]))
    q = model.negative_layer_exposure(exposure)
    rel = np.abs(q[1] / q[0] - 2.0) / 2.0
    checks["one_stop_doubles_layer_exposure"] = {
        "rule": "Q(2 H) / Q(H) = 2 for each layer, relative error",
        "tolerance": TOL_LINEARITY_REL, "measured": rel, "passes": bool(rel.max() <= TOL_LINEARITY_REL)}

    # C2: speed point from the sensitivity chart against the characteristic chart.
    daylight = daylight_speed_point(model, model.camera_light)
    diff = daylight - model.negative_criterion_log_h
    checks["speed_point_sensitivity_against_characteristic"] = {
        "rule": ("log10 lux-seconds of D55 light at which Q_i = 1 (sensitivity chart, CIE 1931 V(lambda), 683 lm/W) "
                 "minus log10 H where the characteristic curve is 0.2 above its D-min; channels R, G, B"),
        "assumption": "'Daylight' = CIE D55; same exposure time (1/50 s) on both charts",
        "tolerance_log_h": TOL_SPEED_POINT_LOG_H,
        "sensitivity_chart_log_h": daylight, "characteristic_chart_log_h": model.negative_criterion_log_h,
        "difference_log_h": diff, "difference_stops": diff / np.log10(2.0),
        "passes": bool(np.abs(diff).max() <= TOL_SPEED_POINT_LOG_H)}

    # C3: D-min spectrum against the curve D-min (Status M).
    dmin_m = model.status_density(model.negative_dmin, model.w_status_m)
    checks["dmin_spectrum_status_m_against_curve"] = {
        "rule": "Status M density of the digitized D-min spectrum minus the characteristic-curve D-min; R, G, B",
        "tolerance": TOL_DMIN_STATUS_M, "spectrum_status_m": dmin_m, "curve_dmin": model.negative_curve_dmin,
        "difference": dmin_m - model.negative_curve_dmin,
        "passes": bool(np.abs(dmin_m - model.negative_curve_dmin).max() <= TOL_DMIN_STATUS_M)}

    # C4: midscale neutral spectrum against the characteristic curves.
    mid_m = model.status_density(model.negative_midscale, model.w_status_m)
    at_ref = np.array([c.density_at(model.options.midscale_log_h) for c in model.negative_curves.values()])
    matched = midscale_matched_log_h(model, mid_m)
    above_spectrum = mid_m - dmin_m
    matched_above = np.array([c.log_h_at(c.d_min + float(a)) for c, a in zip(model.negative_curves.values(), above_spectrum)])
    checks["midscale_neutral_status_m_against_curve"] = {
        "rule": ("Status M of the midscale-neutral spectrum; the log10 H at which each curve has that density; "
                 "the spread of the three log10 H values"),
        "tolerance_spread_log_h": TOL_MIDSCALE_LOG_H_SPREAD,
        "spectrum_status_m": mid_m, "curve_at_log_h_ref": at_ref, "log_h_ref": model.options.midscale_log_h,
        "difference_at_log_h_ref": mid_m - at_ref,
        "matched_log_h": matched, "matched_log_h_spread": float(np.ptp(matched)),
        "density_above_dmin_of_spectra": above_spectrum,
        "matched_log_h_of_density_above_dmin": matched_above,
        "matched_log_h_above_dmin_spread": float(np.ptp(matched_above)),
        "passes": bool(np.ptp(matched) <= TOL_MIDSCALE_LOG_H_SPREAD)}

    # C5: Status A neutral print and its color under D50.
    white = model.white_xyz()
    rows = []
    for d in np.round(np.arange(0.1, 2.01, 0.1), 2):
        b = model.print_dye_amounts(np.array([d, d, d]))
        lab = ref.xyz_to_lab(model.viewed_xyz(model.print_spectral_density(b)), white)
        rows.append({"status_a": d, "dye_amounts_cmy": b, "lab_d50": lab, "chroma": float(np.hypot(lab[1], lab[2]))})
    max_chroma = max(r["chroma"] for r in rows)
    checks["status_a_neutral_print_chroma_d50"] = {
        "rule": ("solve the paper dye amounts for Status A R = G = B = d on a flat base of "
                 f"{model.options.paper_base_density} density; C*ab under D50 against the perfect diffuser"),
        "tolerance_chroma": TOL_PRINT_NEUTRAL_CHROMA, "max_chroma": max_chroma, "rows": rows,
        "passes": bool(max_chroma <= TOL_PRINT_NEUTRAL_CHROMA)}

    # C6: the film base is counted once.
    zero = model.negative_spectral_density(np.zeros(3))
    base_diff = float(np.abs(zero - model.negative_dmin).max())
    checks["film_base_counted_once"] = {
        "rule": "negative spectral density at zero dye amounts equals the D-min spectrum (no second base term)",
        "tolerance": TOL_BASE_ONCE, "max_abs_difference": base_diff, "passes": base_diff <= TOL_BASE_ONCE}

    # C7: D65 by the daylight formula against the CIE table.
    wl = model.grid.wavelengths
    band = (wl >= 380) & (wl <= 780)
    d65_formula = ref.cie_daylight_relative_spd(6500.0, wl)
    rel65 = np.abs(d65_formula[band] / model.illuminants["D65"][band] - 1.0).max()
    checks["daylight_formula_d65_against_cie_table"] = {
        "rule": "CIE daylight formula at nominal 6500 K against CIE_std_illum_D65.csv, 380-780 nm, max relative difference",
        "tolerance": TOL_DAYLIGHT_FORMULA_REL, "measured": float(rel65), "passes": bool(rel65 <= TOL_DAYLIGHT_FORMULA_REL)}
    return checks


def neutral_ramp(model: ref.ReferenceModel) -> dict:
    white = model.white_xyz()
    exposure = model.spectral_exposure_for_luminous_exposure(model.camera_light, 10.0 ** RAMP_LOG_H)
    q = model.negative_layer_exposure(exposure)
    status_m = model.negative_status_m_from_layer_exposure(q)
    a = model.negative_dye_amounts(status_m)
    neg = model.negative_spectral_density(a)
    paper_log_h = model.paper_log_exposure(neg)
    status_a = model.paper_status_a(neg)
    b = model.print_dye_amounts(status_a)
    xyz = model.viewed_xyz(model.print_spectral_density(b))
    lab = ref.xyz_to_lab(xyz, white)
    xyz_d65 = model.viewed_xyz(model.print_spectral_density(b), "D65")
    finite = all(np.all(np.isfinite(v)) for v in (q, status_m, a, neg, paper_log_h, status_a, b, xyz))
    # Slope of the paper log exposure against the scene log exposure at the midscale (+-0.1 log H).
    mid = int(np.argmin(np.abs(RAMP_LOG_H - model.options.midscale_log_h)))
    printing_gamma = -(paper_log_h[mid + 1] - paper_log_h[mid - 1]) / (RAMP_LOG_H[mid + 1] - RAMP_LOG_H[mid - 1])
    status_m_gamma = (status_m[mid + 1] - status_m[mid - 1]) / (RAMP_LOG_H[mid + 1] - RAMP_LOG_H[mid - 1])
    paper_top = np.array([c.log_h[int(np.argmax(c.density))] for c in model.paper_curves.values()])

    # Diagnostic: the paper alone. The three paper layers get the same log exposure change from the
    # midscale point (each at Status A = target), so any color comes from the paper curves and dyes.
    paper_mid = np.array([c.log_h_at(model.options.print_midscale_status_a) for c in model.paper_curves.values()])
    offsets = paper_log_h[:, :1] - paper_log_h[mid, 0]
    paper_only_log_h = paper_mid[None, :] + offsets
    paper_only_a = np.stack([c.density_at(paper_only_log_h[:, k]) for k, c in enumerate(model.paper_curves.values())], axis=-1)
    paper_only_lab = ref.xyz_to_lab(model.viewed_xyz(model.print_spectral_density(model.print_dye_amounts(paper_only_a))), white)
    return {
        "scene": "CIE D55 neutral, luminous exposure 10^log_h lux-seconds",
        "log_h": RAMP_LOG_H, "negative_layer_exposure_rgb": q, "negative_status_m_rgb": status_m,
        "negative_dye_amounts_cmy": a, "paper_log_exposure_rgb": paper_log_h, "print_status_a_rgb": status_a,
        "print_dye_amounts_cmy": b, "print_xyz_d50": xyz, "print_lab_d50": lab,
        "print_chroma_d50": np.hypot(lab[:, 1], lab[:, 2]), "print_xyz_d65": xyz_d65,
        "all_finite": finite,
        "lightness_increases_with_exposure": bool(np.all(np.diff(lab[:, 0]) >= -1e-9)),
        "largest_lightness_decrease_between_ramp_steps": float(max(0.0, -np.diff(lab[:, 0]).min())),
        "paper_only_diagnostic": {
            "rule": "same paper log exposure change in R, G, B from the Status A midscale point, red-channel offsets of this ramp",
            "print_status_a_rgb": paper_only_a, "print_lab_d50": paper_only_lab,
            "max_chroma_d50": float(np.hypot(paper_only_lab[:, 1], paper_only_lab[:, 2]).max())},
        "ramp_points_beyond_paper_curve_maximum": int(np.any(paper_log_h > paper_top, axis=1).sum()),
        "midscale_negative_status_m_gamma_rgb": status_m_gamma,
        "midscale_printing_gamma_rgb": printing_gamma,
        "printer_balance_log10": model.printer_balance_log10,
    }


def viewing_independence(options: ref.ModelOptions) -> dict:
    """The viewing light must leave the developed print dyes unchanged."""
    status_a = np.array([[0.3, 0.3, 0.3], [0.75, 0.8, 0.7], [1.6, 1.2, 1.4]])
    d50 = ref.ReferenceModel(1.0, replace(options, viewing_daylight_cct_k=5000.0))
    d65 = ref.ReferenceModel(1.0, replace(options, viewing_daylight_cct_k=6500.0))
    b50, b65 = d50.print_dye_amounts(status_a), d65.print_dye_amounts(status_a)
    xyz50 = d50.viewed_xyz(d50.print_spectral_density(b50))
    xyz65 = d65.viewed_xyz(d65.print_spectral_density(b65))
    diff = float(np.abs(b50 - b65).max())
    return {"rule": "print dye amounts solved in a model with D50 viewing and in a model with D65 viewing; max abs difference",
            "tolerance": 0.0, "max_abs_difference": diff, "xyz_d50": xyz50, "xyz_d65": xyz65,
            "xyz_differ": bool(np.abs(xyz50 - xyz65).max() > 1e-3), "passes": diff == 0.0}


def uncertainty_study(base: ref.ReferenceModel) -> dict:
    """Effect of each inferred field on the checks (the 1 nm model with one option changed)."""
    out = {}
    wl = base.grid.wavelengths
    for cct in (5000.0, 5500.0, 6500.0):
        spd = ref.cie_daylight_relative_spd(cct, wl)
        out[f"speed_point_difference_camera_daylight_{int(cct)}K"] = daylight_speed_point(base, spd) - base.negative_criterion_log_h
    out["speed_point_difference_camera_illuminant_A"] = daylight_speed_point(base, base.illuminants["A"]) - base.negative_criterion_log_h

    hold = ref.ReferenceModel(1.0, replace(base.options, sensitivity_outside="hold_below"))
    out["speed_point_difference_sensitivity_held_to_360nm"] = daylight_speed_point(hold, hold.camera_light) - hold.negative_criterion_log_h

    linear = ref.ReferenceModel(1.0, replace(base.options, negative_density_outside="linear"))
    out["dmin_status_m_hold_minus_linear_extrapolation"] = (
        base.status_density(base.negative_dmin, base.w_status_m) - linear.status_density(linear.negative_dmin, linear.w_status_m))
    out["midscale_status_m_hold_minus_linear_extrapolation"] = (
        base.status_density(base.negative_midscale, base.w_status_m) - linear.status_density(linear.negative_midscale, linear.w_status_m))
    out["midscale_print_log_exposure_hold_minus_linear"] = (
        np.log10(base.paper_layer_exposure_unbalanced(base.negative_midscale))
        - np.log10(linear.paper_layer_exposure_unbalanced(linear.negative_midscale)))
    weights_above_700 = base.w_status_m[:, base.grid.wavelengths > 700].sum(axis=1) / base.w_status_m.sum(axis=1)
    out["status_m_weight_fraction_above_700nm_rgb"] = weights_above_700
    paper_above_700 = base.w_printing[:, base.grid.wavelengths > 700].sum(axis=1) / base.w_printing.sum(axis=1)
    out["printing_weight_fraction_above_700nm_rgb_lamp_A"] = paper_above_700

    for density in (0.03, 0.08):
        variant = ref.ReferenceModel(1.0, replace(base.options, paper_base_density=density))
        white = variant.white_xyz()
        chroma = []
        for d in (0.3, 0.75, 1.5):
            lab = ref.xyz_to_lab(variant.viewed_xyz(variant.print_spectral_density(variant.print_dye_amounts(np.array([d, d, d])))), white)
            chroma.append(float(np.hypot(lab[1], lab[2])))
        out[f"status_a_neutral_chroma_paper_base_{density}"] = {"status_a": [0.3, 0.75, 1.5], "chroma": chroma}

    for lamp in ("D55",):
        variant = ref.ReferenceModel(1.0, replace(base.options, printer_lamp=lamp))
        ramp = neutral_ramp(variant)
        out[f"ramp_max_chroma_printer_lamp_{lamp}"] = float(np.max(ramp["print_chroma_d50"]))
    out["ramp_max_chroma_printer_lamp_A"] = float(np.max(neutral_ramp(base)["print_chroma_d50"]))
    return out


SPECTRAL_FILM_LUT_VARIANTS = {
    "reference": {},
    "sfl_sensitivity_log_linear": {"sensitivity_outside": "log_linear"},
    "sfl_gaussian_tails": {"negative_density_outside": "gaussian_tail", "paper_dye_outside": "gaussian_tail"},
    "sfl_band_split_dyes": {"negative_dye_basis": "band_split"},
    "sfl_band_split_dyes_with_tails": {"negative_dye_basis": "band_split", "negative_density_outside": "gaussian_tail",
                                       "paper_dye_outside": "gaussian_tail"},
    "sfl_all_three": {"sensitivity_outside": "log_linear", "negative_dye_basis": "band_split",
                      "negative_density_outside": "gaussian_tail", "paper_dye_outside": "gaussian_tail"},
}


def spectral_film_lut_variants(options: ref.ModelOptions) -> dict:
    """The P0 checks and the ramp with the methods adopted from spectral_film_lut (README U11)."""
    rows = {}
    for name, change in SPECTRAL_FILM_LUT_VARIANTS.items():
        model = ref.ReferenceModel(1.0, replace(options, **change))
        checks = neutral_checks(model)
        ramp = neutral_ramp(model)
        mid_status_m = np.array([c.density_at(options.midscale_log_h) for c in model.negative_curves.values()])
        q_mid = np.log10(model.paper_layer_exposure_unbalanced(model.negative_spectral_density(model.negative_dye_amounts(mid_status_m))))
        q_step = np.log10(model.paper_layer_exposure_unbalanced(model.negative_spectral_density(
            model.negative_dye_amounts(mid_status_m + np.array([0.5, 0.0, 0.0])))))
        wl = model.grid.wavelengths
        rows[name] = {
            "options_changed": change,
            "speed_point_difference_log_h": checks["speed_point_sensitivity_against_characteristic"]["difference_log_h"],
            "dmin_status_m_difference": checks["dmin_spectrum_status_m_against_curve"]["difference"],
            "midscale_matched_log_h_spread": checks["midscale_neutral_status_m_against_curve"]["matched_log_h_spread"],
            "status_a_neutral_max_chroma": checks["status_a_neutral_print_chroma_d50"]["max_chroma"],
            "ramp_max_chroma_d50": float(np.max(ramp["print_chroma_d50"])),
            "ramp_paper_white_lab_d50": ramp["print_lab_d50"][-1],
            "ramp_midscale_printing_gamma_rgb": ramp["midscale_printing_gamma_rgb"],
            "print_log_exposure_change_rgb_for_status_m_red_plus_0_5": q_step - q_mid,
            "printing_weight_fraction_above_700nm_rgb": model.w_printing[:, wl > 700].sum(axis=1) / model.w_printing.sum(axis=1),
            "negative_midscale_density_at_750nm": float(np.interp(750.0, wl, model.negative_midscale)),
            "dye_basis": {k: v for k, v in model.negative_dye_fit.items() if k != "dyes"},
            "all_ramp_values_finite": ramp["all_finite"],
        }
    return {"source": "spectral_film_lut commit bcbcfc6861f49cc706dc5d00ea048e4853060aab (MIT); methods ported in film_spectral_reference.py",
            "variants": rows}


def dye_basis_scan(base: ref.ReferenceModel) -> dict:
    """Refit the negative dye basis with the cyan peak fixed; record the fit and its effect on printing."""
    rows = []
    mid_status_m = np.array([c.density_at(base.options.midscale_log_h) for c in base.negative_curves.values()])
    for peak in (660.0, 680.0, 700.0, 720.0, 740.0, 760.0, 780.0):
        model = ref.ReferenceModel(1.0, replace(base.options, fixed_cyan_peak_nm=peak))
        # A cyan-only step: Status M red 0.5 above the midscale neutral, green and blue unchanged.
        step = mid_status_m + np.array([0.5, 0.0, 0.0])
        a_mid = model.negative_dye_amounts(mid_status_m)
        a_step = model.negative_dye_amounts(step)
        q_mid = np.log10(model.paper_layer_exposure_unbalanced(model.negative_spectral_density(a_mid)))
        q_step = np.log10(model.paper_layer_exposure_unbalanced(model.negative_spectral_density(a_step)))
        ramp = neutral_ramp(model)
        rows.append({"cyan_peak_nm": peak, "fit_rms": model.negative_dye_fit["rms_residual"],
                     "fit_max_abs": model.negative_dye_fit["max_abs_residual"], "dyes": model.negative_dye_fit["dyes"],
                     "midscale_dye_amounts_cmy": a_mid,
                     "print_log_exposure_change_rgb_for_status_m_red_plus_0_5": q_step - q_mid,
                     "ramp_midscale_printing_gamma_rgb": ramp["midscale_printing_gamma_rgb"],
                     "ramp_max_chroma_d50": float(np.max(ramp["print_chroma_d50"]))})
    return {"free_fit": base.negative_dye_fit, "fixed_cyan_peak_scan": rows,
            "note": "The fit uses only the published 400-700 nm midscale neutral minus D-min."}


NEG_AMOUNTS = np.array(list(itertools.product([0.0, 0.5, 1.0, 1.5, 2.0], repeat=3)))
PRINT_AMOUNTS = np.array(list(itertools.product([0.0, 0.6, 1.2, 1.8, 2.4], repeat=3)))


def gaussian_sources(model: ref.ReferenceModel, fwhm: float) -> np.ndarray:
    centers = np.arange(383.0, 704.0, 10.0)
    sigma = fwhm / 2.3548
    return np.exp(-0.5 * ((model.grid.wavelengths[None, :] - centers[:, None]) / sigma) ** 2)


def stage_values(model: ref.ReferenceModel) -> dict:
    lights = np.stack([model.illuminants[k] for k in ("D55", "D65", "A")])
    values = {
        "log_layer_exposure_broadband": np.log10(model.negative_layer_exposure(lights)),
        "log_layer_exposure_fwhm30": model.negative_layer_exposure(gaussian_sources(model, 30.0)),
        "log_layer_exposure_fwhm10": model.negative_layer_exposure(gaussian_sources(model, 10.0)),
    }
    neg = model.negative_spectral_density(NEG_AMOUNTS)
    values["negative_status_m"] = model.status_density(neg, model.w_status_m)
    values["log_print_exposure"] = np.log10(model.paper_layer_exposure_unbalanced(neg))
    values["print_lab_d50"] = ref.xyz_to_lab(model.viewed_xyz(model.print_spectral_density(PRINT_AMOUNTS)), model.white_xyz())
    ramp = neutral_ramp(model)
    values["ramp_print_lab_d50"] = np.array(ramp["print_lab_d50"])
    values["ramp_print_status_a"] = np.array(ramp["print_status_a_rgb"])
    return values


def stage_errors(test: dict, refv: dict) -> dict:
    out = {}
    for key in ("log_layer_exposure_broadband", "negative_status_m", "log_print_exposure", "ramp_print_status_a"):
        out[key] = float(np.abs(test[key] - refv[key]).max())
    for key in ("log_layer_exposure_fwhm30", "log_layer_exposure_fwhm10"):
        # Only the sources and layers that give at least 1 % of the largest response of the layer.
        significant = refv[key] >= 0.01 * refv[key].max(axis=0, keepdims=True)
        out[key] = float(np.abs(np.log10(test[key][significant]) - np.log10(refv[key][significant])).max())
    for key in ("print_lab_d50", "ramp_print_lab_d50"):
        out[key + "_delta_e"] = float(np.linalg.norm(test[key] - refv[key], axis=-1).max())
    return out


def largest_step_meeting(table: dict) -> dict:
    result = {}
    for key in next(iter(table.values())):
        if key == "band_count":
            continue
        tol = TOL_INTEGRATION_DELTA_E if key.endswith("delta_e") else TOL_INTEGRATION_DENSITY
        largest = None
        for s in TEST_STEPS_NM:  # the largest step for which it and every finer test step meet the tolerance
            if table[str(s)][key] <= tol:
                largest = s
            else:
                break
        result[key] = {"tolerance": tol, "largest_step_nm": largest}
    return result


def convergence_study(base_options: ref.ModelOptions) -> dict:
    t0 = time.perf_counter()
    reference = ref.ReferenceModel(REFERENCE_STEP_NM, base_options)
    fixed = replace(base_options, printer_balance_log10=tuple(reference.printer_balance_log10.tolist()))
    reference = ref.ReferenceModel(REFERENCE_STEP_NM, fixed)
    ref_values = stage_values(reference)

    # Convergence of the reference itself: 0.1 nm against a 0.05 nm fine grid.
    finer = ref.ReferenceModel(REFERENCE_STEP_NM / 2, fixed, fine_step_nm=REFERENCE_STEP_NM / 2)
    self_check = stage_errors(ref_values, stage_values(finer))

    tables = {}
    for rule in ("point", "projected"):
        table = {}
        for step in TEST_STEPS_NM:
            model = ref.ReferenceModel(step, fixed, rule=rule)
            table[str(step)] = stage_errors(stage_values(model), ref_values)
            table[str(step)]["band_count"] = len(model.grid.wavelengths)
        tables[rule] = {"errors_by_step_nm": table, "largest_step_meeting_tolerance": largest_step_meeting(table)}
    return {
        "reference_step_nm": REFERENCE_STEP_NM, "range_nm": [ref.WAVELENGTH_START_NM, ref.WAVELENGTH_STOP_NM],
        "rules": {
            "point": "fixed functions sampled at the nodes, support-restricted trapezoid weights",
            "projected": "fixed functions projected on the hat basis of the nodes (weights integrated on the 0.1 nm grid)",
        },
        "variable_functions": "scene spectra, dye spectra, transmission and reflectance sampled at the working nodes",
        "error": "max absolute difference against the 0.1 nm reference (log10 exposure, density, or Delta E*ab)",
        "printer_balance": "fixed to the 0.1 nm reference value for every step and rule",
        "reference_against_0_05nm": self_check,
        "tests": {
            "log_layer_exposure_broadband": "log10 Q of the negative layers for D55, D65, A",
            "log_layer_exposure_fwhm30": "log10 Q for Gaussian sources, FWHM 30 nm, centers 383-703 nm (10 nm apart)",
            "log_layer_exposure_fwhm10": "log10 Q for Gaussian sources, FWHM 10 nm, centers 383-703 nm",
            "negative_status_m": "Status M of 125 negative dye combinations (0-2 per dye)",
            "log_print_exposure": "log10 paper layer exposure through the same 125 negatives, lamp A",
            "print_lab_d50_delta_e": "Lab of 125 print dye combinations (0-2.4 per dye) under D50",
            "ramp_print_status_a": "end-to-end neutral ramp, print Status A",
            "ramp_print_lab_d50_delta_e": "end-to-end neutral ramp, print Lab under D50",
        },
        "by_rule": tables,
        "seconds": time.perf_counter() - t0,
    }


def main() -> int:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    options = ref.ModelOptions()
    model = ref.ReferenceModel(1.0, options)
    machine = {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__,
               "platform": platform.platform(), "processor": platform.processor()}

    checks = neutral_checks(model)
    checks["viewing_light_leaves_print_dyes_unchanged"] = viewing_independence(options)
    write("checks.json", {"model_step_nm": 1.0, "integration_rule": "point", "options": asdict(options),
                          "machine": machine, "checks": checks})
    for name, check in checks.items():
        print(f"{'PASS' if check['passes'] else 'FAIL'}  {name}")

    write("neutral_ramp.json", neutral_ramp(model))
    write("negative_dye_basis.json", dye_basis_scan(model))
    write("uncertainty.json", uncertainty_study(model))
    write("spectral_film_lut_variants.json", spectral_film_lut_variants(options))
    convergence = convergence_study(options)
    convergence["machine"] = machine
    write("integration_convergence.json", convergence)
    print("reference 0.1 nm against 0.05 nm:", {k: f"{v:.1e}" for k, v in convergence["reference_against_0_05nm"].items()})
    for rule, item in convergence["by_rule"].items():
        for key, value in item["largest_step_meeting_tolerance"].items():
            print(f"{rule:9s} {key}: largest step {value['largest_step_nm']} nm (tolerance {value['tolerance']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
