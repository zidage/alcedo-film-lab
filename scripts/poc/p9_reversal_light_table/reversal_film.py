"""Reversal film on a light table: linear AP1 to a display image through a colour reversal film, with no print. Step P9, ROADMAP U86.

Input: the reversal profiles of import_reversal_profiles.py, reversal_catalog.json and reversal_physics.json next to this script, and the tables of steps P1 and P2.
Output: library. ReversalPreview.render() gives sRGB display code; the pipeline of the Python viewer (mvp_pipeline.py, method 'light_table') uses it.

A slide is the final image. The camera exposes it, process E-6 develops it to a positive, and the viewer looks at it on a light table through a loupe. The stages:
1. Layer exposure: the spectral input of the print method (rules 'spectral_locus_projection', 'light_like_spectra', 'foliage_spectra', 'relight'), the spread of the light in each layer, and halation, as on a negative.
2. Development, rule 'removed_dye_record'. The published curves are Status A densities that fall with exposure. The dye solve of rule 'dye_amount_curves' runs once on the neutral ramp, with Status A weights, and gives the
   dye amount a_i(log H) of each layer. The record of the model is the removed dye s_i = a_i,max - a_i: the dye that the first developer (a black-and-white negative image) takes from the layer. It rises with exposure, as the
   record of a negative does. So rule 'development_inhibition' acts on it with no change: s_i = F_i(log H_i - sum_j K_ij G * s_j). The first developer of E-6 holds the inhibitor couplers, and a layer that develops more
   silver gives the other layers less silver and so more dye. On a neutral the published curve holds; on a colour this effect raises the saturation, which is the interimage effect of a reversal film.
   The dye amount of a pixel is a_max - s, and each layer exposure sets only the amount of its own dye; the spectral density and every reading follow.
3. Light table, rule 'light_table_view': the transmittance 10^-(base + sum a_i d_i(lambda)) under the light of the table, CIE D50 (ISO 3664, the viewing condition of a transparency; a real light table has a
   fluorescent or LED lamp of this chromaticity, and the CIE spectrum stands for it, inferred), integrated with the CIE 1931 2 degree observer. A table of 65^3 nodes over the record holds the cube root of XYZ.
4. Loupe flare, rule 'loupe_flare': the veiling glare of the magnifier, a share of the light of a wide Gaussian, added in linear light. The option enlarger_flare of FilmOptions holds the share, and enlarger_flare_size the sigma;
   this is the product control 'Enlarger flare' for this method. The value is not measured for any loupe.
5. Display, rule 'clear_film_white': through a loupe the clear film is the brightest light in view, so the eye adapts to it. Its XYZ goes to display white, with Bradford adaptation to D65. The loupe hides the table
   around the slide, so the surround is dark: rule 'dark_surround_on_display' of the cine print (CIECAM02 c = 0.525 against 0.59). Then the display compression of the print and sRGB.

There is no print, so there are no printer lights: a scene light that is not the balance light of the film leaves its cast on the slide (no timing), as on real film.
Rule 'daylight_reversal_balance': each film has rule grey_anchor with the balance light D55. A daylight reversal film is made so that a grey under daylight at the box speed gives the neutral of the film, and a sensitivity chart
cannot fix the level of each layer to the tenth of a stop that a slide shows: a negative has the printer lights to take a level error back, and a slide has none. The chart of E100 is absolute and puts the grey of D55 at
+0.28, +0.48, +0.85 stops (red, green, blue), and its first render was strongly blue (P9 report). The anchor moves only the level of each layer; the neutral of the published curves, the cast of the stock, stays (ROADMAP U36).
At the scene light 'reference' the input is white balanced, so the scene light is the balance light.
Not independent: the light table and the clear film level of a transparency are also in Fotufilm (Apache-2.0) SpectralModel.swift, NegativeViewing.lightBox; this code reuses no code or value from it. See THIRD_PARTY_NOTICES.md.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p2_negative_print"))
import film_preview as fp  # noqa: E402

fk, p0, sr = fp.fk, fp.p0, fp.sr
CATALOG = json.loads((SCRIPT_DIR / "reversal_catalog.json").read_text(encoding="utf-8"))
PHYSICS_PATH = SCRIPT_DIR / "reversal_physics.json"
LIGHT_TABLE_CCT_K = 5000.0  # ISO 3664 transparency viewing: D50
TABLE_CHUNK = 8192
REFERENCE_LIGHT = "reference"
LUMINANCE = np.array([0.2126, 0.7152, 0.0722])  # Y of linear Rec. 709


def load_physics() -> dict:
    return json.loads(PHYSICS_PATH.read_text(encoding="utf-8")) if PHYSICS_PATH.exists() else {}


def reversal_options(film: str, scene_light: str = REFERENCE_LIGHT, physics: dict | None = None, foliage: bool = True, light_spectra: bool = True) -> fp.FilmOptions:
    """The options of one film: rule 'stock_options_from_catalog' of step P6 (grey at 12.5 / ISO lux seconds, the published dyes, spread and inhibition from the modulation transfer), and the rules of this step."""
    entry = CATALOG["films"][film]
    fitted = (physics if physics is not None else load_physics()).get(film, {})
    # Rule 'daylight_reversal_balance'. grey_anchor False is for the measurement of the chart level in fit_reversal_physics.py only.
    if fitted.get("grey_anchor") is False:
        light = dict(grey_anchor=False, balance_light="E_ref", scene_light="E_ref")
    else:
        light = dict(grey_anchor=True, balance_light="D55", scene_light="D55" if scene_light == REFERENCE_LIGHT else fp.PRODUCT_LIGHTS.get(scene_light, scene_light))
    physical = dict(layer_spread_um=tuple(fitted["layer_spread_um"]), inhibition_total=tuple(fitted["inhibition_image"]), inhibition_image=tuple(fitted["inhibition_image"])) if fitted.get("layer_spread_um") else {}
    return fp.FilmOptions(**{**fp.DARKROOM, "negative_profile": film, "midscale_log_h": math.log10(12.5 / entry["iso"]), "negative_dye_basis": "published", "negative_record": "dye_amount",
                             "light_spectra": light_spectra, "foliage": foliage, "scatter_um": 0.0, "adjacency_gain": 0.0, "gamut_limit": fp.P4_GAMUT_LIMIT, "viewing_cct_k": LIGHT_TABLE_CCT_K,
                             "display_white": "print_dmin", "surround_exponent": fp.CINE_SURROUND_EXPONENT, "entry_gamut_compress": True, **light, **physical})


class ReversalPreview(fp.FilmPreview):
    """The negative stages of FilmPreview on the record of rule 'removed_dye_record', and the light table in place of the print."""

    def __init__(self, options: fp.FilmOptions) -> None:
        # Rule 'loupe_flare' acts in linear light after the table, not on the record, so the stages of the negative get no enlarger flare.
        self.loupe_flare, self.loupe_flare_size = float(options.enlarger_flare), float(options.enlarger_flare_size)
        self.options = o = replace(options, enlarger_flare=0.0)
        if o.negative_record != "dye_amount" or o.display_white != "print_dmin":
            raise ValueError("a reversal film needs negative_record 'dye_amount' and display white 'print_dmin' (rule clear_film_white)")
        model_options = p0.ModelOptions(camera_daylight_cct_k=sr.E_REF_NOMINAL_CCT_K, negative_dye_basis=o.negative_dye_basis, negative_density_outside=o.density_outside, paper_dye_outside=o.density_outside,
                                        negative_profile=o.negative_profile, print_profile=o.print_profile, midscale_log_h=o.midscale_log_h, viewing_daylight_cct_k=o.viewing_cct_k, printer_balance_log10=(0.0, 0.0, 0.0))
        self.c = sr.Colorimetry(model_options)
        self.film = self.c.film
        if self.film.film_type != "reversal":
            raise ValueError(f"{o.negative_profile} is not a reversal film")
        fp.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.status_curves = list(self.film.negative_curves.values())
        self.negative_curves = self._removed_dye_curves()
        self._prepare_inhibition()
        self.paper_curves = []
        self.scene_spectrum = self.light(o.scene_light)
        self.layer_gain = self._camera_filter()
        self.uv_table = self._load_uv_table()
        self.density_grid, self.print_table, self.table_counts = self._build_light_table()
        self._prepare_display()
        self._prepare_kernels()
        self._grade_grey = None

    # --- development ---------------------------------------------------------------------------

    def _removed_dye_curves(self) -> list[p0.CharacteristicCurve]:
        """Rule 'removed_dye_record': the dye amounts of the neutral ramp with Status A weights, on one log H grid, as removed dye. Ends: each published curve keeps its end values."""
        f = self.film
        step = self.status_curves[0].log_h[1] - self.status_curves[0].log_h[0]
        start, stop = min(c.log_h[0] for c in self.status_curves), max(c.log_h[-1] for c in self.status_curves)
        log_h = start + step * np.arange(int(round((stop - start) / step)) + 1)
        status_a = np.stack([np.interp(log_h, c.log_h, c.density) for c in self.status_curves], axis=1)
        base = f.status_density(f.negative_dmin, f.w_status_a)
        amounts, residual = fp.solve_amounts(status_a - f.negative_curve_dmin + base, f.negative_dmin, f.negative_dyes, f.w_status_a)
        falling = np.minimum.accumulate(amounts, axis=0)
        self.dye_max = falling[0].copy()
        self.dye_curve_info = {"largest_solve_residual": float(residual.max()), "largest_rise_removed": float((amounts - falling).max()), "dye_amount_range": [falling.min(axis=0).tolist(), falling.max(axis=0).tolist()]}
        return [p0.CharacteristicCurve(log_h, self.dye_max[k] - falling[:, k]) for k in range(3)]

    def _camera_filter(self) -> np.ndarray:
        """Rule grey_anchor with no printer: one gain per layer, so that an 18 % grey of the balance light lands on each curve at the exposure of the grey. With no anchor, the chart sets the level."""
        o = self.options
        if not o.grey_anchor:
            if o.scene_light != "E_ref":
                raise ValueError("scene_light needs grey_anchor")
            return np.ones(3)
        f = self.film
        gain = 10.0 ** (f.options.midscale_log_h - f.negative_criterion_log_h) / self.c.layer_exposure(0.18 * self.light(o.balance_light))
        grey = gain * self.c.layer_exposure(0.18 * self.scene_spectrum)
        self.scene_grey_stops = np.log2(grey / 10.0 ** (f.options.midscale_log_h - f.negative_criterion_log_h))
        return gain

    # --- light table ---------------------------------------------------------------------------

    def record_to_status_a(self, record: np.ndarray) -> np.ndarray:
        """Status A of the slide at a record of removed dye (N, 3), on the scale of the published curves."""
        f = self.film
        amounts = np.maximum(self.dye_max - np.atleast_2d(record), 0.0)
        return f.status_density(f.negative_spectral_density(amounts), f.w_status_a) - f.status_density(f.negative_dmin, f.w_status_a) + f.negative_curve_dmin

    def light_table_xyz(self, record: np.ndarray) -> np.ndarray:
        """Rule 'light_table_view': XYZ (Y of the bare table = 100) of the slide at a record of removed dye (N, 3), with no surround rule."""
        f = self.film
        weights = f.w_viewing[f.viewing_name]
        support = fp.spectral_support(weights)
        dmin, dyes, w = f.negative_dmin[support], f.negative_dyes[:, support], weights[:, support]
        record = np.atleast_2d(record)
        out = np.empty((len(record), 3))
        for begin in range(0, len(record), TABLE_CHUNK):
            amounts = np.maximum(self.dye_max - record[begin:begin + TABLE_CHUNK], 0.0)
            out[begin:begin + TABLE_CHUNK] = (10.0 ** -(dmin + amounts @ dyes)) @ w.T
        return 100.0 * out / weights[1].sum()

    def _build_light_table(self) -> tuple[list[np.ndarray], np.ndarray, dict]:
        grid = [np.linspace(0.0, float(c.density.max()), fp.DENSITY_NODES) for c in self.negative_curves]
        nodes = np.stack(np.meshgrid(*grid, indexing="ij"), axis=-1).reshape(-1, 3)
        xyz = self.light_table_xyz(nodes)
        if not np.isfinite(xyz).all() or (xyz < 0.0).any():
            raise FloatingPointError(f"the light table of {self.options.negative_profile} has values that are not finite or negative")
        return grid, np.cbrt(xyz).reshape(fp.DENSITY_NODES, fp.DENSITY_NODES, fp.DENSITY_NODES, 3), {"nodes": fp.DENSITY_NODES ** 3}

    def print_dmin_xyz(self) -> np.ndarray:
        """Rule 'clear_film_white': XYZ of the clear film, the record at the top of each removed dye curve."""
        return self.light_table_xyz(np.array([[float(c.density.max()) for c in self.negative_curves]]))[0]

    def print_xyz(self, density: np.ndarray) -> np.ndarray:
        shape = density.shape
        return self.light_table_xyz(density.reshape(-1, 3)).reshape(shape)

    def surround(self, rgb: np.ndarray) -> np.ndarray:
        """Rule 'dark_surround_on_display' in linear display light, where the clear film has Y = 1: the luminance takes the exponent, and the chromaticity stays."""
        exponent = self.options.surround_exponent
        if exponent == 1.0:
            return rgb
        y = np.maximum(rgb @ LUMINANCE.astype(np.float32), 1e-12)
        return (rgb * (y ** np.float32(exponent - 1.0))[..., None]).astype(np.float32)

    def render(self, ap1: np.ndarray, detailed: bool = False) -> tuple[np.ndarray, dict]:
        """Linear AP1 to sRGB, through the kernels."""
        o = self.options
        shape = ap1.shape
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        if image.ndim == 2:
            image = image[None]
        record, stats = self.negative_image(image)
        rgb = fk.print_display(record, self._print_f32, self._grid_start, self._grid_step, self.xyz_to_display)
        if self.loupe_flare and min(image.shape[:2]) >= 16:
            rgb = ((1.0 - self.loupe_flare) * rgb + self.loupe_flare * fk.gaussian_blur(rgb, self.loupe_flare_size * max(image.shape[:2]))).astype(np.float32)
        rgb = self.surround(rgb)
        if detailed:
            stats["gamut_distance_p999"] = np.percentile(fp.gamut_distance(rgb).reshape(-1, 3), 99.9, axis=0).round(3).tolist()
        out, before, after = fk.finish_display(rgb, bool(o.gamut_compress), np.array(o.gamut_threshold), np.array(o.gamut_limit), float(o.gamut_power))
        stats["display_clipped"] = int(before)
        if o.gamut_compress:
            stats["display_clipped_after_compression"] = int(after)
        return (out[0] if len(shape) == 2 else out), stats
