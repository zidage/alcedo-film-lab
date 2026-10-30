"""Checks and measurements of step P1 (spectral input), synthetic part.

Input: the reflectance datasets and light sources (spectral_datasets.py), the reconstruction
candidates (spectral_reconstruction.py), the P0 evaluator (Portra 400 layer sensitivities and
characteristic curves; Endura chain for section I).
Output: results/p1_spectral_input/*.json (summaries) and build/tmp/p1/eval/*.npz (per-sample
arrays for the plots).

Step: P1, README section 8: held-out XYZ and layer-exposure errors, exposure scaling, metamer
comparison, near-black and saturated-light probes. RGC is out of scope of this step (user
decision of 2026-10-29, README U13); all inputs here are without RGC.

Sections (each one writes one JSON file):
A. reference_white.json: ACES white against E_ref; Mallett-Yuksel basis fit.
B. heldout_reflectance.json: reflectances of each dataset under 9 scene lights. The measured
   prior is trained on the other datasets (leave one dataset out). Truth: the measured
   reflectance times the scene light. Input: AP1 of the truth (no white balance, no RGC).
   The in-sample linear floor is the 3x3 matrix AP1 -> Q fitted on the test set itself (least
   squares of the relative Q error); no method that is linear in AP1 can be better on average.
C. exposure_scaling.json: Q(s x) = s Q(x) for scales 1e-6 to 1e3.
D. near_black.json: grey ramp to 1e-12, exact zero, noisy near-black inputs with mixed signs.
E. saturated_light.json: Gaussian emission (FWHM 10 nm and 30 nm), CIE LED-RGB1, HP1, FL11.
F. metamers.json: measured metamer pairs (Delta E*ab <= 0.5 under D65) and the linear-program
   bounds of Q over all reflectances 0 <= rho <= 1 with the same XYZ.
G. camera_stage.json: camera RGB from 21 measured camera sensitivities; IDT fitted on the
   rawtoaces 190 patches; reconstruction from the camera AP1 under the XYZ constraint and
   under the camera constraint; direct camera RGB -> Q matrix.
H. film_sensitivity_variant.json: section B summary (D55) with the spectral_film_lut log-linear
   sensitivity extension instead of the P0 'zero' rule.
I. print_effect.json: Delta E*ab of the viewed print (uncalibrated P0 chain) between truth and
   reconstruction, for a fixed random subset.
J. scene_light_matched.json: section B for the non-daylight scene lights, with the scene light
   (assumed known) in place of E_ref as the reference light of every reconstruction.
K. in_distribution_prior.json: the measured prior trained on one half of every dataset and
   tested on the other half (ISSA split by subject, the others by a fixed random split), D55.
   The local prior is evaluated with sigma_uv 0.005, 0.01 (default), and 0.02.

Tolerances (set before the first run of this script; the order of magnitude of the red-layer
error was seen in a trial on rawtoaces_190 before, the tolerances were not changed after it):
- XYZ reproduction inside the domain of a method: Delta E*ab <= 0.1 (relative to the scene-light
  white, Y = 1).
- Layer exposure, "stable" per dataset and daylight scene light (D55, D65, E_ref): negative
  Status M error p95 <= 0.01 and max <= 0.03 for each channel. Reason: P0 found that a 0.1 log H
  channel offset gives C*ab 13 on the print grey; 0.01 density (about 0.017 log H at the
  negative gamma 0.6) is near the 2.0 C*ab grey tolerance of P0.
- Exposure scaling: relative error <= 1e-12 for linear methods, <= 1e-9 for the non-negative
  prior (deterministic solve on the Y-normalized input), <= 1e-6 for the sigmoid fit (iterative
  solve stops at Delta E*ab 1e-7).
- Near black and every probe: finite output (no NaN or infinite value) for every input; domain
  failures are counted and reported, not replaced.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import cKDTree

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import spectral_datasets as sd  # noqa: E402
import spectral_reconstruction as sr  # noqa: E402
from spectral_reconstruction import p0  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parents[2]
RESULT_DIR = REPO_ROOT / "results" / "p1_spectral_input"
EVAL_DIR = REPO_ROOT / "build" / "tmp" / "p1" / "eval"

XYZ_DELTA_E_TOLERANCE = 0.1
DENSITY_P95_TOLERANCE = 0.01
DENSITY_MAX_TOLERANCE = 0.03
METHOD_NAMES = ("mallett_yuksel_rec709", "jakob_hanika_sigmoid", "measured_prior_linear", "measured_prior_nonnegative",
                "measured_prior_local")
SCALING_TOLERANCE = {"measured_prior_local": 1e-12, "mallett_yuksel_rec709": 1e-12, "measured_prior_linear": 1e-12,
                     "measured_prior_nonnegative": 1e-9, "jakob_hanika_sigmoid": 1e-6,
                     "camera_prior_linear": 1e-12, "camera_prior_nonnegative": 1e-9}
LOCAL_SIGMA_STUDY = (0.005, 0.01, 0.02)  # u'v' widths of the local prior; 0.01 is the default
DAYLIGHT_SCENES = ("E_ref", "D55", "D65")
SCENE_LIGHTS = ("E_ref", "D55", "D65", "A", "FL2", "FL11", "LED-B3", "LED-RGB1", "HP1")
CHANNELS = ("red", "green", "blue")
RNG_SEED = 20261029


def write_json(name: str, payload: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    (RESULT_DIR / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {name}")


def stats(values: np.ndarray) -> dict:
    """Median, p95, max of |values| per channel (rows: samples)."""
    v = np.abs(np.atleast_2d(np.asarray(values)))
    if v.shape[0] == 0:
        return {"count": 0}
    return {"count": int(v.shape[0]), "p50": np.round(np.median(v, axis=0), 5).tolist(),
            "p95": np.round(np.percentile(v, 95, axis=0), 5).tolist(), "max": np.round(v.max(axis=0), 5).tolist()}


class Evaluator:
    def __init__(self, c: sr.Colorimetry) -> None:
        self.c = c
        curves = list(c.film.negative_curves.values())
        self.curve_end_log_h = np.array([cv.log_h[-1] for cv in curves])

    def film_response(self, radiance: np.ndarray) -> dict:
        """Q, log10 Q, and Status M density; masks for Q <= 0 and for exposure above the curve end.

        Rule 'zero_layer_exposure': a layer with Q = 0 exactly (narrowband light outside the
        published sensitivity domain) has the density of the curve start, the limit of the P0
        rule 'characteristic_curve_below_toe'. Its log10 Q is not defined, so it is excluded
        from the log Q statistics. Q < 0 (negative radiance) has no density."""
        q = self.c.layer_exposure(radiance)
        finite = np.all(np.isfinite(q), axis=1)
        positive = np.all(q > 0, axis=1) & finite
        nonnegative = np.all(q >= 0, axis=1) & finite
        log_q = np.full_like(q, np.nan)
        log_q[positive] = np.log10(q[positive])
        curve_start = np.array([cv.log_h[0] for cv in self.c.film.negative_curves.values()])
        with np.errstate(divide="ignore", invalid="ignore"):
            log_h = np.where(q > 0, self.c.film.negative_criterion_log_h + np.log10(np.where(q > 0, q, 1.0)), curve_start)
        in_curve = nonnegative & np.all(log_h <= self.curve_end_log_h + 1e-9, axis=1)
        density = np.full_like(q, np.nan)
        if in_curve.any():
            curves = list(self.c.film.negative_curves.values())
            density[in_curve] = np.stack([cv.density_at(log_h[in_curve, k]) for k, cv in enumerate(curves)], axis=1)
        return {"q": q, "log_q": log_q, "density": density, "positive": positive, "in_curve": in_curve}

    def compare(self, truth: dict, xyz_true: np.ndarray, white: np.ndarray, rec: sr.Reconstruction) -> dict:
        finite = np.all(np.isfinite(rec.radiance), axis=1)
        xyz = self.c.xyz(rec.radiance)
        de = np.linalg.norm(sr.xyz_to_lab(xyz, white) - sr.xyz_to_lab(xyz_true, white), axis=1)
        resp = self.film_response(rec.radiance)
        valid = rec.domain & finite & resp["positive"] & truth["positive"]
        dense = rec.domain & finite & resp["in_curve"] & truth["in_curve"]
        return {"finite": finite, "domain": rec.domain, "delta_e": de, "valid": valid, "dense": dense,
                "d_log_q": resp["log_q"] - truth["log_q"], "d_density": resp["density"] - truth["density"],
                "log_q": resp["log_q"], "density": resp["density"],
                "negative_radiance": np.any(rec.radiance < 0, axis=1)}

    def summary(self, cmp: dict) -> dict:
        v, d = cmp["valid"], cmp["dense"]
        dd = stats(cmp["d_density"][d])
        out = {
            "samples": int(len(v)),
            "non_finite_output": int((~cmp["finite"]).sum()),
            "outside_domain": int((~cmp["domain"]).sum()),
            "negative_radiance": int(cmp["negative_radiance"].sum()),
            "layer_exposure_not_positive": int((cmp["domain"] & ~v).sum()),
            "density_defined": int(d.sum()),
            "xyz_delta_e_ab_in_domain": stats(cmp["delta_e"][cmp["domain"] & cmp["finite"]][:, None]),
            "xyz_reproduced_in_domain": bool(np.all(cmp["delta_e"][cmp["domain"] & cmp["finite"]] <= XYZ_DELTA_E_TOLERANCE)),
            "d_log10_q": stats(cmp["d_log_q"][v]),
            "d_status_m": dd,
        }
        if dd["count"]:
            out["status_m_within_tolerance"] = bool(max(dd["p95"]) <= DENSITY_P95_TOLERANCE and max(dd["max"]) <= DENSITY_MAX_TOLERANCE)
        return out


def scene_lights(c: sr.Colorimetry) -> dict[str, np.ndarray]:
    lights = {"E_ref": c.e_ref, "D55": c.film.illuminants["D55"], "D65": c.film.illuminants["D65"],
              "D50": c.film.illuminants["D50"], "A": c.film.illuminants["A"]}
    lights.update(sd.cie_light_sources())
    return {k: v / c.xyz(v)[1] for k, v in lights.items()}


def linear_floor(ap1: np.ndarray, q: np.ndarray) -> np.ndarray:
    """In-sample 3x3 AP1 -> Q, least squares of the relative error; returns the predicted Q."""
    rows = []
    for k in range(3):
        m = np.linalg.lstsq(ap1 / q[:, [k]], np.ones(len(q)), rcond=None)[0]
        rows.append(m)
    return ap1 @ np.array(rows).T


def make_methods(c: sr.Colorimetry, my: sr.MallettYukselBasis, jh: sr.SigmoidPolynomial,
                 sets: dict[str, sd.ReflectanceSet], held_out: str | None) -> tuple[list, dict]:
    training = {k: v.reflectance for k, v in sets.items() if k != held_out}
    moment, info = sr.prior_second_moment(c, training)
    return [my, jh, sr.MeasuredPriorLinear(c, moment), sr.MeasuredPriorNonnegative(c, moment),
            sr.MeasuredPriorLocal(c, moment, training)], info


# --------------------------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------------------------


def section_a(c: sr.Colorimetry, my: sr.MallettYukselBasis) -> None:
    xy = c.white_ref[:2] / c.white_ref.sum()
    rgb_white = c.xyz(c.e_ref) @ c.xyz_to_ap1.T
    write_json("reference_white.json", {
        "e_ref": "CIE daylight formula, T = 6000 K (nominal 5996.66 K), on the 1 nm grid",
        "e_ref_chromaticity": xy.round(7).tolist(), "aces_white": sr.ACES_WHITE_XY.tolist(),
        "difference": (xy - sr.ACES_WHITE_XY).round(7).tolist(),
        "ap1_of_e_ref_white": rgb_white.round(7).tolist(),
        "ap1_to_xyz": c.ap1_to_xyz.round(10).tolist(),
        "mallett_yuksel_basis": my.fit_info,
        "mallett_yuksel_basis_knots": {"wavelength_nm": c.knots.tolist(), "red": my.basis_knots[0].round(6).tolist(),
                                        "green": my.basis_knots[1].round(6).tolist(), "blue": my.basis_knots[2].round(6).tolist()},
    })


def section_b(c, ev, my, jh, sets, lights) -> dict:
    out = {"scene_lights": list(SCENE_LIGHTS), "datasets": {}, "prior": {}}
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    for name, s in sets.items():
        methods, info = make_methods(c, my, jh, sets, name)
        out["prior"][name] = info
        out["datasets"][name] = {"count": int(len(s.reflectance)), "rejected": s.rejected, "clipped_values": s.clipped_values,
                                 "measured_range_nm": [float(v) for v in s.measured_range_nm], "notes": s.notes, "scenes": {}}
        for light in SCENE_LIGHTS:
            t0 = time.time()
            radiance = s.reflectance * lights[light][None, :]
            xyz = c.xyz(radiance)
            white = c.xyz(lights[light])
            ap1 = xyz @ c.xyz_to_ap1.T
            truth = ev.film_response(radiance)
            entry = {"truth_above_curve_end": int((truth["positive"] & ~truth["in_curve"]).sum()),
                     "inside_spectral_locus": int(c.inside_spectral_locus(xyz).sum()),
                     "ap1_negative_component": int(np.any(ap1 < 0, axis=1).sum()), "methods": {}}
            arrays = {"log_q_true": truth["log_q"], "density_true": truth["density"], "ap1": ap1}
            for m in methods:
                cmp = ev.compare(truth, xyz, white, m.reconstruct(ap1))
                entry["methods"][m.name] = ev.summary(cmp)
                arrays[f"d_density_{m.name}"] = np.where(cmp["dense"][:, None], cmp["d_density"], np.nan)
                arrays[f"d_log_q_{m.name}"] = np.where(cmp["valid"][:, None], cmp["d_log_q"], np.nan)
            ok = truth["positive"]
            q_floor = linear_floor(ap1[ok], truth["q"][ok])
            floor_ok = np.all(q_floor > 0, axis=1)
            fq = np.full_like(truth["q"], np.nan)
            fq[np.flatnonzero(ok)[floor_ok]] = q_floor[floor_ok]
            floor_resp = {"q": fq}
            dl = np.log10(fq) - truth["log_q"]
            fin = np.all(np.isfinite(dl), axis=1)
            dens = np.full_like(fq, np.nan)
            in_c = fin & truth["in_curve"] & np.all(c.film.negative_criterion_log_h + np.log10(np.where(fin[:, None], fq, 1.0)) <= ev.curve_end_log_h, axis=1)
            dens[in_c] = c.negative_status_m(fq[in_c])
            entry["in_sample_linear_floor"] = {"d_log10_q": stats(dl[fin]), "d_status_m": stats((dens - truth["density"])[in_c]),
                                               "layer_exposure_not_positive": int((ok.sum() - floor_ok.sum()))}
            arrays["d_density_linear_floor"] = dens - truth["density"]
            out["datasets"][name]["scenes"][light] = entry
            np.savez_compressed(EVAL_DIR / f"heldout_{name}_{light}.npz", **arrays)
            print(f"B {name} {light}: {time.time() - t0:.1f} s")
    # Acceptance per method: stable on every dataset under the daylight scenes.
    accept = {}
    for mname in METHOD_NAMES:
        accept[mname] = all(out["datasets"][d]["scenes"][l]["methods"][mname].get("status_m_within_tolerance", False)
                            for d in out["datasets"] for l in DAYLIGHT_SCENES)
    out["stable_on_all_datasets_under_daylight"] = accept
    out["floor_within_tolerance_under_daylight"] = {
        d: {l: bool(max(out["datasets"][d]["scenes"][l]["in_sample_linear_floor"]["d_status_m"]["p95"]) <= DENSITY_P95_TOLERANCE)
            for l in DAYLIGHT_SCENES} for d in out["datasets"]}
    write_json("heldout_reflectance.json", out)
    return out


def section_c(c, my, jh, sets, lights) -> None:
    methods, _ = make_methods(c, my, jh, sets, None)
    s = sets["rawtoaces_190"].reflectance * lights["D55"][None, :]
    ap1 = c.xyz(s) @ c.xyz_to_ap1.T
    scales = [1e-6, 1e-3, 0.5, 2.0, 16.0, 1e3]
    out = {"input": "rawtoaces_190 under D55", "scales": scales, "methods": {}}
    for m in methods:
        rec = m.reconstruct(ap1)
        q1 = c.layer_exposure(rec.radiance)
        worst = 0.0
        domain_changes = 0
        for k in scales:
            r2 = m.reconstruct(k * ap1)
            q2 = c.layer_exposure(r2.radiance)
            both = rec.domain & r2.domain
            domain_changes += int((rec.domain != r2.domain).sum())
            worst = max(worst, float(np.abs(q2[both] / (k * q1[both]) - 1).max()))
        out["methods"][m.name] = {"max_relative_error": worst, "domain_changes": domain_changes,
                                  "tolerance": SCALING_TOLERANCE[m.name], "pass": worst <= SCALING_TOLERANCE[m.name] and domain_changes == 0}
    write_json("exposure_scaling.json", out)


def section_d(c, my, jh, sets, lights) -> None:
    methods, _ = make_methods(c, my, jh, sets, None)
    rng = np.random.default_rng(RNG_SEED)
    grey = c.xyz(0.18 * lights["E_ref"]) @ c.xyz_to_ap1.T
    ramp = grey[None, :] * 10.0 ** -np.arange(0, 13)[:, None]
    noisy = rng.normal(1e-3, 1e-3, size=(10000, 3))  # near-black with read noise; mixed signs
    probes = {"grey_ramp_to_1e-12": ramp, "zero": np.zeros((1, 3)),
              "noisy_near_black_mean_1e-3_sigma_1e-3": noisy,
              "one_negative_component": np.array([[0.01, 0.02, -0.001], [-0.001, 0.01, 0.01], [0.01, -0.0005, 0.01]]),
              "negative_luminance": np.array([[-0.01, -0.01, -0.01], [0.001, -0.01, 0.001]])}
    out = {"probes": {}}
    for pname, x in probes.items():
        entry = {"count": int(len(x)), "methods": {}}
        y = (x @ c.ap1_to_xyz.T)[:, 1]
        entry["inputs_with_y_not_positive"] = int((y <= 0).sum())
        entry["inputs_inside_spectral_locus"] = int(c.inside_spectral_locus(x @ c.ap1_to_xyz.T).sum())
        for m in methods:
            rec = m.reconstruct(x)
            q = c.layer_exposure(rec.radiance)
            e = {"non_finite_output": int((~np.all(np.isfinite(rec.radiance), axis=1)).sum()),
                 "outside_domain": int((~rec.domain).sum()),
                 "negative_radiance": int(np.any(rec.radiance < 0, axis=1).sum()),
                 "layer_exposure_not_positive": int((~np.all(q > 0, axis=1)).sum())}
            if pname == "grey_ramp_to_1e-12":
                e["q_over_scale_relative_spread"] = float(np.ptp(q[:, 1] / ramp[:, 1]) / np.mean(q[:, 1] / ramp[:, 1]))
            if pname == "zero":
                e["zero_input_radiance_max_abs"] = float(np.abs(rec.radiance).max())
            entry["methods"][m.name] = e
        out["probes"][pname] = entry
    write_json("near_black.json", out)


def gaussian_emission(c: sr.Colorimetry, center: float, fwhm: float) -> np.ndarray:
    sigma = fwhm / (2 * np.sqrt(2 * np.log(2)))
    return np.exp(-0.5 * ((c.wavelengths - center) / sigma) ** 2)


def section_e(c, ev, my, jh, sets, lights) -> None:
    methods, _ = make_methods(c, my, jh, sets, None)
    spectra, labels = [], []
    for fwhm in (10.0, 30.0):
        for center in np.arange(400.0, 701.0, 10.0):
            spectra.append(gaussian_emission(c, center, fwhm))
            labels.append(f"gauss_{center:.0f}nm_fwhm{fwhm:.0f}")
    for name in ("LED-RGB1", "HP1", "FL11", "FL2", "LED-B3"):
        spectra.append(lights[name])
        labels.append(name)
    spectra = np.array(spectra)
    spectra *= 0.18 / c.xyz(spectra)[:, 1:2]  # every probe at the luminance of an 18 % grey
    xyz = c.xyz(spectra)
    white = c.white_ref
    ap1 = xyz @ c.xyz_to_ap1.T
    truth = ev.film_response(spectra)
    out = {"scale": "each probe has Y = 0.18 (white diffuser under E_ref: Y = 1)", "probes": {}}
    per_method = {}
    for m in methods:
        per_method[m.name] = ev.compare(truth, xyz, white, m.reconstruct(ap1))
    locus = c.inside_spectral_locus(xyz)
    for k, label in enumerate(labels):
        e = {"ap1": ap1[k].round(5).tolist(), "inside_spectral_locus": bool(locus[k]),
             "log10_q_true": truth["log_q"][k].round(4).tolist(), "methods": {}}
        for mname, cmp in per_method.items():
            e["methods"][mname] = {"in_domain": bool(cmp["domain"][k]), "finite": bool(cmp["finite"][k]),
                                   "d_log10_q": None if not cmp["valid"][k] else cmp["d_log_q"][k].round(4).tolist(),
                                   "d_status_m": None if not cmp["dense"][k] else cmp["d_density"][k].round(4).tolist()}
        out["probes"][label] = e
    out["summary"] = {mname: {"gaussian_fwhm10": ev.summary({kk: v[:31] for kk, v in cmp.items()}),
                              "gaussian_fwhm30": ev.summary({kk: v[31:62] for kk, v in cmp.items()}),
                              "cie_sources": ev.summary({kk: v[62:] for kk, v in cmp.items()})}
                      for mname, cmp in per_method.items()}
    write_json("saturated_light.json", out)


def section_f(c, ev, my, jh, sets, lights) -> None:
    """Metamers: measured pairs and linear-program bounds."""
    d65 = lights["D65"]
    white = c.xyz(d65)
    names, spectra = [], []
    for s in sets.values():
        spectra.append(s.reflectance)
        names += [f"{s.name}:{l}" for l in s.labels]
    refl = np.vstack(spectra)
    radiance = refl * d65[None, :]
    xyz = c.xyz(radiance)
    lab = sr.xyz_to_lab(xyz, white)
    truth = ev.film_response(radiance)
    tree = cKDTree(lab)
    pairs = np.array(sorted(tree.query_pairs(0.5)))
    dataset = np.array([n.split(":")[0] for n in names])
    # Exclude identical spectra (repeated records): a metamer pair must differ in spectrum.
    rms = np.sqrt(np.mean((refl[pairs[:, 0]] - refl[pairs[:, 1]]) ** 2, axis=1))
    distinct = rms > 0.01
    pairs = pairs[distinct]
    ok = truth["in_curve"][pairs[:, 0]] & truth["in_curve"][pairs[:, 1]]
    dd = truth["density"][pairs[ok, 0]] - truth["density"][pairs[ok, 1]]
    dl = truth["log_q"][pairs[ok, 0]] - truth["log_q"][pairs[ok, 1]]
    cross = dataset[pairs[ok, 0]] != dataset[pairs[ok, 1]]
    worst = np.argsort(-np.abs(dd[:, 0]))[:10]
    out = {"scene": "D65", "pair_rule": "Delta E*ab <= 0.5 at the same exposure, spectral RMS difference > 0.01",
           "pairs": int(ok.sum()), "cross_dataset_pairs": int(cross.sum()),
           "pairs_by_dataset": {f"{a}|{b}": int(n) for (a, b), n in zip(*np.unique(
               np.sort(np.stack([dataset[pairs[ok, 0]], dataset[pairs[ok, 1]]], 1), axis=1), axis=0, return_counts=True))},
           "d_log10_q": stats(dl), "d_status_m": stats(dd), "d_status_m_cross_dataset": stats(dd[cross]),
           "largest_red_density_differences": [
               {"a": names[pairs[ok][i, 0]], "b": names[pairs[ok][i, 1]], "d_status_m": dd[i].round(4).tolist(),
                "lab_a": lab[pairs[ok][i, 0]].round(2).tolist()} for i in worst]}
    # Linear-program bounds: for selected targets, min and max of each Q over 0 <= rho <= 1 with
    # XYZ(rho * D65) fixed. Targets: the median spectrum of chosen categories.
    a = c.w_xyz * d65[None, :]
    wq = c.film.w_negative * d65[None, :]
    targets = {}
    rng = np.random.default_rng(RNG_SEED)
    for sname, rule in (("issa_skin", None), ("gutierrez_natural", "Plants: Leaves (L)"), ("usgs_splib07", "Vegetation"),
                        ("gutierrez_natural", "Plants: Flowers (Fl)"), ("rawtoaces_190", None)):
        s = sets[sname]
        idx = np.arange(len(s.reflectance)) if rule is None else np.array([k for k, cat in enumerate(s.categories) if cat == rule])
        pick = rng.choice(idx, size=min(3, len(idx)), replace=False)
        for k in pick:
            targets[f"{sname}:{s.labels[k]}"] = s.reflectance[k]
    grey = np.full_like(c.wavelengths, 0.18)
    targets["flat_grey_0.18"] = grey
    bounds = {}
    erg = c.lux_seconds_per_y / p0.LUMINOUS_EFFICACY_LM_PER_W * p0.ERG_PER_CM2_PER_J_PER_M2
    for tname, rho in targets.items():
        x = a @ rho
        q_true = erg * (wq @ rho)
        e = {"lab": sr.xyz_to_lab(x, white).round(2).tolist(), "log10_q_true": np.log10(q_true).round(4).tolist(),
             "log10_q_min": [], "log10_q_max": []}
        for k in range(3):
            lo = linprog(wq[k], A_eq=a, b_eq=x, bounds=(0, 1), method="highs")
            hi = linprog(-wq[k], A_eq=a, b_eq=x, bounds=(0, 1), method="highs")
            if not (lo.success and hi.success):
                raise RuntimeError(f"metamer bound LP failed for {tname}: {lo.message} / {hi.message}")
            e["log10_q_min"].append(round(float(np.log10(max(erg * lo.fun, 1e-300))), 4))
            e["log10_q_max"].append(round(float(np.log10(erg * -hi.fun)), 4))
        qmin, qmax = 10.0 ** np.array(e["log10_q_min"]), 10.0 ** np.array(e["log10_q_max"])
        e["status_m_true"] = c.negative_status_m(q_true[None])[0].round(4).tolist()
        e["status_m_min"] = c.negative_status_m(np.maximum(qmin, 1e-12)[None])[0].round(4).tolist()
        e["status_m_max"] = c.negative_status_m(qmax[None])[0].round(4).tolist()
        bounds[tname] = e
    out["linear_program_bounds"] = {"rule": "0 <= rho <= 1 at the 1 nm nodes, XYZ under D65 fixed", "targets": bounds}
    write_json("metamers.json", out)


# --- section G: camera stage ------------------------------------------------------------------


class CameraPriorLinear:
    name = "camera_prior_linear"

    def __init__(self, c, moment, camera_w, ap1_from_camera):
        a = (camera_w * c.e_ref[None, :]) @ c.knot_to_grid
        self.matrix = (c.knot_to_grid @ (moment @ a.T @ np.linalg.inv(a @ moment @ a.T))) * c.e_ref[:, None]
        self.camera_from_ap1 = np.linalg.inv(ap1_from_camera)

    def reconstruct(self, ap1):
        cam = np.atleast_2d(ap1) @ self.camera_from_ap1.T
        radiance = cam @ self.matrix.T
        return sr.Reconstruction(radiance, np.all(radiance >= 0, axis=1), {})


class CameraPriorNonnegative(sr.MeasuredPriorNonnegative):
    name = "camera_prior_nonnegative"

    def __init__(self, c, moment, camera_w, ap1_from_camera):
        super().__init__(c, moment)
        self.a = (camera_w * c.e_ref[None, :]) @ c.knot_to_grid
        self.camera_from_ap1 = np.linalg.inv(ap1_from_camera)

    def reconstruct(self, ap1, residual_tolerance: float = 1e-6):
        cam = np.atleast_2d(ap1) @ self.camera_from_ap1.T
        feasible = np.all(cam >= 0, axis=1) & (cam.sum(axis=1) > 0)  # necessary condition; the solve checks the rest
        rho = np.zeros((len(cam), len(self.c.knots)))
        residual = np.full(len(cam), np.inf)
        if feasible.any():
            rho[feasible], residual[feasible] = self.solve_knots(cam[feasible])
        radiance = (rho @ self.c.knot_to_grid.T) * self.c.e_ref[None, :]
        return sr.Reconstruction(radiance, feasible & (residual <= residual_tolerance), {"relative_camera_residual": residual})

    def solve_knots(self, cam):
        # Same solve as the XYZ prior; the camera green channel takes the place of Y in the scaling.
        return super().solve_knots(cam)


def fit_idt(c, camera_w, light, training) -> np.ndarray:
    """Camera RGB -> XYZ matrix for one scene light, fitted on the training reflectances in CIELAB
    with the white preserved (the rawtoaces method; target is the XYZ of the scene radiance,
    without chromatic adaptation). Returns XYZ_from_camera."""
    from scipy.optimize import least_squares

    radiance = training * light[None, :]
    cam = radiance @ camera_w.T
    xyz = c.xyz(radiance)
    cam_white = camera_w @ light
    xyz_white = c.xyz(light)
    lab_t = sr.xyz_to_lab(xyz, xyz_white)
    # Parameterize by 6 free entries; the third column is fixed by the white constraint.
    m0 = np.linalg.lstsq(cam, xyz, rcond=None)[0].T

    def matrix(p):
        m = np.zeros((3, 3))
        m[:, :2] = p.reshape(3, 2)
        m[:, 2] = (xyz_white - m[:, :2] @ cam_white[:2]) / cam_white[2]
        return m

    res = least_squares(lambda p: (sr.xyz_to_lab(cam @ matrix(p).T, xyz_white) - lab_t).ravel(), m0[:, :2].ravel())
    return matrix(res.x)


def fit_camera_to_q(c, camera_w, light, training) -> np.ndarray:
    radiance = training * light[None, :]
    cam = radiance @ camera_w.T
    q = c.layer_exposure(radiance)
    return np.stack([np.linalg.lstsq(cam / q[:, [k]], np.ones(len(q)), rcond=None)[0] for k in range(3)])


def section_g(c, ev, my, jh, sets, lights) -> None:
    rng = np.random.default_rng(RNG_SEED)
    issa = sets["issa_skin"].reflectance
    test_sets = {"gutierrez_natural": sets["gutierrez_natural"].reflectance, "usgs_splib07": sets["usgs_splib07"].reflectance,
                 "issa_skin_subset_2000": issa[rng.choice(len(issa), 2000, replace=False)]}
    training = sets["rawtoaces_190"].reflectance
    cameras = sd.available_cameras()
    out = {"cameras": cameras, "idt_training": "rawtoaces_190 under the scene light", "scenes": ["D55", "A"],
           "test_sets": {k: int(len(v)) for k, v in test_sets.items()}, "results": {}}
    for light_name in ("D55", "A"):
        light = lights[light_name]
        white = c.xyz(light)
        for tname, refl in test_sets.items():
            held = {"issa_skin_subset_2000": "issa_skin"}.get(tname, tname)
            training_g = {k: v.reflectance for k, v in sets.items() if k != held}
            moment, _ = sr.prior_second_moment(c, training_g)
            ml, mp = sr.MeasuredPriorLinear(c, moment), sr.MeasuredPriorNonnegative(c, moment)
            mloc = sr.MeasuredPriorLocal(c, moment, training_g)
            radiance = refl * light[None, :]
            xyz = c.xyz(radiance)
            truth = ev.film_response(radiance)
            key = f"{light_name}|{tname}"
            per_camera = {}
            agg = {}
            for cam_name in cameras:
                t0 = time.time()
                cw = sd.read_camera_sensitivity(cam_name)
                xyz_from_cam = fit_idt(c, cw, light, training)
                ap1_from_cam = c.xyz_to_ap1 @ xyz_from_cam
                cam = radiance @ cw.T
                ap1 = cam @ ap1_from_cam.T
                xyz_cam = ap1 @ c.ap1_to_xyz.T
                de_idt = np.linalg.norm(sr.xyz_to_lab(xyz_cam, white) - sr.xyz_to_lab(xyz, white), axis=1)
                entry = {"idt_delta_e_ab": stats(de_idt[:, None])}
                methods = [jh, ml, mp, mloc, CameraPriorLinear(c, moment, cw, ap1_from_cam), CameraPriorNonnegative(c, moment, cw, ap1_from_cam)]
                for m in methods:
                    cmp = ev.compare(truth, xyz, white, m.reconstruct(ap1))
                    sm = ev.summary(cmp)
                    entry[m.name] = {"d_status_m": sm["d_status_m"], "outside_domain": sm["outside_domain"]}
                    agg.setdefault(m.name, []).append(cmp["d_density"][cmp["dense"]])
                m_q = fit_camera_to_q(c, cw, light, training)
                q_direct = cam @ m_q.T
                okd = np.all(q_direct > 0, axis=1) & truth["in_curve"]
                dens = np.full_like(q_direct, np.nan)
                lh = c.film.negative_criterion_log_h + np.log10(np.where(okd[:, None], q_direct, 1.0))
                okd &= np.all(lh <= ev.curve_end_log_h, axis=1)
                dens[okd] = c.negative_status_m(q_direct[okd])
                dd = (dens - truth["density"])[okd]
                entry["camera_to_q_matrix_trained_on_rawtoaces"] = {"d_status_m": stats(dd)}
                agg.setdefault("camera_to_q_matrix_trained_on_rawtoaces", []).append(dd)
                per_camera[cam_name] = entry
                print(f"G {key} {cam_name}: {time.time() - t0:.1f} s")
            # Exact XYZ input (no camera), same test set, for comparison.
            exact = {}
            ap1_exact = xyz @ c.xyz_to_ap1.T
            for m in (jh, ml, mp, mloc):
                cmp = ev.compare(truth, xyz, white, m.reconstruct(ap1_exact))
                exact[m.name] = ev.summary(cmp)["d_status_m"]
            out["results"][key] = {"per_camera": per_camera,
                                   "all_cameras_pooled": {k: stats(np.vstack(v)) for k, v in agg.items()},
                                   "exact_xyz_input": exact}
    write_json("camera_stage.json", out)


def section_h(c_variant, ev_variant, sets, lights) -> None:
    my = sr.MallettYukselBasis(c_variant)
    jh = sr.SigmoidPolynomial(c_variant)
    out = {"film_options": "sensitivity_outside = 'log_linear' (spectral_film_lut), other P0 defaults", "scene": "D55", "datasets": {}}
    for name, s in sets.items():
        methods, _ = make_methods(c_variant, my, jh, sets, name)
        radiance = s.reflectance * lights["D55"][None, :]
        xyz = c_variant.xyz(radiance)
        ap1 = xyz @ c_variant.xyz_to_ap1.T
        truth = ev_variant.film_response(radiance)
        e = {}
        for m in methods:
            e[m.name] = ev_variant.summary(ev_variant.compare(truth, xyz, c_variant.xyz(lights["D55"]), m.reconstruct(ap1)))["d_status_m"]
        ok = truth["positive"]
        fq = linear_floor(ap1[ok], truth["q"][ok])
        fin = np.all(fq > 0, axis=1)
        e["in_sample_linear_floor_d_log10_q"] = stats((np.log10(fq[fin]) - truth["log_q"][ok][fin]))
        out["datasets"][name] = e
        print(f"H {name}")
    write_json("film_sensitivity_variant.json", out)


def section_i(c, ev, my, jh, sets, lights) -> None:
    """Viewed-print Delta E*ab (P0 chain, uncalibrated) between truth and reconstruction."""
    rng = np.random.default_rng(RNG_SEED)
    film = c.film
    white_view = film.white_xyz()
    out = {"chain": "P0 reference chain: Status M -> inferred dyes -> lamp A printer balanced on a D55 grey -> Endura -> D50 viewing",
           "scene": "D55", "subset_per_dataset": 300, "datasets": {}}

    for name, s in sets.items():
        methods, _ = make_methods(c, my, jh, sets, name)
        pick = rng.choice(len(s.reflectance), size=min(300, len(s.reflectance)), replace=False)
        radiance = s.reflectance[pick] * lights["D55"][None, :]
        xyz = c.xyz(radiance)
        ap1 = xyz @ c.xyz_to_ap1.T
        truth = ev.film_response(radiance)
        paper_end = np.array([cv.log_h[-1] for cv in film.paper_curves.values()])

        def lab_of(density, mask):
            """Print Lab per sample. A sample is not printable when the P0 negative dye basis cannot
            reach its Status M density with non-negative dye amounts (the solve raises), when its
            paper exposure is above the end of the Endura curve, or when the Endura dyes cannot
            reach its Status A density. Each case is counted."""
            lab = np.full((len(density), 3), np.nan)
            counts = {"dye_basis_cannot_reach_density": 0, "paper_exposure_above_curve_end": 0,
                      "paper_dye_basis_cannot_reach_density": 0}
            for i in np.flatnonzero(mask):
                try:
                    dyes = film.negative_dye_amounts(density[i])
                except RuntimeError:
                    counts["dye_basis_cannot_reach_density"] += 1
                    continue
                neg = film.negative_spectral_density(np.atleast_2d(dyes))
                if np.any(film.paper_log_exposure(neg) > paper_end):
                    counts["paper_exposure_above_curve_end"] += 1
                    continue
                sa = film.paper_status_a(neg)
                try:
                    paper_dyes = film.print_dye_amounts(sa)
                except RuntimeError:
                    counts["paper_dye_basis_cannot_reach_density"] += 1
                    continue
                pd = film.print_spectral_density(np.atleast_2d(paper_dyes))
                lab[i] = sr.xyz_to_lab(film.viewed_xyz(pd), white_view)[0]
            return lab, counts

        t0 = time.time()
        lab_true, counts_true = lab_of(truth["density"], truth["in_curve"])
        e = {"truth_printable": int(np.isfinite(lab_true[:, 0]).sum()), "truth_not_printable": counts_true}
        for m in methods:
            cmp = ev.compare(truth, xyz, c.xyz(lights["D55"]), m.reconstruct(ap1))
            lab_m, counts_m = lab_of(cmp["density"], cmp["dense"])
            de = np.linalg.norm(lab_m - lab_true, axis=1)
            fin = np.isfinite(de)
            e[m.name] = {"delta_e_ab": stats(de[fin][:, None]), "not_printable": counts_m}
        out["datasets"][name] = e
        print(f"I {name}: {time.time() - t0:.1f} s")
    write_json("print_effect.json", out)


def with_reference_light(c: sr.Colorimetry, light: np.ndarray) -> sr.Colorimetry:
    """A copy of the colorimetry with another reference light (normalized to Y = 1)."""
    import copy

    out = copy.copy(c)
    out.e_ref = light / c.xyz(light)[1]
    out.white_ref = c.xyz(out.e_ref)
    out.a_ref_knots = (c.w_xyz * out.e_ref[None, :]) @ c.knot_to_grid
    return out


def section_j(c, ev, sets, lights) -> None:
    out = {"rule": "reference light of every reconstruction = the scene light (known)", "datasets": {}}
    for light in [l for l in SCENE_LIGHTS if l not in DAYLIGHT_SCENES]:
        cl = with_reference_light(c, lights[light])
        my_feasible = sr.MallettYukselBasis.feasible(cl)
        out.setdefault("mallett_yuksel_basis_defined", {})[light] = my_feasible
        my, jh = (sr.MallettYukselBasis(cl) if my_feasible else None), sr.SigmoidPolynomial(cl)
        for name, s in sets.items():
            methods, _ = make_methods(cl, my, jh, sets, name)
            methods = [m for m in methods if m is not None]  # MY is not defined for this light (LP infeasible)
            radiance = s.reflectance * lights[light][None, :]
            xyz = c.xyz(radiance)
            ap1 = xyz @ c.xyz_to_ap1.T
            truth = ev.film_response(radiance)
            e = {}
            for m in methods:
                cmp = ev.compare(truth, xyz, c.xyz(lights[light]), m.reconstruct(ap1))
                sm = ev.summary(cmp)
                d = cmp["d_density"][cmp["dense"]]
                e[m.name] = {"d_status_m": sm["d_status_m"], "signed_median_d_status_m": np.round(np.median(d, axis=0), 5).tolist(),
                             "outside_domain": sm["outside_domain"]}
            out["datasets"].setdefault(name, {})[light] = e
            print(f"J {light} {name}")
    write_json("scene_light_matched.json", out)


def split_halves(s: sd.ReflectanceSet, rng) -> np.ndarray:
    """True for the training half. ISSA: by subject (origin and subject number); others: random."""
    if s.name == "issa_skin":
        subjects = np.array([l.split("_", 1)[1] for l in s.labels])
        unique = np.unique(subjects)
        train_subjects = set(rng.choice(unique, size=len(unique) // 2, replace=False))
        return np.array([u in train_subjects for u in subjects])
    mask = np.zeros(len(s.reflectance), dtype=bool)
    mask[rng.choice(len(mask), size=len(mask) // 2, replace=False)] = True
    return mask


def section_k(c, ev, my, jh, sets, lights) -> None:
    rng = np.random.default_rng(RNG_SEED)
    halves = {k: split_halves(s, rng) for k, s in sets.items()}
    moment, info = sr.prior_second_moment(c, {k: s.reflectance[halves[k]] for k, s in sets.items()})
    training = {k: s.reflectance[halves[k]] for k, s in sets.items()}
    methods = [sr.MeasuredPriorLinear(c, moment), sr.MeasuredPriorNonnegative(c, moment)]
    methods += [sr.MeasuredPriorLocal(c, moment, training, sigma_uv=sigma) for sigma in LOCAL_SIGMA_STUDY]
    for m, sigma in zip(methods[2:], LOCAL_SIGMA_STUDY):
        m.name = f"measured_prior_local_sigma{sigma:g}"
    out = {"scene": "D55", "prior": info, "datasets": {}}
    for name, s in sets.items():
        refl = s.reflectance[~halves[name]]
        radiance = refl * lights["D55"][None, :]
        xyz = c.xyz(radiance)
        ap1 = xyz @ c.xyz_to_ap1.T
        truth = ev.film_response(radiance)
        e = {"test_count": int(len(refl))}
        for m in methods:
            cmp = ev.compare(truth, xyz, c.xyz(lights["D55"]), m.reconstruct(ap1))
            d = cmp["d_density"][cmp["dense"]]
            e[m.name] = {"d_status_m": stats(d), "signed_median_d_status_m": np.round(np.median(d, axis=0), 5).tolist()}
        out["datasets"][name] = e
        print(f"K {name}")
    write_json("in_distribution_prior.json", out)


def main() -> int:
    sections = set(sys.argv[1:]) or set("ABCDEFGHIJK")
    t_start = time.time()
    c = sr.Colorimetry()
    ev = Evaluator(c)
    sets = sd.load_all_reflectance_sets()
    lights = scene_lights(c)
    my = sr.MallettYukselBasis(c)
    jh = sr.SigmoidPolynomial(c)
    timings = {}
    for key, fn in (("A", lambda: section_a(c, my)), ("B", lambda: section_b(c, ev, my, jh, sets, lights)),
                    ("C", lambda: section_c(c, my, jh, sets, lights)), ("D", lambda: section_d(c, my, jh, sets, lights)),
                    ("E", lambda: section_e(c, ev, my, jh, sets, lights)), ("F", lambda: section_f(c, ev, my, jh, sets, lights)),
                    ("G", lambda: section_g(c, ev, my, jh, sets, lights))):
        if key in sections:
            t0 = time.time()
            fn()
            timings[key] = round(time.time() - t0, 1)
    if "H" in sections:
        t0 = time.time()
        cv = sr.Colorimetry(p0.ModelOptions(sensitivity_outside="log_linear"))
        section_h(cv, Evaluator(cv), sets, scene_lights(cv))
        timings["H"] = round(time.time() - t0, 1)
    if "I" in sections:
        t0 = time.time()
        section_i(c, ev, my, jh, sets, lights)
        timings["I"] = round(time.time() - t0, 1)
    if "J" in sections:
        t0 = time.time()
        section_j(c, ev, sets, lights)
        timings["J"] = round(time.time() - t0, 1)
    if "K" in sections:
        t0 = time.time()
        section_k(c, ev, my, jh, sets, lights)
        timings["K"] = round(time.time() - t0, 1)
    print("timings (s):", timings, "total", round(time.time() - t_start, 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
