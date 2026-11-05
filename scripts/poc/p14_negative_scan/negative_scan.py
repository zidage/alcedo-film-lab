"""Negative Scan (step P14): the developed negative read by a virtual film scanner, then a negative rendering model.

Input: the FilmOptions of a negative (mvp_pipeline.film_options), linear AP1 after the product grade.
Output: sRGB display code through OpenDRT (native grey), and the stages as arrays for the checks and the report.
Step: P14, user request of 2026-11-04 ("Negative Scan": Film Scanner Model + Negative Rendering Model). P13 is not used: the input is the
current spectral input of the viewer (spectral_input 'current').

The method has two parts. Each stage is done once; no later stage repeats a correction of an earlier one.

Part 1, Film Scanner Model (deterministic, no image statistic):
  I_i = k_i * integral L(lambda) S_i(lambda) 10^-D(lambda) dlambda,   i = R, G, B,
  D(lambda) = the spectral density of the developed negative (film base + the three dyes of the model, per pixel).
  - Rule 'ideal_scanner_bands': S_i is a Gaussian in wavelength with a centre and a full width at half maximum (option centres_nm,
    width_nm). It stands for an idealised sensor behind a filter; it is not the response of a Frontier or a Noritsu (their curves are not
    published). The band is cut where it falls below 1e-4 of its peak.
  - L(lambda) is the scanner light (option light): 'halogen' is a Planckian radiator at 3200 K; 'equal_energy' is a flat spectrum.
  - k_i normalises each channel to the empty film holder (no film): I_i = 1 with no film.
  - Integration: sum on the 1 nm nodes of the model grid (360-840 nm). The negative has three free dye amounts per pixel, so the reading is
    a table over the negative record (the table of ScanPreview of step P3, built by the C++ library of step P7), read by trilinear
    interpolation.
Part 2, Negative Rendering Model:
  a. Rule 'base_relative_density': D_i = log10(I_i,base / I_i), the density of channel i above the unexposed film (film base and orange mask).
  b. Rule 'generic_density_inversion': x_i = contrast * (D_i - D_i,aim) / gamma_i, a straight line in log10 exposure units about the grey,
     with E_i = 0.18 * 10^x_i. gamma_i is the channel density per log10 exposure of the 18 % grey of the average negative of the medium
     (the pool of rule generic_scan; each stock under its balance light, central difference at 0.09 and 0.36). gamma is the same for every
     stock of the medium, so a stock keeps its own contrast, crossover, toe, and shoulder: the inversion does not undo the curve of the stock.
     D_aim is rule 'stock_balance': the channel density of the 18 % grey of the balance light of the stock (D55 or T3200), as a lab scanner
     has one channel set-up per film type. This is the only stage that depends on the stock.
  c. Rule 'frame_auto_colour' (option auto, step P4 of the request): the only stage that reads a statistic of the frame. It is off in
     'Neutral Scan'. See auto_colour_shift.
  d. Manual keys: exposure (stops, neutral) and cyan, magenta, yellow keys (log10 units of the positive; +Y takes blue away, as a
     yellow key of a lab scanner).
  e. Rule 'black_at_film_base' (option black): the film base after stages b to d is subtracted per channel with this share, and the
     18 % grey stays at 0.18: E' = 0.18 (E - b E_base) / (0.18 - b E_base). b = 1 puts the black at the film base.
  f. Option primaries: 'channels' takes the three positive channels as linear AP1. 'film_primaries' is a comparison: a 3 x 3 matrix from
     the average layer sensitivities of the medium to the AP1 colour matching functions (least squares on the spectral curves under the
     balance light, rows sum to 1 so the balance grey stays neutral). The matrix is the same for every stock of a medium, and it is not
     fitted to a chart. ROADMAP section 2 forbids a matrix as a film stage; this one is a stage of the scanner software, and it is shown
     for review only.
  g. Display: OpenDRT, the default DRT of the document, with ACES 0.18 shown as 0.18 (display_transforms.render_native). No ACES output
     transform and no RGC on the output.
Values below 0 after stage e are counted (stats 'positive_below_0') and set to 0, because the display transform needs a non-negative
input; the count is in the record of each render.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p10_chart_scan"))
from aces_scan import ScanPreview, fp  # noqa: E402
import display_transforms as dt  # noqa: E402

LIGHTS = ("halogen", "equal_energy")
PRIMARIES = ("channels", "film_primaries")
AUTO_MODES = ("off", "neutral", "warm", "cool")
BAND_CUT = 1e-4
MODEL_GRID_NM = np.arange(360.0, 841.0, 1.0)  # the grid of the model (P0): 360-840 nm, 1 nm
LOG2 = float(np.log10(2.0))
# Rule 'frame_auto_colour' constants (inferred, not measured; stated in the P14 report):
AUTO_LONG_EDGE = 96  # the prescan: the frame reduced by area to this long edge
AUTO_VALID_LOG = (-1.6, 0.9)  # log10 exposure about the grey of the pixels that the statistic reads (about -5.3 to +3 stops)
AUTO_SIGMA = 0.12  # log10: width of the near-neutral weight about the current estimate of the cast
AUTO_ITERATIONS = 4
AUTO_CROSS_SHARE = 0.5  # share of the correction across the light axis (green-magenta), against 1 along it: subject failure suppression
AUTO_HIGHLIGHT_SHARE = 0.05  # the brightest share of the valid prescan pixels: the white-patch estimate
AUTO_TARGET = {"neutral": 0.0, "warm": 0.04, "cool": -0.04}  # log10 along the light axis toward the warm light


@dataclass(frozen=True)
class ScannerSetup:
    """The virtual scanner of rule 'ideal_scanner_bands'. Channel order R, G, B."""

    centres_nm: tuple[float, float, float] = (650.0, 545.0, 450.0)
    width_nm: float = 40.0
    light: str = "halogen"

    def validate(self) -> None:
        if self.light not in LIGHTS:
            raise ValueError(f"unknown scanner light {self.light!r}")
        if not 5.0 <= self.width_nm <= 150.0:
            raise ValueError(f"scanner band width {self.width_nm} nm: outside 5 to 150 nm")
        r, g, b = self.centres_nm
        if not (380.0 <= b < g < r <= 760.0):
            raise ValueError(f"scanner centres {self.centres_nm}: need 380 <= blue < green < red <= 760 nm")

    def responsivities(self, wavelengths: np.ndarray = MODEL_GRID_NM) -> tuple[np.ndarray, np.ndarray]:
        """Nodes (nm) and L(lambda) S_i(lambda) on them, shape (3, nodes). The scale of L does not matter, because k_i normalises each channel."""
        self.validate()
        sigma = self.width_nm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        bands = np.stack([np.exp(-0.5 * ((wavelengths - c) / sigma) ** 2) for c in self.centres_nm])
        light = np.ones_like(wavelengths) if self.light == "equal_energy" else wavelengths ** -5.0 / np.expm1(1.4388e7 / (wavelengths * 3200.0))
        keep = (bands >= BAND_CUT).any(axis=0)
        first, last = np.flatnonzero(keep)[[0, -1]]
        nodes = slice(first, last + 1)
        weights = np.where(bands[:, nodes] >= BAND_CUT, bands[:, nodes], 0.0) * light[nodes]
        return wavelengths[nodes], weights


def balance_light_name(negative_entry: dict) -> str:
    return "T3200" if negative_entry.get("exposure_kelvin", 5500) < 4500 else "D55"


class VirtualScan:
    """Part 1 of the method and stage a: the record of the negative to the channel density above the film base."""

    def __init__(self, options: fp.FilmOptions, setup: ScannerSetup) -> None:
        setup.validate()
        self.setup = setup
        # The scanner reads the negative only: ScanPreview turns the enlarger flare off, and its offset and output are not used here.
        # ScanPreview checks that the nodes are nodes of the model grid.
        wavelengths, weights = setup.responsivities()
        self.scan = ScanPreview(options, output="opendrt", lad_aim=False, scanner=("negative_scan", wavelengths, weights), reading="apd", encoding="adx16")
        self.negative = self.scan.negative
        self.base = self.scan.apd_dmin

    def density(self, record: np.ndarray) -> np.ndarray:
        """Stage a: channel density above the film base, D_i = log10(I_base / I)."""
        return self.scan.table_apd(record) - self.base

    def grey_density(self, light: str, scene_value: float = 0.18) -> np.ndarray:
        return self.scan.grey_apd(light, scene_value) - self.base

    def grey_gamma(self, light: str) -> np.ndarray:
        """Channel density per log10 exposure of the 18 % grey under a light (central difference at 0.09 and 0.36)."""
        return (self.grey_density(light, 0.36) - self.grey_density(light, 0.09)) / (2.0 * LOG2)


def average_sensitivities(models: list[VirtualScan], lights: list[str]) -> np.ndarray:
    """Layer sensitivities of each stock times its balance light, each channel normalised to 1, then the mean over the pool. Shape (3, grid)."""
    curves = []
    for model, light in zip(models, lights):
        n = model.negative
        weighted = n.c.film.w_negative * n.light(light)[None]
        curves.append(weighted / weighted.sum(axis=1, keepdims=True))
    return np.mean(curves, axis=0)


def film_primaries_matrix(model: VirtualScan, sensitivities: np.ndarray, light: str) -> np.ndarray:
    """Option primaries 'film_primaries' (comparison only): M with rows summing to 1 that minimises sum_lambda |M s(lambda) - a(lambda)|^2,
    s the pool sensitivities under the light (each channel sum 1), a the AP1 colour matching functions under the light (each channel sum 1)."""
    c = model.negative.c
    target = (c.xyz_to_ap1 @ c.w_xyz) * model.negative.light(light)[None]
    target = target / target.sum(axis=1, keepdims=True)
    s = sensitivities
    # Least squares with the constraint M 1 = 1, by a Lagrange multiplier per row.
    gram = s @ s.T
    ones = np.ones(3)
    rows = []
    for k in range(3):
        rhs = s @ target[k]
        kkt = np.block([[2.0 * gram, ones[:, None]], [ones[None, :], np.zeros((1, 1))]])
        solution = np.linalg.solve(kkt, np.concatenate([2.0 * rhs, [1.0]]))
        rows.append(solution[:3])
    return np.array(rows)


@dataclass(frozen=True)
class RenderingSetup:
    """Part 2 controls. Defaults: Neutral Scan."""

    contrast: float = 1.0
    exposure_stops: float = 0.0
    cyan: float = 0.0
    magenta: float = 0.0
    yellow: float = 0.0
    black: float = 1.0
    auto: str = "off"
    auto_strength: float = 0.8
    auto_density: float = 0.0
    primaries: str = "channels"

    def validate(self) -> None:
        if self.auto not in AUTO_MODES:
            raise ValueError(f"unknown auto colour mode {self.auto!r}")
        if self.primaries not in PRIMARIES:
            raise ValueError(f"unknown primaries {self.primaries!r}")


def reduce_frame(x: np.ndarray, long_edge: int = AUTO_LONG_EDGE) -> np.ndarray:
    """The prescan of rule 'frame_auto_colour': an area reduction of a (rows, columns, 3) image to this long edge; shape (N, 3)."""
    if x.ndim != 3:
        return np.asarray(x, dtype=np.float64).reshape(-1, 3)
    height, width = x.shape[:2]
    scale = long_edge / max(height, width)
    if scale >= 1.0:
        return np.asarray(x, dtype=np.float64).reshape(-1, 3)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return np.stack([np.asarray(Image.fromarray(np.ascontiguousarray(x[..., k], dtype=np.float32), mode="F").resize(size, Image.Resampling.BOX))
                     for k in range(3)], axis=-1).reshape(-1, 3).astype(np.float64)


def auto_colour_shift(x: np.ndarray, light_axis: np.ndarray, mode: str, strength: float, density_strength: float) -> tuple[np.ndarray, dict]:
    """Rule 'frame_auto_colour': the per-channel log10 shift that the scanner software applies to this frame.

    x: the positive in log10 exposure units about the grey (stage b), shape (rows, columns, 3).
    1. Prescan: x reduced by area to AUTO_LONG_EDGE; only pixels with a mean log10 in AUTO_VALID_LOG count (no deep shadow, no clipped light).
    2. Cast: u = x - mean_c(x), a vector in the plane of zero sum. Start from the median of u, then AUTO_ITERATIONS times: weight
       w = exp(-|u - m|^2 / AUTO_SIGMA^2), m = sum w u / sum w. The near-neutral pixels of the frame decide, so a large green or red area
       counts less than in a plain grey-world mean.
       Second estimate (white patch): the median of u over the brightest AUTO_HIGHLIGHT_SHARE of the valid pixels (white clouds, water,
       lit walls). Rule 'smaller_cast': the estimate with the smaller length is used. A frame with no real neutral (a meadow, a forest, a
       coloured backdrop) moves both estimates differently, and the smaller one gives the more conservative correction, as a lab avoids
       subject failure. (First review, 2026-11-04: the near-neutral estimate alone turned a yellow-green forest and meadow blue.)
    3. Correction: along the light axis (the direction in x of a change of light from T3200 to D65 for this stock, normalised) the share
       'strength' of the cast is removed; across it (green-magenta) the share strength * AUTO_CROSS_SHARE. 'warm' and 'cool' keep
       AUTO_TARGET along the light axis.
    4. Density (option density_strength): the share of the weighted mean log10 of the frame that moves to the grey; 0 is off.
    Returns the shift (3,) to add to x, and the record."""
    if mode == "off":
        return np.zeros(3), {"auto": "off"}
    pixels = reduce_frame(x)
    level = pixels.mean(axis=1)
    valid = (level > AUTO_VALID_LOG[0]) & (level < AUTO_VALID_LOG[1]) & np.isfinite(level)
    if valid.sum() < 16:
        raise ValueError(f"rule frame_auto_colour: only {int(valid.sum())} prescan pixels inside the valid range {AUTO_VALID_LOG}")
    u = pixels[valid] - level[valid, None]
    cast = np.median(u, axis=0)
    cast = cast - cast.mean()
    for _ in range(AUTO_ITERATIONS):
        weight = np.exp(-np.sum((u - cast) ** 2, axis=1) / AUTO_SIGMA ** 2)
        if weight.sum() <= 1e-9:
            break
        cast = (weight[:, None] * u).sum(axis=0) / weight.sum()
    neutral_cast = cast
    bright = level[valid] >= np.quantile(level[valid], 1.0 - AUTO_HIGHLIGHT_SHARE)
    white_cast = np.median(u[bright], axis=0)
    white_cast = white_cast - white_cast.mean()
    cast = white_cast if np.linalg.norm(white_cast) < np.linalg.norm(neutral_cast) else neutral_cast
    axis = light_axis - light_axis.mean()
    axis = axis / np.linalg.norm(axis)
    along = float(cast @ axis)
    across = cast - along * axis
    target = AUTO_TARGET[mode]
    shift = -(strength * (along - target)) * axis - strength * AUTO_CROSS_SHARE * across
    weight = np.exp(-np.sum((u - cast) ** 2, axis=1) / AUTO_SIGMA ** 2)
    mean_level = float(np.average(level[valid], weights=weight + 1e-12))
    shift = shift - density_strength * mean_level
    record = {"auto": mode, "cast_log10": [round(float(v), 4) for v in cast], "near_neutral_cast_log10": [round(float(v), 4) for v in neutral_cast],
              "white_patch_cast_log10": [round(float(v), 4) for v in white_cast], "along_light_axis": round(along, 4),
              "shift_log10": [round(float(v), 4) for v in shift], "frame_mean_log10": round(mean_level, 4),
              "prescan_pixels": int(valid.sum()), "near_neutral_weight": round(float(weight.sum()), 2)}
    return shift, record


class NegativeScanPreview:
    """The two parts of the method for one negative. render(ap1) gives sRGB display code and a record."""

    def __init__(self, options: fp.FilmOptions, scanner: ScannerSetup, rendering: RenderingSetup, balance_light: str,
                 gamma: np.ndarray, matrix: np.ndarray | None = None) -> None:
        self.read = VirtualScan(options, scanner)
        self.negative = self.read.negative
        self.balance_light = balance_light
        self.gamma = np.asarray(gamma, dtype=np.float64)
        if self.gamma.shape != (3,) or np.min(self.gamma) <= 0:
            raise ValueError(f"generic gamma {self.gamma}: needs three positive values")
        self.aim = self.read.grey_density(balance_light)
        self.medium_matrix = matrix
        # The light axis of rule frame_auto_colour: the change of stage b of a grey from T3200 to D65, for this stock (contrast 1).
        self.light_axis = (self.read.grey_density("D65") - self.read.grey_density("T3200")) / self.gamma
        self.set_rendering(rendering)

    def set_rendering(self, rendering: RenderingSetup) -> None:
        """Part 2 acts after the scan, so new rendering controls keep the scan table."""
        rendering.validate()
        if rendering.primaries == "film_primaries" and self.medium_matrix is None:
            raise ValueError("primaries 'film_primaries' needs the matrix of the medium")
        self.rendering = rendering
        self.matrix = self.medium_matrix if rendering.primaries == "film_primaries" else None

    def positive_log(self, density: np.ndarray) -> np.ndarray:
        """Stage b: log10 exposure about the grey."""
        return self.rendering.contrast * (density - self.aim) / self.gamma

    def manual_shift(self) -> np.ndarray:
        r = self.rendering
        return r.exposure_stops * LOG2 - np.array([r.cyan, r.magenta, r.yellow])

    def positive(self, density: np.ndarray, spatial: bool = True) -> tuple[np.ndarray, dict]:
        """Stages b to f: channel density above the base to linear AP1."""
        r = self.rendering
        x = self.positive_log(density)
        shift, record = auto_colour_shift(x, self.light_axis, r.auto, r.auto_strength, r.auto_density) if spatial else (np.zeros(3), {"auto": "not applied to a ramp"})
        total = shift + self.manual_shift()
        linear = 0.18 * 10.0 ** (x + total)
        base = 0.18 * 10.0 ** (self.positive_log(np.zeros((1, 3)))[0] + total)
        b = r.black
        if b * base.max() >= 0.18:
            raise ValueError(f"black {b}: the film base {base} is at or above the grey; lower the black share")
        linear = 0.18 * (linear - b * base) / (0.18 - b * base)
        if self.matrix is not None:
            linear = linear @ self.matrix.T
        below = int((linear < 0).any(axis=-1).sum())
        record = {**record, "film_base_positive": [round(float(v), 5) for v in base], "positive_below_0": below}
        return np.maximum(linear, 0.0), record

    def render(self, ap1: np.ndarray) -> tuple[np.ndarray, dict]:
        image = np.ascontiguousarray(ap1, dtype=np.float32)
        record, stats = self.negative.negative_image(image[None] if image.ndim == 2 else image)
        spatial = image.ndim == 3 and min(image.shape[:2]) >= 16
        density = self.read.density(record)
        linear, info = self.positive(density, spatial)
        display = dt.render_native("opendrt", np.asarray(linear, dtype=np.float32), fp.srgb_encode)
        if not np.isfinite(display).all():
            raise RuntimeError("OpenDRT returned values that are not finite")
        info = {**stats, **info, "display_outside_0_1": int(((display < 0) | (display > 1)).any(axis=-1).sum())}
        return np.clip(display, 0.0, 1.0), info


def derive_medium(make_read, pool: tuple[str, ...], balance_of) -> dict:
    """Rule 'generic_density_inversion' and the comparison matrix: from the stocks of a pool. make_read(stock) gives the VirtualScan of a stock
    with the scene light at its balance light; balance_of(stock) gives that light. Returns gamma (3,), the matrix, and the per-stock gammas."""
    models = [make_read(stock) for stock in pool]
    lights = [balance_of(stock) for stock in pool]
    gammas = np.array([m.grey_gamma(light) for m, light in zip(models, lights)])
    sensitivities = average_sensitivities(models, lights)
    matrix = film_primaries_matrix(models[0], sensitivities, "D55")
    return {"gamma": gammas.mean(axis=0), "matrix": matrix, "stock_gamma": {s: g.round(4).tolist() for s, g in zip(pool, gammas)}}
