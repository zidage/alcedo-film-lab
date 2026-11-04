"""Rule 'scan_print_colour' of Lab Scan (step P10, ROADMAP U95): a correction of hue and chroma at fixed luminance after the ADX to ACES transform.

Why (U94): the Academy ADX to ACES transform assumes the sensitivities of an average motion picture negative. On the stocks of the model it turns
blue to cyan, orange to red, and magenta to red, and it loses chroma in green; even the best 3x3 from the true layer exposure of a stock keeps orange
toward red (salmon), because the sensitivities of a negative are not colorimetric. The print of the stock (dyes and paper) renders these colours
well, so the scan takes its hue from the print.

Form: in Oklab of XYZ (D65; Bradford from the white of each side), normalized to Y = YN, so only a and b move; the output keeps the Y of the input,
so the tone of the scan stays. Relative to the scan grey of the scene light (aces / grey * 0.18), so the cast of the LAD aim off stays.
A table over the hue (HUE_BINS) and the chroma (CHROMA_NODES) of the scan colour holds a hue shift and a chroma ratio, bilinear in hue (periodic)
and chroma. It is fitted on TRAINING colours (hues of linear Rec. 709 at the luminance of the grey, 8 saturations): per cell a Gaussian-weighted
mean of the shift and the ratio from the scan colour to the target; a cell with no sample takes the next lower chroma node of its hue.
Targets (option of ScanPreview 'colour'):
- 'print_hue_scene_chroma' (U95, user choice of 2026-11-04 for the GUI check): hue of the print, chroma of the scene.
- 'print_hue_scan_chroma': hue of the print, chroma of the scan.  'scene_hue_scan_chroma': hue of the scene, chroma of the scan.
- 'print_hue_print_chroma': hue and chroma of the print (U95 first form; the user found it too strong).
The hue of the print: the hue shift that the print of the stock gives each training colour against the scene, added to the scene hue.
The print: rule 'scan_colour_print_by_medium' of mvp_pipeline.py (a cine negative on Kodak 2383, a photo negative on Kodak Endura Premier), under
the scene light of the scan.
"""

from __future__ import annotations

import numpy as np

YN = 0.18
HUE_BINS = 72
CHROMA_NODES = np.array([0.0, 0.02, 0.04, 0.07, 0.10, 0.14, 0.19, 0.25, 0.32])
SATURATIONS = (0.06, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)
SHIFT_LIMIT = 0.6  # radians
GAIN_LIMITS = (0.4, 2.5)
COLOURS = ("academy", "print_hue_scene_chroma", "print_hue_scan_chroma", "scene_hue_scan_chroma", "print_hue_print_chroma")
M1 = np.array([[0.8189330101, 0.3618667424, -0.1288597137], [0.0329845436, 0.9293118715, 0.0361456387], [0.0482003018, 0.2643662691, 0.6338517070]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])
AP0_TO_XYZ = np.array([[0.9525523959, 0.0, 0.0000936786], [0.3439664498, 0.7281660966, -0.0721325464], [0.0, 0.0, 1.0088251844]])
REC709_LUMINANCE = np.array([0.2126, 0.7152, 0.0722])


def oklab(xyz: np.ndarray) -> np.ndarray:
    return np.cbrt(np.maximum(xyz @ M1.T, 0.0)) @ M2.T


def oklab_inverse(lab: np.ndarray) -> np.ndarray:
    return ((lab @ np.linalg.inv(M2).T) ** 3) @ np.linalg.inv(M1).T


def chroma_hue(xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lab = oklab(xyz / np.maximum(xyz[..., 1:2], 1e-12) * YN)
    return np.hypot(lab[..., 1], lab[..., 2]), np.arctan2(lab[..., 2], lab[..., 1])


def wrap(angle: np.ndarray) -> np.ndarray:
    return (angle + np.pi) % (2 * np.pi) - np.pi


class ScanColour:
    """The table of rule 'scan_print_colour' for one scan model and one print model."""

    def __init__(self, fp, scan, printer, colour: str) -> None:
        if colour not in COLOURS or colour == "academy":
            raise ValueError(f"unknown scan colour {colour!r}")
        self.colour = colour
        d60 = AP0_TO_XYZ.sum(axis=1)
        self.ap0_to_xyz = fp.bradford_matrix(d60 / d60[1], fp.XYZ_D65) @ AP0_TO_XYZ
        self.xyz_to_ap0 = np.linalg.inv(self.ap0_to_xyz)
        c = scan.negative.c
        ap1_to_ap0 = np.linalg.inv(np.array([[1.4514393161, -0.2365107469, -0.2149285693], [-0.0765537734, 1.1762296998, -0.0996759264], [0.0083161484, -0.0060324498, 0.9977163014]]))
        rec709_to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3)) @ np.linalg.inv(fp.XYZ_TO_REC709)
        hue = np.arange(HUE_BINS * 2) * 6.0 / (HUE_BINS * 2)
        channels = np.stack([np.clip(np.abs(((hue + s) % 6.0) - 3.0) - 1.0, 0.0, 1.0) for s in (0.0, 4.0, 2.0)], axis=-1)
        rgb = np.concatenate([1.0 - s + s * channels for s in SATURATIONS])
        train = (rgb / (rgb @ REC709_LUMINANCE)[:, None] * 0.18 @ rec709_to_ap1.T).astype(np.float32)
        self.grey = scan.to_aces(scan.adx10(np.full((1, 1, 3), 0.18, dtype=np.float32))[0].reshape(-1, 3))[0]
        scan_aces = scan.to_aces(scan.adx10(train[None])[0].reshape(-1, 3))
        c_scene, h_scene = chroma_hue((train @ ap1_to_ap0.T) @ self.ap0_to_xyz.T)
        c_scan, h_scan = chroma_hue((scan_aces / self.grey * 0.18) @ self.ap0_to_xyz.T)
        density, _ = printer.negative_image(train[None])
        c_print, h_print = chroma_hue(printer.display_linear(printer.print_xyz(density))[0] @ np.linalg.inv(fp.XYZ_TO_REC709).T)
        target_h = h_scene + wrap(h_print - h_scene) if colour.startswith("print_hue") else h_scene
        target_c = {"scene": c_scene, "scan": c_scan, "print": c_print}[colour.rsplit("_", 2)[1]]
        self.shift, self.gain = self._fit(c_scan, h_scan, target_c, target_h)

    @staticmethod
    def _fit(c_scan, h_scan, c_target, h_target) -> tuple[np.ndarray, np.ndarray]:
        dh = wrap(h_target - h_scan)
        ratio = c_target / np.maximum(c_scan, 1e-6)
        shift = np.full((HUE_BINS, len(CHROMA_NODES)), np.nan)
        gain = np.full((HUE_BINS, len(CHROMA_NODES)), np.nan)
        step = 2 * np.pi / HUE_BINS
        for i in range(HUE_BINS):
            dist = wrap(h_scan - (i * step - np.pi))
            for j, node in enumerate(CHROMA_NODES[1:], start=1):
                w = np.exp(-0.5 * (dist / step) ** 2 - 0.5 * ((c_scan - node) / max(0.012, 0.25 * node)) ** 2)
                if w.sum() >= 1e-3:
                    shift[i, j], gain[i, j] = np.sum(w * dh) / w.sum(), np.sum(w * ratio) / w.sum()
                elif j > 1:
                    shift[i, j], gain[i, j] = shift[i, j - 1], gain[i, j - 1]
        if np.isnan(shift[:, 1]).any():
            raise ValueError("rule scan_print_colour: a hue of the first chroma node has no training colour")
        shift[:, 0], gain[:, 0] = shift[:, 1], 1.0
        return np.clip(shift, -SHIFT_LIMIT, SHIFT_LIMIT), np.clip(gain, *GAIN_LIMITS)

    @staticmethod
    def _lookup(table: np.ndarray, c: np.ndarray, h: np.ndarray) -> np.ndarray:
        pos = (h + np.pi) / (2 * np.pi) * HUE_BINS
        i0 = np.floor(pos).astype(int) % HUE_BINS
        i1 = (i0 + 1) % HUE_BINS
        t = pos - np.floor(pos)
        j = np.clip(np.searchsorted(CHROMA_NODES, c) - 1, 0, len(CHROMA_NODES) - 2)
        u = np.clip((c - CHROMA_NODES[j]) / (CHROMA_NODES[j + 1] - CHROMA_NODES[j]), 0.0, 1.0)

        def row(i):
            return table[i, j] * (1 - u) + table[i, j + 1] * u
        return row(i0) * (1 - t) + row(i1) * t

    def apply(self, aces: np.ndarray) -> np.ndarray:
        shape = aces.shape
        xyz = (np.asarray(aces, dtype=np.float64).reshape(-1, 3) / self.grey * 0.18) @ self.ap0_to_xyz.T
        y = xyz[:, 1].copy()
        ok = y > 1e-6
        lab = oklab(xyz[ok] / y[ok, None] * YN)
        c, h = np.hypot(lab[:, 1], lab[:, 2]), np.arctan2(lab[:, 2], lab[:, 1])
        h2, c2 = h + self._lookup(self.shift, c, h), c * self._lookup(self.gain, c, h)
        new = oklab_inverse(np.stack([lab[:, 0], c2 * np.cos(h2), c2 * np.sin(h2)], axis=-1))
        xyz[ok] = new / np.maximum(new[:, 1:2], 1e-12) * y[ok, None]
        return ((xyz @ self.xyz_to_ap0.T) * self.grey / 0.18).reshape(shape)
