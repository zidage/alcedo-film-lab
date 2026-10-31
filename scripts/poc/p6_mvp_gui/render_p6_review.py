"""Review sheets of the Python MVP, with a label on every panel. Local only, because the inputs are photographs.

Input: AP1 arrays of the earlier steps under build/tmp/ (names below). Output: build/tmp/p6/review/<file>_<set>.jpg. Step: P6, README U61.
Sets: 'negatives_frontier' and 'negatives_print', all negatives; 'prints', all print materials on 5207; 'options', the spectral prior and the scene lights on 5207 by both methods.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import mvp_pipeline as mp

OUT = mp.REPO_ROOT / "build" / "tmp" / "p6" / "review"
ROOTS = ["p3/input", "p4/input_shangrila", "p4/input_night", "p5/input_hongkong", "p5/input_hongkong_half", "p4/input_spektra_compare"]
FILES = ["se188", "se228", "leica_m11", "_DSC4063", "_DSC8148", "nikon_zf"]
DEFAULT_PRINT = {"cine": "kodak_2383", "photo": "kodak_endura_premier"}
PANEL = (420, 300)
FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 15)


def read_input(name: str) -> np.ndarray:
    for root in ROOTS:
        path = mp.REPO_ROOT / "build" / "tmp" / root / f"{name}.npy"
        if path.exists():
            return np.ascontiguousarray(np.load(path), dtype=np.float32)
    raise FileNotFoundError(name)


def write_sheet(path: Path, panels: list[tuple[str, np.ndarray]], columns: int = 6) -> None:
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
    for name in names:
        ap1 = read_input(name)
        for method in mp.METHODS:
            panels = []
            for negative, entry in mp.CATALOG["negatives"].items():
                material = DEFAULT_PRINT[entry["medium"].lower()]
                settings = replace(base, negative=negative, method=method, print_material=material)
                label = f"{entry['name']} | Frontier" if method == "frontier" else f"{entry['name']} | {mp.CATALOG['prints'][material]['name']}"
                panels.append((label[:52], pipeline.render_array(ap1, settings)))
            write_sheet(OUT / f"{name}_negatives_{method}.jpg", panels)
        panels = [(f"5207 | {entry['name']}"[:52], pipeline.render_array(ap1, replace(base, print_material=material))) for material, entry in mp.CATALOG["prints"].items()]
        write_sheet(OUT / f"{name}_prints.jpg", panels)
        panels = []
        for method in mp.METHODS:
            title = "Frontier" if method == "frontier" else "2383 print"
            for prior in mp.SPECTRAL_PRIORS:
                panels.append((f"5207 | {title} | prior {prior}", pipeline.render_array(ap1, replace(base, method=method, spectral_prior=prior))))
            for light in ("daylight", "tungsten", "fluorescent", "led", "sodium", "street_mixed"):
                panels.append((f"5207 | {title} | light {light}", pipeline.render_array(ap1, replace(base, method=method, scene_light=light))))
        write_sheet(OUT / f"{name}_options.jpg", panels, 4)
        print(name, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
