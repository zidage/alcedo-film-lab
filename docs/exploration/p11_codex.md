# P11: colour formation in the print chain and print viewing

Date: 2026-11-04. Status: research candidate implemented, measured and rendered;
user review open. No product change. Work is confined to P11.

## Question

Does the reflection-print viewing step account for excessive colourfulness, and
which physical stage amplifies colour separation? This study is separate from
the real 5207/X5 comparison. It uses no scan of real film and no rejected method.

## Result summary

The print output lacks a colour appearance transfer between a print and a
monitor. Adding it is physically meaningful when the viewing conditions are
specified. It is not a general solution for the current look. At 100 lux it
reduces M' ratios by about 4 to 12 percent on these photos, with darker midtones.
At 500 or 2000 lux it can increase colourfulness. Stock separation stays small.
The candidate is not recommended as a default correction.

The paper characteristic response is a strong amplification stage. At grey the
Endura Premier curve slopes are 3.103, 3.201 and 3.363 to 3.433 density units per
log10 exposure. These are calculations from the current profile, not a new
measurement of paper. The derivative result identifies where separation grows;
it does not prove that the paper curves are wrong or justify reducing them.

## Inputs and sources

- Current shared checkout: P6 pipeline, P2 film model, P3 scan, P10 generic scan
  and CAM16. Exact source hashes are in `build/tmp/p11/provenance.json`.
- Existing profiles and spectral data, with their existing provenance. No new
  dye curve, interlayer coefficient, scanner table or stock fit is added.
- Six Kodak photo stocks: Portra 160, 400, 800, Ektar 100, Gold 200 and Ultramax
  400; also 5207. The four image stocks are Portra 400, Ektar 100, Gold 200, 5207.
- Five RAW files: dune `se357.cr2`, day `se222.arw`, night street
  `5253219691.rw2`, portraits `se188.nef` and `se274.dng`. Absolute source paths
  and as-shot light are in `measurements.json`. Photos remain local.
- [CIE 248:2022 abstract](https://www.cie.co.at/publications/cie-2016-colour-appearance-model-colour-management-systems-ciecam16),
  read now: CAM16 is intended for related colours in prints and self-luminous
  displays, with viewing-specific forward and inverse appearance calculations.
  The full standard was not obtained. No claim of complete standard compliance.
- [Colour CAM16 API and example](https://colour.readthedocs.io/en/develop/generated/colour.XYZ_to_CAM16.html),
  read now: viewing inputs and example values. The existing lab implementation
  has its own known-value check and inverse check. No external code was copied.

The CIE publication web page was saved locally. Direct retrieval of the Colour
API page failed with HTTP 403; that page was read through web.open. Provenance
records URL, date, edition, licensing and SHA-256 of each local artifact: the
CIE web page and the Colour retrieval note. The note hash is not a hash of the
Colour source document. No full CIE standard, manufacturer document or external
dataset was downloaded. New P11 code is GPL-3.0-only; existing profiles retain
their notices. CIE text is copyrighted; Colour uses BSD-3-Clause. Sources stay local.

## Physical audit and candidate

The current chain already models spectral scene recovery, layer exposure,
development, negative transmission, printer illumination, paper exposure,
paper characteristic curves and a dye-density reconstruction. Its viewed XYZ is
the integral of 10^(-D(lambda)) times viewing light and CIE observer weights.
Paper Status A density and negative Status M density remain instrument readings.
No extra factor of two is applied for reflection: the paper density basis is an
effective reflection-density model. Adding a second optical pass without new
data would not follow from these profiles.

The print then uses Bradford adaptation, display primaries, the existing gamut
operation and encoding. It does not specify adapting luminance or surround.
Its surface-reflection parameter exists but is zero by default. There is no
measurement here to justify increasing it. This study adds no flare.

Candidate: CAM16 corresponding colours, preserving J, M and h. Source white is
the perfect diffuser under the model viewing light, not the paper white or a
neutral of a stock. Thus stock and paper casts remain part of the stimulus.
For a Lambertian diffuser, white luminance Lw = E/pi cd/m2. Three explicit
illuminance scenarios are E = 100, 500, 2000 lux. Adapting luminance is 0.2 Lw
(6.366, 31.831, 127.324 cd/m2); background Yb = 20, average surround, D = 1.
The display is the existing analysis condition: D65, LA = 20 cd/m2, Yb = 20,
dim surround, D = 1. These are assumed conditions, not measurements. Full
adaptation is deliberately explicit. No illuminance is selected by a fit.

Forward CAM16 uses spectral print XYZ. Inverse CAM16 under display conditions
finds the corresponding XYZ. Display conversion, existing gamut mapping and
sRGB encoding follow. No additional scene DRT is applied to the print.
The scan remains unchanged and uses the current generic numbers, Academy axis,
LAD aim off, stock balance offset and OpenDRT native grey. Its matrices are
inherited baseline operations; this study adds no matrix as a film stage.

## Method and numerical limits

CPU only, Intel Core i7-12700H Windows machine specified by AGENTS.md. No GPU
run, allocation or backend validation. Peak CPU working set was not measured.
Each image is decoded at 640 pixels on the long edge, chosen for review before
the run. Full spectral images are not allocated. Spectral tables retain the
current 360 to 840 nm, 1 nm point/trapezoid integration grid, with CIE weights
zero beyond their domain. Scene and printer transport use the existing energy
radiometric model, not a new photon integral; layer Q is dimensionless relative
exposure, characteristic-curve inputs are log10 exposure, density is unitless,
and viewed XYZ has perfect-diffuser Y = 100. No spectral extrapolation rule is
changed. Existing source-domain and Gaussian-tail assumptions still apply.

The appearance transform and array print-table interpolation use float64.
Image negative kernels, compiled rendering and output encoding retain their
existing float32 operations. The full image chain is not a float64 reference.
The product grade remains +1.5 EV and the existing contrast/saturation defaults.
The synthetic sweep enters after that grade; it is not graded twice.

Checks specified in code before execution: CAM16 known example and inverse
test; J/M preservation before gamut mapping within 1e-8; baseline against the
compiled print within 1e-4 display code on the sweep. Derivatives use central
differences at 0.001 log10 AP1 and report the change at 0.0005. Their numerical
stability is reported, not assigned a post-hoc pass threshold.

Colourfulness metric is mean M' ratio to OpenDRT on pixels/probes whose reference
M' exceeds 6, using CAM16-UCS under the same display condition. It is not the
ratio of mean M values. The D55 sweep uses 36 hues and four common colourfulness
levels at 0 EV, 144 probes. Stock spread is mean pairwise CAM16-UCS distance on
these probes. This is not the full historical exposure sweep, and the stock set
contains Ultramax rather than C200. Its spread cannot be compared directly to
the earlier 1.1 to 1.6 numbers. Metrics explain changes; they do not rank looks.

## Measured results

Run: `run_study.py`, initial day/night invocation, then portrait invocation with
the correct `.nef` and `.dng` extensions. An earlier invocation with incorrect
portrait extensions was stopped before portrait rendering; its log is retained.
Commands to reproduce all results are in the P11 README. The summary run is
`summarize.py`; evidence is `build/tmp/p11/measurements.json`, `paper_slopes.json`,
`summary_complete.txt`, and the run logs.

| Stock, D55 probes | Current print | CAM100 | CAM500 | CAM2000 | Current scan |
| --- | ---: | ---: | ---: | ---: | ---: |
| Portra 160 | 1.286 | 1.217 | 1.341 | 1.450 | 0.889 |
| Portra 400 | 1.392 | 1.318 | 1.447 | 1.561 | 0.994 |
| Portra 800 | 1.369 | 1.296 | 1.425 | 1.538 | 0.983 |
| Ektar 100 | 1.475 | 1.397 | 1.528 | 1.643 | 1.065 |
| Gold 200 | 1.262 | 1.193 | 1.312 | 1.418 | 0.880 |
| Ultramax 400 | 1.358 | 1.286 | 1.414 | 1.527 | 0.970 |
| 5207 | 1.171 | 1.107 | 1.226 | 1.332 | 0.969 |

Photo-stock spread: print 2.781, CAM100 2.737, CAM500 2.893, CAM2000 3.034,
scan 2.138 dE'. CAM100 reduces spread slightly; it does not recover stock
differences. Portra 400 on the dune is 1.267 to 1.216, the night 1.377 to 1.244,
the outdoor portrait 1.296 to 1.186, the stage portrait 1.274 to 1.128.

Local derivatives at ungraded 18% AP1 grey, Portra 400, D55:

| Output quantity | Two local separation singular values |
| --- | --- |
| log10 layer exposure | 1.486, 0.931 |
| Negative dye amount | 1.133, 0.652 |
| log10 paper exposure | 0.972, 0.481 |
| Paper Status A density | 3.053, 1.620 |
| Print CAM16-UCS a', b' before gamut mapping | 252.196, 122.858 |

The input directions form an orthonormal zero-sum plane in log10 AP1. The first
four outputs are projected on the corresponding three-record plane. The last
uses a', b'. These values have different units. They are not sequential factors
that can be multiplied. Full Jacobians are saved. Half-step largest absolute
changes are 1.88e-6, 1.04e-4, 8.37e-5, 0.00891 and 0.23713, respectively.
Piecewise curves and table interpolation limit derivative precision. The paper
amplification is large enough to be visible despite that limit. It is a local
result, not a global factor of three in perceived colourfulness.

CAM16 example and inverse checks passed. Largest sweep J/M preservation error
is 3.04e-13; compiled/reference print difference is 1.35e-7 code or less.
These checks validate the implementation, not the appearance match.

The corresponding colours can exceed display gamut. Across the 20 photo/stock
renders, the existing output gamut operation still reports 1046 pixels outside
after compression for CAM100, 7060 for CAM500, 19104 for CAM2000. These are sums
over separate renders, not unique scene pixels. CAM2000 also produces negative
destination XYZ for 469 pixels in se222, 379 in the night and 10 in se188,
summed over stocks. These are reported, not silently repaired. Display encoding
retains the existing clipping behavior. This is another reason this prototype
is not ready for production. No new substitute gamut method was introduced.

## Visual observations by the research agent

Inspected local rows: Portra 400 dune, outdoor portrait and night; Ektar stage
portrait. CAM100 makes the sand less bright, keeps a strong blue sky, and gives
the dune shadows more weight. It does not produce the soft scan rendering.
The outdoor portrait remains strongly orange; its face is darker after CAM100.
The night gets deeper shadows and less colourful lit pavement; lamp highlights
remain bright. On the stage portrait, the green dress and blue backdrop become
darker and less intense. These changes do not establish a better stock look.
CAM500 and CAM2000 tend to retain or increase the intense colours. No user
review has occurred. The other rendered rows have not all been inspected.

Review sheets: `build/tmp/p11/review_se357.jpg`, `review_se222.jpg`,
`review_5253219691.jpg`, `review_se188.jpg`, `review_se274.jpg`. Each sheet has
four stock rows and six labelled columns. Separate `_<stock>.jpg` rows make
comparison easier. `review.html` includes the comparison plot and Portra rows.

## Recommendation and open items

Keep an explicit print viewing operation as an architectural requirement when
the goal is to show the appearance of a physical print. Do not select 100 lux
because its colourfulness number is lower. The result depends on real viewing
conditions, and the portrait tone change is substantial. This study rejects
the hypothesis that a standard appearance transfer alone explains the excess.

The strongest next physical audit is the reconstruction of reflection-paper
colour response from effective dye curves and Status A curves. A neutral
characteristic curve and peak-normalised dye curves do not determine the full
off-neutral sensitometry of paper. Treating three channel curves as independent
paper-layer responses remains an inference. The present derivative locates the
amplification but does not measure real Endura off-neutral response. Obtain a
source that constrains that response before changing the paper curves, adding
scattering, or choosing flare. None of those coefficients is fitted here.

The photo negative dye basis also remains underdetermined by a single neutral
spectrum: Dneutral(lambda) constrains only a weighted sum of three dye spectra.
Band splitting supplies the missing shapes by assumption. A viewing transform
shared across stocks cannot recover stock-specific information absent there.
This study does not solve stock separation or ugly scan rendering.

Open: user visual review; measured print/display conditions; output gamut
handling for corresponding colours; independent paper off-neutral data; spatial
viewing glare and incomplete adaptation; full-resolution and GPU verification.
No real-film accuracy, real-print agreement, or production suitability is claimed.
