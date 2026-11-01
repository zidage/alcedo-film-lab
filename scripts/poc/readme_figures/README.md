# Figures of the root README

Scripts that make `docs/images/` (ROADMAP U65). They need the RAW files of `build/tmp/baseline/signature_edits/raw/`, two local RAW files of the owner (U66), and the tables of P6, so they do not run on a clean clone.

| Script | Environment | Output |
| --- | --- | --- |
| `make_readme_figures.py decode` | P6 | AP1 arrays in `build/tmp/readme_figures/input/` |
| `render_spektrafilm_figures.py` | `build/tmp/baseline/venv_spektra` | sRGB arrays in `build/tmp/readme_figures/spektrafilm/` |
| `make_readme_figures.py figures` | P6 | `docs/images/` |

```bash
P=build/tmp/p6/venv/Scripts/python
D=scripts/poc/readme_figures
$P $D/make_readme_figures.py decode
build/tmp/baseline/venv_spektra/Scripts/python $D/render_spektrafilm_figures.py
$P $D/make_readme_figures.py figures
```

The requirements are those of the P6 environment; `requirements.txt` here includes them. The spektrafilm environment is the one of `scripts/poc/p2_negative_print/baseline/`.
