"""Appearance analysis of Lab Scan (step P10, ROADMAP U97): what the scan does to colours, in CAM16 of the display, on a scene-referred sweep.

Sweep (the input of the film, after the product grade): hues of CAM16 (scene viewing, D65, L_A 64, average surround, D = 1) every 10 degrees, at the
lightness of the 18 % grey, at four colourfulness levels (fractions of the largest M that all hues reach inside Rec. 709 at that lightness), each
at exposures -10 .. +10 stops (the same chromaticity, the scene luminance times 2^e); a neutral ramp -10 .. +10 stops; memory colours.
Display: the sRGB of the flow, decoded, as XYZ of Rec. 709 (D65), in CAM16 of the display: white 100, L_A 20, Y_b 20, dim surround, D = 1 (the
viewer adapted to the display white). Distances in CAM16-UCS (dE').

Decomposition of the change of the film against the reference (the scene through the same OpenDRT, no film):
- white balance part: the best von Kries change of the scene (three CAT16 gains, so also the exposure) that, through the reference, comes nearest
  to the film (least dE' on the sweep from -4 to +4 stops and the neutral ramp). This is what a change of the colour temperature and tint of a
  digital photo can do.
- character: the film against the white-balanced reference. Its hue rotation (degrees of CAM16 h) is split over the hue circle into the part with
  period 180 degrees (a hue and its complement turn the same way: the only part a 3x3 matrix about the neutral can make, because M(-v) = -M(v)) and
  the remainder (a hue and its complement turn differently).
- the cast of the neutral ramp, along the axis of the colour temperature (the display grey of the reference when the scene light gets bluer:
  + is bluer) and the tint axis at right angles to it (+ is greener), per exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

import cam16

D65_100 = (95.047, 100.0, 108.883)
DISPLAY = cam16.Viewing(D65_100, 20.0, 20.0, "dim", 1.0)
SCENE = cam16.Viewing(D65_100, 64.0, 20.0, "average", 1.0)
HUES = np.arange(0.0, 360.0, 10.0)
M_FRACTIONS = (0.25, 0.5, 0.75, 1.0)
EXPOSURES = np.arange(-10.0, 10.01, 1.0)
FIT_RANGE = (-4.0, 4.0)
NEUTRAL = np.arange(-10.0, 10.01, 0.5)
MEMORY_EXPOSURES = (-3.0, -1.0, 0.0, 1.0)
# AP1 (white balanced) of memory colours; scaled to the luminance of the grey.
MEMORY = {"dune": (0.1201, 0.0807, 0.0449), "foliage": (0.045, 0.075, 0.025), "sky": (0.10, 0.16, 0.30), "skin": (0.27, 0.18, 0.13),
          "red": (0.30, 0.06, 0.04), "yellow": (0.36, 0.30, 0.04), "teal": (0.04, 0.13, 0.12), "lamp": (0.42, 0.20, 0.05)}
# Named hues of the report, CAM16 h of the scene (unique red 20.14, yellow 90, green 164.25, blue 237.53).
NAMED_HUES = {"red": 20, "orange": 50, "yellow": 90, "lime": 120, "green": 160, "cyan": 200, "blue": 240, "violet": 280, "magenta": 330}


def srgb_decode(code: np.ndarray) -> np.ndarray:
    return np.where(code <= 0.04045, code / 12.92, ((code + 0.055) / 1.055) ** 2.4)


def wrap(deg: np.ndarray) -> np.ndarray:
    return (np.asarray(deg) + 180.0) % 360.0 - 180.0


@dataclass
class Sweep:
    ap1: np.ndarray
    exposure: np.ndarray
    fraction: np.ndarray
    hue: np.ndarray
    kind: np.ndarray  # 0 chromatic, 1 neutral, 2 memory
    name: list = field(default_factory=list)
    m_common: float = 0.0


def make_sweep(fp, c) -> Sweep:
    scene = cam16.Cam16(SCENE)
    xyz_to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))
    j_grey = float(scene.forward(np.asarray(D65_100) * 0.18)["J"])

    def inside(m, h):
        return (scene.inverse(j_grey, m, h) / 100.0 @ fp.XYZ_TO_REC709.T).min() >= 0.0

    limits = []
    for h in HUES:
        lo, hi = 0.0, 200.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if inside(mid, h) else (lo, mid)
        limits.append(lo)
    m_common = float(min(limits))
    ap1, exposure, fraction, hue, kind, name = [], [], [], [], [], []
    for e in EXPOSURES:
        for f in M_FRACTIONS:
            xyz = scene.inverse(np.full(len(HUES), j_grey), np.full(len(HUES), f * m_common), HUES) / 100.0 * 2.0 ** e
            ap1.append(xyz @ xyz_to_ap1.T)
            exposure += [e] * len(HUES)
            fraction += [f] * len(HUES)
            hue += list(HUES)
            kind += [0] * len(HUES)
            name += [""] * len(HUES)
    grey = np.ones(3) * 0.18
    for e in NEUTRAL:
        ap1.append((grey * 2.0 ** e)[None])
        exposure.append(e), fraction.append(0.0), hue.append(np.nan), kind.append(1), name.append("neutral")
    y_of = c.ap1_to_xyz[1]
    for key, value in MEMORY.items():
        v = np.asarray(value) / (np.asarray(value) @ y_of) * 0.18
        for e in MEMORY_EXPOSURES:
            ap1.append((v * 2.0 ** e)[None])
            exposure.append(e), fraction.append(np.nan), hue.append(np.nan), kind.append(2), name.append(key)
    return Sweep(np.concatenate(ap1).astype(np.float32), np.asarray(exposure, dtype=float), np.asarray(fraction, dtype=float),
                 np.asarray(hue, dtype=float), np.asarray(kind), name, m_common)


class Display:
    """sRGB code of a flow to CAM16 of the display."""

    def __init__(self, fp) -> None:
        self.cam = cam16.Cam16(DISPLAY)
        self.rec709_to_xyz = np.linalg.inv(fp.XYZ_TO_REC709)

    def appearance(self, code: np.ndarray) -> dict[str, np.ndarray]:
        xyz = srgb_decode(np.clip(np.asarray(code, dtype=np.float64), 0.0, 1.0)) @ self.rec709_to_xyz.T * 100.0
        v = self.cam.forward(np.maximum(xyz, 0.0))
        v["UCS"] = cam16.ucs_of(v["J"], v["M"], v["h"])
        return v


class Reference:
    """The scene through OpenDRT (native grey), no film; with a von Kries change of the scene (CAT16 gains)."""

    def __init__(self, fp, dt, c) -> None:
        self.fp, self.dt = fp, dt
        self.cone = cam16.M16 @ c.ap1_to_xyz
        self.cone_inverse = np.linalg.inv(self.cone)

    def code(self, ap1: np.ndarray, log_gains: np.ndarray | None = None) -> np.ndarray:
        if log_gains is not None:
            ap1 = ap1 @ (self.cone_inverse @ np.diag(np.exp(log_gains)) @ self.cone).T
        return np.asarray(self.dt.render_native("opendrt", np.ascontiguousarray(ap1, dtype=np.float32), self.fp.srgb_encode))


def film_code(model, ap1: np.ndarray) -> np.ndarray:
    return np.asarray(model.render(np.ascontiguousarray(ap1, dtype=np.float32)[None])[0][0])


def axes(reference: Reference, display: Display, c) -> tuple[np.ndarray, np.ndarray]:
    """Unit vectors in CAM16-UCS a', b' of the display: the colour temperature axis (+ bluer) and the tint axis (+ greener)."""
    def white(kelvin):
        # CIE daylight chromaticity (4000 to 25000 K).
        t = kelvin
        x = (-4.6070e9 / t ** 3 + 2.9678e6 / t ** 2 + 0.09911e3 / t + 0.244063) if t <= 7000 else (-2.0064e9 / t ** 3 + 1.9018e6 / t ** 2 + 0.24748e3 / t + 0.237040)
        y = -3.0 * x * x + 2.870 * x - 0.275
        return np.array([x / y, 1.0, (1 - x - y) / y])
    cone_d65 = cam16.M16 @ white(6504.0)
    grey = np.full((1, 3), 0.18)
    points = []
    for kelvin in (6000.0, 7000.0):
        gains = np.log((cam16.M16 @ white(kelvin)) / cone_d65)
        points.append(display.appearance(reference.code(grey, gains))["UCS"][0, 1:])
    blue = points[1] - points[0]
    blue /= np.linalg.norm(blue)
    green = np.array([-blue[1], blue[0]])
    if np.cos(np.arctan2(green[1], green[0]) - np.radians(150.0)) < 0:
        green = -green
    return blue, green


@dataclass
class Result:
    film: dict
    ref: dict
    balanced: dict
    log_gains: np.ndarray
    sweep: Sweep


def analyse(model, sweep: Sweep, reference: Reference, display: Display) -> Result:
    film = display.appearance(film_code(model, sweep.ap1))
    ref = display.appearance(reference.code(sweep.ap1))
    use = (sweep.kind < 2) & (sweep.exposure >= FIT_RANGE[0]) & (sweep.exposure <= FIT_RANGE[1])
    target = film["UCS"][use]

    def residual(p):
        return (display.appearance(reference.code(sweep.ap1[use], p))["UCS"] - target).ravel()
    fit = least_squares(residual, np.zeros(3), jac="3-point", diff_step=1e-3)  # central: the neutrals sit on the kink of M at zero chroma
    balanced = display.appearance(reference.code(sweep.ap1, fit.x))
    return Result(film, ref, balanced, fit.x, sweep)


def de(a: dict, b: dict, mask: np.ndarray) -> float:
    return float(np.mean(np.linalg.norm(a["UCS"][mask] - b["UCS"][mask], axis=1)))


def hue_split(dh: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """dh over HUES (last axis): the part with period 180 degrees and the remainder."""
    half = len(HUES) // 2
    even = 0.5 * (dh + np.roll(dh, half, axis=-1))
    return even, dh - even


def summary(r: Result, blue: np.ndarray, green: np.ndarray) -> dict:
    s = r.sweep
    fit_range = (s.exposure >= FIT_RANGE[0]) & (s.exposure <= FIT_RANGE[1])
    chromatic = (s.kind == 0) & fit_range
    out = {"log_gains": r.log_gains.tolist(), "dE_total": de(r.film, r.ref, chromatic | ((s.kind == 1) & fit_range)),
           "dE_wb_part": de(r.balanced, r.ref, chromatic | ((s.kind == 1) & fit_range)),
           "dE_character": de(r.film, r.balanced, chromatic | ((s.kind == 1) & fit_range))}
    out["wb_explained"] = 1.0 - np.sum(np.linalg.norm(r.film["UCS"] - r.balanced["UCS"], axis=1)[fit_range & (s.kind < 2)] ** 2) / max(
        np.sum(np.linalg.norm(r.film["UCS"] - r.ref["UCS"], axis=1)[fit_range & (s.kind < 2)] ** 2), 1e-12)
    # Cast of the neutral ramp.
    n = s.kind == 1
    cast = r.film["UCS"][n][:, 1:] - r.ref["UCS"][n][:, 1:]
    out["cast"] = {f"{e:+.0f}": [float(cast[k] @ blue), float(cast[k] @ green), float(r.film["UCS"][n][k, 0] - r.ref["UCS"][n][k, 0])]
                   for k, e in enumerate(s.exposure[n]) if e in (-8, -6, -4, -2, 0, 2, 4, 6)}
    cast_b = r.balanced["UCS"][n][:, 1:] - r.ref["UCS"][n][:, 1:]
    out["cast_wb"] = {f"{e:+.0f}": [float(cast_b[k] @ blue), float(cast_b[k] @ green)] for k, e in enumerate(s.exposure[n]) if e in (-8, -4, 0, 4)}
    # Hue, colourfulness and lightness fields, per exposure and fraction: arrays over HUES.
    fields = {}
    for which, base in (("total", r.ref), ("character", r.balanced)):
        per = {}
        for e in EXPOSURES:
            for f in M_FRACTIONS:
                k = (s.kind == 0) & (s.exposure == e) & (s.fraction == f)
                dh = wrap(r.film["h"][k] - base["h"][k])
                dH = wrap((r.film["H"][k] - base["H"][k]) * 0.9) / 0.9  # quadrature, 400 per turn
                ratio = r.film["M"][k] / np.maximum(base["M"][k], 1e-6)
                dj = r.film["UCS"][k, 0] - base["UCS"][k, 0]
                per[(e, f)] = (dh, dH, ratio, dj, base["H"][k])
        fields[which] = per
    out["fields"] = fields
    rows = {}
    for which in ("total", "character"):
        tab = {}
        for e in (-4.0, -2.0, 0.0, 2.0):
            dh, dH, ratio, dj, _ = fields[which][(e, 0.5)]
            even, odd = hue_split(dh)
            tab[f"{e:+.0f}"] = {"rms_dh": float(np.sqrt(np.mean(dh ** 2))), "rms_even": float(np.sqrt(np.mean(even ** 2))), "rms_odd": float(np.sqrt(np.mean(odd ** 2))),
                                "named_dH": {k: float(dH[list(HUES).index(v)]) for k, v in NAMED_HUES.items()},
                                "named_ratio": {k: float(ratio[list(HUES).index(v)]) for k, v in NAMED_HUES.items()},
                                "named_dJ": {k: float(dj[list(HUES).index(v)]) for k, v in NAMED_HUES.items()},
                                "mean_ratio": float(np.mean(ratio))}
        rows[which] = tab
    out["rows"] = rows
    memory = {}
    for key in MEMORY:
        for e in MEMORY_EXPOSURES:
            k = np.array([nm == key for nm in s.name]) & (s.exposure == e)
            memory[f"{key}{e:+.0f}"] = {"ref_H": float(r.ref["H"][k][0]), "ref_M": float(r.ref["M"][k][0]),
                                        "dH": float(wrap((r.film["H"][k][0] - r.ref["H"][k][0]) * 0.9) / 0.9), "ratio": float(r.film["M"][k][0] / max(r.ref["M"][k][0], 1e-6)),
                                        "dJ": float(r.film["UCS"][k][0, 0] - r.ref["UCS"][k][0, 0]),
                                        "dH_char": float(wrap((r.film["H"][k][0] - r.balanced["H"][k][0]) * 0.9) / 0.9)}
    out["memory"] = memory
    return out


def spread(results: list[Result], use_character: bool) -> float:
    """Mean dE' of each stock to the mean of the stocks (chromatic sweep, -4 .. +4 stops), of the output or of the character."""
    s = results[0].sweep
    k = (s.kind == 0) & (s.exposure >= FIT_RANGE[0]) & (s.exposure <= FIT_RANGE[1])
    vectors = np.stack([(r.film["UCS"] - r.balanced["UCS"])[k] if use_character else r.film["UCS"][k] for r in results])
    return float(np.mean(np.linalg.norm(vectors - vectors.mean(axis=0), axis=-1)))
