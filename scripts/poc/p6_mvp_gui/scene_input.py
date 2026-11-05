"""P13 scene input for the P6 viewer and CLI, with P12 stock character.

Input: the complete estimated RAW white and the graded AP1 image. Output:
matched-white spectral families and optional constrained film-layer exposures.
The tested P13 spectral solver is reused. No full spectral image is retained.
Project-authored code: GPL-3.0-only.
"""
from __future__ import annotations

from collections import OrderedDict
from functools import lru_cache
import hashlib
from pathlib import Path
import sys
import types

import numpy as np

MODES = {
    "current": "Current scene light and prior",
    "white_smooth": "Full RAW white / smooth",
    "white_led": "Full RAW white / LED",
    "white_fluorescent": "Full RAW white / fluorescent",
    "conditioned_smooth": "Constrained / smooth",
    "conditioned_led": "Constrained / LED",
}


@lru_cache(maxsize=1)
def solver_module() -> types.ModuleType:
    """Load the existing full-grid P13 algorithm only when it is selected."""
    directory = Path(__file__).resolve().parent.parent / "p13_spectral_input"
    sys.path.insert(0, str(directory))
    import spectral_input

    return spectral_input


@lru_cache(maxsize=16)
def _read_white(path: str, modified_ns: int, size: int) -> tuple[tuple, float]:
    white = solver_module().read_raw_white(Path(path))
    return tuple(float(value) for value in white.xyz), white.cct


def raw_white(path: Path) -> tuple[tuple[float, float, float], float]:
    """Cache RAW metadata by file identity; return full XYZ and estimated CCT."""
    stat = path.stat()
    return _read_white(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=1)
def _colourimetry():
    return solver_module().sr.Colorimetry()


@lru_cache(maxsize=16)
def matched_spectrum(mode: str, white: tuple[float, float, float]) -> tuple[tuple, dict]:
    """Use the selected P13 family at the full RAW white; no stock is involved."""
    module = solver_module()
    c = _colourimetry()
    target = np.asarray(white, dtype=np.float64)
    target = target / target[1]
    x, y = target[:2] / target.sum()
    n = (x - 0.3320) / (y - 0.1858)
    kelvin = float(round(np.clip(-449*n**3+3525*n*n-6823.3*n+5520.33, 2000, 15000)))
    family = mode.split("_", 1)[1]
    if family == "smooth":
        source = module.fp.cct_light(kelvin, c.wavelengths, c.xyz)
    elif family in ("led", "fluorescent"):
        source = module.sd.cie_light_sources()["LED-B3" if family == "led" else "FL11"]
    else:
        raise ValueError(f"unknown P13 light family {family!r}")
    spectrum, metrics = module.fit_white(c, source, target)
    return tuple(float(value) for value in spectrum), {
        "family": family, "RAW_white_XYZ": target.tolist(),
        "estimated_CCT_K": kelvin, "inferred_illuminant": True,
        "white_fit": metrics, "grid_nm": [360, 840, 1],
        "conditioned": mode.startswith("conditioned_"),
    }


class ConstrainedInput:
    """Keep two layer-exposure results, never a full spectral image.

    The cache includes the graded image, scene spectrum, and actual film-layer
    weights. P12 changes those weights, so a stock-character change recomputes
    the exposures. Scan timing and other downstream controls can reuse them.
    """

    def __init__(self) -> None:
        self.engine = solver_module().SpectralInput(_colourimetry())
        self.cache: OrderedDict = OrderedDict()
        self.last_stats: dict = {}

    def layer_exposure(self, negative: object, image: np.ndarray) -> tuple[np.ndarray, dict]:
        """Compute with the selected stock's current spectral sensitivities."""
        source = np.ascontiguousarray(image, dtype=np.float64)
        signature = hashlib.blake2b(source.view(np.uint8), digest_size=16).digest()
        weights = np.ascontiguousarray(negative.film.w_negative, dtype=np.float64)
        weight_signature = hashlib.blake2b(weights.view(np.uint8), digest_size=16).digest()
        spectrum = np.ascontiguousarray(negative.scene_spectrum, dtype=np.float64)
        key = (source.shape, signature, spectrum.tobytes(), weight_signature,
               negative.c.lux_seconds_per_y)
        if key in self.cache:
            raw, stats = self.cache.pop(key)
            self.cache[key] = raw, stats
            self.last_stats = {**stats, "cache_hit": True}
        else:
            result, stats = self.engine.exposures(
                source, spectrum, {"selected_stock": negative}, True)
            raw = result["selected_stock"]
            self.cache[key] = raw, stats
            while len(self.cache) > 2:
                self.cache.popitem(last=False)
            self.last_stats = {**stats, "cache_hit": False}
        return raw * negative.layer_gain, {
            "moved_by_rule": stats["moved_by_existing_locus_rule"],
            "y_not_positive": stats["Y_not_positive"],
        }

    def bind(self, negative: object) -> None:
        """Replace only the layer-exposure operation of this model instance."""
        owner = self

        def reference_exposure(model, ap1):
            return owner.layer_exposure(model, ap1)

        def image_exposure(model, image):
            q, stats = owner.layer_exposure(
                model, np.asarray(image, dtype=np.float64)+model.options.scene_flare)
            return np.asarray(q, dtype=np.float32), stats["moved_by_rule"], stats["y_not_positive"]

        negative.layer_exposure = types.MethodType(reference_exposure, negative)
        negative._image_layer_exposure = types.MethodType(image_exposure, negative)
