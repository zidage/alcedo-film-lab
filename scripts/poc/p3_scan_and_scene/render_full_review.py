"""Labeled comparison of all film paths on the portrait collection, the sample images of the product, and the night files.

Input: RAW files of build/tmp/baseline/signature_edits/raw/ and of the Alcedo Studio sample images, AP1 arrays of the night files. Never committed.
Output (local only): build/tmp/p3/review/images/<category>__<name>.png, one sheet with a label on every panel;
build/tmp/p3/review/overview_<category>_<n>.png, one row per image; results/p3_scan_and_scene/full_review.json (statistics and the files that failed).
Step: P3, README section 8. The input of each panel is product_input() of P2. Scene light D55 for the cine stocks, print_timing 0.75.

A file that LibRaw cannot read is named in the JSON and in no sheet. No other file replaces it.
Run with no arguments for all files, or with --limit N for the first N files of each category.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_scan_review import INPUTS, NIGHT, REPO_ROOT, measure, paths  # noqa: E402

LIBRARY = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw")
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review"
CACHE = REPO_ROOT / "build" / "tmp" / "p3" / "input"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "full_review.json"
RAW_SUFFIXES = {".arw", ".nef", ".cr2", ".cr3", ".dng", ".raf", ".rw2", ".orf", ".pef", ".3fr", ".fff"}
LIBRARY_FOLDERS = ["portrait", "signature_edits", "landscape", "airplane", "blue_clipping", "building", "cat", "city", "lowlight", "misc", "plant", "showcase", "street", "item", "gps"]
PANEL = 520
LABEL_STRIP = 54
OVERVIEW_PANEL = 360
LABEL_FONT = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 19)
TITLE_FONT = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 24)
METHODS = {"print": "打印 Print (P2)", "aces20_matched": "ADX → ACES 2.0 (中灰匹配)", "aces13_matched": "ADX → ACES 1.3 (中灰匹配)", "direct": "直接反转 Direct inversion"}
STOCK_NAMES = {"5207": "5207 250D", "5219": "5219 500T (日光)", "portra": "Portra 400"}
OVERVIEW_COLUMNS = [("5207", "print"), ("5207", "aces20_matched"), ("5207", "direct"), ("5219", "direct")]


def catalog() -> dict[str, list[tuple[str, Path]]]:
    """Category to (name, file). In the sample library, the first file of each camera model stands for that model."""
    groups: dict[str, list[tuple[str, Path]]] = {"signature_edits": [], "sample_subjects": [], "sample_cameras": [], "night": []}
    for path in sorted((INPUTS / "signature_edits" / "raw").iterdir()):
        if path.suffix.lower() in RAW_SUFFIXES and path.stat().st_size > 100_000:
            groups["signature_edits"].append((path.stem, path))
    for folder in LIBRARY_FOLDERS:
        files = [path for path in sorted((LIBRARY / folder).rglob("*")) if path.suffix.lower() in RAW_SUFFIXES and "dng" not in path.parent.name]
        stems = {path.stem for path in files if path.suffix.lower() != ".dng"}
        # A DNG made from a RAW file of the same name is the same photo. The name keeps the end of the stem, where the file number is.
        for path in files:
            if path.suffix.lower() != ".dng" or path.stem not in stems:
                groups["sample_subjects"].append((f"{folder}_{path.stem[-28:]}".replace(" ", "_").replace("@", ""), path))
    names = [name for name, _ in groups["sample_subjects"]]
    if len(names) != len(set(names)):
        raise ValueError(f"two files have one output name: {sorted(n for n in names if names.count(n) > 1)}")
    for model in sorted(p for maker in sorted((LIBRARY / "camera").iterdir()) if maker.is_dir() for p in sorted(maker.iterdir()) if p.is_dir()):
        files = sorted(p for p in model.rglob("*") if p.suffix.lower() in RAW_SUFFIXES)
        if files:
            groups["sample_cameras"].append((f"{model.parent.name}_{model.name}", files[0]))
    for name in NIGHT:
        groups["night"].append((name, INPUTS / "night" / f"{name}_ap1.npy"))
    return groups


def load(name: str, path: Path, c) -> np.ndarray:
    if path.suffix == ".npy":
        return np.load(path).astype(np.float64)
    cached = CACHE / f"{name}.npy"
    if cached.exists():
        return np.load(cached).astype(np.float64)
    ap1, _ = fp.decode_raw_ap1(path, 1000, c)
    np.save(cached, ap1.astype(np.float32))
    return ap1


def fit(image: np.ndarray, side: int) -> Image.Image:
    panel = Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8))
    panel.thumbnail((side, side), Image.LANCZOS)
    return panel


def sheet_cell(panel: Image.Image, label: str, width: int, height: int, font=LABEL_FONT) -> Image.Image:
    strip = LABEL_STRIP
    cell = Image.new("RGB", (width, height + strip), (26, 26, 26))
    ImageDraw.Draw(cell).multiline_text((6, 2), label, fill=(240, 240, 225), font=font, spacing=1)
    cell.paste(panel, ((width - panel.width) // 2, strip + (height - panel.height) // 2))
    return cell


def full_sheet(title: str, plain: np.ndarray, images: dict) -> Image.Image:
    plain_panel = fit(plain, PANEL)
    w, h = plain_panel.size
    columns = list(METHODS)
    rows = list(images)
    cw, ch = w + 8, h + LABEL_STRIP + 8
    sheet = Image.new("RGB", (cw * (len(columns) + 1) + 8, ch * len(rows) + 52), (26, 26, 26))
    ImageDraw.Draw(sheet).text((10, 8), title, fill=(255, 225, 150), font=TITLE_FONT)
    sheet.paste(sheet_cell(plain_panel, "未经胶片\nPlain sRGB", w, h), (8, 52))
    for r, stock in enumerate(rows):
        for k, method in enumerate(columns):
            sheet.paste(sheet_cell(fit(images[stock][method], PANEL), f"{STOCK_NAMES[stock]}\n{METHODS[method]}", w, h), (8 + cw * (k + 1), 52 + ch * r))
    return sheet


def save_overviews(category: str, rows: list[tuple[str, np.ndarray, dict]]) -> None:
    per_sheet = 6
    for start in range(0, len(rows), per_sheet):
        chunk = rows[start:start + per_sheet]
        cw, ch = OVERVIEW_PANEL + 8, OVERVIEW_PANEL + LABEL_STRIP + 8
        sheet = Image.new("RGB", (cw * (len(OVERVIEW_COLUMNS) + 1) + 8, ch * len(chunk) + 8), (26, 26, 26))
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
        for r, (name, plain, images) in enumerate(chunk):
            sheet.paste(sheet_cell(fit(plain, OVERVIEW_PANEL), f"{name}\n未经胶片 Plain", OVERVIEW_PANEL, OVERVIEW_PANEL, font), (8, 8 + ch * r))
            for k, (stock, method) in enumerate(OVERVIEW_COLUMNS):
                sheet.paste(sheet_cell(fit(images[stock][method], OVERVIEW_PANEL), f"{STOCK_NAMES[stock]}\n{METHODS[method]}", OVERVIEW_PANEL, OVERVIEW_PANEL, font), (8 + cw * (k + 1), 8 + ch * r))
        sheet.save(OUT / f"overview_{category}_{start // per_sheet + 1:02d}.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "images").mkdir(exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    previews = {"5207": paths("5207_2383", scene_light="D55", print_timing=0.75), "5219": paths("5219_2383", scene_light="D55", print_timing=0.75), "portra": paths("portra400_endura")}
    for stock, extra in (("5207_2383", dict(scene_light="D55", print_timing=0.75)), ("5219_2383", dict(scene_light="D55", print_timing=0.75)), ("portra400_endura", {})):
        key = {"5207_2383": "5207", "5219_2383": "5219", "portra400_endura": "portra"}[stock]
        previews[key]["direct"] = scan.DirectInversionPreview(fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra}))
    c = previews["5207"]["print"].c
    result: dict = {"failed": {}, "images": {}}
    groups = catalog()
    print({k: len(v) for k, v in groups.items()}, flush=True)
    for category, items in groups.items():
        overview_rows = []
        for name, path in items[:limit]:
            start = time.time()
            try:
                ap1 = load(name, path, c)
            except Exception as error:  # the file is named in the result, and no other file replaces it
                result["failed"][f"{category}/{name}"] = f"{path.name}: {str(error)[:120]}"
                print("failed", name, error, flush=True)
                continue
            graded = fp.product_input(ap1, c)
            scale = fp.center_weighted_exposure(ap1, c)
            plain = fp.srgb_encode(ap1 * scale @ (fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz).T)
            images = {stock: {method: group[method].render(graded)[0] for method in METHODS} for stock, group in previews.items()}
            title = f"{category} / {name}   |   输入: 产品默认调色后   |   5207/5219: 场景光 D55, timing 0.75   |   Portra: 无场景光选项"
            full_sheet(title, plain, images).save(OUT / "images" / f"{category}__{name}.png")
            overview_rows.append((name, plain, images))
            result["images"][f"{category}/{name}"] = {f"{stock}_{method}": measure(images[stock][method]) for stock in images for method in METHODS}
            print(category, name, round(time.time() - start, 1), "s", flush=True)
        save_overviews(category, overview_rows)
        RESULT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("done", len(result["images"]), "images;", len(result["failed"]), "failed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
