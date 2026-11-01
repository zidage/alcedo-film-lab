"""The final sRGB of the lab evaluator on one AP1 array at full size, for test FilmPrintImageMatchesLab of Alcedo Studio.

Input: one RAW file (first argument; the plan uses _DSC8148.ARW at 6000 pixels), the reflectance table under build/tmp/p2/tables/, the profiles, and stock_catalog.json. Output: build/tmp/p7/product_resources/expected/image/ (form: build_product_resources.py). Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F4.
Machine rule: CPU only, one process, no GPU job. The arrays take about 290 MB per file on the disk and about 1 GB of memory.

| File | Arrays | Content |
| ap1.bin | ap1, (rows, columns, 3) | The AP1 array after the product grade, as check_fast_image_steps.py makes it. |
| <selection>.bin | srgb, (rows, columns, 3) | Its sRGB through the image-plane rules of the lab, with all sliders at their defaults. |

The selections are the expected selections of build_product_resources.py. The product resources have no rule 'foliage_spectra', so this script sets that option to False when the option exists.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_product_resources as bpr  # noqa: E402

mp = bpr.mp
fp = bpr.fp
fk = fp.fk
OUTPUT = bpr.OUTPUT / "expected" / "image"
LONG_EDGE = 6000


def options_of(negative: str, paper: str, light: str) -> fp.FilmOptions:
    options = mp.film_options(mp.RenderSettings(negative=negative, print_material=paper, scene_light=light))
    if any(field.name == "foliage" for field in dataclasses.fields(options)):
        options = dataclasses.replace(options, foliage=False)
    return options


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_image_expected.py RAW_FILE", file=sys.stderr)
        return 2
    default = mp.RenderSettings()
    first = fp.FilmPreview(options_of(*bpr.EXPECTED_SELECTIONS[0]))
    ap1, _ = mp.decode_raw(Path(sys.argv[1]), first.c, LONG_EDGE)
    graded = np.ascontiguousarray(fk.product_grade(ap1, float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32)
    commit = bpr.lab_commit()
    bpr.write_arrays(OUTPUT / "ap1.bin", {"ap1": graded}, {"source": Path(sys.argv[1]).name, "lab_commit": commit})
    for negative, paper, light in bpr.EXPECTED_SELECTIONS:
        srgb = np.asarray(fp.FilmPreview(options_of(negative, paper, light)).render(graded)[0], dtype=np.float32)
        if not np.isfinite(srgb).all():
            raise FloatingPointError(f"{negative} on {paper} under {light}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"{negative}__{paper}__{light}.bin", {"srgb": srgb}, {"negative": negative, "print_material": paper, "scene_light": light, "lab_commit": commit})
        print(f"{negative} on {paper} under {light}: {srgb.shape}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
