"""The final sRGB of the lab evaluator on one AP1 array at full size, for test FilmPrintImageMatchesLab of Alcedo Studio.

Input: one RAW file (first argument; the plan uses _DSC8148.ARW at 6000 pixels), the reflectance table under build/tmp/p2/tables/, the profiles, and stock_catalog.json. Output: build/tmp/p7/product_resources/expected/image/ (form: build_product_resources.py). Step: P7, ROADMAP U70. Film Print DRT Plan of Alcedo Studio, phase F4.
Machine rule: CPU only, one process, no GPU job. The arrays take about 290 MB per file on the disk and about 1 GB of memory.

| File | Arrays | Content |
| ap1.bin | ap1, (rows, columns, 3) | The AP1 array after the product grade, as check_fast_image_steps.py makes it. |
| <selection>.bin | srgb, (rows, columns, 3) | Its sRGB through the image-plane rules of the lab, with all sliders at their defaults. |

The selections are the expected selections of build_product_resources.py, without rule 'foliage_spectra' since schema 8 (U93), as in the product resources.
Reversal films (step P9, Alcedo Studio issue 654): each of the five films under the scene light 'reference', through ReversalPreview (method 'light_table'), with all sliders at their defaults. The files are reversal__<film>__reference.bin.
Negative Scan (step P14, Alcedo Studio issues 661 and 664): NegativeScanPreview of the viewer as linear AP1 before the display transform (array 'linear' in
place of 'srgb'), on SCAN_IMAGE_SELECTIONS: the negatives of the scan expected selections of build_product_resources.py, each under its SCAN_DISPLAY_LIGHTS
(reference, daylight, and two colour temperatures between grid nodes), with auto colour off and 'neutral': 32 files of about 290 MB. Each file also holds
'shift' (3, the log10 shift of rule frame_auto_colour on the full frame; 0 with auto off), 'prescan' (the x frame reduced by area to a long edge of 96), and
'light_axis'. The files are scan__<negative>__<light>__auto_<off|neutral>.bin, a blend light named cct<kelvin>. As in build_display_expected.py, the scan
model is built with the default point steps and rendered with the steps of the product.
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
SCAN_IMAGE_SELECTIONS = tuple((negative, light, auto) for negative in dict.fromkeys(n for n, _ in bpr.SCAN_EXPECTED_SELECTIONS) for light in bpr.SCAN_DISPLAY_LIGHTS for auto in ("off", "neutral"))


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
    # Option --scan-only: only the Negative Scan files; the ap1.bin and the other files of an earlier run stay (the same RAW file gives the same AP1).
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
    point_steps = fp.INHIBITION_STEPS_POINT
    for negative, light, auto in SCAN_IMAGE_SELECTIONS:
        fp.INHIBITION_STEPS_POINT = point_steps
        model = bpr.scan_expected_model(negative, light)
        fp.INHIBITION_STEPS_POINT = fp.INHIBITION_STEPS_IMAGE
        linear, shift, prescan = bpr.scan_linear(model, graded, auto)
        fp.INHIBITION_STEPS_POINT = point_steps
        if not np.isfinite(linear).all():
            raise FloatingPointError(f"scan {negative} under {light}: the output is not finite")
        label = bpr.scan_light_label(light)
        bpr.write_arrays(OUTPUT / f"scan__{negative}__{label}__auto_{auto}.bin", {"linear": linear, "shift": shift, "prescan": prescan, "light_axis": np.asarray(model.light_axis, dtype=np.float64)},
                         {"negative": negative, "print_material": bpr.NEGATIVE_SCAN["id"], "scene_light": label, "auto": auto, "lab_commit": commit})
        print(f"scan {negative} under {label}, auto {auto}: {linear.shape}, shift {shift}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
