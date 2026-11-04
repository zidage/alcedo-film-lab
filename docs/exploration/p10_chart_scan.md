# P10: chart-calibrated scan

**Status:** first results 2026-11-03 (ROADMAP U87); round 6 on 2026-11-04 (U89). Scripts: [`scripts/poc/p10_chart_scan/`](../../scripts/poc/p10_chart_scan/README.md).
Results: `results/p10_chart_scan/chart_scan.json`, `review.json`. Review sheets: `build/tmp/p10/review/<stock>.jpg` (local only). No user review yet.
Nothing in the product changes.

## 1. Aim

The user asks for a scan mode whose inversion is calibrated by a chart with public spectra, photographed on the simulated negative, in place
of the generic ADX10 to ACES transform of P3, and with no ACES output transform: the scene values go directly to Rec. 709 (U87). The inversion
must come from the data of the stock, not from statistics of a frame (U79).

## 2. Method

Rules are stated in `chart_scan.py`.

- Chart: BabelColor Avg of 30 ColorChecker charts, 24 patches, 380-730 nm in 10 nm steps, on the 1 nm grid by the hold rule of P1 (source in
  `sources.json`; the file states no redistribution terms, so it stays in `build/tmp/p10/sources/`).
- Light: the balance light of the stock (rule `chart_calibration_light`). With the reference scene light of the viewer, this is `E_ref` for most
  stocks; Superia X-TRA 400 has a relative sensitivity and uses D55.
- Negative and scanner: the point form of the P2 negative (flat patches) and the ideal APD scanner of P3.
- Curves (rule `chart_grey_scale`): a flat grey from -10 to +10 stops in 1/32 stop steps; per APD channel, the rising part of record against
  stops is inverted (rule `chart_equivalent_exposure`).
- Matrix (rule `chart_matrix`): least squares from the equivalent exposures of the 24 patches to their AP1 under the calibration light
  (Bradford to the AP1 white), with M (1, 1, 1) = (1, 1, 1).
- Display (rule `chart_scan_display`): AP1 to linear Rec. 709 (Bradford AP1 white to D65), clip, sRGB encoding. No tone curve.
- Check set that the fit does not see: the 190 rawtoaces training spectra of P1.

## 3. Results (`run_chart_scan.py`)

CIEDE2000 against the target of each patch (mean / p90):

| Stock | Chart, curves only | Chart, curves + matrix | rawtoaces 190, curves only | rawtoaces 190, curves + matrix |
| --- | --- | --- | --- | --- |
| kodak_5207 | 5.10 / 9.35 | 3.01 / 5.17 | 5.72 / 10.02 | 3.95 / 7.63 |
| kodak_5219 | 5.63 / 9.90 | 3.34 / 5.35 | 5.97 / 10.36 | 4.08 / 8.07 |
| kodak_portra_400 | 6.01 / 10.80 | 2.51 / 5.21 | 6.38 / 10.87 | 3.40 / 7.15 |
| kodak_portra_160 | 6.17 / 12.49 | 1.86 / 3.74 | 6.29 / 11.86 | 2.26 / 4.66 |
| kodak_ektar_100 | 7.25 / 13.95 | 2.71 / 6.00 | 7.84 / 13.79 | 3.81 / 8.33 |
| fuji_superia_xtra_400 | 4.67 / 9.82 | 1.91 / 3.75 | 5.33 / 9.29 | 2.80 / 6.23 |

- The kept part of the grey scale covers at least -5.4 to +5.7 stops on every channel of these stocks.
- The matrices are alike between stocks: the red row takes 0.34 to 0.56 of green, and the diagonal of red is 0.54 to 0.73. So the curves
  alone give more chroma than the scene, mostly in red and green.
- A neutral of the image path (an AP1 grey through the reflectance reconstruction, not a flat grey) comes back within 0.01 stop. Its chroma is
  0.2 to 1.4 C* at the grey and 0.6 to 3.5 C* at +4 stops: the reconstructed spectrum of an AP1 grey is not flat.

## 4. Review sheets (`render_chart_scan_review.py`)

Six sample RAW files (portrait, plant, daylight, cat, film_emulation, street), long edge 1200, product input of P2. Per row: the digital input
through the same display, the scan with the curves only, the scan with the curves and the matrix.

Author's view, not a user review:
- Curves + matrix is close to the digital input on all stocks. The curves undo the tone of the negative fully, and the matrix undoes most of
  its colour, so the remaining film character is small: what a 3 x 3 matrix cannot take back, and the image-plane steps.
- Curves only keeps the colour separation of each stock: cyan blue skies, denser reds and greens; Ektar is the strongest, Superia the weakest.
  The tone is still that of the scene, because the curves undo the characteristic curve.
- With no tone curve, values above 1 clip (`review.json` has the share per panel). On the daylight file, Ektar with the curves only clips
  22.7 % of the pixels (digital input 1.3 %), mostly the sky that leaves the Rec. 709 gamut.
- Records outside the kept part of a curve take its end (rule `chart_grey_scale`). Their count is in `review.json`; it is largest on Portra 160,
  whose blue curve is kept only from -5.4 stops.

## 5. Second round: straight line, and public scans of real film (U87)

The user asked for a second try, and noted that many lab scans were compared before. Two additions:

- Rule `chart_straight_line` (option inversion = 'straight'): per channel, only the slope of the grey scale from -2 to +2 stops and the record
  of the grey. It keeps the toe and the shoulder of the negative.
- `compare_lab_scans.py`: the method of P3 section 10.3 on the public chart scans of Film Analyzer (local, license not stated), with the
  current stock options of the viewer under daylight. Chart accuracy is not a goal (P3 section 10.3); the numbers show a direction only.

Delta E*ab median / hue difference median / chroma ratio median at offset 0, after one exposure shift to the Neutral 5 of the scan:

| Set | Curves only | Curves + matrix | Straight line only | Straight line + matrix |
| --- | --- | --- | --- | --- |
| 5207, CoolScan 9000 | 15.8 / 9.6 / 1.21 | 14.7 / 8.1 / 1.26 | 15.8 / 9.5 / 1.21 | 14.7 / 8.1 / 1.26 |
| 5207, X-T5 | 24.0 / 12.5 / 1.56 | 26.5 / 11.9 / 1.76 | 24.2 / 12.4 / 1.57 | 26.3 / 11.9 / 1.75 |
| 5219, CoolScan 9000 | 20.9 / 15.0 / 1.14 | 32.0 / 14.4 / 1.46 | 20.9 / 15.0 / 1.14 | 32.3 / 14.5 / 1.46 |
| Portra 400, X-T5 | 21.6 / 14.6 / 1.22 | 13.3 / 7.1 / 1.12 | 21.7 / 14.8 / 1.23 | 13.5 / 6.9 / 1.13 |

Median C* of the colour patches from -2 to +2 stops:

| Set | Real scan | Curves only | Curves + matrix |
| --- | --- | --- | --- |
| 5207, CoolScan 9000 | 55.6, 61.3, 51.4, 37.1, 27.5 | 39.6, 49.8, 61.8, 53.1, 44.0 | 41.1, 51.6, 60.3, 65.2, 43.4 |
| 5219, CoolScan 9000 | 56.4, 57.3, 49.6, 37.2, 30.5 | 41.3, 52.3, 54.9, 49.9, 41.8 | 45.6, 57.4, 66.6, 55.1, 33.8 |
| Portra 400, X-T5 | 36.5, 43.8, 44.2, 35.2, 25.9 | 31.9, 40.4, 51.1, 61.2, 53.0 | 33.8, 42.4, 53.3, 58.9, 53.0 |

Reading:
- The straight line gives the same values as the curves within 0.3, and the sheets look the same apart from slightly deeper shadows. These
  negatives are straight over the range of a chart and of most photos, so keeping the toe and the shoulder changes little.
- The matrix does not move the result toward the real scans in a consistent way: nearer on Portra 400, about the same on 5207 CoolScan,
  further on 5207 X-T5 and on 5219. The real scans keep a colour of the film that a chart calibration takes away.
- The largest difference to all four real sets is the bracket: the real scans keep or raise chroma when underexposed and lose it when
  overexposed; these variants peak at 0 to +1 stop and keep high chroma at +2, because the display clips with no tone curve. The neutrals of
  the real scans also compress toward white (White L* 81 to 91 over 4 stops on 5207); here White and Neutral 8 reach L* 100 from offset 0. This points to the output curve of the scanner
  program, a curve per channel, and not to the calibration of the inversion. The direct inversion of P3 section 10.2 has such a curve.

## 6. Third round: an output curve per channel (U87)

The user asked to continue with the output curve. The inversion is the straight line of the grey scale (stock data, no frame statistic), with
no matrix. Two output curves, both with values set before the comparison (rules in `chart_scan.py`):
- `scan_channel_curve`: each channel of e shown as the same display channel, through the curve of P3 rule `direct_inversion` (t = 0.22,
  n = 1.6) in linear display light, then sRGB. With the grey scale of this step in place of the balance-light ramp of P3, this is the P3 path.
- `scan_log_curve`: the same channel mapping with a logistic in stops on the display code, equal to a digital grey at the grey.

`compare_lab_scans.py`, Delta E*ab median / hue difference median / chroma ratio median at offset 0:

| Set | Straight line, clip | Channel curve | Log curve |
| --- | --- | --- | --- |
| 5207, CoolScan 9000 | 15.8 / 9.5 / 1.21 | 8.3 / 4.4 / 0.88 | 18.8 / 5.5 / 0.65 |
| 5207, X-T5 | 24.2 / 12.4 / 1.57 | 11.0 / 9.5 / 1.13 | 10.2 / 9.2 / 0.86 |
| 5219, CoolScan 9000 | 20.9 / 15.0 / 1.14 | 19.0 / 17.0 / 0.84 | 22.2 / 15.1 / 0.64 |
| Portra 400, X-T5 | 21.7 / 14.8 / 1.23 | 10.6 / 5.6 / 0.96 | 14.7 / 8.6 / 0.76 |

Median C* from -2 to +2 stops:

| Set | Real scan | Channel curve |
| --- | --- | --- |
| 5207, CoolScan 9000 | 55.6, 61.3, 51.4, 37.1, 27.5 | 35.9, 44.4, 40.4, 33.7, 19.0 |
| 5219, CoolScan 9000 | 56.4, 57.3, 49.6, 37.2, 30.5 | 35.9, 41.8, 39.0, 28.7, 16.4 |
| Portra 400, X-T5 | 36.5, 43.8, 44.2, 35.2, 25.9 | 32.4, 43.0, 48.2, 40.2, 31.2 |

L* of the neutrals White to Black at offset 0, after the shift to the Neutral 5 of the scan: 5207 CoolScan real 88.2, 84.3, 78.4, 66.1,
45.5, 24.7, channel curve 94.8, 90.3, 82.1, 66.1, 43.9, 19.9; Portra 400 real 88.8, 81.4, 70.7, 52.2, 27.8, 9.4, channel curve 89.7, 82.3,
70.7, 52.2, 31.8, 12.0.

Reading:
- The output curve per channel removes about half of the difference to the real scans on three of four sets, and gives the direction of the
  bracket: chroma falls with overexposure and peaks at -1 or 0. On 5207 and 5219 the level stays lower than the CoolScan on the
  underexposed side, as in P3. The log curve is too flat in chroma.
- 5219 under daylight keeps its blue cast through the whole scale (b* -5.8 to -29.0 on the neutrals), while the real scan has a crossover
  from +6.5 in white to -35.9 in black. The cause stays open, as in P3.
- The tone of the neutrals of the channel curve is near the real scans without any value taken from them.
- Sheets `build/tmp/p10/review3/<stock>.jpg` (local): digital, straight line with clip, channel curve, log curve. Author's view, not a user
  review: the channel curve rolls off the highlights with no clip, the skies are less cyan than with the clip, and the shadows are deeper;
  the log curve looks flat and faded.

## 7. Fourth round: the colour of the log curve (U87)

The user accepts the tone of the log curve and asks to solve its colour by any means that cost no render time. Film Analyzer stays a test
only (U28): every option below has its value fixed before the comparison, and none is fitted to the scans. Options are stated in
`chart_scan.py`; all are a table built once or one 3 x 3 product, so the render time does not change.

`compare_lab_scans.py`, Delta E*ab median / hue difference median / chroma ratio median at offset 0, log curve:

| Variant | 5207 CoolScan | 5207 X-T5 | 5219 CoolScan | Portra 400 X-T5 |
| --- | --- | --- | --- | --- |
| APD (round 3) | 18.8 / 5.5 / 0.65 | 10.2 / 9.2 / 0.86 | 22.2 / 15.1 / 0.64 | 14.7 / 8.6 / 0.76 |
| Frontier light | 21.8 / 4.8 / 0.59 | 10.0 / 8.3 / 0.79 | 26.7 / 17.0 / 0.54 | 16.0 / 7.6 / 0.69 |
| Status M | 18.3 / 6.1 / 0.65 | 10.0 / 9.9 / 0.86 | 22.7 / 14.4 / 0.63 | 14.1 / 7.8 / 0.77 |
| analytical | 11.5 / 6.8 / 0.80 | 11.6 / 9.7 / 1.01 | 16.3 / 16.2 / 0.81 | 13.0 / 8.6 / 0.83 |
| APD + CDD_TO_CID | 25.2 / 9.8 / 0.49 | 14.9 / 11.4 / 0.64 | 25.3 / 14.5 / 0.54 | 21.3 / 11.9 / 0.60 |
| APD, common slope | 18.5 / 9.0 / 0.66 | 11.3 / 14.4 / 0.85 | 20.3 / 19.6 / 0.63 | 14.3 / 7.3 / 0.76 |
| APD, sensitivity matrix | 10.1 / 6.2 / 0.77 | 10.9 / 10.0 / 1.06 | 21.2 / 15.6 / 0.74 | 9.9 / 7.9 / 0.98 |
| APD, sensitivity matrix, scan timing 1 | 10.1 / 6.2 / 0.77 | 10.9 / 10.0 / 1.06 | **15.8 / 9.8 / 0.87** | 9.9 / 7.9 / 0.98 |
| analytical, sensitivity matrix | 8.3 / 7.0 / 0.97 | 17.8 / 9.9 / 1.27 | 16.5 / 16.3 / 1.02 | 12.7 / 6.8 / 1.06 |

For scale: the two real scanners on the same 5207 roll differ by Delta E 12.2 median, hue 7.7 degrees (P3 section 10.3).

Reading:
- The scanner light is not the cause: Frontier and Status M give the same or less chroma than APD, and CDD_TO_CID mixes the channels and
  lowers chroma further. Only the analytical limit adds chroma.
- Rule `film_sensitivity_matrix` gives most of the gain. The cause of the faded colour of round 3 was that the film channels were shown as
  Rec. 709 primaries; the published sensitivities of the layers give them their primaries, and the development stays as it is. The matrix is
  near the chart matrix of round 1 (5207 red row 0.61, 0.48, -0.09), which shows that most of that matrix was the primaries; the difference
  is that this one is fitted on layer exposures, so it does not undo the development.
- Rule `scan_timing` with share 1, as `print_timing` of the print, takes the daylight cast of 5219 back to neutral and lowers its error.
  The daylight stocks do not change, because their calibration light is their scene light.
- One slope for the three channels (rule `scan_common_slope`) gives a crossover of +3.3 to -2.8 b* on 5219 against +6.5 to -35.9 in the
  real scan, and moves hue the wrong way on other sets. Not adopted. The strong blue of the real 5219 shadows stays open.
- Input path (`--spectral`, `lab_scan_compare_spectral.json`): the BabelColor spectra straight to the film give errors of the same size
  (Portra 9.9 / 7.9 to 10.6 / 5.8; 5207 CoolScan 10.1 / 6.2 to 11.9 / 7.1), so the reconstruction of AP1 is not the main rest. What stays
  in all sets is Bluish Green and Cyan greener than the scans (hue -13 to -32 and -7 to -21 degrees).
- The selected form: APD, straight line of the grey scale, sensitivity matrix, scan timing equal to print_timing, log curve on the Rec. 709
  channels. Its Delta E is below the 12.2 between the two real scanners on three of four sets; its hue difference is below 7.7 degrees
  on one set.
- Sheets `build/tmp/p10/review4/<stock>.jpg` (local): digital, log curve of round 3, the selected form. Author's view, not a user review:
  the selected form keeps the flat tone of the log curve, with deeper blue skies and fuller greens and reds than round 3. The sheets use the
  reference scene light, so scan timing does not act there.

## 8. Other photos, and a blue-violet lamp (U87)

The user asked for other photos (`render_chart_scan_review.py --more`, nine other sample files, sheets `build/tmp/p10/review4_more/`).
One fault showed: on `artificial_lights/3754960364.dng` the lamp of the carousel turned hard blue with the sensitivity matrix.
Trace (`build/tmp/p10/magenta_probe2.py`, local): the lamp is blue-violet in the input (linear Rec. 709 1.15, 0.02, 3.62); the digital panel
shows magenta only because both red and blue clip. The film reads it as blue (inverted channels 0.95, 1.19, 7.90): a red layer has no
short-wave lobe, so violet goes to blue on film, the known anomalous rendering of violet flowers. The sensitivity matrix has -0.12 of blue in
its red row, so the red channel falls below 0 (-0.26) and shows 0.

Fix: rule `rgc_style_display_compression` of P2 on the linear Rec. 709 channels before the log curve (option display_compress), with the
gamut values of the stock options, as the print display uses. The lamp now shows a light blue-violet. On the chart, Delta E / hue median:
5207 CoolScan 10.1 / 6.2 to 11.5 / 5.1; 5207 X-T5 10.9 / 10.0 to 9.3 / 8.1; 5219 15.8 / 9.8 to 11.8 / 9.1; Portra 9.9 / 7.9 to 11.2 / 6.0.
The hue difference falls on all four sets. Other photos barely change.

The selected form is now: APD, straight line of the grey scale, sensitivity matrix, scan timing equal to print_timing, the display
compression, and the log curve on the Rec. 709 channels. Its cost at run time: the APD table at load, one 3 x 3 product (the sensitivity
matrix and AP1 to Rec. 709 combine), the compression, and one curve per channel.

## 9. Method `chart_scan` of the Python viewer (U88)

The user asked for the selected form in the Python viewer, to test on more photos. `mvp_pipeline.py` has the method `chart_scan`:
`ChartScanPreview` with `SELECTED_FORM` of `chart_scan.py`, scan timing from option print_timing, and the new control Scan exposure (rule
`scan_exposure`, -3 to +3 stops, a neutral scale before the display steps). The negative controls act; the print controls do not. The window
lists it as "Scan, chart calibrated (log curve)", with its own group "Chart scan"; `p6_mvp_cli.py` takes `--method chart_scan`.

Checks (local, `build/tmp/p10/all_negatives_check.py`): all 30 negatives of the catalog build the method and give a finite output in 0 to 1 on
a neutral ramp of -8 to +8 stops and a colour sweep; green does not fall by more than 1e-4 along the ramp; the largest channel spread of the
ramp between -6 and +6 stops is 0.069 code (kodak_5219), 0.007 to 0.056 on the others. A RAW file through the command line takes 2.3 s at 2048
pixels on the CPU, the same order as the other methods. The offscreen window starts and switches the groups; its exit code 127 after the
window closes is the same with the file of HEAD.


## 10. Status M in place of APD, for the port (U88)

The user accepts the look and asks for the port to Alcedo Studio as a new print method. The APD responsivities are the elements of SMPTE
ST 2065-2; the sources of P3 state that the tables must not be committed, so they cannot ship in the resources. Status M (the ANSI tables of
python-colormath, BSD-3-Clause, already used by P0) is the densitometry for colour negatives. The same comparison with Status M in the
selected form (`compare_lab_scans.py`, Delta E / hue median): 5207 CoolScan 11.5 / 5.1 to 11.0 / 5.3; 5207 X-T5 9.3 / 8.1 to 9.1 / 8.1;
5219 11.8 / 9.1 to 12.7 / 8.3; Portra 400 11.2 / 6.0 to 10.8 / 6.2. The difference is below 1 Delta E, so `SELECTED_FORM` and the viewer use
Status M. The sensitivity matrix, the grey scale, and the timing are computed with the Status M reading, as for APD.

Check of all 30 negatives again: all finite, in 0 to 1. The largest fall of a ramp channel is 0.00012 code (kodak_portra_400, green, at +6.4
stops), under the limit 0.002 of `check_p6_mvp.py`; on the same stock the print falls 0.00007 and the APD method 0.00039.

## 11. Resources of the port

For [Alcedo Studio issue 661](https://github.com/zidage/AlcedoStudio/issues/661). Scripts of step P7, changed in lab commit `9bb4284`; record:
[`product_resources.json`](../../results/p7_spectral_acceleration/product_resources.json), key `scan`.

- Schema version 7. `film_print_setup.bin` (225568 bytes) has per negative and scene light `scan_slope` (3), `scan_grey` (3), and
  `scan_rec709_matrix` (3, 3). `film_stock_bundle.bin` (3086880 bytes) has `common/scan_status_m_weights` (3, 481, on `common/wavelengths_nm`)
  and `common/scan_log_curve` (s0 0.2581, w 1.6664), and the metadata `lab_scan` (id `lab_scan`, name "Lab Scan"). All three are per scene light,
  because the calibration light is the balance light of the stock, which depends on the scene light.
- The product builds the Status M table on the record nodes of the print table, as the lab does in `ScanPreview._build_table`. The lab ships no
  table (ROADMAP U68).
- The compact reflectance table does not change: its arrays are equal to schema 6, and only the schema version of its header differs, so its
  SHA-256 changes.
- Checks: the stored values of 8 scan selections (4 random, the 4 expected) against `ChartScanPreview` of the viewer, largest difference 0 (limit
  1e-9); the layer gain of each scan model against `layer_gain` of the setup, 0; the formula of issue 661 from the stored values against
  `ChartScanPreview.render`, largest 5.2e-13 of a code on a neutral ramp and 4096 random colours (limit 1e-6). The other checks of step P7 pass
  with no change.
- Expected values under `build/tmp/p7/product_resources/expected/` (not committed), for `kodak_5207`, `kodak_portra_400`, and `kodak_ektar_100`
  under `reference` and `kodak_5219` under `daylight`: `scan__<negative>__<light>.bin` with the Status M table and the stored values;
  `display/scan__*.bin` with the ramp and chart sRGB (the calibration with the default point steps of the inhibition, the render with the two
  steps of the product); `image/scan__*.bin` with the 6000 x 4006 sRGB of `_DSC8148.ARW` (`build_image_expected.py --scan-only`, which checks
  that the AP1 equals `ap1.bin` of the earlier run).

## 12. Sixth round: the stocks look alike (U89)

The user finds that the stocks look alike again on Lab Scan, and asks for the cause from a sweep of hue and lightness, not from photos.

`check_stock_spread.py`: CIELab hues 0 to 345 degrees in 15 degree steps, L* 85 to 25, C* 30, and a neutral ramp of -6 to +6 stops, through the
eight stocks of `ACCEPTED_STOCKS` under `reference`, with no change of the input by the product grade. The spread between stocks is the mean Delta
E*ab of a stock to the mean of the stocks, per patch. Record: [`stock_spread.json`](../../results/p10_chart_scan/stock_spread.json).

| Form | Spread, Delta E | Spread, L* | Hue, std | Chroma ratio, std | Neutral, L* spread | Neutral, C* |
| --- | --- | --- | --- | --- | --- | --- |
| Print on Endura Premier | 3.73 | 1.06 | 7.40 | 0.137 | 0.38 | 2.65 |
| APD method | 3.08 | 1.07 | 5.79 | 0.152 | 0.77 | 2.34 |
| Lab Scan, U88 (slope of the stock) | 2.36 | 0.51 | 3.10 | 0.099 | 0.38 | 1.53 |
| U88, with the mean sensitivity matrix of the eight stocks | 2.51 | 0.72 | 3.82 | 0.090 | 0.38 | 1.52 |
| U88, slopes scaled to one mean, the contrast of each stock kept | 2.97 | 0.86 | 3.34 | 0.123 | 0.98 | 1.55 |
| U88, one slope for all stocks and channels | 3.66 | 0.82 | 5.45 | 0.148 | 0.80 | 3.79 |
| **Lab Scan, U89 (rule `fixed_scan_slope`)** | **3.57** | 0.80 | 5.46 | 0.145 | 0.78 | 2.66 |

Reading:
- The cause is rule `chart_straight_line`: each channel is divided by the slope of the grey scale of its own stock. The Status M slopes differ
  between stocks (5207 0.14 to 0.16 per stop, Ektar 100 and C200 0.17 to 0.20), and with one log curve for all stocks every grey scale gives the
  same tone. This takes away the contrast of the stock (the row "contrast of each stock kept" gives back part of the spread, mostly in chroma and
  L*) and the ratio of the gammas of the three layers (the rest, and most of the hue).
- The sensitivity matrix of each stock is not the cause: the matrices are near each other, and the mean matrix changes the spread from 2.36 to 2.51.
  It pulls each stock toward the digital input by the same amount.
- On U88 each stock is 3.5 to 6.2 Delta E from the digital input through the same display steps.

Rule `fixed_scan_slope` (`chart_scan.py`, option `slope_source = 'fixed'`): one Status M slope per channel for all stocks, `FIXED_STATUS_M_SLOPE` =
0.160868, 0.170611, 0.181802, the mean slope of the eight stocks under `reference` (`fit_fixed_slope.py`, `fixed_slope.json`, largest difference
3.4e-7). The record of the grey of each stock stays, so a grey of the calibration light stays neutral and scan timing acts as before. A stock with
a higher gamma gives more contrast and chroma, and a stock whose layers differ from the fixed ratio keeps its crossover, as a scan with one fixed
setup for all films. The neutral C* of the ramp is 2.66, the same as the print (2.65).

Checks: all 30 negatives of the catalog give a finite output in 0 to 1 on a neutral ramp of -8 to +8 stops and a colour sweep
(`build/tmp/p10/all_negatives_check.py`, local). The largest fall of the green channel of the ramp is 0.0003 code on Portra 400 and 0.00017 on Portra
800, at the shoulder, under the limit 0.002 of `check_p6_mvp.py` (0.00012 on U88). The largest channel spread of the ramp between -6 and +6 stops
is 0.085 code (kodak_5247).

The user reviewed the form in the Python viewer and accepts it. Method `chart_scan` uses it by default; setting `chart_scan_slope = 'stock'` keeps
U88. The resources of schema 7 hold it (section 13).

## 13. Resources with the fixed slope (U89)

For [Alcedo Studio issue 661](https://github.com/zidage/AlcedoStudio/issues/661). The scripts of section 11 at lab commit `10c159b`, run with a
clean tree; record: [`product_resources.json`](../../results/p7_spectral_acceleration/product_resources.json).

- Schema version 7, the same layout as section 11. Only `film_print_setup.bin` changes (SHA-256 `97302a27...`): `scan_slope` holds
  `FIXED_STATUS_M_SLOPE` for every negative and scene light. `scan_grey` and `scan_rec709_matrix` do not change, because the grey and the matrix do
  not read the slope. `film_stock_bundle.bin` and `film_reflectance_table.bin` are the same bytes as in section 11.
- No product build read the resources of section 11: Lab Scan was not in a product branch at that time.
- Checks, with the limits of section 11: the stored values of the 8 scan selections against `ChartScanPreview`, 0; the formula of issue 661
  against `ChartScanPreview.render`, largest 4.7e-13 of a code. The other checks of step P7 pass with no change.
- Expected values under `build/tmp/p7/product_resources/expected/` (not committed), the same four selections as section 11: `scan__*.bin`,
  `display/scan__*.bin`, and `image/scan__*.bin` (`build_image_expected.py _DSC8148.ARW --scan-only`; the AP1 equals `ap1.bin`).

## 14. Seventh round: the light of the frame, the black, and the blue (U90)

The user tested Lab Scan of U89 on more photos and finds that the colour of 5219 and 5207 does not come out; the cause that the user names is
that the spectral inversion runs on a white-balanced image. Film Analyzer values are a test only (U28): the records below hold the values of the
paths and their differences to the scans. Probes and sheets are local (`build/tmp/p10/u90_*.py`, `build/tmp/p10/review_u90*/`); the night photos
are the user's own files, not committed.

Findings, in the order of the round:
- With scene light `reference`, a stock is lit by its balance light and calibrated under the same light, so a stock never sees a light that
  it is not balanced for: the camera white balance took the cast of the real light away before the film. Scene light `as_shot` (P4 rule
  `light_from_raw_white`: camera white balance and camera matrix of the RAW file, McCamy CCT, CIE daylight from 4000 K, Planckian below) puts
  the light of the frame back. The user white balance stays a creative cast on the reflectance, so nothing counts twice.
- Scan timing is the lever of the cast that stays (rule `scan_timing`). On the 5219 Film Analyzer set under daylight, U89 form: timing 1, Delta E
  13.5, hue 13.0 degrees; 0.75: 11.4 and 8.4; 0.5: 12.5 and 8.4. The real scan does not take the daylight cast of 5219 away in full; a printer
  corrects a frame in part for the same reason (subject failure). Photos at 6700 to 7800 K turn too blue at 0.5. Selected: 0.75.
- Black (rule `scan_base_black`): the straight line of U88 and U89 floors at the film base, near -4.4 to -4.8 stops for e, so the black of the log
  curve stays at 11 to 15 of 255 on a ramp (the user: the shadows do not sink). With the black at the base, the ramp reaches 0 and is darker than
  the digital input from -5 stops; on photos the darkest 1 % goes from 14 to 1. Under daylight the base of 5219 gives e0 = 0.0135, 0.0064, 0.0050
  (red, green, blue), so its shadows turn cool. The image-plane steps do not change the dark percentiles by more than 1 code. Strength 1.5 crisps
  the image and 2 clips black clothes; selected: 1. On the Film Analyzer chart the black has no effect, because the darkest patch stays far from
  the base.
- Blue: against the chart reference, the real scans of 5219 raise the chroma of Blue, Blue Sky, Purplish Blue, and Purple far more than of the
  other patches. U89 reaches 0.64, 0.70, 0.72, and 0.62 of the real chroma of these patches; the hue is toward cyan by 9 to 27 degrees, and 5207
  shows the same, so it is the scan form and not the stock.
  - Rule `scan_matrix_domain` (option `matrix_domain`): `code`, the curve per film channel first and then the matrix on the codes, as a scan
    program curves its scanner channels and a profile acts on the encoded scan. Median hue error against the scans: 5219 8.1 to 4.8 degrees,
    5207 CoolScan 8.4 to 4.9, Portra 6.0 to 4.3; the chroma of the blues does not change. `log` (the matrix on the stops) is near `code` and
    slightly worse.
  - Rule `dye_reading_density_contrast` (option `slope_source = 'density'`, scanner `analytical`): the scanner reads the dye amounts. The
    integral mask of a colour negative is made to cancel the unwanted absorptions of the dyes, so a masked negative read after the mask is near
    its dye amounts; Status M reads them with the crosstalk. The contrast stays that of rule `fixed_scan_slope` in Status M density, so the tone
    of each stock is that of U89. On 5219 the chroma of the four blue patches goes to 0.84, 0.96, 0.98, and 0.94 of the real scan.
- Film Analyzer, with as-shot daylight, timing 0.75, black at the base, and `matrix_domain = 'code'` (median of the colour patches):

| Set | Status M reading, Delta E / hue | Dye reading, Delta E / hue |
| --- | --- | --- |
| 5207, CoolScan 9000 | 12.3 / 4.9 | 6.2 / 2.6 |
| 5207, X-T5 | 8.5 / 10.8 | 15.1 / 8.0 |
| 5219, CoolScan 9000 | 10.1 / 4.8 | 8.6 / 3.8 |
| Portra 400, X-T5 | 9.3 / 4.3 | 14.0 / 8.7 |

  The two sets of the dedicated scanner move toward the scans; the two sets scanned with a camera move away. A camera scan keeps more of the
  crosstalk of the dyes. The target of Lab Scan is a lab scanner, so the dye reading is selected; this is the author's reading of the table,
  for the user to confirm.
- Rejected: one mean dye slope for all stocks (the dye amounts per stop of the cine stocks are near 0.155 and of the consumer stocks near 0.2,
  so one value flattens 5207 and 5219); the mean sensitivity matrix of the eight stocks (no gain of chroma); the Frontier band estimate and APD
  with the stock slope (less chroma than the dye reading).
- Photos (`build/tmp/p10/review_u90_final/`, U89 against U90): 5219 under daylight gives a deeper blue sky with warm lights and clean black; the
  blue-violet lamp of `artificial_lights/3754960364.dng` turns violet in place of the hard blue of U89; 5219 turns foliage under daylight to a
  strong teal, which the user should judge.
- All 30 negatives of the catalog give a finite output in 0 to 1 on a ramp of -8 to +8 stops and a colour sweep; the largest fall of the green
  channel is 0.00023 code (Portra 400), under the limit 0.002 of `check_p6_mvp.py`.

The viewer (method `chart_scan`): scene light `as_shot`, settings `chart_scan_reading` (`dye`, default; `status_m`) and `chart_scan_matrix`
(`code`, default; `linear`), and controls `chart_scan_timing` (0.75) and `chart_scan_black` (1). The scan timing of this method is no longer
`print_timing`. A RAW file with no camera matrix stops with an error for `as_shot`. `SELECTED_FORM` and the resources of schema 7 are those of
U89 until the user accepts this form.

Cost in the product: none per pixel. The dye reading removes the Status M table, because the record of FP5 is already the dye amounts; the
black is one subtraction per channel; the order of the matrix and the curve does not change the count of operations. The as-shot light needs
the camera white of the RAW file in the film print module and scene lights on a grid of colour temperature in place of the five named lights.

## 15. Eighth round: a wide gamut and a display rendering transform (U91)

The user finds that the colour of the step to Rec. 709 is not right and asks to take the scan to a wide gamut and to try OpenDRT, ACES 2.0,
Cineon, and AgX, from public OCIO configs. `scripts/poc/p10_chart_scan/display_transforms.py`: views ACES 2.0 and AgX of the Blender colour
management config, OpenDRT 1.0.0 of OpenDRT-OCIO-Config (Chris Brejon; OpenDRT of Jed Smith, GPL-3.0), and the Kodak Cineon conversion, on the
linear AP1 of the sensitivity matrix, each with an exposure that shows the grey at the code of the log curve (ACES 2.0 +0.78 stops, OpenDRT
+0.56, Cineon +0.25, AgX 0). The configs are downloaded by `fetch()` into `build/tmp/p10/drt/` and not committed. Option `display_transform`
of `ChartScanPreview`, setting `chart_scan_display` of the viewer.

Reading (sheets `build/tmp/p10/review_u91_drt/`): the colour of a stock (the blue sky and the teal foliage of 5219) is the same under every
transform, so it comes from the scan before the display. ACES 2.0 and OpenDRT give much deeper shadows; AgX has the tone nearest the log
curve; the blue-violet lamp shows violet only with the curve before the matrix.

## 16. Ninth round: the ADX scan (U92)

The user found the most convincing form in the viewer: method `apd` (the scan of P3) with the LAD aim off, ACES 2.0, and scene light
`as_shot`, and asks why it works and how AgX and OpenDRT compare after the ADX to ACES step. The form: the negative read in printing density
(APD, ST 2065-2), ADX10 code values on the base of the film (ST 2065-3), no offset (LAD aim off), the Academy ADX10 to ACES transform (a
channel unmixing matrix, one fixed curve of an average negative, one matrix to ACES; no parameter of the stock), and the ACES 2.0 output.

Why (probes `build/tmp/p10/u92_*.py`, sheets `build/tmp/p10/review_u92_adx/`):
- Tone. On a neutral ramp the green code is 1, 5, 20, 107, 227 at -5, -4, -3, 0, +4 stops (5207), against 6, 12, 26, 118, 232 for the log
  curve of U90 and 17, 27, 41, 118, 255 for the digital input: the shadows reach black, as the user asked in U90.
- Balance. With the LAD aim off, the scan sits on the film base and no grey is balanced, as an untimed scan. The 18 % grey of 5219 under D55
  is at ADX10 415, 484, 533 against the aim 445, so the grey shows a* -9, b* -11; the Film Analyzer scan of 5219 has a* -8, b* -13 at Neutral 5
  (Lab Scan of U90: a* -2, b* -7). The cine stocks sit near the aim; a consumer stock does not (Portra 400 under D55: a* +16, b* -11), which is
  why the user keeps the LAD aim as an option for strong casts.
- Colour. The transform is the same for all stocks and is not fitted to a chart, and ACES 2.0 compresses chroma, so the colour is muted. On
  the Film Analyzer charts this form is far from the scans: Delta E 19 to 31 (U90: 6 to 15), chroma 0.46 to 0.6 of the CoolScan scans, hue 14 to
  25 degrees. The match the user sees is of tone, cast, and saturation on photos, not of the chart.
- Reading. The Kodak 2383 printing density (the printer lamp times the published sensitivity of the paper, `w_printing` of the model) in place
  of APD gives the same result within 1 to 2 Delta E on the four sets. APD is defined as such a printing density, and the 2383 data already
  ship with the product, so the SMPTE tables are not needed. Option `reading = 'print2383'` of `aces_scan.ScanPreview`.
- Display after the ADX to ACES step (AgX and OpenDRT at the grey code of ACES 2.0): OpenDRT is near ACES 2.0 (the same toe, highlights 230
  against 227 at +4 stops, the same cast and chroma); AgX has a softer toe (code 7 at -5 stops), a flatter tone, and less chroma. With no
  exposure change (option `drt_grey = 'native'`), ACES 0.18 shows at code 0.368 on OpenDRT, 0.461 on AgX, and 0.349 on ACES 2.0.

The viewer, method `apd`: outputs `agx` and `opendrt`, setting `apd_reading` (`apd`, `print2383`), and setting `apd_drt_grey` (`aces20`,
`native`). Scene light `as_shot` acts for every method.

The user accepts this form for the product (2026-11-04): Lab Scan of Alcedo Studio issue 661 is redone as this ADX scan with the 2383
printing density, the LAD aim off by default, scene light as shot by default (linked to the colour temperature of the RAW decode, reference
for an input that is not RAW), and OpenDRT with all its settings. The chart-calibrated form of sections 1 to 14 stays in the lab as method
`chart_scan`; the resources of schema 7 (section 13) are replaced in the next schema.
