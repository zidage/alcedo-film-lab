"""Measured reflectance datasets and test light sources of step P1.

Input: the source files in build/tmp/p1/sources/ (see sources.json) and the P0 CIE tables in
build/tmp/p0/sources/.
Output: functions that return the reflectances of each dataset on the model grid (360-840 nm,
1 nm, the grid of the P0 evaluator) and the relative spectral power of the test light sources.

Step: P1 (spectral input), ROADMAP section 8. Rules that change a measured value (each one is
named in the function that applies it and in the P1 report):

- 'reflectance_unit': ISSA gives percent; the values are divided by 100.
- 'reflectance_resampling': linear interpolation of the published samples onto 1 nm.
- 'reflectance_outside_measured_range': the value at the nearest measured end (hold). This rule
  changes the 360-400 nm part of the Gutierrez spectra and the 360-380 nm and 780-840 nm parts of
  the rawtoaces and ISSA spectra. The Portra 400 yellow-forming layer is sensitive from 380 nm,
  so the rule is part of the test spectrum of those datasets; truth and reconstruction use the
  same extended spectrum.
- 'issa_formula_rows': ISSA rows whose spectral cells are spreadsheet formulas (averages of other
  records) are not measurements and are not used.
- 'reflectance_plausibility': a record is rejected when any value in 380-780 nm is below
  -0.02 or above 1.5, or when a USGS value in 360-840 nm is missing (the USGS missing-value
  marker -1.23e34). Values from -0.02 to 0 are set to 0.
- 'light_source_resampling': the 5 nm CIE tables are interpolated linearly onto 1 nm and are zero
  outside 380-780 nm (their published range).
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_DIR = REPO_ROOT / "build" / "tmp" / "p1" / "sources"

GRID_NM = np.arange(360.0, 840.0 + 0.5, 1.0)  # the 1 nm working nodes of the P0 evaluator
PLAUSIBLE_RANGE = (-0.02, 1.5)
PLAUSIBILITY_BAND_NM = (380.0, 780.0)
USGS_MISSING_BELOW = -1.0e30


@dataclass
class ReflectanceSet:
    """Reflectances (count, len(GRID_NM)) of one dataset, with the label of each record."""

    name: str
    reflectance: np.ndarray
    labels: list[str]
    categories: list[str]
    measured_range_nm: tuple[float, float]
    rejected: int = 0
    clipped_values: int = 0
    notes: list[str] = field(default_factory=list)


def resample_hold(wavelengths: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Rules 'reflectance_resampling' and 'reflectance_outside_measured_range'."""
    return np.interp(GRID_NM, wavelengths, values)


def plausibility_filter(spectra: np.ndarray, measured_lo: np.ndarray | float) -> tuple[np.ndarray, np.ndarray, int]:
    """Rule 'reflectance_plausibility'. Returns (kept mask, spectra with small negatives at 0,
    count of values set to 0)."""
    band = (GRID_NM >= PLAUSIBILITY_BAND_NM[0]) & (GRID_NM <= PLAUSIBILITY_BAND_NM[1])
    inside = spectra[:, band]
    keep = (inside.min(axis=1) >= PLAUSIBLE_RANGE[0]) & (inside.max(axis=1) <= PLAUSIBLE_RANGE[1])
    clipped = int(((spectra < 0) & keep[:, None]).sum())
    return keep, np.clip(spectra, 0.0, None), clipped


def load_rawtoaces_training() -> ReflectanceSet:
    data = json.loads((SOURCE_DIR / "rawtoaces_training_spectral.json").read_text(encoding="utf-8"))
    table = data["spectral_data"]["data"]["main"]
    wl = np.array(sorted(float(k) for k in table))
    values = np.array([table[f"{w:g}"] for w in wl]).T  # (patches, wavelengths)
    spectra = np.stack([resample_hold(wl, v) for v in values])
    keep, spectra, clipped = plausibility_filter(spectra, wl[0])
    labels = [f"patch{k + 1}" for k in range(len(values))]
    zero_380 = int(np.sum((values[:, 0] == 0.0) & (values[:, 1] > 0.02)))
    s = ReflectanceSet("rawtoaces_190", spectra[keep], [l for l, k in zip(labels, keep) if k],
                       ["training patch"] * int(keep.sum()), (wl[0], wl[-1]), int((~keep).sum()), clipped)
    s.notes.append(f"{zero_380} patches have exactly 0 at 380 nm and more than 0.02 at 385 nm; kept as published")
    return s


def load_gutierrez() -> ReflectanceSet:
    spectra, labels, cats = [], [], []
    wl = None
    for part in ("Plants", "Animals", "Stones"):
        with open(SOURCE_DIR / f"gutierrez_Database_{part}.csv", encoding="latin-1", newline="") as stream:
            rows = list(csv.reader(stream, delimiter=";"))
        header = rows[1]
        start = header.index("400")
        columns = [k for k in range(start, len(header)) if header[k].strip()]
        wl = np.array([float(header[k]) for k in columns])
        for row in rows[2:]:
            if not row or not row[0].strip():
                continue
            values = np.array([float(row[k].replace(",", ".")) for k in columns])
            spectra.append(resample_hold(wl, values))
            labels.append(row[0])
            cats.append(f"{part}: {row[4]}")
    spectra = np.array(spectra)
    keep, spectra, clipped = plausibility_filter(spectra, wl[0])
    return ReflectanceSet("gutierrez_natural", spectra[keep], [l for l, k in zip(labels, keep) if k],
                          [c for c, k in zip(cats, keep) if k], (wl[0], wl[-1]), int((~keep).sum()), clipped)


def load_issa() -> ReflectanceSet:
    import openpyxl

    workbook = openpyxl.load_workbook(SOURCE_DIR / "ISSA_17_Jan_2025_Yan_Lu.xlsx", read_only=True)
    sheet = workbook["ISSA"]
    rows = sheet.iter_rows(values_only=True)
    header_wl = None
    spectra, labels, cats, lows, highs = [], [], [], [], []
    formula_rows = 0
    for row in rows:
        if header_wl is None:
            if row[0] == "A" and row[1] == "B" and row[13] == 360:
                header_wl = np.array([float(v) for v in row[13:56]])
            continue
        if not isinstance(row[0], (int, float)):
            continue
        if any(isinstance(v, str) and v.startswith("=") for v in row[13:56]):
            formula_rows += 1  # rule 'issa_formula_rows': an average of other records, not a measurement
            continue
        lo, hi = float(row[9]), float(row[10])
        values = np.array([np.nan if v is None else float(v) for v in row[13:56]]) / 100.0  # rule 'reflectance_unit'
        inside = (header_wl >= lo) & (header_wl <= hi) & np.isfinite(values)
        spectra.append(resample_hold(header_wl[inside], values[inside]))
        labels.append(f"record{int(row[0])}_origin{row[1]}_subject{row[2]}")
        cats.append(f"skin: {row[3]}, {row[6]}")
        lows.append(lo)
        highs.append(hi)
    spectra = np.array(spectra)
    keep, spectra, clipped = plausibility_filter(spectra, np.array(lows))
    s = ReflectanceSet("issa_skin", spectra[keep], [l for l, k in zip(labels, keep) if k],
                       [c for c, k in zip(cats, keep) if k], (min(lows), max(highs)), int((~keep).sum()), clipped)
    s.notes.append(f"{formula_rows} rows are spreadsheet formulas (averages of other records) and are not used")
    s.notes.append("measured ranges: " + ", ".join(f"{lo:g}-{hi:g} nm: {n}" for (lo, hi), n in
                                                   zip(*np.unique(np.stack([lows, highs], 1), axis=0, return_counts=True))))
    return s


USGS_CHAPTERS = ("ChapterA_ArtificialMaterials", "ChapterC_Coatings", "ChapterL_Liquids", "ChapterM_Minerals",
                 "ChapterO_OrganicCompounds", "ChapterS_SoilsAndMixtures", "ChapterV_Vegetation")


def load_usgs() -> ReflectanceSet:
    root = "ASCIIdata_splib07b_cvASD/"
    with zipfile.ZipFile(SOURCE_DIR / "ASCIIdata_splib07b_cvASD.zip") as archive:
        def read_column(name: str) -> np.ndarray:
            lines = archive.read(name).decode("latin-1").splitlines()[1:]
            return np.array([float(v) for v in lines if v.strip()])

        wl = 1000.0 * read_column(root + "s07_ASD_Wavelengths_ASD_0.35-2.5_microns_2151_ch.txt")
        band = (wl >= GRID_NM[0] - 1.0) & (wl <= GRID_NM[-1] + 1.0)
        spectra, labels, cats, missing = [], [], [], 0
        for name in sorted(archive.namelist()):
            parts = name.split("/")
            if len(parts) != 3 or parts[1] not in USGS_CHAPTERS or not parts[2].endswith(".txt"):
                continue
            values = read_column(name)
            if np.any(values[band] < USGS_MISSING_BELOW):
                missing += 1
                continue
            spectra.append(resample_hold(wl[band], values[band]))
            labels.append(parts[2][len("s07_ASD_"):-len(".txt")])
            cats.append(parts[1].split("_", 1)[1])
    spectra = np.array(spectra)
    keep, spectra, clipped = plausibility_filter(spectra, wl[0])
    s = ReflectanceSet("usgs_splib07", spectra[keep], [l for l, k in zip(labels, keep) if k],
                       [c for c, k in zip(cats, keep) if k], (350.0, 2500.0), int((~keep).sum()) + missing, clipped)
    s.notes.append(f"{missing} records rejected for missing values in 360-840 nm")
    return s


def load_all_reflectance_sets() -> dict[str, ReflectanceSet]:
    return {s.name: s for s in (load_rawtoaces_training(), load_gutierrez(), load_issa(), load_usgs())}


# --------------------------------------------------------------------------------------------
# Test light sources
# --------------------------------------------------------------------------------------------


def _read_cie_5nm(name: str) -> tuple[np.ndarray, np.ndarray]:
    with open(SOURCE_DIR / name, newline="", encoding="utf-8") as stream:
        rows = np.array([[float(v) for v in row] for row in csv.reader(stream) if row])
    return rows[:, 0], rows[:, 1:]


CIE_TABLE_COLUMNS = {
    "CIE_illum_FLs.csv": ["FL1", "FL2", "FL3", "FL4", "FL5", "FL6", "FL7", "FL8", "FL9", "FL10", "FL11", "FL12"]
                         + [f"FL3.{k}" for k in range(1, 16)],
    "CIE_illum_LEDs.csv": ["LED-B1", "LED-B2", "LED-B3", "LED-B4", "LED-B5", "LED-BH1", "LED-RGB1", "LED-V1", "LED-V2"],
    "CIE_illum_HPs.csv": ["HP1", "HP2", "HP3", "HP4", "HP5"],
}


def cie_light_sources() -> dict[str, np.ndarray]:
    """Relative spectral power of the CIE 015:2018 FL, LED, and HP sources on GRID_NM.

    Rule 'light_source_resampling'. The column names follow CIE 015:2018 tables 10, 11, 12.1
    and the metadata of the FL file; the LED and HP column counts are checked."""
    out = {}
    for name, columns in CIE_TABLE_COLUMNS.items():
        wl, values = _read_cie_5nm(name)
        if values.shape[1] != len(columns):
            raise ValueError(f"{name}: {values.shape[1]} columns, expected {len(columns)}")
        for k, column in enumerate(columns):
            out[column] = np.interp(GRID_NM, wl, values[:, k], left=0.0, right=0.0)
    return out


def read_camera_sensitivity(camera: str) -> np.ndarray:
    """Relative camera spectral sensitivity (3, len(GRID_NM)), R, G, B; zero outside 380-780 nm
    (the published range of the rawtoaces-data files)."""
    data = json.loads((SOURCE_DIR / f"rawtoaces_camera_{camera}_380_780_5.json").read_text(encoding="utf-8"))
    table = data["spectral_data"]["data"]["main"]
    if data["spectral_data"]["index"]["main"] != ["R", "G", "B"]:
        raise ValueError(f"{camera}: unexpected channel index")
    wl = np.array(sorted(float(k) for k in table))
    values = np.array([table[f"{w:g}"] for w in wl]).T
    return np.stack([np.interp(GRID_NM, wl, v, left=0.0, right=0.0) for v in values])


def available_cameras() -> list[str]:
    prefix, suffix = "rawtoaces_camera_", "_380_780_5.json"
    return sorted(p.name[len(prefix):-len(suffix)] for p in SOURCE_DIR.glob(prefix + "*" + suffix))


if __name__ == "__main__":
    for s in load_all_reflectance_sets().values():
        print(s.name, s.reflectance.shape, "rejected", s.rejected, "clipped", s.clipped_values, s.measured_range_nm, s.notes[:1])
    print(sorted(cie_light_sources()))
