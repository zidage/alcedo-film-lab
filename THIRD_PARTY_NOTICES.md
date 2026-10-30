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
  `scripts/poc/p2_negative_print/import_cine_profiles.py`.
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

## Methods from publications (no code reused)

P1 implements these methods from their publications: L. Mallett and C. Yuksel, *Spectral Primary
Decomposition for Rendering with sRGB Reflectance* (EGSR 2019); W. Jakob and J. Hanika, *A
Low-Dimensional Function Space for Efficient Spectral Upsampling* (Eurographics 2019); the
primal active-set method of J. Nocedal and S. Wright, *Numerical Optimization* (2nd ed.,
algorithm 16.3). The brightness normalization 2 max(rgb) of the sigmoid follows pbrt-v4
`RGBIlluminantSpectrum` (rule only; no pbrt-v4 code is used). The P1 dataset selection follows
the Fotufilm third-party notices (reference, README U12).

P2 runs spektrafilm (`3bb2c2d2`, GPLv3; profiles CC BY-SA 4.0) and the Fotufilm engine (v1.14.1,
Apache-2.0; profiles CC BY-SA 4.0) as external programs to compare appearance (README U18). This
repository contains no code, table, or profile from them. The P2 exposure target, display white
choice, and interlayer gain were selected by comparison with spektrafilm output, so that appearance is
not an independent result. P2 test portraits come from the free RAW collection of
[Signature Edits](https://www.signatureedits.com/free-raw-photos/) under its
[license](https://www.signatureedits.com/free-raw-license-terms/). The photos stay local and are not
redistributed here; each photo stays the work of its photographer.
