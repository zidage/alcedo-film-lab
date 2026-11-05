"""P13: summarize measured comparisons and make focused smooth review sheets.

Input: completed run_study and analyze_sweep artifacts. Output: summary.json,
summary.md and compact JPEG comparisons under the existing local run directory.
Photo measurements are read from JSON, never recomputed from the JPEG sheets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_study import ROOT, STOCKS, write_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--sweep", type=Path)
    args = parser.parse_args()
    run = json.loads((args.directory / "measurements.json").read_text(encoding="utf-8"))
    chosen = ("current_measured", "white_smooth", "conditioned_smooth")
    summary = {"photos": {}, "failures": {}, "user_review": {
        "date": "2026-11-04", "stock": "kodak_portra_400", "photo": "5253219691",
        "timing": "balance0", "cases": ["white_smooth", "conditioned_smooth"],
        "feedback": "Both smooth columns look close to the wanted result.",
        "scope": "User visual feedback on the night photo; no default selection."}}
    lines = ["# P13 measured summary", "", "The values describe a result; they do not rank a look.", "",
             "User review: Portra 400 on the night photo, balance0: both smooth columns look close to the wanted result.", "",
             "## Portra 400 and Gold 200 separation", "",
             "CAM16-UCS median pixel distance, with the same scan timing for all candidates.", "",
             "| Photo | Timing | Current measured | Full white / smooth | Constrained / smooth |",
             "| --- | --- | ---: | ---: | ---: |"]
    for stem, photo in run["photos"].items():
        summary["photos"][stem] = {}
        summary["failures"][stem] = photo["failures"]
        for timing in ("balance0", "balance1"):
            entries = {}
            for case in run["cases"]:
                key = f"{timing}/{case}"
                pairs = photo["stock_separation"].get(key)
                if pairs is not None:
                    entries[case] = {
                        "portra_gold": pairs["kodak_portra_400/kodak_gold_200"],
                        "5219_5207": pairs["kodak_5219/kodak_5207"],
                        "portra_appearance": photo["renders"][f"{timing}/kodak_portra_400/{case}"]["appearance"]}
            summary["photos"][stem][timing] = entries
            values = [f"{entries[case]['portra_gold']['p50']:.3f}" if case in entries else "FAILED" for case in chosen]
            lines.append(f"| {stem} | {timing} | "+" | ".join(values)+" |")
            # The original review rows contain exactly the labelled columns.
            # Copy them at their existing size; do not resize the photos.
            selected_columns = [0]+[run["cases"].index(case)+1 for case in chosen]
            rows = []
            for stock in STOCKS:
                source = args.directory / f"{stem}_{timing}_{stock}.jpg"
                with Image.open(source) as image:
                    stride = image.width // (len(run["cases"])+1)
                    focused = Image.new("RGB", (stride*len(selected_columns),image.height), (20,20,20))
                    for position,column in enumerate(selected_columns):
                        focused.paste(image.crop((column*stride,0,(column+1)*stride,image.height)),
                                      (position*stride,0))
                    focused.save(args.directory / f"smooth_{stem}_{timing}_{stock}.jpg",quality=94,subsampling=0)
                    rows.append(focused)
            sheet = Image.new("RGB",(rows[0].width,sum(row.height for row in rows)),(20,20,20))
            y = 0
            for row in rows:
                sheet.paste(row,(0,y))
                y += row.height
            sheet.save(args.directory / f"smooth_{stem}_{timing}.jpg",quality=94,subsampling=0)
    if args.sweep:
        sweep = json.loads(args.sweep.read_text(encoding="utf-8"))
        summary["sweep"] = {name: value.get("pairs",value) for name,value in sweep["cases"].items()}
        lines += ["", "## Hue sweep", "", "| Case | Timing | Portra/Gold full UCS | Neutral removed a'b' at 0 EV |",
                  "| --- | --- | ---: | ---: |"]
        for case in run["cases"]:
            for timing in ("balance0","balance1"):
                pair = summary["sweep"][case][f"{timing}/kodak_portra_400/kodak_gold_200"]
                lines.append(f"| {case} | {timing} | {pair['full_UCS_p50']:.3f} | "
                             f"{pair['neutral_removed_ab_p50_at_0EV']:.3f} |")
    write_json(args.directory / "summary.json",summary)
    (args.directory / "summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    # Reuse the recorded source provenance. No source is downloaded by P13.
    existing = json.loads((ROOT / "scripts/poc/p1_spectral_input/sources.json").read_text(encoding="utf-8"))
    selected_sources = []
    for source in existing["sources"]:
        if source["file"] in ("CIE_illum_LEDs.csv", "CIE_illum_FLs.csv", "rawtoaces_training_spectral.json"):
            actual = ROOT / "build/tmp/p1/sources" / source["file"]
            checksum = hashlib.sha256(actual.read_bytes()).hexdigest()
            if checksum != source["sha256"]:
                raise ValueError(f"source checksum differs from P1 provenance: {actual}")
            selected_sources.append({**source, "retrieved": existing["retrieved"],
                                     "local_path": str(actual), "sha256_verified": True})
    dependencies = [ROOT / "profiles" / f"{stock}.json" for stock in STOCKS]
    dependencies += [ROOT / "profiles/kodak_2383.json",
                     ROOT / "scripts/poc/p1_spectral_input/spectral_reconstruction.py",
                     ROOT / "scripts/poc/p1_spectral_input/spectral_datasets.py",
                     ROOT / "scripts/poc/p0_data_and_reference/film_spectral_reference.py",
                     ROOT / "scripts/poc/p6_mvp_gui/stock_physics.json",
                     ROOT / "scripts/poc/p6_mvp_gui/inhibition_image.json"]
    profiles = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in dependencies}
    write_json(args.directory / "sources/reused_source_provenance.json",
               {"sources": selected_sources, "additional_dependency_sha256": profiles,
                "new_downloads": [], "project_code_license": "GPL-3.0-only"})
    focused = ["<!doctype html><meta charset='utf-8'><title>P13 smooth review</title>",
               "<style>body{background:#181818;color:#eee;font:16px system-ui;margin:24px}"
               "img{width:100%}a{color:#a9cfff}figure{margin:32px 0}</style>",
               "<h1>P13 smooth comparison</h1><p>Columns: no film; CCT / measured; "
               "full RAW white / smooth; constrained reconstruction / smooth. "
               "Stock character 1. The full white is a RAW metadata estimate.</p>",
               "<p>User review: Portra 400, night photo, balance0: both smooth columns "
               "look close to the wanted result. No default was selected.</p>",
               "<p><a href='review.html'>All seven input cases</a> | "
               "<a href='summary.md'>Measured comparison</a></p>"]
    for stem in run["photos"]:
        focused.append(f"<h2>{stem}</h2>")
        for timing in ("balance0", "balance1"):
            row = f"smooth_{stem}_{timing}_kodak_portra_400.jpg"
            sheet = f"smooth_{stem}_{timing}.jpg"
            focused.append(f"<figure><figcaption>Portra 400 / {timing}; "
                           f"<a href='{sheet}'>all four stocks</a></figcaption>"
                           f"<a href='{row}'><img src='{row}'></a></figure>")
    (args.directory / "smooth_review.html").write_text("\n".join(focused)+"\n",encoding="utf-8",newline="\n")
    print("\n".join(lines),flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
