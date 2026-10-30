"""Host spectral reference evaluator of step P0 (float64, NumPy).

Input: the digitized profiles (profiles/kodak_portra_400.json, profiles/kodak_endura_premier.json),
the CIE tables and the Status A / Status M table in build/tmp/p0/sources/ (see sources.json).
Output: a ReferenceModel object with one function per physical stage. The checks and the
convergence study in run_p0_checks.py use it.

Step: P0 (data and reference), README sections 4 and 8. The stages and their quantities:

1. camera exposure: spectral exposure H_e(lambda) in erg/cm^2/nm (radiometric energy units).
2. negative layer exposure: Q_i = integral H_e * S_i d(lambda). S_i = 10^(log sensitivity) in
   cm^2/erg. Q_i = 1 is the criterion exposure of layer i (Status M density 0.2 above D-min),
   by the definition printed on the data sheet.
3. negative development: Status M density D_i = C_i(log10 H*_i + log10 Q_i), where C_i is the
   characteristic curve and H*_i is the curve exposure at density D-min + 0.2.
4. negative dyes: dye amounts a_i such that the Status M density of the spectral density
   D_min(lambda) + sum a_i d_i(lambda), less the Status M density of D_min(lambda), equals the
   curve density above D-min. The dye basis d_i is inferred (the data sheet gives no isolated dye).
5. printing: Q_print_j = k_j * integral I(lambda) T_neg(lambda) S_paper_j(lambda) d(lambda),
   T_neg = 10^(-D_neg). k_j is the printer balance (exposure time and filtration).
6. print development: Status A density from the paper characteristic curve.
7. print dyes: amounts b_j of the peak-normalized paper dyes e_j(lambda) on an inferred paper
   base density, such that the Status A density equals the curve density.
8. viewing: reflectance R = 10^(-D_print), XYZ under a viewing illuminant.

Every value outside the published domain of a curve follows a rule that is named in the
function that applies it. Values outside a characteristic curve raise an error, except below the
toe, where the curve is flat on the chart and the first value is kept (rule
'characteristic_curve_below_toe').
"""

from __future__ import annotations

import ast
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_DIR = REPO_ROOT / "build" / "tmp" / "p0" / "sources"
PROFILE_DIR = REPO_ROOT / "profiles"

WAVELENGTH_START_NM = 360.0
WAVELENGTH_STOP_NM = 840.0  # CIE tables end at 830 nm; the values from 831 to 840 nm are zero.
LUMINOUS_EFFICACY_LM_PER_W = 683.0
ERG_PER_CM2_PER_J_PER_M2 = 1.0e3
NEGATIVE_CRITERION_ABOVE_DMIN = 0.2
TOE_FALL_TOLERANCE = 0.005  # density; the tick tolerance of the digitization

# --------------------------------------------------------------------------------------------
# Source tables
# --------------------------------------------------------------------------------------------


def read_cie_csv(name: str) -> np.ndarray:
    with open(SOURCE_DIR / name, newline="", encoding="utf-8") as stream:
        rows = [[float(v) if v not in ("", "NaN") else np.nan for v in row] for row in csv.reader(stream) if row]
    return np.array(rows)


def read_status_tables() -> dict[str, np.ndarray]:
    """Status A and Status M spectral products (linear, peak 100) at 340-830 nm, 10 nm.

    The source file is read as data with ast; it is not imported or executed.
    """
    tree = ast.parse((SOURCE_DIR / "colormath_density_standards.py").read_text(encoding="utf-8"))
    tables = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            name = node.targets[0].id
            if name.startswith("ANSI_STATUS_A_") or name.startswith("ANSI_STATUS_M_"):
                tables[name] = np.array(ast.literal_eval(node.value.args[0]), dtype=float)
    wavelengths = np.arange(340.0, 831.0, 10.0)
    for name, values in tables.items():
        if len(values) != len(wavelengths):
            raise ValueError(f"{name}: {len(values)} values, expected {len(wavelengths)}")
    tables["wavelengths"] = wavelengths
    return tables


def cie_daylight_relative_spd(nominal_cct_k: float, wavelengths: np.ndarray) -> np.ndarray:
    """CIE 015:2018 daylight formula. The nominal CCT is corrected by 1.4388/1.4380 and M1, M2
    are rounded to three decimals, as for the tabulated CIE illuminants. The 5 nm components are
    interpolated linearly."""
    comp = read_cie_csv("CIE_illum_Dxx_comp.csv")
    t = nominal_cct_k * 1.4388 / 1.4380
    if not 4000.0 <= t <= 25000.0:
        raise ValueError("CCT outside the CIE daylight formula domain")
    if t <= 7000.0:
        x_d = -4.6070e9 / t**3 + 2.9678e6 / t**2 + 0.09911e3 / t + 0.244063
    else:
        x_d = -2.0064e9 / t**3 + 1.9018e6 / t**2 + 0.24748e3 / t + 0.237040
    y_d = -3.000 * x_d**2 + 2.870 * x_d - 0.275
    m = 0.0241 + 0.2562 * x_d - 0.7341 * y_d
    m1 = round((-1.3515 - 1.7703 * x_d + 5.9114 * y_d) / m, 3)
    m2 = round((0.0300 - 31.4424 * x_d + 30.0717 * y_d) / m, 3)
    spd5 = comp[:, 1] + m1 * comp[:, 2] + m2 * comp[:, 3]
    return np.interp(wavelengths, comp[:, 0], spd5, left=0.0, right=0.0)


def load_profile(name: str) -> dict:
    return json.loads((PROFILE_DIR / f"{name}.json").read_text(encoding="utf-8"))


def curve_on_grid(curve: dict, wavelengths: np.ndarray, outside: str) -> np.ndarray:
    """Sample a digitized spectral curve on the model grid.

    outside = 'zero': zero outside the published domain (sensitivities).
    outside = 'hold': the value at the nearest published end (densities; an inferred rule).
    outside = 'linear': linear extrapolation with the slope of the last 20 nm at each end.
    outside = 'gaussian_tail': Gaussian tails of spectral_film_lut (see gaussian_tail_extension).
    """
    x, y = np.array(curve["x"]), np.array(curve["y"])
    if outside == "gaussian_tail":
        return gaussian_tail_extension(x, y, wavelengths)
    values = np.interp(wavelengths, x, y)
    below, above = wavelengths < x[0], wavelengths > x[-1]
    if outside == "zero":
        values[below | above] = 0.0
    elif outside == "linear":
        lo = (y[20] - y[0]) / (x[20] - x[0])
        hi = (y[-1] - y[-21]) / (x[-1] - x[-21])
        values[below] = y[0] + lo * (wavelengths[below] - x[0])
        values[above] = y[-1] + hi * (wavelengths[above] - x[-1])
    elif outside != "hold":
        raise ValueError(f"unknown rule {outside!r}")
    return values


# --------------------------------------------------------------------------------------------
# Methods reused from spectral_film_lut (MIT, Copyright (c) 2026 Jan Lohse), commit
# bcbcfc6861f49cc706dc5d00ea048e4853060aab. See THIRD_PARTY_NOTICES.md. The parameters are
# the ones of that commit; spectral_film_lut works on a 380-780 nm grid with 10 nm steps.
# --------------------------------------------------------------------------------------------

SFL_NEIGHBOR_NM = 10.0  # the end slope of a curve uses the point 10 nm inside (their 10 nm grid)
SFL_TAIL_D1 = 30.0
SFL_TAIL_D2 = 0.75
SFL_BAND_SIGMA_NM = 25.0
SFL_SENSITIVITY_SLOPE_NM = 5.0  # their log sensitivity uses the last two hand-placed points (2-8 nm apart)
SFL_RANGE_NM = (380.0, 780.0)


def _gaussian_tail(a_x: float, a_y: float, b_x: float, b_y: float, wavelengths: np.ndarray) -> np.ndarray:
    """Gaussian that has the value a_y and the slope (a_y - b_y) / (a_x - b_x) at a_x.

    Port of FilmSpectral.gaussian_extrapolation.extrapolate of spectral_film_lut (d_1 = 30,
    d_2 = 0.75)."""
    m = (a_y - b_y) / (a_x - b_x)
    if abs(a_y) < 0.001:
        a_y = np.copysign(0.001, a_y)
    d = SFL_TAIL_D1 * m / abs(a_y) ** SFL_TAIL_D2
    a = a_y / max(np.exp(-(d**2)), 1e-10)
    c = a / m * -2 * d * np.exp(-(d**2)) if m != 0 else 1e6
    b = a_x - c * d
    return a * np.exp(-((wavelengths - b) ** 2) / max(c**2, 1e-4))


def gaussian_tail_extension(x: np.ndarray, y: np.ndarray, wavelengths: np.ndarray) -> np.ndarray:
    """The curve inside its published domain and a Gaussian tail on each side outside it."""
    values = np.interp(wavelengths, x, y)
    below, above = wavelengths < x[0], wavelengths > x[-1]
    lo_y = np.interp(x[0] + SFL_NEIGHBOR_NM, x, y)
    hi_y = np.interp(x[-1] - SFL_NEIGHBOR_NM, x, y)
    values[below] = _gaussian_tail(x[0], y[0], x[0] + SFL_NEIGHBOR_NM, lo_y, wavelengths[below])
    values[above] = _gaussian_tail(x[-1], y[-1], x[-1] - SFL_NEIGHBOR_NM, hi_y, wavelengths[above])
    return values


def band_split_dyes(wavelengths: np.ndarray, neutral_above_dmin: np.ndarray) -> tuple[np.ndarray, dict]:
    """Split one neutral density spectrum into cyan, magenta, yellow bands.

    Port of construct_spectral_density of spectral_film_lut: maxima in 600-750 (red), 500-600
    (green), 400-500 nm (blue); cut points at the minima between them; step masks blurred with a
    Gaussian of sigma 25 nm. The three bands add up to the neutral spectrum.
    """
    from scipy import ndimage

    def argext(low: float, high: float, fn) -> float:
        inside = (wavelengths >= low) & (wavelengths <= high)
        return float(wavelengths[inside][fn(neutral_above_dmin[inside])])

    red = argext(600.0, 750.0, np.argmax)
    green = argext(500.0, 600.0, np.argmax)
    blue = argext(400.0, 500.0, np.argmax)
    bg_cut = argext(blue, green, np.argmin)
    gr_cut = argext(green, red, np.argmin)
    masks = np.stack([np.where(wavelengths >= gr_cut, 1.0, 0.0),
                      np.where((wavelengths > bg_cut) & (wavelengths < gr_cut), 1.0, 0.0),
                      np.where(wavelengths <= bg_cut, 1.0, 0.0)])
    step = float(wavelengths[1] - wavelengths[0])
    masks = ndimage.gaussian_filter1d(masks, SFL_BAND_SIGMA_NM / step, axis=1)
    info = {"red_peak_nm": red, "green_peak_nm": green, "blue_peak_nm": blue,
            "blue_green_cut_nm": bg_cut, "green_red_cut_nm": gr_cut}
    return masks * neutral_above_dmin[None, :], info


@dataclass
class CharacteristicCurve:
    """Density against log10 exposure, digitized on a 0.01 log10 lux-seconds grid."""

    log_h: np.ndarray
    density: np.ndarray

    @property
    def d_min(self) -> float:
        return float(self.density[0])

    def density_at(self, log_h: np.ndarray) -> np.ndarray:
        log_h = np.asarray(log_h, dtype=float)
        if np.any(~np.isfinite(log_h)):
            raise ValueError("non-finite log exposure")
        if np.any(log_h > self.log_h[-1] + 1e-9):
            raise ValueError(f"log exposure {log_h.max():.3f} above the published curve end {self.log_h[-1]:.3f}")
        # Rule 'characteristic_curve_below_toe': the chart curve is flat at its start; keep the first value.
        return np.interp(log_h, self.log_h, self.density)

    def log_h_at(self, density: float) -> float:
        """Exposure where the curve first reaches the density, on the rising part up to the maximum.

        The Endura curves fall slightly after their maximum (shoulder); that part is not used here.
        The drawn Endura toe falls by up to 0.002 density over 0.4 log H; a fall of up to
        TOE_FALL_TOLERANCE is accepted and the running maximum is inverted.
        """
        top = int(np.argmax(self.density)) + 1
        rising_h = self.log_h[:top]
        running_max = np.maximum.accumulate(self.density[:top])
        fall = float((running_max - self.density[:top]).max())
        if fall > TOE_FALL_TOLERANCE:
            raise ValueError(f"curve falls by {fall:.4f} before its maximum")
        rising_d = running_max
        if density < rising_d[0] or density > rising_d[-1]:
            raise ValueError(f"density {density} outside the curve range")
        return float(np.interp(density, rising_d, rising_h))


def characteristic_curves(profile: dict, channels: list[str]) -> dict[str, CharacteristicCurve]:
    chart = profile["charts"]["characteristic"]
    return {c: CharacteristicCurve(np.array(chart["curves"][c]["x"]), np.array(chart["curves"][c]["y"]))
            for c in channels}


# --------------------------------------------------------------------------------------------
# Spectral grid and integration
# --------------------------------------------------------------------------------------------


def support_trapezoid_weights(step_nm: float, support: np.ndarray) -> np.ndarray:
    """Trapezoid weights restricted to the support of a function: step_nm inside each run of
    True values, step_nm / 2 at the two ends of each run, zero outside. A function that is cut at
    the end of its published domain is integrated over that domain only, so the cut does not
    become a ramp between two nodes."""
    support = np.asarray(support, dtype=bool)
    weights = np.where(support, step_nm, 0.0)
    padded = np.concatenate([[False], support, [False]])
    starts = support & ~padded[:-2]
    ends = support & ~padded[2:]
    weights[starts] *= 0.5
    weights[ends] *= 0.5
    weights[starts & ends] = 0.0  # a single isolated node has no width
    return weights


@dataclass
class SpectralGrid:
    """Working wavelength grid and the integration rule.

    The fixed spectral functions of the model (layer sensitivities, printer light times paper
    sensitivity, Status products, viewing light times the CIE observer) are defined on a fine grid
    (fine_step_nm). The variable functions (scene spectra, dye spectra, transmission, reflectance)
    are sampled at the working nodes. An integral is the dot product of the variable samples with
    weights of the fixed function:

    - rule 'point': the fixed function sampled at the working nodes times the support-restricted
      trapezoid weights of the working grid.
    - rule 'projected': the fixed function projected on the hat (linear interpolation) basis of the
      working nodes, integrated on the fine grid. This rule is exact when the variable function is
      linear between the working nodes.

    At step_nm == fine_step_nm both rules give the fine-grid trapezoid rule.
    """

    step_nm: float
    rule: str = "point"
    fine_step_nm: float = 0.1

    def __post_init__(self) -> None:
        span = WAVELENGTH_STOP_NM - WAVELENGTH_START_NM
        count = int(round(span / self.step_nm))
        fine_count = int(round(span / self.fine_step_nm))
        ratio = int(round(self.step_nm / self.fine_step_nm))
        if abs(count * self.step_nm - span) > 1e-9 or abs(ratio * self.fine_step_nm - self.step_nm) > 1e-9:
            raise ValueError("the step must divide the wavelength range and be a multiple of the fine step")
        if self.rule not in ("point", "projected"):
            raise ValueError(f"unknown integration rule {self.rule!r}")
        self.ratio = ratio
        self.wavelengths = WAVELENGTH_START_NM + self.step_nm * np.arange(count + 1)
        self.fine_wavelengths = WAVELENGTH_START_NM + self.fine_step_nm * np.arange(fine_count + 1)
        if self.rule == "projected" and ratio > 1:
            distance = np.abs(self.fine_wavelengths[None, :] - self.wavelengths[:, None]) / self.step_nm
            self._hat = np.clip(1.0 - distance, 0.0, None)

    def weights(self, fine_values: np.ndarray, fine_support: np.ndarray | None = None) -> np.ndarray:
        """Integration weights (rows, nodes) of a fixed function given on the fine grid."""
        fine_values = np.atleast_2d(fine_values)
        if fine_support is None:
            fine_support = np.ones_like(fine_values, dtype=bool)
        fine_support = np.broadcast_to(fine_support, fine_values.shape)
        if self.ratio == 1 or self.rule == "point":
            nodes = fine_values[:, ::self.ratio]
            support = fine_support[:, ::self.ratio]
            return np.stack([nodes[k] * support_trapezoid_weights(self.step_nm, support[k]) for k in range(len(nodes))])
        fine_weights = np.stack([fine_values[k] * support_trapezoid_weights(self.fine_step_nm, fine_support[k])
                                 for k in range(len(fine_values))])
        return fine_weights @ self._hat.T

    @staticmethod
    def integrate(variable_values: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """Integral of variable x fixed for each row: (..., nodes) x (rows, nodes) -> (..., rows)."""
        return np.asarray(variable_values) @ weights.T


# --------------------------------------------------------------------------------------------
# Inferred negative dye basis
# --------------------------------------------------------------------------------------------


def asymmetric_gaussian(wavelengths: np.ndarray, peak_nm: float, sigma_short: float, sigma_long: float) -> np.ndarray:
    sigma = np.where(wavelengths < peak_nm, sigma_short, sigma_long)
    return np.exp(-0.5 * ((wavelengths - peak_nm) / sigma) ** 2)


NEGATIVE_DYES = ("cyan", "magenta", "yellow")  # in the order of the Status M channels R, G, B
PEAK_BOUNDS_NM = {"cyan": (600.0, 780.0), "magenta": (500.0, 590.0), "yellow": (410.0, 490.0)}


def fit_negative_dye_basis(wavelengths: np.ndarray, delta_density: np.ndarray,
                           fixed_cyan_peak_nm: float | None = None) -> dict:
    """Fit the midscale-neutral density above D-min with three non-negative asymmetric Gaussians.

    This is an inferred field: the data sheet gives one neutral spectrum, which does not
    identify three dye spectra. Returns the peak-normalized dyes as parameters, the amounts of
    the midscale neutral, and the fit residual.
    """
    start = {"cyan": [1.0, 690.0, 50.0, 50.0], "magenta": [1.0, 545.0, 30.0, 30.0], "yellow": [1.0, 450.0, 25.0, 25.0]}
    lower, upper, x0 = [], [], []
    for dye in NEGATIVE_DYES:
        lo_peak, hi_peak = PEAK_BOUNDS_NM[dye]
        peak = start[dye][1]
        if dye == "cyan" and fixed_cyan_peak_nm is not None:
            lo_peak, hi_peak, peak = fixed_cyan_peak_nm - 1e-6, fixed_cyan_peak_nm + 1e-6, fixed_cyan_peak_nm
        lower += [0.0, lo_peak, 8.0, 8.0]
        upper += [5.0, hi_peak, 150.0, 150.0]
        x0 += [start[dye][0], peak, start[dye][2], start[dye][3]]

    def model(p: np.ndarray) -> np.ndarray:
        return sum(p[4 * k] * asymmetric_gaussian(wavelengths, *p[4 * k + 1:4 * k + 4]) for k in range(3))

    result = least_squares(lambda p: model(p) - delta_density, np.array(x0), bounds=(lower, upper),
                           x_scale="jac", max_nfev=20000)
    residual = model(result.x) - delta_density
    dyes = {dye: {"peak_nm": float(result.x[4 * k + 1]), "sigma_short_nm": float(result.x[4 * k + 2]),
                  "sigma_long_nm": float(result.x[4 * k + 3])} for k, dye in enumerate(NEGATIVE_DYES)}
    amounts = {dye: float(result.x[4 * k]) for k, dye in enumerate(NEGATIVE_DYES)}
    return {"dyes": dyes, "midscale_amounts": amounts,
            "rms_residual": float(np.sqrt(np.mean(residual**2))),
            "max_abs_residual": float(np.abs(residual).max()), "success": bool(result.success)}


# --------------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------------


@dataclass
class ModelOptions:
    """Explicit choices for the fields that the sources do not give (see the P0 report)."""

    camera_daylight_cct_k: float = 5500.0  # 'Exposure: Daylight' on E-4050; the CCT is not stated
    printer_lamp: str = "A"  # E-4070 does not state the exposure light ('A', 'D50', 'D55', 'D65')
    viewing_daylight_cct_k: float = 5000.0  # D50, the ICC viewing condition (5000 or 6500)
    negative_density_outside: str = "hold"  # D-min spectrum outside 400-700 nm
    paper_dye_outside: str = "hold"  # paper dye spectra outside 400-700 nm
    paper_base_density: float = 0.05  # spectrally flat paper base; not published
    print_midscale_status_a: float = 0.75  # printer balance: midscale neutral prints to this Status A density
    midscale_log_h: float = -1.44  # 'Log H Ref' of the characteristic chart, used as the midscale neutral exposure
    fixed_cyan_peak_nm: float | None = None
    printer_balance_log10: tuple[float, float, float] | None = None  # fixed balance; None computes it
    # 'zero'; 'hold_below' (the first published value down to 360 nm, uncertainty study);
    # 'log_linear' (spectral_film_lut: log sensitivity extended linearly inside 380-780 nm)
    sensitivity_outside: str = "zero"
    negative_dye_basis: str = "gaussian_fit"  # or 'band_split' (spectral_film_lut)
    negative_profile: str = "kodak_portra_400"
    print_profile: str = "kodak_endura_premier"


class ReferenceModel:
    def __init__(self, step_nm: float = 1.0, options: ModelOptions | None = None, rule: str = "point",
                 fine_step_nm: float = 0.1) -> None:
        self.options = options or ModelOptions()
        self.grid = SpectralGrid(step_nm, rule, fine_step_nm)
        wl = self.grid.wavelengths
        fwl = self.grid.fine_wavelengths
        o = self.options

        illum_a = read_cie_csv("CIE_std_illum_A_1nm.csv")
        illum_d65 = read_cie_csv("CIE_std_illum_D65.csv")

        def illuminants_on(grid: np.ndarray) -> dict[str, np.ndarray]:
            return {
                "A": np.interp(grid, illum_a[:, 0], illum_a[:, 1], left=0.0, right=0.0),
                "D65": np.interp(grid, illum_d65[:, 0], illum_d65[:, 1], left=0.0, right=0.0),
                "D50": cie_daylight_relative_spd(5000.0, grid),
                "D55": cie_daylight_relative_spd(5500.0, grid),
            }

        # Variable spectra: sampled at the working nodes.
        self.illuminants = illuminants_on(wl)
        self.camera_light = cie_daylight_relative_spd(o.camera_daylight_cct_k, wl)

        # Fixed spectral functions: defined on the fine grid, reduced to integration weights.
        cmf_table = read_cie_csv("CIE_xyz_1931_2deg.csv")
        cmf = np.stack([np.interp(fwl, cmf_table[:, 0], cmf_table[:, k], left=0.0, right=0.0) for k in (1, 2, 3)])
        fine_lights = illuminants_on(fwl)
        self.w_luminance = self.grid.weights(cmf[1])
        self.w_viewing = {name: self.grid.weights(fine_lights[name] * cmf) for name in ("D50", "D65")}
        self.viewing_name = {5000.0: "D50", 6500.0: "D65"}.get(o.viewing_daylight_cct_k)
        if self.viewing_name is None:
            raise ValueError("viewing CCT must be 5000 K (D50) or 6500 K (D65)")

        status = read_status_tables()
        swl = status["wavelengths"]

        def product(name: str) -> np.ndarray:
            # Rule 'status_table_interpolation': linear between the 10 nm values, zero outside 340-830 nm.
            return np.interp(fwl, swl, status[name], left=0.0, right=0.0)

        self.w_status_m = self.grid.weights(np.stack([product(f"ANSI_STATUS_M_{c}") for c in ("RED", "GREEN", "BLUE")]))
        self.w_status_a = self.grid.weights(np.stack([product(f"ANSI_STATUS_A_{c}") for c in ("RED", "GREEN", "BLUE")]))

        portra = load_profile(o.negative_profile)
        endura = load_profile(o.print_profile)
        layers = ("cyan_forming_layer", "magenta_forming_layer", "yellow_forming_layer")
        sens = portra["charts"]["spectral_sensitivity"]["curves"]
        neg_values, neg_support = zip(*(self._sensitivity(sens[k], fwl) for k in layers))
        self.w_negative = self.grid.weights(np.stack(neg_values), np.stack(neg_support))
        psens = endura["charts"]["spectral_sensitivity"]["curves"]
        pap_values, pap_support = zip(*(self._sensitivity(psens[k], fwl) for k in layers))
        self.w_printing = self.grid.weights(fine_lights[o.printer_lamp] * np.stack(pap_values), np.stack(pap_support))

        dye_chart = portra["charts"]["spectral_dye_density"]["curves"]
        self.negative_dmin = curve_on_grid(dye_chart["minimum_density"], wl, o.negative_density_outside)
        self.negative_midscale = curve_on_grid(dye_chart["midscale_neutral"], wl, o.negative_density_outside)
        wl_pub = np.array(dye_chart["minimum_density"]["x"])
        delta_pub = np.array(dye_chart["midscale_neutral"]["y"]) - np.array(dye_chart["minimum_density"]["y"])
        if o.negative_dye_basis == "gaussian_fit":
            self.negative_dye_fit = fit_negative_dye_basis(wl_pub, delta_pub, o.fixed_cyan_peak_nm)
            fitted = self.negative_dye_fit["dyes"]
            self.negative_dyes = np.stack([asymmetric_gaussian(wl, fitted[d]["peak_nm"], fitted[d]["sigma_short_nm"],
                                                               fitted[d]["sigma_long_nm"]) for d in NEGATIVE_DYES])
        elif o.negative_dye_basis == "band_split":
            # On a 1 nm grid over the model range, from the neutral and D-min spectra extended with
            # the density rule of this model; then sampled at the working nodes.
            grid_1nm = np.arange(WAVELENGTH_START_NM, WAVELENGTH_STOP_NM + 0.5, 1.0)
            neutral = (curve_on_grid(dye_chart["midscale_neutral"], grid_1nm, o.negative_density_outside)
                       - curve_on_grid(dye_chart["minimum_density"], grid_1nm, o.negative_density_outside))
            bands, info = band_split_dyes(grid_1nm, neutral)
            self.negative_dyes = np.stack([np.interp(wl, grid_1nm, band) for band in bands])
            self.negative_dye_fit = {"method": "band_split", **info, "midscale_amounts": {d: 1.0 for d in NEGATIVE_DYES}}
        else:
            raise ValueError(f"unknown dye basis {o.negative_dye_basis!r}")

        pdyes = endura["charts"]["spectral_dye_density"]["curves"]
        self.paper_dyes = np.stack([curve_on_grid(pdyes[k], wl, o.paper_dye_outside) for k in ("cyan_dye", "magenta_dye", "yellow_dye")])
        self.paper_base = np.full_like(wl, o.paper_base_density)

        self.negative_curves = characteristic_curves(portra, ["red", "green", "blue"])
        self.paper_curves = characteristic_curves(endura, ["red", "green", "blue"])
        self.negative_criterion_log_h = np.array([c.log_h_at(c.d_min + NEGATIVE_CRITERION_ABOVE_DMIN)
                                                  for c in self.negative_curves.values()])
        self.negative_curve_dmin = np.array([c.d_min for c in self.negative_curves.values()])
        if o.printer_balance_log10 is None:
            self.printer_balance_log10 = self._printer_balance()
        else:
            self.printer_balance_log10 = np.array(o.printer_balance_log10, dtype=float)

    def _sensitivity(self, curve: dict, wavelengths: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """10^(log sensitivity) in cm^2/erg and its support.

        Rule 'sensitivity_outside_published_domain' (option sensitivity_outside):
        - 'zero': zero outside the published domain;
        - 'hold_below': the first published value down to 360 nm (uncertainty study);
        - 'log_linear': spectral_film_lut; the log sensitivity continues with the slope of the
          last SFL_SENSITIVITY_SLOPE_NM at each end, inside 380-780 nm, zero outside that range.
        """
        x, y = np.array(curve["x"]), np.array(curve["y"])
        rule = self.options.sensitivity_outside
        log_s = np.interp(wavelengths, x, y)
        if rule == "zero":
            inside = (wavelengths >= x[0] - 1e-9) & (wavelengths <= x[-1] + 1e-9)
        elif rule == "hold_below":
            inside = (wavelengths >= WAVELENGTH_START_NM - 1e-9) & (wavelengths <= x[-1] + 1e-9)
        elif rule == "log_linear":
            n = int(round(SFL_SENSITIVITY_SLOPE_NM / (x[1] - x[0])))
            lo, hi = (y[n] - y[0]) / (x[n] - x[0]), (y[-1] - y[-1 - n]) / (x[-1] - x[-1 - n])
            log_s = np.where(wavelengths < x[0], y[0] + lo * (wavelengths - x[0]), log_s)
            log_s = np.where(wavelengths > x[-1], y[-1] + hi * (wavelengths - x[-1]), log_s)
            inside = (wavelengths >= SFL_RANGE_NM[0] - 1e-9) & (wavelengths <= SFL_RANGE_NM[1] + 1e-9)
        else:
            raise ValueError(f"unknown sensitivity rule {rule!r}")
        return np.where(inside, 10.0 ** log_s, 0.0), inside

    # --- stage 1-2: camera exposure and negative layer exposure -------------------------------

    def spectral_exposure_for_luminous_exposure(self, relative_spd: np.ndarray, lux_seconds: np.ndarray) -> np.ndarray:
        """Scale a relative spectrum to a spectral exposure in erg/cm^2/nm with the given lux-seconds."""
        lux_per_unit = LUMINOUS_EFFICACY_LM_PER_W * self.grid.integrate(relative_spd, self.w_luminance)[0]
        scale = np.atleast_1d(lux_seconds)[:, None] / lux_per_unit
        return scale * relative_spd[None, :] * ERG_PER_CM2_PER_J_PER_M2

    def negative_layer_exposure(self, spectral_exposure_erg: np.ndarray) -> np.ndarray:
        """Q_i for each layer (cyan-, magenta-, yellow-forming), dimensionless."""
        return self.grid.integrate(spectral_exposure_erg, self.w_negative)

    # --- stage 3-4: development and dyes ------------------------------------------------------

    def negative_status_m_from_layer_exposure(self, layer_exposure: np.ndarray) -> np.ndarray:
        if np.any(layer_exposure <= 0):
            raise ValueError("layer exposure must be positive")
        log_h = self.negative_criterion_log_h + np.log10(layer_exposure)
        return np.stack([c.density_at(log_h[..., k]) for k, c in enumerate(self.negative_curves.values())], axis=-1)

    def status_density(self, spectral_density: np.ndarray, status_weights: np.ndarray) -> np.ndarray:
        transmission = 10.0 ** (-np.asarray(spectral_density))
        return -np.log10(self.grid.integrate(transmission, status_weights) / status_weights.sum(axis=1))

    def negative_spectral_density(self, dye_amounts: np.ndarray) -> np.ndarray:
        return self.negative_dmin + np.asarray(dye_amounts) @ self.negative_dyes

    def negative_dye_amounts(self, status_m: np.ndarray) -> np.ndarray:
        """Solve the dye amounts for Status M densities (R, G, B) of the characteristic curves."""
        above = np.asarray(status_m) - self.negative_curve_dmin
        base = self.status_density(self.negative_dmin, self.w_status_m)
        return self._solve_amounts(above, lambda a: self.status_density(self.negative_spectral_density(a), self.w_status_m) - base,
                                   np.clip(above, 0, None))

    # --- stage 5-6: printing ------------------------------------------------------------------

    def paper_layer_exposure_unbalanced(self, negative_density: np.ndarray) -> np.ndarray:
        return self.grid.integrate(10.0 ** (-np.asarray(negative_density)), self.w_printing)

    def _printer_balance(self) -> np.ndarray:
        """log10 k_j such that the negative of a camera-light grey at midscale_log_h prints to the
        target Status A density. The grey goes through the same camera path as every scene
        (spectral sensitivity, criterion anchor), as a printer is balanced on a grey-card negative."""
        exposure = self.spectral_exposure_for_luminous_exposure(self.camera_light, np.array([10.0 ** self.options.midscale_log_h]))
        mid_status_m = self.negative_status_m_from_layer_exposure(self.negative_layer_exposure(exposure))[0]
        mid_density = self.negative_spectral_density(self.negative_dye_amounts(mid_status_m))
        q = self.paper_layer_exposure_unbalanced(mid_density)
        target = np.array([c.log_h_at(self.options.print_midscale_status_a) for c in self.paper_curves.values()])
        return target - np.log10(q)

    def paper_log_exposure(self, negative_density: np.ndarray) -> np.ndarray:
        return np.log10(self.paper_layer_exposure_unbalanced(negative_density)) + self.printer_balance_log10

    def paper_status_a(self, negative_density: np.ndarray) -> np.ndarray:
        log_h = self.paper_log_exposure(negative_density)
        return np.stack([c.density_at(log_h[..., k]) for k, c in enumerate(self.paper_curves.values())], axis=-1)

    # --- stage 7-8: print dyes and viewing ----------------------------------------------------

    def print_spectral_density(self, dye_amounts: np.ndarray) -> np.ndarray:
        return self.paper_base + np.asarray(dye_amounts) @ self.paper_dyes

    def print_dye_amounts(self, status_a: np.ndarray) -> np.ndarray:
        return self._solve_amounts(np.asarray(status_a),
                                   lambda b: self.status_density(self.print_spectral_density(b), self.w_status_a),
                                   np.clip(np.asarray(status_a) - self.options.paper_base_density, 0, None))

    def viewed_xyz(self, print_density: np.ndarray, viewing: str | None = None) -> np.ndarray:
        """XYZ (Y of the perfect diffuser = 100) of a reflection print under a viewing light."""
        weights = self.w_viewing[viewing or self.viewing_name]
        reflectance = 10.0 ** (-np.asarray(print_density))
        return 100.0 * self.grid.integrate(reflectance, weights) / weights[1].sum()

    def white_xyz(self, viewing: str | None = None) -> np.ndarray:
        return self.viewed_xyz(np.zeros_like(self.grid.wavelengths), viewing)

    # --- helpers ------------------------------------------------------------------------------

    @staticmethod
    def _solve_amounts(target: np.ndarray, forward, start: np.ndarray) -> np.ndarray:
        target = np.atleast_2d(target)
        start = np.atleast_2d(start)
        out = np.empty_like(target)
        for n in range(target.shape[0]):
            result = least_squares(lambda a: forward(a) - target[n], start[n], bounds=(0.0, 10.0),
                                   xtol=1e-14, ftol=1e-14, gtol=1e-14)
            residual = np.abs(forward(result.x) - target[n]).max()
            if residual > 1e-6:
                raise RuntimeError(f"dye amount solve did not reach the target: residual {residual:.2e}, target {target[n]}")
            out[n] = result.x
        return out if out.shape[0] > 1 else out[0]


def xyz_to_lab(xyz: np.ndarray, white: np.ndarray) -> np.ndarray:
    r = np.asarray(xyz) / white
    f = np.where(r > (6 / 29) ** 3, np.cbrt(r), r / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)
