"""Target strength of the display-referred grain of Alcedo Studio (step P15, plan G0 step 6).

Input: results/p15_film_grain/stock_grain.json and layer_correlation.json, and the film print of the viewer:
KODAK VISION3 250D 5207 on KODAK ENDURA Premier, scene light 'reference'.
Output: results/p15_film_grain/post_path_target.json.

Product rule (plan, section 3.5): at 35mm and mid grey, the Film Grain of the methods with no negative (ACES 2.0,
OpenDRT) at strength 1 gives the display standard deviation that the grain in the negative gives through the film
print. The value here is for the 48 um aperture; the product scales both paths by the same pixel factor
I(sigma_c, p) * sqrt(A_48), so the ratio holds at every pitch.

Method: the negative record of an 18 % grey AP1 input (FilmPreview.negative_image, one pixel, so no image-plane
step), the dye-amount noise of each layer at that record (stock_grain.json) with the layer correlation R
(layer_correlation.json), and the Jacobian of the display output (print table, display matrix, display finish, sRGB
encoding) by central differences of 1e-4 in each dye amount. Output: the standard deviation of each display channel,
encoded and linear, and the correlation of the display channels.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

GRAIN = ROOT / "results" / "p15_film_grain" / "stock_grain.json"
CORRELATION = ROOT / "results" / "p15_film_grain" / "layer_correlation.json"
OUTPUT = ROOT / "results" / "p15_film_grain" / "post_path_target.json"
STEP = 1e-4
GREY = 0.18


def main() -> int:
    fp = mp.fp
    settings = mp.RenderSettings(negative="kodak_5207", print_material="kodak_endura_premier", scene_light="reference")
    settings.validate()
    model = fp.FilmPreview(mp.film_options(settings))
    record, _ = model.negative_image(np.full((1, 1, 3), GREY, dtype=np.float32))
    a0 = record[0, 0].astype(np.float64)

    def display(a: np.ndarray, encoded: bool) -> np.ndarray:
        rgb = fp.fk.print_display(a.reshape(1, 1, 3).astype(np.float32), model._print_f32, model._grid_start, model._grid_step, model.xyz_to_display)
        o = model.options
        out, _, _ = fp.fk.finish_display(rgb, bool(o.gamut_compress), np.array(o.gamut_threshold), np.array(o.gamut_limit), float(o.gamut_power))
        out = out[0, 0].astype(np.float64)
        if encoded:
            return out
        return np.where(out <= 0.04045, out / 12.92, ((out + 0.055) / 1.055) ** 2.4)

    grain = json.loads(GRAIN.read_text(encoding="utf-8"))["stocks"]["kodak_5207"]["layer"]
    s = np.array([np.interp(a0[k], grain["amount"][k], grain["sigma_amount"][k]) for k in range(3)])
    r = json.loads(CORRELATION.read_text(encoding="utf-8"))["layer_correlation"]
    rm = np.array([[1, r["rg"], r["rb"]], [r["rg"], 1, r["gb"]], [r["rb"], r["gb"], 1]])
    cov_a = np.diag(s) @ rm @ np.diag(s)
    out = {"selection": ["kodak_5207", "kodak_endura_premier", "reference"], "grey_ap1": GREY, "record": a0.round(6).tolist(),
           "sigma_amount_48": s.round(7).tolist(), "aperture": "48 um circle"}
    for encoded in (True, False):
        jac = np.zeros((3, 3))
        for k in range(3):
            up, down = a0.copy(), a0.copy()
            up[k] += STEP
            down[k] -= STEP
            jac[:, k] = (display(up, encoded) - display(down, encoded)) / (2 * STEP)
        cov = jac @ cov_a @ jac.T
        std = np.sqrt(np.diag(cov))
        value = display(a0, encoded)
        key = "encoded" if encoded else "linear"
        out[key] = {"display_value": value.round(6).tolist(), "display_sigma_48": std.round(7).tolist(),
                    "relative_sigma_48": (std / value).round(6).tolist(),
                    "display_correlation_rg_gb_rb": [round(float(cov[0, 1] / (std[0] * std[1])), 4), round(float(cov[1, 2] / (std[1] * std[2])), 4),
                                                     round(float(cov[0, 2] / (std[0] * std[2])), 4)]}
    print(json.dumps(out, indent=1))
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
