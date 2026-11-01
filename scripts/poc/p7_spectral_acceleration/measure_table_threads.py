"""Wall time and process CPU time of each stage of the print table, to show how far each one runs in parallel.

Input: the profiles and the reflectance tables. Output: a line per stage on stdout. Step: P7, ROADMAP U68.
"""
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts/poc/p6_mvp_gui"))
import mvp_pipeline as mp

fp = mp.fp
model = fp.FilmPreview(mp.film_options(mp.RenderSettings()))
grid = model.density_grid


def measure(name, fn, repeat=3):
    best = None
    for _ in range(repeat):
        wall, cpu = time.perf_counter(), time.process_time()
        fn()
        wall, cpu = time.perf_counter() - wall, time.process_time() - cpu
        if best is None or wall < best[0]:
            best = (wall, cpu)
    print(f"{name}: wall {best[0]:.3f} s, CPU {best[1]:.3f} s, CPU / wall {best[1] / best[0]:.1f}", flush=True)


def stage_a():
    fp._stage_tables.clear()
    model._negative_stage(grid)


def stage_b():
    fp._stage_tables.clear()
    model._paper_stage()


model._negative_stage(grid)
model._paper_stage()
measure("stage A, negative to paper exposure", stage_a)
measure("stage B, paper Status A to XYZ", stage_b)
model._negative_stage(grid)
model._paper_stage()
measure("stage C, composition", lambda: model._compose_print_table(grid, model.film.printer_balance_log10), 5)
measure("model build, stages kept", lambda: fp.FilmPreview(mp.film_options(mp.RenderSettings(print_contrast=1.1))))
