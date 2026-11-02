"""Separation exposure against neutral exposure: does rule 'development_inhibition' give the form of a real over-corrected colour negative?

Input: the profiles, the catalog, the reflectance tables, wratten_filters.py of spectral_film_lut (first argument, its src/spectral_film_lut directory; read as literals, the code does not run). Output: results/p7_spectral_acceleration/separation_curves.json, and a figure at the second argument. Machine rule: CPU only, one process.

Reference: Sehlin, Kennel, Ortman, Reinking, "Choosing Eastman Color Negative Film 5247 or Eastman Color High-Speed Negative Film 5294", SMPTE Journal, July 1985, page 730, Figure 14: green Status M density of 5294 under a neutral and a green exposure. Read by eye from the scan, so each value has an error of about 0.03 density:
- the curves overlap up to about 0.8 density above base; the base is about 0.41;
- at 1.71 above base on the neutral curve, the separation curve is about 0.27 higher;
- over the 1.6 log H above the overlap, the neutral curve rises 0.92 and the separation curve 1.19, so the slope is about 30 % higher.
This is another stock, so the limits test the form, and they are wide. Text of that paper: a separation curve above the neutral curve is 'over-corrected', and 5247 and 5294 are generally over-corrected.

Limits, set before the first run, on the green layer with the separation light of case 'wratten_99':
- sign: separation minus neutral is at least -0.03 at each exposure;
- overlap: the difference is at most 0.05 in size, up to 0.6 above base;
- onset: the difference first passes 0.03 between 0.4 and 1.2 above base;
- top: at 1.7 above base on the neutral curve (or the highest value that the curve reaches), the difference is between 0.10 and 0.45;
- slope: the slope gain over the range above the onset is between 10 % and 50 %.

Case 'one_layer' exposes the green layer only, so the sensitivities take no part. Case 'wratten_99' and 'wratten_58' pass the filter under D55, with the three layer weights of the negative; a gain per layer makes D55 a neutral exposure, which is rule 'grey_anchor' in form.
Sweeps of the share between layers and of the total of K are a measure of what the form can reach, not a fit: no value of them changes the model.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "separation_curves.json"
NEGATIVES = ("kodak_5207", "kodak_5219", "kodak_5213", "kodak_5203", "fuji_eterna_500", "kodak_portra_400", "kodak_gold_200", "kodak_ektar_100")
SWEEP_NEGATIVE = "kodak_5207"
LAYER = {"red": 0, "green": 1, "blue": 2}
OTHER_FILTER = {"red": "29", "green": "99", "blue": "47"}
SHARES = (0.0, 0.25, 0.5, 0.75, 1.0)
K_SCALES = (0.0, 0.5, 1.0, 1.5)
OVERLAP_ABOVE_BASE = 0.6
TOP_ABOVE_BASE = 1.7


def wratten(source: Path) -> dict:
    for node in ast.parse((source / "wratten_filters.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "WRATTEN" and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise ValueError("no WRATTEN table")


def filter_transmittance(points: dict, wavelengths: np.ndarray) -> np.ndarray:
    x = np.array(sorted(points))
    y = np.array([points[v] for v in x])
    return 10.0 ** -np.interp(wavelengths, x, y)


def relative_layers(model: fp.FilmPreview, transmittance: np.ndarray, layer: int) -> np.ndarray:
    """log10 of the exposure of each layer against the chosen layer, under D55 and the filter, with D55 alone as the neutral."""
    f = model.film
    wl = f.grid.wavelengths
    light = fp.p0.cie_daylight_relative_spd(5500.0, wl)
    weights = f.w_negative
    neutral = f.grid.integrate(light, weights)
    filtered = f.grid.integrate(light * transmittance, weights)
    ratio = np.log10(filtered / neutral)
    return ratio - ratio[layer]


def status_m(model: fp.FilmPreview, log_h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Status M of a chart exposure (N, 3): the fixed point of 16 steps, and the two steps that the product takes on a flat area."""
    crit = model.film.negative_criterion_log_h
    record, _ = model.negative_density(10.0 ** (log_h - crit))
    two_steps = record
    if model.inhibition is not None:
        i = model.inhibition
        grid = i["start"][:, None] + i["step"] * np.arange(i["free"].shape[1])[None, :]
        amounts = np.stack([np.interp(log_h[:, k], c.log_h, c.density) for k, c in enumerate(model.negative_curves)], axis=1)
        for _ in range(fp.INHIBITION_STEPS_IMAGE + 1):
            reduced = log_h - amounts @ i["k"].T
            amounts = np.stack([np.interp(reduced[:, k], grid[k][: i["lengths"][k]], i["free"][k][: i["lengths"][k]]) for k in range(3)], axis=1)
        two_steps = amounts
    return model.record_to_status_m(record), model.record_to_status_m(two_steps)


def compare(model: fp.FilmPreview, relative: np.ndarray | None, name: str) -> dict:
    layer = LAYER[name]
    curves = model.negative_curves
    start = max(c.log_h[0] for c in curves)
    stop = min(c.log_h[-1] for c in curves)
    x = np.arange(start, stop, 0.02)
    neutral = np.stack([x, x, x], axis=1)
    if relative is None:
        separation = np.stack([np.full_like(x, c.log_h[0]) for c in curves], axis=1)
        separation[:, layer] = x
    else:
        separation = np.maximum(x[:, None] + relative, np.array([c.log_h[0] for c in curves]))
    n, n2 = status_m(model, neutral)
    s, s2 = status_m(model, separation)
    base = n[0, layer]
    above = n[:, layer] - base
    difference = s[:, layer] - n[:, layer]
    return {"x": x, "above": above, "difference": difference, "difference_two_steps": s2[:, layer] - n2[:, layer], "separation_above": s[:, layer] - base, "base": float(base), "other_layers_at_top": separation[-1].tolist()}


def scores(curve: dict) -> dict:
    above, difference, x = curve["above"], curve["difference"], curve["x"]
    overlap = above <= OVERLAP_ABOVE_BASE
    passed = np.flatnonzero(difference > 0.03)
    onset = float(above[passed[0]]) if len(passed) else None
    top_above = min(TOP_ABOVE_BASE, float(above.max()))
    top = int(np.argmin(np.abs(above - top_above)))
    gain = None
    if onset is not None and top > passed[0] + 5:
        first = int(passed[0])
        gain = float((curve["separation_above"][top] - curve["separation_above"][first]) / (above[top] - above[first]) - 1.0)
    result = {"smallest_difference": float(difference.min()), "largest_in_overlap": float(np.abs(difference[overlap]).max()), "onset_above_base": onset, "top_above_base": top_above, "difference_at_top": float(difference[top]), "slope_gain": gain,
              "difference_at_top_two_steps": float(curve["difference_two_steps"][top])}
    result["limits"] = {"sign": result["smallest_difference"] >= -0.03, "overlap": result["largest_in_overlap"] <= 0.05, "onset": onset is not None and 0.4 <= onset <= 1.2, "top": 0.10 <= result["difference_at_top"] <= 0.45, "slope": gain is not None and 0.10 <= gain <= 0.50}
    return result


def main() -> int:
    table = wratten(Path(sys.argv[1]))
    figure_path = Path(sys.argv[2])
    record: dict = {"negatives": {}, "sweep": {}}
    plotted = {}
    failures = 0
    for negative in NEGATIVES:
        settings = mp.RenderSettings(negative=negative, print_material="kodak_2383")
        options = mp.film_options(settings)
        model = fp.FilmPreview(options)
        wl = model.film.grid.wavelengths
        entry = {"k": model.inhibition["k"].tolist() if model.inhibition is not None else None, "cases": {}}
        for case, relative in {"one_layer": None, "wratten_99": relative_layers(model, filter_transmittance(table["99"], wl), 1), "wratten_58": relative_layers(model, filter_transmittance(table["58"], wl), 1)}.items():
            curve = compare(model, relative, "green")
            entry["cases"][case] = {**scores(curve), "relative_log_h": None if relative is None else relative.tolist()}
            if case == "wratten_99":
                plotted[negative] = curve
                failures += sum(not v for v in entry["cases"][case]["limits"].values())
        for name in ("red", "blue"):
            curve = compare(model, relative_layers(model, filter_transmittance(table[OTHER_FILTER[name]], wl), LAYER[name]), name)
            entry["cases"][f"{name}_wratten_{OTHER_FILTER[name]}"] = scores(curve)
        record["negatives"][negative] = entry
        print(negative, {c: (round(v["difference_at_top"], 3), v["onset_above_base"] and round(v["onset_above_base"], 2), v["slope_gain"] and round(v["slope_gain"], 3), [k for k, ok in v["limits"].items() if not ok]) for c, v in entry["cases"].items()}, flush=True)

    base = mp.film_options(mp.RenderSettings(negative=SWEEP_NEGATIVE, print_material="kodak_2383"))
    probe = fp.FilmPreview(base)
    wl = probe.film.grid.wavelengths
    relative = relative_layers(probe, filter_transmittance(table["99"], wl), 1)
    for scale in K_SCALES:
        for share in SHARES:
            total = tuple(v * scale for v in base.inhibition_total)
            options = replace(base, inhibition_total=total, inhibition_image=total, inhibition_cross_share=share)
            key = f"k_scale {scale} share {share}"
            try:
                model = fp.FilmPreview(options)
            except ValueError as error:
                record["sweep"][key] = {"error": str(error)}
                print(key, "error", error, flush=True)
                continue
            curve = compare(model, relative, "green")
            record["sweep"][key] = scores(curve)
            print(key, round(record["sweep"][key]["difference_at_top"], 3), record["sweep"][key]["slope_gain"] and round(record["sweep"][key]["slope_gain"], 3), [k for k, ok in record["sweep"][key]["limits"].items() if not ok], flush=True)
    record["failures_wratten_99"] = failures
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([0.0, 0.8, 1.3, 1.71], [0.0, 0.0, 0.16, 0.27], "k--", lw=2, label="5294, read from Fig. 14 (another stock)")
    for negative, curve in plotted.items():
        keep = curve["above"] <= 1.9
        ax.plot(curve["above"][keep], curve["difference"][keep], label=negative)
    ax.axhline(0.0, color="0.7", lw=1)
    ax.set_xlabel("Green Status M density above base, neutral exposure")
    ax.set_ylabel("Separation minus neutral, green density")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=130)
    print("failures", failures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
