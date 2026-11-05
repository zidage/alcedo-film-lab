"""P13 hue sweep before photo judgement: cast, residual colour and stock distance.

Input: existing CAM16 scene sweep and selected RAW white metadata. Output: local
JSON and a hue-sweep comparison PNG. No film output or chart is fitted.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_study as study  # noqa: E402
from spectral_input import SpectralInput, read_raw_white, make_lights, sr  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--out", type=Path, default=study.ROOT / "build/tmp/p13_sweep")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    pipeline = study.mp.Pipeline()
    settings = study.mp.RenderSettings(method="apd", scene_light="CCT4138",
                                       apd_axis="numbers", stock_character=1.0)
    scans = {name: pipeline.scan_model(replace(settings, negative=name)) for name in study.STOCKS}
    c = scans[study.STOCKS[0]].negative.c
    engine = SpectralInput(c)
    sweep = study.sa.make_sweep(study.fp, c)
    # The same chromaticities at 0 EV. Scale the integrals to other exposures.
    # This uses exact homogeneity, not a lower spectral or chromaticity resolution.
    unit = sweep.ap1.astype(np.float64) / np.exp2(sweep.exposure[:,None])
    unique, inverse = np.unique(unit, axis=0, return_inverse=True)
    white = read_raw_white(args.raw)
    lights, records = make_lights(c, white)
    display = study.sa.Display(study.fp)
    result = {"RAW": str(args.raw), "lights": records, "cases": {},
              "sweep_samples": len(unit), "unit_chromaticities": len(unique),
              "grid_nm": [360,840,1], "stock_character": 1.0}
    zero_colour = (sweep.kind == 0) & (sweep.exposure == 0) & (sweep.fraction == 1)
    zero_neutral = (sweep.kind == 1) & (sweep.exposure == 0)
    shown = {}
    for case, (_label, family, prior, conditioned) in study.CASES.items():
        spectrum = lights[family]
        q_all = None
        try:
            if conditioned:
                q_unique, solve = engine.exposures(unique[None], spectrum,
                                  {stock: scan.negative for stock, scan in scans.items()}, True)
                q_all = {stock: q_unique[stock][0][inverse]*np.exp2(sweep.exposure[:,None])
                         for stock in scans}
            case_record = {"stocks": {}, "pairs": {}}
            if conditioned:
                case_record["solve"] = solve
            appearances = {}
            for stock, scan in scans.items():
                study.set_scene(scan, spectrum, engine.shapes[prior])
                for timing in (0.0, 1.0):
                    scan.timing = timing
                    scan.offset = scan._adx_offset()
                    if conditioned:
                        image = np.ascontiguousarray(sweep.ap1[None], dtype=np.float32)
                        q = q_all[stock][None]*scan.negative.layer_gain
                        with study.injected_exposure(scan.negative, image, q, 0, 0):
                            code, _ = scan.render(image)
                        code = code[0]
                    else:
                        code, _ = scan.render(sweep.ap1)
                        code = code[0] if code.ndim == 3 else code
                    app = display.appearance(code)
                    appearances[stock,timing] = app
                    neutral = app["UCS"][zero_neutral][0]
                    colours = app["UCS"][zero_colour]
                    relative = colours[:,1:] - neutral[1:]
                    case_record["stocks"][f"{stock}/balance{int(timing)}"] = {
                        "neutral_UCS": neutral.tolist(),
                        "mean_distance_from_neutral_ab": float(np.mean(np.linalg.norm(relative,axis=1))),
                        "hue_relative_to_neutral_deg": np.degrees(np.arctan2(relative[:,1],relative[:,0])).tolist()}
                    if timing == 1.0:
                        shown[case,stock] = code[zero_colour]
            for timing in (0.0,1.0):
                for a,b in ((study.STOCKS[0],study.STOCKS[1]),(study.STOCKS[2],study.STOCKS[3])):
                    aa,bb = appearances[a,timing]["UCS"],appearances[b,timing]["UCS"]
                    selected = (sweep.kind == 0) & (np.abs(sweep.exposure) <= 4)
                    full = np.linalg.norm(aa[selected]-bb[selected],axis=1)
                    # At 0 EV, subtract each stock's own neutral a'b' before comparison.
                    a_colour = aa[zero_colour,1:]-aa[zero_neutral,1:]
                    b_colour = bb[zero_colour,1:]-bb[zero_neutral,1:]
                    chromatic = np.linalg.norm(a_colour-b_colour,axis=1)
                    case_record["pairs"][f"balance{int(timing)}/{a}/{b}"] = {
                        "full_UCS_p50": float(np.median(full)),
                        "neutral_removed_ab_p50_at_0EV": float(np.median(chromatic))}
            result["cases"][case] = case_record
            print(f"sweep {case} complete", flush=True)
        except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as error:
            result["cases"][case] = {"FAILED": f"{type(error).__name__}: {error}"}
            print(f"sweep {case} FAILED: {error}",flush=True)
        study.write_json(args.out / "sweep.json", result)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(study.STOCKS), 1, figsize=(15,8))
    for row,stock in enumerate(study.STOCKS):
        ax = axes[row]
        for column,case in enumerate(study.CASES):
            if (case,stock) in shown:
                strip = np.repeat(shown[case,stock][None],12,axis=0)
                ax.imshow(strip,extent=(0,360,column,column+0.9),aspect="auto")
        ax.set_yticks(np.arange(len(study.CASES))+0.45,
                      [value[0] for value in study.CASES.values()],fontsize=7)
        ax.set_title(stock,fontsize=10)
        ax.set_xlim(0,360)
        ax.set_ylim(0,len(study.CASES))
        ax.set_xlabel("Input CAM16 hue (degrees), 0 EV; scene balance 1")
    fig.tight_layout()
    fig.savefig(args.out / "hue_sweep.png",dpi=140)
    plt.close(fig)
    return int(any("FAILED" in value for value in result["cases"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
