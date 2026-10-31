"""The shared pipeline of the Python MVP: RAW file to display image, by the print method or the Frontier scan method.

Input: a RAW file that LibRaw reads, a negative and a print material of stock_catalog.json, a scene light, a spectral prior, and the product grade.
Output: sRGB display code (float32) with its parameters. No value of a frame is kept between renders; the tables stay in build/tmp/p2/tables/.
Step: P6, README U61. The negative chain and the print are those of P2 to P5 (film_preview.py), and the scan read is the APD read of P3 (aces_scan.py).

Rules of this step:
- 'stock_options_from_catalog': an accepted stock of P4 and P5 keeps its values. A new stock takes the rules of P5: exposure of the grey 12.5 / ISO lux seconds (inferred),
  the published dye curves or the band split, and spread and inhibition from its modulation transfer curves when it has them.
- 'print_conditions_by_medium': a cine print material takes the conditions of 2383 (projection at D65, neutral printing, grey aim 0.85), and a paper takes those of Endura (D50 viewing, grey aim 0.75).
- 'no_anchor_at_reference_light': the default scene has no rule grey_anchor (U58). Another scene light needs the rule, because the printer balance follows the light. A stock with a relative sensitivity chart keeps the rule at each light.
- 'spectral_prior': 'light_like' applies rule 'light_like_spectra' of P4, and 'measured_reflectance' uses the reflectance prior of P1 with no change.
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
from aces_scan import ScanPreview, fp  # noqa: E402
import frontier_scan  # noqa: E402

CATALOG = json.loads((SCRIPT_DIR / "stock_catalog.json").read_text(encoding="utf-8"))
PHYSICS_PATH = SCRIPT_DIR / "stock_physics.json"
ACCEPTED_STOCKS = {"kodak_5207": "5207_2383", "kodak_5219": "5219_2383", "kodak_portra_400": "portra400_endura", "kodak_portra_160": "portra160_endura",
                   "kodak_portra_800": "portra800_endura", "kodak_ektar_100": "ektar100_endura", "kodak_gold_200": "gold200_endura", "fuji_c200": "c200_endura"}
STOCK_PRINT_FIELDS = ("print_profile", "print_midscale_status_a", "viewing_cct_k", "neutral_printing", "grey_anchor", "balance_light", "scene_light")
REFERENCE_LIGHT = "reference"
SCENE_LIGHTS = (REFERENCE_LIGHT, *fp.PRODUCT_LIGHTS, *fp.SCENE_PRESETS)
SPECTRAL_PRIORS = ("light_like", "measured_reflectance")
METHODS = ("print", "frontier")
SCAN_CARRIER_PRINT = "kodak_2383"
DEFAULT_LONG_EDGE = 2048


@dataclass(frozen=True)
class RenderSettings:
    negative: str = "kodak_5207"
    method: str = "print"
    print_material: str = "kodak_2383"
    scene_light: str = REFERENCE_LIGHT
    spectral_prior: str = "light_like"
    exposure_ev: float = 1.5
    contrast: float = float(fp.PRODUCT_CONTRAST)
    saturation: float = float(fp.PRODUCT_SATURATION)
    scanner_stage: bool = True

    def validate(self) -> None:
        if self.negative not in CATALOG["negatives"]:
            raise ValueError(f"unknown negative {self.negative!r}")
        failure = load_physics().get(self.negative, {}).get("error")
        if failure:
            raise ValueError(f"negative {self.negative!r} does not run on the model: {failure}")
        if self.method not in METHODS:
            raise ValueError(f"unknown method {self.method!r}")
        if self.print_material not in CATALOG["prints"]:
            reason = CATALOG["not_usable"].get(self.print_material, {}).get("reason", "not in the catalog")
            raise ValueError(f"print material {self.print_material!r}: {reason}")
        if self.scene_light not in SCENE_LIGHTS:
            raise ValueError(f"unknown scene light {self.scene_light!r}")
        if self.spectral_prior not in SPECTRAL_PRIORS:
            raise ValueError(f"unknown spectral prior {self.spectral_prior!r}")


def load_physics() -> dict:
    return json.loads(PHYSICS_PATH.read_text(encoding="utf-8")) if PHYSICS_PATH.exists() else {}


def negative_options(negative: str, physics: dict | None = None) -> dict:
    """Rule 'stock_options_from_catalog', with no print condition."""
    if negative in ACCEPTED_STOCKS:
        key = ACCEPTED_STOCKS[negative]
        accepted = fp.P4_PHYSICAL[key] if key in fp.P4_PHYSICAL else fp.P5_PHYSICAL[key]
        stock = {k: v for k, v in fp.STOCKS[key].items() if k not in STOCK_PRINT_FIELDS}
        return {**stock, **{k: v for k, v in accepted.items() if k != "scene_light"}, "negative_profile": negative}
    entry = CATALOG["negatives"][negative]
    options = dict(negative_profile=negative, midscale_log_h=math.log10(12.5 / entry["iso"]), negative_dye_basis="published" if entry["published_dyes"] else "band_split",
                   negative_record="dye_amount", light_spectra=True, scatter_um=0.0, adjacency_gain=0.0, gamut_limit=fp.P4_GAMUT_LIMIT)
    fitted = (physics if physics is not None else load_physics()).get(negative, {})
    if fitted.get("layer_spread_um"):
        options.update(layer_spread_um=tuple(fitted["layer_spread_um"]), inhibition_total=tuple(fitted["inhibition_total"]))
    return options


def print_conditions(print_material: str) -> dict:
    """Rule 'print_conditions_by_medium'."""
    if CATALOG["prints"][print_material]["medium"].lower() == "cine":
        return dict(print_profile=print_material, print_midscale_status_a=fp.CINE_GREY_STATUS_A, viewing_cct_k=6500.0, neutral_printing=True)
    return dict(print_profile=print_material, print_midscale_status_a=0.75, viewing_cct_k=5000.0, neutral_printing=False)


def light_conditions(negative: str, scene_light: str, physics: dict | None = None) -> dict:
    """Rule 'no_anchor_at_reference_light'."""
    fitted = (physics if physics is not None else load_physics()).get(negative, {})
    relative = bool(fitted.get("relative_sensitivity")) or negative == "fuji_c200"
    balance = "T3200" if CATALOG["negatives"][negative].get("exposure_kelvin", 5500) < 4500 else "D55"
    if scene_light == REFERENCE_LIGHT:
        if relative:
            return dict(grey_anchor=True, balance_light=balance, scene_light=balance)
        return dict(grey_anchor=False, balance_light="E_ref", scene_light="E_ref")
    light = fp.PRODUCT_LIGHTS.get(scene_light, scene_light)
    return dict(grey_anchor=True, balance_light=balance, scene_light=light)


def film_options(settings: RenderSettings, print_material: str | None = None, physics: dict | None = None) -> fp.FilmOptions:
    material = print_material or settings.print_material
    return fp.FilmOptions(**{**fp.DARKROOM, **negative_options(settings.negative, physics), **print_conditions(material), **light_conditions(settings.negative, settings.scene_light, physics),
                             "light_spectra": settings.spectral_prior == "light_like"})


def decode_raw(path: Path, colorimetry, long_edge: int = DEFAULT_LONG_EDGE) -> tuple[np.ndarray, dict]:
    """White-balanced linear AP1 with this long edge, by area reduction of the demosaiced data. A smaller sensor keeps its size, and the record states it; there is no enlargement."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        sensor_long_edge = max(raw.sizes.width, raw.sizes.height)
        half_size = sensor_long_edge // 2 >= long_edge
        xyz = raw.postprocess(output_color=rawpy.ColorSpace.XYZ, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True, half_size=half_size,
                              output_bps=16, highlight_mode=rawpy.HighlightMode.Clip).astype(np.float32) / 65535.0
    height, width = xyz.shape[:2]
    scale = long_edge / max(height, width)
    if scale < 1.0:
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        xyz = np.stack([np.asarray(Image.fromarray(xyz[..., k], mode="F").resize(size, Image.Resampling.BOX)) for k in range(3)], axis=-1)
    to_ap1 = colorimetry.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, colorimetry.ap1_to_xyz @ np.ones(3))
    ap1 = np.ascontiguousarray((xyz.astype(np.float64) @ to_ap1.T), dtype=np.float32)
    return ap1, {"sensor_long_edge": sensor_long_edge, "half_size_decode": half_size, "processed_long_edge": int(max(ap1.shape[:2]))}


class Pipeline:
    """One render at a time. It keeps the models of the last settings, because a new model reads its tables from disk."""

    def __init__(self) -> None:
        self._models: dict[tuple, object] = {}
        self._frontier_table = None

    def _model(self, tag: tuple, build):
        if tag not in self._models:
            if len(self._models) >= 4:
                self._models.pop(next(iter(self._models)))
            self._models[tag] = build()
        return self._models[tag]

    def print_model(self, settings: RenderSettings) -> fp.FilmPreview:
        return self._model(("print", settings.negative, settings.print_material, settings.scene_light, settings.spectral_prior), lambda: fp.FilmPreview(film_options(settings)))

    def scan_model(self, settings: RenderSettings) -> ScanPreview:
        return self._model(("scan", settings.negative, settings.scene_light, settings.spectral_prior), lambda: ScanPreview(film_options(settings, SCAN_CARRIER_PRINT)))

    def colorimetry(self, settings: RenderSettings):
        return self.print_model(settings).c if settings.method == "print" else self.scan_model(settings).negative.c

    def density_above_base(self, settings: RenderSettings, graded: np.ndarray) -> np.ndarray:
        model = self.scan_model(settings)
        return model.table_apd(model.negative.negative_image(graded)[0]).astype(np.float64) - model.apd_dmin

    def render_array(self, ap1: np.ndarray, settings: RenderSettings) -> np.ndarray:
        """Linear AP1 of the RAW file to sRGB display code. Non-finite output stops with an error."""
        settings.validate()
        graded = np.ascontiguousarray(fp.fk.product_grade(np.ascontiguousarray(ap1, dtype=np.float32), float(settings.exposure_ev), float(settings.contrast), float(settings.saturation)), dtype=np.float32)
        if settings.method == "print":
            image = np.asarray(self.print_model(settings).render(graded)[0], dtype=np.float32)
        else:
            if self._frontier_table is None:
                self._frontier_table = frontier_scan.load_table()
            image = np.asarray(frontier_scan.scan_to_display(self.density_above_base(settings, graded), self._frontier_table, settings.scanner_stage), dtype=np.float32)
        if not np.isfinite(image).all():
            raise FloatingPointError(f"non-finite output: {settings}")
        return image

    def render_file(self, path: Path, settings: RenderSettings, long_edge: int = DEFAULT_LONG_EDGE) -> tuple[np.ndarray, dict]:
        settings.validate()
        start = time.perf_counter()
        colorimetry = self.colorimetry(settings)
        load = time.perf_counter() - start
        start = time.perf_counter()
        ap1, decode = decode_raw(path, colorimetry, long_edge)
        decoded = time.perf_counter() - start
        start = time.perf_counter()
        image = self.render_array(ap1, settings)
        record = {"input": str(path), "settings": asdict(settings), **decode, "model_load_s": round(load, 2), "decode_s": round(decoded, 2), "render_s": round(time.perf_counter() - start, 2)}
        return image, record


def write_outputs(image: np.ndarray, record: dict, path: Path) -> list[Path]:
    """TIFF, 16 bit sRGB code, or JPEG by the suffix, and a parameter file next to it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    code = np.clip(image, 0.0, 1.0)
    if path.suffix.lower() in (".tif", ".tiff"):
        import tifffile

        tifffile.imwrite(path, (code * 65535.0 + 0.5).astype(np.uint16), photometric="rgb", compression="zlib")
    elif path.suffix.lower() in (".jpg", ".jpeg"):
        Image.fromarray((code * 255.0 + 0.5).astype(np.uint8)).save(path, quality=95, subsampling=0)
    else:
        raise ValueError(f"{path}: the output must be .tif or .jpg")
    sidecar = path.with_suffix(path.suffix + ".json")
    sidecar.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    return [path, sidecar]
