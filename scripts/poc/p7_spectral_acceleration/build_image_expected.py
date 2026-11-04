"""The final sRGB of the lab evaluator on one AP1 array at full size, for test FilmPrintImageMatchesLab of Alcedo Studio.

Input: one RAW file (first argument; the plan uses _DSC8148.ARW at 6000 pixels), the reflectance table under build/tmp/p2/tables/, the profiles, and stock_catalog.json. Output: build/tmp/p7/product_resources/expected/image/ (form: build_product_resources.py). Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F4.
Machine rule: CPU only, one process, no GPU job. The arrays take about 290 MB per file on the disk and about 1 GB of memory.

| File | Arrays | Content |
| ap1.bin | ap1, (rows, columns, 3) | The AP1 array after the product grade, as check_fast_image_steps.py makes it. |
| <selection>.bin | srgb, (rows, columns, 3) | Its sRGB through the image-plane rules of the lab, with all sliders at their defaults. |

The selections are the expected selections of build_product_resources.py, with rule 'foliage_spectra', as in the product resources.
Reversal films (step P9, Alcedo Studio issue 654): each of the five films under the scene light 'reference', through ReversalPreview (method 'light_table'), with all sliders at their defaults. The files are reversal__<film>__reference.bin.
Lab Scan (step P10, Alcedo Studio issue 661): the scan expected selections of build_product_resources.py through method 'chart_scan' of the viewer with all controls at
their defaults. The files are scan__<negative>__<light>.bin.
"""

from __future__ import annotations

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


def read_ap1(path: Path) -> np.ndarray:
    """Array 'ap1' of a file of write_arrays."""
    import json
    import struct

    data = path.read_bytes()
    if data[:8] != bpr.MAGIC:
        raise ValueError(f"{path}: not an array file")
    length = struct.unpack("<Q", data[8:16])[0]
    entry = json.loads(data[16:16 + length])["arrays"]["ap1"]
    return np.frombuffer(data, dtype=np.dtype("<" + entry["type"]), count=int(np.prod(entry["shape"])), offset=16 + length + entry["offset"]).reshape(entry["shape"])


def options_of(negative: str, paper: str, light: str) -> fp.FilmOptions:
    return mp.film_options(mp.RenderSettings(negative=negative, print_material=paper, scene_light=light))


def main() -> int:
    # Option --scan-only: only the Lab Scan files; the ap1.bin and the other files of an earlier run stay (the same RAW file gives the same AP1).
    scan_only = "--scan-only" in sys.argv
    arguments = [a for a in sys.argv[1:] if a != "--scan-only"]
    if len(arguments) != 1:
        print("usage: build_image_expected.py RAW_FILE [--scan-only]", file=sys.stderr)
        return 2
    default = mp.RenderSettings()
    first = fp.FilmPreview(options_of(*bpr.EXPECTED_SELECTIONS[0]))
    ap1, _ = mp.decode_raw(Path(arguments[0]), first.c, LONG_EDGE)
    graded = np.ascontiguousarray(fk.product_grade(ap1, float(default.exposure_ev), float(default.contrast), float(default.saturation)), dtype=np.float32)
    commit = bpr.lab_commit()
    if not scan_only:
        bpr.write_arrays(OUTPUT / "ap1.bin", {"ap1": graded}, {"source": Path(arguments[0]).name, "lab_commit": commit})
    elif not np.array_equal(read_ap1(OUTPUT / "ap1.bin"), graded):
        raise ValueError("--scan-only: the AP1 of this RAW file differs from ap1.bin of the earlier run")
    for negative, paper, light in (() if scan_only else bpr.EXPECTED_SELECTIONS):
        srgb = np.asarray(fp.FilmPreview(options_of(negative, paper, light)).render(graded)[0], dtype=np.float32)
        if not np.isfinite(srgb).all():
            raise FloatingPointError(f"{negative} on {paper} under {light}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"{negative}__{paper}__{light}.bin", {"srgb": srgb}, {"negative": negative, "print_material": paper, "scene_light": light, "lab_commit": commit})
        print(f"{negative} on {paper} under {light}: {srgb.shape}", flush=True)
    for film in (() if scan_only else mp.REVERSAL_ORDER):
        srgb = np.asarray(bpr.rf.ReversalPreview(bpr.reversal_options(film, "reference")).render(graded)[0], dtype=np.float32)
        if not np.isfinite(srgb).all():
            raise FloatingPointError(f"reversal {film}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"reversal__{film}__reference.bin", {"srgb": srgb}, {"reversal": film, "scene_light": "reference", "lab_commit": commit})
        print(f"reversal {film}: {srgb.shape}", flush=True)
    for negative, light in bpr.SCAN_EXPECTED_SELECTIONS:
        srgb = np.asarray(bpr.scan_model(negative, light).render(graded)[0], dtype=np.float32)
        if not np.isfinite(srgb).all():
            raise FloatingPointError(f"scan {negative} under {light}: the output is not finite")
        bpr.write_arrays(OUTPUT / f"scan__{negative}__{light}.bin", {"srgb": srgb}, {"negative": negative, "print_material": bpr.LAB_SCAN["id"], "scene_light": light, "lab_commit": commit})
        print(f"scan {negative} under {light}: {srgb.shape}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
