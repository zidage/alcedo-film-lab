# P15: Film grain data

Scripts of step P15 ([report](../../../docs/exploration/p15_film_grain.md)). They make the grain data of every film stock of the catalog
and the reference evaluator for phase G0 of the Alcedo Studio plan `film_grain_format_and_stock_plan.md` (issue #675). The product
renders the grain; this step makes its data and its expected values (ROADMAP section 2, point 12).

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | `build/tmp/p15_grain/sources/` (local, 38 documents, hash checked) |
| `digitize_granularity_charts.py` | the vector charts of `chart_config.json` | `results/p15_film_grain/granularity_curves.json`; overlays in `build/tmp/p15_grain/overlays/` (local) |
| `check_5207_product_segments.py` | the 5207 digitization and the segments of `film_grain_math.h` | `results/p15_film_grain/check_5207_product_segments.json` |
| `stock_granularity.py` | the digitization, the values of its table `STOCKS`, the viewer models | `results/p15_film_grain/stock_grain.json` |
| `fit_scan_correlation_width.py` | residual blocks of the 5207 scans (`build/tmp/p15_grain/study_660/`, local) | `results/p15_film_grain/scan_correlation_width.json` |
| `fit_layer_correlation.py` | `stock_grain.json`, the 5207 negative, the Negative Scan scanner | `results/p15_film_grain/layer_correlation.json` |
| `post_path_target.py` | `stock_grain.json`, `layer_correlation.json`, 5207 on Endura Premier | `results/p15_film_grain/post_path_target.json` |
| `grain_reference.py` | the three results above, the viewer models | `results/p15_film_grain/grain_reference.json`; with `--expected DIR`, `DIR/grain__expected.bin` |

`scripts/poc/p7_spectral_acceleration/build_product_resources.py` reads the results and writes the group `grain/<stock>/` of
`film_stock_bundle.bin` (schema 11) and `expected/grain__expected.bin`.

## Commands

Use the environment of step P6 (`build/tmp/p6/venv`, see [the P6 README](../p6_mvp_gui/README.md)); this step adds no package
(PyMuPDF and SciPy are in it). Run the scripts in this order:

```powershell
$P = "build/tmp/p6/venv/Scripts/python.exe"
& $P -I scripts/poc/p15_film_grain/fetch_sources.py
& $P -I scripts/poc/p15_film_grain/digitize_granularity_charts.py
& $P -I scripts/poc/p15_film_grain/check_5207_product_segments.py
& $P -I scripts/poc/p15_film_grain/stock_granularity.py
& $P -I scripts/poc/p15_film_grain/fit_scan_correlation_width.py
& $P -I scripts/poc/p15_film_grain/fit_layer_correlation.py
& $P -I scripts/poc/p15_film_grain/post_path_target.py
& $P -I scripts/poc/p15_film_grain/grain_reference.py
& $P -I scripts/poc/p7_spectral_acceleration/build_product_resources.py
```

`fit_scan_correlation_width.py` needs the residual blocks of the grain colour study of Alcedo Studio #660, made from the 5207 scans
of the user. The scans and the blocks stay local (AGENTS.md, "Photos and privacy"); the committed result holds only the fitted
widths.
