"""The resources that Alcedo Studio ships for the film print DRT, and the lab values that its host tests compare with.

Input: the profiles, stock_catalog.json, stock_physics.json, and the reflectance table under build/tmp/p2/tables/. Output: build/tmp/p7/product_resources/resources/ (shipped), build/tmp/p7/product_resources/expected/ (tests only), and results/p7_spectral_acceleration/product_resources.json. Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F1.
Machine rule: CPU only, one process, no GPU job.

Each resource is one array file: 8 bytes 'ALCDFILM', a little-endian uint64 header length, a JSON header, then the arrays, each one little-endian, row major, on a boundary of 8 bytes. The header names each array with its type ('f8', 'f4', 'i4', 'i8', 'u1'), its shape, and its offset from the end of the header.

| File | Content |
| manifest.json | Schema version, lab commit, and the file name, size, and SHA-256 of each resource |
| film_stock_bundle.bin | Per negative, per paper, per reversal film, each scene spectrum, and the values that are the same for all stocks. The header holds the catalog names. |
| film_print_setup.bin | The scalar values of each film, print material, and scene light: printer balance, layer gain, printing gain, aim, display matrix; and of each reversal film and scene light: layer gain, display matrix |
| film_reflectance_table.bin | The compact form of the final reflectance table, with rule 'foliage_spectra', by rule 'compact_reflectance_table' |

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

Lab Scan (step P10, ROADMAP U92, Alcedo Studio issue 661): the ADX scan of method 'apd' of the viewer (scripts/poc/p3_scan_and_scene/aces_scan.py,
ScanPreview with reading 'print2383' and timing 1). Print material 'lab_scan' selects it for any negative. The product reads the record in the
printing density of Kodak 2383 (the printing weights of 'paper/kodak_2383/'), encodes ADX10 on the base of the film, adds the LAD offset when the
user turns the LAD aim on, applies the Academy ADX10 to ACES transform, and shows the result through its OpenDRT. Values:
- 'negative/<negative>/adx_base_printing_density' (3): the printing density of the negative base (D_base of issue 661).
- The setup holds per negative and scene light 'adx_grey' (3): ADX10 with no offset of an 18 % grey under the light. The LAD offset is 445 - adx_grey.
- 'common/adx10_*': the constants of the ADX10 to ACES transform (aces-dev v1.3.1, A.M.P.A.S. license): scale, cdd_to_cid, exp_to_aces (row
  vectors), lut_cid, lut_log_e, ref_pt.
- Metadata 'lab_scan': the id, the name, and the print material of the printing weights.
Scene light 'as_shot' (U92): the scene lights hold a grid of colour temperature, CCT_GRID_MIRED (10 mired from 500 to 70, and 15000 K), named
'CCT<kelvin>', each from film_preview.cct_light (Planckian to 4000 K, CIE daylight from 5000 K, a blend linear in mired between). Metadata
'cct_grid' holds the mired, the kelvin, and the names. The product blends the two nodes around the colour temperature of the RAW decode, linear in
mired: the spectra (each with Y = 1) and the setup values of the light. A colour temperature outside the grid takes the nearest end.
Expected values: scan__<negative>__<light>.bin (the printing density table on the record nodes, the base density, the ADX10 grey, the LAD offset) for
SCAN_EXPECTED_SELECTIONS, and scan__<negative>__cct<kelvin>.bin (the share of the second node, the blended spectrum, layer gain, ADX10 grey, and
LAD offset) for SCAN_BLEND_SELECTIONS; the blended spectrum and layer gain are checked against the model of the blend light (limit 1e-9).
Checks, on 4 random and the expected scan selections:

| Check | Comparison rule | Limit |
| Scan setup | adx_grey, adx_base_printing_density, the LAD offset, and the printing weights against a new ScanPreview: largest absolute difference | 1e-9 |
| Scan point form | ACES2065-1 of the formula of issue 661 from the stored values against ScanPreview, LAD aim on and off, on a neutral ramp of -5 to +5 stops and 4096 random colours: largest relative difference | 1e-9 |
| Grid blend | The blend of two nodes against the exact light, at the mid-points of CCT_BLEND_CHECKS: the print (Kodak 2383) in sRGB, and the scan through ACES 2.0, LAD aim off and on; 8 bit code | largest at most 0.5 |
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

import aces_scan as acs  # noqa: E402  (P3, on the path through mvp_pipeline)

fp = mp.fp
rf = mp.rf
p0 = fp.p0
sr = fp.sr
SCHEMA_VERSION = 8  # 6: the reversal films (step P9); 7: Lab Scan (step P10); 8: the ADX scan and the colour temperature grid (U92)
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
LAB_SCAN = {"id": "lab_scan", "name": "Lab Scan", "printing_paper": "kodak_2383"}
SCAN_EXPECTED_SELECTIONS = (("kodak_5207", "reference"), ("kodak_portra_400", "reference"), ("kodak_ektar_100", "reference"), ("kodak_5219", "daylight"))
# Colour temperatures between grid nodes for the expected values of the blend (issue 661): one below and one above 4000 K.
SCAN_BLEND_SELECTIONS = (("kodak_5219", 5650.0), ("kodak_5207", 3100.0))
SCAN_RANDOM_CHECKS = 4
SCAN_POINT_LIMIT = 1e-9
CCT_GRID_MIRED = (*(float(m) for m in range(500, 69, -10)), 1e6 / 15000.0)
CCT_BLEND_CHECKS = (495.0, 335.0, 245.0, 205.0, 195.0, 105.0)  # mired, mid-points of grid segments (U92 probe: largest 0.11 code)
CCT_BLEND_LIMIT = 0.5


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


def scan_model(negative: str, light: str, lad: bool) -> "acs.ScanPreview":
    """Method 'apd' of the viewer as Lab Scan of issue 661: Kodak 2383 printing density, timing 1, LAD aim on or off, with the defaults of the other controls."""
    register_lights()
    settings = mp.RenderSettings(negative=negative, method="apd", scene_light=light)
    settings.validate()
    return acs.ScanPreview(mp.film_options(settings, mp.SCAN_CARRIER_PRINT), output="aces20", timing=1.0, lad_aim=lad, reading="print2383")


def scan_blend_model(negative: str, kelvin: float, lad: bool) -> "acs.ScanPreview":
    """Lab Scan at a colour temperature between grid nodes, as the product computes it: the blended spectrum and, with the LAD aim, the offset of the
    blended ADX10 grey of the two nodes."""
    name, a, b, w = blend_light(kelvin)
    model = scan_model(negative, name, lad)
    if lad:
        node_a, node_b = scan_model(negative, a, False), scan_model(negative, b, False)
        grey = (1.0 - w) * node_a.grey_adx(node_a.negative.options.scene_light) + w * node_b.grey_adx(node_b.negative.options.scene_light)
        model.offset = acs.ADX10_LAD - grey
    return model


SCAN_DISPLAY_LIGHTS = ("reference", "daylight", *(kelvin for _, kelvin in SCAN_BLEND_SELECTIONS))  # the lights of the expected values of the scan form (issue 661)


def scan_light_label(light: str | float) -> str:
    return light if isinstance(light, str) else f"cct{round(light)}"


def scan_expected_model(negative: str, light: str | float, lad: bool) -> "acs.ScanPreview":
    """A named light of the resources, or a colour temperature between grid nodes in the blend form of the product."""
    return scan_model(negative, light, lad) if isinstance(light, str) else scan_blend_model(negative, light, lad)


def scan_aces(model: "acs.ScanPreview", ap1: np.ndarray) -> np.ndarray:
    """ACES2065-1 of the scan, before the display transform."""
    code, _ = model.adx10(np.ascontiguousarray(ap1, dtype=np.float32))
    return acs.adx10_to_aces(code)


def adx_constants() -> dict[str, np.ndarray]:
    return {"common/adx10_scale": np.asarray(acs.ADX10_SCALE, dtype=np.float64), "common/adx10_cdd_to_cid": np.asarray(acs.CDD_TO_CID, dtype=np.float64),
            "common/adx10_exp_to_aces": np.asarray(acs.EXP_TO_ACES, dtype=np.float64), "common/adx10_lut_cid": np.asarray(acs.LUT_CID, dtype=np.float64),
            "common/adx10_lut_log_e": np.asarray(acs.LUT_LOG_E, dtype=np.float64), "common/adx10_ref_pt": scalar(acs.REF_PT)}


def collect_scan(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], negatives: list[str], lights: list[str], spectrum_names: list[str]) -> tuple[dict[str, np.ndarray], dict]:
    """The values of Lab Scan (U92). One ScanPreview per negative builds the printing density table, which does not depend on the light; the ADX10 grey
    of each light reads it, as ScanPreview.grey_apd does. Adds the base densities and the ADX constants to the bundle."""
    grey = np.zeros((len(negatives), len(lights), 3))
    started = time.perf_counter()
    bundle.update(adx_constants())
    for n, negative in enumerate(negatives):
        model = scan_model(negative, lights[0], False)
        require_same("lab_scan printing weights", {"w": bundle[f"paper/{LAB_SCAN['printing_paper']}/printing_weights"]}, {"w": np.asarray(model.apd_weights, dtype=np.float64)})
        bundle[f"negative/{negative}/adx_base_printing_density"] = np.asarray(model.apd_dmin, dtype=np.float64)
        neg = model.negative
        for l, light in enumerate(lights):
            spectrum = bundle[f"light/{spectrum_names[setup['scene_spectrum_index'][n, l]]}/spectrum"]
            q = setup["layer_gain"][n, l] * neg.c.layer_exposure(0.18 * spectrum)
            grey[n, l] = acs.adx10_from_apd(model.table_apd(neg.negative_density(q[None])[0])[0], model.apd_dmin)
        print(f"scan {negative}: {n + 1} of {len(negatives)}, {time.perf_counter() - started:.0f} s", flush=True)
    grid = {"mired": [1e6 / round(1e6 / m) for m in CCT_GRID_MIRED], "kelvin": [round(1e6 / m) for m in CCT_GRID_MIRED], "lights": list(CCT_LIGHTS)}
    return {"adx_grey": grey}, {"lab_scan": dict(LAB_SCAN), "cct_grid": grid}


def scan_point_form(model: "acs.ScanPreview", bundle: dict[str, np.ndarray], grey: np.ndarray, negative: str, lad: bool, ap1: np.ndarray) -> np.ndarray:
    """Check 'Scan point form': ACES2065-1 of the formula of issue 661 from the stored values. The record and the printing density table come from the model."""
    record, _ = model.negative.negative_image(np.ascontiguousarray(ap1[None], dtype=np.float32))
    density = model.table_apd(record)[0]
    offset = acs.ADX10_LAD - grey if lad else 0.0
    adx = np.clip(bundle["common/adx10_scale"] * (density - bundle[f"negative/{negative}/adx_base_printing_density"]) * 500.0 + 95.0 + offset, 0.0, 1023.0)
    cid = ((adx - 95.0) / 500.0) @ bundle["common/adx10_cdd_to_cid"]
    log_e = np.where(cid <= 0.6, np.interp(cid, bundle["common/adx10_lut_cid"], bundle["common/adx10_lut_log_e"]), (100.0 / 55.0) * cid - float(bundle["common/adx10_ref_pt"]))
    return (10.0 ** log_e) @ bundle["common/adx10_exp_to_aces"]


def check_scan(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, selection: tuple[str, str], images: dict[str, np.ndarray]) -> tuple["acs.ScanPreview", dict]:
    """Checks 'Scan setup' and 'Scan point form' on one selection."""
    negative, light = selection
    n, l = sorted(metadata["negatives"]).index(negative), metadata["scene_lights"].index(light)
    point, largest = {}, 0.0
    model = None
    for lad in (False, True):
        model = scan_model(negative, light, lad)
        grey = setup["adx_grey"][n, l]
        largest = max(largest, float(np.abs(model.grey_adx(model.negative.options.scene_light) - grey).max()), float(np.abs(model.apd_dmin - bundle[f"negative/{negative}/adx_base_printing_density"]).max()),
                      float(np.abs(np.asarray(model.negative.layer_gain) - setup["layer_gain"][n, l]).max()), float(np.abs(model.offset - (acs.ADX10_LAD - grey if lad else 0.0)).max()))
        for name, ap1 in images.items():
            reference = scan_aces(model, ap1[None])[0]
            formula = scan_point_form(model, bundle, grey, negative, lad, ap1)
            point[f"{name}, LAD {'on' if lad else 'off'}"] = float(np.abs(formula / np.maximum(np.abs(reference), 1e-12) - 1.0).max())
    if largest > SETUP_LIMIT:
        raise ValueError(f"scan {selection}: the stored values differ from ScanPreview by {largest:.3g}")
    if max(point.values()) > SCAN_POINT_LIMIT:
        raise ValueError(f"scan {selection}: the formula of issue 661 differs from ScanPreview by {point}")
    return model, {"setup": largest, "point_form_largest_relative": point}


def check_grid_blend(images: dict[str, np.ndarray]) -> dict:
    """Check 'Grid blend': the blend of two nodes against the exact light at mid-points of grid segments."""
    aces20 = acs.builtin_processor(acs.OUTPUT_TRANSFORMS["aces20"], acs.DISPLAY_TRANSFORM)
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
        for negative in ("kodak_5219", "kodak_portra_400"):
            for lad in (False, True):
                shown = [acs.apply_processor(aces20, scan_aces(model, ap1).reshape(-1, 3)) for model in (scan_model(negative, exact, lad), scan_blend_model(negative, kelvin, lad))]
                row[f"scan_{negative}_lad_{'on' if lad else 'off'}"] = float(np.abs(shown[0] - shown[1]).max() * 255.0)
        out[f"{kelvin:.0f} K between {a} and {b}"] = row
        print(f"grid blend at {kelvin:.0f} K: {row}", flush=True)
        if max(row.values()) > CCT_BLEND_LIMIT:
            raise ValueError(f"grid blend at {kelvin:.0f} K: {row} codes")
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
    metadata = {"negatives": {k: {"name": mp.CATALOG["negatives"][k]["name"]} for k in negatives}, "print_materials": {k: {"name": mp.CATALOG["prints"][k]["name"], "medium": mp.CATALOG["prints"][k]["medium"]} for k in papers}, "scene_lights": lights, "scene_spectra": spectrum_names}
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
    scan_images = {"neutral_ramp": np.outer(0.18 * 2.0 ** np.linspace(-5.0, 5.0, 241), np.ones(3)).astype(np.float32), "random_colours": images["random_colours"][:8].reshape(-1, 3)}
    scan_random = [(rng.choice(sorted(metadata["negatives"])), rng.choice(metadata["scene_lights"])) for _ in range(SCAN_RANDOM_CHECKS)]
    scan_checks = {}
    for selection in (*scan_random, *SCAN_EXPECTED_SELECTIONS):
        model, scan_checks[" under ".join(selection)] = check_scan(bundle, setup, metadata, selection, scan_images)
        print(f"scan {selection}: {scan_checks[' under '.join(selection)]}", flush=True)
        if selection not in SCAN_EXPECTED_SELECTIONS:
            continue
        if not np.isfinite(model.table).all():
            raise FloatingPointError(f"scan {selection}: the printing density table has values that are not finite")
        n, l = sorted(metadata["negatives"]).index(selection[0]), metadata["scene_lights"].index(selection[1])
        name = f"scan__{selection[0]}__{selection[1]}.bin"
        write_arrays(expected / name, {"printing_density_table": np.asarray(model.table, dtype=np.float64), "density_grid_start": np.array([g[0] for g in model.negative.density_grid]),
                                       "density_grid_stop": np.array([g[-1] for g in model.negative.density_grid]), "adx_base_printing_density": bundle[f"negative/{selection[0]}/adx_base_printing_density"],
                                       "adx_grey": setup["adx_grey"][n, l], "lad_offset": acs.ADX10_LAD - setup["adx_grey"][n, l]},
                     {"negative": selection[0], "print_material": LAB_SCAN["id"], "scene_light": selection[1]})
        expected_files[name] = {"bytes": (expected / name).stat().st_size}
    for negative, kelvin in SCAN_BLEND_SELECTIONS:
        _, a, b, w = blend_light(kelvin)
        n = sorted(metadata["negatives"]).index(negative)
        la, lb = metadata["scene_lights"].index(a), metadata["scene_lights"].index(b)
        grey = (1.0 - w) * setup["adx_grey"][n, la] + w * setup["adx_grey"][n, lb]
        model = scan_blend_model(negative, kelvin, True)
        if float(np.abs(model.offset - (acs.ADX10_LAD - grey)).max()) > SETUP_LIMIT:
            raise ValueError(f"scan {negative} at {kelvin} K: the blended LAD offset differs from the stored values")
        spectrum = (1.0 - w) * bundle[f"light/{a}/spectrum"] + w * bundle[f"light/{b}/spectrum"]
        gain = (1.0 - w) * setup["layer_gain"][n, la] + w * setup["layer_gain"][n, lb]
        blend_difference = max(float(np.abs(model.negative.light(model.negative.options.scene_light) - spectrum).max()), float(np.abs(np.asarray(model.negative.layer_gain) - gain).max()))
        if blend_difference > SETUP_LIMIT:
            raise ValueError(f"scan {negative} at {kelvin} K: the blended spectrum or layer gain differs from the model of the blend by {blend_difference:.3g}")
        scan_checks[f"{negative} at {round(kelvin)} K, blend"] = {"setup": blend_difference}
        name = f"scan__{negative}__cct{round(kelvin)}.bin"
        write_arrays(expected / name, {"blend_share": scalar(w), "adx_grey": grey, "lad_offset": acs.ADX10_LAD - grey, "spectrum": spectrum, "layer_gain": gain},
                     {"negative": negative, "print_material": LAB_SCAN["id"], "kelvin": kelvin, "node_a": a, "node_b": b})
        expected_files[name] = {"bytes": (expected / name).stat().st_size, "node_a": a, "node_b": b, "share_of_b": w}
    grid_checks = check_grid_blend(scan_images)

    record = {"schema_version": SCHEMA_VERSION, "manifest": manifest, "selections": {"negatives": len(metadata["negatives"]), "print_materials": len(metadata["print_materials"]), "reversal_films": len(metadata["reversal_films"]), "scene_lights": len(metadata["scene_lights"])}, "setup_difference_limit": SETUP_LIMIT, "setup_difference": checks, "scan_point_limit_relative": SCAN_POINT_LIMIT, "scan": scan_checks, "grid_blend_limit_code": CCT_BLEND_LIMIT, "grid_blend": grid_checks, "compact_table": {"mantissa_bits": MANTISSA_BITS, "first_wavelength_nm": float(bundle["common/wavelengths_nm"][int(compact["first_wavelength"])]), "wavelength_count": int(compact["wavelength_count"]), "nodes_kept": int(node_mask.sum()), "nodes": int(node_mask.size), "uv_relative_limit": UV_RELATIVE_LIMIT, "display_code_limit": DISPLAY_CODE_LIMIT, "checks": compact_checks}, "expected": expected_files, "seconds": round(time.perf_counter() - started, 1)}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
