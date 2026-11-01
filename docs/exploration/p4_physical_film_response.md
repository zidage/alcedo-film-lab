# P4: Physical colour and film response

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P4, with decision U31.
**Date:** 2026-10-30.
**Status:** closed (2026-10-30, U32). All four work items are measured, and the numeric checks pass. The user accepts the look of the print. The direct inversion is set aside and has no accepted look. Section 15 lists the open items. Sections 1 to 7 are the plan, and sections 8 to 16 the results.

## 1. Question

Why do the colours of this model look wrong, and which physical stages give the look of real film scans? Can these stages replace the corrections at the end of the chain?

## 2. Start point

Measurements and observations from [P3](p3_scan_and_scene.md):

- The user found the following (2026-10-30): the soft settings of the direct inversion still do not look like film, spektrafilm has a poor result too, and the colours of this software are strange.
- The direct inversion of 5207 has an effective coefficient of +0.200 from AP1 blue to the red display channel. The AP1 to Rec. 709 matrix has -0.083 (P3 section 11.1). This is a fit on colours inside Rec. 709, not a stage of the model.
- By the eye of the author, sky moves toward violet in this model and toward cyan in the Portra scans that were examined (P3 sections 13.3 and 13.4). The link between this and the coefficient above is a hypothesis.
- The negative dyes use the inferred `band_split` basis (P0, U11).
- `DARKROOM` has `interlayer_gain=0`. The density crosstalk of P3 acts after the negative and does not change with exposure.
- `DirectInversionPreview` scales each record to a neutral ramp, which removes the crossover of the stock.
- All three layers have one `scatter_um` in `negative_image`.

## 3. Rules for this step

- No calibration roll is available (U31). Use published sources and first principles.
- The film input stays spectral. A 3x3 matrix can only be a comparison and has that label.
- Do not reuse spektrafilm (U12). It stays an external comparison (U18).
- Film Analyzer and web scans stay a local test or style reference (U28, U30). Do not copy a value from them to a profile or to a default.
- Grain is outside this lab.
- Keep the print and the direct inversion with APD as the two review paths (U29).
- Mark each inferred field. If a stage cannot be specified from sources, state this and do not fill it with a silent substitute.
- Define the numeric limit of each check before its first run. The sections below give the first limits.

## 4. Work items

Order: W1, W3, W2, W4. W1 comes first because it can invalidate the values of the later items. W3 changes little code and shows its effect quickly. W2 is the largest model change. W4 needs high-resolution review.

### W1: Trace the colour error through the dye chain

**Principle.** A negative dye also absorbs outside its main band. A color negative compensates with coloured couplers (the orange mask). A scanner reads the product of the light, the dye transmission, and the sensor response, so a wrong dye shape changes each record.

**Work.**

1. Send narrow bands and the 11 chart colours of P3 through each stage: layer exposure, dye amounts, spectral density, APD reading, display. Report the part of the +0.200 coefficient that each stage adds.
2. Compare the `band_split` dyes with the published dye densities of each stock and with the data of spectral_film_lut (MIT). Record what the sources do and do not specify.
3. Add a coloured coupler model in the spectral density: the mask density falls as the dye density rises. Mark its inferred fields.

**Checks.**

- A table gives the coefficient per stage. The sum of the stages equals the total within 0.01.
- The transmission of the base and of a neutral density agrees with the existing Status M reconstruction: p95 error at most 0.01 density.

**Review.** Sky, foliage, skin, and the hue sweep, on large sheets.

### W2: Interlayer inhibition (DIR couplers)

**Principle.** A developing layer releases an inhibitor that reduces development in the same layer and in other layers. This effect is nonlinear and local. So the chroma of a colour follows a path that changes with exposure, and detail near a strong edge changes.

**Work.**

1. Replace the constant `interlayer_gain` with a small development model: the rate of each layer falls with the inhibitor from the developed amounts of all layers. The steady state of a neutral must reproduce the published characteristic curve.
2. Add diffusion of the inhibitor in the image plane, with a stated length.
3. Run it for the three stocks. Record each parameter as inferred, with the sources that limit its range.

**Checks.**

- The neutral curve agrees with the published curve: largest error at most 0.02 density inside the published domain.
- A saturated colour ramp from -3 to +3 stops is continuous and has no fall in any record: largest fall at most 0.001 density.
- A report shows the chroma against exposure of each chart colour, with and without the model.

**Review.** The sweep from -3 to +3 stops, and landscape files.

### W3: Colour crossover and timing in density

**Principle.** The three layers have different slopes, toes, and shoulders. A lab balances a frame with one offset per channel in density, so a neutral stays a little warm or cool away from the balance point. The light of the scene also reaches the film before the balance, and not after it as a white balance of a sensor does.

**Work.**

1. Remove the per-record slope of the direct inversion, and keep one density offset per channel for each frame.
2. Add the option to remove the white balance of the camera from the input, expose the negative under the estimated light, and then balance in density. Check first how the input of this lab is balanced.
3. Compare frame balance from a fixed neutral with frame balance from the image.

**Checks.**

- The display of a mid grey under the balance light is neutral within 0.002 linear per channel.
- The report gives the crossover of each stock as a* and b* of the neutral ramp, from -5 to +5 stops. No limit applies, because this is a measured property of the model.

**Review.** Shadows and highlights on landscape files, and portraits for the skin.

### W4: Optics of the layers

**Principle.** Light passes the blue, green, and red layers in sequence. Scatter grows with depth, and reflection from the base adds halation. So each layer has its own spread, and a high-contrast edge gets a colour transition.

**Work.**

1. Give each layer its own spread function, with values from published modulation transfer data where they exist. Mark the other values as inferred.
2. Keep the units in micrometres on the film, and scale them with the frame size.
3. Review at the resolution where the effect is visible. Do not judge it on a small preview.

**Checks.**

- Each kernel preserves the mean of the image: error at most 1e-4 relative.
- A flat field does not change: largest change at most 1e-4.

**Review.** Crops at full resolution with labels, and whole frames.

## 5. Evidence for all items

- All numeric checks of `check_scan_path.py` and `check_fast_kernels.py` stay valid, or the report explains the change.
- The hue sweep has no break: the largest second difference along it is at most 0.02. This is the maximum in the same order as the current model after table smoothing (0.0182).
- Labeled sheets, one per file, of the 37 landscape files and of the portraits, for the print and the direct inversion. Each item compares the result before and after.
- User review decides the look. A chart error does not rank a result.

## 6. Items carried from P3

| ID | Item | Work item |
| --- | --- | --- |
| P3-O12 | Contrast of the product grade in the classic scan | W3 |
| P3-O16, P3-O17 | Density crosstalk | W2 replaces it if the review accepts the result |
| P3-O18 | Soft settings, sunset that goes pink, grey low-key areas | W1, W3 |

## 7. Not in this step

- A calibration roll (U31).
- Spectral acceleration (P6) and the GPU backends (P7).
- Grain.

## 8. Result summary

Date of all runs: 2026-10-30. The numeric limits pass, after two fixes that sections 9.2 and 13 state. The user accepts the look of the print and closes this step (U32).

- **The main colour error is not in the dyes.** The coefficient from AP1 blue to the red record is +0.205 on 5207 (P3 reported +0.200 at the exposure estimate of its own probe). Of the difference of +0.288 from Rec. 709, the layer exposure stage adds +0.282, and the dye and APD stages add +0.005.
- **The cause is in the reconstruction, not in the film.** The prior holds reflectances of objects, and a blue object often reflects again in the far red. A sky spectrum does not. At the colour of a sky, the prior has 1.68 at 700 nm where the sky has 0.38. So the red layer of 5207 has +0.164 log10 too much exposure, and the sky moves toward violet. A Planckian light of 1800 K has the opposite error (red -0.16, blue +0.23). The measured reflectance sets do not show this bias.
- **New rule `light_like_spectra`.** The error on the sky spectrum falls to -0.011, and on 1800 K to +0.020 or less. The coefficient falls to +0.061 on 5207. The film input stays spectral. The cost is on blue and saturated orange objects (section 9.2).
- **The isolated dye curves exist for 5207 and 5219.** An importer had dropped them. They add up to the published neutral within RMS 0.0027 and 0.0047 density, so the author reads them as net of the orange mask. A separate coupler model would count the mask two times (section 9.3).
- **The modulation transfer curves limit two inferred fields.** They give the spread of each layer (red about 5 um, green and blue about 3 um) and the total inhibition of each layer. The exponential spread of these lengths is much narrower than the Gaussian of 10 um that P3 used for all layers (section 12).
- **Author's proposal for review:** the physical options in `P4_PHYSICAL`. The two ways to set the slope of the inversion are both on the sheets, because the author cannot select one (section 10.3).

## 9. W1: colour error through the dye chain

Script: `trace_colour_error.py`. Results: [`colour_trace.json`](../../results/p4_physical_film_response/colour_trace.json).

### 9.1 Coefficient per stage

The matrix fit is the method of P3 section 11.1. It is a comparison measurement and not a transform. The coefficient is from AP1 blue to the red record. The light is the balance light of the 5207 and Portra 400 cases (D55, E_ref) and T3200 for 5219, with `timing` 1. Rec. 709 has -0.083 in all rows.

| Case | Layer | Curve | Status M | APD | Sum above Rec. 709 | End-to-end fit above Rec. 709 |
| --- | --- | --- | --- | --- | --- | --- |
| 5207, band split, Status M record | 0.199 | 0.200 | 0.200 | 0.205 | 0.288 | 0.288 |
| 5207, published dyes, Status M record | 0.199 | 0.200 | 0.200 | 0.211 | 0.295 | 0.295 |
| 5207, published dyes, dye amount record | 0.199 | 0.200 | 0.163 | 0.168 | 0.251 | 0.251 |
| 5207, same, `light_like_spectra` | 0.078 | 0.078 | 0.059 | 0.061 | 0.144 | 0.144 |
| 5219, band split, Status M record | 0.172 | 0.172 | 0.172 | 0.175 | 0.259 | 0.259 |
| 5219, published dyes, dye amount record | 0.172 | 0.172 | 0.146 | 0.150 | 0.233 | 0.233 |
| 5219, same, `light_like_spectra` | 0.065 | 0.065 | 0.052 | 0.052 | 0.135 | 0.135 |
| Portra 400, band split, Status M record | 0.138 | 0.138 | 0.138 | 0.139 | 0.222 | 0.222 |
| Portra 400, band split, dye amount record | 0.138 | 0.137 | 0.134 | 0.135 | 0.218 | 0.218 |
| Portra 400, same, `light_like_spectra` | 0.050 | 0.047 | 0.049 | 0.049 | 0.132 | 0.132 |

Check: the sum of the stages equals the total within 0.01 in all cases (limit 0.01). Neutral against the Status M reconstruction: p95 at most 0.0054 density (limit 0.01). Pass.

The layer stage has two parts. A least-squares fit of the layer sensitivities of 5207 as a combination of the colour matching functions (local probe `sky_probe.py`, not committed) gives a coefficient of -0.072, near the -0.083 of Rec. 709. So the sensitivities alone do not give the +0.2. The reconstruction does.

Even with the rule, the coefficient stays near +0.06. A matrix fit over all colours inside Rec. 709 still includes the blue and violet objects outside the sectors of the rule.

Hue of the chart colour `blue sky` at the APD stage on 5207, in degrees of RGB hue: Rec. 709 -143.7, P3 chain -138.6, this chain -143.8. The value of cyan is 180 and of blue is -120. The foliage colour moves from 101.4 to 93.8 (Rec. 709 89.2). The chart colours are values and not measured spectra.

### 9.2 Rule `light_like_spectra`

In two sectors of u'v' around the white, the shape of the table moves to a smooth spectrum rho = exp(c0 + c1 x + c2 x^2), with the XYZ of the node. The blue sector follows the direction of skylight, and the warm sector the direction of a Planckian light of 2500 K, from a distance of 0.05. Inferred: the family, the sectors, and the distances. A photo gives no way to separate a light from an object, and sky and sunset are the larger areas of a landscape. This is the reason for the choice.

Script: `check_light_spectra.py`. Results: [`light_spectra.json`](../../results/p4_physical_film_response/light_spectra.json). Limits set before the first run. Layer exposure error on 5207, reconstruction minus true spectrum, in log10, red, green, blue:

| Spectrum | Before | After |
| --- | --- | --- |
| Daylight 8000 K | +0.064, -0.004, -0.060 | +0.005, 0.000, -0.005 |
| Daylight 12000 K | +0.092, -0.007, -0.073 | 0.000, +0.001, -0.005 |
| Daylight 20000 K | +0.119, -0.009, -0.076 | -0.011, +0.002, -0.003 |
| D55 x lambda^-2 | +0.071, -0.005, -0.056 | -0.004, 0.000, -0.003 |
| D55 x lambda^-4 | +0.164, -0.013, -0.076 | -0.011, 0.000, -0.007 |
| Planck 2500 K | -0.063, +0.007, +0.092 | +0.014, +0.002, -0.008 |
| Planck 1800 K | -0.162, -0.001, +0.232 | +0.004, +0.003, +0.020 |
| D55 x lambda^+4 | -0.030, -0.002, +0.034 | -0.021, -0.001, +0.026 |

The limit is 0.03 log10 and all spectra pass. **The first run failed**: Planck 1800 K was -0.065, +0.013, +0.162. A run with no table smoothing gave +0.013, +0.003, +0.002, so the smoothing of `sigma_far` caused the error. The rule now acts after the smoothing, and the limit did not change.

Cost, p95 of the absolute error in log10, red, green, blue, on measured reflectances under D55:

| Set | Before | After |
| --- | --- | --- |
| `issa_skin` | 0.023, 0.006, 0.021 | 0.020, 0.006, 0.022 |
| `usgs_splib07` | 0.050, 0.008, 0.059 | 0.063, 0.009, 0.045 |
| `gutierrez_natural` | 0.082, 0.016, 0.075 | 0.127, 0.040, 0.154 |
| `rawtoaces_190` | 0.149, 0.034, 0.099 | 0.265, 0.069, 0.150 |

Skin passes its limit (growth at most 0.005). The other sets get worse, and this is the stated cost: for example, the far-red reflection of a blue flower is gone. XYZ of the table inside AP1: p99 relative error 1.1e-8 (limit 0.015). The largest error is 0.10.

Nodes that the family cannot reach: 13894 of the 26227 nodes in the sectors. Of these, 402 are inside the spectral locus and 66 are inside AP1 (local probe `reach_probe.py`, not committed), and the others are outside the locus. They keep the measured shape, and the weight falls to zero toward them (`LIGHT_REACH_FADE`), so the table has no step.

### 9.3 What the sources specify about the dyes

Script: `compare_dye_models.py`. Results: [`dye_models.json`](../../results/p4_physical_film_response/dye_models.json).

| Stock | Isolated dye curves | Fit of the neutral above D-min by the curves, RMS and largest residual |
| --- | --- | --- |
| 5207 | Digitized by spectral_film_lut; dropped by `import_cine_profiles.py` until now | 0.0027, 0.0067 |
| 5219 | Same | 0.0047, 0.0151 |
| Portra 400 | E-4050 does not publish them, and spectral_film_lut has none. Band split stays, inferred | Cine curves as a comparison only: RMS 0.0527 and 0.0495; largest 0.14 |

The profiles now hold these curves (`import_dyes_and_mtf.py`). They were not checked against Kodak documents.

Hypothesis from this calculation: the curves add up to the neutral above D-min within the digitization, and the magenta curve is below zero in the blue (lowest value -0.018 on 5207, -0.040 on 5219). An analytical dye cannot have a negative density. So the author reads these curves as net: the mask that a dye consumes is already in its curve. This is the reason the coupler model of work item W1 step 3 is **not added**: it would count the mask two times. The curves cannot show the point where a layer has used all of its coupler. This is an open limit. The Portra 400 neutral does not fit the cine dyes, so no family value is used for that stock.

Rule `dye_amount_curves` (option `negative_record`) corrects one error of the chain: a Status M curve is a reading of a neutral and not the response of one layer. With the Status M record, the dye solve removes the side absorption of each dye. With the dye amount record, each layer sets the amount of its own dye. The rule moves the coefficient from 0.200 to 0.163 at the Status M stage on 5207.

## 10. W3: crossover and timing in density

Script: `check_film_response.py`. Results: [`film_response.json`](../../results/p4_physical_film_response/film_response.json).

### 10.1 How the input is balanced

The input of this lab comes through LibRaw with the camera white balance, then XYZ, Bradford, and AP1 with the ACES white. Option `scene_light` (rule `relight`, U20) then exposes the reflectance shape under a spectrum, and `print_timing` removes a share of the cast. So exposure under the light already exists. Added: rule `light_from_raw_white` in `render_light_and_detail_review.py`, which estimates the light from the white of a RAW file (the McCamy formula, CIE daylight at 4000 K and above, and Planckian below). Four files: [`estimated_light.json`](../../results/p4_physical_film_response/estimated_light.json), 4716 K to 7487 K. This is a review only: U21 keeps the light as a manual choice in the product.

### 10.2 Crossover

Rule `density_timing` (`per_record_slope=False`): one slope, the mean of the three, and one offset per channel. Check: mid grey under the balance light is neutral within 0.002 linear per channel (measured spread 0.0). Pass.

a* and b* of the neutral ramp, with the APD record and the P4 options, from -5 to +5 stops. This is a property of the model, so no limit applies. The balance light is that of the stock.

| Stock | APD slope R, G, B | a* | b* |
| --- | --- | --- | --- |
| 5207 | 0.502, 0.575, 0.524 | 1.4, 2.3, 4.3, 4.5, 3.2, 0, -3.3, -3.9, -2.6, -1.3, -0.6 | -0.5, -0.7, -1.3, -2.4, -1.7, 0, 1.8, 2.0, 1.3, 0.6, 0.3 |
| 5219 | 0.515, 0.581, 0.533 | 1.6, 2.2, 4.1, 4.0, 2.9, 0, -3.0, -3.5, -2.1, -1.1, -0.5 | -0.8, -0.9, -1.7, -2.1, -1.6, 0, 1.8, 1.9, 1.1, 0.5, 0.2 |
| Portra 400 | 0.637, 0.585, 0.628 | -0.7, -1.4, -2.7, -2.8, -2.0, 0, 2.2, 2.9, 1.8, 0.9, 0.4 | 1.1, 1.1, 1.9, 1.8, 1.3, 0, -1.2, -1.6, -1.0, -0.5, -0.2 |

With the slope per record, the ramp stays within a* and b* of 0.91 on all stocks. How a real inversion program treats this difference of slopes is not known to this lab.

### 10.3 Author's visual results, not user review

Sheets of `review_w3/`:

- `frame_balance="image"` fails on portraits: on `se188` the skin turns grey-green and the flowers purple. It also takes the colour of the sunset of `fuji_xt5`. The author does not propose it.
- Density timing gives plum shadows on 5207 (`fuji_xt5`, the black top of `se188`). This agrees with the measured a* of about +4. It comes from the model, but it can read as "strange" colour, the first complaint of the user. So both forms are on the final sheets.
- The light estimated from the RAW white changes little on `se188` on 5207. On 5219 with a timing of 0.5, it keeps a cool cast.

Review control `P4_TONE` (display grey 0.32, black 0.004, `log_contrast` 0.92, `record_saturation` 0.95), chosen by eye: it takes back the slope of the product grade (P3-O12), and it uses a smaller black than the soft settings of P3, so low-key areas stay dark.

## 11. W2: interlayer inhibition

Rule `development_inhibition`: a_i = F_i(log H_i - sum_j K_ij G * a_j). F_i is computed so that a neutral returns the published curve. This rule is not independent of spektrafilm (correction of 2026-10-31, [P6 report](p6_python_mvp.md), section 5.2): no code or value of spektrafilm is used, but the first step of the fixed point is the same algorithm as `compute_density_curves_before_dir_couplers` and `compute_exposure_correction_dir_couplers` in `model/couplers.py`, and README section 3.2 records that the initial research read that method. It needs the dye amount record, and it stops with an error otherwise. `P4_PHYSICAL` turns `adjacency_gain` off, because the published modulation transfer already includes the edge effect.

Parameters, from the published modulation transfer. The form is M(f) = 1 / (1 + (2 pi s f)^2) * B / (1 + (B - 1) exp(-2 pi^2 sigma_d^2 f^2)). A Gaussian spread left an RMS residual of 0.03 to 0.07, and the exponential spread leaves 0.004 to 0.027. Script `fit_mtf.py`, results [`mtf_fit.json`](../../results/p4_physical_film_response/mtf_fit.json). Red, green, blue:

| Stock | Spread s, um | sigma_d, um | Boost B | Total K, log10 H per dye amount |
| --- | --- | --- | --- | --- |
| 5207 | 4.95, 3.02, 2.83 | 33.8, 46.3, 24.3 | 1.078, 1.045, 1.122 | 0.145, 0.079, 0.204 |
| 5219 | 5.00, 3.41, 3.17 | 60.0 (at the limit), 24.4, 26.8 | 1.106, 1.145, 1.192 | 0.184, 0.246, 0.283 |
| Portra 400 | 4.53, 3.21, 2.63 | 47.2, 32.2, 53.0 | 1.169, 1.265, 1.135 | 0.211, 0.336, 0.190 |

Inferred: the form of the fit; the single length of 35 um (`inhibition_um`), near the median of the values above, which the curves do not fix well; and `inhibition_cross_share` = 0.5, the split between a layer and the other layers, which has no source. The charts are from spectral_film_lut and were not checked against Kodak documents.

| Check | Limit | 5207 | 5219 | Portra 400 |
| --- | --- | --- | --- | --- |
| Neutral against the published curve, largest error | 0.02 density | 0.0004 | 0.0020 | 0.0016 |
| Six saturated ramps, -3 to +3 stops, largest fall | 0.001 density | 0.0 | 0.0 | 0.0 |
| Image form against point form, flat field | 0.002 amount | < 0.0001 | < 0.0001 | < 0.0001 |

Chroma against exposure of each chart colour, with and without the rule: `film_response.json`. On 5207, `blue sky` from -3 to +3 stops: with the rule 12.5, 17.7, 22.6, 24.1, 19.7, 11.8, 5.3; without 11.6, 16.3, 20.9, 22.5, 18.5, 11.0, 4.9. So the gain is about 7 %, and the path over exposure keeps its form. The published curves limit the size of K. This modest size agrees with the fact that the product grade already adds saturation (U24).

Author's visual results on `review_w2/`, not user review: the rule gives a small gain of colour. The difference between a cross share of 0.5 and 0 is hard to see on `canon_r`. So the image does not need a decision on this split now. **The P4 sheets do not use the density crosstalk of P3**: its reason was the sky, and it moved sunset orange toward pink. P3-O16 and P3-O17 can close if the review accepts this.

## 12. W4: optics of the layers

Rule `layer_spread`: an exponential spread with the length of the table above, per layer, in layer exposure, in micrometres on the film. Two Gaussians stand for the exponential (`SPREAD_GAUSSIANS`; largest error 0.028 in the transfer function). The frame is 36 mm wide (`frame_mm`), an assumption for all stocks. A 5207 frame in a cine camera is smaller, and this is not modeled.

Check (`check_film_response.py`, 4.5 um per pixel): the mean of the image changes by at most 1.6e-5 relative (limit 1e-4), and a flat field by at most 1.5e-8 (limit 1e-4). Pass.

Author's visual results on the full-resolution crop of `se224` in `review_detail/` (about 6 um per pixel, enlarged 2 times), not user review; the other 3 crops are rendered and not examined: the P3 setting (10 um and Eberhard) is clearly softer. `layer_spread` keeps more detail, and inhibition adds a little local contrast. A review at 1000 pixels (36 um per pixel) cannot show this. Halation stays as in P3, inferred: 5207 has a rem-jet backing, so the value may be too high on that stock.

## 13. Evidence for all items

| Evidence | Result |
| --- | --- |
| `check_scan_path.py`, with the default options | all pass |
| `check_fast_kernels.py`, with the default options | all pass. It does not cover the new rules. The new image form of inhibition is compared with its point form on flat fields only, and `layer_spread` has no array form |
| Hue sweep, largest second difference (limit 0.02) | 0.0090 to 0.0158 for the P4 paths on all stocks. Pass, after one fix |
| Labeled sheets | 43 files (37 landscape, 6 portrait), 16 panels each, three stocks. Review on the JPEG files |

**The sweep failed first** on the Portra 400 print: 0.0239. A trial switched each option on and off, and the cause is `light_like_spectra` together with the display clip. The more saturated sky reaches a gamut distance of 1.32 in cyan (p99.9 on the sweep; 1.26 and 1.25 on 5207 and 5219), and the ACES RGC limit of 1.147 leaves a clip. `P4_GAMUT_LIMIT` = (1.4, 1.3, 1.312), set from this measurement, removes the clip on the sweep for all three stocks. This is again a variant of the method of RGC and not the standard ACES RGC. The P3 options keep their limits.

Not measured: L* and C* statistics over the review files; the files of the P3 set outside these 43; the night files with the P4 options.

### Author's visual results on the P4 sheets, not user review

Sheets `se224`, `fuji_xt5`, `se167`, `se188`, and the sweep. The other 39 sheets are rendered and not examined:

- **Sky:** the violet of the direct inversion is gone on all stocks, and the sky is clean blue (`se224`). The print moves from grey to teal on 5207 and 5219. This is a strong change, and the teal can look too strong.
- **Sunset:** the direct inversion on 5207 keeps more gold than in P3, but the top of the sky of `fuji_xt5` is still pink. So the second open fault of P3 is reduced and not removed.
- **Skin:** the 5207 and 5219 paths stay near P3. **The Portra 400 print gets denser and more orange on `se188`, and the author finds this worse than P3.** The Portra 400 direct inversion is pleasant on skin.
- **Portra 400 print, sky:** a strong saturated blue on `se224`. This path needs the review most.
- **Tone:** `P4_TONE` is soft and keeps dark shadows on these files. The shadows of `fuji_xt5` are lifted a little.

These sheets do not show that the result looks like film. Only the user can decide this.

### Night files on the 5219 print

The user added 5 night RAW files (`alcedo_studio/tests/resources/sample_images/raw/night`, not committed) and asked for the P4 print of 5219. The direct inversion is not in this review, at the request of the user. Script: `render_night_review.py`. Results: [`night_review.json`](../../results/p4_physical_film_response/night_review.json). Pixels clipped after the gamut compression: at most 0.086 % per file. The light of the RAW white is 3538 K to 6588 K, and the exposure rule raises the files by 0.95 to 2.82 stops.

Author's visual results on the 5 sheets, not user review:

- Compared with P3, yellow leaves move from lemon to gold (`2136729222`), and lit sails from pale to orange (`P1031516`).
- T3200 with timing 1, the balance light of the stock, gives the most coherent warm lamps and keeps a blue sky. It is the proposal of the author for night files. Foreground pavement in `5437808984` turns warm brown under it.
- **Fault:** with D55 or a daylight light from the RAW white, a deep blue dusk sky moves to teal (`8390668518`, `P1031516`). T3200 reduces this and does not remove it on `8390668518`. The sodium mixture keeps the most blue.
- **Fault:** dark areas are heavy in all print panels: the crowd of `0696694599` and the band of `P1031516` lose detail that the plain image holds. P3 has the same fault, so it does not come from the P4 rules.

Comparison with spektrafilm (external comparison only, U18; nothing is reused; `render_spektrafilm_night.py`; default settings, its own automatic exposure, no grain, with its Vision3 500T and 2383 profiles). Each sheet has two panels of it: the input with no product grade, and the input after the product grade. Its exposure rule differs from the rule of this lab, so the tone level does not compare directly. Author's visual results on the 5 sheets, not user review:

- spektrafilm is darker and denser than the P4 print on all 5 files, with blacker shadows and less detail in the crowd and the band. So the P4 print is not the heaviest of the two, but this does not show that its shadows are right.
- It also moves the deep blue sky of `8390668518` toward cyan, with less chroma than the P4 print. So the direction of this change is shared by two models. This does not show that the direction is correct, and the chroma of the P4 print stays a candidate fault.
- Warm colours are near each other: gold leaves and orange sails. spektrafilm is a little more yellow on the sails of `P1031516`.
- The product grade before spektrafilm adds density and saturation, and it does not change the direction of these results.

User review (2026-10-30): the P4 print of 5219 on these night files is much better than spektrafilm.

### Daylight files on the 5207 and Portra 400 print

The user added 5 daylight RAW files (`alcedo_studio/tests/resources/sample_images/raw/daylight`, not committed) and asked for 5207 and Portra 400, with only the P4 results. The print is the path under review. Script: `render_daylight_review.py`. Results: [`daylight_review.json`](../../results/p4_physical_film_response/daylight_review.json). No pixel stays clipped after the gamut compression. `rawpy` gives no `rgb_xyz_matrix` for the two Sigma BF DNG files, so this review does not use rule `light_from_raw_white`. These files have a camera white balance and a `color_matrix`.

Author's visual results, not user review:

- **Fault, confirmed by a trial:** the violet iris of `8471933047` moves to blue on both stocks. This is the cost that section 9.2 states, on a real object. A local probe (`day_cause_probe.py`, not committed) switched each rule off. The median hue of the flower pixels in Lab is -54 degrees in the plain image. On Portra 400 it is -69 with the rule and -50 without it, and the other rules change it by at most 2 degrees. On 5207 it is -61 with the rule and -42 without it. So the P3 chain was on the magenta side of the plain image (-40 and -49), and the rule moves the flower past it to the blue side.
- **Blue sky:** teal on 5207 and a saturated cyan-blue on Portra 400 (`5897833591`, `5965296318`). The same rule moves it: on `5897833591` with 5207, a* of the sky is -16 with the rule and -5 without it. With the published dyes, the sky is also more teal than with the band split (hue -124 and -114 degrees).
- **Ground on Portra 400:** warm orange (`5897833591`, `3224436375`). The same probe shows that this does not come from the P4 rules: a* and b* of the ground are 8, 15 in the P3 chain and 9, 16 in the P4 chain. So this part of P4-O3 belongs to the chain of Portra 400 and Endura from before P4.
- **Good:** the pink of the cherry tree and the red of the car hold their hue on both stocks.
- **Greens on 5207** move toward olive. The cause was not traced.

User review (2026-10-30): the look of the P4 print on the night and daylight files is good by perception.

### Artificial light files on the print

The user added 4 RAW files (`alcedo_studio/tests/resources/sample_images/raw/artificial_lights`, not committed). Script: `render_artificial_light_review.py`, 5219 under five lights, 5207 under two, and Portra 400. Results: [`artificial_light_review.json`](../../results/p4_physical_film_response/artificial_light_review.json). Pixels clipped after the gamut compression: at most 0.161 % per file.

Author's visual results, not user review: the platform of `1438651342` and the car of `5348631143` hold well, and the choice of light changes these files little.

**Fault:** the magenta neon of `3754960364` washes to a pale lilac on all panels, and its blue reflection moves toward cyan. A local probe (`magenta_probe.py`, not committed) measured the neon pixels and the blue pixels on the 5219 print, with T3200 and timing 1. Median in Lab:

| Case | Neon: L, C, hue | Blue: L, C, hue |
| --- | --- | --- |
| Plain image | 60, 113, -33 | 32, 134, -54 |
| P3 print | 80, 27, -26 | 60, 35, -133 |
| P4 print | 85, 6, -55 | 61, 35, -133 |
| P4 print, no `light_like_spectra` | 84, 15, -19 | 61, 35, -133 |
| P4 print, input -1 stop | 78, 17, -60 | 52, 37, -107 |
| P4 print, input -2 stops | 68, 31, -59 | 42, 43, -82 |

Calculation and hypothesis: the graded AP1 of the neon has a median of (2.97, 0.02, 14.34), and 45 % of these pixels have a negative AP1 value. So the blue record is more than 6 stops above the grey, and the exposure rule of this review adds 2.64 stops on this file. The loss of chroma exists in P3 and it grows in P4. The chroma returns with less exposure, so the hypothesis is that the shoulder of the chain causes most of it. The plain image keeps its chroma because a display clip does not desaturate in the same way. The blue moves to cyan in P3 too, so the P4 rules do not cause that move. The exposure in the product is not this rule, so the size of this fault in the product is not known.

User review (2026-10-30), after the artificial light sheets: this is the wanted feeling. The user review covers the P4 print. The direct inversion, the slope of the inversion (P4-O2), and the faults P4-O10 to P4-O12 have no user decision.

### Eight mountain files on the 5207 and Portra 400 print

Author's visual results, not user review (2026-10-30). The files are 8 Sony RAW files that the user named (`_DSC4049` to `_DSC4306`). The options and the panels are the same as the daylight review. The sheets are local, in `build/tmp/p4/review_shangrila/`. No pixel stays clipped after the compression. The author read the sheets at about 660 pixels per landscape panel.

- Dark foregrounds lose most detail on both stocks (`_DSC4063`, `_DSC4069`). This agrees with P4-O10.
- The Portra 400 shadows go blue-black, and sunlit grass and soil go orange (`_DSC4196`, `_DSC4306`). User statement (2026-10-30): a red lean on Portra 400 is a characteristic of the stock, not a fault.
- 5207 moves white clouds to cream (`_DSC4049`, `_DSC4071`, `_DSC4196`). Portra 400 keeps them near neutral.
- Open sky at mid luminance moves to teal or cyan (`_DSC4049`, `_DSC4071`), and more on Portra 400. A deep sky stays blue (`_DSC4067`, `_DSC4069`). This agrees with P4-O10.
- Distant grey-blue ridges become a saturated blue, more on Portra 400 (`_DSC4250`, `_DSC4306`).
- The author sees no abrupt band in the skies or the flags at this size. This result is visual, and no band measurement ran on these files.

### Comparison with spektrafilm on 13 daylight files

Author's visual results, not user review (2026-10-30). The files are the 8 mountain files and 5 files of temples, a street, and a coast. Each sheet has the plain image, the graded input, the P4 print of 5207 and Portra 400, and spektrafilm at 3bb2c2d2 (external comparison only, README U18). The spektrafilm panels use Vision3 250D with 2383, and Portra 400 with Portra Endura, with its default settings, its own automatic exposure, no grain, and the same graded input. The sheets are local, in `build/tmp/p4/review_spektra_compare/`.

- Dark areas are as dark or darker on spektrafilm with 250D (`_DSC2197`, `_DSC4063`, `_DSC4069`, `_DSC4071`). So the loss of shadow detail on these files is not only a fault of the P4 print. The author's earlier note on these shadows is too strong.
- On Portra 400 the shadows have a similar level. They are blue-black on the P4 print and more neutral on spektrafilm.
- The P4 print of 5207 has more cream or green-yellow in clouds and overcast sky (`_DSC2173`, `_DSC2194`, `_DSC4071`) than spektrafilm.
- Spektrafilm has a cyan tint in the clouds of Portra 400 (`_DSC4196`, `_DSC4306`) and moves the greens of 250D to yellow (`_DSC4196`, `_DSC4306`). The P4 print does not.
- The P4 print of Portra 400 has a brighter and more saturated blue in the sky and distant ridges (`_DSC4063`, `_DSC4250`, `_DSC4306`).
- Both chains move the yellow barriers of `_DSC2197` to orange on Portra 400.

### Bands at green and blue of the hue sweep

User report (2026-10-30): the P4 print of 5207 has two abrupt changes on the hue sweep, at green and at blue. The measurements below use local probes. No production file changed, and `P4_PHYSICAL` did not change. The probes are local, in `build/tmp/p4/scripts/`: `sweep_rounded.py`, `green_notch.py`, `band_layers.py`, and `mask_probe.py`.

The bands are at the columns of the primaries (320 and 640). The test pattern has a corner at each primary. The depth is the fall of L* at the primary against the mean L* 60 columns to each side. The slope is the largest change of L* per column near the band.

| Case, after the product grade | Green, +1 stop | Green, 0 stop | Blue, +1 stop | Blue, 0 stop |
| --- | --- | --- | --- | --- |
| Graded input | 1.2 | 0.9 | 14.9 | 9.7 |
| P3 print | 6.5 | 3.6 | 16.5 | 9.4 |
| P4 print | 7.7 | 6.7 | 16.7 | 10.2 |
| P4 print, each layer free, before the gamut stage | 8.1 | 6.9 | 17.9 | 12.6 |
| Same, red layer flat across the band | 2.3 | 2.5 | 8.0 | 6.8 |
| Same, green layer flat across the band | 9.1 | 8.2 | 9.3 | 5.5 |
| Same, blue layer flat across the band | 5.5 | 3.8 | 18.0 | 12.7 |

- **Green: the chain makes this band.** The input has about 1 L*. The red layer falls at the primary (log10 exposure 0.835, 0.326, and 0.606 at columns 260, 320, and 380, row 1). This change is the largest cause in the table.
- **P4 makes the green band deeper than P3.** At 0 stop the depth is 6.9 with no inhibition, and 3.5 with the record `status_m`. The cause is the dye amount record: the cyan dye also absorbs in the green band. Cyan falls at the primary, so the Status M green reading falls (1.449, 1.426, 1.452), although the green amount rises (0.929, 0.943, 0.910). The display green falls too (0.147, 0.117, 0.166). The record `status_m` has no such fall (1.526, 1.536, 1.511).
- **These items do not cause the green band:** inhibition (6.7 against 6.9), `light_like_spectra`, the gamut stage, the print contrast, the flash, and the viewing flare. The direct inversion of the same negative has 5.1, so most of the increase occurs before the print stage.
- **Blue: the input has most of this band.** The blue primary has low luminance, so L* rises quickly when the red or green record rises. The chain does not make the band much deeper. The red layer and the green layer fall at the primary, and the red amount falls to about 0 (0.007 at column 645, then 0.772 at column 720). The input without the product grade has a blue band of 17.8 and 14.6, so the grade does not cause it.
- **Third place: red, at the wrap of the pattern.** The largest step between two columns is at columns 945 to 947 at +1 stop: 2.36 with `light_like_spectra`, and 1.63 without.
- **The check of the sweep cannot see these bands.** The second difference passes at 0.009 against a limit of 0.02, because a band spans tens of columns. This limit does not show that the sweep is smooth. A check over a window is necessary, with limits that a user decision sets.
- **Rounded corners do not remove the bands.** With a Gaussian of sigma 24 columns on the pattern, the green depth is 4.4 on P4 and 2.6 to 3.4 on P3, and the blue edge stays.

Probe with no source: a share of the Status M reading of each layer comes only from the neutral curve of that layer, so the cross absorption falls. The neutral stays on the same curve. The dye curves are read as net of the orange mask (section 9.3), so a source does not support this share.

| Mask share | Green, +1 stop | Green, 0 stop | Green, -1 stop | Blue, +1 stop | Blue, 0 stop |
| --- | --- | --- | --- | --- | --- |
| 0 (baseline) | 7.7 | 6.7 | 4.0 | 16.7 | 10.2 |
| 0.5 | 6.2 | 4.9 | 2.6 | 15.5 | 9.4 |
| 0.75 | 6.0 | 4.0 | 1.8 | 14.9 | 9.0 |
| 1 | 7.4 | 3.2 | 1.1 | 14.4 | 8.7 |

The probe gives the green band of P3 again at 0 stop and at -1 stop. It does not remove the green band at +1 stop or the blue band. At share 1 the edge slope of green at +1 stop increases from 0.20 to 0.32. The sweep has visibly more saturation, so the probe changes the accepted look. The probe was not run on photographs.

Not traced: why the red layer exposure rises after column 320 (the part from the spectrum against the part from the AP1 value). Whether photographs show the bands at a visible size is not measured.

### User decision that closes this step

User decision (2026-10-30, U32): P4 is complete. The print is the accepted look. A red lean on Portra 400 is a characteristic of the stock, not a fault. So the Portra 400 items of the author's notes in this section are not faults. The user made no decision on the bands of P4-O13, and `P4_PHYSICAL` stays as it is.

## 14. Machine and commands

Intel Core i7-12700H, 31.8 GB, CPU only. No GPU job. Commands: [script README](../../scripts/poc/p4_physical_film_response/README.md).

## 15. Open items

| ID | Item | Owner |
| --- | --- | --- |
| P4-O1 | Review of the 43 sheets: `build/tmp/p4/review_p4/`. Start with the sky, the sunset, and the skin of the Portra 400 print. | User |
| P4-O2 | Decide the slope of the inversion: density timing (from the model, plum shadows on cine stocks) or one slope per record (clean neutrals). | User |
| P4-O3 | The Portra 400 print is denser and more orange on skin. Isolate the cause (dye amount record, inhibition, or light rule). | P4 |
| P4-O4 | `inhibition_cross_share` and the length of the inhibitor have no source. | No source found |
| P4-O5 | The dye curves and the modulation transfer curves were not checked against Kodak documents. The Kodak data sheets of 5207 and 5219 are not in the lab. | P4 |
| P4-O6 | The point where a layer uses all of its coupler is not modeled (section 9.3). | No source found |
| P4-O7 | Run the P4 options on the rest of the P3 set and on the 6 earlier night files. The print of 5219 on 5 new night files is done. | P4 |
| P4-O10 | The print moves a deep blue sky to teal or cyan under a daylight light, and dark areas are heavy at night. | P4 |
| P4-O12 | Very bright saturated lights wash out and blue moves to cyan on the print (`3754960364`). | P4 |
| P4-O11 | Rule `light_like_spectra` moves violet objects to blue (the iris of `8471933047`). The blue sector needs a limit on its violet side. | P4 |
| P4-O13 | The hue sweep has bands at green and blue, and a step near red (section 13). The dye amount record makes the green band deeper. The second difference check cannot see the bands. Decide if the band at green or at blue needs a change, and set the limits of a window check. | User |
| P4-O8 | Close P3-O12, P3-O16, P3-O17, and P3-O18 if the review accepts the result. | User |
| P4-O9 | The new rules are not in the reference evaluator of `check_fast_kernels.py`. P6 needs this before a table replaces them. | P6 |

## 16. Completion record (2026-10-30)

**Status:** complete by user decision (U32). The four work items have code, numeric checks, and sheets. The user accepts the look of the print. The direct inversion has no accepted look, and W1 step 3 was replaced by a measurement (section 9.3).

**Primary success call chain:**

```text
render_p4_review.py --set p4
  -> film_preview.product_input (default grade, U24)
  -> FilmPreview.negative_image
     -> fast_kernels.layer_exposure (u'v' table: smoothing, then rule light_like_spectra)
     -> FilmPreview._spread_layers (rule layer_spread)
     -> fast_kernels.negative_density (rule dye_amount_curves)
     -> FilmPreview._inhibited_image -> fast_kernels.inhibited_step (rule development_inhibition)
  -> print: fast_kernels.print_display, finish_display (P4_GAMUT_LIMIT)
     or scan: DirectInversionPreview.table_apd -> render (rule density_timing, P4_TONE)
  -> labeled sheet in build/tmp/p4/review_p4/<name>.jpg
```

**Primary failure call chains:**

```text
inhibition_total set, negative_record = 'status_m'
  -> FilmPreview._prepare_inhibition raises ValueError; nothing renders
reduced exposure of a neutral does not rise
  -> FilmPreview._prepare_inhibition raises ValueError: F_i does not exist
negative_dye_basis = 'published' on a stock with no isolated curves
  -> ReferenceModel.__init__ raises KeyError; no substitute dye
RAW file with no camera white balance or matrix
  -> estimated_light raises ValueError
```

**What was proven:**

| Criterion | Script | Result |
| --- | --- | --- |
| W1: sum of the stages equals the total, within 0.01 | `trace_colour_error.py` | PASS, 10 cases |
| W1: base and neutral, p95 at most 0.01 density | `trace_colour_error.py` | PASS, at most 0.0054 |
| W1: light-like spectra at most 0.03 log10; skin growth at most 0.005; table XYZ | `check_light_spectra.py` | PASS, after one fix |
| W2: neutral curve at most 0.02; no fall above 0.001; image against point | `check_film_response.py` | PASS, 3 stocks |
| W3: mid grey neutral within 0.002 linear | `check_film_response.py` | PASS, 3 stocks |
| W4: mean within 1e-4; flat field within 1e-4 | `check_film_response.py` | PASS, 3 stocks |
| Section 5: earlier checks stay valid | `check_scan_path.py`, `check_fast_kernels.py` | PASS |
| Section 5: hue sweep at most 0.02 | `render_p4_review.py` | PASS for the P4 paths, after one fix |
| User review of the print | - | ACCEPTED (U32) |
| User review of the direct inversion | - | NOT DONE, set aside |
| Hue sweep has no band over a window | - | NOT CHECKED, the bands exist (P4-O13) |

**Remaining gaps:** section 15.
