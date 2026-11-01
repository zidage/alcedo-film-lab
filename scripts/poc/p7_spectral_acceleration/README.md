# P7: Spectral acceleration

Scripts of step P7 ([report](../../../docs/exploration/p7_spectral_acceleration.md), ROADMAP U68). The C++ library builds the print table and the APD table. The Python viewer and the product use the same source.

| File | Input | Output |
| --- | --- | --- |
| `film_tables/film_tables.hpp`, `film_tables.cpp` | flat arrays | the table stages; static library target `film_tables`, with no dependency on Python or Qt |
| `film_tables/python_bindings.cpp` | NumPy arrays | Python module `alcedo_film_tables` (nanobind) |
| `check_film_tables.py` | profiles, reflectance tables, AP1 arrays under `build/tmp/` | `results/p7_spectral_acceleration/checks.json` |
| `check_fast_image_steps.py` | RAW files, or AP1 arrays | `results/p7_spectral_acceleration/image_steps.json` |
| `sweep_inhibition_steps.py` | a RAW file, an AP1 array | `results/p7_spectral_acceleration/inhibition_steps.json` |
| `sweep_paper_axis.py` | the same | stdout: error and time for each node count and axis power |
| `measure_table_threads.py` | profiles, reflectance tables | stdout: wall time and CPU time of each stage |
| `build_product_resources.py` | profiles, catalog, reflectance table | `build/tmp/p7/product_resources/resources/` (shipped by Alcedo Studio), `.../expected/` (lab values of its host tests), `results/p7_spectral_acceleration/product_resources.json` |

`film_preview.py` imports `alcedo_film_tables`. If the module is not installed, the import stops with an error, and there is no other path for the tables. Install it again after a change of the C++ source.

The print tables and the APD tables are not stored. The process keeps the spectral stages in memory (`STAGE_TABLES_KEPT` in `film_preview.py`). The reflectance tables stay in `build/tmp/p2/tables/`.

## Commands

Run these from the repository root. The build needs a C++20 compiler (MSVC 2022 on the development machine). pip downloads nanobind, scikit-build-core, and a CMake of at least 3.29.

```bash
E=build/tmp/p6
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p7_spectral_acceleration/requirements.txt
P=$E/venv/Scripts/python
$P -I scripts/poc/p7_spectral_acceleration/check_film_tables.py      # about 7 min
$P -I scripts/poc/p7_spectral_acceleration/check_fast_image_steps.py RAW1 RAW2
$P -I scripts/poc/p7_spectral_acceleration/sweep_paper_axis.py       # about 10 min
$P -I scripts/poc/p7_spectral_acceleration/measure_table_threads.py
$P -I scripts/poc/p7_spectral_acceleration/build_product_resources.py  # about 2 min
$P -I scripts/poc/p7_spectral_acceleration/build_display_expected.py   # about 1 min; sRGB values for the kernel tests of Alcedo Studio
```

To install only the library in an environment that exists:

```bash
$E/venv/Scripts/python -m pip install ./scripts/poc/p7_spectral_acceleration/film_tables
```
