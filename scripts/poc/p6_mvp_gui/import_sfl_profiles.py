"""Write the profiles of all colour negative and colour print materials of spectral_film_lut, and the stock catalog of step P6.

Input: first argument, the src/spectral_film_lut directory of a local clone of spectral_film_lut (MIT, README U11) at commit bcbcfc68.
The data modules of that project run with a local FilmData class, so that the transforms of a data file (for example dataclasses.replace) stay as the project wrote them.
Its other code does not run.
Output: profiles/<module>.json for each material that has no profile, in the schema of the earlier profiles; stock_catalog.json next to this script (facts per material); a table on stdout.
An existing profile does not change, because the accepted stocks of P0 to P5 use it.
Step: P6, README section 8.

Rules, each recorded in the profile and in the catalog:
- resampled linearly on 1 nm, 1 cycle/mm, or 0.01 log10 lux-seconds inside the digitized domain, with no extrapolation;
- a curve with exposure_base other than 10 has its axis in stops around the exposure 12.5 / ISO lux seconds (definition of spectral_film_lut);
- a rising curve keeps its running maximum;
- rule 'zero_minimum_density': a negative with no minimum density curve takes zero, as spectral_film_lut does (inferred);
- rule 'neutral_from_dyes': a negative with no midscale neutral curve takes the minimum density plus the sum of its dye curves (inferred).
"""

from __future__ import annotations

import dataclasses
import importlib
import json
import math
import sys
import types
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PROFILE_DIR = REPO_ROOT / "profiles"
CATALOG = SCRIPT_DIR / "stock_catalog.json"
PROVENANCE = "spectral_film_lut (MIT) commit bcbcfc6861f49cc706dc5d00ea048e4853060aab, digitized by that project; linearly resampled by this lab; not checked against the manufacturer document"
GROUPS = ("negative_film", "print_film")


@dataclasses.dataclass
class FilmData:
    """The fields of the class of the same name in spectral_film_lut/film_data.py, with no dependency of that module."""

    name: str
    manufacturer: str
    film_type: str
    stage: str
    medium: str
    density_measure: str
    sensiometric_curve: list
    year: int | None = None
    iso: int | None = None
    alias: str | None = None
    comment: str | None = None
    exposure_kelvin: int = 5500
    projection_kelvin: int = 6500
    exposure_base: int = 10
    rms: float | None = None
    color_masking: float | None = None
    lad: list | None = None
    d_min_adjustment: bool | None = None
    log_sensitivity: list | None = None
    sensitivity: object | None = None
    spectral_density: list | None = None
    d_ref_sd: dict | None = None
    d_min_sd: dict | None = None
    rms_curve: list | None = None
    rms_density: list | None = None
    mtf: list | None = None


def read_materials(source: Path) -> dict[str, list[tuple[str, FilmData]]]:
    """Run the data modules with the local FilmData. Each module-level FilmData is one material, in the order of the module."""
    package = types.ModuleType("spectral_film_lut")
    package.__path__ = [str(source)]
    film_data = types.ModuleType("spectral_film_lut.film_data")
    film_data.FilmData = FilmData
    sys.modules["spectral_film_lut"] = package
    sys.modules["spectral_film_lut.film_data"] = film_data
    result: dict[str, list[tuple[str, FilmData]]] = {}
    for group in GROUPS:
        result[group] = []
        for path in sorted((source / group).glob("*.py")):
            if path.name == "__init__.py":
                continue
            module = importlib.import_module(f"spectral_film_lut.{group}.{path.stem}")
            found = [(k, v) for k, v in vars(module).items() if isinstance(v, FilmData) and not k.startswith("_")]
            own = [(k, v) for k, v in found if k.lower() == path.stem.lower() or len(found) == 1]
            if not own:
                own = found
            for variable, material in own:
                stem = path.stem if len(own) == 1 else variable.lower()
                result[group].append((stem, material))
    return result


def resampled(points: dict) -> dict:
    x = np.array(sorted(points), dtype=float)
    y = np.array([points[v] for v in sorted(points)], dtype=float)
    grid = np.arange(math.ceil(x[0]), math.floor(x[-1]) + 1.0)
    return {"x": grid.tolist(), "y": np.interp(grid, x, y).round(5).tolist()}


def characteristic(points: dict, to_log_h) -> tuple[dict, float]:
    x = np.array(sorted(points), dtype=float)
    y = np.array([points[v] for v in sorted(points)], dtype=float)
    log_h = to_log_h(x)
    grid = np.arange(math.ceil(log_h[0] * 100) / 100, log_h[-1], 0.01)
    values = np.interp(grid, log_h, y)
    rising = np.maximum.accumulate(values)
    return {"x": grid.round(4).tolist(), "y": rising.round(5).tolist()}, float((rising - values).max())


def chart(x_quantity: str, y_quantity: str, step: float, curves: dict) -> dict:
    return {"source": PROVENANCE, "x_quantity": x_quantity, "y_quantity": y_quantity, "grid_step": step, "provenance": PROVENANCE, "curves": curves}


def common_range(curves: dict) -> dict:
    """The same wavelengths on all curves, as the band split of the P0 model needs."""
    lo = max(c["x"][0] for c in curves.values())
    hi = min(c["x"][-1] for c in curves.values())
    for curve in curves.values():
        keep = [i for i, w in enumerate(curve["x"]) if lo <= w <= hi]
        curve["x"], curve["y"] = [curve["x"][i] for i in keep], [curve["y"][i] for i in keep]
    return curves


def build_profile(d: FilmData) -> tuple[dict, list[str]]:
    """Profile and the list of inference rules for one material. A ValueError names a field that the model of this lab needs and the material does not have."""
    inferred: list[str] = []
    if d.log_sensitivity is None:
        raise ValueError("no spectral sensitivity")
    if d.iso is None and d.exposure_base != 10:
        raise ValueError("a curve in stops with no ISO")
    reference = math.log10(12.5 / d.iso) if d.iso else 0.0
    to_log_h = (lambda x: x * math.log10(d.exposure_base) + reference) if d.exposure_base != 10 else (lambda x: x)
    curves = {}
    largest_fall = 0.0
    for channel, points in zip(("red", "green", "blue"), d.sensiometric_curve):
        curves[channel], fall = characteristic(points, to_log_h)
        largest_fall = max(largest_fall, fall)
    if largest_fall > 0.0:
        inferred.append(f"running_maximum_curve, largest fall {largest_fall:.4f}")
    charts = {
        "characteristic": chart("log10_exposure_lux_s", f"{d.density_measure}_density", 0.01, curves),
        "spectral_sensitivity": chart("wavelength_nm", "log10_sensitivity", 1.0, {layer: resampled(c) for layer, c in zip(("cyan_forming_layer", "magenta_forming_layer", "yellow_forming_layer"), d.log_sensitivity)}),
    }
    dyes = {name: resampled(c) for name, c in zip(("cyan_dye", "magenta_dye", "yellow_dye"), d.spectral_density)} if d.spectral_density else {}
    if d.stage == "camera":
        if d.d_ref_sd is None and not dyes:
            raise ValueError("no midscale neutral and no dye curves")
        minimum = resampled(d.d_min_sd) if d.d_min_sd else None
        if d.d_ref_sd:
            neutral = resampled(d.d_ref_sd)
        else:
            grid = np.arange(max(c["x"][0] for c in dyes.values()), min(c["x"][-1] for c in dyes.values()) + 1.0)
            total = sum(np.interp(grid, c["x"], c["y"]) for c in dyes.values())
            base = np.interp(grid, minimum["x"], minimum["y"]) if minimum else 0.0
            neutral = {"x": grid.tolist(), "y": np.round(base + total, 5).tolist()}
            inferred.append("neutral_from_dyes")
        if minimum is None:
            minimum = {"x": neutral["x"], "y": [0.0] * len(neutral["x"])}
            inferred.append("zero_minimum_density")
        dye_curves = common_range({"midscale_neutral": neutral, "minimum_density": minimum})
        dye_curves.update(dyes)
    else:
        if not dyes:
            raise ValueError("no dye curves")
        dye_curves = dyes
    charts["spectral_dye_density"] = chart("wavelength_nm", "spectral_density", 1.0, dye_curves)
    if d.mtf:
        names = ("red", "green", "blue") if len(d.mtf) == 3 else ("all_layers",)
        charts["modulation_transfer"] = chart("spatial_frequency_cycles_per_mm", "response", 1.0, {n: resampled(c) for n, c in zip(names, d.mtf)})
    profile = {"material": d.name, "source_document": PROVENANCE, "charts": charts, "inferred_rules": inferred,
               "redistribution_note": "Values from spectral_film_lut (MIT); see THIRD_PARTY_NOTICES.md and profiles/README.md."}
    return profile, inferred


def main() -> int:
    source = Path(sys.argv[1])
    materials = read_materials(source)
    catalog: dict = {"source": PROVENANCE, "negatives": {}, "prints": {}, "not_usable": {}}
    for group, entries in materials.items():
        for stem, d in entries:
            path = PROFILE_DIR / f"{stem}.json"
            existing = path.exists()
            try:
                profile, inferred = build_profile(d)
            except ValueError as error:
                catalog["not_usable"][stem] = {"name": d.name, "reason": str(error)}
                print(f"{stem:32s} NOT USABLE: {error}")
                continue
            if not existing:
                path.write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")
            entry = {"name": d.name, "manufacturer": d.manufacturer, "medium": d.medium, "year": d.year, "density_measure": d.density_measure, "profile_existed": existing, "inferred_rules": inferred}
            if group == "negative_film":
                entry.update(iso=d.iso, exposure_kelvin=d.exposure_kelvin, published_dyes=bool(d.spectral_density), mtf_curves=len(d.mtf) if d.mtf else 0)
                catalog["negatives"][stem] = entry
            else:
                catalog["prints"][stem] = entry
            print(f"{stem:32s} {'kept' if existing else 'wrote'} {d.density_measure:10s} {d.medium:5s} {inferred}")
    CATALOG.write_text(json.dumps(catalog, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(len(catalog["negatives"]), "negatives", len(catalog["prints"]), "prints", len(catalog["not_usable"]), "not usable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
