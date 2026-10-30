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
