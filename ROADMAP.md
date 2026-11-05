# Alcedo Film Lab: roadmap and decisions

This file is the source of truth for the requirements, the user decisions, and the route of this repository. The [README](README.md) is the public overview. Results and text before 2026-10-31 that say "README U..." or "README section ..." mean this file; a U number points to the decisions in the git history (section 2).

Research and prototypes for a spectral film simulation pipeline and a new Display Rendering
Transform (DRT) for [Alcedo Studio](https://github.com/zidage/AlcedoStudio).

The goal is to model film exposure, development, dye absorption, and printing from published
principles and source measurements. The implementation must support **CUDA, Metal, and OpenCL**.
The research combines useful ideas from **Fotufilm** and **spektrafilm**, with independent code
and data preparation where practical.

**Status (2026-11-04): P0 to P7, P9, and P10 have results; P8 and the MVP are cancelled, and the work continues in Alcedo Studio. The earlier decisions are cleared (section 2).** The Python
program of P6 takes a RAW file to an image by the print or by the APD scan, on 30 negatives and 18
print materials, on the CPU. There is no GPU measurement. The product integration is not done; its plan is the [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md). The step index is
[docs/exploration/README.md](docs/exploration/README.md). Agent rules are in
[AGENTS.md](AGENTS.md).

**ACES means ACES Reference Gamut Compression (RGC) in this project** (section 2, point 1). **Film grain is outside this research:**
Alcedo Studio already has its own implementation.

## 1. Main project and research workflow

| Item | Reference |
| --- | --- |
| Product | [Alcedo Studio](https://github.com/zidage/AlcedoStudio) |
| Research workflow example | [Alcedo AI Mask Lab](https://github.com/zidage/alcedo-ai-mask-lab) |
| Example of step reports | [AI Mask exploration index](https://github.com/zidage/alcedo-ai-mask-lab/blob/main/docs/exploration/README.md) |
| Example of an integrated prototype | [AI Mask MVP report](https://github.com/zidage/alcedo-ai-mask-lab/blob/main/docs/exploration/mvp_ai_mask.md) |
| Alcedo source inspected | [`4261b8a5`](https://github.com/zidage/AlcedoStudio/tree/4261b8a5c93e127a13cf96c78b686be3c3430742) |

Follow the AI Mask Lab approach: state the product requirements, test candidates in separate
experiments, keep reproducible evidence, then run the selected approach in one standalone MVP.
The final integration belongs in Alcedo Studio. This lab must prove the model and its execution
before the port.

Each experiment must state its question, inputs, source versions, method, command, numerical
criteria, result, cost, limitations, and recommendation. Separate source observations,
calculations, hypotheses, proposed designs, measured results, and user review.

## 2. Decisions

On 2026-11-04 the user cleared the 99 earlier decisions (U1 to U99). They stay in the git history (`ROADMAP.md` at commit
`cbaf4fa`) and in the step reports; a U number in a report or in a later section of this file points there. These points
replace them.

1. **Product.** A film simulation DRT in Alcedo Studio. Its input is scene-referred linear AP1 after the default grade of the
   product, from any camera, with the scene white of the RAW file when there is one. The work goes directly into Alcedo Studio
   (CUDA, Metal, OpenCL; tables built in C++ when a model needs them, with no disk cache). Gamut compression follows ACES RGC;
   the display rendering is the DRT of the document (OpenDRT by default). Grain, halation, and glow are in the product and are
   outside this lab.
2. **Method.** A physical, spectral process: the spectrum of the scene, the exposure of each layer, development, then a print
   or a scan. No 3x3 matrix as a film stage, no correction fitted to the data of one stock (it removes the character of that
   stock), no hue warp, and no fit to a colour chart.
3. **Judgement.** The rendered image decides, by eye, on labelled sheets of a broad set of photos (portraits, day, night). Each
   stock must show its own cast and character. Chart error and one-dimensional Lab measures are not a target; a measure must
   come from perception and must explain a cause.
4. **Target look.** The film look that people know: lab scans of real negatives, soft, with clear differences between the
   stocks.
5. **Sources and licences.** spectral_film_lut (MIT) can be adopted; Fotufilm (Apache-2.0) is a reference; spektrafilm is only
   an external comparison by eye. Manufacturer PDFs are not published. Film Analyzer, scans from the web, and scanner vendor
   data are for tests only and stay under `build/tmp/`. The only real film data is the 5207 strips of the user scanned on a
   Hasselblad X5, with two digital photos of one scene (`_DSC4976`, `_DSC4909`; P12 report).
6. **Open problems (2026-11-04).** Some stocks look ugly on Lab Scan; the prints of all stocks are too vivid; the photo stocks
   differ too little. Directions that were tried and rejected: interlayer values from the Academy CDD_TO_CID (U79, U99), scan
   colour fitted per stock (U95 to U97), the hue sector warp (U81 attempt), and the Frontier table (U64).
7. **Stock character (2026-11-04).** The scan cannot separate stocks whose negatives are nearly the same (P12 report,
   section 4). The user chose a creative control in the viewer, `stock_character` k: the sensitivities and the characteristic
   curves of a negative differ from the average negative of its medium k times as much as in the data (k = 1 is the data).
   The direction of each difference comes from the data of the stock; its size is chosen. Not yet in the C++ resources.

8. **Complete RAW white in the Python viewer (2026-11-04).** After the P13 comparison, the user asked to add the spectral
   input modes to the current Python GUI and combine them with Stock character. The viewer offers the full-white smooth,
   LED and fluorescent families, and constrained smooth/LED reconstruction. The P13 smooth scan button applies the reviewed
   balance0 scan settings and keeps the selected stock and character strength. The scene spectrum stays independent of the
   stock-character strength. C++ resources and GPU integration are not part of this request.

9. **Negative Scan (2026-11-04).** The user asked for a new scan method in two parts: a Film Scanner Model (scanner light x channel
   response x 10^-D of the negative) and a Negative Rendering Model (density above the base, inversion, colour), with a Neutral Scan that has
   no automatic correction and an automatic colour from the frame as a separate stage; scanner styles from measured samples come later. The
   P13 input is not used for it. Result: [P14 report](docs/exploration/p14_negative_scan.md), method `negative_scan` of the Python viewer.

10. **Negative Scan is the final form (2026-11-05).** The user accepts method `negative_scan` of P14 as the final form of the scan and stops
   the review rounds. Defaults: no automatic correction (Neutral Scan, auto colour off) and scene light As Shot, so the cast of the RAW white
   stays. The viewer and the command line start with these defaults. In Alcedo Studio this form replaces the ADX scan: issues #661, #662,
   and #664 take it, and the form of PR #663 is dropped (the pull request is done again). The port has two phases: first the model layer
   (resources, host tables, document, panel), then the GPU passes (CUDA and OpenCL, then Metal).

The target source license is GPL-3.0-only. Third-party code, measurements, profiles, and derived
tables retain their applicable license terms.

## 3. Initial findings from the reference projects

The inspected revisions are fixed below. Later upstream changes require a new source check.

| Project | Inspected revision | Useful parts |
| --- | --- | --- |
| [Fotufilm engine](https://github.com/DhaliwalX/fotufilm-engine) | [`96623ba0`](https://github.com/DhaliwalX/fotufilm-engine/tree/96623ba0831a52dbddcda35727a206d4123a8b5f) | Measured-reflectance priors, separation of brightness from spectral reconstruction, explicit film-base density, print materials, and staged precomputation for GPU execution. |
| [spektrafilm](https://github.com/andreavolpato/spektrafilm) | [`3bb2c2d2`](https://github.com/andreavolpato/spektrafilm/tree/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc) | Film-to-print spectral transport, dye and base separation, development inhibitor couplers, neutral-curve compensation, and chromaticity-to-layer-exposure tables. Avoid as a reference for new work (U12); the notes in this section are kept as a record of the initial research. |
| [spectral_film_lut](https://github.com/JanLohse/spectral_film_lut) | [`bcbcfc68`](https://github.com/JanLohse/spectral_film_lut/tree/bcbcfc6861f49cc706dc5d00ea048e4853060aab) | A large set of hand-digitized data sheets (about 60 negative, print, and reversal materials), Status A, Status M, and Academy Printing Density tables, a split of a single neutral spectrum into three dye bands, Gaussian tails outside the published range, and a color-masking factor through printing density. Inspected after P0; can be adopted directly (U11); see the P0 report, section 10. |

### 3.1 Spectral reconstruction and layer exposure

RGB does not uniquely determine a spectrum. Two spectra can produce the same XYZ and different
film-layer exposures. A small XYZ reconstruction error therefore does not prove an accurate film
response.

Fotufilm uses a prior derived from measured reflectance datasets. Its recovery separates
chromaticity from brightness and includes treatment of saturated colors outside its ordinary
reflectance domain. See its [spectral model](https://github.com/DhaliwalX/fotufilm-engine/blob/96623ba0831a52dbddcda35727a206d4123a8b5f/Sources/FotufilmCore/SpectralModel.swift)
and [data provenance](https://github.com/DhaliwalX/fotufilm-engine/blob/96623ba0831a52dbddcda35727a206d4123a8b5f/THIRD_PARTY_NOTICES.md).

spektrafilm includes a chromaticity-based irradiance reconstruction route and a Mallett/Yuksel
spectral-basis route. Its chromaticity route can precompute the integral against each film layer,
then restore brightness at runtime. See [spectral upsampling](https://github.com/andreavolpato/spektrafilm/blob/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc/src/spektrafilm/utils/spectral_upsampling.py).

Candidate foundations include [Mallett and Yuksel 2019](https://www.cemyuksel.com/research/papers/spectral_primary_decomposition.pdf),
[Jakob and Hanika 2019](https://rgl.epfl.ch/publications/Jakob2019Spectral), and an independently
fitted measured-spectrum prior. Reflectance methods need a defined domain. Emission, extreme
chromaticities, and HDR exposure cannot be handled by assuming every input is a bounded sRGB
reflectance.

### 3.2 Development, dyes, and printing

Treat layer exposure, developed dye amount, measured density, spectral density, and encoded RGB
as different quantities. A manufacturer's Status M or Status A density curve is an instrument
reading. It is not automatically the amount of one isolated dye.

spektrafilm models development inhibitors and compensates the underlying curves so neutral
exposure ramps can retain the supplied characteristic response. This is useful: adding layer
coupling without that constraint can count an effect twice. See [couplers](https://github.com/andreavolpato/spektrafilm/blob/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc/src/spektrafilm/model/couplers.py)
and [printing](https://github.com/andreavolpato/spektrafilm/blob/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc/src/spektrafilm/runtime/stages/printing.py).

Fotufilm represents minimum-density spectra separately and distinguishes capture illumination,
printing illumination, and viewing illumination. These distinctions should remain explicit in
this lab. A change of viewing light must not change already developed dye amounts.

### 3.3 Original measurements do not specify a complete film

[Kodak Portra 400 E-4050](https://business.kodakmoments.com/sites/default/files/files/resources/e4050_portra_400.pdf),
page 4, provides characteristic curves, spectral sensitivity, and minimum-density and midscale
neutral spectra. The neutral spectra do not uniquely identify three isolated image-dye spectra.

[Kodak 2383 technical data](https://www.kodak.com/content/products-brochures/Film/KODAK-VISION-Color-Print-Film-2383-3383-data-sheet.pdf),
page 5, provides peak-normalized dye curves. Their amplitude and relationship to measured
instrument density still require calibration.

Each profile must distinguish original measurements, independently digitized points, inferred
parameters, material-family approximations, and creative controls. Record the source edition,
page, exposure conditions, processing conditions, units, digitization method, and extrapolation.
Published charts constrain a model; they do not prove a complete reconstruction of a commercial
emulsion or a particular laboratory process.

## 4. Proposed image pipeline

```text
Scene-referred RGB with an explicit encoding
  -> linear AP1 / XYZ conversion
  -> ACES RGC at a documented location, accounting for prior application
  -> spectral reconstruction and a defined realizable input domain
  -> film-layer exposure
  -> characteristic response and development coupling
  -> dye amounts + film base and mask contributions
  -> spectral transmission through the negative
  -> printing light and filtration
  -> print-material exposure and development
  -> viewing spectrum and XYZ
  -> explicit display luminance and gamut treatment
  -> output encoding
```

**Scene light (U21, U22).** The scene light is a user control of the product, with daylight as the default and
choices such as tungsten, fluorescent, LED, and sodium. Step P3 adds a scene choice in place of one light ([report](docs/exploration/p3_scan_and_scene.md#7-scene-presets)). It selects the spectrum that multiplies the reconstructed
reflectance before the film-layer exposure. The white point cannot show that a light has spectral spikes, so
this is a choice and not a detection. The [P2 report](docs/exploration/p2_negative_and_print.md#83-night-photos-and-the-scene-light-as-a-product-control-u21) has the first results.

The first experiment should use one negative and one print material with traceable data.
Portra 400 with an Endura-family paper is a candidate, subject to the source-data audit. The
model must support independent negative exposure, print exposure, filtration, and viewing
conditions. A direct-view positive or scan path can share the same physical stages when its
measurements and interpretation are defined.

For layer sensitivity S_i and incident spectral radiance L, relative layer exposure is:

```text
H_i(x) = t * integral L_x(lambda) * S_i(lambda) d(lambda)
```

For a defined additive effective density basis:

```text
D_negative(lambda, x) = D_base(lambda) + sum_i a_i(x) * d_i(lambda)
T_negative(lambda, x) = 10 ^ (-D_negative(lambda, x))
H_print_j(x) = t_print * integral I_print(lambda) * F_print(lambda)
              * T_negative(lambda, x) * S_print_j(lambda) d(lambda)
```

These equations define a starting model, not a claim that every masking process is an
independent positive absorber. An effective basis can include signed changes from consumed
masking material. Validate total spectral density and transmission, and count the base once.
State whether sensitivities use radiometric energy or photon units. Do not apply an extra photon
conversion to a sensitivity curve that already uses the chosen energy convention.

## 5. ACES RGC: scope and checks

Use the [ACES 1.3 RGC specification](https://docs.acescentral.com/rgc/specification/) and its
[implementation guide](https://docs.acescentral.com/rgc/guides/rgc-implementation/).
The standard transform operates through linear AP1 and compresses distances from an achromatic
axis. Its standard domain and parameters must be preserved when claiming the reference behavior.

RGC does not supply a film tone scale, negative inversion, print response, display transfer
function, or a general guarantee that every extreme input lands inside a target display gamut.
It also does not prove that a result admits the bounded reflectance assumed by a reconstruction
method. Test the reconstruction domain separately.

The PoC must compare these cases: input already processed by RGC, input processed once in the
lab, and diagnostic input without RGC. The result must identify the application point and avoid
an accidental repeated application. A target-gamut variant with different parameters or a
different color domain is a separate derived operation. Do not label it the standard ACES RGC.

Display adaptation must preserve the film and print appearance as far as the selected output
permits. Define white, black, luminance scale, and out-of-gamut behavior. Do not append a full
ACES output transform as an implicit extra tone scale.

## 6. Proposed research contributions

### 6.1 Separate spectral shape from exposure

For a reconstruction that is homogeneous in brightness, write L(lambda; c, b) as
b * L_hat(lambda; c), where c is chromaticity and b is a positive brightness scale. Precompute
the integral of L_hat against each layer sensitivity. Restore b at runtime.

Verify that one additional exposure stop multiplies every layer exposure by two. Check the
near-black definition, chromaticity boundaries, and interpolation continuity. This avoids
clipping scene exposure to an ordinary unit RGB cube.

### 6.2 Optimize deterministic wavelength integration for the film process

Build a dense numerical reference first. Fit fixed wavelength nodes and weights against layer
exposure, negative transmission over the density range, print exposure, and viewing XYZ.
Use held-out spectra, illuminants, and density combinations for evaluation.

Do not select a small wavelength count before measuring its error. Narrow sensitivity edges and
light-source peaks can dominate the result. Interpolation of a coarse source chart does not add
measurement information. Report separately the source-data uncertainty and integration error.

### 6.3 Evaluate the response of metamers

Use different measured spectra with similar XYZ to examine variation in film-layer exposure.
Compare XYZ error and layer-exposure error for each reconstruction candidate. Include skin,
foliage, fabrics, saturated objects, and narrowband illumination where suitable data exist.
This evaluates the model's assumptions; it does not recover a unique spectrum from RGB.

### 6.4 Preserve physical stages in GPU precomputation

Compile pointwise spectral operations into separate response tables where the error permits.
Keep film exposure, development, negative-to-print exposure, and viewing independently
inspectable. Keep any measured spatial development effect outside pointwise tables.
Do not fit one final look LUT to upstream renders and call that an independent physical model.

## 7. GPU architecture and Alcedo integration

Use a high-precision host evaluator for numerical reference and parameter preparation. Product
image execution must use the selected GPU backend. A GPU error must report the real failure;
it must not silently select CPU execution, another backend, a smaller image, or a weaker model.

| Shared work | Backend-specific work |
| --- | --- |
| Profile validation, units, characteristic curves, table construction, mathematical definitions, and comparison criteria | Device resources, kernel dispatch, image bindings, transfers, synchronization, and timing |

Use float32 as the initial GPU arithmetic. Check arithmetic and interpolation differences
against the host evaluator. A later precision change needs a separate measured justification.
Keep image intermediates as layer exposures, dye amounts, or ordinary RGB where possible.
For scale: 24 million pixels * 81 bands * 4 bytes is 7.776 GB for one spectral image alone.
This is a storage calculation, not a measured allocation or speed result.

The inspected Alcedo source uses ACEScc AP1 for scene editing. Its diffusion pass decodes that
value to linear AP1 before the DRT. The existing DRT owner exposes focused parameter updates.
The future port should add a method to that owner and use the existing history and export paths.
It must not create a second editable document state for the film model.

Source entry points at the inspected revision:

- [DRT method and parameter owner](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/include/edit/graph/drt_node_model.hpp)
- [Compiled DRT inputs and stages](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/include/edit/runtime/execution_plan.hpp)
- [CUDA DRT](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/edit/runtime/cuda/cuda_drt_pass.cu)
- [Metal DRT](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/edit/runtime/metal/metal_drt_pass.mm)
- [OpenCL DRT](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/edit/runtime/opencl/opencl_drt_pass.cpp)
- [Shared RGC math](https://github.com/zidage/AlcedoStudio/blob/4261b8a5c93e127a13cf96c78b686be3c3430742/alcedo_studio/src/include/edit/runtime/aces_reference_gamut_compression.h)

Alcedo already applies RGC in its camera-color path and again at the current DRT entry.
The new method must account for those locations. It cannot recover color information changed
before its input. The lab does not authorize changing existing Develop behavior.

Existing film grain remains an Alcedo-owned effect. The lab does not require moving it into
negative density, changing its appearance, or adopting either reference project's grain model.

## 8. Route from PoC to MVP

P0 is measured (2026-10-29, [report](docs/exploration/p0_data_and_reference.md)). P1 is measured
for the spectral input (2026-10-30, [report](docs/exploration/p1_spectral_input.md)); its RGC
part is open (U13). P2 is in progress ([report](docs/exploration/p2_negative_and_print.md)). P3 is
closed for now (2026-10-30, [report](docs/exploration/p3_scan_and_scene.md)); its look items move to P4. P4 is closed: the user accepts the look of its print (U32), and the direct inversion is set aside (2026-10-30, [report](docs/exploration/p4_physical_film_response.md)). P5 has results (2026-10-30 and 2026-10-31, [report](docs/exploration/p5_film_and_print_combinations.md)). P6 runs, and the user reports that its result looks good (2026-10-31, [report](docs/exploration/p6_python_mvp.md)). P7 has results for the table construction (2026-10-31, [report](docs/exploration/p7_spectral_acceleration.md)); its check of the table cell boundaries is open. P8 and the MVP are **cancelled** (U70). They are experimental deliverables, not claims of product support. Define numerical tolerances before evaluating each candidate.

| Step | Question and work | Required evidence |
| --- | --- | --- |
| P0: data and reference | Can one negative and print pair be specified from traceable sources? Digitize curves, define units and density meanings, and implement a host spectral evaluator. | Source manifest and hashes; curve overlays; explicit inferred fields; neutral exposure and density checks; dense-integration convergence. |
| P1: spectral input and RGC | Which independent reconstruction gives stable XYZ and film-layer exposure? Compare compact spectral models and a measured-data prior. Verify standard RGC against its published criteria. | Held-out XYZ and layer-exposure errors; exposure scaling; metamer comparison; near-black and saturated-light probes; documented RGC location and residual domain failures. |
| P2: negative and print | Does the complete pointwise process retain the measured characteristic response? Add dye/base separation, development coupling, print exposure, filtration, and viewing conditions. | Neutral and color sweeps; instrument-density reconstruction; total transmission checks; parameter-isolation tests; comparison with available physical measurements. |
| P3: scene presets and scanned-negative output | (a) Can the product offer a scene choice in place of one light, when a night scene mixes tungsten, LED, and sodium? (b) Can a digital intermediate path be simulated: the negative of P2, a scanner, an ADX encoding, and an ACES 1.3 or 2.0 output, in place of a 2383 print? | (a) Definition of each scene as named CIE spectra and weights; user review on night photos; a statement of what a global mixture cannot do. (b) Source and license of the APD responsivities, the ADX encoding, and the ADX to ACES transform; ADX values of a neutral ramp against the published encoding; a statement of which scanner fields are public and which are inferred; user review against a second path that uses the print model of P2; how much difference between stocks each path keeps. |
| P4: physical colour and film response | Why do the colours look wrong, and which physical stages give the look of real film scans? Trace the colour error through the dye chain, add interlayer inhibition, keep colour crossover with timing in density, and add the optics of the layers. Use published sources; no calibration roll (U31). | Coefficient per stage of the colour error; source record for each dye and each inferred field; neutral curve against the published curve; chroma against exposure; crossover of each stock; labeled sheets of landscape files and portraits for each item; user review. |
| P5: other film and print combinations | Which other combinations of film and print material can the model use, and what do the sources specify for each one? (U33) | Source and license record for each candidate; which fields are published and which are inferred; a statement of the combinations that cannot be specified; labeled sheets; user review. |
| P6: Python MVP | Can one Python program take a RAW file through all film and paper data of spectral_film_lut, by the print and by the APD scan (U64; the first version used a Frontier table), at 2048 pixels, with the spectral prior as an option? (U61) | The materials that run and those that do not, with the reason; checks with limits set before the run; labeled review sheets; a command line and a desktop viewer on one pipeline; timings. |
| P7: spectral acceleration | Can staged tables or optimized integration reproduce the direct evaluator across the declared domain? | Maximum and distribution of errors; table-boundary continuity; negative and print density coverage; construction time; resource size. |
| P9: reversal film on a light table | Can the model take a RAW file through a colour reversal film and a light table, with no print, from the published data of each film? (U86) | Source record and a second source for each film; the neutral ramp against the published curve; the light table against the direct integral; labeled sheets; user review. |
| **Cancelled (U70):** P8: three GPU backends | Do CUDA, Metal, and OpenCL execute the same complete model at full image resolution? | Per-backend numerical comparison; device and driver records; cold and warm timings; full-resolution export time; steady and peak memory; explicit failure cases. |
| **Cancelled (U70):** MVP: standalone workflow | Can one program run the selected pipeline, controls, and export with the same results as the experiments? | Shared pipeline used by CLI and a small desktop viewer; repeatable parameter files; backend selection; full-resolution output; cost report; user review of appearance and controls. |

The port to Alcedo Studio replaces P8 and the MVP (U70). Its phases and its acceptance limits are in the [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md). An unavailable device is unverified support.

Use scene-linear float images with explicit primaries and white point for controlled experiments.
Do not add a second RAW decoder to this lab by default. Inputs prepared by Alcedo must record the
export stage, encoding, exposure scale, and previous RGC processing. A standalone reference input
must remain available so the tests do not require an Alcedo GUI session.

Suggested future paths follow the AI Mask Lab structure:

| Proposed path | Purpose |
| --- | --- |
| `docs/research/` | Source analysis, material data, papers, and algorithm comparisons. |
| `docs/exploration/` | One report per experiment and an index of measured status. |
| `scripts/poc/` | Reproducible reference experiments and evaluation commands. |
| `src/` | Shared model code and the CUDA, Metal, and OpenCL implementations. |
| `profiles/` | Independently prepared material descriptions with provenance and licenses. |
| `results/` | Small, redistributable measurements and result summaries. |
| `build/tmp/` | Uncommitted source downloads, intermediate files, private photos, and local evidence. |

`docs/exploration/`, `scripts/poc/`, `profiles/`, and `results/` exist since P0; `src/` does not
exist yet. Never publish source photos, downloaded assets, or manufacturer documents without
checking redistribution rights.

## 9. Evidence required before the Alcedo port

- A one-stop exposure increase doubles each layer exposure before development.
- Neutral ramps reproduce the declared source curves within predeclared tolerances.
- Development coupling preserves the neutral calibration used to fit the model.
- Film base is counted once; total transmission is finite and physically admissible.
- Print exposure and filtration affect the print stage; viewing light leaves dyes unchanged.
- Staged GPU calculations match direct spectral calculations across the declared input domain.
- RGC matches the published implementation criteria in its standard form. Any variant is named
  and evaluated separately.
- Each backend passes independent comparisons with the host evaluator. Agreement among three
  ports alone does not establish a correct physical model.
- Near-black values, high exposure, chromaticity edges, density limits, and table seams remain
  continuous and free of NaN or infinite output for valid inputs.
- Profile or illumination changes update the resources they affect without reusing stale tables.
- Full-resolution image processing and export run without a quality or backend substitution.
- The cost report states the build type, hardware, drivers, resolution, active effects, table
  preparation, first render, warm latency distribution, and memory measurement method.
- User review of film appearance and controls is recorded separately from numerical checks.

## 10. Independent implementation, data, and licensing

Use public physical principles, original publications, and independently prepared datasets.
Record how each algorithm and profile was derived. Code, methods, and data of spectral_film_lut
(MIT) can be adopted directly (U11); Fotufilm (Apache-2.0) can be used as a reference (U12).
Label each reuse as reuse in the code and the report and keep its notice in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Avoid spektrafilm as a reference for new work
(U12). Do not call a result independent when it reuses upstream constants, tables, or code.

This initial research reads upstream source code. It is not a strict separation between
researchers who inspect code and implementers who do not. Describe future work accurately as an
independent implementation from published principles and documented measurements unless a
separate process establishes a stronger claim.

The inspected Fotufilm engine is Apache-2.0; its listed film profiles are CC BY-SA 4.0, and
other assets have their own notices. See [licensing](https://github.com/DhaliwalX/fotufilm-engine/blob/96623ba0831a52dbddcda35727a206d4123a8b5f/LICENSING.md).
Apache-2.0 code can be included in a GPLv3 project with the required notices; see the
[Apache explanation](https://www.apache.org/licenses/GPL-compatibility.html).

spektrafilm code uses GPLv3. Its inspected [profile and LUT license](https://github.com/andreavolpato/spektrafilm/blob/3bb2c2d2801ff68b92019cf1dbcbb133d60832bc/SPEKTRAFILM_LICENSE.txt)
states CC BY-SA 4.0 and separately lists requests beyond the legal requirements. The inspected
README also contains different wording about LUT licensing. Check the exact asset and revision
before importing it; this repository does not redistribute those assets.

[spectral_film_lut](https://github.com/JanLohse/spectral_film_lut) (MIT) was inspected at
[`bcbcfc68`](https://github.com/JanLohse/spectral_film_lut/tree/bcbcfc6861f49cc706dc5d00ea048e4853060aab)
after P0. P0 compares its hand-digitized Portra 400 and Endura Premier data and its Status A and M
tables with the lab data, and ports three of its methods as options (P0 report, section 10;
notice in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

Independent digitization does not automatically establish redistribution rights for a source
publication. Preserve provenance and check source-data terms. A model derived from a dataset
does not become rights-free because its storage format changes.

Useful independent data starting points:

- [CIE 1931 2-degree observer](https://cie.co.at/datatable/cie-1931-colour-matching-functions-2-degree-observer): official color-matching function data at 1 nm intervals.
- [rawtoaces-data](https://github.com/AcademySoftwareFoundation/rawtoaces-data): camera sensitivities, illuminants, observer functions, and training spectra. Check each dataset's metadata and license.
- [USGS Spectral Library Version 7](https://doi.org/10.5066/F7RR1WDJ): measured material spectra; inspect individual records for suitability.
- [NIST human skin reflectance reference data](https://doi.org/10.6028/jres.122.026): a candidate source for independent skin-spectrum evaluation.

## License

Project-authored material is licensed under **GPL-3.0-only**. See [LICENSE](LICENSE).
Third-party materials keep their own terms. No upstream film profiles, LUTs, grain code, or
manufacturer documents are included. Most profiles use data of spectral_film_lut (MIT, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). The `profiles/` files contain values digitized from Kodak
data sheets; they can be published (U10). The Kodak PDFs are not in the repository
([profiles/README.md](profiles/README.md#source-documents-not-distributed)).
