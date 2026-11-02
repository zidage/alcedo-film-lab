# P7: Spectral acceleration

Date: 2026-10-31. Decision: [ROADMAP U68](../../ROADMAP.md). Scripts: [`scripts/poc/p7_spectral_acceleration/`](../../scripts/poc/p7_spectral_acceleration/). Results: [`checks.json`](../../results/p7_spectral_acceleration/checks.json).

## 1. Question

Can staged tables reproduce the direct evaluator, and can the table construction run from one code base in the Python viewer and in the product?

## 2. Result summary

- **One C++ library builds the tables.** `film_tables.hpp` has no dependency on Python or Qt. The Python viewer calls it through nanobind. The CMake target `film_tables` is a static library for the product. It is not yet linked into Alcedo Studio.
- **The print table has three stages (rule `staged_print_table`).** A new value of a print control now takes 0.016 s for the table and 0.30 s for the model. Before this step it took about 5.7 s and about 8 s.
- **No print table or APD table goes to disk (U68).** The table directory went from 845 MB to 203 MB. The spectral stages stay in memory for the life of the process.
- **The error is small on photos.** On 7 photos, 10 stock pairs, and 28 control cases: p99.9 at most 0.23 of an 8 bit code value, largest 1.22. On a neutral ramp: largest 0.25. All 125 checks pass. On all table nodes the largest error is 6.4 code values, on colours that no test photo reached.
- **Table construction was already multithreaded, and it stays so.** The longest stage reaches 17.3 CPU seconds per second of wall time on 20 hardware threads.
- **Image-plane rules for speed (U70).** Two inhibition steps, a half-size blur from a sigma of 4 pixels, and a spread in two passes. 24 of 30 negatives stay inside the limits against P6; 6 with strong inhibition do not (section 5.3).
- **Stock repair (U71).** 13 stocks whose grey fell onto the toe now take rule `grey_anchor` (section 5.4).
- **User review (U72, 2026-11-01).** The user accepts the final rules and the stock repair.

## 3. Inputs

The profiles and reflectance tables of P0 to P6. Photos, as AP1 arrays under `build/tmp/`: `se188`, `se228`, `leica_m11`, `nikon_zf`, `_DSC4063`, `_DSC8148` (night), `digital_ap1`. They go through the product grade of the MVP defaults.

Machine: Intel Core i7-12700H (20 hardware threads), 31.8 GB. CPU only, no GPU job. Compiler: MSVC 2022, Release, with no fast-math option and no architecture option.

## 4. Method

### 4.1 Observations before the change

These values come from a local probe on commit `3ee8b60`. The probe is not in this repository.

| Observation | Value |
| --- | --- |
| Print table in numba, 65^3 nodes | 5.6 to 6.0 s |
| Same algorithm in C++ (MinGW g++ -O3), same result (relative XYZ difference below 1e-14) | 1.44 s |
| Model build with stored tables | 2.3 s, of which 1.96 s in `SpectralGrid.weights` |
| APD table in NumPy, from 1/64 of the nodes | estimate 66 s |

So a language change alone gives a factor of 4 on the print table. The stages give the rest.

### 4.2 Calculations that were removed

- **Negative dye solve.** With rule `dye_amount_curves`, the record is the dye amounts. The old table converted the record to Status M and solved back. Check "Record is the amounts" shows a largest difference of 1.8e-15 on 10 stock pairs. A stock with a Status M record keeps the solve.
- **Dense integration matrix.** A fine sample has one or two working nodes, so `SpectralGrid.weights` now uses the nonzero values. The largest relative difference is 4.4e-16.
- **Repeated file read.** The reflectance table is read once per process. It has no dependence on a stock.

### 4.3 Rule `staged_print_table`

| Stage | Calculation | Depends on | Time |
| --- | --- | --- | --- |
| A | Negative record to log10 of the unbalanced paper exposure | Negative, printer lamp, paper sensitivity | 0.09 s |
| B | Paper Status A to print XYZ, by the dye solve of the paper | Paper, viewing light | 0.63 s |
| C | Printer lights, print contrast, flash, paper curves, trilinear read of stage B, surface reflection | Print controls | 0.016 s |

Stage C makes the same 65^3 table as before, so the per-pixel kernels do not change. Stages A and B are kept in memory by a hash of their input values, so a kept stage cannot be out of date.

Stage B has 65 nodes per axis, the same number as before. Node k of an axis has the density `start + range * (k / 64) ^ 2`. A uniform axis failed the limits on the first run: 17 of 125 checks failed, and the largest neutral ramp error was 2.11 code values, near +5 stops, where the dye amounts reach zero. The sweep below chose the power 2.

| Axis | Model build with empty stage memory | Worst of the 6 sweep cases: neutral ramp, largest | Photos p99.9 | Photos largest |
| --- | --- | --- | --- | --- |
| 65 nodes, uniform | 1.20 s | 2.11 | 3.20 | 3.74 |
| 97 nodes, uniform | 2.63 s | 1.87 | 2.22 | 2.56 |
| 129 nodes, uniform | 5.47 s | 1.62 | 1.74 | 2.01 |
| 65 nodes, power 1.5 | 1.16 s | 0.50 | 0.76 | 1.50 |
| **65 nodes, power 2** | **1.27 s** | **0.25** | **0.32** | **1.18** |
| 65 nodes, power 3 | 1.20 s | 0.09 | 0.27 | 1.27 |
| 97 nodes, power 2 | 2.80 s | 0.11 | 0.19 | 0.71 |

Source: `sweep_paper_axis.py`. Power 3 has a lower ramp error in this sweep. The choice of power 2 is a judgment: it has more nodes than power 3 at a high density, and both are inside the limits. The sweep used the same photos as the checks, so the photos did not test this choice independently.

## 5. Checks

Script: `check_film_tables.py`. Results: [`checks.json`](../../results/p7_spectral_acceleration/checks.json). The limits were written before the first run of the script and were not changed after the failures of the first run. They were written after the probe of section 4.1 had shown the size of the error on two photos. The reference is the dye solve per node of `FilmPreview._print_nodes`.

| Check | Value | Limit |
| --- | --- | --- |
| Weights, largest relative difference | 4.4e-16 | 1e-12 |
| Band response, largest log10 difference | 8.9e-16 | 1e-11 |
| Record is the amounts, largest difference | 1.8e-15 | 1e-9 |
| Status M record, largest difference | 1.5e-11 | 1e-9 |
| Paper stage, largest relative XYZ difference | 1.9e-11 | 1e-9 |
| APD table, largest density difference | 1.8e-15 | 1e-9 |
| 10 stock pairs on 7 photos, 8 bit code, p99.9 | 0.23 | 1.0 |
| The same, largest | 0.97 | 4.0 |
| The same, neutral ramp, largest | 0.06 | 0.5 |
| 7 print table controls at both ends, 2 stocks, 2 photos, p99.9 | 0.19 | 1.0 |
| The same, largest | 1.22 | 4.0 |
| The same, neutral ramp, largest | 0.25 | 0.5 |
| Table at mask density 0, largest difference of the cube root | 2.4e-7 | 1e-6 |
| New files in the table directory | 0 | 0 |
| Print table with empty stage memory | 0.65 s | 2 s |
| Print table for a new control value | 0.016 s | 0.05 s |
| APD table | 0.053 s | 1 s |

Error on all 274625 table nodes, with no limit: p99 at most 0.83, largest 6.38 code values (control cases). Most nodes are colours that no photo reaches.

Model times of the same run: 0.88 s with empty stage memory, 0.30 s for a new control value, 0.44 s for a scan model of a new negative.

### 5.1 Multithreading

Source: `measure_table_threads.py`, in a run before the reflectance table was kept in memory.

| Stage | Wall time | CPU time | CPU / wall |
| --- | --- | --- | --- |
| A | 0.093 s | 1.30 s | 13.9 |
| B | 0.625 s | 10.78 s | 17.3 |
| C | 0.017 s | 0.078 s | 4.6 |
| Model build, stages kept | 0.449 s | 0.125 s | 0.3 |

Stages A and B use nearly all threads. The model build waited mostly for the file read, so the file read was removed (section 4.2). Stage C is short, and each call starts its threads again, so it does not use all of them.

### 5.2 Checks of the earlier steps

The checks of the earlier steps ran on the final rules, with the following differences, except `run_p0_checks.py`, which ran before the rules for speed and does not use them. Their output files were restored after the comparison, so the reports of those steps keep their numbers. The timing values of these runs are not evidence, because several ran side by side.

| Check | Result |
| --- | --- |
| `run_p0_checks.py` | The same 3 failed checks as the committed results |
| `check_fast_kernels.py`, `check_scan_path.py`, `check_film_response.py` | The pass values do not change |
| `check_stock_chain.py` | One new failure, from `inhibition_two_steps`: `image_against_point` on Ektar 100, 0.0059 dye amount against the limit 0.002. The check expects the steps on an image to converge to the steps of a point. |
| `check_shadow_mode.py` | The same failures as the committed results: `table_interpolation` on 6 stocks, `plus_3_stops_change` on Gold 200 |
| `check_p6_mvp.py` | 0 failures, on `_DSC8148.ARW`; the committed run used `P2625273.RW2` |
| `check_p6_controls.py` | 0 failures, on the committed input. On `digital_ap1.npy`, a file with no strong highlight, 5 cases of "no effect" for halation length and gamut compression; this is a property of that input |

The command line and the window each rendered `_DSC8148.ARW` after the stored tables were deleted.

### 5.3 Rules for speed on images (U70)

The user sets speed before numeric accuracy. The final rules:

- `spread_per_layer_pass`: two passes, each with one Gaussian per layer, in place of six blurs. The largest difference on 2 RAW files and 3 stocks is 0, so this rule has no cost in accuracy.
- `inhibition_two_steps`: two fixed-point steps in place of 4.
- `inhibitor_on_half_size`: a half-size blur when the sigma is at least 4 pixels. At 2048 pixels (sigma about 2) it stays at full size.

Script: `sweep_inhibition_steps.py`, results [`inhibition_steps.json`](../../results/p7_spectral_acceleration/inhibition_steps.json): all 30 negatives on their default print, against 4 full-size steps, on one array at 2048 pixels and `_DSC8148.ARW` at 6000 pixels. The limits are mean 0.5, p99.9 2.0, largest 5.0. The case `2048, 2 half` of this file is from before the 4 pixel rule, so the final form at 2048 pixels is `2048, 2 full`.

| Case | 2048 pixels: inside the limits | Worst mean, p99.9, largest | 6000 pixels: inside the limits | Worst mean, p99.9, largest |
| --- | --- | --- | --- | --- |
| 1 step, half-size | 6 of 30 | 9.17, 51.6, 57.6 | 20 of 30 | 13.16, 33.2, 47.5 |
| 2 steps, half-size | 8 of 30 | 2.73, 20.8, 39.1 | **24 of 30** | **3.11, 9.9, 14.3** |
| 1 step, full size | 21 of 30 | 8.99, 51.3, 52.2 | 20 of 30 | 13.16, 33.2, 47.4 |
| 2 steps, full size | **24 of 30** | **2.31, 11.1, 12.7** | 24 of 30 | 3.11, 9.9, 14.3 |

**6 negatives are outside the limits with the final rules, and they stay failed:** `kodak_5277`, `fuji_eterna_500`, `fuji_eterna_500_vivid`, `kodak_5203`, `kodak_aerocolor`, and `kodak_ektar_100`. These have strong inhibition. Ektar 100 is an accepted stock: at 6000 pixels 0.76 mean, 2.04 p99.9, 2.87 largest. The 4 steps of P6 are themselves not a converged value for the strongest stocks, for example `kodak_5277`. The first conclusion of this step, one step, came from 5207 and Portra 400 only, and the sweep over all stocks replaced it.

`check_fast_image_steps.py` ([`image_steps.json`](../../results/p7_spectral_acceleration/image_steps.json)), on `_DSC8148.ARW` (6000 pixels) and `se188.nef` (4310 pixels):

| Check | 5207 on 2383 | Portra 400 on Endura | Ektar 100 on Endura | Limit |
| --- | --- | --- | --- | --- |
| Spread in two passes against six blurs, largest | 0 | 0 | 0 | 0.5 |
| Final rules against 4 full-size steps, mean | 0.002 | 0.028 | **0.760 (fail)** | 0.5 |
| The same, p99.9 | 0.020 | 0.164 | **2.04 (fail)** | 2.0 |
| The same, largest | 0.041 | 0.481 | 2.83 | 5.0 |
| Flat neutral at -3, 0, +3 stops, largest | 0.004 | 0.019 | 0.031 | 0.1 |
| Neutral ramp with no image plane, largest | 0 | 0 | 0 | 0 |

Render time on the CPU, Portra 400 on Endura: 6.55 s to 2.98 s at 6000 pixels, 3.08 s to 1.62 s at 4310 pixels. The time on the GPU is not known.

A sweep (local, labeled crops under `build/tmp/p7/blur_sweep/`) also tried one Gaussian per layer for the spread. It differs by up to 83 code values at lamp edges and makes the edges harder, so the rule keeps the two Gaussians. Light spread off differs by a mean of about 3.8 at 6000 pixels and by 0.00 at about 2000 pixels, so this effect is a property of the full-size image.

### 5.4 Stock repair (U71)

The user reports faults on the Fuji stocks other than C200. In `mvp_pipeline.light_conditions`, C200 had rule `grey_anchor` by name. A grey of the balance light, through the layer exposure of the pipeline, against its exposure on the curve (stops per layer; largest R-G code difference on a neutral at -2, 0, +2 stops, before and after):

| Stock | Stops | R-G before | R-G after |
| --- | --- | --- | --- |
| Portra 400 (accepted, no change) | +0.28, +0.41, +0.06 | 4.3 | 4.3 |
| Fuji Eterna 500 | -3.56, -2.54, -2.18 | 47.5 | 8.3 |
| Fuji Eterna 500 Vivid | -3.56, -2.56, -2.06 | 54.1 | 8.5 |
| Fuji Pro 160C | -4.25, -3.87, -3.66 | 25.3 | 7.9 |
| Fuji Pro 160S | -3.72, -3.53, -3.66 | 15.9 | 9.7 |
| Fuji Pro 400H | -3.74, -2.79, -2.58 | 27.2 | 12.1 |
| Kodak Vericolor III | -4.27, -3.29, -2.98 | 33.9 | 2.5 |

Rule `grey_off_the_curve` of `fit_stock_physics.py`, with the limit set before its first run: more than 1 stop on any layer. The largest value of an accepted stock is 0.84. The stock then takes rule `grey_anchor`. The rule changes 13 stocks: Fuji Eterna 500, Eterna 500 Vivid, Natura 1600, Pro 160C, Pro 160S, Pro 400H, Superia X-Tra 400; Kodak 5203, 5247 II, 5293, EXR 5248, Vericolor III; Agfa Vista 100. No profile changes; only `stock_physics.json` does. The inference is that these charts have no usable level; the sources do not state this. This does not neutralize a stock: the gains act at the grey of the balance light, so a crossover of the stock stays. Labeled sheets before and after are local, under `build/tmp/p7/stock_repair/`. The user accepts the result (U72).

### 5.5 Resources for the product

`build_product_resources.py` makes the files that Alcedo Studio ships (phase F1 of its [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md)) and the lab values of its host tests. Results: [`product_resources.json`](../../results/p7_spectral_acceleration/product_resources.json). The files stay under `build/tmp/`, and they do not go into Git.

| File | Content | Size |
| --- | --- | --- |
| `film_stock_bundle.bin` | 30 negatives, 18 print materials, the scene spectra, and the common values | 2.7 MB |
| `film_print_setup.bin` | Printer balance of each of the 5940 selections, layer gain, printing gain, aim, display matrix | 167 KB |
| `film_reflectance_table.bin` | Compact form of the final reflectance table, with rule `foliage_spectra` of the P6 report (rule `compact_reflectance_table`) | 25.1 MB |

The product has fixed hidden controls, so these scalar values are constants. Rule `setup_without_tables` calculates them with the methods of `FilmPreview` with no table build, so all selections take about 2 minutes. The script builds the complete `FilmPreview` for 11 selections and compares: the largest difference is 1.8e-15, against a limit of 1e-9. A value that the bundle holds once must be identical in each selection that uses it, or the script stops.

Rule `compact_reflectance_table` (user decision of 2026-11-01): the complete table of 70.9 MB took 38.7 MB after xz, because the low mantissa bits of a float32 have almost no repeated patterns. The file now holds 346 of 481 wavelengths (360 to 705 nm, where a weight of a negative is not zero), only the u'v' nodes that a read can reach after rule `spectral_locus_projection`, and 12 mantissa bits. Each byte of a float32 is in its own plane. The steps, on this table alone, with xz:

| Form | After xz | Largest relative u'v' difference |
| --- | --- | --- |
| Complete | 38.7 MB | 0 |
| Byte planes | 29.7 MB | 0 |
| Also only the used wavelengths | 18.8 MB | 0 |
| Also only the nodes that a read can reach | 14.2 MB | 0 on these nodes |
| Also 16 mantissa bits | 9.0 MB | 7.5e-6 |
| **Also 12 mantissa bits (shipped)** | **5.6 MB** | **1.1e-4** |
| Also 8 mantissa bits | 3.2 MB | 1.8e-3 |

The sizes of this table are from a probe with zeros at the removed nodes; the size of the shipped file is in the results.

Two other forms do not work on this table. Wavelength knots of 2, 5, or 10 nm with linear interpolation, and a linear 16 bit scale, give u'v' errors above 1, because the table holds values up to 2.8e8. The largest of these is at 364 nm, near the end of the range of the reference light. The cause is an inference, and this step did not check it.

Checks of the shipped form, with the limits written before the first run: on 11 selections the largest relative u'v' difference is 1.2e-4 (limit 2e-4). The removed nodes hold NaN, and the layer exposure stays finite on 3 photos, a ramp, 512^2 random colours, and the edge of the hull. On 6 selections the final sRGB differs by at most 0.0054 of an 8 bit code (limit 0.5). A new stock with a weight outside the wavelength band needs a new file; the product stops with an error that names the stock.

### 5.6 Rule `inhibition_image_part` (U74)

**Fault.** `fit_mtf.py`, `fit_mtf_stocks.py`, and `fit_stock_physics.py` fit the spread `s`, the inhibitor length `sigma_d`, and the boost `B`, and discard `sigma_d`. The render uses `inhibition_um` = 35 um. With a chart that has no rise above 1, these three values have no single solution, and the fit stops at `B` = 2 with `sigma_d` under 7 um. At 35 um the same `B` gives an edge effect that the chart does not have.

**Rule.** `fit_inhibition_image.py` fits `s` and `B` with `sigma_d` fixed at 35 um. The K of the old fit stays as the total, and `F_i` stays on this total, so a flat area keeps its colour. The image part is `K_image = min((B - 1) (1 - K gamma) / gamma, K)`, because `F_i` has the slope `gamma / (1 - K gamma)`. `B` at its upper bound is an error.

**Form for the GPU.** The point part must add no image and no blur. One point step gives `a1 = F(log H - K a)` in the pass of the first amounts, and the later steps read the exposure `H 10^(-K_point a1)`. So there is no image of the amounts between the steps. A negative with no image part runs no blur, and takes `F(log H - K a1)`, as two point steps do. `check_fast_image_steps.py` and `sweep_inhibition_steps.py` of 5.3 replace this method and measure the form of U70.

**Checks (`check_inhibition_image.py`). Limits set before the first run.** Results: [`inhibition_image.json`](../../results/p7_spectral_acceleration/inhibition_image.json). The first run had one failure, `kodak_5206` at 1.11 against a chart of 0.96: the formula then was `(B - 1) / (B gamma)`, with no term for the steeper `F_i` of the total. The table has the run after this correction.

| Check | Limit | Before | After |
| --- | --- | --- | --- |
| Largest response of a layer minus the chart peak, 3 to 40 cycles/mm, 29 negatives | 0.10 | 1.12 (`kodak_5277`, red) | 0.09 (`kodak_5206`, green) |
| `fuji_eterna_500`, overshoot and undershoot at a step edge of 3 stops | 1 code | 14.6, 13.0 | 0.02, 0.00 |
| `fuji_eterna_500` on `_DSC8148`, mean chroma | 1 % | 54.39 | 54.42 |
| `kodak_5207` on `_DSC8148`, mean difference from before | 0.2 codes | | 0.017 |
| `kodak_portra_400` on `_DSC8148`, mean difference from before | 0.2 codes | | 0.033 |

Peak response of the layer with the largest change, before and after, against the chart: Eterna 500 green 1.64, 0.99 (1.00); Vivid green 1.70, 0.99 (1.00); `kodak_5203` blue 1.68, 1.00 (0.99); `kodak_5277` red 2.13, 0.97 (1.00); `kodak_5206` green 1.35, 1.05 (0.96). The mean difference of Eterna 500 from before on `_DSC8148` is 1.79 codes, mostly at edges and in fine detail; this difference is the purpose of the rule.

The rule rests on charts that spectral_film_lut digitized, not checked against the manufacturer documents. The review of the new look by the user is open.

### 5.7 Neutral axis of the projected prints (U75)

**Fault.** The user found 2383 yellow-green. On a neutral ramp of 5207 + 2383, the shadows were green (L* 20: a* -5.3, b* +1.5) and the highlights yellow-green (L* 85: a* -3.5, b* +9.3).

**Source observations.** KODAK H-61b: the LAD patch of 2383 is a visual neutral of density 1.0 at Status A 1.09, 1.06, 1.03, and a colour shift up and down the gray scale with a neutral mid-tone is a contrast mismatch. SMPTE 196M-2003: the projection light is 5400 K, +600 K, -200 K, with typical readings x = 0.332, y = 0.347.

**Trace.** Rule `neutral_printing_gain` raises the red and blue slopes, and this makes the green shadows. Display white `reflector` keeps the colour of the densest print node, and this adds about b* +6 along the ramp. The LAD aim is not a cause: equal Status A is near neutral under D65 with these dyes (a* +0.1, b* +0.3).

**Rule.** The user compared three versions on four photos and selected the print with no gain and with the white of the densest print node ("no gain" in the local sheet `build/tmp/print_cast_2383/sheet.jpg`). Projected prints now have no rule `neutral_printing_gain`. New rule `projected_print_white`: each projected print material has one chromaticity that goes to D65, and the level stays on the perfect reflector. `fit_display_white.py` takes it from the densest node of the 5207 print table on that material. This is an empirical choice, not a measurement. It is not the D-min of the print (2383: x = 0.3208, y = 0.3411 against x = 0.3275, y = 0.3532), and a print curve alone does not reach this value. With one value per material, a negative keeps its difference from the other negatives, and a scene light does not move the white. Reflection papers do not change.

**Checks.** The rule against the selected look on `_DSC8148`, 5207 + 2383: largest difference 0.0003 of an 8 bit code. `check_neutral_axis.py` compares the neutral axis with a Resolve LUT at the same L*, with no limit, because a LUT is an emulation with a neutral Cineon input and not a measurement. Results: [`neutral_axis.json`](../../results/p7_spectral_acceleration/neutral_axis.json). Mean and largest a*b* distance:

| Selection | Resolve LUT | Before | After |
| --- | --- | --- | --- |
| 5207 + 2383 | 2383 D65 | 6.8, 8.9 | 2.1, 3.6 |
| 5219 + 2383 | 2383 D65 | 7.3, 10.7 | 4.4, 8.2 |
| 5213 + 2383 | 2383 D65 | 5.1, 8.0 | 3.3, 5.7 |
| 5203 + 2383 | 2383 D65 | 4.8, 7.5 | 3.2, 5.2 |
| Eterna 500 + 2383 | 2383 D65 | 5.1, 8.3 | 3.4, 4.4 |
| Portra 400 + 2383 | 2383 D65 | 5.2, 7.9 | 4.3, 6.5 |
| Gold 200 + 2383 | 2383 D65 | 6.1, 8.7 | 3.3, 4.5 |
| C200 + 2383 | 2383 D65 | 5.8, 9.6 | 4.0, 4.9 |

Not measured: a real print, and a review by the user of any selection other than 5207 + 2383. Other projected materials have no "before" value; the "after" values are in the results file.

### 5.8 UV filter of the printer (U77)

**Fault.** The user finds 2383 strange on daylight photos (Alcedo Studio issue 645). After 5.7, a neutral ramp of 5207 + 2383 still had blue shadows and yellow-green highlights.

**Source observation.** The data sheet of 2383: "Overall filtration should include a UV-absorbing filter, such as a KODAK WRATTEN Filter No. 2B." The sheet of 2393 has the same statement. Kennel and others, SMPTE Journal, October 1982, page 926, define the exposure density of a negative onto a print film with "printer illuminant + UV filter (2B)". The printer model had lamp A with no filter (P0 option `printer_lamp`).

**Trace (local scripts `build/tmp/issue_645/`).** The chart of the blue layer of 2383 goes down to 361 nm, and at 380 nm its sensitivity is about 18 % of its peak. The yellow dye of 5207 at 380 nm is 0.24 of its peak. So part of the exposure does not follow the image. Share of the blue layer exposure below 400 nm through a 5207 grey, and the blue slope against green, printing slope times paper slope:

| Print material | Share, no filter | Share, 2B | B/G, no filter | B/G, 2B |
| --- | --- | --- | --- | --- |
| `kodak_2383` | 0.247 | 0.008 | 0.756 | 0.878 |
| `kodak_2393` | 0.232 | 0.007 | 0.789 | 0.917 |
| `kodak_5383` | 0.681 | 0.103 | 0.599 | 0.781 |
| `kodak_5381` | 0.681 | 0.103 | 0.724 | 0.942 |
| `kodak_5384` | 0.316 | 0.016 | 0.824 | 0.874 |
| `fuji_3513di` | 0.233 | 0.005 | 0.729 | 0.780 |
| `kodak_endura_premier` | 0.033 | 0.005 | 0.913 | 0.924 |

This is the low blue slope of P2 report section 8.4, which that report could not explain. Rule `neutral_printing_gain` corrected its effect, and U75 removed that rule. Other printer lights do not change the result much: additive bands of 420 to 490 nm, 510 to 580 nm, and 600 to 720 nm give 0.836 against the 0.847 of lamp A with a sharp cut at 420 nm.

**Rule `printer_uv_filter`.** The printer light of a cine print passes the Wratten 2B density curve, from the digitization of spectral_film_lut (`import_printer_filters.py`). Reflection papers do not change. `fit_display_white.py` runs again: the white of 2383 moves from x = 0.3275, y = 0.3532 to x = 0.3226, y = 0.3456, near its D-min (x = 0.3208, y = 0.3411).

**Checks.** Neutral ramp, range of a* and b* for L* 15 to 88: 5207 + 2383, a* 6.3 to 4.3, b* 13.7 to 5.5; 5219 + 2383, a* 8.3 to 3.1, b* 22.2 to 6.4; 5207 + 3513DI, a* 8.4 to 6.6, b* 15.8 to 12.1; 5207 + 5383, a* 13.1 to 12.2, b* 22.6 to 9.5. `check_neutral_axis.py`, 5207 + 2383, against the Resolve LUT: mean 2.1 to 2.0, largest 3.6 to 4.8. The fix has no aim to match this LUT. The other selections are in the results file.

**Limits.** The numbers of this section are for the rule alone, with the conditions of 5.7. Section 5.9 changes those conditions. No real print was measured. The blue slope of 2383 stays about 12 % below green. The density of a negative dye below 400 nm is a Gaussian tail. `kodak_5381` and `kodak_5383` have about 10 % of the exposure below 400 nm, and on 5383 the range of a* stays large. The user has not reviewed the new look on the RAW files of the issue.

### 5.9 Print conditions from their sources (U78)

**User request.** Remove the values that came from a comparison with spektrafilm, and build the print from its process. Section 5.2 of the P6 report and section 8.5 of the P2 report list these values.

| Item | Before | Now | Source |
| --- | --- | --- | --- |
| `CINE_GREY_STATUS_A` | 0.85, by comparison with spektrafilm | 1.09, 1.06, 1.03 | LAD patch, KODAK H-61b |
| `print_contrast` | 0.85, by a sweep | 1 | The published curve |
| `print_flash` | 0.02, by eye | 0 | No measured value |
| `viewing_flare` | 0.003, by eye | 0 | No measured value |
| Cine viewing light | D65 | D54, rule `projection_light` | SMPTE 196M-2003. D54 as a xenon lamp is an inference |
| Cine display white | `projected_print_white`, fitted | `print_dmin`, rule `clear_print_white`: the lowest Status A density of each paper curve, under the viewing light, goes to display white | In a dark cinema the clear print is the brightest light. This is an inference, with one test below |
| Surround of a cine print | None | Rule `dark_surround_on_display`: luminance relative to the clear print takes the exponent 0.525 / 0.59 | CIECAM02 surround values c, dark and dim |

Papers keep D50, the perfect reflector, and Status A 0.75, which is 18 % reflectance. `fit_display_white.py` and `display_white.json` are removed.

**Results, 5207 + 2383.** A grey of 0.18 has L* 44.9 (46.2 before). Range for L* 15 to 88: a* 4.9, b* 7.2 (6.3, 13.7 before). Black L* 1.0, top L* 99.0 (3.7, 92.9 before). Script: `build/tmp/issue_645/d7_first_principles.py`, local. `check_neutral_axis.py`, against the Resolve LUT, mean 2.2, largest 4.9; this has no limit, and the LUT took no part in any value. The same LUT has L* 40.1 at Cineon 445.

**Tests that the values give.** The LAD patch on this chain has L* 44.5, a* +0.7, b* -6.0. H-61b states a visual neutral, so the digitized dyes or the choice of the clear print as white has an error of this size. The test does not separate them.

**Not independent, and stays.** Rule `development_inhibition` is an empirical model that agrees with DIR couplers in quality only: an inhibitor from the image, and a spread. It keeps the algorithm of spektrafilm. Its form (a shift of log exposure that is linear in dye amount), its K from a fit to modulation transfer charts, its share between layers, and its point part have no source in process data. KODAK H-24 modules 1, 7, 8, 9, and 10 do not mention inhibitors or interimage effects, and their chemical charts are trend charts for 5213, 5254, and 5242. The Enlarger flare default, the Halation strength, rule `grey_anchor`, and the band split also have no source, and a stock chart gives no value for them.

**Not measured.** A real print, and the review by the user. Chroma rises with the published curve, and the grade of the product stays in front of the film.

### 5.10 Separation curves against rule `development_inhibition`

**Question.** Does the rule give the form of a real colour negative? Reference: Sehlin and others, SMPTE Journal, July 1985, Figure 14 (5294) and its text. There, the green separation curve overlaps the neutral curve up to about 0.8 density above base, and at 1.71 above base it is about 0.27 higher. The paper calls this over-corrected, and it states that 5247 and 5294 are generally over-corrected. This is another stock, so the limits test the form. They are in the header of `check_separation_curves.py`, and were set before the first run.

**Result: the rule fails.** 38 of the 40 limits fail on 8 negatives with Wratten 99. The two that pass are the overlap of Portra 400 and of Ektar 100. Results: [`separation_curves.json`](../../results/p7_spectral_acceleration/separation_curves.json). Separation minus neutral at 1.7 above base, or at the top of the curve:

| Negative | Difference |
| --- | --- |
| `kodak_5207` | -0.176 |
| `kodak_5219` | -0.192 |
| `kodak_5213` | -0.140 |
| `kodak_5203` | -0.166 |
| `fuji_eterna_500` | -0.106 (about +0.24 near 1.2, then a fall at the end of the curve) |
| `kodak_portra_400` | -0.062 |
| `kodak_gold_200` | -0.096 |
| `kodak_ektar_100` | -0.105 |

**Split on 5207, at 1.3 above base (local script `build/tmp/issue_645/sep/decompose.py`).** With K = 0 the dye amounts are equal, as they must be, and the difference is -0.188. This part is the side absorption of the dyes in Status M. The model K adds +0.014. So the inhibition of 5207 is too small to show in this measure. To bring the difference above zero, K needs about 6 times its value with all of it between layers; then the blue amount falls to 0.009 on the separation, the difference is present from low density, and at 1.7 above base it is still -0.049. So this form did not reach the shape of the reference in the sweep. The overlap and then a late rise did not appear at any value.

**Eterna 500.** Its K is much larger than that of 5207: the green row is 0.596 against 0.079. Section 5.6 states that its fit stops at a bound with a length under 7 um. So the size of K follows the fit, and a large difference between these stocks has no support from process data. At 2 times K with all of it between layers, F_i does not exist.

**Limits of this result.** The reference is 5294, read by eye. No chart for 5207 or for the other tested stocks was found, so a stock may differ. The side absorption depends on the reading of the digitized dye curves as net of the mask (P4 report, section 9.3). The check cannot separate that error from a too small K: in the real film the two can cancel at low density. Nothing in the model changes from this check.

### 5.11 Other ways to the colour of a 2383 print (U79)

**Status:** local probes in `build/tmp/issue_645/` (2026-11-02). No rule of the model changes. Photographs and sheets are local only.

**K fitted to a form: rejected by the user.** A rule with K between layers, a gain from the exposure of the receiving layer, and an extension of F_i was fitted to Figure 14 of Sehlin and others. It had 17 of 40 limits failing, against 38 of 40 here. The user does not accept a forced fit, so it was removed and was not committed.

**K from the matrix `CDD_TO_CID` of ADX: rejected by the user.** ACES developers state that Kodak and Fuji supplied this matrix as an average for all films. Under the form of this lab, K_ij = (M S)_ij / gamma_i for i and j different, with no search. M is the matrix, S is d APD / d amount, and gamma is the neutral slope. On `kodak_5207` this K is 0.07 to 0.51, against 0.02 to 0.05 now.

| Check | K now | K from the matrix |
| --- | --- | --- |
| Overlap of separation and neutral up to 0.6 above base, 7 stocks | Fails on most | Passes on all, and it was not a target |
| Other limits of section 5.10 | Fail | Fail: -0.1 at 1.7 above base |
| Real 5207 pair `f15`, RMS of R - G and B - G, density | 0.041, 0.035 | 0.074, 0.069 |
| 34 real frames (real variance off the axis 0.034), 17 digital files; no paired scene | 0.034 | 0.079 |
| Grey of the reference light on 5207 + 2383, b\* at L\* 45 | -2.5 | -12.9 |

The real scan has hypotheses: gamma 2, and X5 channels as APD. The user reviewed the sheets and finds the look not acceptable.

**Printing bands: no change is necessary.** With rule `printer_uv_filter`, the bands of the model and the responsivities of ST 2065-2 are near: the 5 % and 95 % points of red and blue differ by at most 3 nm. Green differs at its short end: 491 nm against 510 nm at the 5 % point. Two probes, each with its own printer balance: the bands of APD, and the green band cut below 500 nm. On 9 test colours a\* and b\* change by at most 2, and on the neutral ramp by at most 0.9. The author sees no change on 8 real frames and 4 digital files. No public data for the bands of a real additive printer was found.

**A direct scan path in the form of NegPy: of interest, not built.** The probe is written again from NegPy at `3928f81` (GPL-3.0), so it is not the output of NegPy. Log T per channel, a stretch of each channel between its 1 % and 99 % points, the print curve of NegPy, and no cast removal (U36). By the view of the author, colour is cleaner and cooler on real and simulated negatives, and the warm cast of the print goes away. The bounds of each frame remove the key of a dusk frame, and a statistic of the frame has a cost in the product. The user prefers bounds that are calculated from the known data of the stock. No such rule exists yet. This path would reverse a part of U64.

### 5.12 Saturation of the default look (U80)

The user finds the saturation too high on Eterna 500, Ektar 100, and Portra 800, and finds pink highlights on Ektar 100. All values in this section are from 12 files in `sample_images/raw` of the product, through the lab pipeline with its default settings. C\* is CIELAB of the final sRGB, at p95 of all pixels. The user reviews the look; the review is pending.

| Print | Stock | C\* p95 before | C\* p95 after |
| --- | --- | --- | --- |
| 2383 | 5207 | 47.1 | 39.1 |
| 2383 | Portra 800 | 53.2 | 42.5 |
| 2383 | Ektar 100 | 53.7 | 43.5 |
| 2383 | Eterna 500 | 64.6 | 39.5 |
| Endura Premier | 5207 | 47.5 | 39.9 |
| Endura Premier | Portra 800 | 53.5 | 45.3 |
| Endura Premier | Ektar 100 | 53.8 | 46.2 |
| Endura Premier | Eterna 500 | 65.8 | 42.7 |

**Saturation 1.0 on the film print.** This replaces the 1.3 of U24 for this chain. The default of a product document stays 1.3, for the other methods. When the user turns on the film print, the product writes 1.0 to the saturation of the Default Grade, in the same undo step. A value that the user selected stays.

**K has only the part that the chart supports (rule `inhibition_total_from_image_part`).** K total came from the fits of P4. On Eterna 500 its 0.5 to 0.6 is the value of a fit at its bound, and the chart supports an image part of 0 at 35 um. Only the terms between layers change colour. On the photo of `check_inhibition_image.py` the mean of (largest - smallest channel) of Eterna 500 falls from 48.46 to 34.46. This is the intended result, so the 1 % limit of U74 on this value is removed and the value stays in the record. The edge of Eterna 500 stays at 0.019 and 0.003 codes. The charts stay within their limit.

**The share of K between layers is not the cause.** A 1D diffusion model (the layer order of Kennel 1982, figure 1, and the gelatin of US4830954) gives a share across layers of 0.44 to 0.55 at a length of 35 um and a thickness of 40 um. So 0.5 is a plausible value, and a different value in this range moves colour by a small amount. The length and the thickness are not measured; over the sweep the share is 0.01 to 0.66.

**Pink highlights: half of the match of the printing slopes (rule `print_slope_match`).** Pink comes from the ratio of the printing slopes of a pair: red and blue against green. On 2383, 5207 has 0.887 and 0.922, and a consumer negative about 1.1. A change to the film data would harm the pairs on Endura Premier, where the effect almost does not occur. So `printing_gain` of each pair with a cine print moves to the slopes of 5207 at strength 0.5, `CINE_PRINT_SLOPE_MATCH`. The strength is a choice, not a measurement. No rule of the process gives it. The gain of a paper is 1.

| Stock on 2383 | Gain R, G, B | a\*, b\* at L\* 75 | a\*, b\* at L\* 85 |
| --- | --- | --- | --- |
| Portra 800 | 0.888, 1, 0.915 | +3.2, -0.6 | +0.7, -0.2 |
| Ektar 100 | 0.909, 1, 0.911 | +2.2, -0.7 | +1.0, -0.3 |
| Eterna 500 | 0.924, 1, 0.959 | +2.2, +0.6 | -0.9, -0.5 |

**Entry gamut compression (rule `entry_reference_gamut_compression`).** A grade can move a colour out of AP1, and the final colour space is not known at this point. So the entry has the same ACES Reference Gamut Compression as `DrtKernel`. On the 12 files the share of graded pixels with a negative AP1 value rounds to 0.0, and C\* p95 changes by at most 0.1. So this rule protects extreme colours. It does not control saturation.

**Not handled.** 5207 on Endura Premier leans green: a\* reaches -5.5 on the neutral ramp, by the same mechanism as pink. Ektar 100 and Portra 800 on Endura Premier stay 5 to 6 above 5207.

### 5.13 Rule `print_cinema_look` (U81)

**User request.** 5207 on 2383 at midday looks thin and strange (Alcedo Studio issue 645). The user asks for the look of La La Land, by any means, with research into grading practice, and with no argument from Lab analysis.

**Source observations.** [American Cinematographer](https://theasc.com/article/la-la-land-city-of-stars/): the midday exteriors used 5207 at EI 100, all footage had a pull of one stop, a Lustre DI followed the scan, a goal of the DI was blue in the blacks, and the LUT of the show had a white point near D65. [Mixing Light](https://mixinglight.com/color-grading-tutorials/what-makes-film-print-emulation-luts-special-and-how-do-you-use-them): on the 2383 LUT of Resolve, blues rotate toward cyan, skin gains richness, and shadows crush before a ramp and a roll-off. No source gives the LUT of the show.

**Observation by eye.** The simulated 5207 negative through the Rec. 709 2383 LUT of Resolve, as a local comparison only, is about as thin as the print of this lab. So the printer model alone does not explain the difference. The target is a finished grade, and the set and the costumes of the film are part of it.

**Candidates.** Two independent local studies (`build/tmp/look_codex/`, `build/tmp/look_claude/`) gave candidates on the same frames. The user selected candidate P6 of `look_codex` and asked not to merge candidates. The report of that study holds its other rounds.

**Rule.** `cinema_look.py`, on the sRGB code of the finished print: a separation and a coupling of the channels in a density of code, a curve that prints the lower mids down, blue in the blacks and warm lit surfaces, a lower chroma, more density on blue, and a small shift of blue and green. All constants are creative choices. `print_conditions` turns the rule on for `kodak_2383`. It is outside the print table, so the three sliders and the tables do not change.

**Checks.** `check_cinema_look.py`, with limits set before the run; results in [`cinema_look.json`](../../results/p7_spectral_acceleration/cinema_look.json). The rule against the array of candidate P6 on 8 frames: largest difference 3.0e-8 of code, limit 1e-5 (local script `build/tmp/look_claude/check_p6_port.py`).

**What is not solved.** The study states that pale blossoms can stay dry and grey-brown, that skin can lean orange, and that shaded plants can lose detail. A global step cannot give the shot-level grade of the film. The user reviewed 5207 on 2383 only. The other negatives on 2383 take the same step with no review. No matched RAW file of a film frame exists.

## 6. Not measured

- Continuity at the boundaries of table cells, which ROADMAP section 8 requires for this step.
- Coverage of the negative and print density ranges by photos.
- The other 21 negatives and 14 print materials have no comparison with the reference. `check_p6_mvp.py` shows only that their output is finite and in range.
- A link into Alcedo Studio. A build on macOS, or with a compiler other than MSVC in this form of the library.
- Full-resolution images. The table work has no dependence on the image size.
- The first build of the reflectance tables (about 5 minutes, P2 report). These stay on disk, because this step did not make them faster.

## 7. Recommendation

Keep this form. The stages of this table fit the product: the host builds stages A and B, and a new film, print material, or scene light sends one new table to the GPU. The three sliders of the product (U69) act on the image and build no table. The next step is the port to Alcedo Studio (U70).

## 8. Commands

See [the script README](../../scripts/poc/p7_spectral_acceleration/README.md).

## 9. Open items

| Item | Owner |
| --- | --- |
| Check continuity at the table cell boundaries, and the density coverage | Lab |
| The phases of the [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md) | Product port |
