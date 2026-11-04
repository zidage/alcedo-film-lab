"""The shared pipeline of the Python MVP: RAW file to display image, by the print method, the APD scan method, or a reversal film on a light table.

Input: a RAW file that LibRaw reads, a negative and a print material of stock_catalog.json, a scene light, a spectral prior, and the product grade.
Output: sRGB display code (float32) with its parameters. No value of a frame is kept between renders. The print and APD tables are built in memory and are not stored (ROADMAP U68); the reflectance tables stay in build/tmp/p2/tables/.
Step: P6, ROADMAP U61 and U64. The negative chain and the print are those of P2 to P5 (film_preview.py). The APD method is the path of P3 (aces_scan.py): APD (ST 2065-2), ADX10 (ST 2065-3), the mid grey at code value 445, ADX10 to ACES, and an ACES output transform.

Rules of this step:
- 'stock_options_from_catalog': an accepted stock of P4 and P5 keeps its values. A new stock takes the rules of P5: exposure of the grey 12.5 / ISO lux seconds (inferred),
  the published dye curves or the band split, and spread and inhibition from its modulation transfer curves when it has them.
- 'print_conditions_by_medium': a cine print material takes the conditions of 2383 (projection at D65, neutral printing, grey aim 0.85), and a paper takes those of Endura (D50 viewing, grey aim 0.75).
- 'no_anchor_at_reference_light': the default scene has no rule grey_anchor (U58). Another scene light needs the rule, because the printer balance follows the light. A stock with a relative sensitivity chart keeps the rule at each light.
- 'spectral_prior': 'light_like' applies rule 'light_like_spectra' of P4, and 'measured_reflectance' uses the reflectance prior of P1 with no change.
- 'foliage_spectra': off by default since U93 (2026-11-04: some photos look strange with it); on through RenderSettings.foliage; see the header of film_preview.py.
- 'negative_show_grade': on for the tungsten stocks on print material cine_look (ROADMAP U82 to U84); see negative_grade.py.
- 'light_table' (step P9, ROADMAP U86): the method of the reversal films of reversal_catalog.json, with no print. The film is the field 'reversal'; see scripts/poc/p9_reversal_light_table/reversal_film.py.
  The controls of the negative act on the slide, 'Enlarger flare' is the flare of the loupe, and the print controls do not act.
- 'chart_scan' (step P10, ROADMAP U88): the negative of the stock read with Status M densitometry, inverted from a chart and a grey scale photographed
  on the same stock (scripts/poc/p10_chart_scan/chart_scan.py, SELECTED_FORM): the straight line of the grey scale per channel, the sensitivity
  matrix of the stock, the scan timing of option print_timing, the display compression on Rec. 709, and a log curve per channel. No ACES
  output transform and no statistic of a frame. The print controls do not act. Setting chart_scan_slope (U89): 'fixed' (default) applies rule
  'fixed_scan_slope', one Status M slope per channel for all stocks; 'stock' is the form of U88, the slope of the grey scale of each stock.
  Round 7 (U90): setting chart_scan_reading 'dye' (default) reads the dye amounts with the Status M contrast of U89 (chart_scan.py rule
  'dye_reading_density_contrast'), 'status_m' is the reading of U88 and U89; chart_scan_matrix 'code' (default) curves the film channels and then
  applies the matrix to the codes (rule 'scan_matrix_domain'), 'linear' is the form of U88; control chart_scan_black is rule 'scan_base_black'
  (1: black at the film base); control chart_scan_timing is the scan timing (it replaces print_timing for this method).
  Round 8 (U91): setting chart_scan_display, 'log_curve' (default) or a display rendering transform of a public OCIO config ('aces20', 'agx',
  'opendrt') or the Cineon conversion ('cineon'), on the linear AP1 of the scan (p10_chart_scan/display_transforms.py).
- Scene light 'as_shot' (U90, P4 rule 'light_from_raw_white'): the camera white balance and the camera matrix of the RAW file give the XYZ
  of the neutral and a correlated colour temperature (McCamy), clipped to 2000-15000 K; the light is film_preview.cct_light (U92: Planckian to
  4000 K, CIE daylight from 5000 K, a blend linear in mired between). The
  renderer replaces 'as_shot' with the name of that light (as_shot_light). A RAW file with no camera matrix stops with an error.
- 'user_controls': CONTROLS lists the values that the user can change, with their ranges. Each one is a value of the model or of the APD method that was fixed before; the defaults give the same image as before. They are creative controls and not measurements. A value outside its range stops with an error.
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
from aces_scan import DRT_GREYS, DRT_OUTPUTS, ENCODINGS, OUTPUT_TRANSFORMS, READINGS, ScanPreview, fp  # noqa: E402

SCAN_OUTPUTS = (*OUTPUT_TRANSFORMS, *DRT_OUTPUTS)  # U92
SCAN_COLOURS = ("academy", "print_hue_scene_chroma", "print_hue_scan_chroma", "scene_hue_scan_chroma", "print_hue_print_chroma")  # U95, scan_colour.COLOURS

sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p9_reversal_light_table"))
import reversal_film as rf  # noqa: E402

CATALOG = json.loads((SCRIPT_DIR / "stock_catalog.json").read_text(encoding="utf-8"))
# Print material 'cine_look' (ROADMAP U83): the data of Kodak 2383, with rules 'print_cinema_look' and 'negative_show_grade'. Print material kodak_2383 has neither of them.
CINE_LOOK_PRINT = "cine_look"
CINE_LOOK_BASE_PRINT = "kodak_2383"
CATALOG["prints"][CINE_LOOK_PRINT] = {**CATALOG["prints"][CINE_LOOK_BASE_PRINT], "name": "Cine Look (2383)"}
# List order of the viewer and of the product (ROADMAP U83): the common stocks first, then Fuji, then the old Kodak stocks. kFilmNegativeIds and kFilmPrintMaterialIds of Alcedo Studio have the same order.
NEGATIVE_ORDER = ("kodak_5207", "kodak_5219", "kodak_5213", "kodak_5203", "kodak_5206", "kodak_portra_400", "kodak_portra_160", "kodak_portra_800", "kodak_ektar_100", "kodak_gold_200", "kodak_ultramax_400",
                  "fuji_eterna_500", "fuji_eterna_500_vivid", "fuji_pro_400h", "fuji_pro_160c", "fuji_pro_160s", "fuji_natura_1600", "fuji_superia_xtra_400", "fuji_superia_reala", "fuji_c200",
                  "kodak_5277", "kodak_5293", "kodak_exr_5248", "kodak_5248", "kodak_5247", "kodak_5247_II", "kodak_5250", "kodak_vericolor_iii", "kodak_aerocolor", "agfa_vista_100")
PRINT_ORDER = (CINE_LOOK_PRINT, "kodak_2383", "kodak_endura_premier", "kodak_portra_endura", "kodak_supra_endura", "kodak_2393",
               "fuji_3513di", "fuji_3523XD", "fuji_ca_maxima", "fuji_ca_dpII", "fuji_ca_pdII", "fuji_ca_super_c", "fujiflex_new", "fujiflex_old",
               "kodak_duraflex_plus", "kodak_5383", "kodak_5384", "kodak_5381", "kodak_exr_5386")
CATALOG["negatives"] = {key: CATALOG["negatives"][key] for key in NEGATIVE_ORDER}
CATALOG["prints"] = {key: CATALOG["prints"][key] for key in PRINT_ORDER}
PHYSICS_PATH = SCRIPT_DIR / "stock_physics.json"
IMAGE_PART_PATH = SCRIPT_DIR / "inhibition_image.json"
ACCEPTED_STOCKS = {"kodak_5207": "5207_2383", "kodak_5219": "5219_2383", "kodak_portra_400": "portra400_endura", "kodak_portra_160": "portra160_endura",
                   "kodak_portra_800": "portra800_endura", "kodak_ektar_100": "ektar100_endura", "kodak_gold_200": "gold200_endura", "fuji_c200": "c200_endura"}
STOCK_PRINT_FIELDS = ("print_profile", "print_midscale_status_a", "viewing_cct_k", "neutral_printing", "grey_anchor", "balance_light", "scene_light")
REFERENCE_LIGHT = "reference"
AS_SHOT = "as_shot"
SCENE_LIGHTS = (REFERENCE_LIGHT, AS_SHOT, *fp.PRODUCT_LIGHTS, *fp.SCENE_PRESETS)
SPECTRAL_PRIORS = ("light_like", "measured_reflectance")
METHODS = ("print", "apd", "light_table", "chart_scan")
REVERSAL_ORDER = ("fuji_velvia_50", "fuji_velvia_100", "fuji_provia_100f", "fuji_astia_100f", "kodak_ektachrome_e100")
CATALOG["reversals"] = {key: rf.CATALOG["films"][key] for key in REVERSAL_ORDER}
SCAN_CARRIER_PRINT = "kodak_2383"
# Rule 'negative_show_grade', on print material cine_look (ROADMAP U82 to U84): the tungsten stocks. kodak_5293 is EXR 200T, and the catalog holds the default 5500 K for it.
NEGATIVE_GRADE_STOCKS = ("kodak_5219", "kodak_5213", "kodak_5277", "kodak_5293", "kodak_exr_5248", "fuji_eterna_500", "fuji_eterna_500_vivid")
DEFAULT_LONG_EDGE = 2048
MEDIUM_WHITE = "by_medium"
DISPLAY_WHITES = (MEDIUM_WHITE, "reflector", "paper", "print_dmin")
PRINT = ("print",)
SCAN = ("apd",)
LIGHT_TABLE = ("light_table",)
CHART_SCAN = ("chart_scan",)
CHART_SCAN_SLOPES = ("fixed", "stock")
CHART_SCAN_READINGS = ("dye", "status_m")
CHART_SCAN_MATRICES = ("code", "linear")
CHART_SCAN_DISPLAYS = ("log_curve", "aces20", "agx", "opendrt", "cineon")
BOTH = METHODS


@dataclass(frozen=True)
class Control:
    """One value that the user can change: the field of RenderSettings, its text, its range, and the methods that use it."""

    name: str
    label: str
    group: str
    low: float
    high: float
    step: float
    decimals: int
    methods: tuple[str, ...]
    note: str


CONTROLS = (
    Control("overexposure_stops", "Overexposure (stops)", "Negative", -2.0, 4.0, 0.25, 2, (*PRINT, *SCAN, *CHART_SCAN), "Rule overexposed_negative: the negative takes more light, and the printer lights take it back. It moves the shadows off the toe."),
    Control("inhibition_scale", "Development inhibition", "Negative", 0.0, 1.5, 0.1, 2, BOTH, "Scale of the inhibition from the modulation transfer curves. 0: off. A stock with no curve has no inhibition."),
    Control("layer_spread_scale", "Light spread", "Negative", 0.0, 3.0, 0.25, 2, BOTH, "Scale of the spread length of each layer. 0: off. A stock with no curve has no spread."),
    Control("halation_scale", "Halation", "Negative", 0.0, 8.0, 0.5, 2, BOTH, "Scale of the halation strength. 0: off."),
    Control("halation_um", "Halation length (um)", "Negative", 20.0, 500.0, 20.0, 0, BOTH, "Length of the halation on a frame of 36 mm."),
    Control("scene_flare", "Lens flare", "Negative", 0.0, 0.02, 0.001, 4, BOTH, "Veiling glare of the taking lens, a neutral addition before the film."),
    Control("print_grey_shift", "Print grey density shift", "Print", -0.3, 0.4, 0.05, 2, PRINT, "Added to the Status A density of mid grey: the LAD patch on a cine print, 0.75 on a paper. A higher value gives a darker print."),
    Control("print_contrast", "Print contrast", "Print", 0.5, 1.3, 0.05, 2, PRINT, "Scale of the paper log exposure about the grey. 1: the published curve."),
    Control("print_flash", "Paper flash", "Print", 0.0, 0.2, 0.01, 3, PRINT, "Uniform exposure of the paper, as a share of the balance exposure. It softens the print highlights."),
    Control("enlarger_flare", "Enlarger flare", "Print", 0.0, 0.1, 0.005, 3, (*PRINT, *LIGHT_TABLE), "Stray light of the enlarger lens, as a share of the light. It lifts the print shadows. On the light table: the flare of the loupe, in linear light; it lifts the shadows of the slide."),
    Control("viewing_flare", "Surface reflection", "Print", 0.0, 0.03, 0.001, 4, PRINT, "Reflection of the print surface. It lifts the black."),
    Control("print_timing", "Timing", "Negative", 0.0, 1.0, 0.1, 2, (*PRINT, *SCAN), "Share of the mid grey cast of the scene light that the printer lights or the scanner offset remove. It acts when the scene light is not 'reference', and on a stock with a relative sensitivity chart."),
    Control("apd_exposure_stops", "Scanner light (stops)", "Scan", -3.0, 3.0, 0.25, 2, SCAN, "One neutral offset of the ADX10 code values. 0: the mid grey at code value 445, as the ADX to ACES transform assumes. +0.53 on ACES 2.0 and +0.37 on ACES 1.3 show the grey of the print (P3 report)."),
    Control("chart_scan_timing", "Scan timing", "Chart scan", 0.0, 1.0, 0.05, 2, CHART_SCAN, "Rule scan_timing: share of the mid grey cast of the scene light that the scan removes. 1: a grey of any light is neutral. Below 1, part of the cast stays, as a lab that does not correct a frame in full (U90)."),
    Control("chart_scan_black", "Black at film base", "Chart scan", 0.0, 2.0, 0.25, 2, CHART_SCAN, "Rule scan_base_black: share of the value of the unexposed film that the scanner takes as black. 1: black at the film base. Above 1, the toe of the negative clips to black (U90)."),
    Control("chart_scan_exposure_stops", "Scan exposure (stops)", "Chart scan", -3.0, 3.0, 0.25, 2, CHART_SCAN, "Rule scan_exposure: one neutral scale of the scene values before the log curve, as a scanner light. 0: the grey of the chart shows as a digital grey."),
)


@dataclass(frozen=True)
class RenderSettings:
    negative: str = "kodak_5207"
    method: str = "print"
    reversal: str = "kodak_ektachrome_e100"
    print_material: str = "kodak_endura_premier"
    scene_light: str = REFERENCE_LIGHT
    spectral_prior: str = "light_like"
    foliage: bool = False  # U93
    negative_grade: bool = True
    exposure_ev: float = 1.5
    contrast: float = float(fp.PRODUCT_CONTRAST)
    saturation: float = float(fp.PRODUCT_SATURATION)
    overexposure_stops: float = 0.0
    inhibition_scale: float = 1.0
    layer_spread_scale: float = 1.0
    halation_scale: float = 1.0
    halation_um: float = float(fp.FilmOptions().halation_um)
    scene_flare: float = float(fp.FilmOptions().scene_flare)
    print_grey_shift: float = 0.0
    print_contrast: float = float(fp.DARKROOM["print_contrast"])
    print_flash: float = float(fp.DARKROOM["print_flash"])
    enlarger_flare: float = float(fp.DARKROOM["enlarger_flare"])
    viewing_flare: float = float(fp.DARKROOM["viewing_flare"])
    print_timing: float = float(fp.FilmOptions().print_timing)
    display_white: str = MEDIUM_WHITE
    gamut_compress: bool = bool(fp.DARKROOM["gamut_compress"])
    apd_exposure_stops: float = 0.0
    chart_scan_exposure_stops: float = 0.0
    chart_scan_slope: str = "fixed"
    chart_scan_reading: str = "dye"
    chart_scan_matrix: str = "code"
    chart_scan_display: str = "log_curve"
    chart_scan_timing: float = 0.75
    chart_scan_black: float = 1.0
    apd_lad_aim: bool = True
    apd_output: str = "opendrt"  # U95: the display of the product form
    apd_reading: str = "print2383"  # U95: the reading of the product form
    apd_drt_grey: str = "native"  # U95: the grey of the product form
    apd_encoding: str = "adx16"  # U93
    apd_slope_match: bool = True  # U93, rule 'adx_slope_match' of aces_scan.py
    apd_colour: str = "academy"  # U95, rule 'scan_print_colour' of p10_chart_scan/scan_colour.py; 'academy': no correction (U96)
    apd_numbers: str = "stock"  # U96: 'stock' (rule 'adx_stock_numbers' of p10_chart_scan/scan_unbuild.py) or 'academy'
    apd_untimed: str = "stock_balance"  # U96: the LAD aim off; 'stock_balance' (the grey of the balance light of the stock on the aim) or 'film_base' (offset 0, U92)
    apd_axis: str = "academy"  # U97: the LAD aim off with numbers 'stock'; 'academy' (rule 'untimed_axis_academy' of p10_chart_scan/scan_axis.py) or 'numbers' (U96)

    def validate(self) -> None:
        if self.reversal not in CATALOG["reversals"]:
            raise ValueError(f"unknown reversal film {self.reversal!r}")
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
        if self.scene_light not in SCENE_LIGHTS and not is_light_name(self.scene_light):
            raise ValueError(f"unknown scene light {self.scene_light!r}")
        if self.scene_light == AS_SHOT:
            raise ValueError("scene light 'as_shot' needs the white of a RAW file: render through resolve_as_shot")
        if self.chart_scan_reading not in CHART_SCAN_READINGS:
            raise ValueError(f"unknown chart scan reading {self.chart_scan_reading!r}")
        if self.chart_scan_display not in CHART_SCAN_DISPLAYS:
            raise ValueError(f"unknown chart scan display {self.chart_scan_display!r}")
        if self.chart_scan_matrix not in CHART_SCAN_MATRICES:
            raise ValueError(f"unknown chart scan matrix {self.chart_scan_matrix!r}")
        if self.spectral_prior not in SPECTRAL_PRIORS:
            raise ValueError(f"unknown spectral prior {self.spectral_prior!r}")
        if self.display_white not in DISPLAY_WHITES:
            raise ValueError(f"unknown display white {self.display_white!r}")
        if self.chart_scan_slope not in CHART_SCAN_SLOPES:
            raise ValueError(f"unknown chart scan slope {self.chart_scan_slope!r}")
        if self.apd_output not in SCAN_OUTPUTS:
            raise ValueError(f"unknown output {self.apd_output!r}")
        if self.apd_drt_grey not in DRT_GREYS:
            raise ValueError(f"unknown DRT grey {self.apd_drt_grey!r}")
        if self.apd_reading not in READINGS:
            raise ValueError(f"unknown scanner reading {self.apd_reading!r}")
        if self.apd_encoding not in ENCODINGS:
            raise ValueError(f"unknown scan encoding {self.apd_encoding!r}")
        if self.apd_colour not in SCAN_COLOURS:
            raise ValueError(f"unknown scan colour {self.apd_colour!r}")
        if self.apd_numbers not in ("stock", "academy") or self.apd_untimed not in ("stock_balance", "film_base") or self.apd_axis not in ("academy", "numbers"):
            raise ValueError(f"unknown scan numbers {self.apd_numbers!r}, untimed form {self.apd_untimed!r} or axis {self.apd_axis!r}")
        for control in CONTROLS:
            value = getattr(self, control.name)
            if not control.low <= value <= control.high:
                raise ValueError(f"{control.name} = {value}: outside its range {control.low} to {control.high}")


def load_physics() -> dict:
    return json.loads(PHYSICS_PATH.read_text(encoding="utf-8")) if PHYSICS_PATH.exists() else {}


def load_image_part() -> dict:
    return json.loads(IMAGE_PART_PATH.read_text(encoding="utf-8")) if IMAGE_PART_PATH.exists() else {}


def negative_options(negative: str, physics: dict | None = None, image_part: bool = True) -> dict:
    """Rule 'stock_options_from_catalog', with no print condition. image_part: the spread and the image part of the inhibition of rule 'inhibition_image_part'."""
    options = _stock_options(negative, physics)
    fitted = load_image_part().get(negative) if image_part and any(options.get("inhibition_total", ())) else None
    if fitted:
        # Rule 'inhibition_total_from_image_part' (ROADMAP U80): K has only the part that the chart of the stock supports at the length of the inhibitor.
        options.update(layer_spread_um=tuple(fitted["layer_spread_um"]), inhibition_image=tuple(fitted["inhibition_image"]), inhibition_total=tuple(fitted["inhibition_image"]))
    return options


def _stock_options(negative: str, physics: dict | None) -> dict:
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
    """Rule 'print_conditions_by_medium' (ROADMAP U78). A cine print: the LAD aim, the projection light, the clear print as white, and the dark surround. A paper: 18 % reflectance for the grey, D50, and the perfect reflector as white."""
    if CATALOG["prints"][print_material]["medium"].lower() == "cine":
        return dict(print_profile=CINE_LOOK_BASE_PRINT if print_material == CINE_LOOK_PRINT else print_material, print_midscale_status_a=fp.CINE_GREY_STATUS_A, viewing_cct_k=fp.CINE_VIEWING_CCT_K, neutral_printing=False, printer_filter=fp.CINE_PRINTER_FILTER, display_white="print_dmin", surround_exponent=fp.CINE_SURROUND_EXPONENT, print_slope_match=fp.CINE_PRINT_SLOPE_MATCH, cinema_look=print_material == CINE_LOOK_PRINT)
    return dict(print_profile=print_material, print_midscale_status_a=0.75, viewing_cct_k=5000.0, neutral_printing=False, display_white="reflector")


def is_light_name(name: str) -> bool:
    """A light of rule 'light_from_raw_white': 'D' and hundreds of kelvin (CIE daylight), 'T' and kelvin (Planckian), or 'CCT' and kelvin (either, by the rule; U92)."""
    return (len(name) > 2 and name[0] in "DT" and name[1:].isdigit()) or (name.startswith("CCT") and name[3:].isdigit())


def as_shot_light(path: Path) -> tuple[str, float]:
    """P4 rule 'light_from_raw_white' (render_light_and_detail_review.estimated_light): the light name and the CCT in K."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        multipliers = np.array(raw.camera_whitebalance[:3], dtype=np.float64)
        camera_from_xyz = np.array(raw.rgb_xyz_matrix[:3], dtype=np.float64)
    if multipliers.min() <= 0.0 or abs(np.linalg.det(camera_from_xyz)) < 1e-9:
        raise ValueError(f"{Path(path).name}: the RAW file has no camera white balance or no camera matrix, so scene light 'as_shot' cannot run")
    xyz = np.linalg.solve(camera_from_xyz, 1.0 / multipliers)
    x, y = xyz[0] / xyz.sum(), xyz[1] / xyz.sum()
    n = (x - 0.3320) / (y - 0.1858)
    cct = float(-449.0 * n ** 3 + 3525.0 * n ** 2 - 6823.3 * n + 5520.33)
    # U92: the continuous form of the rule (film_preview.cct_light), on the colour temperature range of the RAW white balance of Alcedo Studio.
    return f"CCT{int(round(np.clip(cct, 2000.0, 15000.0)))}", cct


def resolve_as_shot(settings: "RenderSettings", path: Path) -> "RenderSettings":
    """Scene light 'as_shot': the light of the RAW white in its place. Other lights do not change."""
    return replace(settings, scene_light=as_shot_light(path)[0]) if settings.scene_light == AS_SHOT else settings


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


def scan_colour_print(settings: RenderSettings) -> fp.FilmOptions | None:
    """Rule 'scan_colour_print_by_medium' (U95): the print of rule 'scan_print_colour' is Kodak 2383 for a cine negative and Kodak Endura Premier for a
    photo negative, under the scene light of the scan."""
    if settings.apd_colour == "academy":
        return None
    paper = "kodak_2383" if CATALOG["negatives"][settings.negative]["medium"].lower() == "cine" else "kodak_endura_premier"
    return film_options(replace(settings, method="print", print_material=paper))


def film_options(settings: RenderSettings, print_material: str | None = None, physics: dict | None = None, image_part: bool = True) -> fp.FilmOptions:
    material = print_material or settings.print_material
    options = fp.FilmOptions(**{**fp.DARKROOM, **negative_options(settings.negative, physics, image_part), **print_conditions(material), **light_conditions(settings.negative, settings.scene_light, physics),
                                "light_spectra": settings.spectral_prior == "light_like", "foliage": settings.foliage, "entry_gamut_compress": settings.method == "print",
                                "negative_grade": settings.negative_grade and settings.method == "print" and material == CINE_LOOK_PRINT and settings.negative in NEGATIVE_GRADE_STOCKS})

    def scaled(values: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
        return tuple(float(v) * scale for v in values)

    return replace(options, overexposure_stops=settings.overexposure_stops, inhibition_total=scaled(options.inhibition_total, settings.inhibition_scale),
                   inhibition_image=None if options.inhibition_image is None else scaled(options.inhibition_image, settings.inhibition_scale), layer_spread_um=scaled(options.layer_spread_um, settings.layer_spread_scale),
                   halation=scaled(options.halation, settings.halation_scale), halation_um=settings.halation_um, scene_flare=settings.scene_flare, print_midscale_status_a=tuple(np.broadcast_to(options.print_midscale_status_a, 3) + settings.print_grey_shift),
                   print_contrast=settings.print_contrast, print_flash=settings.print_flash, enlarger_flare=settings.enlarger_flare, viewing_flare=settings.viewing_flare, print_timing=settings.print_timing,
                   display_white=options.display_white if settings.display_white == MEDIUM_WHITE else settings.display_white, gamut_compress=settings.gamut_compress)


def chart_scan_reading(settings: RenderSettings) -> dict:
    """Options of ChartScanPreview for setting chart_scan_reading: 'dye' (U90) or 'status_m' with setting chart_scan_slope (U88, U89)."""
    if settings.chart_scan_reading == "dye":
        return dict(scanner="analytical", slope_source="density")
    return dict(scanner="status_m", slope_source=settings.chart_scan_slope)


def control_values(settings: RenderSettings, method: str) -> tuple:
    """The values of a model of this method, so that a change of a control of the other method keeps the model."""
    values = (settings.foliage, settings.negative_grade, *(getattr(settings, c.name) for c in CONTROLS if method in c.methods))
    if method == "light_table":
        return (*values, settings.gamut_compress)
    if method == "chart_scan":
        return (*values, settings.chart_scan_slope, settings.chart_scan_reading, settings.chart_scan_matrix, settings.chart_scan_display)
    return (*values, settings.display_white, settings.gamut_compress) if method == "print" else (*values, settings.apd_lad_aim, settings.apd_output, settings.apd_reading, settings.apd_drt_grey, settings.apd_encoding, settings.apd_slope_match, settings.apd_colour, settings.apd_numbers, settings.apd_untimed, settings.apd_axis)


def light_table_options(settings: RenderSettings) -> fp.FilmOptions:
    """Method 'light_table' (step P9): the options of the reversal film with the values of the controls of this method."""
    options = rf.reversal_options(settings.reversal, settings.scene_light, foliage=settings.foliage, light_spectra=settings.spectral_prior == "light_like")

    def scaled(values: tuple[float, float, float], scale: float) -> tuple[float, float, float]:
        return tuple(float(v) * scale for v in values)

    return replace(options, inhibition_total=scaled(options.inhibition_total, settings.inhibition_scale), inhibition_image=None if options.inhibition_image is None else scaled(options.inhibition_image, settings.inhibition_scale),
                   layer_spread_um=scaled(options.layer_spread_um, settings.layer_spread_scale), halation=scaled(options.halation, settings.halation_scale), halation_um=settings.halation_um,
                   scene_flare=settings.scene_flare, enlarger_flare=settings.enlarger_flare, gamut_compress=settings.gamut_compress)


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
    """One render at a time. It keeps the models of the last settings, because a new model reads the reflectance tables and computes its weights."""

    def __init__(self) -> None:
        self._models: dict[tuple, object] = {}

    def _model(self, tag: tuple, build):
        if tag not in self._models:
            if len(self._models) >= 4:
                self._models.pop(next(iter(self._models)))
            self._models[tag] = build()
        return self._models[tag]

    def print_model(self, settings: RenderSettings) -> fp.FilmPreview:
        return self._model(("print", settings.negative, settings.print_material, settings.scene_light, settings.spectral_prior, control_values(settings, "print")), lambda: fp.FilmPreview(film_options(settings)))

    def scan_model(self, settings: RenderSettings) -> ScanPreview:
        negative_only = replace(settings, **{c.name: getattr(RenderSettings(), c.name) for c in CONTROLS if "apd" not in c.methods})
        return self._model(("scan", settings.negative, settings.scene_light, settings.spectral_prior, control_values(settings, "apd")), lambda: self._scan(settings, negative_only))

    def _scan(self, settings: RenderSettings, negative_only: RenderSettings) -> ScanPreview:
        """Method 'apd'. With the LAD aim off and numbers 'stock', axis 'academy' (U97): the neutral axis of the untimed scan through the Academy
        numbers, the colours about it through the stock numbers. With the LAD aim off, form 'stock_balance' (U96) is the LAD aim at the balance light of the stock (timing 0): a lab scans
        each film type with its own channel balance, and only the cast of the scene light against that light stays. Numbers 'stock' (U96): rule
        'adx_stock_numbers', derived on a scan model under the balance light."""
        common = dict(reading=settings.apd_reading, encoding=settings.apd_encoding, slope_match=settings.apd_slope_match)
        numbers = None
        if settings.apd_numbers == "stock":
            sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p10_chart_scan"))
            import scan_unbuild  # step P10, U96

            balance = "tungsten" if CATALOG["negatives"][settings.negative].get("exposure_kelvin", 5500) < 4500 else "daylight"
            balance_model = ScanPreview(film_options(replace(negative_only, scene_light=balance), SCAN_CARRIER_PRINT), output=settings.apd_output, lad_aim=True, timing=1.0, **common)
            numbers = scan_unbuild.derive(fp, balance_model)
        untimed = not settings.apd_lad_aim and settings.apd_untimed == "stock_balance"
        axis = settings.apd_axis if not settings.apd_lad_aim and settings.apd_numbers == "stock" else "numbers"
        return ScanPreview(film_options(negative_only, SCAN_CARRIER_PRINT), output=settings.apd_output, lad_aim=settings.apd_lad_aim or untimed, timing=0.0 if untimed else None,
                           exposure_stops=settings.apd_exposure_stops, drt_grey=settings.apd_drt_grey, colour=settings.apd_colour, colour_print=scan_colour_print(settings), numbers=numbers, axis=axis, **common)

    def chart_scan_model(self, settings: RenderSettings):
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p10_chart_scan"))
        import chart_scan as cs  # step P10; imported here so that the other methods do not read the chart

        negative_only = replace(settings, **{c.name: getattr(RenderSettings(), c.name) for c in CONTROLS if "chart_scan" not in c.methods})
        return self._model(("chart_scan", settings.negative, settings.scene_light, settings.spectral_prior, control_values(settings, "chart_scan")),
                           lambda: cs.ChartScanPreview(film_options(negative_only, SCAN_CARRIER_PRINT), cs.cached_chart(),
                                                       **{**cs.SELECTED_FORM, **chart_scan_reading(settings)}, scan_timing=settings.chart_scan_timing, exposure_stops=settings.chart_scan_exposure_stops,
                                                       base_black=settings.chart_scan_black, matrix_domain=settings.chart_scan_matrix,
                                                       display_transform=settings.chart_scan_display))

    def light_table_model(self, settings: RenderSettings) -> rf.ReversalPreview:
        return self._model(("light_table", settings.reversal, settings.scene_light, settings.spectral_prior, control_values(settings, "light_table")), lambda: rf.ReversalPreview(light_table_options(settings)))

    def colorimetry(self, settings: RenderSettings):
        if settings.method == "light_table":
            return self.light_table_model(settings).c
        if settings.method == "chart_scan":
            return self.chart_scan_model(settings).negative.c
        return self.print_model(settings).c if settings.method == "print" else self.scan_model(settings).negative.c

    def render_array(self, ap1: np.ndarray, settings: RenderSettings) -> np.ndarray:
        """Linear AP1 of the RAW file to sRGB display code. Non-finite output stops with an error."""
        settings.validate()
        graded = np.ascontiguousarray(fp.fk.product_grade(np.ascontiguousarray(ap1, dtype=np.float32), float(settings.exposure_ev), float(settings.contrast), float(settings.saturation)), dtype=np.float32)
        if settings.method == "print":
            image = np.asarray(self.print_model(settings).render(graded)[0], dtype=np.float32)
        elif settings.method == "light_table":
            image = np.asarray(self.light_table_model(settings).render(graded)[0], dtype=np.float32)
        elif settings.method == "chart_scan":
            image = np.asarray(self.chart_scan_model(settings).render(graded)[0], dtype=np.float32)
        else:
            image = np.asarray(self.scan_model(settings).render(graded)[0], dtype=np.float32)
        if not np.isfinite(image).all():
            raise FloatingPointError(f"non-finite output: {settings}")
        return image

    def render_file(self, path: Path, settings: RenderSettings, long_edge: int = DEFAULT_LONG_EDGE) -> tuple[np.ndarray, dict]:
        settings = resolve_as_shot(settings, path)
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
