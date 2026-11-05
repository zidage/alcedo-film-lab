# P6: Python MVP

Scripts of step P6 ([report](../../../docs/exploration/p6_python_mvp.md), ROADMAP U61, U64). The program takes a RAW file to a TIFF or JPEG at 2048 pixels on the long edge, by the print or by the APD scan: APD, ADX10, the mid grey at code value 445, ADX10 to ACES, and an ACES output transform (`scripts/poc/p3_scan_and_scene/aces_scan.py`). It runs on the CPU, and it is not the product path of Alcedo Studio.

| Script | Input | Output |
| --- | --- | --- |
| `import_sfl_profiles.py` | a local clone of spectral_film_lut at `bcbcfc68` | new files in `profiles/`, `stock_catalog.json` |
| `fit_stock_physics.py` | the profiles | `stock_physics.json`; rule `relative_sensitivity_level` in the profiles that need it |
| `fit_inhibition_image.py` | the profiles, `stock_physics.json` | `inhibition_image.json`: the spread and the image part of rule `inhibition_image_part` |
| `mvp_pipeline.py` | library | used by the scripts below |
| `stock_character.py` | library | rule `stock_character` of control `--stock-character` (step P12, ROADMAP section 2, point 7) |
| `scene_input.py` | library | P13 complete RAW white, spectral families and constrained input with stock character |
| `check_scene_input.py` | night RAW and P13 reference | display comparison at stock character 1/2 and cache checks in `build/tmp/p13_gui/` |
| `check_scene_input_gui.py` | night RAW | Qt worker, stock character 2/3, cached rerender and export checks |
| `p6_mvp_cli.py` | a RAW file and options | image and a parameter file |
| `p6_mvp_gui.py` | a RAW file, chosen in the window | display and export |
| `check_p6_mvp.py` | a RAW file | `results/p6_python_mvp/checks.json` |
| `check_p6_controls.py` | an AP1 array at 2048 pixels | `results/p6_python_mvp/controls.json` |
| `check_foliage_spectra.py` | synthetic colours, all negatives | `results/p6_python_mvp/foliage_spectra.json` |
| `render_p6_review.py` | AP1 arrays of the earlier steps | `build/tmp/p6/review/*.jpg` with a label on every panel (local only) |

The tables and the sources of P0 to P5 must be present. A first use of a negative and print pair builds its table and model in about 1 second, in memory (P7, ROADMAP U68).

Step P9 adds the method `light_table`: a reversal film on a light table, with no print (`--method light_table --reversal NAME`; see [the P9 scripts](../p9_reversal_light_table/README.md)).

Step P10 adds the method `chart_scan` (ROADMAP U88): the negative scanned with APD and inverted from a chart photographed on the same stock, with a log curve and no ACES output transform (`--method chart_scan`, control `--chart-scan-exposure-stops`; in the window: Method "Scan, chart calibrated (log curve)"; see [the P10 scripts](../p10_chart_scan/README.md)). Setting `--chart-scan-slope` (U89; window: Slope in the group Chart scan): `fixed` (default), one Status M slope for all stocks; `stock`, the slope of the grey scale of each stock (U88). It reads the BabelColor chart of `build/tmp/p10/sources/` (run `scripts/poc/p10_chart_scan/fetch_sources.py` once) and needs `xlrd`.

Step P12 adds control `--stock-character` (window: Stock character, group Negative; ROADMAP section 2, point 7): a creative control k that
enlarges how the sensitivities and the characteristic curves of a negative differ from the average negative of its medium (the pool of rule
generic_scan). 1 is the data, 0 the average, 2 doubles each difference. The changed profile is kept in memory (`PROFILE_OVERRIDES` of
`film_spectral_reference.py`); no file is written. See the [P12 report](../../../docs/exploration/p12_real_pair.md), section 5.

The window and the command line have the controls of `mvp_pipeline.CONTROLS` (ROADMAP U62). `p6_mvp_cli.py --help` lists them with their ranges. A new value of a control that is part of the print table (print contrast, paper flash, surface reflection, print grey density shift, print timing, overexposure, development inhibition) composes one more table in about 0.02 seconds, and the model takes about 0.3 seconds. These tables are not stored. If `build/tmp/p2/tables/` is empty, the next run builds the reflectance tables again from the sources of P1 in `build/tmp/p1/sources/`, and this reads the ISSA workbook through `openpyxl`.

Step P14 adds method `negative_scan` (window: Method "Negative Scan (virtual scanner, P14)", group "Negative scan"; CLI `--method negative_scan`,
`--neg-scan-auto off|neutral|warm|cool`, and the `--neg-scan-*` controls): a virtual film scanner reads the negative, and a rendering model
inverts it, with an optional automatic colour from the frame. See [the P14 scripts](../p14_negative_scan/README.md). Since 2026-11-05 the window
and the command line start with this method, auto colour off, and scene light As Shot (`mvp_pipeline.VIEWER_DEFAULTS`).

## Full RAW white and stock character (P13)

In the window, click **P13 smooth scan** to use the reviewed combination:
Lab Scan, full RAW white / smooth, measured prior, generic scan numbers,
OpenDRT native, and scene cast retained (P13 balance0). The button keeps the
selected negative and Stock character value. Change **Stock character** in
the Negative group to use the changed sensitivity and curves with this input.

**Spectral input** also offers the matched-white LED and fluorescent families,
and constrained smooth or LED reconstruction. These modes use the complete
estimated white of the open RAW. Scene light and Spectral prior are fixed by
that choice and are disabled while it is active. The current input remains
available. P13 modes apply to Lab Scan; other methods keep their existing input.

Constrained modes keep the full 360--840 nm, 1 nm grid and float64 spectral solve.
They can take longer. No complete spectral image is allocated. Two layer-exposure
images are cached; the image, scene light and actual film sensitivity weights
identify a cached result. A stock-character change therefore recomputes the
layer exposures. The RAW white, input family and solver statistics are in the
export parameter file. The generic scanner remains based on stock character 1.

CLI example (use the existing environment):

```powershell
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p6_mvp_gui/p6_mvp_cli.py INPUT.RAW build/tmp/p6/out/smooth.jpg --method apd --negative kodak_portra_400 --spectral-input white_smooth --stock-character 2 --no-lad-aim --apd-axis numbers
```

Checks (set BLAS, OpenMP and Numba to one CPU thread for the recorded run):

```powershell
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p6_mvp_gui/check_scene_input.py
$env:QT_QPA_PLATFORM='offscreen'
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p6_mvp_gui/check_scene_input_gui.py
```

## Commands

```bash
E=build/tmp/p6
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p6_mvp_gui/requirements.txt
P=$E/venv/Scripts/python
D=scripts/poc/p6_mvp_gui
$P -I scripts/poc/p3_scan_and_scene/fetch_sources.py
$P $D/p6_mvp_cli.py --list
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.tif --negative kodak_gold_200 --method apd --apd-output aces13
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.jpg --negative kodak_ektar_100 --method print --print-material kodak_endura_premier --scene-light tungsten --spectral-prior measured_reflectance
$P $D/p6_mvp_gui.py INPUT.ARW
$P $D/p6_mvp_cli.py INPUT.ARW build/tmp/p6/out/result.jpg --print-contrast 1.0 --print-flash 0.0 --halation-scale 3
$P $D/check_p6_mvp.py INPUT.ARW
$P $D/check_p6_controls.py AP1_2048.npy
$P $D/render_p6_review.py
```

To make the data again: `$P -I $D/import_sfl_profiles.py build/tmp/baseline/src_sfl/repo/src/spectral_film_lut`, then `$P -I $D/fit_stock_physics.py`. Delete a new profile first to write it again, because the importer does not change an existing file.
