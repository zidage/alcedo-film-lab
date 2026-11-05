"""The resources that Alcedo Studio ships for the film print DRT, and the lab values that its host tests compare with.

Input: the profiles, stock_catalog.json, stock_physics.json, and the reflectance table under build/tmp/p2/tables/. Output: build/tmp/p7/product_resources/resources/ (shipped), build/tmp/p7/product_resources/expected/ (tests only), and results/p7_spectral_acceleration/product_resources.json. Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F1.
Machine rule: CPU only, one process, no GPU job.

Each resource is one array file: 8 bytes 'ALCDFILM', a little-endian uint64 header length, a JSON header, then the arrays, each one little-endian, row major, on a boundary of 8 bytes. The header names each array with its type ('f8', 'f4', 'i4', 'i8', 'u1'), its shape, and its offset from the end of the header.

| File | Content |
| manifest.json | Schema version, lab commit, and the file name, size, and SHA-256 of each resource |
| film_stock_bundle.bin | Per negative, per paper, per reversal film, each scene spectrum, and the values that are the same for all stocks. The header holds the catalog names. |
| film_print_setup.bin | The scalar values of each film, print material, and scene light: printer balance, layer gain, printing gain, aim, display matrix; and of each reversal film and scene light: layer gain, display matrix |
| film_reflectance_table.bin | The compact form of the final reflectance table, without rule 'foliage_spectra' since schema 8 (U93), by rule 'compact_reflectance_table' |

Rule 'compact_reflectance_table' (user decision of 2026-11-01): the file holds only the wavelengths where a weight of a negative is not zero, only the u'v' nodes that a read can reach after rule 'spectral_locus_projection', and values rounded to 12 mantissa bits. Each byte of a float32 is in its own plane, so that the compression of the installer finds the repeated high bytes. A node that a read can reach: it is inside the hull, or it is 1 node from such a node, or it is a corner of a cell that the edge of the hull crosses.

The hidden controls of the product have their default values (Film Print DRT Plan, section 1), so each selection has fixed scalar values. Rule 'setup_without_tables': the values come from the methods of FilmPreview with no table build. The checks of this script build the complete FilmPreview for some selections and compare.

| Check | Comparison rule | Limit |
| Setup | Each value of the print setup and of the bundle against the complete FilmPreview, 3 expected selections and 8 random ones: largest absolute difference | 1e-9 |
| Shared values | A value that the bundle holds once (per negative, per paper, per pair) is the same in each selection that uses it: largest absolute difference | 0 |
| Print table | The expected table is the table of the complete FilmPreview, and it is finite | finite |
| Compact table, u'v' | The table from the compact form against the complete table, on the nodes that it keeps, each of the selections of the Setup check: largest relative difference | 2e-4 |
| Compact table, nodes | The removed nodes hold NaN. Layer exposure of photos, a ramp, random colours, and the hull edge, for the same selections, is finite | finite |
| Compact table, display | Final sRGB against the complete table, on the images of the check above except the hull edge, 3 expected and 3 random selections, 8 bit code, per pixel the largest channel difference | largest at most 0.5 |

Reversal films (step P9, ROADMAP U86, Alcedo Studio issue 654). The method 'light_table' of the viewer (scripts/poc/p9_reversal_light_table/reversal_film.py) has no print, so a reversal film has no paper, no printer balance, and no printing gain.
Group 'reversal/<film>/' of the bundle holds the values of the film in the form of group 'negative/', with the record of rule 'removed_dye_record' (the curves rise with exposure) and 'dye_max': the dye amount of a pixel is dye_max - record.
Group 'light_table/' holds the values of rule 'light_table_view' that are the same for all films: the D50 viewing weights, the XYZ scale, the exponent of the dark surround, and the luminance weights of linear Rec. 709 of that rule.
The setup holds per film and scene light the layer gain (rule 'daylight_reversal_balance'), and per film the display matrix of rule 'clear_film_white'. The product builds the light table (65^3 over the record, cube root of XYZ) from these values.
The compact reflectance table keeps the wavelengths of the reversal films too. The checks above run on 3 expected and 4 random reversal selections with ReversalPreview in place of FilmPreview, with the same limits; check 'Compact table, display' runs on the 3 expected and 2 random ones.

Negative Scan (step P14, Alcedo Studio issues 661, 664 and 662): method 'negative_scan' of the viewer (negative_scan.NegativeScanPreview through
Pipeline.negative_scan_model of mvp_pipeline.py) with its defaults: scanner 650, 545 and 450 nm, 40 nm, halogen; primaries 'channels'; stock character 1;
spectral input 'current'. Print material 'negative_scan' selects it for any negative. It replaces all forms of Lab Scan (schema 7 to 9). With the record
a of the negative (the dye amounts), the scanner weights w_i = L S_i on the nodes of the model grid where a band is at least BAND_CUT of its peak, and the
stored values of the negative and the scene light:
    T(a) = log10(sum w_i) - log10(sum w_i 10^-(base + dyes a))     (rule ideal_scanner_bands; a table on the record nodes of the print table, trilinear)
    D = T(a) - D_base                                              (rule base_relative_density; D_base = T(0), the unexposed film)
    x = contrast (D - D_aim) / gamma                               (rule generic_density_inversion)
    x = x + s_auto + exposure_stops log10(2) - (cyan, magenta, yellow)
    E = 0.18 10^x, E_base = 0.18 10^(x at D = 0), E' = 0.18 (E - b E_base) / (0.18 - b E_base), not below 0 (rule black_at_film_base)
E' is linear AP1, shown by OpenDRT with 0.18 as 0.18.
Values:
- 'common/negative_scan_centres_nm' (3: R, G, B), 'common/negative_scan_width_nm' (full width at half maximum), 'common/negative_scan_band_cut',
  'common/negative_scan_lamp_kelvin', 'common/negative_scan_planck_c2_nm_k': the default scanner of rule ideal_scanner_bands. S_i is a Gaussian, L is the
  Planckian radiator lambda^-5 / (exp(c2 / (lambda T)) - 1) ('halogen') or 1 ('equal_energy'). The product builds the weights from these values.
- 'negative/<negative>/scan_base_density' (3, D_base) for the default scanner.
- 'scan_medium/<medium>/gamma' (3): the channel density per log10 exposure of the 18 % grey of the average negative of the medium (the pool of rule
  generic_scan, each stock under its balance light, central difference at 0.09 and 0.36), for the default scanner. Metadata 'negative_scan' holds the
  pool of each medium and the scene light of each pool stock (its balance light), so the product can derive gamma for another scanner (derive_medium).
- The setup holds per negative and scene light 'negative_scan_aim_density' (3, D_aim: rule stock_balance, the D of the 18 % grey under the balance light of
  the stock, with the layer gain of the scene light) and 'negative_scan_light_axis' (3: the change of x of the 18 % grey from T3200 to D65, contrast 1,
  for rule frame_auto_colour), for the default scanner. Both read the stored layer gain and the spectra of the bundle (light/D55, light/T3200, light/D65).
- Metadata 'negative_scan': the id, the name, the default light, the lights, the axis lights, the pools; metadata 'negatives' holds the medium and the
  balance light ('scan_balance_light') of each negative.
The grey records of the stored values use the default inhibition steps of the point form (INHIBITION_STEPS_POINT, 16); the kernels of the product use
rule inhibition_two_steps. A product that derives the values for another scanner must use the same 16 steps.
Scene light 'as_shot' (U92): the scene lights hold a grid of colour temperature, CCT_GRID_MIRED (5 mired from 500 to 70, and 15000 K), named
'CCT<kelvin>', each from film_preview.cct_light (Planckian to 4000 K, CIE daylight from 5000 K, a blend linear in mired between). Metadata
'cct_grid' holds the mired, the kelvin, and the names. The product blends the two nodes around the colour temperature of the RAW decode, linear in
mired: the spectra (each with Y = 1) and the setup values of the light (for Negative Scan D_aim and the light axis). A colour temperature outside the grid
takes the nearest end.
Expected values: scan__<negative>__<light>.bin (the scanner weights, the table T on the record nodes, D_base, D_aim, the light axis, the gamma of the
medium, the layer gain) for SCAN_EXPECTED_SELECTIONS; scan__<negative>__cct<kelvin>.bin (the share of the second node, the blended spectrum, layer gain,
D_aim and light axis) for SCAN_BLEND_SELECTIONS, checked against the model of the blend light (limit 1e-9); scan__scanner_b.bin (the weights of
SCANNER_B, the gamma of each medium derived for it, and D_base, D_aim and the light axis of the negatives of SCAN_EXPECTED_SELECTIONS under 'daylight');
scan__auto.bin (rule frame_auto_colour on two random frames of x, a and b: each frame, its prescan, the light axis, and the shift of each of AUTO_CASES;
frame a takes the near-neutral estimate and frame b the white-patch estimate of rule smaller_cast).
Checks, on 4 random and the expected scan selections, and on the grid:

| Check | Comparison rule | Limit |
| Scan setup | D_base, D_aim, the light axis, gamma, and the layer gain against NegativeScanPreview of the viewer: largest absolute difference | 1e-9 |
| Scan point form | Linear AP1 of the formula above from the stored values against NegativeScanPreview.positive, auto off, contrast, keys and black at their defaults and at other values, on a neutral ramp of -10 to +10 stops and 4096 random colours: largest difference per pixel relative to its largest channel | 1e-9 |
| Scanner table | The table T on 512 random nodes against the direct sum of numpy on the model grid (VirtualScan.scan.apd of the spectral density): largest absolute difference in density | 1e-12 |
| Grid blend, print | The blend of two nodes against the exact light, at the mid-points of CCT_BLEND_CHECKS: 5207 on Kodak 2383 in sRGB, 8 bit code | largest at most 0.5 |
| Grid blend, scan | The same for Negative Scan of four negatives (the blended spectrum and layer gain, the blend of the stored values): linear AP1, values above 2^-10, in stops | largest at most 0.03 stops |
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import struct
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation
from scipy.spatial import ConvexHull

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402


fp = mp.fp
rf = mp.rf
p0 = fp.p0
sr = fp.sr
SCHEMA_VERSION = 10  # 6: the reversal films (step P9); 7: Lab Scan (step P10); 8: the ADX16 scan with the slope match and the colour temperature grid (U92, U93), and no rule foliage_spectra (U93); 9: the generic scan of each medium, rule stock_balance, and rule untimed_axis_academy (U96 to U98, issue 664); 10: Negative Scan (step P14, issue 661) in place of all Lab Scan forms
MAGIC = b"ALCDFILM"
OUTPUT = REPO_ROOT / "build" / "tmp" / "p7" / "product_resources"
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "product_resources.json"
EXPECTED_SELECTIONS = (("kodak_5207", "kodak_2383", "reference"), ("kodak_portra_400", "kodak_endura_premier", "daylight"), ("fuji_eterna_500", "kodak_2383", "street_mixed"), ("kodak_5219", "cine_look", "reference"), ("kodak_5207", "cine_look", "reference"))
RANDOM_CHECKS = 8
REVERSAL_EXPECTED_SELECTIONS = (("fuji_velvia_50", "reference"), ("kodak_ektachrome_e100", "daylight"), ("fuji_provia_100f", "street_mixed"))
REVERSAL_RANDOM_CHECKS = 4
SETUP_LIMIT = 1e-9
MANTISSA_BITS = 12
UV_RELATIVE_LIMIT = 2e-4
DISPLAY_CODE_LIMIT = 0.5
RENDER_PHOTOS = {"se188": "p3/input/se188", "_DSC8148": "baseline/night/_DSC8148_ap1", "digital_ap1": "p5/real_5207/pair/digital_ap1"}
RENDER_RANDOM_SELECTIONS = 3
NEGATIVE_SCAN = {"id": "negative_scan", "name": "Negative Scan"}
SCAN_EXPECTED_SELECTIONS = (("kodak_5207", "reference"), ("kodak_portra_400", "reference"), ("kodak_ektar_100", "reference"), ("kodak_5219", "daylight"))
# Colour temperatures between grid nodes for the expected values of the blend (issue 661): one below and one above 4000 K.
SCAN_BLEND_SELECTIONS = (("kodak_5219", 5650.0), ("kodak_5207", 3100.0))
SCAN_RANDOM_CHECKS = 4
SCAN_MEDIA = ("cine", "photo")  # the pools of rule generic_scan (p10_chart_scan/scan_generic.POOLS)
SCAN_POINT_LIMIT = 1e-9
SCAN_TABLE_LIMIT = 1e-12
SCAN_AXIS_LIGHTS = ("T3200", "D65")  # rule frame_auto_colour: the light axis from T3200 to D65
SCAN_SPECTRA = ("D55", "T3200", "D65")  # the balance lights and the axis lights, in the bundle as light/<name>/spectrum
# A second scanner for the expected values of a scanner change (issue 661: gamma derived again for a second scanner setting).
SCANNER_B = {"neg_scan_red_nm": 630.0, "neg_scan_green_nm": 530.0, "neg_scan_blue_nm": 460.0, "neg_scan_width_nm": 60.0, "neg_scan_light": "equal_energy"}
# Point form check: rendering settings other than the defaults (auto stays off: the auto shift has its own check and file).
SCAN_POINT_RENDERINGS = ({}, {"neg_scan_contrast": 1.2, "neg_scan_exposure_stops": -0.75, "neg_scan_cyan": 0.05, "neg_scan_magenta": -0.03, "neg_scan_yellow": 0.11, "neg_scan_black": 0.6},
                         {"neg_scan_contrast": 0.7, "neg_scan_black": 0.0})
# Rule frame_auto_colour on a random frame (scan__auto.bin): mode, strength, density strength.
AUTO_CASES = (("neutral", 0.8, 0.0), ("warm", 0.8, 0.0), ("cool", 0.8, 0.0), ("neutral", 0.35, 0.5), ("neutral", 1.0, 1.0))
AUTO_FRAME_SHAPE = (257, 391)  # not a multiple of the prescan, so the area reduction has partial boxes
# 5 mired from 500 to 70, and 15000 K. A step of 10 mired gave up to 0.0115 stops between the blend and the exact light (5128 K, Portra 400, LAD aim on).
CCT_GRID_MIRED = (*(float(m) for m in range(500, 69, -5)), 1e6 / 15000.0)
CCT_BLEND_CHECKS = (497.5, 337.5, 252.5, 247.5, 222.5, 202.5, 197.5, 102.5, 72.5)  # mired, mid-points of grid segments
CCT_BLEND_LIMIT = 0.5  # print, 8 bit sRGB code
# Scan: linear AP1 in stops for values above 2^-10, the form of the scan tests. The Lab Scan forms of schema 8 and 9 had up to 0.022 stops, so the limit
# stays 0.03 stops.
CCT_BLEND_STOPS_LIMIT = 0.03
CCT_BLEND_FLOOR = 2.0 ** -10
CCT_BLEND_SCAN_NEGATIVES = ("kodak_5207", "kodak_portra_400", "kodak_ektar_100", "kodak_5219")


def write_arrays(path: Path, arrays: dict[str, np.ndarray], metadata: dict | None = None) -> None:
    """The array file of the header of this script. The bytes depend only on the input values."""
    types = {"float64": "f8", "float32": "f4", "int32": "i4", "int64": "i8", "uint8": "u1"}
    index, blobs, offset = {}, [], 0
    for name in sorted(arrays):
        array = np.asarray(arrays[name])
        if array.dtype.name not in types:
            raise TypeError(f"{name}: type {array.dtype.name} has no form in the array file")
        data = array.astype(array.dtype.newbyteorder("<")).tobytes(order="C")
        index[name] = {"type": types[array.dtype.name], "shape": list(array.shape), "offset": offset}
        padding = -len(data) % 8
        blobs.append(data + b"\0" * padding)
        offset += len(data) + padding
    header = json.dumps({"schema_version": SCHEMA_VERSION, "metadata": metadata or {}, "arrays": index}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    header += b" " * (-(len(MAGIC) + 8 + len(header)) % 8)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(MAGIC + struct.pack("<Q", len(header)) + header)
        for blob in blobs:
            stream.write(blob)


def read_arrays(path: Path) -> tuple[dict[str, np.ndarray], dict]:
    """The arrays and the metadata of a file of write_arrays."""
    data = path.read_bytes()
    if data[:8] != MAGIC:
        raise ValueError(f"{path}: not an array file")
    length = struct.unpack("<Q", data[8:16])[0]
    header = json.loads(data[16:16 + length])
    start = 16 + length
    arrays = {name: np.frombuffer(data, dtype=np.dtype("<" + entry["type"]), count=int(np.prod(entry["shape"], dtype=np.int64)), offset=start + entry["offset"]).reshape(entry["shape"])
              for name, entry in header["arrays"].items()}
    return arrays, header["metadata"]


def read_scan_resources(output: Path = OUTPUT) -> tuple[dict[str, np.ndarray], dict]:
    """The setup and the bundle metadata of the resources of an earlier run, for the scan values of the expected scripts."""
    resources = output / "resources"
    setup, _ = read_arrays(resources / "film_print_setup.bin")
    _, metadata = read_arrays(resources / "film_stock_bundle.bin")
    return setup, metadata


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def lab_commit() -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT), "describe", "--always", "--dirty", "--abbrev=40"], capture_output=True, text=True, check=True).stdout.strip()


def scalar(value: float) -> np.ndarray:
    return np.array(float(value), dtype=np.float64)


def uniform_curves(curves: list) -> dict[str, np.ndarray]:
    """Curves of different lengths on one log H step, in the form of film_tables::PaperCurves."""
    step = float(curves[0].log_h[1] - curves[0].log_h[0])
    for curve in curves:
        if not np.allclose(np.diff(curve.log_h), step, atol=1e-9):
            raise ValueError("the product needs characteristic curves on one uniform log H step")
    length = max(len(c.density) for c in curves)
    return {"curve_density": np.stack([np.pad(c.density, (0, length - len(c.density)), mode="edge") for c in curves]).astype(np.float64),
            "curve_lengths": np.array([len(c.density) for c in curves], dtype=np.int64),
            "curve_log_h_start": np.array([c.log_h[0] for c in curves], dtype=np.float64),
            "curve_log_h_step": scalar(step)}


def negative_arrays(model: fp.FilmPreview) -> dict[str, np.ndarray]:
    """The values that depend on the negative only. exposure_weights: Q = radiance @ exposure_weights.T, for a radiance in the relative units of Colorimetry.layer_exposure."""
    f, c = model.film, model.c
    erg_per_unit = c.lux_seconds_per_y / p0.LUMINOUS_EFFICACY_LM_PER_W * p0.ERG_PER_CM2_PER_J_PER_M2
    arrays = {"base": f.negative_dmin, "dyes": f.negative_dyes, "exposure_weights": f.w_negative * erg_per_unit, "criterion_log_h": f.negative_criterion_log_h,
              "density_grid_start": np.array([c_.density.min() for c_ in model.negative_curves]), "density_grid_stop": np.array([c_.density.max() for c_ in model.negative_curves]),
              "layer_spread_um": np.array(model.options.layer_spread_um, dtype=np.float64), "negative_grade": scalar(1.0 if model.options.negative_profile in mp.NEGATIVE_GRADE_STOCKS else 0.0), **uniform_curves(model.negative_curves)}
    if model.inhibition is not None:
        i = model.inhibition
        arrays.update(inhibition_k=i["k"], inhibition_image_k=i["k_image"], inhibition_start=i["start"], inhibition_free=i["free"], inhibition_lengths=np.asarray(i["lengths"], dtype=np.int64), inhibition_step=scalar(i["step"]))
    return {name: np.asarray(value, dtype=np.int64 if value.dtype.kind == "i" else np.float64) for name, value in arrays.items()}


def paper_arrays(model: fp.FilmPreview) -> dict[str, np.ndarray]:
    """The values that depend on the paper and its viewing light only."""
    f = model.film
    weights = f.w_viewing[f.viewing_name]
    start = np.array([c.density.min() for c in model.paper_curves])
    arrays = {"base": f.paper_base, "dyes": f.paper_dyes, "printing_weights": f.w_printing, "status_a_weights": f.w_status_a, "viewing_weights": weights,
              "xyz_scale": scalar(100.0 / weights[1].sum()), "clear_luminance": scalar(model.print_dmin_xyz()[1]), "surround_exponent": scalar(model.options.surround_exponent), "cinema_look": scalar(1.0 if model.options.cinema_look else 0.0), "white_xyz": f.white_xyz(), "status_axis_start": start, "status_axis_range": np.array([c.density.max() for c in model.paper_curves]) - start,
              **uniform_curves(model.paper_curves)}
    return {name: np.asarray(value, dtype=np.int64 if value.dtype.kind == "i" else np.float64) for name, value in arrays.items()}


def reversal_arrays(model: rf.ReversalPreview) -> dict[str, np.ndarray]:
    """The values that depend on the reversal film only, in the form of negative_arrays, and dye_max of rule 'removed_dye_record'."""
    f, c = model.film, model.c
    erg_per_unit = c.lux_seconds_per_y / p0.LUMINOUS_EFFICACY_LM_PER_W * p0.ERG_PER_CM2_PER_J_PER_M2
    arrays = {"base": f.negative_dmin, "dyes": f.negative_dyes, "exposure_weights": f.w_negative * erg_per_unit, "criterion_log_h": f.negative_criterion_log_h, "dye_max": model.dye_max,
              "density_grid_start": np.array([g[0] for g in model.density_grid]), "density_grid_stop": np.array([g[-1] for g in model.density_grid]),
              "clear_luminance": scalar(model.print_dmin_xyz()[1]), "layer_spread_um": np.array(model.options.layer_spread_um, dtype=np.float64), **uniform_curves(model.negative_curves)}
    if model.inhibition is not None:
        i = model.inhibition
        arrays.update(inhibition_k=i["k"], inhibition_image_k=i["k_image"], inhibition_start=i["start"], inhibition_free=i["free"], inhibition_lengths=np.asarray(i["lengths"], dtype=np.int64), inhibition_step=scalar(i["step"]))
    return {name: np.asarray(value, dtype=np.int64 if value.dtype.kind == "i" else np.float64) for name, value in arrays.items()}


def light_table_arrays(model: rf.ReversalPreview) -> dict[str, np.ndarray]:
    """The values of rule 'light_table_view' that are the same for all reversal films."""
    f = model.film
    weights = f.w_viewing[f.viewing_name]
    return {"light_table/viewing_weights": np.asarray(weights, dtype=np.float64), "light_table/xyz_scale": scalar(100.0 / weights[1].sum()), "light_table/surround_exponent": scalar(model.options.surround_exponent),
            "light_table/display_luminance": np.asarray(rf.LUMINANCE, dtype=np.float64), "light_table/viewing_cct_k": scalar(model.options.viewing_cct_k)}


def reversal_options(film: str, light: str) -> fp.FilmOptions:
    settings = mp.RenderSettings(method="light_table", reversal=film, scene_light=light)
    settings.validate()
    return mp.light_table_options(settings)


def collect_reversals(bundle: dict[str, np.ndarray], reference_options: fp.FilmOptions, lights: list[str], spectrum_names: list[str]) -> tuple[dict[str, np.ndarray], dict]:
    """The values of the reversal films. Adds the groups 'reversal/' and 'light_table/', and new scene spectra, to the bundle. Returns the setup arrays and the metadata."""
    films = sorted(mp.CATALOG["reversals"])
    layer_gain = np.zeros((len(films), len(lights), 3))
    to_display = np.zeros((len(films), 3, 3))
    spectrum_index = np.zeros((len(films), len(lights)), dtype=np.int32)
    for r, film in enumerate(films):
        options = reversal_options(film, lights[0])
        for field in FIXED_FIELDS:
            if getattr(options, field) != getattr(reference_options, field):
                raise ValueError(f"reversal film {film}: {field} is not one value for all stocks")
        model = rf.ReversalPreview(options)
        bundle.update({f"reversal/{film}/{name}": value for name, value in reversal_arrays(model).items()})
        shared = light_table_arrays(model)
        if "light_table/viewing_weights" in bundle:
            require_same(film, {k: bundle[k] for k in shared}, shared)
        bundle.update(shared)
        to_display[r] = model.xyz_to_display
        for l, light in enumerate(lights):
            light_options = reversal_options(film, light)
            # The steps of ReversalPreview.__init__ that depend on the scene light, as apply_light does for a negative.
            model.options = replace(light_options, enlarger_flare=0.0)
            model.scene_spectrum = model.light(light_options.scene_light)
            model.layer_gain = model._camera_filter()
            layer_gain[r, l] = model.layer_gain
            name = light_options.scene_light
            if name not in spectrum_names:
                spectrum_names.append(name)
                bundle[f"light/{name}/spectrum"] = np.asarray(model.scene_spectrum, dtype=np.float64)
            elif not np.array_equal(bundle[f"light/{name}/spectrum"], model.scene_spectrum):
                raise ValueError(f"{name}: the scene spectrum depends on the stock")
            spectrum_index[r, l] = spectrum_names.index(name)
        print(f"reversal {film}: {r + 1} of {len(films)}", flush=True)
    metadata = {"reversal_films": {k: {"name": mp.CATALOG["reversals"][k]["name"]} for k in films}, "reversal_list_order": list(mp.REVERSAL_ORDER)}
    return {"reversal_layer_gain": layer_gain, "reversal_xyz_to_display": to_display, "reversal_scene_spectrum_index": spectrum_index}, metadata


def cct_light_name(mired: float) -> str:
    return f"CCT{round(1e6 / mired)}"


CCT_LIGHTS = tuple(cct_light_name(m) for m in CCT_GRID_MIRED)


def register_lights() -> None:
    """The grid lights are names of rule 'light_from_raw_white' (mvp_pipeline.is_light_name); this adds them to the viewer list once."""
    mp.SCENE_LIGHTS = tuple(dict.fromkeys((*mp.SCENE_LIGHTS, *CCT_LIGHTS)))


def product_lights() -> list[str]:
    """The scene lights of the resources: the named lights of the viewer (not 'as_shot', which the product resolves), then the grid."""
    register_lights()
    return [light for light in mp.SCENE_LIGHTS if light != mp.AS_SHOT and light not in CCT_LIGHTS] + list(CCT_LIGHTS)


def grid_blend(kelvin: float) -> tuple[str, str, float]:
    """The two grid nodes around a colour temperature and the share of the second, linear in mired (issue 661)."""
    mired = 1e6 / kelvin
    nodes = [1e6 / round(1e6 / m) for m in CCT_GRID_MIRED]  # the mired of the rounded kelvin of each node
    for k in range(len(nodes) - 1):
        if nodes[k] >= mired >= nodes[k + 1]:
            return cct_light_name(CCT_GRID_MIRED[k]), cct_light_name(CCT_GRID_MIRED[k + 1]), (nodes[k] - mired) / (nodes[k] - nodes[k + 1])
    raise ValueError(f"{kelvin} K is outside the grid")


def blend_light(kelvin: float) -> tuple[str, str, str, float]:
    """A scene light that is the blend of two grid nodes (each Y = 1, so the weights are the shares of fp.SCENE_PRESETS). Returns (name, a, b, w)."""
    a, b, w = grid_blend(kelvin)
    name = f"blend_{round(kelvin)}"
    fp.SCENE_PRESETS[name] = ((a, 1.0 - w), (b, w))
    register_lights()
    mp.SCENE_LIGHTS = tuple(dict.fromkeys((*mp.SCENE_LIGHTS, name)))
    return name, a, b, w


PIPELINE = mp.Pipeline()  # one viewer pipeline: it keeps the gamma of each medium and scanner
ns = mp.negative_scan  # step P14
# The defaults of the product form (issue 661). A viewer default that differs stops the script.
SCAN_FORM = {"stock_character": 1.0, "spectral_input": "current", "neg_scan_primaries": "channels", "neg_scan_auto": "off", "neg_scan_contrast": 1.0,
             "neg_scan_exposure_stops": 0.0, "neg_scan_cyan": 0.0, "neg_scan_magenta": 0.0, "neg_scan_yellow": 0.0, "neg_scan_black": 1.0,
             "neg_scan_auto_strength": 0.8, "neg_scan_auto_density": 0.0}


def scan_settings(negative: str, light: str, **values) -> "mp.RenderSettings":
    """The settings of method 'negative_scan' of the viewer with the defaults of the other controls, and @p values."""
    register_lights()
    default = mp.RenderSettings(negative=negative, method="negative_scan", scene_light=light)
    for name, value in SCAN_FORM.items():
        if getattr(default, name) != value:
            raise ValueError(f"the viewer default {name} = {getattr(default, name)!r} of method 'negative_scan' is not the form of the product ({value!r})")
    if Pipeline_scanner(default) != ns.ScannerSetup():
        raise ValueError("the default scanner of the viewer is not negative_scan.ScannerSetup()")
    settings = replace(default, **values)
    settings.validate()
    return settings


def Pipeline_scanner(settings: "mp.RenderSettings") -> "ns.ScannerSetup":
    return mp.Pipeline.scanner_setup(settings)


def scan_read(negative: str, light: str, **scanner) -> "ns.VirtualScan":
    """Part 1 of Negative Scan for one negative, with no cache: the options of Pipeline.negative_scan_model."""
    settings = scan_settings(negative, light, **scanner)
    negative_only = replace(settings, **{c.name: getattr(mp.RenderSettings(), c.name) for c in mp.CONTROLS if "negative_scan" not in c.methods})
    return ns.VirtualScan(mp.film_options(negative_only, mp.SCAN_CARRIER_PRINT), Pipeline_scanner(settings))


def scan_model(negative: str, light: str, **values) -> "ns.NegativeScanPreview":
    """Negative Scan of issue 661: method 'negative_scan' of the viewer (Pipeline.negative_scan_model). The cache of the pipeline is cleared after each
    call, so the memory stays bounded; the gamma of each medium stays."""
    model = PIPELINE.negative_scan_model(scan_settings(negative, light, **values))
    PIPELINE._models.clear()
    return model


def medium_of(negative: str) -> str:
    medium = str(mp.CATALOG["negatives"][negative].get("medium", "")).lower()
    if medium not in SCAN_MEDIA:
        raise ValueError(f"negative {negative} has no medium of rule generic_scan (medium {medium!r})")
    return medium


def scan_generic():
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p10_chart_scan"))
    import scan_generic as module  # step P10, U98: the pools

    return module


def pool_scene_light(stock: str) -> str:
    """The scene light of a pool stock in Pipeline.negative_scan_medium: its balance light, as a product light name."""
    return "tungsten" if mp.CATALOG["negatives"][stock].get("exposure_kelvin", 5500) < 4500 else "daylight"


def balance_of(negative: str) -> str:
    return ns.balance_light_name(mp.CATALOG["negatives"][negative])


def medium_gamma(medium: str, **scanner) -> np.ndarray:
    """Rule 'generic_density_inversion': gamma of a medium for a scanner, from the viewer (Pipeline.negative_scan_medium, lab derive_medium)."""
    stock = scan_generic().POOLS[medium][0]
    return np.asarray(PIPELINE.negative_scan_medium(scan_settings(stock, pool_scene_light(stock), **scanner))["gamma"], dtype=np.float64)


def scan_grey(read: "ns.VirtualScan", gain: np.ndarray, spectrum: np.ndarray, value: float = 0.18) -> np.ndarray:
    """D of a neutral of @p value under @p spectrum with the layer gain @p gain: VirtualScan.grey_density with a stored gain and spectrum."""
    n = read.negative
    q = gain * n.c.layer_exposure(value * spectrum)
    return read.scan.table_apd(n.negative_density(q[None])[0])[0] - read.base


def scan_light_values(read: "ns.VirtualScan", gain: np.ndarray, gamma: np.ndarray, spectra: dict[str, np.ndarray], balance: str) -> dict[str, np.ndarray]:
    """D_aim and the light axis of one negative and scene light, as NegativeScanPreview computes them, from the stored layer gain and spectra."""
    aim = scan_grey(read, gain, spectra[balance])
    axis = (scan_grey(read, gain, spectra[SCAN_AXIS_LIGHTS[1]]) - scan_grey(read, gain, spectra[SCAN_AXIS_LIGHTS[0]])) / gamma
    return {"negative_scan_aim_density": aim, "negative_scan_light_axis": axis}


SCAN_SETUP_NAMES = ("negative_scan_aim_density", "negative_scan_light_axis")


def scanner_arrays(setup: "ns.ScannerSetup") -> dict[str, np.ndarray]:
    """The weights w_i = L S_i of a scanner and the index of their first node on the model grid."""
    nodes, weights = setup.responsivities()
    return {"first_node": np.array(int(np.searchsorted(ns.MODEL_GRID_NM, nodes[0])), dtype=np.int64), "weights": np.asarray(weights, dtype=np.float64)}


def collect_scan(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], negatives: list[str], lights: list[str], spectrum_names: list[str]) -> tuple[dict[str, np.ndarray], dict]:
    """The values of Negative Scan (issue 661). One VirtualScan per negative builds the scanner table, which does not depend on the light; the values of
    each light read it with the stored layer gain (scan_light_values). Adds the scanner setup, the base densities, the gamma of each medium, and the spectra
    of the balance and axis lights to the bundle."""
    if not np.array_equal(bundle["common/wavelengths_nm"], ns.MODEL_GRID_NM):
        raise ValueError("the wavelengths of the bundle are not the model grid of negative_scan.py")
    default = ns.ScannerSetup()
    bundle.update({"common/negative_scan_centres_nm": np.asarray(default.centres_nm, dtype=np.float64), "common/negative_scan_width_nm": scalar(default.width_nm),
                   "common/negative_scan_band_cut": scalar(ns.BAND_CUT), "common/negative_scan_lamp_kelvin": scalar(3200.0), "common/negative_scan_planck_c2_nm_k": scalar(1.4388e7)})
    # The weights of the stored setup are those of ScannerSetup.responsivities; the product builds them from the values above.
    probe = scanner_arrays(default)
    nodes = ns.MODEL_GRID_NM[int(probe["first_node"]):int(probe["first_node"]) + probe["weights"].shape[1]]
    sigma = default.width_nm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    bands = np.stack([np.exp(-0.5 * ((nodes - c) / sigma) ** 2) for c in default.centres_nm])
    lamp = nodes ** -5.0 / np.expm1(float(bundle["common/negative_scan_planck_c2_nm_k"]) / (nodes * float(bundle["common/negative_scan_lamp_kelvin"])))
    if not np.array_equal(np.where(bands >= ns.BAND_CUT, bands, 0.0) * lamp, probe["weights"]):
        raise ValueError("the stored scanner values do not give the weights of ScannerSetup.responsivities")
    started = time.perf_counter()
    reference = scan_read(negatives[0], lights[0])
    for name in SCAN_SPECTRA:
        spectrum = np.asarray(reference.negative.light(name), dtype=np.float64)
        key = f"light/{name}/spectrum"
        if key in bundle:
            if not np.array_equal(bundle[key], spectrum):
                raise ValueError(f"{key}: the stored spectrum differs from FilmPreview.light")
        else:
            bundle[key] = spectrum
            spectrum_names.append(name)
    spectra = {name: bundle[f"light/{name}/spectrum"] for name in SCAN_SPECTRA}
    gamma = {}
    for medium in SCAN_MEDIA:
        gamma[medium] = medium_gamma(medium)
        bundle[f"scan_medium/{medium}/gamma"] = gamma[medium]
        print(f"scan medium {medium}: gamma {gamma[medium]}, {time.perf_counter() - started:.0f} s", flush=True)
    values = {name: np.zeros((len(negatives), len(lights), 3)) for name in SCAN_SETUP_NAMES}
    for n, negative in enumerate(negatives):
        read = scan_read(negative, lights[0])
        bundle[f"negative/{negative}/scan_base_density"] = np.asarray(read.base, dtype=np.float64)
        for l in range(len(lights)):
            light_values = scan_light_values(read, setup["layer_gain"][n, l], gamma[medium_of(negative)], spectra, balance_of(negative))
            for name in SCAN_SETUP_NAMES:
                values[name][n, l] = light_values[name]
        print(f"scan {negative}: {n + 1} of {len(negatives)}, {time.perf_counter() - started:.0f} s", flush=True)
    grid = {"mired": [1e6 / round(1e6 / m) for m in CCT_GRID_MIRED], "kelvin": [round(1e6 / m) for m in CCT_GRID_MIRED], "lights": list(CCT_LIGHTS)}
    pools = {medium: {"pool": list(scan_generic().POOLS[medium]), "pool_scene_lights": [pool_scene_light(s) for s in scan_generic().POOLS[medium]]} for medium in SCAN_MEDIA}
    metadata = {"negative_scan": {**NEGATIVE_SCAN, "light": default.light, "lights": list(ns.LIGHTS), "axis_lights": list(SCAN_AXIS_LIGHTS), "media": pools},
                "cct_grid": grid, "scan_media": list(SCAN_MEDIA)}
    return values, metadata


def stored_scan(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, negative: str, light: str) -> dict[str, np.ndarray]:
    n, l = sorted(metadata["negatives"]).index(negative), metadata["scene_lights"].index(light)
    medium = metadata["negatives"][negative]["medium"]
    return {"base": bundle[f"negative/{negative}/scan_base_density"], "gamma": bundle[f"scan_medium/{medium}/gamma"], "layer_gain": setup["layer_gain"][n, l],
            **{name: setup[name][n, l] for name in SCAN_SETUP_NAMES}}


def scan_point_form(model: "ns.NegativeScanPreview", stored: dict[str, np.ndarray], rendering: "ns.RenderingSetup", ap1: np.ndarray) -> np.ndarray:
    """Check 'Scan point form': linear AP1 of the formula of the header from the stored values. The record and the table come from the model."""
    record, _ = model.negative.negative_image(np.ascontiguousarray(ap1[None], dtype=np.float32))
    d = model.read.scan.table_apd(record)[0] - stored["base"]
    shift = rendering.exposure_stops * np.log10(2.0) - np.array([rendering.cyan, rendering.magenta, rendering.yellow])
    x = rendering.contrast * (d - stored["negative_scan_aim_density"]) / stored["gamma"] + shift
    x_base = rendering.contrast * (0.0 - stored["negative_scan_aim_density"]) / stored["gamma"] + shift
    e, e_base = 0.18 * 10.0 ** x, 0.18 * 10.0 ** x_base
    b = rendering.black
    return np.maximum(0.18 * (e - b * e_base) / (0.18 - b * e_base), 0.0)


def check_scan(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, selection: tuple[str, str], images: dict[str, np.ndarray]) -> tuple["ns.NegativeScanPreview", dict]:
    """Checks 'Scan setup', 'Scan point form' and 'Scanner table' on one selection, against the viewer."""
    negative, light = selection
    stored = stored_scan(bundle, setup, metadata, negative, light)
    model = scan_model(negative, light)
    pairs = [(model.read.base, stored["base"]), (model.aim, stored["negative_scan_aim_density"]), (model.light_axis, stored["negative_scan_light_axis"]),
             (model.gamma, stored["gamma"]), (np.asarray(model.negative.layer_gain), stored["layer_gain"])]
    largest = max(float(np.abs(np.asarray(a) - np.asarray(b)).max()) for a, b in pairs)
    if largest > SETUP_LIMIT:
        raise ValueError(f"scan {selection}: the stored values differ from the viewer by {largest:.3g}")
    point = {}
    for index, values in enumerate(SCAN_POINT_RENDERINGS):
        rendering = PIPELINE.negative_scan_rendering(scan_settings(negative, light, **values))
        model.set_rendering(rendering)
        for name, ap1 in images.items():
            record, _ = model.negative.negative_image(np.ascontiguousarray(ap1[None], dtype=np.float32))
            reference, _ = model.positive(model.read.density(record)[0], spatial=False)
            formula = scan_point_form(model, stored, rendering, ap1)
            scale = np.maximum(np.abs(reference).max(axis=-1, keepdims=True), 1e-12)
            point[f"{name}, rendering {index}"] = float((np.abs(formula - reference) / scale).max())
    if max(point.values()) > SCAN_POINT_LIMIT:
        raise ValueError(f"scan {selection}: the formula of issue 661 differs from the viewer by {point}")
    # The table on its nodes against the direct sum of numpy on the model grid.
    film = model.negative.film
    grid = model.negative.density_grid
    rng = np.random.default_rng(20261105)
    index = rng.integers(0, len(grid[0]), size=(512, 3))
    amounts = np.stack([np.asarray(grid[k])[index[:, k]] for k in range(3)], axis=-1)
    direct = model.read.scan.apd(film.negative_dmin[None] + amounts @ film.negative_dyes)
    table = model.read.scan.table[index[:, 0], index[:, 1], index[:, 2]]
    table_difference = float(np.abs(direct - table).max())
    if table_difference > SCAN_TABLE_LIMIT:
        raise ValueError(f"scan {selection}: the scanner table differs from the direct sum by {table_difference:.3g} at its nodes")
    return model, {"setup": largest, "point_form_largest_relative": point, "table_nodes_largest": table_difference}


def scan_blend_model(negative: str, kelvin: float, **values) -> "ns.NegativeScanPreview":
    """Negative Scan at a colour temperature between grid nodes: the blended spectrum and layer gain (the light of the model). D_aim and the light axis of
    the model are those of the blend light; the product blends the stored values of the two nodes, and the expected files check that they agree."""
    name, _, _, _ = blend_light(kelvin)
    return scan_model(negative, name, **values)


def blended_scan(setup: dict[str, np.ndarray], metadata: dict, negative: str, kelvin: float) -> tuple[dict[str, np.ndarray], str, str, float]:
    _, a, b, w = blend_light(kelvin)
    n = sorted(metadata["negatives"]).index(negative)
    la, lb = metadata["scene_lights"].index(a), metadata["scene_lights"].index(b)
    return {name: (1.0 - w) * setup[name][n, la] + w * setup[name][n, lb] for name in (*SCAN_SETUP_NAMES, "layer_gain")}, a, b, w


SCAN_DISPLAY_LIGHTS = ("reference", "daylight", *(kelvin for _, kelvin in SCAN_BLEND_SELECTIONS))  # the lights of the expected values of the scan form (issue 661)


def scan_light_label(light: str | float) -> str:
    return light if isinstance(light, str) else f"cct{round(light)}"


def scan_expected_model(negative: str, light: str | float, **values) -> "ns.NegativeScanPreview":
    """A named light of the resources (the viewer), or a colour temperature between grid nodes in the blend form of the product."""
    return scan_model(negative, light, **values) if isinstance(light, str) else scan_blend_model(negative, light, **values)


def prescan_shape(rows: int, columns: int) -> tuple[int, int]:
    """The shape (rows, columns) of negative_scan.reduce_frame of a frame."""
    scale = ns.AUTO_LONG_EDGE / max(rows, columns)
    if scale >= 1.0:
        return rows, columns
    return max(1, round(rows * scale)), max(1, round(columns * scale))


def scan_linear(model: "ns.NegativeScanPreview", frame: np.ndarray, auto: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Linear AP1 of Negative Scan before the display (stage e) of a frame (rows, columns, 3), with auto colour @p auto and the other rendering
    controls at their defaults. The frame is the frame of the product render, so a ramp or a chart of one row gets the shift of that row.
    Returns the linear AP1, the auto shift (3), and the prescan (rows', columns', 3)."""
    model.set_rendering(replace(model.rendering, auto=auto))
    record, _ = model.negative.negative_image(np.ascontiguousarray(frame, dtype=np.float32))
    density = model.read.density(record)
    x = model.positive_log(density)
    shift, _ = ns.auto_colour_shift(x, model.light_axis, auto, model.rendering.auto_strength, model.rendering.auto_density)
    prescan = ns.reduce_frame(x).reshape(*prescan_shape(*x.shape[:2]), 3)
    linear, _ = model.positive(density, spatial=True)
    return np.asarray(linear, dtype=np.float32), np.asarray(shift, dtype=np.float64), np.asarray(prescan, dtype=np.float64)


def check_grid_blend(images: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict) -> dict:
    """Check 'Grid blend': the blend of two nodes against the exact light at mid-points of grid segments."""
    ap1 = np.concatenate(list(images.values()))[None].astype(np.float32)
    out = {}
    for mid in CCT_BLEND_CHECKS:
        kelvin = 1e6 / mid
        exact = f"CCT{round(kelvin)}"
        register_lights()
        mp.SCENE_LIGHTS = tuple(dict.fromkeys((*mp.SCENE_LIGHTS, exact)))
        name, a, b, w = blend_light(kelvin)
        row = {}
        print_options = {light: mp.film_options(mp.RenderSettings(negative="kodak_5207", print_material="kodak_2383", scene_light=light)) for light in (exact, a, b, name)}
        exact_print, blend_print = fp.FilmPreview(print_options[exact]), fp.FilmPreview(print_options[name])
        blend_print.film.printer_balance_log10 = (1.0 - w) * np.asarray(fp.FilmPreview(print_options[a]).film.printer_balance_log10) + w * np.asarray(fp.FilmPreview(print_options[b]).film.printer_balance_log10)
        blend_print.density_grid, blend_print.print_table, blend_print.table_counts = blend_print._build_print_table()
        row["print_5207_2383"] = float(np.abs(np.asarray(exact_print.render(ap1)[0]) - np.asarray(blend_print.render(ap1)[0])).max() * 255.0)
        if row["print_5207_2383"] > CCT_BLEND_LIMIT:
            raise ValueError(f"grid blend at {kelvin:.0f} K: the print differs from the exact light by {row['print_5207_2383']:.3g} codes")
        for negative in CCT_BLEND_SCAN_NEGATIVES:
            blended, _, _, _ = blended_scan(setup, metadata, negative, kelvin)
            exact_model, blend_model = scan_model(negative, exact), scan_blend_model(negative, kelvin)
            # The product form: the blend model with the blended stored values in place of the values of the blend light.
            blend_model.aim, blend_model.light_axis = blended["negative_scan_aim_density"], blended["negative_scan_light_axis"]
            values = [np.asarray(scan_linear(model, ap1, "off")[0], dtype=np.float64).reshape(-1, 3) for model in (exact_model, blend_model)]
            keep = (values[0] > CCT_BLEND_FLOOR) & (values[1] > CCT_BLEND_FLOOR)
            stops = float(np.abs(np.log2(np.where(keep, values[0], 1.0) / np.where(keep, values[1], 1.0))).max())
            row[f"scan_{negative}_stops"] = stops
            if stops > CCT_BLEND_STOPS_LIMIT:
                raise ValueError(f"grid blend at {kelvin:.0f} K: Negative Scan of {negative} differs from the exact light by {stops:.3g} stops")
        out[f"{kelvin:.0f} K between {a} and {b}"] = row
        print(f"grid blend at {kelvin:.0f} K: {row}", flush=True)
    return out


def setup_model(options: fp.FilmOptions) -> fp.FilmPreview:
    """Rule 'setup_without_tables': the part of FilmPreview.__init__ in front of the tables, on the first light of a pair."""
    model = fp.FilmPreview.__new__(fp.FilmPreview)
    model.options = options
    model_options = p0.ModelOptions(camera_daylight_cct_k=sr.E_REF_NOMINAL_CCT_K, negative_dye_basis=options.negative_dye_basis, negative_density_outside=options.density_outside, paper_dye_outside=options.density_outside,
                                    print_midscale_status_a=options.print_midscale_status_a, printer_lamp=options.printer_lamp, printer_filter=options.printer_filter, negative_profile=options.negative_profile, print_profile=options.print_profile,
                                    midscale_log_h=options.midscale_log_h, viewing_daylight_cct_k=options.viewing_cct_k)
    model.c = sr.Colorimetry(model_options)
    model.film = model.c.film
    model.status_curves = list(model.film.negative_curves.values())
    if options.negative_record != "dye_amount":
        raise ValueError(f"{options.negative_profile}: the product chain needs negative_record = 'dye_amount'")
    model.negative_curves = model._dye_amount_curves()
    model._prepare_inhibition()
    model.paper_curves = list(model.film.paper_curves.values())
    model.printing_gain = model._printing_gain()
    return model


def apply_light(model: fp.FilmPreview, options: fp.FilmOptions, default_balance: np.ndarray) -> None:
    """The steps of FilmPreview.__init__ that depend on the scene light. The options of one pair differ only in the fields of light_conditions."""
    model.options = options
    model.film.printer_balance_log10 = default_balance.copy()
    model.scene_spectrum = model.light(options.scene_light)
    model.layer_gain = model._camera_filter()


def display_matrix(model: fp.FilmPreview) -> np.ndarray:
    """FilmPreview._prepare_display. The whites of the product chain do not read a table."""
    if model.options.display_white not in ("reflector", "print_dmin"):
        raise ValueError("the product chain needs display_white = 'reflector' or 'print_dmin'")
    return model.display_matrix(model.options.display_white)


def aim_of(model: fp.FilmPreview) -> np.ndarray:
    return p0.status_aim_log_h(model.paper_curves, model.options.print_midscale_status_a)


def require_same(name: str, stored: dict[str, np.ndarray], values: dict[str, np.ndarray]) -> None:
    """Check 'Shared values'."""
    if set(stored) != set(values):
        raise ValueError(f"{name}: the array names differ between selections: {sorted(set(stored) ^ set(values))}")
    for key, value in values.items():
        if not np.array_equal(stored[key], value):
            raise ValueError(f"{name}: {key} is not the same in each selection that uses it")


def constants() -> tuple[dict[str, np.ndarray], fp.FilmOptions]:
    """The fixed values of the product chain. A value that differs between stocks stops the script in collect()."""
    options = mp.film_options(mp.RenderSettings())
    arrays = {"common/uv_max": np.array(fp.UV_MAX, dtype=np.float64), "common/print_contrast": scalar(options.print_contrast), "common/print_flash": scalar(options.print_flash), "common/viewing_flare": scalar(options.viewing_flare),
              "common/enlarger_flare_size": scalar(options.enlarger_flare_size), "common/frame_mm": scalar(options.frame_mm), "common/halation_strength": np.array(options.halation, dtype=np.float64), "common/halation_um": scalar(options.halation_um),
              "common/inhibition_um": scalar(options.inhibition_um), "common/spread_gaussians": np.array(fp.SPREAD_GAUSSIANS, dtype=np.float64), "common/gamut_threshold": np.array(options.gamut_threshold, dtype=np.float64),
              "common/gamut_limit": np.array(options.gamut_limit, dtype=np.float64), "common/gamut_power": scalar(options.gamut_power)}
    return arrays, options


FIXED_FIELDS = ("print_contrast", "print_flash", "viewing_flare", "enlarger_flare_size", "frame_mm", "halation", "halation_um", "inhibition_um", "gamut_threshold", "gamut_limit", "gamut_power", "uv_smooth", "light_spectra", "foliage",
                "interlayer_gain", "overexposure_stops", "print_timing", "mask_gamma", "adjacency_gain", "scatter_um", "scene_flare", "printer_lamp", "density_outside")


def collect() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict, list]:
    """All values of the two small resources. Returns (bundle arrays, setup arrays, bundle metadata, models for the reflectance table)."""
    negatives, papers = sorted(mp.CATALOG["negatives"]), sorted(mp.CATALOG["prints"])
    lights = product_lights()
    bundle, reference_options = constants()
    balance = np.zeros((len(negatives), len(papers), len(lights), 3))
    layer_gain = np.zeros((len(negatives), len(lights), 3))
    printing_gain = np.zeros((len(negatives), len(papers), 3))
    aim = np.zeros((len(papers), 3))
    to_display = np.zeros((len(papers), 3, 3))
    spectrum_index = np.zeros((len(negatives), len(lights)), dtype=np.int32)
    spectrum_names: list[str] = []
    stored_negatives: dict[str, dict[str, np.ndarray]] = {}
    stored_papers: dict[str, dict[str, np.ndarray]] = {}
    last_model = None
    started = time.perf_counter()
    for n, negative in enumerate(negatives):
        for p, paper in enumerate(papers):
            settings = mp.RenderSettings(negative=negative, print_material=paper, scene_light=lights[0])
            settings.validate()
            options = mp.film_options(settings)
            for field in FIXED_FIELDS:
                if getattr(options, field) != getattr(reference_options, field):
                    raise ValueError(f"{negative} on {paper}: {field} is not one value for all stocks")
            model = setup_model(options)
            default_balance = np.asarray(model.film.printer_balance_log10, dtype=np.float64).copy()
            for values, store, key in ((negative_arrays(model), stored_negatives, negative), (paper_arrays(model), stored_papers, paper)):
                if key in store:
                    require_same(key, store[key], values)
                else:
                    store[key] = values
            printing_gain[n, p] = model.printing_gain
            matrix, aim_value = display_matrix(model), aim_of(model)
            if negative != negatives[0]:
                require_same(paper, {"matrix": to_display[p], "aim": aim[p]}, {"matrix": matrix, "aim": aim_value})
            to_display[p], aim[p] = matrix, aim_value
            for l, light in enumerate(lights):
                light_options = mp.film_options(replace(settings, scene_light=light))
                apply_light(model, light_options, default_balance)
                balance[n, p, l] = model.film.printer_balance_log10
                if p and not np.array_equal(layer_gain[n, l], model.layer_gain):
                    raise ValueError(f"{negative}, {light}: the layer gain depends on the print material")
                layer_gain[n, l] = model.layer_gain
                spectrum_name = light_options.scene_light
                if spectrum_name not in spectrum_names:
                    spectrum_names.append(spectrum_name)
                    bundle[f"light/{spectrum_name}/spectrum"] = np.asarray(model.scene_spectrum, dtype=np.float64)
                elif not np.array_equal(bundle[f"light/{spectrum_name}/spectrum"], model.scene_spectrum):
                    raise ValueError(f"{spectrum_name}: the scene spectrum depends on the stock")
                spectrum_index[n, l] = spectrum_names.index(spectrum_name)
            last_model = model
        print(f"{negative}: {n + 1} of {len(negatives)}, {time.perf_counter() - started:.0f} s", flush=True)
    for negative, values in stored_negatives.items():
        bundle.update({f"negative/{negative}/{name}": value for name, value in values.items()})
    for paper, values in stored_papers.items():
        bundle.update({f"paper/{paper}/{name}": value for name, value in values.items()})
    projection = sr.LocusProjection(last_model.c)
    bundle.update({"common/wavelengths_nm": np.asarray(last_model.c.wavelengths, dtype=np.float64), "common/ap1_to_xyz": np.asarray(last_model.c.ap1_to_xyz, dtype=np.float64), "common/locus_normals": np.asarray(projection.normals, dtype=np.float64),
                   "common/locus_room": -(projection.offsets + projection.normals @ projection.white), "common/locus_white": np.asarray(projection.white, dtype=np.float64), "common/locus_inset": scalar(projection.LOCUS_INSET)})
    metadata = {"negatives": {k: {"name": mp.CATALOG["negatives"][k]["name"], "medium": medium_of(k), "scan_balance_light": balance_of(k)} for k in negatives}, "print_materials": {k: {"name": mp.CATALOG["prints"][k]["name"], "medium": mp.CATALOG["prints"][k]["medium"]} for k in papers}, "scene_lights": lights, "scene_spectra": spectrum_names}
    # Rule 'negative_show_grade': the grey needs the kernels, so it comes from the complete FilmPreview. Other negatives hold 0.
    grade_grey = np.zeros((len(negatives), len(lights), 3))
    for negative in mp.NEGATIVE_GRADE_STOCKS:
        for l, light in enumerate(lights):
            grade_grey[negatives.index(negative), l] = fp.FilmPreview(mp.film_options(mp.RenderSettings(negative=negative, print_material=mp.CINE_LOOK_PRINT, scene_light=light)))._grade_grey
    setup = {"negative_grade_grey": grade_grey, "printer_balance_log10": balance, "layer_gain": layer_gain, "printing_gain": printing_gain, "aim_log_h": aim, "xyz_to_display": to_display, "scene_spectrum_index": spectrum_index}
    # The reversal films add their spectra to spectrum_names, the list of metadata['scene_spectra'].
    reversal_setup, reversal_metadata = collect_reversals(bundle, reference_options, lights, spectrum_names)
    setup.update(reversal_setup)
    metadata.update(reversal_metadata)
    scan_setup, scan_metadata = collect_scan(bundle, setup, negatives, lights, spectrum_names)
    setup.update(scan_setup)
    metadata.update(scan_metadata)
    return bundle, setup, metadata, [last_model]


def check_setup(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, selection: tuple[str, str, str]) -> tuple[fp.FilmPreview, float]:
    """Check 'Setup': the complete FilmPreview against the stored values of one selection."""
    negative, paper, light = selection
    model = fp.FilmPreview(mp.film_options(mp.RenderSettings(negative=negative, print_material=paper, scene_light=light)))
    n, p, l = sorted(metadata["negatives"]).index(negative), sorted(metadata["print_materials"]).index(paper), metadata["scene_lights"].index(light)
    pairs = [(setup["printer_balance_log10"][n, p, l], model.film.printer_balance_log10), (setup["layer_gain"][n, l], model.layer_gain), (setup["printing_gain"][n, p], model.printing_gain), (setup["aim_log_h"][p], aim_of(model)), (setup["xyz_to_display"][p], model.xyz_to_display),
             (bundle[f"light/{metadata['scene_spectra'][setup['scene_spectrum_index'][n, l]]}/spectrum"], model.scene_spectrum), (bundle["common/locus_room"], model._room), (bundle[f"negative/{negative}/density_grid_start"], np.array([g[0] for g in model.density_grid])),
             (bundle[f"negative/{negative}/density_grid_stop"], np.array([g[-1] for g in model.density_grid])), (bundle[f"negative/{negative}/criterion_log_h"], model.film.negative_criterion_log_h)]
    if model._grade_grey is not None:
        pairs.append((setup["negative_grade_grey"][n, l], model._grade_grey))
    largest = max(float(np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)).max()) for a, b in pairs)
    if largest > SETUP_LIMIT:
        raise ValueError(f"{selection}: the stored setup differs from FilmPreview by {largest:.3g}")
    return model, largest


def check_reversal_setup(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, selection: tuple[str, str]) -> tuple[rf.ReversalPreview, float]:
    """Check 'Setup' on a reversal film: the complete ReversalPreview against the stored values of one selection."""
    film, light = selection
    model = rf.ReversalPreview(reversal_options(film, light))
    r, l = sorted(metadata["reversal_films"]).index(film), metadata["scene_lights"].index(light)
    stored = {name.split("/", 2)[2]: value for name, value in bundle.items() if name.startswith(f"reversal/{film}/")}
    values = reversal_arrays(model)
    if set(stored) != set(values):
        raise ValueError(f"{selection}: the stored arrays differ from ReversalPreview: {sorted(set(stored) ^ set(values))}")
    pairs = [(setup["reversal_layer_gain"][r, l], model.layer_gain), (setup["reversal_xyz_to_display"][r], model.xyz_to_display), (bundle[f"light/{metadata['scene_spectra'][setup['reversal_scene_spectrum_index'][r, l]]}/spectrum"], model.scene_spectrum),
             (bundle["common/locus_room"], model._room), *((stored[k], v) for k, v in values.items())]
    largest = max(float(np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)).max()) for a, b in pairs)
    if largest > SETUP_LIMIT:
        raise ValueError(f"{selection}: the stored setup differs from ReversalPreview by {largest:.3g}")
    return model, largest


def hull_edge_uv(c: sr.Colorimetry) -> np.ndarray:
    """Dense points on the edge of the hull of LocusProjection, in u'v'. A line in (X/Y, Z/Y) stays a line in u'v'."""
    columns = c.a_ref_knots.T
    columns = columns[columns[:, 1] > 0]
    points = np.stack([columns[:, 0] / columns[:, 1], columns[:, 2] / columns[:, 1]], axis=1)
    corners = points[ConvexHull(points).vertices]
    denominator = corners[:, 0] + 15.0 + 3.0 * corners[:, 1]
    corners_uv = np.stack([4.0 * corners[:, 0] / denominator, 9.0 / denominator], axis=1)
    shares = np.linspace(0.0, 1.0, 2000, endpoint=False)[None, :, None]
    return (corners_uv[:, None, :] * (1.0 - shares) + np.roll(corners_uv, -1, axis=0)[:, None, :] * shares).reshape(-1, 2)


def reachable_nodes(model: fp.FilmPreview, nodes: int) -> np.ndarray:
    """Rule 'compact_reflectance_table': the (nodes, nodes) mask of the nodes that a bilinear read can reach."""
    projection = sr.LocusProjection(model.c)
    u, v = fp.FilmPreview.uv_axes()
    uu, vv = np.meshgrid(u, np.maximum(v, 1e-3), indexing="ij")
    p = np.stack([9.0 * uu / (4.0 * vv), (12.0 - 3.0 * uu - 20.0 * vv) / (4.0 * vv)], axis=-1)
    room = -(projection.offsets + projection.normals @ projection.white)
    inside = np.all((p - projection.white) @ projection.normals.T <= room, axis=-1)
    mask = binary_dilation(inside, structure=np.ones((3, 3), dtype=bool))
    edge = hull_edge_uv(model.c)
    cell = np.floor(edge / np.array(fp.UV_MAX) * (nodes - 1)).astype(np.int64)
    for du in (0, 1):
        for dv in (0, 1):
            mask[np.clip(cell[:, 0] + du, 0, nodes - 1), np.clip(cell[:, 1] + dv, 0, nodes - 1)] = True
    return mask


def round_mantissa(values: np.ndarray, bits: int) -> np.ndarray:
    """Round to the nearest value with this count of mantissa bits. A carry moves into the exponent, which is correct for a positive value."""
    if (values < 0.0).any() or not np.isfinite(values).all():
        raise ValueError("the reflectance table must be finite and not negative")
    drop = 23 - bits
    raw = values.view(np.uint32)
    rounded = ((raw + np.uint32(1 << (drop - 1))) & np.uint32((0xFFFFFFFF << drop) & 0xFFFFFFFF)).view(np.float32)
    return np.where(values == 0.0, np.float32(0.0), rounded)


def compact_arrays(table: np.ndarray, bundle: dict[str, np.ndarray], mask: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """The arrays of the file and the dense table that they mean, with zero at each removed value."""
    weights = np.stack([value for name, value in bundle.items() if name.endswith("/exposure_weights")])
    used = np.flatnonzero(np.any(weights != 0.0, axis=(0, 1)))
    first, count = int(used[0]), int(used[-1] - used[0] + 1)
    rows = round_mantissa(table[mask][:, first:first + count], MANTISSA_BITS)
    data = rows.astype("<f4").tobytes()
    planes = np.frombuffer(b"".join(data[plane::4] for plane in range(4)), dtype=np.uint8).reshape(4, -1)
    dense = np.zeros_like(table)
    dense[mask, first:first + count] = rows
    arrays = {"byte_planes": planes, "node_index": np.flatnonzero(mask.ravel()).astype(np.int32), "uv_nodes": np.array(table.shape[0], dtype=np.int32), "first_wavelength": np.array(first, dtype=np.int32), "wavelength_count": np.array(count, dtype=np.int32)}
    return arrays, dense


def uv_of(model: fp.FilmPreview, dense: np.ndarray) -> np.ndarray:
    return model.c.layer_exposure(dense.reshape(-1, dense.shape[-1]).astype(np.float64) * model.scene_spectrum[None, :]).reshape(fp.UV_NODES, fp.UV_NODES, 3)


def check_images(c: sr.Colorimetry, default: mp.RenderSettings) -> tuple[dict[str, np.ndarray], np.ndarray]:
    """The images of check 'Compact table, display', and the hull edge as one more image for check 'Compact table, nodes'."""
    images = {}
    for name, path in RENDER_PHOTOS.items():
        photo = np.ascontiguousarray(np.load(REPO_ROOT / "build" / "tmp" / f"{path}.npy"), dtype=np.float32)
        images[name] = np.ascontiguousarray(fp.fk.product_grade(photo, float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32)
    images["neutral_ramp"] = np.outer(0.18 * 2.0 ** np.linspace(-5.0, 5.0, 241), np.ones(3)).astype(np.float32)[None]
    colours = np.random.default_rng(20261101)
    images["random_colours"] = (colours.uniform(-0.5, 1.0, (512, 512, 3)) * 2.0 ** colours.uniform(-6.0, 5.0, (512, 512, 1))).astype(np.float32)
    uv = hull_edge_uv(c)
    y = np.ones(len(uv))
    xyz = np.stack([9.0 * uv[:, 0] / (4.0 * uv[:, 1]), y, (12.0 - 3.0 * uv[:, 0] - 20.0 * uv[:, 1]) / (4.0 * uv[:, 1])], axis=1)
    return images, (xyz @ c.xyz_to_ap1.T).astype(np.float32)[None]


def check_compact(model: fp.FilmPreview, dense: np.ndarray, mask: np.ndarray, images: dict[str, np.ndarray], edge: np.ndarray, render: bool) -> dict:
    """The three checks of the compact table on one selection. A failed limit stops the script."""
    complete_uv = np.asarray(model.uv_table, dtype=np.float64)
    compact_uv = uv_of(model, dense)
    scale = np.maximum(np.abs(complete_uv), np.abs(compact_uv))[mask]
    relative = float((np.abs(complete_uv - compact_uv)[mask] / np.where(scale > 0.0, scale, 1.0)).max())
    if relative > UV_RELATIVE_LIMIT:
        raise ValueError(f"the compact u'v' table differs by {relative:.3g}")
    marked = compact_uv.astype(np.float32)
    marked[~mask] = np.nan
    projection = model._projection()
    for name, image in {**images, "hull_edge": edge}.items():
        q = fp.fk.layer_exposure(image, 0.0, model.c.ap1_to_xyz, projection.normals, model._room, projection.white, projection.LOCUS_INSET, marked, np.array(fp.UV_MAX), model.layer_gain)[0]
        if not np.isfinite(q).all():
            raise ValueError(f"{name}: a read reached a removed node of the compact table")
    result = {"uv_relative": relative}
    if render:
        complete_f32 = model._uv_f32
        codes = {}
        for name, image in images.items():
            model._uv_f32 = complete_f32
            reference = np.asarray(model.render(image)[0], dtype=np.float64)
            model._uv_f32 = marked
            candidate = np.asarray(model.render(image)[0], dtype=np.float64)
            codes[name] = float((np.abs(reference - candidate) * 255.0).max())
        model._uv_f32 = complete_f32
        result["display_largest_code"] = codes
        if not max(codes.values()) <= DISPLAY_CODE_LIMIT:
            raise ValueError(f"the compact table changes the display by {codes}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    resources, expected = args.output / "resources", args.output / "expected"
    started = time.perf_counter()
    bundle, setup, metadata, models = collect()
    print(f"collected the setup in {time.perf_counter() - started:.0f} s", flush=True)
    write_arrays(resources / "film_stock_bundle.bin", bundle, metadata)
    write_arrays(resources / "film_print_setup.bin", setup)
    reflectance = models[0]._final_reflectance_table().astype(np.float32).reshape(fp.UV_NODES, fp.UV_NODES, -1)
    node_mask = reachable_nodes(models[0], fp.UV_NODES)
    compact, dense = compact_arrays(reflectance, bundle, node_mask)
    write_arrays(resources / "film_reflectance_table.bin", compact)
    files = {"stock_bundle": "film_stock_bundle.bin", "print_setup": "film_print_setup.bin", "reflectance_table": "film_reflectance_table.bin"}
    manifest = {"schema_version": SCHEMA_VERSION, "lab_commit": lab_commit(), "resources": {key: {"file": name, "bytes": (resources / name).stat().st_size, "sha256": sha256_of(resources / name)} for key, name in files.items()}}
    (resources / "manifest.json").write_bytes((json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8"))

    checks = {}
    compact_checks = {}
    images, hull_edge = check_images(models[0].c, mp.RenderSettings())
    rng = random.Random(20261101)
    random_selections = [(rng.choice(sorted(metadata["negatives"])), rng.choice(sorted(metadata["print_materials"])), rng.choice(metadata["scene_lights"])) for _ in range(RANDOM_CHECKS)]
    for index, selection in enumerate(random_selections):
        model, checks[" on ".join(selection)] = check_setup(bundle, setup, metadata, selection)
        compact_checks[" on ".join(selection)] = check_compact(model, dense, node_mask, images, hull_edge, index < RENDER_RANDOM_SELECTIONS)
        print(f"compact table on {selection}: {compact_checks[' on '.join(selection)]}", flush=True)
    expected_files = {}
    for selection in EXPECTED_SELECTIONS:
        model, largest = check_setup(bundle, setup, metadata, selection)
        checks[" on ".join(selection)] = largest
        compact_checks[" on ".join(selection)] = check_compact(model, dense, node_mask, images, hull_edge, True)
        print(f"compact table on {selection}: {compact_checks[' on '.join(selection)]}", flush=True)
        if not np.isfinite(model.print_table).all() or not np.isfinite(model.uv_table).all():
            raise FloatingPointError(f"{selection}: a table has values that are not finite")
        name = f"{selection[0]}__{selection[1]}__{selection[2]}.bin"
        counts = model.table_counts
        write_arrays(expected / name, {"uv_table": np.asarray(model.uv_table, dtype=np.float64), "uv_table_compact": uv_of(model, dense), "uv_reachable": node_mask.astype(np.uint8), "print_table": np.asarray(model.print_table, dtype=np.float64), "outside_curve": np.array(counts["paper_exposure_outside_curve"], dtype=np.int64), "print_not_reached": np.array(counts["print_not_reached"], dtype=np.int64)},
                     {"negative": selection[0], "print_material": selection[1], "scene_light": selection[2]})
        expected_files[name] = {"bytes": (expected / name).stat().st_size, "table_counts": counts}
        print(f"expected values of {selection}: largest setup difference {largest:.3g}", flush=True)
    reversal_random = [(rng.choice(sorted(metadata["reversal_films"])), rng.choice(metadata["scene_lights"])) for _ in range(REVERSAL_RANDOM_CHECKS)]
    for index, selection in enumerate((*reversal_random, *REVERSAL_EXPECTED_SELECTIONS)):
        key = "reversal " + " under ".join(selection)
        model, checks[key] = check_reversal_setup(bundle, setup, metadata, selection)
        compact_checks[key] = check_compact(model, dense, node_mask, images, hull_edge, index < 2 or selection in REVERSAL_EXPECTED_SELECTIONS)
        print(f"compact table on reversal {selection}: {compact_checks[key]}", flush=True)
        if selection not in REVERSAL_EXPECTED_SELECTIONS or index < len(reversal_random):
            continue
        if not np.isfinite(model.print_table).all() or not np.isfinite(model.uv_table).all():
            raise FloatingPointError(f"{selection}: a table has values that are not finite")
        name = f"reversal__{selection[0]}__{selection[1]}.bin"
        write_arrays(expected / name, {"uv_table": np.asarray(model.uv_table, dtype=np.float64), "uv_table_compact": uv_of(model, dense), "uv_reachable": node_mask.astype(np.uint8), "light_table": np.asarray(model.print_table, dtype=np.float64)},
                     {"reversal": selection[0], "scene_light": selection[1]})
        expected_files[name] = {"bytes": (expected / name).stat().st_size}
        print(f"expected values of reversal {selection}: largest setup difference {checks[key]:.3g}", flush=True)
    scan_images = {"neutral_ramp": np.outer(0.18 * 2.0 ** np.linspace(-10.0, 10.0, 481), np.ones(3)).astype(np.float32), "random_colours": images["random_colours"][:8].reshape(-1, 3)}
    scan_random = [(rng.choice(sorted(metadata["negatives"])), rng.choice(metadata["scene_lights"])) for _ in range(SCAN_RANDOM_CHECKS)]
    scan_checks = {}
    default_scanner = scanner_arrays(ns.ScannerSetup())
    for selection in (*scan_random, *SCAN_EXPECTED_SELECTIONS):
        model, scan_checks[" under ".join(selection)] = check_scan(bundle, setup, metadata, selection, scan_images)
        print(f"scan {selection}: {scan_checks[' under '.join(selection)]}", flush=True)
        if selection not in SCAN_EXPECTED_SELECTIONS:
            continue
        if not np.isfinite(model.read.scan.table).all():
            raise FloatingPointError(f"scan {selection}: the scanner table has values that are not finite")
        name = f"scan__{selection[0]}__{selection[1]}.bin"
        stored = stored_scan(bundle, setup, metadata, *selection)
        write_arrays(expected / name, {"scanner_table": np.asarray(model.read.scan.table, dtype=np.float64), "density_grid_start": np.array([g[0] for g in model.negative.density_grid]),
                                       "density_grid_stop": np.array([g[-1] for g in model.negative.density_grid]), "scanner_first_node": default_scanner["first_node"],
                                       "scanner_weights": default_scanner["weights"], "base_density": stored["base"], "aim_density": stored["negative_scan_aim_density"],
                                       "light_axis": stored["negative_scan_light_axis"], "gamma": stored["gamma"], "layer_gain": stored["layer_gain"]},
                     {"negative": selection[0], "print_material": NEGATIVE_SCAN["id"], "scene_light": selection[1], "medium": metadata["negatives"][selection[0]]["medium"]})
        expected_files[name] = {"bytes": (expected / name).stat().st_size}
    for negative, kelvin in SCAN_BLEND_SELECTIONS:
        blended, a, b, w = blended_scan(setup, metadata, negative, kelvin)
        model = scan_blend_model(negative, kelvin)
        n = sorted(metadata["negatives"]).index(negative)
        la, lb = metadata["scene_lights"].index(a), metadata["scene_lights"].index(b)
        stored_difference = max(float(np.abs(model.aim - blended["negative_scan_aim_density"]).max()), float(np.abs(model.light_axis - blended["negative_scan_light_axis"]).max()))
        if stored_difference > SETUP_LIMIT:
            raise ValueError(f"scan {negative} at {kelvin} K: the model of the blend light differs from the blend of the stored values by {stored_difference:.3g}")
        spectrum = (1.0 - w) * bundle[f"light/{a}/spectrum"] + w * bundle[f"light/{b}/spectrum"]
        gain = blended["layer_gain"]
        blend_difference = max(float(np.abs(model.negative.light(model.negative.options.scene_light) - spectrum).max()), float(np.abs(np.asarray(model.negative.layer_gain) - gain).max()))
        if blend_difference > SETUP_LIMIT:
            raise ValueError(f"scan {negative} at {kelvin} K: the blended spectrum or layer gain differs from the model of the blend by {blend_difference:.3g}")
        scan_checks[f"{negative} at {round(kelvin)} K, blend"] = {"setup": max(blend_difference, stored_difference)}
        name = f"scan__{negative}__cct{round(kelvin)}.bin"
        write_arrays(expected / name, {"blend_share": scalar(w), "aim_density": blended["negative_scan_aim_density"], "light_axis": blended["negative_scan_light_axis"], "spectrum": spectrum, "layer_gain": gain},
                     {"negative": negative, "print_material": NEGATIVE_SCAN["id"], "kelvin": kelvin, "node_a": a, "node_b": b})
        expected_files[name] = {"bytes": (expected / name).stat().st_size, "node_a": a, "node_b": b, "share_of_b": w}
    # A second scanner: the weights, the gamma of each medium derived again, and the values of the expected negatives under daylight.
    scanner_b = Pipeline_scanner(scan_settings(SCAN_EXPECTED_SELECTIONS[0][0], "daylight", **SCANNER_B))
    b_arrays = {f"weights_{key}": value for key, value in scanner_arrays(scanner_b).items()}
    b_arrays.update({f"gamma_{medium}": medium_gamma(medium, **SCANNER_B) for medium in SCAN_MEDIA})
    b_negatives = list(dict.fromkeys(negative for negative, _ in SCAN_EXPECTED_SELECTIONS))
    for k, negative in enumerate(b_negatives):
        model = scan_model(negative, "daylight", **SCANNER_B)
        if not np.array_equal(model.gamma, b_arrays[f"gamma_{medium_of(negative)}"]):
            raise ValueError(f"scanner B: the gamma of {negative} is not the gamma of its medium")
        b_arrays.update({f"base_density_{k}": np.asarray(model.read.base, dtype=np.float64), f"aim_density_{k}": np.asarray(model.aim, dtype=np.float64),
                         f"light_axis_{k}": np.asarray(model.light_axis, dtype=np.float64)})
    write_arrays(expected / "scan__scanner_b.bin", b_arrays, {"scanner": {"centres_nm": list(scanner_b.centres_nm), "width_nm": scanner_b.width_nm, "light": scanner_b.light},
                                                              "negatives": b_negatives, "scene_light": "daylight"})
    expected_files["scan__scanner_b.bin"] = {"bytes": (expected / "scan__scanner_b.bin").stat().st_size, "gamma": {m: b_arrays[f"gamma_{m}"].tolist() for m in SCAN_MEDIA}}
    print(f"scanner B {scanner_b}: gamma {expected_files['scan__scanner_b.bin']['gamma']}", flush=True)
    # Rule frame_auto_colour on two random frames of x. Frame a: a small cast plus random colours (the near-neutral estimate is the smaller). Frame b: a
    # strong yellow-green cast with near-neutral highlights, as the forest of the P14 report (the white-patch estimate is the smaller). Rule
    # smaller_cast takes each branch once.
    auto_rng = np.random.default_rng(20261105)
    rows, columns = AUTO_FRAME_SHAPE
    level = auto_rng.uniform(-1.8, 1.1, (rows, columns, 1))
    frame_a = level + np.array([0.06, 0.01, -0.07]) + auto_rng.normal(0.0, 0.05, (rows, columns, 3)) + np.where(auto_rng.uniform(size=(rows, columns, 1)) < 0.3, auto_rng.normal(0.0, 0.25, (rows, columns, 3)), 0.0)
    level_b = auto_rng.uniform(-1.5, 0.5, (rows, columns, 1))
    bright = (np.arange(rows) < 30)[:, None, None] & np.ones((1, columns, 1), dtype=bool)  # a band of sky at the top
    frame_b = np.where(bright, auto_rng.uniform(0.6, 0.85, (rows, columns, 1)) + auto_rng.normal(0.0, 0.02, (rows, columns, 3)),
                       level_b + np.array([0.15, 0.13, -0.28]) + auto_rng.normal(0.0, 0.06, (rows, columns, 3)))
    axis = stored_scan(bundle, setup, metadata, "kodak_portra_400", "daylight")["negative_scan_light_axis"]
    auto_arrays = {"light_axis": axis}
    auto_record = []
    for label, frame in (("a", frame_a), ("b", frame_b)):
        frame = frame.astype(np.float32).astype(np.float64)
        auto_arrays.update({f"frame_{label}": frame, f"prescan_{label}": ns.reduce_frame(frame).reshape(*prescan_shape(rows, columns), 3)})
        for index, (mode, strength, density) in enumerate(AUTO_CASES):
            shift, record = ns.auto_colour_shift(frame, axis, mode, strength, density)
            auto_arrays[f"shift_{label}_{index}"] = np.asarray(shift, dtype=np.float64)
            white = float(np.linalg.norm(record["white_patch_cast_log10"])) < float(np.linalg.norm(record["near_neutral_cast_log10"]))
            auto_record.append({"frame": label, "mode": mode, "strength": strength, "density": density, "white_patch_used": white, "record": record})
    if {c["white_patch_used"] for c in auto_record} != {False, True}:
        raise ValueError("scan__auto.bin: the two frames do not take both branches of rule smaller_cast")
    constants = {"long_edge": ns.AUTO_LONG_EDGE, "valid_log": list(ns.AUTO_VALID_LOG), "sigma": ns.AUTO_SIGMA, "iterations": ns.AUTO_ITERATIONS, "cross_share": ns.AUTO_CROSS_SHARE,
                 "highlight_share": ns.AUTO_HIGHLIGHT_SHARE, "target": ns.AUTO_TARGET}
    write_arrays(expected / "scan__auto.bin", auto_arrays, {"cases": [{k: c[k] for k in ("mode", "strength", "density")} for c in auto_record[:len(AUTO_CASES)]],
                                                            "white_patch_used": {f"{c['frame']}_{i % len(AUTO_CASES)}": c["white_patch_used"] for i, c in enumerate(auto_record)},
                                                            "constants": constants})
    expected_files["scan__auto.bin"] = {"bytes": (expected / "scan__auto.bin").stat().st_size, "cases": auto_record}
    grid_checks = check_grid_blend(scan_images, setup, metadata)

    record = {"schema_version": SCHEMA_VERSION, "manifest": manifest, "selections": {"negatives": len(metadata["negatives"]), "print_materials": len(metadata["print_materials"]), "reversal_films": len(metadata["reversal_films"]), "scene_lights": len(metadata["scene_lights"])}, "setup_difference_limit": SETUP_LIMIT, "setup_difference": checks, "scan_point_limit_relative": SCAN_POINT_LIMIT, "scan": scan_checks, "grid_blend_print_limit_code": CCT_BLEND_LIMIT, "grid_blend_scan_limit_stops": CCT_BLEND_STOPS_LIMIT, "grid_blend": grid_checks, "compact_table": {"mantissa_bits": MANTISSA_BITS, "first_wavelength_nm": float(bundle["common/wavelengths_nm"][int(compact["first_wavelength"])]), "wavelength_count": int(compact["wavelength_count"]), "nodes_kept": int(node_mask.sum()), "nodes": int(node_mask.size), "uv_relative_limit": UV_RELATIVE_LIMIT, "display_code_limit": DISPLAY_CODE_LIMIT, "checks": compact_checks}, "expected": expected_files, "seconds": round(time.perf_counter() - started, 1)}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
