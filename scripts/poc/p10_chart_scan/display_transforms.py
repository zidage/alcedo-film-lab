"""Display rendering transforms for the chart scan (step P10, ROADMAP U91), from public OCIO configs. A test of the display only.

The user asked to take the scan to a wide scene-linear gamut and to try OpenDRT, ACES 2.0, AgX, and a Cineon log form in place of the log curve
on Rec. 709. Input: linear AP1 (ACEScg) with the grey at 0.18. Output: sRGB display code. Each transform gets one exposure, found once, that
shows a grey of 0.18 at the sRGB code of 0.18 (the grey of rule 'scan_log_curve'), so only the shape differs.

Configs (downloaded by fetch(), kept in build/tmp/p10/drt/, not committed; licenses of the sources apply):
- Blender colour management (https://github.com/blender/blender, release/datafiles/colormanagement): views 'ACES 2.0' and 'AgX' of
  display 'sRGB'. AgX after Troy Sobotka and Eary Chow.
- OpenDRT-OCIO-Config (https://github.com/chrisbrejon/OpenDRT-OCIO-Config): OpenDRT 1.0.0 of Jed Smith (GPL-3.0), Rec.1886 100 nit; its
  gamma 2.4 code is decoded and encoded as sRGB.
- 'cineon': the DI scan with no print emulation, written here: linear Rec. 709 to Cineon code per channel (grey at 445, 0.002 density per
  code, negative gamma 0.6, so 90.309 codes per stop), the Kodak log to linear conversion (white 685, black 95), a clip, and the sRGB encoding.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGS = REPO_ROOT / "build" / "tmp" / "p10" / "drt"
TRANSFORMS = ("log_curve", "aces20", "agx", "opendrt", "cineon")
NAMES = {"log_curve": "Log curve (P10)", "aces20": "ACES 2.0", "agx": "AgX", "opendrt": "OpenDRT 1.0.0", "cineon": "Cineon, Kodak conversion (DI, no print)"}
BLENDER = "https://raw.githubusercontent.com/blender/blender/main/release/datafiles/colormanagement"
OPENDRT = "https://raw.githubusercontent.com/chrisbrejon/OpenDRT-OCIO-Config/HEAD"
FILES = {"blender/config.ocio": f"{BLENDER}/config.ocio",
         **{f"blender/luts/{f}": f"{BLENDER}/luts/{f}" for f in ("AgX_Base_sRGB.cube", "Guard_Rail_Shaper_EOTF.spi1d", "xyz_E_to_D65.spimtx",
                                                             "luminance_compensation_bt2020.cube", "AgX_Base_Rec2020.cube")},
         "opendrt/config.ocio": f"{OPENDRT}/config.ocio",
         **{f"opendrt/transforms/{f}": f"{OPENDRT}/transforms/{f}" for f in ("CineonLog_2_Linear.spi1d", "OpenDRT_Default_v1.0.0_tlog-egamut_to_Rec1886.cube",
                                                                         "TLog_2_Linear.spi1d", "linear_to_rec1886.spi1d", "linear_to_sRGB.spi1d")}}
_PROCESSORS: dict = {}
_GREY_STOPS: dict = {}


def fetch() -> None:
    """Download the configs of FILES into CONFIGS (curl)."""
    for relative, url in FILES.items():
        target = CONFIGS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            subprocess.run(["curl", "-sSfL", "-o", str(target), url], check=True)


def _processor(transform: str):
    import PyOpenColorIO as ocio

    if transform not in _PROCESSORS:
        source = {"aces20": ("blender", "ACEScg", "sRGB", "ACES 2.0"), "agx": ("blender", "ACEScg", "sRGB", "AgX"),
                  "opendrt": ("opendrt", "acescg", "Rec1886 100 nits Video dim", "OpenDRT 1.0.0")}[transform]
        config_path = CONFIGS / source[0] / "config.ocio"
        if not config_path.exists():
            raise FileNotFoundError(f"{config_path}: run display_transforms.fetch() (python -c \"import display_transforms; display_transforms.fetch()\")")
        config = ocio.Config.CreateFromFile(str(config_path))
        _PROCESSORS[transform] = config.getProcessor(*source[1:], ocio.TRANSFORM_DIR_FORWARD).getDefaultCPUProcessor()
    return _PROCESSORS[transform]


def _cineon(rec709: np.ndarray) -> np.ndarray:
    code = np.clip(445.0 + 90.309 * np.log2(np.maximum(rec709, 1e-6) / 0.18), 0.0, 1023.0)
    black = 10.0 ** ((95.0 - 685.0) * 0.002 / 0.6)
    return (10.0 ** ((code - 685.0) * 0.002 / 0.6) - black) / (1.0 - black)


def _shown(transform: str, ap1: np.ndarray, ap1_to_rec709: np.ndarray, srgb_encode) -> np.ndarray:
    if transform == "cineon":
        return srgb_encode(np.clip(_cineon(ap1 @ ap1_to_rec709.T), 0.0, 1.0))
    out = np.ascontiguousarray(ap1.reshape(-1, 3), dtype=np.float32).copy()
    _processor(transform).applyRGB(out)
    out = out.reshape(ap1.shape).astype(np.float64)
    if transform == "opendrt":
        out = srgb_encode(np.clip(out, 0.0, 1.0) ** 2.4)
    return np.clip(out, 0.0, 1.0)


def render_at(transform: str, ap1: np.ndarray, grey_code: float, srgb_encode) -> np.ndarray:
    """Linear AP1 to sRGB code through 'agx' or 'opendrt', with the exposure that shows a grey of 0.18 at grey_code (U92: the code of
    ACES 2.0, so that the scan of method 'apd' keeps its exposure)."""
    if transform not in ("agx", "opendrt"):
        raise ValueError(f"render_at needs 'agx' or 'opendrt', not {transform!r}")
    key = (transform, round(grey_code, 9))
    if key not in _GREY_STOPS:
        lo, hi = -4.0, 4.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            code = _shown(transform, np.full((1, 3), 0.18 * 2.0 ** mid), np.eye(3), srgb_encode)[0, 1]
            lo, hi = (mid, hi) if code < grey_code else (lo, mid)
        _GREY_STOPS[key] = 0.5 * (lo + hi)
    return _shown(transform, ap1 * 2.0 ** _GREY_STOPS[key], np.eye(3), srgb_encode)


def render_native(transform: str, ap1: np.ndarray, srgb_encode) -> np.ndarray:
    """Linear AP1 to sRGB code through 'agx' or 'opendrt' with no exposure change: ACES 0.18 goes in as 0.18 (U92)."""
    if transform not in ("agx", "opendrt"):
        raise ValueError(f"render_native needs 'agx' or 'opendrt', not {transform!r}")
    return _shown(transform, ap1, np.eye(3), srgb_encode)


def render(transform: str, ap1: np.ndarray, ap1_to_rec709: np.ndarray, srgb_encode) -> np.ndarray:
    """Linear AP1 (..., 3) to sRGB code through the transform, with the grey exposure of the module text."""
    if transform not in TRANSFORMS or transform == "log_curve":
        raise ValueError(f"unknown display transform {transform!r}")
    if transform not in _GREY_STOPS:
        target = float(srgb_encode(np.array([0.18]))[0])
        lo, hi = -4.0, 4.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            code = _shown(transform, np.full((1, 3), 0.18 * 2.0 ** mid), ap1_to_rec709, srgb_encode)[0, 1]
            lo, hi = (mid, hi) if code < target else (lo, mid)
        _GREY_STOPS[transform] = 0.5 * (lo + hi)
    return _shown(transform, ap1 * 2.0 ** _GREY_STOPS[transform], ap1_to_rec709, srgb_encode)
