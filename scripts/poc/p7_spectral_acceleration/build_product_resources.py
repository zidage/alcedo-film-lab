"""The resources that Alcedo Studio ships for the film print DRT, and the lab values that its host tests compare with.

Input: the profiles, stock_catalog.json, stock_physics.json, and the reflectance table under build/tmp/p2/tables/. Output: build/tmp/p7/product_resources/resources/ (shipped), build/tmp/p7/product_resources/expected/ (tests only), and results/p7_spectral_acceleration/product_resources.json. Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F1.
Machine rule: CPU only, one process, no GPU job.

Each resource is one array file: 8 bytes 'ALCDFILM', a little-endian uint64 header length, a JSON header, then the arrays, each one little-endian, row major, on a boundary of 8 bytes. The header names each array with its type ('f8', 'f4', 'i4', 'i8', 'u1'), its shape, and its offset from the end of the header.

| File | Content |
| manifest.json | Schema version, lab commit, and the file name, size, and SHA-256 of each resource |
| film_stock_bundle.bin | Per negative, per paper, each scene spectrum, and the values that are the same for all stocks. The header holds the catalog names. |
| film_print_setup.bin | The scalar values of each film, print material, and scene light: printer balance, layer gain, printing gain, aim, display matrix |
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
p0 = fp.p0
sr = fp.sr
SCHEMA_VERSION = 1
MAGIC = b"ALCDFILM"
OUTPUT = REPO_ROOT / "build" / "tmp" / "p7" / "product_resources"
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "product_resources.json"
EXPECTED_SELECTIONS = (("kodak_5207", "kodak_2383", "reference"), ("kodak_portra_400", "kodak_endura_premier", "daylight"), ("fuji_eterna_500", "kodak_2383", "street_mixed"))
RANDOM_CHECKS = 8
SETUP_LIMIT = 1e-9
MANTISSA_BITS = 12
UV_RELATIVE_LIMIT = 2e-4
DISPLAY_CODE_LIMIT = 0.5
RENDER_PHOTOS = {"se188": "p3/input/se188", "_DSC8148": "baseline/night/_DSC8148_ap1", "digital_ap1": "p5/real_5207/pair/digital_ap1"}
RENDER_RANDOM_SELECTIONS = 3


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
              "layer_spread_um": np.array(model.options.layer_spread_um, dtype=np.float64), **uniform_curves(model.negative_curves)}
    if model.inhibition is not None:
        i = model.inhibition
        arrays.update(inhibition_k=i["k"], inhibition_start=i["start"], inhibition_free=i["free"], inhibition_lengths=np.asarray(i["lengths"], dtype=np.int64), inhibition_step=scalar(i["step"]))
    return {name: np.asarray(value, dtype=np.int64 if value.dtype.kind == "i" else np.float64) for name, value in arrays.items()}


def paper_arrays(model: fp.FilmPreview) -> dict[str, np.ndarray]:
    """The values that depend on the paper and its viewing light only."""
    f = model.film
    weights = f.w_viewing[f.viewing_name]
    start = np.array([c.density.min() for c in model.paper_curves])
    arrays = {"base": f.paper_base, "dyes": f.paper_dyes, "printing_weights": f.w_printing, "status_a_weights": f.w_status_a, "viewing_weights": weights,
              "xyz_scale": scalar(100.0 / weights[1].sum()), "white_xyz": f.white_xyz(), "status_axis_start": start, "status_axis_range": np.array([c.density.max() for c in model.paper_curves]) - start,
              **uniform_curves(model.paper_curves)}
    return {name: np.asarray(value, dtype=np.int64 if value.dtype.kind == "i" else np.float64) for name, value in arrays.items()}


def setup_model(options: fp.FilmOptions) -> fp.FilmPreview:
    """Rule 'setup_without_tables': the part of FilmPreview.__init__ in front of the tables, on the first light of a pair."""
    model = fp.FilmPreview.__new__(fp.FilmPreview)
    model.options = options
    model_options = p0.ModelOptions(camera_daylight_cct_k=sr.E_REF_NOMINAL_CCT_K, negative_dye_basis=options.negative_dye_basis, negative_density_outside=options.density_outside, paper_dye_outside=options.density_outside,
                                    print_midscale_status_a=options.print_midscale_status_a, printer_lamp=options.printer_lamp, negative_profile=options.negative_profile, print_profile=options.print_profile,
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
    """FilmPreview._prepare_display with display_white = 'reflector'. This white does not read a table."""
    if model.options.display_white != "reflector":
        raise ValueError("the product chain needs display_white = 'reflector'")
    white = model.film.white_xyz()
    return fp.XYZ_TO_REC709 @ fp.bradford_matrix(white / white[1], fp.XYZ_D65) / white[1]


def aim_of(model: fp.FilmPreview) -> np.ndarray:
    return np.array([c.log_h_at(model.options.print_midscale_status_a) for c in model.paper_curves])


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
    lights = list(mp.SCENE_LIGHTS)
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
    setup = {"printer_balance_log10": balance, "layer_gain": layer_gain, "printing_gain": printing_gain, "aim_log_h": aim, "xyz_to_display": to_display, "scene_spectrum_index": spectrum_index}
    return bundle, setup, metadata, [last_model]


def check_setup(bundle: dict[str, np.ndarray], setup: dict[str, np.ndarray], metadata: dict, selection: tuple[str, str, str]) -> tuple[fp.FilmPreview, float]:
    """Check 'Setup': the complete FilmPreview against the stored values of one selection."""
    negative, paper, light = selection
    model = fp.FilmPreview(mp.film_options(mp.RenderSettings(negative=negative, print_material=paper, scene_light=light)))
    n, p, l = sorted(metadata["negatives"]).index(negative), sorted(metadata["print_materials"]).index(paper), metadata["scene_lights"].index(light)
    pairs = [(setup["printer_balance_log10"][n, p, l], model.film.printer_balance_log10), (setup["layer_gain"][n, l], model.layer_gain), (setup["printing_gain"][n, p], model.printing_gain), (setup["aim_log_h"][p], aim_of(model)), (setup["xyz_to_display"][p], model.xyz_to_display),
             (bundle[f"light/{metadata['scene_spectra'][setup['scene_spectrum_index'][n, l]]}/spectrum"], model.scene_spectrum), (bundle["common/locus_room"], model._room), (bundle[f"negative/{negative}/density_grid_start"], np.array([g[0] for g in model.density_grid])),
             (bundle[f"negative/{negative}/density_grid_stop"], np.array([g[-1] for g in model.density_grid])), (bundle[f"negative/{negative}/criterion_log_h"], model.film.negative_criterion_log_h)]
    largest = max(float(np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)).max()) for a, b in pairs)
    if largest > SETUP_LIMIT:
        raise ValueError(f"{selection}: the stored setup differs from FilmPreview by {largest:.3g}")
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

    record = {"schema_version": SCHEMA_VERSION, "manifest": manifest, "selections": {"negatives": len(metadata["negatives"]), "print_materials": len(metadata["print_materials"]), "scene_lights": len(metadata["scene_lights"])}, "setup_difference_limit": SETUP_LIMIT, "setup_difference": checks, "compact_table": {"mantissa_bits": MANTISSA_BITS, "first_wavelength_nm": float(bundle["common/wavelengths_nm"][int(compact["first_wavelength"])]), "wavelength_count": int(compact["wavelength_count"]), "nodes_kept": int(node_mask.sum()), "nodes": int(node_mask.size), "uv_relative_limit": UV_RELATIVE_LIMIT, "display_code_limit": DISPLAY_CODE_LIMIT, "checks": compact_checks}, "expected": expected_files, "seconds": round(time.perf_counter() - started, 1)}
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
