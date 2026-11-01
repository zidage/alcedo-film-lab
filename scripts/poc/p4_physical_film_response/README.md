# P4: physical colour and film response

Scripts of step P4 ([report](../../../docs/exploration/p4_physical_film_response.md)). This is a CPU review tool, not the product path. The rules are in `film_preview.py` (P2) and `aces_scan.py` (P3), behind options whose defaults keep the earlier results. `P4_PHYSICAL` in `film_preview.py` holds the options of this step.

| Script | Input | Output |
| --- | --- | --- |
| `import_dyes_and_mtf.py` | a local clone of spectral_film_lut at `bcbcfc68` | isolated dye curves and modulation transfer curves in `profiles/`. Run it after `import_cine_profiles.py` |
| `trace_colour_error.py` | the libraries, no photo | `results/p4_physical_film_response/colour_trace.json` |
| `check_light_spectra.py` | the libraries, the P1 reflectance sets | `results/p4_physical_film_response/light_spectra.json` |
| `compare_dye_models.py` | the profiles | `results/p4_physical_film_response/dye_models.json` |
| `fit_mtf.py` | the profiles | `results/p4_physical_film_response/mtf_fit.json` |
| `check_film_response.py` | the libraries, no photo | `results/p4_physical_film_response/film_response.json` |
| `render_p4_review.py` | AP1 arrays of P3 (`build/tmp/p3/input/`) | `build/tmp/p4/review_<set>/*.jpg` with a label on every panel (local only), `results/p4_physical_film_response/sweep_<set>.json` |
| `render_light_and_detail_review.py` | RAW files of `build/tmp/baseline/signature_edits/raw/` | `build/tmp/p4/review_light/`, `build/tmp/p4/review_detail/` (local only), `results/p4_physical_film_response/estimated_light.json` |
| `render_night_review.py` | a directory of RAW files, first argument | `build/tmp/p4/review_night/*.jpg` with a label on every panel (local only), `results/p4_physical_film_response/night_review.json` |
| `render_spektrafilm_night.py` | the arrays of `render_night_review.py --inputs-only`; the local spektrafilm clone and its environment (external comparison only, ROADMAP U18) | `build/tmp/baseline/out_spektrafilm_night/*.png` (local only) |
| `render_daylight_review.py` | a directory of RAW files, first argument | `build/tmp/p4/review_daylight/*.jpg` with a label on every panel (local only), `results/p4_physical_film_response/daylight_review.json` |
| `render_artificial_light_review.py` | a directory of RAW files, first argument | `build/tmp/p4/review_artificial/*.jpg` with a label on every panel (local only), `results/p4_physical_film_response/artificial_light_review.json` |

The P0, P1, P2, and P3 sources and tables must be present.

## Commands

Run from the repository root (Git Bash on Windows). The environment of P3 has all the packages (`requirements.txt` here lists the same ones).

```bash
P=build/tmp/p3/venv/Scripts/python
D=scripts/poc/p4_physical_film_response
python $D/import_dyes_and_mtf.py build/tmp/baseline/src_sfl/repo/src/spectral_film_lut
$P -I $D/check_light_spectra.py
$P -I $D/fit_mtf.py
$P -I $D/check_film_response.py
$P -I $D/compare_dye_models.py
$P -I $D/trace_colour_error.py                  # about 5 min
$P -I scripts/poc/p3_scan_and_scene/check_scan_path.py
$P -I scripts/poc/p2_negative_print/check_fast_kernels.py
$P -I $D/render_p4_review.py --set w1           # or names of files
$P -I $D/render_p4_review.py --set w2 se224 canon_r se188 fuji_xt5 se167 hasselblad_x1dii
$P -I $D/render_p4_review.py --set w3 se224 canon_r se188 fuji_xt5 se167 hasselblad_x1dii
$P -I $D/render_p4_review.py --set p4           # 37 landscape files, 6 portraits
$P -I $D/render_light_and_detail_review.py se224 se188 se167 se146
N=D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/night
$P -I $D/render_night_review.py $N --inputs-only
build/tmp/baseline/venv_spektra/Scripts/python -I $D/render_spektrafilm_night.py
$P -I $D/render_night_review.py $N
$P -I $D/render_artificial_light_review.py D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/artificial_lights
$P -I $D/render_daylight_review.py D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/daylight
```
