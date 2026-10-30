# P2: Negative and print (appearance baseline)

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P2, with decisions U17
(the final appearance is the priority, so the renders come first), U18 (an appearance baseline), and
U19 (darkroom process, cine stocks).
**Date:** 2026-10-30.
**Status:** in progress. The chain renders real files, and its appearance is near the baseline on
25 test images. Darkroom controls, an RGC-style display compression, and 5207 and 5219 are in review
(section 8.1). Most of the required P2 evidence is not measured (section 8).

> **Renders are local only.** `build/tmp/p2/renders/` and `build/tmp/baseline/`. They contain photos
> and are not committed. The commands are in the [script README](../../scripts/poc/p2_negative_print/README.md).

## 1. Question

Can the selected P1 reconstruction, the Portra 400 negative, and the Endura print give an image with
an appearance near the reference projects, from real files, with no 3x3 shortcut in the film input?

## 2. Result summary

- **The first look was wrong because of this project's own choices, not because of the film data.**
  The first review used an exposure rule that was too bright and then lowered the print contrast to
  compensate. Skies, sunsets, and bright skin became pale.
- **Three changes bring the image near spektrafilm** (Portra 400, Endura Premier, default settings,
  no grain). The published print curve is used without softening:
  1. Exposure: center-weighted mean of linear Y = 0.18 (section 5).
  2. Display white: a perfect reflector, not the paper white (section 6).
  3. Interlayer gain 0.2: an approximation of the colour gain of development inhibitor couplers
     (section 7).
- **Result on 14 portraits:** Delta E*ab p50 4.0, p95 16.5, median chroma ratio 1.06, largest difference
  of median L* 5.6. The portraits did not contribute to the exposure rule or to the display white. They
  did contribute to the choice of the gain (section 7).
- **Open:** display clipping of saturated colours (up to 72 % of the pixels in one image), a yellower
  rendering of saturated yellow than spektrafilm, and no spatial effects (halation, coupler diffusion).
- The values follow the output of spektrafilm, so this appearance is not an independent result (U18).
  No spektrafilm code, table, or profile is used.

## 3. Inputs and method

`film_preview.py` documents each stage and each rule. Summary:

| Stage | Method |
| --- | --- |
| Input | LibRaw, camera white balance, XYZ (D65), Bradford to the ACES white, linear AP1. Half-size decode and box reduction, for review images only. This is not the Alcedo camera path. No RGC. |
| Exposure | Rule `center_weighted_exposure` (section 5). It is a review rule. |
| Layer exposure | `measured_prior_local_nonnegative` with rule `spectral_locus_projection`, reference light E_ref, as a table of Q / Y over u'v' (192 x 192). |
| Negative | P0 Portra curves, with interlayer gain 0.2 before the curves. Dye basis: band split; densities outside 400-700 nm: Gaussian tails (spectral_film_lut, U11). |
| Print | P0 lamp A, balanced on an E_ref grey; published Endura curves and dyes; table over negative Status M (65 nodes per axis). |
| Display | D50 viewing; a perfect reflector to display white (Bradford to D65); linear Rec. 709; clip; sRGB. |

Rules for values that the dye sets cannot reach: `dye_solve_nearest` (nearest non-negative amounts,
counted). Machine: as in the P1 report. CPU only.

**Images.** Three sets, all local:

| Set | Files | Use |
| --- | --- | --- |
| First review | 8 files of the RAW library | numeric checks of the tables (section 9) |
| Baseline development | 11 files of the RAW library by subject | exposure rule, display white, gain |
| Portraits | 14 files from the free RAW collection of signatureedits.com, chosen from thumbnails by skin tone and light | test of the appearance |

The user found that the RAW library does not represent portrait use well and asked for the third set.

## 4. Baselines

| Project | Version | Run | Result |
| --- | --- | --- | --- |
| spektrafilm | `3bb2c2d2` (GPLv3) | Python, Portra 400 and Endura Premier, default settings, automatic exposure, no grain; input: the same linear AP1 as this project | **Selected baseline.** The same chain as this project: negative, print, display. |
| Fotufilm | v1.14.1 (Apache-2.0; profiles CC BY-SA 4.0) | Linux release engine through its C interface, in WSL, CUDA; Portra 400, no grain; the engine decodes the RAW | Comparison only. |

Fotufilm is a comparison only for two reasons. Its default (Auto Levels) is a scanner model, with
brighter and flatter images and a different goal. Its Endura medium without exposure settings is much
darker in these runs (median L* 3.7 to 18 on 10 of the 11 development images). This report did not
adjust its settings, so this is not a judgment of its best result.

The film grain of both projects is off, because film grain is outside this lab.

## 5. Exposure

The first rule (log average of Y = 0.18) raised images by up to 4.9 stops. The diagnostic solved the
exposure of each development image so that its median L* equals the median L* of spektrafilm. At
this exposure, the published curves without softening already give an image near the baseline. The
solved exposure is 0.4 to 1.7 stops below the first rule.

These statistics of linear Y were tested against the solved exposure, with one fitted constant and
leave-one-out error ([`baseline_exposure_match.json`](../../results/p2_negative_print/baseline_exposure_match.json)):

| Statistic | RMS (stops) | Max (stops) |
| --- | --- | --- |
| Center-weighted mean (Gaussian, sigma 0.35 of each side) | 0.12 | 0.19 |
| Mean | 0.19 | 0.38 |
| Center-weighted log average | 0.44 | 0.68 |
| Log average, 1st to 99th percentile | 0.49 | 0.74 |
| 90th percentile | 0.60 | 1.25 |
| 75th percentile | 0.62 | 1.57 |
| Median | 0.70 | 1.11 |

The fitted constant is 2^-2.45 = 0.183, so the rule uses 0.18. spektrafilm also has a center-weighted
automatic exposure by its setting name. This project did not read that code, and the fit does not show
that the two rules are equal.

## 6. Display white

A neutral ramp through both chains shows that spektrafilm does not map the paper white to display white
(L* of the paper: 86.6, b* -2.5). The first version of this project did this mapping, with L* 100. This
caused the bright highlights and part of the warm colour of the first review.

The display white is now a perfect reflector under the viewing light. This is a physical definition,
with no fitted value: the paper keeps its own reflectance and colour, as a print next to a white
reference does. The paper white is then L* 91, b* -3. The remaining difference of 4.5 L* is not explained.

| Input | This project L*, a*, b* | spektrafilm L*, a*, b* |
| --- | --- | --- |
| 0.05 | 8.8, -2.5, -0.8 | 9.2, -3.6, -1.1 |
| 0.10 | 26.3, -0.9, 0.9 | 26.2, -1.2, 0.4 |
| 0.20 | 54.2, 0.6, -0.3 | 52.0, -0.5, 0.0 |
| 0.40 | 77.3, 1.5, -2.4 | 76.6, -0.9, -2.0 |
| 0.79 | 88.0, 1.4, -2.8 | 85.4, 0.1, -2.4 |
| 1.58 | 90.7, 1.1, -3.0 | 86.6, 0.4, -2.5 |

## 7. Interlayer gain

With the exposure and the display white fixed, the chroma of the mid-tones was about 0.8 of the
baseline. With its couplers off, the chroma of spektrafilm falls to 0.62 to 0.86 of its default. So
couplers are the likely cause of most of this difference. This is P2-O5 of the first report: the review
found a colour problem that development coupling can solve.

The approximation: before the Portra curves, the difference between each layer's log exposure and the
mean of the three layers grows by a share `interlayer_gain`. The differences are measured from the
layer ratios of a neutral. The first version measured them from zero, and this gave a blue cast (mid
grey sRGB 0.487, 0.506, 0.531). With the neutral reference, mid grey is 0.511, 0.507, 0.510.

| Gain | Delta E*ab p50 / p95 (11 images) | Median chroma ratio (11 images) | Median chroma ratio (14 portraits) |
| --- | --- | --- | --- |
| 0.10 | 4.6 / 18.7 | 0.89 | not run |
| 0.15 | 4.5 / 18.3 | 0.92 | not run |
| 0.20 | 4.5 / 18.3 | 0.95 | 1.06 |
| 0.25 | 4.6 / 19.1 | 0.99 | 1.10 |
| 0.30 | 4.6 / 20.4 | 1.03 | not run |

The value 0.2 was selected after the portrait run at 0.25, so the portraits are not a held-out test of
the gain. The model has no spatial part, unlike real couplers. It is a review control, not a measurement.

## 8. Remaining differences and open items

[`baseline_portraits.json`](../../results/p2_negative_print/baseline_portraits.json) has the values of
each portrait.

- **Largest differences:** two images with saturated yellow in strong sun (`se019`: b* difference 9.7,
  Delta E*ab p50 10.6; `se231`: 5.6, 8.0). This project keeps the yellow, and spektrafilm moves it to
  orange. Both also clip on the display (25 % and 13 %).
- **Chroma:** 1.19 to 1.21 of the baseline on these two images; 0.93 to 1.14 on the other 12.
- **Exposure:** the median L* differs by 5.6 at most (`se127`, a backlit face, is darker).
- **Spatial effects:** the Delta E*ab p95 includes halation and glare, which this project does not model.
- **Display clipping:** 0 % to 25 % on the portraits. On the 18 broader review images it is 0 % to 26 %, and
  on the first review set it is 0 % to 2.9 %, except for `nikon/d810/DSC_7647.NEF` (72 %). spektrafilm
  compresses the output gamut; this project still clips.

| ID | Item | Owner |
| --- | --- | --- |
| P2-O1 | Accept or adjust the appearance. | User |
| P2-O2 | Noise of saturated skies at full resolution. Not reviewed again with the new options. | P2 |
| P2-O3 | Out-of-gamut display treatment. The clip is a placeholder. | P2, with U13 |
| P2-O4 | Reconstruction on Alcedo AP1 instead of the LibRaw path. | P2 |
| P2-O5 | Replace the interlayer gain by a coupler model, only if the review requires it. | On demand |
| P2-O6 | Hue of saturated yellow in strong sun. | P2 |
| P2-O7 | Paper white L* 91 against 86.6. | P2 |
| P2-O8 | Files that LibRaw decodes incorrectly or does not support: `canon/r6iii/9327411796.cr3` (the raw 1st percentile is 2,043, the reported black is 0 to 100; the likely cause is a black level that is not removed); `nikon/z8/DSC_2230.NEF` (unsupported). They are outside the film evaluation. | P2-O4 |
| P2-O9 | Black level, profile, or white balance of `se009`: the skin is strongly red in all three chains. The cause is not known. | P2 |

Not measured: instrument-density reconstruction, parameter-isolation tests, total transmission
checks, comparison with physical film, and full-resolution output.

## 8.1 Darkroom controls and cine stocks (U19)

The user found the chroma too high and the texture poor, asked for ideas from the traditional darkroom
process, and stated that 5207 and 5219 are important. The first review set is not rendered again with
these options; sections 2 to 9 describe the state before this section.

**Controls.** Option set `DARKROOM` of `film_preview.py`. The author selected the values by eye on 8 images.
They are review controls, not measurements, and the user has not accepted them.

| Process step | Control | Value | Effect |
| --- | --- | --- | --- |
| Light scatter in the emulsion | `scatter_um` | 10 | softer fine edges |
| Light that returns from the film base | `halation`, `halation_um` | 0.03, 0.008, 0; 120 | red and orange glow around highlights |
| Developer exhaustion at edges (Eberhard effect) | `adjacency_gain`, `adjacency_um` | 0.25; 60 | edge contrast from the negative |
| Enlarger lens flare | `enlarger_flare`, `enlarger_flare_size` | 0.01; 0.1 | lifted print shadows, in transmittance |
| Paper flash before the print | `print_flash` | 0.02 | softer print highlights |
| Paper grade | `print_contrast` | 0.92 | softer print |
| Paper surface | `viewing_flare` | 0.003 | black point above zero |
| Lower coupler gain | `interlayer_gain` | 0.1 (was 0.2) | lower chroma |

On 8 images, the mid-tone chroma with these options is 0.83 to 1.07 of spektrafilm (Portra 400), and it
was 0.99 to 1.21 before (`darkroom_probe.py`). These steps have an image plane, and they use a frame of 36 mm.

**Display compression.** Rule `rgc_style_display_compression`, as the user asked: the distance and curve of
the ACES Reference Gamut Compression, with its thresholds, limits, and power. It is **not the standard ACES
RGC**: it acts on linear Rec. 709 after the print, not on AP0 before the film. On the 8 images at most 0.36 % of
the pixels stay outside the display range after the compression. The limits are not fitted to this domain.

**Stocks.** `import_cine_profiles.py` writes KODAK VISION3 250D 5207, VISION3 500T 5219 and VISION 2383 from
the digitization of spectral_film_lut (U11). This lab did not digitize or check these data against Kodak
documents.

Rule `grey_anchor`: the first cine renders were too dark, and a check found the 18 % grey up to 0.6 stops
from the stated exposure 12.5 / ISO lux seconds, different per layer. One gain per layer now places the grey
within 0.03 stops. This stands for the camera filter and timing; a tungsten film therefore does not show
a daylight cast. The print grey is `CINE_GREY_STATUS_A` = 0.85, by comparison with spektrafilm, not the 2383 LAD aim
of about 1.06. `viewing_flare` has the value for paper also on the cine prints; this is not a physical choice.

**Result** ([`stock_probe.log`](../../results/p2_negative_print/stock_probe.log)), 8 images, against
spektrafilm with its own Vision3 and 2383 profiles:

| Stock | Delta E*ab p50, range over images | Delta E*ab p95, range over images |
| --- | --- | --- |
| 5207 + 2383 | 4.6 to 9.3 | 9.7 to 14.5 |
| 5219 + 2383 | 4.5 to 9.8 | 9.5 to 16.5 |

Open items:

- Neutral highlights are warmer than spektrafilm: b* +13 against +6 at input 1.0, L* 80 against 82.
- 5207 and 5219 are almost equal in these renders, because `grey_anchor` removes the balance difference. The
  remaining difference comes from their curves and sensitivity shapes. The difference between the two stocks in
  the renders of Fotufilm and spektrafilm was not analyzed.
- Cyan is greener than in spektrafilm (`se002`). The cause is not known.
- The 5219 blue layer gain is 0.26, a strong filter; the same filter on real film has a cost in noise, which
  is not modeled.

## 8.2 Scene light and the character of 5219 (U20)

Rule `grey_anchor` of section 8.1 also removed the tungsten balance of 5219. The rule now uses the balance light
of the stock (5219: Planckian 3200 K; 5207: D55), and the gains stay with the stock. The results of section 8.1
were made before this change.

Rule `relight`: the reflectance shape of the reconstruction is multiplied by the spectrum of `scene_light`
(CIE daylight, Planckian, or a CIE FL, LED, or HP source). A grey under another light lands at a different place per
layer. Option `print_timing` is the share of the mid-grey cast that the printer lights remove. With `E_ref`,
the new table agrees with the previous Portra table within the value printed by this run (see the log).

[`light_probe.log`](../../results/p2_negative_print/light_probe.log), 5219:

| Scene light | Grey on the curves, stops (R, G, B) | a*, b* at input 0.045 | a*, b* at input 0.18 |
| --- | --- | --- | --- |
| T3200, timing 1 | 0, 0, 0 | 0.4, -5.2 | -0.2, 0.8 |
| D55, timing 1 | -0.54, 0.18, 1.14 | 1.0, -6.3 | -0.3, 0.8 |
| D55, timing 0.75 | -0.54, 0.18, 1.14 | 1.1, -11.7 | -2.8, -5.5 |
| FL11, timing 1 | -0.75, 0.28, 0.40 | 1.0, -6.0 | -0.2, 0.4 |
| FL11, timing 0.75 | -0.75, 0.28, 0.40 | -1.5, -8.0 | -5.8, -2.4 |
| LED-RGB1, timing 1 | 0.32, -0.09, -1.15 | 0.2, -4.8 | 0.0, 0.1 |

Findings:

- With timing 1, the effect is small, and it is mostly on saturated colours. The curves are almost parallel in the
  mid-tones, so a printer shift removes the cast almost fully. Most of the visible character comes from a
  timing below 1. This value is a control, not a measurement.
- The renders simulate a light: the input is white balanced, and the real light of each photo is not known.
- RAW white can select a daylight or Planckian light. It cannot show a spiky spectrum, so FL and LED need an
  explicit choice. The selection from RAW white is not implemented yet.
- No comparison with real 5219 footage was made.
- The print tables depend on the light and the timing. A new pair needs a new table (about 2.5 s on CPU, section 8.4).

## 8.3 Night photos and the scene light as a product control (U21)

The user asked for a manual scene light in the product, with daylight as the default. `PRODUCT_LIGHTS` of
`film_preview.py` is the first list: daylight D55, tungsten T3200, fluorescent FL11, LED LED-B3, sodium HP1. Each type
has one CIE spectrum, and real lamps differ. Test: 6 of 31 night files of the user, 5219 + 2383, timing 0.75
(tungsten: 1). The files stay local. Numbers: [`night_probe.log`](../../results/p2_negative_print/night_probe.log).

The author's visual results:

- The light changes the colour of surfaces in the expected direction. Sodium is the strongest: yellow-green, higher
  chroma (C* p95 45 to 47 on 3 of 6 images, against 31 to 40 with daylight).
- **One light for the whole image is a limit.** A night scene has several lights, and signs and lamps emit their
  own light. The rule multiplies them too: under sodium, the red sign moves to orange. Those are not a physical result.
- **Neutral highlights are yellow-green, with blue shadows.** At night this is more visible than in daylight: a white
  wall lit by a lamp becomes pale yellow-green, and the lamp has a blue edge. It is the open item of section 8.1.
- Shadows are dark. `center_weighted_exposure` follows bright lights, so people in dark areas of `_DSC8169` almost
  disappear (median L* 7).

This section has no comparison with real film of these scenes. Section 8.4 changes the two last items above.

## 8.4 Render time, neutral printing, and the meter

**Render time.** The hot stages are now compiled parallel kernels (`fast_kernels.py`, numba). The array methods stay as
the reference. Machine: 20 logical CPUs. Image: synthetic, 1 MP. Values changed between runs with the machine load.

| Item | Array reference | Kernels |
| --- | --- | --- |
| Render, 1 MP | 3000 to 3500 ms | 80 to 130 ms |
| Print table, 274,625 nodes | about 2 min (scaled from 4096 nodes in 1.8 s; not run in full) | 2.1 to 2.5 s |

[`fast_kernels.json`](../../results/p2_negative_print/fast_kernels.json), with limits set before the first run. One limit
failed in the first run: the blur with a large sigma had an error of 0.0049, and the limit is 0.002. The cause was
the reduced image and its edges. The fix keeps the limit. All limits now pass:

| Check | Limit | Result |
| --- | --- | --- |
| Print nodes, 4096 | Delta E max <= 0.01, same counts | 1.4e-9, same counts |
| Blur, sigma 0.35 to 125 | relative max error <= 0.002 | 0.00026 |
| Render against the reference | sRGB p99.9 <= 1/255, max <= 3/255 | 3.7e-5, 6.7e-5 |
| Same check, image with colours outside the locus and negative values | the same, same counts | 1.4e-5, 5.8e-5, same counts |

The count of display values outside the range can differ by a few pixels (float32 against float64). The check does not limit this count.

**Neutral printing.** On 5207 and 5219 through 2383, a neutral ramp had yellow-green highlights and blue
shadows. `baseline/cine_ramp_diagnosis.py` shows the cause: at scene value 1.0, the paper log exposure from the grey
is R -0.38, G -0.42, B -0.31. The blue slope is low, and the shadows show the same error in the opposite direction.
Rule `neutral_printing_gain` sets one gain per paper layer. Values: 5207 (1.115, 1, 1.269), 5219 (1.113, 1, 1.263).
It is computed on the curves, so a scene light can still cause a crossover.

The gains are large. The cause of the low slope is not known: it can be the digitized data, the band split of the dyes,
or lamp A as a printer model. No test separated these causes, and the gains are a correction, not a measurement.

Neutral ramp of 5207, CIELAB (a*, b*):

| Scene value | Before | After | spektrafilm |
| --- | --- | --- | --- |
| 0.063 | 0.3, -6.0 | -4.4, 0.4 | -4.6, -0.5 |
| 0.398 | -2.8, 8.8 | 0.5, 5.0 | 1.0, 3.0 |
| 1.0 | -6.3, 13.5 | -1.8, 7.5 | -0.5, 5.8 |
| 6.31 | -5.9, 12.6 | -2.8, 8.2 | -0.8, 6.0 |

Mean of 8 portraits, the same exposure rule in both columns (5207 / 5219):

| Measure | Gain off | Gain on | spektrafilm |
| --- | --- | --- | --- |
| Delta E p50 against spektrafilm | 6.6 / 7.3 | 4.3 / 5.1 | n/a |
| Delta E p95 against spektrafilm | 12.1 / 13.6 | 8.6 / 10.4 | n/a |
| C* p95 | 37.6 / 37.1 | 41.4 / 40.8 | 42.5 / 41.7 |

Limits of this result:

- The gain raises C* p95 by about 10 %. This is a risk, because the user judged an earlier saturation too high. The value is
  near spektrafilm, but on `se231.nef` it is above spektrafilm (61.7 against 56.9).
- One case is worse: `se019.arw` on 5219, Delta E p95 16.5 to 17.0.
- Agreement with spektrafilm is not agreement with real film.
- The top of the ramp is still lighter than spektrafilm (L* 92.8 against 88.1 at scene value 6.31).
- Portra 400 + Endura does not use this rule.

**Meter.** Rule `center_weighted_exposure` now counts a value above 16 times the weighted median as that value
(`METER_CAP`). The value 16 is a choice from a comparison of candidates on 31 local files. The change is +1.1 stops on `_DSC8169`, +0.8 on
`L1001108`, +0.33 on `se127`, +0.28 on `_DSC8170`, +0.23 on `se015`. On the other 26 files it is 0.1 stops or less. Median L* of `_DSC8169`
goes from 7 to 16. People in the dark areas of that file are visible but still dark.

**Open.** A bright green sign becomes pale mint on 5219 (`_DSC8169`). The rule 'relight' still applies one light to emissive signs.

## 8.5 The default grade of the product comes before the film

In Alcedo Studio, the default document of a RAW file is Develop, then the primary Color Grade, then the DRT. The grade has
exposure +1.5 EV, contrast +15, and saturation 1.3
(`alcedo_studio/src/include/edit/graph/pipeline_document.hpp`). So a film DRT receives a graded image. Until this
section, the review did not apply this grade, and values that were set against spektrafilm did part of its work.

**Change.** Function `product_input()` applies the grade to the review input, with the order and the math of
`primary_grade.cl` (saturation about the luma of the ACEScc values, contrast on OkLab lightness).
`DARKROOM` changes from `interlayer_gain=0.1, print_contrast=0.92` to `interlayer_gain=0, print_contrast=0.85`.

- The saturation of the grade replaces the colour gain of the interlayer option.
- 0.92 / 2^0.15 = 0.83 takes back the mid-grey slope of the grade. The value 0.85 comes from the sweep below.
- The review uses rule `center_weighted_exposure` in place of the +1.5 EV, so that the test images stay comparable.

Mean of 8 portraits. Columns: C* p50 / C* p95, Delta E p50 / p95 against spektrafilm. The spektrafilm images have
an ungraded input, so they are a reference for the appearance and not the same experiment.

| Stock | Target: spektrafilm C* | No grade, old options | Grade, old options | Grade, new options | No grade, new options (raster file) |
| --- | --- | --- | --- | --- | --- |
| 5207 | 15.2 / 42.5 | 14.2 / 41.4, 4.3 / 8.6 | 17.3 / 47.2, 5.0 / 12.4 | 15.4 / 43.0, 4.2 / 8.8 | 12.6 / 36.7, 5.0 / 10.5 |
| 5219 | 14.2 / 41.7 | 14.0 / 40.8, 5.1 / 10.4 | 17.1 / 46.6, 5.9 / 14.6 | 15.2 / 42.3, 5.0 / 11.1 | 12.5 / 36.0, 5.3 / 11.4 |
| Portra 400 | 15.5 / 50.6 | 13.1 / 47.7, 4.5 / 10.7 | 16.0 / 53.6, 4.5 / 11.0 | 14.4 / 49.6, 4.1 / 9.3 | 11.7 / 43.0, 5.6 / 13.8 |

The check of `product_grade` is in [`fast_kernels.json`](../../results/p2_negative_print/fast_kernels.json): an array form of the
product reference, maximum error 4.1e-5 against a limit of 1e-4. It was not compared with an image from the product. The first run failed (0.035): the array
form did not have the decode of a code value below the ACEScc floor. The kernel was correct.

Limits of this result:

- **`se019.arw` is worse.** Delta E p95 goes from 13.6 to 18.4 on 5207 and from 17.0 to 22.9 on 5219. The red dress is lighter
  and more saturated than in spektrafilm.
- **Night files stay more saturated.** C* p95 of `_DSC8169` goes from 37 to 42 and of `_DSC8159` from 44 to 50 (5219, daylight).
- **A raster file has a neutral grade in the product.** With the new options it has about 15 % less C* p95 than the same RAW path.
  No decision was made for this case.
- About 0.05 % of the pixels of the portraits are now outside the spectral locus (rule `spectral_locus_projection`), because of the saturation.
- `compare_portraits.py`, `darkroom_probe.py`, and `gain_sweep.py` keep the ungraded input, as records of the earlier comparisons. The numbers of
  sections 7 to 8.4 are before this change.

**Correction.** The key of the print table did not include `interlayer_gain`, but the printer balance under a light that is
not the balance light uses it. A change of that option could read a table with the wrong balance. The key now includes it. Results that use one value
of this option for each table are not affected.

## 9. Measurements of the tables

[`preview_checks.json`](../../results/p2_negative_print/preview_checks.json), with limits set before the
first run:

| Check | Measured | Limit | Result |
| --- | --- | --- | --- |
| Print table against the direct stages, Delta E*ab p95 (2,000 random densities) | 0.13 (max 1.2) | 0.5 | pass |
| u'v' table against the direct reconstruction, relative Q p95 | 0.0055 (max 0.047) | 0.005 | **fail** |
| Grey ramp finite | yes | finite | pass |
| Grey ramp, largest fall of display luminance | 2.0e-5 | (information) | - |
| Grey ramp, max C*ab of the print | 3.1 | (information) | - |
| Mid grey, display linear luminance | 0.22 | (information) | - |

The u'v' table check misses its limit by a small amount. The limit is not changed. A render takes 2 to
5 s per image of 0.7 to 1.3 MP (CPU) after the tables are built.

Print table nodes: the negative dyes do not reach 12 % of the nodes and the Endura dyes do not reach
64 %. Most of these density triples are far from image data. The first review sampled 3,000 pixels per
image: most images reach both dye sets. Files with very saturated colour do not reach the Endura dyes in
some pixels (`preview_broad.json`, `sample_3000_dye_solve`).
