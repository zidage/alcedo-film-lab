"""Reference evaluator of the grain of Alcedo Studio, and the expected values of the product tests (step P15, plan G0 step 7).

Input: results/p15_film_grain/stock_grain.json, layer_correlation.json, post_path_target.json, and the viewer models of the film
print (FilmPreview) and the light table (ReversalPreview) for the record of an 18 % grey.
Output: results/p15_film_grain/grain_reference.json, and with --expected DIR the array file DIR/grain__expected.bin in the form
of build_product_resources.write_arrays (the directory that ALCEDO_FILM_PRINT_EXPECTED_DIR names in the product tests).
build_product_resources.py calls expected_arrays() and writes the same file with the other expected files.

Rules (plan 'film_grain_format_and_stock_plan.md', sections 3.2 and 6.2; the product follows them exactly):

- Rule 'grain_pitch': the pitch of the reference pixel is p = frame_mm * 1000 / long side of the reference image, in um. Frame long
  sides (U1): 16mm 12.52, 35mm 36, 70mm 70 mm. A render at scale s has the pitch p / s.
- Rule 'grain_pixel_integral': the field of one layer is white noise of spectral density G^2 blurred by a Gaussian cloud of sigma_c,
  read by a square pixel of side p. One axis:
      I(sigma_c, p) = integral of exp(-4 pi^2 sigma_c^2 f^2) sinc^2(p f) df
                    = (1 / p) * [erf(q / sqrt(2)) - 2 (phi(0) - phi(q)) / q],   q = p / (sqrt(2) sigma_c), phi the unit normal pdf.
  Pixel standard deviation: sigma_px = G * I = sigma_48 * sqrt(A_48) * I, A_48 = pi * 24^2 um^2. pixel_factor = sqrt(A_48) * I.
- Rule 'grain_kernel': weights exp(-i^2 / (2 sigma_b^2)) divided by their sum, radius ceil(3 sigma_b), at most 24 taps on each
  side. sigma_b is the value that gives the discrete field the lag-1 correlation of the continuous pixel field,
  rho1 = C(p) / C(0) (bisection, 60 steps, sigma_b in [1e-3, 8]). The first form, sigma_b = sigma_c / p, omits the pixel box: at
  sigma_b below 1 it gives a lag-1 correlation up to 0.28 too low, and the 2 x 2 zoom check fails by 21 % (recorded in the
  report). With rho1 matched, the 2 x 2 box ratio (1 + rho1) / 2 equals I(2 p) / I(p) exactly. The separable blur of unit
  white noise has the standard deviation sum w^2 (one axis), so the unit field is u = blur / sum w^2.
- Rule 'grain_layer_mix' (in place of the shared field of the plan, see layer_correlation.json): the three unit fields u_k are
  independent before the mix; N = L u, L the lower Cholesky factor of the layer correlation R. The mix comes after the blur and
  the division, so the pixel correlation of the layers is R exactly and the pixel variance of each layer is 1.
- Rule 'grain_aggregate': a render at scale s < 1 draws k x k reference-pixel Gaussians per render pixel and divides the sum by k,
  k = clamp(round(1 / s), 1, 4).
- Film print path: a' = a + strength * sigma_a(a) * pixel_factor_k * N_k, sigma_a the layer curve of stock_grain.json at the
  48 um aperture. Reversal films: a = dye_max - record.
- Post path: the display channel j changes by strength * display_sigma_48_j * pixel_factor_j * N_j (linear display, 5207 on Endura
  Premier at mid grey, post_path_target.json). The post fields are mixed with the display correlation of that print (rg 0.535,
  gb 0.509, rb 0.087) in place of the layer correlation, so the colour of the post grain is the colour of the print grain.

Lag-1 correlation (one axis): of the discrete field, sum_i w_i w_(i+1) / sum w^2; of the continuous model, C(p) / C(0) with
C(d) = integral of tri_p(u) N(d - u; 0, 2 sigma_c^2) du = (1 / p) [F(-p) - 2 F(0) + F(p)], F(a) = E[(X - a)+] for
X ~ N(d, 2 sigma_c^2). After the mix, layer j has sum_k L_jk^2 rho1_k.

Zoom: the full render divided into 2 x 2 boxes has the factor pixel_factor * sum c^2 / sum w^2 with c = w convolved with
(1/2, 1/2) (one axis); the render at scale 0.5 has the factor sqrt(A_48) * I(sigma_c, 2 p). The product test requires the two
within 5 %. Pattern correlation of the two images (same reference noise): the 2-D value is the square of the 1-D value
<c, r> / (|c| |r|), with r the weights of the render at scale 0.5 on the reference lattice (each tap on two reference pixels,
rule 'grain_aggregate'). The product test requires above 0.9.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import erf

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "results" / "p15_film_grain"
GRAIN = RESULTS / "stock_grain.json"
CORRELATION = RESULTS / "layer_correlation.json"
POST = RESULTS / "post_path_target.json"
OUTPUT = RESULTS / "grain_reference.json"
EXPECTED_NAME = "grain__expected.bin"

FORMATS = (("16mm", 12.52), ("35mm", 36.0), ("70mm", 70.0))
LONG_SIDES = (2560, 6000)
CLOUD_SIGMA_UM = (2.0, 2.0, 2.8)
APERTURE_AREA_UM2 = math.pi * 24.0 ** 2
MAX_RADIUS = 24
MAX_AGGREGATE = 4
RENDER_SCALES = (1.0, 0.5, 0.3, 0.1)
PRINT_STOCKS = ("kodak_5207", "kodak_5219", "kodak_portra_400", "fuji_velvia_50")
GREY = 0.18
SELWYN_PITCHES_UM = (50.0, 250.0, 500.0)
PLAN_TABLE_SIGMA_48 = 0.0070
PLAN_TABLE_LONG_SIDES = (2560, 6000, 9504)
INTEGRAL_LIMIT = 1e-6


def pitch_um(frame_mm: float, long_side: int) -> float:
    """Rule 'grain_pitch'."""
    return frame_mm * 1000.0 / long_side


def pixel_integral(sigma_c: float, p: float) -> float:
    """Rule 'grain_pixel_integral', closed form."""
    q = p / (math.sqrt(2.0) * sigma_c)
    phi = lambda x: math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)  # noqa: E731
    return (float(erf(q / math.sqrt(2.0))) - 2.0 * (phi(0.0) - phi(q)) / q) / p


def pixel_integral_frequency(sigma_c: float, p: float) -> float:
    """The frequency form of rule 'grain_pixel_integral', for the check of the closed form."""
    f = lambda x: math.exp(-4.0 * math.pi ** 2 * sigma_c ** 2 * x * x) * float(np.sinc(p * x)) ** 2  # noqa: E731
    top = 4.0 / sigma_c
    value, _ = quad(f, 0.0, top, limit=2000, points=[k / p for k in range(1, int(top * p) + 1)][:400])
    return 2.0 * value


def pixel_factor(sigma_c: float, p: float) -> float:
    return math.sqrt(APERTURE_AREA_UM2) * pixel_integral(sigma_c, p)


def gaussian_kernel(sigma_b: float) -> np.ndarray:
    """The weights of rule 'grain_kernel' for one sigma_b, one axis."""
    radius = min(int(math.ceil(3.0 * sigma_b)), MAX_RADIUS)
    i = np.arange(-radius, radius + 1, dtype=np.float64)
    w = np.exp(-i * i / (2.0 * sigma_b * sigma_b))
    return w / w.sum()


def lag1_discrete(w: np.ndarray) -> float:
    return float(np.sum(w[:-1] * w[1:]) / np.sum(w * w))


def pixel_covariance(sigma_c: float, p: float, d: float) -> float:
    """C(d) of the continuous pixel field, closed form (docstring)."""
    s = math.sqrt(2.0) * sigma_c

    def f(a: float) -> float:  # E[(X - a)+], X ~ N(d, s^2)
        z = (d - a) / s
        return (d - a) * 0.5 * (1.0 + float(erf(z / math.sqrt(2.0)))) + s * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    return (f(-p) - 2.0 * f(0.0) + f(p)) / p


def lag1_continuous(sigma_c: float, p: float) -> float:
    return pixel_covariance(sigma_c, p, p) / pixel_covariance(sigma_c, p, 0.0)


def matched_sigma_b(sigma_c: float, p: float) -> float:
    """Rule 'grain_kernel': the sigma_b of the discrete kernel with the lag-1 correlation of the continuous field."""
    target = lag1_continuous(sigma_c, p)
    lo, hi = 1e-3, 8.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if lag1_discrete(gaussian_kernel(mid)) < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def kernel(sigma_c: float, p: float) -> np.ndarray:
    """Rule 'grain_kernel', one axis."""
    return gaussian_kernel(matched_sigma_b(sigma_c, p))


def zoom_pattern_correlation(sigma_c: float, p: float) -> float:
    """The 2-D pattern correlation of the render at scale 0.5 and the 2 x 2 box mean of the full render (docstring)."""
    full = np.convolve(kernel(sigma_c, p), [0.5, 0.5])  # reference taps of one box mean, centre between the two pixels
    half = kernel(sigma_c, 2.0 * p)
    render = np.repeat(half, 2) / math.sqrt(2.0)  # each render tap reads two reference pixels
    n = max(full.size, render.size)
    n += n % 2  # both vectors are even in length and centred between two reference pixels
    a, b = np.zeros(n), np.zeros(n)
    a[(n - full.size) // 2:(n - full.size) // 2 + full.size] = full
    b[(n - render.size) // 2:(n - render.size) // 2 + render.size] = render
    one_axis = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
    return one_axis ** 2


def box2_factor(w: np.ndarray) -> float:
    """The standard deviation of the unit field u = blur / sum w^2 after a 2 x 2 box mean (one axis factor; the 2-D value is the same)."""
    c = np.convolve(w, [0.5, 0.5])
    return float(np.sum(c * c) / np.sum(w * w))


def aggregate(render_scale: float) -> int:
    """Rule 'grain_aggregate'."""
    if render_scale >= 1.0:
        return 1
    return int(min(max(round(1.0 / render_scale), 1), MAX_AGGREGATE))


def correlation_matrix(r: dict) -> np.ndarray:
    return np.array([[1.0, r["rg"], r["rb"]], [r["rg"], 1.0, r["gb"]], [r["rb"], r["gb"], 1.0]])


def grey_amounts(stock: str) -> np.ndarray:
    """The dye amount of each layer at an 18 % grey AP1 input, one pixel (no image-plane step), on the viewer model of the stock."""
    sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p6_mvp_gui"))
    import mvp_pipeline as mp  # noqa: E402

    grey = np.full((1, 1, 3), GREY, dtype=np.float32)
    if stock in mp.CATALOG["reversals"]:
        settings = mp.RenderSettings(method="light_table", reversal=stock, scene_light="reference")
        settings.validate()
        model = mp.rf.ReversalPreview(mp.light_table_options(settings))
        record, _ = model.negative_image(grey)
        return np.maximum(model.dye_max - record[0, 0].astype(np.float64), 0.0)
    settings = mp.RenderSettings(negative=stock, print_material="kodak_endura_premier", scene_light="reference")
    settings.validate()
    model = mp.fp.FilmPreview(mp.film_options(settings))
    record, _ = model.negative_image(grey)
    return record[0, 0].astype(np.float64)


def geometry_values() -> dict[str, np.ndarray]:
    """The values of each format, long side, and layer at render scale 1, and of the 2 x 2 zoom."""
    nf, ns = len(FORMATS), len(LONG_SIDES)
    out = {name: np.zeros((nf, ns, 3)) for name in ("pixel_factor", "weight_square_sum", "lag1_kernel", "lag1_continuous", "sigma_b_px", "zoom_half_render_factor", "zoom_half_box_factor", "zoom_pattern_correlation")}
    out["blur_radius"] = np.zeros((nf, ns, 3), dtype=np.int32)
    out["pitch_um"] = np.zeros((nf, ns))
    for f, (_, frame_mm) in enumerate(FORMATS):
        for s, side in enumerate(LONG_SIDES):
            p = pitch_um(frame_mm, side)
            out["pitch_um"][f, s] = p
            for k, sigma_c in enumerate(CLOUD_SIGMA_UM):
                w = kernel(sigma_c, p)
                out["sigma_b_px"][f, s, k] = matched_sigma_b(sigma_c, p)
                out["blur_radius"][f, s, k] = (w.size - 1) // 2
                out["weight_square_sum"][f, s, k] = float(np.sum(w * w))
                out["pixel_factor"][f, s, k] = pixel_factor(sigma_c, p)
                out["lag1_kernel"][f, s, k] = lag1_discrete(w)
                out["lag1_continuous"][f, s, k] = lag1_continuous(sigma_c, p)
                out["zoom_half_render_factor"][f, s, k] = pixel_factor(sigma_c, 2.0 * p)
                out["zoom_half_box_factor"][f, s, k] = pixel_factor(sigma_c, p) * box2_factor(w)
                out["zoom_pattern_correlation"][f, s, k] = zoom_pattern_correlation(sigma_c, p)
    return out


def first_form_record() -> dict:
    """The lag-1 and zoom errors of the first kernel form sigma_b = sigma_c / p (recorded, not used)."""
    lag, zoom = 0.0, 1.0
    for _, frame_mm in FORMATS:
        for side in LONG_SIDES:
            p = pitch_um(frame_mm, side)
            for sigma_c in CLOUD_SIGMA_UM:
                w = gaussian_kernel(sigma_c / p)
                lag = max(lag, lag1_continuous(sigma_c, p) - lag1_discrete(w))
                zoom = min(zoom, pixel_factor(sigma_c, p) * box2_factor(w) / pixel_factor(sigma_c, 2.0 * p))
    return {"lag1_too_low_by_largest": round(lag, 4), "zoom_box_over_render_smallest": round(zoom, 4)}


def expected_arrays() -> tuple[dict[str, np.ndarray], dict, dict]:
    """The arrays of grain__expected.bin, its metadata, and the record of the checks."""
    stocks = json.loads(GRAIN.read_text(encoding="utf-8"))["stocks"]
    r = json.loads(CORRELATION.read_text(encoding="utf-8"))["layer_correlation"]
    post = json.loads(POST.read_text(encoding="utf-8"))
    rm = correlation_matrix(r)
    chol = np.linalg.cholesky(rm)
    arrays = geometry_values()
    arrays["lag1_layer"] = np.einsum("jk,fsk->fsj", chol ** 2, arrays["lag1_kernel"])
    arrays.update({"frame_mm": np.array([m for _, m in FORMATS]), "long_sides": np.array(LONG_SIDES, dtype=np.int32), "cloud_sigma_um": np.array(CLOUD_SIGMA_UM),
                   "aperture_area_um2": np.array([APERTURE_AREA_UM2]), "render_scales": np.array(RENDER_SCALES), "aggregate": np.array([aggregate(s) for s in RENDER_SCALES], dtype=np.int32),
                   "layer_correlation": np.array([r["rg"], r["gb"], r["rb"]]), "layer_cholesky": chol, "grey_ap1": np.array([GREY])})
    record_amount = np.zeros((len(PRINT_STOCKS), 3))
    sigma_amount_48 = np.zeros((len(PRINT_STOCKS), 3))
    for i, stock in enumerate(PRINT_STOCKS):
        a = grey_amounts(stock)
        layer = stocks[stock]["layer"]
        record_amount[i] = a
        sigma_amount_48[i] = [np.interp(a[k], layer["amount"][k], layer["sigma_amount"][k]) for k in range(3)]
    arrays["print_amount"] = record_amount
    arrays["print_sigma_amount_48"] = sigma_amount_48
    arrays["print_pixel_sigma"] = sigma_amount_48[:, None, None, :] * arrays["pixel_factor"][None]
    linear = np.array(post["linear"]["display_sigma_48"])
    arrays["post_display_value_linear"] = np.array(post["linear"]["display_value"])
    arrays["post_display_sigma_48_linear"] = linear
    arrays["post_pixel_sigma_linear"] = linear[None, None, :] * arrays["pixel_factor"]
    post_r = post["linear"]["display_correlation_rg_gb_rb"]
    post_chol = np.linalg.cholesky(correlation_matrix({"rg": post_r[0], "gb": post_r[1], "rb": post_r[2]}))
    arrays["post_display_correlation"] = np.array(post_r)
    arrays["post_cholesky"] = post_chol
    arrays["post_lag1"] = np.einsum("jk,fsk->fsj", post_chol ** 2, arrays["lag1_kernel"])

    # Checks of the evaluator itself.
    closed_vs_frequency = max(abs(pixel_integral(sc, p) / pixel_integral_frequency(sc, p) - 1.0) for sc in (1.0, 2.0, 2.8, 4.0) for p in (1.0, 2.09, 6.0, 14.06, 27.34, 60.0))
    if closed_vs_frequency > INTEGRAL_LIMIT:
        raise ValueError(f"the closed form of I differs from the frequency form by {closed_vs_frequency:.3g}")
    selwyn = {f"{p:g}": round(pixel_integral(CLOUD_SIGMA_UM[1], p) * p, 5) for p in SELWYN_PITCHES_UM}
    plan_table = {}
    for name, frame_mm in FORMATS:
        plan_table[name] = {str(side): {"pitch_um": round(pitch_um(frame_mm, side), 3), "sigma_px": round(PLAN_TABLE_SIGMA_48 * pixel_factor(2.0, pitch_um(frame_mm, side)), 4),
                                        "blur_px": round(2.0 / pitch_um(frame_mm, side), 3)} for side in PLAN_TABLE_LONG_SIDES}
    zoom_ratio = arrays["zoom_half_box_factor"] / arrays["zoom_half_render_factor"]
    metadata = {"formats": [n for n, _ in FORMATS], "print_stocks": list(PRINT_STOCKS), "layers": ["red", "green", "blue"], "post_selection": post["selection"],
                "rules": ["grain_pitch", "grain_pixel_integral", "grain_kernel", "grain_layer_mix", "grain_aggregate"]}
    checks = {"closed_form_vs_frequency_largest_relative": float(f"{closed_vs_frequency:.3g}"), "selwyn_ratio_I_times_p_green": selwyn,
              "plan_table_green_sigma_48_0_0070": plan_table, "zoom_box_over_render_range": [round(float(zoom_ratio.min()), 4), round(float(zoom_ratio.max()), 4)],
              "lag1_kernel_minus_continuous_largest": float(f'{float(np.abs(arrays["lag1_kernel"] - arrays["lag1_continuous"]).max()):.3g}'),
              "zoom_pattern_correlation_smallest": round(float(arrays["zoom_pattern_correlation"].min()), 4),
              "first_kernel_form_sigma_c_over_p": first_form_record()}
    return arrays, metadata, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expected", type=Path, help="directory for grain__expected.bin")
    args = parser.parse_args()
    arrays, metadata, checks = expected_arrays()
    if args.expected:
        sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p7_spectral_acceleration"))
        import build_product_resources as bpr  # noqa: E402

        bpr.write_arrays(args.expected / EXPECTED_NAME, arrays, metadata)
    out = {"metadata": metadata, "checks": checks,
           "values": {k: (np.round(v, 7).tolist() if v.dtype.kind == "f" else v.tolist()) for k, v in sorted(arrays.items())}}
    print(json.dumps(checks, indent=1))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
