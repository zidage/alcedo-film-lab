# P1: Spectral input (AP1 to Portra 400 layer exposure)

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P1, and sections
[3.1](../../README.md#31-spectral-reconstruction-and-layer-exposure),
[6.1](../../README.md#61-separate-spectral-shape-from-exposure), and
[6.3](../../README.md#63-evaluate-the-response-of-metamers).
**Date:** 2026-10-29 to 2026-10-30.
**Status:** measurements done for the spectral input. **RGC is out of scope of this step** (user
decision U13, 2026-10-29); the RGC verification and its location stay open (section 9).
The user decided on 2026-10-30 that the DRT receives no camera identity and delegated the
near-black rule and the tolerances to this step (README U14 to U16, sections 7.14 to 7.19). User
review of the recommendation is open. U17 (2026-10-30) sets the final appearance as the priority;
section 8 is the selected route after that decision.

> **Plots are local only.** `results/p1_spectral_input/plots/` (`*.png` is in `.gitignore`).
> No photo, crop, or image made from a photo is in the repository; section 7.12 gives only
> statistics and file names. The commands are in the
> [script README](../../scripts/poc/p1_spectral_input/README.md#commands).

## 1. Question

Which spectral reconstruction from linear AP1 gives stable XYZ and stable Portra 400 layer
exposure? The step compares compact spectral models and measured-data priors on:

1. held-out measured reflectances under daylight and non-daylight scene lights;
2. exposure scaling (one stop doubles every layer exposure);
3. metamers (spectra with the same XYZ and different layer exposure);
4. near-black and saturated-light probes;
5. a synthetic camera stage (measured camera sensitivities, IDT) and real RAW files.

The pipeline candidates all reconstruct a full spectrum and integrate it against the Portra
layer sensitivities on the P0 reference grid. The in-sample 3x3 matrix of section 4.4 and the
camera-to-exposure matrix of section 7.10 are **comparison measurements, not candidates**.

## 2. Result summary

- **XYZ is stable with every candidate.** Every candidate reproduces XYZ to Delta E*ab below
  5e-6 inside its domain (all values round to 0 at the 5 decimals of the JSON files). Every candidate is homogeneous: one exposure step changes every layer
  exposure by the same factor, with a relative error of at most 7.2e-14 for scales 1e-6 to
  1e3. No candidate gives a non-finite value for any input (near black, zero, negative,
  narrowband).
- **Layer exposure is not stable with any candidate, and it cannot be with AP1 alone.** No
  candidate meets the predeclared tolerance (Status M error p95 at most 0.01 and max at most 0.03
  for each channel) on any held-out dataset under daylight. The in-sample linear floor (the best
  3x3 map from AP1 to layer exposure, fitted on the test set itself) also fails on every dataset.
  The cause is the film, not the method:
  - The Portra red-sensitive layer has its maximum at 651 nm and continues to 680 nm, where the
    CIE observer has almost no weight (`plots/sensitivity_vs_observer.png`).
  - For one mid-grey XYZ, the red-layer density of the developed negative can be anywhere from
    0.39 to 1.21 over all reflectances in [0, 1] (linear program, section 7.7).
  - Measured metamer pairs (Delta E*ab at most 0.5) differ by up to 0.048 (red) and 0.063
    (blue) in negative density; for pairs from different datasets the p95 is 0.025 (red) and
    0.054 (blue).
- **Best held-out results under D55** (negative Status M error, p50 / p95 per R, G, B):

  | Dataset | Best candidate | p50 | p95 | Linear floor p95 |
  | --- | --- | --- | --- | --- |
  | Skin (ISSA, 15,254) | sigmoid (JH) | 0.0075, 0.0048, 0.020 | 0.012, 0.0084, 0.032 | 0.0054, 0.0029, 0.011 |
  | Natural objects (1,576) | JH (red), local prior (blue) | 0.0054, 0.0031, 0.027 (JH) | 0.041, 0.019, 0.107 (JH); 0.047, 0.012, 0.057 (local) | 0.049, 0.009, 0.036 |
  | USGS materials (1,543) | JH | 0.0021, 0.0003, 0.0024 | 0.024, 0.006, 0.031 | 0.034, 0.0045, 0.025 |
  | rawtoaces 190 patches | local prior | 0.014, 0.0034, 0.020 | 0.069, 0.016, 0.101 | 0.116, 0.016, 0.040 |

- **Skin has a systematic error that the smooth models cannot see.** Measured skin is low at
  380-430 nm (mean 0.11-0.12; hemoglobin Soret absorption near 415 nm and melanin), and every
  candidate puts about 0.04 more reflectance there. The Portra blue layer has a second lobe at
  400-430 nm (0.75 of its maximum at 410 nm). The CIE
  z-bar (times E_ref) has its maximum at 450 nm, so XYZ barely constrains this band, but the Portra
  blue-sensitive layer is sensitive there. The result is a blue density bias (signed median) of
  +0.018 to +0.028 and a red bias of -0.006 to -0.019. The blue error is positive for 97 % to
  99.99 % of the skin records, depending on the candidate and the light.
- **A chromaticity-local measured prior removes most of the skin bias when it has seen skin.**
  The new candidate `measured_prior_local` builds the prior from the training spectra nearest in
  u'v'. Trained on other ISSA subjects (split by subject), it reduces the skin bias from
  (-0.015, +0.004, +0.022) to (-0.0036, +0.0011, +0.0061), and the p50 to
  (0.0038, 0.0012, 0.0064). The width of the kernel (0.005 to 0.02 in u'v') has almost no effect.
  When it is trained without any skin (dataset held out), it does not help skin. The prior
  needs representative data for each class of colour; held-out data from another class does not
  substitute for it.
- **Most of the error under a non-daylight scene light is the assumed reference light.** Every
  reflectance-type candidate assumes daylight (E_ref, ACES white). Under fluorescent, LED, and
  sodium light, all candidates have the same large bias (for example red +0.09 under FL11, red
  +0.16 to +0.18 under HP1). With the actual scene light as the reference light, the error falls
  by a factor of 5 to 100: HP1 red p50 0.16-0.18 to 0.005-0.008; skin under FL11, red p50
  0.093 to 0.0007 (JH). The scene light is the largest single input to the layer exposure that
  AP1 does not carry.
- **The camera adds an error of the same size as the reconstruction.** With 21 measured camera
  sensitivities (rawtoaces-data) and an IDT fitted on the rawtoaces patches, the IDT error alone
  is Delta E*ab p50 0.2 to 3.1, largest on skin. The skin blue-density p50 increases from 0.020
  (exact XYZ) to 0.041 (camera AP1, JH). A reconstruction constrained by the camera response
  instead of XYZ is not better. A direct camera-RGB-to-exposure matrix (a comparison
  measurement) is better on skin (blue p50 0.015): the camera channels resemble the film
  layers more than XYZ does, and the IDT to XYZ removes part of that information.
- **The print amplifies the layer error.** Through the uncalibrated P0 chain (Endura, steep
  paper), the difference between truth and reconstruction is Delta E*ab p50 4.4 (JH) to 7.3 on
  skin and 3.7 to 4.1 on natural objects. Treat this as a size estimate only: the P0 chain is not
  calibrated (P0 report, section 7.3).
- **Domain.** Mallett-Yuksel (Rec. 709 basis) and the linear priors give negative radiance for
  saturated inputs. The sigmoid (JH) cannot reach most narrowband lights (26 of 31 Gaussians of
  10 nm FWHM). The non-negative prior is in its domain for every physically realizable input
  (61 of 62 Gaussian probes; the one failure is at 680 nm, 10 nm FWHM).
- **RAW photos (44 files, 21 cameras).** Per file, a median of 0.065 % of the unclipped pixels is
  outside the spectral locus (max 16 %); the two sources are near-black noise and saturated
  colours moved by the 3x3 IDT. The candidates disagree on real pixels by a median p95 of 0.044
  (red) and 0.051 (blue) in negative density.
- **Method without a camera identity (U16; sections 7.14 to 7.19).** The non-negative local prior
  with the near-black rule meets the revised acceptance criteria (U15) on skin and USGS materials
  when its training data includes the class. Trained on the error distribution of other camera
  makers, the camera population prior reduces the skin blue bias on a held-out maker from +0.039
  (JH) to +0.005, without any camera identity at run time. Natural objects and the saturated
  rawtoaces patches still fail the p95 criterion.
- **Correction of the scene-light result.** The factor of 5 to 100 needs the full spectrum of the
  light. With the scene white only, daylight and tungsten improve; fluorescent, LED, and sodium
  light do not (section 7.15). The same white can have very different spectra.
- **Selected route after U17 (section 8):** one reconstruction, the non-negative local prior with
  the near-black rule. The reference light comes from the scene white for RAW input and is E_ref
  (the ACES white) for non-RAW input. User review of the final appearance replaces further numeric
  work on this stage.

## 3. Inputs and machine

### 3.1 Sources

Full manifest: [`source_manifest.json`](../../results/p1_spectral_input/source_manifest.json);
expected hashes: [`sources.json`](../../scripts/poc/p1_spectral_input/sources.json). Retrieved
2026-10-29. No source file is committed. The P0 sources (CIE CMF, daylight, A, D65, Status
tables, Kodak profiles) come from step P0.

| Source | Edition | License | Use |
| --- | --- | --- | --- |
| rawtoaces-data training spectra (190 patches, 380-780 nm, 5 nm) | commit `e9b8503c` | Apache-2.0 | test set; prior training; IDT fit |
| rawtoaces-data camera sensitivities, 21 cameras | commit `e9b8503c` | Apache-2.0 | camera stage; RAW IDT |
| Gutierrez et al., natural objects of the Southern cone (plants 887, animals 501, stones 188; 400-1000 nm, 4 nm) | figshare 10.6084/m9.figshare.25705380 v4 | CC BY 4.0 | test set; prior training |
| Lu et al., International Skin Spectra Archive (ISSA) | figshare 10.6084/m9.figshare.28228571 v4 | CC BY 4.0 | test set; prior training |
| USGS Spectral Library 7, splib07b convolved to ASD (350-2500 nm) | doi:10.5066/F7RR1WDJ | U.S. public domain | test set; prior training |
| CIE 015:2018 FL, LED, HP tables (5 nm) | CIE 015:2018 data set | CC BY-SA 4.0 | scene lights |
| Alcedo Studio RAW test library (44 files of 21 cameras) | local, supplied by the user | not distributed | section 7.12 |

The dataset list follows the open sets that the Fotufilm measured prior uses (Fotufilm
THIRD_PARTY_NOTICES at `96623ba0`; README U12: reference). No Fotufilm code or table is used.

### 3.2 Machine and software

Intel Core i7-12700H, Windows 11 10.0.22635, Python 3.14.2, NumPy 2.5.4, SciPy 1.18.1,
matplotlib 3.11.2, rawpy 0.27.1 (LibRaw 0.22.1), openpyxl 3.1.5. CPU only, one process at a
time. No GPU was used. Run times: section B 728 s, section G 1,535 s, section J 1,448 s,
section K 172 s; RAW files 48-85 s each (section 7.12).

Run history (all result files come from the final solver):

- The first runs used a penalized NNLS for the non-negative prior. It was not exact near the
  spectral locus (narrowband probes outside the domain by the XYZ residual). It was replaced by
  the active-set QP (section 4.2), whose largest XYZ residual is 6.4e-16; all sections were run
  again.
- Rule `zero_layer_exposure` (section 4.1) was added after sections B, C, F, G, and H had run.
  These sections have no sample with a zero layer exposure (checked: 0 of 167,067 held-out
  samples); sections D, E, I, J, and K were run again with the rule.
- Section I first stopped with the real error of the P0 dye solve; the script now counts the
  samples that the P0 dye sets cannot reach (section 7.13).

## 4. Method

### 4.1 Quantities

| Quantity | Definition |
| --- | --- |
| Radiance L | Relative spectral radiance on the P0 1 nm grid (360-840 nm). The perfect white diffuser under the scene light has Y = 1. |
| XYZ | CIE 1931 2 degree, projected weights of the 1 nm grid from the 0.1 nm fine grid (exact for spectra that are linear between 1 nm nodes; P0 report section 4.3). |
| AP1 | Linear AP1 from XYZ with the SMPTE RP 177 matrix of the AP1 primaries and the ACES white. No white balance and no RGC: AP1 is the colorimetry of the scene radiance. |
| E_ref | CIE daylight formula at T = 6000 K (nominal 5996.66 K). Chromaticity (0.3216806, 0.3376734); the ACES white is (0.32168, 0.33767). The reflectance-type candidates produce L = E_ref * rho. |
| Layer exposure Q | Portra 400 (P0 profile, rule 'zero' outside the published sensitivity domain): Q = 1 is the criterion exposure. Scale: an 18 % grey (Y = 0.18) receives 10^-1.44 lux s (the P0 midscale). |
| Negative density | Status M from the P0 characteristic curves at log H* + log10 Q. Q = 0 exactly gives the curve start (rule 'zero_layer_exposure', the limit of the P0 below-toe rule); Q < 0 has no density. |
| Error | Reconstruction minus truth, per channel. The main metric is the Status M error: it weights each layer by its effect on the negative and is flat in the toe. |

### 4.2 Candidates

All five candidates are homogeneous of degree 1: the spectral shape depends on the chromaticity
only (README section 6.1). Definitions: module docstring of
[`spectral_reconstruction.py`](../../scripts/poc/p1_spectral_input/spectral_reconstruction.py).

| Name | Method | Source | Linear in AP1 |
| --- | --- | --- | --- |
| `mallett_yuksel_rec709` | three non-negative basis reflectances that add up to 1, minimum roughness (squared first differences at 5 nm knots), each reproduces one Rec. 709 primary under E_ref | Mallett and Yuksel 2019, re-derived here (SLSQP); the original uses sRGB under D65 | yes |
| `jakob_hanika_sigmoid` | rho = algebraic sigmoid of a quadratic in wavelength; batched Levenberg-Marquardt in CIELAB; continuation from the grey of the same L* for hard targets | Jakob and Hanika 2019; normalization 2 max(rgb) of pbrt-v4 `RGBIlluminantSpectrum` (rule only, no code) | no |
| `measured_prior_linear` | rho = C A^T (A C A^T)^-1 XYZ; C = second moment of measured reflectances at 5 nm knots | minimum-norm (Wiener-type) estimate | yes |
| `measured_prior_nonnegative` | minimum rho^T C^-1 rho with A rho = XYZ, rho >= 0; primal active-set QP (Nocedal and Wright, algorithm 16.3, null-space steps), started from a penalized NNLS | this lab | no |
| `measured_prior_local` | as `measured_prior_linear`, with C built from the 256 training spectra nearest in u'v' (Gaussian weights, sigma 0.01), blended 5 % with the global C | this lab; the chromaticity-indexed prior idea of README section 3.1 | no |

Prior rules: each dataset has the same total weight in C (rule `prior_dataset_weight`); ridge
1e-4 * trace(C) / n (rule `prior_ridge`). The prior matrices are made at run time from the
downloaded data and are not committed.

### 4.3 Tests

| Section | File | Test |
| --- | --- | --- |
| A | `reference_white.json` | E_ref against the ACES white; Mallett-Yuksel basis fit |
| B | `heldout_reflectance.json` | each dataset under 9 scene lights (E_ref, D55, D65, A, FL2, FL11, LED-B3, LED-RGB1, HP1); priors trained without the test dataset |
| C | `exposure_scaling.json` | Q(s x) = s Q(x), s = 1e-6 to 1e3 |
| D | `near_black.json` | grey ramp to 1e-12, zero, 10,000 noisy near-black inputs (mean 1e-3, sigma 1e-3, mixed signs), negative components, negative luminance |
| E | `saturated_light.json` | 62 Gaussian emissions (FWHM 10 and 30 nm, 400-700 nm), CIE LED-RGB1, HP1, FL11, FL2, LED-B3, each at Y = 0.18 |
| F | `metamers.json` | measured pairs with Delta E*ab <= 0.5 under D65 (all datasets pooled, spectral RMS difference > 0.01); linear-program bounds of Q over 0 <= rho <= 1 at fixed XYZ |
| G | `camera_stage.json` | 21 cameras; IDT camera RGB -> scene XYZ fitted on the rawtoaces patches in CIELAB with the white preserved (rawtoaces method, no chromatic adaptation); D55 and A |
| H | `film_sensitivity_variant.json` | section B under D55 with the spectral_film_lut log-linear sensitivity extension |
| I | `print_effect.json` | viewed-print Delta E*ab (uncalibrated P0 chain), 300 records per dataset, D55 |
| J | `scene_light_matched.json` | section B for the 6 non-daylight lights with the scene light as reference light |
| K | `in_distribution_prior.json` | prior trained on one half of every dataset (ISSA split by subject), tested on the other half, D55 |
| (plots) | `skin_band_error.json` | band analysis of the skin error (2,000 ISSA records, E_ref, held-out prior) |
| RAW | `raw_photos.json` | section 7.12 |

### 4.4 The in-sample linear floor

For each dataset and light, the floor is the 3x3 matrix from AP1 to Q that minimizes the
squared relative Q error **on the test set itself**. It is not a candidate, and it is not a way
to transform an image: it uses the answer. It measures how much of the error any map that is
linear in AP1 must have. Mallett-Yuksel and `measured_prior_linear` are linear in AP1, so their
composition with the layer integral is a 3x3 map, and the floor is a lower bound for them on
average. The nonlinear candidates can be better than the floor, and on several datasets they are.

### 4.5 Tolerances

Set in `run_p1_checks.py` before its first run. A trial on rawtoaces_190 before that run showed
the order of the red-layer error; the tolerances were not changed after it.

| Check | Tolerance | Reason |
| --- | --- | --- |
| XYZ reproduction inside the domain | Delta E*ab <= 0.1 | below visibility |
| Layer exposure "stable", per dataset and daylight light | Status M error p95 <= 0.01 and max <= 0.03, each channel | P0: 0.1 log H channel offset gives C*ab 13 on the print grey; 0.01 density (about 0.017 log H at gamma 0.6) is near the P0 grey tolerance |
| Exposure scaling | relative 1e-12 (linear), 1e-9 (QP), 1e-6 (iterative sigmoid fit) | float64; solver stop rule |
| Near black and every probe | finite output for every input; domain failures counted | README section 9 |

### 4.6 Data rules

Named in [`spectral_datasets.py`](../../scripts/poc/p1_spectral_input/spectral_datasets.py).

| Rule | Effect |
| --- | --- |
| `reflectance_outside_measured_range`: hold the end value | Gutierrez 360-400 nm; rawtoaces 360-380 and 780-840 nm; ISSA: 9,958 records are 400-700 nm, 5,296 are 360-740 nm. The Portra blue layer is sensitive from 380 nm, so this rule is part of the test spectrum of these datasets; truth and reconstruction use the same extended spectrum. |
| `reflectance_plausibility` | reject a record outside -0.02 to 1.5 in 380-780 nm; values -0.02 to 0 set to 0. Rejected: USGS 914 (missing values in 360-840 nm); set to 0: 8 USGS values. |
| `issa_formula_rows` | 2 ISSA rows are spreadsheet averages of other records; not used. |
| (kept as published) | 18 rawtoaces patches are exactly 0 at 380 nm and above 0.02 at 385 nm. |
| `light_source_resampling` | CIE FL, LED, HP tables: linear onto 1 nm, zero outside 380-780 nm. |

Records used: rawtoaces 190, Gutierrez 1,576, ISSA 15,254, USGS 1,543 (artificial materials,
coatings, liquids, minerals, organic compounds, soils, vegetation).

## 5. Inferred fields and choices

| ID | Field | Choice | Effect |
| --- | --- | --- | --- |
| P1-1 | Reference light of the reconstruction | E_ref (daylight 6000 K, ACES white) | Under a non-daylight scene light this choice is the main error (section 7.6). |
| P1-2 | Brightness normalization of the sigmoid | 2 max(AP1), from pbrt-v4 | Changes which spectral shape is fitted for a chromaticity; not varied. |
| P1-3 | Prior: dataset weights, ridge, knots | equal dataset weight, ridge 1e-4, 5 nm knots | Not varied, except the local kernel width (section 7.5: no effect). |
| P1-4 | Exposure of the reflectances | 18 % grey at the P0 midscale (-1.44 log H) | Places the toe and the shoulder; same for all candidates. |
| P1-5 | Portra sensitivity above 680 nm | P0 rule 'zero' (published domain) | The log-linear extension of spectral_film_lut changes the held-out p50 by at most 0.0002 (section 7.11); it matters for deep-red narrowband light (section 7.9). |

## 6. Checks

| Check | Measured | Tolerance | Result |
| --- | --- | --- | --- |
| E_ref chromaticity against ACES white | (6e-7, 3.4e-6) | (information) | - |
| Mallett-Yuksel basis: primary residual, sum to 1 | 1.1e-15, 1.1e-16; min value 0 | 1e-6 | pass |
| XYZ reproduction in the domain, all candidates, all datasets and lights | max Delta E*ab below 5e-6 | 0.1 | pass |
| Exposure scaling, max relative error | MY 1.4e-15, JH 6.9e-15, prior linear 1.8e-15, non-negative 1.5e-14, local 7.2e-14; no domain change | 1e-12 / 1e-9 / 1e-6 | pass |
| Grey ramp to 1e-12: Q / scale spread | at most 1.3e-15 | (information) | - |
| Finite output for every probe (sections D, E) | 0 non-finite outputs | 0 | pass |
| Layer exposure stable on every dataset under daylight | no candidate; the linear floor neither | p95 0.01, max 0.03 | **fail (all)** |

## 7. Results

### 7.1 Why the red layer is not determined by XYZ

`plots/sensitivity_vs_observer.png` shows the Portra layer weights and the CIE functions, both
multiplied by E_ref. The Portra cyan-forming (red-sensitive) layer has its maximum at 651 nm and
is cut at 680 nm. With the same light, x-bar is at 0.24 of its maximum at 650 nm and 0.040 at
680 nm. Two spectra that differ only at 640-680 nm have nearly the same XYZ and different red
exposure. The blue-sensitive layer starts at 380 nm with 15 % of its maximum (P0); z-bar times E_ref has
its maximum at 450 nm and is at 0.16 of it at 415 nm. The green layer is near y-bar, and its error is always the smallest.

### 7.2 Held-out reflectances under daylight

[`heldout_reflectance.json`](../../results/p1_spectral_input/heldout_reflectance.json),
`plots/heldout_density_error.png`. Status M error, D55, p50 / p95 (R, G, B):

| Dataset | MY | JH | prior linear | prior non-negative | prior local | linear floor (p95) |
| --- | --- | --- | --- | --- | --- | --- |
| skin | 0.011, 0.0013, 0.024 / 0.019, 0.0038, 0.030 | 0.0075, 0.0048, 0.020 / 0.012, 0.0084, 0.032 | 0.019, 0.0051, 0.028 / 0.026, 0.0074, 0.035 | same as linear | 0.019, 0.0037, 0.023 / 0.029, 0.0056, 0.030 | 0.0054, 0.0029, 0.011 |
| natural | 0.014, 0.0050, 0.016 / 0.063, 0.024, 0.067 | 0.0054, 0.0031, 0.027 / 0.041, 0.019, 0.107 | 0.011, 0.0029, 0.015 / 0.047, 0.011, 0.062 | 0.012, 0.0030, 0.016 / 0.052, 0.013, 0.071 | 0.011, 0.0036, 0.018 / 0.047, 0.012, 0.057 | 0.049, 0.0091, 0.036 |
| USGS | 0.0021, 0.0007, 0.0092 / 0.026, 0.0074, 0.027 | 0.0021, 0.0003, 0.0024 / 0.024, 0.0060, 0.031 | 0.0084, 0.0012, 0.0061 / 0.020, 0.0037, 0.030 | 0.0084, 0.0012, 0.0062 / 0.022, 0.0044, 0.031 | 0.0018, 0.0008, 0.0063 / 0.021, 0.0045, 0.045 | 0.034, 0.0045, 0.025 |
| rawtoaces | 0.030, 0.0047, 0.015 / 0.128, 0.038, 0.042 | 0.029, 0.0049, 0.035 / 0.145, 0.026, 0.120 | 0.016, 0.0024, 0.0079 / 0.084, 0.027, 0.030 | 0.022, 0.0033, 0.0096 / 0.179, 0.029, 0.039 | 0.014, 0.0034, 0.020 / 0.069, 0.016, 0.101 | 0.116, 0.016, 0.040 |

Outside the domain (D55): MY 25 / 31 / 0 / 18 records (rawtoaces / natural / skin / USGS),
prior linear 49 / 66 / 0 / 21, prior local 4 / 0 / 0 / 2; JH and the non-negative prior 0.
E_ref and D65 give the same picture (in the JSON file).

Observations:

- No candidate is best on every dataset. JH is best for skin, USGS, and the red layer of
  natural objects. The priors are best for the blue layer and for the saturated rawtoaces
  patches.
- The nonlinear candidates are better than the linear floor for natural objects, USGS, and
  rawtoaces (red p95 0.024-0.069 against 0.034-0.116). For skin, the floor is better than every
  candidate: skin occupies a small region of chromaticity, and inside it a fitted 3x3 map
  corrects the systematic bias of section 7.3. The floor needs the answer, so this shows the
  size of the bias, not a method.
- The non-negative prior equals the linear prior where the linear estimate is already
  non-negative (all skin records). Its value is the domain, not the accuracy.

### 7.3 Skin: the 380-430 nm region

[`skin_band_error.json`](../../results/p1_spectral_input/skin_band_error.json),
`plots/skin_spectrum.png`. Mean over 2,000 ISSA records, E_ref, held-out prior. Signed median
Status M error under E_ref: JH (-0.006, +0.005, +0.019); prior linear (-0.017, +0.005, +0.023);
MY (-0.010, +0.001, +0.021). The blue error is positive for 97 % (JH, D65) to 99.99 % (D55)
of the records; the red error is negative for 97 % to 99.99 %.

Mean reconstruction minus mean measurement (measured mean 0.114 at 380-400 nm and 0.121 at
400-430 nm):

| Candidate | 380-400 nm | 400-430 nm | 470-520 nm | 600-640 nm | 400-430 nm share of the blue-layer exposure |
| --- | --- | --- | --- | --- | --- |
| MY | +0.050 | +0.043 | -0.014 | -0.004 | +8.2 % |
| JH | +0.045 | +0.038 | -0.025 | -0.026 | +7.4 % |
| prior linear and non-negative | +0.043 | +0.041 | -0.033 | -0.025 | +7.9 % |
| prior local (no skin in training) | +0.037 | +0.032 | -0.024 | -0.023 | +6.2 % |

Skin absorbs strongly at 380-430 nm (hemoglobin Soret band near 415 nm, and melanin). At the
10 nm sampling of ISSA, the mean measurement is a low, flat region, not a resolved dip; 65 % of
the records start at 400 nm, so their 380-400 nm values are held (rule
`reflectance_outside_measured_range`). The Portra blue layer has a second lobe in this region
(0.75 of its maximum at 410 nm, `plots/sensitivity_vs_observer.png`). The 400-430 nm band alone adds 6 %
to 8 % to the blue-layer exposure (about +0.03 log H, +0.02 density at the negative gamma); the
380-400 nm band adds about 1.5 % to 1.9 %. The reconstruction is below the measurement at
470-520 nm and 600-640 nm; this gives the red bias.

XYZ carries little of this information: z-bar (times E_ref) is at 0.16 of its maximum at
415 nm. A smooth spectral model has no reason to put a low region there. Only a prior that knows that colours of skin chromaticity have this
low region can reproduce it.

### 7.4 Chromaticity-local prior and in-distribution training

[`in_distribution_prior.json`](../../results/p1_spectral_input/in_distribution_prior.json). D55,
prior trained on one half of every dataset (ISSA: by subject, so no test subject is in the
training data), tested on the other half. p50 / p95 / signed median (R, G, B):

| Dataset | prior linear (global C) | prior local, sigma 0.005 | sigma 0.01 | sigma 0.02 |
| --- | --- | --- | --- | --- |
| skin (7,643) | 0.015, 0.0038, 0.022 / 0.021, 0.0059, 0.028 / -0.015, +0.0038, +0.022 | 0.0038, 0.0012, 0.0064 / 0.019, 0.0039, 0.018 / -0.0036, +0.0011, +0.0062 | 0.0038, 0.0012, 0.0064 / 0.019, 0.0039, 0.018 / -0.0036, +0.0011, +0.0061 | 0.0037, 0.0012, 0.0064 / 0.019, 0.0039, 0.018 |
| natural (788) | 0.011, 0.0025, 0.012 / 0.047, 0.010, 0.049 | 0.0061, 0.0023, 0.0096 / 0.032, 0.0086, 0.037 | 0.0079, 0.0027, 0.011 / 0.036, 0.0096, 0.040 | 0.0086, 0.0030, 0.013 / 0.039, 0.0100, 0.040 |
| USGS (772) | 0.0022, 0.0005, 0.0047 / 0.018, 0.0037, 0.030 | 0.0019, 0.0004, 0.0024 / 0.020, 0.0046, 0.050 | 0.0019, 0.0004, 0.0024 / 0.020, 0.0043, 0.046 | 0.0019, 0.0004, 0.0024 / 0.020, 0.0043, 0.045 |
| rawtoaces (95) | 0.021, 0.0027, 0.0063 / 0.097, 0.014, 0.033 | 0.019, 0.0027, 0.013 / 0.083, 0.021, 0.074 | 0.017, 0.0022, 0.013 / 0.090, 0.019, 0.055 | 0.017, 0.0025, 0.012 / 0.096, 0.019, 0.056 |

- The local prior reduces the skin error by a factor of 3 to 4 and removes most of the bias. A
  global prior that includes skin does not: the global matrix mixes skin with all other
  materials.
- The skin p95 (0.019 red, 0.018 blue) still fails the tolerance. The measured metamer spread
  of skin (section 7.7) is p95 0.011 (red) and 0.014 (blue), so about half of the remaining error
  is the metamer limit of the data.
- With the dataset held out (section 7.2), the local prior is not better for skin. The local
  prior is only as good as the coverage of its training data.

### 7.5 Kernel width of the local prior

Sigma 0.005, 0.01, and 0.02 in u'v' give the same skin result within 0.0001 (table above).
Natural objects are slightly better with 0.005. The default 0.01 is kept; it was set before the
evaluation.

### 7.6 Non-daylight scene lights

[`heldout_reflectance.json`](../../results/p1_spectral_input/heldout_reflectance.json) (E_ref
as reference light) and
[`scene_light_matched.json`](../../results/p1_spectral_input/scene_light_matched.json) (scene
light as reference light). Red Status M error p50, JH, E_ref -> scene light:

| Dataset | A | FL2 | FL11 | LED-B3 | LED-RGB1 | HP1 |
| --- | --- | --- | --- | --- | --- | --- |
| skin | 0.013 -> 0.0029 | 0.100 -> 0.0055 | 0.093 -> 0.0007 | 0.042 -> 0.0021 | 0.026 -> 0.0013 | 0.160 -> 0.0076 |
| natural | 0.0098 -> 0.0090 | 0.110 -> 0.0065 | 0.089 -> 0.0052 | 0.048 -> 0.0082 | 0.040 -> 0.0055 | 0.167 -> 0.0050 |
| USGS | 0.0047 -> 0.0014 | 0.120 -> 0.0014 | 0.092 -> 0.0008 | 0.055 -> 0.0016 | 0.042 -> 0.0010 | 0.181 -> 0.0007 |
| rawtoaces | 0.026 -> 0.028 | 0.097 -> 0.023 | 0.087 -> 0.014 | 0.039 -> 0.028 | 0.047 -> 0.023 | 0.162 -> 0.015 |

The blue channel has the same pattern (for example LED-RGB1 blue p50 0.08-0.10 -> 0.004-0.007).
The local prior gives similar values.

- Under E_ref, every candidate has nearly the same bias under a given light (FL11: signed median
  red +0.078 to +0.096 for all candidates and datasets). The bias belongs to the light, not to
  the candidate.
- Under HP1 (E_ref as reference light), no skin record is inside the Mallett-Yuksel domain: all
  skin colours under high-pressure sodium light are outside the Rec. 709 triangle.
- With the scene light known, the error under fluorescent, LED, and sodium light is as small as
  or smaller than under daylight. A spiky scene light dominates the radiance, and the smooth
  reflectance is easy to reconstruct.
- Mallett-Yuksel is not defined for FL2, LED-B3, and HP1 as reference light: no three
  reflectances in [0, 1] that add up to 1 reproduce the Rec. 709 primaries under these lights
  (linear program infeasible). The other candidates have no such limit.

### 7.7 Metamers

[`metamers.json`](../../results/p1_spectral_input/metamers.json), `plots/metamer_bounds.png`.

**Measured pairs.** 17,794 pairs with Delta E*ab at most 0.5 under D65 (17,337 skin-skin, 190
between datasets). Status M difference between the two spectra of a pair:

| Pairs | p50 | p95 | max |
| --- | --- | --- | --- |
| all | 0.0038, 0.0019, 0.0045 | 0.011, 0.0052, 0.014 | 0.048, 0.013, 0.063 |
| between datasets | 0.0086, 0.0041, 0.016 | 0.025, 0.011, 0.054 | 0.048, 0.013, 0.063 |

The largest red difference (0.048) is between a flower (Gutierrez `Fl_TcapO`) and a skin record
(Lab 53.5, 24.8, 12.1). Two real objects with the same colour give different negatives. No method
that only sees XYZ can separate them; this is the floor of every XYZ-based candidate.

**Linear-program bounds.** For one XYZ (D65), the range of each layer exposure over all
reflectances 0 <= rho <= 1, as negative Status M density:

| Target (Lab) | Red min / true / max | Green | Blue |
| --- | --- | --- | --- |
| flat grey 0.18 (49.5, 0, 0) | 0.39 / 0.91 / 1.21 | 1.32 / 1.44 / 1.55 | 1.62 / 1.83 / 2.08 |
| skin record 3087 (57.1, 9.5, 17.5) | 0.66 / 1.08 / 1.26 | 1.36 / 1.48 / 1.59 | 1.57 / 1.77 / 2.06 |
| leaf `L_BsinG` (41.2, -12.3, 19.8) | 0.28 / 0.75 / 1.17 | 1.23 / 1.35 / 1.47 | 1.14 / 1.54 / 1.98 |
| patch 103 (52.3, -41.5, 21.1) | 0.27 / 0.73 / 1.18 | 1.41 / 1.50 / 1.59 | 1.40 / 1.66 / 2.03 |

The physically possible range is about 0.8 density in red and 0.4-0.8 in blue. The data of
section 7.2 occupy a small part of it. The prior, not the colorimetry, decides the result.

### 7.8 Near black

[`near_black.json`](../../results/p1_spectral_input/near_black.json).

- Grey ramp from 0.18 to 1.8e-13: every candidate in its domain, Q / scale constant within
  1.3e-15.
- Zero input: radiance 0 for every candidate; JH and the non-negative prior mark it outside the
  domain (no chromaticity).
- 10,000 noisy near-black inputs (mean 1e-3, sigma 1e-3 per channel): 852 have Y <= 0 and 3,225
  are outside the spectral locus. Outside the domain: MY 5,735, JH 3,612, prior linear 6,085,
  non-negative prior 3,228, local prior 4,611. No non-finite output.
- **Near-black noise is the main domain failure of all candidates.** Noise gives random
  chromaticities, many of them outside the spectral locus. Because the shape is a function of
  chromaticity, the reconstructed shape of noise jumps between pixels, and its brightness goes to
  zero continuously. The DRT must define what happens to these inputs (open item P1-O4).

### 7.9 Saturated light

[`saturated_light.json`](../../results/p1_spectral_input/saturated_light.json). Each probe has
Y = 0.18. All Gaussian probes are inside the spectral locus; many are outside AP1 (for example
the 500 nm, 10 nm FWHM probe has AP1 (-0.088, 0.291, 0.149)).

| Candidate | Gaussian 10 nm in domain | Gaussian 30 nm in domain | Status M error p50 (10 nm / 30 nm) |
| --- | --- | --- | --- |
| MY, prior linear, prior local | 0 / 31 | 0 / 31 | negative radiance |
| JH | 5 / 31 | 13 / 31 | (0.042, 0.012, 0) / (0.0016, 0.0043, 0) |
| non-negative prior | 30 / 31 (fails at 680 nm) | 31 / 31 | (0.0004, 0.0002, 0) / (0.0027, 0.0025, 0) |

- The non-negative prior reconstructs most narrowband probes to within 0.003 density (p50),
  but not all: at 590-630 nm it spreads the light into the neighbouring layer (green error up to
  0.46 at 600 nm, 10 nm FWHM), and at 690 nm (10 nm FWHM) it moves light from beyond the 680 nm
  end of the published red sensitivity to below it (red error 0.59). A smooth prior cannot
  represent a narrow line exactly.
- CIE lights as scene radiance with E_ref (white surfaces under FL2, FL11, LED-B3, LED-RGB1,
  HP1): every candidate has a red error of 0.05 to 0.18. Section 7.6 shows that this is the
  reference-light assumption.

### 7.10 Camera stage

[`camera_stage.json`](../../results/p1_spectral_input/camera_stage.json). 21 cameras, IDT fitted
on the rawtoaces patches, tested on natural objects, USGS, and 2,000 random ISSA records; priors
without the test dataset. Pooled over all cameras, Status M error p50 (R, G, B):

| D55 | skin | natural | USGS |
| --- | --- | --- | --- |
| IDT Delta E*ab p50 (range over cameras) | 1.10-3.13 | 0.60-1.62 | 0.22-0.71 |
| JH, exact XYZ | 0.0074, 0.0049, 0.020 | 0.0054, 0.0031, 0.027 | 0.0021, 0.0003, 0.0024 |
| JH, camera AP1 | 0.0043, 0.012, 0.041 | 0.0094, 0.0047, 0.028 | 0.0023, 0.0013, 0.0048 |
| prior local, camera AP1 | 0.0092, 0.011, 0.041 | 0.0084, 0.0036, 0.017 | 0.0017, 0.0011, 0.0069 |
| camera-constrained prior (linear) | 0.012, 0.011, 0.044 | 0.0058, 0.0039, 0.018 | 0.0057, 0.0025, 0.0081 |
| camera RGB -> Q matrix (comparison) | 0.014, 0.0034, 0.015 | 0.012, 0.0066, 0.030 | 0.0079, 0.0036, 0.016 |

- The camera doubles the skin green and blue errors. The IDT error on skin (Delta E*ab up to
  3.1 p50 for one camera) is larger than any reconstruction error in XYZ.
- Reconstructing from the camera response (the camera sensitivity and the IDT are known, so AP1
  is a 3x3 of camera RGB) instead of XYZ is not better with a prior that has not seen skin.
- The camera-to-exposure matrix (fitted on the rawtoaces patches, a comparison measurement) is
  better on skin than every reconstruction from AP1. The camera channels carry information about
  the film layers that the IDT to XYZ removes. This is a property of the input, not a
  recommendation of a matrix: section 8, item 4.
- Under A, the same pattern holds; the skin blue error of the priors increases to 0.11 (no
  reference-light correction).

### 7.11 Film sensitivity variant

[`film_sensitivity_variant.json`](../../results/p1_spectral_input/film_sensitivity_variant.json).
With the spectral_film_lut log-linear sensitivity extension (P0 report section 10.4), the
held-out p50 of every candidate changes by at most 0.0002 under D55. The extension matters only
for light above 680 nm (section 7.9), which the reflectances do not have in large amounts.

### 7.12 RAW photos

[`raw_photos.json`](../../results/p1_spectral_input/raw_photos.json). 44 RAW files of 21
cameras of the Alcedo Studio test library (every native RAW file of a camera with a
rawtoaces-data sensitivity; DNG conversions of other files and the Sony YCbCr-compressed file are
excluded). Method: module docstring of
[`run_p1_raw_photos.py`](../../scripts/poc/p1_spectral_input/run_p1_raw_photos.py). LibRaw
decodes camera-native linear RGB; the scene light is selected from the as-shot white balance
(daylight 4000-25000 K, Planckian 2000-4000 K); the IDT maps camera RGB to the scene XYZ (no
chromatic adaptation, no RGC). The statistics use every unclipped pixel at full resolution; the
reconstruction comparison uses 2,000 random pixels per file (a sample count chosen for the run
time of the exact QP, about 13 ms per pixel on real data).

- All 44 files decode. Selected lights: daylight 4300-7800 K (41 files), Planckian 3050, 3700,
  and 3950 K (3 files). White-balance distance (log R/G, B/G): median 0.028, max 0.136.
  Clipped pixels: median 0.06 %, max 8.4 % (`canon/r6/1H1A6888.CR3`).
- **Domain over all unclipped pixels**, per file (median / max over files; files above 0.1 %):

  | Condition | Median | Max | Files above 0.1 % |
  | --- | --- | --- | --- |
  | an AP1 component < 0 | 0.20 % | 21.4 % | 27 |
  | outside the spectral locus (no non-negative spectrum) | 0.065 % | 16.0 % | 18 |
  | outside the Rec. 709 triangle (MY weight < 0) | 1.4 % | 28.9 % | 39 |
  | Y <= 0 | 0 | 6.5 % | 5 |

- **Two sources of pixels outside the spectral locus.**
  - Near-black noise. In the three files with the largest share (`sony/a7rii/DSC00694_ACR.ARW`
    16.0 %, `sony/a7riii/DSC00674.ARW` 4.0 %, `sony/a7rii/DSC00459.ARW` 4.0 %), 86 % to 100 %
    of these pixels are below 1/256 of the clip level. Over all files, near-black pixels are a
    median 3.2 % of the image, and a median 0.31 % of them (max 38.7 %) are outside the locus.
  - Bright saturated colours. In `fuji/xt4/9603741704.raf` (2.2 %), `lumix/gx9/P1012323.RW2`
    (1.2 %), `sony/a6400/DSC00342.ARW` (0.8 %), `canon/r5/Canon-eos-r5-raw-00016.cr3` (0.5 %),
    and `nikon/d850/DSC_0836.NEF` (0.5 %), only 1 % to 9 % of them are near black. These are
    saturated objects that the 3x3 IDT moves outside the locus. A camera is not colorimetric
    (section 7.10), so a real colour can map to an impossible XYZ.
  - `sony/a7rii/DSC00694_ACR.ARW` is the outlier of every statistic (6.5 % Y <= 0). The file
    name suggests a file written by another program; its black level was not checked.
- **Sampled pixels in the domain** (median / min over files): MY 99.0 % / 82.2 %, JH
  99.95 % / 93.0 %, prior linear 98.8 % / 81.4 %, non-negative prior 99.95 % / 95.1 %, prior
  local 99.8 % / 88.2 %. The non-negative prior has the smallest domain loss; its failures are
  inputs outside the spectral locus.
- **Spread of the negative density over the candidates** (max minus min over the candidates that
  are in their domain; per file, median over files): p50 (0.013, 0.0033, 0.020), p95
  (0.044, 0.0093, 0.051); the largest p95 is (0.24, 0.036, 0.089) (`nikon/d810/DSC_7647.NEF`,
  Planckian 3050 K). On real images the candidates disagree by about as much as their held-out
  error (section 7.2). The choice of the reconstruction is visible in the negative.

### 7.13 Effect on the viewed print

[`print_effect.json`](../../results/p1_spectral_input/print_effect.json). The P0 chain is not
calibrated (no couplers, inferred negative dyes, assumed printer light). 300 records per dataset,
D55. Delta E*ab of the print, truth against reconstruction, p50 / p95:

| Dataset | MY | JH | prior linear | prior non-negative | prior local |
| --- | --- | --- | --- | --- | --- |
| skin | 5.6 / 7.1 | 4.4 / 7.4 | 7.3 / 9.1 | 7.3 / 9.1 | 6.5 / 8.8 |
| natural | 4.1 / 16.2 | 4.0 / 17.3 | 3.7 / 13.3 | 4.0 / 13.2 | 4.0 / 12.3 |
| USGS | 1.2 / 6.1 | 0.36 / 3.9 | 0.95 / 5.0 | 0.96 / 5.2 | 0.62 / 6.4 |
| rawtoaces | 4.8 / 18.1 | 5.5 / 20.9 | 2.5 / 16.4 | 3.3 / 20.1 | 3.5 / 13.4 |

- The steep paper (print gamma near 3) amplifies a negative density error of 0.02 to several
  Delta E*ab. A systematic skin bias of +0.02 blue density shows as a visible colour shift on every
  skin tone of the print.
- Not printable with the P0 dye sets (counted in the JSON file): up to 7 records per dataset
  and candidate. Two cases occur: the inferred negative dyes cannot reach a Status M triple
  with low red and high green and blue, and the Endura dyes cannot reach a Status A triple with
  low red and high green and blue (the magenta dye adds red density). This is a domain limit of
  the P0 chain for P2.

### 7.14 Decisions after the first results (U14 to U16)

Three decisions were made on 2026-10-30, after sections 7.1 to 7.13. The criteria of U15 are
therefore not blind to the five first candidates; they were fixed before the first run of
`run_p1_camera_free.py` and are not tuned to its results.

| ID | Decision | Rule |
| --- | --- | --- |
| U14 (P1-O4, delegated by the user) | Near-black and out-of-locus rule | `spectral_locus_projection`: Y <= 0 gives zero radiance; Y > 0 outside the reachable cone moves toward the reference white at constant Y to the cone boundary. The rule is continuous and depends on chromaticity only. It is not RGC. |
| U15 (P1-O5, delegated by the user) | Acceptance criteria per dataset under daylight | Status M error p95 at most (0.025, 0.011, 0.054), the p95 of between-dataset measured metamers: such an estimate is no worse than another real object of the same colour. Signed median at most 0.01: a systematic error is a colour cast on a class of colours. The max is reported and is not a criterion. |
| U16 (P1-O3, user) | No camera identity in the DRT | Camera sensitivities may only simulate the input and build a population statistic. Camera-constrained reconstruction is closed (P1-O2). |

### 7.15 Combined candidate and white-only reference light

[`camera_free/combined_candidate.json`](../../results/p1_spectral_input/camera_free/combined_candidate.json),
[`camera_free/white_only_reference.json`](../../results/p1_spectral_input/camera_free/white_only_reference.json).
Exact XYZ input, D55, prior from the other half of each dataset. p95 / signed median:

| Dataset | JH, E_ref | combined, E_ref | combined, reference from the white | U15 (combined, white) |
| --- | --- | --- | --- | --- |
| skin | 0.012, 0.0084, 0.033 / -0.0075, +0.0049, +0.020 | 0.019, 0.0039, 0.018 / -0.0036, +0.0011, +0.0061 | 0.011, 0.0031, 0.012 / -0.0019, +0.0005, +0.0025 | pass |
| USGS | 0.026, 0.0058, 0.028 / -0.0013, +0.0001, +0.0010 | 0.020, 0.0043, 0.047 / -0.0010, -0.0002, -0.0005 | 0.020, 0.0041, 0.036 / +0.0005, -0.0003, -0.0020 | pass |
| natural | 0.041, 0.019, 0.106 / -0.0018, -0.0005, -0.0076 | 0.036, 0.0096, 0.040 / -0.0002, -0.0019, -0.0075 | 0.033, 0.010, 0.045 / +0.0019, -0.0020, -0.012 | **fail** (red p95, blue median) |
| rawtoaces | 0.146, 0.031, 0.106 / -0.027, +0.0020, -0.0002 | 0.090, 0.019, 0.055 / -0.0088, +0.0009, +0.0072 | 0.084, 0.021, 0.046 / -0.0054, +0.0006, +0.0027 | **fail** (red and green p95) |

With the training data that has no skin (dataset held out), the combined candidate has the skin
bias of section 7.3: (-0.019, +0.0037, +0.023), D55.

The reference from the scene white is the nearest member of the daylight and Planckian family in
u'v'; the spectrum of the light is not used. Signed median, combined candidate, range over the
four datasets:

| Scene | Selected | Red | Blue | With the true spectrum (section 7.6, JH, p50) |
| --- | --- | --- | --- | --- |
| A | Planckian 2850 K | -0.0040 to +0.0007 | -0.0092 to +0.0022 | 0.0014 to 0.028 |
| FL2 | daylight 4200 K | +0.107 to +0.129 | -0.028 to -0.014 | 0.0014 to 0.023 |
| FL11 | Planckian 3950 K | +0.088 to +0.097 | +0.018 to +0.025 | 0.0007 to 0.014 |
| LED-B3 | Planckian 3950 K | +0.045 to +0.054 | +0.070 to +0.082 | 0.0016 to 0.028 |
| LED-RGB1 | Planckian 2800 K | -0.036 to -0.015 | +0.078 to +0.083 | 0.0010 to 0.023 |
| HP1 | Planckian 2000 K | +0.188 to +0.206 | -0.050 to -0.029 | 0.0007 to 0.015 |

The scene white fixes continuous lights only. The large errors under discharge and LED lights stay,
because a white chromaticity does not identify a spectrum. The film response under these lights
is not available from AP1 and a white point.

### 7.16 Held-out camera makers

[`camera_free/held_out_makers.json`](../../results/p1_spectral_input/camera_free/held_out_makers.json).
For each of the 5 makers, the camera population statistic comes only from the other makers; the
input comes from the cameras of the held-out maker, with an IDT fitted on the rawtoaces patches.
Test spectra are the other half of each dataset (skin: 1,000 records). The reconstruction receives
AP1 only. Pooled over the 21 cameras, D55, p95 / signed median:

| Dataset | JH | combined | camera population | U15 (population) |
| --- | --- | --- | --- | --- |
| skin | 0.015, 0.020, 0.060 / +0.0058, +0.012, +0.039 | 0.019, 0.013, 0.036 / +0.0089, +0.0073, +0.021 | 0.013, 0.0076, 0.024 / -0.0006, +0.0007, +0.0048 | pass |
| USGS | 0.028, 0.011, 0.043 / +0.0007, +0.0010, +0.0030 | 0.018, 0.0085, 0.054 / +0.0015, +0.0006, +0.0006 | 0.016, 0.0083, 0.039 / +0.0002, -0.0002, -0.0009 | pass |
| natural | 0.045, 0.035, 0.128 / -0.0003, +0.0010, -0.0030 | 0.028, 0.021, 0.059 / +0.0024, -0.0005, -0.011 | 0.025, 0.015, 0.059 / -0.0004, -0.0010, -0.010 | **fail** (green, blue p95; blue median) |

Under A (reference Planckian 2850 K), the population prior has skin p95 (0.0085, 0.0059, 0.024),
USGS (0.012, 0.0055, 0.032), and natural (0.021, 0.011, 0.064) with blue median -0.010.

The camera error on skin is mostly a shared error, not a camera-specific one: its mean over other
makers removes most of it. This is the generalization that U16 asks for. Limits:

- The population has one IDT method (rawtoaces patches, fitted per light, no chromatic adaptation).
  Alcedo's camera path is not this IDT. The statistic must be built with the actual camera path.
- Only 5 makers and 21 cameras; Fujifilm and Panasonic have one camera each.
- The statistic was computed for the light of the test. Its dependence on the light was not
  measured separately.

### 7.17 The camera population prior: other checks

[`camera_free/camera_population_checks.json`](../../results/p1_spectral_input/camera_free/camera_population_checks.json).

- **Scaling:** max relative error 1.7e-9, above the tolerance 1e-9: **fail**. The error is in the
  NNLS solve. 1.7e-9 is 7e-10 in log10 Q, below any density effect that this report measures.
  The tolerance was not changed.
- **Near black:** no non-finite output and no negative radiance.
- **Input without camera error (exact XYZ, D55), p95 / signed median:** skin (0.018, 0.0092, 0.024)
  / (-0.012, -0.0060, -0.014): bias **fail**. The prior corrects a camera error that is absent.
  USGS passes. Natural and rawtoaces fail the p95 criterion as they do with the other candidates.
  A source that is not a camera (rendered or already colour-managed spectra) needs the combined
  candidate. This is a property of the input source, not a camera identity.

### 7.18 Near-black rule

[`camera_free/near_black_rule.json`](../../results/p1_spectral_input/camera_free/near_black_rule.json).
Combined candidate with the rule.

| Check | Measured | Criterion | Result |
| --- | --- | --- | --- |
| Continuity: output XYZ step / input step, 2,000 lines | 1.0 | 1 + 1e-6 | pass |
| Scaling, all layers | 2.3e-9 | 1e-9 | **fail** |
| Noise: mean density minus noise-free, mean and sigma 1e-3 | 0.0020, 0.0012, 0.0015 | 0.002 | pass (at the limit) |
| Finite output, every input | 0 non-finite | 0 | pass |

The scaling failure is float64 rounding in a very small layer: the worst layer has Q = 3.7e-10
in a sample with largest layer Q = 0.041. Relative to the largest layer of the sample, the error
rounds to 0; on layers above 1e-6 of the largest, it is 3.6e-10 (information, not the predeclared
check). A tighter QP stop does not change it (1e-12: same value; 5e-13: no convergence).

Noise in units of the 18 % grey scale. The mean bias grows when sigma is near the mean, because
the film response is logarithmic and Y <= 0 goes to zero:

| Mean, sigma | Mean density minus noise-free | Density std | Y <= 0 / moved (of 3,000) |
| --- | --- | --- | --- |
| 1e-3, 1e-3 | 0.0020, 0.0012, 0.0015 | 0.0049, 0.0025, 0.013 | 278 / 668 |
| 1e-2, 3e-3 | 0.015, -0.0005, -0.0097 | 0.054, 0.046, 0.066 | 0 / 2 |
| 1e-2, 1e-2 | 0.018, 0.018, -0.018 | 0.12, 0.11, 0.15 | 246 / 749 |
| 5e-2, 1e-2 | 0.0015, -0.0052, -0.013 | 0.064, 0.045, 0.060 | 0 / 0 |
| 5e-2, 5e-2 | -0.11, -0.067, -0.18 | 0.27, 0.23, 0.32 | 253 / 714 |

Calculation for the 5e-2, 1e-2 row: gamma 0.6 and 20 % noise give 0.6 * 0.087 = 0.052 density. The
measured std is of that size, so the chromaticity dependence of the shape does not amplify this
noise much. The spatial appearance was not measured.

Gaussian probes: all 62 in the domain (the 680 nm failure of section 7.9 is solved); 7 moved by the
rule (660-700 nm at 10 nm FWHM, 690 and 700 nm at 30 nm FWHM). p50 (0.0004, 0.0002, 0) and
(0.0060, 0.0023, 0); max (0.59, 0.44, 0.014) and (0.13, 0.27, 0.086).

### 7.19 RAW photos with the rule

[`camera_free/raw_photos_rule.json`](../../results/p1_spectral_input/camera_free/raw_photos_rule.json).
Combined candidate, 44 files, 87,167 random unclipped pixels, E_ref, exposure from the file median.
The camera sensitivity prepares the input (section 7.12); the reconstruction does not receive it.

- Every pixel is in the domain, with finite output and in the characteristic curve.
- 232 pixels (0.27 %) have Y <= 0; 466 (0.53 %) are moved by the rule. Per file: median 0.08 %, max
  10.1 % (`sony/a7rii/DSC00694_ACR.ARW`).
- 1,147 pixels (1.3 %) need the QP; the others use the closed form. Median 23 s per file.
- Difference to JH (median over files): p50 (0.0058, 0.0021, 0.016), p95 (0.037, 0.0077, 0.052);
  largest p95 (0.14, 0.028, 0.10).

## 8. Recommendation

User decision U17 sets the final appearance as the priority and asks for a simple model. This
section replaces the earlier recommendation of the camera population prior.

1. **Use one reconstruction: `measured_prior_local_nonnegative` with rule
   `spectral_locus_projection`.** It has one code path for all input and needs no statistic of a
   camera path.
2. **Reference light:** the nearest daylight or Planckian member to the scene white for RAW input;
   E_ref (the ACES white) for non-RAW input. No other new DRT input.
3. **Do not add the camera population prior.** Known cost: on camera input this route keeps a skin
   bias of about (+0.009, +0.007, +0.021) in negative density (D55, section 7.16). The population
   prior reduces it to (-0.0006, +0.0007, +0.0048), but it needs a statistic of the Alcedo camera path
   and a second prior for non-camera input. Add it only if the user review finds a skin problem
   that the print stage cannot correct.
4. **Use the U15 criteria as guidance, not as a requirement of later steps.** The user review of the
   rendered images decides. The numeric checks of README section 9 that protect the physical
   stages stay (scaling, finite output, stage separation).
5. **For P5, tabulate by chromaticity and reference light.** Only 1.3 % of real pixels need the QP
   (section 7.19).

## 9. Open items

| ID | Item | Owner |
| --- | --- | --- |
| P1-O1 | Combined candidate. **Measured and selected.** | Closed |
| P1-O2 | Camera-constrained reconstruction. **Closed by U16.** | Closed |
| P1-O3 | DRT input. **Decided (U16, U17):** no camera identity; scene white for RAW, ACES white for non-RAW. Open: how the film model reads white-balanced AP1. | P2 |
| P1-O4 | Near-black rule. **Decided (U14).** Appearance in deep shadows is part of the user review. | P2 |
| P1-O5 | Tolerances. **Decided (U15), guidance after U17.** | Closed |
| P1-O6 | RGC: verification, location in Alcedo, and order with rule `spectral_locus_projection` (U13). | after user decision |
| P1-O7 | NIST skin and BCI plant data. Not required after U17; use only if the user review finds a colour problem that points to the prior. | on demand |
| P1-O8 | Camera population statistic on the Alcedo camera path. Not required after U17 (item 3 above). | on demand |

Not measured in P1:

- RGC (U13);
- a GPU or table implementation of any candidate (P5, P6);
- the selected route through the print on real images, and any user review of its appearance;
- white-balanced AP1;
- fluorescent materials (reflectance above 1 is rejected above 1.5 only);
- spatial effects of the reconstruction (noise of the reconstructed shape between pixels).

## 10. Reuse and licenses

- No code was copied. The candidates are implementations from the papers: Mallett and Yuksel
  2019 (spectral primary decomposition), Jakob and Hanika 2019 (sigmoid polynomial), and Nocedal
  and Wright (active-set QP). The 2 max(rgb) normalization rule is from pbrt-v4
  (`RGBIlluminantSpectrum`); no pbrt code is used.
- The film sensitivity variant (section 7.11) uses the spectral_film_lut method ported in P0
  (MIT; [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)).
- The dataset selection follows Fotufilm's notices (reference, README U12).
- The datasets are read at run time and are not distributed. The CC BY 4.0 datasets
  (Gutierrez et al., ISSA) are credited in this report and in THIRD_PARTY_NOTICES.md. No prior
  matrix made from them is committed.
- `reference_white.json` contains the Mallett-Yuksel basis (derived from the CIE tables only).
