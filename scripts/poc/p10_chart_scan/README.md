# P10: chart-calibrated scan

Scripts of step P10 (ROADMAP U87). The negative of a stock is scanned by the ideal APD scanner of P3, and the inversion is calibrated by a
chart photographed on the same stock under the light of the stock: one curve per channel from a flat grey scale, and a 3 x 3 matrix
that keeps a grey neutral, fitted to the 24 patches of the BabelColor Avg ColorChecker spectra. No statistic of a frame, and no ACES
output transform: linear AP1 goes to Rec. 709 with a clip and the sRGB encoding. The rules are stated in `chart_scan.py`.
This is a CPU review tool, not the product path.

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | `build/tmp/p10/sources/` (not committed), hashes checked |
| `chart_scan.py` | P2 negative, P3 APD scanner, the chart | library |
| `run_chart_scan.py` | the library, the rawtoaces training spectra of P1, no photo | `results/p10_chart_scan/chart_scan.json` |
| `compare_lab_scans.py` | the library, `build/tmp/p3/filmanalyzer/measurements.json` (local, public chart scans of real film, no license stated) | `results/p10_chart_scan/lab_scan_compare.json`; with `--spectral`, `lab_scan_compare_spectral.json` (chart spectra straight to the film) |
| `fit_fixed_slope.py` | the viewer, the eight stocks of `ACCEPTED_STOCKS` | `results/p10_chart_scan/fixed_slope.json`; stops if `FIXED_STATUS_M_SLOPE` differs from the mean slope by more than 1e-6 |
| `check_stock_spread.py` | the viewer, a synthetic hue and lightness sweep, no photo | `results/p10_chart_scan/stock_spread.json`; sheet `build/tmp/p10/stock_spread/sweep_sheet.png` (local) |
| `scan_generic.py` | the viewer (method `apd`), the stocks of `POOLS` | library: rule `generic_scan` (U98), one channel scale and one pair of ADX to ACES matrices per medium |
| `render_chart_scan_review.py` | RAW files of the Alcedo Studio sample images | `build/tmp/p10/review3/<stock>.jpg` with a label on every panel (local only), `results/p10_chart_scan/review4.json` (round 4; earlier rounds wrote `review/`, `review3/`) |

```
build/tmp/p6/venv/Scripts/python -I scripts/poc/p10_chart_scan/fetch_sources.py
build/tmp/p6/venv/Scripts/python -I scripts/poc/p10_chart_scan/run_chart_scan.py
build/tmp/p6/venv/Scripts/python -I scripts/poc/p10_chart_scan/render_chart_scan_review.py
build/tmp/p6/venv/Scripts/python -I scripts/poc/p10_chart_scan/fit_fixed_slope.py
build/tmp/p6/venv/Scripts/python -I scripts/poc/p10_chart_scan/check_stock_spread.py
```
