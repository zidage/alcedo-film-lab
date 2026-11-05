"""P13 input experiment: RAW white, matched-white lights, constrained spectra.

Inputs: existing P1 tables, CIE tables, RAW metadata, graded linear AP1.
Outputs: float64 illuminants and streamed film-layer exposures on 360--840 nm
at 1 nm, with the existing projected integration weights. No scan is fitted.
Project-authored code: GPL-3.0-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import time

import numpy as np
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
for directory in ("p1_spectral_input", "p2_negative_print", "p6_mvp_gui"):
    sys.path.insert(0, str(ROOT / "scripts" / "poc" / directory))
import spectral_reconstruction as sr  # noqa: E402
import spectral_datasets as sd  # noqa: E402
import film_preview as fp  # noqa: E402

WHITE_TOLERANCE = 1e-8
RECONSTRUCTION_TOLERANCE = 1e-8
PRIOR_POSITIVE_SHARE = 1e-5
MAX_ITERATIONS = 60
BATCH_PIXELS = 512


@dataclass
class RawWhite:
    """White estimated by the existing matrix convention, not a light measurement."""

    xyz: np.ndarray
    cct: float
    matrix: np.ndarray
    multipliers: np.ndarray


def read_raw_white(path: Path) -> RawWhite:
    """Preserve the XYZ that the current as-shot function reduces to CCT."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        multipliers = np.asarray(raw.camera_whitebalance[:3], dtype=np.float64)
        matrix = np.asarray(raw.rgb_xyz_matrix[:3], dtype=np.float64)
    if np.min(multipliers) <= 0 or abs(np.linalg.det(matrix)) < 1e-9:
        raise ValueError(f"{path}: missing RAW white balance or camera matrix")
    xyz = np.linalg.solve(matrix, 1.0 / multipliers)
    if not np.all(np.isfinite(xyz)) or np.min(xyz) <= 0:
        raise ValueError(f"{path}: invalid matrix-derived white {xyz}")
    xyz /= xyz[1]
    x, y = xyz[:2] / xyz.sum()
    n = (x - 0.3320) / (y - 0.1858)
    cct = float(-449 * n**3 + 3525 * n**2 - 6823.3 * n + 5520.33)
    return RawWhite(xyz, cct, matrix, multipliers)


def fit_white(c: sr.Colorimetry, source: np.ndarray,
              target: np.ndarray) -> tuple[np.ndarray, dict]:
    """Infer a positive smooth tilt of a source; match XYZ at Y=1.

    This is a constructed spectral family, not a measured lamp. Zeros in a CIE
    source stay zero. The three coefficients have no stock-specific values.
    """
    source = np.asarray(source, dtype=np.float64)
    source = source / c.xyz(source)[1]
    x = (c.wavelengths - 560.0) / 100.0
    basis = np.stack((np.ones_like(x), x, x*x))

    def residual(coefficient: np.ndarray) -> np.ndarray:
        return c.xyz(source * np.exp(coefficient @ basis)) - target

    solution = least_squares(residual, np.zeros(3), xtol=1e-13,
                             ftol=1e-13, gtol=1e-13, max_nfev=300)
    spectrum = source * np.exp(solution.x @ basis)
    error = float(np.max(np.abs(c.xyz(spectrum) - target)))
    if not solution.success or error > WHITE_TOLERANCE:
        raise RuntimeError(f"illuminant white fit failed: {solution.message}; {error=}")
    if not np.all(np.isfinite(spectrum)) or np.min(spectrum) < 0:
        raise FloatingPointError("invalid fitted illuminant")
    return spectrum, {"coefficients": solution.x.tolist(), "XYZ_max_abs": error,
                      "spectrum_xy": (c.xyz(spectrum)[:2] / c.xyz(spectrum).sum()).tolist()}


def make_lights(c: sr.Colorimetry, white: RawWhite) -> tuple[dict, dict]:
    """Construct smooth, LED-B3 and FL11 families at the same RAW white."""
    # Match the original CCT path, including its stated temperature limits.
    kelvin = float(round(np.clip(white.cct, 2000, 15000)))
    smooth = fp.cct_light(kelvin, c.wavelengths, c.xyz)
    smooth /= c.xyz(smooth)[1]
    lights = {"cct": smooth}
    records = {"cct": {"kelvin": kelvin, "XYZ": c.xyz(smooth).tolist()}}
    sources = sd.cie_light_sources()
    for name, source in (("smooth", smooth), ("led", sources["LED-B3"]),
                         ("fluorescent", sources["FL11"])):
        lights[name], records[name] = fit_white(c, source, white.xyz)
    return lights, records


class SpectralInput:
    """Stream a spectral prior and an optional relative-entropy projection.

    Let L0 = E * (rho_prior + epsilon), normalized to the input WB Y=1.
    Minimize sum_j [L_j log(L_j/L0_j) - L_j + L0_j], L >= 0,
    subject to W_xyz L = inverse(Bradford(scene white -> reference white)) XYZ_wb.
    The solution has L = L0 exp(B.T lambda), B = row-scaled W_xyz.
    epsilon=1e-5 explicitly gives the prior support wherever E is positive.
    It is an inferred regularization, not an emission or material measurement.

    This uses the colourimetric Bradford input model; it does not claim to invert
    LibRaw's sensor-space white balance. HDR scale remains separate. No upper
    bound on this Y-normalized relative reflectance is imposed.
    """

    def __init__(self, c: sr.Colorimetry) -> None:
        self.c = c
        self.shapes = {}
        for name, filename in (
                ("measured", "reflectance_over_uv_smooth_0.006_0.025.npy"),
                ("light", "reflectance_over_uv_light_0.006_0.025.npy")):
            self.shapes[name] = np.load(fp.CACHE_DIR / filename).reshape(
                fp.UV_NODES, fp.UV_NODES, -1).astype(np.float64)
        self.projection = sr.LocusProjection(c)
        self.row_scale = c.w_xyz.max(axis=1)
        self.basis = c.w_xyz / self.row_scale[:, None]

    def prior(self, xyz: np.ndarray, name: str = "measured") -> np.ndarray:
        """Read the existing 192x192 table without changing its resolution."""
        uv = sr.MeasuredPriorLocal.chromaticity_uv(xyz)
        coordinates = (uv / np.asarray(fp.UV_MAX) * (fp.UV_NODES-1)).T
        if np.any(coordinates < 0) or np.any(coordinates > fp.UV_NODES-1):
            raise ValueError("input chromaticity is outside the existing table rectangle")
        return np.stack([map_coordinates(self.shapes[name][..., k], coordinates,
                                         order=1, mode="nearest")
                         for k in range(len(self.c.wavelengths))], axis=1)

    def condition(self, prior: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, dict]:
        """Solve the stated convex objective; stop on infeasible or failed input."""
        if not np.all(self.c.inside_spectral_locus(target)):
            bad = ~self.c.inside_spectral_locus(target)
            raise ValueError(f"inverse white adaptation gives {int(bad.sum())} spectra "
                             f"outside the non-negative spectral locus; first XYZ={target[bad][0]}")
        basis = self.basis
        aim = target / self.row_scale
        coefficient = np.zeros((len(prior), 3), dtype=np.float64)
        solved = np.zeros(len(prior), dtype=bool)
        maximum = 0.0
        for iteration in range(MAX_ITERATIONS):
            radiance = prior * np.exp(coefficient @ basis)
            error_xyz = (radiance @ self.c.w_xyz.T - target)
            error = np.max(np.abs(error_xyz), axis=1) / np.max(np.abs(target), axis=1)
            solved |= error <= RECONSTRUCTION_TOLERANCE
            if solved.all():
                maximum = float(error.max())
                break
            active = np.flatnonzero(~solved)
            values = radiance[active]
            residual = values @ basis.T - aim[active]
            hessian = np.einsum("nk,ak,bk->nab", values, basis, basis, optimize=True)
            step = np.linalg.solve(hessian, residual[..., None])[..., 0]
            slope = np.sum(residual * step, axis=1)
            old = values.sum(axis=1) - np.sum(coefficient[active] * aim[active], axis=1)
            rate = np.minimum(1.0, 20.0 / np.maximum(np.max(np.abs(step @ basis), axis=1), 1e-30))
            accepted = np.zeros(len(active), dtype=bool)
            for _ in range(45):
                trial = coefficient[active] - rate[:, None] * step
                exponent = trial @ basis
                if not np.isfinite(exponent).all() or np.max(exponent) > 700:
                    raise FloatingPointError("non-finite or excessive exponent in spectral solve")
                trial_values = prior[active] * np.exp(exponent)
                dual = trial_values.sum(axis=1) - np.sum(trial * aim[active], axis=1)
                accepted |= dual <= old - 1e-4 * rate * slope + 1e-13 * np.maximum(1, np.abs(old))
                if accepted.all():
                    coefficient[active] = trial
                    break
                rate[~accepted] *= 0.5
            else:
                raise RuntimeError("relative-entropy Newton line search did not converge")
        else:
            raise RuntimeError(f"relative-entropy solve exceeded {MAX_ITERATIONS} iterations; "
                               f"maximum normalized XYZ error={error.max()}")
        if not np.isfinite(radiance).all() or np.min(radiance) < 0:
            raise FloatingPointError("invalid constrained radiance")
        return radiance, {"XYZ_relative_max": maximum, "iterations": iteration+1}

    def exposures(self, image: np.ndarray, spectrum: np.ndarray,
                  stock_models: dict, conditioned: bool) -> tuple[dict, dict]:
        """Stream full-grid spectra, integrate each stock, and discard each batch."""
        started = time.perf_counter()
        flat = np.asarray(image, dtype=np.float64).reshape(-1, 3)
        xyz = flat @ self.c.ap1_to_xyz.T
        located, moved, black = self.projection.apply(xyz)
        positive = np.flatnonzero(~black)
        inverse_wb = fp.bradford_matrix(self.c.white_ref, self.c.xyz(spectrum))
        output = {name: np.zeros_like(flat) for name in stock_models}
        records = {"pixels": len(flat), "moved_by_existing_locus_rule": int(moved.sum()),
                   "Y_not_positive": int(black.sum()), "XYZ_relative_max": 0.0,
                   "max_iterations": 0, "conditioned": conditioned,
                   "batch_spectral_bytes": BATCH_PIXELS*len(self.c.wavelengths)*8}
        # Unit radiance integrals provide the exact linear weights of each stock.
        weights = {name: model.c.layer_exposure(np.eye(len(self.c.wavelengths))).T
                   for name, model in stock_models.items()}
        for start in range(0, len(positive), BATCH_PIXELS):
            idx = positive[start:start+BATCH_PIXELS]
            y = located[idx, 1]
            unit_xyz = located[idx] / y[:, None]
            rho = self.prior(unit_xyz, "measured")
            prior = (rho + PRIOR_POSITIVE_SHARE if conditioned else rho) * spectrum
            if conditioned:
                target = unit_xyz @ inverse_wb.T
                radiance, metrics = self.condition(prior, target)
                records["XYZ_relative_max"] = max(records["XYZ_relative_max"], metrics["XYZ_relative_max"])
                records["max_iterations"] = max(records["max_iterations"], metrics["iterations"])
            else:
                radiance = prior
            for name in output:
                output[name][idx] = (radiance @ weights[name].T) * y[:, None]
            if start and start % (BATCH_PIXELS*128) == 0:
                print(f"  spectra {start}/{len(positive)}, conditioned={conditioned}", flush=True)
        for name in output:
            if not np.isfinite(output[name]).all() or np.min(output[name]) < 0:
                raise FloatingPointError(f"invalid film exposure for {name}")
            output[name] = output[name].reshape(image.shape)
        records["seconds"] = time.perf_counter()-started
        return output, records
