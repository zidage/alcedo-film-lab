"""Spectral reconstruction candidates of step P1: linear AP1 -> relative spectral radiance.

Input: linear AP1 RGB (ACES white, scene-referred, any positive scale); the P0 evaluator
(scripts/poc/p0_data_and_reference/film_spectral_reference.py) for the CIE tables, the 1 nm
working grid with projected integration weights, and the Portra 400 layer sensitivities; the
training reflectances of the measured prior (spectral_datasets.py).
Output: reconstruction objects. Each one returns the spectral radiance on the 1 nm grid and a
domain mask (False where the method cannot represent the input).

Step: P1 (spectral input), README sections 3.1, 6.1, and 8.

Quantities:
- Radiance L(lambda) is relative: the perfect white diffuser under the scene light has Y = 1.
- XYZ = integral L * cmf d(lambda), CIE 1931 2 degree, projected weights of the 1 nm grid (exact
  for spectra that are linear between 1 nm nodes, P0 report section 4.3).
- AP1: SMPTE ST 2065-1 / Academy S-2014-004 primaries R (0.713, 0.293), G (0.165, 0.830),
  B (0.128, 0.044), white (0.32168, 0.33767). The normalized primary matrix is computed from these
  chromaticities (SMPTE RP 177).
- Reference light E_ref: the CIE daylight formula at T = 6000 K (nominal 6000 * 1.4380 / 1.4388).
  Its chromaticity (0.321681, 0.337673) is the ACES white. Reflectance-type models produce
  L = E_ref * rho; rho is a relative reflectance shape.

Every candidate is homogeneous of degree 1 (README section 6.1): the spectral shape depends on
the chromaticity only, and the brightness is a scale factor. A linear candidate is homogeneous by
construction; a nonlinear candidate solves its shape on the input divided by a positive norm of
the input and multiplies the result by that norm.

Candidates:
- MallettYukselBasis: method of Mallett and Yuksel 2019 (three non-negative basis reflectances
  that add up to 1, minimum roughness, each basis reproduces one primary under the reference
  light), re-derived here for Rec. 709 primaries with the E_ref white. Linear; AP1 inputs outside
  the Rec. 709 triangle give a basis weight below zero and negative radiance lobes.
- SigmoidPolynomial: method of Jakob and Hanika 2019 (rho = algebraic sigmoid of a quadratic
  polynomial in wavelength, fitted per chromaticity in CIELAB). Normalization rule from pbrt-v4
  RGBIlluminantSpectrum: the shape is fitted for rgb / (2 max(rgb)) and the radiance is
  2 max(rgb) * E_ref * rho. rho is bounded in (0, 1); an input that the sigmoid family cannot
  reach within MAX_FIT_DELTA_E_AB is outside the domain.
- MeasuredPriorLinear: minimum-norm estimate under the second-moment matrix C of measured
  reflectances (rho = C A^T (A C A^T)^-1 XYZ). Linear, exact XYZ, can be negative.
- MeasuredPriorNonnegative: the same objective rho^T C^-1 rho with rho >= 0 (quadratic program).
  Exact XYZ for every input inside the spectral-locus cone (every physically realizable colour,
  without an upper bound on rho, so emission is allowed); outside that cone it has no solution.

The prior matrix C is built from training reflectances sampled at 5 nm knots (360-840 nm): each
dataset contributes its mean of rho rho^T with equal weight (rule 'prior_dataset_weight'), and a
ridge of PRIOR_RIDGE_RELATIVE * trace(C) / n is added (rule 'prior_ridge').
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import minimize, nnls

SCRIPT_DIR = Path(__file__).resolve().parent
P0_DIR = SCRIPT_DIR.parent / "p0_data_and_reference"
sys.path.insert(0, str(P0_DIR))
import film_spectral_reference as p0  # noqa: E402

AP1_PRIMARIES_XY = np.array([[0.713, 0.293], [0.165, 0.830], [0.128, 0.044]])
ACES_WHITE_XY = np.array([0.32168, 0.33767])
REC709_PRIMARIES_XY = np.array([[0.640, 0.330], [0.300, 0.600], [0.150, 0.060]])
E_REF_NOMINAL_CCT_K = 6000.0 * 1.4380 / 1.4388  # T = 6000 K after the CIE 015 correction

KNOT_STEP_NM = 5.0
MAX_FIT_DELTA_E_AB = 0.1
PRIOR_RIDGE_RELATIVE = 1.0e-4


def normalized_primary_matrix(primaries_xy: np.ndarray, white_xy: np.ndarray) -> np.ndarray:
    """RGB -> XYZ matrix with RGB (1, 1, 1) -> white with Y = 1 (SMPTE RP 177)."""
    xyz = np.array([[x / y, 1.0, (1.0 - x - y) / y] for x, y in primaries_xy]).T
    w = np.array([white_xy[0] / white_xy[1], 1.0, (1.0 - white_xy.sum()) / white_xy[1]])
    return xyz * np.linalg.solve(xyz, w)[None, :]


def xyz_to_lab(xyz: np.ndarray, white: np.ndarray) -> np.ndarray:
    return p0.xyz_to_lab(xyz, white)


def lab_jacobian(xyz: np.ndarray, white: np.ndarray) -> np.ndarray:
    """d Lab / d XYZ, shape (N, 3, 3)."""
    r = xyz / white
    eps = (6 / 29) ** 3
    df = np.where(r > eps, np.cbrt(np.maximum(r, eps)) / (3 * np.maximum(r, eps)), 1 / (3 * (6 / 29) ** 2)) / white
    j = np.zeros(xyz.shape[:-1] + (3, 3))
    j[..., 0, 1] = 116 * df[..., 1]
    j[..., 1, 0] = 500 * df[..., 0]
    j[..., 1, 1] = -500 * df[..., 1]
    j[..., 2, 1] = 200 * df[..., 1]
    j[..., 2, 2] = -200 * df[..., 2]
    return j


class Colorimetry:
    """The 1 nm grid of the P0 evaluator, XYZ weights, AP1, E_ref, and the Portra layer weights."""

    def __init__(self, film_options: p0.ModelOptions | None = None) -> None:
        self.film = p0.ReferenceModel(step_nm=1.0, rule="projected", options=film_options)
        self.grid = self.film.grid
        self.wavelengths = self.grid.wavelengths
        fwl = self.grid.fine_wavelengths
        table = p0.read_cie_csv("CIE_xyz_1931_2deg.csv")
        cmf = np.stack([np.interp(fwl, table[:, 0], table[:, k], left=0.0, right=0.0) for k in (1, 2, 3)])
        self.w_xyz = self.grid.weights(cmf)  # (3, nodes)
        self.ap1_to_xyz = normalized_primary_matrix(AP1_PRIMARIES_XY, ACES_WHITE_XY)
        self.xyz_to_ap1 = np.linalg.inv(self.ap1_to_xyz)
        e_ref = p0.cie_daylight_relative_spd(E_REF_NOMINAL_CCT_K, self.wavelengths)
        self.e_ref = e_ref / self.xyz(e_ref)[1]
        self.white_ref = self.xyz(self.e_ref)
        self.knots = np.arange(p0.WAVELENGTH_START_NM, p0.WAVELENGTH_STOP_NM + 0.5, KNOT_STEP_NM)
        # Linear interpolation from the 5 nm knots to the 1 nm nodes (exact: a function that is
        # linear between 5 nm knots is linear between 1 nm nodes).
        eye = np.eye(len(self.knots))
        self.knot_to_grid = np.stack([np.interp(self.wavelengths, self.knots, eye[k]) for k in range(len(self.knots))], axis=1)
        # XYZ of E_ref * rho for rho given at the knots: (3, knots)
        self.a_ref_knots = (self.w_xyz * self.e_ref[None, :]) @ self.knot_to_grid
        # Luminous exposure scale of the P0 camera path: an 18 % grey (Y = 0.18) receives 10^-1.44 lux s.
        self.lux_seconds_per_y = 10.0 ** self.film.options.midscale_log_h / 0.18

    def xyz(self, radiance: np.ndarray) -> np.ndarray:
        return self.grid.integrate(radiance, self.w_xyz)

    def layer_exposure(self, radiance: np.ndarray) -> np.ndarray:
        """Portra 400 layer exposure Q (cyan-, magenta-, yellow-forming), P0 definition (Q = 1 is
        the criterion exposure). The radiance is in the relative units above."""
        erg_per_unit = self.lux_seconds_per_y / p0.LUMINOUS_EFFICACY_LM_PER_W * p0.ERG_PER_CM2_PER_J_PER_M2
        return self.film.negative_layer_exposure(np.asarray(radiance) * erg_per_unit)

    def negative_status_m(self, layer_exposure: np.ndarray) -> np.ndarray:
        return self.film.negative_status_m_from_layer_exposure(layer_exposure)

    def spectral_locus_xy(self) -> np.ndarray:
        """Chromaticities of monochromatic light at the 1 nm nodes where the CMF are not zero."""
        w = self.w_xyz
        inside = w[1] > 0
        xyz = w[:, inside].T
        return xyz[:, :2] / xyz.sum(axis=1, keepdims=True)

    def inside_spectral_locus(self, xyz: np.ndarray) -> np.ndarray:
        """True where XYZ lies inside the cone of non-negative spectra (convex hull of the locus
        in xy, with Y > 0). This is the feasibility condition of MeasuredPriorNonnegative."""
        from matplotlib.path import Path as PolyPath

        xyz = np.atleast_2d(xyz)
        s = xyz.sum(axis=1)
        ok = (xyz[:, 1] > 0) & (s > 0)
        xy = np.where(ok[:, None], xyz[:, :2] / np.where(ok, s, 1.0)[:, None], 0.0)
        from scipy.spatial import ConvexHull

        locus = self.spectral_locus_xy()
        hull = locus[ConvexHull(locus).vertices]
        return ok & PolyPath(hull).contains_points(xy)


@dataclass
class Reconstruction:
    radiance: np.ndarray  # (N, nodes)
    domain: np.ndarray  # (N,) bool
    detail: dict


# --------------------------------------------------------------------------------------------
# Mallett and Yuksel 2019, re-derived for Rec. 709 primaries and the E_ref white
# --------------------------------------------------------------------------------------------


class MallettYukselBasis:
    name = "mallett_yuksel_rec709"

    @staticmethod
    def feasible(c: Colorimetry) -> bool:
        """True when three reflectances in [0, 1] that add up to 1 can reproduce the Rec. 709
        primaries (white = the reference light) under the reference light of c (linear program)."""
        from scipy.optimize import linprog

        white_xy = c.white_ref[:2] / c.white_ref.sum()
        targets = normalized_primary_matrix(REC709_PRIMARIES_XY, white_xy).T
        a = c.a_ref_knots
        n = a.shape[1]
        a_eq = np.zeros((9 + n, 3 * n))
        b_eq = np.zeros(9 + n)
        for k in range(3):
            a_eq[3 * k:3 * k + 3, k * n:(k + 1) * n] = a
            b_eq[3 * k:3 * k + 3] = targets[k]
        for j in range(n):
            a_eq[9 + j, [j, n + j, 2 * n + j]] = 1.0
            b_eq[9 + j] = 1.0
        return linprog(np.zeros(3 * n), A_eq=a_eq, b_eq=b_eq, bounds=(0, 1), method="highs").status == 0

    def __init__(self, c: Colorimetry) -> None:
        self.c = c
        white_xy = c.white_ref[:2] / c.white_ref.sum()
        self.rgb709_to_xyz = normalized_primary_matrix(REC709_PRIMARIES_XY, white_xy)
        self.ap1_to_rgb709 = np.linalg.inv(self.rgb709_to_xyz) @ c.ap1_to_xyz
        n = len(c.knots)
        a = c.a_ref_knots
        targets = self.rgb709_to_xyz.T  # row k: XYZ of primary k

        # Variables: basis r and g at the knots; b = 1 - r - g. Objective: sum of squared first
        # differences of the three bases (the roughness of Mallett and Yuksel).
        d = np.diff(np.eye(n), axis=0)
        dtd = d.T @ d

        def split(v):
            return v[:n], v[n:], 1.0 - v[:n] - v[n:]

        def objective(v):
            r, g, b = split(v)
            return float(r @ dtd @ r + g @ dtd @ g + b @ dtd @ b)

        def gradient(v):
            r, g, b = split(v)
            return np.concatenate([2 * dtd @ r - 2 * dtd @ b, 2 * dtd @ g - 2 * dtd @ b])

        constraints = [
            {"type": "eq", "fun": lambda v: np.concatenate([a @ split(v)[0] - targets[0], a @ split(v)[1] - targets[1]])},
            {"type": "ineq", "fun": lambda v: 1.0 - v[:n] - v[n:]},
        ]
        x0 = np.full(2 * n, 1.0 / 3.0)
        result = minimize(objective, x0, jac=gradient, method="SLSQP", bounds=[(0.0, 1.0)] * (2 * n),
                          constraints=constraints, options={"maxiter": 2000, "ftol": 1e-15})
        r, g, b = split(result.x)
        self.basis_knots = np.stack([r, g, np.clip(b, 0.0, None)])
        residual = np.abs(a @ self.basis_knots.T - targets.T).max()
        if not result.success or residual > 1e-6:
            raise RuntimeError(f"Mallett-Yuksel basis solve failed: {result.message}, primary residual {residual:.2e}")
        self.basis = self.basis_knots @ c.knot_to_grid.T  # (3, nodes)
        self.fit_info = {"success": bool(result.success), "iterations": int(result.nit),
                         "max_primary_xyz_residual": float(residual),
                         "min_basis_value": float(self.basis_knots.min()),
                         "sum_to_one_max_error": float(np.abs(self.basis_knots.sum(axis=0) - 1).max())}

    def reconstruct(self, ap1: np.ndarray) -> Reconstruction:
        weights = np.atleast_2d(ap1) @ self.ap1_to_rgb709.T
        radiance = (weights @ self.basis) * self.c.e_ref[None, :]
        return Reconstruction(radiance, np.all(weights >= 0.0, axis=1), {"rec709_weights": weights})


# --------------------------------------------------------------------------------------------
# Jakob and Hanika 2019 sigmoid polynomial, pbrt-v4 normalization
# --------------------------------------------------------------------------------------------


def algebraic_sigmoid(x: np.ndarray) -> np.ndarray:
    return 0.5 + x / (2.0 * np.sqrt(1.0 + x * x))


class SigmoidPolynomial:
    name = "jakob_hanika_sigmoid"
    iterations = 200
    continuation_steps = 8

    def __init__(self, c: Colorimetry) -> None:
        self.c = c
        lo, hi = 360.0, 830.0
        t = (c.wavelengths - lo) / (hi - lo)
        self.powers = np.stack([t * t, t, np.ones_like(t)])  # c0 t^2 + c1 t + c2
        self.w_ref = c.w_xyz * c.e_ref[None, :]

    def spectrum(self, coefficients: np.ndarray) -> np.ndarray:
        return algebraic_sigmoid(np.atleast_2d(coefficients) @ self.powers)

    def _solve(self, lab_target: np.ndarray, start: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Batched Levenberg-Marquardt in CIELAB (white = E_ref, Y = 1)."""
        white = self.c.white_ref
        coef = start.copy()
        mu = np.full(len(coef), 1e-3)

        def evaluate(cf):
            x = cf @ self.powers
            s = algebraic_sigmoid(x)
            xyz = s @ self.w_ref.T
            return x, s, xyz, xyz_to_lab(xyz, white) - lab_target

        x, s, xyz, r = evaluate(coef)
        cost = (r * r).sum(axis=1)
        for _ in range(self.iterations):
            ds = 0.5 * (1.0 + x * x) ** -1.5
            dxyz = np.einsum("np,kn,ln->nlk", ds, self.powers, self.w_ref.T.T) if False else \
                np.einsum("in,kn,jn->ijk", ds, self.powers, self.w_ref)  # (N, 3 xyz, 3 coef)
            jac = lab_jacobian(xyz, white) @ dxyz
            jtj = np.einsum("nij,nik->njk", jac, jac)
            jtr = np.einsum("nij,ni->nj", jac, r)
            damp = jtj + mu[:, None, None] * np.eye(3)[None] * (np.einsum("nii->ni", jtj)[:, :, None] + 1e-12)
            step = -np.linalg.solve(damp, jtr[..., None])[..., 0]
            trial = coef + step
            tx, ts, txyz, tr = evaluate(trial)
            tcost = (tr * tr).sum(axis=1)
            better = tcost < cost
            coef = np.where(better[:, None], trial, coef)
            x = np.where(better[:, None], tx, x)
            s = np.where(better[:, None], ts, s)
            xyz = np.where(better[:, None], txyz, xyz)
            r = np.where(better[:, None], tr, r)
            cost = np.where(better, tcost, cost)
            mu = np.where(better, mu * 0.3, mu * 10.0)
            mu = np.clip(mu, 1e-12, 1e12)
            if np.all(cost < 1e-14):
                break
        return coef, np.sqrt(cost)

    def fit_xyz(self, xyz_norm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Coefficients for target XYZ (reflectance colours under E_ref), and the Delta E*ab."""
        white = self.c.white_ref
        lab = xyz_to_lab(xyz_norm, white)
        coef, de = self._solve(lab, np.zeros((len(lab), 3)))
        hard = de > MAX_FIT_DELTA_E_AB * 1e-2
        if np.any(hard):
            # Continuation from the grey of the same lightness, as in the table construction of
            # Jakob and Hanika: the target moves from L*,0,0 to L*,a*,b* in equal steps.
            start = np.zeros((int(hard.sum()), 3))
            target = lab[hard]
            grey = target * np.array([1.0, 0.0, 0.0])
            for k in range(1, self.continuation_steps + 1):
                start, de_k = self._solve(grey + (target - grey) * k / self.continuation_steps, start)
            improved = de_k < de[hard]
            idx = np.flatnonzero(hard)
            coef[idx[improved]] = start[improved]
            de[idx[improved]] = de_k[improved]
        return coef, de

    def reconstruct(self, ap1: np.ndarray) -> Reconstruction:
        ap1 = np.atleast_2d(ap1)
        scale = 2.0 * ap1.max(axis=1)
        positive = scale > 0
        norm = np.where(positive[:, None], ap1 / np.where(positive, scale, 1.0)[:, None], 0.5)
        coef, de = self.fit_xyz(norm @ self.c.ap1_to_xyz.T)
        radiance = np.where(positive, scale, 0.0)[:, None] * self.spectrum(coef) * self.c.e_ref[None, :]
        domain = positive & (de <= MAX_FIT_DELTA_E_AB)
        return Reconstruction(radiance, domain, {"fit_delta_e_ab": de, "coefficients": coef})


# --------------------------------------------------------------------------------------------
# Measured prior
# --------------------------------------------------------------------------------------------


def prior_second_moment(c: Colorimetry, training_sets: dict[str, np.ndarray]) -> tuple[np.ndarray, dict]:
    """Rules 'prior_dataset_weight' and 'prior_ridge'. training_sets: name -> (count, nodes)."""
    knot_index = np.searchsorted(c.wavelengths, c.knots)
    moments = []
    for name, spectra in training_sets.items():
        at_knots = spectra[:, knot_index]
        moments.append(at_knots.T @ at_knots / len(at_knots))
    moment = np.mean(moments, axis=0)
    n = moment.shape[0]
    ridge = PRIOR_RIDGE_RELATIVE * np.trace(moment) / n
    info = {"datasets": {k: int(len(v)) for k, v in training_sets.items()}, "ridge": float(ridge)}
    return moment + ridge * np.eye(n), info


class MeasuredPriorLinear:
    name = "measured_prior_linear"

    def __init__(self, c: Colorimetry, moment: np.ndarray) -> None:
        self.c = c
        a = c.a_ref_knots
        self.knot_matrix = moment @ a.T @ np.linalg.inv(a @ moment @ a.T)  # XYZ -> rho at knots
        self.grid_matrix = (c.knot_to_grid @ self.knot_matrix) * c.e_ref[:, None]  # XYZ -> radiance

    def reconstruct(self, ap1: np.ndarray) -> Reconstruction:
        xyz = np.atleast_2d(ap1) @ self.c.ap1_to_xyz.T
        radiance = xyz @ self.grid_matrix.T
        return Reconstruction(radiance, np.all(radiance >= 0.0, axis=1), {})


class MeasuredPriorNonnegative:
    name = "measured_prior_nonnegative"
    penalty_weight = 1.0e4
    step_stop = 1.0e-10  # active-set stop: largest step relative to the largest rho

    def __init__(self, c: Colorimetry, moment: np.ndarray) -> None:
        self.c = c
        self.precision = np.linalg.inv(moment)
        self.precision = 0.5 * (self.precision + self.precision.T)
        self.whitener = np.linalg.cholesky(self.precision).T  # precision = W^T W
        self.a = c.a_ref_knots

    def solve_knots(self, xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """rho >= 0 at the knots with A rho = xyz and minimum rho^T C^-1 rho; returns (rho, max
        relative XYZ residual). The XYZ is first scaled to Y = 1 (homogeneity).

        Solve: a penalized non-negative least squares gives a start point and an active set; a
        primal active-set method for the convex quadratic program (Nocedal and Wright, Numerical
        Optimization, algorithm 16.3) then gives the exact minimum. It starts from the penalized
        solution when the equality-constrained minimum on its free set is non-negative, otherwise
        from the vertex nnls(A, xyz), which satisfies A rho = xyz exactly. The method stops when
        the Lagrange multipliers of all zero bounds are non-negative (KKT conditions).
        """
        a, w, p = self.a, self.whitener, self.precision
        n = a.shape[1]
        out = np.zeros((len(xyz), n))
        residual = np.full(len(xyz), np.inf)
        stacked = np.vstack([self.penalty_weight * a, w])
        for k, target in enumerate(xyz):
            scale = abs(target[1]) if target[1] != 0 else 1.0
            t = target / scale
            rho_pen, _ = nnls(stacked, np.concatenate([self.penalty_weight * t, np.zeros(n)]), maxiter=50 * n)
            free = rho_pen > 0
            rho = self._equality_minimum(free, t)
            if rho is None or np.any(rho < 0):
                rho, _ = nnls(a, t, maxiter=50 * n)
                free = rho > 0
            rho = self._active_set(rho, free, t)
            out[k] = rho * scale
            residual[k] = np.abs(a @ rho - t).max() / max(np.abs(t).max(), 1e-300)
        return out, residual

    def _null_space(self, idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
        """SVD of A on the free columns: (pseudo-inverse, null-space basis, rank)."""
        af = self.a[:, idx]
        u, sv, vt = np.linalg.svd(af, full_matrices=True)
        rank = int(np.sum(sv > 1e-12 * sv[0])) if len(sv) else 0
        pinv = vt[:rank].T @ np.diag(1.0 / sv[:rank]) @ u[:, :rank].T
        return pinv, vt[rank:].T, rank

    def _equality_minimum(self, free: np.ndarray, t: np.ndarray) -> np.ndarray | None:
        """Minimum of rho^T P rho with A rho = t and rho = 0 outside the free set (null-space
        method); None when the free columns cannot reach t."""
        idx = np.flatnonzero(free)
        if len(idx) < 1:
            return None
        pinv, z, _ = self._null_space(idx)
        x0 = pinv @ t
        if np.abs(self.a[:, idx] @ x0 - t).max() > 1e-9 * max(np.abs(t).max(), 1e-300):
            return None
        pf = self.precision[np.ix_(idx, idx)]
        if z.shape[1]:
            x0 = x0 - z @ np.linalg.solve(z.T @ pf @ z, z.T @ pf @ x0)
        rho = np.zeros(self.a.shape[1])
        rho[idx] = x0
        return rho

    def _active_set(self, rho: np.ndarray, free: np.ndarray, t: np.ndarray, max_iterations: int = 2000) -> np.ndarray:
        p, a = self.precision, self.a
        free = free.copy()
        for _ in range(max_iterations):
            idx = np.flatnonzero(free)
            pinv, z, _ = self._null_space(idx)
            # Keep A rho = t exact on the free set (removes rounding drift).
            rho[idx] += pinv @ (t - a[:, idx] @ rho[idx])
            grad = p @ rho
            step = np.zeros_like(rho)
            if z.shape[1]:
                pf = p[np.ix_(idx, idx)]
                step[idx] = -z @ np.linalg.solve(z.T @ pf @ z, z.T @ grad[idx])
            if np.abs(step).max() <= self.step_stop * max(np.abs(rho).max(), 1e-300):
                # Multipliers: gradient P rho = A^T nu + mu, mu = 0 on the free set.
                nu = np.linalg.lstsq(a[:, idx].T, grad[idx], rcond=None)[0]
                mu = grad - a.T @ nu
                mu[free] = 0.0
                worst = int(np.argmin(mu))
                if mu[worst] >= -1e-9 * max(np.abs(grad).max(), 1e-300):
                    return np.clip(rho, 0.0, None)
                free[worst] = True
                continue
            blocking = (step < 0) & free
            alpha, block = 1.0, -1
            if blocking.any():
                ratios = np.where(blocking, -rho / np.where(blocking, step, -1.0), np.inf)
                block = int(np.argmin(ratios))
                alpha = min(1.0, float(ratios[block]))
            rho = rho + alpha * step
            if alpha < 1.0:
                rho[block] = 0.0
                free[block] = False
        raise RuntimeError("active-set QP did not converge")

    def reconstruct(self, ap1: np.ndarray, residual_tolerance: float = 1e-6) -> Reconstruction:
        xyz = np.atleast_2d(ap1) @ self.c.ap1_to_xyz.T
        feasible = self.c.inside_spectral_locus(xyz)
        rho = np.zeros((len(xyz), len(self.c.knots)))
        residual = np.full(len(xyz), np.inf)
        if feasible.any():
            rho[feasible], residual[feasible] = self.solve_knots(xyz[feasible])
        radiance = (rho @ self.c.knot_to_grid.T) * self.c.e_ref[None, :]
        domain = feasible & (residual <= residual_tolerance)
        return Reconstruction(radiance, domain, {"relative_xyz_residual": residual, "inside_locus": feasible})


class MeasuredPriorLocal:
    """Chromaticity-local measured prior.

    For an input of chromaticity (u', v'), the second-moment matrix is built from the
    LOCAL_NEIGHBORS training spectra nearest in (u', v') under E_ref, with Gaussian weights
    exp(-d^2 / (2 LOCAL_SIGMA_UV^2)), blended with the global matrix of prior_second_moment:
    C(u', v') = (1 - LOCAL_GLOBAL_BLEND) C_local + LOCAL_GLOBAL_BLEND C_global (rule
    'local_prior_blend'). The estimate is rho = C A^T (A C A^T)^-1 XYZ: exact XYZ, homogeneous
    (the weights depend on chromaticity only), nonlinear in AP1. It can be negative; a negative
    radiance is outside the domain. The weights are fixed before the evaluation; section B of
    run_p1_checks.py reports the effect of LOCAL_SIGMA_UV.
    """

    name = "measured_prior_local"
    batch = 512

    def __init__(self, c: Colorimetry, moment: np.ndarray, training_sets: dict[str, np.ndarray],
                 sigma_uv: float = 0.01, neighbors: int = 256, global_blend: float = 0.05) -> None:
        from scipy.spatial import cKDTree

        self.c = c
        self.moment = moment
        self.sigma_uv, self.neighbors, self.global_blend = sigma_uv, neighbors, global_blend
        knot_index = np.searchsorted(c.wavelengths, c.knots)
        spectra = np.vstack(list(training_sets.values()))
        # Rule 'prior_dataset_weight' also for the local matrix: each record has the weight
        # 1 / (count of its dataset), so that every dataset has the same total weight.
        self.record_weight = np.concatenate([np.full(len(v), 1.0 / len(v)) for v in training_sets.values()])
        self.training_knots = spectra[:, knot_index]
        self.uv = self.chromaticity_uv(spectra @ (c.w_xyz * c.e_ref[None, :]).T)
        self.tree = cKDTree(self.uv)
        self.a = c.a_ref_knots

    @staticmethod
    def chromaticity_uv(xyz: np.ndarray) -> np.ndarray:
        d = xyz[:, 0] + 15 * xyz[:, 1] + 3 * xyz[:, 2]
        d = np.where(d > 0, d, np.nan)
        return np.stack([4 * xyz[:, 0] / d, 9 * xyz[:, 1] / d], axis=1)

    def reconstruct(self, ap1: np.ndarray) -> Reconstruction:
        xyz = np.atleast_2d(ap1) @ self.c.ap1_to_xyz.T
        uv = self.chromaticity_uv(xyz)
        valid = np.all(np.isfinite(uv), axis=1) & (xyz[:, 1] > 0)
        rho = np.zeros((len(xyz), len(self.c.knots)))
        a = self.a
        idx_valid = np.flatnonzero(valid)
        for start in range(0, len(idx_valid), self.batch):
            idx = idx_valid[start:start + self.batch]
            dist, nb = self.tree.query(uv[idx], k=self.neighbors)
            # Relative to the nearest neighbour: the same normalized weights, without underflow.
            w = np.exp(-0.5 * (dist ** 2 - dist[:, :1] ** 2) / self.sigma_uv ** 2) * self.record_weight[nb]
            w /= w.sum(axis=1, keepdims=True)
            x = self.training_knots[nb]  # (B, k, knots)
            local = np.einsum("bk,bki,bkj->bij", w, x, x)
            cov = (1 - self.global_blend) * local + self.global_blend * self.moment[None]
            cat = cov @ a.T  # (B, knots, 3)
            gram = a @ cat  # (B, 3, 3)
            rho[idx] = np.einsum("bij,bj->bi", cat, np.linalg.solve(gram, xyz[idx][..., None])[..., 0])
        radiance = (rho @ self.c.knot_to_grid.T) * self.c.e_ref[None, :]
        domain = valid & np.all(radiance >= 0, axis=1)
        return Reconstruction(radiance, domain, {})


class LocusProjection:
    """Rule 'spectral_locus_projection' (user decision U14, README).

    Y <= 0 gives zero radiance. Y > 0 outside the cone of non-negative spectra that the 5 nm knots
    can reach moves along the line to the reference white at constant Y, to the cone boundary
    (inset by LOCUS_INSET). The hull is built in (X/Y, Z/Y), where a line through the white at
    constant Y stays a line. The map is continuous, depends on the chromaticity only, and is the
    identity inside the cone. It is not RGC and it is not a gamut compression of AP1.
    """

    LOCUS_INSET = 1.0e-6

    def __init__(self, c: Colorimetry) -> None:
        from scipy.spatial import ConvexHull

        columns = c.a_ref_knots.T
        columns = columns[columns[:, 1] > 0]
        points = np.stack([columns[:, 0] / columns[:, 1], columns[:, 2] / columns[:, 1]], axis=1)
        hull = ConvexHull(points)
        self.normals, self.offsets = hull.equations[:, :2], hull.equations[:, 2]
        white = c.a_ref_knots.sum(axis=1)
        self.white = np.array([white[0] / white[1], white[2] / white[1]])

    def apply(self, xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns (projected XYZ, moved mask, Y not positive mask)."""
        xyz = np.atleast_2d(xyz)
        positive = xyz[:, 1] > 0
        out = np.zeros_like(xyz)
        moved = np.zeros(len(xyz), dtype=bool)
        if positive.any():
            y = xyz[positive, 1]
            p = np.stack([xyz[positive, 0] / y, xyz[positive, 2] / y], axis=1)
            d = p - self.white
            rate = d @ self.normals.T
            room = -(self.offsets + self.normals @ self.white)
            with np.errstate(divide="ignore", invalid="ignore"):
                limits = np.where(rate > 0, room[None, :] * (1.0 - self.LOCUS_INSET) / rate, np.inf)
            t = np.minimum(1.0, limits.min(axis=1))
            q = self.white + t[:, None] * d
            out[positive] = np.stack([q[:, 0] * y, y, q[:, 1] * y], axis=1)
            moved[positive] = t < 1.0
        return out, moved, ~positive


class MeasuredPriorLocalNonnegative(MeasuredPriorNonnegative):
    """Combined candidate: the local matrix of MeasuredPriorLocal, rho >= 0, and LocusProjection.

    The closed-form local estimate is the exact QP minimum when it is non-negative; the active-set
    QP of MeasuredPriorNonnegative solves the other inputs with the local precision matrix.
    """

    name = "measured_prior_local_nonnegative"

    def __init__(self, c: Colorimetry, moment: np.ndarray, training_sets: dict[str, np.ndarray],
                 sigma_uv: float = 0.01, neighbors: int = 256, global_blend: float = 0.05) -> None:
        super().__init__(c, moment)
        self.local = MeasuredPriorLocal(c, moment, training_sets, sigma_uv, neighbors, global_blend)
        self.projection = LocusProjection(c)

    def reconstruct(self, ap1: np.ndarray, residual_tolerance: float = 1e-6) -> Reconstruction:
        target, moved, not_positive = self.projection.apply(np.atleast_2d(ap1) @ self.c.ap1_to_xyz.T)
        local, a = self.local, self.a
        rho = np.zeros((len(target), len(self.c.knots)))
        residual = np.zeros(len(target))
        uv = local.chromaticity_uv(target)
        indices = np.flatnonzero(~not_positive)
        quadratic_solves = 0
        for start in range(0, len(indices), local.batch):
            idx = indices[start:start + local.batch]
            dist, nb = local.tree.query(uv[idx], k=local.neighbors)
            w = np.exp(-0.5 * (dist ** 2 - dist[:, :1] ** 2) / local.sigma_uv ** 2) * local.record_weight[nb]
            w /= w.sum(axis=1, keepdims=True)
            x = local.training_knots[nb]
            cov = (1 - local.global_blend) * np.einsum("bk,bki,bkj->bij", w, x, x) + local.global_blend * local.moment[None]
            cat = cov @ a.T
            rho_b = np.einsum("bij,bj->bi", cat, np.linalg.solve(a @ cat, target[idx][..., None])[..., 0])
            for j in np.flatnonzero(np.any(rho_b < 0, axis=1)):
                self.precision = np.linalg.inv(cov[j])
                self.precision = 0.5 * (self.precision + self.precision.T)
                self.whitener = np.linalg.cholesky(self.precision).T
                solved, res = self.solve_knots(target[idx[j]][None])
                rho_b[j], residual[idx[j]] = solved[0], res[0]
                quadratic_solves += 1
            rho[idx] = rho_b
        radiance = (rho @ self.c.knot_to_grid.T) * self.c.e_ref[None, :]
        return Reconstruction(radiance, residual <= residual_tolerance,
                              {"moved_by_rule": moved, "y_not_positive": not_positive, "quadratic_solves": quadratic_solves})


class MeasuredPriorLocalCameraPopulation(MeasuredPriorLocal):
    """Local prior that models the camera stage as a population, without a camera identity.

    Input t = XYZ / Y of the camera AP1. For each training record, b_i and S_i are the mean and the
    covariance of the XYZ error of the IDT (camera AP1 minus truth, divided by the Y of the camera
    AP1) over a set of training cameras. The estimate minimizes
    rho^T C^-1 rho + (A rho - t + b)^T S^-1 (A rho - t + b), rho >= 0, with C, b, S local in u'v'.
    The training spectra are divided by their Y. The estimate does not reproduce the input XYZ
    exactly, by design: the input XYZ has a known error distribution.
    """

    name = "measured_prior_local_camera_population"
    SIGMA_FLOOR = 1.0e-8

    def __init__(self, c: Colorimetry, training_sets: dict[str, np.ndarray], error_mean: np.ndarray,
                 error_moment: np.ndarray, sigma_uv: float = 0.01, neighbors: int = 256, global_blend: float = 0.05) -> None:
        y = np.vstack(list(training_sets.values())) @ (c.w_xyz[1] * c.e_ref)
        offset, normalized = 0, {}
        for name, spectra in training_sets.items():
            normalized[name] = spectra / y[offset:offset + len(spectra), None]
            offset += len(spectra)
        moment, _ = prior_second_moment(c, normalized)
        super().__init__(c, moment, normalized, sigma_uv, neighbors, global_blend)
        self.error_mean, self.error_moment = error_mean, error_moment
        self.projection = LocusProjection(c)

    def reconstruct(self, ap1: np.ndarray) -> Reconstruction:
        xyz = np.atleast_2d(ap1) @ self.c.ap1_to_xyz.T
        located, moved, not_positive = self.projection.apply(xyz)
        uv = self.chromaticity_uv(located)
        rho = np.zeros((len(xyz), len(self.c.knots)))
        a = self.a
        indices = np.flatnonzero(~not_positive)
        solves = 0
        for start in range(0, len(indices), self.batch):
            idx = indices[start:start + self.batch]
            dist, nb = self.tree.query(uv[idx], k=self.neighbors)
            w = np.exp(-0.5 * (dist ** 2 - dist[:, :1] ** 2) / self.sigma_uv ** 2) * self.record_weight[nb]
            w /= w.sum(axis=1, keepdims=True)
            x = self.training_knots[nb]
            cov = (1 - self.global_blend) * np.einsum("bk,bki,bkj->bij", w, x, x) + self.global_blend * self.moment[None]
            bias = np.einsum("bk,bki->bi", w, self.error_mean[nb])
            sigma = np.einsum("bk,bkij->bij", w, self.error_moment[nb]) + self.SIGMA_FLOOR * np.eye(3)[None]
            t = xyz[idx] / xyz[idx, 1:2] - bias
            cat = cov @ a.T
            rho_b = np.einsum("bij,bj->bi", cat, np.linalg.solve(a @ cat + sigma, t[..., None])[..., 0])
            for j in np.flatnonzero(np.any(rho_b < 0, axis=1)):
                precision = np.linalg.inv(cov[j])
                whitener = np.linalg.cholesky(0.5 * (precision + precision.T)).T
                noise = np.linalg.cholesky(np.linalg.inv(sigma[j])).T
                rho_b[j], _ = nnls(np.vstack([noise @ a, whitener]), np.concatenate([noise @ t[j], np.zeros(a.shape[1])]),
                                   maxiter=50 * a.shape[1])
                solves += 1
            rho[idx] = rho_b * xyz[idx, 1:2]
        radiance = (rho @ self.c.knot_to_grid.T) * self.c.e_ref[None, :]
        return Reconstruction(radiance, np.ones(len(xyz), dtype=bool),
                              {"y_not_positive": not_positive, "moved_by_rule": moved, "quadratic_solves": solves})
