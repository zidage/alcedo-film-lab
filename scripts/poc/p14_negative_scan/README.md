# P14: Negative Scan

Scripts of step P14 ([report](../../../docs/exploration/p14_negative_scan.md)). Method `negative_scan` of the Python viewer reads the developed
negative with a virtual film scanner and then turns the scan into a positive. It runs on the CPU. It uses the current spectral input of the
viewer; the P13 input modes are not used.

| Script | Input | Output |
| --- | --- | --- |
| `negative_scan.py` | library | the virtual scanner, the density inversion, rule `frame_auto_colour`, OpenDRT display |
| `check_negative_scan.py` | the profiles and tables of P0 to P7 | `results/p14_negative_scan/checks.json` |
| `render_negative_scan_review.py` | RAW files (list in the script, or paths) | `build/tmp/p14/review/*.jpg` and `auto_records.json` (local only) |

The method has two parts:

1. **Film Scanner Model.** `I_i = k_i * sum L(lambda) S_i(lambda) 10^-D(lambda)` on the 1 nm grid of the model. `S_i` is a Gaussian band
   (centre and width are controls), `L` is a 3200 K halogen lamp or an equal-energy light, and `k_i` normalises each channel to the empty film holder.
   This is an idealised scanner, not a Frontier or a Noritsu.
2. **Negative Rendering Model.** The density above the film base, a straight-line inversion with one gamma per channel for each medium (the
   average negative of the pool of rule `generic_scan`), the grey of the balance light of the stock as the aim, an optional automatic colour
   from the frame (off is **Neutral Scan**), cyan, magenta, and yellow keys, the black at the film base, and OpenDRT.

## Commands

Use the environment of step P6 (`build/tmp/p6/venv`, see [the P6 README](../p6_mvp_gui/README.md)); this step adds no package.

```powershell
$P = "build/tmp/p6/venv/Scripts/python.exe"
& $P -I scripts/poc/p14_negative_scan/check_negative_scan.py
& $P -I scripts/poc/p14_negative_scan/render_negative_scan_review.py
& $P -I scripts/poc/p6_mvp_gui/p6_mvp_cli.py INPUT.RAW build/tmp/p14/out/neutral.jpg --method negative_scan --negative kodak_portra_400 --scene-light as_shot
& $P -I scripts/poc/p6_mvp_gui/p6_mvp_cli.py INPUT.RAW build/tmp/p14/out/auto.jpg --method negative_scan --negative kodak_portra_400 --scene-light as_shot --neg-scan-auto neutral
```

In the window: Method "Negative Scan (virtual scanner, P14)", and the group "Negative scan".
