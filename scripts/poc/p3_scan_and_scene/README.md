# P3: scene presets and scanned-negative output

Scripts of step P3 ([report](../../../docs/exploration/p3_scan_and_scene.md)). They take the negative of P2 through an ideal APD scanner, ADX10, and the ACES 1.3 and 2.0
output transforms, and they review global scene mixtures (ROADMAP U21, U22, U23). This is a CPU review tool, not the product path.

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | `build/tmp/p3/sources/` (not committed), hashes checked |
| `aces_scan.py` | P2 library, APD table, OpenColorIO | library: scanner, encoding, transform, output; APD table cache in `build/tmp/p2/tables/` |
| `check_scan_path.py` | the library, no photo | `results/p3_scan_and_scene/scan_checks.json` |
| `compare_apd_spectral_film_lut.py` | APD table, local clone of spectral_film_lut | `results/p3_scan_and_scene/apd_table_comparison.json` |
| `render_scan_review.py` | AP1 arrays of the P2 baseline | `build/tmp/p3/renders/<name>_<stock>.png` (local only), `results/p3_scan_and_scene/scan_review.json` |
| `compare_film_analyzer.py` | `build/tmp/p3/filmanalyzer/measurements.json` (local, public chart measurements, no license stated) | `results/p3_scan_and_scene/film_analyzer_compare.json`; the values of the scans stay in `build/tmp/p3/filmanalyzer/real_summary.json` |
| `render_full_review.py` | RAW files of signatureedits.com and of the Alcedo Studio sample images, night arrays | `build/tmp/p3/review/images/` and `overview_*.png` with a label on every panel (local only), `results/p3_scan_and_scene/full_review.json` |
| `fit_scanner_to_chart.py` | `build/tmp/p3/filmanalyzer/measurements.json` (local). Test only, ROADMAP U28 | `build/tmp/p3/fitted_scanner/fits.json` (local only) |
| `render_fitted_scanner_review.py` | The fits, AP1 arrays. Test only, ROADMAP U28 | `build/tmp/p3/fitted_scanner/review/*.png` with a label on every panel (local only) |
| `render_soft_scan_review.py` | AP1 arrays; reference scans under `build/tmp/p3/refs/` when present (style reference only, ROADMAP U30) | `build/tmp/p3/review_soft/*.jpg` with a label on every panel (local only) |
| `render_print_apd_review.py` | AP1 arrays | `build/tmp/p3/review_crosstalk/*` with a label on every panel (local only), `results/p3_scan_and_scene/crosstalk_checks.json` |
| `render_scanner_light_review.py` | AP1 arrays; local copies of `noritsu-tool` and of the FlexColor installer data under `build/tmp/p3/scanners/` | `build/tmp/p3/review_light/*.png` with a label on every panel (local only), `results/p3_scan_and_scene/scanner_light.json` |
| `render_scene_review.py` | AP1 arrays of the night files | `build/tmp/p3/renders/scene_<name>.png` (local only), `results/p3_scan_and_scene/scene_review.json` |

The P0, P1, and P2 sources and tables must be present. The AP1 arrays come from `dump_portraits.py` and `night_probe.py` of P2 (`build/tmp/baseline/`).

## Commands

Run from the repository root (Git Bash on Windows).

```bash
E=build/tmp/p3
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p3_scan_and_scene/requirements.txt
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/fetch_sources.py
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/check_scan_path.py                 # about 3 min with the tables cached
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/compare_apd_spectral_film_lut.py
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/render_scan_review.py              # 14 portraits, 6 night files; or names of files
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/render_scene_review.py             # 6 night files; or names of files
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/compare_film_analyzer.py           # needs the local measurements
$E/venv/Scripts/python -I scripts/poc/p3_scan_and_scene/render_full_review.py              # all files, about 20 min; --limit N for a test
```
