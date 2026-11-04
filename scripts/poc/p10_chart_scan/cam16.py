"""CAM16 and CAM16-UCS (Li, Li, Wang, Zu, Luo, Cui, Melgosa, Brill, Pointer 2017, "Comprehensive colour solutions: CAM16, CAT16, and CAM16-UCS",
Color Res. Appl. 42 (6)), forward and inverse, for the appearance analysis of Lab Scan (step P10, ROADMAP U97).

XYZ on the scale of Y_w = 100. Viewing conditions: the white XYZ_w, the adapting luminance L_A (cd/m2), the background Y_b, the surround (F, c, N_c),
and the degree of adaptation D (None: the formula of the model from F and L_A). Outputs J (lightness), C (chroma), h (hue angle, degrees), M
(colourfulness), s (saturation), Q (brightness), H (hue quadrature: 0 red, 100 yellow, 200 green, 300 blue, 400 red), and the UCS J', a', b'.
check() compares the forward model with the test values of the colour-science library for the same input (XYZ_to_CAM16 example).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

M16 = np.array([[0.401288, 0.650173, -0.051461], [-0.250268, 1.204414, 0.045854], [-0.002079, 0.048952, 0.953127]])
M16_INVERSE = np.linalg.inv(M16)
SURROUNDS = {"average": (1.0, 0.69, 1.0), "dim": (0.9, 0.59, 0.9), "dark": (0.8, 0.525, 0.8)}
HUE_H = np.array([20.14, 90.00, 164.25, 237.53, 380.14])
HUE_E = np.array([0.8, 0.7, 1.0, 1.2, 0.8])
HUE_Q = np.array([0.0, 100.0, 200.0, 300.0, 400.0])
UCS_C1, UCS_C2 = 0.007, 0.0228


def _compress(x: np.ndarray, f_l: float) -> np.ndarray:
    p = (f_l * np.abs(x) / 100.0) ** 0.42
    return 400.0 * np.sign(x) * p / (p + 27.13) + 0.1


def _expand(x: np.ndarray, f_l: float) -> np.ndarray:
    y = np.abs(x - 0.1)
    return np.sign(x - 0.1) * 100.0 / f_l * (27.13 * y / (400.0 - y)) ** (1.0 / 0.42)


@dataclass(frozen=True)
class Viewing:
    white: tuple[float, float, float]
    adapting_luminance: float
    background: float = 20.0
    surround: str = "average"
    degree: float | None = None


class Cam16:
    def __init__(self, viewing: Viewing) -> None:
        self.viewing = viewing
        xyz_w = np.asarray(viewing.white, dtype=np.float64)
        self.f, self.c, self.n_c = SURROUNDS[viewing.surround]
        l_a = float(viewing.adapting_luminance)
        d = self.f * (1.0 - (1.0 / 3.6) * np.exp((-l_a - 42.0) / 92.0)) if viewing.degree is None else viewing.degree
        d = float(np.clip(d, 0.0, 1.0))
        rgb_w = M16 @ xyz_w
        self.d_rgb = d * xyz_w[1] / rgb_w + 1.0 - d
        k = 1.0 / (5.0 * l_a + 1.0)
        self.f_l = 0.2 * k ** 4 * (5.0 * l_a) + 0.1 * (1.0 - k ** 4) ** 2 * (5.0 * l_a) ** (1.0 / 3.0)
        self.n = viewing.background / xyz_w[1]
        self.z = 1.48 + np.sqrt(self.n)
        self.n_bb = 0.725 * self.n ** -0.2
        rgb_aw = _compress(self.d_rgb * rgb_w, self.f_l)
        self.a_w = (2.0 * rgb_aw[0] + rgb_aw[1] + 0.05 * rgb_aw[2] - 0.305) * self.n_bb

    def forward(self, xyz: np.ndarray) -> dict[str, np.ndarray]:
        rgb_a = _compress((np.asarray(xyz, dtype=np.float64) @ M16.T) * self.d_rgb, self.f_l)
        r, g, b = rgb_a[..., 0], rgb_a[..., 1], rgb_a[..., 2]
        a = r - 12.0 * g / 11.0 + b / 11.0
        bb = (r + g - 2.0 * b) / 9.0
        h = np.degrees(np.arctan2(bb, a)) % 360.0
        e_t = 0.25 * (np.cos(np.radians(h) + 2.0) + 3.8)
        big_a = (2.0 * r + g + 0.05 * b - 0.305) * self.n_bb
        j = 100.0 * np.maximum(big_a / self.a_w, 0.0) ** (self.c * self.z)
        q = (4.0 / self.c) * np.sqrt(j / 100.0) * (self.a_w + 4.0) * self.f_l ** 0.25
        t = (50000.0 / 13.0 * self.n_c * self.n_bb * e_t * np.hypot(a, bb)) / (r + g + 21.0 / 20.0 * b)
        chroma = np.maximum(t, 0.0) ** 0.9 * np.sqrt(j / 100.0) * (1.64 - 0.29 ** self.n) ** 0.73
        m = chroma * self.f_l ** 0.25
        s = 100.0 * np.sqrt(m / np.maximum(q, 1e-12))
        return {"J": j, "C": chroma, "h": h, "M": m, "s": s, "Q": q, "H": hue_quadrature(h)}

    def inverse(self, j: np.ndarray, m: np.ndarray, h: np.ndarray) -> np.ndarray:
        """XYZ of J, M, h."""
        j, m, h = (np.asarray(v, dtype=np.float64) for v in (j, m, h))
        chroma = m / self.f_l ** 0.25
        t = (chroma / (np.sqrt(np.maximum(j, 1e-12) / 100.0) * (1.64 - 0.29 ** self.n) ** 0.73)) ** (1.0 / 0.9)
        hr = np.radians(h)
        e_t = 0.25 * (np.cos(hr + 2.0) + 3.8)
        big_a = self.a_w * (j / 100.0) ** (1.0 / (self.c * self.z))
        p2 = big_a / self.n_bb + 0.305
        p1 = 50000.0 / 13.0 * self.n_c * self.n_bb * e_t
        # Opponent dimensions: from t = p1 sqrt(a^2 + b^2) / (R_a + G_a + 21/20 B_a), with R_a + G_a + 21/20 B_a linear in (p2, a, b).
        gamma = 23.0 * p2 * t / np.maximum(23.0 * p1 + 11.0 * t * np.cos(hr) + 108.0 * t * np.sin(hr), 1e-12)
        a, b = gamma * np.cos(hr), gamma * np.sin(hr)
        r = (460.0 * p2 + 451.0 * a + 288.0 * b) / 1403.0
        g = (460.0 * p2 - 891.0 * a - 261.0 * b) / 1403.0
        bl = (460.0 * p2 - 220.0 * a - 6300.0 * b) / 1403.0
        rgb = _expand(np.stack([r, g, bl], axis=-1), self.f_l) / self.d_rgb
        return rgb @ M16_INVERSE.T

    def ucs(self, xyz: np.ndarray) -> np.ndarray:
        """CAM16-UCS J', a', b'."""
        v = self.forward(xyz)
        return ucs_of(v["J"], v["M"], v["h"])


def ucs_of(j: np.ndarray, m: np.ndarray, h: np.ndarray) -> np.ndarray:
    jp = (1.0 + 100.0 * UCS_C1) * j / (1.0 + UCS_C1 * j)
    mp = np.log1p(UCS_C2 * m) / UCS_C2
    return np.stack([jp, mp * np.cos(np.radians(h)), mp * np.sin(np.radians(h))], axis=-1)


def hue_quadrature(h: np.ndarray) -> np.ndarray:
    hp = np.where(h < HUE_H[0], h + 360.0, h)
    i = np.clip(np.searchsorted(HUE_H, hp, side="right") - 1, 0, 3)
    hi, hj, ei, ej = HUE_H[i], HUE_H[i + 1], HUE_E[i], HUE_E[i + 1]
    return HUE_Q[i] + 100.0 * ((hp - hi) / ei) / ((hp - hi) / ei + (hj - hp) / ej)


def check() -> None:
    """The colour-science example of XYZ_to_CAM16, and the round trip of the inverse."""
    cam = Cam16(Viewing((95.05, 100.00, 108.88), 318.31, 20.0, "average"))
    v = cam.forward(np.array([19.01, 20.00, 21.78]))
    expected = {"J": 41.7312079, "C": 0.1033557, "h": 217.0679597, "M": 0.1074367, "Q": 195.3717089, "H": 275.5949861}
    for key, value in expected.items():
        if abs(float(v[key]) - value) > 1e-4 * max(1.0, abs(value)):
            raise AssertionError(f"CAM16 {key} {float(v[key])} against {value}")
    rng = np.random.default_rng(1)
    xyz = rng.uniform(2.0, 90.0, (500, 3))
    back = cam.inverse(*(cam.forward(xyz)[k] for k in ("J", "M", "h")))
    if np.max(np.abs(back - xyz)) > 1e-6 * 100:
        raise AssertionError(f"CAM16 inverse round trip {np.max(np.abs(back - xyz))}")


if __name__ == "__main__":
    check()
    print("CAM16 check passed")
