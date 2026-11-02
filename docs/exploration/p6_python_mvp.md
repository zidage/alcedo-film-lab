# P6: Python MVP

**Design:** [ROADMAP section 8](../../ROADMAP.md#8-route-from-poc-to-mvp), step P6, with decision U61.
**Date:** 2026-10-31.
**Status:** in progress. **The Frontier method is dropped (U64).** Section 5.3 states the APD method that replaces it, and the text about Frontier in the other sections, and `results/p6_python_mvp/checks.json`, are the record of the earlier state. The checks pass. The user ran the desktop viewer and judged the result very good (2026-10-31). The review sheets were stopped at the request of the user, who runs the program, so the look of most new stocks has no review.

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

## 5.3 The APD method (U64)

The user dropped the Frontier method and asked for APD as its requirements state. The chain is `ScanPreview` of `aces_scan.py` (P3): equation 1 of ST 2065-2 at its 2 nm nodes, equation 2 of ST 2065-3 with no rounding (float pipeline) and with the clip to 0 to 1023, one offset per channel in ADX10 that sets a neutral at code value 445, the ADX10 to ACES transform of aces-dev v1.3.1, and an ACES output transform (default ACES 2.0, Rec. 709, 100 nit; ACES 1.3 is an option). The P3 checks of the encoding and the transform are the checks of this code; this code did not change. The standards do not define another display rendering.

Controls: scanner light (default 0), LAD aim (default on), ACES output, and timing, now shared with the print. `frontier_scan.py` and `fetch_frontier_tables.py` are removed. `build/tmp/p6/vendor/frontier.npz` stays local and nothing reads it.

Checks: `check_p6_controls.py` on 5207 passes with 0 failures: 40 cases at the ends of the controls, smallest effect 0.00085, largest fall on the neutral ramp 0. A neutral of 0.18 on the 8 accepted stocks is in ADX10 441.2 to 447.0 (limit 445 +/- 5). The offset comes from a flat spectrum, and the image goes through the reconstruction, so the difference stays. Not run: `check_p6_mvp.py`, so the other 22 negatives have no check on this method.

Local script `build/tmp/p6_spektrafilm_audit/apd_shadows.py`, 5 files with the product grade. Shadow pixels: L* below 25 in the print of the same stock. Columns: shadow L*, shadow b*, median L*, C* p95.

| Stock | Print | APD, ACES 2.0 | APD, ACES 2.0, scanner light +0.5 | APD, no LAD aim |
| --- | --- | --- | --- | --- |
| 5207 | 12.3, 4.2, 33.3, 36.2 | 8.4, 1.6, 27.1, 27.0 | 13.2, 2.3, 34.4, 28.3 | 8.1, -1.7, 26.6, 26.8 |
| 5219 | 12.3, 2.5, 33.4, 35.2 | 7.9, 1.5, 26.8, 27.9 | 12.7, 2.2, 34.0, 29.4 | 10.4, -11.2, 30.7, 36.7 |
| Portra 400 | 12.2, 1.2, 33.3, 48.0 | 7.5, 3.2, 26.5, 32.9 | 11.8, 4.5, 33.6, 34.0 | 12.4, -0.9, 34.8, 41.6 |

- The offset per channel of the LAD aim removes the blue of the earlier scan path (shadow b* of 5219 on Frontier: -15.7).
- As in P3, the standard chain is darker than the print and has less chroma, because the ADX to ACES transform has no print stock. The user rejected this path on 2026-10-30 (U26), before P4. There is no user review of it on the current negative.
- The differences between stocks are small when each stock has its grey at code value 445. Time at 2048 pixels with a loaded model: APD 2.98 s, print 1.91 s, in the same run.
- The APD responsivities are SMPTE copyright, and the license in their archive covers XML schemas only. The product must not include that table before a review. A table derived from it for a stock has an open question too.

## 5.4 Rule `foliage_spectra` (U73)

**Question.** Noritsu scans of real Portra 160 (`D:/Download/000001340001.tif`, `000001340006.tif`) show clean green foliage. The Portra 160 print of the Cuihu DNG files of 2026-05-22 shows yellow foliage. The scenes differ, and no true pair exists.

**Trace (source: local probe `build/tmp/p9_noritsu/`).** The foliage is green in the product input, more yellow after the negative with a plain three-LED reading, and most yellow in the print. Both spectral priors give this result. The cause in the negative is a hypothesis with strong support: a synthetic leaf spectrum (chlorophyll bands, green peak, red edge) gives a Portra 160 red layer exposure 0.098 log10 below the table at the same XYZ. The leaf spectrum is inferred, and it is not a measurement.

**Method.** See the header of `film_preview.py`. One sector of u'v' moves to a leaf shape with the XYZ of each node. The rule is in the table, so each stock applies its own sensitivities. No per-stock value exists.

**Checks.** `check_foliage_spectra.py`, all 30 negatives, `results/p6_python_mvp/foliage_spectra.json`. Limits were set before the run. All 30 pass: a grey ramp does not change (0 of 8 bit code), six colours outside the sector change by at most 1, and the largest step along the chroma sweeps grows by at most 1 against the limit of 2.

**Measured property.** Red layer error with the rule off, in log10: Portra 160 -0.098, Portra 400 -0.150, Portra 800 -0.165, Ektar -0.158, Gold 200 -0.165, 5207 -0.179, 5219 -0.154, C200 -0.129, Pro 400H -0.114. So Portra 160 has the smallest change of these stocks. With the rule on, the error is 0.000 on the Kodak stocks of this list and about -0.014 on the Fuji stocks. Four tungsten stocks (5213, 5277, Eterna 500, EXR 5248) keep about -0.17, because the leaf under T3200 falls mostly outside the sector.

**User review.** The user chose the Portra 160 print with this rule. The sheets of 11 stocks on 4 files are local: `build/tmp/p9_noritsu/sheets/stocks_*.jpg`. The user has not reviewed them yet.

**Not measured.** Real leaf spectra, other green objects in the sector, portraits with green surroundings, and sizes other than 1600 pixels. The earlier checks of P6 did not run with this rule.

**Resources of Alcedo Studio.** `build_product_resources.py` ran with the rule at lab commit `f7084c0`, and all its checks pass with their limits; see the [P7 report](p7_spectral_acceleration.md), section 5.5. `check_foliage_spectra.py` ran again at the commit of that record, and its result file has the same bytes.

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
| P6-O5 | Closed by U64: the Frontier method is dropped, so its table does not ship. New: review the SMPTE terms for the APD responsivities and the tables derived from them. | User |
| P6-O6 | `fuji_superia_reala`, `kodak_5213`, and the other stocks of rule `relative_sensitivity_level`: check that the rule does not take away a real tungsten or stock balance. | P6 |
| P6-O7 | Review rule `foliage_spectra` on the 11 stocks (section 5.4). The resources of Alcedo Studio already have the rule. | User |
