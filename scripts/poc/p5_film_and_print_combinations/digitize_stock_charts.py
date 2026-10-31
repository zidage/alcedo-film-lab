"""Write the profiles of Portra 160, Portra 800, Ektar 100, Gold 200, and Fujicolor C200, and check the values against a second source.

Input: the data sheets in build/tmp/p5/sources/ (fetch_sources.py); the data files of spectral_film_lut (MIT, README U11) at commit bcbcfc68, read as literals, first argument: the src/spectral_film_lut directory of a local clone.
Output: profiles/kodak_portra_160.json, kodak_portra_800.json, kodak_ektar_100.json, kodak_gold_200.json, fuji_c200.json; results/p5_film_and_print_combinations/source_checks.json.
Step: P5, README section 8, decision U34.

Values per stock:
- Kodak charts that are one vector path per curve: digitized by this lab, with the functions of digitize_kodak_charts.py (P0). No smoothing, no extrapolation.
- Gold 200, sensitivity: the chart is separate fragments that cross, so the values come from spectral_film_lut. The fragments check them. E-7022 has no modulation transfer chart, so this profile has no such chart.
- C200: the charts of AF3-0249E are raster images, so all values come from spectral_film_lut. Sensitivity is relative, with the criterion 1.0 above D-min. The modulation transfer chart has one curve for all layers.

Rule 'running_maximum_curve': a characteristic curve keeps its running maximum, because the model reads D-min from the first value and inverts a rising curve. The largest fall is in the results.
Limits, set before the first run: lab digitization against spectral_film_lut, RMS at most 0.03 density on characteristic and dye density charts, at most 0.05 log10 on sensitivity charts, at most 0.05 response on modulation transfer charts. Two editions of one sheet count as equal if the largest difference is at most 0.005 chart units. Gold 200 sensitivity against the fragments: largest distance at most 2 pt on the page (0.05 log10 or 5 nm).
"""

from __future__ import annotations

import ast
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p0_data_and_reference"))
import digitize_kodak_charts as dk  # noqa: E402

SOURCES = REPO_ROOT / "build" / "tmp" / "p5" / "sources"
RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "source_checks.json"
SFL_PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; linearly resampled by this lab"
LAB_PROVENANCE = "digitized point: PDF vector path, Bezier segments evaluated and linearly resampled; no smoothing, no extrapolation"
LIMITS = {"characteristic": 0.03, "spectral_dye_density": 0.03, "spectral_sensitivity": 0.05, "modulation_transfer": 0.05}
EDITION_LIMIT = 0.005
FRAGMENT_LIMIT_PT = 2.0
LAYERS = {"blue": "yellow_forming_layer", "green": "magenta_forming_layer", "red": "cyan_forming_layer"}


@dataclass(frozen=True)
class Chart:
    """One chart: the page, the frame on the page in PDF points, and the axis values at the frame edges."""

    page: int
    frame: tuple[float, float, float, float]
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    log_axes: bool = False


def characteristic(page: int, frame: tuple, x_range: tuple[float, float] = (-4.0, 1.0)) -> Chart:
    return Chart(page, frame, x_range, (0.0, 4.0))


def sensitivity(page: int, frame: tuple, y_range: tuple[float, float]) -> Chart:
    return Chart(page, frame, (250.0, 750.0), y_range)


def dye_density(page: int, frame: tuple) -> Chart:
    return Chart(page, frame, (400.0, 700.0), (0.0, 2.5))


def modulation(page: int, frame: tuple) -> Chart:
    return Chart(page, frame, (1.0, 600.0), (1.0, 200.0), True)


STOCKS = {
    "kodak_portra_160": dict(material="KODAK PROFESSIONAL PORTRA 160 Film (color negative, C-41)", document="KODAK Publication No. E-4051, Revised 1-25", pdf="e4051_portra_160.pdf", older="e4051_portra_160_2016.pdf", sfl="negative_film/kodak_portra_160.py", log_h_ref=-1.051, effective_exposure_s=1 / 50,
                             charts=dict(characteristic=characteristic(4, (81.4, 102.1, 266.0, 286.6)), spectral_sensitivity=sensitivity(4, (73.8, 348.0, 274.2, 499.6), (-1.0, 3.0)), spectral_dye_density=dye_density(4, (355.1, 101.2, 539.5, 285.5)), modulation_transfer=modulation(4, (349.0, 350.4, 551.4, 503.5)))),
    "kodak_portra_800": dict(material="KODAK PROFESSIONAL PORTRA 800 Film (color negative, C-41), EI 800", document="KODAK Publication No. E-4040, Revised 1-25", pdf="e4040_portra_800.pdf", older="e4040_portra_800_2016.pdf", sfl="negative_film/kodak_portra_800.py", log_h_ref=-1.74, effective_exposure_s=1 / 200,
                             charts=dict(characteristic=characteristic(4, (81.6, 74.5, 266.2, 258.9)), spectral_sensitivity=sensitivity(4, (350.2, 313.7, 550.9, 465.4), (0.0, 4.0)), spectral_dye_density=dye_density(5, (81.1, 101.8, 265.4, 286.1)), modulation_transfer=modulation(5, (71.6, 345.7, 274.1, 498.7)))),
    "kodak_ektar_100": dict(material="KODAK PROFESSIONAL EKTAR 100 Film (color negative, C-41)", document="KODAK Publication No. E-4046, Revised 1/25", pdf="e4046_ektar_100.pdf", older="e4046_ektar_100_2016.pdf", sfl="negative_film/kodak_ektar_100.py", log_h_ref=-0.84, effective_exposure_s=1 / 25,
                            charts=dict(characteristic=characteristic(4, (81.2, 107.9, 265.7, 292.4), (-3.0, 2.0)), spectral_sensitivity=sensitivity(4, (74.2, 356.6, 274.7, 508.0), (0.0, 3.0)), spectral_dye_density=dye_density(4, (357.5, 106.0, 541.8, 290.4)), modulation_transfer=modulation(4, (347.6, 358.2, 550.1, 511.2)))),
    "kodak_gold_200": dict(material="KODAK GOLD 200 Film (color negative, C-41)", document="KODAK Publication No. E-7022, Revised 06-23", pdf="e7022_gold_200.pdf", older=None, sfl="negative_film/kodak_gold_200.py", log_h_ref=-1.14, effective_exposure_s=1 / 50,
                           charts=dict(characteristic=characteristic(4, (81.7, 71.9, 266.2, 256.4), (-3.0, 1.0)), spectral_dye_density=dye_density(4, (357.1, 55.4, 541.4, 239.7)))),
}
GOLD_SENSITIVITY_FRAME = (74.9, 317.9, 275.4, 469.4)
PORTRA_400_CHARTS = dict(characteristic=(81.2, 102.9, 265.6, 287.4), spectral_sensitivity=(76.2, 343.1, 276.7, 494.6), spectral_dye_density=(357.1, 103.7, 541.8, 288.1))


def sfl_data(path: Path) -> dict:
    """The literal fields of FilmData of a data file, and the module level curve table of Portra 800. The code of that project does not run."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tables = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FilmData":
            out = {}
            for keyword in node.keywords:
                value = keyword.value
                if isinstance(value, ast.Subscript) and getattr(value.value, "id", "") in tables:
                    out[keyword.arg] = ast.literal_eval(tables[value.value.id])[ast.literal_eval(value.slice)]
                else:
                    try:
                        out[keyword.arg] = ast.literal_eval(value)
                    except ValueError:
                        pass
            return out
    raise ValueError(f"no FilmData in {path}")


def sfl_curve(points: dict, step: float = 1.0) -> dict:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    grid = np.round(np.arange(math.ceil(x[0] / step) * step, x[-1] + step * 1e-6, step), 6)
    return {"x": grid.tolist(), "y": np.interp(grid, x, y).round(5).tolist()}


def to_chart_units(points: np.ndarray, chart: Chart) -> np.ndarray:
    fx0, fy0, fx1, fy1 = chart.frame
    u, v = (points[:, 0] - fx0) / (fx1 - fx0), (fy1 - points[:, 1]) / (fy1 - fy0)
    if chart.log_axes:
        (x0, x1), (y0, y1) = chart.x_range, chart.y_range
        return np.stack([x0 * (x1 / x0) ** u, y0 * (y1 / y0) ** v], axis=1)
    return np.stack([chart.x_range[0] + u * (chart.x_range[1] - chart.x_range[0]), chart.y_range[0] + v * (chart.y_range[1] - chart.y_range[0])], axis=1)


def curve_paths(page: pymupdf.Page, chart: Chart) -> list[np.ndarray]:
    """The stroked paths of many segments inside the frame, in chart units. A path with gaps stays one curve; the linear interpolation of the resampling bridges each gap."""
    fx0, fy0, fx1, fy1 = chart.frame
    curves = []
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if drawing["type"] != "s" or len(drawing["items"]) < 8 or r.x0 < fx0 - 1 or r.x1 > fx1 + 1 or r.y0 < fy0 - 1 or r.y1 > fy1 + 1:
            continue
        if any(item[0] not in ("l", "c") for item in drawing["items"]):
            continue
        polylines, _ = dk.path_to_polylines(drawing)
        curves.append(to_chart_units(np.concatenate(polylines), chart))
    return curves


def labeled_channels(page: pymupdf.Page, chart: Chart, curves: list[np.ndarray]) -> list[str]:
    """Each curve of a modulation transfer chart takes the letter R, G, or B that is nearest to its right end."""
    letters = {w[4]: to_chart_units(np.array([[(w[0] + w[2]) / 2, (w[1] + w[3]) / 2]]), chart)[0] for w in page.get_text("words") if w[4] in ("R", "G", "B")
               and chart.frame[0] < (w[0] + w[2]) / 2 < chart.frame[2] and chart.frame[1] < (w[1] + w[3]) / 2 < chart.frame[3]}
    if set(letters) != {"R", "G", "B"}:
        raise RuntimeError(f"letters found on the chart: {sorted(letters)}")
    ends = sorted(range(len(curves)), key=lambda i: -curves[i][np.argmax(curves[i][:, 0])][1])
    by_height = sorted(letters, key=lambda k: -letters[k][1])
    names = {"R": "red", "G": "green", "B": "blue"}
    out = [""] * len(curves)
    for index, letter in zip(ends, by_height):
        out[index] = names[letter]
    return out


def digitize(pdf: Path, name: str, chart: Chart) -> dict:
    page = pymupdf.open(pdf)[chart.page - 1]
    curves = curve_paths(page, chart)
    expected = 2 if name == "spectral_dye_density" else 3
    if len(curves) != expected:
        raise RuntimeError(f"{pdf.name} {name}: found {len(curves)} curve paths, expected {expected}")
    if name == "characteristic":
        labels = ["blue", "green", "red"]
        ordered = sorted(curves, key=lambda c: -c[:, 1].mean())
    elif name == "spectral_dye_density":
        labels = ["midscale_neutral", "minimum_density"]
        ordered = sorted(curves, key=lambda c: -c[:, 1].mean())
    elif name == "spectral_sensitivity":
        labels = ["yellow_forming_layer", "magenta_forming_layer", "cyan_forming_layer"]
        ordered = sorted(curves, key=lambda c: c[np.argmax(c[:, 1]), 0])
    else:
        labels, ordered = labeled_channels(page, chart, curves), curves
    step = {"characteristic": 0.01, "spectral_sensitivity": 1.0, "spectral_dye_density": 1.0, "modulation_transfer": 1.0}[name]
    out = {}
    for label, curve in zip(labels, ordered):
        points = curve.copy()
        if name == "modulation_transfer":
            points[:, 1] /= 100.0
        grid, values, _ = dk.resample(points, step)
        out[label] = {"x": grid.tolist(), "y": np.round(values, 5).tolist()}
    return out


def common_wavelengths(curves: dict) -> dict:
    # The same wavelengths on both, as the band split of the P0 model needs.
    lo, hi = max(c["x"][0] for c in curves.values()), min(c["x"][-1] for c in curves.values())
    return {k: {"x": [x for x in c["x"] if lo <= x <= hi], "y": [y for x, y in zip(c["x"], c["y"]) if lo <= x <= hi]} for k, c in curves.items()}


def running_maximum(curves: dict) -> tuple[dict, dict]:
    falls, out = {}, {}
    for channel, curve in curves.items():
        y = np.array(curve["y"])
        rising = np.maximum.accumulate(y)
        falls[channel] = round(float((rising - y).max()), 4)
        out[channel] = {"x": curve["x"], "y": rising.round(5).tolist()}
    return out, falls


def difference(a: dict, b: dict) -> dict:
    lo, hi = max(a["x"][0], b["x"][0]), min(a["x"][-1], b["x"][-1])
    x = np.linspace(lo, hi, 401)
    d = np.interp(x, a["x"], a["y"]) - np.interp(x, b["x"], b["y"])
    return {"rms": round(float(np.sqrt(np.mean(d ** 2))), 4), "largest": round(float(np.abs(d).max()), 4), "domain": [round(float(lo), 2), round(float(hi), 2)]}


def sfl_charts(data: dict) -> dict:
    return {"characteristic": {c: sfl_curve(p, 0.01) for c, p in zip(("red", "green", "blue"), data["sensiometric_curve"])},
            "spectral_sensitivity": {LAYERS[c]: sfl_curve(p) for c, p in zip(("red", "green", "blue"), data["log_sensitivity"])},
            "spectral_dye_density": {"midscale_neutral": sfl_curve(data["d_ref_sd"]), "minimum_density": sfl_curve(data["d_min_sd"])},
            "modulation_transfer": {c: sfl_curve(p) for c, p in zip(("red", "green", "blue"), data["mtf"])}}


def fragment_distance_pt(page: pymupdf.Page, frame: tuple, y_range: tuple, curve: dict) -> float:
    """Largest distance on the page from the points of a curve to the vector fragments inside the frame. The curve points outside the fragments show as a large distance."""
    fx0, fy0, fx1, fy1 = frame
    nodes = []
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if drawing["type"] == "fs" and r.x0 >= fx0 - 1 and r.x1 <= fx1 + 1 and r.y0 >= fy0 - 1 and r.y1 <= fy1 + 1:
            for polyline in dk.path_to_polylines(drawing)[0]:
                # Points on each line segment at most 0.25 pt apart, because a distance to the end points alone would count the length of a segment.
                for start, stop in zip(polyline[:-1], polyline[1:]):
                    count = int(np.ceil(np.hypot(*(stop - start)) / 0.25)) + 1
                    nodes.append(start + np.linspace(0.0, 1.0, count)[:, None] * (stop - start))
    nodes = np.concatenate(nodes)
    px = fx0 + (np.array(curve["x"]) - 250.0) / 500.0 * (fx1 - fx0)
    py = fy1 - (np.array(curve["y"]) - y_range[0]) / (y_range[1] - y_range[0]) * (fy1 - fy0)
    return float(np.sqrt(((px[:, None] - nodes[:, 0][None]) ** 2 + (py[:, None] - nodes[:, 1][None]) ** 2).min(axis=1)).max())


def chart_record(curves: dict, provenance: str, source: str, x_quantity: str, y_quantity: str, step: float, **conditions) -> dict:
    return {"source": source, "conditions": conditions, "x_quantity": x_quantity, "y_quantity": y_quantity, "grid_step": step, "provenance": provenance, "curves": curves}


def write_profile(name: str, material: str, document: str, charts: dict, note: str) -> None:
    profile = {"material": material, "source_document": document, "charts": charts, "redistribution_note": note}
    (REPO_ROOT / "profiles" / f"{name}.json").write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")


def other_edition_chart(pdf: Path, chart: Chart) -> Chart:
    """The same chart in another edition: the stroked frame of the page nearest to the frame of this chart, because the page layout moves by some points."""
    page = pymupdf.open(pdf)[chart.page - 1]
    width, height = chart.frame[2] - chart.frame[0], chart.frame[3] - chart.frame[1]
    best, best_distance = None, 30.0
    for drawing in page.get_drawings():
        r = drawing["rect"]
        if "s" not in drawing["type"] or abs(r.width - width) > 2.0 or abs(r.height - height) > 2.0:
            continue
        distance = max(abs(r.x0 - chart.frame[0]), abs(r.y0 - chart.frame[1]))
        if distance < best_distance:
            best, best_distance = (r.x0, r.y0, r.x1, r.y1), distance
    if best is None:
        raise RuntimeError(f"{pdf.name}: no frame near {chart.frame}")
    return Chart(chart.page, best, chart.x_range, chart.y_range, chart.log_axes)


def main() -> int:
    sfl_root = Path(sys.argv[1])
    checks: dict = {"limits_rms": LIMITS, "edition_limit": EDITION_LIMIT, "fragment_limit_pt": FRAGMENT_LIMIT_PT}
    note = "Values digitized by this lab from a manufacturer data sheet, and values of spectral_film_lut where the chart states it. The source document is not distributed (README U10); see profiles/README.md."
    quantities = {"characteristic": ("log10_exposure_lux_s", "status_m_density", 0.01), "spectral_sensitivity": ("wavelength_nm", "log10_sensitivity_cm2_per_erg", 1.0), "spectral_dye_density": ("wavelength_nm", "diffuse_spectral_density", 1.0), "modulation_transfer": ("spatial_frequency_cycles_per_mm", "response", 1.0)}
    for name, stock in STOCKS.items():
        pdf = SOURCES / stock["pdf"]
        sfl = sfl_charts(sfl_data(sfl_root / stock["sfl"]))
        check: dict = {"against_spectral_film_lut": {}, "against_older_edition": {}}
        charts = {}
        for chart_name, chart in stock["charts"].items():
            curves = digitize(pdf, chart_name, chart)
            if stock["older"]:
                older_pdf = SOURCES / stock["older"]
                older = digitize(older_pdf, chart_name, other_edition_chart(older_pdf, chart))
                check["against_older_edition"][chart_name] = {k: difference(curves[k], older[k]) for k in curves}
            if chart_name == "characteristic":
                curves, check["largest_fall_removed"] = running_maximum(curves)
            if chart_name == "spectral_dye_density":
                curves = common_wavelengths(curves)
            x_q, y_q, step = quantities[chart_name]
            charts[chart_name] = chart_record(curves, LAB_PROVENANCE, f"{stock['document']}, page {chart.page}", x_q, y_q, step, exposure="Daylight", densitometry="Status M", process="C-41", log_h_ref=stock["log_h_ref"], effective_exposure_s=stock["effective_exposure_s"], criterion="density 0.2 above D-min")
            check["against_spectral_film_lut"][chart_name] = {k: difference(curves[k], sfl[chart_name][k]) for k in curves}
        if name == "kodak_gold_200":
            page = pymupdf.open(pdf)[3]
            layers = sfl["spectral_sensitivity"]
            charts["spectral_sensitivity"] = chart_record(layers, SFL_PROVENANCE + "; checked against the fragments of the vector chart", "spectral_film_lut, from E-7022", "wavelength_nm", "log10_sensitivity_cm2_per_erg", 1.0, exposure="Daylight", densitometry="Status M", effective_exposure_s=1 / 50, criterion="density 0.2 above D-min")
            check["sensitivity_against_fragments_pt"] = {k: round(fragment_distance_pt(page, GOLD_SENSITIVITY_FRAME, (0.0, 4.0), c), 2) for k, c in layers.items()}
            portra_160 = sfl_charts(sfl_data(sfl_root / "negative_film/kodak_portra_160.py"))["modulation_transfer"]
            check["modulation_transfer_of_spectral_film_lut_against_its_portra_160"] = {k: difference(sfl["modulation_transfer"][k], portra_160[k]) for k in portra_160}
        write_profile(name, stock["material"], stock["document"], charts, note)
        checks[name] = check

    # C200: all values from spectral_film_lut.
    data = sfl_data(sfl_root / "negative_film/fuji_c200.py")
    sfl = sfl_charts({**data, "mtf": data["mtf"] * 3})
    curves, falls = running_maximum(sfl["characteristic"])
    source = "spectral_film_lut, from Fujifilm AF3-0249E; not digitized by this lab"
    charts = {"characteristic": chart_record(curves, SFL_PROVENANCE, source, "log10_exposure_lux_s", "status_m_density", 0.01, exposure="Daylight, 1/125 s", process="CN-16", densitometry="Status M"),
              "spectral_sensitivity": chart_record(sfl["spectral_sensitivity"], SFL_PROVENANCE, source, "wavelength_nm", "relative_log10_sensitivity", 1.0, process="CN-16", densitometry="Status M", criterion="density 1.0 above D-min", absolute_level="not published; the chart has a scale bar of 1.0 and no zero"),
              "spectral_dye_density": chart_record(common_wavelengths(sfl["spectral_dye_density"]), SFL_PROVENANCE, source, "wavelength_nm", "diffuse_spectral_density", 1.0),
              "modulation_transfer": chart_record(sfl["modulation_transfer"], SFL_PROVENANCE, source, "spatial_frequency_cycles_per_mm", "response", 1.0, one_curve_for_all_layers="The chart has one curve. The three entries are copies, and the spread per layer is not specified.")}
    write_profile("fuji_c200", "FUJICOLOR C200 (color negative, CN-16 and compatible)", "FUJIFILM Product Information Bulletin AF3-0249E (17.05-BX), through spectral_film_lut", charts, "Values from spectral_film_lut (MIT); see THIRD_PARTY_NOTICES.md and profiles/README.md.")
    checks["fuji_c200"] = {"largest_fall_removed": falls}

    # Portra 400: does the current edition change the curves of the accepted profile? The profile does not change. The frames of the two editions are the same on the page.
    portra = json.loads((REPO_ROOT / "profiles" / "kodak_portra_400.json").read_text(encoding="utf-8"))["charts"]
    pdf = SOURCES / "e4050_portra_400_2025.pdf"
    axes = {"characteristic": characteristic(4, PORTRA_400_CHARTS["characteristic"]), "spectral_sensitivity": sensitivity(4, PORTRA_400_CHARTS["spectral_sensitivity"], (0.0, 4.0)), "spectral_dye_density": dye_density(4, PORTRA_400_CHARTS["spectral_dye_density"])}
    checks["kodak_portra_400_edition_1_25_against_profile_2_16"] = {name: {k: difference(c, portra[name]["curves"][k]) for k, c in digitize(pdf, name, chart).items()} for name, chart in axes.items()}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
