"""Fit a scanner model to public chart scans of real film. TEST ONLY: no license is stated for the data, so the results stay local and no product path may use them (README U28).

Input: build/tmp/p3/filmanalyzer/measurements.json (not committed), the P2 negative.
Output (local only): build/tmp/p3/fitted_scanner/fits.json. Step: P3, README section 8.

Model, for one negative and one scanner. d = reading of the scanner (equation 1 of ST 2065-2 with fitted bands) above the base.
    d' = d C                                 density crosstalk (unit diagonal)
    E  = 10 ^ ((d' - g) / 0.55)              per channel
    y  = b + (w - b) E^n / (E^n + 1/0.22 - 1)  per channel: position g, contrast n, lift b, top w
    display = y M                            display matrix (each row sums to 1)
Levels, each one adds to the one before: A tone (g, n, b, w, with APD as the reading); B the bands of the light (peak, width);
C the density crosstalk (6); D the display matrix (6). The film exposure shift is searched on a grid. The fit minimizes Lab differences with a soft-L1 loss.

Checks of generality. All are held out of the fit: patch folds (4 folds of the colour and neutral patches); the outer offsets (fit -1, 0, +1, test -2, +2); and the same scanner on another film
(5207 on X-T5 to Portra 400 on X-T5, 5207 on CoolScan to 5219 on CoolScan, with g refitted, because a new roll is set by its own base and grey).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from compare_film_analyzer import D50, SRGB_TO_XYZ, SRGB_WHITE, lab_to_xyz_d50  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE = REPO_ROOT / "build" / "tmp" / "p3" / "filmanalyzer" / "measurements.json"
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "fitted_scanner"
SHIFTS = (-1.0, -0.5, 0.0, 0.5, 1.0)
LEVELS = ("A", "B", "C", "D")
WAVELENGTHS = np.arange(400.0, 751.0)
STOCK_OPTIONS = {"5207": ("5207_2383", dict(scene_light="D55")), "5219": ("5219_2383", dict(scene_light="D55", print_timing=1.0)), "portra": ("portra400_endura", {})}
SLOPE = 0.55
GREY_TERM = 1.0 / 0.22 - 1.0


def bands(peaks: np.ndarray, widths: np.ndarray) -> np.ndarray:
    return np.stack([np.exp(-0.5 * ((WAVELENGTHS - p) / (w / 2.3548)) ** 2) + 0.05 / (1.0 + ((WAVELENGTHS - p) / w) ** 2) for p, w in zip(peaks, widths)])


class ChartSet:
    """Spectral density of the negative for every patch and offset of one chart scan, for one exposure shift."""

    def __init__(self, stock: str, set_name: str, data: dict, shift: float, negative: scan.ScanPreview) -> None:
        rows = data[set_name]
        self.offsets = np.array([r["exposure_offset"] for r in rows], dtype=np.float64)
        self.names = [r["patch_name"] for r in rows]
        self.target = np.array([[r["mean_L"], r["mean_a"], r["mean_b_lab"]] for r in rows])
        reference = np.array([[r["reference_L"], r["reference_a"], r["reference_b"]] for r in rows])
        n = negative.negative
        c = n.c
        ap1 = lab_to_xyz_d50(reference) @ (c.xyz_to_ap1 @ fp.bradford_matrix(D50, c.ap1_to_xyz @ np.ones(3))).T
        ap1 = ap1 * 2.0 ** (self.offsets + shift)[:, None]
        status, _ = n.negative_image(ap1[None].astype(np.float32))
        film = n.film
        base = film.status_density(film.negative_dmin, film.w_status_m)
        amounts, _ = fp.solve_amounts(status[0].astype(np.float64) - film.negative_curve_dmin + base, film.negative_dmin, film.negative_dyes, film.w_status_m)
        self.transmission = 10.0 ** -film.negative_spectral_density(amounts)
        self.base = 10.0 ** -film.negative_dmin
        self.nodes = np.searchsorted(film.grid.wavelengths, WAVELENGTHS)
        apd_wavelengths, apd = scan.read_apd_responsivities()
        self.apd_nodes = np.searchsorted(film.grid.wavelengths, apd_wavelengths)
        self.apd_weights = apd

    def reading(self, peaks: np.ndarray | None, widths: np.ndarray | None) -> np.ndarray:
        if peaks is None:
            nodes, weights = self.apd_nodes, self.apd_weights
        else:
            nodes, weights = self.nodes, bands(peaks, widths)
        sample = self.transmission[:, nodes] @ weights.T
        white = self.base[nodes] @ weights.T
        return -np.log10(np.maximum(sample / white, 1e-9))


def linear_to_lab(y: np.ndarray) -> np.ndarray:
    return fp.sr.xyz_to_lab(np.maximum(y, 1e-6) @ SRGB_TO_XYZ.T, SRGB_WHITE)


LAYOUT = {"g": 3, "n": 3, "b": 3, "w": 3, "peak": 3, "width": 3, "C": 6, "M": 6}


def names_for(level: str) -> list[str]:
    return ["g", "n", "b", "w"] + (["peak", "width"] if level in "BCD" else []) + (["C"] if level in "CD" else []) + (["M"] if level == "D" else [])


def unpack(x: np.ndarray, level: str) -> dict:
    out, k = {}, 0
    for name in names_for(level):
        out[name] = x[k:k + LAYOUT[name]]
        k += LAYOUT[name]
    return out


def off_diagonal(values: np.ndarray, row_sum_one: bool) -> np.ndarray:
    m = np.eye(3)
    m[0, 1], m[0, 2], m[1, 0], m[1, 2], m[2, 0], m[2, 1] = values
    if row_sum_one:
        m[np.arange(3), np.arange(3)] = 1.0 - (m.sum(axis=1) - 1.0)
    return m


def scanner_output(d: np.ndarray, p: dict) -> np.ndarray:
    """Reading above the base to linear display values."""
    if "C" in p:
        d = d @ off_diagonal(p["C"], False).T
    exposure = 10.0 ** np.clip((d - p["g"]) / SLOPE, -6.0, 6.0)
    powered = exposure ** p["n"]
    y = p["b"] + (p["w"] - p["b"]) * powered / (powered + GREY_TERM)
    if "M" in p:
        y = y @ off_diagonal(p["M"], True).T
    return y


def predict(chart: ChartSet, p: dict) -> np.ndarray:
    return linear_to_lab(scanner_output(chart.reading(p.get("peak"), p.get("width")), p))


def start_and_bounds(level: str, previous: dict | None, light: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = {"g": [0.7, 0.7, 0.7], "n": [1.6, 1.6, 1.6], "b": [0.01, 0.01, 0.01], "w": [0.95, 0.95, 0.95], "peak": [632.0, 540.0, 465.0],
              "width": [20.0, 35.0, 20.0] if light == "narrow" else [70.0, 70.0, 60.0], "C": [0.0] * 6, "M": [0.0] * 6}
    limits = {"g": (0.2, 1.5), "n": (0.6, 4.0), "b": (0.0, 0.25), "w": (0.6, 1.1), "peak": (None, None), "width": (10.0, 130.0), "C": (-0.4, 0.4), "M": (-0.5, 0.5)}
    x, low, high = [], [], []
    for name in names_for(level):
        current = np.array(previous[name] if previous and name in previous else values[name], dtype=np.float64)
        x.append(current)
        if name == "peak":
            low.append(np.array([590.0, 505.0, 425.0]))
            high.append(np.array([700.0, 580.0, 490.0]))
        else:
            low.append(np.full(LAYOUT[name], limits[name][0]))
            high.append(np.full(LAYOUT[name], limits[name][1]))
    x, low, high = np.concatenate(x), np.concatenate(low), np.concatenate(high)
    return np.clip(x, low + 1e-6, high - 1e-6), low, high


def fit(chart: ChartSet, level: str, select: np.ndarray, previous: dict | None = None) -> tuple[dict, float]:
    best = None
    for light in (("narrow", "wide") if level in "BCD" and not (previous and "peak" in previous) else ("narrow",)):
        x0, low, high = start_and_bounds(level, previous, light)

        def residual(x: np.ndarray) -> np.ndarray:
            return (predict(chart, unpack(x, level)) - chart.target)[select].ravel()

        result = least_squares(residual, x0, bounds=(low, high), loss="soft_l1", f_scale=3.0, max_nfev=120)
        if best is None or result.cost < best.cost:
            best = result
    return unpack(best.x, level), float(best.cost)


def delta_e(chart: ChartSet, p: dict, select: np.ndarray) -> dict:
    d = np.linalg.norm(predict(chart, p)[select] - chart.target[select], axis=1)
    return {"median": float(np.median(d).round(2)), "p95": float(np.percentile(d, 95).round(2))}


def refit_position(chart: ChartSet, p: dict) -> dict:
    """A new roll: only the position g changes, as the base and the grey of a roll are set per roll."""
    fixed = {k: v for k, v in p.items() if k != "g"}

    def residual(g: np.ndarray) -> np.ndarray:
        return (predict(chart, {**fixed, "g": g}) - chart.target).ravel()

    result = least_squares(residual, np.array(p["g"]), bounds=(0.1, 2.0), loss="soft_l1", f_scale=3.0, max_nfev=60)
    return {**fixed, "g": result.x}


def refit_tone(chart: ChartSet, fixed: dict, start: dict) -> dict:
    """Only the tone (g, n, b, w) is fitted. The light and the crosstalk stay as in `fixed`."""
    keys = ("g", "n", "b", "w")
    x0 = np.concatenate([start[k] for k in keys])
    low = np.array([0.1] * 3 + [0.6] * 3 + [0.0] * 3 + [0.6] * 3)
    high = np.array([1.5] * 3 + [4.0] * 3 + [0.25] * 3 + [1.1] * 3)

    def rebuild(x: np.ndarray) -> dict:
        return {**fixed, **{k: x[3 * i:3 * i + 3] for i, k in enumerate(keys)}}

    result = least_squares(lambda x: (predict(chart, rebuild(x)) - chart.target).ravel(), np.clip(x0, low + 1e-6, high - 1e-6), bounds=(low, high), loss="soft_l1", f_scale=3.0, max_nfev=120)
    return rebuild(result.x)


def crosstalk_transfer(a: tuple[str, str], b: tuple[str, str], data: dict, parameters: dict, shifts: dict) -> dict:
    """Test: is the crosstalk a property of one scanner? Scanner a keeps its own tone curves but takes the light and the crosstalk of scanner b."""
    stock_id, extra = STOCK_OPTIONS[a[0]]
    negative = scan.ScanPreview(fp.FilmOptions(**{**fp.STOCKS[stock_id], **fp.DARKROOM, **extra, "enlarger_flare": 0.0}))
    chart = ChartSet(a[0], a[1], data, shifts[a[1]], negative)
    every = np.ones(len(chart.offsets), dtype=bool)
    source = {k: np.array(v) for k, v in parameters[b[1]]["levels"]["C"]["parameters"].items()}
    fixed = {k: source[k] for k in ("peak", "width", "C")}
    own = {k: np.array(v) for k, v in parameters[a[1]]["levels"]["C"]["parameters"].items()}
    return {"tone_only_level_A": parameters[a[1]]["levels"]["A"]["train_all"], "own_level_C": parameters[a[1]]["levels"]["C"]["train_all"],
            f"own_tone_with_light_and_crosstalk_of_{b[1]}": delta_e(chart, refit_tone(chart, fixed, own), every)}


def run(label: str, stock: str, set_name: str, other: tuple[str, str] | None, data: dict) -> dict:
    stock_id, extra = STOCK_OPTIONS[stock]
    negative = scan.ScanPreview(fp.FilmOptions(**{**fp.STOCKS[stock_id], **fp.DARKROOM, **extra, "enlarger_flare": 0.0}))
    charts = {s: ChartSet(stock, set_name, data, s, negative) for s in SHIFTS}
    every = np.ones(len(charts[0.0].offsets), dtype=bool)
    level_a = {s: fit(charts[s], "A", every) for s in SHIFTS}
    shift = min(level_a, key=lambda s: level_a[s][1])
    chart = charts[shift]
    out: dict = {"set": set_name, "film_exposure_shift_stops": shift, "patches": int(every.sum()), "levels": {}}
    previous = level_a[shift][0]
    names = np.array(chart.names)
    unique = sorted(set(chart.names))
    rng = np.random.default_rng(20261030)
    folds = np.array_split(rng.permutation(unique), 4)
    other_chart = None
    if other:
        other_id, other_extra = STOCK_OPTIONS[other[0]]
        other_negative = scan.ScanPreview(fp.FilmOptions(**{**fp.STOCKS[other_id], **fp.DARKROOM, **other_extra, "enlarger_flare": 0.0}))
        other_chart = ChartSet(other[0], other[1], data, shift, other_negative)
    for level in LEVELS:
        p, _ = fit(chart, level, every, previous)
        previous = p
        record = {"train_all": delta_e(chart, p, every), "at_offset_0": delta_e(chart, p, chart.offsets == 0)}
        held = []
        for fold in folds:
            test = np.isin(names, fold)
            fold_p, _ = fit(chart, level, ~test, p)
            held.append(np.linalg.norm(predict(chart, fold_p)[test] - chart.target[test], axis=1))
        held = np.concatenate(held)
        record["held_out_patches"] = {"median": float(np.median(held).round(2)), "p95": float(np.percentile(held, 95).round(2))}
        inner = np.abs(chart.offsets) <= 1
        inner_p, _ = fit(chart, level, inner, p)
        record["held_out_offsets_plus_minus_2"] = delta_e(chart, inner_p, ~inner)
        if other_chart is not None:
            moved = refit_position(other_chart, p)
            record[f"same_scanner_on_{other[1]}"] = delta_e(other_chart, moved, np.ones(len(other_chart.offsets), dtype=bool))
        record["parameters"] = {k: np.round(v, 4).tolist() for k, v in p.items()}
        out["levels"][level] = record
        print(label, level, {k: v for k, v in record.items() if k != "parameters"}, flush=True)
    if other_chart is not None:
        own, _ = fit(other_chart, "A", np.ones(len(other_chart.offsets), dtype=bool))
        out[f"own_level_A_fit_of_{other[1]}"] = delta_e(other_chart, own, np.ones(len(other_chart.offsets), dtype=bool))
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(SOURCE.read_text(encoding="utf-8"))["sets"]
    result = {"note": "TEST ONLY. Fitted to public measurements with no stated license. Not for a product path (README U28).",
              "5207_xt5": run("5207_xt5", "5207", "5207_xt5", ("portra", "portra400_xt5"), data),
              "5207_ls9000": run("5207_ls9000", "5207", "5207_ls9000", ("5219", "5219_ls9000"), data)}
    shifts = {k: result[k]["film_exposure_shift_stops"] for k in ("5207_xt5", "5207_ls9000")}
    result["crosstalk_transfer"] = {"5207_xt5": crosstalk_transfer(("5207", "5207_xt5"), ("5207", "5207_ls9000"), data, result, shifts),
                                    "5207_ls9000": crosstalk_transfer(("5207", "5207_ls9000"), ("5207", "5207_xt5"), data, result, shifts)}
    print(json.dumps(result["crosstalk_transfer"], indent=1))
    (OUT / "fits.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
