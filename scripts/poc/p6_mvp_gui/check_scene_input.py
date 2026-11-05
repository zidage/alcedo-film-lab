"""Check P13 GUI input, P12 stock character, caching and export metadata.

Input: the existing night RAW and P13 reference code. Output: checks and local
review renders under build/tmp/p13_gui. Display tolerance is 2e-6; cached output
must be exact. No material, scan or curve is fitted by these comparisons.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mvp_pipeline as mp  # noqa: E402
sys.path.insert(0, str(HERE.parent / "p13_spectral_input"))
import run_study as study  # noqa: E402

OUT = mp.REPO_ROOT / "build/tmp/p13_gui"
RAW = study.RAW_ROOT / "film_emulation/5253219691.rw2"
DISPLAY_TOLERANCE = 2e-6


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    pipeline = mp.Pipeline()
    unresolved = mp.RenderSettings(method="apd", negative="kodak_portra_400",
                                    scene_light=mp.AS_SHOT, apd_axis="numbers",
                                    apd_lad_aim=False, spectral_input="white_smooth")
    settings = mp.resolve_as_shot(unresolved, RAW)
    settings.validate()
    probe = pipeline.scan_model(settings)
    ap1, decode = mp.decode_raw(RAW, probe.negative.c, 640)
    graded = np.ascontiguousarray(mp.fp.fk.product_grade(
        ap1, settings.exposure_ev, settings.contrast, settings.saturation),dtype=np.float32)
    engine = study.SpectralInput(probe.negative.c)
    spectrum = np.asarray(mp.scene_input.matched_spectrum("white_smooth",settings.scene_white_xyz)[0])
    checks = {"display_tolerance": DISPLAY_TOLERANCE, "cases": {}, "decode": decode}
    # Compare the integrated scene construction against the original P13 path.
    for mode, k in (("white_smooth",1.0), ("white_smooth",2.0),
                    ("conditioned_smooth",1.0), ("conditioned_smooth",2.0)):
        current = replace(settings, spectral_input=mode, stock_character=k)
        code = pipeline.render_array(ap1,current)
        record = pipeline.spectral_input_record(current)
        reference_settings = replace(current, spectral_input="current", scene_white_xyz=None)
        reference = mp.Pipeline().scan_model(reference_settings)
        study.set_scene(reference,spectrum,engine.shapes["measured"])
        reference.timing = 0.0
        reference.offset = reference._adx_offset()
        if mode.startswith("conditioned_"):
            q, stats = engine.exposures(graded,spectrum,{"selected": reference.negative},True)
            with study.injected_exposure(reference.negative,graded,
                     q["selected"]*reference.negative.layer_gain,
                     stats["moved_by_existing_locus_rule"],stats["Y_not_positive"]):
                expected,_ = reference.render(graded)
        else:
            expected,_ = reference.render(graded)
        error = float(np.max(np.abs(code-expected)))
        if error > DISPLAY_TOLERANCE:
            raise AssertionError(f"{mode}/{k}: P13 display differs by {error}")
        repeated = pipeline.render_array(ap1,current)
        if not np.array_equal(repeated,code):
            raise AssertionError("cached output changed")
        if mode.startswith("conditioned_") and not pipeline.spectral_input_record(current)["reconstruction"]["cache_hit"]:
            raise AssertionError("repeated constrained input did not use its exposure cache")
        checks["cases"][f"{mode}/character{k}"] = {"display_max_abs":error,"record":record}
        mp.write_outputs(code,{"settings":mp.asdict(current),"spectral_input":record},
                         OUT / f"{mode}_character{k}.jpg")
        print(f"PASS {mode}, character {k}, max display error {error}",flush=True)
    # Same scene-name string but a different XYZ white must build a new model.
    changed = replace(settings,scene_white_xyz=(settings.scene_white_xyz[0]*1.001,
                                               settings.scene_white_xyz[1],settings.scene_white_xyz[2]))
    if pipeline.scan_model(settings) is pipeline.scan_model(changed):
        raise AssertionError("model cache ignored the complete scene white")
    for mode in ("white_led","white_fluorescent","conditioned_led"):
        spectrum_tuple, record = mp.scene_input.matched_spectrum(mode,settings.scene_white_xyz)
        if record["white_fit"]["XYZ_max_abs"] > 1e-8:
            raise AssertionError(f"{mode}: invalid white fit")
        checks[mode] = {"white_fit":record["white_fit"],"spectral_nodes":len(spectrum_tuple)}
    # Resolve another file with the same settings; do not reuse the previous RAW white.
    other = mp.resolve_as_shot(unresolved,study.RAW_ROOT / "signature_edits/se357.cr2")
    if other.scene_white_xyz == settings.scene_white_xyz:
        raise AssertionError("RAW white was reused for a different file")
    checks["RAW_white_changes_with_file"] = True
    checks["seconds"] = time.perf_counter()-started
    checks["peak_working_set_bytes"] = study.peak_working_set()
    (OUT / "pipeline_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8",newline="\n")
    print("PASS pipeline checks",flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
