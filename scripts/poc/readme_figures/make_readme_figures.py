"""Make the figures of the root README, with a label on every panel.

Input: the RAW files of build/tmp/baseline/signature_edits/raw/ listed in FILES, and the two local files of the owner in OWNER_RAW; the profiles; the tables of P6; the arrays of render_spektrafilm_figures.py.
Output: docs/images/*.jpg and *.png. Step: P6, ROADMAP U65.
Usage: make_readme_figures.py decode, then render_spektrafilm_figures.py in its environment, then make_readme_figures.py figures.
Rule 'no_recognizable_person': the license of the source does not grant the image of a recognizable person, a brand, or a work of art (see docs/images/CREDITS.md), so FILES holds landscapes and still lifes only. Portraits stay local.
Rule 'owner_photo_exposure': the two photos of the owner are underexposed, so they take the exposure of EXPOSURE_EV in the product grade in place of +1.5 EV (user choice, ROADMAP U66).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p6_mvp_gui"))
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p4_physical_film_response"))
import mvp_pipeline as mp  # noqa: E402
from fit_mtf import BOUNDS, response  # noqa: E402

fp = mp.fp
BASE = ROOT / "build" / "tmp" / "readme_figures"
INPUT = BASE / "input"
OUT = ROOT / "docs" / "images"
RAW = ROOT / "build" / "tmp" / "baseline" / "signature_edits" / "raw"
FILES = ("se357", "se069", "se368", "se034")
OWNER_RAW = {name: Path(f"D:/素材/照片/2026.5香港/香港/{name}.RW2") for name in ("P2625280", "P2625314")}
EXPOSURE_EV = {name: 3.0 for name in OWNER_RAW}
LONG_EDGE = 1400
FONT = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
S5207 = mp.RenderSettings()
PORTRA = mp.RenderSettings(negative="kodak_portra_400", print_material="kodak_endura_premier")
SERIES = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a"}
RECORD = {"red": "#c8352b", "green": "#008300", "blue": "#2a78d6"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def exposed(name: str, settings: mp.RenderSettings) -> mp.RenderSettings:
    return replace(settings, exposure_ev=EXPOSURE_EV.get(name, settings.exposure_ev))


def load(name: str) -> np.ndarray:
    return np.ascontiguousarray(np.load(INPUT / f"{name}.npy"), dtype=np.float32)


def spektra(name: str, key: str) -> np.ndarray:
    return np.load(BASE / "spektrafilm" / f"{name}_{key}.npy")


def plain(ap1: np.ndarray, exposure_ev: float = S5207.exposure_ev) -> np.ndarray:
    """The input with the product exposure and no film: AP1 to linear Rec. 709 with Bradford adaptation, clip, sRGB encoding."""
    c = mp.Pipeline().colorimetry(S5207)
    matrix = fp.XYZ_TO_REC709 @ fp.bradford_matrix(c.ap1_to_xyz @ np.ones(3), fp.XYZ_D65) @ c.ap1_to_xyz
    return fp.srgb_encode(np.clip((ap1 * 2.0 ** exposure_ev) @ matrix.T, 0.0, 1.0))


def sheet(path: Path, panels: list[tuple[str, np.ndarray]], columns: int, width: int = 620) -> None:
    tiles = []
    for title, image in panels:
        tile = Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
        tile = tile.resize((width, round(tile.height * width / tile.width)), Image.Resampling.LANCZOS if tile.width > width else Image.Resampling.BICUBIC)
        tiles.append((title, tile))
    heights = [max(t.height for _, t in tiles[i:i + columns]) for i in range(0, len(tiles), columns)]
    canvas = Image.new("RGB", (columns * (width + 6) + 6, sum(h + 40 for h in heights) + 6), (18, 18, 18))
    draw = ImageDraw.Draw(canvas)
    for i, (title, tile) in enumerate(tiles):
        height = heights[i // columns]
        x, y = 6 + i % columns * (width + 6), 6 + sum(h + 40 for h in heights[:i // columns])
        draw.text((x + 2, y + 3), title, fill=(236, 236, 236), font=FONT)
        canvas.paste(tile, (x + (width - tile.width) // 2, y + 34 + (height - tile.height) // 2))
    OUT.mkdir(parents=True, exist_ok=True)
    canvas.save(path, quality=88, optimize=True)
    print(path.name, canvas.size, path.stat().st_size // 1024, "KB", flush=True)


def decode() -> None:
    INPUT.mkdir(parents=True, exist_ok=True)
    c = mp.Pipeline().colorimetry(S5207)
    for name in (*FILES, *OWNER_RAW):
        path = OWNER_RAW.get(name) or next(RAW.glob(f"{name}.*"))
        ap1, record = mp.decode_raw(path, c, LONG_EDGE)
        np.save(INPUT / f"{name}.npy", ap1)
        print(name, ap1.shape, record, flush=True)


def stages(p: mp.Pipeline) -> None:
    ap1 = load("se357")
    settings = replace(S5207, method="apd")
    graded = np.ascontiguousarray(fp.fk.product_grade(ap1, 1.5, float(fp.PRODUCT_CONTRAST), float(fp.PRODUCT_SATURATION)), dtype=np.float32)
    model = p.scan_model(settings)
    apd = model.table_apd(model.negative.negative_image(graded)[0])
    negative = fp.srgb_encode(np.clip(10.0 ** -apd * 1.1, 0.0, 1.0))
    sheet(OUT / "stages.jpg", [("1. Input with product exposure, no film", plain(ap1)), ("2. Simulated 5207 negative, with its orange base", negative),
                               ("3a. Print on simulated 2383", p.render_array(ap1, S5207)), ("3b. APD scan, ADX10, ACES 2.0 output", p.render_array(ap1, settings))], 2)


def hero(p: mp.Pipeline) -> None:
    panels = []
    for name in ("P2625280", "P2625314", "se368"):
        ap1 = load(name)
        panels += [("No film", plain(ap1, EXPOSURE_EV.get(name, S5207.exposure_ev))), ("5207 + 2383, print", p.render_array(ap1, exposed(name, S5207))), ("Portra 400 + Endura, print", p.render_array(ap1, exposed(name, PORTRA)))]
    sheet(OUT / "hero.jpg", panels, 3, 470)


def against_spektrafilm(p: mp.Pipeline) -> None:
    panels = []
    for name in ("se357", "P2625280", "P2625314"):
        ap1 = load(name)
        panels += [("This lab: 5207 + 2383, print", p.render_array(ap1, exposed(name, S5207))), ("spektrafilm: Vision3 250D + 2383", spektra(name, "5207")),
                   ("This lab: Portra 400 + Endura", p.render_array(ap1, exposed(name, PORTRA))), ("spektrafilm: Portra 400 + Endura", spektra(name, "portra"))]
    sheet(OUT / "against_spektrafilm.jpg", panels, 4, 390)


def stocks(p: mp.Pipeline) -> None:
    ap1 = load("se357")
    panels = []
    for negative in mp.ACCEPTED_STOCKS:
        material = "kodak_2383" if mp.CATALOG["negatives"][negative]["medium"].lower() == "cine" else "kodak_endura_premier"
        short = "2383" if material == "kodak_2383" else "Endura"
        panels.append((f"{mp.CATALOG['negatives'][negative]['name'].removeprefix('Kodak ')} + {short}", p.render_array(ap1, replace(S5207, negative=negative, print_material=material))))
    sheet(OUT / "stocks.jpg", panels, 4, 390)


def lights(p: mp.Pipeline) -> None:
    ap1 = load("se034")
    panels = [(f"5219 + 2383, timing 0 | light: {light}", p.render_array(ap1, replace(S5207, negative="kodak_5219", print_timing=0.0, scene_light=light))) for light in ("reference", "daylight", "tungsten", "fluorescent", "led", "street_mixed")]
    sheet(OUT / "scene_lights.jpg", panels, 3, 470)


def controls(p: mp.Pipeline) -> None:
    ap1 = load("se069")
    cases = [("Default: print contrast 0.85, flash 0.02", {}), ("Print contrast 1.2", {"print_contrast": 1.2}), ("Print contrast 0.6", {"print_contrast": 0.6}), ("Paper flash 0.1", {"print_flash": 0.1}), ("Print grey shift +0.2", {"print_grey_shift": 0.2}), ("Overexposure +2 stops", {"overexposure_stops": 2.0})]
    sheet(OUT / "controls.jpg", [(title, p.render_array(ap1, replace(S5207, **change))) for title, change in cases], 3, 470)
    night = load("se034")
    h, w = night.shape[:2]
    crop = (slice(int(h * 0.30), int(h * 0.62)), slice(int(w * 0.30), int(w * 0.72)))
    cases = [("Halation 0", 0.0), ("Halation 1 (default)", 1.0), ("Halation 8", 8.0)]
    sheet(OUT / "halation.jpg", [(title, p.render_array(night, replace(S5207, halation_scale=value))[crop]) for title, value in cases], 3, 470)


def prior(p: mp.Pipeline) -> None:
    panels = []
    for name in ("se357", "se069"):
        ap1 = load(name)
        panels += [(f"Light-like spectra (default)", p.render_array(ap1, S5207)), ("Measured reflectance prior", p.render_array(ap1, replace(S5207, spectral_prior="measured_reflectance")))]
    sheet(OUT / "spectral_prior.jpg", panels, 4, 390)


def style(plt) -> None:
    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 11, "axes.edgecolor": MUTED, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "lines.linewidth": 2.0, "savefig.dpi": 150})


def stock_data(plt) -> None:
    profile = fp.p0.load_profile("kodak_5207")["charts"]
    figure, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    for (name, curve), colour in zip(profile["characteristic"]["curves"].items(), RECORD.values()):
        axes[0].plot(curve["x"], curve["y"], color=colour, label=name)
    axes[0].set(title="", xlabel="log10 exposure (lux s)", ylabel="Status M density")
    axes[0].set_title("Characteristic curves", loc="left", fontsize=12)
    axes[0].legend(frameon=False)
    for (name, curve), colour in zip(profile["spectral_sensitivity"]["curves"].items(), RECORD.values()):
        axes[1].plot(curve["x"], curve["y"], color=colour, label=name.replace("_forming_layer", " layer"))
    axes[1].set(xlabel="Wavelength (nm)", ylabel="log10 sensitivity")
    axes[1].set_title("Spectral sensitivity", loc="left", fontsize=12)
    axes[1].set_ylim(top=3.3)
    axes[1].legend(frameon=False, loc="upper center", ncol=3, fontsize=9)
    dyes = profile["spectral_dye_density"]["curves"]
    for (name, label), colour in zip((("cyan_dye", "cyan dye"), ("magenta_dye", "magenta dye"), ("yellow_dye", "yellow dye")), RECORD.values()):
        axes[2].plot(dyes[name]["x"], dyes[name]["y"], color=colour, label=label)
    axes[2].plot(dyes["minimum_density"]["x"], dyes["minimum_density"]["y"], color=MUTED, linestyle="--", label="base (D-min)")
    axes[2].set(xlabel="Wavelength (nm)", ylabel="Spectral density")
    axes[2].set_title("Dyes and orange base", loc="left", fontsize=12)
    axes[2].set_ylim(top=1.3)
    axes[2].legend(frameon=False, loc="upper center", ncol=2, fontsize=9)
    figure.tight_layout()
    figure.savefig(OUT / "stock_data_5207.png")
    print("stock_data_5207.png", flush=True)


def mtf(plt) -> None:
    from scipy.optimize import least_squares

    curves = fp.p0.load_profile("kodak_5207")["charts"]["modulation_transfer"]["curves"]
    figure, axis = plt.subplots(figsize=(6.4, 3.9))
    for name, colour in RECORD.items():
        x, y = np.array(curves[name]["x"]), np.array(curves[name]["y"])
        fit = least_squares(lambda v: response(x, *v) - y, (4.0, 15.0, 1.2), bounds=BOUNDS)
        axis.plot(x, y, color=colour, linewidth=2.0, label=f"{name}: spread {fit.x[0]:.1f} um, boost {fit.x[2]:.2f}")
        axis.plot(x, response(x, *fit.x), color=INK, linestyle=":", linewidth=1.2)
    axis.set_xscale("log")
    axis.set_xticks([3, 5, 10, 20, 40, 70], labels=["3", "5", "10", "20", "40", "70"])
    axis.minorticks_off()
    axis.set(xlabel="Spatial frequency (cycles/mm)", ylabel="Response")
    axis.set_title("5207 modulation transfer (colour), model fit (dotted)", loc="left", fontsize=12)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(OUT / "mtf_fit_5207.png")
    print("mtf_fit_5207.png", flush=True)


def sky_spectrum(p: mp.Pipeline, plt) -> None:
    model = p.print_model(S5207)
    c = model.c
    white = c.xyz(c.e_ref)
    white_uv = np.array([4.0 * white[0], 9.0 * white[1]]) / (white[0] + 15.0 * white[1] + 3.0 * white[2])
    wl = c.wavelengths
    sky = c.xyz(c.e_ref * (550.0 / wl) ** 4)
    sky_uv = np.array([4.0 * sky[0], 9.0 * sky[1]]) / (sky[0] + 15.0 * sky[1] + 3.0 * sky[2])
    u, v = model.uv_axes()
    index = (int(np.argmin(np.abs(u - sky_uv[0]))), int(np.argmin(np.abs(v - sky_uv[1]))))
    near, far = model.options.uv_smooth
    smooth = np.load(fp.CACHE_DIR / f"reflectance_over_uv_smooth_{near}_{far}.npy").reshape(fp.UV_NODES, fp.UV_NODES, -1)[index]
    light = np.load(fp.CACHE_DIR / f"reflectance_over_uv_light_{near}_{far}.npy").reshape(fp.UV_NODES, fp.UV_NODES, -1)[index]
    truth = (550.0 / wl) ** 4
    keep = (wl >= 380.0) & (wl <= 780.0)
    scale = lambda s: s / s[(wl >= 540) & (wl <= 560)].mean()  # noqa: E731
    figure, axis = plt.subplots(figsize=(6.4, 3.9))
    for values, label, colour in ((scale(truth), "Rayleigh sky spectrum", SERIES["aqua"]), (scale(smooth), "Measured reflectance prior", SERIES["orange"]), (scale(light), "Rule light_like_spectra", SERIES["blue"])):
        axis.plot(wl[keep], values[keep], color=colour, label=label)
    axis.set(xlabel="Wavelength (nm)", ylabel="Relative radiance (550 nm = 1)")
    axis.set_title(f"One sky colour (u'v' {sky_uv[0]:.3f}, {sky_uv[1]:.3f}), white at {white_uv[0]:.3f}, {white_uv[1]:.3f}", loc="left", fontsize=11)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(OUT / "sky_spectrum.png")
    print("sky_spectrum.png", flush=True)


def window() -> None:
    import os

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["QT_QPA_FONTDIR"] = "C:/Windows/Fonts"
    from PySide6.QtWidgets import QApplication

    import p6_mvp_gui as gui

    app = QApplication([])
    w = gui.MainWindow()
    w.resize(1500, 1050)
    w.show()
    path = next(RAW.glob("se357.*"))
    w.status.setText("")

    def finish() -> None:
        w.grab().save(str(OUT / "window.png"))
        print("window.png", flush=True)
        w.close()
        app.quit()

    w.after_render = finish
    w.load(path)
    app.exec()


def figures(only: list[str]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    style(plt)
    p = mp.Pipeline()
    steps = {"stages": lambda: stages(p), "hero": lambda: hero(p), "against_spektrafilm": lambda: against_spektrafilm(p), "stocks": lambda: stocks(p), "lights": lambda: lights(p), "controls": lambda: controls(p), "prior": lambda: prior(p),
             "stock_data": lambda: stock_data(plt), "mtf": lambda: mtf(plt), "sky_spectrum": lambda: sky_spectrum(p, plt), "window": window}
    for name in only or steps:
        steps[name]()


if __name__ == "__main__":
    if sys.argv[1] == "decode":
        decode()
    else:
        figures(sys.argv[2:])
