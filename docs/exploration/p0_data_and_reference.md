# P0: Data and host spectral reference (Portra 400 and Endura Premier)

**Design:** [ROADMAP section 8](../../ROADMAP.md#8-route-from-poc-to-mvp), step P0, and
[section 4](../../ROADMAP.md#4-proposed-image-pipeline).
**Date:** 2026-10-29.
**Status:** measurements done. O1 is decided. User review of the inferred fields, the tolerances,
and open items O2 to O6 is open. Section 10 compares P0 with spectral_film_lut and measures its
methods in the P0 evaluator (added after the first measurements).

> **Plots are local only.** The overlay plots contain renders of the Kodak charts. All plots are
> under `results/p0_data_and_reference/plots/` (`*.png` is in `.gitignore`). To make them again,
> run the commands of the [script README](../../scripts/poc/p0_data_and_reference/README.md#commands).

## 1. Question

Can one negative and print pair be specified from traceable sources? Step P0 does this work:

1. Select one negative and one print material with traceable data, and record the sources with
   hashes.
2. Digitize the curves and record what each axis means (units, density status, criterion).
3. Implement a host spectral evaluator (float64) from camera exposure to the viewed print.
4. Check the data against itself: neutral exposure and density checks.
5. Measure the convergence of the dense wavelength integration.
6. List each field that the sources do not give, and its effect.

## 2. Result summary

- **The curves are traceable without manual tracing.** All six charts of KODAK PORTRA 400
  (E-4050, page 4) and KODAK ENDURA Premier Paper (E-4070, pages 4 and 5) are PDF vector
  drawings. Each curve is one stroked path. The script maps it with the axis frame. All tick marks
  and grid lines map to their labeled values within 0.00074 density or log units and 0.09 nm. The
  1 nm and 0.01 log H grids differ from the dense paths by at most 0.0045 log units. The overlays
  show the digitized curves on the source curves (section 4.1). Kodak 2383 (also named in the
  README) has raster charts; it was not used.
- **The sources do not specify the pair completely.** These fields are not given (section 5):
  - E-4050 gives only the D-min and midscale-neutral spectra. There are no isolated dye spectra.
    A fit with three dyes reproduces the neutral spectrum (RMS 0.0066 density), but the cyan peak
    is not identified: peaks from 680 nm to 780 nm fit within RMS 0.021.
  - **The negative spectral density stops at 700 nm.** With lamp A, 25.8 % of the weight of the
    Endura red-sensitive (cyan-forming) layer is above 700 nm, where the layer has its maximum
    (695 nm). The red print exposure therefore depends on an extrapolation. For a +0.5 Status M
    red step, the red print log exposure is -0.49 to -0.57 when the cyan density continues
    above 700 nm. It is -0.31 when the cyan density falls immediately after 700 nm; this fit is
    also consistent with the data (RMS 0.0078).
  - E-4070 states no exposure light and no criterion density for the spectral sensitivity. There is
    also no paper base spectrum.
  - E-4050 says "Daylight" and gives no CCT.
- **E-4050 is not self-consistent within the predeclared tolerances.** The checks are in
  section 6.
  - The speed point from the spectral-sensitivity chart (D55, CIE 1931 V, 683 lm/W) is lower than
    the characteristic curve: -0.084, -0.123, -0.019 log H (R, G, B). The tolerance is 0.10 (1/3
    stop). Green fails for D50, D55, and D65.
  - The Status M density of the published D-min spectrum is lower than the curve D-min: -0.024,
    -0.025, -0.068. The tolerance is 0.03, so blue fails.
  - The midscale-neutral spectrum matches the curves at -1.26, -1.17, and -1.35 log H, not at
    the "Log H Ref" -1.44. The spread is 0.18 and the tolerance is 0.10.
- **The paper data is consistent.** With the published dye shapes, a Status A neutral print
  (0.1 to 2.0) has C*ab at most 1.11 under D50. The tolerance is 2.0.
- **The chain runs, and the uncalibrated grey scale is almost as neutral as the paper alone.**
  A D55 grey ramp from -3.3 to +0.4 log H goes from the camera to the viewed print with finite
  values at all steps. The printer is balanced on the negative of a midscale grey, so that grey
  prints at Status A 0.75. With this balance, C*ab is at most 3.6 (at L* 8.6). When the paper is
  driven with equal log exposures, C*ab is at most 3.4. Two results show that the grey depends
  on choices that the sources do not fix:
  - A balance on the characteristic curve instead of on the camera path (the speed-point
    difference of section 6) gives C*ab 13.1 at L* 35.
  - A different cyan dye inferred for the negative gives up to 12.3.
- **Two inconsistencies cause most of the uncertainty of the pair.** The first is the 0.1 log H
  disagreement between the two E-4050 charts. The second is the unknown negative density above
  700 nm. The digitization and the integration are much smaller sources of error.
- **The dense reference is converged.** The 0.1 nm reference agrees with a 0.05 nm grid within
  1.8e-5 density and 0.0009 Delta E*ab on the end-to-end ramp. A cut published curve must be
  integrated over its own support. Without that, a cut curve is an O(h) error, and in the first
  run this error was 0.012 log units at 1 nm.
- **Coarse integration (input for P6):**
  - The end-to-end ramp meets 0.1 Delta E*ab at 5 nm with hat-projected weights (0.067), but
    not at 1 nm with point sampling (0.12).
  - Status M of dense negatives needs 1 nm with both rules (3.5e-4 at 1 nm, 1.4e-3 at 2 nm).
  - Dense paper dyes are better with point sampling than with projected weights at 2 to 10 nm.
  - No rule meets all tolerances above 1 nm. Do not select a small band count from these rules
    alone.
- **An independent hand digitization agrees.** The same two data sheets in spectral_film_lut
  agree with the vector extraction to a median of 0.001 to 0.014. Its Status tables change the
  densities by at most 0.0135. Its methods (log-linear sensitivity, Gaussian tails, band-split
  dyes) are ported as options; they change no check of section 6 and the grey ramp by at most
  0.2 C*ab (section 10).
- **Recommendation:** use this pair and the reference evaluator as the base of P1 and P2. Get
  the missing negative data before P2 claims a print response (open item O2). Section 8 has the
  details.

## 3. Inputs and machine

### 3.1 Sources

The full manifest with sizes and hashes is
[`source_manifest.json`](../../results/p0_data_and_reference/source_manifest.json); the expected
hashes are in [`sources.json`](../../scripts/poc/p0_data_and_reference/sources.json). Retrieved
2026-10-29. No source file is committed.

| Source | Edition | SHA-256 | License | Use |
| --- | --- | --- | --- | --- |
| KODAK PROFESSIONAL PORTRA 400 Film, E-4050 | Revised 2-16 | `e83ac677...e97e3a` | manufacturer data; the PDF is not distributed (ROADMAP U10) | page 4: characteristic (Status M), spectral sensitivity, spectral dye density (D-min, midscale neutral) |
| KODAK PROFESSIONAL ENDURA Premier Paper, E-4070 | Revised 12-17 | `94ead00f...7982e` | manufacturer data; the PDF is not distributed (ROADMAP U10) | page 4: characteristic (Status A), spectral sensitivity; page 5: dye spectral density (Y, M, C) |
| CIE 1931 2 degree CMFs, 1 nm | DOI 10.25039/CIE.DS.xvudnb9b | `fa663e35...713c1` | CC BY-SA 4.0 | XYZ, lux-seconds |
| CIE daylight components S0, S1, S2 | CIE 015:2018 | `4056cf7c...8c6be` | CC BY-SA 4.0 | D50, D55 |
| CIE D65, CIE A, 1 nm | ISO/CIE 11664-2 | `e76f210b...32cb`, `61ef23fe...3c1` | CC BY-SA 4.0 | test spectra; printer lamp |
| python-colormath `density_standards.py` | commit `6d3261f9` | `60f4171d...b0dc3` | BSD-3-Clause | Status M and Status A spectral products (secondary copy of ANSI/ISO; section 5, I14) |

### 3.2 Machine and software

Intel Core i7-12700H (Windows 11 10.0.22635), Python 3.13.12, NumPy 2.5.4, SciPy 1.18.1,
matplotlib 3.11.2, PyMuPDF (1.27 series). CPU only, one process. `run_p0_checks.py` takes about
50 s; the convergence study alone takes 15.6 s. No GPU was used.

## 4. Method

### 4.1 Digitization

`digitize_kodak_charts.py` reads the PDF drawing list with PyMuPDF. For each chart:

1. **Axis frame.** The script finds the frame edges near a given approximate frame. It uses the
   median of the stroked segments within 0.6 pt and stops with an error if an edge is missing.
2. **Map check.** The script maps each tick mark and grid line with the frame. Each one must be a
   multiple of the tick step within 0.005 units (0.5 nm on wavelength axes). Measured: at most
   7.4e-4 on the value axes and 0.09 nm on the wavelength axes.
3. **Curves.** The curves are the stroked paths inside the frame with at least 8 segments. The
   expected count is checked: 3, 3, 2, 3, 3, 3. Each path has one subpath. Bezier segments are
   evaluated at 64 points each.
4. **Labels.** The curve data, not the label text, assigns the labels. The Portra B, G, R curves
   and the neutral spectra are ordered by mean density. The Endura R, G, B curves are ordered by
   maximum density. The sensitivity and dye curves are ordered by the wavelength of their
   maximum. The overlays confirm the assignment.
5. **Resampling.** The script interpolates linearly onto 1 nm or 0.01 log H inside the published
   domain. The grid differs from the dense path by at most 0.0045 (Endura magenta sensitivity,
   at its steep edge). No path steps backward in x.

Observations from the paths:

- The Portra characteristic curves are polylines of 37 to 39 straight segments from -3.44 to
  +0.56 log H. There is no shoulder.
- The spectral curves are Bezier paths. Their end points lie on whole wavelengths. The Portra
  domains are 380-520 (yellow-forming), 390-600 (magenta-forming), and 490-680 nm (cyan-forming).
  The Endura domains are 380-510, 420-585, and 530-740 nm.
- Several curves stop at a high value. At 380 nm the Portra yellow-forming layer has log
  sensitivity 1.75 (15 % of its maximum). At 600 nm the magenta-forming layer has 0.75.
- The Endura characteristic curves end at -0.149 log H and fall after their maximum by up to
  0.03 (red: 2.757 at -0.38). The Endura toe falls by up to 0.002 over 0.4 log H.

### 4.2 Quantities and units

| Quantity | Definition in the evaluator |
| --- | --- |
| Spectral exposure | H_e(lambda) in erg/cm^2/nm (radiometric energy). Scene ramps are given in lux-seconds: 683 lm/W and CIE 1931 y-bar; 1 J/m^2 = 1000 erg/cm^2. |
| Layer sensitivity | S_i = 10^(log sensitivity) in cm^2/erg. By the data sheet definition, this is the reciprocal of the exposure that gives the criterion density. No photon conversion is applied. |
| Layer exposure | Q_i = integral H_e S_i d(lambda), dimensionless. Q_i = 1 is the criterion exposure (negative: Status M 0.2 above D-min). |
| Negative development | Status M D_i = C_i(log10 H*_i + log10 Q_i). H*_i is the curve exposure at D-min + 0.2: -2.340, -2.369, -2.551 (R, G, B). |
| Negative spectral density | D(lambda) = D_min(lambda) + sum a_i d_i(lambda). D_min is published; d_i is inferred (I6). The base is in D_min only. |
| Dye amounts a_i | Solved so that Status M(D) - Status M(D_min) = curve density - curve D-min (residual below 1e-6). |
| Print exposure | Q_print_j = k_j integral I_A T_neg S_paper_j d(lambda), T_neg = 10^-D. k_j is the printer balance (I9, I10). |
| Print development | Status A from the Endura curves at log10 Q_print_j. |
| Print spectral density | D_print = D_base (flat, I11) + sum b_j e_j(lambda). e_j are the published dyes with peak 1; b_j are solved for the Status A density. |
| Viewing | R = 10^-D_print (I13); XYZ under D50, Y of the perfect diffuser = 100; CIELAB relative to the perfect diffuser. |
| Status density | -log10( integral Pi T / integral Pi ), with Pi the Status M or A spectral product. |

### 4.3 Integration

The wavelength range is 360-840 nm; the CIE tables are zero above 830 nm. The fixed spectral
functions are defined on a 0.1 nm fine grid and reduced to integration weights: layer
sensitivities, printer lamp times paper sensitivity, Status products, and viewing light times
the CMFs. The variable functions are sampled at the working nodes: scene spectra, dye spectra,
transmission, and reflectance.

- **Support-restricted trapezoid.** A sensitivity is zero outside its published domain, so it
  has a jump at the domain end. The weights are the trapezoid weights over the published support
  only, with half weight at the run ends. In the first run the plain trapezoid over the full
  range was used. That run changed each jump into a ramp between two nodes and gave 0.012 log
  units of error at 1 nm even for the dense reference. The weights fixed this error.
- **Rules.** `point` samples the fixed function at the nodes. `projected` projects the fixed
  function on the hat basis of the nodes and is exact for a variable function that is linear
  between nodes.
- **Reference.** 0.1 nm. Checked against a 0.05 nm fine grid and a 0.05 nm working grid.
- **Tests.**
  - log10 Q for D55, D65, and A.
  - log10 Q for Gaussian sources (FWHM 30 nm and 10 nm, centers 383-703 nm). Only the layers
    with at least 1 % of their largest response count.
  - Status M of 125 negatives (dye amounts 0 to 2).
  - log10 print exposure through the same 125 negatives.
  - Lab of 125 prints (paper dye amounts 0 to 2.4).
  - The end-to-end ramp.
- **Printer balance.** Fixed to the reference value at every step, so the comparison measures
  integration error only.

### 4.4 Tolerances

The tolerances were set in `run_p0_checks.py` before its first run.

| Check | Tolerance | Reason |
| --- | --- | --- |
| One stop doubles each layer exposure | relative 1e-12 | float64 linearity |
| Speed point, sensitivity chart against characteristic chart | 0.10 log H | 1/3 stop |
| Status M of D-min spectrum against curve D-min | 0.03 | densitometer repeatability plus digitization |
| Midscale neutral: spread of the matched log H of R, G, B | 0.10 log H | one exposure for all channels |
| Status A neutral print, C*ab under D50 | 2.0 | near the visual threshold for a grey |
| Film base counted once | 1e-12 | structure |
| Viewing light leaves the print dyes unchanged | 0 (exact) | structure |
| CIE daylight formula D65 against the CIE table | relative 2e-3 | CIE rounding of M1, M2 |
| Integration against the reference | 0.001 density or log H; 0.1 Delta E*ab | one quarter of a densitometer step; below visibility |

## 5. Inferred fields

Each item is a value that the sources do not give. The reference uses the stated choice. The
effects come from `uncertainty.json` and `negative_dye_basis.json`.

| ID | Field | Choice in the reference | Measured effect |
| --- | --- | --- | --- |
| I1 | Spectrum of "Daylight" exposure (E-4050) | CIE D55 by the daylight formula | Speed-point difference (R, G, B), in log H: D50 -0.109, -0.113, +0.040; D55 -0.084, -0.123, -0.019; D65 -0.046, -0.138, -0.108. |
| I2 | Exposure time of the characteristic chart | Same as the sensitivity chart (1/50 s); reciprocity | Not measurable from the sources. |
| I3 | Sensitivity outside the published domain | Zero | Hold the yellow-forming value 380 nm -> 360 nm: blue speed point -0.019 -> -0.025. |
| I4 | Characteristic curve outside its domain | Below the toe: first value. Above the end: error | Ramp limited to +0.4 log H. |
| I5 | Negative D-min spectrum outside 400-700 nm | Hold the end value | Status M against linear extrapolation: at most 5.4e-5. Midscale print log exposure: +0.004 (R), -0.004 (B). Status M has only 0.5 % of its red weight above 700 nm. |
| I6 | Isolated negative dye spectra | 3 asymmetric Gaussians fitted to midscale minus D-min (400-700 nm) | Fit: peaks 449, 543, 709 nm; RMS 0.0066, max 0.032. The cyan long-side width reaches the fit limit (150 nm), so it is not constrained. Cyan peak 660-780 nm: RMS 0.0075-0.044. The cyan step effect on the red print exposure is -0.31 to -0.57, the midscale red printing gamma is 0.40 to 0.65, and the ramp max C*ab is 3.6 to 12.3 (12.3 for the 700 nm peak, whose long-side width falls to the 8 nm limit). |
| I7 | Exposure of the midscale-neutral spectrum | "Log H Ref" -1.44 | The spectrum matches -1.26, -1.17, -1.35 (section 6). |
| I8 | Criterion density of the Endura sensitivity | Not used | The printer balance absorbs it. |
| I9 | Paper exposure light | CIE A | With D55 as lamp, the ramp max C*ab is 3.3 (3.6 with A). |
| I10 | Printer balance | The midscale neutral prints to Status A 0.75 neutral | log10 k = -4.280, -4.398, -4.447. |
| I11 | Paper base spectrum | Flat, density 0.05 | Status A neutral C*ab at most 1.11. Base 0.03: at most 0.99; base 0.08: at most 1.08. |
| I12 | Paper dyes outside 400-700 nm | Hold the end value | Endura cyan stays at 0.42 to 780 nm. CMF weight there is small. Not measured separately. |
| I13 | Additivity of reflection density | R = 10^-D_print | Not tested. Surface reflection and multiple reflection are not modeled. |
| I14 | Status M and Status A responses | colormath BSD copy of the ANSI tables, 10 nm, linear interpolation | Peaks M 640, 540, 450 nm; A 620, 530, 440 nm. Not verified against ISO 5-3:2009 (not available to this step). The independent copy in spectral_film_lut changes the P0 densities by at most 0.0135 (section 10.2). |
| I15 | Development coupling and masking couplers | None: each layer follows its own Status M curve | Not measurable without a coupler model. The Status M curves already contain the interimage effects of a neutral exposure; colored exposures are not checked. It is the work of P2. |

## 6. Neutral exposure and density checks

From [`checks.json`](../../results/p0_data_and_reference/checks.json) (1 nm, point rule).

| Check | Measured | Tolerance | Result |
| --- | --- | --- | --- |
| One stop doubles each layer exposure | relative error 0 | 1e-12 | pass |
| Speed point: sensitivity chart minus characteristic chart (R, G, B) | -0.084, -0.123, -0.019 log H (-0.28, -0.41, -0.06 stop) | 0.10 | **fail (G)** |
| Status M of D-min spectrum minus curve D-min | -0.024, -0.025, -0.068 | 0.03 | **fail (B)** |
| Midscale neutral: matched log H | -1.264, -1.171, -1.351; spread 0.180 | 0.10 | **fail** |
| Same, density above D-min | -1.220, -1.126, -1.243; spread 0.117 | (information) | - |
| Status A neutral print 0.1-2.0, max C*ab under D50 | 1.11 | 2.0 | pass |
| Film base counted once | 0 | 1e-12 | pass |
| Viewing light (D50 or D65) leaves print dyes unchanged | 0 difference; XYZ differ as expected | 0 | pass |
| CIE daylight formula D65 against the CIE table | 8.6e-6 | 2e-3 | pass |

Interpretation (hypotheses, not measured):

- The speed-point differences have the same sign in all three channels. The spectral-sensitivity
  chart is up to 0.4 stop faster than the characteristic chart. Possible causes: a different
  exposure time or reciprocity, a source spectrum other than D55 (the green difference stays
  near -0.12 for D50 to D65), or the absence of interlayer effects at the criterion density.
- The D-min and midscale differences can come from four causes: the Status table copy (I14), a
  difference between a densitometer reading and a spectrophotometer diffuse density, a different
  coating or process for the dye chart, or a midscale exposure other than -1.44. The data sheet
  does not state the midscale exposure.

## 7. Results

### 7.1 Digitization

[`digitization.json`](../../results/p0_data_and_reference/digitization.json). The overlays
`plots/overlay_*.png` show the red digitized grid on the black source curve for all six charts.
A check by eye found no visible offset at 300 dpi.

| Chart | Curves | Max tick residual (x, y) | Max grid error |
| --- | --- | --- | --- |
| Portra characteristic | B, G, R (polylines) | 4.7e-4, 6.6e-4 | 6e-5 |
| Portra spectral sensitivity | Y, M, C (Bezier) | 0.083 nm, 6.9e-4 | 0.0027 |
| Portra spectral dye density | midscale, D-min | 0.072 nm, 5.0e-4 | 0.0014 |
| Endura characteristic | R, G, B | 4.3e-4, 7.4e-4 | 3.3e-4 |
| Endura spectral sensitivity | Y, M, C | 0.050 nm, 7.2e-4 | 0.0045 |
| Endura dye spectral density | Y, M, C (peak 1.0) | 0.091 nm, 3.7e-4 | 1.9e-4 |

The digitization error is much smaller than the inconsistencies of section 6 and the effects of
the inferred fields. The source uncertainty is unknown. E-4070 says that the curves are
"representative of production coatings" and are not specifications.

### 7.2 Spectral inputs

`plots/spectral_inputs.png` shows these inputs:

- the layer sensitivities of both materials (linear, peak 1);
- the Status M and Status A products;
- the published Portra spectra with the inferred dye decomposition;
- the Endura dyes.

Observations:

- The Portra cyan-forming layer peaks at 651 nm. The Endura cyan-forming layer times lamp A peaks
  near 700 nm and extends to 740 nm. 25.8 % of its weight is above 700 nm, where E-4050 publishes
  no negative density.
- The Portra magenta-forming layer has a secondary blue sensitivity of 1/10 to 1/16 of its peak
  (log 1.35-1.55 at 400-470 nm against 2.53 at 550 nm).

### 7.3 End-to-end neutral ramp

[`neutral_ramp.json`](../../results/p0_data_and_reference/neutral_ramp.json),
`plots/neutral_ramp.png`. D55 grey, -3.3 to +0.4 log H in 0.1 steps, 1 nm point rule. The
printer balance comes from the negative of a D55 grey at -1.44 log H. That negative goes through
the same camera path as the ramp: sensitivity, criterion anchor, and curve.

- All values are finite at all 38 steps. No step is past the maximum of the paper curve.
- The print L* goes from 2.9 (scene -3.3) to 91.2 (scene +0.4); scene -1.44 prints at Status A
  0.75 (L* about 50).
- L* decreases by at most 0.0019 between steps. This comes from the 0.002 fall of the drawn
  Endura toe.
- Midscale gammas, per log H, for R, G, B:
  - negative Status M: 0.543, 0.558, 0.634;
  - printing (paper log exposure): 0.629, 0.594, 0.596.
- The maximum C*ab is 3.6 at -2.0 log H (L* 8.6, a* -3.4, b* -1.2). In the mid-tones the ramp
  stays within C*ab 1.3 from -1.7 to -1.4. The highlights are slightly blue: paper white is L*
  91.2, a* +0.8, b* -3.2, because the published Status A D-min of the paper is 0.078 in blue
  against 0.104 in red and green.
- Paper alone (the same log exposure change in R, G, B) gives C*ab at most 3.4. The negative
  adds little color to the paper with the reference choices.

**Sensitivity of the grey to the anchors.** The first run of this step balanced the printer on
the characteristic-curve density at -1.44 log H instead of on the camera path. The ramp then
went through the sensitivity anchor, which is offset by the speed-point differences of section 6
(-0.084, -0.123, -0.019 log H). That ramp had C*ab 13.1 at L* 35.5 (a* -7.1, b* +11.1). This
result was an error in the set-up, which is now corrected. It is kept because it gives a size: a
0.1 log H inconsistency between the two E-4050 charts becomes a strong color cast after the steep
paper. The inferred cyan dye has a similar effect (section 5, I6: up to C*ab 12.3).

This chain is not calibrated: it has no development coupling, no masking-coupler model, and an
inferred dye basis. It shows that the stages connect and that the units are consistent. It does
not show film appearance. Do not use it for a user review of the look.

### 7.4 Integration convergence

[`integration_convergence.json`](../../results/p0_data_and_reference/integration_convergence.json),
`plots/integration_convergence.png`. The table gives the maximum error against the 0.1 nm
reference. The reference itself differs from 0.05 nm by at most:

- 1.1e-6 (log Q, broadband);
- 2.8e-6 (Status M);
- 5.1e-6 (log print exposure);
- 1.8e-5 (ramp Status A);
- 1.1e-4 Delta E*ab (print Lab);
- 9.1e-4 Delta E*ab (ramp).

| Test | Rule | 1 nm | 2 nm | 5 nm | 10 nm | 20 nm |
| --- | --- | --- | --- | --- | --- | --- |
| log Q, broadband | point | 1.5e-4 | 1.3e-4 | 1.1e-3 | 5.4e-3 | 8.1e-2 |
| | projected | 1e-9 | 1.3e-5 | 1.0e-4 | 4.3e-4 | 5.8e-3 |
| log Q, FWHM 30 nm | point | 4.0e-4 | 1.0e-2 | 5.3e-2 | 0.18 | 0.43 |
| | projected | 9.1e-4 | 3.6e-3 | 2.2e-2 | 8.4e-2 | 0.25 |
| log Q, FWHM 10 nm | point | 6.0e-4 | 1.0e-2 | 8.5e-2 | 0.29 | 1.5 |
| | projected | 1.3e-3 | 5.4e-3 | 3.3e-2 | 0.15 | 0.49 |
| Status M, 125 negatives | point | 3.6e-4 | 1.4e-3 | 9.0e-3 | 3.6e-2 | 3.3e-2 |
| | projected | 3.5e-4 | 1.4e-3 | 8.9e-3 | 3.6e-2 | 0.13 |
| log print exposure, 125 negatives | point | 6.7e-4 | 1.7e-3 | 7.3e-3 | 2.1e-2 | 0.18 |
| | projected | 2.5e-4 | 1.0e-3 | 6.5e-3 | 2.7e-2 | 0.11 |
| Print Lab, 125 prints (Delta E) | point | 0.014 | 0.015 | 0.018 | 0.088 | 0.49 |
| | projected | 0.007 | 0.038 | 0.25 | 1.0 | 4.0 |
| Ramp Status A | point | 2.3e-3 | 2.3e-3 | 1.9e-2 | 5.3e-2 | 0.48 |
| | projected | 3.7e-5 | 1.9e-4 | 1.1e-3 | 4.6e-3 | 3.0e-2 |
| Ramp Lab (Delta E) | point | 0.12 | 0.18 | 1.3 | 4.1 | 32 |
| | projected | 0.003 | 0.011 | 0.067 | 0.31 | 2.7 |

Observations:

- **Broadband light.** Projected weights are exact at 1 nm, because the CIE illuminants are
  linear between 1 nm nodes. Point sampling has an error floor near 1.5e-4: the
  exponentiated log sensitivity is curved between the 1 nm nodes.
- **Dense dyes.** For dense dyes (Status M, print Lab), the error comes from the variable
  function 10^-D, which is far from linear between nodes. Projected weights do not help there,
  and they are worse for the print Lab at 2 to 10 nm.
- **End-to-end ramp.** The steep paper curves amplify the errors (print gamma near 3). The ramp
  meets 0.1 Delta E with projected weights up to 5 nm, but with point sampling not even at 1 nm.
- **Narrowband light.** Narrowband sources (FWHM 10 nm) need 1 nm or finer with both rules.
  A small fixed band count cannot represent them without a different method (P6).

## 8. Recommendation

1. **Keep Portra 400 and Endura Premier as the P0 pair.** Both data sheets are vector PDFs and the
   digitization is exact to the drawing. The paper data is consistent (Status A neutral C*ab at
   most 1.11).
2. **Do not claim a print response before the negative density above 700 nm is known.** This
   region has 26 % of the paper red-layer weight. A cyan dye that falls immediately after
   700 nm, which the data cannot exclude, changes the red print exposure by 0.24 log H and gives
   ramp C*ab 12.3 (section 10.4). The closest viable sources (a user decision, O2):
   - measure a processed Portra 400 neutral step wedge with a spectrophotometer to 780 nm;
   - or find a Kodak publication with isolated Portra dye curves to 750 nm.
3. **Take the E-4050 inconsistencies as calibration targets in P2. Do not hide them.** Choose
   which chart is the reference for neutral tone reproduction: characteristic curves (Status M)
   or spectral data. The evaluator already keeps both anchors apart (H*_i from the curve, the
   speed point from the spectra). A 0.1 log H anchor error gives C*ab 13 on the print grey
   (section 7.3).
4. **Use the 0.1 nm support-restricted trapezoid as the numerical reference in P1 to P7.** It is
   converged to below 0.001 Delta E*ab.
5. **For P6, start from projected weights** (5 nm meets 0.1 Delta E*ab on the neutral ramp).
   Add separate treatment of the dense-dye transmission (the 10^-D nonlinearity) and of
   narrowband scene light. A fixed band count is not justified by these results.
6. **Verify the Status M and Status A tables against ISO 5-3:2009** before a density claim is
   published (O3).

## 9. Open items

| ID | Item | Owner |
| --- | --- | --- |
| O1 | Publication of the digitized values. **Decided 2026-10-29 (ROADMAP U10):** the generated data (profiles, results) can be published; the original Kodak PDFs are not distributed ([profiles/README.md](../../profiles/README.md#source-documents-not-distributed)). | Closed |
| O2 | Source for the Portra negative density above 700 nm and for isolated dye spectra (measurement or other publication). | User decision, then P2 |
| O3 | Verify the colormath Status M and Status A tables against ISO 5-3:2009. | P1 or P2 |
| O4 | The E-4070 paper exposure light, criterion density, and base spectrum; the E-4050 "Daylight" CCT and the exposure of the midscale neutral. Ask Kodak Alaris or measure. | User decision |
| O5 | Accept or change the predeclared tolerances of section 4.4. | User |
| O6 | Development coupling and masking couplers, checked with colored exposures. The neutral ramp is within C*ab 3.6 now, but colored exposures were not checked. | P2 |

Not measured in P0:

- RGC (P1);
- reconstruction of scene spectra from RGB (P1);
- a coupler model (P2);
- GPU execution, time, and memory (P7);
- photos;
- user review of appearance.

## 10. Comparison with spectral_film_lut

[spectral_film_lut](https://github.com/JanLohse/spectral_film_lut) (Jan Lohse, MIT) makes film
LUTs from digitized data sheets. It was inspected at commit `bcbcfc68` after the P0
measurements. Its Portra 400 and Endura Premier files come from the same two Kodak data sheets.
The curve points were placed by hand. `compare_spectral_film_lut.py` downloads the files of that
commit and checks their hashes. It reads the files as data with `ast`; it does not import or run
the code. No value of that project goes into the profiles of this lab. Results:
[`comparison_spectral_film_lut.json`](../../results/p0_data_and_reference/comparison_spectral_film_lut.json).

### 10.1 Digitization

For each curve: their value minus our value interpolated at their wavelength or log H, inside
our domain.

| Curve | Points | Median abs. difference | Max abs. difference |
| --- | ---: | ---: | ---: |
| Portra log sensitivity Y, M, C | 38, 41, 43 | 0.0049, 0.0048, 0.0046 | 0.020, 0.041, 0.030 |
| Portra characteristic R, G, B | 30 each | 0.0024, 0.0014, 0.0010 | 0.0035, 0.0034, 0.0025 |
| Portra midscale neutral, D-min | 48, 38 | 0.0006, 0.0011 | 0.0080, 0.0036 |
| Endura log sensitivity Y, M, C | 24, 28, 25 | 0.0029, 0.0044, 0.0068 | 0.014, 0.029, 0.017 |
| Endura characteristic R, G, B | 50, 48, 48 | 0.011, 0.013, 0.014 | 0.037, 0.057, 0.045 |
| Endura dyes Y, M, C | 17, 21, 19 | 0.0030, 0.0032, 0.0025 | 0.0051, 0.0049, 0.0059 |

- The two independent digitizations agree to a median of 0.001 to 0.014.
- The largest differences are on steep sections, where a small error in x gives a large error
  in y:
  - the Endura characteristic curves (gamma near 3);
  - the cut edges of the sensitivity curves.
- The vector paths of this lab have no placement error (section 7.1). The differences are
  therefore an estimate of the error of a hand digitization of these charts.
- They do not show any error of the vector extraction. No offset or wrong label was found.
- Their Portra characteristic curves end at -0.05 log H. The chart continues to +0.56 log H.

### 10.2 Status A and Status M tables

spectral_film_lut has its own copy of the Status A and M tables. It gives log10 spectral
products with peak 5.000, which is the ISO 5-3 format, at 10 nm. It also adds points 1 nm
outside each band.

- **Agreement in the bands.** The two secondary copies agree within 0.01 log units at all
  common points except the tails.
- **Differences in the tails.** The tails are where the product is below about 1 % of its peak:
  - Status A red: 710-740 nm, up to 0.26;
  - Status M green: 470 and 610 nm, up to 0.15;
  - Status A blue: 480-490 nm, up to 0.09.

  The colormath copy stores linear percentages with two decimals, so its tail values are rounded
  (for example 0.01 % against 0.0055 %).
- **Effect on densities.** With their tables in place of the colormath tables:
  - Status M of the Portra D-min spectrum changes by at most 0.0016;
  - Status M of the midscale neutral changes by at most 0.0082;
  - Status A of Endura prints (0.3 to 2.5) changes by at most 0.0135.
- **Conclusion for P0.** The table source does not explain the failed checks of section 6
  (0.068 density, 0.18 log H). Item I14 stays open: no copy was checked against ISO 5-3:2009.
  The two copies give a tolerance near 0.01 density until that check is done.

### 10.3 Different choices for the fields that the sources do not give

The project fills the same gaps of section 5 with other rules. Each row below compares two
approaches; it does not make one of them correct.

| Field | This lab (P0) | spectral_film_lut |
| --- | --- | --- |
| Sensitivity outside the published domain (I3) | zero | linear extrapolation of log sensitivity |
| Characteristic curve outside its domain (I4) | first value below the toe; error above the end | extended with a logistic shoulder (assumed height 3.0) |
| Spectral density outside 400-700 nm (I5, I12) | hold the end value | Gaussian tail fitted to the slope at the end |
| Isolated negative dyes (I6) | three asymmetric Gaussians fitted to midscale minus D-min | the same neutral difference cut into three bands at its two minima between the B, G, and R maxima, with Gaussian-blurred band edges (sigma 25 nm); the three bands add up exactly to the neutral |
| Midscale exposure (I7) | "Log H Ref" -1.44 | log H where the curves reach a Laboratory Aim Density (LAD) grey |
| Masking couplers and interlayer effects (I15) | none | a color-masking factor through Academy Printing Density (SMPTE ST 2065-2) for Status M films |
| Printing light | CIE A with a balance per channel | the APD printer light split into three lights |

Their README states the same limit as this report: the data sheets give almost no data about
the interlayer effects and the strength of the masking couplers.

### 10.4 Measured: the spectral_film_lut methods in the P0 evaluator

spectral_film_lut is MIT, so its methods can be adopted as they are (ROADMAP U11). Three methods
were ported into `film_spectral_reference.py`, with the parameters of commit `bcbcfc68`. The
notice is in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md). The three methods:

- `sensitivity_outside = "log_linear"`: log sensitivity extended with the end slope (last 5 nm),
  inside 380-780 nm.
- `negative_density_outside = paper_dye_outside = "gaussian_tail"`: Gaussian tails with the end
  value and the slope over the last 10 nm (d_1 = 30, d_2 = 0.75).
- `negative_dye_basis = "band_split"`: the neutral above D-min is cut at 500 nm and 596 nm (the
  minima between the maxima at 454, 542, and 697 nm), with sigma 25 nm edges.

[`spectral_film_lut_variants.json`](../../results/p0_data_and_reference/spectral_film_lut_variants.json),
1 nm, point rule, same balance rule as section 7.3:

| Variant | Speed point diff. R, G, B | D-min diff. B | Midscale spread | Status A neutral C*ab | Ramp max C*ab | Printing gamma R, G, B | Cyan step, red print log H |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| reference | -0.084, -0.123, -0.019 | -0.068 | 0.180 | 1.11 | 3.61 | 0.629, 0.594, 0.596 | -0.555 |
| log-linear sensitivity | -0.086, -0.124, -0.019 | -0.068 | 0.180 | 1.11 | 3.66 | 0.629, 0.592, 0.595 | -0.551 |
| Gaussian tails | -0.084, -0.123, -0.019 | -0.068 | 0.180 | 1.18 | 3.39 | 0.630, 0.594, 0.595 | -0.556 |
| band-split dyes | -0.084, -0.123, -0.019 | -0.068 | 0.180 | 1.11 | 3.55 | 0.630, 0.597, 0.601 | -0.552 |
| band-split dyes + tails | -0.084, -0.123, -0.019 | -0.068 | 0.180 | 1.18 | 3.42 | 0.627, 0.597, 0.599 | -0.551 |
| all three | -0.086, -0.124, -0.019 | -0.068 | 0.180 | 1.18 | 3.47 | 0.624, 0.595, 0.598 | -0.545 |

- **No variant changes a result of section 6.** The failed checks come from the data sheet, not
  from the extrapolation or dye rules.
- **The Gaussian tails change the spectra a lot but the prints very little.**
  - At 750 nm, the tails lower the Portra midscale density from 1.27 (hold) to 0.70.
  - The tails lower the Endura cyan dye at 750 nm from 0.42 to 0.03.
  - The printer balance absorbs the constant part of the change. On the grey and the cyan step,
    the effect is at most 0.2 C*ab and 0.01 log H.
- **The band split gives the same cyan step as the smooth Gaussian fits** (-0.551 against -0.49
  to -0.57). One case is different: the fit with the cyan peak at 700 nm and an 8 nm long-side
  width (RMS 0.0078, nearly as good as the free fit) lets the cyan density fall immediately
  after 700 nm. It gives -0.31 and ramp C*ab 12.3. The data cannot exclude this case, so the
  missing negative density above 700 nm (O2) stays the largest uncertainty.

### 10.5 What P0 takes from this comparison

- The digitization of P0 is confirmed by an independent method.
- The Status table choice is worth at most about 0.01 density on this pair.
- The three ported methods are available as options. They can be the default rules in P1 and P2,
  because they are within 0.3 C*ab of the P0 rules and they give finite smooth spectra on
  380-780 nm instead of held values.
- Two further methods of spectral_film_lut can be adopted directly in P2:
  - the APD color-masking factor for Status M films;
  - the logistic shoulder of the characteristic curve.

  Measure them with the checks of section 6 and the cyan-peak scan.
- The about 60 digitized materials of the project are a useful index of which data sheets exist
  and which charts they give. Before a second material pair is selected, check for each sheet
  whether it is a vector PDF and whether it publishes isolated dyes and density to 750 nm.
