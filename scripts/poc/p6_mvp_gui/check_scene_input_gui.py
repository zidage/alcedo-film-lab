"""Check the P13 preset, P12 control and real Qt worker renders.

Input: the existing night RAW. Output: GUI export and state checks in
build/tmp/p13_gui. Run with QT_QPA_PLATFORM=offscreen for a window-free check.
The check uses 640-pixel review input and retains the complete spectral grid.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
from PySide6.QtCore import QObject, QTimer, Slot
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mvp_pipeline as mp  # noqa: E402
from p6_mvp_gui import MainWindow  # noqa: E402


def main() -> int:
    out = mp.REPO_ROOT / "build/tmp/p13_gui"
    out.mkdir(parents=True, exist_ok=True)
    raw = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/film_emulation/5253219691.rw2")
    app = QApplication(sys.argv[:1])
    window = MainWindow()
    window.negative.setCurrentIndex(window.negative.findData("kodak_portra_400"))
    window.controls["stock_character"].setValue(2.0)
    window.long_edge.setValue(640)
    window.use_smooth_scan()
    settings = window.settings()
    assert settings.stock_character == 2.0 and settings.negative == "kodak_portra_400"
    assert settings.method == "apd" and settings.spectral_input == "white_smooth"
    assert settings.scene_light == mp.AS_SHOT and not settings.apd_lad_aim
    assert settings.apd_axis == "numbers" and settings.apd_numbers == "generic"
    assert not window.prior.isEnabled() and not window.light.isEnabled()
    state = {"phase": 0, "renders": [], "errors": []}
    previous = [None]

    def finish() -> None:
        (out / "gui_checks.json").write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8",newline="\n")
        print("Finishing Qt check on the application thread",flush=True)
        window.close()
        app.exit(0)

    def failed(message: str) -> None:
        state["errors"].append(message)
        QTimer.singleShot(0,window,finish)

    def rendered(image: np.ndarray, record: dict) -> None:
        try:
            assert np.isfinite(image).all()
            assert record["settings"]["scene_white_xyz"] is not None
            assert record["settings"]["spectral_prior"] == "measured_reflectance"
            state["renders"].append({"mode":record["settings"]["spectral_input"],
                                    "stock_character":record["settings"]["stock_character"],
                                    "spectral_input":record["spectral_input"]})
            phase = state["phase"]
            if phase == 0:
                assert record["settings"]["stock_character"] == 2.0
                mp.write_outputs(image,record,out / "gui_smooth_character2.jpg")
                state["phase"] = 1
                QTimer.singleShot(0,window,lambda: window.controls["stock_character"].setValue(3.0))
            elif phase == 1:
                assert record["settings"]["stock_character"] == 3.0
                state["phase"] = 2
                QTimer.singleShot(0,window,lambda: window.spectral_input.setCurrentIndex(window.spectral_input.findData("conditioned_smooth")))
            elif phase == 2:
                assert record["settings"]["stock_character"] == 3.0
                assert record["settings"]["spectral_input"] == "conditioned_smooth"
                assert record["spectral_input"]["reconstruction"]["XYZ_relative_max"] <= 1e-8
                previous[0] = image.copy()
                state["phase"] = 3
                QTimer.singleShot(0,window,window.schedule)
            else:
                assert record["spectral_input"]["reconstruction"]["cache_hit"]
                assert np.array_equal(image,previous[0])
                state["phase"] = 4
                QTimer.singleShot(0,window,finish)
        except Exception as error:
            failed(f"{type(error).__name__}: {error}")

    class Results(QObject):
        @Slot(object, object)
        def receive(self, image: np.ndarray, record: dict) -> None:
            rendered(image,record)

        @Slot(str)
        def error(self, message: str) -> None:
            failed(message)

    receiver = Results()
    window.worker.finished.connect(receiver.receive)
    window.worker.failed.connect(receiver.error)
    QTimer.singleShot(180000,window,lambda: failed("GUI render check exceeded 180 seconds"))
    window.load(raw)
    app.exec()
    if state["errors"] or state["phase"] != 4:
        raise AssertionError(state)
    print("PASS Qt worker renders, P13 preset, stock character 2/3, cache and export metadata",flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
