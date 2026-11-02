"""Rule 'print_cinema_look': a fixed creative rendering of the display code of a print.

Input: sRGB code, 0 to 1, of the finished print. Output: sRGB code, 0 to 1, as float32. Step: P7, ROADMAP U81, U83. Print material cine_look has this rule, and print material kodak_2383 does not.
Source: candidate P6 of a local look study, which the user selected by eye for 5207 on 2383 as the look of La La Land at midday. All constants are creative choices with no measurement. They are not a measurement of 2383 or of the LUT of that film. The density here is a density of display code, and not an optical density of a film.
The operation reads no statistic of a frame and has no spatial part. Function FilmKernelCinemaLook of Alcedo Studio has the same steps.
"""

from __future__ import annotations

import numpy as np

STRENGTH = 0.65
DENSITY_SEPARATION = 1.0 + 0.26 * STRENGTH
DENSITY_COUPLING = np.eye(3) + STRENGTH * (np.array([[1.06, -0.04, -0.02], [-0.03, 1.04, -0.01], [-0.02, -0.08, 1.10]]) - np.eye(3))
PRINT_DOWN_INPUT = (0.0, 0.08, 0.20, 0.42, 0.65, 0.85, 1.0)
PRINT_DOWN_OUTPUT = (0.0, 0.045, 0.135, 0.35, 0.62, 0.85, 1.0)
LUMA = np.array([0.2126, 0.7152, 0.0722])
BLUE_BLACKS = np.array([-0.009, 0.002, 0.024])
WARM_SURFACES = np.array([0.012, 0.002, -0.009])
CHROMA_SCALE = 0.93
BLUE_CHROMA_LOSS = 0.65
BLUE_DENSITY = 0.70
BLUE_SHIFT = np.array([0.06, 0.20, -0.18])
BLUE_SHIFT_SHARE = 0.12
GREEN_SHIFT = np.array([0.06, 0.0, -0.14])
GREEN_SHIFT_SHARE = 0.6


def _print_down(x: np.ndarray) -> np.ndarray:
    return np.interp(x, PRINT_DOWN_INPUT, PRINT_DOWN_OUTPUT)


def cinema_look(code: np.ndarray) -> np.ndarray:
    """The steps of the rule, in this order, in float64."""
    density = -np.log10(np.maximum(np.asarray(code, dtype=np.float64), 1e-6))
    mean = density.mean(axis=-1, keepdims=True)
    density = (mean + DENSITY_SEPARATION * (density - mean)) @ DENSITY_COUPLING.T
    x = 10.0 ** -density
    x = STRENGTH * _print_down(x) + (1.0 - STRENGTH) * x

    y = x @ LUMA
    blue_blacks = np.exp(-((y / 0.25) ** 2)) * (1.0 - np.exp(-y / 0.025))
    warm_surfaces = 4.0 * y * (1.0 - y)
    x = np.clip(x + STRENGTH * (blue_blacks[..., None] * BLUE_BLACKS + warm_surfaces[..., None] * WARM_SURFACES), 0.0, 1.0)

    y = (x @ LUMA)[..., None]
    x = y + CHROMA_SCALE * (x - y)
    blue_excess = np.maximum(x[..., 2] - (x[..., 0] + x[..., 1]) / 2.0, 0.0)[..., None]
    x = (y + (1.0 - BLUE_CHROMA_LOSS * blue_excess) * (x - y)) * (1.0 - BLUE_DENSITY * blue_excess)

    blue_excess = np.maximum(x[..., 2] - (x[..., 0] + x[..., 1]) / 2.0, 0.0)[..., None]
    green_excess = np.maximum(x[..., 1] - (x[..., 0] + x[..., 2]) / 2.0, 0.0)[..., None]
    return np.clip(x + BLUE_SHIFT_SHARE * blue_excess * BLUE_SHIFT + GREEN_SHIFT_SHARE * green_excess * GREEN_SHIFT, 0.0, 1.0).astype(np.float32)
