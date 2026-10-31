# Modern film workflow: how a scanned negative gets a film look

**Date:** 2026-10-30.
**Use:** input to step P3 of the [README route](../../README.md#8-route-from-poc-to-mvp) (decision U23).
**Status:** source audit. The ADX to ACES path ran in the [P3 report](../exploration/p3_scan_and_scene.md), and the user dropped it (README U26). This lab did not measure a scanner. Section 11 of that report lists the classic scanner data.

## 1. Summary

- **A scan alone does not look like film on a display.** A scan of a negative is a flat, low-contrast
  log image. The look comes from what is applied after the scan.
- **The main step is the display preparation.** Practice usually applies a show LUT or a print film emulation
  (PFE), with a separate grade. So a production that has no film print can still use a print model.
- **The ACES ADX path has a different aim.** The ADX to ACES transform is universal: it removes a generic negative
  response, and then the ACES output transform renders the image. It does not contain a print stock.
- **Consequence for P3:** the requested path (scan, ADX, ACES output) can show a look that is different from the
  2383 path, and it can show less film character. P3 must compare it with a second path: scan, ADX, print model.
- **Evidence quality.** Yedlin and the ACES sources are direct. The statements on general practice come from
  colorist forums, vendor pages, and one facility blog. This audit found no survey of current productions.

## 2. What practice says

| Statement | Source | Quality |
| --- | --- | --- |
| A DPX log scan of a negative looks nothing like the final film. A PFE LUT simulates the negative and the print. | [What's After the Movie: archival LUT](https://www.whatsafterthemovie.com/wiki/term/archival-lut) | Glossary, secondary |
| "The substantial part of the perceptual look comes from the mathematical preparation of the image for display." | [S. Yedlin, On Color Science](https://www.yedlin.net/NerdyFilmTechStuff/OnColorScience/) | Direct, one author's position |
| Tone is not sufficient: a color response model is also necessary. Yedlin cites measured 5219 data. Grain, halation, and gate weave are separate attributes. | Same | Direct |
| A demonstration alternates film and digital footage, both with custom display preparation, and does not state which is which. | [ASC: display prep demo](https://theasc.com/news/yedlin-releases-display-prep-demo) | Direct |
| A PFE treats the image as if it was printed onto a stock. Some LUTs expect a Cineon curve as input. Accurate public print data is rare. | [Lowepost: PFE workflow](https://lowepost.com/insider/insights/print-film-emulation-workflow-r76/) (the full article is paid; this audit read the public part and search extracts) | Practitioner |
| A facility creates a show LUT, and it also makes dailies film prints and print screenings on a film production. | [FotoKem blog](https://fotokem.com/blog/) | Facility, no technical values |

Not all film-look traits come from the display preparation. Grain, halation, and gate weave are in the real negative and
the real transport. Alcedo Studio keeps its own grain (README). Halation is an approximate control of P2. Gate weave
is not in this lab.

## 3. The ACES and ADX facts

- **Standards.** APD is in [SMPTE ST 2065-2](https://pub.smpte.org/doc/2065/). Its responsivities come from print stock
  sensitivities and a printer lamp. ADX is in [SMPTE ST 2065-3](https://pub.smpte.org/doc/st2065-3/20200909-pub/st2065-3-2020.pdf).
- **The transform.** [`ACEScsc.Academy.ADX10_to_ACES.ctl`](https://github.com/ampas/aces-dev/blob/v1.3.1/transforms/ctl/csc/ADX/ACEScsc.Academy.ADX10_to_ACES.ctl)
  has the name "Universal ADX10 to ACES Transform". This lab read the code:
  1. channel dependent density = (ADX10 - 95) / 500. The encoding of ST 2065-3 has a scale of 1.00, 0.92, 0.95 per channel, and this step does not remove it;
  2. a 3x3 matrix to channel independent density;
  3. a table, and above density 0.6 a straight line with a slope of 100 / 55, to log exposure;
  4. power of 10, and a 3x3 matrix to ACES.

  It has no film stock parameter. Inference, not measured: a stock that differs from the generic response keeps that
  difference as a color and tone offset, and other character of the negative is partly removed.
- **Low values.** A thread reports a clip of values below D-min, near code value 95
  ([ACESCentral](https://community.acescentral.com/t/setting-up-a-scanner-for-adx-encoding/3434)).
- **ADX16 and ADX10.** ADX16 has a density range near 8, and ADX10 near 2. A scan with the ADX10 range in a 16-bit file
  appears wrong with the ADX16 transform ([ACESCentral](https://community.acescentral.com/t/film-scans-setup-with-aces-workflow/1341)).
  P3 starts with ADX10, because it is the range of the transform above. A thread says that few negative stocks exceed
  this range. This lab did not measure this for its stocks, so P3 must count the values outside the range.
- **Licenses.** `ampas/aces-dev` and `ampas/aces-output` report Apache-2.0 on their default branches. At the tag v1.3.1, `LICENSE.md` of aces-dev
  is the A.M.P.A.S. license (checked in P3). Its notice is in [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

## 4. Scanners

| Item | Finding | Use in P3 |
| --- | --- | --- |
| ARRILASER | A laser film [recorder](https://digitalproduction.com/2010/01/18/arri-freut-sich-ueber-den-16-technischen-oscar/): digital to film. Not a scanner. | None |
| ARRISCAN XT | [ARRI data sheet](https://www.Arri.com/resource/blob/42554/d0edb98ccb56fcd9b2ba261ac6459722/arriscan-xt-leaflet-data.pdf): **monochrome** custom ALEXA XT dual-gain CMOS sensor, 16-bit linear output, or a log conversion to the Kodak Cineon standard. This audit found no published lamp spectrum or spectral response. | Name only |
| Blackmagic Cintel | No technical data found. A thread says that it likely does not capture APD directly, and that calibration needs measured film patches ([ACESCentral](https://community.acescentral.com/t/setting-up-a-scanner-for-adx-encoding/3434)). | None |
| ALEV III curves of [Yellowmoon](https://github.com/ngriaznov/yellowmoon) (Apache-2.0, user reference) | `data/alexa/alexa_alev3_estimate_380_780_5.json`. Its notice says: "It is an estimate, not a measurement", fitted to ARRI matrices with a prior from rawtoaces-data. | See below |

**Limit of the ALEV III estimate.** The estimate is an RGB camera response with a color filter array. The ARRISCAN XT sensor
is monochrome, so the color records of that scanner come from its light sources and the sensor, and those data are not
public in this audit. Thus the estimate does not describe the ARRISCAN. It can describe a different case: a
digital ALEXA that photographs a negative on a light table. That is a possible later comparison, labeled as an
estimate.

**Decision for P3 (user, 2026-10-30): ADX first.** Use the published APD responsivities as an ideal scanner. A result of this
kind represents the standard, not a specific machine.

## 5. Ideas from Yellowmoon for the scene choice

Yellowmoon uses light classes (daylight, tungsten, fluorescent, LED) with probabilities from a learned estimate, and it
blends tables by class. It also has manual presets, from its
[pipeline document](https://github.com/ngriaznov/yellowmoon/blob/main/docs/02-colour-pipeline.md). This agrees with U22:
a scene can be a weighted mixture of classes. Its sensor map is a 3x3 matrix per light; this lab does not adopt that
for the film input (README, P1 route). Its own report states that most of its fit lights miss its limits.

## 5a. Direct scanning without a print

The user reports that a developed negative is now usually scanned directly, with no print. [Film Analyzer](https://filmanalyzer.talkativephotographer.com/browse/kodak-5207-vision3-250d) shows the result on a chart per film and per scanner. The comparison is in the [P3 report, section 10](../exploration/p3_scan_and_scene.md#10-direct-scanning-real-measurements-and-a-direct-inversion-path).

## 6. Plan for P3

1. Negative of P2 (spectral density), then APD responsivities, then APD, then ADX10.
2. **Path A (requested):** ADX10, the ACES transform, ACES 1.3 and 2.0 output transforms.
3. **Path B (comparison):** ADX10 or the same negative, then the 2383 print model of P2.
4. Review on the portraits, the night files, and 5207 and 5219. Report how much difference between the stocks each path keeps.

The APD responsivities come from ST 2065-2, and they equal the table of spectral_film_lut after normalization. Status: see the [P3 report](../exploration/p3_scan_and_scene.md).
