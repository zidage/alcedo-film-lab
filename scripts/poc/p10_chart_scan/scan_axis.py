"""Rule 'untimed_axis_academy' of Lab Scan (step P10, ROADMAP U97): with the LAD aim off, the neutral axis of the scan comes from the untimed scan
through the Academy numbers, and the colours about that axis come from the stock numbers (rule adx_stock_numbers) of the same scan timed to the
scene light.

Why (U97, scan_appearance.py, CAM16-UCS of the display): the Academy numbers and the stock numbers differ in two separate things.
- The neutral axis. Kodak 5219 under the as-shot light of a night scene (4138 K) against its balance light T3200: the Academy scan has the cast
  +9.6 on the colour temperature axis and +3.8 on the green axis (cyan blue), the stock numbers +12.3 and +1.0 (along the colour temperature axis,
  as a change of the white balance of a digital photo: 89 % of the change of the stock numbers is a white balance, 71 % of the Academy numbers).
- The colours. In daylight on a daylight stock (no cast), the Academy numbers turn the hues with a pattern of period 180 degrees (Portra 400: rms
  12.1 degrees of hue in that part, 4.3 in the rest): blue toward cyan with yellow and orange toward red, and they lower the colourfulness (0.82).
  The stock numbers keep the hues (rms 3.5) and the colourfulness (0.98).
A 3x3 matrix turns a colour and its complement the same way (M(-v) = -M(v)), and the cast of a light that is bluer than the balance light lies along
the blue colours, so numbers that give the cyan-blue cast also turn yellow to red. No set of numbers of the Academy form gives both. The two parts are
separate in this rule: the axis (cast and tone per exposure) from the Academy scan, the colours from the stock numbers.

Form: a ramp of the 18 % grey of the scene light, STOPS. Per stop, the ACES2065-1 of the grey through the Academy numbers at the offset of the scan
(axis), and through the stock numbers at the offset with the grey of the scene light on the LAD aim (content). Gains in CAT16 cone space of ACES2065-1
(M16 of CAM16 on the XYZ of AP0): log(axis / content) per channel, over the log2 luminance of the content grey. A pixel: its ACES of the stock numbers
at the timed offset, then the gains at its luminance (linear in log2 luminance between ramp nodes, held at the ends). The grey ramp of the scan is
then the Academy one at every exposure.
"""

from __future__ import annotations

import numpy as np

STOPS = np.arange(-14.0, 14.01, 0.25)
AP0_TO_XYZ = np.array([[0.9525523959, 0.0, 0.0000936786], [0.3439664498, 0.7281660966, -0.0721325464], [0.0, 0.0, 1.0088251844]])
M16 = np.array([[0.401288, 0.650173, -0.051461], [-0.250268, 1.204414, 0.045854], [-0.002079, 0.048952, 0.953127]])
CONE = M16 @ AP0_TO_XYZ
CONE_INVERSE = np.linalg.inv(CONE)


class UntimedAxis:
    def __init__(self, scan, academy_cdd_to_cid: np.ndarray, academy_exp_to_aces: np.ndarray) -> None:
        import aces_scan

        o = scan.negative.options
        per_stop = aces_scan.ADX10_PER_STOP * scan.per_density / aces_scan.ADX10_PER_DENSITY
        timed = scan.code_lad - scan.grey_adx(o.scene_light) + scan.exposure_stops * per_stop
        self.scan = scan
        self.shift = timed - scan.offset
        codes = np.stack([scan.code(scan.grey_apd(o.scene_light, 0.18 * 2.0 ** e)) for e in STOPS])
        cdd = (np.clip(codes + scan.offset, 0.0, scan.code_max) - scan.code_dmin) / scan.per_density
        axis = aces_scan.cdd_to_aces(cdd, academy_cdd_to_cid, academy_exp_to_aces)
        content = scan.to_aces(np.clip(codes + timed, 0.0, scan.code_max))
        log_y = np.log2(np.maximum(content @ AP0_TO_XYZ[1], 1e-12))
        keep = np.concatenate([[True], np.diff(np.maximum.accumulate(log_y)) > 1e-6])
        self.log_y = log_y[keep]
        self.log_gain = np.log(np.maximum(axis @ CONE.T, 1e-12) / np.maximum(content @ CONE.T, 1e-12))[keep]

    def gains(self, log_y: np.ndarray) -> np.ndarray:
        return np.exp(np.stack([np.interp(log_y, self.log_y, self.log_gain[:, k]) for k in range(3)], axis=-1))

    def apply(self, code: np.ndarray) -> np.ndarray:
        """ACES2065-1 of code values of the scan (with its offset): the content of the stock numbers, timed, with the gains of the axis."""
        s = self.scan
        content = s.to_aces(np.clip(np.asarray(code, dtype=np.float64) + self.shift, 0.0, s.code_max))
        g = self.gains(np.log2(np.maximum(content @ AP0_TO_XYZ[1], 1e-12)))
        return ((content @ CONE.T) * g) @ CONE_INVERSE.T
