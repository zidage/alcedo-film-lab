"""P11: measure print viewing, stage derivatives, and labelled RAW review sheets.

Inputs: current P6 profiles and local RAW files. Outputs: build/tmp/p11 only.
All stage derivatives are diagnostics, never transforms fitted to image data.
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from print_viewing import fp, mp, sa, cam16, render_variants
import display_transforms as dt

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "build/tmp/p11"
STOCKS = ("kodak_portra_160", "kodak_portra_400", "kodak_portra_800",
          "kodak_ektar_100", "kodak_gold_200", "kodak_ultramax_400", "kodak_5207")
DISPLAY = sa.Display(fp)


def metrics(code: np.ndarray, base: np.ndarray) -> dict:
    """Mean M' ratio over reference M'>6; also retain unratioed means."""
    a, b = (DISPLAY.appearance(x.reshape(-1, 3))["UCS"] for x in (code, base))
    ma, mb = np.linalg.norm(a[:, 1:], axis=-1), np.linalg.norm(b[:, 1:], axis=-1)
    valid = mb > 6
    return {"Mprime_ratio": float(np.mean(ma[valid] / mb[valid])),
            "mean_Mprime": float(ma.mean()), "mean_Jprime": float(a[:, 0].mean())}


def stage_trace(model) -> dict:
    """Central differences at grey: epsilon=0.001 log10 AP1, check at half step.

    Save full derivatives with units. Density and exposure units are distinct.
    Singular values on the zero-sum plane are only local separation measures.
    """
    basis = np.array([[1, -1, 0], [1, 1, -2]], dtype=float).T
    basis /= np.linalg.norm(basis, axis=0)

    def stages(x):
        q, _ = model.layer_exposure(x)
        a, _ = model.negative_density(q)
        f = model.film
        ph = f.paper_log_exposure(f.negative_spectral_density(a))
        pa = np.stack([np.interp(ph[:, k], c.log_h, c.density)
                       for k, c in enumerate(model.paper_curves)], axis=-1)
        xyz = model.print_xyz(a)
        cam = DISPLAY.cam.forward(xyz @ model.xyz_to_display.T
                                  @ DISPLAY.rec709_to_xyz.T * 100)
        return {"log10_layer_exposure": np.log10(q), "negative_dye_amount": a,
                "log10_paper_exposure": ph, "paper_Status_A": pa,
                "print_CAM16_UCS": cam16.ucs_of(*(cam[k] for k in ("J", "M", "h")))}

    derivatives = []
    for step in (0.001, 0.0005):
        x = np.concatenate([0.18 * 10 ** (step * np.eye(3)),
                            0.18 * 10 ** (-step * np.eye(3))])
        derivatives.append({k: ((v[:3] - v[3:]) / (2 * step)).T
                            for k, v in stages(x).items()})
    return {k: {"jacobian_per_log10_AP1": v.tolist(),
                "opponent_singular_values": np.linalg.svd(
                    v[1:, :] @ basis if k == "print_CAM16_UCS" else basis.T @ v @ basis,
                    compute_uv=False).tolist(),
                "half_step_absolute_difference": float(np.max(np.abs(v - derivatives[1][k])))}
            for k, v in derivatives[0].items()}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cam16.check()
    pipe = mp.Pipeline()
    settings = mp.RenderSettings(scene_light="D55", apd_lad_aim=False)
    probe = pipe.print_model(settings)
    sweep = sa.make_sweep(fp, probe.c)
    select = (sweep.kind == 0) & (sweep.exposure == 0)
    ramp = sweep.ap1[select][None].astype(np.float64)
    reference = np.asarray(dt.render_native("opendrt", ramp.astype(np.float32), fp.srgb_encode))
    previous = OUT / "measurements.json"
    photos = json.loads(previous.read_text(encoding="utf-8"))["photos"] if previous.exists() else {}
    report = {"settings": vars(settings), "sweep": {}, "photos": photos, "stages": {}}
    spread = {k: [] for k in ("print", "cam100", "cam500", "cam2000", "scan")}
    for stock in STOCKS:
        st = replace(settings, negative=stock)
        model = pipe.print_model(st)
        variants, checks = render_variants(model, ramp)
        variants["scan"] = np.asarray(pipe.scan_model(replace(st, method="apd")).render(ramp)[0])
        original = np.asarray(model.render(ramp)[0])
        error = float(np.max(np.abs(original - variants["print"])))
        if error > 1e-4:
            raise AssertionError(f"reference print differs from compiled print: {error}")
        report["sweep"][stock] = {k: metrics(v, reference) for k, v in variants.items()}
        report["sweep"][stock]["checks"] = checks | {"print_code_difference": error}
        report["stages"][stock] = stage_trace(model)
        if stock != "kodak_5207":
            for k, v in variants.items():
                spread[k].append(DISPLAY.appearance(v.reshape(-1, 3))["UCS"])
        print(stock, report["sweep"][stock], flush=True)
    report["spread"] = {k: float(np.mean([np.linalg.norm(a-b, axis=-1).mean()
                         for i, a in enumerate(v) for b in v[i+1:]])) for k, v in spread.items()}
    font = ImageFont.load_default(size=15)
    for name in sys.argv[1:]:
        path = Path(name)
        st = mp.resolve_as_shot(replace(settings, scene_light=mp.AS_SHOT), path)
        ap1, decode = mp.decode_raw(path, probe.c, 640)
        graded = np.ascontiguousarray(fp.fk.product_grade(ap1, st.exposure_ev, st.contrast, st.saturation))
        base = np.asarray(dt.render_native("opendrt", graded, fp.srgb_encode))
        rows, photo = [], {"source": str(path), "scene_light": st.scene_light, "stocks": {}}
        for stock in ("kodak_portra_400", "kodak_ektar_100", "kodak_gold_200", "kodak_5207"):
            model = pipe.print_model(replace(st, negative=stock))
            variants, checks = render_variants(model, graded)
            variants["scan"] = np.asarray(pipe.scan_model(replace(st, negative=stock, method="apd")).render(graded)[0])
            values = {k: metrics(v, base) for k, v in variants.items()}
            photo["stocks"][stock] = {"metrics": values, "checks": checks}
            tiles = [("OpenDRT | no film", base)] + [(f"{stock} | {k} | M' {values[k]['Mprime_ratio']:.2f}", v) for k, v in variants.items()]
            h, w = base.shape[:2]
            row = Image.new("RGB", ((w+4)*len(tiles), h+48), (20, 20, 20))
            draw = ImageDraw.Draw(row)
            for i, (label, tile) in enumerate(tiles):
                row.paste(Image.fromarray((np.clip(tile, 0, 1)*255+0.5).astype(np.uint8)), (i*(w+4), 48))
                draw.text((i*(w+4)+5, 3), label.replace(" | ", "\n", 1), font=font, fill="white")
            rows.append(row)
        sheet = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
        y = 0
        for row in rows:
            sheet.paste(row, (0, y))
            y += row.height
        sheet.save(OUT / f"review_{path.stem}.jpg", quality=94)
        # A separate readable sheet per stock, without changing the measured render size.
        for stock, row in zip(("portra400", "ektar100", "gold200", "5207"), rows):
            row.save(OUT / f"review_{path.stem}_{stock}.jpg", quality=94)
        report["photos"][path.stem] = photo
        (OUT / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
        print(path.stem, "done", flush=True)
    (OUT / "measurements.json").write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
