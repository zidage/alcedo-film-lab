# P7: Spectral acceleration

Date: 2026-10-31. Decision: [ROADMAP U68](../../ROADMAP.md). Scripts: [`scripts/poc/p7_spectral_acceleration/`](../../scripts/poc/p7_spectral_acceleration/). Results: [`checks.json`](../../results/p7_spectral_acceleration/checks.json).

## 1. Question

Can staged tables reproduce the direct evaluator, and can the table construction run from one code base in the Python viewer and in the product?

## 2. Result summary

- **One C++ library builds the tables.** `film_tables.hpp` has no dependency on Python or Qt. The Python viewer calls it through nanobind. The CMake target `film_tables` is a static library for the product. It is not yet linked into Alcedo Studio.
- **The print table has three stages (rule `staged_print_table`).** A new value of a print control now takes 0.015 s for the table and 0.27 s for the model. Before this step it took about 5.7 s and about 8 s.
- **No print table or APD table goes to disk (U68).** The table directory went from 845 MB to 203 MB. The spectral stages stay in memory for the life of the process.
- **The error is small on photos.** On 7 photos, 10 stock pairs, and 28 control cases: p99.9 at most 0.25 of an 8 bit code value, largest 1.23. On a neutral ramp: largest 0.25. All 125 checks pass. On all table nodes the largest error is 6.4 code values, on colours that no test photo reached.
- **Table construction was already multithreaded, and it stays so.** The longest stage reaches 17.3 CPU seconds per second of wall time on 20 hardware threads.
- **The user has not reviewed this result.** The image differs slightly from the image of P6. A render at 2048 pixels did not get faster, because this step changes the tables and not the per-pixel kernels.

## 3. Inputs

The profiles and reflectance tables of P0 to P6. Photos, as AP1 arrays under `build/tmp/`: `se188`, `se228`, `leica_m11`, `nikon_zf`, `_DSC4063`, `_DSC8148` (night), `digital_ap1`. They go through the product grade of the MVP defaults.

Machine: Intel Core i7-12700H (20 hardware threads), 31.8 GB. CPU only, no GPU job. Compiler: MSVC 2022, Release, with no fast-math option and no architecture option.

## 4. Method

### 4.1 Observations before the change

These values come from a local probe on commit `3ee8b60`. The probe is not in this repository.

| Observation | Value |
| --- | --- |
| Print table in numba, 65^3 nodes | 5.6 to 6.0 s |
| Same algorithm in C++ (MinGW g++ -O3), same result (relative XYZ difference below 1e-14) | 1.44 s |
| Model build with stored tables | 2.3 s, of which 1.96 s in `SpectralGrid.weights` |
| APD table in NumPy, from 1/64 of the nodes | estimate 66 s |

So a language change alone gives a factor of 4 on the print table. The stages give the rest.

### 4.2 Calculations that were removed

- **Negative dye solve.** With rule `dye_amount_curves`, the record is the dye amounts. The old table converted the record to Status M and solved back. Check "Record is the amounts" shows a largest difference of 1.8e-15 on 10 stock pairs. A stock with a Status M record keeps the solve.
- **Dense integration matrix.** A fine sample has one or two working nodes, so `SpectralGrid.weights` now uses the nonzero values. The largest relative difference is 4.4e-16.
- **Repeated file read.** The reflectance table is read once per process. It has no dependence on a stock.

### 4.3 Rule `staged_print_table`

| Stage | Calculation | Depends on | Time |
| --- | --- | --- | --- |
| A | Negative record to log10 of the unbalanced paper exposure | Negative, printer lamp, paper sensitivity | 0.09 s |
| B | Paper Status A to print XYZ, by the dye solve of the paper | Paper, viewing light | 0.63 s |
| C | Printer lights, print contrast, flash, paper curves, trilinear read of stage B, surface reflection | Print controls | 0.015 s |

Stage C makes the same 65^3 table as before, so the per-pixel kernels do not change. Stages A and B are kept in memory by a hash of their input values, so a kept stage cannot be out of date.

Stage B has 65 nodes per axis, the same number as before. Node k of an axis has the density `start + range * (k / 64) ^ 2`. A uniform axis failed the limits on the first run: 17 of 125 checks failed, and the largest neutral ramp error was 2.11 code values, near +5 stops, where the dye amounts reach zero. The sweep below chose the power 2.

| Axis | Model build with empty stage memory | Worst of the 6 sweep cases: neutral ramp, largest | Photos p99.9 | Photos largest |
| --- | --- | --- | --- | --- |
| 65 nodes, uniform | 1.20 s | 2.11 | 3.20 | 3.74 |
| 97 nodes, uniform | 2.63 s | 1.87 | 2.22 | 2.56 |
| 129 nodes, uniform | 5.47 s | 1.62 | 1.74 | 2.01 |
| 65 nodes, power 1.5 | 1.16 s | 0.50 | 0.76 | 1.50 |
| **65 nodes, power 2** | **1.27 s** | **0.25** | **0.32** | **1.18** |
| 65 nodes, power 3 | 1.20 s | 0.09 | 0.27 | 1.27 |
| 97 nodes, power 2 | 2.80 s | 0.11 | 0.19 | 0.71 |

Source: `sweep_paper_axis.py`. Power 3 has a lower ramp error in this sweep. The choice of power 2 is a judgment: it has more nodes than power 3 at a high density, and both are inside the limits. The sweep used the same photos as the checks, so the photos did not test this choice independently.

## 5. Checks

Script: `check_film_tables.py`. Results: [`checks.json`](../../results/p7_spectral_acceleration/checks.json). The limits were written before the first run of the script and were not changed after the failures of the first run. They were written after the probe of section 4.1 had shown the size of the error on two photos. The reference is the dye solve per node of `FilmPreview._print_nodes`.

| Check | Value | Limit |
| --- | --- | --- |
| Weights, largest relative difference | 4.4e-16 | 1e-12 |
| Band response, largest log10 difference | 8.9e-16 | 1e-11 |
| Record is the amounts, largest difference | 1.8e-15 | 1e-9 |
| Status M record, largest difference | 1.5e-11 | 1e-9 |
| Paper stage, largest relative XYZ difference | 1.9e-11 | 1e-9 |
| APD table, largest density difference | 1.8e-15 | 1e-9 |
| 10 stock pairs on 7 photos, 8 bit code, p99.9 | 0.25 | 1.0 |
| The same, largest | 0.97 | 4.0 |
| The same, neutral ramp, largest | 0.06 | 0.5 |
| 7 print table controls at both ends, 2 stocks, 2 photos, p99.9 | 0.19 | 1.0 |
| The same, largest | 1.23 | 4.0 |
| The same, neutral ramp, largest | 0.25 | 0.5 |
| Table at mask density 0, largest difference of the cube root | 2.4e-7 | 1e-6 |
| New files in the table directory | 0 | 0 |
| Print table with empty stage memory | 0.73 s | 2 s |
| Print table for a new control value | 0.015 s | 0.05 s |
| APD table | 0.066 s | 1 s |

Error on all 274625 table nodes, with no limit: p99 at most 0.83, largest 6.38 code values (control cases). Most nodes are colours that no photo reaches.

Model times of the same run: 0.99 s with empty stage memory, 0.27 s for a new control value, 0.56 s for a scan model of a new negative.

### 5.1 Multithreading

Source: `measure_table_threads.py`, in a run before the reflectance table was kept in memory.

| Stage | Wall time | CPU time | CPU / wall |
| --- | --- | --- | --- |
| A | 0.093 s | 1.30 s | 13.9 |
| B | 0.625 s | 10.78 s | 17.3 |
| C | 0.017 s | 0.078 s | 4.6 |
| Model build, stages kept | 0.449 s | 0.125 s | 0.3 |

Stages A and B use nearly all threads. The model build waited mostly for the file read, so the file read was removed (section 4.2). Stage C is short, and each call starts its threads again, so it does not use all of them.

### 5.2 Checks of the earlier steps

The checks of the earlier steps ran on the new tables, with the following differences. These runs were before the reflectance table was kept in memory, which does not change a value. Their output files were restored after the comparison, so the reports of those steps keep their numbers. The timing values of these runs are not evidence, because several ran side by side.

| Check | Result |
| --- | --- |
| `run_p0_checks.py` | The same 3 failed checks as the committed results |
| `check_fast_kernels.py`, `check_scan_path.py`, `check_film_response.py`, `check_stock_chain.py` | The pass values do not change |
| `check_shadow_mode.py` | The same failures as the committed results: `table_interpolation` on 6 stocks, `plus_3_stops_change` on Gold 200 |
| `check_p6_mvp.py` | 0 failures, on `_DSC8148.ARW`; the committed run used `P2625273.RW2` |
| `check_p6_controls.py` | 0 failures, on the committed input. On `digital_ap1.npy`, a file with no strong highlight, 5 cases of "no effect" for halation length and gamut compression; this is a property of that input |

The command line and the window each rendered `_DSC8148.ARW` after the stored tables were deleted.

## 6. Not measured

- The user review of the image. The differences are small by the numbers, and the appearance decision belongs to the user.
- Continuity at the boundaries of table cells, which ROADMAP section 8 requires for this step.
- Coverage of the negative and print density ranges by photos.
- The other 21 negatives and 14 print materials have no comparison with the reference. `check_p6_mvp.py` shows only that their output is finite and in range.
- A link into Alcedo Studio. A build on macOS, or with a compiler other than MSVC in this form of the library.
- Full-resolution images. The table work has no dependence on the image size.
- The first build of the reflectance tables (about 5 minutes, P2 report). These stay on disk, because this step did not make them faster.

## 7. Recommendation

Keep this form. The next costs of a render are in the per-pixel code, which P8 replaces: on the APD path, `table_apd` on SciPy, `adx10_to_aces` on NumPy, and the OpenColorIO output. The stages of this table fit the product: the host builds stages A and B, and a control change sends one new table to the GPU.

## 8. Commands

See [the script README](../../scripts/poc/p7_spectral_acceleration/README.md).

## 9. Open items

| Item | Owner |
| --- | --- |
| Review the image against P6 | User |
| Check continuity at the table cell boundaries, and the density coverage | Lab |
| Link `film_tables` into Alcedo Studio, and build it on macOS | Product port |
