"""Write the profiles of the reversal films of step P9, and check the values of each source against a second source.

Input: the data sheets in build/tmp/p9/sources/ (fetch_sources.py); first argument, the src/spectral_film_lut directory of a local clone of spectral_film_lut (MIT, ROADMAP U11) at commit bcbcfc68;
second argument, a local clone of the Fotufilm engine (Apache-2.0 code, film profiles CC BY-SA 4.0, ROADMAP U12). The data files of both projects are read as data; their code does not run.
Output: profiles/<film>.json for the five films below; reversal_catalog.json next to this script; results/p9_reversal_light_table/source_checks.json.
Step: P9, ROADMAP U86.

Values per film:
- kodak_ektachrome_e100: KODAK E-4000 Revised 8-18, all charts digitized by this lab from the PDF vector paths (pages 3 and 4), with the functions of digitize_kodak_charts.py (P0). No smoothing, no extrapolation.
- fuji_velvia_100: FUJIFILM AF3-202E, all charts digitized by this lab from the PDF vector paths (page 8). The text of the page is outlined, so each axis is read from the grid lines of the chart.
- fuji_velvia_50, fuji_provia_100f: the charts of AF3-0221E2 and of the Provia 100F bulletin are raster images, so the values come from spectral_film_lut.
- fuji_astia_100f: no data sheet was supplied, and spectral_film_lut has no Astia. The values come from the Fotufilm profile astia100f.json (CC BY-SA 4.0, digitized by that project from FUJIFILM AF3-149E).
  Rule 'fotufilm_exposure_axis': the exposure coordinate x of a Fotufilm profile is log10 H - log10(10 / ISO) lux seconds, and a reversal profile stores the formed density D-min + D-max - D.
  The rule is measured, not stated by Fotufilm: on Velvia 50, Provia 100F, and E100 it puts the Fotufilm curve on the curve of spectral_film_lut (see source_checks.json). The first and last 12 points of each Fotufilm record are its extrapolation, and this script drops them.

Rules, each recorded in the profile:
- 'running_minimum_curve': a characteristic curve of a reversal film keeps its running minimum, because the model inverts a falling curve. The largest rise is in the profile.
- 'zero_minimum_density': no film has a D-min spectrum, so the spectral base density is zero (inferred). The D-min of the curves then comes from the dyes; see reversal_film.py.
- 'neutral_from_dyes': a film with no midscale neutral curve takes the sum of its dye curves (inferred).
- 'relative_sensitivity': a Fuji chart and the Fotufilm values are relative, so their level per layer has no meaning; reversal_film.py then uses rule grey_anchor.

Limits, set before the first run, as in step P5: one source against another, RMS at most 0.03 density on characteristic charts and on peak-normalized dye curves, at most 0.05 log10 on sensitivity charts (a relative chart after the removal of its mean
offset per layer), at most 0.05 response on modulation transfer charts. Axis calibration: each grid line or tick of a chart lies at most 0.6 pt from the line of its value. A result over a limit is recorded; it does not stop the script.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pymupdf

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p0_data_and_reference"))
import digitize_kodak_charts as dk  # noqa: E402

SOURCES = REPO_ROOT / "build" / "tmp" / "p9" / "sources"
PROFILE_DIR = REPO_ROOT / "profiles"
CATALOG = SCRIPT_DIR / "reversal_catalog.json"
RESULT = REPO_ROOT / "results" / "p9_reversal_light_table" / "source_checks.json"
SFL_PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; linearly resampled by this lab; not checked against the manufacturer document"
LAB_PROVENANCE = "digitized point: PDF vector path, Bezier segments evaluated and linearly resampled; no smoothing, no extrapolation"
LIMITS = {"characteristic": 0.03, "spectral_dye_density": 0.03, "spectral_sensitivity": 0.05, "modulation_transfer": 0.05}
AXIS_LIMIT_PT = 0.6
FOTUFILM_EXTRAPOLATED_POINTS = 12
LAYERS = ("cyan_forming_layer", "magenta_forming_layer", "yellow_forming_layer")
DYES = ("cyan_dye", "magenta_dye", "yellow_dye")
CHANNELS = ("red", "green", "blue")

# Each axis: pairs (position on the page in pt, value) of the grid lines or ticks, and 'log' for a logarithmic axis. The positions were read from the vector lines of each page.
E100_CHARTS = {
    "characteristic": dict(page=3, select=(368.0, 358.0, 555.0, 544.0), x=[(368.72, -3.0), (415.02, -2.0), (461.31, -1.0), (507.61, 0.0), (553.91, 1.0)], y=[(542.97, 0.0), (358.6, 4.0)]),
    "spectral_sensitivity": dict(page=4, select=(74.0, 106.0, 276.0, 259.0), x=[(74.34 + 20.055 * k, 250.0 + 50.0 * k) for k in range(11)], y=[(106.97, 2.0), (144.88, 1.0), (182.73, 0.0), (220.64, -1.0), (258.5, -2.0)]),
    "spectral_dye_density": dict(page=4, select=(70.0, 349.0, 272.0, 502.0), x=[(70.64, 400.0), (137.46, 500.0), (204.28, 600.0), (271.1, 700.0)],
                                 y=[(501.08, 0.0), (479.42, 0.2), (457.82, 0.4), (436.17, 0.6), (414.57, 0.8), (392.91, 1.0), (371.31, 1.2), (349.66, 1.4)]),
    "modulation_transfer": dict(page=3, select=(357.0, 126.0, 561.0, 281.0), log=True, x=[(357.64, 1), (379.58, 2), (392.42, 3), (401.53, 4), (408.58, 5), (430.53, 10), (452.42, 20), (481.47, 50), (503.37, 100), (525.31, 200), (560.09, 600)],
                                y=[(126.89, 200), (146.92, 100), (157.18, 70), (166.89, 50), (181.58, 30), (193.3, 20), (213.26, 10), (223.59, 7), (233.3, 5), (247.99, 3), (259.71, 2), (279.67, 1)]),
}
VELVIA_100_CHARTS = {
    "characteristic": dict(page=8, select=(85.0, 173.0, 283.0, 349.0), x=[(86.04, -3.5), (107.57, -3.0), (129.46, -2.5), (151.63, -2.0), (172.94, -1.5), (194.83, -1.0), (216.43, -0.5), (238.32, 0.0), (259.92, 0.5), (281.8, 1.0)],
                           y=[(347.49, 0.0), (326.29, 0.5), (304.59, 1.0), (282.75, 1.5), (261.13, 2.0), (239.57, 2.5), (217.74, 3.0), (195.66, 3.5), (174.22, 4.0)]),
    "spectral_sensitivity": dict(page=8, select=(335.0, 174.0, 535.0, 346.0), x=[(347.05, 400.0), (405.68, 500.0), (463.76, 600.0), (521.8, 700.0)], y=[(205.13, 1.0), (262.76, 0.0), (320.39, -1.0)]),
    "spectral_dye_density": dict(page=8, select=(333.0, 449.0, 535.0, 598.0), x=[(344.97, 400.0), (404.43, 500.0), (463.32, 600.0), (522.19, 700.0)], y=[(596.82, 0.0), (537.28, 0.5), (477.73, 1.0)]),
    "modulation_transfer": dict(page=8, select=(85.0, 447.0, 282.0, 596.0), log=True, x=[(145.76, 5), (170.91, 10), (197.1, 20), (229.78, 50), (255.2, 100)],
                                y=[(462.39, 100), (474.2, 70), (485.98, 50), (502.77, 30), (517.02, 20), (541.11, 10), (552.89, 7), (564.92, 5), (581.21, 3)]),
}
# Velvia 100 characteristic chart: the legend draws R solid, G dash-dot, B dashed.
VELVIA_100_DASHES = {"": "red", "[ 8.999 1.5 2.5 1.5 ] 0": "green", "[ 3 1.5 ] 0": "blue"}

FILMS = {
    "kodak_ektachrome_e100": dict(name="Kodak Ektachrome E100", manufacturer="Kodak", iso=100, source="lab", document="KODAK Alaris Publication No. E-4000, Revised 8-18", pdf="e4000_ektachrome_100.pdf", sfl="kodak_ektachrome_100d.py", fotufilm="ektachromee100.json",
                                  conditions=dict(process="E-6", exposure="Daylight 1/100 second", densitometry="Status A"),
                                  criterion=dict(density=1.0, above_dmin=False, text="E.N.D. = 1.0", effective_exposure_s=0.1), relative_sensitivity=False),
    "fuji_velvia_100": dict(name="Fujichrome Velvia 100", manufacturer="Fujifilm", iso=100, source="lab", document="FUJIFILM Product Information Bulletin AF3-202E", pdf="velvia_100.pdf", sfl=None, fotufilm=None,
                            conditions=dict(process="E-6/CR-56", exposure="Daylight", densitometry="Status A"),
                            criterion=dict(density=1.0, above_dmin=True, text="1.0 above D-min"), relative_sensitivity=True),
    "fuji_velvia_50": dict(name="Fujichrome Velvia 50", manufacturer="Fujifilm", iso=50, source="sfl", document="FUJIFILM Data Guide AF3-0221E2 (charts by spectral_film_lut)", sfl="fuji_velvia_50.py", fotufilm="velvia50.json",
                           conditions=dict(process="E-6/CR-56", exposure="Daylight", densitometry="Status A"),
                           criterion=dict(density=1.0, above_dmin=True, text="1.0 above D-min (the criterion of the Fuji bulletins; the raster chart was not read)"), relative_sensitivity=True),
    "fuji_provia_100f": dict(name="Fujichrome Provia 100F", manufacturer="Fujifilm", iso=100, source="sfl", document="FUJIFILM Product Information Bulletin, PROVIA 100F (charts by spectral_film_lut)", sfl="fuji_provia_100f.py", fotufilm="provia100f.json",
                             conditions=dict(process="E-6/CR-56", exposure="Daylight", densitometry="Fuji FAD-30S (Status A)"),
                             criterion=dict(density=1.0, above_dmin=True, text="1.0 above D-min, stated on the chart"), relative_sensitivity=True),
    "fuji_astia_100f": dict(name="Fujichrome Astia 100F", manufacturer="Fujifilm", iso=100, source="fotufilm", document="FUJIFILM AF3-149E (charts by Fotufilm)", sfl=None, fotufilm="astia100f.json",
                            conditions=dict(process="E-6", exposure="Daylight", densitometry="Status A (the Fuji bulletins)"),
                            criterion=dict(density=1.0, above_dmin=True, text="not stated by Fotufilm; the values are relative"), relative_sensitivity=True),
}
ORDER = ("fuji_velvia_50", "fuji_velvia_100", "fuji_provia_100f", "fuji_astia_100f", "kodak_ektachrome_e100")


# --- reading -----------------------------------------------------------------------------------

def axis_map(pairs: list, log: bool) -> tuple[callable, float]:
    """A linear map from the page to the axis value (log10 of the value on a log axis), by least squares on the pairs. Returns the map and the largest distance in pt of a pair from its line."""
    position = np.array([p for p, _ in pairs], dtype=float)
    value = np.array([math.log10(v) if log else v for _, v in pairs], dtype=float)
    slope, offset = np.polyfit(position, value, 1)
    residual = float(np.abs((value - offset) / slope - position).max()) if len(pairs) > 2 else 0.0
    return (lambda p: 10.0 ** (offset + slope * p)) if log else (lambda p: offset + slope * p), residual


def chart_paths(page: pymupdf.Page, select: tuple) -> list[tuple[np.ndarray, dict]]:
    """The stroked curves inside the rectangle: each subpath of a path with a Bezier segment, or of a path of 8 or more segments, with the path that holds it. Grid lines and frames have fewer segments or only straight ones."""
    x0, y0, x1, y1 = select
    out = []
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if drawing["type"] != "s" or r.x0 < x0 or r.x1 > x1 or r.y0 < y0 or r.y1 > y1:
            continue
        if any(item[0] not in ("l", "c") for item in drawing["items"]):
            continue
        if len(drawing["items"]) < 8 and not any(item[0] == "c" for item in drawing["items"]):
            continue
        for polyline in dk.path_to_polylines(drawing)[0]:
            if len(polyline) >= 8:  # a grid line is one straight segment, two points
                out.append((polyline, drawing))
    return out


def digitize_chart(pdf: Path, name: str, spec: dict) -> tuple[dict, dict]:
    page = pymupdf.open(pdf)[spec["page"] - 1]
    log = bool(spec.get("log"))
    to_x, x_residual = axis_map(spec["x"], log)
    to_y, y_residual = axis_map(spec["y"], log)
    if max(x_residual, y_residual) > AXIS_LIMIT_PT:
        print(f"{pdf.name} {name}: a grid line is {max(x_residual, y_residual):.2f} pt from its value, above the limit {AXIS_LIMIT_PT} pt (recorded)", flush=True)
    paths = chart_paths(page, spec["select"])
    curves = [(np.stack([to_x(p[:, 0]), to_y(p[:, 1])], axis=1), d) for p, d in paths]
    if name == "characteristic":
        if len(curves) != 3:
            raise RuntimeError(f"{pdf.name} {name}: found {len(curves)} curves, expected 3")
        if pdf.name == "velvia_100.pdf":
            labels = [VELVIA_100_DASHES["" if str(d.get("dashes")).strip() == "[] 0" else str(d.get("dashes")).strip()] for _, d in curves]
            rule = "Legend of the chart: R solid, G dash-dot, B dashed."
        else:
            order = np.argsort([-c[:, 1].max() for c, _ in curves])
            labels = [""] * 3
            for label, index in zip(("blue", "green", "red"), order):
                labels[index] = label
            rule = "Labels B, G, R from top to bottom at the toe of the chart: order by the largest density, highest first."
    elif name == "spectral_sensitivity":
        order = np.argsort([c[np.argmax(c[:, 1]), 0] for c, _ in curves])
        labels = [""] * len(curves)
        for label, index in zip(("yellow_forming_layer", "magenta_forming_layer", "cyan_forming_layer"), order):
            labels[index] = label
        rule = "Order by the wavelength of the curve maximum."
    elif name == "spectral_dye_density":
        neutral = [i for i, (c, _) in enumerate(curves) if len(curves) == 4 and c[:, 1].mean() == max(k[:, 1].mean() for k, _ in curves)]
        dyes = [i for i in range(len(curves)) if i not in neutral]
        order = sorted(dyes, key=lambda i: curves[i][0][np.argmax(curves[i][0][:, 1]), 0])
        labels = [""] * len(curves)
        for label, index in zip(("yellow_dye", "magenta_dye", "cyan_dye"), order):
            labels[index] = label
        for index in neutral:
            labels[index] = "midscale_neutral"
        rule = "Dyes ordered by the wavelength of the curve maximum; a fourth curve with the highest mean is the neutral of the chart."
    else:
        if len(curves) == 1:
            labels, rule = ["all_layers"], "One curve for all layers."
        else:
            letters = {w[4]: ((w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words") if w[4] in ("R", "G", "B")
                       and spec["select"][0] < (w[0] + w[2]) / 2 < spec["select"][2] and spec["select"][1] < (w[1] + w[3]) / 2 < spec["select"][3]}
            if set(letters) != {"R", "G", "B"}:
                raise RuntimeError(f"{pdf.name} {name}: letters found {sorted(letters)}")
            ends = sorted(range(3), key=lambda i: -curves[i][0][np.argmax(curves[i][0][:, 0]), 1])
            by_height = sorted(letters, key=lambda k: letters[k][1])
            labels = [""] * 3
            for index, letter in zip(ends, by_height):
                labels[index] = {"R": "red", "G": "green", "B": "blue"}[letter]
            rule = "Each curve takes the letter R, G, or B in the order of the height of its right end."
    step = 0.01 if name == "characteristic" else 1.0
    out = {}
    for label, (curve, _) in zip(labels, curves):
        points = curve.copy()
        if name == "modulation_transfer":
            points[:, 1] /= 100.0
        grid, values, _ = dk.resample(points, step)
        out[label] = {"x": grid.round(6).tolist(), "y": np.round(values, 5).tolist()}
    return out, {"label_rule": rule, "axis_residual_pt": [round(x_residual, 3), round(y_residual, 3)], "axis_within_limit": max(x_residual, y_residual) <= AXIS_LIMIT_PT, "curves": len(curves)}


def sfl_data(path: Path) -> dict:
    """The literal fields of FilmData of a data file. The code of that project does not run."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FilmData":
            out = {}
            for keyword in node.keywords:
                try:
                    out[keyword.arg] = ast.literal_eval(keyword.value)
                except ValueError:
                    pass
            return out
    raise ValueError(f"no FilmData in {path}")


def resampled(points: dict, step: float = 1.0) -> dict:
    x = np.array(sorted(points), dtype=float)
    y = np.array([points[v] for v in x], dtype=float)
    grid = np.round(np.arange(math.ceil(x[0] / step - 1e-9) * step, x[-1] + step * 1e-6, step), 6)
    return {"x": grid.tolist(), "y": np.interp(grid, x, y).round(5).tolist()}


def sfl_charts(data: dict) -> dict:
    charts = {"characteristic": {c: resampled(p, 0.01) for c, p in zip(CHANNELS, data["sensiometric_curve"])},
              "spectral_sensitivity": {layer: resampled(p) for layer, p in zip(LAYERS, data["log_sensitivity"])},
              "spectral_dye_density": {dye: resampled(p) for dye, p in zip(DYES, data["spectral_density"])}}
    if data.get("d_ref_sd"):
        charts["spectral_dye_density"]["midscale_neutral"] = resampled(data["d_ref_sd"])
    if data.get("mtf"):
        names = CHANNELS if len(data["mtf"]) == 3 else ("all_layers",)
        charts["modulation_transfer"] = {n: resampled(p) for n, p in zip(names, data["mtf"])}
    return charts


def fotufilm_charts(path: Path, iso: float) -> dict:
    """Rule 'fotufilm_exposure_axis', and the spectral values of the profile on its 5 nm grid (380 to 780 nm), resampled to 1 nm. A sensitivity of zero is outside the chart."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("isReversal"):
        raise ValueError(f"{path.name} is not a reversal profile")
    characteristic = {}
    for channel, curve in zip(CHANNELS, data["curves"]):
        x = np.array(curve["sampled"]["logExposure"], dtype=float)[FOTUFILM_EXTRAPOLATED_POINTS:-FOTUFILM_EXTRAPOLATED_POINTS]
        formed = np.array(curve["sampled"]["density"], dtype=float)
        developed = formed.min() + formed.max() - formed[FOTUFILM_EXTRAPOLATED_POINTS:-FOTUFILM_EXTRAPOLATED_POINTS]
        log_h = x + math.log10(10.0 / iso)
        grid = np.round(np.arange(math.ceil(log_h[0] * 100) / 100, log_h[-1], 0.01), 4)
        characteristic[channel] = {"x": grid.tolist(), "y": np.interp(grid, log_h, developed).round(5).tolist()}
    wavelengths = np.arange(380.0, 781.0, 5.0)
    if len(data["spectral"]["layerSensitivity"][0]) != len(wavelengths):
        raise ValueError(f"{path.name}: the spectral samples are not on 380 to 780 nm at 5 nm")
    sensitivity = {}
    for layer, values in zip(LAYERS, data["spectral"]["layerSensitivity"]):
        values = np.array(values, dtype=float)
        inside = np.flatnonzero(values > 0.0)
        span = wavelengths[inside[0]:inside[-1] + 1]
        positive = values[inside[0]:inside[-1] + 1]
        if (positive <= 0.0).any():
            raise ValueError(f"{path.name}: a zero inside the sensitivity of {layer}")
        grid = np.arange(span[0], span[-1] + 0.5, 1.0)
        sensitivity[layer] = {"x": grid.tolist(), "y": np.interp(grid, span, np.log10(positive)).round(5).tolist()}
    grid = np.arange(380.0, 780.5, 1.0)
    dyes = {dye: {"x": grid.tolist(), "y": np.interp(grid, wavelengths, values).round(5).tolist()} for dye, values in zip(DYES, data["spectral"]["imageDyeDensity"])}
    return {"characteristic": characteristic, "spectral_sensitivity": sensitivity, "spectral_dye_density": dyes}


# --- profile ---------------------------------------------------------------------------------

def running_minimum(curves: dict) -> tuple[dict, float]:
    out, rise = {}, 0.0
    for channel, curve in curves.items():
        y = np.array(curve["y"])
        falling = np.minimum.accumulate(y)
        rise = max(rise, float((y - falling).max()))
        out[channel] = {"x": curve["x"], "y": falling.round(5).tolist()}
    return out, rise


def neutral_and_base(dyes: dict, neutral: dict | None, inferred: list[str]) -> dict:
    lo = max(c["x"][0] for c in dyes.values())
    hi = min(c["x"][-1] for c in dyes.values())
    grid = np.arange(lo, hi + 0.5, 1.0)
    if neutral is None:
        neutral = {"x": grid.tolist(), "y": np.round(sum(np.interp(grid, c["x"], c["y"]) for c in dyes.values()), 5).tolist()}
        inferred.append("neutral_from_dyes")
    else:
        neutral = {"x": [x for x in neutral["x"] if lo <= x <= hi], "y": [y for x, y in zip(neutral["x"], neutral["y"]) if lo <= x <= hi]}
    inferred.append("zero_minimum_density")
    return {"midscale_neutral": neutral, "minimum_density": {"x": neutral["x"], "y": [0.0] * len(neutral["x"])}, **dyes}


def build_profile(stem: str, film: dict, charts: dict, provenance: str, license_note: str) -> dict:
    inferred: list[str] = []
    characteristic, rise = running_minimum(charts["characteristic"])
    if rise > 0.0:
        inferred.append(f"running_minimum_curve, largest rise {rise:.4f}")
    dyes = {k: v for k, v in charts["spectral_dye_density"].items() if k in DYES}
    dye_chart = neutral_and_base(dyes, charts["spectral_dye_density"].get("midscale_neutral"), inferred)
    if film["relative_sensitivity"]:
        inferred.append("relative_sensitivity")
    record = lambda curves, x, y, **extra: {"source": film["document"], "x_quantity": x, "y_quantity": y, "provenance": provenance, **extra, "curves": curves}  # noqa: E731
    out = {"characteristic": record(characteristic, "log10_exposure_lux_s", "status_a_density", conditions=film["conditions"], grid_step=0.01),
           "spectral_sensitivity": record(charts["spectral_sensitivity"], "wavelength_nm", "log10_sensitivity" + ("_relative" if film["relative_sensitivity"] else "_cm2_per_erg"), criterion=film["criterion"], grid_step=1.0),
           "spectral_dye_density": record(dye_chart, "wavelength_nm", "spectral_density", grid_step=1.0)}
    if "modulation_transfer" in charts:
        out["modulation_transfer"] = record(charts["modulation_transfer"], "spatial_frequency_cycles_per_mm", "response", grid_step=1.0)
    return {"material": film["name"], "film_type": "reversal", "iso": film["iso"], "source_document": film["document"], "charts": out, "inferred_rules": inferred, "redistribution_note": license_note}


# --- checks ----------------------------------------------------------------------------------

def difference(a: dict, b: dict, peak_normalize: bool = False, remove_offset: bool = False) -> dict:
    lo, hi = max(a["x"][0], b["x"][0]), min(a["x"][-1], b["x"][-1])
    x = np.linspace(lo, hi, 401)
    ya, yb = np.interp(x, a["x"], a["y"]), np.interp(x, b["x"], b["y"])
    if peak_normalize:
        ya, yb = ya / np.max(a["y"]), yb / np.max(b["y"])
    d = ya - yb
    if remove_offset:
        d = d - d.mean()
    return {"rms": round(float(np.sqrt(np.mean(d ** 2))), 4), "largest": round(float(np.abs(d).max()), 4), "domain": [round(float(lo), 2), round(float(hi), 2)]}


def compare(first: dict, second: dict, relative: bool) -> dict:
    out = {}
    for chart, limit in LIMITS.items():
        if chart not in first or chart not in second:
            continue
        rows = {}
        for key in first[chart]:
            if key in second[chart] and key != "minimum_density":
                rows[key] = difference(first[chart][key], second[chart][key], peak_normalize=chart == "spectral_dye_density" and key in DYES, remove_offset=chart == "spectral_sensitivity" and relative)
        if rows:
            largest = max(r["rms"] for r in rows.values())
            out[chart] = {"curves": rows, "largest_rms": largest, "limit": limit, "within_limit": largest <= limit}
    return out


def git_head(path: Path) -> str:
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    sfl_dir, fotufilm_dir = Path(sys.argv[1]), Path(sys.argv[2])
    fotufilm_head = git_head(fotufilm_dir)
    stocks_dir = fotufilm_dir / "Sources" / "FotufilmCore" / "Stocks"
    fotufilm_provenance = f"Fotufilm film profile (CC BY-SA 4.0, attribution: Fotufilm, https://fotufilm.com) at commit {fotufilm_head}, digitized by that project; rule fotufilm_exposure_axis and resampling by this lab; not checked against the manufacturer document"
    checks: dict = {"limits": LIMITS, "axis_limit_pt": AXIS_LIMIT_PT, "fotufilm_commit": fotufilm_head, "films": {}}
    catalog: dict = {"films": {}}
    for stem in ORDER:
        film = FILMS[stem]
        record: dict = {}
        if film["source"] == "lab":
            specs = E100_CHARTS if stem == "kodak_ektachrome_e100" else VELVIA_100_CHARTS
            charts, record["digitization"] = {}, {}
            for name, spec in specs.items():
                charts[name], record["digitization"][name] = digitize_chart(SOURCES / film["pdf"], name, spec)
            provenance, note = LAB_PROVENANCE, "Values digitized by this lab from a manufacturer data sheet. The source document is not distributed (ROADMAP U10); see profiles/README.md."
        elif film["source"] == "sfl":
            charts, provenance = sfl_charts(sfl_data(sfl_dir / "reversal_film" / film["sfl"])), SFL_PROVENANCE
            note = "Values from spectral_film_lut (MIT); see THIRD_PARTY_NOTICES.md and profiles/README.md."
        else:
            path = stocks_dir / film["fotufilm"]
            charts, provenance = fotufilm_charts(path, film["iso"]), fotufilm_provenance
            note = (f"This profile is an adaptation of the Fotufilm profile {film['fotufilm']} (SHA-256 {hashlib.sha256(path.read_bytes()).hexdigest()}), by Fotufilm (https://fotufilm.com), "
                    "licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Changes: rule fotufilm_exposure_axis, the removal of the extrapolated points, resampling, log10 of the sensitivity. "
                    "This file is licensed under CC BY-SA 4.0; see THIRD_PARTY_NOTICES.md.")
        profile = build_profile(stem, film, charts, provenance, note)
        (PROFILE_DIR / f"{stem}.json").write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")
        if film["sfl"] and film["source"] != "sfl":
            record["against_spectral_film_lut"] = compare(charts, sfl_charts(sfl_data(sfl_dir / "reversal_film" / film["sfl"])), film["relative_sensitivity"])
        if film["fotufilm"] and film["source"] != "fotufilm":
            record["against_fotufilm"] = compare(charts, fotufilm_charts(stocks_dir / film["fotufilm"], film["iso"]), True)
        checks["films"][stem] = record
        catalog["films"][stem] = {"name": film["name"], "manufacturer": film["manufacturer"], "iso": film["iso"], "exposure_kelvin": 5500, "source": film["source"], "document": film["document"],
                                  "relative_sensitivity": film["relative_sensitivity"], "mtf_curves": len(charts.get("modulation_transfer", {})), "inferred_rules": profile["inferred_rules"]}
        summary = {k: {c: v["largest_rms"] for c, v in record[k].items()} for k in record if k.startswith("against")}
        print(f"{stem:24s} {film['source']:9s} {profile['inferred_rules']} {summary}", flush=True)
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8", newline="\n")
    CATALOG.write_text(json.dumps(catalog, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
