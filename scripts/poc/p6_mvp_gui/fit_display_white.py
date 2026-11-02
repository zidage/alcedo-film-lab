"""Rule 'projected_print_white': the display white of each projected print material.

Input: the profiles, the catalog, the reflectance tables. Output: display_white.json next to this script, and a table on stdout. Step: P7, ROADMAP U75. Machine rule: CPU only, one process.
The value is the chromaticity of the densest node of the print table of KODAK VISION3 5207 at the reference light on that print material, with no rule 'neutral_printing_gain'. It is an empirical choice and not a measurement: the user selected this look on 5207 + 2383 by eye. A print curve alone does not reach this chromaticity, because the negative adds to it. One white per print material keeps the differences between negatives, so a stock keeps its own cast (U36), and the scene light does not move the white.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import mvp_pipeline as mp  # noqa: E402

fp = mp.fp
REFERENCE_NEGATIVE = "kodak_5207"


def main() -> int:
    result = {}
    for material, entry in sorted(mp.CATALOG["prints"].items()):
        if entry["medium"].lower() != "cine":
            continue
        options = mp.film_options(mp.RenderSettings(negative=REFERENCE_NEGATIVE, print_material=material, display_white="reflector"))
        white = fp.FilmPreview(options).paper_white
        result[material] = {"xy": [round(float(white[0] / white.sum()), 6), round(float(white[1] / white.sum()), 6)], "reference_negative": REFERENCE_NEGATIVE}
        print(f"{material:24s} {result[material]['xy']}", flush=True)
    mp.DISPLAY_WHITE_PATH.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
