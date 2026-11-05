# P13: spectral input and the complete RAW white

Date: 2026-11-04 (America/Chicago). This report covers a separate CPU prototype.
The current viewer defaults and the product implementation are not changed.

## 1. Question and result summary

Can the existing RAW white and a scene-light constraint improve Lab Scan input,
without changing the film data, development, scanner numbers or output transform?

The implementation compares seven input cases. The complete estimated RAW white
is used to construct smooth, LED and fluorescent light families. Two cases also
solve for a non-negative spectrum that reproduces the input under a defined
colourimetric white-adaptation model.

The checks and the 3,097-sample hue sweep pass. All 280 photo scan renders
complete with no failed case. The complete photo set is recorded in
`build/tmp/p13/measurements.json`. Section 6 records the completed run.
User review of the night photo: Portra 400, balance0, both smooth cases look close
to the wanted result. This is a user judgement on that image, not a new default
selection or proof that the actual lamp spectrum was recovered.

## 2. Inputs and provenance

Current requirements: ROADMAP section 2, dated 2026-11-04. Stock character stays
at 1. The comparison does not use the rejected stock-specific scan correction,
an added film matrix, a hue warp, or a fit to chart output colours.

Four negatives: Kodak 5219, 5207, Portra 400 and Gold 200. The profiles and the
existing spectral model keep their provenance. The scanner is the current
generic Lab Scan for each medium, reading `print2383`, encoding `adx16`, and
OpenDRT with its native grey. The input grade is the current default: exposure
+1.5 EV, contrast +15, saturation 1.3. All image-plane film steps stay in the
existing implementation. Scene flare is zero, as required by this prototype.

The five RAW files are:

- `signature_edits/se357.cr2`: daylight dune and blue sky.
- `film_emulation/5253219691.rw2`: night street under mixed lamps.
- `D:/素材/照片/2026.6香格里拉/RAW/P2636154.RW2`: forest.
- `signature_edits/se188.nef`: outdoor portrait.
- `signature_edits/se274.dng`: stage portrait.

Paths under `signature_edits` and `film_emulation` are relative to
`D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/`.
No photos or derived images are stored outside `build/tmp/`.

The P1 spectral priors are read from the existing 192x192 caches. Their source
precision is float32. P13 converts them to float64 without changing their
resolution. Foliage is off, as in the current viewer default. The same measured
prior is used for the full-white and constrained cases.

Existing source records, retrieved on 2026-10-29:

| Source | Edition and licence | Use |
| --- | --- | --- |
| [CIE LED table](https://files.cie.co.at/Publications-datasets/CIE_illum_LEDs.csv) | CIE 015:2018, CC BY-SA 4.0 | LED-B3 family, 380--780 nm at 5 nm, linear interpolation and zero outside the published range, as in P1 |
| [CIE fluorescent table](https://files.cie.co.at/Publications-datasets/CIE_illum_FLs.csv) | CIE 015:2018, CC BY-SA 4.0 | FL11 family, same resampling rule |
| [rawtoaces training spectra](https://raw.githubusercontent.com/AcademySoftwareFoundation/rawtoaces-data/e9b8503cf8a0641f40e5345d9757bde60c15f423/data/training/training_spectral.json) | commit e9b8503c, Apache-2.0 | known-spectrum forward check; no fit to chart colour output |
| P0 CIE XYZ and daylight tables | licences in THIRD_PARTY_NOTICES.md and P0 source records | integration and smooth light family |

No source was downloaded for P13. Full SHA-256 values are in
`build/tmp/p13/sources/local_source_hashes.json` and
`build/tmp/p13/sources/reused_source_provenance.json`. The latter verifies the
three P1 source hashes against the existing provenance. The prior training
datasets and material data retain the notices in THIRD_PARTY_NOTICES.md.
Project-authored P13 code is GPL-3.0-only. No new external code is copied.

## 3. Method

### 3.1 Preserve the estimated white

The existing `as_shot_light` convention is retained: solve the camera matrix
against inverse white-balance multipliers and normalize XYZ to Y=1. P13 keeps
this full XYZ. The baseline reduces it to CCT and constructs the existing
daylight/Planckian blend. The complete white is a camera metadata estimate,
not a measurement of the actual illuminant. The matrix convention is not
independently calibrated by this experiment.

For each candidate light family, multiply its source spectrum by
`exp(c0+c1*x+c2*x*x)`, where `x=(wavelength_nm-560)/100`. Solve the three
coefficients to reproduce the complete estimated XYZ white at Y=1. The
coefficients are inferred spectral parameters. No film response enters this
fit. The LED and fluorescent spectra are constructed families, not records
of the lamps in the photos. Source wavelengths with zero energy stay zero.

### 3.2 Seven input cases

| Case | Scene spectrum | Spectral reconstruction |
| --- | --- | --- |
| Current light | existing CCT spectrum | existing light-like prior |
| Current measured | existing CCT spectrum | existing measured prior |
| Full white / smooth | smooth source fitted to full white | measured prior, then relight |
| Full white / LED | LED-B3 fitted to full white | measured prior, then relight |
| Full white / fluorescent | FL11 fitted to full white | measured prior, then relight |
| Constrained / smooth | smooth source fitted to full white | relative-entropy projection under that light |
| Constrained / LED | LED-B3 fitted to full white | same constrained reconstruction |

The same spectrum is used for all stocks for a given photo and case.
The current measured case isolates the complete-white change from the separate
light-like versus measured prior choice.

### 3.3 Constrained reconstruction

Let `t` be XYZ of the graded AP1 input, divided by its Y. Let `W` contain the
existing projected XYZ integration weights. Let `E` be the selected light,
with Y=1. The input white-adaptation model is Bradford from the white of E
to the ACES reference white. Let `A` be this adaptation and `rho0` the existing
measured-prior shape at the input chromaticity.

Start from `L0 = E * (rho0 + epsilon)`, with `epsilon=1e-5`. This explicit
inferred prior term gives support wherever E is positive. It is not measured
reflectance or a numerical replacement applied after a failed solve.

Solve the convex problem, on the complete 1 nm grid:

```text
minimize sum_j [L_j * log(L_j/L0_j) - L_j + L0_j]
subject to W L = inverse(A) t, and L >= 0
```

Its positive solution has the form `L = L0 * exp(B.T * lambda)`, where B is W
with its rows scaled for the numerical solve. Newton steps with a line search
solve the three multipliers. Failed, infeasible or non-finite results stop that
case and are recorded as failures. No replacement render is used.

The normalizing Y is restored before film-layer integration. Exposure scale
therefore stays separate from spectral shape. No upper bound of 1 is imposed
on the Y-normalized relative reflectance. The spectra describe a virtual
graded scene. This is not a reconstruction of unique original scene spectra.
Bradford on XYZ is an explicit colourimetric approximation; it does not invert
LibRaw's camera-channel white balance exactly.

### 3.4 Preserve development and scan

Full-white relight cases replace only the instance's scene spectrum and layer
exposure table. The constrained cases stream radiance in batches, integrate it
with each stock's existing layer sensitivity weights, and inject those exposures
at the entry of the unchanged negative image function. All spatial operations,
characteristic curves, dye formation, scan density tables and OpenDRT then run
through their current implementation. An explicit baseline comparison checks
this injection.

Two scan timings are shown. `balance0` uses the stock balance with timing 0,
so the scene-light response remains. `balance1` uses the same current scan rule
with timing 1. Generic scales and numbers are unchanged; their pivot and offset
are evaluated for each scene spectrum. Neither comparison applies the U97
Academy neutral-axis replacement. This is an input experiment, not a comparison
against historical U97 renders.

The existing input spectral-locus projection and Y<=0 rule remain. Their counts
are recorded. The constrained solve adds no projection after inverse adaptation;
an infeasible target is reported as an error.

## 4. Criteria declared before execution

| Behaviour | Comparison and tolerance |
| --- | --- |
| Same-white light construction | Maximum absolute XYZ error <= 1e-8 at Y=1 |
| Constrained spectrum reproduces target | Maximum absolute XYZ error / maximum absolute target component <= 1e-8 |
| Valid radiance | Finite and non-negative; no NaN or infinity replacement |
| Exposure scaling | Multiplying target and prior by 3.25 multiplies recovered radiance by 3.25, relative error <= 1e-9 |
| Unchanged film stages | Injected baseline exposure versus current scan display code, maximum absolute difference <= 1e-6 |
| Streamed baseline integral | Existing measured table versus streamed measured spectrum integral, relative error <= 2e-6 |

CAM16-UCS distances and colourfulness ratios describe the rendered changes.
They are not acceptance targets. The hue-sweep analysis also subtracts each
stock's own neutral a'b' at 0 EV before comparing chromatic responses. This
separates a change of the grey axis from a change of the surrounding colours.
A stock cast is a property, not a numerical fault.
The photo colourfulness ratio is the mean per-pixel ratio of CAM16-UCS M'
radius to the no-film M' radius, for pixels with no-film M'>6. The review
labels abbreviate this as `M ratio`; it is not the uncompressed CAM16 M ratio.

## 5. Execution and machine

Code and complete commands: `scripts/poc/p13_spectral_input/README.md`.
The existing P6 environment is used with `python -I`. The working grid is
360--840 nm at 1 nm, with the existing projected integration weights. Relative
radiometric spectra use a light white Y=1. The film evaluator converts these
to its existing luminous exposure and erg/cm^2 units before its dimensionless
layer exposure. The host spectral solve and integral use float64; downstream
image kernels use their existing float32 inputs. No wavelength, table or
numerical resolution is reduced.

The review long edge is fixed at 640 pixels before execution. Only the review
RAW decode uses this image size. A batch of 512 full-grid float64 spectra has
1,970,176 bytes for one spectral array; temporary arrays also exist. No complete
spectral image is allocated. The existing scene sweep has 3,097 samples; exact
homogeneity reduces the spectral solves to 155 unit-exposure inputs without
reducing the sweep or the wavelength grid.

Machine: the Windows development machine of AGENTS.md, Intel i7-12700H,
31.8 GB RAM. BLAS, OpenMP and Numba are requested to use one CPU thread.
No GPU job is used. Peak Windows working set is measured by
`GetProcessMemoryInfo`. CUDA, Metal and OpenCL execution are unverified.

Runs:

- `build/tmp/p13_pilot/`: one night RAW to verify the complete review path.
- `build/tmp/p13_sweep/`: the full scene sweep, with the night RAW white.
- `build/tmp/p13/`: five-photo, four-stock, seven-input, two-timing review.
- Logs: `build/tmp/spectral_input_audit/p13_pilot.log`, `p13_sweep.log`,
  `p13_study.log`, and `p13_summary.log`.

## 6. Results

The synthetic consistency checks passed: maximum constrained XYZ error
2.303e-9; forward-adapted input XYZ error 2.249e-9; exposure scaling error
4.963e-16. Injected baseline display code differs by at most 9.433e-8;
the streamed baseline integral differs by at most 3.353e-15 relative.

All seven cases complete on the hue sweep. For Portra 400 versus Gold 200,
the following are medians. Full UCS uses coloured sweep samples from -4 to
+4 EV. The neutral-subtracted result uses a'b' at 0 EV, so these columns
measure different things and are not interchangeable.

| Input | Timing | Full UCS distance | Neutral-subtracted a'b' distance |
| --- | --- | ---: | ---: |
| Current light | 0 | 1.743 | 1.606 |
| Current measured | 0 | 1.692 | 1.673 |
| Full white / smooth | 0 | 1.707 | 1.063 |
| Constrained / smooth | 0 | 1.704 | 1.076 |
| Full white / LED | 0 | 2.394 | 1.517 |
| Full white / fluorescent | 0 | 3.456 | 3.036 |
| Current measured | 1 | 1.715 | 1.412 |
| Full white / smooth | 1 | 1.653 | 1.510 |
| Constrained / smooth | 1 | 1.646 | 1.500 |

This sweep does not show a general increase in stock separation from the smooth
cases. A larger full distance can also contain a grey-axis change. The constrained
smooth and full-white smooth results are close on this sweep. LED and fluorescent
are useful independent light-family comparisons, not identified actual lamps.

### Five-photo run

The full run took 393.86 seconds. Peak Windows working set was 1,629,171,712
bytes (1,553.70 MiB). The ten full-photo constrained solves each took 17.68 to
22.24 seconds. They required at most five Newton iterations per batch. Maximum
normalized XYZ error was 9.999893e-9, below the predeclared 1e-8 tolerance.
No photo input was moved by the existing spectral-locus projection. There were
no failed cases. This records CPU review performance, not product latency.

Portra 400 versus Gold 200, median CAM16-UCS distance over all photo pixels:

| Photo | Timing | Current measured | Full white / smooth | Constrained / smooth |
| --- | --- | ---: | ---: | ---: |
| Day dune | 0 | 2.122 | 2.395 | 2.401 |
| Night street | 0 | 0.962 | 1.613 | 1.613 |
| Forest | 0 | 1.561 | 1.693 | 1.692 |
| Outdoor portrait | 0 | 1.202 | 1.510 | 1.519 |
| Stage portrait | 0 | 2.891 | 1.780 | 1.775 |
| Night street | 1 | 1.155 | 1.778 | 1.783 |
| Outdoor portrait | 1 | 1.465 | 1.441 | 1.426 |

The full table, with both timings for each photo and both stock pairs, is in
`build/tmp/p13/summary.json`. These distances include the stock casts and
tonal differences. They do not isolate material character from the grey axis.
The smooth cases increase this distance in some scenes and decrease it in
others. They are not a general stock-separation multiplier.

Visual observations from the labelled sheets, not reference-match claims:

- Portra 400, night, timing 0: the smooth cases retain a more yellow-green
  scene response than the CCT-only measured case. The user prefers both smooth
  cases on this image.
- Portra 400, dune: the full-white smooth and constrained smooth columns are
  close. The sand is redder and the sky more violet than the CCT-only measured
  case, consistent with the changed estimated scene white.
- Portra 400, outdoor portrait: the smooth cases have a more pink-purple
  scene response. The two smooth columns remain close. User review is open.
- Portra 400, stage portrait: the smooth cases move the blue-purple scene
  toward cyan-green. This is a property of the input-light choice. The scene
  contains mixed lighting, which the one-light model does not separate.
- 5219, night: the smooth cases show a cyan-green response; the CCT-only
  measured case is bluer. No stock curve or scanner colour fit was changed.

The simpler complete-white change accounts for most of the visible difference
in this set. The added constrained solve passes its input consistency checks,
but these images do not show a distinct additional appearance benefit.

Review entry points:

- `build/tmp/p13/smooth_review.html`: focused Portra 400 comparisons, with links
  to the same three input cases on all four stocks.
- `build/tmp/p13/review.html`: all seven input cases and both timings.
- `build/tmp/p13_sweep/hue_sweep.png`: hue strips for all four stocks.

The focused photo columns are: no film, current CCT/measured, full-white smooth,
and constrained smooth. Focused sheets copy the original rendered review pixels
at their existing size. They do not resize or remeasure the photos.

### User review

The user viewed the night Portra 400 results and said that smooth looked right.
On clarification, the user selected both `Full white / smooth` and
`Constrained / smooth`, specifically with `balance0`. The observation supports
continued review of these two cases. The user has not selected a global default.

## 7. Recommendation and open items

Keep the two smooth cases as the focused review candidates. The simpler
full-white smooth case is the first candidate for a viewer option if the broad
photo review confirms the result. The constrained case remains an independent
comparison because its input consistency is defined and checked. The current
evidence does not establish that it has a better appearance.

Open items:

- User review of day, forest, skin and the other stocks.
- A measured illuminant or a calibrated RAW-white estimate; this experiment has
  neither for the review scenes.
- Independent spectral truth for image pixels and held-out validation. The
  synthetic check proves forward consistency, not reconstruction accuracy.
- A sensor-specific input model if actual camera spectral sensitivities become
  available within the product design. A 3x3 camera matrix alone is insufficient.
- Emission versus reflection and local mixed illumination remain unmodelled.
- Product UI, C++ resource generation and all three GPU backends remain unverified.

No existing viewer default, stock data, shared implementation, or branch is
changed by P13. No commit or push is made.
