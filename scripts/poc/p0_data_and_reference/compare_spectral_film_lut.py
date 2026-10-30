"""Compare the P0 digitization and the Status tables with the spectral_film_lut project.

Input:
- build/tmp/p0/reference/spectral_film_lut/ (downloaded by this script from the pinned commit
  in REFERENCE_FILES; hashes checked): the hand-digitized Portra 400 and Endura Premier data and
  the Status A / Status M tables of spectral_film_lut (MIT, Jan Lohse).
- profiles/*.json of this lab and the colormath Status tables (build/tmp/p0/sources/).
Output: results/p0_data_and_reference/comparison_spectral_film_lut.json.

Step: P0 (data and reference), independent check of the digitization. The two digitizations
come from the same Kodak data sheets by different methods (PDF vector paths here, points placed
by hand there), so their difference is an estimate of the digitization error of the hand method,
not of the source. The reference files are read as data with ast; no code of that project is
imported or executed, and no value of it is written to the profiles of this lab.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_spectral_reference as ref  # noqa: E402

COMMIT = "bcbcfc6861f49cc706dc5d00ea048e4853060aab"
BASE_URL = f"https://raw.githubusercontent.com/JanLohse/spectral_film_lut/{COMMIT}/"
REFERENCE_DIR = ref.REPO_ROOT / "build" / "tmp" / "p0" / "reference" / "spectral_film_lut"
REFERENCE_FILES = {
    "src/spectral_film_lut/negative_film/kodak_portra_400.py": "d106bac4d95834be6e696b89b40e9341792341a45172e61ffde273d3d763c682",
    "src/spectral_film_lut/print_film/kodak_endura_premier.py": "ebb7eb73ec42da0c6eb8611d5eee36721e37e34870e324c3d74047ab5a7c26e6",
    "src/spectral_film_lut/densiometry.py": "c04ea67f57bfef6852ac50d0306291f98b59c1509ff3a4dbd98ea2bc9564ba75",
    "LICENSE": "3cdc90b3e7727be6e5930102fadeaf35cf3d3bd7c492b90d6d16fb9ad8c3a1bd",
}
RESULT_PATH = ref.REPO_ROOT / "results" / "p0_data_and_reference" / "comparison_spectral_film_lut.json"


def fetch() -> dict[str, Path]:
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, expected in REFERENCE_FILES.items():
        path = REFERENCE_DIR / name.replace("/", "_")
        if not path.exists():
            with urllib.request.urlopen(BASE_URL + name, timeout=60) as response:
                path.write_bytes(response.read())
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"{name}: SHA-256 {actual}, expected {expected}")
        paths[name] = path
    return paths


def film_data_keywords(path: Path) -> dict:
    """Literal keyword arguments of the FilmData(...) call in a film definition file."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FilmData":
            out = {}
            for keyword in node.keywords:
                try:
                    out[keyword.arg] = ast.literal_eval(keyword.value)
                except ValueError:
                    pass
            return out
    raise RuntimeError(f"no FilmData call in {path}")


def first_literal_assignment(path: Path, name: str):
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            return ast.literal_eval(node.value)
    raise RuntimeError(f"no literal {name} in {path}")


def compare_curve(ours: dict, theirs: dict) -> dict:
    """Our curve interpolated at their points, inside our published domain."""
    x = np.array(sorted(theirs), dtype=float)
    y = np.array([theirs[k] for k in sorted(theirs)], dtype=float)
    ox, oy = np.array(ours["x"]), np.array(ours["y"])
    inside = (x >= ox[0]) & (x <= ox[-1])
    diff = y[inside] - np.interp(x[inside], ox, oy)
    return {"points": int(inside.sum()), "points_outside_our_domain": int((~inside).sum()),
            "their_x_range": [float(x[0]), float(x[-1])],
            "max_abs_difference": float(np.abs(diff).max()), "median_abs_difference": float(np.median(np.abs(diff))),
            "mean_difference": float(diff.mean())}


def label_by_peak(curves: list[dict], names: list[str]) -> dict:
    order = np.argsort([max(c, key=c.get) for c in curves])
    return {names[k]: curves[i] for k, i in enumerate(order)}


def label_by_level(curves: list[dict], names: list[str]) -> dict:
    order = np.argsort([np.mean(list(c.values())) for c in curves])
    return {names[k]: curves[i] for k, i in enumerate(order)}


def main() -> int:
    paths = fetch()
    portra = film_data_keywords(paths["src/spectral_film_lut/negative_film/kodak_portra_400.py"])
    endura = film_data_keywords(paths["src/spectral_film_lut/print_film/kodak_endura_premier.py"])
    ours_p = ref.load_profile("kodak_portra_400")["charts"]
    ours_e = ref.load_profile("kodak_endura_premier")["charts"]
    layers = ["yellow_forming_layer", "magenta_forming_layer", "cyan_forming_layer"]

    result = {"reference": {"repository": "https://github.com/JanLohse/spectral_film_lut", "commit": COMMIT,
                            "license": "MIT", "files": REFERENCE_FILES},
              "rule": "their value minus our value interpolated at their wavelength or log H, inside our domain",
              "portra_400": {}, "endura_premier": {}, "status_tables": {}}
    sens = label_by_peak(portra["log_sensitivity"], layers)
    for name in layers:
        result["portra_400"][f"log_sensitivity_{name}"] = compare_curve(ours_p["spectral_sensitivity"]["curves"][name], sens[name])
    char = label_by_level(portra["sensiometric_curve"], ["red", "green", "blue"])
    for name in ("red", "green", "blue"):
        result["portra_400"][f"characteristic_{name}"] = compare_curve(ours_p["characteristic"]["curves"][name], char[name])
    result["portra_400"]["midscale_neutral"] = compare_curve(ours_p["spectral_dye_density"]["curves"]["midscale_neutral"], portra["d_ref_sd"])
    result["portra_400"]["minimum_density"] = compare_curve(ours_p["spectral_dye_density"]["curves"]["minimum_density"], portra["d_min_sd"])

    sens = label_by_peak(endura["log_sensitivity"], layers)
    for name in layers:
        result["endura_premier"][f"log_sensitivity_{name}"] = compare_curve(ours_e["spectral_sensitivity"]["curves"][name], sens[name])
    char = label_by_level(endura["sensiometric_curve"], ["blue", "green", "red"])
    for name in ("red", "green", "blue"):
        result["endura_premier"][f"characteristic_{name}"] = compare_curve(ours_e["characteristic"]["curves"][name], char[name])
    dyes = label_by_peak(endura["spectral_density"], ["yellow_dye", "magenta_dye", "cyan_dye"])
    for name in ("yellow_dye", "magenta_dye", "cyan_dye"):
        result["endura_premier"][name] = compare_curve(ours_e["spectral_dye_density"]["curves"][name], dyes[name])

    # Status tables: their log10 spectral products (peak 5.000) against log10 of the colormath
    # linear products (peak 100) + 3, at the colormath 10 nm wavelengths where both are defined.
    colormath = ref.read_status_tables()
    wl = colormath["wavelengths"]
    densiometry = paths["src/spectral_film_lut/densiometry.py"]
    for status in ("A", "M"):
        theirs = first_literal_assignment(densiometry, f"STATUS_{status}")
        for channel, table in zip(("RED", "GREEN", "BLUE"), theirs):
            ours = colormath[f"ANSI_STATUS_{status}_{channel}"]
            rows = []
            for w, value in zip(wl, ours):
                if int(w) in table and value > 0:
                    rows.append((int(w), table[int(w)], float(np.log10(value / 100.0) + 5.0)))
            diff = np.array([r[1] - r[2] for r in rows])
            result["status_tables"][f"status_{status.lower()}_{channel.lower()}"] = {
                "common_10nm_points": len(rows), "max_abs_log_difference": float(np.abs(diff).max()),
                "wavelengths_with_difference_above_0_01": [r[0] for r, d in zip(rows, diff) if abs(d) > 0.01]}

    # Effect on densities: the P0 density checks with their tables (log10 values interpolated
    # linearly at 0.1 nm, zero outside their range) in place of the colormath tables.
    model = ref.ReferenceModel(1.0)
    fwl = model.grid.fine_wavelengths

    def their_weights(status: str) -> np.ndarray:
        rows = []
        for table in first_literal_assignment(densiometry, f"STATUS_{status}"):
            x = np.array(sorted(table), dtype=float)
            y = np.array([table[k] for k in sorted(table)])
            rows.append(np.where((fwl >= x[0]) & (fwl <= x[-1]), 10.0 ** np.interp(fwl, x, y), 0.0))
        return model.grid.weights(np.stack(rows))

    w_m, w_a = their_weights("M"), their_weights("A")
    effect = {}
    for name, density in (("portra_dmin", model.negative_dmin), ("portra_midscale_neutral", model.negative_midscale)):
        effect[f"status_m_{name}"] = {
            "colormath": model.status_density(density, model.w_status_m).tolist(),
            "spectral_film_lut": model.status_density(density, w_m).tolist()}
    prints = model.print_spectral_density(np.array([[0.3, 0.3, 0.3], [0.7, 0.65, 0.68], [1.5, 1.4, 1.45], [2.4, 2.3, 2.3]]))
    a_cm, a_jl = model.status_density(prints, model.w_status_a), model.status_density(prints, w_a)
    effect["status_a_endura_prints"] = {"colormath": a_cm.tolist(), "spectral_film_lut": a_jl.tolist(),
                                        "max_abs_difference": float(np.abs(a_cm - a_jl).max())}
    for key in ("status_m_portra_dmin", "status_m_portra_midscale_neutral"):
        effect[key]["max_abs_difference"] = float(np.abs(np.array(effect[key]["colormath"]) - np.array(effect[key]["spectral_film_lut"])).max())
    result["status_table_effect_on_density"] = effect
    print("density effect of the Status table source:", {k: round(v["max_abs_difference"], 5) for k, v in effect.items()})

    RESULT_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    for group in ("portra_400", "endura_premier", "status_tables"):
        for key, value in result[group].items():
            print(f"{group:15s} {key:42s} max {value.get('max_abs_difference', value.get('max_abs_log_difference')):.4f}"
                  + (f" median {value['median_abs_difference']:.4f} n={value['points']}" if "points" in value else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
