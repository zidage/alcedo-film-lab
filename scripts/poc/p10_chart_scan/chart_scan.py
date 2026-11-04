"""Chart-calibrated scan of step P10 (ROADMAP U87): the negative of a stock, an ideal APD scanner, and an inversion that a chart on the same stock calibrates.

Input: a FilmPreview of step P2 (the negative), the APD scanner of step P3 (aces_scan.ScanPreview), the BabelColor Avg ColorChecker spectra (build/tmp/p10/sources/, fetch_sources.py).
Output: library used by run_chart_scan.py and render_chart_scan_review.py.

This stands for a laboratory practice: a lab photographs a chart and a grey scale on the stock under the light of the stock, develops and scans the
negative, and fits the inversion of the scanner software to the known values of the chart. Here the chart is photographed, developed, and scanned
by the model. The inversion comes from the data of the stock and from the chart, not from statistics of a frame, so one inversion serves all frames.

Rules:
- 'chart_calibration_light': the chart and the grey scale are lit by the balance light of the stock (options.balance_light). A scene under another
  light keeps its cast (ROADMAP U36).
- 'chart_grey_scale': a spectrally flat grey, 0.18 * 2^s for s from RAMP_STOPS[0] to RAMP_STOPS[1] in steps of RAMP_STEP, as flat areas (the point
  form of the inhibition). Per APD channel, the record against s is the calibration curve. Only the part where the record rises by at least
  RAMP_MIN_RISE per step is kept, so the inverse exists. A record outside the kept part takes the nearest end, and the count is reported.
- 'chart_equivalent_exposure': per channel, e_k = 0.18 * 2^(s_k), with s_k the inverse of the curve of channel k at its record. A flat grey of
  any level returns (e, e, e).
- 'chart_straight_line' (option inversion = 'straight'): per channel, only the slope of the grey scale in STRAIGHT_WINDOW and the record of the
  grey: e_k = 0.18 * 2^((record_k - record_grey_k) / slope_k). This undoes the gamma and the offset of each layer, as a scanner program that
  balances a grey does, and keeps the toe and the shoulder of the negative, so a grey outside the window can leave the neutral axis (crossover).
- 'chart_matrix' (option matrix): a 3 x 3 matrix M from e to linear AP1, fitted by least squares on the 24 patches, with the constraint M (1, 1, 1) =
  (1, 1, 1), so that a flat grey stays a flat grey. The target of a patch: its XYZ under the calibration light, adapted by Bradford from the
  white of that light to the white of AP1. With matrix = False, M is the identity: the per-channel inversion alone.
- 'chart_scan_display' (ROADMAP U87, the user asks for no ACES output transform): linear AP1 to linear Rec. 709 (Bradford from the AP1 white
  to D65), a clip to 0-1, and the sRGB encoding. No tone curve: a value above 1 clips, and the count is reported.
- 'scan_channel_curve' (option output = 'channel_curve', round 3): no matrix to Rec. 709; each channel of e is shown as the same display channel,
  as a scanner program shows its scanner RGB, through the curve of P3 rule 'direct_inversion' in linear display light,
  y = E^n / (E^n + 1/t - 1) with E = e / 0.18, and the sRGB encoding. Values of P3: t = 0.22, n = 1.6 (set there before any comparison).
- 'scan_log_curve' (option output = 'log_curve', round 3): the same channel mapping, with a logistic in stops on the display code,
  code = 1 / (1 + exp(-(s - s0) / w)), s = log2(e / 0.18). It is a flat, density-linear positive, as a scan inverted in log space. Values set
  before any comparison: the grey shows code 0.4614 (sRGB of 0.18) with the slope of the sRGB code of a digital grey at that point, so a
  digital image and this curve agree at the grey.
Round 4 (colour of the log curve). Options that change the record before the grey scale; each is fixed before a comparison, and all cost no
time at run time (a table built once, or one 3 x 3 product):
- 'scan_light' (option scanner): 'apd' (ST 2065-2), 'frontier' (P3 rule 'frontier_sp3000_light_estimate': three narrow bands 632, 540,
  465 nm read from a public spectrum picture of the SP3000), 'status_m' (the Status M weights of the model, ISO 5-3, the densitometry for
  colour negatives), or 'analytical' (the dye amounts of the record, the limit of a scanner with no
  overlap between its channels).
- 'scan_unmix' (option unmix): the channel-dependent densities above the base go through CDD_TO_CID of the ACES ADX10 to ACES transform
  (aces-dev v1.3.1), with the ADX10 channel scale: the standard step that removes the crosstalk of the dyes from a printing-density scan.
- 'scan_common_slope' (option common_slope): one slope for the three channels, the mean of the three, with the offset per channel at the
  grey (P4 rule 'density_timing'): a lab balances a grey but does not equalize the gammas of the layers, so a stock keeps its crossover.
- 'film_sensitivity_matrix' (option sensitivity_matrix): a 3 x 3 matrix, white kept, fitted by least squares on the chart from the layer
  exposures of the stock alone (its published spectral sensitivities, under the calibration light, each layer divided by its value at the
  grey) to the AP1 of the patches. It is the profile of the film as a camera: it gives the channels of the inversion their primaries, and it
  sees nothing of the development (inhibition, dye curves, dyes), so the colour that the development makes stays. With a curve output, the
  matrix goes to linear Rec. 709, and the curve acts on the Rec. 709 channels.
- 'scan_timing' (option scan_timing, inversion 'straight'): the record of the grey moves by the share scan_timing toward the record of an
  18 % grey under the scene light of the options, as the share print_timing does for the printer lights of the print (P3 rule 'adx_lad_aim').
  The scene light is a setting, not a statistic of the frame. 0: the grey of the calibration light only, and the cast of the scene stays.
- 'rgc_style_display_compression' of P2 (option display_compress, with sensitivity_matrix and a curve output): the curve of the ACES
  Reference Gamut Compression on the linear Rec. 709 channels before the curve, with the gamut_threshold, gamut_limit, and gamut_power of the
  options, as the print display does. It is not the standard ACES RGC (another domain). It brings back a channel that the sensitivity matrix
  takes below 0 on a saturated light (a blue-violet lamp: red 0 and a hard blue without it).
- 'scan_exposure' (option exposure_stops): one neutral scale 2^stops of the scene values before the display steps, as a scanner light or a
  brightness setting of a scan program. 0: no change.
SELECTED_FORM (round 5, ROADMAP U88) is the form that the Python viewer runs as method 'chart_scan'.
The inhibition and the other image-plane steps of the negative act on images, as in the print path; the chart and the grey scale are flat areas.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
for step in ("p1_spectral_input", "p2_negative_print", "p3_scan_and_scene", "p6_mvp_gui"):
    sys.path.insert(0, str(SCRIPT_DIR.parent / step))
import aces_scan as acs  # noqa: E402
import film_preview as fp  # noqa: E402
import spectral_datasets as sd  # noqa: E402

CHART_WORKBOOK = REPO_ROOT / "build" / "tmp" / "p10" / "sources" / "bc" / "ColorChecker_RGB_and_spectra.xls"
RAMP_STOPS = (-10.0, 10.0)
RAMP_STEP = 1.0 / 32.0
RAMP_MIN_RISE = 1e-5
STRAIGHT_WINDOW = (-2.0, 2.0)  # rule 'chart_straight_line': stops of the grey scale for the slope
INVERSIONS = ("curves", "straight")
OUTPUTS = ("clip709", "channel_curve", "log_curve")
SCANNERS = ("apd", "frontier", "status_m", "analytical")
# The selected form of report sections 8 and 10 (scan_timing comes from the option print_timing of the viewer). Status M in place of APD
# (section 10): the same result, and its table (python-colormath, BSD-3-Clause) can ship with the product; the SMPTE table cannot.
SELECTED_FORM = dict(matrix=False, inversion="straight", output="log_curve", scanner="status_m", sensitivity_matrix=True, display_compress=True)
_CHART: "Chart | None" = None
FRONTIER_BANDS = ((632.0, 16.0), (540.0, 34.0), (465.0, 16.0))  # P3 rule 'frontier_sp3000_light_estimate'
CHANNEL_CURVE_T, CHANNEL_CURVE_N = 0.22, 1.6  # P3 rule 'direct_inversion'
GREY = 0.18


@dataclass
class Chart:
    name: str
    labels: list[str]
    reflectance: np.ndarray  # (patches, len(sd.GRID_NM))


def cached_chart() -> Chart:
    """The BabelColor chart, read once per process."""
    global _CHART
    if _CHART is None:
        _CHART = babelcolor_chart()
    return _CHART


def babelcolor_chart() -> Chart:
    """Sheet 'spectral_data' of the BabelColor workbook: 24 rows, 380-730 nm in 10 nm steps. Rules 'reflectance_resampling' and
    'reflectance_outside_measured_range' of P1 put the values on the 1 nm grid (hold outside 380-730 nm)."""
    import xlrd

    sheet = xlrd.open_workbook(str(CHART_WORKBOOK)).sheet_by_name("spectral_data")
    header = sheet.row_values(1)
    if header[0] != "No." or float(header[2]) != 380.0:
        raise ValueError(f"{CHART_WORKBOOK}: unexpected header {header[:4]}")
    columns = [k for k, v in enumerate(header) if isinstance(v, float)]
    wavelengths = np.array([header[k] for k in columns])
    if not (wavelengths[0] == 380.0 and wavelengths[-1] == 730.0 and np.all(np.diff(wavelengths) == 10.0)):
        raise ValueError(f"{CHART_WORKBOOK}: unexpected wavelengths {wavelengths[[0, -1]]}")
    labels, spectra = [], []
    for r in range(2, 26):
        row = sheet.row_values(r)
        if int(row[0]) != r - 1:
            raise ValueError(f"{CHART_WORKBOOK}: row {r} holds patch {row[0]}")
        labels.append(str(row[1]))
        spectra.append(sd.resample_hold(wavelengths, np.array([row[k] for k in columns], dtype=np.float64)))
    return Chart("babelcolor_avg", labels, np.array(spectra))


def frontier_responsivity() -> tuple[str, np.ndarray, np.ndarray]:
    """P3 rule 'frontier_sp3000_light_estimate' (render_scanner_light_review.py): 0.7 Gaussian + 0.3 Lorentzian per band, flat sensor."""
    wavelengths = np.arange(400.0, 751.0)
    bands = []
    for peak, width in FRONTIER_BANDS:
        gaussian = np.exp(-0.5 * ((wavelengths - peak) / (width / 2.3548)) ** 2)
        lorentzian = 1.0 / (1.0 + ((wavelengths - peak) / (width / 2.0)) ** 2)
        bands.append(0.7 * gaussian + 0.3 * lorentzian)
    return "frontier_sp3000_estimate", wavelengths, np.stack(bands)


def fit_white_preserving(e: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Rule 'chart_matrix': per output row r, least squares of e r = target_k with sum(r) = 1 (KKT system)."""
    a = np.zeros((4, 4))
    a[:3, :3] = 2.0 * e.T @ e
    a[:3, 3] = a[3, :3] = 1.0
    rows = []
    for k in range(3):
        b = np.concatenate([2.0 * e.T @ target[:, k], [1.0]])
        rows.append(np.linalg.solve(a, b)[:3])
    return np.array(rows)


def lab(xyz: np.ndarray, white: np.ndarray) -> np.ndarray:
    t = xyz / white
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e2000(lab1: np.ndarray, lab2: np.ndarray) -> np.ndarray:
    """CIEDE2000 (Sharma, Wu, Dalal 2005), kL = kC = kH = 1."""
    l1, a1, b1 = np.moveaxis(lab1, -1, 0)
    l2, a2, b2 = np.moveaxis(lab2, -1, 0)
    c_bar = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    g = 0.5 * (1 - np.sqrt(c_bar ** 7 / (c_bar ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dl, dc = l2 - l1, c2p - c1p
    dh = h2p - h1p
    dh = np.where(c1p * c2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dhh = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))
    l_bar, cp_bar = (l1 + l2) / 2, (c1p + c2p) / 2
    hsum = h1p + h2p
    h_bar = np.where(c1p * c2p == 0, hsum, np.where(np.abs(h1p - h2p) <= 180, hsum / 2, np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2)))
    t = 1 - 0.17 * np.cos(np.radians(h_bar - 30)) + 0.24 * np.cos(np.radians(2 * h_bar)) + 0.32 * np.cos(np.radians(3 * h_bar + 6)) - 0.20 * np.cos(np.radians(4 * h_bar - 63))
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / np.sqrt(20 + (l_bar - 50) ** 2)
    sc, sh = 1 + 0.045 * cp_bar, 1 + 0.015 * cp_bar * t
    rt = -2 * np.sqrt(cp_bar ** 7 / (cp_bar ** 7 + 25.0 ** 7)) * np.sin(np.radians(60 * np.exp(-(((h_bar - 275) / 25) ** 2))))
    return np.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dhh / sh) ** 2 + rt * (dc / sc) * (dhh / sh))


class ChartScanPreview(acs.ScanPreview):
    """The negative through the ideal APD scanner, inverted by rule 'chart_calibrated_scan' (see the module text)."""

    def __init__(self, options: fp.FilmOptions, chart: Chart, matrix: bool = True, inversion: str = "curves", output: str = "clip709",
                 scanner: str = "apd", unmix: bool = False, common_slope: bool = False, sensitivity_matrix: bool = False, scan_timing: float = 0.0, display_compress: bool = False, exposure_stops: float = 0.0) -> None:
        if scanner not in SCANNERS:
            raise ValueError(f"unknown scanner {scanner!r}")
        super().__init__(options, lad_aim=False, scanner=frontier_responsivity() if scanner == "frontier" else None)
        self.scanner_kind, self.unmix, self.common_slope = scanner, unmix, common_slope
        if scanner == "status_m":
            film = self.negative.film
            self.scanner_name = "status_m"
            self.apd_nodes = np.arange(len(film.grid.wavelengths))
            self.apd_weights = np.asarray(film.w_status_m, dtype=np.float64)
            self.apd_dmin = self.apd(film.negative_dmin[None])[0]
            self.table = self._build_table()
        if inversion not in INVERSIONS:
            raise ValueError(f"unknown inversion {inversion!r}")
        self.inversion = inversion
        if output not in OUTPUTS:
            raise ValueError(f"unknown output {output!r}")
        self.output = output
        # Rule 'scan_log_curve': grey code g and the slope of the sRGB code of 0.18 * 2^s at s = 0.
        g = float(fp.srgb_encode(np.array([GREY]))[0])
        h = 1e-4
        slope = float((fp.srgb_encode(np.array([GREY * 2.0 ** h])) - fp.srgb_encode(np.array([GREY * 2.0 ** -h])))[0] / (2 * h))
        self.log_w = g * (1.0 - g) / slope
        self.log_s0 = self.log_w * np.log(1.0 / g - 1.0)
        n = self.negative
        c = n.c
        if not np.array_equal(c.wavelengths, sd.GRID_NM):
            raise ValueError("the chart grid is not the grid of the model")
        self.chart = chart
        self.light_name = n.options.balance_light
        self.calibration_light = n.light(self.light_name)
        stops = np.arange(RAMP_STOPS[0], RAMP_STOPS[1] + 0.5 * RAMP_STEP, RAMP_STEP)
        ramp = self.patch_apd(np.outer(GREY * 2.0 ** stops, np.ones(len(c.wavelengths))))
        self.ramp_stops, self.ramp_apd = [], []
        for k in range(3):
            keep = np.concatenate([[True], np.diff(ramp[:, k]) >= RAMP_MIN_RISE])
            run = np.flatnonzero(~keep)
            # The longest rising run that holds the grey (s = 0).
            centre = int(np.argmin(np.abs(stops)))
            lo = int(run[run <= centre].max()) if (run <= centre).any() else 0
            hi = int(run[run > centre].min()) if (run > centre).any() else len(stops)
            self.ramp_stops.append(stops[lo:hi])
            self.ramp_apd.append(ramp[lo:hi, k])
        # Rule 'chart_straight_line': per channel, the slope of the record against stops by least squares in STRAIGHT_WINDOW, and the record of the grey.
        window = (stops >= STRAIGHT_WINDOW[0] - 1e-9) & (stops <= STRAIGHT_WINDOW[1] + 1e-9)
        self.straight_slope = np.array([np.polyfit(stops[window], ramp[window, k], 1)[0] for k in range(3)])
        if common_slope:
            self.straight_slope = np.full(3, self.straight_slope.mean())
        self.straight_grey = ramp[int(np.argmin(np.abs(stops)))]
        if scan_timing:
            scene_grey = self.density(n.negative_density(n.layer_gain * c.layer_exposure(GREY * n.scene_spectrum)[None])[0])[0]
            self.straight_grey = self.straight_grey + scan_timing * (scene_grey - self.straight_grey)
        light_white = c.xyz(self.calibration_light)
        self.ap1_white = c.ap1_to_xyz @ np.ones(3)
        self.to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(light_white, self.ap1_white)
        self.e_chart, _ = self.equivalent_exposure(self.patch_apd(chart.reflectance))
        self.target_chart = self.patch_ap1(chart.reflectance)
        self.matrix = fit_white_preserving(self.e_chart, self.target_chart) if matrix else np.eye(3)
        self.sensitivity_matrix = sensitivity_matrix
        self.display_compress = display_compress
        self.exposure_scale = 2.0 ** exposure_stops
        if sensitivity_matrix:
            if matrix:
                raise ValueError("options matrix and sensitivity_matrix exclude each other")
            q_grey = n.layer_gain * c.layer_exposure(GREY * self.calibration_light)
            x = GREY * (n.layer_gain * c.layer_exposure(chart.reflectance * self.calibration_light)) / q_grey
            self.matrix = fit_white_preserving(x, self.target_chart)
        self.ap1_to_rec709 = fp.XYZ_TO_REC709 @ fp.bradford_matrix(self.ap1_white, fp.XYZ_D65) @ c.ap1_to_xyz

    def patch_apd(self, reflectance: np.ndarray) -> np.ndarray:
        """APD of flat patches (N, nodes) under the calibration light: the point form of the negative."""
        n = self.negative
        q = n.layer_gain * n.c.layer_exposure(reflectance * self.calibration_light)
        record, _ = n.negative_density(q)
        return self.density(record)

    def density(self, record: np.ndarray) -> np.ndarray:
        """Rules 'scan_light' and 'scan_unmix': the record of the negative as the scanner reads it."""
        if self.scanner_kind == "analytical":
            d = np.asarray(record, dtype=np.float64)
        else:
            d = self.table_apd(record)
        if self.unmix:
            d = (acs.ADX10_SCALE * (d - self.apd_dmin)) @ acs.CDD_TO_CID
        return d

    def patch_ap1(self, reflectance: np.ndarray) -> np.ndarray:
        return self.negative.c.xyz(reflectance * self.calibration_light) @ self.to_ap1.T

    def equivalent_exposure(self, apd: np.ndarray) -> tuple[np.ndarray, int]:
        """Rule 'chart_equivalent_exposure' (inversion 'curves') or 'chart_straight_line' (inversion 'straight'). The second value counts the records outside the kept part of a curve."""
        if self.inversion == "straight":
            return GREY * 2.0 ** ((apd - self.straight_grey) / self.straight_slope), 0
        out = np.empty(apd.shape, dtype=np.float64)
        outside = 0
        for k in range(3):
            x = apd[..., k]
            outside += int(((x < self.ramp_apd[k][0]) | (x > self.ramp_apd[k][-1])).sum())
            out[..., k] = GREY * 2.0 ** np.interp(x, self.ramp_apd[k], self.ramp_stops[k])
        return out, outside

    def scene_ap1(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        record, stats = self.negative.negative_image(image[None] if image.ndim == 2 else image)
        e, outside = self.equivalent_exposure(self.density(record))
        out = e @ self.matrix.T
        stats = {**stats, "record_outside_curve": outside}
        return (out[0] if image.ndim == 2 else out), stats

    def display(self, scene: np.ndarray) -> tuple[np.ndarray, int]:
        """Rule 'chart_scan_display'."""
        rec709 = scene @ self.ap1_to_rec709.T
        clipped = int(((rec709 < 0) | (rec709 > 1)).any(axis=-1).sum())
        return fp.srgb_encode(np.clip(rec709, 0.0, 1.0)), clipped

    def render_spectra(self, reflectance: np.ndarray, light: np.ndarray) -> np.ndarray:
        """Flat patches of measured reflectance (N, nodes) under a light (Y = 1), with no reconstruction from AP1: the point form of the negative,
        then the same scan, inversion, matrix, and output as render. A diagnostic of the input path."""
        n = self.negative
        q = n.layer_gain * n.c.layer_exposure(reflectance * light)
        record, _ = n.negative_density(q)
        e, _ = self.equivalent_exposure(self.density(record))
        scene = e @ self.matrix.T
        if self.output == "clip709":
            return self.display(scene)[0]
        if self.sensitivity_matrix:
            scene = self.compress_709(scene @ self.ap1_to_rec709.T)
        return self.display_channels(scene)

    def compress_709(self, rgb: np.ndarray) -> np.ndarray:
        if not self.display_compress:
            return rgb
        o = self.negative.options
        return fp.compress_gamut(rgb, o.gamut_threshold, o.gamut_limit, o.gamut_power)

    def display_channels(self, e: np.ndarray) -> np.ndarray:
        """Rules 'scan_channel_curve' and 'scan_log_curve': each channel of e as the same display channel."""
        if self.output == "channel_curve":
            powered = (np.maximum(e, 0.0) / GREY) ** CHANNEL_CURVE_N
            return fp.srgb_encode(powered / (powered + 1.0 / CHANNEL_CURVE_T - 1.0))
        s = np.log2(np.maximum(e, 1e-12) / GREY)
        return 1.0 / (1.0 + np.exp(-(s - self.log_s0) / self.log_w))

    def render(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        scene, stats = self.scene_ap1(ap1)
        scene = scene * self.exposure_scale
        if self.output != "clip709":
            stats["display_clipped"] = 0
            if self.sensitivity_matrix:
                scene = self.compress_709(scene @ self.ap1_to_rec709.T)
            return self.display_channels(scene), stats
        out, clipped = self.display(scene)
        stats["display_clipped"] = clipped
        return out, stats

    def product_values(self) -> dict[str, np.ndarray]:
        """The values of a selection that Alcedo Studio needs for the scan form of FP6 (issue 661), for SELECTED_FORM with exposure 0:
        the slope and the grey of rule 'chart_straight_line' (Status M density per stop, Status M density), the matrix from e to linear Rec. 709
        (rule 'film_sensitivity_matrix' with AP1 to Rec. 709 folded in), and s0, w of rule 'scan_log_curve'."""
        if self.inversion != "straight" or self.output != "log_curve" or not self.sensitivity_matrix or not self.display_compress or self.exposure_scale != 1.0:
            raise ValueError("product_values needs SELECTED_FORM with exposure 0")
        return {"slope": np.asarray(self.straight_slope, dtype=np.float64), "grey": np.asarray(self.straight_grey, dtype=np.float64),
                "rec709_matrix": np.asarray(self.ap1_to_rec709 @ self.matrix, dtype=np.float64), "log_curve": np.array([self.log_s0, self.log_w], dtype=np.float64)}

    def lab_of_ap1(self, ap1: np.ndarray) -> np.ndarray:
        return lab(ap1 @ self.negative.c.ap1_to_xyz.T, self.ap1_white)
