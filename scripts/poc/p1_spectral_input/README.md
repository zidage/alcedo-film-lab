# P1: spectral input

Scripts of step P1 ([report](../../../docs/exploration/p1_spectral_input.md)). They compare
spectral reconstructions from linear AP1 to scene radiance by the Portra 400 layer exposure and
the developed negative density that they give, on held-out measured reflectances, light
probes, a synthetic camera stage, and real RAW files. RGC is out of scope of this step (README
U13).

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | `build/tmp/p1/sources/`, `results/p1_spectral_input/source_manifest.json` |
| `spectral_datasets.py` | rawtoaces-data, Gutierrez et al., ISSA, USGS splib07, CIE FL/LED/HP tables, camera sensitivities | library: reflectances and light sources on the 1 nm grid |
| `spectral_reconstruction.py` | the P0 evaluator, the reflectances | library: colorimetry (AP1, E_ref), five reconstruction candidates |
| `run_p1_checks.py` | the libraries | `results/p1_spectral_input/*.json` (sections A to K), `build/tmp/p1/eval/*.npz` |
| `run_p1_raw_photos.py` | a RAW library (default: the Alcedo Studio test library) | `results/p1_spectral_input/raw_photos.json` |
| `run_p1_camera_free.py` | the libraries, the RAW library | `results/p1_spectral_input/camera_free/*.json`: combined candidate, reference from the white, held-out makers, near-black rule, RAW with the rule, population checks |
| `plot_p1_figures.py` | results, eval arrays | `results/p1_spectral_input/plots/*.png` (local only), `results/p1_spectral_input/skin_band_error.json` |

The P0 sources must be present (`build/tmp/p0/sources/`, see the
[P0 commands](../p0_data_and_reference/README.md#commands)).

## Commands

Run from the repository root (Git Bash on Windows).

```bash
E=build/tmp/p1
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p1_spectral_input/requirements.txt

$E/venv/Scripts/python -I scripts/poc/p1_spectral_input/fetch_sources.py
$E/venv/Scripts/python -I scripts/poc/p1_spectral_input/run_p1_checks.py      # all sections; or e.g. "B F" for some
$E/venv/Scripts/python -I scripts/poc/p1_spectral_input/run_p1_raw_photos.py  # optional: library path ("-" = default), file count
$E/venv/Scripts/python -I scripts/poc/p1_spectral_input/run_p1_camera_free.py   # all sections; or e.g. "A F"
$E/venv/Scripts/python -I scripts/poc/p1_spectral_input/plot_p1_figures.py
```

`fetch_sources.py` stops with an error when a SHA-256 hash differs from `sources.json`.

## Candidates

All candidates are homogeneous of degree 1: the spectral shape depends on the chromaticity only.
The module docstring of `spectral_reconstruction.py` gives the definitions.

| Name | Method | Linear in AP1 | Domain |
| --- | --- | --- | --- |
| `mallett_yuksel_rec709` | Mallett and Yuksel 2019, re-derived for Rec. 709 primaries and the E_ref white | yes | Rec. 709 triangle (else negative radiance) |
| `jakob_hanika_sigmoid` | Jakob and Hanika 2019 sigmoid polynomial; pbrt-v4 normalization 2 max(rgb) | no | sigmoid gamut at max(rgb) = 0.5 |
| `measured_prior_linear` | minimum-norm estimate under the second-moment matrix of measured reflectances | yes | where the estimate is non-negative |
| `measured_prior_nonnegative` | the same objective with rho >= 0 (quadratic program) | no | the spectral-locus cone |
| `measured_prior_local` | second-moment matrix of the training spectra nearest in u'v' (Gaussian weights, sigma 0.01), blended 5 % with the global matrix | no | where the estimate is non-negative |

Two more candidates are in `run_p1_camera_free.py`: `measured_prior_local_nonnegative` (local
matrix, rho >= 0, rule `spectral_locus_projection`) and `measured_prior_local_camera_population`
(also models the IDT error of a camera population; no camera identity at run time).

The measured priors are trained by leaving the test dataset out (section B) or on one half of
each dataset (section K). The prior matrices are made at run time from the downloaded data and
are not committed.

## Run time (development machine, CPU)

Section B about 12 min, G about 26 min, J about 24 min, K about 3 min, the other sections
less than 4 min each. `run_p1_raw_photos.py` takes about 50 to 85 s per file (44 files, about
50 min); the exact QP of `measured_prior_nonnegative` takes about 13 ms per real pixel, so the
reconstruction comparison uses 2,000 random pixels per file (`SAMPLE_PIXELS`). The domain
statistics use every pixel.
