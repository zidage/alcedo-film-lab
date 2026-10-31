"""The two kept paths, print and direct inversion with APD, and rule 'density_crosstalk' on the inversion, on landscape files and the hue sweep.

Input: AP1 arrays of the full review (build/tmp/p3/input/), never committed. Output (local only): build/tmp/p3/review_crosstalk/<name>.jpg, one large sheet per file, and sweep.png, with a label on every panel.
results/p3_scan_and_scene/crosstalk_checks.json holds the checks: neutrals do not change, the record never reverses, and the sweep has no break above the value of the input.
Step: P3, README section 8, decision U29.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_scanner_light_review import STOCKS, hue_sweep, load  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "build" / "tmp" / "p3" / "review_crosstalk"
RESULT = REPO_ROOT / "results" / "p3_scan_and_scene" / "crosstalk_checks.json"
PANEL = 1000
# Chosen by eye from contact sheets: the sample images of the product, and the files of one landscape photographer on signatureedits.com.
FILES = ["se041", "se042", "se044", "se113", "se115", "se116", "se167", "se186", "se204", "se220", "se222", "se223", "se224", "se238", "se377", "se378", "se201",
         "canon_r", "canon_5div", "canon_r6ii", "fuji_xt5", "fuji_gfx50sii", "hasselblad_x1dii", "hasselblad_h5d", "hasselblad_cfvii50c", "nikon_d780", "nikon_d6", "nikon_z6ii",
         "lumix_l10", "lumix_s5", "ricoh_gr3", "ricoh_gr4", "sony_a7riii", "sony_a7rv", "sigma_fp", "landscape__DSC0726", "landscape__DSC4735"]


def uniform(k: float) -> np.ndarray:
    return k * (np.ones((3, 3)) - np.eye(3))


# Row i, column j: how far record i moves from record j. Order: R, G, B.
WARM = np.array([[0.0, 0.05, 0.15], [0.30, 0.0, 0.05], [0.05, 0.05, 0.0]])
STYLES = {"k = 0": None, "uniform 0.10": uniform(0.10),
          "warm: G from R 0.30, R from B 0.15": WARM, "warm x 0.5": 0.5 * WARM}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stock, extra = STOCKS["5207"]
    options = fp.FilmOptions(**{**fp.STOCKS[stock], **fp.DARKROOM, **extra})
    print_path = fp.FilmPreview(options)
    paths = {name: scan.DirectInversionPreview(options, crosstalk=k) for name, k in STYLES.items()}
    c = print_path.c
    to_display = fp.XYZ_TO_REC709 @ np.linalg.inv(fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))) @ c.ap1_to_xyz
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    checks: dict = {"styles": {k: None if v is None else v.tolist() for k, v in STYLES.items()}, "limit_log10": 0.5, "stock": "5207"}

    ramp = np.outer(0.18 * 2.0 ** np.linspace(-6.0, 6.0, 49), np.ones(3)).astype(np.float32)
    sweep = hue_sweep(c).astype(np.float32)
    graded_sweep = fp.product_input(sweep, c)
    input_breaks = np.abs(np.diff(fp.srgb_encode(np.clip(graded_sweep @ to_display.T, 0.0, 1.0)).astype(np.float64), 2, axis=1)).max()
    checks["sweep_input_largest_second_difference"] = round(float(input_breaks), 4)
    base_ramp = paths["k = 0"].render(ramp[None])[0][0]
    for name, path in paths.items():
        shown = path.render(ramp[None])[0][0]
        image = path.render(graded_sweep)[0]
        # Ungraded sweep at high exposure spread: the case where the fitted crosstalk drove a channel to black.
        dark = path.render(sweep * 0.25)[0]
        checks[name] = {"neutral_ramp_largest_change_from_k0": round(float(np.abs(shown - base_ramp).max()), 6),
                        "sweep_largest_second_difference": round(float(np.abs(np.diff(image.astype(np.float64), 2, axis=1)).max()), 4),
                        "sweep_min_display_value": round(float(image.min()), 4), "ungraded_dark_sweep_min_display_value": round(float(dark.min()), 4)}
    print(json.dumps(checks, indent=1), flush=True)

    columns = ["print", *STYLES]
    titles = {"print": "打印 Print (P2)", **{k: f"APD 反转 | 串扰 {k}" for k in STYLES}}
    for name in sys.argv[1:] or FILES:
        source = load(name, c)
        graded = fp.product_input(source, c)
        plain = fp.srgb_encode(np.clip(source * fp.center_weighted_exposure(source, c) @ to_display.T, 0.0, 1.0))
        images = {"print": print_path.render(graded)[0], **{k: p.render(graded)[0] for k, p in paths.items()}}
        first = fit(plain, PANEL)
        w, h = first.size
        panels = [("原图 Plain", first)] + [(titles[m], fit(images[m], PANEL)) for m in columns]
        cols = 3 if w >= h else len(panels)
        rows = (len(panels) - 1) // cols + 1
        cw, ch = w + 8, h + LABEL_STRIP + 8
        sheet = Image.new("RGB", (cw * cols + 8, ch * rows + 8), (26, 26, 26))
        for k, (title, panel) in enumerate(panels):
            sheet.paste(sheet_cell(panel, f"{name} | 5207 250D | 表平滑\n{title}", w, h, font), (8 + cw * (k % cols), 8 + ch * (k // cols)))
        sheet.save(OUT / f"{name}.jpg", quality=95)
        print(name, sheet.size, flush=True)
    h, w = sweep.shape[:2]
    sheet = Image.new("RGB", (2 * w + 30, 3 * (h + 34) + 10), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)
    for k, name in enumerate(columns + ["input"]):
        x, y = 10 + (k % 2) * (w + 10), 6 + (k // 2) * (h + 34)
        title = "输入,不经胶片 Graded input" if name == "input" else titles[name]
        draw.text((x, y), f"hue_sweep | 5207 | {title}", fill=(255, 225, 150), font=font)
        image = fp.srgb_encode(np.clip(graded_sweep @ to_display.T, 0.0, 1.0)) if name == "input" else (print_path if name == "print" else paths[name]).render(graded_sweep)[0]
        sheet.paste(Image.fromarray((np.clip(image, 0.0, 1.0) * 255.0).astype(np.uint8)), (x, y + 28))
    sheet.save(OUT / "sweep.png")
    RESULT.write_text(json.dumps(checks, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
