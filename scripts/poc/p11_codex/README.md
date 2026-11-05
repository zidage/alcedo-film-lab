# P11: print viewing and local stage response

This prototype tests a missing viewing operation. It preserves CAM16 J, M and h
from a spectral reflection print to a display. It does not fit a stock or a chart.
The source and display conditions are explicit scenarios. They are not measured
conditions of the user's monitor or of a physical print.

Code written for P11 is GPL-3.0-only. Existing lab modules and material profiles
retain their licenses and provenance. No external code or new material curves
are copied. The prototype uses the lab CAM16 module.

Use the existing P6 environment (Python, NumPy, SciPy, Pillow, rawpy, matplotlib
and all P6 dependencies). Run from the repository root, in PowerShell:

```powershell
$python = 'D:/Projects/alcedo-film-lab/build/tmp/p6/venv/Scripts/python.exe'
$raw = 'D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw'
& $python -I scripts/poc/p11_codex/run_study.py "$raw/signature_edits/se357.cr2" "$raw/signature_edits/se222.arw" "$raw/film_emulation/5253219691.rw2" "$raw/signature_edits/se188.nef" "$raw/signature_edits/se274.dng"
& $python -I scripts/poc/p11_codex/summarize.py
```

Outputs stay in `build/tmp/p11/`. Each image panel has a stock, method and
colourfulness ratio. Whole sheets and separate rows per stock are supplied.
`measurements.json` stores stage derivatives, settings, photo metrics and counts
outside the output gamut. `paper_slopes.json` stores the paper slopes at grey.
`viewing_comparison.png` is a plot; `review.html` displays it and selected sheets.
Runs preserve earlier photo entries in the measurement file.

Review images use 640 pixels on the long edge, set before execution. Tables and
spectral grids keep their existing sizes. No GPU operation is used. The float64
print table evaluator is used after the existing float32 image negative kernels.
This is not a new float64 reference for the complete spatial pipeline.

Checks: the supplied CAM16 example and inverse test; J/M preservation before
gamut mapping within 1e-8; baseline print agreement with compiled rendering
within 1e-4 display code on the sweep. Stage differences at epsilon 0.001 and
0.0005 log10 AP1 are reported, without a pass claim.

The source abstract and API documentation were read with web tools. Direct
urllib retrieval of the Colour API page returned HTTP 403. The source folder
stores the CIE web page and a Colour retrieval note. Provenance includes SHA-256 of these artifacts and
the local implementation dependencies. See the report for the limitations.
