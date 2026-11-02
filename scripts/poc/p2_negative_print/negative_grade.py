"""Rule 'negative_show_grade': a fixed creative grade of the negative record of a tungsten stock, before the print table.

Input: the negative record (dye amounts, rule 'dye_amount_curves') and the record of an 18 % grey under the scene light of the model. Output: the graded record, as float32. Step: P7, ROADMAP U82 to U84. Only the tungsten stocks of NEGATIVE_GRADE_STOCKS of mvp_pipeline.py, on print material cine_look, have this rule.
Practice: a DI grades the scanned negative in density and then applies the print transform. This step has that place in the chain. All constants are creative choices with no measurement. They are not a measurement of a stock, and they do not stand for a chemical process.
The operation reads no statistic of a frame. One part is spatial (ROADMAP U85): the colours where green or blue leads are found on a blurred record, so the noise of one channel of a pixel does not move the density of the other channels. On a record, more density of a layer prints as more of the colour of that layer: red, green, or blue.
"""

from __future__ import annotations

import numpy as np

CHROMA_SCALE = 0.88
SHADOW_RANGE = (-0.05, 0.40)  # record below the grey: no weight, then full weight, by a smoothstep
SHADOW_CHROMA_LOSS = 0.35
SHADOW_OFFSET = np.array([-0.035, 0.02, 0.05])  # cool shadows with a small olive lean
HIGHLIGHT_RANGE = (0.35, 0.95)  # record above the grey
HIGHLIGHT_CHROMA_LOSS = 0.22
COOL_CHROMA_LOSS = 0.45  # a colour where green or blue leads: the emitters of signs lose their electric look
COOL_DENSITY_LOSS = 0.45  # the same colours print darker, as a dense subtractive colour does; red and yellow keep their colour


def _smoothstep(low: float, high: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - low) / (high - low), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def negative_grade(record: np.ndarray, grey: np.ndarray, soft_record: np.ndarray | None = None) -> np.ndarray:
    """The steps of the rule, in float64. record: (..., 3). grey: (3,). soft_record: the blurred record of the same shape; None: the record, as on a test ramp with no image plane."""
    difference = np.asarray(record, dtype=np.float64) - grey
    level = difference.mean(axis=-1, keepdims=True)
    colour = difference - level
    shadow = _smoothstep(*SHADOW_RANGE, -level)
    highlight = _smoothstep(*HIGHLIGHT_RANGE, level)
    soft = colour
    if soft_record is not None:
        soft = np.asarray(soft_record, dtype=np.float64) - grey
        soft = soft - soft.mean(axis=-1, keepdims=True)
    green_lead = np.maximum(soft[..., 1] - np.maximum(soft[..., 0], soft[..., 2]), 0.0)
    blue_lead = np.maximum(soft[..., 2] - np.maximum(soft[..., 0], soft[..., 1]), 0.0)
    cool_lead = (green_lead + blue_lead)[..., None]
    colour = colour * CHROMA_SCALE * (1.0 - SHADOW_CHROMA_LOSS * shadow) * (1.0 - HIGHLIGHT_CHROMA_LOSS * highlight)
    colour = colour - COOL_CHROMA_LOSS * cool_lead * colour
    graded = level + colour + shadow * SHADOW_OFFSET - COOL_DENSITY_LOSS * cool_lead
    return np.maximum(graded + grey, 0.0).astype(np.float32)
