# P2: negative and print

Scripts of step P2 ([report](../../../docs/exploration/p2_negative_and_print.md)). They render real
RAW files through the selected P1 reconstruction, the Portra 400 negative, and the Endura print for
user review (ROADMAP U17, U18). This is a CPU review tool, not the product path.

| Script | Input | Output |
| --- | --- | --- |
| `film_preview.py` | P0 and P1 libraries, profiles, datasets | library: stages and tables; reflectance tables in `build/tmp/p2/tables/`, print tables in memory only |
| `fast_kernels.py` | arrays from the library | compiled parallel kernels of `render()`, and the reference form of the print table (numba) |
| `check_fast_kernels.py` | the library, a synthetic image | comparison with the array reference, `results/p2_negative_print/fast_kernels.json` |
| `profile_preview.py` | the library, a synthetic image | render times on the console |
| `render_review_images.py` | the library, RAW files | `build/tmp/p2/renders/*.png` (local only), `results/p2_negative_print/*.json` |
| `baseline/` | RAW files, external projects | comparison with spektrafilm and Fotufilm; `build/tmp/baseline/` (local only) |

The P0 and P1 sources must be present. The P1 environment has the required packages.

## Commands

Run from the repository root (Git Bash on Windows).

```bash
E=build/tmp/p1
$E/venv/Scripts/python -I scripts/poc/p2_negative_print/render_review_images.py             # checks, 8 images
$E/venv/Scripts/python -I scripts/poc/p2_negative_print/render_review_images.py --broad     # plain and film, 18 files by subject
$E/venv/Scripts/python -I scripts/poc/p2_negative_print/render_review_images.py --variants  # plain and every entry of VARIANTS
```

The first run builds the u'v' table (about 5 min). The print tables come from the C++ library of P7 (`scripts/poc/p7_spectral_acceleration/`), in memory. The first run also compiles the kernels and caches them in `__pycache__/`. Change the options in `VARIANTS` of `render_review_images.py`.

## Baseline comparison

The scripts in `baseline/` call the external projects and do not contain their code. They expect these
local items under `build/tmp/baseline/`, and they have absolute paths of this machine:

| Item | Source |
| --- | --- |
| `src_spektrafilm/repo` | `git clone` of spektrafilm at `3bb2c2d2`; `venv_spektra`: Python 3.13 with its core packages |
| WSL distro `ff24` | Ubuntu 24.04 base; `setup_ff24.sh` unpacks the Fotufilm v1.14.1 Linux release and adds its packages |
| `signature_edits/raw` | portrait RAW files from <https://www.signatureedits.com/free-raw-photos/> (their free RAW license; never committed) |

Order of the runs:

1. `dump_inputs.py`, `dump_portraits.py` (P1 environment): common linear AP1 inputs.
2. `render_spektrafilm.py`, `render_spektrafilm_nocouplers.py` (`venv_spektra`); `run_fotufilm.sh` (in `ff24`).
3. `grey_ramp_spektrafilm.py` (`venv_spektra`), then `grey_compare.py` (P1 environment).
4. `match_probe.py`, `gap_analysis.py`, `gain_sweep.py`, `compare_portraits.py` (P1 environment).
5. `import_cine_profiles.py <spectral_film_lut/src/spectral_film_lut>` writes the cine profiles. Then `render_spektrafilm_cine.py`, `grey_ramp_spektrafilm_cine.py` (`venv_spektra`), `run_fotufilm_cine.sh` (in `ff24`, with `FILES`), `darkroom_probe.py`, `cine_grey_check.py`, `cine_ramp_diagnosis.py`, `stock_probe.py <names>`, `light_probe.py` (P1 environment).
6. `night_sheet.py <folder>`, `night_probe.py <folder> <names>` (P1 environment): night photos with each product light.
