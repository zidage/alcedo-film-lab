"""P11: record source provenance and summarize completed measurements and plots.

Input: build/tmp/p11/measurements.json. Output: local JSON, a plot, HTML review.
Downloaded documents stay local. No external source code is copied.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from print_viewing import ROOT, fp, mp

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = ROOT / "build/tmp/p11"


def main() -> None:
    sources = OUT / "sources"
    sources.mkdir(exist_ok=True)
    entries = []
    for filename, url, edition, license_text in (
        ("cie_cam16.html", "https://www.cie.co.at/publications/cie-2016-colour-appearance-model-colour-management-systems-ciecam16",
         "CIE 248:2022 publication abstract; full standard not obtained", "CIE copyright; local research only"),
        ("colour_cam16.html", "https://colour.readthedocs.io/en/develop/generated/colour.XYZ_to_CAM16.html",
         "Colour develop documentation 0.4.7 as served on retrieval", "Colour BSD-3-Clause; website saved locally only")):
        path = sources / filename
        if not path.exists():
            # The direct download returned HTTP 403. Record that error; the
            # publication abstract and API documentation were read with web.open.
            # This file is a retrieval note, not a copy of the source document.
            path = path.with_suffix(".txt")
            path.write_text(f"URL: {url}\nEdition: {edition}\n"
                            "Read through web.open on 2026-11-04.\n"
                            "Direct urllib download failed: HTTP 403 Forbidden.\n"
                            "No full source document downloaded or redistributed.\n",
                            encoding="utf-8", newline="\n")
        entries.append({"file": str(path.relative_to(ROOT)), "url": url,
                        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "edition": edition, "license": license_text})
    dependencies = ["scripts/poc/p6_mvp_gui/mvp_pipeline.py", "scripts/poc/p2_negative_print/film_preview.py",
                    "scripts/poc/p10_chart_scan/cam16.py", "scripts/poc/p10_chart_scan/scan_generic.py",
                    "scripts/poc/p3_scan_and_scene/aces_scan.py"]
    provenance = {"sources": entries, "machine": platform.platform(), "python": sys.version,
                  "dependency_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in dependencies}}
    (OUT/"provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8", newline="\n")
    d = json.loads((OUT/"measurements.json").read_text())
    photo_stocks = [k for k in d["sweep"] if k != "kodak_5207"]
    print("stock print cam100 cam500 cam2000 scan")
    for k in d["sweep"]:
        print(k, *(round(d["sweep"][k][v]["Mprime_ratio"], 4)
                    for v in ("print", "cam100", "cam500", "cam2000", "scan")))
    print("spread", d["spread"])
    for k, p in d["photos"].items():
        print(k, p["scene_light"], {s: [round(v["metrics"][m]["Mprime_ratio"], 3)
              for m in ("print", "cam100", "cam500", "cam2000", "scan")]
              for s, v in p["stocks"].items()})
    # Actual local curve slope at the grey, with independent paper-exposure input.
    pipe = mp.Pipeline()
    slopes = {}
    for stock in photo_stocks:
        model = pipe.print_model(mp.RenderSettings(negative=stock, scene_light="D55"))
        q, _ = model.layer_exposure(np.full((1, 3), .18, dtype=np.float64))
        amounts, _ = model.negative_density(q)
        h = model.film.paper_log_exposure(model.film.negative_spectral_density(amounts))[0]
        slopes[stock] = [(np.interp(h[k]+.0005, c.log_h, c.density)-np.interp(h[k]-.0005, c.log_h, c.density))/.001
                         for k, c in enumerate(model.paper_curves)]
    print("paper slopes density/log10H", slopes)
    (OUT/"paper_slopes.json").write_text(json.dumps(slopes, indent=2), encoding="utf-8", newline="\n")
    fig, ax = plt.subplots(figsize=(10, 4.2), layout="constrained")
    x = np.arange(len(photo_stocks))
    for i, (flow, label) in enumerate((("print", "Current print"), ("cam100", "CAM16 100 lux"),
                                     ("cam500", "CAM16 500 lux"), ("cam2000", "CAM16 2000 lux"), ("scan", "Current scan"))):
        ax.plot(x, [d["sweep"][k][flow]["Mprime_ratio"] for k in photo_stocks], "o-", label=label)
    ax.axhline(1, color="grey", linewidth=.8)
    ax.set_xticks(x, [s.replace("kodak_", "").replace("_", " ") for s in photo_stocks])
    ax.set_ylabel("Mean CAM16-UCS M' / OpenDRT M'")
    ax.set_title("D55, 144 equal-lightness colour probes, 0 EV; no fit")
    ax.legend(ncol=3, fontsize=8)
    fig.savefig(OUT/"viewing_comparison.png", dpi=150)
    html = '<!doctype html><html><body><p>P11: print viewing scenarios (100, 500, 2000 lux), unchanged film and paper.</p>'
    html += f'<img style="width:100%" src="{OUT / "viewing_comparison.png"}">'
    html += '<p>OpenDRT · current print · CAM16 100 lux · CAM16 500 lux · CAM16 2000 lux · current scan. Each panel carries its stock and M\' ratio.</p>'
    for stem in d["photos"]:
        html += f'<p>{stem}: Portra 400</p><img style="width:100%" src="{OUT / ("review_"+stem+"_portra400.jpg")}">'
    html += '</body></html>'
    (OUT/"review.html").write_text(html, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
