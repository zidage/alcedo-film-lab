# P5: Other film and print combinations

**Design:** [ROADMAP section 8](../../ROADMAP.md#8-route-from-poc-to-mvp), step P5, with decisions U33 and U34.
**Date:** 2026-10-30.
**Status:** in progress. Five stocks have profiles, options, numeric checks, and labeled sheets. The user review of the stocks is not done. Sections 11 and 12 add the backlit work of U35 and U37. Section 26 adds a scan path with three stages (U54).

## 1. Question

Which popular color negative stocks can the model use on the accepted P4 print, and what do the sources specify for each one?

User scope (2026-10-30, U34): stocks in current production, for example C200, Ektar, Gold 200, and Portra 160, 400, and 800. Other stocks are set aside. This step keeps one print material, Endura Premier, so the sheets show the difference between stocks. Other print materials are set aside by the same decision.

## 2. Result summary

- **All five stocks run through the P4 chain.** All limits on the chain pass (section 6). Two source checks exceed their limits by small amounts, and section 4 states them.
- **Four Kodak stocks are digitized by this lab** from the vector charts of the current data sheets. Their values agree with spectral_film_lut (MIT) within the limits. Only the Gold 200 sensitivity comes from that project, because its chart is not one path per curve.
- **C200 is the weakest record.** All its values come from spectral_film_lut, because its charts are raster images. Its sensitivity has no absolute level, and its modulation transfer chart has one curve for all layers.
- **No stock has published isolated dye curves.** All five use the inferred band split, as Portra 400 does.
- **Gold 200 has no modulation transfer chart.** So it has no spread and no inhibition. The values of spectral_film_lut for this stock are an exact copy of its Portra 160 curves, and this lab does not use them. Its sheets have one labeled comparison panel with the Portra 160 values.
- **Production status of C200 is not confirmed.** See section 3.2.
- **The accepted Portra 400 does not change.** Its profile stays at edition 2-16, and the curves of edition 1-25 are near it (section 4).

## 3. Sources

### 3.1 What each stock has

Downloads, hashes, and terms: [`sources.json`](../../scripts/poc/p5_film_and_print_combinations/sources.json). The documents are not committed (U10).

| Stock | Document | Characteristic | Sensitivity | Neutral and D-min | Isolated dyes | Modulation transfer | Log H Ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Portra 160 | E-4051, Revised 1-25 | Lab, vector | Lab, vector | Lab, vector | Not published; band split, inferred | Lab, vector, 3 curves | -1.051 |
| Portra 400 | E-4050, Revised 2-16 (P0) | Lab, vector | Lab, vector | Lab, vector | Not published; band split, inferred | spectral_film_lut (P4) | -1.44 |
| Portra 800 | E-4040, Revised 1-25, EI 800 | Lab, vector | Lab, vector | Lab, vector | Not published; band split, inferred | Lab, vector, 3 curves | -1.74 |
| Ektar 100 | E-4046, Revised 1/25 | Lab, vector | Lab, vector | Lab, vector | Not published; band split, inferred | Lab, vector, 3 curves | -0.84 |
| Gold 200 | E-7022, Revised 06-23 | Lab, vector | spectral_film_lut, checked against the fragments of the chart | Lab, vector | Not published; band split, inferred | **Not published. No value used** | -1.14 |
| Fujicolor C200 | AF3-0249E (17.05-BX) | spectral_film_lut | spectral_film_lut; **relative**, criterion 1.0 above D-min | spectral_film_lut | Not published; band split, inferred | spectral_film_lut, **one curve** | **Not published.** -1.14 inferred, the value of Gold 200 |

Inferred for all stocks on this print: the band split, `inhibition_cross_share`, the length of the inhibitor, the frame width, the printer lamp, and the halation, as in P4. Endura stays the print of a Fuji stock too: no source states this pairing as a reference.

### 3.2 Production status

Source observations on 2026-10-30, not a statement from the manufacturers:

- Kodak Alaris publishes data sheets of 2023 and 2025 for the four Kodak stocks and for Portra 400.
- Fujifilm support pages still list FUJICOLOR C200 with the bulletin of 2017. Web sources disagree about the current product: some say that "Fujifilm 200" replaced it, and some that this film is made by another company. This lab did not resolve this.

So this profile describes the C200 of bulletin AF3-0249E. It may not describe a roll on sale now.

## 4. Source checks

Script: `digitize_stock_charts.py`. Results: [`source_checks.json`](../../results/p5_film_and_print_combinations/source_checks.json). Limits set before the first run.

Lab digitization against spectral_film_lut, largest RMS per chart:

| Stock | Characteristic (limit 0.03) | Sensitivity (limit 0.05) | Dye density (limit 0.03) | Modulation transfer (limit 0.05) |
| --- | --- | --- | --- | --- |
| Portra 160 | 0.0034 | 0.0104 | 0.0050 | 0.0101 |
| Portra 800 | 0.0024 | 0.0168 | 0.0062 | 0.0056 |
| Ektar 100 | 0.0045 | 0.0179 | 0.0030 | 0.0066 |
| Gold 200 | 0.0049 | Not digitized | 0.0053 | No chart |

These two digitizations are independent readings of one chart. Their agreement does not check the chart itself. It also gives the first check of the data of spectral_film_lut against the Kodak documents for these stocks.

**One limit fails: Gold 200 sensitivity against the fragments of the chart.** Limit 2 pt. Yellow layer 1.71 pt and magenta layer 1.06 pt pass. The cyan layer is 2.91 pt, at 478 nm, where its log sensitivity is about 0.006, more than two log10 units below its peak. The chart has a gap between the blue lobe and the main part of this layer, and spectral_film_lut joins them along the axis. A local probe located this. The value stays, and the effect on layer exposure is not measured.

Editions. The limit of 0.005 chart units, set before the first run, passes on all characteristic, dye density, and modulation transfer charts (largest 0.0015). It fails on three sensitivity charts:

| Comparison | Characteristic, largest | Sensitivity, largest | Dye density, largest |
| --- | --- | --- | --- |
| Portra 160, 1-25 against 2-16 | 0.0007 | 0.0041 | 0.0008 |
| Portra 800, 1-25 against 2-16 | 0.0009 | **0.0105** | 0.0008 |
| Ektar 100, 1/25 against 2/16 | 0.0004 | **0.0112** | 0.0015 |
| Portra 400, 1-25 against the profile of 2-16 | 0.0011 | **0.0079** | 0.0009 |

The bold values are above the limit and at most 0.0112 log10. The author reads this as a redraw of the chart and not a new emulsion. No Kodak note was found on this, so this is a hypothesis. The profile of Portra 400 stays at 2-16.

Rule `running_maximum_curve` removes a fall of 0.0313 density in the toe of the blue curve of Gold 200. It removes at most 0.002 on the other stocks.

C200 is a raster chart. A local overlay (`build/tmp/p5/scripts/c200_overlay.py`, calibrated by eye, no number from it) shows that the characteristic and dye density curves follow the chart. The sensitivity curves have the same shape with an arbitrary vertical offset, as a relative chart permits. The modulation transfer curve was not overlaid.

## 5. Model settings

- `STOCKS` and `P5_PHYSICAL` in `film_preview.py`. The rules are those of P4, and no new rule enters the film chain.
- **Rule `grey_anchor`, balance light D55, for the five new stocks.** A gain per layer puts an 18 % grey under D55 at the Log H Ref. Without it, the Kodak layers land up to 0.70 stops apart under D55, by the values of `layer_gain_log10` in `stock_chain.json`. Calculation, not a render: the blue layer of Gold 200 would be 0.6 stops over, so its negative would have more yellow dye and the print would lean blue. This is against the warm reputation of that stock, so the author reads the spread as a limit of the charts and not as a character of the stock. This is a hypothesis. C200 needs the rule because its chart has no absolute level.
- **Portra 400 keeps its accepted options** (no anchor, E_ref), by U32. The two forms differ, but the grey of the print stays near: a*, b* of 0.86, 0.03 on Portra 400, and 0.63, -0.07 and 0.64, 0.22 on Portra 160 and 800.

Spread and inhibition from the modulation transfer curves, by the form of P4. Script: `fit_mtf_stocks.py`. Results: [`mtf_fit.json`](../../results/p5_film_and_print_combinations/mtf_fit.json). Red, green, blue:

| Stock | Spread s, um | sigma_d, um | Boost B | Total K | Largest RMS residual |
| --- | --- | --- | --- | --- | --- |
| Portra 160 | 5.55, 2.98, 3.03 | 21.5, 31.2, 36.2 | 1.277, 1.241, 1.056 | 0.279, 0.265, 0.083 | 0.032 |
| Portra 800 | 5.21, 3.64, 2.51 | 60.0 (at the limit), 39.5, 34.9 | 1.107, 1.318, 1.111 | 0.130, 0.349, 0.120 | 0.017 |
| Ektar 100 | 6.51, 3.86, 3.13 | 25.1, 39.1, 60.0 (at the limit) | 1.563, 1.304, 1.085 | 0.499, 0.359, 0.138 | 0.039 |
| C200 | 3.24 for all (one curve) | 60.0 (at the limit) | 1.170 for all | 0.275, 0.236, 0.215 | 0.025 |
| Gold 200 | None | None | None | 0 | No chart |

The red K of Ektar 100 is the largest value in this lab. Its red boost of 1.563 comes from the chart, which rises above 100 % at about 10 cycles/mm. K is a fit with an inferred form, so it can overstate the colour gain of this stock. The stated model does not separate an optical gain from a chemical gain.

## 6. Numeric checks

Script: `check_stock_chain.py`. Results: [`stock_chain.json`](../../results/p5_film_and_print_combinations/stock_chain.json). Limits from P4.

| Stock | Neutral, limit 0.02 | Largest fall, limit 0.001 | Image against point, limit 0.002 | Spread mean, limit 1e-4 | Sweep, limit 0.02 | Mean C* of the chart colours |
| --- | --- | --- | --- | --- | --- | --- |
| Portra 400 (accepted) | 0.0016 | 0 | 0.00003 | 1.0e-5 | 0.0146 | 47.6 |
| Portra 160 | 0.0009 | 0 | 0.00004 | 1.0e-5 | 0.0127 | 43.3 |
| Portra 800 | 0.0012 | 0 | 0.00007 | 1.0e-5 | 0.0121 | 47.4 |
| Ektar 100 | 0.0019 | 0 | 0.00051 | 1.3e-5 | 0.0154 | 49.9 |
| Gold 200 | 0.0058 | 0 | 0 | No kernel | 0.0168 | 43.7 |
| C200 | 0.0014 | 0 | 0.000003 | 0.9e-5 | 0.0091 | 48.0 |

The print table of each stock has no negative exposure outside its curve. The share of nodes where the print dye solve does not reach its target is 47 % to 54 %, near the 54 % of Portra 400, so these stocks do not add a new problem.

The sweep limit cannot see a band over tens of columns (P4-O13). The band depth of these stocks is not measured.

The mean C* does not rank a look. Gold 200 has no inhibition, so its value is not comparable with the others.

**Neutral ramp near the grey.** a* and b* on the print from -2 to +2 stops: `fine_a` and `fine_b` in the results. This has no limit.

- **Gold 200 has a notch at the grey.** b* is +3.1 at -0.75 stops, -0.2 at 0, and +2.5 at +0.75 stops. Its blue curve has a visible bend near the Log H Ref on chart E-7022, and rule `grey_anchor` puts the neutral exactly at that bend. So the stock reads warm on each side of the grey, and part of this warmth depends on the place of the anchor. No band shows on the author's sheets. A neutral gradient was not examined.
- Ektar 100 has the largest green lean in the shadows, a* of -4.7 at -1.5 stops.

## 7. Sheets

Script: `render_p5_review.py`. Local only: `build/tmp/p5/review/<name>.jpg`, 56 files (6 portraits, 37 landscape files, 5 daylight files, 8 mountain files), with a label on every panel. Results: [`review.json`](../../results/p5_film_and_print_combinations/review.json). Panel sizes follow the cached arrays, about 750 pixels on the long side for the portraits and most landscape files, so the small-scale effects of `layer_spread` are not visible.

Comparison with spektrafilm at 3bb2c2d2 (external comparison only, ROADMAP U18; nothing is reused): `render_spektrafilm_stocks.py` and `compare_spektrafilm_sheets.py`, 7 files, the six stocks on its Portra Endura paper, with its default settings, its own automatic exposure, and no grain. Sheets: `build/tmp/p5/review_spektrafilm/`.

### Author's visual results, not user review

The author read `se188`, `se224`, `se274`, `se178`, `canon_r`, `_DSC4196`, and `5897833591`, and the spektrafilm sheets of `se345` and `fuji_xt5`. The other sheets are rendered and not examined.

- **The stocks differ in the expected order.** Ektar 100 has the most saturated and darkest result: a stronger sky on `se224` and `canon_r`, and deep reds on `se178`. Portra 160 is the softest. Portra 800 stays near Portra 400.
- **Gold 200 has a paler, greener sky** on `se224` and `canon_r`, and warm ground. The comparison panel with the Portra 160 values has more local contrast and adds little colour. So the missing chart does not cause the pale sky.
- **C200 moves toward magenta in blue** on `se224` and `se274`.
- **Skin on `se188`** stays dense and orange on all stocks, and most on Ektar 100. The Portra 400 result is the accepted reference. The look of the new stocks has no user decision.
- **Spektrafilm:** on `se345` and `fuji_xt5`, its six stocks are nearer to each other than the six stocks of this lab, and its neon background is less saturated on some stocks. Its exposure rule differs, so the tone level does not compare directly.

These notes do not show that a stock looks like the real film. Only the user can decide this.

## 8. Combinations that cannot be specified

| Item | Fact |
| --- | --- |
| Isolated dye curves of all six stocks | Not in the data sheets. The band split is inferred, and the cross absorption of each dye is not published |
| Spread and inhibition of Gold 200 | No chart in E-7022 |
| Spread per layer of C200 | One curve for all layers |
| Absolute sensitivity of C200 | Relative chart |
| The current product sold as Fujifilm 200 | No data sheet was found, and the sources disagree about the emulsion |
| A Fuji paper for C200 | Set aside by U34. spectral_film_lut has data for Crystal Archive papers, not checked here |

Push processing of Portra 800 is published (EI 1600 and EI 3200, E-4040), and this step does not use it.

## 9. Machine and commands

Intel Core i7-12700H, 31.8 GB, CPU only. No GPU job. Commands: [script README](../../scripts/poc/p5_film_and_print_combinations/README.md).

`check_fast_kernels.py` and `check_scan_path.py` ran again after the changes of this step. Their result files do not change, except the timings of `fast_kernels.json`, and that run is not kept. They run the earlier stocks, and they do not cover the new stocks.

Not measured: band depth on the sweep; L* and C* over the review files; the night and artificial light files with the new stocks; scene lights other than D55 on the new stocks; the direct inversion, which stays set aside (U32).

## 10. Open items

| ID | Item | Owner |
| --- | --- | --- |
| P5-O1 | Review the sheets: `build/tmp/p5/review/`. | User |
| P5-O2 | Gold 200 has no modulation transfer chart. Keep no spread and no inhibition, or authorize the Portra 160 values (the comparison panel). | User |
| P5-O3 | C200: use this 2017 record as is, or find a data sheet of the current product. | User |
| P5-O4 | Gold 200: the notch of b* at the grey. The look decides if the anchor needs a change. | User |
| P5-O5 | The red K of Ektar 100 is large, and the fit form is inferred (section 5). | P5 |
| P5-O6 | The Gold 200 sensitivity comes from spectral_film_lut, and its cyan layer fails the fragment limit at 478 nm (section 4). | P5 |
| P5-O7 | Run the new stocks on the night and artificial light files. | P5 |
| P5-O8 | Backlit areas: decide the strength of the mask, and if a product path uses the mask, the automatic inversion, or both (sections 11 and 12). | User |
| P5-O9 | The mask tables fail the interpolation limit (section 11). A finer step of the mask density is the direct fix, and it costs more table time. | P6 |
| P5-O10 | Closed (2026-10-31). The user ran the Portra 400 negatives through NexFilm (section 13). | User |
| P5-O11 | Review the rule `density_window_inversion` on all stocks: `build/tmp/p5/review_density_window/`. Only Portra 400 has a user result. | User |
| P5-O12 | Closed (2026-10-31). The upper endpoint comes from a window on the image (section 15). | User |
| P5-O13 | Closed (2026-10-31). The user finds the fixed direct mapping with a shoulder the most promising (section 16). | User |
| P5-O14 | Review look C on 5219 under `street_mixed`, and look A (sections 17 and 18). Sheets: `build/tmp/p5/review_looks4/`, `build/tmp/p5/review_looks3/`. | User |
| P5-O15 | Closed by the correction of section 20, if the user agrees: the real product input needs no night exposure. | User |
| P5-O16 | Closed (2026-10-31). The module takes the product grade as its input (section 20). | User |
| P5-O17 | Closed (2026-10-31). The user finds density compensation the right direction, and the colour too thin (section 21). | User |
| P5-O18 | Review the recipes from the linear scan, the levels recipe first (section 21). Sheets: `build/tmp/p5/review_recipes/`. | User |
| P5-O19 | Review the levels recipe with exposure to the right (section 22). Sheets: `build/tmp/p5/review_recipes_ettr/`. | User |
| P5-O20 | Closed (U49): the user chose candidate B of the second review (section 24). | User |
| P5-O21 | Review two lights by pixel colour on candidate B (section 24). Sheets: `build/tmp/p5/review_two_lights/`. | User |
| P5-O22 | Run NexFilm on the Hong Kong TIFF files, and review the study of the real 5219 images (section 25). Files: `build/tmp/p5/scan_negative_hk/`, `build/tmp/p5/real_5219/llf/`. | User |
| P5-O23 | Closed (2026-10-31). The user rejected all results of section 26 (U55). | User |
| P5-O24 | Think again about the scan path from the orange film base. On hold by U55. | User |
| P5-O25 | Review the print against candidate B on the 17 files (section 27). Sheets: `build/tmp/p5/review_print_vs_b/`. | User |
| P5-O26 | Review real 5207 negatives through the display paths (section 28). Sheets: `build/tmp/p5/real_5207/review/`. | User |
| P5-O27 | One true pair of one dusk scene exists (section 29). A chart or a pair with strong colours is still missing. | User |
| P5-O28 | The rule `grey_anchor` removes 0.58 stops of the blue layer of 5207, and the pair does not support this removal. Test it on more pairs, and on the other stocks (section 29). | P5 |
| P5-O29 | Review the mask removal on the real negatives (section 30). Sheets: `build/tmp/p5/real_5207/unmask/`. | User |
| P5-O30 | Review the real negatives through the 2383 print with no anchor (section 31). Sheets: `build/tmp/p5/real_5207/print/`. | User |
| P5-O31 | On the print, the simulated negative of the pair is cyan and the real negative is warm. Find the source of the red error, on more pairs (section 31). | P5 |
| P5-O32 | Review the Hong Kong day files through the print (section 32). Sheets: `build/tmp/p5/hk_day/review/`. | User |

## 11. Backlit areas of high contrast scenes (U35)

**Status:** local probes only (2026-10-31). No option of the model changes. Probes: `shadow_probe.py`, `shade_tint.py`, `ettr_probe.py`, and `shadow_mode.py`, in `build/tmp/p5/scripts/`, not committed. Sheets: `build/tmp/p5/review_shadow_mode/`. Files: the 8 mountain files. Shadow pixels: L* from 6 to 35 in the plain image. Metrics were set during the probe, with no limit, so they are descriptive.

**The light spectrum is not the main cause (calculation).** A measured reflectance under D150, with the white balance of D55, against its reconstruction, on 5207: median layer error at most 0.051 log10, against at most 0.017 under D55. The p95 grows from 0.154 to 0.219 on the largest set. D150 stands for skylight here; no measured sky spectrum was used. Scene light D65, D75, or D100 in the chain changes the neutral pixels of the first test group by at most 0.3 in a* or b*. That group had files that the user later removed, so this test needs a new run on the mountain files.

**The print stage compresses the shadows (measured).**

| Path | Mean shadow L* | Share below L* 8 |
| --- | --- | --- |
| Plain image | 23.2 | 0.02 |
| 5207, P4 print | 12.2 | 0.37 |
| 5207, spektrafilm | 9.2 | 0.54 |
| Portra 400, P4 print | 11.8 | 0.36 |
| Portra 400, spektrafilm | 12.5 | 0.40 |

**The tint of shade is a property of each stock (calculation).** A grey object under D150, with the white balance of D55, at -1 stop: C* 20.9 plain, 29.8 on 5207, and 42.1 on Portra 400. By U36 this is character and not a fault.

**Exposure to the right, printed down (user proposal).** The negative gets N more stops, and the printer balance keeps the grey. Results for 2 stops:

| Stock | Shadow L* | Share below L* 8 | Near-neutral shadow C*, b* | Highlight L* |
| --- | --- | --- | --- | --- |
| 5207 | 12.2 to 12.0 | 0.37 to 0.38 | 5.1, +0.3 to 5.0, +0.4 | 78.1 to 77.6 |
| Portra 160 | 12.2 to 11.8 | 0.34 to 0.36 | 4.7, -2.9 to 4.1, -2.2 | 86.7 to 86.3 |

So the highlights hold and the shadow colour gets a little cleaner. The shadows do not get lighter, because the negative is not the limit: the neutral ramp keeps L* 6.5 at -3 stops at each N. The Portra 400 values of this probe are not valid: it has no rule `grey_anchor`, and its printer balance did not follow.

**Contrast mask at the print stage (author's probe).** A soft positive of the negative adds density where the negative is thin, as a darkroom mask does. It uses a guided filter, with a strength in log10 exposure and values chosen by eye. With strength 0.5, on 5207: shadow L* 17.5, share below L* 8 0.05, highlight L* unchanged. On Portra 160: 15.9, 0.00, unchanged. User review (2026-10-31): a large improvement, and no cast is visible (U36).

**Physical rules (2026-10-31).** The probe above becomes two options in `film_preview.py`, and no default uses them. Rule `contrast_mask` adds a neutral density during the print, computed from the pan transmittance of the negative through a blur of 1000 um and a mask curve of gamma 0.5. The printer lights take back the density at the grey. This replaces the guided filter of the probe, which is not a physical step, so a real halo can now occur. Rule `overexposed_negative` now works on all stocks, Portra 400 too. Every value is inferred.

Script: `check_shadow_mode.py`. Results: [`shadow_mode.json`](../../results/p5_film_and_print_combinations/shadow_mode.json). Limits set before the first run. Six stocks, with the mask, 2 stops over, and both:

| Check | Limit | Result |
| --- | --- | --- |
| Table at zero density against the print table | 1e-6 | Pass, 2.4e-7 |
| Halfway between two tables against a direct table | 0.002 | **Fails on all stocks**, 0.026 to 0.041 |
| Flat mid grey, change of L* | 0.1 | Pass, at most 0.024 |
| Neutral ramp, largest fall of L* | 0.05 | Pass, 0 |
| Flat field at +3 stops, change of L* | 1.5 | **Fails on Gold 200**, 2.10. Pass on the others, at most 1.33 |
| Hue sweep, second difference | 0.02 | Pass, at most 0.0167 |

- **Interpolation.** The limit stays. A local probe (`mask_interp.py`, Portra 400 and 5207) puts the worst nodes at the edges of the table. Within 0.5 of the neutral ramp, the largest error is 0.016 and p99 is 0.007. No step was seen on the sheets. Open item P5-O9.
- **Gold 200.** The 2.10 comes with the 2 stops over: L* 89.52 to 87.42. The negative is then 5 stops above its grey. The hypothesis is that the slope of the published curve of Gold 200 falls near its end; this was not traced. The mask alone changes this field by 0.24.
- **Halo.** At a step edge from -3 to +2 stops on Portra 400, L* of the dark side is 10.0 far from the edge and 8.2 near it, and 7.4 without the mask. So the mask leaves a darker band at the edge, and it stays lighter than the P4 print. This is the halo of the real method. It was not examined on photographs at full resolution.

Neutral ramp of Portra 400, L* at -3, -2, and -1 stops: P4 7.4, 12.3, 26.3; mask 10.0, 16.2, 28.7. Sheets: `render_shadow_mode_review.py`, `build/tmp/p5/review_mask/`, 11 files.

## 12. Automatic inversion of the simulated negative (U37)

**Status:** review tool (2026-10-31). No default of the model changes.

**Question.** Does the orange negative of this model look better through an automatic inversion program?

**Later result.** The user then ran NexFilm. Section 13 replaces the statements of this section on what such a program does.

**What this is.** Script: `render_scan_inversion.py`. The scan is the APD reading of the simulated negative, as linear transmittance, with a border of unexposed film. It writes 16 bit TIFF files, linear and gamma 2.2, 11 files for 7 stocks, in `build/tmp/p5/scan_negative/`. **NexFilm did not run.** This lab does not have it, and a search found no description of its method. So rule `auto_negative_inversion` is a model of that kind of program from general descriptions, with per-channel density above the base, per-channel range from the percentiles of the frame, and an S-curve. It has no matrix and no value from a program. The percentiles (0.1, 99.9) and the contrast (1.25) are review controls, chosen by eye. The range follows the image, so the result depends on the frame.

Results: [`inversion_shadows.json`](../../results/p5_film_and_print_combinations/inversion_shadows.json). Mean of the 8 mountain files. Shadow pixels: L* from 6 to 35 in the plain image (mean 23.2, share below L* 8 0.02). Highlight pixels: above L* 85 in the plain image.

| Stock | Shadow L*, print to inversion | Share below L* 8, print to inversion | Highlight L*, print to inversion |
| --- | --- | --- | --- |
| Portra 400 | 11.85 to 26.63 | 0.36 to 0.17 | 86.69 to 97.54 |
| Portra 160 | 12.22 to 22.17 | 0.34 to 0.26 | 86.73 to 97.30 |
| Portra 800 | 12.43 to 22.67 | 0.31 to 0.23 | 85.90 to 97.21 |
| Ektar 100 | 11.32 to 22.77 | 0.40 to 0.24 | 86.92 to 97.62 |
| Gold 200 | 11.49 to 22.05 | 0.37 to 0.22 | 86.75 to 97.46 |
| C200 | 10.75 to 27.97 | 0.40 to 0.10 | 87.95 to 97.45 |
| 5207 | 12.22 to 26.53 | 0.37 to 0.14 | 78.14 to 97.54 |

**The reason, as a calculation.** The print model has a paper curve and a viewing white, and the inversion does not. The inversion puts the density range of each frame directly on the range of the display. So the shadow range of the negative stays, and this agrees with section 11: the negative holds the shadows, and the paper compresses them.

Author's visual results, not user review, on `_DSC4063` and `se274` and, at a small size, on `se188`:

- The shadows of `_DSC4063` open on all stocks, and the grass and the rocks are readable.
- The look is lighter and softer than the print. The highlights are near display white, and the background of `se274` becomes a pale lilac.
- The stocks are nearer to each other than on the print, because a range per channel takes back part of the difference between them. This works against the requirement of U36 that each stock shows its character.
- The option with a median balance per channel is more neutral again, and the skin of `se188` turns grey-green, as `frame_balance="image"` did in P4 (section 10.3 of that report). The author does not propose it.

## 13. The algorithm of NexFilm Auto Invert (U38)

**Status:** review rule (2026-10-31). No default of the model changes. The rule does not replace the accepted P4 print (U32).

**User result.** The user read the linear Portra 400 TIFF files of section 12 into [NexFilm](https://github.com/BillyDu-TJ/NexFilm), with Auto Invert only and the Film Area on the entire frame. User review: very good, and it nearly meets the expectation. Files: `build/tmp/p5/scan_negative/Portra_400_scanned/`, 11 JPEG files, local only.

**Algorithm.** Source reading at commit `fbd7113f`, and measurement on the 11 files. A file with no ICC profile takes this path:

1. The file values are read as linear sRGB, with no decoding, and go through a matrix to linear ProPhoto.
2. Per channel: D = -log10(T).
3. On a grid with a long edge of 512, the pixels are sorted by density luma (0.2126, 0.7152, 0.0722). The low endpoint is the mean of the lowest 2%, and the high endpoint is the mean of the highest 2%. Each channel keeps its own value from the same pixels.
4. n = clip((D - low) / (high - low)) per channel.
5. code = clip(ProPhoto to sRGB matrix x n). This value is the display code. There is no transfer curve and no S-curve.

**Correction of the earlier reading.** The author first read step 5 as linear light with an sRGB encoding, from the shader and the documents of NexFilm. That model gave an RMSE of about 50 of 255. The JPEG code is nearly a straight line against density. A comment in the export code says that this signal is already display-referred.

**Check.** Script: `render_density_window.py`. Results: [`density_window.json`](../../results/p5_film_and_print_combinations/density_window.json).

| Measure, mean of 11 files | RMSE of 255 |
| --- | --- |
| Rule against the NexFilm JPEG files, border removed (limit 6, set after a probe measured 5.14) | 5.66 |
| Earlier rule `auto_negative_inversion` against the same files | 15.50 |
| Rule, whole frame | 5.14 |
| Rule, whole frame, both images with a blur of radius 2 | 1.34 |

The remainder is mostly fine detail. The cause was not traced; export sharpening and JPEG compression are hypotheses. A free fit of a 3x3 matrix from n to code gives values near the ProPhoto to sRGB matrix (first row 1.94 to 2.10, -0.49 to -0.77, -0.30 to -0.40; expected 2.03, -0.73, -0.31).

**Which part does what (local probe `probe_nexfilm_parts.py`).** One part changes at a time on the Portra 400 files, whole frame. Mean of 11 files.

| Variant | RMSE against NexFilm, blur 2 | Mean C* | Median L* |
| --- | --- | --- | --- |
| NexFilm JPEG files | 0 | 14.66 | 48.32 |
| Rule | 1.34 | 14.16 | 47.76 |
| With the sRGB encoding at the end | 48.62 | 10.70 | 71.32 |
| Low endpoint from the scene, not from the border | 7.89 | 14.55 | 44.35 |
| No matrices | 6.83 | 13.79 | 48.23 |
| Independent endpoints per channel | 3.21 | 13.99 | 48.93 |

- **Density as display code is the largest part.** Density follows log exposure, so the display gets a nearly straight line in log exposure.
- **The low endpoint is the unexposed film.** The border of section 12 is more than 2% of the frame, so it fills the low tail, and the low values are the same in all 11 files (0.204, 0.396, 0.583). A black point at the film base is physical, but it comes from this export and the choice of the entire frame. With the border outside the Film Area, the low endpoint comes from the scene, and the median L* falls by about 3.4.
- **The matrices do not add saturation in total.** The first one acts on transmittance and the second one on density, and mean C* changes by only 0.37. They change the relation between colours. The earlier statement of the author, that the second matrix adds saturation, is not supported.

**Tone (local probe, Portra 400).** Neutral ramp through the product grade. The high endpoint comes from `_DSC4063`. The ramp has no frame exposure, so compare the shape and not the position.

| Stops from AP1 0.18 | -5 | -4 | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P4 print, L* | 5.8 | 5.8 | 5.9 | 6.3 | 8.2 | 16.1 | 35.8 | 61.6 | 80.1 | 88.3 |
| Rule, L* | 0.1 | 0.6 | 2.2 | 11.9 | 28.2 | 43.7 | 58.6 | 73.3 | 87.1 | 99.9 |

The rule gives 13 to 16 L* per stop from -2 to +4. The print gives 2 L* or less per stop below -1, and 26 L* per stop between +1 and +2. This agrees with section 11: the negative holds the shadows, and the print stage compresses them. A straight density display does not have this compression. The rule reaches L* 0.1, and the print stops at L* 5.8.

**All stocks (rule only; NexFilm ran only on Portra 400).** Mean of the 8 mountain files.

| Stock | Shadow L*, print to rule | Share below L* 8, print to rule | Highlight L*, print to rule | Mean Lab distance to Portra 400, print to rule |
| --- | --- | --- | --- | --- |
| Portra 400 | 11.85 to 31.78 | 0.36 to 0.09 | 86.69 to 97.27 | - |
| Portra 160 | 12.22 to 26.88 | 0.34 to 0.16 | 86.73 to 97.06 | 2.28 to 4.03 |
| Portra 800 | 12.43 to 27.28 | 0.31 to 0.14 | 85.90 to 96.99 | 2.01 to 5.18 |
| Ektar 100 | 11.32 to 27.59 | 0.40 to 0.14 | 86.92 to 97.34 | 1.72 to 4.11 |
| Gold 200 | 11.49 to 27.86 | 0.37 to 0.12 | 86.75 to 97.22 | 3.97 to 5.70 |
| C200 | 10.75 to 35.96 | 0.40 to 0.02 | 87.95 to 97.28 | 2.54 to 4.08 |
| 5207 | 12.22 to 35.44 | 0.37 to 0.02 | 78.14 to 97.37 | 8.68 to 5.07 |

So the stocks stay apart on this rule, and the five other production stocks are further from Portra 400 than on the print. The concern of section 12 about U36 applies to the earlier rule, and this measurement does not show it for this rule. The differences between stocks on the rule have no user review.

**Limits of the rule.**

- The high endpoint follows the frame. Between the 8 mountain files it moves by 0.19 to 0.29 in density, depending on stock and channel. So the same negative density can give a different code in another frame.
- About 2% of the frame reaches or nears the top of the window, with no shoulder.
- The rule has no paper and no viewing white.

## 14. Inversion from known stock data (U39)

**Status:** literature reading and local probe `probe_known_window.py` (2026-10-31). No default of the model changes. The values below have no user review.

**Published route.** The sources agree on the structure:

| Step | Source | What it uses |
| --- | --- | --- |
| Density above the base, per channel | Tuijn 1996; ADX (`ACEScsc.Academy.ADX10_to_ACES`); negadoctor of darktable | Measured film base |
| Density to log exposure through the neutral curve of the stock, as the scanner reads it | Tuijn 1996; Deschuytere and Tuijn, EP0667706B1; ADX, with one generic curve | Step wedge through the scanner |
| A neutral reference point: a horizontal shift so that the channels agree | Tuijn 1996 | Operator, or a virtual point from the statistics of the film strip and frame, as in minilabs |
| A 3x3 matrix in density space, fitted to a target: the scene or the print | Tuijn 1996 ("a generalised, multi-dimensional gamma function with cross terms"); EP0667706B1; ADX `CDD_TO_CID` | Chart measurements |
| Fixed references for black and white, for example 95 and 685 of Cineon | Cineon documents, read through secondary sources | Reference cards |
| A paper model: exposure, paper gamma, soft clip | negadoctor | Controls |

Tuijn also reports the conflict between the targets: a match to the scene is often too pale, and the high gamma of paper loses detail in the dark parts of the scene. The paper lists a print with less contrast as a third target.

**Reading of the rule of section 13 against this route.** Density per channel, base subtraction, and a matrix in density space have a published basis. Three items do not have a physical basis: the read of a scan as sRGB primaries, the ProPhoto coefficients (they do not come from the film), and density used directly as display code. The endpoints from the highest 2% of the frame are a scene statistic, comparable to the virtual point of a minilab.

**The known Dmax is not the white.** On the neutral ramp of Portra 400, APD (R, G, B): D-min 0.212, 0.620, 0.792; 0.18 grey 1.059, 1.446, 1.717; +2.7 stops 1.584, 1.922, 2.229; +14 stops, the end of the ramp, 2.300, 2.538, 2.939. A scene white is far below saturation. So the known upper endpoint is the density of a neutral at a chosen scene white. It is not the Dmax of the film.

**Probe.** High endpoints of the frame window of section 13, as stops above the grey on the Portra 400 ramp, 8 mountain files: 2.84, 2.68, 2.85, 2.81, 2.89, 2.28, 1.60, 2.06. So this window moves by 1.29 stops between these frames. The probe uses the median of each stock, about +2.7 stops. This value is a review control and comes from these files. For comparison, a 90% white card is +2.32 stops. Portra 400, mean of the 8 mountain files:

| Method | Shadow L* | Share below L* 8 | Highlight L* |
| --- | --- | --- | --- |
| Window per frame (section 13) | 31.78 | 0.09 | 97.27 |
| Known window: D-min to the neutral at +2.7 stops, no matrix | 31.26 | 0.09 | 96.03 |
| Known window with the ProPhoto matrices | 30.46 | 0.09 | 95.91 |
| D-min to the end of the ramp, no matrix | 20.90 | 0.15 | 68.06 |
| Inverse neutral curve, code linear in log exposure from -5 to +2.7 stops | 34.35 | 0.06 | 96.26 |

Author's visual results on `_DSC4063` and `se188`, 4 stocks: the known window with no matrix stays near the window per frame, and it needs no frame statistic. The window to the end of the ramp is flat and grey. The inverse curve brings the stocks nearer to each other, because it removes the crossover of each stock from the neutrals. This works against U36 if the goal is the character of the stock. Sheets: `build/tmp/p5/review_known_window/`.

**Not tested.** A 3x3 matrix per stock fitted in density space, with the print or the scene as target; a print with less contrast as the tone. This model can simulate the step wedge and the chart, so these need no calibration roll (U31).

**Sources.** C. Tuijn, Scanning Color Negatives, IS&T Fourth Color Imaging Conference, 1996. F. Deschuytere and C. Tuijn, EP0667706B1 (Agfa-Gevaert). aces-dev `ACEScsc.Academy.ADX10_to_ACES.ctl`. darktable `negadoctor.c`. The Kodak Cineon documents were not read directly.

## 15. Upper endpoint from the frame, density matrix, and paper grade (U40)

**Status:** local probe `probe_matrix_and_paper.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_matrix_paper/`, 11 files, 4 stocks. The author viewed `_DSC4063`, `se188`, and `_DSC4250`.

**User decision.** The upper endpoint of an image comes from a window on the image. This replaces the fixed scene white that section 14 proposed. The lower endpoint stays the D-min of the stock.

**Methods.** The top 2% of the pixels by density luma set the upper endpoint.

- Window per channel: each channel takes its own mean from these pixels.
- Window for exposure only: these pixels give one exposure on the neutral curve of the stock, and each channel takes the density of the neutral at this exposure. The balance between channels stays that of the stock.
- Matrix: a 3x3 matrix per stock with row sums of 1, in density space, on a chart through the model (5 exposures, 3 saturations, 24 hues, and neutrals). The targets are the graded scene and the P4 print, each carried to the tone of the neutral ramp of the window. The chart is a review control, not a measured chart.
- Paper: the print model, with two settings for each frame, as in a darkroom. The printer exposure puts the top 2% pixels at L* 90. The grade puts the film base at L* 7. Both values are review controls. The grade 0.7 row uses the exposure rule only.

**Results.** Mean of the 8 mountain files. Shadow pixels: L* from 6 to 35 in the plain image (mean 23.2).

| Portra 400 | Shadow L* | Share below L* 8 | Highlight L* |
| --- | --- | --- | --- |
| P4 print | 11.85 | 0.36 | 86.69 |
| Window per channel, no matrix | 32.60 | 0.09 | 97.44 |
| Window for exposure only, no matrix | 32.59 | 0.09 | 97.39 |
| Exposure only, matrix to the scene | 33.67 | 0.08 | 97.07 |
| Exposure only, matrix to the print | 32.35 | 0.09 | 97.34 |
| Paper, grade 0.85, exposure from the window | 20.67 | 0.21 | 89.36 |
| Paper, grade 0.7, exposure from the window | 32.27 | 0.00 | 89.58 |
| Paper, grade and exposure from the window | 25.95 | 0.05 | 89.42 |

| Mean Lab distance to Portra 400 | Ektar 100 | Gold 200 | 5207 |
| --- | --- | --- | --- |
| P4 print | 1.72 | 3.97 | 8.68 |
| Window for exposure only, no matrix | 4.24 | 6.05 | 4.37 |
| Exposure only, matrix to the print | 4.36 | 6.64 | 5.09 |
| Paper, grade and exposure from the window | 4.28 | 4.07 | 12.61 |

**Matrix fit, RMSE of 255 on the chart, no matrix to matrix.** To the scene: 9.72 to 7.49 (Portra 400), 9.56 to 8.01 (Ektar 100), 11.89 to 8.94 (Gold 200), 9.69 to 7.27 (5207). To the print: 6.66 to 5.52, 7.52 to 5.93, 5.99 to 5.04, 5.01 to 4.30. The tone is the same in all rows of the first table, so the matrix changes colour and almost no tone. Portra 400 to the print: rows 1.223, -0.087, -0.135; 0.039, 0.917, 0.044; -0.074, 0.032, 1.042.

**Paper grade.** The solved grade of Portra 400 is 0.71 to 0.88 over the 11 files, and the P4 setting is 0.85. The added printer density is 0.15 to 0.28 log10. The paper stays the published curve, with a grade and an exposure as in a darkroom.

**Which setting opens the shadows (local probe `probe_exposure_only_paper.py`, Portra 400).** With grade 0.85 and only the exposure from the window: shadow L* 20.67, share below L* 8 0.21, against 11.85 and 0.36 for the P4 print. The mean hides a difference between frames. The frames with a small range gain most (`_DSC4250` L* 34.23). The strongly backlit frames do not gain: `_DSC4063` L* 11.58, share 0.37, and `_DSC4071` L* 10.99, share 0.41. So the exposure alone does not solve the backlit case, and the softer grade is the necessary part there.

**Author's visual results.**

- The window per channel and the window for exposure only are nearly equal on the mountain files. On `se188` the background is cooler with the window per channel, because the highlight pixels become neutral.
- The matrix to the print gives more depth in the sky and the greens, and the shadows stay open.
- The paper keeps the depth and saturation of a print, and the shadows are readable. It is darker and less soft than the direct window.
- A fixed grade of 0.7 is pale on the frames with a small range.
- `_DSC4250` has a small range: the solved grade is 0.87 to 0.94, the sky is pale, and the blue areas are strong. 5207 on 2383 is pale here. Its P4 highlight is L* 78, so the highlight value of L* 90 does not suit this print material.

**Limits.** The exposure is rounded to 0.05 log10 and the grade to 0.01. A grade per frame needs a new table for each frame, so a product path needs another method for the speed (P6).

## 16. Fixed mappings from density, with no window on the frame (U41)

**Status:** local probe `probe_density_inverse.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_density_inverse/`, 20 files: 8 night, 7 daylight, 2 mountain, 3 portrait. 4 stocks. The author viewed 6 sheets.

**User decisions.** Do not try to reduce the chart error, so the matrix of section 15 stops here. The look target is soft. Check the daylight and night files too. Direct density as display code looks good. A window on each frame may not be efficient, so try the step back from density through the curve of the stock. This replaces the window decision of section 15 for now.

**Methods.** The low value is the D-min of the stock. The white is the density of a neutral at +2.7 stops above the metered grey, from the neutral curve of the stock. These are fixed per stock. The exposure of the product input stays a meter on the frame. The value +2.7 and the shoulder (knee 0.7) are review controls.

- Direct: n = (D - D-min) / (white - D-min), with a hard clip.
- Direct with a shoulder: the same, with a soft approach to 1 above the knee.
- Inverse per channel: each channel goes back through its own neutral curve to stops, and the code is linear in stops from -5 to +2.7, with the shoulder.
- Inverse with a common curve: each channel takes its density relative to its own grey through the mean curve of the three channels, with the same code.

**Results.** Shadow L*, share with a channel at the top of the code.

| Group, stock | P4 print | Window per frame | Direct | Direct, shoulder | Inverse per channel | Inverse, common curve |
| --- | --- | --- | --- | --- | --- | --- |
| Night, Portra 400 | 13.61, 0 | 32.98, 0.018 | 34.57, 0.036 | 34.57, 0 | 37.74, 0 | 38.64, 0 |
| Night, Ektar 100 | 13.31, 0 | 29.55, 0.024 | 30.76, 0.048 | 30.76, 0 | 38.00, 0 | 39.46, 0 |
| Night, Gold 200 | 13.44, 0 | 29.54, 0.018 | 30.44, 0.035 | 30.44, 0 | 37.90, 0 | 39.12, 0 |
| Night, 5207 | 14.78, 0 | 36.46, 0.018 | 37.93, 0.036 | 37.93, 0 | 38.15, 0 | 36.94, 0 |
| Daylight, Portra 400 | 12.19, 0 | 35.46, 0.051 | 33.57, 0.032 | 33.57, 0 | 36.64, 0 | 37.64, 0 |
| Daylight, Ektar 100 | 11.58, 0 | 30.89, 0.051 | 29.25, 0.032 | 29.25, 0 | 36.62, 0 | 38.29, 0 |
| Daylight, Gold 200 | 11.99, 0 | 31.33, 0.035 | 29.32, 0.025 | 29.32, 0 | 36.76, 0 | 38.04, 0 |
| Daylight, 5207 | 13.28, 0 | 38.60, 0.039 | 36.54, 0.026 | 36.54, 0 | 36.71, 0 | 35.42, 0 |

Highlight L* with the shoulder: 88 to 91 in these groups. The window per frame gives 94 to 99, and direct with no shoulder gives 95 to 97.

**Reading.**

- The fixed direct mapping stays near the window per frame on all groups. The largest group difference of shadow L* on these stocks is 2.1. So the window is not necessary for this tone.
- The shoulder removes the clipped pixels, and it does not change the shadows. Author's visual result: night lamps and clouds keep more separation and look softer.
- **The inverse per channel removes the tone difference of the stocks.** Daylight shadow L* is 36.6 to 36.8 on all four stocks, against 29.2 to 36.5 for direct. This works against U36. It follows from the method: the method takes the curve of the stock back out.
- **The inverse with a common curve is rejected by the author.** It gives strong green or purple in dark areas (Ektar 100 and 5207 on `_DSC4063`, `se188`, and `landscape__DSC0726`). This comes from the inverse: each channel has its own distance from grey to D-min, and the mean curve stretches this distance in the toe. It is not a property of the stock.
- With no window, a frame with a small range stays as metered. The city file under cloud is darker and flatter than with the window. The exposure of the product is the control for this.

**Proposal of the author.** Direct with a shoulder. The step back through the curve is used for one value only: the stock curve gives the density of the white, and no frame statistic is needed. After the negative, this is a fixed function of density per stock.

**Limit.** The value +2.7 comes from the mountain files, and it was not tuned on the other groups. The review exposure is a center-weighted meter, a stand-in for the exposure of the product.

## 17. Low key night looks on 5207 and 5219 (U42)

**Status:** local probes `probe_reference_look.py`, `probe_light_ramps.py`, `probe_looks3.py`, and `probe_looks3_bands.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_looks3/`, 23 files. The author viewed 6 sheets. All numbers of the looks are review controls chosen by eye.

**User decisions.** The fixed direct mapping with a shoulder is the most promising. The night files look too light. Bring 5207 and 5219 to the look of two reference groups, which the user supplied and which stay local: A, from a paid DaVinci plugin, and B, of the kind of the film Lost in Translation. Test on more files.

**Reference structure (measured, descriptive).**

| Group | Median L* | Black and white | Colour |
| --- | --- | --- | --- |
| A | 8 to 27 | Raised floor, code 0.02 to 0.06; no white, 98% code 0.41 to 0.72 | C* 3 to 7, a uniform cool tint |
| B | 1 to 43 | Black clipped; highlights reach white | Green middle tones, a* -5 to -13; b* -3 to -15 in the dark bands of B1 and B2; saturated reds |

**What did not work.** A scene key from the histogram does not separate night files from dark portraits (night 0.33 to 0.54, others 0.42 to 0.68). A meter limited by the highlights gives no change on `_DSC8148`. A scan with one slope gives magenta shadows on these stocks (a* +10 to +16 at -4 stops), so it does not give the green.

**Exposure is the largest part.** The review meter lifts the night files by up to 5.1 stops. A manual offset stands for the exposure of the product: A -2 stops on night files and -0.7 on the others, B -1.25 and -0.3.

**The green comes from the spectra (calculation).** A neutral on 5219, balanced for T3200 and with one slope, gives, from -2 to +2 stops, a* -6 to -13 and b* -10 to -4 under FL11, and a* +3 to -9 and b* -23 to -9 under D55. So a tungsten stock under fluorescent light, with no correction, gives green middle tones with no colour control in the display step. FL11 alone is too blue for B. A share of the cast is removed from the blue channel only, as a yellow filter does.

**Looks.** The window is the D-min to the neutral at +2.7 stops under the balance light, per channel, with a share `timing` toward the neutral of the scene light. Then, in this order: black, saturation in density around the density luma, power, shoulder, floor.

| Look | Stock, light, timing (R, G, B) | Black | Saturation | Power | Knee, ceiling | Floor |
| --- | --- | --- | --- | --- | --- | --- |
| A | 5219, D55, 0.75 for all; or 5207, D85, 0 | 0 | 0.72 | 1.3 | 0.70, 0.84 | 0.03 |
| B | 5219, FL11, (0, 0, 0.8) | 0.10 | 1.25 | 1.3 | 0.82, 1.0 | 0 |

**Result on the 10 night files, same bands as the references.**

| Band of L* | A: a*, b*, C* | B: a*, b*, C* |
| --- | --- | --- |
| 6 to 12 | 1.2, -4.7, 5.9 | -5.7, 0.7, 11.8 |
| 12 to 20 | 1.8, -3.5, 8.5 | -6.4, 4.2, 16.1 |
| 20 to 30 | 1.8, -2.5, 9.9 | -6.2, 11.2, 20.8 |
| 30 to 45 | 0.3, -6.4, 10.3 | -8.7, 4.5, 22.3 |
| 45 to 60 | -1.8, -7.4, 10.9 | -12.8, -4.6, 21.7 |
| 60 to 75 | -3.1, -4.6, 7.8 | -16.7, -6.9, 23.3 |

Median L* per file: A 4.8 to 18.3, B 1.7 to 21.1. These numbers describe the look. They are not a fit target.

**Author's visual results.**

- A is low key and muted, with a cool tint, and it is the nearest to group A. The chroma is higher than in group A (C* 6 to 11 against 3 to 7).
- B has deep black, green and cyan in the middle tones, and strong reds. It is near group B on `_DSC8085`, `_DSC8148`, and `_DSC8170`. The dark bands are not blue as in B1 and B2 (b* 0.7 to 11), and the warm street lights of these files are one possible cause. This was not traced.
- B uses the same light for the whole frame, so on daylight files it turns skin yellow and sky strongly cyan.
- Halation (0.10, 0.03, 0) makes no clear difference at the size of the sheets. It was not examined at full size.

**Not tested.** A Cineon log output, which the user recalls as one possible output of the plugin. A rule for the night exposure in the product.

## 18. Look C, and the colour of street lamps (U43)

**Status:** local probes `probe_reference_c.py` and `probe_looks4.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_looks4/`, 23 files. The author viewed 5 sheets. All values of the looks are review controls chosen by eye.

**User decisions.** Halation and glow are outside this work, because the product already has them. On look B of 5219, the colour of street lamps is too green. A third group of reference images, street scenes that stay local, is nearer to the target.

**Cause (author's reading).** Look B puts one fluorescent light on the whole frame, and warm lamps move toward green with everything else. Median hue of warm pixels on the 10 night files: 82 degrees for B, 71 degrees in the references.

**Reference structure, group C (measured, descriptive).** Median L* 14 to 29 per file. Black clipped: p10 of L* is 0 to 1. No full white: p98 of L* is 60 to 85. Low chroma pixels (C* below 12) from L* 12 to 60: a* -1.0 to -3.5, b* 0.4 to 4.0. Median C* 8 to 10, p90 20 to 30.

**Look C.** The fixed window of section 17, with black 0.11, saturation 1.0, power 1.25, knee 0.74, ceiling 0.90, no floor. Exposure offset: -1.0 on night files, -0.2 on the others. Rule 'light_by_colour' is a second option: warm pixels take the render under the balance light, by the weight smoothstep(0.5, 1.6, log2(R / B)) of the graded input.

| 10 night files | Low chroma a*, L* 12 to 60 | Low chroma b*, L* 12 to 60 | Warm pixels: a*, b*, hue | L* p50 | L* p98 |
| --- | --- | --- | --- | --- | --- |
| Group C (all 5 images) | -1.0 to -3.5 | 0.4 to 4.0 | 10.2, 28.8, 71 | 14 to 29 per file | 60 to 85 per file |
| 5219, street_mixed, whole frame, no correction | -2.2 to -3.2 | 1.4 to 4.2 | 12.5, 31.7, 68 | 12.3 | 77.5 |
| 5219, warm pixels T3200, others street_mixed | -2.2 to -3.2 | 1.4 to 4.3 | 17.2, 32.2, 60 | 13.5 | 77.7 |
| 5219, warm pixels T3200, others FL11, timing (0.6, 0.6, 0.85) | -6.3 to -7.0 | -3.2 to -1.6 | 17.3, 32.3, 60 | 16.2 | 79.5 |
| 5207, warm pixels D55, others street_mixed, timing 0.7 | 0.1 to 1.0 | 1.7 to 8.2 | 13.2, 24.1, 64 | 16.6 | 78.6 |
| 5219, FL11, yellow filter 0.8, whole frame (look B) | -4.8 to -7.5 | -2.8 to 2.3 | 4.9, 36.6, 82 | 17.4 | 88.8 |

The rows of the night files are pooled over the files, and the group C rows of tone are per file, so compare the ranges only roughly. These numbers describe the look. They are not a fit target.

**Reading.**

- 5219 under `street_mixed` for the whole frame is the nearest to group C, with no rule per pixel. This preset was written in P3 for night streets (T2800 0.3, LED-B3 0.4, HP1 0.3).
- `light_by_colour` is not needed for this. It makes lamps more orange than the references (hue 60 against 71). It does keep skin nearer to the input on `se188`.
- The median C* of the night files is higher than in group C on some bands (up to 21 against 10). The scenes differ: warm pixels are 18% of these files and 5% of the references, so the cause may be the scene. A saturation below 1 was not tested.
- `street_mixed` is a night light. On daylight files it gives a warm, olive frame.

**Proposal of the author.** Look C: 5219 under `street_mixed`, as the night preset for this stock. The light by colour rule is not proposed.

## 19. Independent review, the input grade, and emitter spectra (U44)

**Status:** local probes (2026-10-31). No default of the model changes. No user review yet. The review is `build/tmp/p5/codex/REPORT.md`, by GPT-6.1 Sol at the request of the user; sheets `build/tmp/p5/codex/review/final/`. The later probe is `probe_emitter.py`; sheets `build/tmp/p5/review_emitter/`, 9 files. The author viewed 6 of these sheets. All values are review controls.

**User decision.** The look of section 18 is still not right. Ask GPT-6.1 Sol for an independent view.

**Correction to sections 17 and 18.** The list of "10 night files" came from the meter value, not from the content. The review found that `lowlight_DSC_0604` is a studio test target, and that `canon_r6ii`, `hasselblad_h5d`, and `sony_a7riii` are daylight scenes. The numbers that those sections call night files include these 4 files. The probe of this section uses a list of 6 real night files.

**Findings of the review.**

- Similar pooled statistics do not show that two images look alike. So the comparison tables of sections 17 and 18 are weak evidence.
- The input grade (contrast +15, saturation 1.3) makes the result harder. With a neutral grade, weak shadow transitions stay, and lit surfaces and skin are less strong. This conflicts with U24, which evaluates the film chain after the default grade, so it needs a user decision.
- One light for the whole frame cannot describe a scene with several lamps.
- Tone candidate C: a shared tone on the density luma, with the density colour differences added back. T(y) = 1.10 y^1.60 y / (y + 0.12), a shoulder above 0.82, and a colour share from 0.70 to 1.0 over y from 0.30 to 0.75.
- Red signs stay orange on all candidates. A dye matrix derived from the Jacobian does not solve this.

**Cause of the orange signs (trace, `probe_sign_trace.py`, `_DSC8169`, 5219, `street_mixed`, neutral grade).** The red sign has linear Rec. 709 (1.25, 0.001, 0.03). Its layer exposures are +2.7, -0.67, and -1.79 stops from the grey, so the green layer is only 3.4 stops below the red layer. Its normalized density is (0.95, 0.53, 0.32), which shows as orange. So the loss is at the spectral reconstruction, before the dyes and the scan. The table gives a sign the broad spectrum of a reflecting object under the scene light. This also explains why the dye matrix does not solve it. No direct measurement of a real sign spectrum was made.

**Rule 'emitter_spectra' (probe).** A pure and bright pixel is taken as a light source. In the u'v' table, the entry moves toward an emission spectrum: a Gaussian line of sigma 18 nm in the direction of the node, added to the scene light as the chromaticity needs, with purity weight smoothstep(0.35, 0.60). The scene light does not act on the line. A pixel uses this table by the weight smoothstep(1.0, 2.5) of the stops of its peak channel above 0.18. This is a fixed function of colour and level, with no statistic of the frame.

**Author's visual results.**

- Red signs move from orange toward red, with a pale core (`_DSC8169`).
- Skin, flowers, clouds, and sky show no clear change (`se188`, `_DSC4063`). The rule did not act on these at the sheet size.
- The green sign of `_DSC8169` stays pale, and the blue road lights of `_DSC8148` are paler than in the plain image. So the rule is partial.
- Tone C at a colour share of 0.70 looks dull on signs and streets on these files. The tone of section 18 with a neutral grade and the rule keeps more colour, with softer lit surfaces than section 18.
- 5207 under `street_mixed` is strongly warm, near sepia, on `_DSC4063`. This light is not for daylight files.

**Proposal of the author.** Neutral input grade for this path, the tone of section 18, and rule `emitter_spectra`, on 5219 for night files. This is a candidate, and the reference look is not yet reached. Not tested: other line widths, separate treatment of blue and green sources.

## 20. The film module on the real product input (U45)

**Status:** local probes `contact_sheet.py` and `probe_module.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_module/`, 18 files; contact sheets of 203 files: `build/tmp/p5/contact/`. The author viewed 6 module sheets after the last change of the rule. All values are review controls.

**User decisions.** Exposure +1.5 EV, contrast 15, and saturation +30 are in the product. The module will be built in, so it must take this input into account. This replaces the proposal of section 19 to use a neutral input grade. The test files must be good photographs. The author had chosen weak files.

**Correction to sections 16 to 19.** Those sections use the review meter, with a manual offset, in place of the +1.5 EV of the product. The meter lifts the night files by up to 5.1 stops, and the offset of section 17 only takes back a part of this. With the real input there is no meter and no offset. Median of the graded luma, in stops from 0.18: night files -3.6 to -1.3, daylight files -1.0 to -0.5. So the night files are low key with no special exposure rule, and the author sees no need for a night exposure in the module. This was not reviewed by the user.

**Compensation in the module.** The negative receives the graded input. In density: n' = grey + (n - grey) / 2^0.15, and density saturation 1 / 1.3, with the tone of section 18. This is an approximation: the grade acts on ACEScc and Oklab before the negative, so it cannot be taken back exactly. A panel with an exact neutral grade stays as a comparison only.

**Rule 'emitter_spectra', change.** A first run on the real input turned yellow objects green: the yellow N sign of `sony_a7r6` and the yellow car of `se128`. A line near 580 nm falls on the green layer. The rule now acts only on the red end (line weight from 600 to 625 nm), the blue end (495 to 470 nm), and the purple line. Yellow and green light keep the table of the reconstruction.

**Author's visual results.**

- The yellow N sign and the yellow car stay yellow after the change. `se128`, `sony_a7r6`, `leica_m11`.
- Compensation gives softer lit surfaces than no compensation, and it stays near the exact comparison on `_DSC8175` and `leica_m11`.
- `showcase_DSC_7169` (stage light): the magenta lights turn pale and the blue sleeve turns cyan with the compensation. The exact comparison keeps more magenta. So on the most saturated input, saturation 1.3 pushes the colour beyond what the density step takes back. Here the difference is large.
- `se034`: warm city lights become pale cream, weaker than in the input, and the water at the right turns olive. This comes from `street_mixed` on a scene with no street light mix, but this cause was not traced.
- The sheets of `leica_m10` and `_DSC8169` were viewed before the change of the rule, and not after it. There, the neon red was stronger with the rule, and the green sign stayed pale. The change does not act on a pure red above 625 nm.

**Good test files (author's selection from the contact sheets).** Night: `leica_m10`, `sony_a7r6`, `se034`, `leica_m11`, `nikon_z9`, `showcase_DSC_7169`, `se275`, `fuji_gfx100s`, `canon_r3`. Others: `se128`, `se355`, `sigma_bf`, `se231`, `se091`. The user files remain for comparison.

**Proposal of the author.** The negative receives the product input, with no exposure rule in the module. Density compensation, the tone of section 18, and rule `emitter_spectra` for red and blue. The scene light stays a manual choice of the user, and `street_mixed` is not a default.

**Not solved.** The stage light file. The reference look of section 18 has no user acceptance.

## 21. Published scan recipes from the linear scan (U46)

**Status:** local probe `probe_scan_recipes.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_recipes/`, 12 files, 5219 and 5207, scene light D55. The author viewed 7 of the 24 sheets. All display values are review controls.

**User decisions.** Density compensation of section 20 is the right direction. High saturation colours are out of scope for now. The problem is that colours are too thin, with no rich colour and no blue shadows; the result looks like a log image, and the cause is the process and not the values. Start from the linear scan, and apply the published recipes.

**Method.** Each recipe reads only the linear transmittance of the scan, with its orange base, after the density compensation, and fixed data of the stock. No statistic of the frame.

| Recipe | Steps |
| --- | --- |
| Levels (tutorial) | Gamma 2.2 code, channels inverted, levels per channel from the base to the neutral at +2.7 stops, a mid slider per channel that puts the scene grey at code 0.46. The result is the display code. |
| Straight line (Zhihu, V777) | Log of T, inverted, a straight line per channel through grey and white of the balance light, back to linear, gains to the scene grey (all, or a share of 0.7), a display curve. |
| Straight line + profile | The same, through a matrix from the APD responsivities to the CIE functions under D65, to ProPhoto. Derived from spectra, not from a chart. A comparison only. |
| Cineon | ADX10 code, scene grey at 445, the 95/685 conversion with negative gamma 0.6, sRGB encoding, with and without a shoulder. |

**Author's visual results** (`leica_m10`, `sony_a7r6`, `leica_m11`, `se128`, `_DSC8085`, `_DSC8170`).

- **Levels is the richest.** It has deep shadows, blue night areas on 5219 and warm lit surfaces at the same time, and the colour of `se128` and `leica_m11` is dense and not flat. It does not look like a log image. It is harder than direct density display.
- **Straight line** stays flat, with a raised black and thin colour. The display curve here is a choice of the author and the recipe leaves the tone to a later step, so this result does not reject the recipe.
- **White balance share 0.7** gives cool shadows, with thin colour.
- **The profile** gives more saturation, and the sky goes cyan and yellow objects go green. The author does not propose it.
- **Cineon** has a red or magenta black on 5219 (`sony_a7r6`, `se128`, `leica_m11`) and a smaller one on 5207 (`leica_m11`). The cause was not traced.

**Reading.** The levels recipe is a fixed function per channel of density: an exponential of density, not linear in density. So the change from direct density display is the form of the curve, and the display step needs no frame statistic. This reading agrees with the sheets, and no further test separates the form of the curve from the mid slider.

**Proposal of the author.** Levels from the linear scan as the next base, with density compensation. Softness is the open point. The rule `emitter_spectra` was not in this run.

## 22. The levels recipe with exposure to the right (U47)

**Status:** local probe `probe_recipes_ettr.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_recipes_ettr/`, 12 files, 5219 and 5207, scene light D55. The author viewed 5 of the 24 sheets. N and the black point are review controls.

**User question.** What does the levels recipe do with exposure to the right?

**Method.** The negative gets N more stops after the product grade. Grey and white of the inversion move N stops along the neutral curve of the stock, so a grey keeps its display code. This is the printing down of section 11. The black stays the film base, or follows the exposure: the neutral at N - 6 stops.

**Neutral ramp, 5219, through the same rule.**

| Case | L* at -4 to +3 stops | b* at -4 to +3 stops |
| --- | --- | --- |
| N = 0, base | 1, 4, 15, 31, 49, 68, 87, 100 | -1, -2, -2, -1, 0, 0, -1, 0 |
| N = 2, base | 2, 7, 18, 32, 49, 68, 87, 100 | 0, 0, 0, 0, 0, -1, -2, 0 |
| N = 3, base | 2, 7, 18, 32, 49, 69, 88, 100 | 0, 1, 2, 1, 0, -2, -4, 0 |
| N = 2, follow | 1, 5, 16, 31, 49, 68, 87, 100 | 0, 0, 1, 1, 0, -1, -2, 0 |
| N = 3, follow | 1, 5, 16, 31, 49, 69, 88, 100 | 0, 1, 3, 2, 0, -2, -4, 0 |

5207 gives nearly the same L*, with b* within -1 to +1.

**Reading.**

- Tone changes only a little on a neutral. The shadows gain up to 3 L* with the black at the base. The black that follows takes most of this back.
- The neutral at N = 3 on 5219 has warm shadows and cool highlights. This is the opposite direction to the blue shadows that the user wants. So this result gives no reason to expect blue shadows from exposure to the right.

**Author's visual results.**

- Saturated and bright areas change more than a neutral does. They stay further from the top of the channel. The green dome and warm lights of `leica_m11` keep more colour at N = 2 and 3. The skin and the yellow car of `se128` are softer, with no thin look.
- At N = 3, `se128` turns warmer. At N = 3 the sky of `leica_m11` is deeper.
- `leica_m10` and `sony_a7r6` change little.
- The black that follows gives deeper shadows than the black at the base, with the same highlight colour.

**Proposal of the author.** The levels recipe with N = 2 and the black that follows. No blue shadow is added by this step; on the sheets, a blue night area comes from the input scene.

## 23. Second independent review (U48)

**Status:** review by GPT-6.1 Sol at the request of the user (2026-10-31): `build/tmp/p5/codex/round2/REPORT.md`; sheets `build/tmp/p5/codex/round2/review/`, 12 files, 5219 and 5207. No default of the model changes. No user review yet. The author viewed 4 of its 24 sheets and the light patches.

**Findings of the review.**

- **The flat look of the straight line recipe in section 21 comes from the display curve of the author**, and not from the log inversion. With the same log exposures, the curves differ in code at -4, -2, 0, +2, and +3 stops: 0.07, 0.21, 0.46, 0.78, 0.88 against 0.03, 0.13, 0.46, 0.82, 0.91.
- **A broad RGB scan does not restore the colour.** A scan through the Nikon D850 sensitivities under an assumed D55 backlight generally gives weaker colour separation than APD. This is one camera with no profile.
- **The red black of Cineon in section 21 is an encoding fault.** Forcing the grey to code 445 moves the film base of 5219 to codes (123.6, 22.4, -13.6), and the conversion assumes 95.
- **Blue shadows come from mixed light (calculation).** With one scan balance fixed for T3200, a neutral at -2 stops on 5219 has b* +0.08 under T3200 and -16.56 under D55. On 5207, fixed for D55: +0.71 under D55 and -7.96 under D85. So this is an effect of the light, and a bright object under the same light is blue too. Under one uniform light the crossover of the stock is small. Incomplete correction cools the middle and upper tones, and leaves the deep shadows warm, so the review rejects the idea of section 22.

**Candidate B of the review.** Product grade, N = 2, the density compensation, APD. Per-channel slope from the neutral at N +/- 1 stop. x = (Dc - g) / s in stops. Code = sigmoid(log(0.46 / 0.54) + 0.85 x), with no sRGB encoding after it. Controls: N, grey code 0.46, slope 0.85. This has no white endpoint.

**Author's visual results.** B is deeper than the levels recipe of section 22 on `leica_m10` and `_DSC8085`, with a stronger sky colour on `leica_m11` and warmer lit surfaces. Highlights keep more separation. Facial shadows on `se128` are harder, and the image is darker. The review states the same limit. The author agrees that B is the better base for the complaint of thin colour, and that softness is still open.

**Proposal of the author, not tested.** Keep the balance fixed to the balance light of 5219 and combine it with rule 'light_by_colour' of section 18: warm pixels stay under T3200, other pixels go under daylight. Then blue areas beside warm lamps come from the two lights. This assumes that the colour of a pixel identifies its light, which the review warns is not true in general. A neutral object in a warm room would turn blue, so it is at most a scene preset for night.

## 24. Two lights by pixel colour on candidate B (U49)

**Status:** local probe `probe_two_lights.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_two_lights/`, 14 files. The author viewed 11 of the 14 sheets. `se034`, `canon_r3`, and `se275` were not viewed.

**User decision.** Candidate B of section 23 looks best, and it is the base for this work. Warm pixels must be under tungsten light.

**Method.** The tone is candidate B, with N = 2, and with the neutral and slopes from the ramp of the balance light. The rule is 'light_by_colour' of section 18: D = w D(warm light) + (1 - w) D(other light), w = smoothstep(0.5, 1.6, log2(R / B)) of the graded input in linear Rec. 709. It is a fixed function of the pixel, with no statistic of the frame. The only choice per panel is the other light.

| Panel | Balance | Warm pixels | Other pixels |
| --- | --- | --- | --- |
| 5219 baseline | D55 | D55 | D55 |
| 5219, daylight | T3200 | T3200 | D55 |
| 5219, intermediate | T3200 | T3200 | T4300 |
| 5207 baseline | D55 | D55 | D55 |
| 5207, cool | D55 | D55 | D85 |

**Author's visual results.**

- **The direction gives the blue that candidate B did not have.** On `_DSC8085`, `leica_m11`, `nikon_z9`, and `_DSC8148`, the road and the lit surfaces stay warm, and the sky and the areas away from the lamps go deep blue. The lamp colour does not change much against the baseline.
- **5219 with T4300 is the best of the panels at night.** It gives a deep blue with no obvious fault on `_DSC8085`, `_DSC8148`, `leica_m10`, and `sony_a7r6`.
- **5219 with D55 is too strong.** The tree trunk of `_DSC8085`, the gravel of `fuji_gfx100s`, and the sky of `nikon_z9` turn saturated blue. The wall lamp on `_DSC8170` turns blue.
- **5207 with D85 is the most restrained.** It is a usable cool look on all the viewed files, and it has the smallest effect on portraits.
- **Grey areas become blue.** The grey sky of `nikon_z9` and the grey train of `sony_a7r6` have no blue in the input. The result looks good, but the colour comes from the rule.

**Faults of the rule, as the second review warned.**

- **Hue changes on objects, in all two-light panels.** The green skirt of `se128` turns blue. Hair and eyes turn blue on `se128` and `se231`. With D55 the foliage of `se231` turns teal.
- **These are not faults of the stock.** A neutral or green object in warm light has w = 0, so the rule puts it under the cool light. The colour of a pixel does not identify its light.

**Night RAW files of the user (U50).** The same probe on `2136729222`, `5437808984`, `8390668518`, and `P1031516` (`probe_two_lights_night.py`, input cache `build/tmp/p4/input_night/`). The author viewed all 4 sheets. The order of the panels stays the same: T4300 on 5219 is the best, D55 on 5219 is too strong, and D85 on 5207 is the most restrained. With D55, the pavement of `5437808984` and the grey sky of `P1031516` turn a saturated blue. With T4300, the pavement of `5437808984` is blue far from the lamps and warm near them. These 4 files have no close portrait, so they do not test the hue fault on objects. The canopy highlights of `P1031516` are pale in all film panels, and the input has saturated yellow there. This comes from candidate B, not from the rule, because the baseline panels show it too.

**Hong Kong night RAW files of the user (U51).** The same probe on 13 RW2 files (`probe_two_lights_hk.py`, sheets `build/tmp/p5/review_two_lights_hk/`, input cache `build/tmp/p5/input_hongkong/`). The author viewed all 13 sheets.

- **The rule works where warm and cool light are both in the scene.** `P2625463`, `P2625457`, `P2625453`, `P2625452`, and `P2625451` with T4300 on 5219: warm streets and walkways stay warm, and the buildings and the sky go blue.
- **The rule adds too much where the scene is blue already.** On the harbour files `P2625429`, `P2625433`, and `P2625440`, and on `P2625448`, baseline B has a deep blue with no rule. With D55 the sky and the water turn a saturated blue. On `P2625429`, the pink reflections in the water are weaker with both 5219 two-light panels, and 5207 with D85 keeps more of them.
- **The rule is wrong under one interior light.** `P2625475` (train interior) and `P2625455` (arcade) have one main light, and the rule makes the metal and the clothes blue. With D55 on `P2625475`, the face in the foreground turns cool.
- **Pixels that are only a little warm count as cool.** The warm road of `P2625419` and the cream pillars of `P2625447` lose their warm colour, because log2(R / B) is below the range of the smoothstep.
- **Warm highlights are pale in all film panels, the baselines too.** Examples are the orange street of `P2625451` and the yellow walkway of `P2625453`, as on `P1031516`. So this comes from candidate B.

**Decision of the author.** The two-light rule is not a default for all images. It is a night or mixed light option on candidate B, off by default, with the other light as the one control: T4300 on 5219, D85 on 5207. This agrees with the manual scene light of the product, and it needs no detection. Softness on portraits stays open.

## 25. Real 5219 references against candidate B (U52, U53)

**Status:** local probes `probe_real_5219_stats.py`, `probe_real_5219_parts.py`, and `probe_llf_learn.py` (2026-10-31). No default of the model changes. No user review yet. Sheets and data: `build/tmp/p5/real_5219/llf/`. This is a diagnostic. No part of the result is a product rule.

**User statements.** Candidate B is still not soft. The user asked for the Hong Kong files as linear TIFF files with the orange base, to run in NexFilm. The user also asked for a study of the real 5219 images, with a split into a base and a lightness map and with learned colour distributions, and not with one-dimensional Lab measures.

**TIFF files.** `build/tmp/p5/scan_negative_hk/`, local only, half-size RAW decode, product grade, 16 bit linear APD transmittance, border of unexposed film. Sets: `5219_T3200`, `5219_D55`, and `5219_T3200_N2`.

**Method.** All in OKLab at a long edge of 1000.

- Base lightness: local Laplacian filter (Paris 2011, fast form of Aubry 2014). Detail: lightness minus base. Base colour: guided filter of a and b.
- Tone: 1D optimal transport of base lightness, with the quantile mean over images.
- Detail: per Laplacian band, median band size against base lightness, real against source after the tone map.
- Colour: 3 component Gaussian mixture for reading, and sliced optimal transport (Pitie 2007) with a degree 3 polynomial fit of the displacement.

The references are 4 panels from 2 screenshots. The user states that they are real 5219. Their grade, scan, and capture are not known. The source is candidate B on the 13 Hong Kong files. The scenes differ, so a learned map holds scene content too.

**Results.**

| Part | Measure | Stability over the 4 references |
| --- | --- | --- |
| Tone | Base lightness quantiles 5, 25, 50, 75, 95, 99: source 0.21, 0.33, 0.49, 0.66, 0.86, 0.94; real 0.07, 0.17, 0.31, 0.41, 0.64, 0.89. Slope in the middle is near 0.6, with a steep rise above source 0.8. | Consistent in form |
| Detail, finest band | Gain 0.58 | 0.39 to 0.85, all below 1 |
| Detail, other bands | Gain 0.70 to 0.80 | 0.52 to 1.16, not consistent |
| Colour | Base colour has a narrower blue to orange axis. The warm probe moves by about -0.03 in b, and the cool probe by about +0.03. Light neutrals move warm: +0.015 in b at L 0.85. | Pooled only, no per-image value |

**Author's visual results.**

- Tone alone is darker and harder on all 3 viewed part sheets, with crushed shadows. So the global curve does not give softness alone.
- Colour alone gives the largest change toward the references: cream highlights, and a less electric blue.
- Detail alone is a small and natural softening.
- All three on `P2625475` come near the mood of the references. On `P2625457` and `P2625463` the shadows are too dark.

**Limits.** The detail map of the references shows block patterns from image compression, so the gain of the finest band can be partly compression. The colour result comes from pooled pixels of 4 references.

**Reading of the author.** Softness in the references comes from three things together: a low and nearly straight slope through the middle tones, a narrower colour axis with warm highlights, and fine detail with less contrast. Candidate B has a sigmoid with a steep middle. A straight density display with a lower placement is the next physical test, and the NexFilm result on the TIFF files is direct evidence for it.

## 26. A scan path with three stages, and density-domain display preparation (U54)

**User result (U55, 2026-10-31):** all results of this section are rejected, candidate D too. The proposal of the author at the end of this section is withdrawn.

**Status:** local library `density_display.py`, and local probes `check_density_display.py`, `probe_density_display.py`, `probe_density_display_stocks.py`, `probe_density_display_scale.py`, and `probe_hue_trace.py`, in `build/tmp/p5/scripts/` (2026-10-31). Logs: `build/tmp/p5/density_display/`. No default of the model changes. No user review yet. All numeric values are review controls.

**User request.** Test the proposals of a third person: keep the scanner apart from the display preparation; split density into an exposure coordinate and a colour residual; use multiscale rendering on the exposure coordinate; keep the scene light apart from the scan balance, with no rule per pixel. Also read Plutino et al. 2025. The user then rejected the first test files as not representative, so the author chose a new set of 17 files from the contact sheets.

**Files.** Night and mixed light: `leica_m11`, `sony_a7r6`, `fuji_gfx100s`, `se275`, `_DSC8148`, `se034`. Portraits: `se015`, `se228`, `se197`, `se127`. Daylight and interior: `hasselblad_x2dii`, `nikon_zf`, `se091`, `nikon_z5`, `canon_r5ii`, `sony_a7cii`, `_DSC4071`. Stocks: 5219 and 5207. The first files stay only as the source of the first observations below.

**Source observations, Plutino et al. 2025** (Signal, Image and Video Processing 19:976, doi 10.1007/s11760-025-04569-8; read from the supplied PDF). One test leader on KODAK 2254 was scanned on 12 cinema scanners.

- The tone encoding differs between scanners, and the DPX metadata does not always state the applied transfer.
- Glare is always present and depends on the image content, so a LUT cannot compensate for it.
- Context glare difference on the positive scans, in 16 bit code: 379, 392, 1583, and 542 on scanners 1, 2, 8, and 9, which the paper reads as linear. These are 0.6 % to 2.4 % of full scale, for black marks on a white surround.
- The paper gives no spread function. It does not study colour negative film or the look of an image.

**Stages.**

| Stage | Operation | Basis |
| --- | --- | --- |
| A, negative read | APD density | As in earlier sections |
| B, scanner | Glare in linear transmittance above the base: t' = (1 - eta) t + eta blur(t), blur of sigma 2 %, 10 %, 35 % of the long edge, weights 0.5, 0.3, 0.2 | eta from the range of the paper. The spread is inferred |
| C, display preparation | The steps below | Proposed design |

**Stage C.**

- **Tangent split.** v is the tangent of the neutral density per stop at the balance grey, and w = L / v, scaled so that w^T v = 1, with L the Rec. 709 luma weights. x = w^T (D - g), c = (D - g) - x v. There is no inverse H-D curve. On the neutral ramp of the checked stock, x is -5.8 at -6 stops and 4.9 at +6 stops, so the curve of the stock stays in x.
- **Neutral track.** c_n(x) is c on the neutral ramp of the balance light. Object colour is c_p = c - c_n(x). A chroma gain acts only on c_p, so the crossover of the stock stays at full strength (U36).
- **Density multiscale.** A fast local Laplacian filter on x, with the remap r_g(x) = x - (1 - alpha) sigma tanh((x - g) / sigma), sigma 1 stop. The remap is linear in alpha, so one set of K pyramids serves all alpha values. Band alpha, finest first: 0.55, 0.65, 0.8, 0.9, 1, 1, for bands from a period of about 0.2 % of a long edge of 1000 pixels. A larger image takes additional finer levels at the alpha of the finest band. Then Y = T(x').
- **Colour to display.** Form 'channel': a sigmoid per channel on x' + kappa c. Form 'ratio': T on luminance, and colour as log2 ratios in linear Rec. 709. Candidate D is the geometric mean in linear light, with beta 0.4 toward the ratio form. kappa is 1.35 for the ratio form and 1.0 for the channel form, and it falls by 50 % from x = 2 to x = 4.5.
- **Tone.** T(x) = sigmoid(logit(grey code) + 0.85 x). Grey code 0.40 is the proposal. Candidate B has 0.46.

**Double counting.** At these review sizes one pixel is near 36 um on the film, so the layer spread of 3 to 6 um is below one pixel. At full resolution the finest bands overlap the scale of the film model. The alpha of those levels was not studied.

**Numeric checks (`check_density_display.py`, `probe_density_display_scale.py`). Limits set before the first run.** Stocks: 5219 under D55 and T3200, and 5207 under D55.

| Check | Limit | Result |
| --- | --- | --- |
| Split reconstructs D - g | 1e-9 | 1.1e-16 |
| Multiscale with alpha 1 returns x | 1e-12 stops | 0 |
| Flat x at alpha 0.5 | 1e-9 stops | 0 |
| Glare on a flat field | 1e-6 density | 0 |
| Overshoot at a step edge from -3 to +2 stops, alpha 0.5 | 0.10 stops | 0 |
| Falls of luma on the neutral ramp, ratio form | 0 | 0 |
| Green code RMS, long edge 3004 reduced to 751, against long edge 751, `P2625457` on 5219 | 0.02 | 0.018 |

The step edge check uses an ideal edge, and it does not show the absence of a halo on a photograph. The author saw no halo on the viewed sheets, at sheet size only. The RMS is close to its limit, and only one file was tested. `detail_bands` takes 43.4 s on the CPU at a long edge of 3004, so this implementation is not a product path.

**Hue fault of the ratio form (trace, `probe_hue_trace.py`).** With the ratio form alone, yellow walls turn salmon and a cyan sky turns violet (`hasselblad_x2dii`, `leica_m11`). The film path is not the cause: a patch of linear Rec. 709 (1.0, 0.7, 0.12) on 5207 has log2 R/G of +0.51 at the input, +0.55 in the ratio form, and +0.20 in the channel form. The hypothesis of the author is the path above the display range, which moves toward a neutral of equal luminance: a desaturated orange reads as salmon, and clipping per channel moves it toward yellow. This hypothesis was not tested in isolation. The blend removes the visible fault for beta from 0.3 to 0.5 on the viewed files.

**Measured, on the 13 Hong Kong files, 5219, D55, grey code 0.46 (`probe_density_display_scale.py`).** Descriptive, with no limit.

| Measure | Result |
| --- | --- |
| Lightness detail, candidate D against B, median by band, finest first | 0.686, 0.775, 0.867, 0.929, 0.971 |
| Base lightness quantiles 5, 25, 50, 75, 95, 99, B | 0.205, 0.327, 0.490, 0.661, 0.863, 0.940 |
| The same, candidate D | 0.212, 0.334, 0.493, 0.655, 0.849, 0.929 |
| The same, real 5219 panels | 0.066, 0.168, 0.311, 0.410, 0.620, 0.903 |

So detail falls while the base lightness stays near B: at grey code 0.46 the multiscale changes the local contrast and not the global tone. The real panels stay much darker, and the scenes differ. A band comparison against the real panels is not reported here. It was computed without the tone map of section 25, so it is not comparable with that section. These 13 files are not in the new file set, because this measurement reuses the method of section 25.

**Author's visual results, not user review.** Sheets: `build/tmp/p5/review_density_display/`, with `pick/` as the sheets for the user. Viewed in full: `leica_m11`, `se228`, `hasselblad_x2dii`, `sony_a7r6`, `se091`, `se275`, `fuji_gfx100s`, `se197`, `_DSC4071`, `_DSC8148`, `nikon_zf`, `se015`. The other files are rendered and not examined. Skin softening was also viewed in crops of the first files `se188` and `P2625457`.

- **Soft, with the global contrast kept.** Skin, road, and wall texture fall, and the eyes and edges of objects stay sharp (`se228`, `se197`, `se015`). The set 0.35 to 0.85 starts to look retouched on skin, so the author keeps 0.55 to 0.9.
- **Colour.** Skin moves from the grey-yellow of B to a warm and dense colour on `se228` and `se197`. Sunset colour returns on `se091`. Warm highlights keep their colour on `leica_m11`, where B is pale. The sky of `hasselblad_x2dii` has more colour than B.
- **Stocks stay apart on candidate D** (`stocks/hasselblad_x2dii.jpg`, 7 stocks): deeper reds on Ektar 100, warmer on Gold 200, and a cyan sky on C200. Portra 400 was not run: its accepted options have no rule `grey_anchor`, and a scene light needs this rule.
- **Whole frame cooler light, with no rule per pixel.** T4300 on 5219 with balance T3200, and D85 on 5207 with balance D55. With 50 % of the offset removed in the scan, a grey wall and a road go slate blue while skin and lamps stay warm (`se228`, `fuji_gfx100s`, `se197`). No object changes hue the way the green skirt of section 24 does, on the viewed files. With no correction the result is strong: violet sky on `leica_m11`, and cool skin on `se197` and `se228`. The cool light acts on everything, so a warm lamp also moves a little.
- **Spectral Jacobian M (comparison only).** M = J A^-1 from the spectral chain. Hues of flowers and leaves are nearer to the input on `se188`, and skin reads redder. M v against 1 is 0.71 to 0.77 in blue, so the tangent and the Jacobian disagree in that channel. The cause was not traced. The author does not propose M.
- **Glare 0.6 %.** A small effect on these files: lamps and bright windows fall a little and read softer (`se275`, `sony_a7r6`). The 2.4 % panel on the first files dims highlights more. The author keeps it as a scanner option with eta 0.006.
- **Grey code.** 0.40 gives more depth on night files (`_DSC8148`) and stays natural on daylight files (`nikon_zf`). 0.34 is dark on daylight files.
- **Creative cool toe.** A bell in x adds log2 (-0.14, 0, 0.22) per display channel. It gives blue shadows that the scene does not hold. It is labeled as a creative scan colour, and it is not a property of the negative.

**Not solved.** Backlit shadows: the tone of D stays near B in the shadows, so `_DSC4071` is not more open than B. The global tone of the real panels was not reached, and the author did not try to fit it.

**Proposal of the author.** Candidate D with grey code 0.40 as the next base of the scan path. Scene light stays a manual control, with a share of the offset that the scan removes. Glare at 0.6 % stays an option. The creative cool toe stays a separate named control, off by default. Rule `light_by_colour` of section 24 can be dropped if the user accepts the whole frame method.

## 27. The 17 files through the print, against candidate B (U55)

**Status:** local script `build/tmp/p5/scripts/render_print_vs_b.py` (2026-10-31). No default of the model changes. No user review yet. Sheets: `build/tmp/p5/review_print_vs_b/`, 17 files, 2 x 2 panels of long edge 1000, with no plain image. The author viewed `se228`.

**User decisions.** All results of section 26 are rejected. The scan path must be thought through again from the orange film base, and this work is on hold. Output the files through the print, with candidate B as the comparison.

**Method.** The same product input for all panels: +1.5 EV, contrast 15, saturation 1.3. Print: 5219 and 5207 on 2383, scene light D55. Candidate B: section 23, N = 2, scene light D55.

**A choice of the author.** 5219 has balance T3200 by default. So that its print and candidate B have the same scene light and a neutral grey, its print panel uses `balance_light="D55"`. This changes one review option, and the default of the stock stays. A flat AP1 grey of 0.18 through the print gives L*, a*, b* of 45.86, -0.06, 1.21 on 5219 and 45.89, 0.01, 0.97 on 5207.

## 28. Real 5207 negatives of the user (U56)

**Status:** local scripts `inspect_real_5207*.py`, `real_5207_frames.py`, `real_5207_stats.py`, `real_5207_render.py`, and `compare_chuanxi.py`, in `build/tmp/p5/scripts/` (2026-10-31). Outputs: `build/tmp/p5/real_5207/`, local only, because these are private photographs. No default of the model changes. No user review yet.

**User statement.** The user has 5207 scanned on a Hasselblad X5, and asked how it can be used. The user also finds the spectral method weak.

**Source.** `D:/素材/照片/胶片翻拍/2023 5207/2/`: 3 TIFF files of 7992 x 29176 pixels, 16 bit, uncut strips with the orange base, 2 strips per file, about 6 frames per strip. The frame detection gives 34 frames: `f16` holds two half frames. The content is rooms, cats, and mountains. There is no chart.

**Metadata (FlexColor 4.8.13).** Resolution 3200, Gamma 2, FilmType 0, FilmCurve 4, Saturation 15, USMAmount -60, USMRadius 10, ApplyCurves true, ApplyUSM true, input profile Flextight Input. The metadata does not state which of these settings are in the stored pixels. Holder code near 0.046. The film base is stable over the 6 strips: median code near 0.74, 0.525, 0.41.

**Hypotheses.** Code is T^(1/2), from the Gamma setting. The X5 channels stand in for APD; their responsivities are not known.

**Real against simulated negative, no paired scene (`real_5207_stats.py`).** Holder pixels removed. Simulated: the 17 files of section 26, 5207, D55, N = 0. Descriptive, with no limit. The two groups have different scenes and unknown exposure, so a difference can come from the scenes.

| Measure | Real | Simulated, exposure only | Simulated, product grade |
| --- | --- | --- | --- |
| Density of the base (real: gamma 2, against a clear gate; simulated: D-min) | 0.26, 0.56, 0.77 | 0.21, 0.55, 0.84 | same |
| First principal axis, R, G, B to green | 0.847, 1, 1.043 | 0.848, 1, 0.959 | 0.835, 1, 0.972 |
| Variance off that axis | 2.9 % | 3.3 % | 5.3 % |
| p99 density above base | 1.06, 1.18, 1.21 | 1.37, 1.54, 1.38 | 1.40, 1.58, 1.41 |
| Median R - G for G from 0 to 1.4, steps of 0.2 | 0.01, 0.03, 0.00, -0.04, -0.10, -0.13, -0.14 | 0.01, 0.00, -0.02, -0.04, -0.09, -0.13, -0.16 | 0.01, 0.01, -0.01, -0.03, -0.08, -0.12, -0.17 |
| Median B - G for the same steps | -0.01, -0.05, -0.05, -0.06, 0.02, 0.05, 0.01 | -0.02, -0.06, -0.07, -0.09, -0.08, -0.07, -0.08 | -0.02, -0.06, -0.09, -0.10, -0.08, -0.06, -0.05 |

**Reading (hypothesis).** The simulated negative agrees with the real negative in the base, in the red channel track, and in the exposure direction of red. Blue is further away: from G 0.8 up, B - G differs by about 0.1 density. This is not a proof of the model, because no scene is paired. But it gives no support to the statement that the spectral negative is the main fault of the scan path. The product grade raises the variance off the axis to 1.8 times the real value.

**Real negatives through the display paths (`real_5207_render.py`).** Density above base, one neutral offset per frame as printer lights do, which puts the median G density at 0.58. Print: APD to Status M by a fixed point iteration on `table_apd`, then the 2383 print tables, without the spatial steps of the negative. Candidate B: section 23. Density window: section 13, with no matrix and with the base as the low endpoint. Sheets: `real_5207/review/f<nn>.jpg` and `overview_*.jpg`.

The iteration leaves an error above 0.02 density on some pixels of 17 of the 34 frames, at most 0.40. The share of these pixels was not measured.

**Author's visual results, not user review.** The author viewed the 3 overview sheets and `f14`.

- All three paths give a look near real film prints and scans on rooms and buildings. The density window is the softest and most natural, with open shadows. So the simple rule that gave a thin result on the simulated negatives does not look thin here. The scenes differ, so this is not a direct comparison.
- The print and candidate B look similar to each other on these frames.
- The mountain frames `f13` to `f15` are too dark in the print and in candidate B. This comes from the timing rule: a thin sky fills most of the frame, and the median gives -0.41 density. It is not a result of the display paths.

**True pairs.** The search of this section found no pair. The user then found one (section 29). `D:/素材/照片/2023.6川西/` holds 19 Sony ILCE-7RM3 files of a snow mountain with cloud, and 2 NEF files of other scenes. The capture time was not read from the previews, and the framing does not match the viewed frames `f13` to `f17`. The author could not show that it is one scene.

**Not done.** Softness of the real frames by band. Registration of the repeated frames (`f13` to `f15`, `f21` and `f22`, `f29` and `f30`); their median density differs by at most 0.09, and the scene can differ too. Any fit to these frames.

## 29. A true pair: one digital file and the 5207 frames of one scene (U57)

**Status:** local scripts `pair_inspect.py`, `pair_register.py`, `pair_analyse.py`, `pair_flare.py`, and `pair_light.py`, in `build/tmp/p5/scripts/` (2026-10-31). Outputs: `build/tmp/p5/real_5207/pair/`, local only. No default of the model changes. No user review yet. One scene at dusk: snow, rock, cloud, and sky. It holds few colours, and it says nothing about skin or saturated colours. So this section is no calibration.

**Pair.** `D:/Download/_DSC4976.ARW`, Sony ILCE-7RM3, 2023-06-24 20:15:09, 70 mm, f/10, 1/30 s, ISO 100, against frames `f15` and `f14`. The time between the digital and the film frames is not known, and the cloud moved. The lenses differ, and the two cameras had different flare.

**Registration.** An affine fit with SciPy: correlation 0.9687 on `f15` and 0.9357 on `f14`, above the limit of 0.8 set before the run. `f13` reached 0.8418 with a sheared transform, so the author does not use it. The moving cloud is removed by a residual limit of 0.08 density in G: 88.7 % of the pixels of `f15` and 77.3 % of `f14` stay. Blur of sigma 2 pixels on both images.

**Real against simulated negative, pixel by pixel (`pair_analyse.py`).** Density above base. Exposure of the simulated negative: +3.0 stops on `f15` and +3.25 on `f14`, from the smallest G error. Gamma 2 of the scan stays a hypothesis; this agreement supports it, on the middle tones.

| Input | Frame | Median simulated - real, R, G, B | RMS, R, G, B | RMS after an offset per channel |
| --- | --- | --- | --- | --- |
| Exposure only | `f15` | 0.011, 0.013, -0.113 | 0.056, 0.048, 0.116 | 0.059, 0.049, 0.030 |
| Exposure only | `f14` | 0.024, 0.028, -0.107 | 0.064, 0.058, 0.112 | 0.070, 0.060, 0.033 |
| Product grade | `f15` | 0.013, 0.032, -0.089 | 0.071, 0.063, 0.097 | 0.075, 0.065, 0.036 |
| Product grade | `f14` | 0.034, 0.053, -0.081 | 0.080, 0.076, 0.092 | 0.089, 0.077, 0.039 |

Two errors stand out: blue is lower in the simulated negative, and the darkest rock is lower in all channels, by about 0.10 to 0.15 density.

**The blue error.** A search for a gain per channel gives (0.06 to 0.07, 0, 0.74) stops on `f15` and (0.07, 0, 0.78) on `f14`, at no flare.

- **White balance alone does not explain it.** The first hypothesis of the author was that the digital decode takes out the blue of dusk. The multipliers of the file do not support this: as shot 2.926, 1, 1.277, and daylight 2.739, 1, 1.369 to green, so a daylight decode adds -0.095, 0, +0.10 stops.
- **Rule `grey_anchor` explains most of it.** The rule applies a gain per layer so that a grey under D55 lands at the Log H Ref. On 5207 its gain is +0.037, 0, -0.577 stops to green. Section 5 read this spread in the charts as a limit of the charts, and that was a hypothesis. Taken back, and with the daylight decode, the input moves by -0.132, 0, +0.676 stops, with no fitted value.

| Input, `f15`, registered area | Median dD, R, G, B | RMS against real, R, G, B |
| --- | --- | --- |
| Real | 0.845, 0.974, 1.042 | - |
| Now: `grey_anchor`, as shot, +3.0 stops | 0.856, 0.998, 0.952 | 0.058, 0.051, 0.117 |
| No `grey_anchor`, daylight decode, +3.0 stops | 0.814, 1.014, 1.073 | 0.081, 0.052, 0.036 |
| The same, with a flare of 12 % of the frame mean, +2.75 stops | 0.799, 0.996, 1.056 | 0.066, 0.036, 0.038 |

Blue falls from 0.117 to 0.036. Red rises from 0.058 to 0.081: the fit asks for a small positive red gain, and this correction gives a negative one. This is not resolved. The X5 channels are not APD, and their blue response is not known, so a scanner difference can hold a part of the blue.

**The dark rock.** A flare share in the scene light lowers the total RMS, with a coarse search: from 0.050 to 0.037 on `f15`, and from 0.055 to 0.040 on `f14`, both at a share of 12 %, with the exposure search taking part in this. The minimum is broad and the exposure grid makes the curve uneven. So the hypothesis is a real veil of the film camera, or a toe of the film that the data sheet does not show. The cameras had different lenses, so a part of the difference can be the flare of the digital camera. This is not separated.

**Author's visual results, not user review.** `pair/sheet_light_f15.jpg`, one fixed printer offset and one fixed window for all panels. The real negative has a lavender sky and blue rock on the print and on candidate B. The simulated negative with the present input is grey and green. With no `grey_anchor` and with the daylight decode, the simulated negative leaves grey and green and goes blue, but it stays more cyan than the lavender of the real negative. This agrees with the red error in the table above: the simulated negative has too little red density here. With the flare the rock also lifts toward the real negative. No per-channel timing is applied, and a real print or scan has one, so the lavender is not a statement on the final look.

**Reading.** On this one scene, the simulated negative is close to the real negative in tone, and the largest error comes from a rule of this lab and not from the spectral chain. So this pair gives no support to the statement that the spectral sampling is the main fault. It says nothing on saturated colours, where the reconstruction has a known loss (section 19).

**Not tested.** Other scenes; other stocks; a run with `grey_anchor` off in the product path, which needs a printer balance by a measured frame; the softness of the real frame against the digital file.

## 30. Mask removal on the real 5207 negatives, with no exposure to the right and no grey anchor (U58)

**Status:** local script `real_5207_unmask.py`, in `build/tmp/p5/scripts/` (2026-10-31). Log: `build/tmp/p5/real_5207/unmask.log`. Sheets: `build/tmp/p5/real_5207/unmask/`, local only. No default of the model changes. No user review yet.

**User decision.** Remove the exposure to the right. Remove `grey_anchor`. Start from the plain APD read, and try to remove the mask on the real film.

**Method.** Input: the 34 frames of section 28, with the same hypotheses: gamma 2, and X5 channels as APD. The three numbers of each method are the display code, after one scale per frame: the p98 of the density luma. So no method uses a colour statistic of the frame, and there is no tone curve.

| Method | Operation |
| --- | --- |
| m0, control | Density of the negative with its base, inverted only |
| m1 | D - base, per channel: a division by the base in linear transmittance |
| m2 | m1 / neutral density per stop of the data sheet curves at the grey: 0.1518, 0.1734, 0.1568 |
| m3 | Amounts of the cyan, magenta, and yellow dyes of the profile that give D under APD above the spectral D-min, by `solve_amounts` on a table of 33^3 nodes |
| m4 | m3 / amount per stop on the neutral ramp: 0.1507, 0.1642, 0.1604 |

The slopes come from the ramp with `grey_anchor=False`. On that ramp a grey has density above base of 0.665, 0.765, 0.798, and amounts of 0.657, 0.710, 0.830.

37 % of the table nodes keep a residual above 0.01 density. These are combinations of density that the dyes cannot make. The share of real pixels on such nodes was not measured.

**Simulated negative with no anchor, on the pair of section 29.** `f15`, `grey_anchor=False`, exposure +3.5 stops from the smallest G error, with no gain per channel and no fitted colour value. Median simulated - real: -0.013, +0.016, -0.013 density. RMS: 0.065, 0.048, 0.032. With the anchor, section 29 has a blue median of -0.113 and a blue RMS of 0.116. So this removal alone takes out the blue error of section 29. One scene.

**Author's visual results, not user review.** The author viewed `overview_m2.jpg`, `overview_m4.jpg`, `f02.jpg`, and `pair_f15.jpg`.

- m0 is strongly cyan and blue, as an inverted orange base must be.
- m1 takes out the orange, and leaves a green and yellow lean: on `f02` the floor tile is cream and green.
- m2 gives a neutral grey cat and warm tile on `f02`, and rich colour on rooms. Highlights are near the top of the code, and sky goes lavender on `f13` to `f17`.
- m3 is cleaner than m1, with a grey cat and more separate reds on `f02`. It has less lean than m1, and it leans less pink than m4.
- m4 is near m2, more pink on floors and skies.
- On the pair, the simulated negative stays close to the real negative under all five methods. The rock and the sky are bluer in the simulated negative, and the real negative has more red.

The author has no proof that the cat or the tile is neutral. By U36 these leans are measured as properties and not as faults. The result has no tone curve, so highlights are pale and it does not yet have a display step.

**Not done.** A tone curve after the removal. Fine detail at the full scan resolution. Other stocks. The 3 x 3 regression against the digital file in `pair_report.json` is not reported, because this scene has too few colours for it to be stable.

## 31. The real 5207 negatives through the 2383 print, with no anchor (U59)

**Status:** local script `real_5207_print.py`, in `build/tmp/p5/scripts/` (2026-10-31). Log: `build/tmp/p5/real_5207/print.log`. Sheets: `build/tmp/p5/real_5207/print/`, local only. No default of the model changes. No user review yet.

**User request.** Try the 2383 print, after section 30.

**Method.** `FilmPreview` with `grey_anchor=False` and scene light E_ref. No exposure to the right. The density of the scan goes to Status M by the fixed point iteration of section 28, then through the print tables. The spatial steps of the negative are not applied, because the scan holds them. One neutral density offset per frame, as the printer exposure: the p98 of G density above base lands on the neutral at +2 stops (1.114). Two colour settings:

- Printer default: the table as it is.
- Fixed colour timing for the roll, a calculation with no statistic of a frame: an offset per channel that moves a grey under D55, with no anchor, to the grey that the table prints as neutral. Grey that the table prints as neutral, above base: 0.665, 0.765, 0.798. Grey under D55: 0.678, 0.756, 0.783. Offset: -0.022, 0, +0.006 density.

The grey under D55 is read from the anchored ramp, shifted per layer by the gain of the anchor. This is an approximation.

The iteration leaves an error of at most 0.46 density on some pixels. The share of these pixels was not measured.

**Author's visual results, not user review.** The author viewed `overview_a.jpg`, `f02.jpg`, and `pair_f15.jpg`. The fixed timing was viewed only on `f02` and `pair_f15`.

- The print of the real negatives has dense colour and warm light, and it reads as a print. The warmth is strong on rooms under artificial light (`f28`, `f31`, `f32`).
- `f02`: cat and tile are warmer than m3 of section 30, with more depth in shadow.
- Some frames are too dark: `f05`, `f17`, `f19`, `f21`, `f22`. In these frames the p98 sits on a bright window or sky. This comes from the one number exposure rule of this script.
- **The print amplifies small density errors.** An offset of only -0.022 in red visibly removes pink on `f15`. On the pair, the real negative is warm with brown rock, and the simulated negative with no anchor at +3.5 stops is cyan with teal rock, though its density errors are small (section 30: median -0.013, +0.016, -0.013, and RMS 0.065 in red). So density RMS alone does not show if a negative is close enough for the print path.

**Not done.** Another exposure rule. The reason for the red error. Any change to the print tables.

## 32. Hong Kong day files through the simulated 5207 and the 2383 print (U60)

**Status:** local script `render_hk_day.py`, in `build/tmp/p5/scripts/` (2026-10-31). Sheets: `build/tmp/p5/hk_day/review/`, local only, 20 files. No default of the model changes. No user review yet.

**User statement.** The print of the real negatives of section 31 is acceptable. Try the Hong Kong day photographs from `D:/素材/照片/2026.5香港/香港/`.

**Method.** 20 RW2 files, decoded at a long edge of 1600, +1.5 EV, 5207, no exposure to the right on the print panels. Panels on each sheet: print with `grey_anchor` off and the product grade; print with `grey_anchor` off and exposure only; print with `grey_anchor` on, scene light D55, and the product grade (section 27); candidate B, N = 2, D55, and the product grade. The print tables with the anchor off are built for the neutral of that option, so the print takes back a large part of the difference between the two negatives. No real film of these scenes exists, so nothing here compares with film.

**Author's visual results, not user review.** The author viewed the overview, and the sheets of `P2625280`, `P2625329`, and `P2625304`. The other sheets are rendered and not examined.

- The print is soft and dense on all three files, with cream highlights, a muted sky with a green lean, and deep shadows.
- The panels with the anchor on and off are close to each other on these three files. The panel with the anchor off is a little lighter and warmer on `P2625304` and `P2625329`.
- Exposure only is softer and has less saturation than the product grade: the red taxi and the flowers of `P2625304` are less strong. The product grade keeps stronger reds.
- Candidate B has whiter highlights, a cooler sky, and harder contrast.
- Shadows of the market on `P2625280` are heavy in all print panels.
