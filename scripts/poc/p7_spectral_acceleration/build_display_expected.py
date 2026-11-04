"""The final sRGB of the lab evaluator on one AP1 array, for the numeric tests of the film print kernels in Alcedo Studio.

Input: the reflectance table under build/tmp/p2/tables/, the profiles, and stock_catalog.json. Output: build/tmp/p7/product_resources/expected/display/, one array file per selection (form: build_product_resources.py). Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F3.
Machine rule: CPU only, one process, no GPU job.

Each file has four float32 arrays of shape (N, 3):

| Array | Content |
| ramp_ap1, ramp_srgb | A neutral ramp of -5 to +5 stops around 0.18 (241 values), and its sRGB. A row of fewer than 16 pixels has no image plane (rule 'no_image_plane_steps_on_ramps'). |
| chart_ap1, chart_srgb | 180 patches (5 exposures, 12 hues, 3 chroma values, some with negative AP1 values) and 3916 random colours with the distribution of check 'Compact table, display' of build_product_resources.py, and their sRGB. |

This script sets INHIBITION_STEPS_POINT to INHIBITION_STEPS_IMAGE, because the kernels of the product run rule 'inhibition_two_steps'. Under the balance light of a stock, the first amounts of a neutral are the fixed point of the inhibition, so this has no effect on its ramp. Under another light the layers differ on a neutral AP1 value, so it has an effect, as on the chart.
The selections are the expected selections of build_product_resources.py, and one negative with no inhibition (kodak_gold_200).
Reversal films (step P9, Alcedo Studio issue 654): each of the five films under the scene light 'reference', and the reversal expected selections of build_product_resources.py, through ReversalPreview (method 'light_table').
The files are reversal__<film>__<light>.bin. Astia 100F has no spread and no inhibition, and E100 has no inhibition.
Lab Scan (step P10, ROADMAP U92, Alcedo Studio issue 661): the ADX16 scan with rule 'adx_slope_match' (build_product_resources.scan_model: ScanPreview, reading 'print2383', timing 1; U93) as
ACES2065-1 before the display transform, in arrays ramp_aces and chart_aces in place of the sRGB arrays. The negatives of SCAN_EXPECTED_SELECTIONS, each under
SCAN_DISPLAY_LIGHTS of build_product_resources.py (reference, daylight, and two colour temperatures between grid nodes in the blend form of the product), with
the LAD aim off and on. The files are scan__<negative>__<light>__lad_<off|on>.bin, a blend light named cct<kelvin>. A scan model (its LAD offset) is built with the
default point steps, as the stored values of the resources; only its render uses the steps of the product.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_product_resources as bpr  # noqa: E402

mp = bpr.mp
fp = bpr.fp
OUTPUT = bpr.OUTPUT / "expected" / "display"
SELECTIONS = (*bpr.EXPECTED_SELECTIONS, ("kodak_gold_200", "kodak_2383", "reference"))
REVERSAL_SELECTIONS = tuple(dict.fromkeys((*((film, "reference") for film in mp.REVERSAL_ORDER), *bpr.REVERSAL_EXPECTED_SELECTIONS)))
CHART_SEED = 20261101
CHART_RANDOM_COLOURS = 3916
POINT_STEPS = fp.INHIBITION_STEPS_POINT  # the default, before main() sets the steps of the product


def neutral_ramp() -> np.ndarray:
    return np.outer(0.18 * 2.0 ** np.linspace(-5.0, 5.0, 241), np.ones(3)).astype(np.float32)


def chart() -> np.ndarray:
    patches = []
    for stops in (-3.0, -1.0, 0.0, 1.0, 3.0):
        for hue in np.deg2rad(np.arange(0.0, 360.0, 30.0)):
            for chroma in (0.3, 0.7, 1.2):
                patches.append([np.cos(hue + shift) for shift in (0.0, -2.0 * np.pi / 3.0, 2.0 * np.pi / 3.0)])
                patches[-1] = 0.18 * 2.0 ** stops * (1.0 + chroma * np.array(patches[-1]))
    colours = np.random.default_rng(CHART_SEED)
    random_colours = colours.uniform(-0.5, 1.0, (CHART_RANDOM_COLOURS, 3)) * 2.0 ** colours.uniform(-6.0, 5.0, (CHART_RANDOM_COLOURS, 1))
    return np.concatenate([np.array(patches), random_colours]).astype(np.float32)


def srgb_of(model: fp.FilmPreview, ap1: np.ndarray) -> np.ndarray:
    return np.asarray(model.render(np.ascontiguousarray(ap1[None], dtype=np.float32))[0][0], dtype=np.float32)


def main() -> int:
    fp.INHIBITION_STEPS_POINT = fp.INHIBITION_STEPS_IMAGE
    ramp, patches = neutral_ramp(), chart()
    for negative, paper, light in SELECTIONS:
        model = fp.FilmPreview(mp.film_options(mp.RenderSettings(negative=negative, print_material=paper, scene_light=light)))
        ramp_srgb, chart_srgb = srgb_of(model, ramp), srgb_of(model, patches)
        if not np.isfinite(ramp_srgb).all() or not np.isfinite(chart_srgb).all():
            raise FloatingPointError(f"{negative} on {paper} under {light}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"{negative}__{paper}__{light}.bin", {"ramp_ap1": ramp, "ramp_srgb": ramp_srgb, "chart_ap1": patches, "chart_srgb": chart_srgb},
                         {"negative": negative, "print_material": paper, "scene_light": light, "lab_commit": bpr.lab_commit()})
        print(f"{negative} on {paper} under {light}: {len(ramp)} ramp values, {len(patches)} chart colours", flush=True)
    for film, light in REVERSAL_SELECTIONS:
        model = bpr.rf.ReversalPreview(bpr.reversal_options(film, light))
        ramp_srgb, chart_srgb = srgb_of(model, ramp), srgb_of(model, patches)
        if not np.isfinite(ramp_srgb).all() or not np.isfinite(chart_srgb).all():
            raise FloatingPointError(f"reversal {film} under {light}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"reversal__{film}__{light}.bin", {"ramp_ap1": ramp, "ramp_srgb": ramp_srgb, "chart_ap1": patches, "chart_srgb": chart_srgb},
                         {"reversal": film, "scene_light": light, "lab_commit": bpr.lab_commit()})
        print(f"reversal {film} under {light}: {len(ramp)} ramp values, {len(patches)} chart colours", flush=True)
    for negative in dict.fromkeys(negative for negative, _ in bpr.SCAN_EXPECTED_SELECTIONS):
        for light in bpr.SCAN_DISPLAY_LIGHTS:
            for lad in (False, True):
                # The LAD offset is a stored value of the resources, made with the default steps; the render uses the steps of the product.
                fp.INHIBITION_STEPS_POINT = POINT_STEPS
                model = bpr.scan_expected_model(negative, light, lad)
                fp.INHIBITION_STEPS_POINT = fp.INHIBITION_STEPS_IMAGE
                ramp_aces, chart_aces = (np.asarray(bpr.scan_aces(model, values[None])[0], dtype=np.float32) for values in (ramp, patches))
                if not np.isfinite(ramp_aces).all() or not np.isfinite(chart_aces).all():
                    raise FloatingPointError(f"scan {negative} under {light}: the output is not finite")
                label = bpr.scan_light_label(light)
                metadata = {"negative": negative, "print_material": bpr.LAB_SCAN["id"], "scene_light": label, "lad_aim": lad, "lab_commit": bpr.lab_commit()}
                if not isinstance(light, str):
                    a, b, w = bpr.grid_blend(light)
                    metadata.update({"kelvin": light, "node_a": a, "node_b": b, "share_of_b": w})
                bpr.write_arrays(OUTPUT / f"scan__{negative}__{label}__lad_{'on' if lad else 'off'}.bin", {"ramp_ap1": ramp, "ramp_aces": ramp_aces, "chart_ap1": patches, "chart_aces": chart_aces}, metadata)
                print(f"scan {negative} under {label}, LAD aim {'on' if lad else 'off'}: {len(ramp)} ramp values, {len(patches)} chart colours", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
