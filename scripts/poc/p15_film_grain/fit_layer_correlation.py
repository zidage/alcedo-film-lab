"""Correlation of the layer noise, from the channel correlation of the 5207 scans (step P15).

Input: results/p15_film_grain/stock_grain.json (sigma_amount of each layer of kodak_5207), the 5207 negative of the
viewer, and the default scanner of Negative Scan (negative_scan.ScannerSetup).
Output: results/p15_film_grain/layer_correlation.json.

Measured target (the grain colour study of Alcedo Studio #660, Flextight scans of 5207, flat blocks of net green
density 0.03 to 0.8, scanner white noise excluded by the lag-1 and lag-2 cross-covariance): channel correlation
rg 0.661, gb 0.41, rb 0.246.

Model: the dye-amount noise of the three layers has the standard deviations s_k (stock_grain.json) and the layer
correlation matrix R (unit diagonal, off-diagonal r_rg, r_gb, r_rb). The scanner reads the transmittance through its
three bands; for small noise the scan density changes by J_scan @ da, with J_scan_jk = sum_l w_jl T_l e_kl /
sum_l w_jl T_l. Channel covariance: J_scan S R S J_scan^T, S = diag(s). The correlation is evaluated at net green
density 0.1, 0.3, 0.5, and 0.7 of the neutral ramp and averaged.

Rule 'layer_correlation_from_scan': R is the matrix that gives the three measured channel correlations (least
squares, R positive semidefinite). Requirement: each channel correlation within 0.05 of the target (plan G0, step 5).
With R = I the correlation comes from the dye side absorption alone; that case is reported.

A single shared field (one rho for all pairs, the first form of the plan) cannot give the target: rho = 0.466 matches
rg but gives gb 0.62 and rb 0.53; that run is reported as 'single_shared_field'.

The Flextight bands differ from the default virtual scanner, so the side absorption part differs too (inferred). The
product uses R of 5207 for all stocks: no other stock has a measured scan (inferred).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p7_spectral_acceleration"))
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402
import build_product_resources as bpr  # noqa: E402

GRAIN = ROOT / "results" / "p15_film_grain" / "stock_grain.json"
OUTPUT = ROOT / "results" / "p15_film_grain" / "layer_correlation.json"
TARGET = np.array([0.661, 0.41, 0.246])  # rg, gb, rb
NET_GREEN = (0.1, 0.3, 0.5, 0.7)
LIMIT = 0.05
STOCK = "kodak_5207"
PAIRS = ((0, 1), (1, 2), (0, 2))


def correlations(cov: np.ndarray) -> np.ndarray:
    d = np.sqrt(np.diag(cov))
    c = cov / np.outer(d, d)
    return np.array([c[a, b] for a, b in PAIRS])


def layer_matrix(r: np.ndarray) -> np.ndarray:
    m = np.eye(3)
    for (a, b), v in zip(PAIRS, r):
        m[a, b] = m[b, a] = v
    return m


def main() -> int:
    grain = json.loads(GRAIN.read_text(encoding="utf-8"))["stocks"][STOCK]
    settings = mp.RenderSettings(negative=STOCK)
    settings.validate()
    model = bpr.setup_model(mp.film_options(settings))
    f = model.film
    amounts = np.stack([c.density for c in model.negative_curves], axis=1)
    log_h = model.negative_curves[0].log_h
    green = np.interp(log_h, model.status_curves[1].log_h, model.status_curves[1].density)
    net_green = green - green.min()
    scan_nm, scan_w = mp.negative_scan.ScannerSetup().responsivities()
    model_nm = np.asarray(model.c.wavelengths, dtype=np.float64)
    dyes = np.stack([np.interp(scan_nm, model_nm, f.negative_dyes[k]) for k in range(3)])
    dmin = np.interp(scan_nm, model_nm, f.negative_dmin)

    points = []
    for target in NET_GREEN:
        i = int(np.argmin(np.abs(net_green - target)))
        a = amounts[i]
        t = 10.0 ** (-(dmin + a @ dyes))
        jac = np.array([[np.sum(scan_w[j] * t * dyes[k]) / np.sum(scan_w[j] * t) for k in range(3)] for j in range(3)])
        s = np.array([np.interp(a[k], grain["layer"]["amount"][k], grain["layer"]["sigma_amount"][k]) for k in range(3)])
        points.append((jac, np.diag(s)))

    def channel_corr(r: np.ndarray) -> np.ndarray:
        rm = layer_matrix(r)
        return np.mean([correlations(jac @ s @ rm @ s @ jac.T) for jac, s in points], axis=0)

    def residual(r: np.ndarray) -> np.ndarray:
        penalty = max(0.0, -float(np.linalg.eigvalsh(layer_matrix(r)).min())) * 100.0
        return np.concatenate([channel_corr(r) - TARGET, [penalty]])

    fit = least_squares(residual, x0=np.array([0.5, 0.3, 0.2]), bounds=(-0.99, 0.99))
    r = fit.x
    got = channel_corr(r)
    eig = np.linalg.eigvalsh(layer_matrix(r))
    within = bool(np.all(np.abs(got - TARGET) <= LIMIT) and eig.min() >= -1e-9)

    def single(rho: float) -> np.ndarray:
        return channel_corr(np.array([rho, rho, rho]))

    grid = np.linspace(0, 1, 1001)
    rho = float(grid[int(np.argmin([abs(single(x)[0] - TARGET[0]) for x in grid]))])
    names = ("rg", "gb", "rb")
    out = {"stock": STOCK, "target": dict(zip(names, TARGET.tolist())), "net_green_points": NET_GREEN, "limit": LIMIT,
           "independent_layers": dict(zip(names, np.round(channel_corr(np.zeros(3)), 4).tolist())),
           "single_shared_field": {"rho": rho, "channel": dict(zip(names, np.round(single(rho), 4).tolist()))},
           "layer_correlation": dict(zip(names, np.round(r, 4).tolist())),
           "layer_correlation_eigenvalues": np.round(eig, 4).tolist(),
           "channel_with_layer_correlation": dict(zip(names, np.round(got, 4).tolist())), "within_limit": within,
           "scanner": "negative_scan.ScannerSetup() default bands"}
    print(json.dumps(out, indent=1))
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return 0 if within else 1


if __name__ == "__main__":
    sys.exit(main())
