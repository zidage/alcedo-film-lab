# P0: data and host spectral reference

Scripts of step P0 ([report](../../../docs/exploration/p0_data_and_reference.md)). They download and
verify the sources, read the Portra 400 and Endura Premier curves from the PDF vector paths,
evaluate the film-to-print chain in float64, and write the checks and the integration
convergence study.

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | `build/tmp/p0/sources/`, `results/p0_data_and_reference/source_manifest.json` |
| `digitize_kodak_charts.py` | the two Kodak PDFs | `profiles/kodak_portra_400.json`, `profiles/kodak_endura_premier.json`, `results/p0_data_and_reference/digitization.json`, `build/tmp/p0/digitized_paths.json` |
| `film_spectral_reference.py` | profiles, CIE tables, Status table | library: `ReferenceModel` (one function per stage) |
| `run_p0_checks.py` | the library | `checks.json`, `neutral_ramp.json`, `negative_dye_basis.json`, `uncertainty.json`, `spectral_film_lut_variants.json`, `integration_convergence.json` |
| `plot_p0_figures.py` | PDFs, profiles, results | `results/p0_data_and_reference/plots/*.png` (local only) |
| `compare_spectral_film_lut.py` | profiles, colormath tables, spectral_film_lut files at commit `bcbcfc68` (downloaded, hashes checked, read as data) | `results/p0_data_and_reference/comparison_spectral_film_lut.json` |

## Commands

Run from the repository root (Git Bash on Windows). The scripts use `python -I`; they add their
own directory to `sys.path` where they import the library.

```bash
E=build/tmp/p0
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p0_data_and_reference/requirements.txt

$E/venv/Scripts/python -I scripts/poc/p0_data_and_reference/fetch_sources.py
$E/venv/Scripts/python -I scripts/poc/p0_data_and_reference/digitize_kodak_charts.py
$E/venv/Scripts/python -I scripts/poc/p0_data_and_reference/run_p0_checks.py      # about 50 s
$E/venv/Scripts/python -I scripts/poc/p0_data_and_reference/plot_p0_figures.py
$E/venv/Scripts/python -I scripts/poc/p0_data_and_reference/compare_spectral_film_lut.py
```

`fetch_sources.py` stops with an error when a SHA-256 hash differs from `sources.json`. A new
revision of a data sheet needs a new source check and new hashes; the script does not accept a
different file.

## Model functions and explicit rules

`film_spectral_reference.py` documents each stage in its module docstring. The values that the
sources do not give are in `ModelOptions` and in the report, section 5. Values outside a
published domain follow a named rule:

- `sensitivity_outside_published_domain`: zero.
- `characteristic_curve_below_toe`: the first value of the curve. Above the last published
  point, the function raises an error.
- `status_table_interpolation`: linear between the 10 nm values, zero outside 340-830 nm.
- Negative D-min and paper dye spectra outside 400-700 nm: the value at the nearest end
  (`hold`); the uncertainty study also uses `linear`.

## Methods reused from spectral_film_lut

`ModelOptions` can select three methods ported from spectral_film_lut (MIT, commit `bcbcfc68`;
notice in [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md)):
`sensitivity_outside="log_linear"`, `negative_density_outside="gaussian_tail"` and
`paper_dye_outside="gaussian_tail"`, and `negative_dye_basis="band_split"`. The P0 defaults
stay unchanged; `spectral_film_lut_variants.json` compares them.

## Integration rules

The fixed spectral functions are reduced to weights on the working grid (`SpectralGrid.weights`).
The trapezoid weights are restricted to the published support of each function, so a curve that
the data sheet cuts at its end is not changed into a ramp between two nodes. Rule `point` samples
the fixed function at the nodes; rule `projected` projects it on the hat basis of the nodes. The
reference is the 0.1 nm grid.
