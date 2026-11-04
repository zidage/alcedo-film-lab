"""Review sheets of rule 'chart_calibrated_scan' (step P10, ROADMAP U87). Local only: the photos are not committed.

Input: RAW files of the Alcedo Studio sample images (alcedo_studio/tests/resources/sample_images/raw/), decoded by mvp_pipeline.decode_raw,
with the product input of P2 (rule 'center_weighted_exposure' and the default grade).
Output: build/tmp/p10/review/<stock>.jpg, one row per photo, a label on every panel:
the digital input through the same display (rule 'chart_scan_display'), then the scan with each variant of VARIANTS.
results/p10_chart_scan/review.json: the clipped share of each panel.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import chart_scan as cs  # noqa: E402
import mvp_pipeline as mp  # noqa: E402

RAW = Path(r"D:\Projects\pu-erh_lab\alcedo_studio\tests\resources\sample_images\raw")
PHOTOS = ("portrait/P1031513.RW2", "plant/_DSC0180.ARW", "daylight/0691416133.dng", "cat/_DSC1103.NEF", "film_emulation/212A8758.CR3", "street/_DSC0155.NEF")
# Option --more: a second set of sample files, written to review4_more/ (the user asked for other photos).
MORE = ("portrait/1099463.RW2", "landscape/_DSC9729.ARW", "artificial_lights/3754960364.dng", "night/4928099113.nef", "daylight/5897833591.dng",
        "film_emulation/4516784837.dng", "airplane/_DSC1704.NEF", "signature_edits/credit @ryanbreitkreutz P1073454.RW2", "item/_DSC0915.ARW")
if "--more" in sys.argv:
    PHOTOS = MORE
STOCKS = ("kodak_portra_400", "kodak_5207", "kodak_ektar_100", "kodak_5219")
LONG_EDGE = 1200
# Name: options of ChartScanPreview. Round 4 of the P10 report. The first variant also shows the digital input (rule 'chart_scan_display').
LOG = dict(matrix=False, inversion="straight", output="log_curve")
VARIANTS = {"log curve (round 3)": LOG, "log curve + sensitivity matrix + scan timing": {**LOG, "sensitivity_matrix": True, "scan_timing": 1.0},
            "same + display compression": {**LOG, "sensitivity_matrix": True, "scan_timing": 1.0, "display_compress": True}}
OUT = cs.REPO_ROOT / "build" / "tmp" / "p10" / ("review4_more" if "--more" in sys.argv else "review4")
RESULT = cs.REPO_ROOT / "results" / "p10_chart_scan" / ("review4_more.json" if "--more" in sys.argv else "review4.json")


def label(image: np.ndarray, text: str) -> Image.Image:
    panel = Image.fromarray((np.clip(image, 0, 1) * 255 + 0.5).astype(np.uint8))
    draw = ImageDraw.Draw(panel)
    font = ImageFont.load_default(size=22)
    box = draw.textbbox((10, 8), text, font=font)
    draw.rectangle((box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4), fill=(0, 0, 0))
    draw.text((10, 8), text, fill=(255, 255, 255), font=font)
    return panel


def main() -> int:
    chart = cs.babelcolor_chart()
    OUT.mkdir(parents=True, exist_ok=True)
    models = {}
    inputs = []
    for stock in STOCKS:
        options = mp.film_options(mp.RenderSettings(negative=stock, method="apd"), mp.SCAN_CARRIER_PRINT)
        models[stock] = {name: cs.ChartScanPreview(options, chart, **kwargs) for name, kwargs in VARIANTS.items()}
    c = next(iter(models[STOCKS[0]].values())).negative.c
    for photo in PHOTOS:
        ap1, _ = mp.decode_raw(RAW / photo, c, LONG_EDGE)
        inputs.append((photo, np.ascontiguousarray(cs.fp.product_input(ap1, c), dtype=np.float32)))
    report = {}
    for stock in STOCKS:
        variants = models[stock]
        display = next(iter(variants.values()))
        rows = []
        report[stock] = {}
        for photo, image in inputs:
            pixels = image.shape[0] * image.shape[1]
            digital, digital_clip = display.display(image.astype(np.float64))
            panels = [label(digital, f"digital, same display  {photo}")]
            entry = {"clipped_share": {"digital": round(digital_clip / pixels, 4)}, "record_outside_curve": {}}
            for name, model in variants.items():
                out, stats = model.render(image)
                entry["clipped_share"][name] = round(stats["display_clipped"] / pixels, 4)
                entry["record_outside_curve"][name] = stats["record_outside_curve"]
                panels.append(label(out, f"{stock} scan, {name}"))
            report[stock][photo] = entry
            print(stock, photo, json.dumps(entry), flush=True)
            row = Image.new("RGB", (sum(p.width for p in panels), panels[0].height))
            x = 0
            for p in panels:
                row.paste(p, (x, 0))
                x += p.width
            rows.append(row)
        width = max(r.width for r in rows)
        sheet = Image.new("RGB", (width, sum(r.height for r in rows)), (20, 20, 20))
        y = 0
        for r in rows:
            sheet.paste(r, (0, y))
            y += r.height
        sheet.save(OUT / f"{stock}.jpg", quality=90)
    RESULT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
