# P15: Film grain data

Date: 2026-11-05 (America/Chicago). Python, CPU only. Phase G0 of the Alcedo Studio plan
`docs/roadmap/alcedo_studio/edit/film_grain_format_and_stock_plan.md` (issue #675, plan PR #686).

**User decision of 2026-11-05.** The user approved the plan of three film formats (16mm, 35mm, 70mm) with a grain size per format
and a grain strength from the datasheet of each stock. Old projects must open. The user left the other choices to the
recommendations of the plan (U1 to U4 of the plan, closed). The user asked for G0 first and for stacked pull requests for the whole
plan. The lab makes the data and the expected values; the product renders the grain (ROADMAP section 2, point 12).

## 1. Question and result summary

Questions of G0:

1. What is the RMS granularity of each layer of each stock of the catalog, against density, and from which source?
2. What is the standard deviation of the dye amount of each layer, so that the film print path can add the grain before the print
   table?
3. How large is the dye cloud, and how do the noise fields of the three layers correlate?
4. How strong must the display-referred grain of the methods with no negative (ACES 2.0, OpenDRT) be, so that it matches the
   film print?
5. Which values must the product tests compare with?

Result:

- All 35 stocks of the catalog (30 negatives, 5 reversal films) have grain data with a source and a tier: 8 digitized datasheet
  curves, 9 published single values, 6 values from a related stock (`family`), 7 values from the Print Grain Index (`pgi`, with an
  external anchor), and 5 reversal films (section 4.2).
- The layer solve has no negative square and an error of 0 on every stock. The 16-node curves differ from the full curves by at most
  4.3 % (section 4.3).
- The 5207 segments of Alcedo Studio (`film_grain_math.h`) differ from the vector digitization by a median of 6 % (red), 12 %
  (green), and 15 % (blue). The product puts the green and blue peaks at higher density. Phase G1 replaces the segments with the
  bundle values (section 4.1).
- The 5207 scans of the user cannot separate the dye cloud from the scanner blur. The fitted total width (5.9 to 7.8 um) is an upper
  limit of the cloud size. The product keeps the literature values 2.0 / 2.0 / 2.8 um and has no cluster term (section 4.4).
- One shared field (the first form of the plan) cannot give the measured channel correlation of the scans. A 3 x 3 layer correlation
  R (rg 0.489, gb 0.2349, rb 0.1743, positive definite) gives it exactly. R replaces the shared field in the plan (section 4.5).
- Post-path target: at 35mm, mid grey, and the 48 um aperture, the linear display standard deviation of 5207 on Endura Premier is
  0.0107 / 0.0100 / 0.0152 (R, G, B). The display channels correlate at rg 0.535, gb 0.509, and rb 0.087 (section 4.6).
- The reference evaluator `grain_reference.py` reproduces the table of section 3.2 of the plan. Its discrete kernel matches the
  lag-1 correlation of the continuous pixel field. With that kernel, the 2 x 2 zoom statistic is exact and the zoom pattern
  correlation is at least 0.943. The first kernel form (`sigma_b = sigma_c / p`) failed the zoom check by 21 % (section 5).
- The bundle builder writes resource schema 11 with the group `grain/<stock>/` and the expected file `grain__expected.bin`
  (section 6).

## 2. Inputs and provenance

| Input | Use | Licence and storage |
| --- | --- | --- |
| 38 manufacturer documents (`scripts/poc/p15_film_grain/sources.json`: URL, SHA-256, title, use; retrieved 2026-11-05) | Granularity charts, RMS values, PGI values | Manufacturer data; no redistribution licence. `build/tmp/p15_grain/sources/`, not committed (ROADMAP section 2, point 5) |
| Fotufilm profile `Sources/FotufilmCore/Stocks/portra400.json`, `grainStrength` 0.009 (commit `6b45c80`) | The absolute anchor of the PGI tier (rule `pgi_anchor_external`) | CC BY-SA 4.0 (THIRD_PARTY_NOTICES.md). One value; an external value with no primary source |
| Residual blocks of three 5207 frames of the user (Flextight X5, 3200 dpi, 7.94 um per pixel), made by the grain colour study of Alcedo Studio #660 | Correlation width, channel correlation (rg 0.661, gb 0.41, rb 0.246) | Local only (`build/tmp/p15_grain/study_660/`) |
| Viewer models (`mvp_pipeline`): negative curves, Status M and Status A, dyes, the 5207 print on Endura Premier, the light table | Dye amount of a grey, the Jacobians of the layer solve and of the display | This repository |
| `film_grain_math.h` of Alcedo Studio main `f28ca394` | Comparison of the 5207 segments | Alcedo Studio (GPL-3.0) |

The Aerocolor IV sheet is not available at its Kodak URL (HTTP 404). The value 8.5 comes from a review that quotes the sheet (a
secondary source, named in `stock_grain.json`).

## 3. Method

### 3.1 Digitization of the vector charts (`digitize_granularity_charts.py`)

The granularity and characteristic charts of eight Kodak sheets are PDF vector paths. PyMuPDF reads the paths (`get_drawings`) on
the page and in the clip of `chart_config.json`. The script joins the pieces of a curve by continuity and calibrates each axis from
the label positions: it takes the labels of one column, removes labels closer than 6 pt to a neighbour, snaps each label to its
mutual-nearest tick (curve paths excluded), and fits the axis (linear for density, log10 for sigma). Limits: largest tick residual
1.0 pt, RMS 0.5 pt (0.7 pt for the sigma axis of EXR 5248, which has a crowded label column). The characteristic curves are assigned
by their vertical order, and the granularity curves by the path indices of the configuration or by the nearest label. Density and
sigma are sampled at the same log exposure. The overlays of each chart (`build/tmp/p15_grain/overlays/`, local) were checked by eye.

| Stock | Sheet, page | Characteristic paths | Granularity paths | Density axis RMS (pt) | Sigma axis RMS (pt) |
| --- | --- | --- | --- | --- | --- |
| 5203 | `kodak_5203_ti.pdf`, 4 | 49, 50, 51 | 46 R, 47 G, 48 B | 0.172 | 0.001 |
| 5207 | `kodak_5207_ti.pdf`, 4 | 3, 4, 5 | 6 | 0.172 | 0.019 |
| 5213 | `kodak_5213_ti.pdf`, 4 | 58, 59, 60 | 3 R, 56 G, 57 B | 0.349 | 0.009 |
| 5219 | `kodak_5219_ti.pdf`, 4 | 45, 46, 47 | 48, 49 | 0.172 | 0.016 |
| 5277 | `kodak_5277.pdf`, 3 | 10, 11 | 9 | 0.193 | 0.460 |
| 5293 | `kodak_5293.pdf`, 4 | 6, 8, 9, 10 | 12 to 16 | 0.224 | 0.336 |
| EXR 5248 | `kodak_5248.pdf`, 3 | 22 | 23 to 26 | 0.310 | 0.629 |
| 5206 | `kodak_5206.pdf`, 3 | 9, 10, 11 | 12 B, 13 G, 14 R | 0.096 | 0.059 |

Read condition of all charts: diffuse RMS granularity at a 48 um circular aperture, against gross Status M density.

### 3.2 Tiers and rules (`stock_granularity.py`)

| Tier | Rule | Stocks |
| --- | --- | --- |
| `curve` | `granularity_chart`: the digitized curves of each layer | 5203, 5206, 5207, 5213, 5219, 5277, 5293, EXR 5248 |
| `number` | `single_value_green_anchor`: the 5207 curve shape of each layer, scaled so that the green value at net density 1.0 is the published value (RMS x 1000) | Agfa Vista 100 (4.0), Fuji C200, Pro 400H, Superia X-TRA 400, Superia Reala (4), Pro 160C, Pro 160S (3), Kodak 5247 (5, upper bound of the sheet), Aerocolor (8.5, secondary source) |
| `family` | The value of a named related stock (inferred) | 5247 II, 5250 (5, from 5247), Natura 1600 (7, from Superia 1600), Eterna 500 and Eterna 500 Vivid (3.5, from F-250), Kodak 5248 (the EXR 5248 curve) |
| `pgi` | `pgi_ratio`, `pgi_anchor_external`, then `single_value_green_anchor` | Portra 160, 400, 800, Ektar 100, Gold 200, Ultramax 400, Vericolor III |
| `reversal` | `reversal_nutting`: sigma = v * sqrt(D_gross) / 1000 per layer, v the published value at gross visual density 1.0 | Velvia 50 (9), Velvia 100 (8), Provia 100F (8), Astia 100F (7), Ektachrome E100 (8) |

Rule `pgi_ratio`: PGI = c + 34.3 ln(sigma) (Kodak E-58: 2 units are 6 % of granularity; US 5629769). The ratio to the reference
stock is exp((PGI_s - PGI_ref) / 34.3), averaged over the magnifications where both values are 25 or more. Rule
`pgi_anchor_external`: no primary source gives an RMS value and a PGI for one Kodak still film. The anchor is Portra 400 = 0.009 at
net density 1.0, the Fotufilm value (section 2). This is the only external value of the step; its effect is one common scale of the
seven PGI stocks.

### 3.3 Layer solve

The chart reads the channels of a densitometer, and the product adds noise to the dye amount of each layer. For small noise the
channel density changes by `J da`, `J_jk = sum w_j T e_k / sum w_j T` (Status M weights `w_j`, transmittance `T` of the negative,
dye `e_k`; Status A for the reversal films). With independent layers, `sigma_48_j^2 = sum_k J_jk^2 sigma_a_k^2`. The script solves
`sigma_a_k^2` at each node with non-negative least squares (rule `layer_noise_from_channels`). A negative square is a data error:
the script stops for that stock. The curves are reduced to at most 16 nodes by Douglas-Peucker with a relative limit of 5 %.

### 3.4 Cloud size (`fit_scan_correlation_width.py`)

The plan asked for a fit of sigma_c on the 5207 scans, with the scanner MTF from a sharp edge. The scans have no sprocket hole and no
film edge in the focal plane (the black border is the holder mask), so the MTF is not measured. The script fits the total Gaussian
width `s` (`s^2 = sigma_c^2 + sigma_s^2`) from the ratio of the covariance at lags 2 and 1, which white scanner noise does not
change. This gives an upper limit of sigma_c.

### 3.5 Layer correlation (`fit_layer_correlation.py`)

The scans of #660 give the channel correlation rg 0.661, gb 0.41, rb 0.246. The script reads the 5207 negative at net green density
0.1, 0.3, 0.5, and 0.7 through the default scanner of Negative Scan. The channel covariance is `J S R S J^T`. It fits the three
off-diagonal values of R (least squares, R positive semidefinite) and records two comparisons: independent layers (R = I), and one
shared field (one rho for all pairs). Requirement: each channel correlation within 0.05 of the target.

### 3.6 Post-path target (`post_path_target.py`)

The record of an 18 % grey on 5207 (one pixel, no image-plane step), the dye-amount noise of each layer at that record, the layer
correlation R, and the Jacobian of the display output (print table, display matrix, display finish, sRGB encoding; central
differences of 1e-4). Output: the standard deviation of each display channel at the 48 um aperture, encoded and linear, and the
display correlation.

### 3.7 Reference evaluator (`grain_reference.py`)

Rules (docstring of the script; the product follows them exactly):

| Rule | Statement |
| --- | --- |
| `grain_pitch` | `p = frame_mm * 1000 / long side of the reference image`; frame long sides 12.52, 36, 70 mm; a render at scale s has the pitch p / s |
| `grain_pixel_integral` | `I(sigma_c, p) = (1 / p) [erf(q / sqrt 2) - 2 (phi(0) - phi(q)) / q]`, `q = p / (sqrt 2 sigma_c)`; `sigma_px = sigma_48 sqrt(A_48) I` |
| `grain_kernel` | Gaussian weights, radius `ceil(3 sigma_b)` (at most 24); `sigma_b` by bisection so that the discrete lag-1 correlation equals the continuous one; unit field `u = blur / sum w^2` |
| `grain_layer_mix` | `N = L u`, L the Cholesky factor of R; after the blur and the division, so the pixel correlation is R exactly |
| `grain_aggregate` | `k = clamp(round(1 / s), 1, 4)`; the sum of k x k reference Gaussians divided by k |

The film print path adds `strength * sigma_a(a) * pixel_factor_k * N_k` to the dye amount `a` (`pixel_factor = sqrt(A_48) I`). For a
reversal film `a = dye_max - record`. The post path adds `strength * display_sigma_48_j * pixel_factor_j * N_j` to the linear display
channel j, with the fields mixed by the display correlation of section 3.6.

## 4. Results

### 4.1 The 5207 segments of the product (`check_5207_product_segments.py`)

| Layer | Density range | Median difference | Largest difference (at density) | Mean ratio product / digitization |
| --- | --- | --- | --- | --- |
| Red | 0.25 to 2.03 | 6.3 % | 27.9 % (0.30) | 0.98 |
| Green | 0.61 to 2.69 | 11.7 % | 35.9 % (0.68) | 1.00 |
| Blue | 1.02 to 3.00 | 15.4 % | 49.1 % (2.99) | 1.15 |

The plan expected agreement within 3 %. The product segments put the green peak at density 0.94 (digitization 0.77) and the blue peak
at 1.32 (digitization 1.12). The vector digitization has a tick residual below 0.02 pt on this chart, so the product segments are the
older reading. Phase G1 replaces them with `grain/kodak_5207/channel_*`. The comparison is a recorded measurement, not a pass.

### 4.2 Values of each stock (`stock_grain.json`)

Green sigma_48 at net density 1.0 (curve and pgi tiers: from the curves; number and family: the published value):

| Stock | Tier | Value | Stock | Tier | Value |
| --- | --- | --- | --- | --- | --- |
| 5203 | curve | 0.00442 | Portra 160 | pgi | 0.00686 |
| 5206 | curve | 0.00667 | Portra 400 | pgi | 0.00900 (anchor) |
| 5207 | curve | 0.00632 | Portra 800 | pgi | 0.01228 |
| 5213 | curve | 0.00638 | Ektar 100 | pgi | 0.00474 |
| 5219 | curve | 0.00709 | Gold 200 | pgi | 0.01104 |
| 5277 | curve | 0.00774 | Ultramax 400 | pgi | 0.01170 |
| 5293 | curve | 0.00763 | Vericolor III | pgi | 0.00954 |
| EXR 5248 | curve | 0.00592 | Velvia 50 | reversal | 0.00354 |
| Kodak 5248 | family | 0.00592 | Velvia 100 | reversal | 0.00290 |
| 5247, 5247 II, 5250 | number, family | 0.005 | Provia 100F | reversal | 0.00229 |
| Aerocolor | number | 0.0085 | Astia 100F | reversal | 0.00227 |
| Fuji C200, Pro 400H, Superia X-TRA 400, Reala, Agfa Vista 100 | number | 0.004 | Ektachrome E100 | reversal | 0.00318 |
| Fuji Pro 160C, Pro 160S | number | 0.003 | Natura 1600 | family | 0.007 |
| Eterna 500, Eterna 500 Vivid | family | 0.0035 | | | |

The 5207 green value 0.0063 at net density 1.0 equals `grainStrength` of the Fotufilm profile `vision250d.json` (0.0063). The Fuji values are about half
of the Kodak values of a similar speed (Pro 160S 0.003 against 5207 0.0063). The Fuji sheets state no aperture or densitometry, so
the difference can be a measurement condition (inferred). The values are used as published.

### 4.3 Layer solve and node reduction

All 35 stocks: largest relative error of the solve 0 (limit 2 %), no negative square. Largest node error 4.3 % (5203; limit 5 %).
The first limit of 2 % failed with 16 nodes. The limit of 5 % is near the reading error of the log axis of the charts (3.7 % on
EXR 5248), and 16 nodes are the limit of the plan.

### 4.4 Cloud size

| Channel | Total width s, median (quartiles), um | Ratio C(2p) / C(p), median | Blocks fitted |
| --- | --- | --- | --- |
| R | 5.87 (5.62 to 6.55) | 0.305 | 56 |
| G | 7.69 (6.89 to 12.17) | 0.443 | 47 |
| B | 7.77 (7.04 to 9.03) | 0.483 | 45 |

The widths are above all the literature values (1.6 to 3.8 um), so they contain the scanner blur. The fit cannot test the cluster term
of the plan (section 3.3 of the plan), and none is added. Recommendation: an 8000 dpi scan of a 5207 frame with a sharp film edge
would give the MTF and a fit of sigma_c.

The blur of the scanner also lowers the per-pixel standard deviation of a real scan: at 7.94 um the scans show about one third of the
per-pixel value of the model. The product models an ideal scan of the film (no scanner blur), so its grain is stronger than the
grain of these scans at the same pitch.

### 4.5 Layer correlation

| Case | rg | gb | rb |
| --- | --- | --- | --- |
| Target (scans of #660) | 0.661 | 0.41 | 0.246 |
| Independent layers (R = I) | 0.255 | 0.178 | 0.044 |
| One shared field, rho 0.466 | 0.661 | 0.624 | 0.529 |
| Layer correlation R (rg 0.489, gb 0.2349, rb 0.1743) | 0.661 | 0.410 | 0.246 |

R has the eigenvalues 0.51, 0.87, and 1.62. The side absorption of the dyes gives about 40 % of the rg target; the rest is a
correlation of the layer noise. One shared field gives too much gb and rb. The Flextight bands differ from the default virtual
scanner, so the side absorption part differs too (inferred). The product uses R of 5207 for all stocks: no other stock has a measured
scan (inferred).

### 4.6 Post-path target

| Value | R | G | B |
| --- | --- | --- | --- |
| Record (dye amount) | 0.6575 | 0.7096 | 0.8292 |
| sigma_a at 48 um | 0.00789 | 0.00761 | 0.01440 |
| Display value, encoded | 0.470 | 0.474 | 0.452 |
| Display sigma_48, encoded | 0.0124 | 0.0115 | 0.0187 |
| Display value, linear | 0.1876 | 0.1905 | 0.1720 |
| Display sigma_48, linear | 0.01065 | 0.00998 | 0.01523 |

Display correlation: rg 0.535, gb 0.509, rb 0.087. The print table turns the layer correlation into a different display
correlation, so the post path mixes with the display correlation (rule `grain_layer_mix`, post form).

## 5. Checks of the reference evaluator

| Check | Comparison rule | Limit | Result |
| --- | --- | --- | --- |
| Closed form of I | Against the frequency integral (SciPy `quad`), sigma_c 1 to 4 um, p 1 to 60 um: largest relative difference | 1e-6 | 4e-15 |
| Plan table | sigma_px of section 3.2 of the plan (sigma_48 0.0070, sigma_c 2.0) at 3 formats and 3 sizes | 0.001 | equal to the printed values at every entry |
| Kernel lag-1 | Discrete lag-1 against the continuous C(p) / C(0), 3 formats x 2 sizes x 3 layers: largest difference | 1e-6 | 2e-16 |
| Zoom statistic | Standard deviation of the 2 x 2 box mean of the full render against the render at scale 0.5 | 5 % | ratio 1.0000 on all 18 cases |
| Zoom pattern | Pattern correlation of the same two images (exact, from the weights) | above 0.9 | smallest 0.943 (16mm, 6000 px, red and green) |

Recorded, not used: the first kernel form `sigma_b = sigma_c / p` has a lag-1 correlation up to 0.278 too low (16mm, 2560 px, red) and a
zoom ratio down to 0.793 (35mm, 6000 px, red). The discrete Gaussian of a white lattice leaves out the pixel box, which dominates when sigma_b is
below 1.

Selwyn's law: `I p` is 0.955 at p = 50 um, 0.991 at 250 um, and 0.995 at 500 um (sigma_c 2.0). The plan test of G1 ("within 1 % at
p = 50 um") cannot pass; the plan changes it to 500 um (section 7).

Expected values for the product tests (`grain__expected.bin`, formats {16, 35, 70} x long sides {2560, 6000} x layers): pitch,
sigma_b, blur radius, sum w^2, pixel factor, lag-1 (kernel, continuous, after the layer mix, after the post mix), the zoom factors and
pattern correlation, the aggregate k for render scales 1, 0.5, 0.3, 0.1 (1, 2, 3, 4), R and its Cholesky factor, the dye amount and
pixel sigma of the film print for 5207, 5219, Portra 400, and Velvia 50 at an 18 % grey, and the post-path pixel sigma. Run time 7 s.

## 6. Product resources, schema 11

`build_product_resources.py` adds (docstring of the builder):

| Array | Shape | Content |
| --- | --- | --- |
| `grain/<stock>/layer_amount`, `layer_sigma_amount` | (3, 16) | sigma_a of each layer against the dye amount |
| `grain/<stock>/channel_density`, `channel_sigma_48` | (3, 16) | sigma_48 of each channel against gross density (Status M; Status A for a reversal film) |
| `grain/<stock>/layer_node_count`, `channel_node_count` | (3), int32 | Counted nodes; the others repeat the last node |
| `common/grain_cloud_sigma_um` | (3) | 2.0, 2.0, 2.8 |
| `common/grain_layer_correlation` | (3) | rg, gb, rb of R |
| `common/grain_aperture_area_um2` | () | pi 24^2 |
| `common/grain_post_display_value`, `grain_post_display_sigma_48`, `grain_post_display_correlation` | (3) | Post-path target, linear display |

Metadata `grain` holds the tier, the source, and the rule of each stock. Checks of the builder: every negative and reversal film has a
group; the nodes are finite and rise; sigma is positive; the evaluator and the bundle hold the same sigma_c and R. Run of
2026-11-05: section 9.

## 7. Changes to the Alcedo Studio plan

| Plan item | Change | Reason |
| --- | --- | --- |
| Shared field `shared_share` (rho), 4th noise channel | Layer correlation R (3 values), mixed after the blur; 3 noise channels | Section 4.5 |
| Post path | Mixed with the display correlation of 5207 on Endura Premier | Section 4.6 |
| `sigma_c` fit, cluster term | Literature values, no cluster term | Section 4.4 |
| `sigma_b = sigma_c / p` | Rule `grain_kernel` (lag-1 match) | Section 5 |
| G1 test "Selwyn within 1 % at p = 50 um" | At p = 500 um | Section 5 |
| Bundle field `cloud_sigma_um` per stock, `tier` per stock | `common/grain_cloud_sigma_um`; tier in the metadata | One value for all stocks; the array file has no string type |
| 5207 segments of `film_grain_math.h` | Replaced in G1 from the bundle | Section 4.1 |

## 8. Open items

- The PGI anchor is external (Fotufilm). A Kodak sheet with an RMS value and a PGI for one still film would replace it.
- The Fuji scale (section 4.2) is not corrected. A Fuji sheet that states the aperture, or a measurement, would decide it.
- sigma_c is not fitted (section 4.4). An 8000 dpi scan of a 5207 frame with a sharp film edge would give the fit.
- R comes from the 5207 scans only and holds for all stocks (inferred).
- Aerocolor uses a secondary source.
- User review of the rendered grain in Alcedo Studio (phases G3 to G6).

## 9. Run record and commands

Machine: Intel Core i7-12700H, 31.8 GB, Windows 11, CPU only. Environment of step P6 (`build/tmp/p6/venv`). Commands: the
[script README](../../scripts/poc/p15_film_grain/README.md).

Builder run: pending.

## Parameters

| Name | Meaning | Unit | Value |
| --- | --- | --- | --- |
| `sigma_48` | Diffuse RMS granularity of a channel at a 48 um circular aperture | density | per stock and density |
| `sigma_a` | Standard deviation of the dye amount of a layer at 48 um | dye amount | per stock and amount |
| `A_48` | Area of the 48 um aperture | um^2 | pi 24^2 = 1809.6 |
| `G` | Selwyn granularity, `sigma_48 sqrt(A_48)` | density um | per stock |
| `sigma_c` | Gaussian sigma of the dye cloud | um | 2.0, 2.0, 2.8 |
| `p` | Pitch of one pixel on the film | um | frame_mm 1000 / long side |
| `I` | Pixel integral of rule `grain_pixel_integral` | 1 / um | per sigma_c and p |
| `pixel_factor` | `sqrt(A_48) I`: sigma_px / sigma_48 | none | per sigma_c and p |
| `sigma_b` | Sigma of the discrete kernel | pixel | rule `grain_kernel` |
| `w` | Weights of the discrete kernel, one axis | none | sum 1 |
| `rho1` | Lag-1 correlation of the pixel field, one axis | none | 0 to 1 |
| `R`, `L` | Layer correlation and its lower Cholesky factor | none | rg 0.489, gb 0.2349, rb 0.1743 |
| `k` | Aggregate of rule `grain_aggregate` | pixel | 1 to 4 |
| `s` | Total Gaussian width of the grain in a scan | um | section 4.4 |
| `J` | Jacobian of the channel density against the dye amounts | none | per stock and density |
| PGI | Kodak Print Grain Index | none | per stock and magnification |
