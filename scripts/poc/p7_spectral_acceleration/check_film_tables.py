"""Checks of the C++ table library and of rule 'staged_print_table'. The limits below were written before this script first ran; a probe on two photos (P7 report, section 2) had shown the size of the error.

Input: the profiles, the reflectance tables, AP1 arrays of the earlier steps under build/tmp/ (names in PHOTOS). Output: results/p7_spectral_acceleration/checks.json, and a line per check on stdout. Step: P7, ROADMAP U68.
A failed check stays in the results with its value, and the exit code is 1. The reference of a table is the dye solve per node of FilmPreview._print_nodes, which check_fast_kernels.py compares with the array form direct_print_xyz.
Machine rule: CPU only, no GPU job.

| Check | Behaviour and comparison rule | Limit |
| Weights | SpectralGrid.weights with stored nonzero values, against the dense matrix, on the fixed functions of one model: largest relative difference | 1e-12 |
| Band response | log10_band_response against the array form paper_layer_exposure_unbalanced, 4096 random nodes: largest log10 difference | 1e-11 |
| Record is the amounts | Rule dye_amount_curves on each stock: the array dye solve of the Status M of 4096 random nodes returns the record: largest difference in amount | 1e-9 |
| Status M record | solve_dye_amounts against the array dye solve, on a stock with negative_record = 'status_m', nodes that the solve reached: largest difference in amount | 1e-9 |
| Paper stage | The table at 4096 random nodes against the array dye solve and viewed_xyz, nodes that the solve reached: largest relative XYZ difference | 1e-9 |
| APD table | ScanPreview table at 4096 random nodes against direct_apd: largest density difference | 1e-9 |
| Photos | Staged table against the table of the reference, each stock on each photo, final sRGB in 8 bit code, per pixel the largest channel difference | p99.9 at most 1.0, largest at most 4.0 |
| Neutral ramp | The same on a neutral ramp of -5 to +5 stops, 241 values | largest at most 0.5 |
| Controls | The Photos and Neutral ramp limits with each control of the print table at its low and high end, on two stocks | the same limits |
| Mask | The table at mask density 0 against the print table: largest difference of the cube root | 1e-6 |
| Disk | A new model and a new scan write nothing into the table directory | no new file |
| Time | Print table with empty stage memory; a new control value with the stages kept; APD table | at most 2 s; at most 0.05 s; at most 1 s |

The error on all table nodes is stated with no limit: most nodes are colours that no photo reaches.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

from aces_scan import ScanPreview  # noqa: E402

fp = mp.fp
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "checks.json"
PHOTOS = {"se188": "p3/input/se188", "se228": "p3/input/se228", "leica_m11": "p3/input/leica_m11", "nikon_zf": "p3/input/nikon_zf", "_DSC4063": "p4/input_shangrila/_DSC4063", "_DSC8148": "baseline/night/_DSC8148_ap1", "digital_ap1": "p5/real_5207/pair/digital_ap1"}
CONTROL_PHOTOS = ["_DSC8148", "se188"]
STOCKS = [("kodak_5207", "kodak_2383"), ("kodak_5219", "kodak_2383"), ("kodak_portra_400", "kodak_endura_premier"), ("kodak_portra_160", "kodak_endura_premier"), ("kodak_portra_800", "kodak_endura_premier"),
          ("kodak_ektar_100", "kodak_endura_premier"), ("kodak_gold_200", "kodak_endura_premier"), ("fuji_c200", "kodak_endura_premier"), ("kodak_5207", "fuji_ca_maxima"), ("fuji_pro_400h", "kodak_supra_endura")]
CONTROL_STOCKS = [("kodak_5207", "kodak_2383"), ("kodak_portra_400", "kodak_endura_premier")]
TABLE_CONTROLS = ("overexposure_stops", "inhibition_scale", "print_grey_shift", "print_contrast", "print_flash", "viewing_flare", "print_timing")
LIMITS = {"weights": 1e-12, "band": 1e-11, "record": 1e-9, "status_m": 1e-9, "paper": 1e-9, "apd": 1e-9, "p999": 1.0, "largest": 4.0, "ramp": 0.5, "mask": 1e-6, "time_first_s": 2.0, "time_control_s": 0.05, "time_apd_s": 1.0}
SAMPLES = 4096
rng = np.random.default_rng(20261031)
failed: list[str] = []
results: dict = {"limits": LIMITS, "photos": list(PHOTOS)}


def report(name: str, value: float, limit: float) -> dict:
    passed = bool(value <= limit)
    print(f"{'pass' if passed else 'FAIL'} {name}: {value:.3g} (limit {limit:.3g})", flush=True)
    if not passed:
        failed.append(name)
    return {"value": float(value), "limit": limit, "pass": passed}


def read_photo(name: str) -> np.ndarray:
    return np.ascontiguousarray(np.load(REPO_ROOT / "build" / "tmp" / f"{PHOTOS[name]}.npy"), dtype=np.float32)


def random_nodes(model: fp.FilmPreview) -> np.ndarray:
    return np.stack([rng.uniform(g[0], g[-1], SAMPLES) for g in model.density_grid], axis=1)


def table_nodes(model: fp.FilmPreview) -> np.ndarray:
    return np.stack(np.meshgrid(*model.density_grid, indexing="ij"), axis=-1).reshape(-1, 3)


def reference_table(model: fp.FilmPreview) -> np.ndarray:
    return np.cbrt(model._print_nodes(table_nodes(model))[0]).reshape(model.print_table.shape).astype(np.float32)


def statistics(difference: np.ndarray) -> dict:
    largest_channel = difference.max(axis=-1) if difference.ndim > 1 else difference
    return {"median": round(float(np.median(largest_channel)), 4), "p99": round(float(np.percentile(largest_channel, 99)), 4), "p999": round(float(np.percentile(largest_channel, 99.9)), 4), "largest": round(float(largest_channel.max()), 4)}


def render_difference(model: fp.FilmPreview, reference: np.ndarray, image: np.ndarray) -> dict:
    staged_image = np.asarray(model.render(image)[0], dtype=np.float64)
    staged_table = model._print_f32
    model._print_f32 = reference
    reference_image = np.asarray(model.render(image)[0], dtype=np.float64)
    model._print_f32 = staged_table
    return statistics(np.abs(staged_image - reference_image) * 255.0)


def compare_on_images(name: str, settings: mp.RenderSettings, graded: dict[str, np.ndarray], ramp: np.ndarray) -> dict:
    model = fp.FilmPreview(mp.film_options(settings))
    reference = reference_table(model)
    white = model.xyz_to_display
    srgb = lambda table: fp.srgb_encode(np.clip(np.maximum(table.reshape(-1, 3).astype(np.float64) ** 3, 0.0) @ white.T, 0.0, 1.0)) * 255.0
    entry = {"all_table_nodes_8bit": statistics(np.abs(srgb(reference) - srgb(model.print_table))), "photos": {}, "table_counts": model.table_counts}
    for photo, image in graded.items():
        entry["photos"][photo] = render_difference(model, reference, image)
        print(f"  {name} {photo}: {entry['photos'][photo]}", flush=True)
    entry["neutral_ramp_8bit"] = render_difference(model, reference, ramp)["largest"]
    entry["p999"] = report(f"{name}, photos p99.9", max(v["p999"] for v in entry["photos"].values()), LIMITS["p999"])
    entry["largest"] = report(f"{name}, photos largest", max(v["largest"] for v in entry["photos"].values()), LIMITS["largest"])
    entry["ramp"] = report(f"{name}, neutral ramp", entry["neutral_ramp_8bit"], LIMITS["ramp"])
    return entry


def check_weights(model: fp.FilmPreview) -> None:
    grid = model.film.grid
    fine = np.stack([np.exp(-0.5 * ((grid.fine_wavelengths - center) / 40.0) ** 2) for center in (450.0, 550.0, 650.0)])
    distance = np.abs(grid.fine_wavelengths[None, :] - grid.wavelengths[:, None]) / grid.step_nm
    dense = np.stack([row * film_trapezoid(grid.fine_step_nm, np.ones_like(row, dtype=bool)) for row in fine]) @ np.clip(1.0 - distance, 0.0, None).T
    results["weights"] = report("weights", float(np.abs(grid.weights(fine) / np.where(dense == 0.0, 1.0, dense) - np.where(dense == 0.0, 0.0, 1.0)).max()), LIMITS["weights"])


def film_trapezoid(step: float, support: np.ndarray) -> np.ndarray:
    return fp.p0.support_trapezoid_weights(step, support)


def check_stages(model: fp.FilmPreview) -> None:
    f = model.film
    nodes = random_nodes(model)
    pr = fp.spectral_support(f.w_printing)
    native = fp.film_tables.log10_band_response(f.negative_dmin[pr], f.negative_dyes[:, pr], f.w_printing[:, pr], nodes)
    results["band_response"] = report("band response", float(np.abs(native - np.log10(f.paper_layer_exposure_unbalanced(f.negative_spectral_density(nodes)))).max()), LIMITS["band"])
    start, axis_range, table, not_reached = model._paper_stage()
    index = np.stack([rng.integers(0, fp.PAPER_TABLE_NODES, SAMPLES) for _ in range(3)], axis=1)
    index = index[not_reached[index[:, 0], index[:, 1], index[:, 2]] == 0]
    amounts, residual = fp.solve_amounts(start + axis_range * (index / (fp.PAPER_TABLE_NODES - 1)) ** fp.PAPER_AXIS_POWER, f.paper_base, f.paper_dyes, f.w_status_a)
    xyz = f.viewed_xyz(f.print_spectral_density(amounts))
    stage = table[index[:, 0], index[:, 1], index[:, 2]] ** 3
    used = residual < 1e-10
    results["paper_stage"] = report("paper stage", float((np.abs(stage - xyz) / np.maximum(xyz, 1e-9))[used].max()), LIMITS["paper"])
    results["paper_stage"]["nodes"] = int(used.sum())
    scan = ScanPreview(mp.film_options(mp.RenderSettings()))
    samples = random_nodes(scan.negative)
    grid = scan.negative.density_grid
    index = np.stack([rng.integers(0, fp.DENSITY_NODES, SAMPLES) for _ in range(3)], axis=1)
    samples = np.stack([grid[k][index[:, k]] for k in range(3)], axis=1)
    results["apd_table"] = report("APD table", float(np.abs(scan.table[index[:, 0], index[:, 1], index[:, 2]] - scan.direct_apd(samples)[0]).max()), LIMITS["apd"])


def check_status_m_record() -> None:
    model = fp.FilmPreview(fp.FilmOptions(**fp.DARKROOM))
    f = model.film
    nodes = random_nodes(model)
    native, _ = model.table_amounts(nodes)
    base = f.status_density(f.negative_dmin, f.w_status_m)
    array, residual = fp.solve_amounts(nodes + base - f.negative_curve_dmin, f.negative_dmin, f.negative_dyes, f.w_status_m)
    reached = residual < 1e-10
    results["status_m_record"] = report("status M record", float(np.abs(native - array)[reached].max()), LIMITS["status_m"])
    results["status_m_record"]["nodes"] = int(reached.sum())


def check_record_identity() -> None:
    largest = 0.0
    for negative, material in STOCKS:
        model = fp.FilmPreview(mp.film_options(mp.RenderSettings(negative=negative, print_material=material)))
        f = model.film
        nodes = random_nodes(model)
        base = f.status_density(f.negative_dmin, f.w_status_m)
        array, _ = fp.solve_amounts(model.record_to_status_m(nodes) + base - f.negative_curve_dmin, f.negative_dmin, f.negative_dyes, f.w_status_m)
        largest = max(largest, float(np.abs(array - nodes).max()))
    results["record_is_amounts"] = report("record is the amounts", largest, LIMITS["record"])


def check_mask() -> None:
    options = mp.film_options(mp.RenderSettings())
    masked = fp.FilmPreview(replace(options, mask_gamma=0.5))
    zero = int(round(-fp.MASK_DENSITY_START / fp.MASK_DENSITY_STEP))
    results["mask"] = report("mask", float(np.abs(masked._mask_tables[zero] - masked.print_table).max()), LIMITS["mask"])


def check_disk_and_time() -> None:
    before = sorted(p.name for p in fp.CACHE_DIR.iterdir())
    settings = mp.RenderSettings(negative="fuji_superia_reala", print_material="fuji_ca_dpII")
    fp._stage_tables.clear()
    start = time.perf_counter()
    model = fp.FilmPreview(mp.film_options(settings))
    first_model = time.perf_counter() - start
    fp._stage_tables.clear()
    start = time.perf_counter()
    model._build_print_table()
    first_table = time.perf_counter() - start
    new_value = mp.film_options(replace(settings, print_contrast=1.1, print_flash=0.05))
    start = time.perf_counter()
    other = fp.FilmPreview(new_value)
    control_model = time.perf_counter() - start
    start = time.perf_counter()
    other._build_print_table()
    control_table = time.perf_counter() - start
    start = time.perf_counter()
    scan = ScanPreview(mp.film_options(replace(settings, negative="fuji_natura_1600")))
    scan_model = time.perf_counter() - start
    start = time.perf_counter()
    scan._build_table()
    apd_table = time.perf_counter() - start
    new_files = sorted(set(p.name for p in fp.CACHE_DIR.iterdir()) - set(before))
    results["time_s"] = {"model_with_empty_stage_memory": round(first_model, 3), "print_table_with_empty_stage_memory": round(first_table, 3), "model_new_control_value": round(control_model, 3), "print_table_new_control_value": round(control_table, 4), "scan_model_new_negative": round(scan_model, 3), "apd_table": round(apd_table, 3)}
    print(results["time_s"], flush=True)
    results["time_first"] = report("time, print table", first_table, LIMITS["time_first_s"])
    results["time_control"] = report("time, new control value", control_table, LIMITS["time_control_s"])
    results["time_apd"] = report("time, APD table", apd_table, LIMITS["time_apd_s"])
    results["disk"] = report("disk, new files", float(len(new_files)), 0.0)
    results["disk"]["files"] = new_files


def main() -> int:
    default = mp.RenderSettings()
    model = fp.FilmPreview(mp.film_options(default))
    check_weights(model)
    check_stages(model)
    check_status_m_record()
    check_record_identity()
    check_mask()
    check_disk_and_time()
    graded = {}
    for name in PHOTOS:
        graded[name] = np.ascontiguousarray(fp.fk.product_grade(read_photo(name), float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32)
    ramp = np.outer(0.18 * 2.0 ** np.linspace(-5.0, 5.0, 241), np.ones(3)).astype(np.float32)[None]
    results["stocks"] = {f"{n} on {m}": compare_on_images(f"{n} on {m}", replace(default, negative=n, print_material=m), graded, ramp) for n, m in STOCKS}
    control_photos = {name: graded[name] for name in CONTROL_PHOTOS}
    results["controls"] = {}
    for negative, material in CONTROL_STOCKS:
        for control in mp.CONTROLS:
            if control.name not in TABLE_CONTROLS:
                continue
            for value in (control.low, control.high):
                label = f"{negative} on {material}, {control.name} = {value}"
                results["controls"][label] = compare_on_images(label, replace(default, negative=negative, print_material=material, **{control.name: value}), control_photos, ramp)
    results["failed"] = failed
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(failed)} failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
