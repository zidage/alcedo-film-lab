# P12: the model negative against the real 5207 negative, on the same pixels

Date: 2026-11-04. Author: Claude. Status: measured; user review open. No change to the model or the product.
This is one of two parallel directions after the reset of the decisions (ROADMAP section 2). The other is
[P11](p11_codex.md) (Codex): the stages after the negative, from first principles.

## Question

Every print is too vivid, some scans look ugly, and the photo stocks differ little. Which stage causes it: the
negative or the print? The only real film data is the 5207 roll of the user, scanned on a Hasselblad X5. Two digital
photos of the same scene (Sony ILCE-7RM3) are registered to the frames f15 and f14:
- `_DSC4976`, 2023-06-24 20:15:09 (P5 report, section 29);
- `_DSC4909`, 20:10:58, found by the user because in `_DSC4976` the sun had already left the summit.
The film frames have no time. In the four minutes between the two digital photos the light on the summit changes from
pink alpenglow to none, so the colour of a digital photo is not the colour of the scene when the film was exposed.

## Data and readings

- Real negative: X5 code, gamma 2 as a hypothesis, density above the base = -2 log10(code / base code).
- Model negative: the current viewer model of kodak_5207 (Lab Scan options, scene light daylight), with the
  registered digital photo as input. Exposure: the smallest error on G (+3.0 and +3.25 stops for f15).
- Registration (`pair_register.py`, method of U57): `_DSC4909` to f15, correlation 0.978; to f14, 0.949.
- The X5 channels are unknown, so the model negative is read three ways: APD, Status M, and the camera sensitivities
  of the Sony ILCE-7RM3 under a flat light (a broad reading). With gamma 2 and an open gate of 1, the X5 base density is
  0.262, 0.560, 0.774. The model base is 0.211, 0.549, 0.838 in APD and 0.339, 0.578, 0.773 in the broad reading. So
  gamma 2 is plausible (G within 0.01), and the X5 reading lies between the two. "X5 proxy": per channel, the blend of
  the two readings that gives the X5 base exactly (camera share 0.43, 0.39, 0.98).
- Mask: pixels where the G density follows the digital photo within 0.08 (removes the moving cloud). Both sides are
  blurred by 3 px (sigma) against grain.

## Measures

- Colour over neutral gamma: the off-axis density (normal to the grey axis, minus its median at each level of the grey
  axis, so no cast and no crossover), rms, per unit of the off-axis spread of log10 of the digital scene, over the slope
  of the grey axis against log10 of the scene luminance.
- On the display (CAM16, the viewing of the P10 sweeps): mean colourfulness M; local separation (rms of a', b' about
  the median of each of 16 lightness bins); the colour along the tone. Each is over the digital photo through OpenDRT
  with no film, at the same median lightness.

## Results

### 1. Colour separation of the negative: no difference shown

| Pair, frame | Real (X5) | Model, APD | Model, broad reading |
| --- | --- | --- | --- |
| `_DSC4976`, f15 | 1.40 | 0.81 | 0.55 |
| `_DSC4976`, f14 | 1.52 | 0.78 | 0.54 |
| `_DSC4909`, f15 | 0.65 | 0.76 | 0.52 |
| `_DSC4909`, f14 | 0.67 | 0.76 | 0.52 |

With `_DSC4909` the real value lies between the two readings of the model, as the X5 reading does. The first pair gave
twice the model value because the digital photo has less colour than the scene had for the film (off-axis spread of
the digital scene 0.023 against 0.055). The 2x2 colour transfer from the digital photo to each negative (a comparison
tool, not a film stage) turns by +46 degrees for the real negative on the first pair and by -44 degrees on the second;
the model turns by less than 17 degrees on both. A change of four minutes moves the real result more than any film
property here. So this pair cannot measure the hue or the separation of a single direction of the real film. The
earlier statement of this report (2026-11-04, first version) that the real negative separates colours twice as much
is withdrawn.

Development inhibition at scale 0 to 2 changes the separation of the model by about 10 %; the spectral prior of the
input (`measured_reflectance` against `light_like`) by 30 to 50 %.

### 2. The print stage makes the real negative vivid too

The same print tables, f15, X5 proxy reading, the real negative timed to the median of the model negative (one offset
per channel). M and local separation are over the digital photo.

| Path | Model negative (`_DSC4909`) | Real negative (`_DSC4909`) | Real negative (`_DSC4976`) |
| --- | --- | --- | --- |
| Lab Scan (generic scan) | 1.07 / 1.14 | 0.97 / 1.16 | 0.88 / 2.52 |
| 2383 print, now | 1.68 / 1.42 | 1.54 / 1.33 | 1.41 / 3.14 |
| 2383 print, values before U78 | 1.57 / 1.29 | 1.44 / 1.18 | 1.38 / 2.75 |
| Endura print, now | 1.59 / 1.28 | 1.48 / 1.30 | 1.47 / 3.03 |
| Endura print, values before U78 | 1.46 / 1.22 | 1.35 / 1.22 | 1.35 / 2.78 |

- The print turns the real negative into 1.4 to 1.5 times the colourfulness of the digital photo, and the scan into
  0.9 to 1.0 times. The model negative adds 7 to 9 % on the second pair. This ratio of print to negative does not
  depend on the time of the digital photo. So most of the vividness of the prints comes from the print stage. P11
  finds the cause there: the slopes of the Endura paper near grey are 3.1 to 3.4.
- The values that U78 removed (print_flash 0.02, print_contrast 0.85, viewing_flare 0.003) lower M by 6 to 9 %.
- By eye (sheet `pair4909/pair_print_f15_blur3_x5proxy.jpg`): the model print and the real print have about the same
  saturation; the model has darker, bluer shadows and pinker alpenglow, the real negative a gold summit and a green-teal
  near slope. The hue of the summit depends on the time, so it is not evidence.

### 3. The real negative has a lower contrast (both pairs)

Slope of each channel against log10 of the scene luminance: real 0.41 to 0.43; model 0.51 in the X5 proxy reading.
Its shadows print lighter (J 16 against 12) and less blue. A veiling glare of the taking lens is one physical cause:
the option `scene_flare` (0 in the viewer) at 0.02 of AP1 lowers the slope of the model in APD from 0.91 to 0.78
(real 0.69 in the X5 reading, which is broader than APD) and moves its shadow colour toward the real one. This is a
check on one scene, not a measured flare.

## 4. Can the scan keep the differences between stocks? (2026-11-04, after the user's note)

The user asks how the scan can keep the differences between stocks; a print would level them anyway. Probe
`build/tmp/p12/scan_reading_spread.py`: Lab Scan with the default controls, rule generic_scan derived again for each
reading on the photo pool, CAM16 sweep under daylight, seven photo stocks (the pool and UltraMax 400). Spread: mean
dE' of each stock to the mean of the stocks, -4 to +4 stops. The check against the viewer model gives a largest code
difference of 0.

| Scan | Spread, output | Spread, character | Colourfulness ratio at 0 EV, lowest to highest |
| --- | --- | --- | --- |
| Reading print2383 (default) | 1.67 | 1.56 | 0.86 (Gold 200) to 1.10 (Ektar 100) |
| Reading APD | 1.63 | 1.52 | 0.86 to 1.09 |
| Reading Status M | 1.73 | 1.61 | 0.86 to 1.09 |
| Narrow LED channels 455, 535, 660 nm, 25 nm FWHM (assumed) | 1.57 | 1.47 | 0.86 to 1.08 |
| print2383, generic CDD_TO_CID with the Academy EXP_TO_ACES | 1.70 | 1.60 | 0.97 to 1.25 |
| print2383, Academy numbers | 1.49 | 1.41 | 0.72 to 0.93 |

The reading and the numbers change the colourfulness of every stock together (EXP_TO_ACES of rule generic_scan is
fitted to the scene colours of the pool, so the average stock reproduces the scene), but not the differences between
stocks. The differences are in the negatives. Every photo stock of the model has band-split dyes, because the Kodak
data sheets of photo stocks give only the midscale neutral and the minimum density. So the three dyes of every photo
stock have the same structure: peaks within 8 nm (cyan 688 to 704, magenta 540 to 550, yellow 442 to 448 nm), and
4 to 20 % of each dye outside its own band, from the blur of the band edges. The cine stocks have the isolated dyes of
spectral_film_lut: 5207 has 19 % and 26 % of its cyan and magenta dyes outside their bands. Gold 200 has no
modulation transfer chart, so it has no inhibition.

## 5. Trial: a creative control 'stock character' k (user choice of 2026-11-04)

The user chose to try a control that enlarges the differences that the data of each photo stock already has. Local
probe `build/tmp/p12/character.py` (the profiles are changed in memory before the model is built) and
`character_run.py`. The reference is the mean of the photo pool of rule generic_scan; k = 1 is the data.

- Spectral sensitivity, per layer: the centroid and the log width of the main lobe (log sensitivity within 1.5 of the
  peak, weighted by the sensitivity) become pool mean + k (stock - pool mean); the wavelength axis of the curve of
  the stock moves and stretches to them, so its own shape stays.
- Characteristic curves, per channel: density above the lowest density against log H relative to the 18 % grey
  exposure of the stock (midscale_log_h); deviation from the pool mean on the range that every pool stock covers, held
  at the ends outside it; new curve = curve + (k - 1) deviation, made non-decreasing.
- Dyes, inhibition, and the scan are unchanged. Rule generic_scan is derived again for each k; the mean of the pool
  does not change with k.

At k = 2 the centroids move by 1 to 13 nm and the curve slopes by 2 to 10 %. The magenta lobe width differs most
between stocks (24 to 47 nm), so it changes most.

| k | Spread, output | Spread, character | Colourfulness at 0 EV, lowest to highest |
| --- | --- | --- | --- |
| 1 (data) | 1.67 | 1.56 | 0.86 (Gold 200) to 1.10 (Ektar 100) |
| 2 | 3.14 | 2.89 | 0.74 (Portra 160) to 1.13 (Ektar 100) |
| 3 | 4.63 | 4.29 | 0.59 (Portra 160) to 1.16 (Ektar 100) |

The spread grows in proportion to k. For scale, the Film Analyzer scans (test only) show 5.6 Delta E*ab between Portra
400 and 5207. Sheets (local; rows: stocks; columns: k = 1, 2, 3): `build/tmp/p12/character/sheet_<photo>.jpg` for
se188, se274, se357, se222, and the night photo 5253219691. Seen by the author at k = 2: Ektar 100 gives a redder dune
and redder skin with more contrast; Portra 160 is paler and turns the magenta flowers toward violet; Gold 200 turns the
sky toward teal; C200 makes the sand more golden; UltraMax 400 turns the sky toward violet. At k = 3 these are strong
(Portra 160 violet flowers and grey skin, Gold 200 teal sky). The portrait files are shown without their orientation
flag, as in P11.

In the viewer (user request of 2026-11-04): control `stock_character` (window: Stock character, group Negative; CLI
`--stock-character`; range 0 to 3, step 0.25, default 1), rule `stock_character` of `scripts/poc/p6_mvp_gui/stock_character.py`,
for the print, Lab Scan, and chart scan methods and both media (the cine pool is that of rule generic_scan). The changed
profile has its own name (`<stock>@stock_character=<k>`) in `PROFILE_OVERRIDES` of `film_spectral_reference.py`; no file is
written. Rule generic_scan keeps the setup that it derives from the data (k = 1), as a scanner set for the average
negative; so the spread at k = 2 is 3.18 dE' (output) and 2.93 (character), against 3.14 and 2.89 in the probe, which
derived the setup again from the changed pool. Checks: the range check names the control; the window shows it and passes
it to the settings; the print and chart scan methods render at k = 2. User review open.

## Limits

- One scene, two frames, one stock. There is no real photo-stock pair and no real print or lab scan of this roll.
- The film frames have no time; the light changes within minutes.
- FlexColor metadata: Gamma 2, FilmCurve 4, ApplyCurves true, Saturation 15. Which of these are in the stored pixels
  is not known.
- The X5 reading is a proxy fitted to the base density only.

## Files (local; private photographs)

`build/tmp/p12/`: `pair_register.py`, `pair_separation.py`, `pair_variants.py`, `pair_print.py`. Without environment
variables they use the `_DSC4976` pair (`build/tmp/p5/real_5207/pair/`, results in `build/tmp/p12/`); with
`P12_PAIR=build/tmp/p12/pair4909 P12_DIGITAL=_DSC4909` they use the second pair (results in that folder);
`P12_VARIANTS=flare` selects the flare variants. Every panel of a sheet has a label. Environment: `build/tmp/p6/venv`.

## Open

User review. The print stage is the main amplifier on real data; P11 proposes an audit of the off-neutral response
of the paper with independent data. A photo-stock pair (a digital photo and a negative exposed at the same moment)
would remove the main limit of this report.
