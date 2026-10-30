"""Domain of the spectral reconstructions on real RAW photos (step P1).

Input: a RAW photo library (default: the Alcedo Studio test library given by the user on
2026-10-29), the rawtoaces-data camera sensitivities of the cameras in that library, the
reconstruction candidates, and the training reflectances.
Output: results/p1_spectral_input/raw_photos.json. No pixel data and no image is written to the
repository; the report names each file and gives only statistics.

Step: P1, README section 8 ("near-black and saturated-light probes ... residual domain
failures"). The README does not add a RAW decoder by default; the user supplied the RAW library
for this step. LibRaw (through rawpy) decodes the files.

Method per file:
1. LibRaw postprocess: AHD demosaic (X-Trans: LibRaw default), camera-native RGB
   (output_color raw), linear (gamma 1, 1), white balance 1, 1, 1, 1, no automatic brightness,
   16 bit, no rotation. A pixel is clipped when a channel is at or above CLIP_FRACTION of 65535.
2. Scene light: the light of a family (CIE daylight 4000-25000 K, Planckian 2000-4000 K) whose
   camera white balance (from the measured camera sensitivity) is nearest to the as-shot white
   balance of the file, in log R/G and log B/G (the rawtoaces method of light selection).
3. IDT: camera RGB -> scene XYZ fitted on the rawtoaces 190 patches under that light, in CIELAB
   with the white preserved, without chromatic adaptation (run_p1_checks.fit_idt). AP1 = the
   colorimetry of the scene radiance. No RGC is applied (README U13).
4. Statistics over every unclipped pixel at full resolution: Y <= 0, an AP1 component < 0,
   outside the spectral locus (no non-negative spectrum has this XYZ), outside the Rec. 709
   triangle with the E_ref white (Mallett-Yuksel basis weight < 0). Each statistic is also
   given for near-black pixels (Y below NEAR_BLACK_Y of the clip level).
5. Reconstruction on SAMPLE_PIXELS random unclipped pixels with Y above SAMPLE_MIN_Y of the
   clip level: domain of each candidate; spread of the Portra 400 Status M density over the
   candidates that are in their domain (max - min per channel). The exposure is set so that the
   median Y of the file is an 18 % grey at the P0 midscale exposure (an assumption for this
   statistic only; the domain results do not depend on it).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_p1_checks as checks  # noqa: E402
import spectral_datasets as sd  # noqa: E402
import spectral_reconstruction as sr  # noqa: E402
from spectral_reconstruction import p0  # noqa: E402

DEFAULT_LIBRARY = Path("D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/camera")
RESULT_PATH = checks.RESULT_DIR / "raw_photos.json"
CLIP_FRACTION = 0.98
NEAR_BLACK_Y = 1.0 / 256.0
SAMPLE_MIN_Y = 1.0 / 1024.0
SAMPLE_PIXELS = 2000
CHUNK_PIXELS = 1 << 22
RAW_SUFFIXES = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".rw2", ".dng"}

# Library directory -> rawtoaces-data camera name.
CAMERA_OF_DIRECTORY = {
    "canon/1dxii": "Canon_EOS-1D_X_Mark_II", "canon/5div": "Canon_EOS_5D_Mark_IV", "canon/r": "Canon_EOS_R",
    "canon/r5": "Canon_EOS_R5", "canon/r5ii": "Canon_EOS_R5m2", "canon/r6": "Canon_EOS_R6", "canon/r6ii": "Canon_EOS_R6m2",
    "fuji/xt4": "Fujifilm_X-T4", "lumix/gx9": "Panasonic_DC-GX9", "nikon/d7000": "Nikon_D7000", "nikon/d800e": "Nikon_D800E",
    "nikon/d810": "Nikon_D810", "nikon/d850": "Nikon_D850", "nikon/zf": "Nikon_Z_f", "sony/a6400": "Sony_ILCE-6400",
    "sony/a7cii": "Sony_ILCE-7CM2", "sony/a7iii": "Sony_ILCE-7M3", "sony/a7iv": "Sony_ILCE-7M4",
    "sony/a7rii": "Sony_ILCE-7RM2", "sony/a7riii": "Sony_ILCE-7RM3", "sony/a7riv": "Sony_ILCE-7RM4",
}


def planck(wavelengths_nm: np.ndarray, temperature_k: float) -> np.ndarray:
    lam = wavelengths_nm * 1e-9
    c2 = 1.4388e-2
    return 1.0 / (lam ** 5 * (np.exp(c2 / (lam * temperature_k)) - 1.0))


def candidate_lights(c: sr.Colorimetry) -> dict[str, np.ndarray]:
    out = {}
    for t in range(2000, 4000, 50):
        out[f"planck_{t}K"] = planck(c.wavelengths, float(t))
    for t in range(4000, 25001, 100):
        out[f"daylight_{t}K"] = p0.cie_daylight_relative_spd(t * 1.4380 / 1.4388, c.wavelengths)
    return {k: v / c.xyz(v)[1] for k, v in out.items()}


def select_light(camera_w: np.ndarray, as_shot_wb: np.ndarray, lights: dict[str, np.ndarray]) -> tuple[str, float]:
    target = np.log(np.array([as_shot_wb[0] / as_shot_wb[1], as_shot_wb[2] / as_shot_wb[1]]))
    best, best_d = None, np.inf
    for name, light in lights.items():
        r, g, b = camera_w @ light
        d = np.linalg.norm(np.log(np.array([g / r, g / b])) - target)
        if d < best_d:
            best, best_d = name, d
    return best, float(best_d)


def decode(path: Path):
    import rawpy

    with rawpy.imread(str(path)) as raw:
        wb = np.array(raw.camera_whitebalance, dtype=float)
        if wb[3] == 0:
            wb[3] = wb[1]
        rgb = raw.postprocess(output_color=rawpy.ColorSpace.raw, gamma=(1, 1), no_auto_bright=True,
                              use_camera_wb=False, use_auto_wb=False, user_wb=[1.0, 1.0, 1.0, 1.0],
                              output_bps=16, user_flip=0, highlight_mode=rawpy.HighlightMode.Clip)
        info = {"color_desc": raw.color_desc.decode(), "raw_pattern_shape": list(raw.raw_pattern.shape) if raw.raw_pattern is not None else None,
                "as_shot_white_balance": wb.round(4).tolist()}
    return rgb, wb, info


def library_files(library: Path) -> list[tuple[Path, str]]:
    files = []
    for directory, camera in CAMERA_OF_DIRECTORY.items():
        folder = library / directory
        if not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*")):
            if p.suffix.lower() not in RAW_SUFFIXES:
                continue
            if p.stem.endswith("_dng"):
                continue  # a DNG conversion of another file in the library
            if "ycbcr_compressed" in p.parts:
                continue  # Sony YCbCr-compressed ARW: not a raw mosaic
            files.append((p, camera))
    return files


def main() -> int:
    library = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] != "-" else DEFAULT_LIBRARY
    c = sr.Colorimetry()
    ev = checks.Evaluator(c)
    sets = sd.load_all_reflectance_sets()
    training = {k: v.reflectance for k, v in sets.items()}
    moment, _ = sr.prior_second_moment(c, training)
    my = sr.MallettYukselBasis(c)
    methods = [my, sr.SigmoidPolynomial(c), sr.MeasuredPriorLinear(c, moment), sr.MeasuredPriorNonnegative(c, moment),
               sr.MeasuredPriorLocal(c, moment, training)]
    lights = candidate_lights(c)
    idt_training = sets["rawtoaces_190"].reflectance
    rng = np.random.default_rng(checks.RNG_SEED)
    out = {"library": str(library), "rules": {"clip_fraction": CLIP_FRACTION, "near_black_y_of_clip": NEAR_BLACK_Y,
                                              "sample_min_y_of_clip": SAMPLE_MIN_Y, "sample_pixels": SAMPLE_PIXELS},
           "files": {}, "decode_failures": {}}
    files = library_files(library)
    if len(sys.argv) > 2:
        files = files[:int(sys.argv[2])]  # optional: the first N files (timing runs)
    print(f"{len(files)} files")
    for path, camera in files:
        t0 = time.time()
        rel = path.relative_to(library).as_posix()
        try:
            rgb, wb, info = decode(path)
        except Exception as error:  # a decode failure is reported per file, not replaced
            out["decode_failures"][rel] = f"{type(error).__name__}: {error}"
            print(f"decode failure {rel}: {error}")
            continue
        cw = sd.read_camera_sensitivity(camera)
        light_name, wb_distance = select_light(cw, wb, lights)
        light = lights[light_name]
        xyz_from_cam = checks.fit_idt(c, cw, light, idt_training)
        ap1_from_cam = c.xyz_to_ap1 @ xyz_from_cam
        flat = rgb.reshape(-1, 3)
        n = len(flat)
        # The clip level in Y: the camera white (all channels at the clip value) after the IDT.
        clip_y = float((xyz_from_cam @ np.full(3, 65535.0))[1])
        counts = {k: 0 for k in ("clipped", "y_not_positive", "ap1_negative", "outside_locus", "outside_rec709")}
        near = {k: 0 for k in ("pixels", "y_not_positive", "ap1_negative", "outside_locus", "outside_rec709")}
        ys = []
        for start in range(0, n, CHUNK_PIXELS):
            cam = flat[start:start + CHUNK_PIXELS].astype(np.float64)
            clipped = np.any(cam >= CLIP_FRACTION * 65535.0, axis=1)
            counts["clipped"] += int(clipped.sum())
            cam = cam[~clipped]
            xyz = cam @ xyz_from_cam.T
            ap1 = xyz @ c.xyz_to_ap1.T
            y = xyz[:, 1] / clip_y
            ys.append(y[::97])
            flags = {"y_not_positive": y <= 0, "ap1_negative": np.any(ap1 < 0, axis=1),
                     "outside_locus": ~c.inside_spectral_locus(xyz),
                     "outside_rec709": np.any(ap1 @ my.ap1_to_rgb709.T < 0, axis=1)}
            nb = y < NEAR_BLACK_Y
            near["pixels"] += int(nb.sum())
            for k, f in flags.items():
                counts[k] += int(f.sum())
                near[k] += int((f & nb).sum())
        unclipped = n - counts["clipped"]
        entry = {"camera_sensitivity": camera, **info, "pixels": n, "selected_light": light_name,
                 "white_balance_log_distance": round(wb_distance, 4),
                 "unclipped_fraction": {k: round(v / max(unclipped, 1), 6) for k, v in counts.items() if k != "clipped"},
                 "clipped_fraction": round(counts["clipped"] / n, 6),
                 "near_black": {"fraction_of_unclipped": round(near["pixels"] / max(unclipped, 1), 6),
                                **{k: round(v / max(near["pixels"], 1), 6) for k, v in near.items() if k != "pixels"}}}
        # Reconstruction on sampled pixels.
        cam_all = flat.astype(np.float64)
        pick = rng.choice(n, size=min(n, 8 * SAMPLE_PIXELS), replace=False)
        cam_s = cam_all[pick]
        keep = ~np.any(cam_s >= CLIP_FRACTION * 65535.0, axis=1)
        xyz_s = cam_s[keep] @ xyz_from_cam.T
        keep_y = xyz_s[:, 1] / clip_y > SAMPLE_MIN_Y
        xyz_s = xyz_s[keep_y][:SAMPLE_PIXELS]
        median_y = float(np.median(np.concatenate(ys)[np.concatenate(ys) > 0])) * clip_y
        xyz_s *= 0.18 / median_y
        ap1_s = xyz_s @ c.xyz_to_ap1.T
        densities, domains = [], {}
        stage = {"decode_idt_and_full_resolution_statistics": round(time.time() - t0, 1)}
        for m in methods:
            t_m = time.time()
            rec = m.reconstruct(ap1_s)
            stage[m.name] = round(time.time() - t_m, 1)
            resp = ev.film_response(rec.radiance)
            ok = rec.domain & resp["in_curve"]
            domains[m.name] = {"in_domain": round(float(rec.domain.mean()), 5),
                               "in_domain_and_in_curve": round(float(ok.mean()), 5)}
            densities.append(np.where(ok[:, None], resp["density"], np.nan))
        dens = np.stack(densities)
        all_ok = np.all(np.isfinite(dens[..., 0]), axis=0)
        spread = np.nanmax(dens, axis=0) - np.nanmin(dens, axis=0)
        entry["sample"] = {"pixels": int(len(ap1_s)), "methods": domains,
                           "all_methods_in_domain": round(float(all_ok.mean()), 5),
                           "status_m_spread_over_methods": checks.stats(spread[all_ok]),
                           "ap1_negative": round(float(np.any(ap1_s < 0, axis=1).mean()), 5)}
        entry["seconds"] = round(time.time() - t0, 1)
        entry["stage_seconds"] = stage
        out["files"][rel] = entry
        print(f"{rel}: {entry['seconds']} s, light {light_name}, outside locus {entry['unclipped_fraction']['outside_locus']:.4f}")
    # Pooled over files (each file has the same weight).
    def pooled(key):
        vals = [e["unclipped_fraction"][key] for e in out["files"].values()]
        return {"median": float(np.median(vals)), "max": float(np.max(vals)), "files_above_0.001": int(np.sum(np.array(vals) > 0.001))}
    out["pooled_over_files"] = {k: pooled(k) for k in ("y_not_positive", "ap1_negative", "outside_locus", "outside_rec709")}
    RESULT_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {RESULT_PATH.relative_to(checks.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
