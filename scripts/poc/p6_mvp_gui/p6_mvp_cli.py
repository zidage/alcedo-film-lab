"""Command line of the Python MVP: one RAW file to one TIFF or JPEG, by the print method, the APD scan method, a reversal film on a light table (step P9), or the chart-calibrated scan (step P10).

Input: a RAW file; the options below. Output: the image and a parameter file <output>.json. Step: P6, ROADMAP U61.
Usage: p6_mvp_cli.py INPUT OUTPUT [--negative NAME] [--method print|apd|light_table|chart_scan] [--reversal NAME] [--print-material NAME] [--scene-light NAME] [--spectral-prior NAME] [--list], and one option per entry of mvp_pipeline.CONTROLS, for example --print-contrast 1.0.
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
    parser.add_argument("--reversal", default=defaults.reversal, choices=list(mp.CATALOG["reversals"]), help="Method light_table: the reversal film.")
    parser.add_argument("--print-material", default=defaults.print_material, choices=list(mp.CATALOG["prints"]))
    parser.add_argument("--scene-light", default=defaults.scene_light, choices=mp.SCENE_LIGHTS)
    parser.add_argument("--spectral-prior", default=defaults.spectral_prior, choices=mp.SPECTRAL_PRIORS)
    parser.add_argument("--exposure-ev", type=float, default=defaults.exposure_ev)
    parser.add_argument("--contrast", type=float, default=defaults.contrast)
    parser.add_argument("--saturation", type=float, default=defaults.saturation)
    parser.add_argument("--long-edge", type=int, default=mp.DEFAULT_LONG_EDGE)
    for control in mp.CONTROLS:
        parser.add_argument("--" + control.name.replace("_", "-"), type=float, default=getattr(defaults, control.name), help=f"{control.note} Range {control.low} to {control.high}. Method: {', '.join(control.methods)}.")
    parser.add_argument("--display-white", default=defaults.display_white, choices=mp.DISPLAY_WHITES, help="Print method: 'reflector' keeps the paper base, and 'paper' maps the paper to display white.")
    parser.add_argument("--no-gamut-compress", action="store_true", help="Print method: clip in place of rule rgc_style_display_compression.")
    parser.add_argument("--apd-output", default=defaults.apd_output, choices=mp.SCAN_OUTPUTS, help="APD method: the output transform (ACES 1.3, ACES 2.0, or AgX and OpenDRT at the grey of ACES 2.0, U92).")
    parser.add_argument("--apd-drt-grey", default=defaults.apd_drt_grey, choices=mp.DRT_GREYS, help="APD method with AgX or OpenDRT: 'aces20', ACES 0.18 at the grey code of ACES 2.0; 'native', no exposure change (U92).")
    parser.add_argument("--apd-encoding", default=defaults.apd_encoding, choices=tuple(mp.ENCODINGS), help="APD method: 'adx16' (no clip) or 'adx10' (clip at 1023), U93.")
    parser.add_argument("--no-slope-match", action="store_true", help="APD method: the scale 1.00, 0.92, 0.95 of ST 2065-3 for every stock, in place of rule 'adx_slope_match' (U93).")
    parser.add_argument("--apd-colour", default=defaults.apd_colour, choices=mp.SCAN_COLOURS, help="APD method: rule 'scan_print_colour' target, or 'academy' (U95).")
    parser.add_argument("--apd-reading", default=defaults.apd_reading, choices=mp.READINGS, help="APD method: 'apd' (ST 2065-2) or 'print2383', the printing density of Kodak 2383 (U92).")
    parser.add_argument("--no-lad-aim", action="store_true", help="APD method: no offset per channel, so the stock keeps its own grey position in ADX10.")
    parser.add_argument("--chart-scan-reading", default=defaults.chart_scan_reading, choices=mp.CHART_SCAN_READINGS, help="Method chart_scan: 'dye', the dye amounts with the Status M contrast of U89 (U90); 'status_m', the reading of U88 and U89.")
    parser.add_argument("--chart-scan-matrix", default=defaults.chart_scan_matrix, choices=mp.CHART_SCAN_MATRICES, help="Method chart_scan: 'code', curve on the film channels then the matrix (U90); 'linear', the matrix then the curve (U88).")
    parser.add_argument("--chart-scan-display", default=defaults.chart_scan_display, choices=mp.CHART_SCAN_DISPLAYS, help="Method chart_scan: the log curve or a display rendering transform on the linear AP1 of the scan (U91).")
    parser.add_argument("--chart-scan-slope", default=defaults.chart_scan_slope, choices=mp.CHART_SCAN_SLOPES, help="Method chart_scan: 'fixed', one Status M slope for all stocks (rule fixed_scan_slope); 'stock', the slope of the grey scale of the stock (U88).")
    parser.add_argument("--list", action="store_true", help="List the materials and stop.")
    args = parser.parse_args()
    if args.list:
        for group in ("negatives", "prints", "reversals"):
            print(group)
            for stem, entry in mp.CATALOG[group].items():
                print(f"  {stem:30s} {entry['name']}")
        print("not usable")
        for stem, entry in mp.CATALOG["not_usable"].items():
            print(f"  {stem:30s} {entry['reason']}")
        return 0
    if args.input is None or args.output is None:
        parser.error("INPUT and OUTPUT are necessary")
    settings = mp.RenderSettings(negative=args.negative, method=args.method, reversal=args.reversal, print_material=args.print_material, scene_light=args.scene_light, spectral_prior=args.spectral_prior,
                                 exposure_ev=args.exposure_ev, contrast=args.contrast, saturation=args.saturation, display_white=args.display_white, gamut_compress=not args.no_gamut_compress, apd_output=args.apd_output, apd_lad_aim=not args.no_lad_aim, apd_reading=args.apd_reading, apd_drt_grey=args.apd_drt_grey, apd_encoding=args.apd_encoding, apd_slope_match=not args.no_slope_match, apd_colour=args.apd_colour, chart_scan_slope=args.chart_scan_slope, chart_scan_reading=args.chart_scan_reading, chart_scan_matrix=args.chart_scan_matrix, chart_scan_display=args.chart_scan_display,
                                 **{control.name: getattr(args, control.name) for control in mp.CONTROLS})
    image, record = mp.Pipeline().render_file(args.input, settings, args.long_edge)
    for path in mp.write_outputs(image, record, args.output):
        print(path)
    print({k: record[k] for k in ("processed_long_edge", "model_load_s", "decode_s", "render_s")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
