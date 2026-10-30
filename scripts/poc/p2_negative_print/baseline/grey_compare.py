"""Local: the same neutral ramp through this lab's preview and spektrafilm: L*, a*, b* (against D65 display white)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp

BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
WHITE = np.array([0.9505, 1.0, 1.089])


def lab(srgb):
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    return fp.sr.xyz_to_lab(linear.reshape(-1, 3) @ M.T, WHITE)


data = json.loads((BASE / "grey_spektrafilm.json").read_text(encoding="utf-8"))
grey = np.array(data["input"])
preview = fp.FilmPreview(fp.FilmOptions())
ours = lab(np.clip(preview.render(np.outer(grey, np.ones(3))[None])[0][0], 0, 1))
default = lab(np.array(data["defaults"]))
bare = lab(np.array(data["no_glare_no_couplers"]))
print("input     ours L a b          spektra default L a b   spektra no glare/couplers")
for i in range(0, len(grey), 3):
    print(f"{grey[i]:8.4f} ", ours[i].round(1), default[i].round(1), bare[i].round(1))
