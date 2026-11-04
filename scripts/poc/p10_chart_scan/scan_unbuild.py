"""Rule 'adx_stock_numbers' of Lab Scan (step P10, ROADMAP U96): the Academy form of the ADX to ACES transform (CDD_TO_CID, the Academy curve,
EXP_TO_ACES) with the two matrices derived per stock from the film model, in the way the Academy numbers describe one average negative.

Why (U94, U96): the Academy numbers describe an average motion picture negative read in APD. On the stocks of the model they turn blue to cyan and
orange to red, and lose chroma in green (mean dE 9 to 11 against the scene, hue 8 to 13 degrees). Their CDD_TO_CID has positive terms off the
diagonal: it takes out the strong interlayer effects of real negatives, which the model has in a weaker form, so on the model it lowers chroma, and
EXP_TO_ACES then turns the hues.

Derivation, under the balance light of the stock (D55 or T3200), with the 18 % grey on the LAD aim:
- CDD_TO_CID: T[i, j] = d cdd_j / d log10 H_i at the grey (layer i, channel j), through the curves of the negative, the interlayer inhibition (point
  form), the Kodak 2383 printing density, and the channel scale of rule adx_slope_match. CDD_TO_CID = T^-1 (row vectors, as in the Academy CTL),
  each column divided by its sum, so that a neutral cdd stays a neutral cid, as in the Academy matrix.
- The curve from cid to log exposure: the Academy table and slope, unchanged.
- EXP_TO_ACES: the 3x3 with columns that sum to 1 (white kept) with the least CIELAB dE (D60 white of ACES) from the exposure of the transform to the
  scene, on TRAINING colours (the 24 ColorChecker colours of sRGB values, and 108 hues at saturations 0.2, 0.4, 0.6, each at -1, 0, +1 stops). This
  is the fit of the ACES procedure for camera input transforms (P-2013-001 form) on the exposure that the transform recovers.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

CHECKER_SRGB = np.array([[115, 82, 68], [194, 150, 130], [98, 122, 157], [87, 108, 67], [133, 128, 177], [103, 189, 170], [214, 126, 44], [80, 91, 166], [193, 90, 99],
                         [94, 60, 108], [157, 188, 64], [224, 163, 46], [56, 61, 150], [70, 148, 73], [175, 54, 60], [231, 199, 31], [187, 86, 149], [8, 133, 161],
                         [243, 242, 242], [200, 200, 200], [160, 160, 160], [122, 122, 121], [85, 85, 85], [52, 52, 52]]) / 255.0
REC709_LUMINANCE = np.array([0.2126, 0.7152, 0.0722])
AP0_TO_XYZ = np.array([[0.9525523959, 0.0, 0.0000936786], [0.3439664498, 0.7281660966, -0.0721325464], [0.0, 0.0, 1.0088251844]])
AP0_TO_AP1 = np.array([[1.4514393161, -0.2365107469, -0.2149285693], [-0.0765537734, 1.1762296998, -0.0996759264], [0.0083161484, -0.0060324498, 0.9977163014]])
JACOBIAN_STEP = 1e-3  # log10 H


def lab(aces: np.ndarray) -> np.ndarray:
    xyz = np.asarray(aces) @ AP0_TO_XYZ.T
    f = np.cbrt(np.maximum(xyz / AP0_TO_XYZ.sum(axis=1), 1e-9))
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def training(fp, c) -> np.ndarray:
    rec709_to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3)) @ np.linalg.inv(fp.XYZ_TO_REC709)
    checker = np.where(CHECKER_SRGB <= 0.04045, CHECKER_SRGB / 12.92, ((CHECKER_SRGB + 0.055) / 1.055) ** 2.4)
    checker = checker * 0.18 / (checker[21] @ REC709_LUMINANCE)  # the fourth grey near 0.18
    hue = np.arange(36) * 6.0 / 36
    channels = np.stack([np.clip(np.abs(((hue + s) % 6.0) - 3.0) - 1.0, 0.0, 1.0) for s in (0.0, 4.0, 2.0)], axis=-1)
    hues = np.concatenate([(1.0 - s + s * channels) for s in (0.2, 0.4, 0.6)])
    hues = hues / (hues @ REC709_LUMINANCE)[:, None] * 0.18
    base = np.concatenate([checker, hues]) @ rec709_to_ap1.T
    return np.concatenate([base * 2.0 ** e for e in (-1.0, 0.0, 1.0)]).astype(np.float32)


def derive(fp, balance) -> tuple[np.ndarray, np.ndarray]:
    """The derived CDD_TO_CID and EXP_TO_ACES from a ScanPreview whose scene light is the balance light, with the LAD aim at that light."""
    n = balance.negative
    q = n.layer_gain * n.c.layer_exposure(0.18 * n.light(n.options.scene_light))

    def cdd(shift):
        record, _ = n.negative_density((q * 10.0 ** shift)[None])
        return balance.scale * balance.table_apd(record)[0]
    t = np.stack([(cdd(JACOBIAN_STEP * np.eye(3)[i]) - cdd(-JACOBIAN_STEP * np.eye(3)[i])) / (2 * JACOBIAN_STEP) for i in range(3)])
    inverse = np.linalg.inv(t)
    cdd_to_cid = inverse / inverse.sum(axis=0, keepdims=True)
    train = training(fp, n.c)
    code, _ = balance.adx10(train[None])
    exposure = balance.exposure_of(code.reshape(-1, 3), cdd_to_cid)
    target = lab(train @ np.linalg.inv(AP0_TO_AP1).T)

    def matrix(p):
        top = p.reshape(2, 3)
        return np.vstack([top, 1.0 - top.sum(axis=0)])

    import aces_scan
    fit = least_squares(lambda p: (lab(exposure @ matrix(p)) - target).ravel(), aces_scan.EXP_TO_ACES[:2].ravel())
    return cdd_to_cid, matrix(fit.x)
