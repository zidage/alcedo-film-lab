# Film simulation exploration

Reports of the steps from PoC to MVP. The steps and the evidence rules are in
[README section 8](../../README.md#8-route-from-poc-to-mvp). Source downloads, renders of the
source charts, and local plots stay under `build/tmp/` and `results/*/plots/` and are not
committed; each report states the commands that make them again.

| Step | Report | Status |
| --- | --- | --- |
| P0 | [Data and host spectral reference: Portra 400 and Endura Premier](p0_data_and_reference.md) | Measured 2026-10-29: the six Kodak charts are PDF vector paths and are digitized without manual tracing (tick residual at most 0.0007 density and 0.09 nm); the float64 chain from camera exposure to viewed print runs with finite output; the sources do not specify the pair completely (no isolated negative dyes, no negative density above 700 nm where 26 % of the paper red-layer printing weight is, no paper base, no paper exposure light); E-4050 is not self-consistent within the predeclared tolerances (speed point up to 0.12 log H, D-min up to 0.068 Status M); the uncalibrated neutral ramp stays within C*ab 3.6 (paper alone 3.4), but a 0.1 log H anchor error or another inferred cyan dye gives 12 to 13; the 0.1 nm reference is converged (0.0009 Delta E*ab against 0.05 nm); an independent hand digitization (spectral_film_lut) agrees to a median of 0.001-0.014; Kodak PDFs not distributed (U10); user review open |
| P1 | Spectral input and RGC | Not started |
| P2 | Negative and print | Not started |
| P3 | Spectral acceleration | Not started |
| P4 | Three GPU backends | Not started |
| MVP | Standalone workflow | Not started |
