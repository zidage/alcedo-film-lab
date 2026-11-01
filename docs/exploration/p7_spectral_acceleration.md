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
| `film_reflectance_table.bin` | `reflectance_over_uv_light`, 192^2 x 481 float32 | 70.9 MB |

The product has fixed hidden controls, so these scalar values are constants. Rule `setup_without_tables` calculates them with the methods of `FilmPreview` with no table build, so all selections take about 2 minutes. The script builds the complete `FilmPreview` for 11 selections and compares: the largest difference is 2.2e-16, against a limit of 1e-9. A value that the bundle holds once must be identical in each selection that uses it, or the script stops.

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
