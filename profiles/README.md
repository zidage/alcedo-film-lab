# Profiles

Material descriptions of the film model. Each file states its source document, the chart, the
stated conditions, the quantity and unit of each axis, and the provenance of the values.

| File | Material | Source | Provenance |
| --- | --- | --- | --- |
| [`kodak_portra_400.json`](kodak_portra_400.json) | KODAK PROFESSIONAL PORTRA 400 (C-41 negative) | E-4050, Revised 2-16, page 4 | digitized points (PDF vector paths) |
| [`kodak_endura_premier.json`](kodak_endura_premier.json) | KODAK PROFESSIONAL ENDURA Premier Paper (RA-4) | E-4070, Revised 12-17, pages 4 and 5 | digitized points (PDF vector paths) |
| `kodak_5207.json`, `kodak_5219.json`, `kodak_2383.json` | KODAK VISION3 250D 5207, VISION3 500T 5219, VISION 2383 | spectral_film_lut (MIT) at `bcbcfc68` | digitized by that project; linearly resampled by `scripts/poc/p2_negative_print/import_cine_profiles.py`; not checked against Kodak documents |
| `kodak_portra_160.json`, `kodak_portra_800.json`, `kodak_ektar_100.json` | KODAK PROFESSIONAL PORTRA 160, PORTRA 800 (EI 800), EKTAR 100 | E-4051 Revised 1-25, E-4040 Revised 1-25, E-4046 Revised 1/25 | digitized points (PDF vector paths), `scripts/poc/p5_film_and_print_combinations/digitize_stock_charts.py` |
| `kodak_gold_200.json` | KODAK GOLD 200 | E-7022 Revised 06-23 | digitized points (PDF vector paths), except the sensitivity, from spectral_film_lut (MIT) at `bcbcfc68`. No modulation transfer chart |
| `fuji_c200.json` | FUJICOLOR C200 | AF3-0249E (17.05-BX), raster charts | spectral_film_lut (MIT) at `bcbcfc68`, not digitized by this lab. Relative sensitivity; one modulation transfer curve, copied to the three layers |

`import_dyes_and_mtf.py` (step P4) adds the isolated dye curves of 5207 and 5219 and the chart `modulation_transfer` of 5207, 5219, and Portra 400, from spectral_film_lut (MIT) at `bcbcfc68`. These were not checked against Kodak documents. Run it again after `import_cine_profiles.py` or `digitize_kodak_charts.py`.

`digitize_kodak_charts.py` (step P0) writes these files. The curves are resampled on 1 nm
(spectral charts) or 0.01 log10 lux-seconds (characteristic charts) inside the published domain
only. There is no smoothing and no extrapolation in the files. The inferred fields of the model
(the negative dye basis, the paper base, the light sources) are not in these files; the
[P0 report](../docs/exploration/p0_data_and_reference.md#5-inferred-fields) lists them.

## Source documents (not distributed)

The original Kodak documents are **not** in this repository and must not be committed
(README decision U10). Only the data that the lab scripts make from them is published.

| Document | Download | SHA-256 |
| --- | --- | --- |
| KODAK Publication No. E-4050, PORTRA 400, Revised 2-16 | [Kodak Alaris](https://business.kodakmoments.com/sites/default/files/files/resources/e4050_portra_400.pdf) | `e83ac6775d37832a4cb466892a3e1cf4c88917a6ee93384e59d6924b1cd97e3a` |
| KODAK Publication No. E-4070, ENDURA Premier Paper, Revised 12-17 | [Kodak Alaris](https://business.kodakmoments.com/sites/default/files/files/products/e4070.pdf) | `94ead00f26a4bbf8ce1a991ff73add049514e38f32d6e88aa7a8a1e3e2d7982e` |

The documents of step P5 are listed with URL, edition, and hash in [`sources.json`](../scripts/poc/p5_film_and_print_combinations/sources.json). The FUJIFILM bulletin follows the same rule as the Kodak documents: it is not committed.

To make the profiles again, run `fetch_sources.py` and `digitize_kodak_charts.py`
([commands](../scripts/poc/p0_data_and_reference/README.md#commands)). The scripts put the PDFs
in `build/tmp/p0/sources/` (not committed; `*.pdf` is also in `.gitignore`) and stop with an
error if a hash differs. If Kodak Alaris removes or changes a document, the profiles stay valid
for the edition above, and a new edition needs a new source check.
