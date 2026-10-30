"""Camera-free method, near-black rule, and revised acceptance criteria of step P1 (README U14, U15).

Input: the libraries of run_p1_checks.py; the RAW library for section E.
Output: results/p1_spectral_input/camera_free/*.json.

Step: P1, open items P1-O1 to P1-O5. The reconstruction does not receive a camera identity. The
camera sensitivities are used only to simulate or prepare the input and to measure a held-out
camera population.

Sections:
A. combined_candidate.json: measured_prior_local_nonnegative against JH under E_ref, D55, D65:
   prior without the test dataset, and prior from the other half of each dataset (ISSA by subject).
B. white_only_reference.json: reference light from the scene white chromaticity only: the nearest
   member (u'v') of the daylight and Planckian family. The spectrum of the light is not used.
C. held_out_makers.json: camera AP1 from a maker that is not in the camera population; D55 and A,
   reference light as in section B. Compares JH, the combined candidate, and the camera population
   prior.
D. near_black_rule.json: rule 'spectral_locus_projection': continuity, scaling, noise, probes.
E. raw_photos_rule.json: the combined candidate on 2,000 pixels of each of the 44 RAW files.
F. camera_population_checks.json: the camera population prior: exposure scaling (<= 1e-9), finite
   output on near-black probes, and the error when the input has no camera error (exact XYZ, D55).

Revised acceptance criteria (U15), set before the first run of this script and after the five
candidates of run_p1_checks.py were seen; the P1 report states this order. For each dataset under
E_ref, D55, and D65, each channel:
- Status M error p95 <= (0.025, 0.011, 0.054), the p95 of the difference between measured metamers
  from different datasets: an estimate with this error is no worse than another real object of the
  same colour.
- |signed median Status M error| <= 0.01: a systematic error is a colour cast on a whole class of
  colours; 0.01 is the P0-derived value (about 0.017 log H at gamma 0.6).
The values 0.01 / 0.03 of run_p1_checks.py stay in the report as the first tolerance. The max is
reported and is not a criterion: measured metamers reach 0.063.

Rule checks, set before the first run:
- continuity of the rule: on 2,000 lines through the cone boundary (2,000 steps per line), the XYZ
  step of the output is at most 1 + 1e-6 times the step of the input in (X/Y, Z/Y);
- scaling: relative error of Q <= 1e-9 for scales 1e-6 to 1e3;
- finite output for every input; every sampled RAW pixel in the domain of the rule;
- noise: mean Status M of noisy near black minus Status M of the noise-free mean <= 0.002 at mean
  and sigma 1e-3 (P0 midscale exposure); other noise levels are reported.
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
import run_p1_raw_photos as raw  # noqa: E402
import spectral_datasets as sd  # noqa: E402
import spectral_reconstruction as sr  # noqa: E402

OUT_DIR = checks.RESULT_DIR / "camera_free"
P95_LIMIT = np.array([0.025, 0.011, 0.054])
BIAS_LIMIT = 0.01
SKIN_SUBSET = 1000


def write(name: str, payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {name}", flush=True)


def density_summary(d: np.ndarray) -> dict:
    d = d[np.all(np.isfinite(d), axis=1)]
    out = checks.stats(d)
    median = np.median(d, axis=0)
    out["signed_median"] = np.round(median, 5).tolist()
    out["p95_within_limit"] = bool(np.all(np.percentile(np.abs(d), 95, axis=0) <= P95_LIMIT))
    out["bias_within_limit"] = bool(np.all(np.abs(median) <= BIAS_LIMIT))
    return out


def density_error(ev, method, truth, xyz, white, ap1) -> np.ndarray:
    cmp = ev.compare(truth, xyz, white, method.reconstruct(ap1))
    return np.where(cmp["dense"][:, None], cmp["d_density"], np.nan)


def split(sets) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(checks.RNG_SEED)
    return {k: checks.split_halves(s, rng) for k, s in sets.items()}


def section_a(c, ev, sets, lights) -> None:
    out = {"held_out_dataset": {}, "other_half": {}}
    halves = split(sets)
    jh = sr.SigmoidPolynomial(c)
    train_half = {k: s.reflectance[halves[k]] for k, s in sets.items()}
    moment_half, _ = sr.prior_second_moment(c, train_half)
    combined_half = sr.MeasuredPriorLocalNonnegative(c, moment_half, train_half)
    for name, s in sets.items():
        train = {k: v.reflectance for k, v in sets.items() if k != name}
        moment, _ = sr.prior_second_moment(c, train)
        combined = sr.MeasuredPriorLocalNonnegative(c, moment, train)
        for key, method, refl in (("held_out_dataset", combined, s.reflectance),
                                  ("other_half", combined_half, s.reflectance[~halves[name]])):
            for light in checks.DAYLIGHT_SCENES:
                t0 = time.time()
                radiance = refl * lights[light][None, :]
                xyz = c.xyz(radiance)
                ap1 = xyz @ c.xyz_to_ap1.T
                truth = ev.film_response(radiance)
                white = c.xyz(lights[light])
                rec = method.reconstruct(ap1)
                cmp = ev.compare(truth, xyz, white, rec)
                moved = rec.detail["moved_by_rule"]
                entry = {"count": len(refl), "moved_by_rule": int(moved.sum()),
                         "quadratic_solves": rec.detail["quadratic_solves"], "outside_domain": int((~rec.domain).sum()),
                         "xyz_delta_e_ab_max_not_moved": float(cmp["delta_e"][rec.domain & ~moved].max()),
                         "combined": density_summary(np.where(cmp["dense"][:, None], cmp["d_density"], np.nan)),
                         "jakob_hanika_sigmoid": density_summary(density_error(ev, jh, truth, xyz, white, ap1))}
                out[key].setdefault(name, {})[light] = entry
                print(f"A {key} {name} {light}: {time.time() - t0:.1f} s", flush=True)
    write("combined_candidate.json", out)


def nearest_family_light(c, family: dict[str, np.ndarray], white_xyz: np.ndarray) -> tuple[str, float]:
    names = list(family)
    uv = sr.MeasuredPriorLocal.chromaticity_uv(np.stack([c.xyz(family[n]) for n in names]))
    target = sr.MeasuredPriorLocal.chromaticity_uv(white_xyz[None])
    d = np.linalg.norm(uv - target, axis=1)
    k = int(np.argmin(d))
    return names[k], float(d[k])


def section_b(c, ev, sets, lights, family) -> None:
    halves = split(sets)
    train = {k: s.reflectance[halves[k]] for k, s in sets.items()}
    out = {"rule": "reference light = nearest daylight or Planckian member in u'v' to the scene white", "scenes": {}}
    for light in ("D55", "D65", "A", "FL2", "FL11", "LED-B3", "LED-RGB1", "HP1"):
        name, distance = nearest_family_light(c, family, c.xyz(lights[light]))
        cl = checks.with_reference_light(c, family[name])
        moment, _ = sr.prior_second_moment(cl, train)
        combined = sr.MeasuredPriorLocalNonnegative(cl, moment, train)
        jh = sr.SigmoidPolynomial(cl)
        entry = {"selected": name, "uv_distance": round(distance, 5), "datasets": {}}
        for ds, s in sets.items():
            t0 = time.time()
            radiance = s.reflectance[~halves[ds]] * lights[light][None, :]
            xyz = c.xyz(radiance)
            ap1 = xyz @ c.xyz_to_ap1.T
            truth = ev.film_response(radiance)
            white = c.xyz(lights[light])
            entry["datasets"][ds] = {"combined": density_summary(density_error(ev, combined, truth, xyz, white, ap1)),
                                     "jakob_hanika_sigmoid": density_summary(density_error(ev, jh, truth, xyz, white, ap1))}
            print(f"B {light} {ds}: {time.time() - t0:.1f} s", flush=True)
        out["scenes"][light] = entry
    write("white_only_reference.json", out)


def camera_error_statistics(c, cameras, idts, light, spectra) -> tuple[np.ndarray, np.ndarray]:
    """Mean and covariance per record of the IDT XYZ error over the cameras, divided by camera Y."""
    radiance = spectra * light[None, :]
    xyz = c.xyz(radiance)
    mean, moment, count = np.zeros_like(xyz), np.zeros((len(xyz), 3, 3)), np.zeros(len(xyz))
    for cam in cameras:
        cw, xyz_from_cam = idts[cam]
        estimate = (radiance @ cw.T) @ xyz_from_cam.T
        y = estimate[:, 1]
        ok = y > 1e-4
        e = np.where(ok[:, None], (estimate - xyz) / np.where(ok, y, 1.0)[:, None], 0.0)
        mean += e
        moment += np.einsum("ni,nj->nij", e, e)
        count += ok
    n = np.maximum(count, 1.0)
    mean /= n[:, None]
    return mean, moment / n[:, None, None] - np.einsum("ni,nj->nij", mean, mean)


def section_c(c, ev, sets, lights, family) -> None:
    halves = split(sets)
    rng = np.random.default_rng(checks.RNG_SEED)
    train = {k: s.reflectance[halves[k]] for k, s in sets.items()}
    all_train = np.vstack(list(train.values()))
    issa_test = sets["issa_skin"].reflectance[~halves["issa_skin"]]
    tests = {"gutierrez_natural": sets["gutierrez_natural"].reflectance[~halves["gutierrez_natural"]],
             "usgs_splib07": sets["usgs_splib07"].reflectance[~halves["usgs_splib07"]],
             "issa_skin_subset": issa_test[rng.choice(len(issa_test), SKIN_SUBSET, replace=False)]}
    cameras = sd.available_cameras()
    makers = sorted({n.split("_")[0] for n in cameras})
    idt_training = sets["rawtoaces_190"].reflectance
    out = {"makers": makers, "test_counts": {k: len(v) for k, v in tests.items()}, "scenes": {}}
    for light_name in ("D55", "A"):
        light = lights[light_name]
        white = c.xyz(light)
        selected, _ = nearest_family_light(c, family, white)
        cl = checks.with_reference_light(c, family[selected])
        moment, _ = sr.prior_second_moment(cl, train)
        combined, jh = sr.MeasuredPriorLocalNonnegative(cl, moment, train), sr.SigmoidPolynomial(cl)
        idts = {}
        for n in cameras:
            w = sd.read_camera_sensitivity(n)
            idts[n] = (w, checks.fit_idt(c, w, light, idt_training))
        pooled: dict[str, dict[str, list]] = {t: {} for t in tests}
        for maker in makers:
            t0 = time.time()
            held = [n for n in cameras if n.split("_")[0] == maker]
            kept = [n for n in cameras if n not in held]
            mean, second = camera_error_statistics(c, kept, idts, light, all_train)
            population = sr.MeasuredPriorLocalCameraPopulation(cl, train, mean, second)
            for tname, refl in tests.items():
                radiance = refl * light[None, :]
                xyz = c.xyz(radiance)
                truth = ev.film_response(radiance)
                for cam in held:
                    cw, xyz_from_cam = idts[cam]
                    ap1 = ((radiance @ cw.T) @ xyz_from_cam.T) @ c.xyz_to_ap1.T
                    for m in (jh, combined, population):
                        pooled[tname].setdefault(m.name, []).append(density_error(ev, m, truth, xyz, white, ap1))
            print(f"C {light_name} {maker}: {time.time() - t0:.1f} s", flush=True)
        out["scenes"][light_name] = {"selected_reference": selected,
                                     "datasets": {t: {m: density_summary(np.vstack(v)) for m, v in r.items()}
                                                  for t, r in pooled.items()}}
    write("held_out_makers.json", out)


def section_d(c, ev, sets, lights) -> None:
    train = {k: s.reflectance for k, s in sets.items()}
    moment, _ = sr.prior_second_moment(c, train)
    method = sr.MeasuredPriorLocalNonnegative(c, moment, train)
    proj = method.projection
    rng = np.random.default_rng(checks.RNG_SEED)
    # Continuity: lines in (X/Y, Z/Y) at Y = 1 from the white to far outside the cone.
    angle = rng.uniform(0, 2 * np.pi, 2000)
    direction = np.stack([np.cos(angle), np.sin(angle)], axis=1)
    worst = 0.0
    for k in range(len(direction)):
        s = np.linspace(0.0, 600.0, 2001)
        pts = proj.white + s[:, None] * direction[k]
        out_xyz, _, _ = proj.apply(np.stack([pts[:, 0], np.ones_like(s), pts[:, 1]], axis=1))
        step = np.linalg.norm(np.diff(out_xyz, axis=0), axis=1) / np.linalg.norm(np.diff(pts, axis=0), axis=1)
        worst = max(worst, float(step.max()))
    grey = c.xyz(0.18 * lights["E_ref"]) @ c.xyz_to_ap1.T
    out = {"continuity_max_output_over_input_step": worst, "continuity_pass": worst <= 1.0 + 1e-6, "noise": {}}
    # Scaling, with inputs inside and outside the cone.
    reflect = sets["rawtoaces_190"].reflectance * lights["D55"][None, :]
    x = np.vstack([rng.normal(1e-3, 1e-3, size=(300, 3)), c.xyz(reflect) @ c.xyz_to_ap1.T])
    x = x[x @ c.ap1_to_xyz[1] > 0]
    base = c.layer_exposure(method.reconstruct(x).radiance)
    largest, largest_sample, largest_major = 0.0, 0.0, 0.0
    sample_max = base.max(axis=1, keepdims=True)
    for scale in (1e-6, 1e-3, 0.5, 2.0, 16.0, 1e3):
        q = c.layer_exposure(method.reconstruct(scale * x).radiance)
        ok = base > 0
        major = base > 1e-6 * sample_max
        largest = max(largest, float(np.abs(q[ok] / (scale * base[ok]) - 1).max()))
        largest_major = max(largest_major, float(np.abs(q[major] / (scale * base[major]) - 1).max()))
        largest_sample = max(largest_sample, float((np.abs(q / scale - base) / sample_max).max()))
    out["scaling_max_relative_error"] = largest
    out["scaling_pass"] = largest <= 1e-9
    # Not part of the check: a failure in a layer far below the other layers of the sample is
    # float64 rounding. These two values separate that case.
    out["scaling_error_relative_to_largest_layer_of_sample"] = largest_sample
    out["scaling_max_relative_error_layers_above_1e-6_of_largest"] = largest_major
    # Noise levels relative to the 18 % grey at the P0 midscale exposure (AP1 of grey = 0.18).
    unit = grey / 0.18
    for mean_level, sigma in ((1e-3, 1e-3), (1e-2, 1e-2), (1e-2, 3e-3), (0.05, 0.05), (0.05, 0.01)):
        n = rng.normal(mean_level, sigma, size=(3000, 3)) * unit
        rec = method.reconstruct(n)
        resp = ev.film_response(rec.radiance)
        clean = ev.film_response(method.reconstruct((mean_level * unit)[None]).radiance)
        d = np.nanmean(resp["density"], axis=0) - clean["density"][0]
        out["noise"][f"mean_{mean_level:g}_sigma_{sigma:g}"] = {
            "mean_density_minus_noise_free": np.round(d, 5).tolist(),
            "density_std": np.round(np.nanstd(resp["density"], axis=0), 5).tolist(),
            "y_not_positive": int(rec.detail["y_not_positive"].sum()), "moved_by_rule": int(rec.detail["moved_by_rule"].sum()),
            "non_finite": int((~np.all(np.isfinite(rec.radiance), axis=1)).sum()), "quadratic_solves": rec.detail["quadratic_solves"]}
    out["noise_pass"] = bool(np.all(np.abs(out["noise"]["mean_0.001_sigma_0.001"]["mean_density_minus_noise_free"]) <= 0.002))
    # Gaussian probes.
    spectra, labels = [], []
    for fwhm in (10.0, 30.0):
        for center in np.arange(400.0, 701.0, 10.0):
            spectra.append(checks.gaussian_emission(c, center, fwhm))
            labels.append(f"gauss_{center:.0f}nm_fwhm{fwhm:.0f}")
    spectra = np.array(spectra)
    spectra *= 0.18 / c.xyz(spectra)[:, 1:2]
    xyz = c.xyz(spectra)
    truth = ev.film_response(spectra)
    rec = method.reconstruct(xyz @ c.xyz_to_ap1.T)
    cmp = ev.compare(truth, xyz, c.white_ref, rec)
    errors = np.where(cmp["dense"][:, None], cmp["d_density"], np.nan)
    out["gaussian_probes"] = {"count": len(labels), "outside_domain": int((~rec.domain).sum()),
                              "moved_by_rule": int(rec.detail["moved_by_rule"].sum()), "non_finite": int((~cmp["finite"]).sum()),
                              "fwhm10": density_summary(errors[:31]), "fwhm30": density_summary(errors[31:]),
                              "moved_labels": [l for l, m in zip(labels, rec.detail["moved_by_rule"]) if m]}
    write("near_black_rule.json", out)


def section_e(c, ev, sets) -> None:
    train = {k: s.reflectance for k, s in sets.items()}
    moment, _ = sr.prior_second_moment(c, train)
    method = sr.MeasuredPriorLocalNonnegative(c, moment, train)
    jh = sr.SigmoidPolynomial(c)
    family = raw.candidate_lights(c)
    rng = np.random.default_rng(checks.RNG_SEED)
    out = {"pixels_per_file": raw.SAMPLE_PIXELS, "exposure": "median Y of the sampled pixels = 18 % grey", "files": {}}
    for path, camera in raw.library_files(raw.DEFAULT_LIBRARY):
        t0 = time.time()
        rgb, wb, _ = raw.decode(path)
        cw = sd.read_camera_sensitivity(camera)
        light_name, _ = raw.select_light(cw, wb, family)
        xyz_from_cam = checks.fit_idt(c, cw, family[light_name], sets["rawtoaces_190"].reflectance)
        flat = rgb.reshape(-1, 3)
        pick = rng.choice(len(flat), size=raw.SAMPLE_PIXELS, replace=False)
        cam = flat[pick].astype(np.float64)
        cam = cam[~np.any(cam >= raw.CLIP_FRACTION * 65535.0, axis=1)]
        xyz = cam @ xyz_from_cam.T
        xyz *= 0.18 / float(np.median(xyz[xyz[:, 1] > 0, 1]))
        ap1 = xyz @ c.xyz_to_ap1.T
        rec = method.reconstruct(ap1)
        resp = ev.film_response(rec.radiance)
        jh_rec = jh.reconstruct(ap1)
        jh_resp = ev.film_response(jh_rec.radiance)
        both = resp["in_curve"] & jh_resp["in_curve"] & jh_rec.domain & rec.domain
        moved = rec.detail["moved_by_rule"]
        shift = np.linalg.norm(c.xyz(rec.radiance[moved]) - xyz[moved], axis=1) / xyz[moved, 1]
        entry = {"pixels": len(xyz), "outside_domain": int((~rec.domain).sum()),
                 "non_finite": int((~np.all(np.isfinite(rec.radiance), axis=1)).sum()),
                 "y_not_positive": int(rec.detail["y_not_positive"].sum()), "moved_by_rule": int(moved.sum()),
                 "quadratic_solves": rec.detail["quadratic_solves"], "above_curve_end": int((rec.domain & ~resp["in_curve"]).sum()),
                 "moved_median_relative_xyz_shift": round(float(np.median(shift)), 4) if moved.any() else None,
                 "difference_to_jh": checks.stats((resp["density"] - jh_resp["density"])[both]),
                 "seconds": round(time.time() - t0, 1)}
        out["files"][path.relative_to(raw.DEFAULT_LIBRARY).as_posix()] = entry
        print(f"E {path.name}: {entry['seconds']} s, moved {entry['moved_by_rule']}, y<=0 {entry['y_not_positive']}", flush=True)
    write("raw_photos_rule.json", out)


def section_f(c, ev, sets, lights, family) -> None:
    halves = split(sets)
    train = {k: s.reflectance[halves[k]] for k, s in sets.items()}
    light = lights["D55"]
    selected, _ = nearest_family_light(c, family, c.xyz(light))
    cl = checks.with_reference_light(c, family[selected])
    idts = {}
    for n in sd.available_cameras():
        w = sd.read_camera_sensitivity(n)
        idts[n] = (w, checks.fit_idt(c, w, light, sets["rawtoaces_190"].reflectance))
    mean, second = camera_error_statistics(c, list(idts), idts, light, np.vstack(list(train.values())))
    method = sr.MeasuredPriorLocalCameraPopulation(cl, train, mean, second)
    rng = np.random.default_rng(checks.RNG_SEED)
    grey_unit = (c.xyz(0.18 * light) @ c.xyz_to_ap1.T) / 0.18
    noisy = rng.normal(1e-3, 1e-3, size=(1000, 3)) * grey_unit
    reflect = c.xyz(sets["rawtoaces_190"].reflectance * light[None, :]) @ c.xyz_to_ap1.T
    x = np.vstack([noisy, reflect])
    rec = method.reconstruct(x)
    base = c.layer_exposure(rec.radiance)
    positive = x @ c.ap1_to_xyz[1] > 0
    sample_max = np.maximum(np.abs(base).max(axis=1, keepdims=True), 1e-300)
    largest, largest_major = 0.0, 0.0
    for scale in (1e-6, 1e-3, 0.5, 2.0, 16.0, 1e3):
        q = c.layer_exposure(method.reconstruct(scale * x).radiance)
        ok = (base > 0) & positive[:, None]
        major = ok & (base > 1e-6 * sample_max)
        largest = max(largest, float(np.abs(q[ok] / (scale * base[ok]) - 1).max()))
        largest_major = max(largest_major, float(np.abs(q[major] / (scale * base[major]) - 1).max()))
    out = {"reference": selected, "camera_population": len(idts), "scaling_max_relative_error": largest, "scaling_pass": largest <= 1e-9,
           "scaling_max_relative_error_layers_above_1e-6_of_largest": largest_major,
           "non_finite": int((~np.all(np.isfinite(rec.radiance), axis=1)).sum()), "negative_radiance": int(np.any(rec.radiance < 0, axis=1).sum()),
           "near_black_y_not_positive": int(rec.detail["y_not_positive"][:1000].sum()), "exact_xyz_input": {}}
    for ds, s in sets.items():
        radiance = s.reflectance[~halves[ds]] * light[None, :]
        xyz = c.xyz(radiance)
        ap1 = xyz @ c.xyz_to_ap1.T
        truth = ev.film_response(radiance)
        out["exact_xyz_input"][ds] = density_summary(density_error(ev, method, truth, xyz, c.xyz(light), ap1))
    write("camera_population_checks.json", out)


def main() -> int:
    sections = set(sys.argv[1:]) or set("ABCDEF")
    c = sr.Colorimetry()
    ev = checks.Evaluator(c)
    sets = sd.load_all_reflectance_sets()
    lights = checks.scene_lights(c)
    family = raw.candidate_lights(c)
    if "D" in sections:
        section_d(c, ev, sets, lights)
    if "A" in sections:
        section_a(c, ev, sets, lights)
    if "B" in sections:
        section_b(c, ev, sets, lights, family)
    if "C" in sections:
        section_c(c, ev, sets, lights, family)
    if "E" in sections:
        section_e(c, ev, sets)
    if "F" in sections:
        section_f(c, ev, sets, lights, family)
    return 0


if __name__ == "__main__":
    sys.exit(main())
