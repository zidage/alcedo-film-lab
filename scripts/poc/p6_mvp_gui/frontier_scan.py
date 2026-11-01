"""The classic scan method of the product: density above base, one window per frame, print curve, Frontier table, lab scanner stage.

Input: density above the film base (H, W, 3) from the APD read of a negative; frontier.npz, which fetch_frontier_tables.py places under build/tmp/p6/vendor/.
Output: sRGB display code. Step: P6, README U61.

Reuse (GPL-3, THIRD_PARTY_NOTICES.md): the form of the window, the print curve, the auto density and grade, and the lab scanner stage follow NegPy cce849ad, docs/PIPELINE.md sections 2, 3, and 6,
written again here on NumPy. The table frontier.npz comes from NegPy, which derives it from the tables of the Fujifilm Frontier 350/370 software. It stays out of this repository, and the product includes it (README U63).
Not used: HyperTone (U61), cast removal (U36), the textured cell vote of the NegPy meters. The result is near NegPy and it is not the output of NegPy.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates, maximum_filter, minimum_filter

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTIER_TABLE = REPO_ROOT / "build" / "tmp" / "p6" / "vendor" / "frontier.npz"
DENSITY_LUMA = np.array([0.2126, 0.7152, 0.0722])
ADOBE_TO_XYZ = np.array([[0.5767, 0.1856, 0.1882], [0.2974, 0.6274, 0.0753], [0.0270, 0.0707, 0.9911]])
XYZ_TO_ADOBE = np.linalg.inv(ADOBE_TO_XYZ)
ADOBE_TO_REC709 = np.array([[1.3983, -0.3983, 0.0], [0.0, 1.0, 0.0], [0.0, -0.0429, 1.0429]])
WHITE_D65 = np.array([0.95047, 1.0, 1.08883])
# papers.py of NegPy, profile 'frontier'.
D_MIN, D_MAX, TOE_SHARPNESS, SHOULDER_SHARPNESS, MIDTONE_GAMMA, GAMMA_WIDTH, SLOPE_GAIN = 0.005, 2.52, 3.53, 1.21, 0.25, 2.0, 1.2
PRINT_DENSITY_AIM = 0.75
ASSUMED_ANCHOR = 0.46
WINDOW_PERCENTILE = 99.5
CHROMA_DENOISE_SIGMA = 2.5
SHARPEN_AMOUNT = 0.25


def load_table(path: Path = FRONTIER_TABLE) -> tuple[np.ndarray, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing. Run fetch_frontier_tables.py (README of this directory).")
    with np.load(path) as f:
        return np.asarray(f["lut"], dtype=np.float64), np.asarray(f["e_max"], dtype=np.float64)


def inverse_softplus(y: float) -> float:
    return float(np.log(np.expm1(y)))


def softplus(z: np.ndarray) -> np.ndarray:
    return np.logaddexp(0.0, z)


def smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb_encode(linear: np.ndarray) -> np.ndarray:
    return np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * np.maximum(linear, 1e-12) ** (1.0 / 2.4) - 0.055)


def table_lookup(table: np.ndarray, position: np.ndarray) -> np.ndarray:
    coordinates = np.moveaxis(position, -1, 0)
    return np.stack([map_coordinates(table[..., k], coordinates, order=1, mode="nearest") for k in range(3)], axis=-1)


def linear_to_lab(linear: np.ndarray) -> np.ndarray:
    t = (linear @ ADOBE_TO_XYZ.T) / WHITE_D65
    f = np.where(t > 0.008856, np.cbrt(np.maximum(t, 1e-9)), 7.787 * t + 16.0 / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_linear(lab: np.ndarray) -> np.ndarray:
    fy = (lab[..., 0] + 16.0) / 116.0
    f = np.stack([fy + lab[..., 1] / 500.0, fy, fy - lab[..., 2] / 200.0], axis=-1)
    t = np.where(f > 0.2069, f**3, (f - 16.0 / 116.0) / 7.787)
    return (t * WHITE_D65) @ XYZ_TO_ADOBE.T


def scanner_stage(linear: np.ndarray, denoise_sigma: float = CHROMA_DENOISE_SIGMA, sharpen: float = SHARPEN_AMOUNT) -> np.ndarray:
    """NegPy section 6: chroma denoise 2.5, skin protection 0.5, unsharp mask 0.25 with radius 1 and masking 0.1, on the render buffer. The defaults are those of NegPy."""
    lab = linear_to_lab(linear)
    sigma = denoise_sigma
    low = np.stack([gaussian_filter(lab[..., k], sigma, mode="nearest") for k in (1, 2)], axis=-1)
    gradient = np.hypot(*np.gradient(low[..., 0])) + np.hypot(*np.gradient(low[..., 1]))
    keep = smoothstep(1.0, 2.5, sigma * gradient)[..., None]
    ab = low + keep * (lab[..., 1:] - low)
    chroma = np.hypot(ab[..., 0], ab[..., 1])
    hue = np.degrees(np.arctan2(ab[..., 1], ab[..., 0])) % 360.0
    lightness = lab[..., 0]
    skin = (1.0 - smoothstep(12.0, 20.0, np.abs(hue - 52.0))) * (1.0 - smoothstep(35.0, 60.0, chroma)) * smoothstep(2.0, 4.0, chroma) * smoothstep(5.0, 15.0, lightness) * (1.0 - smoothstep(90.0, 95.0, lightness))
    ceiling = 22.0 / 0.5
    start = 0.6 * ceiling
    knee = np.where(chroma > start, start + (ceiling - start) * (1.0 - np.exp(-(chroma - start) / (ceiling - start))), chroma)
    limited = chroma + skin * (knee - chroma)
    ab = ab * (limited / np.maximum(chroma, 1e-6))[..., None]
    detail = lightness - gaussian_filter(lightness, 1.0, mode="nearest")
    gain = sharpen * 2.5 * smoothstep(0.25, 0.33, np.abs(detail)) * smoothstep(0.5, 1.0, np.hypot(*np.gradient(lightness))) * (1.0 / 3.0 + 2.0 / 3.0 * smoothstep(0.0, 35.0, lightness))
    sharp = np.clip(lightness + detail * gain, minimum_filter(lightness, 3) - 2.0, maximum_filter(lightness, 3) + 1.0)
    return lab_to_linear(np.concatenate([sharp[..., None], ab], axis=-1))


def print_density(delta: np.ndarray, density_aim: float = PRINT_DENSITY_AIM, grade: float = 1.0, window_percentile: float = WINDOW_PERCENTILE) -> np.ndarray:
    """Density above base to the density of the scanner print curve. The frame window and the two meters are statistics of this frame. grade scales the slope of the auto grade, and the limits of the slope stay."""
    luma = delta @ DENSITY_LUMA
    dense = np.maximum(delta[luma >= np.percentile(luma, window_percentile)].mean(axis=0), 0.3)
    x = 1.0 - delta / dense
    density_range = float(dense.mean())
    texture = max(float(np.percentile(luma, 90.0) - np.percentile(luma, 10.0)), 0.1)
    grade_range = 0.85 * density_range * min(0.6 + 0.4 * 0.9 / texture, 1.2 * 0.9 / texture)
    slope = float(np.clip(2.9 * np.clip(grade_range, 0.3, 3.5) / 1.15 * SLOPE_GAIN * grade, 2.0, 10.0))
    mean_x = x.mean(axis=-1)
    low, high = np.percentile(mean_x, (5.0, 95.0))
    trimmed = mean_x[(mean_x >= low) & (mean_x <= high)]
    meter = 0.5 * (float(trimmed.mean()) + 0.5 * (low + high))
    anchor = ASSUMED_ANCHOR + float(np.clip(0.2 * (meter - ASSUMED_ANCHOR), -0.12, 0.12))
    v1_aim = D_MAX - inverse_softplus(TOE_SHARPNESS * (D_MAX - density_aim)) / TOE_SHARPNESS
    v_aim = D_MIN + inverse_softplus(SHOULDER_SHARPNESS * (v1_aim - D_MIN)) / SHOULDER_SHARPNESS
    lo, up = v_aim - MIDTONE_GAMMA * GAMMA_WIDTH, v_aim + MIDTONE_GAMMA * GAMMA_WIDTH
    for _ in range(60):
        middle = 0.5 * (lo + up)
        lo, up = (middle, up) if middle + MIDTONE_GAMMA * GAMMA_WIDTH * np.tanh((middle - v_aim) / GAMMA_WIDTH) < v_aim else (lo, middle)
    pivot = anchor - 0.5 * (lo + up) / slope
    v = slope * (x - pivot)
    v = v + MIDTONE_GAMMA * GAMMA_WIDTH * np.tanh((v - v_aim) / GAMMA_WIDTH)
    v = D_MIN + softplus(SHOULDER_SHARPNESS * (v - D_MIN)) / SHOULDER_SHARPNESS
    return D_MAX - softplus(TOE_SHARPNESS * (D_MAX - v)) / TOE_SHARPNESS


def scan_to_display(delta: np.ndarray, table: tuple[np.ndarray, np.ndarray], lab_stage: bool = True, density_aim: float = PRINT_DENSITY_AIM, grade: float = 1.0, window_percentile: float = WINDOW_PERCENTILE,
                    denoise_sigma: float = CHROMA_DENOISE_SIGMA, sharpen: float = SHARPEN_AMOUNT) -> np.ndarray:
    """Density above base (H, W, 3) to sRGB display code."""
    lut, e_max = table
    nodes = lut.shape[0] - 1
    scale = 10.0 ** -D_MIN
    linear = scale * table_lookup(lut, np.clip(print_density(delta, density_aim, grade, window_percentile) - D_MIN, 0.0, e_max) / e_max * nodes)
    black = scale * table_lookup(lut, np.minimum(np.full((1, 1, 3), D_MAX - D_MIN), e_max) / e_max * nodes)[0, 0]
    black_luminance = float(black @ ADOBE_TO_XYZ[1])
    linear = np.clip((linear - black_luminance) / (1.0 - black_luminance), 0.0, None)
    if lab_stage:
        linear = scanner_stage(linear, denoise_sigma, sharpen)
    return srgb_encode(np.clip(linear @ ADOBE_TO_REC709.T, 0.0, 1.0))
