# P14: Negative Scan

Date: 2026-11-04 (America/Chicago). Python prototype on the CPU, method `negative_scan` of the Python viewer.

**User decision of 2026-11-05.** This is the final form of the scan. The defaults are no automatic correction (Neutral Scan) and scene light
As Shot. The viewer and the command line start with them (`mvp_pipeline.VIEWER_DEFAULTS`). The user stopped the review rounds: round 2 of
section 5 did not finish, and no further check was run. The port to Alcedo Studio has two phases, the model layer first and then the GPU
passes (issues #661, #664, and #662; PR #663 is done again).

## 1. Question and result summary

The user asked for a new scan method, in two parts (user request of 2026-11-04):

- a **Film Scanner Model**: what a scanner reads from the spectral density of the negative, `I_i = k_i * integral L S_i 10^-D`;
- a **Negative Rendering Model**: how the scan becomes a positive, with a **Neutral Scan** mode that has no automatic correction, and an
  automatic colour that reads the frame, as a separate stage.

The user asked for the stages up to their step P4 (the automatic colour from the frame), and to leave the scanner styles of measured samples
(their step P5) for later. The P13 spectral input is not used.

Result:

- The method runs in the viewer, the CLI, and the review script. All six checks pass on six stocks (section 4).
- The scanner reading through the table agrees with the direct integral on the 1 nm grid to 2e-5 density (largest of 4000 records per stock).
- Neutral Scan keeps the cast of the scene light and the colour of the stock. In daylight it is close to Lab Scan, a little warmer and with
  more contrast; at night it keeps the full tungsten cast (section 5).
- The automatic colour of the first form (a near-neutral estimate only) failed on frames with no neutral: a yellow-green forest and a meadow
  turned blue. The second form adds a white-patch estimate and uses the smaller of the two casts (rule `smaller_cast`). It keeps the forest
  and the dusk light and removes about half of the night cast. The meadow still turns cooler (section 5.2).
- The 3 x 3 matrix that the request proposed is implemented as a labelled comparison only (ROADMAP section 2, point 2). Derived from the
  average layer sensitivities and the AP1 colour matching functions, it *reduces* the saturation (red row 0.71, 0.27, 0.03 on the photo
  stocks), because the red layer of a negative is narrower than the AP1 red.

User decision (2026-11-05): final form, defaults auto off and As Shot.

## 2. Inputs and provenance

- Negatives and their development: the current model of the viewer (profiles of `profiles/`, the rules of P4 to P7), stock character 1.
  The scanner reads the record of the negative after the image-plane steps (spread, halation, inhibition).
- Scene light `as_shot` (P4 rule `light_from_raw_white`, U92 form), so the film sees the light of the RAW white and the cast of the scene is
  on the negative. Spectral input `current`, prior `light_like`, foliage off.
- Product grade before the film: exposure +1.5 EV, contrast +15, saturation 1.3 (`fp.fk.product_grade`).
- Display: OpenDRT 1.0.0 of `display_transforms.py` (P10), with ACES 0.18 shown as 0.18.
- Pools of the generic inversion: the pools of rule `generic_scan` (P10, U98): photo = Portra 400, 160, 800, Ektar 100, Gold 200, C200;
  cine = 5203, 5207, 5213, 5219.
- No scanner vendor data is used. The scanner bands are idealised (section 3.1).
- Photos (local only, not committed): `portrait/P1031513.RW2`, `portrait/1099463.RW2`, `signature_edits/se357.cr2` (dune),
  `signature_edits/se274.dng` (studio, coloured backdrop), `signature_edits/se222.arw` (mountain meadow), `film_emulation/5253219691.rw2`
  (night street, mixed lamps), `night/P1031516.RW2` (dusk concert, lamps), the forest `P2636154.RW2` of P13, `landscape/_DSC4735.ARW`,
  `daylight/5965296318.rw2`. The sample images are from `D:/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw`.

Machine: Intel Core i7-12700H, 31.8 GB, Windows 11, CPU only.

## 3. Method

Code: `scripts/poc/p14_negative_scan/negative_scan.py`, method `negative_scan` of `scripts/poc/p6_mvp_gui/mvp_pipeline.py`.

### 3.1 Film Scanner Model (deterministic)

`I_i = k_i * sum_lambda L(lambda) S_i(lambda) 10^-D(lambda)`, i = R, G, B, on the 1 nm nodes of the model (360 to 840 nm).

- `D(lambda)` is the spectral density of the developed negative: the film base with its mask, plus the three dye amounts of each pixel times
  the dye spectra of the stock.
- Rule `ideal_scanner_bands`: `S_i` is a Gaussian band. Default centres 650, 545, and 450 nm, full width at half maximum 40 nm, cut below
  1e-4 of the peak (nodes 378 to 722 nm). These are inferred values for an idealised scanner. They do not describe a Frontier or a Noritsu,
  whose responses are not published.
- `L` is a halogen lamp (Planckian, 3200 K) or an equal-energy light. `k_i` normalises each channel to the empty film holder.
- The negative has three free dye amounts per pixel, so the reading is a table over the negative record (the table of `ScanPreview`, P3,
  built by the C++ library of P7), read by trilinear interpolation.

### 3.2 Negative Rendering Model

Each correction happens once. No later stage repeats an earlier one.

| Stage | Rule | Depends on |
| --- | --- | --- |
| a | `base_relative_density`: `D_i = log10(I_i,base / I_i)` | the scan |
| b | `generic_density_inversion`: `x_i = contrast * (D_i - D_i,aim) / gamma_i`, `E_i = 0.18 * 10^x_i` | gamma: the medium; D_aim: the stock |
| c | `frame_auto_colour` (off in Neutral Scan) | the frame |
| d | exposure (stops), cyan, magenta, and yellow keys (log10 of the positive) | the user |
| e | `black_at_film_base`: `E' = 0.18 (E - b E_base) / (0.18 - b E_base)` | the film base after b to d |
| f | positive primaries: the channels as linear AP1, or the comparison matrix | the medium |
| g | OpenDRT, native grey | none |

- **gamma** is the channel density per log10 exposure of the 18 % grey (central difference at 0.09 and 0.36) of the average negative of the
  medium, each stock under its balance light. It is the same for all stocks of a medium. So the inversion is a straight line: it does not
  undo the toe, the shoulder, the crossover, or the contrast of a stock. Photo: 0.562, 0.559, 0.620 (R, G, B). Cine: 0.478, 0.546, 0.528.
  Values per stock are in `results/p14_negative_scan/checks.json`.
- **D_aim** is rule `stock_balance`: the channel density of the 18 % grey under the balance light of the stock (D55 or T3200). A lab
  scanner has one channel set-up per film type. This is the only stage that depends on the stock.
- **Black at the film base** (b = 1 by default) subtracts the positive of the unexposed film per channel and keeps the grey at 0.18. With
  b = 0, the black of a plain inversion is lifted (about -3.9 stops for Portra 400).
- **Positive primaries.** Default `channels`: the three positive channels are taken as linear AP1. The comparison `film_primaries` is a
  matrix M with rows that sum to 1 (the balance grey stays neutral). It minimises the spectral difference between M times the average layer
  sensitivities of the medium and the AP1 colour matching functions, both under D55, each channel normalised. It is not fitted to a chart,
  and it is the same for all stocks of a medium. ROADMAP section 2 forbids a matrix as a film stage; this one is a stage of the scanner
  software, and it is shown for review only.

  | Medium | Row R | Row G | Row B |
  | --- | --- | --- | --- |
  | photo | 0.706, 0.267, 0.027 | 0.086, 0.992, -0.078 | -0.003, 0.028, 0.975 |
  | cine | 0.606, 0.316, 0.078 | 0.073, 0.919, 0.009 | -0.015, 0.009, 1.006 |

  The positive off-diagonal terms reduce the saturation, mostly in red.

### 3.3 Rule `frame_auto_colour`

This is the only stage that reads a statistic of the frame. Constants (inferred, not measured):

1. Prescan: stage b reduced by area to a long edge of 96 pixels. Only pixels with a mean log10 between -1.6 and +0.9 about the grey count
   (no deep shadow, no clipped light).
2. Near-neutral estimate: `u = x - mean_c(x)`. Start at the median of u, then four times: weight `exp(-|u - m|^2 / 0.12^2)`, m = the weighted
   mean of u.
3. White-patch estimate (second form): the median of u over the brightest 5 % of the valid pixels.
4. Rule `smaller_cast` (second form): use the estimate with the smaller length.
5. Correction: along the light axis (the change of stage b of a grey from T3200 to D65 for this stock), remove the share `strength`
   (default 0.8) of the cast. Across it (green-magenta), remove `0.5 * strength`, to limit subject failure. `warm` and `cool` keep +0.04 or
   -0.04 log10 along the axis.
6. Optional auto density (default 0, off): the share of the weighted mean level that moves to the grey.

The product needs one reduction pass over a small copy of the frame before the per-pixel pass. Values below 0 after stage e are counted
(`positive_below_0` in the record of each render) and set to 0, because the display transform needs a non-negative input.

### 3.4 Controls

In the window (group "Negative scan") and on the CLI: scanner centres and width, scanner light, scan contrast, scan exposure, C/M/Y keys,
black at film base, auto colour (off, neutral, warm, cool), auto colour strength, auto density, and positive primaries. The rendering
controls act after the scan and do not build the table again (check F).

## 4. Checks (`check_negative_scan.py`)

The tolerances were set before the run. Stocks: Portra 400, Gold 200, Ektar 100, C200, 5207, 5219. Result file:
`results/p14_negative_scan/checks.json`. All checks pass on all six stocks.

| Check | Behaviour | Tolerance | Result |
| --- | --- | --- | --- |
| A | scanner table against the direct integral, 4000 random records | p99 <= 0.002, max <= 0.01 density | p99 and max <= 2e-5 |
| B | 18 % grey under the balance light gives 0.18 per channel | 1e-9 relative | pass |
| C | film base gives 0 with black 1 | 1e-12 | pass |
| D | auto shift of a uniform balance-grey frame | 1e-9 log10 | pass |
| E | auto keeps 0.2 of the cast along the light axis and 0.6 across (strength 0.8) | 1e-6 log10 | pass |
| F | a rendering control keeps the scan object | identity | pass |

Recorded with no limit (stock character, not a fault): the channel spread of a neutral ramp under the balance light, in stops, at -4 to +4
stops about the grey.

| Stock | -4 | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Portra 400 | 0.47 | 0.16 | 0.03 | 0.02 | 0 | 0.03 | 0.10 | 0.16 | 0.23 |
| Gold 200 | 1.51 | 0.51 | 0.27 | 0.18 | 0 | 0.14 | 0.13 | 0.11 | 0.09 |
| Ektar 100 | 0.47 | 0.19 | 0.23 | 0.14 | 0 | 0.05 | 0.16 | 0.22 | 0.27 |
| C200 | 0.56 | 0.32 | 0.15 | 0.08 | 0 | 0.14 | 0.27 | 0.40 | 0.53 |
| 5207 | 0.24 | 0.12 | 0.00 | 0.01 | 0 | 0.01 | 0.02 | 0.03 | 0.07 |
| 5219 | 0.20 | 0.09 | 0.01 | 0.01 | 0 | 0.00 | 0.03 | 0.07 | 0.09 |

The photo stocks keep their crossover, because gamma is the average of the medium. The black at the base enlarges the spread in the deep
shadows (Gold 200 at -4 stops), because the channels approach 0 at different exposures.

## 5. Review sheets (`render_negative_scan_review.py`)

One sheet per photo, rows = Portra 400, Gold 200, Ektar 100, 5207; columns = Lab Scan (current default of method `apd`), Negative Scan Neutral,
Negative Scan Auto neutral, Auto neutral with the comparison matrix. Each panel has the stock, the method, and the scene light. Four sheets
`scanner_*.jpg` show Portra 400 with other scanner bands and black 0. Round 1 is kept in `build/tmp/p14/review_round1/`. Round 2 (the second
form of the auto colour) was stopped before it finished, so the sheets in `build/tmp/p14/review/` are a mix of the two rounds. Timing: about 7 seconds per photo and stock for the four columns at a long edge of
1400 pixels, with a new model for each photo (the as-shot light of each photo is part of the model).

### 5.1 Observations of round 1 (Claude, not a user review)

- Neutral Scan: in daylight and in portraits it is close to Lab Scan, a little warmer and with deeper blacks. On the night street (as-shot
  4138 K) it keeps the full orange cast of the lamps. On the studio frame (se274) the backdrop is bluer than on Lab Scan.
- The photo stocks still look alike on Neutral Scan, as on Lab Scan (ROADMAP section 2, point 6).
- Auto neutral, first form: it removes most of the night cast, but it turns the forest and the meadow blue-cyan and the white water blue,
  and it turns the blue backdrop of se274 toward purple. The near-neutral estimate locks on the dominant colour when the frame has no neutral.
- The comparison matrix gives lower saturation and cooler, pinker skin.
- Scanner bands (Portra 400, Neutral Scan): 80 nm bands read more of the other dyes, so the colours are softer and cooler; 20 nm is close to
  40 nm; the red band at 620 or 690 nm changes the skin and the reds; black 0 gives the lifted, soft black of a plain inversion.

### 5.2 Second form of the auto colour

Casts used (log10, R, G, B), Portra 400:

| Photo | Near-neutral estimate | White-patch estimate | Used |
| --- | --- | --- | --- |
| forest P2636154 | 0.154, 0.134, -0.288 | 0.021, -0.005, -0.016 | white patch |
| night street 5253219691 | 0.169, 0.000, -0.169 | 0.117, -0.007, -0.110 | white patch |
| dusk concert P1031516 | 0.126, -0.029, -0.097 | 0.013, -0.026, 0.013 | white patch |
| dune se357 | 0.111, 0.010, -0.120 | 0.084, 0.011, -0.096 | white patch |
| meadow se222 | 0.155, 0.087, -0.242 | 0.187, 0.062, -0.249 | near-neutral |
| studio se274 | -0.223, 0.000, 0.223 | -0.251, 0.063, 0.188 | near-neutral |

The forest and the dusk light are kept; the night street keeps part of its warmth. The meadow and the studio backdrop still change, because
their bright areas have the same colour as the rest (a warm, hazy sky; a coloured backdrop). This is subject failure of an automatic scan, and
the Neutral mode, the strength, and the warm mode are the user's controls for it. Sheets: `build/tmp/p14/probe/auto2.jpg` (probe) and the
round 2 sheets.

## 6. Decision and recommendation

- User decision (2026-11-05): this is the final form. Defaults: auto colour off (Neutral Scan), scene light As Shot, positive primaries
  `channels`, scanner 650/545/450 nm, 40 nm, halogen, black 1.
- The comparison matrix stays out of the default.
- The scanner bands are a real control of the look (section 5.1). Measured scanner data (the request's step P5) would replace the
  idealised bands.

## 7. Open items

- The port: phase 1 (model layer, issue #661), phase 2 (CUDA and OpenCL, issue #664; Metal, issue #662). The resources of schema 10
  (section 9) are in place.
- Scanner styles from measured samples (the request's step P5) are not done. The test needs an unprocessed high bit-depth scan and the lab
  JPEG of the same negative; the only real film data of this lab is the 5207 strips of P12, scanned on a Hasselblad X5.
- The C++ resources have the method from schema 10 (section 9). The product builds the scanner table on the host, as the APD table of P7.
- Not measured: GPU time and memory, cine stocks other than 5207 on the sheets, reversal films (the method is for negatives), stock character
  other than 1.

## 9. Product resources, schema 10 (issue 661)

`p7_spectral_acceleration/build_product_resources.py` writes the values of Negative Scan in place of the Lab Scan forms of schemas 8 and 9
(the ADX arrays, the printing paper, and the LAD aim are removed). Lab commit fb785ef; the run took 762 s.

- Bundle: the default scanner (`common/negative_scan_centres_nm`, `_width_nm`, `_band_cut`, `_lamp_kelvin`, `_planck_c2_nm_k`), D_base per
  negative (`negative/<n>/scan_base_density`), the gamma of each medium (`scan_medium/<m>/gamma`), and the spectra D55, T3200, and D65.
  The metadata gives each negative its medium and its balance light, and `negative_scan` gives the identifier, the name, the default light,
  the axis lights, and the pool of each medium with the scene light of each pool stock.
- Setup: `negative_scan_aim_density` and `negative_scan_light_axis`, (negatives, scene lights, 3). Both depend on the light, because the
  layer gain of a stock that is not relative to its balance light differs under `reference`.
- The grey records of the stored values use the point form of the lab (16 steps of rule `development_inhibition`). The product derives the
  values again for a scanner other than the default, with the same form.

Checks of the run (limits of the script):

| Check | Largest value | Limit |
| --- | --- | --- |
| Setup values against the model, 10 selections | 0 | 1e-9 |
| Scanner table nodes against the model, 8 tables | 2.7e-15 | 1e-12 |
| Grid blend of As Shot, print 5207 on 2383 | 0.104 code | 0.5 code |
| Grid blend of As Shot, scan, 4 negatives | 0.0028 stops | 0.03 stops |

Expected values for the product tests (`build/tmp/p7/product_resources/expected`):

- `scan__<negative>__<light>.bin`: the scanner table, the record grid, the default scanner weights, D_base, D_aim, the light axis, gamma,
  and the layer gain, for 5207, Portra 400, and Ektar 100 under `reference` and 5219 under `daylight`.
- `scan__<negative>__cct<K>.bin`: the blend of two grid lights (5219 at 5650 K, 5207 at 3100 K).
- `scan__scanner_b.bin`: a second scanner (630/530/460 nm, 60 nm, equal energy). Its gamma is cine 0.42353, 0.53584, 0.50498 and photo
  0.46778, 0.54907, 0.57709; the file also has D_base, D_aim, and the light axis of the four negatives under `daylight`.
- `scan__auto.bin`: rule `frame_auto_colour` on two frames of x (257 x 391), with five cases each. Frame a takes the near-neutral estimate;
  frame b (a near-neutral band of sky over a strong cast) takes the white-patch estimate.
- `display/scan__*__auto_<off|neutral>.bin` (`build_display_expected.py`): a neutral ramp of 241 values and the chart of 180 + 3916 values,
  as linear AP1 with the shift and the prescan. `image/scan__*` (`build_image_expected.py`): the linear AP1 of the RAW frame of the image
  tests.

## 8. Commands

```powershell
$P = "build/tmp/p6/venv/Scripts/python.exe"
& $P -I scripts/poc/p14_negative_scan/check_negative_scan.py
& $P -I scripts/poc/p14_negative_scan/render_negative_scan_review.py
```
