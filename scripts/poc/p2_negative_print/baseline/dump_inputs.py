"""Local: dump the common linear AP1 (ACES white) inputs for the baseline comparison, one .npy per file."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "D:/Projects/alcedo-film-lab/scripts/poc/p2_negative_print")
import film_preview as fp
import render_review_images as rr

FILES = ["canon/r5ii/237A2108.CR3", "nikon/zf/DSC_1535.NEF", "sony/a7riii/DSC00674.ARW", "nikon/d3x/nikon_d3x_08.nef",
         "sony/a7cii/Sonya7c2-Bracaglia-05.ARW", "sony/a7rii/DSC00602.ARW", "fuji/xt5/DSCF1787.RAF", "sony/a7riii/DSC00728.ARW",
         "nikon/d800e/Nikon-D800e-raw-00007.nef", "leica/m10/L1001108.dng", "nikon/d810/DSC_7647.NEF"]
OUT = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline/input")
OUT.mkdir(parents=True, exist_ok=True)
c = fp.FilmPreview(fp.FilmOptions()).c
index = {}
for rel in FILES:
    ap1, rec709 = fp.decode_raw_ap1(rr.LIBRARY / rel, 1000, c)
    name = rel.replace("/", "_")
    scale = fp.review_exposure(ap1, c)
    np.save(OUT / f"{name}.npy", ap1.astype(np.float32))
    index[name] = {"file": rel, "review_scale": scale, "shape": ap1.shape}
    print(name, ap1.shape, round(scale, 3), flush=True)
(OUT / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
