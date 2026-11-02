"""Film preview renderer of step P2: linear AP1 to a display image through Portra 400 and Endura.

Input: the P0 evaluator and profiles, the P1 reconstruction and reflectance datasets, RAW files.
Output: library used by render_review_images.py. The reflectance tables over u'v' stay in build/tmp/p2/tables/. The print tables are not stored (ROADMAP U68).

Step: P2, ROADMAP section 8, with decision U17: the user reviews the rendered appearance first.
This is a review tool. It uses reduced images and CPU tables; it is not the product path.

Execution: render() uses the compiled kernels of fast_kernels.py, and the print table uses the C++ library alcedo_film_tables (step P7, scripts/poc/p7_spectral_acceleration/). The array methods of this class
(layer_exposure, negative_density, direct_print_xyz, print_xyz, reference_render) are the reference;
check_fast_kernels.py compares the kernels with them, and check_film_tables.py of step P7 compares the print table.

Rule 'staged_print_table' (step P7). The print table has three stages, so that a print control does not repeat a spectral integral: the negative record to log10 of the unbalanced paper exposure (no solve with rule 'dye_amount_curves', because the record is the dye amounts);
paper Status A to XYZ, on PAPER_TABLE_NODES per axis, with more nodes at a low density (PAPER_AXIS_POWER); and a composition with the printer lights, print contrast, flash, paper curves, and surface reflection. The composition reads the second stage by trilinear interpolation of the cube root, so it differs a little from a dye solve per node. check_film_tables.py states the size.
This process keeps the two spectral stages in memory (STAGE_TABLES_KEPT); nothing goes to disk. print_not_reached of table_counts reads the nearest node of the paper table.

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

Darkroom controls (ROADMAP U19). Each one is a step of a real process. The values are review controls,
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

Scene light (ROADMAP U20). The input is white balanced, so it holds a reflectance colour and not the light.
Rule 'relight': the reflectance shape of the reconstruction is multiplied by the spectrum of scene_light
(Y of the light = 1), and the layers integrate that radiance. A grey under a light that is not the balance
light of the stock lands on the curves at different places per layer, as on real film. Option print_timing:
the printer lights remove this share of the cast at mid grey (1: a neutral mid grey, 0: uncorrected). The
position on the curves stays, so the shadows and the highlights can keep a colour (crossover), and a
spiky light keeps its effect on colours. RAW white can select a daylight or Planckian light. It cannot show
that a light is fluorescent or LED, so those are an explicit choice.

Rule 'dye_amount_curves' (option negative_record = 'dye_amount', step P4). A Status M curve is an instrument reading of a neutral; it is not the response of one layer. With 'status_m',
each layer exposure sets one Status M channel, and the dye solve then removes the side absorption of each dye. With 'dye_amount', the dye solve runs once on the neutral ramp and gives the curve
amount against log H of each layer. Each layer exposure sets the amount of its own dye, and the spectral density and every reading follow. A neutral keeps its published Status M, and a colour keeps the side absorption of its dyes.

Rule 'light_like_spectra' (option light_spectra, step P4). The prior of the reconstruction holds measured reflectances of objects. A blue object often reflects again in the far red, and sky light does not, so a sky had
too much red layer exposure and turned violet (P4 report, W1). A low-colour-temperature light had the opposite error. In two sectors of u'v' around the white, the table shape moves to a smooth spectrum, rho = exp(c0 + c1 x + c2 x^2), with the XYZ of the node.
The blue sector follows the direction of skylight, and the warm sector the direction of a Planckian light below about 3000 K. The sectors and the family are inferred. The rule acts after rule 'smooth_reflectance_table'. The cost: a blue object or a saturated orange object loses the
detail of its measured neighbours; the P4 report states the size. A photo gives no way to separate an object from a light, and sky and sunset are the larger areas of a landscape.

Rule 'foliage_spectra' (option foliage). The reflectance prior gives a green colour a shape with no chlorophyll band near 670 nm, so a red layer that peaks near 630 nm receives too much exposure from a leaf (up to 0.10 log10 on Portra 160), and foliage turns yellow.
In one sector of u'v' around the colour of a leaf, the table shape moves to a leaf shape times exp(c0 + c1 x + c2 x^2), with the XYZ of the node. The leaf shape, the sector, and the fade are inferred; they are no measurement. The rule acts after rule 'light_like_spectra'. Any object in the sector takes the leaf shape, because a photo cannot separate a leaf from another green object.

Rule 'development_inhibition' (options inhibition_*, step P4, needs negative_record = 'dye_amount'). A developing layer releases an inhibitor that lowers development in the same layer and in the others:
    a_i = F_i(log H_i - sum_j K_ij G * a_j)
G is a Gaussian of the length inhibition_um in the image plane. F_i is computed so that the neutral ramp returns the published curve exactly: on a neutral, F_i maps log H - sum_j K_ij a_j(log H) to a_i(log H). So the published curve holds for a neutral and a large flat area, and a colour, where the layers differ, gets less inhibition from the layers that developed less.
The total of K per layer comes from the published modulation transfer (fit_mtf.py of step P4). Its split between the layers has no source and is inferred. Solve: fixed-point steps from the uninhibited amounts.
Not independent: the first step is the method of spektrafilm model/couplers.py, with no code or value from it (P6 report, section 5.2; THIRD_PARTY_NOTICES.md).

Rule 'overexposed_negative' (option overexposure_stops, step P5, U35). The negative takes N more stops, and the printer lights take them back, so that a grey keeps its print value. The shadows move off the toe of the negative, and the highlights use the latitude of the negative.

Rule 'contrast_mask' (options mask_*, step P5, U35). The darkroom method for a high contrast negative: a faint positive on black and white film, made from the negative, is put on the negative during the print. It adds a neutral density where the negative is thin, so the shadows of the scene take less exposure and print lighter:
    T = integral of the negative transmittance under the lamp and a panchromatic response;  D = -log10(blur of T);  x = D_ref - D;  D_mask = mask_gamma * (x + sqrt(x^2 + k^2)) / 2
D_ref is the pan density of a grey mask_reference_stops from mid grey, and k (mask_knee_density) is the toe of the mask film. The printer lights take back the mask density of a grey. A neutral density moves each paper layer by the same log10 exposure, so the colour comes from the paper and the dyes. A table per mask density holds this, and print_display_masked reads it. Inferred, with no source: the panchromatic response (flat from 400 to 650 nm), mask_gamma, the reference, the toe, and the length of the blur (the spacer between the mask and the negative). A blur has the halo of the real method.

Rule 'layer_spread' (option layer_spread_um, step P4): an exponential spread of the light per layer, in layer exposure, with the length from the published modulation transfer. A sum of two Gaussians stands for the exponential (constants SPREAD_GAUSSIANS, largest error in the transfer function 0.028).
Rule 'spread_per_layer_pass' (step P7): each of the two Gaussians is one pass with a kernel per layer, so this rule has two blur passes in place of six, with the same result.
Rules for speed (step P7, ROADMAP U70, where speed comes before numeric accuracy): 'inhibition_two_steps' runs two fixed-point steps on an image (INHIBITION_STEPS_IMAGE), and 'inhibitor_on_half_size' blurs the inhibitor on a half-size image when its sigma is at least 4 pixels. A value on the neutral ramp keeps the published curve, because the first amounts are the fixed point there. A flat neutral of an image is near that ramp, and check_fast_image_steps.py states the difference.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import alcedo_film_tables as film_tables
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

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
PAPER_TABLE_NODES = 65
PAPER_AXIS_POWER = 2.0  # node k of a Status A axis: start + range * (k / (nodes - 1)) ^ power
STAGE_TABLES_KEPT = 8  # spectral stages of rule 'staged_print_table' that this process keeps in memory
SOLVE_ITERATIONS = 16
SOLVE_REACHED_LIMIT = 1e-4
UV_SMOOTH_BLEND = (0.05, 0.15)  # u'v' distance from the white where sigma_near changes to sigma_far
LIGHT_SECTOR_DEGREES = (30.0, 60.0)  # angle from the direction of a sector: full weight, then a smoothstep to zero
LIGHT_SECTOR_RADIUS = {"blue": (0.006, 0.02), "warm": (0.05, 0.09)}  # u'v' distance from the white: zero weight, then a smoothstep to full weight
LIGHT_FIT_STEPS = 12  # continuation steps from the white to the node
LIGHT_FIT_LIMIT = 1e-5  # largest relative XYZ error of a fitted node
LIGHT_REACH_FADE = 0.008  # u'v' sigma of the fade toward the nodes that the family cannot reach
FOLIAGE_DEGREES = (25.0, 50.0)  # angle from the direction of the leaf colour: full weight, then a smoothstep to zero
FOLIAGE_RADIUS = (0.015, 0.045)  # u'v' distance from the white: zero weight, then a smoothstep to full weight
FOLIAGE_FIT_STEPS = 6  # continuation steps from the leaf colour to the node
FOLIAGE_FIT_LIMIT = 1e-3  # largest relative XYZ error of a fitted node
FOLIAGE_REACH_FADE = 0.02  # u'v' distance of the fade toward the nodes that the family cannot reach
SPREAD_GAUSSIANS = ((0.2528, 0.4142), (0.7472, 1.4271))  # (weight, sigma / spread length): least-squares fit of 1 / (1 + x^2) for x up to 8
MASK_DENSITY_START = -0.05
MASK_DENSITY_STEP = 0.05
MASK_DENSITY_NODES = 16  # up to 0.70 density
MASK_PAN_NM = (400.0, 650.0)
INHIBITION_STEPS_IMAGE = 2  # ROADMAP U70; step P4 used 4, and sweep_inhibition_steps.py of step P7 states the difference
INHIBITION_STEPS_POINT = 16
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


_stage_tables: dict[str, object] = {}
_reflectance_shapes: dict[tuple, np.ndarray] = {}  # the file of a reflectance table is read once per process; the shapes have no dependence on a stock


def kept_stage_table(name: str, inputs: Iterable[np.ndarray], build: Callable[[], object]) -> object:
    """Rule 'staged_print_table': a spectral stage, kept in memory by the values of its input, so it cannot be out of date. The oldest one goes first."""
    digest = hashlib.sha256(name.encode())
    for values in inputs:
        array = np.asarray(values, dtype=np.float64)
        digest.update(repr(array.shape).encode())
        digest.update(array.tobytes())
    key = digest.hexdigest()
    if key not in _stage_tables:
        if len(_stage_tables) >= STAGE_TABLES_KEPT:
            _stage_tables.pop(next(iter(_stage_tables)))
        _stage_tables[key] = build()
    return _stage_tables[key]


def spectral_support(weights: np.ndarray) -> np.ndarray:
    """The nodes where the weights of an integral are not zero."""
    return np.flatnonzero(np.any(weights != 0.0, axis=0))


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
    negative_record: str = "status_m"  # 'status_m' or 'dye_amount': rule 'dye_amount_curves' (P4)
    light_spectra: bool = False  # not part of the print table; rule 'light_like_spectra' (P4)
    foliage: bool = False  # not part of the print table; rule 'foliage_spectra'
    layer_spread_um: tuple[float, float, float] = (0.0, 0.0, 0.0)  # not part of the print table; rule 'layer_spread' (P4), red, green, blue layer
    inhibition_total: tuple[float, float, float] = (0.0, 0.0, 0.0)  # rule 'development_inhibition' (P4): the total inhibition that each layer receives, log10 H per unit of dye amount
    inhibition_cross_share: float = 0.5  # share of the total that comes from the other two layers (inferred)
    inhibition_um: float = 35.0  # not part of the print table; Gaussian length of the inhibitor in the image plane
    overexposure_stops: float = 0.0  # rule 'overexposed_negative' (P5)
    mask_gamma: float = 0.0  # not part of the print table; rule 'contrast_mask' (P5), the next ones too
    mask_reference_stops: float = -1.0
    mask_knee_density: float = 0.15
    mask_um: float = 1000.0


# Review options after the darkroom comparison (ROADMAP U19), for RAW input through product_input().
# The input is product_input(): the default grade of the product comes before the film. So the chain has no interlayer
# gain, and print_contrast takes back about the mid-grey slope of the grade (0.92 / 2^0.15 = 0.83). The value 0.85 comes from a sweep with the chroma of spektrafilm output as the target (U18; P2 report, section 8.5), so it is not independent.
DARKROOM = dict(uv_smooth=(0.006, 0.025), interlayer_gain=0.0, print_flash=0.02, print_contrast=0.85, viewing_flare=0.003, scatter_um=10.0,
                halation=(0.03, 0.008, 0.0), adjacency_gain=0.25, enlarger_flare=0.01, gamut_compress=True)

# Printer lights of the cine prints. The LAD aim of 2383 (Status A about 1.06) is for a dark cinema. This value
# follows the comparison with spektrafilm on a display (U18); it is a review control.
CINE_GREY_STATUS_A = 0.85

# Scene lights that the user selects (ROADMAP U21). Default: daylight. One representative CIE spectrum per type;
# real lamps of a type differ, and this table does not claim to match a lamp.
PRODUCT_LIGHTS = {"daylight": "D55", "tungsten": "T3200", "fluorescent": "FL11", "led": "LED-B3", "sodium": "HP1"}

# Scenes that the user selects in place of one light (ROADMAP U22, step P3). Each one is a global mixture of named
# spectra; the weights are shares of the luminance and the author's choice, not measurements of a place.
# One spectrum applies to every pixel of the image: see the P3 report for what this cannot do.
SCENE_PRESETS = {
    "street_mixed": (("T2800", 0.3), ("LED-B3", 0.4), ("HP1", 0.3)),
    "street_sodium": (("HP1", 0.7), ("T2800", 0.15), ("LED-B3", 0.15)),
    "street_led": (("LED-B3", 0.75), ("T2800", 0.15), ("HP1", 0.1)),
    "interior_warm": (("T2800", 0.7), ("LED-B3", 0.3)),
    "interior_office": (("FL11", 0.5), ("LED-B3", 0.5)),
}

# Physical options of step P4, for each stock. Spread and inhibition: results/p4_physical_film_response/mtf_fit.json. Portra 400 has no published isolated dye curves, so it keeps the inferred band split.
# These options replace scatter_um and adjacency_gain of DARKROOM. gamut_limit: on this chain the print of a saturated sky or cyan reaches a gamut distance of 1.25 to 1.32 (p99.9 on the hue sweep, cyan), so the ACES RGC value 1.147 left a clip that made a break in the sweep.
P4_GAMUT_LIMIT = (1.4, 1.3, 1.312)
P4_PHYSICAL = {
    "5207_2383": dict(negative_dye_basis="published", negative_record="dye_amount", light_spectra=True, scatter_um=0.0, adjacency_gain=0.0, layer_spread_um=(4.95, 3.02, 2.83), inhibition_total=(0.1448, 0.079, 0.204), gamut_limit=P4_GAMUT_LIMIT),
    "5219_2383": dict(negative_dye_basis="published", negative_record="dye_amount", light_spectra=True, scatter_um=0.0, adjacency_gain=0.0, layer_spread_um=(5.0, 3.41, 3.17), inhibition_total=(0.1836, 0.2463, 0.2833), gamut_limit=P4_GAMUT_LIMIT),
    "portra400_endura": dict(negative_dye_basis="band_split", negative_record="dye_amount", light_spectra=True, scatter_um=0.0, adjacency_gain=0.0, layer_spread_um=(4.53, 3.21, 2.63), inhibition_total=(0.211, 0.3356, 0.1902), gamut_limit=P4_GAMUT_LIMIT),
}

# Physical options of step P5, the same rules as P4_PHYSICAL. No isolated dye curves are published for these stocks, so all keep the inferred band split. Spread and inhibition: results/p5_film_and_print_combinations/mtf_fit.json.
# C200: the chart has one curve, so the spread is one value and the inhibition differs only by the slope of each layer. Gold 200: E-7022 has no modulation transfer chart, so this stock has no spread and no inhibition, and a value of another stock is not used.
P5_BAND_SPLIT = dict(negative_dye_basis="band_split", negative_record="dye_amount", light_spectra=True, scatter_um=0.0, adjacency_gain=0.0, gamut_limit=P4_GAMUT_LIMIT)
P5_PHYSICAL = {
    "portra160_endura": dict(P5_BAND_SPLIT, scene_light="D55", layer_spread_um=(5.55, 2.98, 3.03), inhibition_total=(0.2786, 0.2648, 0.083)),
    "portra800_endura": dict(P5_BAND_SPLIT, scene_light="D55", layer_spread_um=(5.21, 3.64, 2.51), inhibition_total=(0.1301, 0.3485, 0.1196)),
    "ektar100_endura": dict(P5_BAND_SPLIT, scene_light="D55", layer_spread_um=(6.51, 3.86, 3.13), inhibition_total=(0.4991, 0.3589, 0.1379)),
    "gold200_endura": dict(P5_BAND_SPLIT, scene_light="D55"),
    "c200_endura": dict(P5_BAND_SPLIT, scene_light="D55", layer_spread_um=(3.24, 3.24, 3.24), inhibition_total=(0.2754, 0.2362, 0.2145)),
}

STOCKS = {
    "portra400_endura": {},
    # Exposure of the grey: 12.5 / ISO lux seconds. Projection at D65.
    "5207_2383": dict(negative_profile="kodak_5207", print_profile="kodak_2383", midscale_log_h=float(np.log10(12.5 / 250)),
                      print_midscale_status_a=CINE_GREY_STATUS_A, viewing_cct_k=6500.0, grey_anchor=True, balance_light="D55", neutral_printing=True),
    "5219_2383": dict(negative_profile="kodak_5219", print_profile="kodak_2383", midscale_log_h=float(np.log10(12.5 / 500)),
                      print_midscale_status_a=CINE_GREY_STATUS_A, viewing_cct_k=6500.0, grey_anchor=True, balance_light="T3200", neutral_printing=True),
    # Step P5. Exposure of the grey: the Log H Ref of the sheet. AF3-0249E states none, so C200 takes the value of Gold 200, the Kodak stock of the same ISO (inferred). Rule 'grey_anchor': C200 has a relative sensitivity chart, and the Kodak charts leave the grey up to 0.70 stops apart between layers under D55.
    "portra160_endura": dict(negative_profile="kodak_portra_160", midscale_log_h=-1.051, grey_anchor=True, balance_light="D55"),
    "portra800_endura": dict(negative_profile="kodak_portra_800", midscale_log_h=-1.74, grey_anchor=True, balance_light="D55"),
    "ektar100_endura": dict(negative_profile="kodak_ektar_100", midscale_log_h=-0.84, grey_anchor=True, balance_light="D55"),
    "gold200_endura": dict(negative_profile="kodak_gold_200", midscale_log_h=-1.14, grey_anchor=True, balance_light="D55"),
    "c200_endura": dict(negative_profile="fuji_c200", midscale_log_h=-1.14, grey_anchor=True, balance_light="D55"),
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
        self.status_curves = list(self.film.negative_curves.values())
        self.negative_curves = self.status_curves if o.negative_record == "status_m" else self._dye_amount_curves()
        self._prepare_inhibition()
        self.paper_curves = list(self.film.paper_curves.values())
        self.scene_spectrum = self.light(o.scene_light)
        self.layer_gain = self._camera_filter()
        self._apply_overexposure()
        self.printing_gain = self._printing_gain()
        self.uv_table = self._load_uv_table()
        self.density_grid, self.print_table, self.table_counts = self._build_print_table()
        self._prepare_display()
        self._prepare_kernels()
        self._prepare_mask()

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
        f.printer_balance_log10 = reference + o.print_timing * (balance(self.record_to_status_m(self.negative_density(grey[None])[0])[0]) - reference)
        return gain

    def _apply_overexposure(self) -> None:
        """Rule 'overexposed_negative'. It works on any stock, because the printer lights move by the change of the grey on the negative."""
        stops = self.options.overexposure_stops
        if not stops:
            return
        f = self.film
        factor = 2.0 ** stops

        def unbalanced(q: np.ndarray) -> np.ndarray:
            status_m = self.record_to_status_m(self.negative_density(q[None])[0])[0]
            return np.log10(f.paper_layer_exposure_unbalanced(f.negative_spectral_density(f.negative_dye_amounts(status_m))))

        grey = self.layer_gain * self.c.layer_exposure(0.18 * self.scene_spectrum)
        f.printer_balance_log10 = np.asarray(f.printer_balance_log10) - (unbalanced(grey * factor) - unbalanced(grey))
        self.layer_gain = self.layer_gain * factor

    def _printing_gain(self) -> np.ndarray:
        # Rule 'neutral_printing_gain': see the header. Range: 1.0 log H on each side of the grey.
        if not self.options.neutral_printing:
            return np.ones(3)
        f = self.film
        log_h = f.options.midscale_log_h + np.linspace(-1.0, 1.0, 21)
        status_m = np.stack([np.interp(log_h, c.log_h, c.density) for c in self.status_curves], axis=1)
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
        key = (self.options.uv_smooth, self.options.light_spectra, self.options.foliage)
        if key not in _reflectance_shapes:
            _reflectance_shapes[key] = self._final_reflectance_table()
        return self.c.layer_exposure(_reflectance_shapes[key] * self.scene_spectrum[None, :]).reshape(UV_NODES, UV_NODES, 3)

    def _final_reflectance_table(self) -> np.ndarray:
        rho = self._load_reflectance_table().astype(np.float64)
        white = self.c.xyz(self.c.e_ref)
        white_uv = np.array([4.0 * white[0], 9.0 * white[1]]) / (white[0] + 15.0 * white[1] + 3.0 * white[2])
        near, far = self.options.uv_smooth
        if any(self.options.uv_smooth):
            path = CACHE_DIR / f"reflectance_over_uv_smooth_{near}_{far}.npy"
            if path.exists():
                rho = np.load(path).astype(np.float64)
            else:
                rho = smooth_reflectance_table(rho, near, far, white_uv, self.c.w_xyz * self.c.e_ref)
                np.save(path, rho.astype(np.float32))
        if self.options.light_spectra:
            # After the smoothing: the family is smooth over u'v', and the smoothing moved the far end of a Planckian light (P4 report, section W1).
            path = CACHE_DIR / f"reflectance_over_uv_light_{near}_{far}.npy"
            if path.exists():
                rho = np.load(path).astype(np.float64)
            else:
                rho = light_like_spectra(rho, self.c, white_uv)
                np.save(path, rho.astype(np.float32))
        if self.options.foliage:
            path = CACHE_DIR / f"reflectance_over_uv_foliage_{self.options.light_spectra}_{near}_{far}.npy"
            if path.exists():
                rho = np.load(path).astype(np.float64)
            else:
                rho = foliage_spectra(rho, self.c, white_uv)
                np.save(path, rho.astype(np.float32))
        return rho

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

    def _dye_amount_curves(self) -> list[p0.CharacteristicCurve]:
        """Rule 'dye_amount_curves': the dye amounts of the neutral ramp, on one log H grid. Ends: the rule 'negative_curve_limits' of each Status M curve."""
        f = self.film
        step = self.status_curves[0].log_h[1] - self.status_curves[0].log_h[0]
        start, stop = min(c.log_h[0] for c in self.status_curves), max(c.log_h[-1] for c in self.status_curves)
        log_h = start + step * np.arange(int(round((stop - start) / step)) + 1)
        status_m = np.stack([np.interp(log_h, c.log_h, c.density) for c in self.status_curves], axis=1)
        base = f.status_density(f.negative_dmin, f.w_status_m)
        amounts, residual = solve_amounts(status_m - f.negative_curve_dmin + base, f.negative_dmin, f.negative_dyes, f.w_status_m)
        rising = np.maximum.accumulate(amounts, axis=0)
        self.dye_curve_info = {"largest_solve_residual": float(residual.max()), "largest_fall_removed": float((rising - amounts).max()), "amount_range": [rising.min(axis=0).tolist(), rising.max(axis=0).tolist()]}
        return [p0.CharacteristicCurve(log_h, rising[:, k]) for k in range(3)]

    def _prepare_inhibition(self) -> None:
        """Rule 'development_inhibition': the matrix K and the curves F_i on a uniform grid."""
        o = self.options
        self.inhibition = None
        if not any(o.inhibition_total):
            return
        if o.negative_record != "dye_amount":
            raise ValueError("rule development_inhibition needs negative_record = 'dye_amount'")
        share = np.full((3, 3), o.inhibition_cross_share / 2.0)
        np.fill_diagonal(share, 1.0 - o.inhibition_cross_share)
        k = np.array(o.inhibition_total)[:, None] * share
        log_h = self.negative_curves[0].log_h
        amounts = np.stack([c.density for c in self.negative_curves], axis=1)
        reduced = log_h[:, None] - amounts @ k.T
        if (np.diff(reduced, axis=0) <= 0.0).any():
            raise ValueError("rule development_inhibition: the reduced exposure of the neutral does not rise, so F_i does not exist")
        step = float(log_h[1] - log_h[0])
        length = len(log_h) + int(np.ceil(np.ptp(reduced, axis=0).max() / step))
        starts = reduced[0]
        grid = starts[:, None] + step * np.arange(length)[None, :]
        free = np.stack([np.interp(grid[i], reduced[:, i], amounts[:, i]) for i in range(3)])
        self.inhibition = {"k": k, "start": starts, "free": free, "lengths": np.array([int(np.searchsorted(grid[i], reduced[-1, i])) + 1 for i in range(3)]), "step": step}

    def _inhibited_amounts(self, log_h: np.ndarray, amounts: np.ndarray) -> np.ndarray:
        """Array form of the fixed point, with no image plane: log H and first amounts (N, 3)."""
        i = self.inhibition
        grid = i["start"][:, None] + i["step"] * np.arange(i["free"].shape[1])[None, :]
        for _ in range(INHIBITION_STEPS_POINT):
            reduced = log_h - amounts @ i["k"].T
            amounts = np.stack([np.interp(reduced[..., k], grid[k][: i["lengths"][k]], i["free"][k][: i["lengths"][k]]) for k in range(3)], axis=-1)
        return amounts

    def record_to_status_m(self, record: np.ndarray) -> np.ndarray:
        """The value of the curve stage (Status M, or dye amounts with rule 'dye_amount_curves') as negative Status M on the scale of the published curves. Shape (N, 3)."""
        if self.options.negative_record == "status_m":
            return record
        f = self.film
        return f.status_density(f.negative_spectral_density(record), f.w_status_m) - f.status_density(f.negative_dmin, f.w_status_m) + f.negative_curve_dmin

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
        if self.inhibition is not None:
            out = self._inhibited_amounts(crit + log_q, out)
        return out, above

    # --- stage 4 ------------------------------------------------------------------------------

    def direct_print_xyz(self, density: np.ndarray) -> tuple[np.ndarray, dict]:
        """Negative Status M (N, 3) to print XYZ (Y of the perfect diffuser = 100), through the stages."""
        film = self.film
        d = self.record_to_status_m(np.atleast_2d(density))
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
        """The kernel form of direct_print_xyz, with a dye solve per node. The reference of check_film_tables.py. Each integral uses only the nodes where its weights are not zero."""
        f, o = self.film, self.options
        m, pr, st, vi = spectral_support(f.w_status_m), spectral_support(f.w_printing), spectral_support(f.w_status_a), spectral_support(f.w_viewing[f.viewing_name])
        w_view = f.w_viewing[f.viewing_name]
        base = f.status_density(f.negative_dmin, f.w_status_m)
        length = max(len(c.density) for c in self.paper_curves)
        curves = np.stack([np.pad(c.density, (0, length - len(c.density)), mode="edge") for c in self.paper_curves])
        aim = np.array([c.log_h_at(o.print_midscale_status_a) for c in self.paper_curves])
        xyz, not_negative, not_print, outside = fk.print_nodes(
            self.record_to_status_m(density).astype(np.float64), base - f.negative_curve_dmin, SOLVE_ITERATIONS,
            f.negative_dmin[m], f.negative_dyes[:, m], f.w_status_m[:, m],
            f.negative_dmin[pr], f.negative_dyes[:, pr], f.w_printing[:, pr], np.asarray(f.printer_balance_log10, dtype=np.float64), aim, float(o.print_contrast) * self.printing_gain, float(o.print_flash),
            np.array([c.log_h[0] for c in self.paper_curves]), curves, np.array([len(c.density) for c in self.paper_curves]), float(self.paper_curves[0].log_h[1] - self.paper_curves[0].log_h[0]),
            f.paper_base[st], f.paper_dyes[:, st], f.w_status_a[:, st],
            f.paper_base[vi], f.paper_dyes[:, vi], w_view[:, vi], o.viewing_flare * f.white_xyz(), 100.0 / w_view[1].sum())
        return xyz, {"negative_not_reached": int(not_negative), "print_not_reached": int(not_print), "paper_exposure_outside_curve": int(outside)}

    def table_amounts(self, record: np.ndarray) -> tuple[np.ndarray, int]:
        """The dye amounts of table nodes of the negative record (N, 3), with the count that the dye solve did not reach. With rule 'dye_amount_curves' the record is the amounts."""
        if self.options.negative_record == "dye_amount":
            return record, 0
        f = self.film
        m = spectral_support(f.w_status_m)
        targets = record + f.status_density(f.negative_dmin, f.w_status_m) - f.negative_curve_dmin
        return film_tables.solve_dye_amounts(f.negative_dmin[m], f.negative_dyes[:, m], f.w_status_m[:, m], targets, SOLVE_ITERATIONS, SOLVE_REACHED_LIMIT)

    def _negative_stage(self, grid: list[np.ndarray]) -> tuple[np.ndarray, int]:
        """Rule 'staged_print_table': log10 of the unbalanced paper exposure on the nodes of the negative record, and the count that the dye solve did not reach."""
        f = self.film
        pr = spectral_support(f.w_printing)

        def build() -> tuple[np.ndarray, int]:
            nodes = np.stack(np.meshgrid(*grid, indexing="ij"), axis=-1).reshape(-1, 3)
            amounts, not_reached = self.table_amounts(nodes)
            return film_tables.log10_band_response(f.negative_dmin[pr], f.negative_dyes[:, pr], f.w_printing[:, pr], amounts), not_reached

        record = float(self.options.negative_record == "dye_amount")
        return kept_stage_table("negative", (record, *grid, f.negative_dmin, f.negative_dyes, f.negative_curve_dmin, f.w_status_m, f.w_printing), build)

    def _paper_stage(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Rule 'staged_print_table': the first and the step of the Status A axes, the cube root of print XYZ with no surface reflection, and where the dye solve did not reach."""
        f = self.film
        w_view = f.w_viewing[f.viewing_name]
        st, vi = spectral_support(f.w_status_a), spectral_support(w_view)
        start = np.array([c.density.min() for c in self.paper_curves])
        axis_range = np.array([c.density.max() for c in self.paper_curves]) - start

        def build() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
            table, not_reached = film_tables.build_paper_table(f.paper_base[st], f.paper_dyes[:, st], f.w_status_a[:, st], f.paper_base[vi], f.paper_dyes[:, vi], w_view[:, vi],
                                                               100.0 / w_view[1].sum(), start, axis_range, PAPER_AXIS_POWER, PAPER_TABLE_NODES, SOLVE_ITERATIONS, SOLVE_REACHED_LIMIT)
            return start, axis_range, table, not_reached

        return kept_stage_table("paper", (start, axis_range, float(PAPER_AXIS_POWER), float(PAPER_TABLE_NODES), f.paper_base, f.paper_dyes, f.w_status_a, w_view), build)

    def _compose_print_table(self, grid: list[np.ndarray], balance: np.ndarray) -> tuple[np.ndarray, dict]:
        """Rule 'staged_print_table': the table of this printer balance, and its counts. This stage has no spectral integral."""
        f, o = self.film, self.options
        paper_log, negative_not_reached = self._negative_stage(grid)
        start, axis_range, paper_table, not_reached = self._paper_stage()
        length = max(len(c.density) for c in self.paper_curves)
        curves = np.stack([np.pad(c.density, (0, length - len(c.density)), mode="edge") for c in self.paper_curves])
        lengths = np.array([len(c.density) for c in self.paper_curves], dtype=np.int64)
        aim = np.array([c.log_h_at(o.print_midscale_status_a) for c in self.paper_curves])
        table, outside, print_not_reached = film_tables.compose_print_table(paper_log, np.asarray(balance, dtype=np.float64), aim, float(o.print_contrast) * self.printing_gain, float(o.print_flash), o.viewing_flare * f.white_xyz(),
                                                                            curves, lengths, np.array([c.log_h[0] for c in self.paper_curves]), float(self.paper_curves[0].log_h[1] - self.paper_curves[0].log_h[0]), start, axis_range, PAPER_AXIS_POWER, paper_table, not_reached)
        if not np.isfinite(table).all():
            raise FloatingPointError(f"the print table of {o.negative_profile} on {o.print_profile} has values that are not finite")
        return table.reshape(DENSITY_NODES, DENSITY_NODES, DENSITY_NODES, 3), {"negative_not_reached": int(negative_not_reached), "print_not_reached": int(print_not_reached), "paper_exposure_outside_curve": int(outside), "nodes": DENSITY_NODES ** 3}

    def _build_print_table(self) -> tuple[list[np.ndarray], np.ndarray, dict]:
        grid = [np.linspace(c.density.min(), c.density.max(), DENSITY_NODES) for c in self.negative_curves]
        table, counts = self._compose_print_table(grid, self.film.printer_balance_log10)
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
        if spatial and any(o.layer_spread_um):
            q = self._spread_layers(q, pixel)
        if spatial and any(o.halation):
            q = fk.mix_exposure(q, fk.gaussian_blur(q, o.halation_um / pixel), np.array(o.halation, dtype=np.float64))
        density, above = fk.negative_density(q, self.film.negative_criterion_log_h, self._neutral, float(o.interlayer_gain), self._curve_start, self._curves_f64, self._curve_lengths, self._curve_step)
        if self.inhibition is not None:
            density = self._inhibited_image(q, density, pixel if spatial else 0.0)
        if spatial and o.adjacency_gain:
            density = fk.add_adjacency(density, fk.gaussian_blur(density, o.adjacency_um / pixel), float(o.adjacency_gain))
        if spatial and o.enlarger_flare:
            t = fk.density_to_transmittance(density)
            density = fk.flare_density(t, fk.gaussian_blur(t, o.enlarger_flare_size * max(image.shape[:2])), float(o.enlarger_flare))
        return density, {"moved_by_rule": int(moved), "y_not_positive": int(not_positive), "negative_above_curve_end": int(above), "pixels": int(image.shape[0] * image.shape[1])}

    def _prepare_mask(self) -> None:
        """Rule 'contrast_mask': the tables per mask density, the pan transmittance over the negative record, the density of the reference and of the grey."""
        o = self.options
        if not o.mask_gamma:
            return
        f = self.film
        rr, gg, bb = np.meshgrid(*self.density_grid, indexing="ij")
        nodes = np.stack([rr, gg, bb], axis=-1).reshape(-1, 3)
        densities = MASK_DENSITY_START + MASK_DENSITY_STEP * np.arange(MASK_DENSITY_NODES)
        balance = np.asarray(f.printer_balance_log10, dtype=np.float64)
        self._mask_tables = np.stack([self._compose_print_table(self.density_grid, balance - density)[0] for density in densities]).astype(np.float32)
        # The pan response: the printer lamp, flat inside MASK_PAN_NM. Stored as the cube root in three channels, so print_display reads it.
        pan = (10.0 ** (-f.negative_spectral_density(self._record_amounts(nodes))) @ self._mask_lamp()) / self._mask_lamp().sum()
        self._mask_pan = np.repeat(np.cbrt(pan).reshape(DENSITY_NODES, DENSITY_NODES, DENSITY_NODES, 1), 3, axis=-1).astype(np.float32)
        grey = self.layer_gain * self.c.layer_exposure(0.18 * self.scene_spectrum)
        self._mask_reference = self._pan_density_of_exposure(grey * 2.0 ** o.mask_reference_stops)
        self._mask_at_grey = self._mask_curve(self._mask_reference - self._pan_density_of_exposure(grey))

    def _mask_lamp(self) -> np.ndarray:
        wl = self.c.wavelengths
        return self.film.illuminants[self.options.printer_lamp] * ((wl >= MASK_PAN_NM[0]) & (wl <= MASK_PAN_NM[1]))

    def _record_amounts(self, record: np.ndarray) -> np.ndarray:
        if self.options.negative_record == "dye_amount":
            return record
        return self.film.negative_dye_amounts(record)

    def _pan_density_of_exposure(self, q: np.ndarray) -> float:
        record = self.negative_density(q[None])[0]
        lamp = self._mask_lamp()
        return float(-np.log10((10.0 ** (-self.film.negative_spectral_density(self._record_amounts(record))) @ lamp)[0] / lamp.sum()))

    def _mask_curve(self, x: np.ndarray) -> np.ndarray:
        o = self.options
        return o.mask_gamma * 0.5 * (x + np.sqrt(x * x + o.mask_knee_density ** 2))

    def mask_density(self, record: np.ndarray, pixel: float) -> np.ndarray:
        """The neutral density of the mask at each pixel, after the printer lights take back the density at the grey. pixel = 0: no image plane."""
        pan = fk.print_display(record, self._mask_pan, self._grid_start, self._grid_step, np.eye(3))
        if pixel:
            pan = fk.gaussian_blur(pan, self.options.mask_um / pixel)
        return (self._mask_curve(self._mask_reference + np.log10(np.maximum(pan[..., 0].astype(np.float64), 1e-9))) - self._mask_at_grey).astype(np.float32)

    def _spread_layers(self, q: np.ndarray, pixel: float) -> np.ndarray:
        """Rule 'layer_spread'. Each layer has its own length, so each one takes its channel of its own blurs."""
        lengths = np.asarray(self.options.layer_spread_um, dtype=np.float64)
        return sum(weight * fk.gaussian_blur_per_layer(q, tuple(ratio * lengths / pixel)) for weight, ratio in SPREAD_GAUSSIANS)

    def _inhibited_image(self, q: np.ndarray, amounts: np.ndarray, pixel: float) -> np.ndarray:
        """Rule 'development_inhibition' on an image. pixel = 0: no image plane."""
        i = self.inhibition
        for _ in range(INHIBITION_STEPS_IMAGE if pixel else INHIBITION_STEPS_POINT):
            inhibitor = fk.gaussian_blur_half_size(amounts, self.options.inhibition_um / pixel) if pixel else amounts
            amounts = fk.inhibited_step(q, inhibitor, self.film.negative_criterion_log_h, i["k"], i["start"], i["free"], i["lengths"], i["step"])
        return amounts

    def render(self, ap1: np.ndarray, detailed: bool = False) -> tuple[np.ndarray, dict]:
        """Linear AP1 to sRGB, through the kernels. detailed adds the percentiles of the gamut distance (slower)."""
        o = self.options
        shape = ap1.shape
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        if image.ndim == 2:
            image = image[None]
        density, stats = self.negative_image(image)
        if o.mask_gamma:
            pixel = self._pixel_um(image) if min(image.shape[:2]) >= 16 else 0.0
            rgb = fk.print_display_masked(density, self.mask_density(density, pixel), self._mask_tables, MASK_DENSITY_START, MASK_DENSITY_STEP, self._grid_start, self._grid_step, self.xyz_to_display)
        else:
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
        if self.options.mask_gamma:
            raise ValueError("reference_render has no form of rule contrast_mask")
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


def light_sector_weight(u: np.ndarray, v: np.ndarray, white_uv: np.ndarray, directions: dict[str, np.ndarray]) -> np.ndarray:
    """Weight of rule 'light_like_spectra' at the points of u'v'. directions: unit vector per sector, from the white."""
    du, dv = u - white_uv[0], v - white_uv[1]
    radius = np.hypot(du, dv)

    def smoothstep(x: np.ndarray) -> np.ndarray:
        x = np.clip(x, 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    weight = np.zeros_like(radius)
    for name, direction in directions.items():
        angle = np.degrees(np.arccos(np.clip((du * direction[0] + dv * direction[1]) / np.maximum(radius, 1e-12), -1.0, 1.0)))
        low, high = LIGHT_SECTOR_RADIUS[name]
        weight = np.maximum(weight, (1.0 - smoothstep((angle - LIGHT_SECTOR_DEGREES[0]) / (LIGHT_SECTOR_DEGREES[1] - LIGHT_SECTOR_DEGREES[0]))) * smoothstep((radius - low) / (high - low)))
    return weight


def light_directions(c: sr.Colorimetry, white_uv: np.ndarray) -> dict[str, np.ndarray]:
    """Directions of the sectors in u'v', from spectra against the reference light: skylight (lambda^-4, Rayleigh) and a Planckian light of 2500 K."""
    wl = c.wavelengths

    def direction(spectrum: np.ndarray) -> np.ndarray:
        xyz = c.xyz(spectrum)
        offset = np.array([4.0 * xyz[0], 9.0 * xyz[1]]) / (xyz[0] + 15.0 * xyz[1] + 3.0 * xyz[2]) - white_uv
        return offset / np.hypot(*offset)

    return {"blue": direction(c.e_ref * (550.0 / wl) ** 4), "warm": direction(wl ** -5.0 / np.expm1(1.4388e7 / (wl * 2500.0)))}


def light_like_spectra(rho: np.ndarray, c: sr.Colorimetry, white_uv: np.ndarray) -> np.ndarray:
    """Rule 'light_like_spectra': see the header. rho: (nodes, wavelengths), with Y = 1 under E_ref. A node in a sector that the family cannot reach keeps the measured shape and is counted."""
    u, v = np.meshgrid(*FilmPreview.uv_axes(), indexing="ij")
    weight = light_sector_weight(u.ravel(), v.ravel(), white_uv, light_directions(c, white_uv))
    index = np.flatnonzero(weight > 0.0)
    to_xyz = c.w_xyz * c.e_ref
    x = (c.wavelengths - 560.0) / 100.0
    basis = np.stack([np.ones_like(x), x, x * x])
    uu, vv = u.ravel()[index], np.maximum(v.ravel()[index], 1e-3)
    target = np.stack([9.0 * uu / (4.0 * vv), np.ones_like(uu), (12.0 - 3.0 * uu - 20.0 * vv) / (4.0 * vv)], axis=-1)
    white = (np.ones_like(x) @ to_xyz.T)[None, :]
    coefficient = np.zeros((len(index), 3))
    for step in range(1, LIGHT_FIT_STEPS + 1):
        aim = white + (target - white) * step / LIGHT_FIT_STEPS
        for _ in range(12):
            shape = np.exp(np.clip(coefficient @ basis, -60.0, 60.0))
            error = aim - shape @ to_xyz.T
            jacobian = np.einsum("ni,ai,bi->nab", shape, to_xyz, basis, optimize=True)
            jacobian += 1e-10 * np.trace(jacobian, axis1=1, axis2=2)[:, None, None] * np.eye(3)
            move = np.linalg.solve(jacobian, error[..., None])[..., 0]
            limit = np.minimum(1.0, 2.0 / np.maximum(np.abs(move).max(axis=1), 1e-12))
            coefficient += limit[:, None] * move
    shape = np.exp(np.clip(coefficient @ basis, -60.0, 60.0))
    error = np.abs(shape @ to_xyz.T - target).max(axis=1) / np.maximum(np.abs(target).max(axis=1), 1e-12)
    reached = error <= LIGHT_FIT_LIMIT
    print(f"rule light_like_spectra: nodes in the sectors {len(index)}, not reached {int((~reached).sum())}", flush=True)
    # The family cannot reach the nodes near and outside the spectral locus. The weight falls to zero toward them, so the table has no step there.
    reachable = np.ones(u.size)
    reachable[index[~reached]] = 0.0
    step = np.array(UV_MAX) / (UV_NODES - 1)
    fade = np.clip(2.0 * gaussian_filter(reachable.reshape(u.shape), (LIGHT_REACH_FADE / step[0], LIGHT_REACH_FADE / step[1]), mode="nearest").ravel() - 1.0, 0.0, 1.0)
    fade = fade * fade * (3.0 - 2.0 * fade)
    used = weight[index[reached], None] * fade[index[reached], None]
    out = rho.copy()
    out[index[reached]] = (1.0 - used) * rho[index[reached]] + used * shape[reached]
    return out


def foliage_spectra(rho: np.ndarray, c: sr.Colorimetry, white_uv: np.ndarray) -> np.ndarray:
    """Rule 'foliage_spectra': see the header. rho: (nodes, wavelengths), with Y = 1 under E_ref. A linear blend of two shapes with one XYZ keeps the XYZ of each node."""
    u, v = np.meshgrid(*FilmPreview.uv_axes(), indexing="ij")
    to_xyz = c.w_xyz * c.e_ref
    wl = c.wavelengths
    leaf = 0.035 + 0.125 * np.exp(-0.5 * ((wl - 552.0) / 32.0) ** 2) + 0.45 / (1.0 + np.exp(-(wl - 712.0) / 11.0))
    leaf_xyz = leaf @ to_xyz.T
    leaf, leaf_xyz = leaf / leaf_xyz[1], leaf_xyz / leaf_xyz[1]
    leaf_uv = np.array([4.0 * leaf_xyz[0], 9.0 * leaf_xyz[1]]) / (leaf_xyz[0] + 15.0 * leaf_xyz[1] + 3.0 * leaf_xyz[2])
    direction = (leaf_uv - white_uv) / np.linalg.norm(leaf_uv - white_uv)
    du, dv = u.ravel() - white_uv[0], v.ravel() - white_uv[1]
    radius = np.hypot(du, dv)
    angle = np.degrees(np.arccos(np.clip((du * direction[0] + dv * direction[1]) / np.maximum(radius, 1e-12), -1.0, 1.0)))

    def smoothstep(x: np.ndarray) -> np.ndarray:
        x = np.clip(x, 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    weight = (1.0 - smoothstep((angle - FOLIAGE_DEGREES[0]) / (FOLIAGE_DEGREES[1] - FOLIAGE_DEGREES[0]))) * smoothstep((radius - FOLIAGE_RADIUS[0]) / (FOLIAGE_RADIUS[1] - FOLIAGE_RADIUS[0]))
    index = np.flatnonzero(weight > 0.0)
    x = (wl - 560.0) / 100.0
    basis = np.stack([np.ones_like(x), x, x * x])
    uu, vv = u.ravel()[index], np.maximum(v.ravel()[index], 1e-3)
    target = np.stack([9.0 * uu / (4.0 * vv), np.ones_like(uu), (12.0 - 3.0 * uu - 20.0 * vv) / (4.0 * vv)], axis=-1)
    coefficient = np.zeros((len(index), 3))
    for step in range(1, FOLIAGE_FIT_STEPS + 1):
        aim = leaf_xyz[None] + (target - leaf_xyz[None]) * step / FOLIAGE_FIT_STEPS
        for _ in range(12):
            shape = leaf * np.exp(np.clip(coefficient @ basis, -60.0, 60.0))
            error = aim - shape @ to_xyz.T
            jacobian = np.einsum("ni,ai,bi->nab", shape, to_xyz, basis, optimize=True)
            jacobian += 1e-10 * np.trace(jacobian, axis1=1, axis2=2)[:, None, None] * np.eye(3)
            move = np.linalg.solve(jacobian, error[..., None])[..., 0]
            limit = np.minimum(1.0, 2.0 / np.maximum(np.abs(move).max(axis=1), 1e-12))
            coefficient += limit[:, None] * move
    shape = leaf * np.exp(np.clip(coefficient @ basis, -60.0, 60.0))
    error = np.abs(shape @ to_xyz.T - target).max(axis=1) / np.maximum(np.abs(target).max(axis=1), 1e-12)
    reached = error <= FOLIAGE_FIT_LIMIT
    print(f"rule foliage_spectra: nodes in the sector {len(index)}, not reached {int((~reached).sum())}", flush=True)
    # The family cannot reach the nodes near and outside the spectral locus. The weight falls to zero toward them, so the table has no step there.
    blocked = np.zeros(u.size, dtype=bool)
    blocked[index[~reached]] = True
    distance = distance_transform_edt(~blocked.reshape(u.shape), sampling=(u[1, 0] - u[0, 0], v[0, 1] - v[0, 0])).ravel()
    used = (weight[index] * reached * smoothstep(distance[index] / FOLIAGE_REACH_FADE))[:, None]
    out = rho.copy()
    out[index] = (1.0 - used) * rho[index] + used * shape
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
