"""Plots of step P0: curve overlays on the source charts, and plots of the measured results.

Input: build/tmp/p0/sources/*.pdf, profiles/*.json, results/p0_data_and_reference/*.json.
Output: results/p0_data_and_reference/plots/*.png (local only; *.png is in .gitignore). The
overlay plots contain renders of the manufacturer charts and must not be published.

Step: P0 (data and reference). The overlay draws the digitized grid values (red) over a 300 dpi
render of the chart, with the frame map of digitize_kodak_charts.py; a correct digitization
covers the black source curve.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pymupdf  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_spectral_reference as ref  # noqa: E402

RESULT_DIR = ref.REPO_ROOT / "results" / "p0_data_and_reference"
PLOT_DIR = RESULT_DIR / "plots"
DPI = 300
CHART_PROFILE = {
    "portra400_characteristic": ("kodak_portra_400", "characteristic"),
    "portra400_spectral_sensitivity": ("kodak_portra_400", "spectral_sensitivity"),
    "portra400_spectral_dye_density": ("kodak_portra_400", "spectral_dye_density"),
    "endura_premier_characteristic": ("kodak_endura_premier", "characteristic"),
    "endura_premier_spectral_sensitivity": ("kodak_endura_premier", "spectral_sensitivity"),
    "endura_premier_spectral_dye_density": ("kodak_endura_premier", "spectral_dye_density"),
}


def load(name: str) -> dict:
    return json.loads((RESULT_DIR / name).read_text(encoding="utf-8"))


def plot_overlays() -> None:
    digitization = load("digitization.json")["charts"]
    for chart_id, info in digitization.items():
        profile_name, chart_key = CHART_PROFILE[chart_id]
        curves = ref.load_profile(profile_name)["charts"][chart_key]["curves"]
        x0, y0, x1, y1 = info["frame_pt"]
        margin = 6.0
        clip = pymupdf.Rect(x0 - margin, y0 - margin, x1 + margin, y1 + margin)
        page = pymupdf.open(ref.SOURCE_DIR / info["pdf"])[info["page"] - 1]
        pix = page.get_pixmap(dpi=DPI, clip=clip)
        image = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        scale = DPI / 72.0
        (xa, xb), (ya, yb) = info["x_range"], info["y_range"]
        fig, ax = plt.subplots(figsize=(pix.width / 150, pix.height / 150), dpi=150)
        ax.imshow(image[..., :3])
        for label, curve in curves.items():
            x, y = np.array(curve["x"]), np.array(curve["y"])
            px = (x0 + (x - xa) / (xb - xa) * (x1 - x0) - clip.x0) * scale
            py = (y1 - (y - ya) / (yb - ya) * (y1 - y0) - clip.y0) * scale
            ax.plot(px, py, color="red", linewidth=0.7, linestyle=(0, (3, 2)), label=label)
        ax.set_axis_off()
        ax.set_title(f"{chart_id}: digitized grid (red) over the source chart", fontsize=7)
        fig.savefig(PLOT_DIR / f"overlay_{chart_id}.png", bbox_inches="tight")
        plt.close(fig)


def plot_spectral_inputs(model: ref.ReferenceModel) -> None:
    wl = model.grid.wavelengths
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    colors = ("tab:red", "tab:green", "tab:blue")
    names = ("cyan-forming (R)", "magenta-forming (G)", "yellow-forming (B)")
    ax = axes[0, 0]
    for k in range(3):
        neg = model.w_negative[k] / model.w_negative[k].max()
        pap = model.w_printing[k] / model.w_printing[k].max()
        ax.plot(wl, neg, color=colors[k], label=f"Portra 400 {names[k]}")
        ax.plot(wl, pap, color=colors[k], linestyle="--", label=f"Endura x lamp A {names[k]}")
    ax.axvspan(700, 760, color="0.85", zorder=0, label="no published negative density")
    ax.set_xlim(360, 780)
    ax.set_title("Layer sensitivities (linear, peak = 1)")
    ax.legend(fontsize=6)

    ax = axes[0, 1]
    for k, c in enumerate(("R", "G", "B")):
        ax.plot(wl, model.w_status_m[k] / model.w_status_m[k].max(), color=colors[k], label=f"Status M {c}")
        ax.plot(wl, model.w_status_a[k] / model.w_status_a[k].max(), color=colors[k], linestyle=":", label=f"Status A {c}")
    ax.set_xlim(360, 780)
    ax.set_title("Densitometer spectral products (colormath copy of ANSI/ISO)")
    ax.legend(fontsize=6)

    ax = axes[1, 0]
    ax.plot(wl, model.negative_dmin, color="0.4", label="D-min (published, held outside 400-700)")
    ax.plot(wl, model.negative_midscale, color="k", label="midscale neutral (published)")
    amounts = model.negative_dye_fit["midscale_amounts"]
    total = model.negative_dmin.copy()
    for k, dye in enumerate(ref.NEGATIVE_DYES):
        part = amounts[dye] * model.negative_dyes[k]
        total = total + part
        ax.plot(wl, part, color=colors[k], linestyle="--", label=f"inferred {dye} x {amounts[dye]:.2f}")
    ax.plot(wl, total, color="tab:orange", linestyle=":", label="D-min + inferred dyes")
    ax.axvspan(700, 780, color="0.85", zorder=0)
    ax.set_xlim(380, 780)
    ax.set_title("Portra 400 spectral density: published and inferred")
    ax.legend(fontsize=6)

    ax = axes[1, 1]
    for k, dye in enumerate(("cyan", "magenta", "yellow")):
        ax.plot(wl, model.paper_dyes[k], color=colors[k], label=f"Endura {dye} (published, peak 1)")
    ax.axvspan(360, 400, color="0.85", zorder=0)
    ax.axvspan(700, 780, color="0.85", zorder=0, label="held outside 400-700")
    ax.set_xlim(360, 780)
    ax.set_title("Endura Premier dye spectral density")
    ax.legend(fontsize=6)
    for a in axes.flat:
        a.set_xlabel("wavelength (nm)")
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "spectral_inputs.png", dpi=150)
    plt.close(fig)


def plot_ramp() -> None:
    ramp = load("neutral_ramp.json")
    log_h = np.array(ramp["log_h"])
    lab = np.array(ramp["print_lab_d50"])
    paper_only = np.array(ramp["paper_only_diagnostic"]["print_lab_d50"])
    status_m = np.array(ramp["negative_status_m_rgb"])
    status_a = np.array(ramp["print_status_a_rgb"])
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for k, c in enumerate(("tab:red", "tab:green", "tab:blue")):
        axes[0].plot(log_h, status_m[:, k], color=c)
        axes[0].plot(log_h, status_a[:, k], color=c, linestyle="--")
    axes[0].set_title("Negative Status M (solid), print Status A (dashed)")
    axes[1].plot(log_h, lab[:, 0], color="k", label="L* chain")
    axes[1].set_title("Print L* under D50")
    axes[2].plot(log_h, lab[:, 1], color="tab:pink", label="a* chain")
    axes[2].plot(log_h, lab[:, 2], color="tab:olive", label="b* chain")
    axes[2].plot(log_h, paper_only[:, 1], color="tab:pink", linestyle=":", label="a* paper only")
    axes[2].plot(log_h, paper_only[:, 2], color="tab:olive", linestyle=":", label="b* paper only")
    axes[2].set_title("Print a*, b* under D50")
    axes[2].legend(fontsize=7)
    for a in axes:
        a.set_xlabel("scene log10 H (lux-seconds, D55)")
        a.axvline(-1.44, color="0.6", linewidth=0.8)
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "neutral_ramp.png", dpi=150)
    plt.close(fig)


def plot_convergence() -> None:
    data = load("integration_convergence.json")
    keys = list(data["tests"].keys())
    fig, axes = plt.subplots(2, 4, figsize=(15, 6.5))
    for ax, key in zip(axes.flat, keys):
        for rule, style in (("point", "-o"), ("projected", "-s")):
            table = data["by_rule"][rule]["errors_by_step_nm"]
            steps = [float(s) for s in table]
            ax.loglog(steps, [max(table[s][key], 1e-9) for s in table], style, label=rule, markersize=3)
        tol = 0.1 if key.endswith("delta_e") else 1e-3
        ax.axhline(tol, color="0.5", linestyle="--", linewidth=0.8)
        ax.set_title(key, fontsize=8)
        ax.set_xlabel("step (nm)")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "integration_convergence.png", dpi=150)
    plt.close(fig)


def main() -> int:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    plot_overlays()
    plot_spectral_inputs(ref.ReferenceModel(1.0))
    plot_ramp()
    plot_convergence()
    print(f"plots in {PLOT_DIR.relative_to(ref.REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
