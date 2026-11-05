"""Review sheets of method negative_scan (step P14), with the stock and the method on every panel. Local only, because the inputs are photographs.

Input: RAW files (the list PHOTOS, or paths as arguments), decoded as the viewer does, with scene light 'as_shot' and the product grade.
Output: build/tmp/p14/review/<photo>.jpg, one sheet per photo: rows = stocks, columns = Lab Scan (the current default of method apd),
Negative Scan Neutral (auto off), Negative Scan Auto neutral, and Auto neutral with the comparison matrix 'film_primaries';
build/tmp/p14/review/scanner_<photo>.jpg: Portra 400, Neutral Scan, with other scanner bands; and build/tmp/p14/review/auto_records.json:
the cast and the shift of rule frame_auto_colour of each auto render.
Step: P14. Command: build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p14_negative_scan/render_negative_scan_review.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[0] / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

OUT = mp.REPO_ROOT / "build" / "tmp" / "p14" / "review"
RAW = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw")
PHOTOS = [RAW / "portrait/P1031513.RW2", RAW / "portrait/1099463.RW2", RAW / "signature_edits/se357.cr2", RAW / "signature_edits/se274.dng",
          RAW / "signature_edits/se222.arw", RAW / "film_emulation/5253219691.rw2", RAW / "night/P1031516.RW2",
          Path("D:/素材/照片/2026.6香格里拉/RAW/P2636154.RW2"), RAW / "landscape/_DSC4735.ARW", RAW / "daylight/5965296318.rw2"]
STOCKS = ("kodak_portra_400", "kodak_gold_200", "kodak_ektar_100", "kodak_5207")
COLUMNS = (("Lab Scan (apd default)", dict(method="apd")),
           ("Negative Scan, Neutral", dict(method="negative_scan")),
           ("Negative Scan, Auto neutral", dict(method="negative_scan", neg_scan_auto="neutral")),
           ("Neg. Scan, Auto neutral, film primaries (comparison)", dict(method="negative_scan", neg_scan_auto="neutral", neg_scan_primaries="film_primaries")))
SCANNERS = (("40 nm, 650/545/450 (default)", {}), ("20 nm bands", dict(neg_scan_width_nm=20.0)), ("80 nm bands", dict(neg_scan_width_nm=80.0)),
            ("red at 690 nm", dict(neg_scan_red_nm=690.0)), ("red at 620 nm", dict(neg_scan_red_nm=620.0)), ("black 0 (plain inversion)", dict(neg_scan_black=0.0)))
SCANNER_PHOTOS = 4
LONG_EDGE = 1400
PANEL = 900
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)


def write_sheet(path: Path, panels: list[tuple[str, np.ndarray]], columns: int) -> None:
    tiles = []
    for title, image in panels:
        tile = Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
        tile.thumbnail((PANEL, PANEL), Image.Resampling.LANCZOS)
        tiles.append((title, tile))
    height = max(t.height for _, t in tiles)
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (PANEL + 6), rows * (height + 36)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (title, tile) in enumerate(tiles):
        x, y = i % columns * (PANEL + 6), i // columns * (height + 36)
        sheet.paste(tile, (x + (PANEL - tile.width) // 2, y + 34))
        draw.text((x + 4, y + 4), title, fill=(235, 235, 235), font=FONT)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=92)


def render(pipeline: mp.Pipeline, ap1: np.ndarray, settings: mp.RenderSettings) -> tuple[np.ndarray, dict]:
    settings.validate()
    if settings.method != "negative_scan":
        return pipeline.render_array(ap1, settings), {}
    graded = mp.fp.fk.product_grade(np.ascontiguousarray(ap1, dtype=np.float32), float(settings.exposure_ev), float(settings.contrast), float(settings.saturation))
    image, info = pipeline.negative_scan_model(settings).render(np.ascontiguousarray(graded, dtype=np.float32))
    return np.asarray(image, dtype=np.float32), info


def main() -> int:
    photos = [Path(p) for p in sys.argv[1:]] or PHOTOS
    pipeline = mp.Pipeline()
    colorimetry = pipeline.colorimetry(mp.RenderSettings(method="negative_scan", negative=STOCKS[0]))
    decoded = {}
    for photo in photos:
        decoded[photo] = mp.decode_raw(photo, colorimetry, LONG_EDGE)[0]
        print("decoded", photo.name, flush=True)
    panels = {photo: [None] * (len(STOCKS) * len(COLUMNS)) for photo in photos}
    records = {}
    for row, stock in enumerate(STOCKS):
        name = mp.CATALOG["negatives"][stock]["name"]
        for photo in photos:
            start = time.time()
            # The scene light of each photo is part of the model, so the columns of one photo run together and share the scan table.
            for col, (label, fields) in enumerate(COLUMNS):
                settings = mp.resolve_as_shot(mp.RenderSettings(negative=stock, scene_light=mp.AS_SHOT, **fields), photo)
                image, info = render(pipeline, decoded[photo], settings)
                panels[photo][row * len(COLUMNS) + col] = (f"{name} | {label} | {settings.scene_light}", image)
                if info.get("auto", "off") != "off":
                    records.setdefault(photo.name, {})[f"{stock} | {label}"] = {k: info[k] for k in ("cast_log10", "along_light_axis", "shift_log10", "positive_below_0")}
            print(stock, photo.name, f"{time.time() - start:.0f}s", flush=True)
    for photo in photos:
        write_sheet(OUT / f"{photo.stem}.jpg", panels[photo], len(COLUMNS))
    for photo in photos[:SCANNER_PHOTOS]:
        sheet = []
        for label, fields in SCANNERS:
            settings = mp.resolve_as_shot(mp.RenderSettings(negative="kodak_portra_400", method="negative_scan", scene_light=mp.AS_SHOT, **fields), photo)
            sheet.append((f"Kodak Portra 400 | Neutral Scan | {label}", render(pipeline, decoded[photo], settings)[0]))
        write_sheet(OUT / f"scanner_{photo.stem}.jpg", sheet, 3)
        print("scanner sheet", photo.name, flush=True)
    (OUT / "auto_records.json").write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
