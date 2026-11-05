"""Rule 'generic_scan' of Lab Scan (step P10, ROADMAP U98): one scanner setup per process for every stock, in the form of the Academy ADX to
ACES transform.

Why (U98): the Academy transform is one set of numbers for an average motion picture negative, so each negative shows how it differs from that
average. Its numbers do not describe the negatives of the model (U94: blue to cyan, orange to red). Rule 'adx_stock_numbers' (U96) derives them per
stock and fits each stock to the scene, so it undoes the colour of each stock; rule 'adx_slope_match' (U93) gives each stock the green slope in red
and blue, so it undoes the crossover of each stock. This rule keeps the Academy method and derives its numbers once, from an average negative of the
model, as rule 'fixed_scan_slope' (U89) does for the tone of method chart_scan.

One setup per process (U98): the Academy transform is defined for motion picture negatives (ECN-2), and a photo lab sets its scanner for colour
negatives of process C-41. One setup from all eight stocks of rule fixed_scan_slope gives the cine stocks the slopes of the photo stocks (red and
blue 10 % lower against green): on the sweep 5207 turns magenta at -4 stops and green at +4 (green axis -5.7 and +5.1 dE' of CAM16-UCS), and on the
Film Analyzer chart it keeps 0.85 of the chroma of the scene. So POOLS has one pool per medium of the catalog: the four Vision3 stocks, and the six
photo stocks of rule fixed_scan_slope. A stock takes the setup of its medium.

Form, from the stocks of a pool, each under its balance light (D55 or T3200) with the 18 % grey on the LAD aim, read in the printing density of the
scan:
- the channel scale: s_c = 0.92 * mean slope_G / mean slope_c, where slope is the printing density per stop of the 18 % grey (central difference at
  2^-1 and 2^+1 of 0.18), the mean over the pool. It is the scale of rule adx_slope_match for the average negative, and the same for every stock of
  the medium.
- the numbers: rule derive_pooled of scan_unbuild.py on the pool with that scale: CDD_TO_CID of the mean Jacobian at the grey, EXP_TO_ACES fitted on
  the training colours of all the stocks of the pool together.
A stock then differs from the average negative of its medium by its curves, its layer slopes (crossover), its dyes, its sensitivities, and its
interlayer inhibition. Only the offset of the scan depends on the stock (the LAD aim or rule stock_balance), as a scanner balances each film or frame.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

import scan_unbuild

POOLS = {"cine": ("kodak_5203", "kodak_5207", "kodak_5213", "kodak_5219"),
         "photo": ("kodak_portra_400", "kodak_portra_160", "kodak_portra_800", "kodak_ektar_100", "kodak_gold_200", "fuji_c200")}
GREEN_SCALE = 0.92  # equation 2 of ST 2065-3


def grey_slope(scan) -> np.ndarray:
    """Printing density per stop of the 18 % grey of the scene light of a ScanPreview."""
    light = scan.negative.options.scene_light
    return (scan.grey_apd(light, 0.36) - scan.grey_apd(light, 0.09)) / 2.0


def derive(fp, make_scan: Callable[[str, np.ndarray | None], object], pool: tuple[str, ...]) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    """The scale and (CDD_TO_CID, EXP_TO_ACES) of a pool. make_scan(stock, fixed_scale) gives the ScanPreview of a stock under its balance light,
    LAD aim at that light (timing 1); fixed_scale None is equation 2."""
    slopes = np.array([grey_slope(make_scan(stock, None)) for stock in pool])
    mean = slopes.mean(axis=0)
    scale = GREEN_SCALE * mean[1] / mean
    balances = [make_scan(stock, scale) for stock in pool]
    return scale, scan_unbuild.derive_pooled(fp, balances)
