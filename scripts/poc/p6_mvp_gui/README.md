# P6: Python MVP

Scripts of step P6 ([report](../../../docs/exploration/p6_python_mvp.md), README U61). The program takes a RAW file to a TIFF or JPEG at 2048 pixels on the long edge, by the print or by the classic scan with the Frontier table. It runs on the CPU, and it is not the product path of Alcedo Studio.

| Script | Input | Output |
| --- | --- | --- |
| `import_sfl_profiles.py` | a local clone of spectral_film_lut at `bcbcfc68` | new files in `profiles/`, `stock_catalog.json` |
| `fit_stock_physics.py` | the profiles | `stock_physics.json`; rule `relative_sensitivity_level` in the profiles that need it |
| `fetch_frontier_tables.py` | NegPy at `cce849ad` | `build/tmp/p6/vendor/frontier.npz` (not in this repository; the product includes it, README U63) |
| `mvp_pipeline.py`, `frontier_scan.py` | library | used by the scripts below |
| `p6_mvp_cli.py` | a RAW file and options | image and a parameter file |
| `p6_mvp_gui.py` | a RAW file, chosen in the window | display and export |
| `check_p6_mvp.py` | a RAW file | `results/p6_python_mvp/checks.json` |
| `check_p6_controls.py` | an AP1 array at 2048 pixels | `results/p6_python_mvp/controls.json` |
| `render_p6_review.py` | AP1 arrays of the earlier steps | `build/tmp/p6/review/*.jpg` with a label on every panel (local only) |

The tables and the sources of P0 to P5 must be present. A first use of a negative and print pair builds its table in about 7 seconds, in `build/tmp/p2/tables/`.

The window and the command line have the controls of `mvp_pipeline.CONTROLS` (README U62). `p6_mvp_cli.py --help` lists them with their ranges. A new value of a control that is part of the print table (print contrast, paper flash, surface reflection, print grey density shift, print timing, overexposure, development inhibition) builds and stores one more table of 6.6 MB, and this takes about 6 seconds. These tables stay in `build/tmp/p2/tables/` until they are deleted. If the directory is empty, the next run builds the spectral tables again from the sources of P1 in `build/tmp/p1/sources/`, and this reads the ISSA workbook through `openpyxl`.

## Commands

```bash
E=build/tmp/p6
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p6_mvp_gui/requirements.txt
P=$E/venv/Scripts/python
D=scripts/poc/p6_mvp_gui
$P -I $D/fetch_frontier_tables.py
$P $D/p6_mvp_cli.py --list
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.tif --negative kodak_gold_200 --method frontier
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.jpg --negative kodak_ektar_100 --method print --print-material kodak_endura_premier --scene-light tungsten --spectral-prior measured_reflectance
$P $D/p6_mvp_gui.py INPUT.ARW
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.jpg --print-contrast 1.0 --print-flash 0.0 --halation-scale 3
$P $D/check_p6_mvp.py INPUT.ARW
$P $D/check_p6_controls.py AP1_2048.npy
$P $D/render_p6_review.py
```

To make the data again: `$P -I $D/import_sfl_profiles.py build/tmp/baseline/src_sfl/repo/src/spectral_film_lut`, then `$P -I $D/fit_stock_physics.py`. Delete a new profile first to write it again, because the importer does not change an existing file.
