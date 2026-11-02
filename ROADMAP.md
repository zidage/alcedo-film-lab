# Alcedo Film Lab: roadmap and decisions

This file is the source of truth for the requirements, the user decisions, and the route of this repository (U65). The [README](README.md) is the public overview. Results and text before 2026-10-31 that say "README U..." or "README section ..." mean this file.

Research and prototypes for a spectral film simulation pipeline and a new Display Rendering
Transform (DRT) for [Alcedo Studio](https://github.com/zidage/AlcedoStudio).

The goal is to model film exposure, development, dye absorption, and printing from published
principles and source measurements. The implementation must support **CUDA, Metal, and OpenCL**.
The research combines useful ideas from **Fotufilm** and **spektrafilm**, with independent code
and data preparation where practical.

**Status (2026-10-31): P0 to P7 have results. P8 and the MVP are cancelled (U70): the work continues in Alcedo Studio.** The Python
program of P6 takes a RAW file to an image by the print or by the APD scan, on 30 negatives and 18
print materials, on the CPU. There is no GPU measurement. The product integration is not done; its plan is the [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md). The step index is
[docs/exploration/README.md](docs/exploration/README.md). Agent rules are in
[AGENTS.md](AGENTS.md).

**ACES means ACES Reference Gamut Compression (RGC) in this project.** The one exception is the APD
method of P6 (U64), which follows the standard chain to an ACES output transform. **Film grain is outside this research:**
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

## 2. User requirements

These requirements come from the user on 2026-10-29. The technical choices below are proposals
until experiments support them.

| ID | Requirement |
| --- | --- |
| U1 | Add a new DRT method built around a film simulation pipeline. |
| U2 | Study Fotufilm and spektrafilm and combine their useful principles. |
| U3 | Provide GPU acceleration on CUDA, Metal, and OpenCL. |
| U4 | Prefer an independent implementation from basic principles, papers, and original film data. |
| U5 | Research improved spectral reconstruction and wavelength sampling methods. |
| U6 | Use ACES RGC for gamut compression. This requirement does not select ACES 2 tone mapping or its complete output transform. |
| U7 | Reuse Alcedo's existing film grain implementation. Do not develop or replace grain in this lab. |
| U8 | Keep the model suitable for Alcedo's existing scene-referred architecture. |
| U9 | Use a public lab repository and progress from PoC to MVP. The initial delivery is this README. |
| U10 | (2026-10-29) Do not publish the original Kodak documents (data sheet PDFs). The data that the lab scripts make from them (digitized profiles, results) can be published. |
| U11 | (2026-10-29) spectral_film_lut is MIT. Its methods, code, and data can be adopted directly; keep its notice ([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). No separate re-derivation is required. |
| U12 | (2026-10-29) Fotufilm (Apache-2.0) can be used as a reference. Avoid spektrafilm as a reference for new work as far as possible. |
| U13 | (2026-10-29) RGC is out of scope of step P1 for now. P1 measures the spectral input without RGC; the RGC verification and its location stay open. The user also supplied the RAW library of the Alcedo Studio tests for P1 and pointed to rawtoaces-data as a data source. |
| U14 | (2026-10-30, delegated to the P1 step by the user) Inputs with Y <= 0 give zero radiance; inputs outside the reachable spectral cone move toward the reference white at constant Y to the cone boundary (rule `spectral_locus_projection`). This rule is not RGC. |
| U15 | (2026-10-30, delegated to the P1 step by the user) P1 layer acceptance per dataset under daylight: Status M error p95 at most (0.025, 0.011, 0.054), the between-dataset metamer p95, and signed median at most 0.01. The max is reported and is not a criterion. |
| U16 | (2026-10-30) The DRT receives no camera identity; the method must generalize across cameras. Camera sensitivities can only simulate input and build a population statistic. |
| U17 | (2026-10-30) The scene white is available for RAW input. Non-RAW input is assumed to have the ACES white. The priority is the final rendered appearance, which must be pleasing; do not over-engineer the model for numeric accuracy. |
| U18 | (2026-10-30) Set an appearance baseline: the render must look at least near the reference projects. spektrafilm is run as an external comparison for this purpose (exception to U12); its code, tables, and profiles are not reused. A result that follows its output is not independent. Portrait RAW files are the main test images. |
| U19 | (2026-10-30) The chroma is too high and the texture is poor: take ideas from the traditional darkroom process. KODAK VISION3 5207 and 5219 are important stocks. The display gamut compression can follow the method of the ACES RGC. |
| U20 | (2026-10-30) Restore the tungsten character of 5219. LED and fluorescent spectra differ strongly from daylight, so the scene light is a spectrum and not only a white point. |
| U21 | (2026-10-30) Product requirement: the user can select the scene light manually. The default is daylight. Options include fluorescent and LED, and the selection changes the spectral reconstruction, mainly for night photos. |
| U22 | (2026-10-30) The product should offer a scene choice rather than one light, because a night photo usually mixes tungsten, LED, and sodium. This extends U21. |
| U23 | (2026-10-30) Simulate the modern film workflow in addition to the 2383 print: scan the negative, encode as ADX, and export through ACES 1.3 or 2.0. Inside this path only, the ACES output transform is the display rendering (exception to U6 for this path). The first version uses ADX with published APD responsivities as an ideal scanner. Scanner candidates for later: ARRISCAN, Blackmagic Cintel. ALEV III reference: the estimate of [Yellowmoon](https://github.com/ngriaznov/yellowmoon). Both items are step P3 (section 8). See the [source audit](docs/research/modern_film_scan_workflow.md). |
| U25 | (2026-10-30) Most users now scan a developed negative directly and do not print. Film Analyzer is a reference to learn the effect of this practice; its data is not adopted. Review sheets carry a label with the method on every panel, on a broad image set that includes more of signatureedits.com and the Alcedo Studio sample images. |
| U26 | (2026-10-30) ADX to ACES is dropped from the product direction. The product keeps two rendering methods: the print model and the classic scan (direct inversion). Colour errors of a scanner are wanted: cine film is accurate, and the scan adds the character. This replaces the display rendering part of U23; the ACES exception of U6 no longer applies to a product path. |
| U27 | (2026-10-30) The classic scanner data (for example Fuji Frontier, Noritsu, Hasselblad Flextight) can be used. A license review is deferred. The release must state that these are style simulations with no endorsement from any manufacturer. Until the release, vendor files stay under `build/tmp/` by the rule of AGENTS.md. |
| U28 | (2026-10-30) Chart measurements of Film Analyzer can be used for tests only, because the site states no license. A scanner model fitted to them, its parameters, and its images stay under `build/tmp/` and no product path uses them. |
| U29 | (2026-10-30) The current review paths are the print and the direct inversion with APD. The other scanner styles (Frontier light, Noritsu curve, X5 table, fitted test model) stay as a record of the process and are not in the current review. The classic scan gets an algorithmic density crosstalk. Breaks in the hue sweep must be solved by an algorithm. See the [P3 report](docs/exploration/p3_scan_and_scene.md), section 13. |
| U30 | (2026-10-30) The direct inversion is too hard and looks digital. The target is the subtle, soft look of real scans of 5207, 5219, and Portra. Grain is not part of this work. Scans from the web are a style reference only, stay under `build/tmp/`, and no value is copied from them to a product path (as in U28). See the [P3 report](docs/exploration/p3_scan_and_scene.md), section 13.4. |
| U31 | (2026-10-30) A calibration roll is not possible. The next step, P4, works on four physical items from published sources and first principles: the colour error through the dye chain, interlayer inhibition (DIR couplers), colour crossover with timing in density, and the optics of the layers. Spectral acceleration and the GPU backends move later and become P5 and P6. See the [P4 report](docs/exploration/p4_physical_film_response.md). |
| U32 | (2026-10-30) The user accepts the look of the P4 print and closes P4. The direct inversion with APD is set aside and has no accepted look. A colour lean is a part of the style of a stock: a red lean on Portra 400 is a characteristic, not a fault. See the [P4 report](docs/exploration/p4_physical_film_response.md), section 13. |
| U33 | (2026-10-30) The next step, P5, is an investigation of other combinations of film and print material. Spectral acceleration and the GPU backends move later and become P6 and P7. |
| U34 | (2026-10-30) P5 starts with the popular stocks in current production: C200, Ektar, Gold 200, and Portra 160, 400, and 800. The other stocks are set aside for now. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md). |
| U35 | (2026-10-31) Backlit areas of high contrast scenes look dirty, for example the 8 mountain files `_DSC4049` to `_DSC4306`. spektrafilm has the same fault, so a solution is a contribution of this project to the community. `lumix_l10` is not a test file for this item, because its colour matrix is wrong. The user proposes a shadow mode: expose the negative to the right. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 11. |
| U36 | (2026-10-31) A colour cast is not a fault of a film simulation. The cast and the character of each stock are wanted, and each stock must show them. Work from the physical process, and do not dwell on a cast. The user sees a large improvement with the contrast mask probe and sees no cast from it. See [AGENTS.md](AGENTS.md). |
| U37 | (2026-10-31) Try this practice with the pipeline of this lab: give the simulated orange negative, not inverted, to an automatic inversion program such as NexFilm. Other programs use similar methods. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 12. |
| U38 | (2026-10-31) The user result of NexFilm Auto Invert on the linear Portra 400 TIFF files, with the Film Area on the entire frame, is very good and nearly meets the expectation of the user. Learn the algorithm. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 13. |
| U39 | (2026-10-31) Is the method of NexFilm scientific? D-min and Dmax are known in this pipeline, so research a more scientific method from published scan workflows. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 14. |
| U40 | (2026-10-31) Try both proposals of section 14: a density matrix per stock, and a paper with less contrast. The upper endpoint of an image comes from a window on the image. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 15. |
| U41 | (2026-10-31) Do not try to reduce the chart error. The look target is soft, and the daylight and night files must be checked too. Direct density as display code looks good. A window on each frame may not be efficient, so try the step back from density through the stock curve. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 16. |
| U42 | (2026-10-31) The fixed direct mapping with a shoulder is the most promising. Night files look too light. Bring 5207 and 5219 to two looks from reference images of the user: a low key soft look from a DaVinci plugin, and a look of the kind of Lost in Translation. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 17. |
| U43 | (2026-10-31) Halation and glow are already in the product. On the 5219 look, street lamps are too green. A third group of reference street scenes is nearer to the target. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 18. |
| U44 | (2026-10-31) The look of section 18 of the P5 report is still not right. Ask GPT-6.1 Sol for an independent view. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 19. |
| U45 | (2026-10-31) Exposure +1.5 EV, contrast 15, and saturation +30 are in the product, and the built-in film module must take them into account. Test on good photographs. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 20. |
| U46 | (2026-10-31) Density compensation is the right direction. High saturation colours are out of scope for now. Colours are too thin, with no blue shadows, like a log image; this is a process problem. Start from the linear scan and apply the published scan recipes. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 21. |
| U47 | (2026-10-31) Try the levels recipe with exposure to the right. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 22. |
| U48 | (2026-10-31) Ask GPT-6.1 Sol to understand the state of the work and to give its own proposal. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 23. |
| U49 | (2026-10-31) Use candidate B of the second review as the base, and try warm pixels under tungsten light. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 24. |
| U50 | (2026-10-31) Run the two-light probe on the night RAW files of the user. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 24. |
| U51 | (2026-10-31) Run the two-light probe on 13 Hong Kong night RAW files of the user. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 24. |
| U52 | (2026-10-31) Candidate B is still not soft. Export the Hong Kong files as linear TIFF files with the orange base for NexFilm, and study the difference from real 5219. See the [P5 report](docs/exploration/p5_film_and_print_combinations.md), section 25. |
| U53 | (2026-10-31) Do not use one-dimensional Lab measures. Split base and detail with a local Laplacian filter, and learn the colour distributions. See section 25 of the same report. |
| U54 | (2026-10-31) Test proposals from a third person on the scan path: separate the scanner from the display preparation, split density into an exposure coordinate and a colour residual, use density-domain multiscale rendering, and keep scene light apart from scan balance. Test on representative files. See section 26 of the same report. |
| U55 | (2026-10-31) All results of U54 are rejected. The scan path must be thought through again from the orange film base, and this work is on hold. Output the review files through the print, with candidate B as the comparison. See sections 26 and 27 of the same report. |
| U56 | (2026-10-31) The user supplies 5207 negatives scanned on a Hasselblad X5, and asks how they can be used. See section 28 of the same report. |
| U57 | (2026-10-31) The user supplies a digital RAW file of one scene on the 5207 strips. This is the first true pair of this lab. See section 29 of the same report. |
| U58 | (2026-10-31) For the scan work: no exposure to the right, no `grey_anchor`, the plain APD read, and mask removal tried on the real film. See section 30 of the same report. |
| U59 | (2026-10-31) Try the real 5207 negatives through the 2383 print, with no exposure to the right and no `grey_anchor`. See section 31 of the same report. |
| U60 | (2026-10-31) The print of the real 5207 negatives is acceptable to the user. Try the Hong Kong day files. See section 32 of the same report. |
| U61 | (2026-10-31) The product has two methods: the print, and the classic scan with the Frontier table of NegPy. HyperTone is not used. The spectral prior stays a user option. The product holds all film and paper data of spectral_film_lut. This set becomes step P6, a Python MVP with RAW input and a processing size of 2048 pixels on the long edge. Spectral acceleration and the GPU backends move later and become P7 and P8; earlier reports use the old numbers. See the [P6 report](docs/exploration/p6_python_mvp.md). |
| U62 | (2026-10-31) The user compared the P6 print with spektrafilm side by side on one file, prefers the soft look of P6, and asked for more options. The MVP exposes the values of the model as user controls; the defaults keep the image. See the [P6 report](docs/exploration/p6_python_mvp.md), section 5.1. |
| U63 | (2026-10-31) The product includes the Frontier table of NegPy. The user's reason: NegPy distributes it, and the machine left production long ago. This replaces the deferred license review of U27 for this table and accepts the risk: the table has no license from Fujifilm. The other text of U27 stays: the release states that this is a style simulation with no endorsement from any manufacturer. The table stays out of this repository until the product packaging is made. |
| U64 | (2026-10-31) The Frontier method is dropped, and this replaces U63 and the scan part of U61. The second method of the product is APD, made as the standards state: APD (ST 2065-2), ADX10 (ST 2065-3), the mid grey at code value 445, the ADX10 to ACES transform, and an ACES output transform. This is an exception to U26 for this method. The standards do not define a display rendering other than the ACES path. See the [P6 report](docs/exploration/p6_python_mvp.md), section 5.3. |
| U65 | (2026-10-31) The user reports that the current result looks good. The repository gets a public README with the whole process, the results, figures, and the difference from spektrafilm. The former README becomes this file. Figures can use processed photos of Signature Edits (exception to the photo rule of AGENTS.md, for these files only). Its license does not grant the image of a recognizable person, a brand, or a work of art, so the figures from it show landscapes and still lifes only. |
| U66 | (2026-10-31) The two mountain photos of the README are not attractive. The user replaces them with two of their own Hong Kong photos, `P2625280` and `P2625314`, at +3 EV in place of +1.5 EV, because both are underexposed. These files are a second exception to the photo rule of AGENTS.md. |
| U67 | (2026-10-31) The README is an introduction and not a summary of experiments: it presents the current MVP and its algorithm, with no step list and no Lab analysis. This replaces the part of U65 on the whole process in the README. The process stays in the reports. |
| U68 | (2026-10-31) The first priority after P6 is the speed of table construction. The final logic runs in C++, and the user keeps testing in the Python viewer, so one C++ library builds the tables for both. The print tables and the APD tables are not stored on disk: they are built when a model needs them and dropped after use. See the [P7 report](docs/exploration/p7_spectral_acceleration.md). |
| U69 | (2026-10-31) The first product version has the print method only. The user removes APD from it because its look is not good; this replaces the product part of U61 and U64, and the lab code stays. The criterion for an exposed control is that a user can understand it, not only the size of its effect. The product exposes the film and print material choices and three controls: light spread, halation, and enlarger flare. All other values of `mvp_pipeline.CONTROLS` and the spectral prior stay fixed at their defaults; this replaces the option of the prior in U61 and the set of controls in U62 for the product. The user confirms the three selections: film, print material, and scene light. The product default grade already exists in Alcedo Studio. Halation has one strength control, and its length stays fixed. The user prefers the halation of this model to the existing Alcedo Studio operator, because its colour comes from the layers of the film and the existing colour is fixed near red. The product has one spectral prior, `light_like`, and no `measured_reflectance`. The output is Rec. 709 SDR only, with no HDR. The existing Halation operator of Alcedo Studio is skipped when the film print method is selected. The Python viewer keeps all controls for tests. |
| U70 | (2026-10-31) The steps P8 and MVP are cancelled. A standalone GPU program would only repeat the device, resource, cache, and test work that Alcedo Studio already has, so the work goes directly to Alcedo Studio: first the host tables, then the model and compile steps, then the CUDA passes, the editor, and Metal and OpenCL. See the [Film Print DRT Plan](https://github.com/zidage/AlcedoStudio/blob/main/docs/roadmap/alcedo_studio/edit/film_print_drt_plan.md). Speed comes before numeric accuracy. On images, development inhibition has two fixed-point steps, with a half-size blur when its sigma is at least 4 pixels (rules `inhibition_two_steps`, `inhibitor_on_half_size`), and the layer spread has two passes with a kernel per layer (rule `spread_per_layer_pass`). The Python viewer uses these rules. See the [P7 report](docs/exploration/p7_spectral_acceleration.md), section 5.3. |
| U71 | (2026-10-31) The user reports that the Fuji stocks other than C200 have faults, from their data. Measurement: a grey of the balance light falls up to 4.3 stops from its exposure on the curve, onto the toe, because these charts have no usable level. This holds for 7 Fuji stocks, 5 Kodak stocks, and Agfa Vista 100. Rule `relative_sensitivity_level` of P6 used another exposure path and did not find them. New rule `grey_off_the_curve`: more than 1 stop on any layer gives the stock rule `grey_anchor`, as C200 has. The profiles do not change, and the 8 accepted stocks do not change. See the [P7 report](docs/exploration/p7_spectral_acceleration.md), section 5.4. |
| U72 | (2026-11-01) The user reviewed the final rules of U70 and the stock repair of U71, and accepts them: "the effect is amazing". The default scene light of the product is `reference`, which replaces the default of U21. The default DRT of a new document stays OpenDRT. |
| U73 | (2026-11-01) The user compared the Portra 160 print of the Cuihu DNG files with Noritsu scans of real Portra 160, and found the simulation too yellow. Trace: the foliage turns yellow in the negative and more in the print, because the reflectance prior has no chlorophyll band. The user chose the print with the new rule `foliage_spectra` ("the middle one is what I want") and asked for it on the main stocks. The rule is on by default for all stocks in the Python viewer. See the [P6 report](docs/exploration/p6_python_mvp.md), section 5.4. The resources of Alcedo Studio have the rule from lab commit `f7084c0` ([Alcedo Studio issue 635](https://github.com/zidage/AlcedoStudio/issues/635)). |
| U74 | (2026-11-01) The user reports that Eterna 500 looks sharpened, in the Python viewer and in the product (Alcedo Studio issue 642). Trace: the fits of P4, P5, and P6 discard their inhibitor length, and on a chart with no rise above 1 they stop at B = 2 with a length under 7 um. The render uses 35 um, so it has a rise that the chart does not have: 1.64 against 1.00 on Eterna 500. K also sets the colour of a flat area, which U72 accepts, so K stays as the total. New rule `inhibition_image_part`: only the part of K that a fit at 35 um supports has a blur. The user asks for no increase of the render time. See the [P7 report](docs/exploration/p7_spectral_acceleration.md), section 5.6. The user review of the new look is open. |
| U24 | (2026-10-30) The film chain is evaluated after the default Color Grade of Alcedo Studio for RAW files (contrast +15, saturation 1.3), because the DRT receives the graded image. The chain does not repeat that colour gain and contrast. See the [P2 report](docs/exploration/p2_negative_and_print.md), section 8.5. |

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
