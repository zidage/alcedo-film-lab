"""Digitize the diffuse RMS granularity charts of Kodak motion picture negatives (step P15).

Input: the vector charts named in chart_config.json, from build/tmp/p15_grain/sources/ (fetch_sources.py).
Output: results/p15_film_grain/granularity_curves.json (per stock and layer: gross Status M density and
sigma_D at the same log exposure), and one overlay PNG per chart in build/tmp/p15_grain/overlays/ (local).

Method. A Kodak granularity chart plots the characteristic curves (density, left axis, linear) and the granularity
curves (sigma_D, right axis, log10) over one log exposure axis. The two curves of a layer are read at the same
horizontal page position, so the horizontal axis needs no calibration: density(x) and sigma(x) give sigma over
density. The vertical axes are calibrated from the tick labels (least squares, linear and log10); a label with a
residual above 1.0 pt is dropped, and the fit must keep at least three labels with a largest residual of 0.6 pt.

Curves are stroke paths (PDF vector). A dashed curve can be one path, several subpaths, or pieces spread over
several paths; the pieces are joined by end-to-start continuity (gap at most 9 pt, direction change counted). The
characteristic curves get their layer by vertical order (top: blue, middle: green, bottom: red). A granularity curve
gets its layer from the config or from the nearest chart label B, G, or R.
"""
from __future__ import annotations

import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pymupdf

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "build" / "tmp" / "p15_grain" / "sources"
OVERLAYS = ROOT / "build" / "tmp" / "p15_grain" / "overlays"
CONFIG = Path(__file__).with_name("chart_config.json")
OUTPUT = ROOT / "results" / "p15_film_grain" / "granularity_curves.json"

LABEL_RESIDUAL_DROP_PT = 1.2
LABEL_RESIDUAL_LIMIT_PT = 1.0
LABEL_RESIDUAL_RMS_LIMIT_PT = 0.5
JOIN_GAP_PT = 9.0
SAMPLES = 241
LAYER_LABELS = {"B": "B", "G": "G", "R": "R", "Blue": "B", "Green": "G", "Red": "R",
                "Blue Grain": "B", "Green Grain": "G", "Red Grain": "R"}


def path_pieces(drawing: dict) -> list[np.ndarray]:
    """Split one drawing into connected polylines (page points)."""
    pieces: list[list[tuple[float, float]]] = []
    prev = None
    for item in drawing["items"]:
        if item[0] == "l":
            a, b = item[1], item[2]
            seg = [(a.x, a.y), (b.x, b.y)]
        elif item[0] == "c":
            p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
            t = np.linspace(0.0, 1.0, 9)
            xs = (1 - t) ** 3 * p0.x + 3 * (1 - t) ** 2 * t * p1.x + 3 * (1 - t) * t ** 2 * p2.x + t ** 3 * p3.x
            ys = (1 - t) ** 3 * p0.y + 3 * (1 - t) ** 2 * t * p1.y + 3 * (1 - t) * t ** 2 * p2.y + t ** 3 * p3.y
            seg = list(zip(xs.tolist(), ys.tolist()))
        else:
            continue
        if prev is not None and math.hypot(seg[0][0] - prev[0], seg[0][1] - prev[1]) < 0.05:
            pieces[-1].extend(seg[1:])
        else:
            pieces.append(seg)
        prev = seg[-1]
    out = []
    for piece in pieces:
        arr = np.asarray(piece, dtype=np.float64)
        if arr[0, 0] > arr[-1, 0]:
            arr = arr[::-1]
        out.append(arr)
    return out


def join_pieces(pieces: list[np.ndarray]) -> list[np.ndarray]:
    """Join pieces end to start by continuity. Returns the chains, longest horizontal extent first."""
    candidates = []
    for i, a in enumerate(pieces):
        da = a[-1] - a[max(len(a) - 3, 0)]
        for j, b in enumerate(pieces):
            if i == j or b[0, 0] < a[-1, 0] - 0.5:
                continue
            gap = float(np.hypot(*(b[0] - a[-1])))
            if gap > JOIN_GAP_PT:
                continue
            db = b[min(2, len(b) - 1)] - b[0]
            angle = abs(math.atan2(da[1], da[0] + 1e-9) - math.atan2(db[1], db[0] + 1e-9))
            candidates.append((gap + 6.0 * angle, i, j))
    candidates.sort()
    nxt: dict[int, int] = {}
    has_prev: set[int] = set()
    for _, i, j in candidates:
        if i in nxt or j in has_prev:
            continue
        k = j
        cycle = False
        while k in nxt:
            k = nxt[k]
            if k == i:
                cycle = True
                break
        if cycle:
            continue
        nxt[i] = j
        has_prev.add(j)
    chains = []
    for start in range(len(pieces)):
        if start in has_prev:
            continue
        seq = [start]
        while seq[-1] in nxt:
            seq.append(nxt[seq[-1]])
        chains.append(np.concatenate([pieces[k] for k in seq]))
    chains.sort(key=lambda c: -(c[:, 0].max() - c[:, 0].min()))
    return chains


def numeric_spans(page: pymupdf.Page, clip: pymupdf.Rect) -> list[tuple[float, float, float, float, str]]:
    spans = []
    for block in page.get_text("dict", clip=clip)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip().replace("–", "-").replace("−", "-")
                x0, y0, x1, y1 = span["bbox"]
                spans.append((x0, y0, x1, y1, text))
    return spans


def fit_axis(labels: list[tuple[float, float]], log_axis: bool, rms_limit: float = 0.5) -> tuple[float, float, dict]:
    """Least-squares y = a + b * f(value). Returns (a, b, record)."""
    pts = [(v, y) for v, y in labels if (v > 0 or not log_axis)]
    if len(pts) < 3:
        raise ValueError(f"axis calibration has {len(pts)} labels")
    for _ in range(len(pts)):
        f = np.array([math.log10(v) if log_axis else v for v, _ in pts])
        y = np.array([y for _, y in pts])
        b, a = np.polyfit(f, y, 1)
        res = np.abs(a + b * f - y)
        worst = int(np.argmax(res))
        if res[worst] > LABEL_RESIDUAL_DROP_PT and len(pts) > 3:
            pts.pop(worst)
            continue
        break
    rms = float(np.sqrt(np.mean(res ** 2)))
    if res.max() > LABEL_RESIDUAL_LIMIT_PT or rms > rms_limit:
        raise ValueError(f"axis residual {res.max():.2f} pt (rms {rms:.2f}) over {LABEL_RESIDUAL_LIMIT_PT} "
                         f"({rms_limit})")
    return float(a), float(b), {"labels": [v for v, _ in pts], "largest_residual_pt": round(float(res.max()), 3),
                                "rms_residual_pt": round(rms, 3)}


def tick_positions(drawings: list[dict], clip: pymupdf.Rect, edge_x: float, curve_paths: set[int]) -> list[float]:
    """Vertical positions of the short horizontal tick marks next to a plot edge. Curve paths are excluded."""
    ys = []
    for index, d in enumerate(drawings):
        if index in curve_paths or not clip.intersects(d["rect"]):
            continue
        for item in d["items"]:
            if item[0] == "l":
                if abs(item[1].y - item[2].y) > 0.05:
                    continue
                r = pymupdf.Rect(item[1], item[2]).normalize()
            elif item[0] == "re":
                r = item[1]
            else:
                continue
            if r.height > 1.6 or r.width > 8.0 or r.width < 0.8:
                continue
            if edge_x - 9.0 <= (r.x0 + r.x1) / 2 <= edge_x + 9.0:
                ys.append((r.y0 + r.y1) / 2)
    return sorted(ys)


def snap_to_ticks(labels: list[tuple[float, float]], ticks: list[float]) -> list[tuple[float, float]]:
    """Calibration points from the labels.

    A label within 6 pt of another label is dropped when at least four labels stay: crowded labels (0.004 to 0.006)
    are moved off their ticks by the layout. Each remaining label moves to its nearest tick when that tick is within
    3 pt and the label is the nearest label of that tick.
    """
    def crowded(y: float) -> bool:
        return any(0 < abs(other - y) < 6.0 for _, other in labels)

    kept = [(v, y) for v, y in labels if not crowded(y)]
    if len(kept) < 4:
        kept = list(labels)
    out = []
    for value, y in kept:
        if ticks:
            t = min(ticks, key=lambda ty: abs(ty - y))
            nearest_label = min(kept, key=lambda lab: abs(lab[1] - t))
            if abs(t - y) <= 3.0 and nearest_label[1] == y:
                y = t
        out.append((value, y))
    return out


def parse_number(text: str) -> float | None:
    if text.startswith("--"):
        text = text.lstrip("-")  # 5293 draws its log ticks as the text '--' before the value
    if not re.fullmatch(r"-?\d*\.?\d+", text):
        return None
    return float(text)


def digitize_chart(name: str, cfg: dict) -> dict:
    doc = pymupdf.open(SOURCES / cfg["file"])
    page = doc[cfg["page"] - 1]
    clip = pymupdf.Rect(*cfg["clip"])
    drawings = page.get_drawings()

    char_pieces = [p for k in cfg["characteristic_paths"] for p in path_pieces(drawings[k])]
    char_curves = join_pieces(char_pieces)[:3]
    if len(char_curves) != 3:
        raise ValueError(f"{name}: {len(char_curves)} characteristic curves")
    char_curves.sort(key=lambda c: float(np.mean(c[:, 1])))
    char_by_layer = dict(zip("BGR", char_curves))

    gran_by_layer: dict[str, np.ndarray] = {}
    if "granularity_layers" in cfg:
        for key, layer in cfg["granularity_layers"].items():
            chains = join_pieces(path_pieces(drawings[int(key)]))
            gran_by_layer[layer] = chains[0]
    else:
        gran_pieces = [p for k in cfg["granularity_paths"] for p in path_pieces(drawings[k])]
        gran_curves = join_pieces(gran_pieces)[:3]
        if len(gran_curves) != 3:
            raise ValueError(f"{name}: {len(gran_curves)} granularity curves")
        labels = []
        for x0, y0, x1, y1, text in numeric_spans(page, clip):
            if text in LAYER_LABELS:
                labels.append(((x0 + x1) / 2, (y0 + y1) / 2, LAYER_LABELS[text]))
        all_curves = gran_curves + char_curves

        def distance(curve: np.ndarray, lx: float, ly: float) -> float:
            return float(np.min(np.hypot(curve[:, 0] - lx, curve[:, 1] - ly)))

        gran_labels = []
        for lx, ly, layer in labels:
            d = [distance(c, lx, ly) for c in all_curves]
            if int(np.argmin(d)) < 3:
                gran_labels.append((lx, ly, layer))
        best = None
        for perm in itertools.permutations("BGR"):
            cost = 0.0
            for curve, layer in zip(gran_curves, perm):
                ds = [distance(curve, lx, ly) for lx, ly, lab in gran_labels if lab == layer]
                if not ds:
                    cost = math.inf
                    break
                cost += min(ds)
            if best is None or cost < best[0]:
                best = (cost, perm)
        if best is None or not math.isfinite(best[0]):
            raise ValueError(f"{name}: granularity labels {[(l[2]) for l in gran_labels]} do not name three curves")
        gran_by_layer = dict(zip(best[1], gran_curves))

    plot_left = min(c[:, 0].min() for c in char_curves)
    plot_right = max(c[:, 0].max() for c in char_curves)
    left_spans, right_spans = [], []
    for x0, y0, x1, y1, text in numeric_spans(page, clip):
        value = parse_number(text)
        if value is None:
            continue
        if x1 < plot_left - 1.5:
            left_spans.append((x0, x1, value, (y0 + y1) / 2))
        elif x0 > plot_right + 1.0:
            right_spans.append((x0, x1, value, (y0 + y1) / 2))
    # The axis labels form one column: the right-most column left of the plot and the left-most right of it.
    left_column_x1 = max(s[1] for s in left_spans)
    right_column_x0 = min(s[0] for s in right_spans if s[2] < 1.0)
    left = [(s[2], s[3]) for s in left_spans if s[1] > left_column_x1 - 4.0 and s[2] <= 4.5]
    right = [(s[2], s[3]) for s in right_spans if s[0] < right_column_x0 + 4.0 and s[2] < 1.0]
    curve_paths = set(cfg["characteristic_paths"]) | set(cfg["granularity_paths"])
    ticks_left = tick_positions(drawings, clip, left_column_x1 + 4.0, curve_paths)
    ticks_right = tick_positions(drawings, clip, right_column_x0 - 4.0, curve_paths)
    da, db, left_record = fit_axis(snap_to_ticks(left, ticks_left), log_axis=False, rms_limit=LABEL_RESIDUAL_RMS_LIMIT_PT)
    sa, sb, right_record = fit_axis(snap_to_ticks(right, ticks_right), log_axis=True,
                                    rms_limit=cfg.get("sigma_axis_rms_limit_pt", LABEL_RESIDUAL_RMS_LIMIT_PT))

    layers = {}
    for layer in "RGB":
        char, gran = char_by_layer[layer], gran_by_layer[layer]
        xc = np.maximum.accumulate(char[:, 0])
        xg = np.maximum.accumulate(gran[:, 0])
        lo, hi = max(xc[0], xg[0]), min(xc[-1], xg[-1])
        x = np.linspace(lo, hi, SAMPLES)
        y_char = np.interp(x, xc, char[:, 1])
        y_gran = np.interp(x, xg, gran[:, 1])
        density = (y_char - da) / db
        sigma = 10.0 ** ((y_gran - sa) / sb)
        layers[layer] = {"density": density.round(5).tolist(), "sigma_d": sigma.round(6).tolist(),
                         "x_page_pt": [round(float(lo), 2), round(float(hi), 2)]}
    write_overlay(name, page, clip, char_by_layer, gran_by_layer)
    return {"file": cfg["file"], "page": cfg["page"], "density_axis": left_record, "sigma_axis": right_record,
            "layers": layers}


def write_overlay(name: str, page: pymupdf.Page, clip: pymupdf.Rect, char: dict, gran: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    scale = 4.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3]
    fig, ax = plt.subplots(figsize=(pix.width / 100, pix.height / 100), dpi=100)
    ax.imshow(img, alpha=0.45)
    colours = {"R": "#d62728", "G": "#2ca02c", "B": "#1f77b4"}
    for layer, curve in char.items():
        ax.plot((curve[:, 0] - clip.x0) * scale, (curve[:, 1] - clip.y0) * scale, color=colours[layer], lw=1.0)
    for layer, curve in gran.items():
        ax.plot((curve[:, 0] - clip.x0) * scale, (curve[:, 1] - clip.y0) * scale, color=colours[layer], lw=2.2, ls="--")
        ax.text((curve[-1, 0] - clip.x0) * scale + 4, (curve[-1, 1] - clip.y0) * scale, layer, color=colours[layer],
                fontsize=14, weight="bold")
    ax.set_title(f"{name}: solid characteristic, dashed granularity", fontsize=12)
    ax.set_axis_off()
    OVERLAYS.mkdir(parents=True, exist_ok=True)
    fig.savefig(OVERLAYS / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    out = {"description": "Diffuse RMS granularity sigma_D over gross Status M density per layer, read from the "
                          "vector charts of chart_config.json by digitize_granularity_charts.py. Density and "
                          "sigma_D are sampled at the same log exposure.",
           "stocks": {}}
    for name, cfg in config["charts"].items():
        out["stocks"][name] = digitize_chart(name, cfg)
        axes = out["stocks"][name]
        print(f"{name}: density axis {axes['density_axis']['largest_residual_pt']:.2f} pt, "
              f"sigma axis {axes['sigma_axis']['largest_residual_pt']:.2f} pt")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
