# Third-party notices

Project-authored material is GPL-3.0-only (see [LICENSE](LICENSE)). This file lists third-party
code and data that the repository contains or reuses, with their notices.

## spectral_film_lut

- Source: <https://github.com/JanLohse/spectral_film_lut>, commit
  `bcbcfc6861f49cc706dc5d00ea048e4853060aab`.
- Reused in `scripts/poc/p0_data_and_reference/film_spectral_reference.py`:
  - the Gaussian tail extension of spectral data (`gaussian_extrapolation`);
  - the split of a neutral density spectrum into three dye bands (`construct_spectral_density`);
  - the linear extension of log sensitivity outside the published domain.
- Reused in `profiles/`: the digitized data of KODAK VISION3 5207, 5219 and VISION 2383, through
  `scripts/poc/p2_negative_print/import_cine_profiles.py`. Through
  `scripts/poc/p4_physical_film_response/import_dyes_and_mtf.py`: the isolated dye curves of 5207
  and 5219, and the modulation transfer curves of 5207, 5219, and Portra 400. Through
  `scripts/poc/p5_film_and_print_combinations/digitize_stock_charts.py`: all digitized data of
  Fujicolor C200, and the spectral sensitivity of KODAK GOLD 200.
- Use without reuse: `compare_spectral_film_lut.py` reads its digitized data and Status tables as
  comparison data only. These files are not in this repository.

```text
MIT License

Copyright (c) 2026 Jan Lohse

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## ACES (aces-dev)

- Source: <https://github.com/ampas/aces-dev>, tag v1.3.1, `transforms/ctl/csc/ADX/ACEScsc.Academy.ADX10_to_ACES.ctl`.
- Reused in `scripts/poc/p3_scan_and_scene/aces_scan.py`: the constants and steps of the ADX10 to ACES transform.

```text
Copyright (c) 2015 Academy of Motion Picture Arts and Sciences (A.M.P.A.S.).
Portions contributed by others as indicated. All rights reserved.

Disclaimer of Warranty: THIS SOFTWARE IS PROVIDED BY A.M.P.A.S. AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
NON-INFRINGEMENT ARE DISCLAIMED. IN NO EVENT SHALL A.M.P.A.S., OR ANY
CONTRIBUTORS OR DISTRIBUTORS, BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, RESITUTIONARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

WITHOUT LIMITING THE GENERALITY OF THE FOREGOING, THE ACADEMY SPECIFICALLY
DISCLAIMS ANY REPRESENTATIONS OR WARRANTIES WHATSOEVER RELATED TO PATENT OR
OTHER INTELLECTUAL PROPERTY RIGHTS IN THE ACADEMY COLOR ENCODING SYSTEM, OR
APPLICATIONS THEREOF, HELD BY PARTIES OTHER THAN A.M.P.A.S.,WHETHER DISCLOSED OR
UNDISCLOSED.
```

The name A.M.P.A.S. and the names of contributors are not used to endorse this project. The complete license terms are in `LICENSE.md` of that tag.

## Data read at run time (not in this repository)

| Data | License | Use |
| --- | --- | --- |
| CIE colour-matching functions and illuminants | CC BY-SA 4.0 | downloaded by `fetch_sources.py` |
| python-colormath `density_standards.py` (ANSI Status A and M tables) | BSD-3-Clause | downloaded by `fetch_sources.py`, read as data |
| Kodak data sheets E-4050 and E-4070 | not distributed (README U10) | downloaded by `fetch_sources.py`; the digitized values in `profiles/` are made by this lab |
| rawtoaces-data (Academy Software Foundation), commit `e9b8503c`: 190 training spectra, 21 camera sensitivities | Apache-2.0 | P1: downloaded by `scripts/poc/p1_spectral_input/fetch_sources.py`, read as data |
| Gutierrez, Silva, Fanchini, Morimoto, Barrionuevo, Sandoval-Salinas, *Spectral dataset of natural objects' reflectance from the Southern cone of South America*, doi:10.6084/m9.figshare.25705380 (v4) | CC BY 4.0 | P1: test and prior training data, read at run time; no derived table is committed |
| Lu et al., *The International Skin Spectra Archive (ISSA)*, doi:10.6084/m9.figshare.28228571 (v4) | CC BY 4.0 | P1: test and prior training data, read at run time; no derived table is committed |
| Clark et al., *USGS Spectral Library Version 7*, doi:10.5066/F7RR1WDJ | U.S. public domain | P1: test and prior training data, read at run time |
| CIE 015:2018 FL, LED, and HP illuminant tables | CC BY-SA 4.0 | P1: scene lights |
| SMPTE ST 2065-2:2020 tables and ST 2065-3:2020 | SMPTE copyright, all rights reserved | P3: downloaded by `scripts/poc/p3_scan_and_scene/fetch_sources.py`, read at run time; not committed |
| Film Analyzer public chart measurements (<https://filmanalyzer.talkativephotographer.com/>) | not stated | P3: read at run time as a comparison, kept in `build/tmp/`; the report quotes a few values with the source; the model is not fitted to them |
| OpenColorIO 2.6 (Academy Software Foundation) | BSD-3-Clause | P3: ACES output transforms, installed as a Python package; not redistributed |

## Methods from publications (no code reused)

P1 implements these methods from their publications: L. Mallett and C. Yuksel, *Spectral Primary
Decomposition for Rendering with sRGB Reflectance* (EGSR 2019); W. Jakob and J. Hanika, *A
Low-Dimensional Function Space for Efficient Spectral Upsampling* (Eurographics 2019); the
primal active-set method of J. Nocedal and S. Wright, *Numerical Optimization* (2nd ed.,
algorithm 16.3). The brightness normalization 2 max(rgb) of the sigmoid follows pbrt-v4
`RGBIlluminantSpectrum` (rule only; no pbrt-v4 code is used). The P1 dataset selection follows
the Fotufilm third-party notices (reference, README U12).

P5 reuses, with a label, the method of the uncalibrated Auto Invert of [NexFilm](https://github.com/BillyDu-TJ/NexFilm)
(commit `fbd7113f4b0d34c0fa84fc8601b6c5a13a742df1`, GPL-3.0-only, the license of this project) in
`scripts/poc/p5_film_and_print_combinations/render_density_window.py`: the order of the steps, the
endpoints from the same pixels, and the tail of 2% on a grid of 512. The code is written for this
lab, and the repository contains no NexFilm source file. The user also ran NexFilm as an external
program on local files.

P2 runs spektrafilm (`3bb2c2d2`, GPLv3; profiles CC BY-SA 4.0) and the Fotufilm engine (v1.14.1,
Apache-2.0; profiles CC BY-SA 4.0) as external programs to compare appearance (README U18). This
repository contains no code, table, or profile from them. The P2 exposure target, display white
choice, and interlayer gain were selected by comparison with spektrafilm output, so that appearance is
not an independent result. P2 test portraits come from the free RAW collection of
[Signature Edits](https://www.signatureedits.com/free-raw-photos/) under its
[license](https://www.signatureedits.com/free-raw-license-terms/). The photos stay local and are not
redistributed here; each photo stays the work of its photographer.
