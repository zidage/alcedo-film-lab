"""Command line of the Python MVP: one RAW file to one TIFF or JPEG, by the print method or the Frontier scan method.

Input: a RAW file; the options below. Output: the image and a parameter file <output>.json. Step: P6, README U61.
Usage: p6_mvp_cli.py INPUT OUTPUT [--negative NAME] [--method print|frontier] [--print-material NAME] [--scene-light NAME] [--spectral-prior NAME] [--list].
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mvp_pipeline as mp


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = mp.RenderSettings()
    parser.add_argument("input", type=Path, nargs="?")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--negative", default=defaults.negative, choices=sorted(mp.CATALOG["negatives"]))
    parser.add_argument("--method", default=defaults.method, choices=mp.METHODS)
    parser.add_argument("--print-material", default=defaults.print_material, choices=sorted(mp.CATALOG["prints"]))
    parser.add_argument("--scene-light", default=defaults.scene_light, choices=mp.SCENE_LIGHTS)
    parser.add_argument("--spectral-prior", default=defaults.spectral_prior, choices=mp.SPECTRAL_PRIORS)
    parser.add_argument("--exposure-ev", type=float, default=defaults.exposure_ev)
    parser.add_argument("--contrast", type=float, default=defaults.contrast)
    parser.add_argument("--saturation", type=float, default=defaults.saturation)
    parser.add_argument("--no-scanner-stage", action="store_true", help="Frontier method: no chroma denoise, skin protection, or unsharp mask.")
    parser.add_argument("--long-edge", type=int, default=mp.DEFAULT_LONG_EDGE)
    parser.add_argument("--list", action="store_true", help="List the materials and stop.")
    args = parser.parse_args()
    if args.list:
        for group in ("negatives", "prints"):
            print(group)
            for stem, entry in mp.CATALOG[group].items():
                print(f"  {stem:30s} {entry['name']}")
        print("not usable")
        for stem, entry in mp.CATALOG["not_usable"].items():
            print(f"  {stem:30s} {entry['reason']}")
        return 0
    if args.input is None or args.output is None:
        parser.error("INPUT and OUTPUT are necessary")
    settings = mp.RenderSettings(negative=args.negative, method=args.method, print_material=args.print_material, scene_light=args.scene_light, spectral_prior=args.spectral_prior,
                                 exposure_ev=args.exposure_ev, contrast=args.contrast, saturation=args.saturation, scanner_stage=not args.no_scanner_stage)
    image, record = mp.Pipeline().render_file(args.input, settings, args.long_edge)
    for path in mp.write_outputs(image, record, args.output):
        print(path)
    print({k: record[k] for k in ("processed_long_edge", "model_load_s", "decode_s", "render_s")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
