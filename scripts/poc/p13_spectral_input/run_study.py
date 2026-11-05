"""P13: verify spectral input candidates and render labelled Lab Scan comparisons.

Input: default RAW review set or supplied RAW paths. Output: local JPEG sheets,
per-stock rows, CAM16 measurements, errors, source hashes and a review index.
The film and scan implementations are used unchanged after layer exposure.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from dataclasses import asdict, replace
import hashlib
import html
import json
from pathlib import Path
import sys
import time
import types

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spectral_input import (  # noqa: E402
    ROOT, BATCH_PIXELS, PRIOR_POSITIVE_SHARE, SpectralInput, make_lights,
    read_raw_white, sr, sd, fp,
)
import mvp_pipeline as mp  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts/poc/p10_chart_scan"))
import scan_appearance as sa  # noqa: E402
import display_transforms as dt  # noqa: E402

RAW_ROOT = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw")
DEFAULT_FILES = [RAW_ROOT / "signature_edits/se357.cr2",
                 RAW_ROOT / "film_emulation/5253219691.rw2",
                 Path("D:/素材/照片/2026.6香格里拉/RAW/P2636154.RW2"),
                 RAW_ROOT / "signature_edits/se188.nef",
                 RAW_ROOT / "signature_edits/se274.dng"]
STOCKS = ("kodak_5219", "kodak_5207", "kodak_portra_400", "kodak_gold_200")
CASES = {
    "current_light": ("CCT / current light prior", "cct", "light", False),
    "current_measured": ("CCT / measured prior", "cct", "measured", False),
    "white_smooth": ("Full white / smooth", "smooth", "measured", False),
    "white_led": ("Full white / LED", "led", "measured", False),
    "white_fluorescent": ("Full white / fluorescent", "fluorescent", "measured", False),
    "conditioned_smooth": ("Constrained / smooth", "smooth", "measured", True),
    "conditioned_led": ("Constrained / LED", "led", "measured", True),
}


def write_json(path: Path, value: dict) -> None:
    """Write LF JSON; reject non-finite numbers."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n",
                    encoding="utf-8", newline="\n")


def peak_working_set() -> int:
    """Read the Windows process peak working set in bytes."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak_working", "working", "peak_paged",
            "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.peak_working)


@contextmanager
def injected_exposure(negative, expected_image: np.ndarray, q: np.ndarray,
                      moved: int, black: int):
    """Replace only the layer integral for one synchronous render, then restore it."""
    original = fp.fk.layer_exposure

    def supplied(image, *_args):
        if image.shape != expected_image.shape or not np.array_equal(image, expected_image):
            raise ValueError("exposure injection received a different input image")
        return np.asarray(q, dtype=np.float32).copy(), moved, black

    fp.fk.layer_exposure = supplied
    try:
        yield
    finally:
        fp.fk.layer_exposure = original


def set_scene(scan, spectrum: np.ndarray, rho: np.ndarray) -> None:
    """Install only this case's scene light and input table on the review instance."""
    n = scan.negative
    if not hasattr(n, "p13_original_light"):
        n.p13_original_light = n.light
    scene_name = n.options.scene_light

    def light(self, name):
        return spectrum if name == scene_name else self.p13_original_light(name)

    n.light = types.MethodType(light, n)
    n.scene_spectrum = spectrum
    n.layer_gain = n._camera_filter()
    n.uv_table = n.c.layer_exposure(rho.reshape(-1, len(spectrum))*spectrum).reshape(
        fp.UV_NODES, fp.UV_NODES, 3)
    n._prepare_kernels()
    scan.pivot = scan.grey_apd(scene_name)
    scan.axis = None


def verify(engine: SpectralInput, scans: dict) -> dict:
    """Check the actual operations and the tolerances declared in README."""
    c = engine.c
    # This is a known-spectrum forward test, not a fit to output chart colours.
    samples = sd.load_rawtoaces_training().reflectance[:32]
    e = fp.cct_light(4138, c.wavelengths, c.xyz)
    e /= c.xyz(e)[1]
    wb = fp.bradford_matrix(c.xyz(e), c.white_ref)
    xyz = c.xyz(samples*e) @ wb.T
    normalized = xyz / xyz[:, 1, None]
    rho = engine.prior(normalized)
    target = normalized @ np.linalg.inv(wb).T
    radiance, metrics = engine.condition((rho+PRIOR_POSITIVE_SHARE)*e, target)
    closed = c.xyz(radiance) @ wb.T
    closure = float(np.max(np.abs(closed-normalized)) / np.max(np.abs(normalized)))
    scaled, _ = engine.condition(3.25*(rho+PRIOR_POSITIVE_SHARE)*e, 3.25*target)
    scaling = float(np.max(np.abs(scaled-3.25*radiance)) / np.max(np.abs(3.25*radiance)))
    if closure > 1e-8 or scaling > 1e-9:
        raise AssertionError(f"spectral consistency failed: {closure=}, {scaling=}")
    test = np.array([[[0.18, 0.18, 0.18], [0.27, 0.18, 0.13],
                      [0.10, 0.16, 0.30], [0.06, 0.10, 0.04]]], dtype=np.float32)
    scan = scans[STOCKS[0]]
    n = scan.negative
    n.options = replace(n.options, light_spectra=False)
    set_scene(scan, e, engine.shapes["measured"])
    scan.timing = 1.0
    scan.offset = scan._adx_offset()
    base, _ = scan.render(test)
    q, stats = n.layer_exposure(test)
    with injected_exposure(n, test, q, stats["moved_by_rule"], stats["y_not_positive"]):
        injected, _ = scan.render(test)
    injection_error = float(np.max(np.abs(injected-base)))
    stream, _ = engine.exposures(test, e, {STOCKS[0]: n}, False)
    stream_q = stream[STOCKS[0]] * n.layer_gain
    relative = float(np.max(np.abs(stream_q-q) / np.maximum(np.abs(q), 1e-20)))
    if injection_error > 1e-6 or relative > 2e-6:
        raise AssertionError(f"unchanged film stages failed: {injection_error=}, {relative=}")
    return {"spectral_solver": metrics, "forward_adapted_XYZ_relative_max": closure,
            "exposure_scaling_relative_max": scaling,
            "injected_display_max_abs": injection_error,
            "streamed_table_exposure_relative_max": relative}


def appearance_metrics(code: np.ndarray, reference: dict, display) -> dict:
    """Describe CAM16 changes; do not rank a look by these measurements."""
    appearance = display.appearance(code.reshape(-1, 3))
    difference = np.linalg.norm(appearance["UCS"]-reference["UCS"], axis=1)
    chroma = np.hypot(reference["UCS"][:, 1], reference["UCS"][:, 2])
    coloured = chroma > 6
    neutral = chroma < 6
    cast = np.mean(appearance["UCS"][neutral,1:] - reference["UCS"][neutral,1:], axis=0) if neutral.any() else None
    ratio = np.hypot(appearance["UCS"][:, 1], appearance["UCS"][:, 2])[coloured] / chroma[coloured]
    return {"distance_from_no_film_p50": float(np.median(difference)),
            "near_neutral_delta_a_b": cast.tolist() if cast is not None else None,
            "colourfulness_ratio_mean": float(np.mean(ratio)) if len(ratio) else None}


def draw_sheet(out: Path, stem: str, timing: str, columns: list,
               images: dict, metrics: dict, nofilm: np.ndarray, font) -> None:
    """Write full sheet and a readable row per stock; errors remain visible."""
    h, w = nofilm.shape[:2]
    header = 64
    rows = []
    for stock in STOCKS:
        row = Image.new("RGB", ((w+8)*(len(columns)+1), h+header), (20, 20, 20))
        draw = ImageDraw.Draw(row)
        row.paste(Image.fromarray((nofilm*255+0.5).astype(np.uint8)), (0, header))
        draw.text((8, 5), f"{stem} | no film\nscene balance {timing}; character 1", font=font, fill="white")
        for column, case in enumerate(columns, 1):
            left = column*(w+8)
            key = (timing, stock, case)
            draw.text((left+8, 5), f"{stock}\n{CASES[case][0]}", font=font, fill="white")
            if key in images:
                row.paste(Image.fromarray((images[key]*255+0.5).astype(np.uint8)), (left, header))
                value = metrics["renders"][f"{timing}/{stock}/{case}"]["appearance"]
                draw.text((left+8, 43), f"M ratio {value['colourfulness_ratio_mean']:.2f}", font=font, fill=(220,220,220))
            else:
                draw.text((left+12, header+20), "FAILED: see measurements.json\nNo substitute image", font=font, fill=(255,160,140))
        row.save(out / f"{stem}_{timing}_{stock}.jpg", quality=94, subsampling=0)
        rows.append(row)
    sheet = Image.new("RGB", (rows[0].width, sum(row.height for row in rows)), (20,20,20))
    y = 0
    for row in rows:
        sheet.paste(row, (0,y))
        y += row.height
    sheet.save(out / f"{stem}_{timing}.jpg", quality=94, subsampling=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--cases", nargs="+", choices=list(CASES), default=list(CASES))
    parser.add_argument("--out", type=Path, default=ROOT / "build/tmp/p13")
    args = parser.parse_args()
    files = args.files or DEFAULT_FILES
    for path in files:
        if not path.exists():
            raise FileNotFoundError(path)
    args.out.mkdir(parents=True, exist_ok=True)
    sources_dir = args.out / "sources"
    sources_dir.mkdir(exist_ok=True)
    started = time.perf_counter()
    pipeline = mp.Pipeline()
    settings = mp.RenderSettings(method="apd", scene_light="CCT4138", apd_axis="numbers",
                                 stock_character=1.0, apd_lad_aim=True)
    scans = {name: pipeline.scan_model(replace(settings, negative=name)) for name in STOCKS}
    if any(scan.negative.options.scene_flare != 0 for scan in scans.values()):
        raise ValueError("P13 direct spectral input requires the unchanged default scene flare to be zero")
    c = scans[STOCKS[0]].negative.c
    engine = SpectralInput(c)
    checks = verify(engine, scans)
    print(f"P13 checks passed: {checks}", flush=True)
    result = {"settings": asdict(settings), "checks": checks, "photos": {},
              "grid_nm": [360,840,1], "review_long_edge": args.width,
              "prior_positive_share": PRIOR_POSITIVE_SHARE, "cases": args.cases,
              "batch_pixels": BATCH_PIXELS, "GPU_used": False,
              "source_note": "Existing local sources reused; no downloads; see source hashes."}
    font = ImageFont.load_default(size=17)
    display = sa.Display(fp)
    failed = 0
    for path in files:
        print(f"PHOTO {path.name}", flush=True)
        photo_started = time.perf_counter()
        white = read_raw_white(path)
        lights, light_records = make_lights(c, white)
        ap1, decode = mp.decode_raw(path, c, args.width)
        graded = np.ascontiguousarray(fp.fk.product_grade(ap1, float(settings.exposure_ev),
                                      float(settings.contrast), float(settings.saturation)), dtype=np.float32)
        nofilm = np.asarray(dt.render_native("opendrt", graded, fp.srgb_encode))
        reference = display.appearance(nofilm.reshape(-1,3))
        photo = {"path": str(path), "RAW_white_XYZ": white.xyz.tolist(),
                 "RAW_cct_K": white.cct, "lights": light_records, "decode": decode,
                 "spectral_solves": {}, "renders": {}, "failures": {}, "stock_separation": {}}
        images = {}
        for case in args.cases:
            label, family, prior, conditioned = CASES[case]
            spectrum = lights[family]
            q_by_stock = None
            try:
                if conditioned:
                    q_by_stock, stats = engine.exposures(graded, spectrum,
                                          {name: scan.negative for name, scan in scans.items()}, True)
                    photo["spectral_solves"][case] = stats
                for stock, scan in scans.items():
                    set_scene(scan, spectrum, engine.shapes[prior])
                    n = scan.negative
                    for timing_name, timing_value in (("balance0", 0.0), ("balance1", 1.0)):
                        scan.timing = timing_value
                        scan.offset = scan._adx_offset()
                        if conditioned:
                            with injected_exposure(n, graded, q_by_stock[stock]*n.layer_gain,
                                      stats["moved_by_existing_locus_rule"], stats["Y_not_positive"]):
                                code, render_stats = scan.render(graded)
                        else:
                            code, render_stats = scan.render(graded)
                        if not np.isfinite(code).all():
                            raise FloatingPointError(f"{case}/{stock}: non-finite scan")
                        images[timing_name, stock, case] = code
                        photo["renders"][f"{timing_name}/{stock}/{case}"] = {
                            "appearance": appearance_metrics(code, reference, display), "stats": render_stats}
                print(f"  {case} rendered", flush=True)
            except (ValueError, RuntimeError, FloatingPointError, np.linalg.LinAlgError) as error:
                # The failed case remains visibly unavailable; nothing is substituted.
                photo["failures"][case] = f"{type(error).__name__}: {error}"
                for key in list(images):
                    if key[2] == case:
                        del images[key]
                failed += 1
                print(f"  FAILED {case}: {error}", flush=True)
        for timing in ("balance0", "balance1"):
            for case in args.cases:
                if all((timing, stock, case) in images for stock in STOCKS):
                    ucs = {stock: display.appearance(images[timing, stock, case].reshape(-1,3))["UCS"]
                           for stock in STOCKS}
                    pairs = {}
                    for a, b in ((STOCKS[0], STOCKS[1]), (STOCKS[2], STOCKS[3])):
                        distance = np.linalg.norm(ucs[a]-ucs[b], axis=1)
                        pairs[f"{a}/{b}"] = {"p50": float(np.median(distance)),
                                             "p95": float(np.percentile(distance,95))}
                    photo["stock_separation"][f"{timing}/{case}"] = pairs
            draw_sheet(args.out, path.stem, timing, args.cases, images, photo, nofilm, font)
        photo["seconds"] = time.perf_counter()-photo_started
        result["photos"][path.stem] = photo
        result["peak_working_set_bytes"] = peak_working_set()
        result["total_seconds"] = time.perf_counter()-started
        write_json(args.out / "measurements.json", result)
        print(f"  photo complete, peak working set {result['peak_working_set_bytes']/2**20:.0f} MiB", flush=True)
    hashes = {}
    paths = list(Path(__file__).parent.glob("*.*")) + [
        ROOT / "scripts/poc/p6_mvp_gui/mvp_pipeline.py",
        ROOT / "scripts/poc/p2_negative_print/film_preview.py",
        ROOT / "scripts/poc/p3_scan_and_scene/aces_scan.py",
        ROOT / "scripts/poc/p10_chart_scan/scan_generic.py",
        ROOT / "build/tmp/p1/sources/CIE_illum_LEDs.csv",
        ROOT / "build/tmp/p1/sources/CIE_illum_FLs.csv",
        ROOT / "build/tmp/p2/tables/reflectance_over_uv_smooth_0.006_0.025.npy",
        ROOT / "build/tmp/p2/tables/reflectance_over_uv_light_0.006_0.025.npy"]
    for source in paths:
        hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    write_json(sources_dir / "local_source_hashes.json", hashes)
    body = ["<!doctype html><meta charset='utf-8'><title>P13 spectral input review</title>",
            "<style>body{background:#181818;color:#eee;font:16px system-ui;margin:24px}img{max-width:none;width:100%}a{color:#a9cfff}section{overflow:auto}figure{margin:24px 0}</style>",
            "<h1>P13 spectral input review</h1><p>Same scan and stock character 1. "
            "Left to right: no film, then the labelled input cases. Balance 0 retains "
            "the stock-balance scene response; balance 1 applies the current scene-grey scan timing. "
            "These are constructed light families, not measured lamps. Failed cases have no substitute.</p>",
            "<p><a href='measurements.json'>Measurements and errors</a></p>"]
    for path in files:
        body.append(f"<h2>{html.escape(path.stem)}</h2>")
        for timing in ("balance0", "balance1"):
            name = f"{path.stem}_{timing}.jpg"
            body.append(f"<figure><figcaption>{timing} | <a href='{name}'>full sheet</a></figcaption>"
                        f"<a href='{name}'><img src='{name}'></a></figure>")
            for stock in STOCKS:
                row = f"{path.stem}_{timing}_{stock}.jpg"
                body.append(f"<a href='{row}'>{stock} / {timing}</a> &nbsp; ")
    (args.out / "review.html").write_text("\n".join(body)+"\n", encoding="utf-8", newline="\n")
    print(f"DONE {args.out}; failed cases={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
