"""Numeric checks of rule 'overexposed_negative' and rule 'contrast_mask' on the six stocks.

Input: the P2 to P4 libraries and the P5 profiles, no photo. Output: results/p5_film_and_print_combinations/shadow_mode.json.
Step: P5, ROADMAP section 8, decision U35. Limits set before the first run:
- the mask table at zero density against the print table: largest difference <= 1e-6 in cube root XYZ;
- a mask density halfway between two tables against a table made at that density: largest error <= 0.002 in cube root XYZ;
- a flat mid grey keeps its print value, with the mask, with 2 stops, and with both: largest change of L* <= 0.1;
- a neutral ramp from -6 to +6 stops stays in order: largest fall of L* <= 0.05;
- a flat field at +3 stops: largest change of L* against the P4 print <= 1.5;
- the hue sweep through the product grade: largest second difference <= 0.02.
Information without a limit: the neutral ramp on the print, and the halo at a step edge: L* of the dark side near the edge and far from it. Every option value of the rules is inferred.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p4_physical_film_response"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aces_scan import fp  # noqa: E402
from check_film_response import srgb_to_lab  # noqa: E402
from check_stock_chain import STOCK_KEYS, stock_options  # noqa: E402
from render_scanner_light_review import hue_sweep  # noqa: E402

RESULT = REPO_ROOT / "results" / "p5_film_and_print_combinations" / "shadow_mode.json"
MASK = dict(mask_gamma=0.5)
OVER = dict(overexposure_stops=2.0)


def flat(value: float) -> np.ndarray:
    return np.full((64, 64, 3), value, dtype=np.float32)


def lab_of(preview: fp.FilmPreview, image: np.ndarray) -> np.ndarray:
    return srgb_to_lab(preview.render(image)[0].astype(np.float64))


def check_stock(key: str) -> dict:
    extra = dict(scene_light="D55") if key == "5207_2383" else {}
    paths = {"p4": fp.FilmPreview(stock_options(key, **extra)), "mask": fp.FilmPreview(stock_options(key, **extra, **MASK)),
             "over": fp.FilmPreview(stock_options(key, **extra, **OVER)), "both": fp.FilmPreview(stock_options(key, **extra, **MASK, **OVER))}
    masked = paths["mask"]
    zero = int(round(-fp.MASK_DENSITY_START / fp.MASK_DENSITY_STEP))
    table_error = float(np.abs(masked._mask_tables[zero] - paths["p4"].print_table).max())
    film = masked.film
    balance = np.asarray(film.printer_balance_log10, dtype=np.float64).copy()
    rr, gg, bb = np.meshgrid(*masked.density_grid, indexing="ij")
    nodes = np.stack([rr, gg, bb], axis=-1).reshape(-1, 3)[::37]
    film.printer_balance_log10 = balance - 0.175
    direct = np.cbrt(masked._print_nodes(nodes)[0])
    film.printer_balance_log10 = balance
    k = int(round((0.15 - fp.MASK_DENSITY_START) / fp.MASK_DENSITY_STEP))
    n = fp.DENSITY_NODES
    halfway = 0.5 * (masked._mask_tables[k] + masked._mask_tables[k + 1]).reshape(n * n * n, 3)[::37]
    interpolation = float(np.abs(halfway - direct).max())
    grey = {name: float(lab_of(p, flat(0.18))[32, 32, 0]) for name, p in paths.items()}
    high = {name: float(lab_of(p, flat(0.18 * 8.0))[32, 32, 0]) for name, p in paths.items()}
    stops = np.arange(-6.0, 6.5, 1.0)
    ramp = np.outer(0.18 * 2.0 ** stops, np.ones(3)).astype(np.float32)[None]
    fine = np.outer(0.18 * 2.0 ** np.linspace(-6.0, 6.0, 241), np.ones(3)).astype(np.float32)[None]
    fall = max(float(np.maximum(0.0, -np.diff(lab_of(p, fine)[0, :, 0])).max()) for p in paths.values())
    edge = np.full((256, 1024, 3), 0.18 * 2.0 ** -3.0, dtype=np.float32)
    edge[:, 512:] = 0.18 * 2.0 ** 2.0
    row = lab_of(masked, edge)[128, :, 0]
    sweep = fp.product_input(hue_sweep(masked.c).astype(np.float32), masked.c)
    second = max(float(np.abs(np.diff(paths[name].render(sweep)[0].astype(np.float64), 2, axis=1)).max()) for name in ("mask", "both"))
    return {"table_at_zero_density": table_error, "table_interpolation": interpolation, "grey_L": {k: round(v, 3) for k, v in grey.items()}, "grey_change": round(max(abs(grey[k] - grey["p4"]) for k in grey), 3),
            "plus_3_stops_L": {k: round(v, 2) for k, v in high.items()}, "plus_3_stops_change": round(max(abs(high[k] - high["p4"]) for k in high), 2), "largest_fall": round(fall, 4), "sweep": round(second, 4),
            "stops": stops.tolist(), "ramp_L": {name: lab_of(p, ramp)[0, :, 0].round(1).tolist() for name, p in paths.items()},
            "edge_dark_L_far": round(float(row[20]), 2), "edge_dark_L_near": round(float(row[505]), 2), "edge_dark_L_p4": round(float(lab_of(paths["p4"], edge)[128, 20, 0]), 2)}


def main() -> int:
    limits = {"table_at_zero_density": 1e-6, "table_interpolation": 0.002, "grey_change": 0.1, "largest_fall": 0.05, "plus_3_stops_change": 1.5, "sweep": 0.02}
    result = {"limits": limits, "mask_options": MASK, "overexposure_options": OVER, "stocks": {}, "pass": {}}
    for key in STOCK_KEYS:
        r = check_stock(key)
        result["stocks"][key] = r
        result["pass"][key] = {name: r[name] <= limit for name, limit in limits.items()}
        print(key, json.dumps(result["pass"][key]), flush=True)
        print("  ", {k: r[k] for k in ("table_at_zero_density", "table_interpolation", "grey_L", "plus_3_stops_L", "largest_fall", "sweep", "edge_dark_L_p4", "edge_dark_L_far", "edge_dark_L_near")}, flush=True)
        print("   ramp", r["ramp_L"], flush=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
