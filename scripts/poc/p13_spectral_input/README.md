# P13: spectral input and the complete RAW white

This prototype compares the current Lab Scan input with three explicit changes:
the complete estimated RAW white; smooth, LED-B3 and FL11 spectral families at
that white; and a non-negative spectral reconstruction constrained by the scene
light and an explicit colourimetric white-adaptation model.

The stock character control stays at 1. Scan numbers, curves, development, and
the display transform are unchanged. The experiment does not fit a colour chart
or the output of a stock. Project-authored code is GPL-3.0-only. Existing material
profiles, CIE tables and P1 caches retain their source provenance and licences.

Use the existing P6 environment. From the repository root:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
$env:NUMBA_NUM_THREADS='1'
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p13_spectral_input/run_study.py
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p13_spectral_input/analyze_sweep.py D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/film_emulation/5253219691.rw2
& build/tmp/p6/venv/Scripts/python.exe -I scripts/poc/p13_spectral_input/summarize.py build/tmp/p13 --sweep build/tmp/p13_sweep/sweep.json
```

The default review set contains a dune, a night street, a forest, an outdoor
portrait and a stage portrait. Review RAW decoding uses 640 pixels on the long
edge, fixed before execution. The wavelength grid remains 360--840 nm at 1 nm;
the existing 192x192 prior table keeps its resolution. The host spectral solve
and integrals use float64. The unchanged spatial film kernels use float32 input.
This is a CPU review experiment, with no claim about GPU implementation.

Outputs, photos, logs and source hashes stay under `build/tmp/p13/`. The report
is `docs/exploration/p13_spectral_input.md`. Run `--help` for a subset of the
default files, case choices, and the output directory. A failed case is reported
as failed and has no substitute render.

Checks declared before execution:

- Matched light XYZ at Y=1: maximum absolute error <= 1e-8.
- Constrained spectra: maximum XYZ error divided by maximum absolute target XYZ
  <= 1e-8; finite, non-negative radiance, no NaN replacement.
- Recovered radiance is re-adapted to the input white for the synthetic checks.
  Scaling by exposure must agree within 1e-9 relative error.
- Injection of baseline layer exposure into the unchanged film stages must
  reproduce display code within 1e-6. Streamed baseline exposure must agree with
  the existing table exposure within 2e-6 relative error.

The spectral prior receives an explicit positive share of 1e-5 before the
relative-entropy projection. The three illuminant tilt coefficients are inferred
from the complete estimated RAW white. These are constructed spectral families,
not measurements of the photographed lamps. The Bradford input model does not
invert LibRaw's camera-native white balance exactly. With graded AP1, the output
is a spectral interpretation of the graded virtual scene. The reconstruction
does not identify a unique original spectrum.
