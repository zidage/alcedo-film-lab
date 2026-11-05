"""Rule 'stock_character' (step P12, ROADMAP section 2, user decision of 2026-11-04): a creative control k that enlarges how the data of a negative
differ from the average negative of its medium. k = 1 is the data, k = 0 gives the average of the pool, k = 2 doubles each difference.

Why: the scan cannot separate stocks that have nearly the same negatives (P12 report, section 4). The photo stocks of the model differ little,
because the Kodak data sheets of photo stocks give only the midscale neutral of the dyes. This control keeps the spectral model and the direction of
each difference from the data of the stock; only the size is chosen. It is not a measurement.

The pool is the pool of rule generic_scan for the medium (p10_chart_scan/scan_generic.py), so the scanner setup stays that of the average negative.
Two parts of the profile change, in memory, before the model is built:
- Spectral sensitivity, per layer: the centroid and the width of the main lobe (log sensitivity within LOBE_LOG of its peak, weighted by the
  sensitivity). New centroid = pool mean + k (stock - pool mean); new log width = pool mean of log width + k (stock - pool mean). The wavelength axis
  of the curve of the stock moves and stretches to these values, so the curve keeps its own shape and peak.
- Characteristic curves, per channel: density above the lowest density of the curve, against log H relative to the 18 % grey exposure of the stock
  (option midscale_log_h). On the range that every pool stock covers, deviation = curve - pool mean; outside it, the deviation at the nearest end.
  New curve = curve + (k - 1) deviation, made non-decreasing and not below the lowest density.
The dyes, the inhibition, and the other data do not change. The mean of the pool does not change with k (the mean of the deviations is zero).
"""

from __future__ import annotations

import copy
from typing import Callable

import numpy as np

LAYERS = ("cyan_forming_layer", "magenta_forming_layer", "yellow_forming_layer")
CHANNELS = ("red", "green", "blue")
LOBE_LOG = 1.5  # log10 sensitivity below the peak that still counts as the main lobe
CURVE_STEP = 0.01  # log H step of the pool mean, the step of the digitized curves
_stats: dict[tuple, dict] = {}


def lobe_moments(x: np.ndarray, log_s: np.ndarray) -> tuple[float, float]:
    """Centroid and width (nm) of the main lobe of a log sensitivity curve, weighted by the sensitivity."""
    lobe = log_s >= log_s.max() - LOBE_LOG
    w = 10.0 ** log_s[lobe]
    centre = float((x[lobe] * w).sum() / w.sum())
    return centre, float(np.sqrt(((x[lobe] - centre) ** 2 * w).sum() / w.sum()))


def _curve(profile: dict, channel: str, anchor: float) -> tuple[np.ndarray, np.ndarray, float]:
    c = profile["charts"]["characteristic"]["curves"][channel]
    x, y = np.array(c["x"], dtype=np.float64), np.array(c["y"], dtype=np.float64)
    return x - anchor, y - y.min(), float(y.min())


def _sensitivity(profile: dict, layer: str) -> tuple[np.ndarray, np.ndarray]:
    c = profile["charts"]["spectral_sensitivity"]["curves"][layer]
    return np.array(c["x"], dtype=np.float64), np.array(c["y"], dtype=np.float64)


def pool_stats(pool: tuple[str, ...], load: Callable[[str], dict], anchor_of: Callable[[str], float]) -> dict:
    """The pool means: per layer the centroid and the mean log width; per channel the mean curve on the common range. Kept per pool."""
    if pool not in _stats:
        profiles = {s: load(s) for s in pool}
        sens = {}
        for layer in LAYERS:
            moments = np.array([lobe_moments(*_sensitivity(profiles[s], layer)) for s in pool])
            sens[layer] = (float(moments[:, 0].mean()), float(np.log(moments[:, 1]).mean()))
        curves = {}
        for ch in CHANNELS:
            parts = [_curve(profiles[s], ch, anchor_of(s)) for s in pool]
            low, high = max(p[0][0] for p in parts), min(p[0][-1] for p in parts)
            if high - low < 1.0:
                raise ValueError(f"rule stock_character: the {ch} curves of the pool {pool} share only {high - low:.2f} log H")
            grid = np.arange(low, high + 1e-9, CURVE_STEP)
            curves[ch] = (grid, np.mean([np.interp(grid, p[0], p[1]) for p in parts], axis=0))
        _stats[pool] = {"sensitivity": sens, "curves": curves}
    return _stats[pool]


def characterised(profile: dict, anchor: float, stats: dict, k: float) -> tuple[dict, dict]:
    """A copy of the profile of a negative with stock character k, and a record of the changed values."""
    out = copy.deepcopy(profile)
    record = {}
    for layer in LAYERS:
        x, log_s = _sensitivity(out, layer)
        centre, width = lobe_moments(x, log_s)
        mean_centre, mean_log_width = stats["sensitivity"][layer]
        new_centre = mean_centre + k * (centre - mean_centre)
        new_width = float(np.exp(mean_log_width + k * (np.log(width) - mean_log_width)))
        out["charts"]["spectral_sensitivity"]["curves"][layer]["x"] = (new_centre + (x - centre) * new_width / width).tolist()
        record[layer] = {"centroid_nm": [round(centre, 2), round(new_centre, 2)], "width_nm": [round(width, 2), round(new_width, 2)]}
    for ch in CHANNELS:
        x_rel, above, dmin = _curve(out, ch, anchor)
        grid, mean = stats["curves"][ch]
        deviation = np.interp(x_rel, grid, np.interp(grid, x_rel, above) - mean)
        new = np.maximum.accumulate(np.maximum(above + (k - 1.0) * deviation, 0.0))
        out["charts"]["characteristic"]["curves"][ch]["y"] = (new + dmin).tolist()
        mid = (x_rel >= -1.0) & (x_rel <= 1.0)
        record[ch] = {"slope_-1_to_+1_log_h": [round(float(np.polyfit(x_rel[mid], above[mid], 1)[0]), 4), round(float(np.polyfit(x_rel[mid], new[mid], 1)[0]), 4)]}
    out["stock_character"] = {"k": k, "rule": "stock_character", "changes": record}
    return out, record


def profile_name(stock: str, k: float) -> str:
    return f"{stock}@stock_character={k:g}"


def register(overrides: dict, load: Callable[[str], dict], stock: str, k: float, pool: tuple[str, ...], anchor_of: Callable[[str], float]) -> str:
    """Put the profile of the stock with character k in overrides (p0.PROFILE_OVERRIDES) and return its name. k = 1 returns the stock."""
    if k == 1.0:
        return stock
    name = profile_name(stock, k)
    if name not in overrides:
        overrides[name] = characterised(load(stock), anchor_of(stock), pool_stats(pool, load, anchor_of), k)[0]
    return name
