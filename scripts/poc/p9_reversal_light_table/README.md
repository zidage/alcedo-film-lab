# P9: reversal film on a light table

Scripts of step P9 ([report](../../../docs/exploration/p9_reversal_light_table.md), ROADMAP U86). A colour reversal film (slide film) is the final image: the camera exposes it, E-6 develops it to a positive, and the viewer looks at it on a light table through a loupe. There is no print film. The Python viewer of step P6 has this path as method `light_table`.

| Script | Input | Output |
| --- | --- | --- |
| `fetch_sources.py` | `sources.json` | the data sheets in `build/tmp/p9/sources/` (not committed) |
| `import_reversal_profiles.py` | the data sheets; a clone of spectral_film_lut at `bcbcfc68`; a clone of the Fotufilm engine | `profiles/<film>.json` of five films, `reversal_catalog.json`, `results/p9_reversal_light_table/source_checks.json` |
| `fit_reversal_physics.py` | the profiles | `reversal_physics.json`: grey placement, spread, and inhibition of each film |
| `reversal_film.py` | library | the model of the film and of the light table; `mvp_pipeline.py` uses it |
| `check_reversal_film.py` | optionally an AP1 array | `results/p9_reversal_light_table/checks.json` |
| `render_p9_review.py` | AP1 arrays of the earlier steps | `build/tmp/p9/review/*.jpg` with a label on every panel (local only) |

The tables and the sources of P0 to P2 must be present, as for step P6. A first use of a film builds its model in about 3 seconds, in memory.

## Commands

```bash
E=build/tmp/p9
python -m venv $E/venv
$E/venv/Scripts/python -m pip install -r scripts/poc/p9_reversal_light_table/requirements.txt
P=$E/venv/Scripts/python
D=scripts/poc/p9_reversal_light_table
git clone https://github.com/JanLohse/spectral_film_lut.git $E/sources/spectral_film_lut && git -C $E/sources/spectral_film_lut checkout bcbcfc6861f49cc706dc5d00ea048e4853060aab
git clone https://github.com/DhaliwalX/fotufilm-engine.git $E/sources/fotufilm-engine && git -C $E/sources/fotufilm-engine checkout 6b45c802
$P -I $D/fetch_sources.py
$P -I $D/import_reversal_profiles.py $E/sources/spectral_film_lut/src/spectral_film_lut $E/sources/fotufilm-engine
$P $D/fit_reversal_physics.py
$P $D/check_reversal_film.py build/tmp/p3/input/leica_m11.npy
$P $D/render_p9_review.py
$P scripts/poc/p6_mvp_gui/p6_mvp_cli.py INPUT.ARW build/tmp/p9/out/velvia.jpg --method light_table --reversal fuji_velvia_50
$P scripts/poc/p6_mvp_gui/p6_mvp_gui.py INPUT.ARW
```

The window has the method "Reversal film on a light table" and the list "Reversal film". On this method the controls of the negative act on the slide (inhibition, light spread, halation, lens flare), "Enlarger flare" is the flare of the loupe, and the other print controls, overexposure, and timing do not act.
