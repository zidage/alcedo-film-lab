# P6: Python MVP

**Design:** [README section 8](../../README.md#8-route-from-poc-to-mvp), step P6, with decision U61.
**Date:** 2026-10-31.
**Status:** in progress. The checks pass. The user ran the desktop viewer and judged the result very good (2026-10-31). The review sheets were stopped at the request of the user, who runs the program, so the look of most new stocks has no review.

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
| Frontier table | NegPy at `cce849ad` (GPL-3.0), `frontier.npz` | Derived from the tables of the Fujifilm Frontier 350/370 software, with no license from Fujifilm. Local in this repository; the product includes it by decision of the user (U63) |
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

## 5.1 User controls (U62)

The window and the command line expose 17 values of the model and of the Frontier method, the display white, the display gamut compression, and in the window the long edge. List: `mvp_pipeline.CONTROLS`. No new process is added. They are creative controls, and their ranges are the choice of the author, not measurements.

The defaults keep the earlier image: on `se188`, with 5207 and with Portra 400, by the print and by Frontier, the largest difference of display code from the same render before the change is exactly 0 (local script `build/tmp/p6_spektrafilm_audit/default_output.py`). A later rebuild of all tables from the sources changed the same renders by at most 3.0e-7 of display code, below one step of a 16 bit file (1.5e-5). So the default look does not change, and the defaults keep their origin. The default print contrast of 0.85 and the print grey of 0.85 on a cine print were selected by comparison with spektrafilm output (P2 report, sections 8.1 and 8.5), so the print look is not an independent result.

Script: `check_p6_controls.py`. Results: [`controls.json`](../../results/p6_python_mvp/controls.json). Limits set before the first run. Input: one RAW file of the Alcedo Studio tests (`4092970974.pef`) at 2048 pixels, 5207 on 2383.

| Check | Limit | Result |
| --- | --- | --- |
| Each control at each end: output in 0 to 1 | No failure | Pass |
| Each control at each end: mean absolute code against the default | Above 0.0001 | Pass; smallest 0.00088 |
| Each control at each end: largest fall of G code on the neutral ramp | 0.002 | Pass; 0 |
| A control of one method on the other method: largest difference of code | 0 | 0 |
| A value outside the range | Error that names the control | Pass |
| The high end of the inhibition on all 30 negatives | The curves F_i exist | Pass |

The first run used `se188` at 718 pixels and failed 2 cases of 45: light spread 0 changed the code by about 1e-9. At that size the spread is below one pixel. The limit did not change, and the input is now at the size of the MVP. On a smaller image this control has little effect.

A control changes one stock pairing in these checks. The other pairings, and the look at each value, have no check and no review. Time of one check case (the photo at 2048 pixels and the ramp), from `controls.json`: 1.2 to 6.3 s by the print with stored tables (the highest with a new scene light), about 6 to 8 s by Frontier, and 55 s for the first Frontier case, which builds its tables. In the first run, a case that built a new print table took about 6 to 7 s at 718 pixels. Each new table stores 6.6 MB.

## 5.2 Links of P6 to spektrafilm

Audit of 2026-10-31 against spektrafilm `3bb2c2d2`. Local scripts: `build/tmp/p6_spektrafilm_audit/`. The chain of P6 has no import of spektrafilm, no shared high-precision constant, and no profile value from it. Shared runs of 30 normalized tokens are structural (dataclass fields, array setup). The share of curve nodes within 0.0005 is 0 to 3 % on sensitivity and characteristic curves, after the scale offsets are removed.

These items are not independent:

| Item | Link | Size, when the item is removed from the default, mean of 5 files |
| --- | --- | --- |
| `CINE_GREY_STATUS_A` = 0.85 | Selected by comparison with its output, in place of the LAD aim of about 1.06 | At 1.06, on 5207 and 2383: Delta E*ab p50 7.5, median L* -7.2 |
| `print_contrast` = 0.85 | Selected by a sweep with the chroma of its output as the target | At 1.0: Delta E*ab p50 2.9 to 3.4, C* p95 about +3.6 |
| `display_white` = reflector | Selected after a ramp through both chains; the definition is physical | With the paper as white: Delta E*ab p50 4.4 to 4.6 |
| Rule `development_inhibition` | Same algorithm as `model/couplers.py`: the largest difference from the first step of this lab is 1.3e-4 dye amount on synthetic input with no diffusion. This lab then takes 4 steps, and K is fitted here | Off: Delta E*ab p50 0.9 to 1.6, C* p95 -1.5 to -3.5, by both methods |

The sizes are sizes of an effect on 5207 and 2383 and on Portra 400 and Endura. They are not scores, and the user did not review them. The first three items act on the print only. So the Frontier method has only the link of the inhibition; its tone and colour come from NegPy and the Frontier table.

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
| P6-O3 | Closed: the user ran the viewer. The controls of section 5.1 ran with no display only, until the user opens them. | User |
| P6-O4 | Review the look of the new stocks and the pairs that did not run. | User |
| P6-O5 | Closed by U63: the product includes the Frontier table, and the user accepts the license risk. The release text with the non-endorsement statement and the NegPy notice stays open. | User |
| P6-O6 | `fuji_superia_reala`, `kodak_5213`, and the other stocks of rule `relative_sensitivity_level`: check that the rule does not take away a real tungsten or stock balance. | P6 |
