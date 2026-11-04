"""Scanned-negative path of step P3: negative Status M, APD, ADX10, ACES, ACES output transform.

Input: a FilmPreview of step P2 (the negative), the APD tables of SMPTE ST 2065-2 (read at run time from
build/tmp/p3/sources/, see fetch_sources.py), OpenColorIO for the output transforms.
Output: library used by check_scan_path.py and render_scan_review.py.
Step: P3, ROADMAP section 8, decision U23. Inside this path only, the ACES output transform is the display rendering.

Stages:
1. Scanner: rule 'ideal_apd_scanner'. Equation 1 of ST 2065-2 on the spectral density of the negative, at the 2 nm nodes of the
   standard. This stands for the standard, not for a machine. The negative has three free dye amounts per pixel, so the
   scan is a table over negative Status M (same nodes as the print table). The negative density outside 400-700 nm
   comes from the Gaussian tails of P0; the red responsivity peaks at 692 nm, so the check reports its share above 700 nm.
2. Encoding: equation 2 of ST 2065-3, on the APD of the negative base as the measured D-min. The rounding of the equation is not
   applied, because a float pipeline carries the value. The clip to 0-1023 is applied and counted.
3. Rule 'adx_lad_aim' (option lad_aim, timing): one offset per channel in code values, for the scanner lights or a first
   grade. The 18 % grey of the balance light of the stock lands on code value 445, the mid grey that the
   ADX to ACES transform assumes (7120 in ADX16). The share `timing` of the remaining cast of the scene light is removed too, as
   option print_timing does for the print. Without this offset a stock keeps its own grey position. Option exposure_stops adds one
   neutral scanner light: above density 0.6 of the transform, ADX10_PER_STOP code values double ACES.
4. ADX10 to ACES2065-1: port of ACEScsc.Academy.ADX10_to_ACES (aces-dev v1.3.1, A.M.P.A.S. license, THIRD_PARTY_NOTICES.md).
   This transform has no stock parameter.
5. Output: OpenColorIO built-in transforms, ACES2065-1 to XYZ D65, then sRGB encoding. 'aces13' is the
   SDR-VIDEO transform of ACES 1.x, 'aces20' the 100 nit Rec. 709 transform of ACES 2.0. Step P10, U92: 'agx' and 'opendrt' are the
   transforms of p10_chart_scan/display_transforms.py on ACES2065-1 converted to AP1, with the exposure that shows ACES 0.18 at the code of
   'aces20'. Option reading (U92): 'apd' (ST 2065-2) or 'print2383', the printing density of the print material of the options (Kodak 2383
   in the viewer: the printer lamp times the published spectral sensitivity of the paper), which stands for APD and can ship. Option
   drt_grey (U92, with 'agx' and 'opendrt'): 'aces20' moves the exposure as above; 'native' gives ACES 0.18 to the transform as 0.18.
Option encoding (U93): 'adx10' (code values 0-1023, the clip near +7 stops above the grey) or 'adx16' (ST 2065-3 ADX16: 8000 code values per
density, D-min at 1520, the LAD aim at 7120, clip 0-65535, so no clip in the range of a negative). The transform to ACES is the same on cdd =
(code - D-min code) / code values per density, as ACEScsc.Academy.ADX16_to_ACES of aces-dev.
Rule 'adx_slope_match' (option slope_match, U93): the scale 1.00, 0.92, 0.95 of equation 2 suits a motion picture negative, whose channels
then rise by about the same code values per stop. A negative for colour paper read in printing density has a steeper red and blue (Portra 400:
95, 79, 89 ADX10 per stop at the grey under daylight), so the scan turns red above the grey and cyan below. The rule gives the red and the blue
the slope of green at the grey: s_c = 0.92 * slope_G / slope_c, where slope is the printing density per stop of the 18 % grey of the scene light
(central difference at 2^-1 and 2^+1 of 0.18). The pivot is that grey (density D_g): code = code(D_g with the scale of equation 2) +
s * (D - D_g) * code values per density. So the grey keeps the code of equation 2 (the LAD aim off keeps its cast), and only the slope changes.
Option colour (U95): 'academy' (the transform alone) or a target of rule 'scan_print_colour' (p10_chart_scan/scan_colour.py), a correction of hue
and chroma at fixed luminance after the transform; option colour_print gives the options of the print of that rule.
Option numbers (U96): the two matrices of the ADX to ACES transform, (CDD_TO_CID, EXP_TO_ACES); None keeps the Academy numbers. Rule
'adx_stock_numbers' (p10_chart_scan/scan_unbuild.py) derives them per stock. The curve of the transform does not change.
Option axis (U97): 'academy' is rule 'untimed_axis_academy' (p10_chart_scan/scan_axis.py): the neutral axis of the scan at its offset through the
Academy numbers, the colours about it through the numbers of option numbers at the offset of the LAD aim at the scene light.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import PyOpenColorIO as ocio
from scipy.ndimage import map_coordinates

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "p2_negative_print"))
import film_preview as fp  # noqa: E402

APD_TABLE = SCRIPT_DIR.parents[2] / "build" / "tmp" / "p3" / "sources" / "st2065-2" / "st2065-2a-2020.csv"
ADX10_SCALE = np.array([1.00, 0.92, 0.95])
# Option axis (U97): 'numbers', the neutral axis of the numbers of the scan; 'academy', rule 'untimed_axis_academy' of p10_chart_scan/scan_axis.py.
AXES = ("numbers", "academy")
ADX10_PER_DENSITY = 500.0
ADX10_DMIN = 95.0
ADX10_LAD = 445.0
ADX10_PER_STOP = float(np.log10(2.0)) * 0.55 * ADX10_PER_DENSITY  # the transform has a slope of 100 / 55
# U93: (code values per density, code of D-min, LAD aim, largest code)
ENCODINGS = {"adx10": (ADX10_PER_DENSITY, ADX10_DMIN, ADX10_LAD, 1023.0), "adx16": (8000.0, 1520.0, 7120.0, 65535.0)}
OUTPUT_TRANSFORMS = {"aces13": "ACES-OUTPUT - ACES2065-1_to_CIE-XYZ-D65 - SDR-VIDEO_1.0",
                     "aces20": "ACES-OUTPUT - ACES2065-1_to_CIE-XYZ-D65 - SDR-100nit-REC709_2.0"}
DISPLAY_TRANSFORM = "DISPLAY - CIE-XYZ-D65_to_sRGB"
DRT_OUTPUTS = ("agx", "opendrt")  # U92
DRT_GREYS = ("aces20", "native")  # U92
READINGS = ("apd", "print2383")  # U92
AP0_TO_AP1 = np.array([[1.4514393161, -0.2365107469, -0.2149285693], [-0.0765537734, 1.1762296998, -0.0996759264], [0.0083161484, -0.0060324498, 0.9977163014]])

# Constants of ACEScsc.Academy.ADX10_to_ACES.ctl, aces-dev v1.3.1. The CTL multiplies row vectors.
CDD_TO_CID = np.array([[0.75573, 0.05901, 0.16134], [0.22197, 0.96928, 0.07406], [0.02230, -0.02829, 0.76460]])
EXP_TO_ACES = np.array([[0.72286, 0.11923, 0.01427], [0.12630, 0.76418, 0.08213], [0.15084, 0.11659, 0.90359]])
LUT_CID = np.array([-0.19, 0.01, 0.028, 0.054, 0.095, 0.145, 0.22, 0.3, 0.4, 0.5, 0.6])
LUT_LOG_E = np.array([-6.0, -2.721718645, -2.521718645, -2.321718645, -2.121718645, -1.921718645, -1.721718645, -1.521718645,
                      -1.321718645, -1.121718645, -0.926545676714876])
REF_PT = (7120.0 - 1520.0) / 8000.0 * (100.0 / 55.0) - np.log10(0.18)


def read_apd_responsivities() -> tuple[np.ndarray, np.ndarray]:
    """Wavelengths (nm) and responsivities (3, nodes; R, G, B) of the element st2065-2a-2020.csv."""
    rows = [line.strip().split(",") for line in APD_TABLE.read_text(encoding="utf-8-sig").splitlines() if line[:1].isdigit()]
    table = np.array(rows, dtype=np.float64)
    if table.shape != (186, 4) or not np.all(np.diff(table[:, 0]) == 2.0):
        raise ValueError(f"{APD_TABLE}: unexpected table of shape {table.shape}")
    return table[:, 0], table[:, 1:].T


def adx10_from_apd(apd: np.ndarray, apd_dmin: np.ndarray) -> np.ndarray:
    """Equation 2 of ST 2065-3, without the rounding and the clip."""
    return ADX10_SCALE * (apd - apd_dmin) * ADX10_PER_DENSITY + ADX10_DMIN


def adx10_to_aces(adx10: np.ndarray) -> np.ndarray:
    """Port of the ADX10 to ACES transform; the input is in code values (0-1023)."""
    return cdd_to_aces((np.asarray(adx10, dtype=np.float64) - ADX10_DMIN) / ADX10_PER_DENSITY)


def cdd_to_exposure(cdd: np.ndarray, cdd_to_cid: np.ndarray = CDD_TO_CID) -> np.ndarray:
    """The ADX10 and ADX16 to ACES transforms after the step to cdd, up to the exposure (aces-dev v1.3.1)."""
    cid = np.asarray(cdd, dtype=np.float64) @ cdd_to_cid
    return 10.0 ** np.where(cid <= 0.6, np.interp(cid, LUT_CID, LUT_LOG_E), (100.0 / 55.0) * cid - REF_PT)


def cdd_to_aces(cdd: np.ndarray, cdd_to_cid: np.ndarray = CDD_TO_CID, exp_to_aces: np.ndarray = EXP_TO_ACES) -> np.ndarray:
    """The ADX10 and ADX16 to ACES transforms after the step to cdd (aces-dev v1.3.1), with the Academy numbers or others (option numbers)."""
    return cdd_to_exposure(cdd, cdd_to_cid) @ exp_to_aces


def builtin_processor(*styles: str):
    group = ocio.GroupTransform()
    for style in styles:
        group.appendTransform(ocio.BuiltinTransform(style))
    return ocio.Config.CreateRaw().getProcessor(group).getDefaultCPUProcessor()


def apply_processor(cpu, rgb: np.ndarray) -> np.ndarray:
    out = np.array(rgb, dtype=np.float32, order="C")
    cpu.applyRGB(out)
    return out


def stops_to_display_luminance(output: str, luminance: float) -> float:
    """Stops from ACES 0.18 to the neutral that the output transform shows at this share of its peak."""
    aces = 0.18 * 2.0 ** np.linspace(-2.0, 5.0, 1401)
    shown = apply_processor(builtin_processor(OUTPUT_TRANSFORMS[output]), np.outer(aces, np.ones(3)))[:, 1]
    return float(np.interp(luminance, shown, np.log2(aces / 0.18)))


class ScanPreview:
    """The negative of a FilmPreview through the ideal scanner. The print-only steps of the options are not used,
    and the enlarger flare is off, because the scan has no enlarger."""

    def __init__(self, options: fp.FilmOptions, output: str = "aces20", timing: float | None = None, lad_aim: bool = True, exposure_stops: float = 0.0,
                 scanner: tuple[str, np.ndarray, np.ndarray] | None = None, reading: str = "apd", drt_grey: str = "aces20", encoding: str = "adx10",
                 slope_match: bool = False, colour: str = "academy", colour_print: fp.FilmOptions | None = None, numbers: tuple[np.ndarray, np.ndarray] | None = None,
                 axis: str = "numbers") -> None:
        if encoding not in ENCODINGS:
            raise ValueError(f"unknown encoding {encoding!r}")
        self.encoding = encoding
        self.per_density, self.code_dmin, self.code_lad, self.code_max = ENCODINGS[encoding]
        self.scale = ADX10_SCALE.copy()
        self.pivot = None
        self.cdd_to_cid, self.exp_to_aces = (CDD_TO_CID, EXP_TO_ACES) if numbers is None else numbers
        if drt_grey not in DRT_GREYS:
            raise ValueError(f"unknown DRT grey {drt_grey!r}")
        self.drt_grey = drt_grey
        self.negative = fp.FilmPreview(replace(options, enlarger_flare=0.0))
        if reading not in READINGS:
            raise ValueError(f"unknown reading {reading!r}")
        if reading == "print2383":
            if scanner is not None:
                raise ValueError("reading 'print2383' and a scanner exclude each other")
            film = self.negative.film
            scanner = ("print_density", film.grid.wavelengths, np.asarray(film.w_printing, dtype=np.float64))
        self.output_name = output
        self.timing = options.print_timing if timing is None else timing
        self.lad_aim = lad_aim
        self.exposure_stops = exposure_stops
        film = self.negative.film
        # scanner: (name, wavelengths, responsivities (3, nodes)) in place of APD. Equation 1 of ST 2065-2 stays the form of the reading.
        self.scanner_name, wavelengths, responsivities = scanner or ("apd", *read_apd_responsivities())
        self.apd_nodes = np.searchsorted(film.grid.wavelengths, wavelengths)
        if not np.array_equal(film.grid.wavelengths[self.apd_nodes], wavelengths):
            raise ValueError("the wavelengths of the APD table are not nodes of the model grid")
        self.apd_weights = responsivities
        self.apd_dmin = self.apd(film.negative_dmin[None])[0]
        self.table = self._build_table()
        if slope_match:
            self.scale, self.pivot = self.slope_match(self.negative.options.scene_light)
        self.offset = self._adx_offset()
        if axis not in AXES:
            raise ValueError(f"unknown axis {axis!r}")
        self.axis = None
        if axis == "academy":
            sys.path.insert(0, str(SCRIPT_DIR.parent / "p10_chart_scan"))
            import scan_axis  # step P10, U97

            self.axis = scan_axis.UntimedAxis(self, CDD_TO_CID, EXP_TO_ACES)
        self.colour = None
        if colour != "academy":
            sys.path.insert(0, str(SCRIPT_DIR.parent / "p10_chart_scan"))
            import scan_colour  # step P10, U95

            if colour_print is None:
                raise ValueError(f"scan colour {colour!r} needs the options of the print (colour_print)")
            self.colour = scan_colour.ScanColour(fp, self, fp.FilmPreview(colour_print), colour)
        if output in DRT_OUTPUTS:
            self.output_cpu = None
            self.grey_code = float(apply_processor(builtin_processor(OUTPUT_TRANSFORMS["aces20"], DISPLAY_TRANSFORM), np.full((1, 3), 0.18))[0, 1])
        elif output in OUTPUT_TRANSFORMS:
            self.output_cpu = builtin_processor(OUTPUT_TRANSFORMS[output], DISPLAY_TRANSFORM)
        else:
            raise ValueError(f"unknown output {output!r}")

    def apd(self, spectral_density: np.ndarray) -> np.ndarray:
        """Equation 1 of ST 2065-2."""
        transmission = 10.0 ** -spectral_density[..., self.apd_nodes]
        return -np.log10((transmission @ self.apd_weights.T) / self.apd_weights.sum(axis=1))

    def direct_apd(self, status_m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Negative Status M (N, 3) to APD through the stages; the second array is the residual of the dye solve."""
        film = self.negative.film
        base = film.status_density(film.negative_dmin, film.w_status_m)
        amounts, residual = fp.solve_amounts(self.negative.record_to_status_m(status_m) - film.negative_curve_dmin + base, film.negative_dmin, film.negative_dyes, film.w_status_m)
        return self.apd(film.negative_spectral_density(amounts)), residual

    def _build_table(self) -> np.ndarray:
        # Equation 1 of ST 2065-2 on the nodes, in the C++ library of step P7. The table is not stored (ROADMAP U68).
        film = self.negative.film
        nodes = np.stack(np.meshgrid(*self.negative.density_grid, indexing="ij"), axis=-1)
        amounts, _ = self.negative.table_amounts(nodes.reshape(-1, 3))
        response = fp.film_tables.log10_band_response(film.negative_dmin[self.apd_nodes], film.negative_dyes[:, self.apd_nodes], self.apd_weights, amounts)
        return (np.log10(self.apd_weights.sum(axis=1)) - response).reshape(nodes.shape)

    def table_apd(self, status_m: np.ndarray) -> np.ndarray:
        grid = self.negative.density_grid
        coordinates = np.stack([(status_m[..., k] - grid[k][0]) / (grid[k][1] - grid[k][0]) for k in range(3)])
        return np.stack([map_coordinates(self.table[..., k], coordinates, order=1, mode="nearest") for k in range(3)], axis=-1)

    def grey_apd(self, light: str, scene_value: float = 0.18) -> np.ndarray:
        """APD of a neutral under a light, through the curves of the negative."""
        n = self.negative
        q = n.layer_gain * n.c.layer_exposure(scene_value * n.light(light))
        return self.table_apd(n.negative_density(q[None])[0])[0]

    def slope_match(self, light: str) -> tuple[np.ndarray, np.ndarray]:
        """Rule 'adx_slope_match': the channel scale and the pivot (printing density of the 18 % grey) under a light."""
        slope = (self.grey_apd(light, 0.36) - self.grey_apd(light, 0.09)) / 2.0
        return ADX10_SCALE[1] * slope[1] / slope, self.grey_apd(light)

    def code(self, apd: np.ndarray) -> np.ndarray:
        """Code values of the encoding without the offset: equation 2 of ST 2065-3, or rule 'adx_slope_match'."""
        if self.pivot is None:
            return ADX10_SCALE * (apd - self.apd_dmin) * self.per_density + self.code_dmin
        return ADX10_SCALE * (self.pivot - self.apd_dmin) * self.per_density + self.code_dmin + self.scale * (apd - self.pivot) * self.per_density

    def grey_adx(self, light: str) -> np.ndarray:
        """Code values without the offset, of an 18 % grey under a light."""
        return self.code(self.grey_apd(light))

    def _adx_offset(self) -> np.ndarray:
        per_stop = ADX10_PER_STOP * self.per_density / ADX10_PER_DENSITY
        if not self.lad_aim:
            return np.full(3, self.exposure_stops * per_stop)
        o = self.negative.options
        balance = self.code_lad - self.grey_adx(o.balance_light)
        return balance + self.timing * (self.code_lad - self.grey_adx(o.scene_light) - balance) + self.exposure_stops * per_stop

    def adx10(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        """Code values of the encoding (ADX10 or ADX16, option encoding) with the offset, clipped."""
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        status_m, stats = self.negative.negative_image(image[None] if image.ndim == 2 else image)
        code = self.code(self.table_apd(status_m)) + self.offset
        stats = {**stats, "code_below_0": int((code < 0).any(axis=-1).sum()), "code_above_max": int((code > self.code_max).any(axis=-1).sum())}
        return np.clip(code, 0.0, self.code_max), stats

    def exposure_of(self, code: np.ndarray, cdd_to_cid: np.ndarray | None = None) -> np.ndarray:
        """The exposure of the transform (before EXP_TO_ACES)."""
        return cdd_to_exposure((np.asarray(code, dtype=np.float64) - self.code_dmin) / self.per_density, self.cdd_to_cid if cdd_to_cid is None else cdd_to_cid)

    def to_aces(self, code: np.ndarray) -> np.ndarray:
        """The ADX10 or ADX16 to ACES2065-1 transform, with the numbers of option numbers."""
        return self.exposure_of(code) @ self.exp_to_aces

    def scene_aces(self, code: np.ndarray) -> np.ndarray:
        """ACES2065-1 of the scan: the transform, then rule 'scan_print_colour' when option colour selects it."""
        aces = self.to_aces(code) if self.axis is None else self.axis.apply(code)
        return aces if self.colour is None else self.colour.apply(aces)

    def render(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        """Linear AP1 to sRGB through the scan and the ACES output transform."""
        code, stats = self.adx10(ap1)
        if self.output_cpu is None:
            sys.path.insert(0, str(SCRIPT_DIR.parent / "p10_chart_scan"))
            import display_transforms as dt  # step P10, U92

            ap1_scene = self.scene_aces(code) @ AP0_TO_AP1.T
            if self.drt_grey == "native":
                display = dt.render_native(self.output_name, ap1_scene, fp.srgb_encode)
            else:
                display = dt.render_at(self.output_name, ap1_scene, self.grey_code, fp.srgb_encode)
        else:
            display = apply_processor(self.output_cpu, self.scene_aces(code))
        if not np.isfinite(display).all():
            raise RuntimeError("the output transform returned values that are not finite")
        stats["display_outside_0_1"] = int(((display < 0) | (display > 1)).any(axis=-1).sum())
        return np.clip(display, 0.0, 1.0), stats


class DirectInversionPreview(ScanPreview):
    """Rule 'direct_inversion': a negative scanned and inverted per channel, with no ADX to ACES transform, no print, and no matrix.

    This stands for the common practice of today: a developed negative, a scan, and a positive made per channel. It is a model of
    that kind of process, not of a named program, and it is a review path. For each APD record:
    - the grey position is the grey of the balance light, with the share `timing` of the scene light cast removed;
    - the slope is the slope of the record on a neutral ramp of the balance light (1 log10 on each side of the grey), so that a neutral stays
      neutral in the straight part;
    - the exposure estimate goes through one curve per channel, y = E^n / (E^n + 1 / t - 1), which shows E = 1 at the display value t and has
      the limit 1. The record is shown as the same channel of the display (linear Rec. 709), with no matrix.
    The values of t (display grey) and n (contrast) are review controls.

    Rule 'density_crosstalk' (option crosstalk, a review control): each record moves away from the other records, with the record difference in log10 exposure through a soft limit,
        L_i' = L_i + sum_j k_ij s(L_i - L_j), s(x) = x / sqrt(1 + (x / crosstalk_limit)^2).
    A neutral has equal records at the grey, so it does not change there; away from the grey the records of a neutral differ a little, and the display changes by 0.0025 at most on the ramp of 5207 (k = 0.25). The move has the size k * crosstalk_limit at most, so a saturated colour cannot drive a channel to black, and the function is smooth.
    Rule 'soft_scan' (review controls): log_contrast scales the log exposure around the grey, and record_saturation scales the distance of each record from the mean of the records. Both take back the
    default grade of the product, as print_contrast does in the print. black and white set the display range of the curve.
    Rule 'density_timing' (step P4, option per_record_slope = False): one slope for all records, the mean of the three, and one offset per channel. A lab balances a frame in this way, so a neutral away from the balance point keeps the crossover of the stock.
    Rule 'frame_balance_image' (step P4, option frame_balance = 'image'): the offset per channel moves by the median of the record in the frame, about the mean of the three medians, as an automatic scanner does. 'fixed': the offset of the grey under the light.
    k is (3, 3); the diagonal is not used. This is an algorithm with values chosen by eye. It is not a measurement of a scanner and not a fit to chart scans."""

    def __init__(self, options: fp.FilmOptions, display_grey: float = 0.22, contrast: float = 1.6, timing: float | None = None,
                 scanner: tuple[str, np.ndarray, np.ndarray] | None = None, tone=None, crosstalk: np.ndarray | None = None, crosstalk_limit: float = 0.5,
                 log_contrast: float = 1.0, record_saturation: float = 1.0, black: float = 0.0, white: float = 1.0, per_record_slope: bool = True, frame_balance: str = "fixed") -> None:
        super().__init__(options, timing=timing, scanner=scanner)
        if frame_balance not in ("fixed", "image"):
            raise ValueError(f"unknown frame balance {frame_balance!r}")
        self.frame_balance = frame_balance
        self.log_contrast, self.record_saturation, self.black, self.white = log_contrast, record_saturation, black, white
        self.crosstalk = crosstalk
        self.crosstalk_limit = crosstalk_limit
        self.tone = tone  # function from log10 exposure per channel to sRGB code values, in place of the curve below
        self.display_grey = display_grey
        self.contrast = contrast
        o = self.negative.options
        scene_values = 0.18 * 10.0 ** np.linspace(-1.0, 1.0, 21)
        ramp = np.stack([self.grey_apd(o.balance_light, float(v)) for v in scene_values])
        self.gamma = np.array([np.polyfit(np.log10(scene_values), ramp[:, k], 1)[0] for k in range(3)])
        self.record_slope = self.gamma if per_record_slope else np.full(3, self.gamma.mean())
        balance = self.grey_apd(o.balance_light)
        self.grey_position = balance + self.timing * (self.grey_apd(o.scene_light) - balance)
        # A neutral of the image goes through the reconstruction, and its layer exposures differ a little from a flat reflectance. The position uses the neutral of the image.
        neutral = self.negative.negative_image(np.full((1, 1, 3), 0.18, dtype=np.float32))[0]
        self.grey_position = self.grey_position + self.table_apd(neutral)[0, 0] - self.grey_apd(o.scene_light)

    def render(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        """Linear AP1 to sRGB through the negative and the per-channel inversion. The curve keeps the values inside the display range."""
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        status_m, stats = self.negative.negative_image(image[None] if image.ndim == 2 else image)
        records = (self.table_apd(status_m) - self.grey_position) / self.record_slope
        if self.frame_balance == "image" and min(image.shape[:2]) >= 16:
            medians = np.median(records.reshape(-1, 3), axis=0)
            records = records - (medians - medians.mean())
        log_exposure = self.finish_records(records)
        if self.tone is not None:
            display = self.tone(log_exposure)
            return (display[0] if image.ndim == 2 else display), stats
        display = self.display_from_records(log_exposure)
        return (display[0] if image.ndim == 2 else display), stats

    def finish_records(self, log_exposure: np.ndarray) -> np.ndarray:
        log_exposure = log_exposure * self.log_contrast
        mean = log_exposure.mean(axis=-1, keepdims=True)
        log_exposure = mean + self.record_saturation * (log_exposure - mean)
        if self.crosstalk is not None:
            difference = log_exposure[..., :, None] - log_exposure[..., None, :]
            log_exposure = log_exposure + (self.crosstalk * difference / np.sqrt(1.0 + (difference / self.crosstalk_limit) ** 2)).sum(axis=-1)
        return log_exposure

    def display_from_records(self, log_exposure: np.ndarray) -> np.ndarray:
        powered = (10.0 ** log_exposure) ** self.contrast
        y = powered / (powered + 1.0 / self.display_grey - 1.0)
        return fp.srgb_encode(self.black + (self.white - self.black) * y)
