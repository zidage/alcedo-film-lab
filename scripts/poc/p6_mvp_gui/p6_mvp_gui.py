"""Small desktop viewer of the Python MVP. It uses the same pipeline as the command line.

Input: a RAW file, chosen in the window. Output: the display of the render, and a TIFF or JPEG with its parameter file on export. Step: P6, ROADMAP U61.
A render runs on one worker thread; a change that comes during a render starts one more render after it. An error of the pipeline shows in the status line, and the last image stays.
Usage: p6_mvp_gui.py [RAW file]. Option --render-once PATH renders the file with the default settings, saves the window to PATH, and stops (a check of the window).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

import mvp_pipeline as mp


class RenderWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.pipeline = mp.Pipeline()
        self._source: tuple[tuple[Path, int], np.ndarray, dict] | None = None

    @Slot(object, object, int)
    def render(self, path: Path, settings: mp.RenderSettings, long_edge: int) -> None:
        try:
            colorimetry = self.pipeline.colorimetry(settings) if settings.validate() is None else None
            if self._source is None or self._source[0] != (path, long_edge):
                ap1, decode = mp.decode_raw(path, colorimetry, long_edge)
                self._source = ((path, long_edge), ap1, decode)
            _, ap1, decode = self._source
            image = self.pipeline.render_array(ap1, settings)
            self.finished.emit(image, {"input": str(path), "settings": mp.asdict(settings), **decode})
        except Exception as error:  # noqa: BLE001 - the window shows the real error of the pipeline and renders no substitute
            self.failed.emit(f"{type(error).__name__}: {error}")


class MainWindow(QMainWindow):
    request = Signal(object, object, int)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Alcedo film lab - P6 Python MVP")
        self.resize(1500, 950)
        self.path: Path | None = None
        self.image: np.ndarray | None = None
        self.record: dict | None = None
        self.busy = False
        self.pending = False
        self.after_render = None
        defaults = mp.RenderSettings()
        self.negative = self._combo(mp.CATALOG["negatives"], defaults.negative)
        self.method = self._combo({"print": {"name": "Print"}, "apd": {"name": "APD scan (ADX, ACES output)"}}, defaults.method)
        self.print_material = self._combo(mp.CATALOG["prints"], defaults.print_material)
        self.light = self._combo({k: {"name": k} for k in mp.SCENE_LIGHTS}, defaults.scene_light)
        self.prior = self._combo({"light_like": {"name": "Light-like spectra"}, "measured_reflectance": {"name": "Measured reflectance"}}, defaults.spectral_prior)
        self.exposure = self._spin(-6.0, 6.0, defaults.exposure_ev, 0.25)
        self.contrast = self._spin(-100.0, 100.0, defaults.contrast, 1.0)
        self.saturation = self._spin(0.0, 2.0, defaults.saturation, 0.05)
        self.long_edge = QSpinBox()
        self.long_edge.setRange(512, 16000)
        self.long_edge.setSingleStep(512)
        self.long_edge.setValue(mp.DEFAULT_LONG_EDGE)
        self.long_edge.setKeyboardTracking(False)
        self.long_edge.valueChanged.connect(self.schedule)
        self.display_white = self._combo({"reflector": {"name": "Perfect reflector"}, "paper": {"name": "Paper"}}, defaults.display_white)
        self.gamut = QCheckBox("Display gamut compression")
        self.gamut.setChecked(defaults.gamut_compress)
        self.gamut.toggled.connect(self.schedule)
        self.controls: dict[str, QDoubleSpinBox] = {}
        groups = {}
        for control in mp.CONTROLS:
            spin = self._spin(control.low, control.high, getattr(defaults, control.name), control.step, control.decimals)
            spin.setToolTip(control.note)
            self.controls[control.name] = spin
            groups.setdefault(control.group, QFormLayout()).addRow(control.label, spin)
        groups["Print"].addRow("Display white", self.display_white)
        groups["Print"].addRow("", self.gamut)
        self.apd_output = self._combo({"aces20": {"name": "ACES 2.0 (Rec. 709, 100 nit)"}, "aces13": {"name": "ACES 1.3 (SDR video)"}}, defaults.apd_output)
        self.lad_aim = QCheckBox("Mid grey at ADX10 445 (LAD aim)")
        self.lad_aim.setChecked(defaults.apd_lad_aim)
        self.lad_aim.toggled.connect(self.schedule)
        groups["Scan"].addRow("ACES output", self.apd_output)
        groups["Scan"].addRow("", self.lad_aim)
        form = QFormLayout()
        for label, widget in (("Negative", self.negative), ("Method", self.method), ("Print material", self.print_material), ("Scene light", self.light), ("Spectral prior", self.prior),
                              ("Exposure (EV)", self.exposure), ("Contrast", self.contrast), ("Saturation", self.saturation), ("Long edge (pixels)", self.long_edge)):
            form.addRow(label, widget)
        open_button = QPushButton("Open RAW...")
        open_button.clicked.connect(self.open_raw)
        export_button = QPushButton("Export...")
        export_button.clicked.connect(self.export)
        reset_button = QPushButton("Reset the controls below")
        reset_button.clicked.connect(self.reset_controls)
        self.status = QLabel("Open a RAW file.")
        self.status.setWordWrap(True)
        panel = QVBoxLayout()
        panel.addWidget(open_button)
        panel.addLayout(form)
        panel.addWidget(export_button)
        panel.addWidget(self.status)
        panel.addWidget(reset_button)
        self.groups = {}
        for name, layout in groups.items():
            self.groups[name] = QGroupBox(name)
            self.groups[name].setLayout(layout)
            panel.addWidget(self.groups[name])
        panel.addStretch(1)
        side = QWidget()
        side.setLayout(panel)
        side_scroll = QScrollArea()
        side_scroll.setWidget(side)
        side_scroll.setWidgetResizable(True)
        side_scroll.setFixedWidth(400)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidget(self.view)
        scroll.setWidgetResizable(True)
        root = QHBoxLayout()
        root.addWidget(side_scroll)
        root.addWidget(scroll, 1)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)
        self._update_visibility()
        self.thread_ = QThread(self)
        self.worker = RenderWorker()
        self.worker.moveToThread(self.thread_)
        self.request.connect(self.worker.render)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.thread_.start()

    def _combo(self, entries: dict, current: str) -> QComboBox:
        box = QComboBox()
        box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(16)
        for key, entry in entries.items():
            box.addItem(entry["name"], key)
        box.setCurrentIndex(box.findData(current))
        box.currentIndexChanged.connect(self.schedule)
        return box

    def _spin(self, low: float, high: float, value: float, step: float, decimals: int = 2) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(decimals)
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        spin.valueChanged.connect(self.schedule)
        return spin

    def settings(self) -> mp.RenderSettings:
        return mp.RenderSettings(negative=self.negative.currentData(), method=self.method.currentData(), print_material=self.print_material.currentData(), scene_light=self.light.currentData(),
                                 spectral_prior=self.prior.currentData(), exposure_ev=self.exposure.value(), contrast=self.contrast.value(), saturation=self.saturation.value(),
                                 display_white=self.display_white.currentData(), gamut_compress=self.gamut.isChecked(), apd_output=self.apd_output.currentData(), apd_lad_aim=self.lad_aim.isChecked(), **{name: spin.value() for name, spin in self.controls.items()})

    @Slot()
    def reset_controls(self) -> None:
        defaults = mp.RenderSettings()
        widgets = [*self.controls.values(), self.display_white, self.gamut, self.apd_output, self.lad_aim]
        for widget in widgets:
            widget.blockSignals(True)
        for name, spin in self.controls.items():
            spin.setValue(getattr(defaults, name))
        self.display_white.setCurrentIndex(self.display_white.findData(defaults.display_white))
        self.gamut.setChecked(defaults.gamut_compress)
        self.apd_output.setCurrentIndex(self.apd_output.findData(defaults.apd_output))
        self.lad_aim.setChecked(defaults.apd_lad_aim)
        for widget in widgets:
            widget.blockSignals(False)
        self.schedule()

    def _update_visibility(self) -> None:
        scan = self.method.currentData() == "apd"
        self.print_material.setEnabled(not scan)
        self.groups["Print"].setEnabled(not scan)
        self.groups["Scan"].setEnabled(scan)

    @Slot()
    def schedule(self) -> None:
        if not hasattr(self, "worker"):
            return
        self._update_visibility()
        if self.path is None:
            return
        if self.busy:
            self.pending = True
            return
        self.busy = True
        self.status.setText("Rendering...")
        self.request.emit(self.path, self.settings(), self.long_edge.value())

    @Slot()
    def open_raw(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open RAW", "", "RAW files (*.arw *.cr2 *.cr3 *.nef *.raf *.rw2 *.dng *.orf *.pef *.3fr *.iiq);;All files (*)")
        if name:
            self.load(Path(name))

    def load(self, path: Path) -> None:
        self.path = path
        self.schedule()

    @Slot(object, object)
    def on_finished(self, image: np.ndarray, record: dict) -> None:
        self.busy = False
        self.image, self.record = image, record
        code = (np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        qimage = QImage(code.tobytes(), code.shape[1], code.shape[0], code.shape[1] * 3, QImage.Format.Format_RGB888)
        self.view.setPixmap(QPixmap.fromImage(qimage).scaled(self.view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.status.setText(f"{self.path.name}: {code.shape[1]} x {code.shape[0]}")
        if self.pending:
            self.pending = False
            self.schedule()
        elif self.after_render:
            self.after_render()

    @Slot(str)
    def on_failed(self, message: str) -> None:
        self.busy = False
        self.status.setText(message)
        if self.pending:
            self.pending = False
            self.schedule()
        elif self.after_render:
            self.after_render()

    @Slot()
    def export(self) -> None:
        if self.image is None:
            self.status.setText("Nothing to export.")
            return
        name, _ = QFileDialog.getSaveFileName(self, "Export", "", "TIFF 16 bit (*.tif);;JPEG (*.jpg)")
        if name:
            written = mp.write_outputs(self.image, self.record, Path(name))
            self.status.setText(f"Wrote {written[0]}")

    def closeEvent(self, event) -> None:  # noqa: N802 - name from Qt
        self.thread_.quit()
        self.thread_.wait()
        super().closeEvent(event)


def main() -> int:
    arguments = sys.argv[1:]
    screenshot = None
    if "--render-once" in arguments:
        index = arguments.index("--render-once")
        screenshot = Path(arguments[index + 1])
        arguments = arguments[:index] + arguments[index + 2:]
    app = QApplication(sys.argv[:1])
    window = MainWindow()
    window.show()
    if arguments:
        window.load(Path(arguments[0]))
    if screenshot:
        def finish() -> None:
            QTimer.singleShot(200, lambda: (window.grab().save(str(screenshot)), print(window.status.text()), window.close()))
        window.after_render = finish
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
