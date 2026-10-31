"""Film preview renderer of step P2: linear AP1 to a display image through Portra 400 and Endura.

Input: the P0 evaluator and profiles, the P1 reconstruction and reflectance datasets, RAW files.
Output: library used by render_review_images.py. Tables are cached in build/tmp/p2/.

Step: P2, README section 8, with decision U17: the user reviews the rendered appearance first.
This is a review tool. It uses reduced images and CPU tables; it is not the product path.

Execution: render() and the print table use the compiled kernels of fast_kernels.py. The array methods of this class
(layer_exposure, negative_density, direct_print_xyz, print_xyz, reference_render) are the reference;
check_fast_kernels.py compares the two.

Stages (each one stays separate):
1. Input: RAW through LibRaw with the camera white balance, to XYZ (D65), Bradford adaptation to the
   ACES white, linear AP1. The input is white balanced, so the reference light is E_ref for all
   input of the first review. Exposure: rule 'center_weighted_exposure' (center-weighted mean of
   linear Y = 0.18). Function product_input() then applies the default grade of Alcedo Studio (contrast
   +15, saturation 1.3), because the DRT receives the graded image in the product. The grade does not apply to a raster file.
2. Layer exposure: measured_prior_local_nonnegative with rule 'spectral_locus_projection' (P1),
   compiled to a table of Q / Y over u'v' (spectral shape depends on chromaticity only).
3. Negative: Status M from the Portra curves. Rule 'negative_curve_limits': below the toe the first
   value (P0); above the published end the last value (counted). Option interlayer_gain: differences
   between the layers' log exposures grow by this share before the curves. It stands for the colour
   gain of development inhibitor couplers; it is an approximation with no spatial part, and a neutral
   stays neutral. The value follows the comparison with spektrafilm output (U18); it is a review
   control, not a measurement.
4. Dyes, printing, print dyes, viewing: P0 stages, compiled to a table over negative Status M.
   Rule 'dye_solve_nearest': where non-negative dye amounts cannot reach a density triple, the
   nearest non-negative amounts are used (counted). Rule 'paper_curve_limits': paper exposure
   outside the curve keeps the end value (counted).
5. Display: print XYZ under D50 viewing, a perfect reflector under the viewing light to display white
   with Bradford adaptation to D65 (option display_white), linear Rec. 709, clip (counted), sRGB
   encoding. The paper base then keeps its own reflectance and colour, as a print next to a white
   reference does. The option 'paper' maps the paper white to display white. Rule
   'rgc_style_display_compression' (option gamut_compress): the method of the ACES Reference Gamut
   Compression on the linear Rec. 709 of the print. It is not the standard ACES RGC: the domain is
   the display, after the print, and the limits are measured on this chain. The rest of the values
   above 1 are clipped (counted).

Review controls (U17). They are named here so that they are not read as measurements:
- scene_flare: veiling glare of the taking lens, a neutral addition to AP1 before the film (physical
  effect, value not measured for any lens).
- print_contrast: creative control. The paper log exposure is scaled about the exposure of the
  balance grey, which has the effect of a softer printing grade. The published Endura curve is
  print_contrast = 1.
- viewing_flare: surface reflection of the print, added to the reflectance (P0 item I13; physical
  effect, value not measured).

Darkroom controls (README U19). Each one is a step of a real process. The values are review controls,
not measurements. Image-plane steps use the frame width of the option frame_mm:
- scatter_um, halation, halation_um: light scatter in the emulsion and light that returns from the film
  base, in layer exposure, before development. Halation reaches the red-sensitive layer first.
- adjacency_gain, adjacency_um: developer exhausts near dense areas, so edges gain density (Eberhard
  effect), in negative density.
- enlarger_flare, enlarger_flare_size: stray light of the enlarger lens, in the transmittance of the
  negative. Light from thin areas veils the dense areas.
- print_flash: a uniform exposure of the paper before the print, as a share of the balance exposure.
  It lowers the contrast of the print highlights (part of the print table).
- print_contrast is the paper grade, viewing_flare the surface of the paper.

Stocks: STOCKS holds the material choices. Rule 'grey_anchor' (option grey_anchor): one gain per layer, so
that an 18 % grey under the balance light of the stock (balance_light) lands on each characteristic curve
at the stated exposure 12.5 / ISO lux seconds. The digitized sensitivities of these stocks do not fix the
absolute level of each layer: without the rule the grey was up to 0.6 stops off, different per layer. The
gains belong to the stock and do not follow the scene.

Rule 'neutral_printing_gain' (option neutral_printing): one gain per paper layer on the paper log exposure about the
balance exposure, so that a neutral negative ramp has the same paper log exposure slope in each layer. The published
curves, the dye data and the lamp gave a blue slope about 20 % lower than green on 2383. That is a yellow highlight and
a blue shadow on a neutral, and a real camera stock and print stock are designed to avoid this, so it is treated as an
error of the data and of the printer model. It is computed on the curves, so a scene light can still cause a crossover.

Scene light (README U20). The input is white balanced, so it holds a reflectance colour and not the light.
Rule 'relight': the reflectance shape of the reconstruction is multiplied by the spectrum of scene_light
(Y of the light = 1), and the layers integrate that radiance. A grey under a light that is not the balance
light of the stock lands on the curves at different places per layer, as on real film. Option print_timing:
the printer lights remove this share of the cast at mid grey (1: a neutral mid grey, 0: uncorrected). The
position on the curves stays, so the shadows and the highlights can keep a colour (crossover), and a
spiky light keeps its effect on colours. RAW white can select a daylight or Planckian light. It cannot show
that a light is fluorescent or LED, so those are an explicit choice.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

SCRIPT_DIR = Path(__file__).resolve().parent
P1_DIR = SCRIPT_DIR.parent / "p1_spectral_input"
sys.path.insert(0, str(P1_DIR))
sys.path.insert(0, str(SCRIPT_DIR))
import fast_kernels as fk  # noqa: E402
import spectral_datasets as sd  # noqa: E402
import spectral_reconstruction as sr  # noqa: E402
from spectral_reconstruction import p0  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parents[2]
CACHE_DIR = REPO_ROOT / "build" / "tmp" / "p2" / "tables"
UV_NODES = 192
UV_MAX = (0.66, 0.62)
DENSITY_NODES = 65
SOLVE_ITERATIONS = 16
UV_SMOOTH_BLEND = (0.05, 0.15)  # u'v' distance from the white where sigma_near changes to sigma_far
METER_CAP = 16.0
# Product default of a RAW file in Alcedo Studio: alcedo_studio/src/include/edit/graph/pipeline_document.hpp.
# A raster file has a neutral grade. The review uses rule 'center_weighted_exposure' in place of the +1.5 EV.
PRODUCT_CONTRAST = 15.0
PRODUCT_SATURATION = 1.3

BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
XYZ_D65 = np.array([0.95047, 1.0, 1.08883])
XYZ_TO_REC709 = np.array([[3.2404542, -1.5371385, -0.4985314], [-0.9692660, 1.8760108, 0.0415560], [0.0556434, -0.2040259, 1.0572252]])


def bradford_matrix(source_xyz: np.ndarray, target_xyz: np.ndarray) -> np.ndarray:
    gain = (BRADFORD @ target_xyz) / (BRADFORD @ source_xyz)
    return np.linalg.inv(BRADFORD) @ np.diag(gain) @ BRADFORD


NOT_IN_PRINT_TABLE = ("uv_smooth", "gamut_compress", "gamut_threshold", "gamut_limit", "gamut_power", "scene_flare", "display_white", "frame_mm", "scatter_um", "halation", "halation_um",
                      "adjacency_gain", "adjacency_um", "enlarger_flare", "enlarger_flare_size")


@dataclass(frozen=True)
class FilmOptions:
    """Choices that the sources do not fix (P0 report section 5)."""

    negative_dye_basis: str = "band_split"  # spectral_film_lut method (U11)
    density_outside: str = "gaussian_tail"  # spectral_film_lut method (U11)
    print_midscale_status_a: float = 0.75  # P0: the 18 % grey prints to this Status A density
    printer_lamp: str = "A"
    print_contrast: float = 1.0
    viewing_flare: float = 0.0
    scene_flare: float = 0.0  # not part of the print table
    display_white: str = "reflector"  # not part of the print table; 'reflector' or 'paper'
    interlayer_gain: float = 0.2  # part of the print table: the printer balance under a scene light uses it
    negative_profile: str = "kodak_portra_400"
    print_profile: str = "kodak_endura_premier"
    midscale_log_h: float = -1.44  # P0: exposure of the 18 % grey
    viewing_cct_k: float = 5000.0
    grey_anchor: bool = False
    balance_light: str = "E_ref"
    scene_light: str = "E_ref"
    print_timing: float = 1.0
    print_flash: float = 0.0
    neutral_printing: bool = False
    gamut_compress: bool = False  # not part of the print table; False: clip
    gamut_threshold: tuple[float, float, float] = (0.815, 0.803, 0.880)  # ACES RGC values (cyan, magenta, yellow)
    gamut_limit: tuple[float, float, float] = (1.147, 1.264, 1.312)  # ACES RGC values
    gamut_power: float = 1.2  # ACES RGC value
    frame_mm: float = 36.0  # not part of the print table; the long side of the frame
    scatter_um: float = 0.0  # not part of the print table; the next ones too
    halation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    halation_um: float = 120.0
    adjacency_gain: float = 0.0
    adjacency_um: float = 60.0
    enlarger_flare: float = 0.0
    enlarger_flare_size: float = 0.1  # sigma, share of the long side
    uv_smooth: tuple[float, float] = (0.0, 0.0)  # not part of the print table; sigma_near, sigma_far of rule 'smooth_reflectance_table'

    def key(self) -> str:
        fields = {k: v for k, v in asdict(self).items() if k not in NOT_IN_PRINT_TABLE}
        return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:12]


# Review options after the darkroom comparison (README U19), for RAW input through product_input().
# The input is product_input(): the default grade of the product comes before the film. So the chain has no interlayer
# gain, and print_contrast takes back about the mid-grey slope of the grade (0.92 / 2^0.15 = 0.83).
DARKROOM = dict(uv_smooth=(0.006, 0.025), interlayer_gain=0.0, print_flash=0.02, print_contrast=0.85, viewing_flare=0.003, scatter_um=10.0,
                halation=(0.03, 0.008, 0.0), adjacency_gain=0.25, enlarger_flare=0.01, gamut_compress=True)

# Printer lights of the cine prints. The LAD aim of 2383 (Status A about 1.06) is for a dark cinema. This value
# follows the comparison with spektrafilm on a display (U18); it is a review control.
CINE_GREY_STATUS_A = 0.85

# Scene lights that the user selects (README U21). Default: daylight. One representative CIE spectrum per type;
# real lamps of a type differ, and this table does not claim to match a lamp.
PRODUCT_LIGHTS = {"daylight": "D55", "tungsten": "T3200", "fluorescent": "FL11", "led": "LED-B3", "sodium": "HP1"}

# Scenes that the user selects in place of one light (README U22, step P3). Each one is a global mixture of named
# spectra; the weights are shares of the luminance and the author's choice, not measurements of a place.
# One spectrum applies to every pixel of the image: see the P3 report for what this cannot do.
SCENE_PRESETS = {
    "street_mixed": (("T2800", 0.3), ("LED-B3", 0.4), ("HP1", 0.3)),
    "street_sodium": (("HP1", 0.7), ("T2800", 0.15), ("LED-B3", 0.15)),
    "street_led": (("LED-B3", 0.75), ("T2800", 0.15), ("HP1", 0.1)),
    "interior_warm": (("T2800", 0.7), ("LED-B3", 0.3)),
    "interior_office": (("FL11", 0.5), ("LED-B3", 0.5)),
}

STOCKS = {
    "portra400_endura": {},
    # Exposure of the grey: 12.5 / ISO lux seconds. Projection at D65.
    "5207_2383": dict(negative_profile="kodak_5207", print_profile="kodak_2383", midscale_log_h=float(np.log10(12.5 / 250)),
                      print_midscale_status_a=CINE_GREY_STATUS_A, viewing_cct_k=6500.0, grey_anchor=True, balance_light="D55", neutral_printing=True),
    "5219_2383": dict(negative_profile="kodak_5219", print_profile="kodak_2383", midscale_log_h=float(np.log10(12.5 / 500)),
                      print_midscale_status_a=CINE_GREY_STATUS_A, viewing_cct_k=6500.0, grey_anchor=True, balance_light="T3200", neutral_printing=True),
}


def solve_amounts(target: np.ndarray, base_density: np.ndarray, dyes: np.ndarray, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Batched projected Newton: amounts >= 0 with Status(base + a dyes) = target.

    Returns (amounts, max residual per sample). The weights are the Status integration weights."""
    total = weights.sum(axis=1)
    a = np.maximum(target, 0.0)
    residual = np.full(len(a), np.inf)
    for _ in range(SOLVE_ITERATIONS):
        t = 10.0 ** (-(base_density[None, :] + a @ dyes))
        s = t @ weights.T
        r = -np.log10(s / total) - target
        residual = np.abs(r).max(axis=1)
        jac = np.einsum("nl,il,jl->nij", t, weights, dyes) / s[:, :, None]
        step = np.linalg.solve(jac + 1e-9 * np.eye(3)[None], r[..., None])[..., 0]
        a = np.maximum(a - step, 0.0)
    t = 10.0 ** (-(base_density[None, :] + a @ dyes))
    r = -np.log10((t @ weights.T) / total) - target
    return a, np.abs(r).max(axis=1)


class FilmPreview:
    def __init__(self, options: FilmOptions | None = None) -> None:
        self.options = options or FilmOptions()
        o = self.options
        model_options = p0.ModelOptions(camera_daylight_cct_k=sr.E_REF_NOMINAL_CCT_K, negative_dye_basis=o.negative_dye_basis,
                                        negative_density_outside=o.density_outside, paper_dye_outside=o.density_outside,
                                        print_midscale_status_a=o.print_midscale_status_a, printer_lamp=o.printer_lamp,
                                        negative_profile=o.negative_profile, print_profile=o.print_profile,
                                        midscale_log_h=o.midscale_log_h, viewing_daylight_cct_k=o.viewing_cct_k)
        self.c = sr.Colorimetry(model_options)
        self.film = self.c.film
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.negative_curves = list(self.film.negative_curves.values())
        self.paper_curves = list(self.film.paper_curves.values())
        self.scene_spectrum = self.light(o.scene_light)
        self.layer_gain = self._camera_filter()
        self.printing_gain = self._printing_gain()
        self.uv_table = self._load_uv_table()
        self.density_grid, self.print_table, self.table_counts = self._load_print_table()
        self._prepare_display()
        self._prepare_kernels()

    def light(self, name: str) -> np.ndarray:
        """Spectrum with Y = 1. 'E_ref'; 'D55' (CIE daylight, 100 K units); 'T3200' (Planckian); a CIE FL, LED or HP name."""
        wl = self.c.wavelengths
        if name in SCENE_PRESETS:
            # Rule 'scene_mixture': the weights are shares of the luminance, because each light has Y = 1.
            return sum(weight * self.light(light) for light, weight in SCENE_PRESETS[name])
        if name == "E_ref":
            spectrum = self.c.e_ref
        elif name[0] == "D" and name[1:].isdigit():
            spectrum = p0.cie_daylight_relative_spd(float(name[1:]) * 100.0, wl)
        elif name[0] == "T" and name[1:].isdigit():
            spectrum = wl ** -5.0 / np.expm1(1.4388e7 / (wl * float(name[1:])))
        else:
            spectrum = np.interp(wl, sd.GRID_NM, sd.cie_light_sources()[name], left=0.0, right=0.0)
        return spectrum / self.c.xyz(spectrum)[1]

    def _camera_filter(self) -> np.ndarray:
        o = self.options
        if not o.grey_anchor:
            if o.scene_light != "E_ref":
                raise ValueError("scene_light needs grey_anchor")
            return np.ones(3)
        f = self.film
        gain = 10.0 ** (f.options.midscale_log_h - f.negative_criterion_log_h) / self.c.layer_exposure(0.18 * self.light(o.balance_light))
        self._neutral_log_q = f.options.midscale_log_h - f.negative_criterion_log_h

        def balance(status_m: np.ndarray) -> np.ndarray:
            unbalanced = f.paper_layer_exposure_unbalanced(f.negative_spectral_density(f.negative_dye_amounts(status_m)))
            target = np.array([c.log_h_at(f.options.print_midscale_status_a) for c in f.paper_curves.values()])
            return target - np.log10(unbalanced)

        reference = balance(np.array([c.density_at(f.options.midscale_log_h) for c in f.negative_curves.values()]))
        grey = gain * self.c.layer_exposure(0.18 * self.scene_spectrum)
        self.scene_grey_stops = np.log2(grey / 10.0 ** self._neutral_log_q)
        f.printer_balance_log10 = reference + o.print_timing * (balance(self.negative_density(grey[None])[0][0]) - reference)
        return gain

    def _printing_gain(self) -> np.ndarray:
        # Rule 'neutral_printing_gain': see the header. Range: 1.0 log H on each side of the grey.
        if not self.options.neutral_printing:
            return np.ones(3)
        f = self.film
        log_h = f.options.midscale_log_h + np.linspace(-1.0, 1.0, 21)
        status_m = np.stack([np.interp(log_h, c.log_h, c.density) for c in self.negative_curves], axis=1)
        base = f.status_density(f.negative_dmin, f.w_status_m)
        amounts, _ = solve_amounts(status_m - f.negative_curve_dmin + base, f.negative_dmin, f.negative_dyes, f.w_status_m)
        paper = f.paper_log_exposure(f.negative_spectral_density(amounts))
        slopes = np.array([np.polyfit(log_h, paper[:, k], 1)[0] for k in range(3)])
        return slopes[1] / slopes

    # --- stage 2 ------------------------------------------------------------------------------

    def _reconstruction(self) -> sr.MeasuredPriorLocalNonnegative:
        sets = sd.load_all_reflectance_sets()
        train = {k: s.reflectance for k, s in sets.items()}
        moment, _ = sr.prior_second_moment(self.c, train)
        return sr.MeasuredPriorLocalNonnegative(self.c, moment, train)

    @staticmethod
    def uv_axes() -> tuple[np.ndarray, np.ndarray]:
        return np.linspace(0.0, UV_MAX[0], UV_NODES), np.linspace(0.0, UV_MAX[1], UV_NODES)

    def _load_reflectance_table(self) -> np.ndarray:
        """Reflectance shape on the nodes of the spectral grid, for Y = 1 under E_ref, over u'v'."""
        path = CACHE_DIR / "reflectance_over_uv.npy"
        if path.exists():
            return np.load(path)
        method = self._reconstruction()
        u, v = self.uv_axes()
        uu, vv = np.meshgrid(u, np.maximum(v, 1e-3), indexing="ij")
        xyz = np.stack([9 * uu / (4 * vv), np.ones_like(uu), (12 - 3 * uu - 20 * vv) / (4 * vv)], axis=-1).reshape(-1, 3)
        e_ref = self.c.e_ref
        rho = np.zeros((len(xyz), len(e_ref)), dtype=np.float32)
        for start in range(0, len(xyz), 4096):
            rec = method.reconstruct(xyz[start:start + 4096] @ self.c.xyz_to_ap1.T)
            if not rec.domain.all():
                raise RuntimeError("uv table: a node is outside the domain of the reconstruction")
            rho[start:start + 4096] = np.where(e_ref > 0, rec.radiance / np.maximum(e_ref, 1e-30), 0.0)
            print(f"uv table {start + 4096} / {len(xyz)}", flush=True)
        np.save(path, rho)
        return rho

    def _load_uv_table(self) -> np.ndarray:
        # Rule 'relight': see the header. Fast, so that a light does not need a new reconstruction.
        rho = self._load_reflectance_table().astype(np.float64)
        if any(self.options.uv_smooth):
            near, far = self.options.uv_smooth
            path = CACHE_DIR / f"reflectance_over_uv_smooth_{near}_{far}.npy"
            if path.exists():
                rho = np.load(path).astype(np.float64)
            else:
                white = self.c.xyz(self.c.e_ref)
                white_uv = np.array([4.0 * white[0], 9.0 * white[1]]) / (white[0] + 15.0 * white[1] + 3.0 * white[2])
                rho = smooth_reflectance_table(rho, near, far, white_uv, self.c.w_xyz * self.c.e_ref)
                np.save(path, rho.astype(np.float32))
        return self.c.layer_exposure(rho * self.scene_spectrum[None, :]).reshape(UV_NODES, UV_NODES, 3)

    def layer_exposure(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        shape = ap1.shape
        xyz = ap1.reshape(-1, 3) @ self.c.ap1_to_xyz.T
        projection = self._projection()
        located, moved, not_positive = projection.apply(xyz)
        q = np.zeros_like(located)
        positive = ~not_positive
        uv = sr.MeasuredPriorLocal.chromaticity_uv(located[positive])
        coordinates = np.stack([uv[:, 0] / UV_MAX[0], uv[:, 1] / UV_MAX[1]]) * (UV_NODES - 1)
        for k in range(3):
            q[positive, k] = self.layer_gain[k] * located[positive, 1] * map_coordinates(self.uv_table[..., k], coordinates, order=1, mode="nearest")
        return q.reshape(shape), {"moved_by_rule": int(moved.sum()), "y_not_positive": int(not_positive.sum())}

    def _projection(self) -> sr.LocusProjection:
        if not hasattr(self, "_projection_cache"):
            self._projection_cache = sr.LocusProjection(self.c)
        return self._projection_cache

    # --- stage 3 ------------------------------------------------------------------------------

    def negative_density(self, q: np.ndarray) -> tuple[np.ndarray, int]:
        out = np.empty_like(q)
        above = 0
        crit = self.film.negative_criterion_log_h
        log_q = np.log10(np.maximum(q, 1e-300))
        gain = self.options.interlayer_gain
        if gain:
            # measured from the neutral's own layer ratios, so that a neutral stays neutral
            if not hasattr(self, "_neutral_log_q"):
                self._neutral_log_q = np.log10(self.layer_exposure(np.ones((1, 3)))[0][0])
            difference = log_q - self._neutral_log_q
            log_q = log_q + gain * (difference - difference.mean(axis=-1, keepdims=True))
        for k, curve in enumerate(self.negative_curves):
            log_h = crit[k] + log_q[..., k]
            above += int((log_h > curve.log_h[-1]).sum())
            out[..., k] = np.interp(log_h, curve.log_h, curve.density)
        return out, above

    # --- stage 4 ------------------------------------------------------------------------------

    def direct_print_xyz(self, density: np.ndarray) -> tuple[np.ndarray, dict]:
        """Negative Status M (N, 3) to print XYZ (Y of the perfect diffuser = 100), through the stages."""
        film = self.film
        d = np.atleast_2d(density)
        base = film.status_density(film.negative_dmin, film.w_status_m)
        target = d - film.negative_curve_dmin + base
        a, r_negative = solve_amounts(target, film.negative_dmin, film.negative_dyes, film.w_status_m)
        negative = film.negative_spectral_density(a)
        log_h = film.paper_log_exposure(negative)
        aim = np.array([c.log_h_at(self.options.print_midscale_status_a) for c in self.paper_curves])
        log_h = aim + self.options.print_contrast * self.printing_gain * (log_h - aim)
        if self.options.print_flash:
            log_h = np.log10(10.0 ** log_h + self.options.print_flash * 10.0 ** aim)
        status_a = np.empty_like(log_h)
        clipped = 0
        for k, curve in enumerate(self.paper_curves):
            clipped += int(((log_h[:, k] < curve.log_h[0]) | (log_h[:, k] > curve.log_h[-1])).sum())
            status_a[:, k] = np.interp(log_h[:, k], curve.log_h, curve.density)
        b, r_print = solve_amounts(status_a, film.paper_base, film.paper_dyes, film.w_status_a)
        xyz = film.viewed_xyz(film.print_spectral_density(b)) + self.options.viewing_flare * film.white_xyz()
        return xyz, {
            "negative_not_reached": int((r_negative > 1e-4).sum()), "print_not_reached": int((r_print > 1e-4).sum()),
            "paper_exposure_outside_curve": clipped}

    def _print_nodes(self, density: np.ndarray) -> tuple[np.ndarray, dict]:
        """The kernel form of direct_print_xyz. Each integral uses only the nodes where its weights are not zero."""
        f, o = self.film, self.options

        def support(weights: np.ndarray) -> np.ndarray:
            return np.flatnonzero(np.any(weights != 0.0, axis=0))

        m, pr, st, vi = support(f.w_status_m), support(f.w_printing), support(f.w_status_a), support(f.w_viewing[f.viewing_name])
        w_view = f.w_viewing[f.viewing_name]
        base = f.status_density(f.negative_dmin, f.w_status_m)
        length = max(len(c.density) for c in self.paper_curves)
        curves = np.stack([np.pad(c.density, (0, length - len(c.density)), mode="edge") for c in self.paper_curves])
        aim = np.array([c.log_h_at(o.print_midscale_status_a) for c in self.paper_curves])
        xyz, not_negative, not_print, outside = fk.print_nodes(
            density.astype(np.float64), base - f.negative_curve_dmin, SOLVE_ITERATIONS,
            f.negative_dmin[m], f.negative_dyes[:, m], f.w_status_m[:, m],
            f.negative_dmin[pr], f.negative_dyes[:, pr], f.w_printing[:, pr], np.asarray(f.printer_balance_log10, dtype=np.float64), aim, float(o.print_contrast) * self.printing_gain, float(o.print_flash),
            np.array([c.log_h[0] for c in self.paper_curves]), curves, np.array([len(c.density) for c in self.paper_curves]), float(self.paper_curves[0].log_h[1] - self.paper_curves[0].log_h[0]),
            f.paper_base[st], f.paper_dyes[:, st], f.w_status_a[:, st],
            f.paper_base[vi], f.paper_dyes[:, vi], w_view[:, vi], o.viewing_flare * f.white_xyz(), 100.0 / w_view[1].sum())
        return xyz, {"negative_not_reached": int(not_negative), "print_not_reached": int(not_print), "paper_exposure_outside_curve": int(outside)}

    def _load_print_table(self) -> tuple[list[np.ndarray], np.ndarray, dict]:
        path = CACHE_DIR / f"print_table_{self.options.key()}.npz"
        grid = [np.linspace(c.density.min(), c.density.max(), DENSITY_NODES) for c in self.negative_curves]
        if path.exists():
            z = np.load(path)
            return grid, z["table"], json.loads(str(z["counts"]))
        rr, gg, bb = np.meshgrid(*grid, indexing="ij")
        d = np.stack([rr, gg, bb], axis=-1).reshape(-1, 3)
        xyz, counts = self._print_nodes(d)
        counts["nodes"] = len(d)
        table = np.cbrt(xyz).reshape(DENSITY_NODES, DENSITY_NODES, DENSITY_NODES, 3)
        np.savez(path, table=table, counts=json.dumps(counts))
        return grid, table, counts

    def print_xyz(self, density: np.ndarray) -> np.ndarray:
        shape = density.shape
        d = density.reshape(-1, 3)
        coordinates = np.stack([(d[:, k] - self.density_grid[k][0]) / (self.density_grid[k][1] - self.density_grid[k][0]) for k in range(3)])
        out = np.stack([map_coordinates(self.print_table[..., k], coordinates, order=1, mode="nearest") for k in range(3)], axis=1)
        return (out ** 3).reshape(shape)

    # --- stage 5 ------------------------------------------------------------------------------

    def _prepare_display(self) -> None:
        # Paper white: the print of the densest negative (lowest paper exposure) in the table.
        top = np.array([g[-1] for g in self.density_grid])
        self.paper_white = self.print_xyz(top[None])[0]
        white = {"reflector": self.film.white_xyz(), "paper": self.paper_white}[self.options.display_white]
        self.xyz_to_display = XYZ_TO_REC709 @ bradford_matrix(white / white[1], XYZ_D65) / white[1]

    def display_linear(self, xyz: np.ndarray) -> np.ndarray:
        return xyz @ self.xyz_to_display.T

    # --- image-plane steps ----------------------------------------------------------------------

    def _pixel_um(self, image: np.ndarray) -> float:
        return self.options.frame_mm * 1000.0 / max(image.shape[:2])

    def _exposure_spread(self, q: np.ndarray) -> np.ndarray:
        o = self.options
        pixel = self._pixel_um(q)
        if o.scatter_um:
            q = gaussian_filter(q, (o.scatter_um / pixel, o.scatter_um / pixel, 0))
        if any(o.halation):
            strength = np.array(o.halation)
            q = (1 - strength) * q + strength * gaussian_filter(q, (o.halation_um / pixel, o.halation_um / pixel, 0))
        return q

    def _development_and_enlarger(self, density: np.ndarray) -> np.ndarray:
        o = self.options
        if o.adjacency_gain:
            sigma = o.adjacency_um / self._pixel_um(density)
            density = density + o.adjacency_gain * (density - gaussian_filter(density, (sigma, sigma, 0)))
        if o.enlarger_flare:
            sigma = o.enlarger_flare_size * max(density.shape[:2])
            t = 10.0 ** -density
            t = (1 - o.enlarger_flare) * t + o.enlarger_flare * gaussian_filter(t, (sigma, sigma, 0))
            density = -np.log10(t)
        return density

    def _prepare_kernels(self) -> None:
        o = self.options
        for curve in self.negative_curves + self.paper_curves:
            if not np.allclose(np.diff(curve.log_h), curve.log_h[1] - curve.log_h[0], atol=1e-9):
                raise ValueError("the kernels need characteristic curves on a uniform log H grid")
        projection = self._projection()
        self._room = -(projection.offsets + projection.normals @ projection.white)
        self._uv_f32 = self.uv_table.astype(np.float32)
        self._print_f32 = self.print_table.astype(np.float32)
        length = max(len(c.density) for c in self.negative_curves)
        self._curves_f64 = np.stack([np.pad(c.density, (0, length - len(c.density)), mode="edge") for c in self.negative_curves])
        self._curve_lengths = np.array([len(c.density) for c in self.negative_curves])
        self._curve_start = np.array([c.log_h[0] for c in self.negative_curves])
        self._curve_step = float(self.negative_curves[0].log_h[1] - self.negative_curves[0].log_h[0])
        if o.interlayer_gain and not hasattr(self, "_neutral_log_q"):
            self._neutral_log_q = np.log10(self.layer_exposure(np.ones((1, 3)))[0][0])
        self._neutral = np.asarray(getattr(self, "_neutral_log_q", np.zeros(3)), dtype=np.float64)
        self._grid_start = np.array([g[0] for g in self.density_grid])
        self._grid_step = np.array([g[1] - g[0] for g in self.density_grid])

    def negative_image(self, image: np.ndarray) -> tuple[np.ndarray, dict]:
        """Linear AP1 (rows, columns, 3; float32) to negative Status M, through the kernels. The print and the scan start here."""
        o = self.options
        # Rule 'no_image_plane_steps_on_ramps': a test ramp (fewer than 16 rows) has no image plane.
        spatial = min(image.shape[:2]) >= 16
        projection = self._projection()
        q, moved, not_positive = fk.layer_exposure(image, float(o.scene_flare), self.c.ap1_to_xyz, projection.normals, self._room, projection.white, projection.LOCUS_INSET,
                                                   self._uv_f32, np.array(UV_MAX), self.layer_gain)
        pixel = self._pixel_um(image)
        if spatial and o.scatter_um:
            sigma = o.scatter_um / pixel
            q = fk.gaussian_blur(q, sigma)
        if spatial and any(o.halation):
            q = fk.mix_exposure(q, fk.gaussian_blur(q, o.halation_um / pixel), np.array(o.halation, dtype=np.float64))
        density, above = fk.negative_density(q, self.film.negative_criterion_log_h, self._neutral, float(o.interlayer_gain), self._curve_start, self._curves_f64, self._curve_lengths, self._curve_step)
        if spatial and o.adjacency_gain:
            density = fk.add_adjacency(density, fk.gaussian_blur(density, o.adjacency_um / pixel), float(o.adjacency_gain))
        if spatial and o.enlarger_flare:
            t = fk.density_to_transmittance(density)
            density = fk.flare_density(t, fk.gaussian_blur(t, o.enlarger_flare_size * max(image.shape[:2])), float(o.enlarger_flare))
        return density, {"moved_by_rule": int(moved), "y_not_positive": int(not_positive), "negative_above_curve_end": int(above), "pixels": int(image.shape[0] * image.shape[1])}

    def render(self, ap1: np.ndarray, detailed: bool = False) -> tuple[np.ndarray, dict]:
        """Linear AP1 to sRGB, through the kernels. detailed adds the percentiles of the gamut distance (slower)."""
        o = self.options
        shape = ap1.shape
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        if image.ndim == 2:
            image = image[None]
        density, stats = self.negative_image(image)
        rgb = fk.print_display(density, self._print_f32, self._grid_start, self._grid_step, self.xyz_to_display)
        if detailed:
            stats["gamut_distance_p999"] = np.percentile(gamut_distance(rgb).reshape(-1, 3), 99.9, axis=0).round(3).tolist()
        out, before, after = fk.finish_display(rgb, bool(o.gamut_compress), np.array(o.gamut_threshold), np.array(o.gamut_limit), float(o.gamut_power))
        stats["display_clipped"] = int(before)
        if o.gamut_compress:
            stats["display_clipped_after_compression"] = int(after)
        return (out[0] if len(shape) == 2 else out), stats

    def reference_render(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        """The array implementation of render(), for check_fast_kernels.py."""
        # Rule 'no_image_plane_steps_on_ramps': a test ramp (fewer than 16 rows) has no image plane.
        spatial = ap1.ndim == 3 and min(ap1.shape[:2]) >= 16
        q, stats = self.layer_exposure(ap1 + self.options.scene_flare)
        if spatial:
            q = self._exposure_spread(q)
        density, above = self.negative_density(q)
        if spatial:
            density = self._development_and_enlarger(density)
        rgb = self.display_linear(self.print_xyz(density))
        stats.update(negative_above_curve_end=above, display_clipped=int(((rgb < 0) | (rgb > 1)).any(axis=-1).sum()), pixels=int(q.size / 3))
        stats["gamut_distance_p999"] = np.percentile(gamut_distance(rgb).reshape(-1, 3), 99.9, axis=0).round(3).tolist()
        if self.options.gamut_compress:
            o = self.options
            rgb = compress_gamut(rgb, o.gamut_threshold, o.gamut_limit, o.gamut_power)
            stats["display_clipped_after_compression"] = int(((rgb < 0) | (rgb > 1)).any(axis=-1).sum())
        return srgb_encode(rgb), stats


def smooth_reflectance_table(rho: np.ndarray, sigma_near: float, sigma_far: float, white_uv: np.ndarray, to_xyz: np.ndarray) -> np.ndarray:
    """Rule 'smooth_reflectance_table': the reconstruction changes its active set and its neighbours from node to node, so the shape has creases and steps over u'v'
    that a colour ramp shows as breaks. A Gaussian over u'v' removes them. Skin and other low chroma colours have measured spectra nearby and small creases, so they get sigma_near; the strong
    breaks are at high chroma, which gets sigma_far. The blend is a smoothstep of the u'v' distance from the white, over UV_SMOOTH_BLEND.
    Each node then gets a scale per wavelength, rho (1 + to_xyz^T lambda), to restore its XYZ (Newton steps). to_xyz: (3, wavelengths)."""
    step = np.array(UV_MAX) / (UV_NODES - 1)
    shape = rho.reshape(UV_NODES, UV_NODES, -1)
    near = gaussian_filter(shape, sigma=(sigma_near / step[0], sigma_near / step[1], 0.0), mode="nearest").reshape(-1, rho.shape[-1])
    far = gaussian_filter(shape, sigma=(sigma_far / step[0], sigma_far / step[1], 0.0), mode="nearest").reshape(-1, rho.shape[-1])
    u, v = np.meshgrid(*FilmPreview.uv_axes(), indexing="ij")
    t = np.clip((np.hypot(u - white_uv[0], v - white_uv[1]).ravel() - UV_SMOOTH_BLEND[0]) / (UV_SMOOTH_BLEND[1] - UV_SMOOTH_BLEND[0]), 0.0, 1.0)
    weight = (t * t * (3.0 - 2.0 * t))[:, None]
    out = (1.0 - weight) * near + weight * far
    target = rho @ to_xyz.T
    for _ in range(8):
        error = target - out @ to_xyz.T
        gram = np.einsum("ni,ai,bi->nab", out, to_xyz, to_xyz, optimize=True)
        scale = np.linalg.solve(gram + 1e-12 * np.trace(gram, axis1=1, axis2=2)[:, None, None] * np.eye(3), error[..., None])[..., 0]
        out = np.maximum(out * (1.0 + scale @ to_xyz), 0.0)
    return out


def gamut_distance(rgb: np.ndarray) -> np.ndarray:
    """Distance of each channel from the largest channel, as a share of that channel (1 = on the boundary)."""
    achromatic = rgb.max(axis=-1, keepdims=True)
    return np.where(achromatic > 0, (achromatic - rgb) / np.maximum(np.abs(achromatic), 1e-9), 0.0)


def compress_gamut(rgb: np.ndarray, threshold: tuple, limit: tuple, power: float) -> np.ndarray:
    """Rule 'rgc_style_display_compression'. The curve of the ACES Reference Gamut Compression: a distance
    below the threshold does not change, and the limit maps to the boundary. The largest channel does not change."""
    achromatic = rgb.max(axis=-1, keepdims=True)
    distance = gamut_distance(rgb)
    t, l = np.array(threshold), np.array(limit)
    scale = (l - t) / (((1.0 - t) / (l - t)) ** -power - 1.0) ** (1.0 / power)
    normal = np.maximum(distance - t, 0.0) / scale
    compressed = np.where(distance > t, t + scale * normal / (1.0 + normal ** power) ** (1.0 / power), distance)
    return achromatic - compressed * np.abs(achromatic)


def srgb_encode(linear: np.ndarray) -> np.ndarray:
    x = np.clip(linear, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def decode_raw_ap1(path: Path, long_edge: int, c: sr.Colorimetry) -> tuple[np.ndarray, np.ndarray]:
    """White-balanced linear AP1 and the linear Rec. 709 of the same data, reduced by box averaging.
    The reduction averages sensor data (half-size decode) and is for the review images only."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        xyz = raw.postprocess(output_color=rawpy.ColorSpace.XYZ, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True,
                              half_size=True, output_bps=16, highlight_mode=rawpy.HighlightMode.Clip).astype(np.float64) / 65535.0
    factor = max(1, int(np.ceil(max(xyz.shape[:2]) / long_edge)))
    h, w = xyz.shape[0] // factor * factor, xyz.shape[1] // factor * factor
    xyz = xyz[:h, :w].reshape(h // factor, factor, w // factor, factor, 3).mean(axis=(1, 3))
    to_ap1 = c.xyz_to_ap1 @ bradford_matrix(XYZ_D65, c.ap1_to_xyz @ np.ones(3))
    return xyz @ to_ap1.T, xyz @ XYZ_TO_REC709.T


def center_weighted_exposure(ap1: np.ndarray, c: sr.Colorimetry) -> float:
    """Rule 'center_weighted_exposure': the scale that sets the mean of linear Y to 0.18, with Gaussian
    weights around the image center (sigma: 0.35 of each side). It acts like a camera meter. A value above
    METER_CAP times the weighted median counts as that value, so that a lamp in a night scene does not set the exposure."""
    y = np.maximum(ap1 @ c.ap1_to_xyz[1], 0.0)
    h, w = y.shape
    yy, xx = np.mgrid[0:h, 0:w]
    weight = np.exp(-(((xx - w / 2) / (0.35 * w)) ** 2 + ((yy - h / 2) / (0.35 * h)) ** 2) / 2)
    order = np.argsort(y, axis=None)
    median = y.ravel()[order][np.searchsorted(np.cumsum(weight.ravel()[order]), 0.5 * weight.sum())]
    return float(0.18 / ((np.minimum(y, METER_CAP * median) * weight).sum() / weight.sum()))


def product_input(ap1: np.ndarray, c: sr.Colorimetry, contrast: float = PRODUCT_CONTRAST, saturation: float = PRODUCT_SATURATION) -> np.ndarray:
    """Linear AP1 of a RAW file as the DRT receives it in the product: exposure of the review rule, then the default grade."""
    image = np.ascontiguousarray(ap1, dtype=np.float32)
    return fk.product_grade(image, float(np.log2(center_weighted_exposure(ap1, c))), float(contrast), float(saturation))


def review_exposure(ap1: np.ndarray, c: sr.Colorimetry) -> float:
    """Rule 'review_exposure': the scale that sets the log average of Y (1st to 99th percentile) to 0.18."""
    y = (ap1.reshape(-1, 3) @ c.ap1_to_xyz[1]).clip(1e-5, None)
    log_y = np.log(y)
    lo, hi = np.percentile(log_y, [1, 99])
    return float(0.18 / np.exp(log_y[(log_y >= lo) & (log_y <= hi)].mean()))
