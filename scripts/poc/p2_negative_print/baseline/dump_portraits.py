"""Local: linear AP1 inputs of the portrait RAW files for the baseline comparison."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp
BASE = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline")
preview = fp.FilmPreview(fp.FilmOptions())
index = json.loads((BASE / "input/index.json").read_text(encoding="utf-8"))
for path in sorted((BASE / "signature_edits/raw").iterdir()):
    ap1, _ = fp.decode_raw_ap1(path, 1000, preview.c)
    name = path.name
    np.save(BASE / f"input/{name}.npy", ap1.astype(np.float32))
    index[name] = {"file": path.as_posix(), "review_scale": fp.review_exposure(ap1, preview.c), "shape": ap1.shape, "portrait": True}
    print(name, ap1.shape, "ev", round(float(np.log2(fp.center_weighted_exposure(ap1, preview.c))), 2), flush=True)
(BASE / "input/index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
