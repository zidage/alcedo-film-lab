# P3: Scene presets and scanned-negative output

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P3, with decisions U21, U22 (scene choice) and
U23 (scan, ADX, ACES output). Source audit: [modern film workflow](../research/modern_film_scan_workflow.md).
**Date:** 2026-10-30.
**Status:** closed for now (2026-10-30). Both parts run on real files and the numeric checks pass. The user review of the look does not accept the result: the soft settings of APD do not look like film, and the colours are strange. These items move to [P4](p4_physical_film_response.md). Sections 10 to 13 record the later work, and section 2 summarizes the first runs.

> **Renders are local only.** `build/tmp/p3/renders/`. They contain photos and are not committed. The commands are in the
> [script README](../../scripts/poc/p3_scan_and_scene/README.md).

## 1. Question

(a) Can the product offer a scene choice in place of one light, when a night scene mixes tungsten, LED, and sodium?

(b) Can a digital intermediate path be simulated: the negative of P2, a scanner, an ADX encoding, and an ACES 1.3 or 2.0 output, in
place of a 2383 print?

## 2. Result summary

- **The scan path runs and meets each numeric limit** (section 5). The ADX transform of this lab agrees with the OpenColorIO
  built-in within 5.9e-5, and a grey lands at code value 445 within 0.5.
- **The stocks do fit ADX10.** No pixel is below 0, and at most 0.0005 % of the pixels of any test image are above 1023.
- **The ACES output is darker than the print path as specified.** ACES 0.18 shows at 10 % of the display peak, and the print path shows the same
  grey at about 22 %. Median L* of the portraits is 28 against 34. A neutral scanner light of +0.37 stops (ACES 1.3) or +0.53
  stops (ACES 2.0) matches the grey. This value is a review control.
- **The scan path has less chroma and a different hue than the print path.** At a matched grey, the mean C* p95 of the portraits is 34.0 (ACES 2.0) or 38.2 (ACES 1.3)
  against 43.5 for the print of 5207. By the author's eye, yellow moves toward green and skin is cooler. Delta E p50 against the print is 8.2 (ACES 2.0) and 7.0 (ACES 1.3).
  This agrees with the inference of the source audit: the transform has no print stock. The cause of the hue change was not isolated.
- **Neither path separates 5207 and 5219 strongly when each stock is timed to a neutral grey.** Delta E p50 is 0.88 (print) and 0.60 to 0.75 (scan) on the portraits.
  With timing below 1, the scan shows the tungsten stock in daylight with a red toe (section 6.4).
- **A scene mixture is exact in the layer exposure and reduces the error on signs, but it does not remove it.** Against daylight, the
  hue of the most chromatic pixels (mostly signs and lamps) changes by 15 degrees with sodium alone and by 6 degrees with `street_mixed`
  (section 7). Scene definitions are the author's choice.
- **Real scans of developed negatives behave differently from the ADX to ACES path** (section 10): bright mid-tones, chroma that falls with overexposure and stays high with underexposure, and a look that changes with the scanner. A third path, per-channel direct inversion, follows part of this behaviour. These paths are creative renderings, so the choice between them comes from the user review of the images and not from a chart score.
- **User decision (U26, U27):** the ADX to ACES path is dropped. The product direction keeps the print model and the classic scan (direct inversion), and the errors of a scanner are wanted. Section 11 has the first scanner styles. Sections 5 to 6 stay as the record of the dropped path. User review of the styles is open.

## 3. Inputs and method

**Images.** 14 portraits and 6 night files of the P2 report, through `product_input()` (exposure rule of P2, default grade of the product). Machine: as in the P2 report, CPU only.

**Scan stages** (`aces_scan.py`):

| Stage | Method | Source or status |
| --- | --- | --- |
| Negative | `FilmPreview.negative_image()`, darkroom options of P2, enlarger flare off | P2 |
| Scanner | Rule `ideal_apd_scanner`: equation 1 of ST 2065-2 at its 2 nm nodes, table of 65 nodes per axis over negative Status M | Published responsivities; represents the standard, not a machine |
| Encoding | Equation 2 of ST 2065-3: scale (1.00, 0.92, 0.95), 500 per density, D-min at 95, clip counted | Published. No rounding, because a float pipeline carries the value |
| D-min | APD of the P2 base density | Inferred from the data of the stock |
| Grey | Rule `adx_lad_aim`: offset so that an 18 % grey of the balance light is at code value 445. Share `timing` of the scene light cast is removed | Control. 445 is published; the offset stands for scanner lights or a first grade |
| Exposure | Option `exposure_stops`: neutral scanner light, 82.8 code values per stop | Control |
| ADX to ACES | Port of `ACEScsc.Academy.ADX10_to_ACES` | aces-dev v1.3.1, A.M.P.A.S. license |
| Output | OpenColorIO 2.6 built-ins, `SDR-VIDEO_1.0` (ACES 1.x) and `SDR-100nit-REC709_2.0` (ACES 2.0), then `CIE-XYZ-D65_to_sRGB` | OCIO implementation; not compared with the CTL or the product in this step |

**Path B** is the print of P2 from the same negative. A pixel of the negative has three free dye amounts, so ADX10 and negative Status M hold the same information where ADX10 does not
clip, and section 6.1 shows that almost no value clips. So "scan, then the print model" gives the same result as this path. The lab did not implement it as a separate route.

**Scanner fields.** Public: the responsivities, the influx spectrum, the encoding, the transform. Inferred or not used: the D-min of a roll (one base density here), scanner flare, lens, and noise. No machine is modeled.

**Source correction.** The [source audit](../research/modern_film_scan_workflow.md) did not state the scale (1.00, 0.92, 0.95) of the encoding. The standard has it, and the ACES transform reads code values without removing it.

## 4. Sources and licenses

| Item | Result |
| --- | --- |
| APD responsivities | ST 2065-2:2020, element `st2065-2a-2020.csv`, public download, SMPTE copyright, read at run time and not committed. Hashes: [`sources.json`](../../scripts/poc/p3_scan_and_scene/sources.json) |
| Same table in spectral_film_lut | Equal after normalization at all 186 nodes (360 to 730 nm), difference 0 ([`apd_table_comparison.json`](../../results/p3_scan_and_scene/apd_table_comparison.json)) |
| ADX encoding | ST 2065-3:2020, not committed |
| ADX to ACES | aces-dev tag v1.3.1. The license at this tag is the A.M.P.A.S. license, not Apache-2.0. Its notice is in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md) |
| Output transforms | OpenColorIO 2.6.0 (BSD-3-Clause), Python package, not redistributed |

## 5. Numeric checks

[`scan_checks.json`](../../results/p3_scan_and_scene/scan_checks.json), `check_scan_path.py`. The limits were set before the first run. All pass in the first run.

| Check | Limit | Result |
| --- | --- | --- |
| Encoding at APD above D-min 0 and 1: (95, 95, 95), (595, 555, 570) | error <= 1e-9 | 0 |
| Port of ADX to ACES against OCIO, 62,632 values | relative error <= 1e-3 | 5.9e-5 |
| Code value 445 gives ACES 0.18 | relative error <= 1e-4 | 1.0e-5 |
| APD table against the stages, 2,000 random densities | p95 <= 0.002, max <= 0.01 | Largest of the 3 stocks: p95 4.0e-5, max 0.0081 |
| Neutral ramp, table against the stages | max <= 1 code value | Largest of the 3 stocks: 0.63 |
| Grey at timing 1 | 445 +- 0.5 | pass on the 3 stocks |
| Layer exposure of a mixture against the weighted sum | relative error <= 1e-9 | pass on the 5 scenes |

`check_fast_kernels.py` of P2 passes after the change to `film_preview.py` (function `negative_image()`).

**ADX10 of an 18 % grey, without the offset:**

| Stock, light | R, G, B | Offset to 445 |
| --- | --- | --- |
| Portra 400, E_ref | 517.3, 475.6, 536.8 | -72.3, -30.6, -91.8 |
| 5207, D55 | 478.7, 485.9, 466.3 | -33.7, -40.9, -21.3 |
| 5219, T3200 (balance light) | 457.1, 467.5, 448.3 | -12.1, -22.5, -3.3 |
| 5219, D55 | 415.1, 482.5, 531.2 | +29.9, -37.5, -86.2 |

The 5207 and 5219 values are near the aim by their own balance light. This is a check on the data, with no fit: the cine stocks were not set against ADX.

**Neutral ramp in ACES, with the offset (R, G, B):**

| Scene value | Portra 400 | 5207 | 5219, D55, timing 1 |
| --- | --- | --- | --- |
| 0.0028 | 0.0000, 0.0001, 0.0000 | 0.0004, 0.0003, 0.0005 | 0.0028, 0.0006, 0.0001 |
| 0.045 | 0.0362, 0.0408, 0.0369 | 0.0459, 0.0447, 0.0474 | 0.0449, 0.0434, 0.0462 |
| 0.18 | 0.18, 0.18, 0.18 | 0.18, 0.18, 0.18 | 0.18, 0.18, 0.18 |
| 1.44 | 1.81, 1.51, 1.73 | 1.25, 1.32, 1.21 | 1.29, 1.34, 1.24 |
| 11.52 | 17.8, 12.7, 16.7 | 7.06, 8.05, 6.70 | 7.94, 8.68, 6.36 |

The universal transform does not make a neutral stay neutral on a stock that differs from its generic response. Portra has magenta highlights, with a large gap above the grey. This path has no correction for this, as the
transform is specified. A rule like `neutral_printing_gain` of P2 is not added, because the user asked for this path as it is, and it was not reviewed yet.

**Red record above 700 nm.** The APD red responsivity peaks at 692 nm, and the published negative density stops at 700 nm. On the midscale neutral, 16 % to 21 % of the red signal comes from above 700 nm. With a different density rule (`hold` in place of the Gaussian tails), grey moves by at most 1.1 code values. So the rule has a small effect on this measure. Colours were not tested.

## 6. Scan review

[`scan_review.json`](../../results/p3_scan_and_scene/scan_review.json), `render_scan_review.py`. Scene light D55, timing 0.75 unless stated. Mean of the images.

### 6.1 Range of ADX10

Below 0: no pixel on any image. Above 1023: none on 5207 and on the portraits, and at most 0.00045 % on one night file of 5219, with the matched scanner light. This answers the open item of the audit for these images and stocks.

### 6.2 Appearance values

| Set | Path | L* p5 / p50 / p95 | C* p50 / p95 | Display values outside 0-1, worst image |
| --- | --- | --- | --- | --- |
| Portraits, 5207 | Print | 5.9 / 34.0 / 71.9 | 18.3 / 43.5 | not comparable: P2 compresses before its clip |
| | ACES 1.3 | 2.4 / 27.8 / 73.0 | 13.5 / 36.9 | 20.6 % |
| | ACES 2.0 | 2.2 / 28.3 / 64.9 | 12.1 / 32.3 | 0.04 % |
| | ACES 1.3 matched | 4.0 / 33.9 / 78.6 | 14.3 / 38.2 | 13.3 % |
| | ACES 2.0 matched | 4.8 / 36.1 / 71.9 | 12.7 / 34.0 | 0.18 % |
| Night, 5207 | Print | 6.3 / 26.8 / 70.4 | 14.9 / 47.5 | |
| | ACES 1.3 matched | 4.6 / 26.4 / 77.1 | 11.6 / 39.2 | 2.4 % |
| | ACES 2.0 matched | 5.6 / 29.5 / 71.4 | 11.4 / 38.9 | 2.1 % |

Values outside the display range are clipped and counted. The file holds both stocks and the values per image.

- Among the portraits with ACES 2.0 matched, `se348`, `se376`, and `se086` have the largest loss of C* p95 (for example 44.5 to 24.5 on `se348`). `se159` has none, and on `_DSC8169` the C* p95 rises (47.2 to 57.7), because the green sign stays more saturated.
- The product grade adds contrast and saturation before the film. `DARKROOM` takes back the contrast with `print_contrast`, which the scan does not use. The scan path has no such control, and its contrast was not tuned.

### 6.3 Author's visual results

This is not user review. Files `se002`, `se019`, `se231`, `_DSC8169`.

- Skin is less warm than in the print path, with magenta in the shadows of dark skin (`se002`).
- Saturated yellow moves toward green, so a sunflower field (`se019`) loses the gold of the print. Cyan (`se002`) also moves toward green.
- Grey walls lean purple (`se002`), in the direction of the ramp above.
- The green sign of `_DSC8169` is more saturated than in the print, which shows it as pale mint.

### 6.4 Difference between stocks

Delta E*ab p50 / p95 between the images of one path, timing 1, so a neutral grey in both stocks.

| Pair, set | Print | ACES 2.0 | ACES 1.3 matched | ACES 2.0 matched |
| --- | --- | --- | --- | --- |
| 5207, 5219; portraits | 0.88 / 1.77 | 0.60 / 1.43 | 0.75 / 1.71 | 0.70 / 1.80 |
| 5207, 5219; night | 0.90 / 1.77 | 0.57 / 1.33 | 0.67 / 1.66 | 0.65 / 1.70 |
| Portra 400, 5207; portraits | 7.31 / 13.0 | 4.74 / 9.48 | 5.76 / 8.71 | 5.78 / 10.1 |
| Portra 400, 5207; night | 6.35 / 12.8 | 5.07 / 8.60 | 5.78 / 9.02 | 6.22 / 9.77 |

The Portra pair of the print path also has a different paper, so this row is not only the negative. The same pair through the scan has no paper, and most of the difference stays. The 5207 and 5219 pair keeps 63 % to 85 % of the difference (p50) of the print path. The difference of this pair is small in both paths: P2 gives each stock its own balance, and most of the visible character comes from the scene light with a timing below 1.

With timing 0.75 under D55, 5219 keeps its cast through the scan. The red offset of +29.9 code values also lifts the D-min of the red record, which gives a red toe in the ramp (0.0028 against 0.0001 for blue at scene value 0.0028). On `_DSC8169` the road and the wall become maroon. It is the strongest visible defect of the scan path on night files with this stock, and it needs a user decision (section 9).

## 7. Scene presets

Definitions: `SCENE_PRESETS` of `film_preview.py`. The weights are shares of luminance, and the author chose them. They are not measurements of a place. Rule `scene_mixture`: a weighted sum of named spectra, each with Y = 1.

| Scene | Spectra and weights | Grey on the 5219 curves, stops (R, G, B) |
| --- | --- | --- |
| `street_mixed` | T2800 0.3, LED-B3 0.4, HP1 0.3 | -0.33, -0.14, -0.46 |
| `street_sodium` | HP1 0.7, T2800 0.15, LED-B3 0.15 | -0.46, -0.42, -1.14 |
| `street_led` | LED-B3 0.75, T2800 0.15, HP1 0.1 | -0.46, 0.02, -0.08 |
| `interior_warm` | T2800 0.7, LED-B3 0.3 | -0.02, -0.01, -0.26 |
| `interior_office` | FL11 0.5, LED-B3 0.5 | -0.67, 0.19, 0.26 |

**Result.** [`scene_review.json`](../../results/p3_scan_and_scene/scene_review.json), `render_scene_review.py`, 6 night files, 5219 + 2383, timing 0.75. Hue change: against the daylight panel, for the 1 % most chromatic pixels. In these files, they are mostly signs and lamps; this was checked by eye on `_DSC8169` only.

| Panel | C* p50 / p95 | Hue change p50 / p95 (degrees) |
| --- | --- | --- |
| Daylight (D55) | 12.4 / 42.7 | 0 / 0 |
| Sodium alone (HP1) | 15.2 / 46.4 | 15.0 / 29.1 |
| `street_mixed` | 14.3 / 46.6 | 6.1 / 14.4 |
| `street_sodium` | 14.9 / 46.6 | 9.7 / 21.9 |
| `street_led` | 13.6 / 46.2 | 5.4 / 12.2 |
| `interior_warm` | 14.8 / 47.2 | 3.4 / 9.5 |
| `interior_office` | 13.4 / 45.5 | 3.1 / 7.5 |
| `street_mixed`, scan, ACES 2.0 matched | 10.4 / 37.6 | 5.4 / 11.1 |

Author's visual result on `_DSC8169`: the red sign is orange under sodium alone, and it stays red with a slight orange shift under `street_mixed`. No user review was made. A smaller hue change means less error on a sign. It does not show a better look for lit surfaces, which should change under a light.

**What a global mixture cannot do:**

- It applies one spectrum to every pixel. A wall under a sodium lamp and a shop under LED light get the same mixture, so no local colour of light appears.
- It treats a lamp or a sign as a reflecting surface under the mixture. The mixture reduces this error because it dilutes the strongest spectrum, not because it finds the emissive parts.
- A real weight depends on the place in the image and on the exposure. The fixed weights do not follow them.
- The input is already white balanced. The mixture simulates a light; it does not recover the real lights of the photo.

**Product cost.** The layer exposure is linear in the spectrum (checked in section 5), so a scene can blend Q / Y tables of its lights and needs no new reconstruction. The print table depends on the printer balance of the scene: about 2.5 s on CPU per new scene (P2 report, section 8.4).

## 8. Not measured

- Comparison with a real scanner of our own or real footage of these stocks. Section 10 compares with public chart measurements only.
- The output transforms against the ACES CTL, and against the `Aces20` method of Alcedo Studio.
- Film grain, gate weave, scanner flare, and noise.
- Rounding to 10 bits and any banding.
- A scan through ADX16 (not needed for range on these images).
- GPU execution and the cost of the APD table outside this CPU tool. The first build of one APD table takes about one minute on CPU with the array solve, and no kernel exists for it. P6 owns this.
- Colour-dependent effect of the density rule above 700 nm.
- Display white and viewing adaptation of the two paths: the print has its own white and paper, the scan has the white of the transform.

## 9. Recommendation and open items

User decision (U26): print and classic scan. Section 11 lists the scanner data and the next work.

| ID | Item | Owner |
| --- | --- | --- |
| P3-O1 | Review of the scan path against the print path: accept the lower chroma and the shift of yellow and skin, or request a correction. | User |
| P3-O2 | Red toe of 5219 under D55 with timing below 1: keep as character, or limit the offset to the middle of the curve. | User |
| P3-O3 | Review of the five scenes, their names and weights. Single lights of P2 stay available. | User |
| P3-O4 | Contrast of the scan path after the product grade. The print takes it back with `print_contrast`. | P3, after P3-O1 |
| P3-O5 | Portra 400 through ADX: magenta highlights on the ramp. Decide if Portra is offered in this path. | User |
| P3-O6 | Compare the OCIO ACES 2.0 output with the product `Aces20` method on the same ACES values. | P3 |
| P3-O8 | Direct inversion: accept it as the scan look, and tune it for the product grade (contrast, yellow) after this review. | User, then P3 |
| P3-O9 | Underexposed chroma and lifted blacks (section 10.5). | P3, on request |
| P3-O10 | Cause of the strong crossover of real 5219 in daylight. The slope test failed. | P3 |
| P3-O7 | ALEV III estimate as a light-table camera (U23). It is not an ARRISCAN (see the audit). Not started; scanner candidates need data that the audit did not find. | On request |

## 10. Direct scanning: real measurements and a direct inversion path

The user pointed to [Film Analyzer](https://filmanalyzer.talkativephotographer.com/browse/kodak-5207-vision3-250d) on 2026-10-30, as a view of the common practice today: a developed negative is scanned directly, with no print. The user asked to learn from it and not to adopt its data. The model is not fitted to it.

**Source.** Public pages of that site, read through its public session on 2026-10-30. It shows a 24-patch chart (Calibrite ColorChecker Passport Photo 2, reference Lab under D50) in a bracket of -2 to +2 stops, per film and per scanner. The site does not state a license, so the measurements stay in `build/tmp/p3/filmanalyzer/`. The results file holds only differences to the paths. The few values below are quoted with this source. The partner API of the site needs a key and was not used. The site does not state the light, the lens, or all inversion settings of these frames in the parts read here.

### 10.1 What real scans do

`compare_film_analyzer.py`, values from `real_summary.json` (local). Sets: 5207 on a Nikon Super CoolScan 9000 ED and on a Fujifilm X-T5, 5219 on the CoolScan, Portra 400 on the X-T5. These 4 sets have measurements. The 5219 set on the X-T5 and the Portra set on the CoolScan have none.

| Observation | Values |
| --- | --- |
| The scanner changes the result strongly | The same 5207: Delta E median 12.2, max 27.4, hue 7.7 degrees between the two scanners at offset 0. Median C*: 51.4 and 32.2 |
| Bright mid-tones on cine film | Neutral 5 (reference L* 50.9) is at L* 66.1 and 67.5 on 5207, 66.0 on 5219, and 52.2 on Portra 400 |
| Chroma falls with overexposure and stays high with underexposure | Median C* from -2 to +2: 55.6, 61.3, 51.4, 37.1, 27.5 (5207, CoolScan); 40.2, 40.5, 32.2, 25.0, 18.0 (5207, X-T5); 36.5, 43.8, 44.2, 35.2, 25.9 (Portra) |
| A tungsten stock in daylight keeps a strong crossover | 5219, b* from White to Black: +6.5, +3.6, -1.5, -13.0, -30.1, -35.9. The dark skin patch has b* -6.7 at offset 0 |

### 10.2 Rule `direct_inversion`

The hypothesis after these values: the look comes from a per-channel positive, and not from a transform with a matrix and a hue-preserving display rendering. Class `DirectInversionPreview` of `aces_scan.py`: the APD records of the same negative, a grey position and a slope per record, and one curve per channel, y = E^n / (E^n + 1/t - 1), shown directly as the display channel, with no matrix. Values: t = 0.22 (the mid grey of the print path) and n = 1.6. The author set them before the first comparison, and they were not changed after it. It is a model of this kind of process and not of a named program.

**Checks** (`scan_checks.json`, limits set before the first run): grey at 0.22 +- 0.002 per channel, finite, display luminance does not fall on a neutral ramp. **The first run failed**: blue was 0.2143 to 0.2158. Cause: the neutral of an image goes through the reconstruction, and the grey position used a flat reflectance. The fix moves the grey position to the neutral of the image and keeps the limit. All checks now pass.

### 10.3 Comparison on the chart

No product grade, because the real film had none. One exposure shift per path puts Neutral 5 at the L* of the real scan, so that the tone level does not dominate. The values are over the 18 colour patches at offset 0. [`film_analyzer_compare.json`](../../results/p3_scan_and_scene/film_analyzer_compare.json).

| Set | Print: Delta E, hue, C ratio | ACES 1.3 | ACES 2.0 | Direct inversion |
| --- | --- | --- | --- | --- |
| 5207, CoolScan | 16.5, 6.5, 0.75 | 17.7, 8.9, 0.66 | 22.1, 13.0, 0.56 | **7.8**, 6.5, 0.91 |
| 5207, X-T5 | **10.8**, 7.5, 0.90 | 14.0, 11.1, 0.82 | 15.8, 15.3, 0.63 | 14.2, 10.8, 1.11 |
| 5219, CoolScan | 18.5, 9.7, 0.68 | 17.9, 10.4, 0.65 | 22.6, 10.9, 0.49 | **10.6**, 6.5, 0.84 |
| Portra 400, X-T5 | **9.0**, 5.6, 0.97 | 16.3, 14.7, 0.81 | 18.0, 17.8, 0.68 | 11.9, 9.1, 0.89 |

| Stops to the Neutral 5 of the scan | Print | ACES 1.3 | ACES 2.0 | Direct |
| --- | --- | --- | --- | --- |
| 5207, CoolScan | 1.22 | 1.37 | 1.92 | 0.51 |
| Portra 400, X-T5 | 0.05 | 0.58 | 0.83 | -0.18 |

**Use of these tables (user, 2026-10-30).** These paths are creative renderings, and accuracy on a chart is not a goal. The tables do not rank the paths and they do not select one. They only show the direction of a behaviour. Also, two real scanners on one roll differ by Delta E 12.2. An earlier message of this work called direct inversion the nearest path; that statement is withdrawn.

Behaviour that the tables show:

- ACES has the lowest chroma of the paths on these sets, and it needs the largest exposure shift to reach the mid-tones of a scan.
- Yellow is greener than the scan in both paths, 3 to 8 degrees in the print and 7 to 11 in direct inversion. Cyan is much bluer in the print on 5207 (-19 and -29 degrees), and -4 and -14 in direct inversion.
- **Bracket:** median C* of direct inversion from -2 to +2 on 5207: 33.1, 43.6, 49.4, 43.1, 28.6. The overexposed side is near the CoolScan values. The underexposed side stays far below both scanners. The print has the same fault (26.2, 39.5, 40.1, 36.2, 26.5), and ACES 2.0 has the flattest response (19.0, 23.7, 27.3, 29.3, 26.3).
- **5219 crossover is not reproduced.** Direct inversion has b* -2.5 to -8.4 on the neutrals, against +6.5 to -35.9. A test (`gamma_probe.py`, local, not committed) replaced the slopes of the cine stock by those of Portra, to test the idea that an inversion made for C-41 makes this crossover. The idea failed: the blue shadow barely changed, a green-magenta crossover appeared, and Delta E grew (5207: 7.7 to 11.8). The cause stays open.

Limits: one chart per set, unknown light and lens, the input is a colour computed from reference Lab, so the chart is not a measured spectrum. The Lab of the site and of this script can differ in adaptation. This is a comparison of behaviour, and it is not a calibration.

### 10.4 Full review

`render_full_review.py`, on all of these, with the product grade before each path. A label with stock and method is on each panel (user request). [`full_review.json`](../../results/p3_scan_and_scene/full_review.json).

| Set | Files rendered | Source |
| --- | --- | --- |
| `signature_edits` | 44 | signatureedits.com: the 14 of P2 and 30 new, chosen from thumbnails for skin, colour, night, and landscape |
| `sample_subjects` | 30 | Alcedo Studio sample images, by subject folder |
| `sample_cameras` | 73 | Alcedo Studio sample images, the first file of each camera model |
| `night` | 6 | the user night files of P2 |

Not rendered: `se215.nef` and `nikon/z8` (LibRaw: unsupported). No other file replaces them. A first run lost one file of the sample subjects, because a cut file name gave two files one output name. The script now stops on such a collision. A DNG made from a RAW file of the same name counts as the same photo.

Mean over the files of a set, 5207:

| Set | Path | L* p5 / p50 / p95 | C* p50 / p95 |
| --- | --- | --- | --- |
| `signature_edits` | Print | 5.4 / 33.2 / 70.4 | 17.5 / 42.9 |
| | ACES 2.0 matched | 4.0 / 35.0 / 70.4 | 13.0 / 33.8 |
| | ACES 1.3 matched | 3.3 / 32.9 / 76.8 | 14.6 / 37.5 |
| | Direct | 5.9 / 40.2 / 83.8 | 19.2 / 49.8 |
| `sample_cameras` | Print | 6.1 / 29.3 / 73.0 | 10.4 / 30.3 |
| | ACES 2.0 matched | 4.5 / 32.0 / 72.8 | 8.2 / 22.2 |
| | Direct | 6.5 / 36.1 / 86.5 | 11.9 / 33.5 |
| `night` | Print | 6.3 / 26.8 / 70.4 | 14.9 / 47.5 |
| | ACES 2.0 matched | 5.6 / 29.5 / 71.4 | 11.4 / 38.9 |
| | Direct | 7.6 / 32.6 / 83.5 | 15.4 / 51.3 |

Author's visual results, 18 files of three overview sheets. This is not user review:

- Direct inversion is the brightest and the most open, near the plain image in hue, with clean neutrals. The print has warmer yellows and darker, green or teal shadows. ACES has dark, slightly magenta shadows and muted colour.
- **Direct inversion stacks on the product grade.** The print takes back the contrast of the grade with `print_contrast`, and direct inversion has no such step. C* p95 is 16 % above the print on `signature_edits`, and L* p95 is 13 higher. The user judged an earlier chroma too high (U19), so this is a risk. This path was not tuned for the grade.
- A saturated sunflower turns greenish in direct inversion and in ACES (`se036`), and keeps gold in the print. A blue sky leans lavender (`se224`). This agrees with the yellow values above.
- The green sign of `_DSC8169` becomes pale with a blue tint in direct inversion and is pale mint in the print.

### 10.5 Ideas from this comparison

Proposals, not measured results:

1. **A scanner is a look.** The scanner changes the result as much as the path. The product could offer a scanner choice for a stock. A second APD-like response (for example a narrow RGB LED record near Status M) costs one table, and the data of real machines stays not public (audit).
2. **Per-channel curves give the behaviour that a display transform removes.** The chroma that falls with overexposure and the hue twists follow from channels that saturate one at a time. This can stay a pointwise table, which fits P6.
3. **The underexposed side is the largest shared error.** Real scans keep chroma at -1 and -2 stops, and every path loses it. Real blacks are also lifted (Black at L* 24.7 on the CoolScan, against 13.8). A lower curve toe is the first thing to test.
4. **Keep the cast of a tungsten stock as an option.** A real scan of 5219 in daylight does not neutralize the shadows. The present option `print_timing` cannot give this crossover.

## 11. Classic scanner styles (U26, U27)

The user decided: keep print and classic scan, and drop ADX to ACES. Cine film is accurate, so the character is expected to come from the error of a scanner. These are style simulations, with no endorsement from a manufacturer (U27).

### 11.1 Why direct inversion has a hue near the input

`direct_matrix_probe.py` (local, not committed) fits one 3x3 matrix from AP1 to the per-channel exposure of the inversion, on colours inside Rec. 709 and away from the curve ends. Matrix for 5207, against the true matrix from AP1 to linear Rec. 709:

| | Inversion, 5207 | AP1 to Rec. 709 |
| --- | --- | --- |
| R | 1.565, -0.653, 0.200 | 1.705, -0.622, -0.083 |
| G | -0.057, 1.027, 0.038 | -0.130, 1.141, -0.011 |
| B | 0.037, -0.028, 0.962 | -0.024, -0.129, 1.153 |

Calculation: the layer sensitivities and dyes, read back per channel, act almost like Rec. 709 primaries. So showing each record as a display channel needs no matrix, and the hue stays near. The RGB hue difference from Rec. 709 has a median of 6.6 degrees (p95 28) on 5207, 5.6 (23) on 5219, and 4.4 (18) on Portra 400, for colours with saturation above 0.3. This supports the statement of the user that these stocks are accurate. The dyes of this model are an inferred band split (P0), so this applies to the model and it is not a measurement of film.

### 11.2 What is public

| Scanner | Found | Not found | Use |
| --- | --- | --- | --- |
| Fuji Frontier SP3000 | Monochrome sensor with sequential RGB light, from secondary sources. A [spectrum picture](https://forums.negativelabpro.com/t/optimize-nlp-for-rgb-light-sources/4012) with bands near 465, 540, 632 nm, source not stated. Qualitative reports: comparisons found through a search summary, not read one by one (cooler, cyan and blue shadows, more saturated; for example [Carmencita](https://carmencitafilmlab.com/blog/frontier-vs-noritsu-round-2/) and [Optik Oldschool](https://www.optik-oldschool.com/blogs/blog/why-we-prefer-frontier-scans-for-opticolour200)), [Schlueter](https://www.sebastian-schlueter.com/blog/2018/3/7/the-magic-fuji-frontier-sp-3000) (harder mid-tones, toward magenta) | ICC profile, tone curve, per-film tables. The [SP-500 research](https://github.com/rohanpandula/negative-universal) lists the structure of film channels (base balance, under and over slopes), but the page of its evidence was not reachable (404) | Light band estimate |
| Hasselblad Flextight X5 | The public [FlexColor 4.8.9.1 installer](https://cdn.hasselblad.com/archive/2017/10/fc4891win.zip): `Flextight_Input.icc` (A2B, 32 grid), `Flextight_X5_949.icc`, and 114 image settings with many film names. The [GitHub file](https://github.com/kehanXue/Flextight-X5-ICC) `3F Negative.icc` is byte-equal to `Flextight_Input.icc` | Spectral response. No cine stock among the settings that this work read by name. Light: cold cathode tube ([filmscanner.info](https://www.filmscanner.info/en/HasselbladFlextightX5.html)) | Table applied |
| Noritsu LS-600 | [noritsu-tool](https://github.com/rohanpandula/noritsu-tool) (MIT, numbers recovered from the software of Noritsu): 20-point tone curves, per-film tables, and fits for 3 stocks | Light spectrum, and the full colour stages of the engine as numbers in this work | Tone curve applied |

The image settings of FlexColor read so far change little: the Portra 400 NC and VC and Gold 200 settings have straight curves and no colour correction, and saturation +15. Portra 160 NC has one S-curve. So the colour of that path is mostly in the input table. The license agreement text of FlexColor was not found in the extracted files and was not read; the user deferred this (U27).

### 11.3 First renders

`render_scanner_light_review.py`, 9 files, with stocks in rows and styles in columns. [`scanner_light.json`](../../results/p3_scan_and_scene/scanner_light.json) holds the values.

| Style | What it changes | Result on 11 chart colours (5207, against APD) |
| --- | --- | --- |
| Frontier light | the light only, with slopes refitted; sensor taken as flat; no software | Hue +-2 degrees, light skin +3.5, cyan +6.6. Chroma 0.86 to 0.95 of APD |
| Noritsu curve | the tone curve only; the range is inferred | Strong contrast (see the images); chart values not computed in this run |
| X5 table | the input table of FlexColor after the same positive | Hue up to 11 degrees: blue sky -11, cyan -9, green +8, orange -7. Chroma 0.87 to 1.20 |

The author's visual results, which are not user review:

- **The light alone is a small effect in this model.** This contradicts the forum reports of strong saturation from narrow light. Two causes are possible: the negative dyes are an inferred band split, and each record is refitted to neutral. The Frontier character in the reports likely needs its software, which is not public.
- **The Noritsu curve gives the largest change.** It has deep blacks, rich skin, and strong colour. It is too hard here, with clipped shadows on `se036`, because it stacks on the contrast of the product grade, and the range is inferred.
- **The X5 table gives a calm rendering**, with a softer and warmer shift in skin and sky. Neutrals stay neutral (a*, b* within 0.8 on the ramp of 5207).
- 5219 keeps a cool cast in shadows in these styles, closer to the direction of real scans in section 10.

The user found these 9 files not representative, in particular the night file. So the sheets now use 23 files chosen for colour richness (a rank of hue coverage and chroma, then by eye from the contact sheets), 14 of them newly downloaded from signatureedits.com, and one synthetic sweep of hue, saturation, and exposure (`hue_sweep`). Each sheet has the plain image in its first column. `overview_5207_*.png` has one row per image.

Author's visual results on this set, 5207, not user review:

- The sweep shows the styles most clearly. The Noritsu curve drives each channel to its end, so colours turn neon and dark rows go black. The X5 table is soft, with cyan and green moved. The Frontier light is a slightly paler form of APD.
- On real scenes the same order holds. The print is warm and dense, with less blue. APD and the Frontier light are near each other. The X5 table is the calmest.

### 11.4 Next work

| ID | Item | Owner |
| --- | --- | --- |
| P3-O11 | Review of the styles: which ones to keep. | User |
| P3-O12 | Take back the contrast of the product grade in the classic scan, as `print_contrast` does in the print. | P3 |
| P3-O13 | Noritsu: apply its per-film tables and colour stages, with per-frame or fixed range as a decision. | P3 |
| P3-O14 | Frontier: no public tone data. Build the style from the light estimate and the qualitative reports, labeled as an estimate, or obtain paired scans of one target. | User, P3 |
| P3-O15 | State the non-endorsement text in the release (U27). | MVP |
| P3-O16 | Density crosstalk as a free style control of the classic scan, with values chosen by eye and not fitted to the test data (section 12). Rule added in section 13.2; the values are open (P3-O17). | User, P3 |
| P3-O17 | Review of the crosstalk values. | User |
| P3-O18 | Choose the soft settings of the direct inversion (section 13.4), and solve the two open faults there. | User, P3 |

## 12. A scanner model fitted to chart scans (test only, U28)

The user asked for a test: fit a scanner to the Film Analyzer chart of 5207 on the X-T5 (set 191). The site states no license, so the parameters and the images stay in `build/tmp/p3/fitted_scanner/`, and no product path uses them. This report holds only differences and the form of the model.

Model (`fit_scanner_to_chart.py`): the reading of the negative above its base goes through a density crosstalk, one tone curve per channel, and a display matrix. The fit has 120 measurements (24 patches at 5 offsets) with no product grade. The levels add parameters in order. The CoolScan set of the same stock is fitted in the same way, for scale.

Delta E, median (95th percentile):

| Set | Level | All patches, in the fit | Patches held out | Offsets +/-2 held out | Same scanner, other film |
|---|---|---|---|---|---|
| X-T5 | A: tone, 12 parameters | 9.85 (20.6) | 10.8 (20.0) | 10.4 (22.6) | Portra 400: 11.5 (22.3) |
| X-T5 | B: A + light, 18 | 8.60 (18.2) | 9.90 (19.1) | 11.7 (23.0) | 12.1 (22.6) |
| X-T5 | C: B + crosstalk, 24 | 5.80 (10.7) | 7.02 (14.8) | 7.20 (14.4) | 8.04 (16.1) |
| X-T5 | D: C + matrix, 30 | 5.36 (10.2) | 5.98 (14.1) | 6.97 (12.9) | 7.96 (15.5) |
| CoolScan | A | 12.3 (25.2) | 13.1 (27.7) | 17.7 (27.8) | 5219: 14.7 (30.8) |
| CoolScan | B | 10.6 (22.7) | 11.9 (24.5) | 17.0 (26.9) | 13.5 (25.6) |
| CoolScan | C | 5.89 (12.2) | 6.88 (14.9) | 7.95 (13.6) | 8.69 (18.6) |
| CoolScan | D | 5.50 (12.2) | 6.58 (12.8) | 8.54 (14.1) | 8.99 (19.3) |

On the other film only the position `g` is fitted again. A tone-only fit made directly on that film has 10.2 on Portra 400 and 14.2 on 5219, so the crosstalk from 5207 is better than the tone-only fit of the film itself.

Results:

- The density crosstalk gives most of the improvement. The result stays on held-out patches, on held-out offsets, and on another film.
- The light is not identified by these data. The peaks and widths go to their limits (for example, red at 700 nm with a width of 10 nm), and they differ between levels. Level B has worse held-out offsets than level A on the X-T5. So the fitted bands are not a measurement of a light.
- The crosstalk terms of the two scanners are similar in sign and size, but they are not the same. The X-T5 tone curves with the CoolScan light and crosstalk give 8.85, against 5.80 with its own. The CoolScan tone curves with the X-T5 light and crosstalk give 10.09, against 5.89. So some part can be common (for example, an error of the negative model), and most of the gain belongs to each set. These data cannot separate the scanner, the light, the lens, and the inversion program of the site.
- Parameters at limits and a contrast `n` of more than 3 in one channel show that the model takes a shape that is not physical. It is a look experiment and not a profile of an X-T5.

Author's visual results on sheets 1, 3, and 5 (13 files and the sweep) and on the chart, not user review. Sheets 2 and 4 are rendered and not examined (`review/overview_*.png`, `review/chart.png`):

- Levels C and D look clearly different from the direct inversion with APD: warmer orange skin, yellow moved toward orange, red moved toward orange, sky moved toward cyan, and a dim top end. This is the first scan path here with a visible character of its own.
- In the sweep, levels C and D narrow the green band, with yellow and cyan on each side of it. A green dress in `se274` moves toward teal.
- Without the product grade, level C has black edges around the saturated blue light of `showcase_DSC_7169`. The cause is probably the crosstalk with negative terms. A real scanner path needs a limit on this.
- Level C and level D look near each other, so the matrix adds little to the image.

The chart cannot show this kind of failure, as 24 patches do not reach the saturated colours. Any later version must also be judged on the sweep.

## 13. Breaks in the hue sweep, and an algorithmic crosstalk (U29)

The user found breaks in the hue sweep, and decided to add a crosstalk by algorithm and to keep the print and APD for now. Sections 11 and 12 stay as a record of the process.

### 13.1 Rule `smooth_reflectance_table`

Cause. Local scripts traced the sweep stage by stage. The breaks are not in the input and not in the product grade. They start at the layer exposure, at the same u'v' positions in both paths, and no input colour was moved by the locus projection. A map of the second difference of log Q/Y over u'v' shows a web of creases, strongest at high chroma on the blue to magenta side. So the source is the Q/Y table from the reconstruction of P1. The creases agree with a reconstruction that changes its active set and its neighbours from node to node (`sigma_uv` 0.01, 256 neighbours), but this work did not isolate which one gives which crease. The P1 evaluation measures error on spectra, so it did not measure this.

Rule. The reflectance table gets a Gaussian over u'v', with `sigma_near` for low chroma and `sigma_far` for high chroma, and a smoothstep between them over a u'v' distance of 0.05 to 0.15 from the white. Then each node gets a scale per wavelength that restores its XYZ. `DARKROOM` sets `uv_smooth=(0.006, 0.025)`. The print table does not use this table, so the print tables stay valid. The values are chosen from these results, by eye on the sweep and on 6 photos, on 5207:

| `uv_smooth` | Largest second difference along the sweep, APD | Same, print | p95 of the Q error in stops: skin (`issa_skin`) | `rawtoaces_190` | `gutierrez_natural` | `usgs_splib07` |
| --- | --- | --- | --- | --- | --- | --- |
| none | 0.0431 | 0.0435 | 0.059 | 0.314 | 0.237 | 0.138 |
| 0.004, 0.02 | 0.0151 | 0.0137 | 0.064 | 0.370 | 0.237 | 0.141 |
| **0.006, 0.025** | **0.0142** | **0.0121** | **0.070** | **0.404** | **0.238** | **0.144** |
| 0.008, 0.03 | 0.0141 | 0.0105 | 0.079 | 0.420 | 0.245 | 0.147 |
| 0.012, 0.03 | 0.0140 | 0.0097 | 0.100 | 0.423 | 0.262 | 0.155 |

For comparison, one sigma of 0.02 everywhere gave 0.133 on skin. The other two stocks show the same change: 5219 goes from 0.0349 and 0.0377 to 0.0132 and 0.0182, and Portra 400 from 0.0338 and 0.0452 to 0.0141 and 0.0140 (APD and print).

Cost. The accuracy on spectra falls: the set `rawtoaces_190` goes from 0.314 to 0.404 stops. The XYZ of a node inside AP1 differs by up to 1.2 % at the 99th percentile, and by more at some nodes at the edge of the table (the worst is 1.21, relative). The user put appearance first, so this cost is accepted. Numbers of the P1 report describe the table with no smoothing, and P2 review images made before this date also used that table.

The sweep still has narrow peaks at green and blue. The input sweep has them too (largest second difference 0.0384 in the input), so they do not come from the film chain.

`check_scan_path.py` and `check_fast_kernels.py` pass after this change.

### 13.2 Rule `density_crosstalk`

On the direct inversion, each record moves away from the other records, in log10 exposure, with a soft limit (0.5 log10 by default); see `aces_scan.py`. The fitted model of section 12 drove a channel to black, and this form was chosen to prevent that: the size of the move is limited. On the ungraded `showcase_DSC_7169`, no pixel is more than 0.25 of the code range darker than with k = 0, for the three settings. Chart scans gave the idea and the sign of the terms only; the values are set by eye, and no parameter of section 12 is used.

Checks are in [`crosstalk_checks.json`](../../results/p3_scan_and_scene/crosstalk_checks.json): on the neutral ramp of 5207 the display changes by 0.0025 at most, and the sweep has no break larger than with k = 0.

Author's visual results on sheets 1, 3, and 5 and the sweep, not user review (`build/tmp/p3/review_crosstalk/`):

- Uniform 0.10 is a mild gain of colour. Uniform 0.25 goes to neon on the sweep and is too strong after the saturation of the product grade.
- The setting `warm` (G from R 0.30, R from B 0.15, others 0.05) changes hue as well as chroma: sky toward cyan (`se146`), warmer sand (`se357`), warmer skin (`se188`). It is the only one of these settings with a look that differs clearly from a saturation control, and it is the proposal of the author.
- The neutrals and the bright smoke of `se296` stay clean.

### 13.3 Landscape files in large sheets

The user found the sheets too small and asked for landscape files, and excluded `showcase_DSC_7169` as an edge case. `render_print_apd_review.py` now makes one sheet per file, with panels of about 600 to 1100 pixels in width, for 37 landscape files: 20 sample images of the product and 17 files of one landscape photographer on signatureedits.com (52 downloaded, chosen by eye from the embedded previews).

Author's visual results on `se167`, `se224`, `fuji_xt5`, and `hasselblad_x1dii`, not user review. These correct the first statement of section 13.2 about `warm`:

- APD with k = 0 moves sky and blue shadows toward purple (`se224`, `hasselblad_x1dii`). `warm` brings the sky back toward a cleaner blue.
- At full strength, `warm` moves orange toward pink and red: the sunset of `fuji_xt5` and the lit rock of `se224`. This is too strong on these files.
- `warm x 0.5` keeps most of the correction of the sky and most of the orange. It is the new proposal of the author.
- The print has a grey sky and cream clouds on the same files, with deeper shadows than APD.

The classic scan still stacks on the contrast of the product grade (P3-O12).

### 13.4 A softer direct inversion (U30)

The user found that the direct inversion is not soft and looks digital, and asked for a trial with Portra and for a style set from real scans. Grain was tried once and removed at the request of the user.

Reference. Local copies of the sample photographs of Film Analyzer (5207, 5219, Portra 400) and of images from public articles are in `build/tmp/p3/refs/`, with their sources. These are a style reference only (U30). Global statistics were compared on 7 landscape samples of 5207 and on 18 landscape files of this review. The scenes differ, so this gives a direction and not a target. This report holds only the differences, as `apd` minus reference, on 5207:

| Statistic | `apd` minus reference |
| --- | --- |
| L, 10th percentile | -18.6 |
| L, median | -29.3 |
| L, 90th percentile | -15.0 |
| Median C at L 15 to 35 | +5.8 |
| Median C at L 35 to 55 | +5.4 |
| Median C at L 75 to 92 | -3.3 |

So the `apd` panel is darker with denser blacks, has more colour in the shadows, and has less colour in the highlights. A coarse search (432 settings) preferred a higher display grey and a small black lift on both stocks; it reached the largest display grey of its grid, so it does not locate an optimum. The final values are chosen by eye.

Rule `soft_scan` (in `aces_scan.py`): `log_contrast` and `record_saturation` take back the default grade; `black` and `white` set the display range.

| Setting | Stock | `display_grey` | `black` | `log_contrast` | `record_saturation` | crosstalk |
| --- | --- | --- | --- | --- | --- | --- |
| `apd` now | all | 0.22 | 0 | 1 | 1 | none |
| soft B | 5207, 5219 | 0.35 | 0.015 | 0.85 | 0.9 | `warm x 0.5` |
| soft C | 5207, 5219 | 0.38 | 0.012 | 0.92 | 0.85 | `warm x 0.5` |
| soft D | 5207, 5219 | 0.38 | 0.02 | 0.8 | 0.8 | `warm x 0.5` |
| soft B | Portra 400 | 0.33 | 0.006 | 0.88 | 0.95 | `warm x 0.5` |
| soft C | Portra 400 | 0.36 | 0.006 | 0.95 | 1 | `warm x 0.5` |
| soft D | Portra 400 | 0.36 | 0.012 | 0.85 | 0.9 | `warm x 0.5` |

Author's visual results on `se167`, `canon_r`, `fuji_xt5`, and the comparison with reference scans, not user review (`build/tmp/p3/review_soft/`):

- All soft settings are much softer than `apd` now. Soft C keeps the most solid shadows of the three, and it is the proposal of the author on each stock.
- Portra 400 keeps more colour and more warmth than 5207 and is the closest to the feeling of the Portra references.
- 5219 under the same values has a cool, blue cast on these daylight files.

Open faults:

- The fixed black lift turns low-key areas grey (the city in `fuji_xt5`), most strongly in soft D. Reference scans of 5207 have dark shadows together with bright mid tones.
- Crosstalk still moves sunset orange toward pink on 5207 and 5219 (`fuji_xt5`).

Comparison with spektrafilm (external comparison only, U18; default settings, its own exposure, no grain, no product grade; `render_spektrafilm_compare.py`, local sheets). Author's visual results on `canon_r`, `se167`, `fuji_xt5`, and `hasselblad_x1dii`, not user review:

- spektrafilm is the densest and most saturated of the three paths. The print of this project is near it in tone, with less saturation. Soft C is much lighter than both, so the two paths of this project now differ clearly.
- Blue sky: spektrafilm moves it toward cyan, most on Portra 400. The print and soft C keep it nearer to blue and violet.
- Sunset: spektrafilm and the print keep a golden orange. Soft C goes to pink, which confirms the second open fault above.

### 13.5 User review and next step

User review (2026-10-30): spektrafilm has a poor result too, the soft settings of APD still do not look like film, and the colours of this software are strange. A calibration roll is not possible (U31). The look items move to [P4](p4_physical_film_response.md). The scene presets of section 7 stay as they are. The look work of sections 11 to 13 stays as a record of the process and as a comparison for P4.

