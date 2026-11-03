"""Review sheets of the reversal films on the light table, with a label on every panel. Local only, because the inputs are photographs.

Input: AP1 arrays of the earlier steps under build/tmp/ (names below, or the arguments). Output: build/tmp/p9/review/films_<n>.jpg (rows: files; columns: the five films and the default print of the viewer, 5207 on Endura Premier,
as a comparison) and build/tmp/p9/review/lights_<film>.jpg (the scene lights on one film; a slide keeps the cast of a light). Step: P9, ROADMAP U86.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[0] / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

OUT = mp.REPO_ROOT / "build" / "tmp" / "p9" / "review"
ROOTS = ["p3/input", "p4/input_shangrila", "p4/input_night"]
FILES = ["leica_m11", "sony_a7r6", "fuji_gfx100s", "se275", "se034", "se015", "se228", "se197", "se127", "hasselblad_x2dii", "nikon_zf", "se091", "nikon_z5", "canon_r5ii", "sony_a7cii", "_DSC4071", "P1031516", "2136729222"]
ROWS_PER_SHEET = 6
PANEL = (420, 300)
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)


def read_input(name: str) -> np.ndarray:
    for root in ROOTS:
        path = mp.REPO_ROOT / "build" / "tmp" / root / f"{name}.npy"
        if path.exists():
            return np.ascontiguousarray(np.load(path), dtype=np.float32)
    raise FileNotFoundError(name)


def write_sheet(path: Path, panels: list[tuple[str, np.ndarray]], columns: int) -> None:
    rows = (len(panels) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * (PANEL[0] + 4), rows * (PANEL[1] + 26)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (title, image) in enumerate(panels):
        x, y = i % columns * (PANEL[0] + 4), i // columns * (PANEL[1] + 26)
        tile = Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
        tile.thumbnail(PANEL, Image.Resampling.BOX)
        sheet.paste(tile, (x + (PANEL[0] - tile.width) // 2, y + 24 + (PANEL[1] - tile.height) // 2))
        draw.text((x + 3, y + 2), title, fill=(235, 235, 235), font=FONT)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=92)


def main() -> int:
    names = sys.argv[1:] or FILES
    pipeline = mp.Pipeline()
    base = mp.RenderSettings()
    panels = []
    for index, name in enumerate(names):
        ap1 = read_input(name)
        for film, entry in mp.CATALOG["reversals"].items():
            panels.append((f"{name} | {entry['name']} | light table", pipeline.render_array(ap1, replace(base, method="light_table", reversal=film))))
        panels.append((f"{name} | Kodak 5207 | Endura Premier print", pipeline.render_array(ap1, base)))
        if (index + 1) % ROWS_PER_SHEET == 0 or index == len(names) - 1:
            write_sheet(OUT / f"films_{index // ROWS_PER_SHEET + 1}.jpg", panels, len(mp.CATALOG["reversals"]) + 1)
            panels = []
        print(name, flush=True)
    lights = ("reference", "daylight", "tungsten", "fluorescent", "led", "street_mixed")
    for film in ("fuji_velvia_50", "kodak_ektachrome_e100"):
        panels = [(f"{name} | {mp.CATALOG['reversals'][film]['name']} | light {light}", pipeline.render_array(read_input(name), replace(base, method="light_table", reversal=film, scene_light=light)))
                  for name in ("se228", "P1031516") for light in lights]
        write_sheet(OUT / f"lights_{film}.jpg", panels, len(lights))
    return 0


if __name__ == "__main__":
    sys.exit(main())
