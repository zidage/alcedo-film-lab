"""Review renders and numeric checks of the P2 film preview.

Input: film_preview.py and a list of RAW files of the library (default: REVIEW_FILES).
Output: build/tmp/p2/renders/*.png (not committed: photos stay local, AGENTS.md) and
results/p2_negative_print/preview_checks.json.

With --variants, each image shows the plain encoding and every entry of VARIANTS side by side.

Step: P2, ROADMAP section 8 and decision U17. Each output image shows the same data twice: left, the
linear camera colour with the same exposure and a plain sRGB encoding; right, the film preview.

Checks (limits set before the first run):
- table against direct stages, 2,000 random negative densities in the table: Delta E*ab p95 <= 0.5;
- uv table against the direct reconstruction, 2,000 pixels of grid-free random reflectance colours:
  relative Q error p95 <= 0.005;
- grey ramp: finite output, monotonic display luminance, mid grey near display 0.18 is reported.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import film_preview as fp  # noqa: E402
from film_preview import sd, sr  # noqa: E402
import matplotlib.image as mpimg  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parents[2]
LIBRARY = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/camera")
RENDER_DIR = REPO_ROOT / "build" / "tmp" / "p2" / "renders"
RESULT_DIR = REPO_ROOT / "results" / "p2_negative_print"
REVIEW_FILES = ["sony/a7rii/DSC00372.ARW", "nikon/d850/DSC_0836.NEF", "canon/r5/020A0059.CR3", "fuji/xt4/9603741704.raf",
                "nikon/d810/DSC_7647.NEF", "lumix/gx9/P1012323.RW2", "sony/a7iii/DSC00628.ARW", "canon/r6/1H1A6888.CR3"]
LONG_EDGE = 1400
VARIANTS = {"baseline": fp.FilmOptions()}  # the options that follow the appearance baseline (U18)
VARIANT_FILES = ["canon/r5/020A0059.CR3", "canon/r6/1H1A6888.CR3", "nikon/d810/DSC_7647.NEF", "nikon/d850/DSC_0836.NEF", "sony/a7iii/DSC00628.ARW"]
# Chosen from the library by subject: skin, saturated colour, landscape, night. Plain encoding and the baseline options, full review size.
BROAD_FILES = ["sony/a7riii/DSC00674.ARW", "canon/r5ii/237A2108.CR3", "canon/5div/793A6931.CR2", "nikon/z6ii/DSC_2457.NEF", "nikon/zf/DSC_1535.NEF",
               "nikon/d3x/nikon_d3x_08.nef", "leica/sl3-p/0768513254.dng", "sony/a7cii/Sonya7c2-Bracaglia-05.ARW", "sony/a7rii/DSC00602.ARW",
               "fuji/xt5/DSCF1787.RAF", "sony/a7riii/DSC00728.ARW", "pentax/k1/4354619001 (1).pef", "nikon/d800e/Nikon-D800e-raw-00007.nef",
               "sony/a7iii/DSC00542.ARW", "sigma/fp/SDIM0220.DNG", "leica/m10/L1001108.dng", "canon/r6iii/9327411796.cr3", "sony/a7rv/DSC07857.ARW"]


def render_variants(files: list[str], variants: dict = VARIANTS, long_edge: int = LONG_EDGE // 2, name: str = "variants") -> None:
    previews = {k: fp.FilmPreview(o) for k, o in variants.items()}
    first = next(iter(previews.values()))
    out = {}
    rng = np.random.default_rng(20261030)
    for rel in files:
        ap1, rec709 = fp.decode_raw_ap1(LIBRARY / rel, long_edge, first.c)
        scale = fp.center_weighted_exposure(ap1, first.c)
        panels = [fp.srgb_encode(rec709 * scale)]
        for k, preview in previews.items():
            graded = fp.product_input(ap1, first.c)
            image, stats = preview.render(graded)
            panels.append(image)
            q, _ = preview.layer_exposure(np.asarray(graded, dtype=np.float64) + preview.options.scene_flare)
            density, _ = preview.negative_density(q)
            sample = density.reshape(-1, 3)[rng.choice(density.size // 3, 3000)]
            _, reach = preview.direct_print_xyz(sample)
            out.setdefault(rel, {})[k] = {**stats, "sample_3000_dye_solve": reach}
        gap = np.ones((panels[0].shape[0], 10, 3))
        row = [panels[0]]
        for panel in panels[1:]:
            row += [gap, panel]
        mpimg.imsave(RENDER_DIR / (name + "_" + rel.replace("/", "_").replace(" ", "_") + ".png"), np.concatenate(row, axis=1))
        print(rel, out[rel], flush=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / f"preview_{name}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")


def checks(preview: fp.FilmPreview) -> dict:
    c = preview.c
    rng = np.random.default_rng(20261030)
    d = np.stack([rng.uniform(g[0], g[-1], 2000) for g in preview.density_grid], axis=1)
    direct, _ = preview.direct_print_xyz(d)
    table = preview.print_xyz(d)
    white = preview.paper_white
    de = np.linalg.norm(sr.xyz_to_lab(direct, white) - sr.xyz_to_lab(table, white), axis=1)
    sets = sd.load_all_reflectance_sets()
    train = {k: s.reflectance for k, s in sets.items()}
    moment, _ = sr.prior_second_moment(c, train)
    method = sr.MeasuredPriorLocalNonnegative(c, moment, train)
    pool = np.vstack([s.reflectance[rng.choice(len(s.reflectance), 500)] for s in sets.values()])
    ap1 = c.xyz(pool * c.e_ref[None, :]) @ c.xyz_to_ap1.T
    q_direct = c.layer_exposure(method.reconstruct(ap1).radiance)
    q_table, _ = preview.layer_exposure(ap1)
    relative = np.abs(q_table / q_direct - 1)
    grey = np.outer(np.logspace(-4, 1.3, 54), np.ones(3))
    srgb, _ = preview.render(grey)
    q, _ = preview.layer_exposure(grey)
    density, _ = preview.negative_density(q)
    linear = preview.display_linear(preview.print_xyz(density))
    luminance = linear @ np.array([0.2126, 0.7152, 0.0722])
    chroma = sr.xyz_to_lab(preview.print_xyz(density), white)
    mid = int(np.argmin(np.abs(grey[:, 0] - 0.18)))
    result = {"table_delta_e_ab": {"p50": float(np.median(de)), "p95": float(np.percentile(de, 95)), "max": float(de.max()), "limit_p95": 0.5,
                                   "pass": bool(np.percentile(de, 95) <= 0.5)},
              "uv_table_relative_q": {"p50": float(np.median(relative)), "p95": float(np.percentile(relative, 95)), "max": float(relative.max()),
                                      "limit_p95": 0.005, "pass": bool(np.percentile(relative, 95) <= 0.005)},
              "grey_ramp": {"finite": bool(np.isfinite(srgb).all()), "largest_luminance_fall": float(np.maximum(0, -np.diff(luminance)).max()),
                            "input": grey[:, 0].round(5).tolist(), "display_linear_luminance": luminance.round(5).tolist(),
                            "print_c_ab": np.hypot(chroma[:, 1], chroma[:, 2]).round(2).tolist(), "mid_grey_display_luminance": float(luminance[mid]),
                            "mid_grey_srgb": srgb[mid].round(3).tolist(), "max_c_ab": float(np.hypot(chroma[:, 1], chroma[:, 2]).max())},
              "table_build_counts": preview.table_counts, "paper_white_xyz": preview.paper_white.round(3).tolist(),
              "options": preview.options.__dict__}
    return result


def main() -> int:
    if "--broad" in sys.argv:
        RENDER_DIR.mkdir(parents=True, exist_ok=True)
        render_variants([f for f in sys.argv[1:] if f != "--broad"] or BROAD_FILES, VARIANTS, LONG_EDGE, "broad")
        return 0
    if "--variants" in sys.argv:
        RENDER_DIR.mkdir(parents=True, exist_ok=True)
        render_variants([f for f in sys.argv[1:] if f != "--variants"] or VARIANT_FILES)
        return 0
    t0 = time.time()
    preview = fp.FilmPreview()
    print(f"tables ready: {time.time() - t0:.0f} s", flush=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    result = checks(preview)
    print(json.dumps({k: result[k] for k in ("table_delta_e_ab", "uv_table_relative_q", "table_build_counts")}), flush=True)
    print(json.dumps({k: v for k, v in result["grey_ramp"].items() if k not in ("input", "display_linear_luminance", "print_c_ab")}), flush=True)
    files = sys.argv[1:] or REVIEW_FILES
    result["images"] = {}
    for rel in files:
        t1 = time.time()
        ap1, rec709 = fp.decode_raw_ap1(LIBRARY / rel, LONG_EDGE, preview.c)
        scale = fp.center_weighted_exposure(ap1, preview.c)
        film, stats = preview.render(fp.product_input(ap1, preview.c))
        plain = fp.srgb_encode(rec709 * scale)
        gap = np.ones((film.shape[0], 12, 3))
        mpimg.imsave(RENDER_DIR / (rel.replace("/", "_") + ".png"), np.concatenate([plain, gap, film], axis=1))
        stats.update(exposure_scale=round(scale, 4), seconds=round(time.time() - t1, 1))
        result["images"][rel] = stats
        print(rel, stats, flush=True)
    (RESULT_DIR / "preview_checks.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
