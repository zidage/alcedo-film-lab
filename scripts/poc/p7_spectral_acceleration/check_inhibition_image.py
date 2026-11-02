"""Checks of rule 'inhibition_image_part' on all negatives with a modulation transfer chart, and on one photo.

Input: stock_catalog.json, inhibition_image.json, the tables of the model, and build/tmp/p7/product_resources/expected/image/ap1.bin (build_image_expected.py). Output: results/p7_spectral_acceleration/inhibition_image.json. Step: P7, ROADMAP U74.
"Before" is the same negative with no value of the rule: all of K has the blur, with the spread of the old fit.

| Check | Comparison rule | Limit |
| Negative response | Largest value in each layer of the response to a neutral sine of 0.25 stop at 6000 pixels, normalized at 1 cycle/mm, from 3 to 40 cycles/mm, minus the largest value of the chart | 0.10 |
| Edge of Eterna 500 | Green code, step edge of 3 stops about the grey at 6000 pixels: overshoot and undershoot against the plateaus | 1 code |
| Colour of Eterna 500 | Mean of (largest - smallest channel) on the photo, against before | 1 % |
| Stocks that the fit of P4 describes | kodak_5207 and kodak_portra_400 on the photo, mean channel difference against before | 0.2 codes |
The negatives whose response before the rule was over the limit are listed, as the record of the fault.
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "p6_mvp_gui"))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
RESULT = mp.REPO_ROOT / "results" / "p7_spectral_acceleration" / "inhibition_image.json"
AP1 = mp.REPO_ROOT / "build" / "tmp" / "p7" / "product_resources" / "expected" / "image" / "ap1.bin"
WIDTH, HEIGHT = 6000, 32
GREY, AMPLITUDE_STOPS, MARGIN = 0.18, 0.25, 600
FREQUENCIES = (3, 5, 7, 10, 15, 20, 30, 40)
PEAK_LIMIT, EDGE_LIMIT_CODES, CHROMA_LIMIT, MEAN_LIMIT_CODES = 0.10, 1.0, 0.01, 0.2


def neutral_image(stops: np.ndarray) -> np.ndarray:
    return np.broadcast_to((GREY * 2.0**stops)[None, :, None], (HEIGHT, WIDTH, 3)).astype(np.float32).copy()


def layer_response(model: fp.FilmPreview, cycles_per_mm: float) -> np.ndarray:
    carrier = np.sin(2 * np.pi * round(cycles_per_mm * 36.0) * (np.arange(WIDTH) + 0.5) / WIDTH)
    density = np.asarray(model.negative_image(neutral_image(AMPLITUDE_STOPS * carrier))[0], dtype=np.float64)[HEIGHT // 2, MARGIN:-MARGIN]
    c = carrier[MARGIN:-MARGIN]
    return np.array([(density[:, k] - density[:, k].mean()) @ c / (c @ c) for k in range(3)])


def peaks(model: fp.FilmPreview, xs: list[np.ndarray]) -> np.ndarray:
    base = layer_response(model, 1.0)
    measured = {f: layer_response(model, f) / base for f in FREQUENCIES}
    return np.array([max(measured[f][k] for f in FREQUENCIES if xs[k][0] <= f <= xs[k][-1]) for k in range(3)])


def edge_codes(model: fp.FilmPreview) -> tuple[float, float]:
    stops = np.where(np.arange(WIDTH) < WIDTH // 2, -1.5, 1.5)
    green = np.asarray(model.render(neutral_image(stops))[0], dtype=np.float64)[HEIGHT // 2, :, 1] * 255.0
    return float(green[WIDTH // 2 :].max() - green[WIDTH // 2 + 1500]), float(green[WIDTH // 2 - 1500] - green[: WIDTH // 2].min())


def read_ap1() -> np.ndarray:
    with AP1.open("rb") as stream:
        magic = stream.read(8)
        length = struct.unpack("<Q", stream.read(8))[0]
        header = json.loads(stream.read(length))
        entry = header["arrays"]["ap1"]
        stream.seek(len(magic) + 8 + length + entry["offset"])
        return np.fromfile(stream, dtype="<f4").reshape(entry["shape"])


def main() -> int:
    stocks, failures = {}, []
    for negative in mp.CATALOG["negatives"]:
        chart = fp.p0.load_profile(negative)["charts"].get("modulation_transfer")
        settings = mp.RenderSettings(negative=negative)
        if not chart or mp.load_physics().get(negative, {}).get("error") or not any(mp.film_options(settings).inhibition_total):
            continue
        names = ("red", "green", "blue") if "red" in chart["curves"] else ("all_layers",) * 3
        xs = [np.array(chart["curves"][n]["x"]) for n in names]
        ys = [np.array(chart["curves"][n]["y"]) for n in names]
        chart_peak = np.array([y[(x >= 3) & (x <= 40)].max() for x, y in zip(xs, ys)])
        before, after = peaks(fp.FilmPreview(mp.film_options(settings, image_part=False)), xs), peaks(fp.FilmPreview(mp.film_options(settings)), xs)
        over = after - chart_peak
        if (over > PEAK_LIMIT).any():
            failures.append(f"{negative}: response {np.round(after, 3).tolist()} against chart {np.round(chart_peak, 3).tolist()}")
        stocks[negative] = dict(chart_peak=np.round(chart_peak, 3).tolist(), before=np.round(before, 3).tolist(), after=np.round(after, 3).tolist())
        print(f"{negative:24s} chart {np.round(chart_peak, 2).tolist()} before {np.round(before, 2).tolist()} after {np.round(after, 2).tolist()}", flush=True)

    eterna = mp.RenderSettings(negative="fuji_eterna_500")
    edges = dict(before=edge_codes(fp.FilmPreview(mp.film_options(eterna, image_part=False))), after=edge_codes(fp.FilmPreview(mp.film_options(eterna))))
    if max(edges["after"]) > EDGE_LIMIT_CODES:
        failures.append(f"edge of fuji_eterna_500: {edges['after']}")
    print("edge", edges, flush=True)

    ap1 = read_ap1()
    photo = {}
    for negative, print_material in (("fuji_eterna_500", "kodak_2383"), ("kodak_5207", "kodak_2383"), ("kodak_portra_400", "kodak_endura_premier")):
        settings = mp.RenderSettings(negative=negative, print_material=print_material)
        old = np.asarray(fp.FilmPreview(mp.film_options(settings, image_part=False)).render(ap1)[0], dtype=np.float32)
        new = np.asarray(fp.FilmPreview(mp.film_options(settings)).render(ap1)[0], dtype=np.float32)
        chroma_old, chroma_new = float((old.max(axis=-1) - old.min(axis=-1)).mean() * 255.0), float((new.max(axis=-1) - new.min(axis=-1)).mean() * 255.0)
        photo[negative] = dict(mean_difference_codes=float(np.abs(new - old).mean() * 255.0), chroma_before=chroma_old, chroma_after=chroma_new)
        print(negative, photo[negative], flush=True)
    if abs(photo["fuji_eterna_500"]["chroma_after"] / photo["fuji_eterna_500"]["chroma_before"] - 1.0) > CHROMA_LIMIT:
        failures.append(f"chroma of fuji_eterna_500: {photo['fuji_eterna_500']}")
    for negative in ("kodak_5207", "kodak_portra_400"):
        if photo[negative]["mean_difference_codes"] > MEAN_LIMIT_CODES:
            failures.append(f"difference on {negative}: {photo[negative]}")

    RESULT.write_text(json.dumps(dict(stocks=stocks, edge_fuji_eterna_500=edges, photo=photo, failures=failures), indent=1) + "\n", encoding="utf-8", newline="\n")
    print("failures:", failures, flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
