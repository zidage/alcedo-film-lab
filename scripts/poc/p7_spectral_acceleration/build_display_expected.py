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
Negative Scan (step P14, Alcedo Studio issues 661 and 664): NegativeScanPreview of the viewer (build_product_resources.scan_model) as linear AP1 before the
display transform (stage e of negative_scan.py), in arrays ramp_linear and chart_linear in place of the sRGB arrays. The negatives of SCAN_EXPECTED_SELECTIONS,
each under SCAN_DISPLAY_LIGHTS of build_product_resources.py (reference, daylight, and two colour temperatures between grid nodes: the model of the blend
light, whose D_aim and light axis agree with the blend of the stored values of the resources to 1e-9), with auto colour off and 'neutral'. The ramp and the
chart are each one frame of one row, as the GPU tests render them, so rule frame_auto_colour reads that row: arrays ramp_shift and chart_shift (3, log10)
hold its shift, ramp_prescan and chart_prescan its prescan, and light_axis the light axis of the selection. The files are
scan__<negative>__<light>__auto_<off|neutral>.bin, a blend light named cct<kelvin>. A scan model (D_aim, the light axis, gamma) is built with the default
point steps, as the stored values of the resources; only its render uses the steps of the product.
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
SCAN_AUTO_MODES = ("off", "neutral")


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
            for auto in SCAN_AUTO_MODES:
                # D_aim, the light axis and gamma are stored values of the resources, made with the default steps; the render uses the steps of the product.
                fp.INHIBITION_STEPS_POINT = POINT_STEPS
                model = bpr.scan_expected_model(negative, light)
                fp.INHIBITION_STEPS_POINT = fp.INHIBITION_STEPS_IMAGE
                (ramp_linear, ramp_shift, ramp_prescan), (chart_linear, chart_shift, chart_prescan) = (bpr.scan_linear(model, values[None], auto) for values in (ramp, patches))
                if not np.isfinite(ramp_linear).all() or not np.isfinite(chart_linear).all():
                    raise FloatingPointError(f"scan {negative} under {light}: the output is not finite")
                label = bpr.scan_light_label(light)
                metadata = {"negative": negative, "print_material": bpr.NEGATIVE_SCAN["id"], "scene_light": label, "auto": auto, "lab_commit": bpr.lab_commit()}
                if not isinstance(light, str):
                    a, b, w = bpr.grid_blend(light)
                    metadata.update({"kelvin": light, "node_a": a, "node_b": b, "share_of_b": w})
                bpr.write_arrays(OUTPUT / f"scan__{negative}__{label}__auto_{auto}.bin",
                                 {"ramp_ap1": ramp, "ramp_linear": ramp_linear[0], "ramp_shift": ramp_shift, "ramp_prescan": ramp_prescan, "chart_ap1": patches,
                                  "chart_linear": chart_linear[0], "chart_shift": chart_shift, "chart_prescan": chart_prescan, "light_axis": np.asarray(model.light_axis, dtype=np.float64)}, metadata)
                print(f"scan {negative} under {label}, auto {auto}: shift ramp {ramp_shift}, chart {chart_shift}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
