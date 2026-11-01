"""Plots of step P1 (local only; *.png is not committed).

Input: results/p1_spectral_input/*.json, build/tmp/p1/eval/*.npz (written by run_p1_checks.py),
the P0 profiles and CIE tables, the reflectance datasets.
Output: results/p1_spectral_input/plots/*.png:
- sensitivity_vs_observer.png: Portra 400 layer sensitivities (relative energy, peak 1) and the
  CIE 1931 functions, both multiplied by E_ref.
- heldout_density_error.png: distribution of the signed Status M error per method and dataset,
  D55 scene, and the in-sample linear floor.
- skin_spectrum.png: mean ISSA reflectance and the mean of each reconstruction (held-out prior),
  E_ref scene, with the Portra blue-layer weight.
- metamer_bounds.png: linear-program range of the Status M density for one XYZ, with the truth.
Also writes results/p1_spectral_input/skin_band_error.json: the mean reflectance difference
(reconstruction minus truth) and the share of the blue- and red-layer exposure error per
wavelength band, for the data of skin_spectrum.png.
Step: P1, ROADMAP section 8.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import run_p1_checks as checks  # noqa: E402
import spectral_datasets as sd  # noqa: E402
import spectral_reconstruction as sr  # noqa: E402

PLOT_DIR = checks.RESULT_DIR / "plots"
SHORT = {"mallett_yuksel_rec709": "MY", "jakob_hanika_sigmoid": "JH", "measured_prior_linear": "prior lin",
         "measured_prior_nonnegative": "prior >=0", "measured_prior_local": "prior local", "linear_floor": "floor (in-sample)"}


def sensitivity_vs_observer(c: sr.Colorimetry) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    wl = c.wavelengths
    for k, (name, color) in enumerate(zip(("cyan-forming (red)", "magenta-forming (green)", "yellow-forming (blue)"), ("C3", "C2", "C0"))):
        w = c.film.w_negative[k] * c.e_ref
        ax.plot(wl, w / w.max(), color=color, label=f"Portra {name}")
    for k, name in enumerate(("x-bar", "y-bar", "z-bar")):
        w = c.w_xyz[k] * c.e_ref
        ax.plot(wl, w / w.max(), color=("C3", "C2", "C0")[k], ls="--", lw=1, label=f"CIE {name}")
    ax.set_xlim(360, 760)
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("weight x E_ref (peak 1)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "sensitivity_vs_observer.png", dpi=150)


def heldout_density_error() -> None:
    datasets = ("rawtoaces_190", "gutierrez_natural", "issa_skin", "usgs_splib07")
    methods = list(checks.METHOD_NAMES) + ["linear_floor"]
    fig, axes = plt.subplots(3, 4, figsize=(14, 8), sharey="row")
    for j, ds in enumerate(datasets):
        z = np.load(checks.EVAL_DIR / f"heldout_{ds}_D55.npz")
        for i, ch in enumerate(checks.CHANNELS):
            data = []
            for m in methods:
                d = z[f"d_density_{m}"][:, i]
                data.append(d[np.isfinite(d)])
            axes[i, j].boxplot(data, whis=(5, 95), showfliers=False)
            axes[i, j].axhline(0, color="k", lw=0.5)
            axes[i, j].axhspan(-checks.DENSITY_P95_TOLERANCE, checks.DENSITY_P95_TOLERANCE, color="0.9")
            axes[i, j].set_xticks(range(1, len(methods) + 1), [SHORT[m] for m in methods], rotation=60, fontsize=7)
            if j == 0:
                axes[i, j].set_ylabel(f"Status M {ch} error")
            if i == 0:
                axes[i, j].set_title(ds, fontsize=9)
    fig.suptitle("Held-out reflectances, D55 scene: signed negative density error (box 25-75 %, whiskers 5-95 %)", fontsize=9)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "heldout_density_error.png", dpi=150)


def skin_spectrum(c: sr.Colorimetry, sets: dict) -> None:
    rng = np.random.default_rng(checks.RNG_SEED)
    skin = sets["issa_skin"].reflectance
    pick = skin[rng.choice(len(skin), 2000, replace=False)]
    radiance = pick * c.e_ref[None, :]
    ap1 = c.xyz(radiance) @ c.xyz_to_ap1.T
    my, jh = sr.MallettYukselBasis(c), sr.SigmoidPolynomial(c)
    methods, _ = checks.make_methods(c, my, jh, sets, "issa_skin")
    fig, ax = plt.subplots(figsize=(8, 4))
    wl = c.wavelengths
    ax.plot(wl, pick.mean(0), color="k", lw=2, label="ISSA mean (2000 records)")
    bands = ((380, 400), (400, 430), (430, 470), (470, 520), (520, 560), (560, 600), (600, 640), (640, 680))
    report = {"records": 2000, "scene": "E_ref", "prior": "held out (no skin)", "methods": {}}
    for m in methods:
        rec = m.reconstruct(ap1)
        rho = rec.radiance / c.e_ref[None, :]
        ax.plot(wl, rho.mean(0), lw=1, label=SHORT[m.name] + " (held-out prior)")
        diff = (rho - pick).mean(0)
        entry = {"mean_reflectance_difference": {}, "share_of_blue_layer_exposure": {}, "share_of_red_layer_exposure": {}}
        for k, name in ((2, "share_of_blue_layer_exposure"), (0, "share_of_red_layer_exposure")):
            contrib = ((rec.radiance - radiance).mean(0) * c.film.w_negative[k])
            total = (radiance.mean(0) * c.film.w_negative[k]).sum()
            for lo, hi in bands:
                inside = (wl >= lo) & (wl < hi)
                entry[name][f"{lo}-{hi}"] = round(float(contrib[inside].sum() / total), 5)
        for lo, hi in bands:
            inside = (wl >= lo) & (wl < hi)
            entry["mean_reflectance_difference"][f"{lo}-{hi}"] = round(float(diff[inside].mean()), 5)
        report["methods"][m.name] = entry
    report["true_mean_reflectance"] = {f"{lo}-{hi}": round(float(pick.mean(0)[(wl >= lo) & (wl < hi)].mean()), 5) for lo, hi in bands}
    checks.write_json("skin_band_error.json", report)
    blue = c.film.w_negative[2] * c.e_ref
    ax.fill_between(wl, 0, 0.1 * blue / blue.max(), color="C0", alpha=0.2, label="Portra blue-layer weight (scaled)")
    ax.set_xlim(370, 720)
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("reflectance")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "skin_spectrum.png", dpi=150)


def metamer_bounds() -> None:
    data = json.loads((checks.RESULT_DIR / "metamers.json").read_text(encoding="utf-8"))["linear_program_bounds"]["targets"]
    names = list(data)
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), sharey=True)
    for i, ch in enumerate(checks.CHANNELS):
        for k, n in enumerate(names):
            e = data[n]
            axes[i].plot([e["status_m_min"][i], e["status_m_max"][i]], [k, k], color="0.5", lw=4)
            axes[i].plot(e["status_m_true"][i], k, "k|", ms=12)
        axes[i].set_title(f"Status M {ch}: range over 0 <= rho <= 1 with the same XYZ (D65)", fontsize=8)
        axes[i].set_xlabel("negative density")
    axes[0].set_yticks(range(len(names)), [n.split(":")[-1][:28] for n in names], fontsize=7)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "metamer_bounds.png", dpi=150)


def main() -> int:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    c = sr.Colorimetry()
    sets = sd.load_all_reflectance_sets()
    sensitivity_vs_observer(c)
    heldout_density_error()
    skin_spectrum(c, sets)
    metamer_bounds()
    print(f"plots in {PLOT_DIR.relative_to(checks.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
