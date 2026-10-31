# P6: Python MVP

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P6, with decision U61.
**Date:** 2026-10-31.
**Status:** in progress. The checks pass. The desktop viewer has not run. The review sheets were stopped at the request of the user, who runs the program. There is no user review.

## 1. Question

Can one Python program take a RAW file through all film and paper data of spectral_film_lut, by the print and by the Frontier scan, at 2048 pixels on the long edge, with the spectral prior as an option?

## 2. Result summary

- **Two methods run on one pipeline:** the print of P2 to P5, and the classic scan with the Frontier table of NegPy. HyperTone is not used (U61).
- **Materials:** 30 colour negatives and 18 print materials run. `kodak_dye_transfer_negative` and `technicolor_v` do not run, because they have no spectral sensitivity and the print model needs it. No substitute is used.
- **Not included:** the black and white and the reversal materials of spectral_film_lut. They need a different chain, and this step does not have one. U61 asks for all data, so this item is open (P6-O1).
- **Time at 2048 pixels:** print 0.82 s, Frontier 4.92 s, RAW decode 0.64 s, on one RAW file. A first use of a pair builds its table in about 6 s. A first Frontier use of a negative takes about 65 s.
- **The look of the new stocks has no review.**

## 3. Inputs

| Input | Source | Note |
| --- | --- | --- |
| Materials | spectral_film_lut (MIT) at `bcbcfc68` | Not checked against the manufacturer documents. Existing profiles do not change |
| Frontier table | NegPy at `cce849ad` (GPL-3.0), `frontier.npz` | Derived from the tables of the Fujifilm Frontier 350/370 software. Local only, license review open (U27) |
| RAW file of the checks | One RW2 file of the user, 6008 pixels on the long edge | Local only |

## 4. Method

`mvp_pipeline.py` holds the shared path: RAW decode, product grade (+1.5 EV, contrast 15, saturation 1.3, as U45), then one of the methods.

**Size.** The decode uses half size when this is at least 2048 pixels, then a box reduction to exactly 2048. A smaller sensor keeps its size, and the parameter file states this. There is no enlargement.

**Frontier method (`frontier_scan.py`).** APD density above base, one window per frame, the print curve with auto density and grade, the Frontier table, then the lab scanner stage (chroma denoise, skin protection, unsharp mask), which the user can switch off. The form follows NegPy and is written again on NumPy, so it is near NegPy and is not its output. There is no cast removal (U36). The window and the meters are statistics of the frame.

**Spectral prior.** The author read this option as two controls, because U61 does not define it further, and the user has not confirmed this reading:

- `spectral_prior`: `light_like` (rule `light_like_spectra` of P4) or `measured_reflectance` (the prior of P1 with no change).
- `scene_light`: `reference` (default) and the lights and mixtures of U21 and U22.

Inferred rules of this step:

| Rule | Operation | Effect |
| --- | --- | --- |
| `stock_options_from_catalog` | An accepted stock keeps its values. A new stock takes a grey exposure of 12.5 / ISO lux seconds, its published dyes or the band split, and spread and inhibition from its modulation transfer curves | Sets the tone position of a new stock |
| `print_conditions_by_medium` | A cine material takes the conditions of 2383, and a paper takes those of Endura | Grey aim and viewing light |
| `no_anchor_at_reference_light` | The default has no `grey_anchor` (U58). Another light needs it, because the printer balance follows the light | Another light changes the balance rule too |
| `relative_sensitivity_level` | A reference grey more than 3 stops from the criterion, as a mean of the layers, means no absolute level. Each layer moves to the criterion, and `grey_anchor` sets the balance | 8 new stocks and the C200 rule (table below) |
| `zero_minimum_density`, `neutral_from_dyes` | A negative with no such curve takes zero, or the sum of its dyes | `kodak_5247_II`, `kodak_5248`, `kodak_5250`, `kodak_5293` have no measured orange base |

Stocks with `relative_sensitivity_level`: `fuji_superia_reala`, `kodak_5213`, `kodak_5247`, `kodak_5248`, `kodak_5250`, `kodak_5277`, `kodak_aerocolor`, `kodak_ultramax_400`. The limit decides by level alone, so a real tungsten stock such as 5213 can pass it. The hypothesis is that a part of its offset is the tungsten balance. The balance light of `grey_anchor` for such a stock is T3200.

## 5. Checks

Script: `check_p6_mvp.py`. Results: [`checks.json`](../../results/p6_python_mvp/checks.json). Limits set before the first run. Input: a synthetic ramp and colours, and one RAW file. Run time: 1888 s on the CPU, with the first table builds. Intel Core i7-12700H, no GPU job. Peak memory was not recorded.

| Check | Limit | Result |
| --- | --- | --- |
| RAW long edge | 2048, exact | 2048 |
| Each negative on its default print and on Frontier, each print on 5207 | No error, output in 0 to 1 | Pass, 0 failures |
| Largest fall of G code on a neutral ramp, -5 to +5 stops | 0.002 | Pass: negatives 0 on print and 0.00002 on Frontier; prints at most 0.00023 |
| The same settings twice | 0 | 0 |
| The two spectral priors differ on saturated colours, mean absolute code | Above 0.001 | 0.02247 print, 0.02788 Frontier |
| Tungsten against daylight, mean absolute code | Above 0.002 | 0.00811 print, 0.04066 Frontier |
| A material with no sensitivity | Error with the reason | Pass |

These checks show that the chain runs and stays monotonic. They do not show that a stock looks right. Only one pairing per negative and one negative per print ran, not all 540 pairs.

The command line wrote one 16 bit TIFF of Gold 200 by the Frontier method, with its parameter file: render 5.11 s. The other planned runs of the command line, the viewer, and `render_p6_review.py` did not finish, because the user stopped them to run the program.

## 6. Source of the Frontier decision

Local probes of 2026-10-31, in `build/tmp/p5/scripts/` (`probe_scanner_taste.py`, `probe_scanner_chain.py`, `probe_scanner_stocks.py`). Sheets: `build/tmp/p5/scanner_taste/`, `scanner_chain/`, `scanner_stocks/`.

- **Narrow band light adds little in this model.** On the published 5207 dyes, the largest term of a channel on another dye is 0.123 for APD, 0.147 for an SP3000 estimate, and 0.148 for Scanlight bands. The terms move between channels, and the sum does not fall clearly. This agrees with P3 section 11.3 on published dyes.
- **Public Frontier data exists.** This corrects P3-O14, which states that no public tone data exists.
- **Backlit shadows, 4 mountain files, shadow L* and share below L* 8:** print 16.0, 17.5 %; density window 32.7, 0.9 %; Frontier 18.3, 11.6 %. So this method opens the shadows less than the density window. The user chose the Frontier method after these sheets.

## 7. Commands

See the [script README](../../scripts/poc/p6_mvp_gui/README.md).

## 8. Open items

| ID | Item | Owner |
| --- | --- | --- |
| P6-O1 | Black and white and reversal materials: a chain for them, or a decision to leave them out. | User |
| P6-O2 | Confirm the reading of the spectral prior option (section 4). | User |
| P6-O3 | Run the viewer. It has not run, so its behaviour is unverified. | User |
| P6-O4 | Review the look of the new stocks and the pairs that did not run. | User |
| P6-O5 | The license review of the Frontier table (U27). | User |
| P6-O6 | `fuji_superia_reala`, `kodak_5213`, and the other stocks of rule `relative_sensitivity_level`: check that the rule does not take away a real tungsten or stock balance. | P6 |
