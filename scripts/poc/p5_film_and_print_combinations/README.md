# P5: other film and print combinations

Scripts of step P5 ([report](../../../docs/exploration/p5_film_and_print_combinations.md)). This is a CPU review tool, not the product path. `STOCKS` and `P5_PHYSICAL` in `film_preview.py` hold the options of this step.

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | data sheets in `build/tmp/p5/sources/` (local only) |
| `digitize_stock_charts.py` | the data sheets; a local clone of spectral_film_lut at `bcbcfc68` | five profiles in `profiles/`, `results/p5_film_and_print_combinations/source_checks.json` |
| `fit_mtf_stocks.py` | the profiles | `results/p5_film_and_print_combinations/mtf_fit.json` |
| `check_stock_chain.py` | the libraries, no photo | `results/p5_film_and_print_combinations/stock_chain.json` |
| `render_p5_review.py` | AP1 arrays of P3 and P4 | `build/tmp/p5/review/*.jpg` with a label on every panel (local only), `results/p5_film_and_print_combinations/review.json` |
| `check_shadow_mode.py` | the libraries, no photo | `results/p5_film_and_print_combinations/shadow_mode.json` |
| `render_shadow_mode_review.py` | AP1 arrays | `build/tmp/p5/review_mask/*.jpg` with a label on every panel (local only) |
| `render_scan_inversion.py --export` | AP1 arrays | 16 bit negatives in `build/tmp/p5/scan_negative/`, `build/tmp/p5/review_inversion/*.jpg` with a label on every panel (local only), `results/p5_film_and_print_combinations/inversion_shadows.json` |
| `render_density_window.py` | AP1 arrays; optional `--reference` with the JPEG files of NexFilm | `build/tmp/p5/review_density_window/*.jpg` with a label on every panel (local only), `results/p5_film_and_print_combinations/density_window.json` |
| `compare_spektrafilm_sheets.py --inputs-only` | AP1 arrays | `build/tmp/p5/input_compare/` (local only) |
| `render_spektrafilm_stocks.py` | those arrays; the local spektrafilm clone and its environment (external comparison only, README U18) | `build/tmp/p5/out_spektrafilm/*.png` (local only) |
| `compare_spektrafilm_sheets.py` | both of the above | `build/tmp/p5/review_spektrafilm/*.jpg` with a label on every panel (local only) |

The P0, P1, P2, P3, and P4 sources and tables must be present.

## Commands

Run from the repository root (Git Bash on Windows). The environment of P0 has `pymupdf`, and the environment of P3 has the model packages. `requirements.txt` lists all of them.

```bash
Q=build/tmp/p0/venv/Scripts/python
P=build/tmp/p3/venv/Scripts/python
D=scripts/poc/p5_film_and_print_combinations
$Q -I $D/fetch_sources.py
$Q -I $D/digitize_stock_charts.py build/tmp/baseline/src_sfl/repo/src/spectral_film_lut
$P -I $D/fit_mtf_stocks.py
$P -I $D/check_stock_chain.py
$P -I $D/render_p5_review.py                    # 56 files; or names of files
$P -I $D/check_shadow_mode.py                   # about 15 min on the first run, for the mask tables
$P -I $D/render_shadow_mode_review.py
$P -I $D/render_scan_inversion.py --export
$P -I $D/render_density_window.py --reference build/tmp/p5/scan_negative/Portra_400_scanned   # JPEG files from NexFilm, local
$P -I $D/compare_spektrafilm_sheets.py --inputs-only
build/tmp/baseline/venv_spektra/Scripts/python -I $D/render_spektrafilm_stocks.py
$P -I $D/compare_spektrafilm_sheets.py
```
