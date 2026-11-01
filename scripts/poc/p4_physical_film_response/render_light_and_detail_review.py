"""W3 and W4 review: the negative exposed under a light estimated from the RAW white, and full-resolution crops of the layer spread and the inhibition.

Input: RAW files under build/tmp/baseline/signature_edits/raw/ and the sample images found through build/tmp/p3/raw_index.json if present, never committed. Command line: file names.
Output (local only): build/tmp/p4/review_light/<name>.jpg, build/tmp/p4/review_detail/<name>.jpg, with a label on every panel. results/p4_physical_film_response/estimated_light.json holds the white and the light of each file.
Step: P4, ROADMAP section 8, work items W3 and W4.

Rule 'light_from_raw_white': the camera white balance and the camera matrix of the RAW file give the XYZ of the neutral, and the McCamy formula gives a correlated colour temperature. At 4000 K and above the light is a CIE daylight; below 4000 K it is a Planckian light.
This is a review of the principle. ROADMAP U21 keeps the light as a manual choice in the product: a RAW white cannot show that a light is fluorescent or LED.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "poc" / "p3_scan_and_scene"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import aces_scan as scan  # noqa: E402
from aces_scan import fp  # noqa: E402
from render_full_review import LABEL_STRIP, fit, sheet_cell  # noqa: E402
from render_p4_review import P4_TONE, physical  # noqa: E402

RAW_DIR = REPO_ROOT / "build" / "tmp" / "baseline" / "signature_edits" / "raw"
OUT = REPO_ROOT / "build" / "tmp" / "p4"
RESULT = REPO_ROOT / "results" / "p4_physical_film_response" / "estimated_light.json"
CROP = 900
ZOOM = 2


def estimated_light(path: Path) -> tuple[str, float, list[float]]:
    """Rule 'light_from_raw_white'. Returns (light name for FilmPreview.light, CCT in K, xy of the neutral)."""
    with rawpy.imread(str(path)) as raw:
        multipliers = np.array(raw.camera_whitebalance[:3], dtype=np.float64)
        camera_from_xyz = np.array(raw.rgb_xyz_matrix[:3], dtype=np.float64)
    if multipliers.min() <= 0.0 or np.abs(camera_from_xyz).sum() == 0.0:
        raise ValueError(f"{path.name}: the RAW file has no camera white balance or no camera matrix")
    xyz = np.linalg.solve(camera_from_xyz, 1.0 / multipliers)
    x, y = xyz[0] / xyz.sum(), xyz[1] / xyz.sum()
    n = (x - 0.3320) / (y - 0.1858)
    cct = float(-449.0 * n ** 3 + 3525.0 * n ** 2 - 6823.3 * n + 5520.33)
    rounded = int(round(np.clip(cct, 1800.0, 24000.0) / 100.0))
    return (f"D{rounded}" if rounded >= 40 else f"T{rounded * 100}"), cct, [float(x), float(y)]


def decode_full(path: Path, c) -> np.ndarray:
    """White-balanced linear AP1 at the full sensor resolution, as decode_raw_ap1 of step P2 with no half-size decode."""
    with rawpy.imread(str(path)) as raw:
        xyz = raw.postprocess(output_color=rawpy.ColorSpace.XYZ, gamma=(1, 1), no_auto_bright=True, use_camera_wb=True, output_bps=16, highlight_mode=rawpy.HighlightMode.Clip).astype(np.float32) / 65535.0
    to_ap1 = c.xyz_to_ap1 @ fp.bradford_matrix(fp.XYZ_D65, c.ap1_to_xyz @ np.ones(3))
    return xyz @ to_ap1.T.astype(np.float32)


def write_sheet(path: Path, panels: list[tuple[str, np.ndarray]], columns: int, side: int, font) -> None:
    images = [(title, fit(image, side)) for title, image in panels]
    w, h = images[0][1].size
    rows = (len(images) - 1) // columns + 1
    cw, ch = w + 8, h + LABEL_STRIP + 12
    sheet = Image.new("RGB", (cw * columns + 8, ch * rows + 8), (26, 26, 26))
    for k, (title, image) in enumerate(images):
        sheet.paste(sheet_cell(image, title, w, h, font), (8 + cw * (k % columns), 8 + ch * (k // columns)))
    sheet.save(path, quality=95)


def light_review(name: str, path: Path, record: dict, font) -> None:
    light, cct, xy = estimated_light(path)
    record[name] = {"light": light, "cct_k": round(cct), "neutral_xy": np.round(xy, 4).tolist()}
    tone = dict(per_record_slope=False, **P4_TONE)
    panels = []
    base = fp.FilmPreview(physical("5207"))
    source, _ = fp.decode_raw_ap1(path, 1000, base.c)
    graded = fp.product_input(source, base.c)
    for stock, title in (("5207", "5207 250D"), ("5219", "5219 500T")):
        for scene, label in ((None, "固定光源"), (light, f"估计光源 {light}, 定时 1"), (light, f"估计光源 {light}, 定时 0.5")):
            extra = {} if scene is None else {"scene_light": scene, "print_timing": 0.5 if "0.5" in label else 1.0}
            panels.append((f"{name} | {title} | {label} | APD 密度定时", scan.DirectInversionPreview(physical(stock, **extra), **tone).render(graded)[0]))
    (OUT / "review_light").mkdir(parents=True, exist_ok=True)
    write_sheet(OUT / "review_light" / f"{name}.jpg", panels, 3, 1000, font)
    print(name, record[name], flush=True)


def detail_review(name: str, path: Path, font) -> None:
    variants = {"P3 scatter 10 um, Eberhard": dict(layer_spread_um=(0.0, 0.0, 0.0), inhibition_total=(0.0, 0.0, 0.0), scatter_um=10.0, adjacency_gain=0.25),
                "无扩散 无 DIR": dict(layer_spread_um=(0.0, 0.0, 0.0), inhibition_total=(0.0, 0.0, 0.0)),
                "W4 分层扩散": dict(inhibition_total=(0.0, 0.0, 0.0)),
                "W4 分层扩散 + W2 DIR": {}}
    tone = dict(per_record_slope=False, **P4_TONE)
    paths = {k: scan.DirectInversionPreview(physical("5207", **v), **tone) for k, v in variants.items()}
    c = next(iter(paths.values())).negative.c
    full = decode_full(path, c)
    reduced = full[::8, ::8].astype(np.float64)
    scale = fp.center_weighted_exposure(reduced, c)
    # The crop at the strongest local contrast of the reduced image, so that a high-contrast edge is in the panel.
    luminance = np.log10(np.maximum(reduced @ c.ap1_to_xyz[1], 1e-4))
    gy, gx = np.gradient(luminance)
    edge = np.hypot(gy, gx)
    margin = CROP // 16
    i, j = np.unravel_index(np.argmax(edge[margin:-margin, margin:-margin]), (edge.shape[0] - 2 * margin, edge.shape[1] - 2 * margin))
    y0, x0 = (i + margin) * 8 - CROP // 2, (j + margin) * 8 - CROP // 2
    y0, x0 = max(y0, 0), max(x0, 0)
    crop = np.ascontiguousarray(full[y0:y0 + CROP, x0:x0 + CROP])
    graded = fp.fk.product_grade(crop, float(np.log2(scale)), fp.PRODUCT_CONTRAST, fp.PRODUCT_SATURATION)
    long_side = max(full.shape[:2])
    panels = []
    for title, p in paths.items():
        # frame_mm applies to the whole frame, and the crop is a part of it, so the frame width in the options scales with the crop.
        shrunk = p.negative.options.frame_mm * max(crop.shape[:2]) / long_side
        p.negative.options = replace(p.negative.options, frame_mm=shrunk)
        image = p.render(graded)[0]
        panels.append((f"{name} | 5207 250D | {title} | 全分辨率 x{ZOOM} | {p.negative._pixel_um(graded):.2f} um/px", np.repeat(np.repeat(image, ZOOM, axis=0), ZOOM, axis=1)))
    (OUT / "review_detail").mkdir(parents=True, exist_ok=True)
    write_sheet(OUT / "review_detail" / f"{name}.jpg", panels, 2, CROP * ZOOM, font)
    print(name, "crop", y0, x0, "of", full.shape, flush=True)


def main() -> int:
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    record: dict = {}
    for name in sys.argv[1:]:
        found = [p for p in RAW_DIR.glob(f"{name}.*")]
        if len(found) != 1:
            raise FileNotFoundError(name)
        light_review(name, found[0], record, font)
        detail_review(name, found[0], font)
    RESULT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
