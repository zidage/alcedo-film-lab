"""Paper table nodes and axis power against the difficult cases of check_film_tables.py, with the place of the largest error on the neutral ramp.

Input: the profiles, the reflectance tables, AP1 arrays under build/tmp/. Output: a line per case on stdout. Step: P7, ROADMAP U68. No limit applies here; check_film_tables.py has the limits.
"""
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts/poc/p6_mvp_gui"))
import mvp_pipeline as mp

fp = mp.fp
T = REPO / "build/tmp"
PHOTOS = {"se188": "p3/input/se188", "se228": "p3/input/se228", "leica_m11": "p3/input/leica_m11", "nikon_zf": "p3/input/nikon_zf", "_DSC4063": "p4/input_shangrila/_DSC4063", "_DSC8148": "baseline/night/_DSC8148_ap1", "digital": "p5/real_5207/pair/digital_ap1"}
d = mp.RenderSettings()
photos = {k: np.ascontiguousarray(fp.fk.product_grade(np.ascontiguousarray(np.load(T / f"{v}.npy"), dtype=np.float32), 1.5, float(d.contrast), float(d.saturation)), dtype=np.float32) for k, v in PHOTOS.items()}
stops = np.linspace(-5, 5, 241)
ramp = np.outer(0.18 * 2.0 ** stops, np.ones(3)).astype(np.float32)[None]
CASES = {"5207 2383": d, "5207 2383 contrast 1.3": replace(d, print_contrast=1.3), "5207 2383 grey -0.3": replace(d, print_grey_shift=-0.3), "5219 2383": replace(d, negative="kodak_5219"),
         "Ektar Endura": replace(d, negative="kodak_ektar_100", print_material="kodak_endura_premier"), "Portra400 Endura": replace(d, negative="kodak_portra_400", print_material="kodak_endura_premier")}
refs = {}
for name, s in CASES.items():
    m = fp.FilmPreview(mp.film_options(s))
    nodes = np.stack(np.meshgrid(*m.density_grid, indexing="ij"), axis=-1).reshape(-1, 3)
    refs[name] = np.cbrt(m._print_nodes(nodes)[0]).reshape(m.print_table.shape).astype(np.float32)


def diff(m, ref, image):
    a = np.asarray(m.render(image)[0], dtype=np.float64)
    keep = m._print_f32
    m._print_f32 = ref
    b = np.asarray(m.render(image)[0], dtype=np.float64)
    m._print_f32 = keep
    return np.abs(a - b).max(axis=-1) * 255.0, a, b


first = True
for n, power in ((65, 1.0), (97, 1.0), (129, 1.0), (65, 1.5), (65, 2.0), (65, 3.0), (81, 2.0), (97, 2.0)):
    fp.PAPER_TABLE_NODES, fp.PAPER_AXIS_POWER = n, power
    fp._stage_tables.clear()
    t = time.perf_counter()
    fp.FilmPreview(mp.film_options(d))
    build = time.perf_counter() - t
    print(f"--- n {n} power {power}: model with empty memory {build:.2f} s", flush=True)
    for name, s in CASES.items():
        m = fp.FilmPreview(mp.film_options(s))
        r, ra, rb = diff(m, refs[name], ramp)
        p999, largest, worst = 0.0, 0.0, ""
        for k, image in photos.items():
            e, _, _ = diff(m, refs[name], image)
            q = float(np.percentile(e, 99.9))
            if q > p999:
                p999, worst = q, k
            largest = max(largest, float(e.max()))
        print(f"{name:26s} ramp {r.max():.2f} at {stops[r.argmax(axis=None) % 241]:+.1f} stops, code {rb[0, r[0].argmax()].max() * 255:.0f}; photos p99.9 {p999:.2f} ({worst}), largest {largest:.2f}", flush=True)
