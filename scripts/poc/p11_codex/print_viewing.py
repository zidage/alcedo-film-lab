"""P11: transfer spectral print XYZ to display XYZ under stated CAM16 conditions.

Input is XYZ with perfect diffuser Y=100. Output is linear Rec.709 and
appearance diagnostics. This code is GPL-3.0-only; it reuses the lab CAM16.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/poc/p6_mvp_gui"))
import mvp_pipeline as mp
sys.path.insert(0, str(ROOT / "scripts/poc/p10_chart_scan"))
import cam16
import scan_appearance as sa

fp = mp.fp


def print_cam(white: np.ndarray, illuminance: float) -> cam16.Cam16:
    """Lambertian perfect diffuser: Lw=E/pi; adapting field is 20% of Lw.

    Full adaptation is an explicit scenario, as in the existing display metric.
    White is the illuminant diffuser, so paper and stock casts remain in XYZ.
    """
    return cam16.Cam16(cam16.Viewing(tuple(white), 0.2 * illuminance / np.pi,
                                   20.0, "average", 1.0))


def corresponding_rgb(xyz: np.ndarray, white: np.ndarray,
                      illuminance: float) -> tuple[np.ndarray, dict]:
    """Preserve J, M and h across print/display conditions, before gamut mapping."""
    source = print_cam(white, illuminance)
    target = cam16.Cam16(sa.DISPLAY)
    appearance = source.forward(xyz)
    destination = target.inverse(*(appearance[k] for k in ("J", "M", "h")))
    if not np.isfinite(destination).all():
        raise FloatingPointError("CAM16 print transfer produced non-finite XYZ")
    restored = target.forward(destination)
    error = max(float(np.max(np.abs(restored[k] - appearance[k])))
                for k in ("J", "M"))
    if error > 1e-8:
        raise AssertionError(f"CAM16 J/M preservation exceeds 1e-8: {error}")
    return destination @ fp.XYZ_TO_REC709.T / 100.0, {
        "JM_preservation_max": error,
        "negative_xyz_count": int(np.any(destination < 0, axis=-1).sum()),
    }


def finish(rgb: np.ndarray, model) -> tuple[np.ndarray, dict]:
    """Use the existing display gamut mapping and encoding after the candidate."""
    o = model.options
    out, before, after = fp.fk.finish_display(
        np.ascontiguousarray(rgb, dtype=np.float32), bool(o.gamut_compress),
        np.array(o.gamut_threshold), np.array(o.gamut_limit), float(o.gamut_power))
    return np.asarray(out), {"outside_before": int(before), "outside_after": int(after)}


def render_variants(model, ap1: np.ndarray) -> tuple[dict, dict]:
    """Run one unchanged negative and print; change only the viewing step."""
    density, stats = model.negative_image(np.ascontiguousarray(ap1, dtype=np.float32))
    xyz = model.print_xyz(density.astype(np.float64))
    result = {"print": finish(model.display_linear(xyz), model)[0]}
    diagnostics = {"negative": stats}
    for lux in (100, 500, 2000):
        rgb, check = corresponding_rgb(xyz, model.film.white_xyz(), lux)
        code, gamut = finish(rgb, model)
        result[f"cam{lux}"] = code
        diagnostics[f"cam{lux}"] = check | gamut
    return result, diagnostics
