"""The neutral axis of the final print chain against the Rec709 film look LUTs of DaVinci Resolve.

Input: the profiles, the reflectance tables, and the LUTs of a local Resolve install. Output: results/p7_spectral_acceleration/neutral_axis.json. Step: P7, ROADMAP U75. Machine rule: CPU only, one process.

A LUT is an emulation with a neutral Cineon input, and not a measurement of a real print. So this is a record of the difference, with no limit on it. Comparison rule: a* and b* (CIELAB, D65) of a neutral ramp at the same L*, L* 10 to 85 in steps of 1: mean and largest distance in the a*b* plane. The model ramp is a 0.18 grey -6 to +6 stops, sRGB out. A LUT reads R = G = B, gamma 2.4 out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
LUTS = Path("C:/ProgramData/Blackmagic Design/DaVinci Resolve/Support/LUT/Film Looks")
RESULT = REPO_ROOT / "results" / "p7_spectral_acceleration" / "neutral_axis.json"
RGB_TO_XYZ = np.linalg.inv(fp.XYZ_TO_REC709)
L_STAR = np.arange(10.0, 86.0)
CASES = (("kodak_5207", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("kodak_5219", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("kodak_5213", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("kodak_5203", "kodak_2383", "Rec709 Kodak 2383 D65.cube"),
         ("fuji_eterna_500", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("kodak_portra_400", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("kodak_gold_200", "kodak_2383", "Rec709 Kodak 2383 D65.cube"), ("fuji_c200", "kodak_2383", "Rec709 Kodak 2383 D65.cube"),
         ("kodak_5207", "kodak_2393", "Rec709 Kodak 2383 D65.cube"), ("fuji_eterna_500", "fuji_3513di", "Rec709 Fujifilm 3513DI D65.cube"), ("kodak_5207", "fuji_3513di", "Rec709 Fujifilm 3513DI D65.cube"))


def lab_of_linear(rgb: np.ndarray) -> np.ndarray:
    ratio = (np.asarray(rgb) @ RGB_TO_XYZ.T) / RGB_TO_XYZ.sum(axis=1)
    f = np.where(ratio > (6 / 29) ** 3, np.cbrt(ratio), ratio / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def lut_axis(name: str) -> np.ndarray:
    rows, size = [], 0
    with (LUTS / name).open(encoding="utf-8") as stream:
        for line in stream:
            fields = line.split()
            if not fields or line[0] == "#":
                continue
            if fields[0] == "LUT_3D_SIZE":
                size = int(fields[1])
            elif len(fields) == 3 and fields[0][0].isdigit():
                rows.append([float(v) for v in fields])
    diagonal = np.asarray(rows)[[i * (1 + size + size * size) for i in range(size)]]
    return lab_of_linear(np.clip(diagonal, 0.0, 1.0) ** 2.4)


def model_axis(model: fp.FilmPreview) -> np.ndarray:
    ramp = np.outer(0.18 * 2.0 ** np.linspace(-6.0, 6.0, 289), np.ones(3)).astype(np.float32)[None]
    code = np.asarray(model.render(ramp)[0], dtype=np.float64)[0]
    return lab_of_linear(np.where(code <= 0.04045, code / 12.92, ((code + 0.055) / 1.055) ** 2.4))


def on_l_star(lab: np.ndarray) -> np.ndarray:
    order = np.argsort(lab[:, 0])
    return np.stack([np.interp(L_STAR, lab[order, 0], lab[order, k]) for k in (1, 2)], axis=1)


def main() -> int:
    record = {}
    for negative, material, lut in CASES:
        options = mp.film_options(mp.RenderSettings(negative=negative, print_material=material))
        model = fp.FilmPreview(options)
        axis, reference = model_axis(model), lut_axis(lut)
        ab = on_l_star(axis)
        distance = np.hypot(*(ab - on_l_star(reference)).T)
        record[f"{negative} on {material}"] = {"lut": lut, "printing_gain": model.printing_gain.tolist(), "display_white": options.display_white, "mean": float(distance.mean()), "largest": float(distance.max()), "top_l_star": float(axis[:, 0].max()),
                                               "a_b_at_l_star": {str(int(L)): ab[int(L - L_STAR[0])].round(2).tolist() for L in (10, 20, 30, 45, 60, 75, 85)}}
        print(negative, material, {k: round(v, 3) for k, v in record[f"{negative} on {material}"].items() if k in ("mean", "largest", "top_l_star")}, flush=True)
    RESULT.write_bytes((json.dumps(record, indent=1) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
