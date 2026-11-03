# P9: reversal film on a light table

Step P9, ROADMAP U86. Scripts: [`scripts/poc/p9_reversal_light_table/`](../../scripts/poc/p9_reversal_light_table/README.md). Results: [`results/p9_reversal_light_table/`](../../results/p9_reversal_light_table/).

## 1. Question

The user asked on 2026-11-03 to add colour reversal films (Velvia, E100, and similar) to the model, with the data of Fotufilm and spectral_film_lut, and with the public data sheets that the user supplied. A reversal film has no print film. The user asked for a view "like a light table", with the enlargement only.

Can the model of this lab take a RAW file through a reversal film and a light table, from the published data of each film, with the spectral input, the layer optics, and the development rules of the negatives?

## 2. Result summary

- Five films run in the Python viewer as method `light_table`: Fujichrome Velvia 50, Velvia 100, Provia 100F, Astia 100F, and Kodak Ektachrome E100.
- E100 and Velvia 100 are digitized by this lab from the vector paths of the data sheets that the user supplied. Velvia 50 and Provia 100F come from spectral_film_lut, because their sheets have raster charts. Astia 100F comes from the Fotufilm profile (CC BY-SA 4.0).
- The record of the model is the removed dye (rule `removed_dye_record`). It rises with exposure, so the spread, halation, and inhibition of the negatives act on a slide with no change in their code. The inhibition acts as the interimage effect of the first developer.
- The view is the transmittance of the slide under CIE D50 (ISO 3664), the CIE 1931 observer, the clear film as display white, the dark surround of a loupe, and the flare of the loupe in linear light.
- All checks pass inside limits that were set before the run (section 6). The print and APD output of the viewer does not change: largest difference 0.0 on three settings.
- The first render showed E100 strongly blue, because its absolute sensitivity chart puts the grey of D55 up to 0.85 stops off on the blue layer, and a slide has no printer lights to take that back. Rule `daylight_reversal_balance` now gives each film the grey anchor at D55. The neutral of the published curves stays, so each film keeps its own cast (U36).
- The user accepts the result (2026-11-03, section 9). The product (Alcedo Studio) does not have this method yet.

## 3. Inputs

| Film | Values | Source |
| --- | --- | --- |
| Kodak Ektachrome E100 (`kodak_ektachrome_e100`) | all charts | KODAK Alaris E-4000, Revised 8-18, pages 3 and 4, vector paths, digitized by this lab |
| Fujichrome Velvia 100 (`fuji_velvia_100`) | all charts | FUJIFILM AF3-202E, page 8, vector paths, digitized by this lab. The text is outlined, so each axis comes from the grid lines |
| Fujichrome Velvia 50 (`fuji_velvia_50`) | all charts | spectral_film_lut (MIT) at `bcbcfc68`, from AF3-0221E2 (raster charts) |
| Fujichrome Provia 100F (`fuji_provia_100f`) | all charts | spectral_film_lut (MIT) at `bcbcfc68` (raster charts in the bulletin) |
| Fujichrome Astia 100F (`fuji_astia_100f`) | curves, sensitivity, dyes; no modulation transfer | Fotufilm profile `astia100f.json` at `6b45c802` (CC BY-SA 4.0), digitized by Fotufilm from AF3-149E |

The URL, the edition, and the SHA-256 of each sheet are in [`sources.json`](../../scripts/poc/p9_reversal_light_table/sources.json). The sheets are not committed (U10). spectral_film_lut also has Kodachrome 64, Aerochrome III, and other reversal materials, and Fotufilm has Agfachrome and Kodachrome. They are not in this step, because the user named Velvia and E100.

Input images: the AP1 arrays of the representative set of steps P3 to P5 (16 files of day, night, and portraits, and two night files of step P4), with the product grade (+1.5 EV, contrast 15, saturation 1.0).

## 4. Method

### 4.1 Source observations

- The characteristic curves of all five films are Status A densities that fall with exposure, from a D-max of 3.2 to 3.8 to a D-min of 0.08 to 0.17.
- E100 states an absolute sensitivity (erg/cm², criterion E.N.D. 1.0). The Fuji charts are relative (log, density 1.0 above D-min). The Fotufilm values are linear and relative.
- E100 states its dyes normalized to a visual neutral of 1.0 for a 5000 K viewing light, with the neutral on the same chart. No film has a D-min spectrum.
- The modulation transfer of Velvia 50 rises to 1.22, of Provia 100F to 1.17, and of Velvia 100 to 1.06. E100 stays below 0.97 on all three layers.

### 4.2 Calculations and rules

- **Fotufilm exposure axis** (rule `fotufilm_exposure_axis`, measured). The exposure coordinate x of a Fotufilm reversal profile is log10 H - log10(10 / ISO), and the profile stores the formed density D-min + D-max - D. With this rule, the Fotufilm curves of Provia 100F and E100 lie on the curves of spectral_film_lut within RMS 0.006 to 0.019 density (fitted offset 1.002 to 1.006 against the expected 1.0). On Velvia 50 the fitted offsets were 0.656, 0.708, and 0.716 against the expected 0.699.
- **Removed dye record** (rule `removed_dye_record`). One dye solve with Status A weights on the neutral ramp gives the amount a_i(log H) of each dye. The record is s_i = a_i,max - a_i. Rule `development_inhibition` acts on s with no change: s_i = F_i(log H_i - sum_j K_ij G * s_j). In E-6 the inhibitor couplers are in the first developer, which develops a black-and-white negative. A layer that develops more silver gives less silver to the other layers, so they keep more dye: a colour gets more saturation and a neutral keeps the published curve.
- **Criterion** (rule `reversal_criterion`, in `film_spectral_reference.py`). Q_i = 1 is the exposure where the falling curve reaches the criterion density of the sensitivity chart. This branch acts only on a profile with `film_type` `reversal`.
- **Grey** (rule `daylight_reversal_balance`). Each film has rule `grey_anchor` with D55 as the balance light, and the grey exposure is 12.5 / ISO lux seconds (rule `stock_options_from_catalog`). At the scene light `reference` the input is white balanced, so the scene light is D55. Another scene light keeps its cast on the slide, because a slide has no printer lights and no timing.
- **Spread and inhibition**. The fits of steps P4 to P7 on the record s: the total K from a free fit, then the image part at 35 µm, and rule `inhibition_total_from_image_part` (U80). Astia 100F has no modulation transfer curve, so it has no spread and no inhibition. A value of another film is not used.
- **Light table** (rule `light_table_view`). XYZ = integral of 10^-(sum a_i d_i(λ)) × D50(λ) × CMF(λ), on a table of 65³ nodes over s (cube root of XYZ). CIE D50 stands for the lamp of a transparency viewer of ISO 3664 (inferred: a real light table is fluorescent or LED).
- **Loupe flare** (rule `loupe_flare`): (1 - f) × RGB + f × Gaussian(RGB), in linear light, with f = 0.01 and sigma 0.1 of the long side (the values of the enlarger flare of the print; not measured for a loupe). This is the control "Enlarger flare" of the viewer on this method.
- **Display** (rule `clear_film_white`): through a loupe the clear film is the brightest light in view, so its XYZ goes to display white with Bradford adaptation to D65. The loupe hides the bright table around the slide, so the surround is dark: the exponent 0.525 / 0.59 on luminance of the cine print. Then the display compression of the print and sRGB.

### 4.3 Hypotheses that were not tested

- The surround of a light table with a loupe is dark. A loupe with a clear skirt lets light of the table in; the surround is then dim, and the exponent is 1.
- Fotufilm uses the same view for a transparency (`NegativeViewing.lightBox`, the clear base at 0.9 of white). This lab reuses no code or value from it.

## 5. Metrics and machine

Machine: Intel Core i7-12700H, 31.8 GB, Windows 11, CPU only (Python, NumPy, Numba). Commands: [script README](../../scripts/poc/p9_reversal_light_table/README.md).

Limits, set before the first run of each script:

| Check | Limit |
| --- | --- |
| One source against another | RMS at most 0.03 density (characteristic, peak-normalized dyes), 0.05 log10 (sensitivity; a relative chart after the removal of its mean offset per layer), 0.05 response (modulation transfer) |
| Axis of a digitized chart | each grid line or tick at most 0.6 pt from the line of its value |
| Neutral ramp against the published curve | at most 0.01 Status A density |
| Clear film to display white | at most 1e-6 in linear light |
| Table against the direct integral, 20000 random records | largest at most 1.0 and p99.9 at most 0.25 of an 8 bit sRGB code |
| Extreme input (AP1 from -1 to 1e4, hue sweeps) | finite output in 0 to 1 |

## 6. Results

### 6.1 Sources ([`source_checks.json`](../../results/p9_reversal_light_table/source_checks.json))

| Film | Against | Characteristic | Dyes | Sensitivity | Modulation transfer |
| --- | --- | --- | --- | --- | --- |
| E100 (lab) | Fotufilm | 0.0021 | 0.0010 | 0.0211 | no curve |
| E100 (lab) | spectral_film_lut | 0.0217 | 0.0105 | **0.077** (over 0.05) | 0.0261 |
| Velvia 50 (spectral_film_lut) | Fotufilm | **0.0524** (over 0.03) | 0.0234 | 0.0091 | no curve |
| Provia 100F (spectral_film_lut) | Fotufilm | 0.0073 | 0.0125 | 0.0174 | no curve |

The E100 sensitivity of spectral_film_lut is the outlier: the lab digitization of the vector paths agrees with Fotufilm within 0.021, and spectral_film_lut differs by up to 0.22 log10 on the magenta-forming layer. On Velvia 50 the red curve differs most (largest 0.18 density); both projects read the same raster chart, and the vector source does not exist, so this lab cannot tell which is right.

Axis calibration: all charts of E100 are at most 0.03 pt from their ticks. Velvia 100: characteristic 0.36 pt, sensitivity 0.22 pt, dyes 0.23 pt, and modulation transfer **0.61 pt, over the limit of 0.6 pt**. The grid lines of that chart are drawn with uneven steps; 0.61 pt is 0.008 log10 of the response. The value is recorded and the profile is kept.

### 6.2 Fits ([`reversal_physics.json`](../../scripts/poc/p9_reversal_light_table/reversal_physics.json))

| Film | Grey of D55 with the chart level (stops, R G B) | Status A of the grey (R G B) | Spread (µm) | K image part (R G B) | B at 35 µm | Largest fit RMS |
| --- | --- | --- | --- | --- | --- | --- |
| Velvia 50 | -1.58, -1.23, -1.09 (relative chart) | 0.935, 0.876, 0.871 | 4.52 | 0.176, 0.245, 0.238 | 1.378 | 0.014 |
| Velvia 100 | -0.95, -0.61, -0.62 (relative chart) | 0.816, 0.818, 0.797 | 3.40 | 0.017, 0.019, 0.019 | 1.032 | 0.051 |
| Provia 100F | -1.37, -0.91, -0.44 (relative chart) | 0.845, 0.844, 0.843 | 4.98 | 0.151, 0.181, 0.215 | 1.320 | 0.036 |
| Astia 100F | -1.03, -1.03, -0.86 (relative values) | 0.849, 0.849, 0.852 | none | none | none | none |
| E100 | +0.28, +0.48, +0.85 (absolute chart) | 0.859, 0.880, 0.819 | 5.87, 4.17, 3.38 | 0, 0, 0 | 1.000 | 0.027 |

E100 has no rise above 1 on its modulation transfer, so the image part is zero, and by rule `inhibition_total_from_image_part` it has no inhibition. The free fit gave K 0.21 to 0.38 with an inhibitor length under 7 µm, the case of U74.

### 6.3 Checks ([`checks.json`](../../results/p9_reversal_light_table/checks.json))

All within limits. Neutral ramp: largest 0.0045 density (Provia 100F). Clear film: (1, 1, 1) within 6e-8. Table against the integral: largest 0.80 and p99.9 0.248 of a code on Velvia 100 (limit 0.25), and lower on the others. Extreme input: finite and inside 0 to 1 on all films. Display code of an 18 % grey:

| Film | sRGB code (R G B) |
| --- | --- |
| Velvia 50 | 0.466, 0.524, 0.535 |
| Velvia 100 | 0.517, 0.542, 0.577 |
| Provia 100F | 0.488, 0.507, 0.521 |
| Astia 100F | 0.485, 0.515, 0.537 |
| E100 | 0.497, 0.518, 0.566 |

These leans are the neutral of the published curves under D50 and the clear film white; they are a property of each film (U36). Before rule `daylight_reversal_balance`, the E100 grey was 0.524, 0.614, 0.751.

Cost on an AP1 array of 953 × 633 pixels: a model takes 2.9 to 3.2 s, a render 0.23 to 0.31 s. The viewer keeps the model of the last settings, as for the print. Not measured: a render at 2048 pixels and the peak memory.

Print and APD of the viewer, before and after the change of the shared files (`film_spectral_reference.py`, `mvp_pipeline.py`): largest difference 0.0 on 5207 with Endura Premier, 5219 with Cine Look, and Portra 400 by APD, on `leica_m11`.

### 6.4 Review sheets (local, `build/tmp/p9/review/`)

`render_p9_review.py` writes three sheets of the 18 files, with the five films and the default print of the viewer (5207 on Endura Premier) as a comparison, and two sheets of the scene lights on Velvia 50 and E100. Each panel has the file, the film, and the method. Observation of the author, not a user review: the slides have more contrast and deeper blacks than the print; Velvia 50 has the most saturation, with deep greens and blues; Astia 100F and Provia 100F are softer; E100 is clean, with a small cool lean.

## 7. Recommendation

The user reviews the sheets and the viewer (`p6_mvp_gui.py`, method "Reversal film on a light table"). The decisions that are open for the user:

1. The look of each film, and whether a film must not be in the list.
2. The surround of the light table: dark (a loupe, now) or dim (exponent 1).
3. A port to Alcedo Studio. The product has the print method only (U69). A port needs a fourth record type in the film print DRT: the removed dye record, the light table table in place of the print table, the flare of the loupe in linear light, and the surround in linear light. The image steps of the negative stay the same.

## 8. Open items

- P9-O1: closed 2026-11-03, the user accepts the result (section 9). The surround stays dark.
- P9-O2: the red curve of Velvia 50 differs between spectral_film_lut and Fotufilm (RMS 0.052); the vector source does not exist.
- P9-O3: the modulation transfer chart of Velvia 100 has an axis residual of 0.61 pt (limit 0.6 pt).
- P9-O4: Astia 100F has no modulation transfer curve, so it has no spread and no inhibition.
- P9-O5: the lamp of the light table is CIE D50; no lamp spectrum of a real viewer is used.
- P9-O6: not measured: renders at 2048 pixels and more, peak memory, and a GPU path.
- P9-O7: the other reversal materials of spectral_film_lut and Fotufilm (Kodachrome, Agfachrome, Aerochrome) are not imported.
- P9-O8: closed 2026-11-03: the product resources hold the reversal films (section 10).

## 9. User review

2026-11-03: the user accepts the result ("可以了") and asks for the port to Alcedo Studio, in two issues: CUDA and OpenCL first ([Alcedo Studio issue 654](https://github.com/zidage/AlcedoStudio/issues/654), phase F8), then Metal ([issue 655](https://github.com/zidage/AlcedoStudio/issues/655), phase F9). The lab work of this step is in commit `2c41e2d`, and the resources and the expected values of the port are in section 10. The five films, the light table, and the dark surround stay as in this report.

## 10. Resources of the port

For [Alcedo Studio issue 654](https://github.com/zidage/AlcedoStudio/issues/654). Scripts of step P7, changed in lab commit `851cf59`; record: [`product_resources.json`](../../results/p7_spectral_acceleration/product_resources.json). The run used that commit with a clean tree, and the manifest names it.

- Schema version 6. `film_stock_bundle.bin` (3075120 bytes) has the group `reversal/<film>/` in the form of `negative/<film>/`, with the record of rule `removed_dye_record` and `dye_max`, and the group `light_table/` with the D50 viewing weights, the XYZ scale, the exponent of the dark surround, and the luminance weights of linear Rec. 709. `film_print_setup.bin` (185776 bytes) has `reversal_layer_gain` (5 films, 11 scene lights), `reversal_xyz_to_display` (5 films), and `reversal_scene_spectrum_index`. The header names the films in the list order of the viewer.
- The product builds the light table (65³ over the record, cube root of XYZ) from these values. The lab ships no light table, as it ships no print table (ROADMAP U68).
- The compact reflectance table does not change in form: the sensitivities of the five films lie inside the wavelengths of the negatives (360 nm, 346 wavelengths, 18103 nodes). Its SHA-256 changes, because the header holds the schema version.
- Checks, with the limits of step P7: the setup of 6 reversal selections against the complete `ReversalPreview`, largest difference 0 (limit 1e-9); the compact u'v' table, largest relative difference 1.11e-4 (limit 2e-4); the final sRGB with the compact table, on 4 selections, largest 0.0031 of an 8 bit code (limit 0.5). The checks of the negatives are the same as in the record of `d47255a`, except Cine Look on 5219, which has rule `negative_show_grade` with the blurred record of U85 (`4c1135f`) since that record: random colours 0.160 of a code against 0.017 before. The product has U85.
- Expected values under `build/tmp/p7/product_resources/expected/` (not committed): the u'v' tables and the light table of Velvia 50 under `reference`, E100 under `daylight`, and Provia 100F under `street_mixed` (`reversal__<film>__<light>.bin`); the ramp and chart sRGB of the five films under `reference` and of the two other selections (`display/`); the sRGB of the five films on `_DSC8148.ARW` at 6000 × 4006 pixels (`image/`). Time: 231 s for the resources, 2 min for the full-size images, on the CPU only.
