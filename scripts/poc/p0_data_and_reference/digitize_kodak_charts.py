"""Read the curves of the Portra 400 and Endura Premier data sheets from the PDF vector paths.

Input: build/tmp/p0/sources/e4050_portra_400.pdf and e4070_endura_premier.pdf (verified by
fetch_sources.py).
Output:
- profiles/kodak_portra_400.json and profiles/kodak_endura_premier.json: the curves resampled on
  a uniform grid (1 nm, or 0.01 log10 lux-seconds), with the chart conditions and provenance.
- results/p0_data_and_reference/digitization.json: axis calibration residuals, path structure,
  monotonicity, and the label assignment rule of each curve.
- build/tmp/p0/digitized_paths.json: the raw path nodes (line ends and Bezier control points) in
  chart units.

Step: P0 (data and reference). The charts of both data sheets are vector drawings, not raster
images. Each curve is one stroked PDF path made of line and cubic Bezier segments. The script
maps the path from PDF points to chart units with the axis frame, and checks the map with the
tick marks and grid lines: each tick must map to its labeled value within TICK_TOLERANCE chart
units. The Bezier segments are evaluated at BEZIER_SAMPLES points each; the uniform grid is a
linear interpolation of that dense polyline. No smoothing and no extrapolation is applied.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pymupdf

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_DIR = REPO_ROOT / "build" / "tmp" / "p0" / "sources"
PROFILE_DIR = REPO_ROOT / "profiles"
RESULT_DIR = REPO_ROOT / "results" / "p0_data_and_reference"
RAW_PATH_FILE = REPO_ROOT / "build" / "tmp" / "p0" / "digitized_paths.json"

BEZIER_SAMPLES = 64
# A tick mark or grid line must map to its labeled value within this many chart units
# (0.005 density, log10 sensitivity, or log10 lux-seconds; 0.5 nm on a wavelength axis).
TICK_TOLERANCE = {"wavelength_nm": 0.5, "default": 0.005}
EDGE_SNAP_PT = 0.6


@dataclass
class ChartSpec:
    chart_id: str
    pdf: str
    page: int
    title: str
    approx_frame: tuple[float, float, float, float]  # x0, y0 (top), x1, y1 (bottom) in PDF points
    x_range: tuple[float, float]  # value at the left and the right frame edge
    y_range: tuple[float, float]  # value at the bottom and the top frame edge
    x_quantity: str
    y_quantity: str
    x_tick_step: float
    y_tick_step: float
    expected_curves: int
    conditions: dict = field(default_factory=dict)


CHARTS = [
    ChartSpec(
        "portra400_characteristic", "e4050_portra_400.pdf", 4, "Characteristic Curves",
        (81.2, 102.9, 265.6, 287.4), (-4.0, 1.0), (0.0, 4.0),
        "log10_exposure_lux_s", "status_m_density", 1.0, 1.0, 3,
        {"exposure": "Daylight", "densitometry": "Status M", "log_h_ref": -1.44,
         "process": "C-41 (stated on the same page for the MTF chart only)"},
    ),
    ChartSpec(
        "portra400_spectral_sensitivity", "e4050_portra_400.pdf", 4, "Spectral-Sensitivity Curves",
        (76.2, 343.1, 276.7, 494.6), (250.0, 750.0), (0.0, 4.0),
        "wavelength_nm", "log10_sensitivity_cm2_per_erg", 50.0, 1.0, 3,
        {"effective_exposure_s": 1 / 50, "exposure": "Daylight", "densitometry": "Status M",
         "criterion": "density 0.2 above D-min",
         "sensitivity_definition": "reciprocal of the exposure (erg/cm^2) that gives the criterion density"},
    ),
    ChartSpec(
        "portra400_spectral_dye_density", "e4050_portra_400.pdf", 4, "Spectral-Dye-Density Curves",
        (357.1, 103.7, 541.8, 288.1), (400.0, 700.0), (0.0, 2.5),
        "wavelength_nm", "diffuse_spectral_density", 50.0, 0.5, 2,
        {"note": "Typical densities for a midscale neutral subject and D-min.",
         "isolated_dye_curves": "not published"},
    ),
    ChartSpec(
        "endura_premier_characteristic", "e4070_endura_premier.pdf", 4, "Characteristic Curves",
        (364.7, 72.5, 549.2, 257.2), (-3.0, 0.0), (0.0, 3.0),
        "log10_exposure_lux_s", "status_a_density", 1.0, 1.0, 3,
        {"exposure_time_s": 0.5, "process": "RA-4 95 F (35 C), 45 s", "densitometry": "Status A",
         "exposure_light": "not stated"},
    ),
    ChartSpec(
        "endura_premier_spectral_sensitivity", "e4070_endura_premier.pdf", 4, "Spectral-Sensitivity Curves",
        (350.6, 315.7, 551.1, 467.3), (250.0, 750.0), (-2.0, 2.0),
        "wavelength_nm", "log10_sensitivity_cm2_per_erg", 50.0, 1.0, 3,
        {"effective_exposure_s": 0.5, "process": "RA-4",
         "criterion": "not stated on the chart",
         "sensitivity_definition": "reciprocal of the exposure (erg/cm^2) that gives the specified density"},
    ),
    ChartSpec(
        "endura_premier_spectral_dye_density", "e4070_endura_premier.pdf", 5, "Spectral-Dye-Density Curves",
        (88.8, 50.6, 273.3, 234.9), (400.0, 700.0), (0.0, 2.5),
        "wavelength_nm", "diffuse_spectral_density_peak_normalized", 50.0, 0.5, 3,
        {"process": "RA-4", "normalization": "each dye curve has its maximum at 1.0 (read from the data)"},
    ),
]


def straight_segments(drawings: list[dict]) -> list[tuple[float, float, float, float]]:
    """Return the straight segments (x0, y0, x1, y1) of all stroked lines and rectangles."""
    segments = []
    for drawing in drawings:
        if "s" not in drawing["type"]:
            continue
        for item in drawing["items"]:
            if item[0] == "l":
                segments.append((item[1].x, item[1].y, item[2].x, item[2].y))
            elif item[0] == "re":
                r = item[1]
                segments += [(r.x0, r.y0, r.x1, r.y0), (r.x1, r.y0, r.x1, r.y1),
                             (r.x0, r.y1, r.x1, r.y1), (r.x0, r.y0, r.x0, r.y1)]
    return segments


def snap_frame(spec: ChartSpec, segments: list) -> tuple[float, float, float, float]:
    """Find the exact frame edges near the approximate frame. Stop with an error if one is missing."""
    x0, y0, x1, y1 = spec.approx_frame
    width, height = x1 - x0, y1 - y0
    vertical = [s for s in segments if abs(s[0] - s[2]) < 1e-3 and abs(s[3] - s[1]) > 0.5 * height]
    horizontal = [s for s in segments if abs(s[1] - s[3]) < 1e-3 and abs(s[2] - s[0]) > 0.5 * width]

    def nearest(values: list[float], target: float, name: str) -> float:
        close = [v for v in values if abs(v - target) <= EDGE_SNAP_PT]
        if not close:
            raise RuntimeError(f"{spec.chart_id}: no frame edge '{name}' within {EDGE_SNAP_PT} pt of {target}")
        return float(np.median(close))

    return (
        nearest([s[0] for s in vertical], x0, "left"),
        nearest([s[1] for s in horizontal], y0, "top"),
        nearest([s[0] for s in vertical], x1, "right"),
        nearest([s[1] for s in horizontal], y1, "bottom"),
    )


def tick_positions(spec: ChartSpec, frame: tuple, segments: list) -> tuple[list[float], list[float]]:
    """Tick marks and grid lines: short or full-length segments perpendicular to an axis, inside the frame."""
    fx0, fy0, fx1, fy1 = frame
    xs, ys = set(), set()
    for sx0, sy0, sx1, sy1 in segments:
        if abs(sx0 - sx1) < 1e-3 and fx0 + 1 < sx0 < fx1 - 1:
            touches = min(abs(sy0 - fy1), abs(sy1 - fy1), abs(sy0 - fy0), abs(sy1 - fy0)) < 1.0
            if touches:
                xs.add(round(sx0, 3))
        if abs(sy0 - sy1) < 1e-3 and fy0 + 1 < sy0 < fy1 - 1:
            touches = min(abs(sx0 - fx0), abs(sx1 - fx0), abs(sx0 - fx1), abs(sx1 - fx1)) < 1.0
            if touches:
                ys.add(round(sy0, 3))
    return sorted(xs), sorted(ys)


def path_to_polylines(drawing: dict) -> tuple[list[np.ndarray], list[list[list[float]]]]:
    """Evaluate a stroked path. Return the dense polylines (one per subpath) and the raw nodes."""
    polylines: list[list[np.ndarray]] = []
    nodes: list[list[list[float]]] = []
    last_end = None
    t = np.linspace(0.0, 1.0, BEZIER_SAMPLES + 1)
    for item in drawing["items"]:
        kind = item[0]
        if kind == "l":
            p0, p3 = np.array(item[1]), np.array(item[2])
            pts = np.stack([p0, p3])
            raw = [list(item[1]), list(item[2])]
        elif kind == "c":
            p0, p1, p2, p3 = (np.array(p) for p in item[1:5])
            b = ((1 - t) ** 3)[:, None] * p0 + (3 * (1 - t) ** 2 * t)[:, None] * p1 \
                + (3 * (1 - t) * t ** 2)[:, None] * p2 + (t ** 3)[:, None] * p3
            pts = b
            raw = [list(p) for p in item[1:5]]
        else:
            raise RuntimeError(f"unexpected path item {kind!r}")
        if last_end is None or np.hypot(*(pts[0] - last_end)) > 1e-3:
            polylines.append([pts])
            nodes.append(raw)
        else:
            polylines[-1].append(pts[1:])
            nodes[-1] += raw[1:]
        last_end = pts[-1]
    return [np.concatenate(p) for p in polylines], nodes


def map_points(points: np.ndarray, frame: tuple, spec: ChartSpec) -> np.ndarray:
    fx0, fy0, fx1, fy1 = frame
    x = spec.x_range[0] + (points[:, 0] - fx0) / (fx1 - fx0) * (spec.x_range[1] - spec.x_range[0])
    y = spec.y_range[0] + (fy1 - points[:, 1]) / (fy1 - fy0) * (spec.y_range[1] - spec.y_range[0])
    return np.stack([x, y], axis=1)


def assign_labels(spec: ChartSpec, curves: list[np.ndarray]) -> tuple[list[str], str]:
    """Assign the chart labels to the curves with a rule that depends only on the curve data."""
    if spec.chart_id == "portra400_characteristic":
        order = np.argsort([-c[:, 1].mean() for c in curves])
        names = ["blue", "green", "red"]
        rule = "Labels B, G, R from top to bottom on the chart: order by mean density, highest first."
    elif spec.chart_id == "endura_premier_characteristic":
        order = np.argsort([-c[:, 1].max() for c in curves])
        names = ["red", "green", "blue"]
        rule = "Labels R, G, B from top to bottom at the shoulder: order by maximum density, highest first."
    elif spec.chart_id == "portra400_spectral_dye_density":
        order = np.argsort([-c[:, 1].mean() for c in curves])
        names = ["midscale_neutral", "minimum_density"]
        rule = "Midscale neutral is the upper curve: order by mean density, highest first."
    else:
        order = np.argsort([c[np.argmax(c[:, 1]), 0] for c in curves])
        if "sensitivity" in spec.chart_id:
            names = ["yellow_forming_layer", "magenta_forming_layer", "cyan_forming_layer"]
        else:
            names = ["yellow_dye", "magenta_dye", "cyan_dye"]
        rule = "Order by the wavelength of the curve maximum: yellow (shortest), magenta, cyan (longest)."
    labels = [""] * len(curves)
    for name, index in zip(names, order):
        labels[index] = name
    return labels, rule


def resample(curve: np.ndarray, step: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Linear interpolation of the dense polyline on a uniform grid inside the curve domain."""
    x, y = curve[:, 0], curve[:, 1]
    dx = np.diff(x)
    backward = dx < -1e-9
    info = {
        "x_min": float(x.min()),
        "x_max": float(x.max()),
        "backward_steps": int(backward.sum()),
        "largest_backward_step": float(-dx[backward].min()) if backward.any() else 0.0,
    }
    # A drawn curve can step back by a fraction of a point where it is almost vertical. Keep the
    # first point of each x value after sorting; record the size of the backward steps above.
    order = np.argsort(x, kind="stable")
    xs, ys = x[order], y[order]
    keep = np.concatenate([[True], np.diff(xs) > 1e-9])
    xs, ys = xs[keep], ys[keep]
    start = np.ceil(xs[0] / step - 1e-9) * step
    stop = np.floor(xs[-1] / step + 1e-9) * step
    grid = np.round(np.arange(start, stop + step / 2, step), 6)
    values = np.interp(grid, xs, ys)
    # Error of the uniform grid against the dense path: interpolate the grid back at the path points.
    inside = (xs >= grid[0]) & (xs <= grid[-1])
    info["grid_interpolation_max_error"] = float(np.abs(np.interp(xs[inside], grid, values) - ys[inside]).max())
    return grid, values, info


def digitize_chart(spec: ChartSpec) -> tuple[dict, dict, dict]:
    page = pymupdf.open(SOURCE_DIR / spec.pdf)[spec.page - 1]
    drawings = page.get_drawings()
    segments = straight_segments(drawings)
    frame = snap_frame(spec, segments)
    fx0, fy0, fx1, fy1 = frame

    tick_xs, tick_ys = tick_positions(spec, frame, segments)
    tick_x_values = map_points(np.array([[x, fy1] for x in tick_xs]).reshape(-1, 2), frame, spec)[:, 0]
    tick_y_values = map_points(np.array([[fx0, y] for y in tick_ys]).reshape(-1, 2), frame, spec)[:, 1]
    x_residual = np.abs(tick_x_values - np.round(tick_x_values / spec.x_tick_step) * spec.x_tick_step)
    y_residual = np.abs(tick_y_values - np.round(tick_y_values / spec.y_tick_step) * spec.y_tick_step)
    x_tol = TICK_TOLERANCE.get(spec.x_quantity, TICK_TOLERANCE["default"])
    y_tol = TICK_TOLERANCE["default"]
    if len(tick_xs) == 0 or len(tick_ys) == 0:
        raise RuntimeError(f"{spec.chart_id}: no tick marks found for the calibration check")
    if x_residual.max() > x_tol or y_residual.max() > y_tol:
        raise RuntimeError(f"{spec.chart_id}: tick residual above tolerance: x {x_residual.max()}, y {y_residual.max()}")

    curve_drawings = []
    for drawing in drawings:
        r = drawing["rect"]
        if drawing["type"] != "s" or len(drawing["items"]) < 8:
            continue
        if r.x0 < fx0 - 1 or r.x1 > fx1 + 1 or r.y0 < fy0 - 1 or r.y1 > fy1 + 1:
            continue
        if any(item[0] not in ("l", "c") for item in drawing["items"]):
            continue
        curve_drawings.append(drawing)
    if len(curve_drawings) != spec.expected_curves:
        raise RuntimeError(f"{spec.chart_id}: found {len(curve_drawings)} curve paths, expected {spec.expected_curves}")

    dense_curves, raw_nodes, path_info = [], [], []
    for drawing in curve_drawings:
        polylines, nodes = path_to_polylines(drawing)
        if len(polylines) != 1:
            raise RuntimeError(f"{spec.chart_id}: a curve path has {len(polylines)} subpaths; expected 1")
        dense_curves.append(map_points(polylines[0], frame, spec))
        raw_nodes.append(map_points(np.array(nodes[0]), frame, spec).round(6).tolist())
        path_info.append({"segments": len(drawing["items"]),
                          "line_segments": sum(1 for i in drawing["items"] if i[0] == "l"),
                          "bezier_segments": sum(1 for i in drawing["items"] if i[0] == "c"),
                          "stroke_width_pt": round(float(drawing.get("width") or 0.0), 3)})

    labels, rule = assign_labels(spec, dense_curves)
    step = 1.0 if spec.x_quantity == "wavelength_nm" else 0.01
    curves_out, check_curves, raw_out = {}, {}, {}
    for label, curve, info, nodes in zip(labels, dense_curves, path_info, raw_nodes):
        grid, values, mono = resample(curve, step)
        curves_out[label] = {"x": grid.tolist(), "y": np.round(values, 5).tolist()}
        check_curves[label] = {**info, **mono, "grid_points": len(grid),
                               "y_min": float(values.min()), "y_max": float(values.max()),
                               "x_at_y_max": float(grid[np.argmax(values)])}
        raw_out[label] = nodes

    pt_per_unit_x = (fx1 - fx0) / (spec.x_range[1] - spec.x_range[0])
    pt_per_unit_y = (fy1 - fy0) / (spec.y_range[1] - spec.y_range[0])
    check = {
        "pdf": spec.pdf,
        "page": spec.page,
        "title": spec.title,
        "frame_pt": [round(v, 4) for v in frame],
        "x_range": spec.x_range,
        "y_range": spec.y_range,
        "points_per_unit": {"x": pt_per_unit_x, "y": pt_per_unit_y},
        "tick_check": {
            "x_ticks": len(tick_xs),
            "y_ticks": len(tick_ys),
            "x_max_residual": float(x_residual.max()),
            "y_max_residual": float(y_residual.max()),
            "x_tolerance": x_tol,
            "y_tolerance": y_tol,
            "rule": "each tick or grid line position, mapped with the frame, must equal a multiple of the tick step within the tolerance",
        },
        "label_rule": rule,
        "curves": check_curves,
    }
    chart_out = {
        "source": {"pdf": spec.pdf, "page": spec.page, "chart": spec.title},
        "conditions": spec.conditions,
        "x_quantity": spec.x_quantity,
        "y_quantity": spec.y_quantity,
        "grid_step": step,
        "provenance": "digitized point: PDF vector path, Bezier segments evaluated and linearly resampled; no smoothing, no extrapolation",
        "curves": curves_out,
    }
    return chart_out, check, raw_out


def main() -> int:
    profiles = {
        "kodak_portra_400": {
            "material": "KODAK PROFESSIONAL PORTRA 400 Film (color negative, C-41)",
            "source_document": "KODAK Publication No. E-4050, Revised 2-16",
            "charts": {},
        },
        "kodak_endura_premier": {
            "material": "KODAK PROFESSIONAL ENDURA Premier Paper (color negative paper, RA-4)",
            "source_document": "KODAK Publication No. E-4070, Revised 12-17",
            "charts": {},
        },
    }
    checks, raw = {}, {}
    for spec in CHARTS:
        chart_out, check, raw_out = digitize_chart(spec)
        target = "kodak_portra_400" if spec.chart_id.startswith("portra") else "kodak_endura_premier"
        short = spec.chart_id.split("_", 1)[1].replace("premier_", "")
        profiles[target]["charts"][short] = chart_out
        checks[spec.chart_id] = check
        raw[spec.chart_id] = raw_out
        tc = check["tick_check"]
        print(f"{spec.chart_id}: {len(chart_out['curves'])} curves, tick residual x {tc['x_max_residual']:.2e} y {tc['y_max_residual']:.2e}")

    note = ("Values digitized by this lab from a manufacturer data sheet. The source document is "
            "not distributed (README U10); see profiles/README.md.")
    for name, profile in profiles.items():
        profile["redistribution_note"] = note
        path = PROFILE_DIR / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    digitization = {
        "method": __doc__.strip().split("\n\n")[-1].replace("\n", " "),
        "bezier_samples_per_segment": BEZIER_SAMPLES,
        "charts": checks,
    }
    (RESULT_DIR / "digitization.json").write_text(json.dumps(digitization, indent=1) + "\n",
                                                  encoding="utf-8", newline="\n")
    RAW_PATH_FILE.write_text(json.dumps(raw) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
