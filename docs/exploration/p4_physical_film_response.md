# P4: Physical colour and film response

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P4, with decision U31.
**Date:** 2026-10-30.
**Status:** not started. This report states the work. No result in this report comes from P4.

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
- Spectral acceleration (P5) and the GPU backends (P6).
- Grain.
