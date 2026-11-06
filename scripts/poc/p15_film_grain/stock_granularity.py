"""Granularity of each film stock of the catalog, per densitometer channel and per dye layer (step P15).

Input: results/p15_film_grain/granularity_curves.json (digitize_granularity_charts.py), the values of STOCKS below
(sources.json names each document), and the negative and reversal models of the viewer (mvp_pipeline).
Output: results/p15_film_grain/stock_grain.json; a summary figure in build/tmp/p15_grain/stock_grain.png (local).

Quantities. sigma_48 is the RMS diffuse density of one densitometer channel read through the 48 um aperture
(Status M for a negative, Status A for a reversal film), as a function of the gross density of that channel on a
neutral exposure. sigma_amount is the RMS of the dye amount of one layer through the same aperture (the record of the
product: the amount a_k with spectral density D_min + sum a_k e_k).

Tiers and rules:
- 'curve': the digitized chart of the stock (rule 'granularity_chart').
- 'number': one published value, read at density 1.0 above D-min for a negative. Rule 'single_value_green_anchor':
  the 5207 chart, on net density, scaled so that its green channel at net density 1.0 is the value; red and blue keep
  the 5207 ratios. Fuji gives the value for the visual density; the green channel stands for it (inferred).
- 'pgi': Kodak still films with the Print Grain Index only. Rule 'pgi_ratio': PGI = c + 34.3 ln(sigma) at a fixed
  magnification (Kodak E-58: 6 % of granularity is 2 units, US 5629769), so G_s / G_ref = exp((PGI_s - PGI_ref) / 34.3),
  averaged over the magnifications where both values are 25 or more. Rule 'pgi_anchor_external': the absolute level
  is Portra 400 = 0.009 at net density 1.0, the value of the Fotufilm profile portra400.json (CC BY-SA 4.0, THIRD_PARTY_NOTICES.md); no
  primary source gives an RMS value and a PGI for one Kodak still film (report P15, section 4). Then 'single_value_green_anchor'.
- 'family': no published value; the value of a named related stock (inferred, named in the record).
- reversal films: one value at gross visual density 1.0. Rule 'reversal_nutting': sigma = value * sqrt(D_gross), the
  same for the three channels (Nutting: for clouds of a fixed size, the variance is proportional to the density;
  inferred, no reversal chart exists in the sources).

Layer solve (rule 'layer_noise_from_channels'). The three layers develop independently. On the neutral ramp of the
model, sigma_48_j^2 = sum_k J_jk^2 sigma_amount_k^2 with J_jk = dD_j/da_k = sum_l w_jl T_l e_kl / sum_l w_jl T_l
(T the transmittance of the neutral, w the Status weights). Non-negative least squares at each exposure. The
datasheet sigma is read at the net density of the model channel (D_j - D_j,min), so a D-min difference between the
chart and the profile moves no value.

Nodes: each curve is reduced to at most MAX_NODES nodes (Douglas-Peucker on the log of sigma); the largest relative
error of the linear interpolation on the dense curve is recorded and must be at most NODE_RELATIVE_LIMIT.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p7_spectral_acceleration"))
sys.path.insert(0, str(ROOT / "scripts" / "poc" / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

CURVES = ROOT / "results" / "p15_film_grain" / "granularity_curves.json"
OUTPUT = ROOT / "results" / "p15_film_grain" / "stock_grain.json"
FIGURE = ROOT / "build" / "tmp" / "p15_grain" / "stock_grain.png"
MAX_NODES = 16
NODE_RELATIVE_LIMIT = 0.05  # the log axis of the charts is read to 3.7 % (EXR 5248); 16 nodes are the limit of the product plan
SOLVE_RELATIVE_LIMIT = 0.02
PGI_UNITS_PER_LN = 2.0 / math.log(1.06)
PGI_REFERENCE = "kodak_portra_400"
PGI_REFERENCE_SIGMA = 0.009
SHAPE_STOCK = "kodak_5207"
MAGNIFICATIONS = ("4.4X", "8.8X", "17.8X")

# value: RMS granularity x 1000. pgi: 135 frame, 4.4X, 8.8X, 17.8X (None: not published or below 25).
STOCKS: dict[str, dict] = {
    "kodak_5203": {"tier": "curve", "source": "kodak_5203_ti.pdf"},
    "kodak_5207": {"tier": "curve", "source": "kodak_5207_ti.pdf"},
    "kodak_5213": {"tier": "curve", "source": "kodak_5213_ti.pdf"},
    "kodak_5219": {"tier": "curve", "source": "kodak_5219_ti.pdf"},
    "kodak_5277": {"tier": "curve", "source": "kodak_5277.pdf"},
    "kodak_5293": {"tier": "curve", "source": "kodak_5293.pdf"},
    "kodak_exr_5248": {"tier": "curve", "source": "kodak_5248.pdf"},
    "kodak_5206": {"tier": "curve", "source": "kodak_5206.pdf"},
    "kodak_5248": {"tier": "family", "family_curve": "kodak_exr_5248", "source": "kodak_5248.pdf",
                   "note": "Product code 5248; the only 5248 chart in the sources is the EXR 100T chart (inferred)."},
    "kodak_5247": {"tier": "number", "value": 5.0, "source": "kodak_5247_ecn_ti0835.pdf",
                   "note": "The sheet gives 'less than 5'; the bound 5 is used (inferred)."},
    "kodak_5247_II": {"tier": "family", "value": 5.0, "family": "kodak_5247", "source": "kodak_5247_ecn_ti0835.pdf",
                      "note": "No sheet found; the value of 5247 (inferred)."},
    "kodak_5250": {"tier": "family", "value": 5.0, "family": "kodak_5247", "source": "kodak_5247_ecn_ti0835.pdf",
                   "note": "No sheet found; the value of the Kodak tungsten camera negative 5247 (inferred)."},
    "kodak_aerocolor": {"tier": "number", "value": 8.5, "source": "secondary: analog.cafe review of Aerocolor IV, quoting the Kodak data sheet",
                        "note": "The Kodak sheet (kodak.com) returned 404 on 2026-11-05; the value is from a secondary source."},
    "agfa_vista_100": {"tier": "number", "value": 4.0, "source": "agfa_vista_brochure.pdf",
                       "note": "The brochure states no read density; 1.0 above D-min is used (inferred)."},
    "fuji_c200": {"tier": "number", "value": 4.0, "source": "af3_c200.pdf"},
    "fuji_pro_400h": {"tier": "number", "value": 4.0, "source": "fuji_pro_400h.pdf"},
    "fuji_pro_160c": {"tier": "number", "value": 3.0, "source": "fuji_pro_160c.pdf"},
    "fuji_pro_160s": {"tier": "number", "value": 3.0, "source": "fuji_pro_160s.pdf"},
    "fuji_superia_xtra_400": {"tier": "number", "value": 4.0, "source": "fuji_superia_xtra_400.pdf"},
    "fuji_superia_reala": {"tier": "number", "value": 4.0, "source": "fuji_superia_reala.pdf"},
    "fuji_natura_1600": {"tier": "family", "value": 7.0, "family": "FUJICOLOR SUPERIA 1600", "source": "fuji_superia_1600.pdf",
                         "note": "The Japanese NATURA 1600 sheet has no text layer; the value of SUPERIA 1600 (inferred: the same emulsion family)."},
    "fuji_eterna_500": {"tier": "family", "value": 3.5, "family": "FUJICOLOR F-250", "source": "fuji_f250.pdf",
                        "note": "No ETERNA 500 value found; Fujifilm describes its granularity as similar to EI 250 films. The value of F-250 (inferred)."},
    "fuji_eterna_500_vivid": {"tier": "family", "value": 3.5, "family": "FUJICOLOR F-250", "source": "fuji_f250.pdf",
                              "note": "No ETERNA VIVID 500 value found; the value of F-250, as for ETERNA 500 (inferred)."},
    "kodak_portra_160": {"tier": "pgi", "pgi": (28, 50, 79), "source": "e4051_portra_160.pdf"},
    "kodak_portra_400": {"tier": "pgi", "pgi": (37, 59, 89), "source": "e4050_portra_400_2025.pdf"},
    "kodak_portra_800": {"tier": "pgi", "pgi": (48, 70, 99), "source": "e4040_portra_800.pdf"},
    "kodak_ektar_100": {"tier": "pgi", "pgi": (None, 38, 66), "source": "e4046_ektar_100.pdf"},
    "kodak_gold_200": {"tier": "pgi", "pgi": (44, None, None), "source": "e7022_gold_200.pdf"},
    "kodak_ultramax_400": {"tier": "pgi", "pgi": (46, None, None), "source": "kodak_ultramax_400.pdf"},
    "kodak_vericolor_iii": {"tier": "pgi", "pgi": (39, 61, 91), "source": "kodak_vericolor_iii.pdf"},
    "fuji_velvia_50": {"tier": "reversal", "value": 9.0, "source": "velvia_50.pdf"},
    "fuji_velvia_100": {"tier": "reversal", "value": 8.0, "source": "velvia_100.pdf"},
    "fuji_provia_100f": {"tier": "reversal", "value": 8.0, "source": "provia_100f.pdf"},
    "fuji_astia_100f": {"tier": "reversal", "value": 7.0, "source": "fuji_astia_100f.pdf"},
    "kodak_ektachrome_e100": {"tier": "reversal", "value": 8.0, "source": "e4000_ektachrome_100.pdf"},
}


def pgi_ratio(stock: str) -> tuple[float, list[float]]:
    own, ref = STOCKS[stock]["pgi"], STOCKS[PGI_REFERENCE]["pgi"]
    logs = [(a - b) / PGI_UNITS_PER_LN for a, b in zip(own, ref) if a is not None and b is not None and a >= 25 and b >= 25]
    if not logs:
        raise ValueError(f"{stock}: no magnification with both Print Grain Index values")
    return math.exp(float(np.mean(logs))), [round(math.exp(v), 4) for v in logs]


class ChannelShape:
    """sigma_48 of each channel over net density, from one digitized chart."""

    def __init__(self, layers: dict) -> None:
        self.net, self.sigma = {}, {}
        for layer, data in layers.items():
            d, s = np.asarray(data["density"]), np.asarray(data["sigma_d"])
            order = np.argsort(d)
            d, s = d[order], s[order]
            keep = np.concatenate([[True], np.diff(d) > 1e-6])
            self.net[layer], self.sigma[layer] = d[keep] - d[keep][0], s[keep]

    def at(self, layer: str, net: np.ndarray) -> np.ndarray:
        """Inside the chart: linear interpolation. Outside: the end value (rule 'chart_end_hold', inferred)."""
        return np.interp(net, self.net[layer], self.sigma[layer])


def model_ramp(stock: str) -> dict:
    """The neutral ramp of the model: gross channel density, dye amounts, and the Jacobian dD/da."""
    reversal = STOCKS[stock]["tier"] == "reversal"
    if reversal:
        settings = mp.RenderSettings(method="light_table", reversal=stock)
        settings.validate()
        model = mp.rf.ReversalPreview(mp.light_table_options(settings))
        weights = model.film.w_status_a
        records = np.stack([c.density for c in model.negative_curves], axis=1)
        amounts = np.maximum(model.dye_max[None] - records, 0.0)
    else:
        import build_product_resources as bpr

        settings = mp.RenderSettings(negative=stock)
        settings.validate()
        model = bpr.setup_model(mp.film_options(settings))
        weights = model.film.w_status_m
        amounts = np.stack([c.density for c in model.negative_curves], axis=1)
    f = model.film
    log_h = model.negative_curves[0].log_h
    gross = np.stack([np.interp(log_h, c.log_h, c.density) for c in model.status_curves], axis=1)
    spectral = f.negative_spectral_density(amounts)
    transmittance = 10.0 ** (-spectral)
    jac = np.zeros((len(log_h), 3, 3))
    for j in range(3):
        denom = (transmittance * weights[j]).sum(axis=1)
        for k in range(3):
            jac[:, j, k] = (transmittance * f.negative_dyes[k] * weights[j]).sum(axis=1) / denom
    return {"log_h": log_h, "gross": gross, "amounts": amounts, "jacobian": jac, "reversal": reversal}


def reduce_nodes(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """At most MAX_NODES nodes of a curve y(x) > 0, by Douglas-Peucker on log y with a falling tolerance."""
    order = np.argsort(x)
    x, y = x[order], y[order]
    keep = np.concatenate([[True], np.diff(x) > 1e-9])
    x, y = x[keep], y[keep]
    ly = np.log(y)
    span = (x[-1] - x[0]) or 1.0

    def dp(tol: float) -> list[int]:
        out = {0, len(x) - 1}
        stack = [(0, len(x) - 1)]
        while stack:
            a, b = stack.pop()
            if b - a < 2:
                continue
            t = (x[a + 1:b] - x[a]) / (x[b] - x[a])
            line = ly[a] + t * (ly[b] - ly[a])
            err = np.abs(ly[a + 1:b] - line)
            i = int(np.argmax(err))
            if err[i] > tol:
                m = a + 1 + i
                out.add(m)
                stack += [(a, m), (m, b)]
        return sorted(out)

    lo, hi = 1e-6, 2.0
    best = dp(hi)
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        idx = dp(mid)
        if len(idx) <= MAX_NODES:
            best, hi = idx, mid
        else:
            lo = mid
    xn, yn = x[best], y[best]
    err = float(np.max(np.abs(np.interp(x, xn, yn) / y - 1.0)))
    del span
    return xn, yn, err


def channel_sigma(stock: str, ramp: dict, shapes: dict[str, ChannelShape], record: dict) -> np.ndarray:
    """sigma_48 of each channel along the ramp, (N, 3) in channel order R, G, B."""
    cfg = STOCKS[stock]
    gross = ramp["gross"]
    net = gross - gross.min(axis=0)
    if cfg["tier"] == "reversal":
        record["rule"] = "reversal_nutting"
        return (cfg["value"] / 1000.0) * np.sqrt(np.maximum(gross, 1e-6))
    if cfg["tier"] == "curve" or "family_curve" in cfg:
        shape = shapes[cfg.get("family_curve", stock)]
        record["rule"] = "granularity_chart"
        return np.stack([shape.at(layer, net[:, j]) for j, layer in enumerate("RGB")], axis=1)
    if cfg["tier"] == "pgi":
        ratio, per_mag = pgi_ratio(stock)
        value = PGI_REFERENCE_SIGMA * ratio
        record.update(rule="pgi_ratio, pgi_anchor_external, single_value_green_anchor", pgi_ratio_to_reference=round(ratio, 4),
                      pgi_ratio_per_magnification=per_mag, value_at_net_1=round(value, 5))
    else:
        value = cfg["value"] / 1000.0
        record.update(rule="single_value_green_anchor", value_at_net_1=value)
    shape = shapes[SHAPE_STOCK]
    scale = value / float(shape.at("G", np.array([1.0]))[0])
    record["scale_of_5207_shape"] = round(scale, 4)
    return np.stack([scale * shape.at(layer, net[:, j]) for j, layer in enumerate("RGB")], axis=1)


def main() -> int:
    curves = json.loads(CURVES.read_text(encoding="utf-8"))["stocks"]
    shapes = {name: ChannelShape(data["layers"]) for name, data in curves.items()}
    catalog = sorted(mp.CATALOG["negatives"]) + sorted(mp.CATALOG["reversals"])
    missing = sorted(set(catalog) ^ set(STOCKS))
    if missing:
        raise ValueError(f"the stock table and the catalog differ: {missing}")
    out = {"description": __doc__.split("\n\n")[0], "max_nodes": MAX_NODES, "node_relative_limit": NODE_RELATIVE_LIMIT,
           "solve_relative_limit": SOLVE_RELATIVE_LIMIT, "pgi_units_per_ln": PGI_UNITS_PER_LN,
           "pgi_reference": {"stock": PGI_REFERENCE, "sigma_48_green_net_1": PGI_REFERENCE_SIGMA,
                             "source": "Fotufilm Sources/FotufilmCore/Stocks/portra400.json grainStrength (Fotufilm profile, CC BY-SA 4.0, commit 6b45c80); external value, no primary source"},
           "stocks": {}}
    failures = []
    for stock in catalog:
        cfg = STOCKS[stock]
        record = {k: v for k, v in cfg.items() if k not in ("pgi",)}
        if "pgi" in cfg:
            record["pgi_135"] = dict(zip(MAGNIFICATIONS, cfg["pgi"]))
        ramp = model_ramp(stock)
        sigma = channel_sigma(stock, ramp, shapes, record)
        jac2 = ramp["jacobian"] ** 2
        layer = np.zeros_like(sigma)
        worst = 0.0
        for i in range(len(sigma)):
            x, _ = nnls(jac2[i], sigma[i] ** 2)
            layer[i] = np.sqrt(x)
            fit = np.sqrt(jac2[i] @ x)
            worst = max(worst, float(np.max(np.abs(fit / sigma[i] - 1.0))))
        record["solve_largest_relative_error"] = round(worst, 5)
        record["density_kind"] = "status_a_gross" if ramp["reversal"] else "status_m_gross"
        record["amount_kind"] = "dye_amount" if not ramp["reversal"] else "dye_amount (dye_max - record)"
        channel, layers, node_err = {"density": [], "sigma_48": []}, {"amount": [], "sigma_amount": []}, 0.0
        for k in range(3):
            xd, yd, e1 = reduce_nodes(ramp["gross"][:, k], sigma[:, k])
            positive = layer[:, k] > 0
            xa, ya, e2 = reduce_nodes(ramp["amounts"][positive, k], layer[positive, k])
            channel["density"].append(xd.round(6).tolist())
            channel["sigma_48"].append(yd.round(7).tolist())
            layers["amount"].append(xa.round(6).tolist())
            layers["sigma_amount"].append(ya.round(7).tolist())
            node_err = max(node_err, e1, e2)
        record.update(channel=channel, layer=layers, node_largest_relative_error=round(node_err, 5))
        g_net1 = float(np.interp(1.0, ramp["gross"][:, 1] - ramp["gross"][:, 1].min(), sigma[:, 1]))
        record["green_sigma_48_at_net_1"] = round(g_net1, 5)
        if worst > SOLVE_RELATIVE_LIMIT or node_err > NODE_RELATIVE_LIMIT:
            failures.append(f"{stock}: solve {worst:.4f}, nodes {node_err:.4f}")
        out["stocks"][stock] = record
        print(f"{stock:24s} {record['tier']:8s} green@net1 {g_net1:.4f} solve {worst:.4f} nodes {node_err:.4f}", flush=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    if failures:
        print("FAILED:", *failures, sep="\n  ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
