"""Limit the optical spread and the development inhibition of the new negatives from their modulation transfer curves, and find the stocks with a relative sensitivity chart.

Input: profiles/<negative>.json; the model form and the bounds of fit_mtf.py (P4). Output: stock_physics.json next to this script, and a table on stdout.
Step: P6, ROADMAP U61. The form, the bounds, and the inference rules are those of P4 and P5. One curve for all layers: the three records use one fit of the spread and the boost, as C200 in P5.

Rule 'relative_sensitivity_level', with a limit set before the first run: a grey of the reference light at the exposure of the grey that lands more than 3 stops from the criterion, as the mean of the three layers,
means that the chart has no absolute level. The script moves the sensitivity of each layer in the profile, so that each layer lands on the criterion, and records the rule in the profile. Rule grey_anchor then sets the balance of such a stock (see mvp_pipeline.py),
so the three values have no effect on the colour of the result. Accepted stocks do not change and are not fitted.
A stock that the model cannot run is recorded with its real error, and the pipeline refuses it.

Rule 'grey_off_the_curve' (step P7, limit set before the first run): an 18 % grey of the balance light of the stock, through the layer exposure of the pipeline, lands more than GREY_OFF_CURVE_LIMIT_STOPS from the exposure of the grey on the curve of any layer.
Its chart then has no usable level, and the grey falls onto the toe. The stock takes rule grey_anchor, as C200 does. The profile does not change, because the gains of rule grey_anchor replace the level of the chart. The limit of rule 'relative_sensitivity_level' uses another exposure path, and it does not find these stocks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR.parent / "p4_physical_film_response"))
import mvp_pipeline as mp  # noqa: E402
from fit_mtf import BOUNDS, response  # noqa: E402

fp = mp.fp
RELATIVE_LIMIT_STOPS = 3.0
GREY_OFF_CURVE_LIMIT_STOPS = 1.0  # rule 'grey_off_the_curve' (step P7); the 8 accepted stocks have at most 0.84 stops
RULE = "relative_sensitivity_level"


def apply_relative_level(negative: str, options: fp.FilmOptions) -> tuple[list[float], bool]:
    """Layer exposure of the reference grey in stops, before any change, and whether the stock has the rule. It reads no print table."""
    path = fp.p0.PROFILE_DIR / f"{negative}.json"
    profile = json.loads(path.read_text(encoding="utf-8"))
    model_options = fp.p0.ModelOptions(camera_daylight_cct_k=fp.sr.E_REF_NOMINAL_CCT_K, negative_dye_basis=options.negative_dye_basis, negative_density_outside=options.density_outside,
                                       paper_dye_outside=options.density_outside, negative_profile=negative, print_profile=options.print_profile, midscale_log_h=options.midscale_log_h,
                                       viewing_daylight_cct_k=options.viewing_cct_k, printer_balance_log10=(0.0, 0.0, 0.0))
    film = fp.p0.ReferenceModel(step_nm=1.0, rule="projected", options=model_options)
    exposure = film.spectral_exposure_for_luminous_exposure(film.camera_light, np.array([10.0 ** options.midscale_log_h]))
    stops = np.log2(film.negative_layer_exposure(exposure))[0]
    done = any(str(r).startswith(RULE) for r in profile.get("inferred_rules", []))
    if not done and abs(stops.mean()) > RELATIVE_LIMIT_STOPS:
        shifts = -stops * np.log10(2.0)
        for shift, curve in zip(shifts, profile["charts"]["spectral_sensitivity"]["curves"].values()):
            curve["y"] = np.round(np.array(curve["y"]) + shift, 5).tolist()
        profile["inferred_rules"].append(f"{RULE}, log10 sensitivity per layer {np.round(shifts, 4).tolist()}")
        path.write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8", newline="\n")
        done = True
    return np.round(stops, 3).tolist(), done


def main() -> int:
    result = {}
    for negative in mp.CATALOG["negatives"]:
        if negative in mp.ACCEPTED_STOCKS:
            continue
        options = mp.film_options(mp.RenderSettings(negative=negative), physics={negative: {"relative_sensitivity": True}})
        stops, relative = apply_relative_level(negative, options)
        entry = {"reference_grey_stops_before_rule": stops, "relative_sensitivity": relative}
        options = mp.film_options(mp.RenderSettings(negative=negative), physics={negative: {"relative_sensitivity": relative}})
        try:
            model = fp.FilmPreview(options)
        except (ValueError, RuntimeError) as error:
            entry["error"] = str(error)
            result[negative] = entry
            print(negative, json.dumps(entry), flush=True)
            continue
        film = model.film
        # Rule 'grey_off_the_curve', in the terms of rule grey_anchor: the grey of the balance light against the curve, per layer.
        balance = "T3200" if mp.CATALOG["negatives"][negative].get("exposure_kelvin", 5500) < 4500 else "D55"
        grey_stops = np.log2(model.c.layer_exposure(0.18 * model.light(balance)) / 10.0 ** (film.options.midscale_log_h - film.negative_criterion_log_h))
        entry["grey_stops_at_balance_light"] = np.round(grey_stops, 3).tolist()
        entry["relative_sensitivity"] = relative or bool(np.abs(grey_stops).max() > GREY_OFF_CURVE_LIMIT_STOPS)
        chart = mp.fp.p0.load_profile(negative)["charts"].get("modulation_transfer")
        if chart:
            names = ("red", "green", "blue") if "red" in chart["curves"] else ("all_layers",) * 3
            middle = film.options.midscale_log_h
            spread, totals, residual = [], [], 0.0
            for k, name in enumerate(names):
                x, y = np.array(chart["curves"][name]["x"]), np.array(chart["curves"][name]["y"])
                fit = least_squares(lambda p: response(x, *p) - y, (4.0, 15.0, 1.2), bounds=BOUNDS)
                curve = model.negative_curves[k]
                gamma = float(np.interp(middle + 0.5, curve.log_h, curve.density) - np.interp(middle - 0.5, curve.log_h, curve.density))
                s, _, boost = fit.x
                spread.append(round(float(s), 2))
                totals.append(round(float((boost - 1.0) / (boost * gamma)), 4))
                residual = max(residual, float(np.sqrt(np.mean(fit.fun**2))))
            entry.update(layer_spread_um=spread, inhibition_total=totals, largest_rms_residual=round(residual, 4))
        result[negative] = entry
        print(negative, json.dumps(entry), flush=True)
    mp.PHYSICS_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
