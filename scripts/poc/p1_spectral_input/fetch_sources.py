"""Download and verify the source files of step P1.

Input: sources.json (URL, expected SHA-256, license, and use of each file).
Output: the files in build/tmp/p1/sources/ and the source manifest
results/p1_spectral_input/source_manifest.json (file, size, SHA-256, verification result).

Step: P1 (spectral input), ROADMAP section 8. The script stops with an error when a hash
differs from the expected value; it does not continue with a different file.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_DIR = REPO_ROOT / "build" / "tmp" / "p1" / "sources"
MANIFEST_PATH = REPO_ROOT / "results" / "p1_spectral_input" / "source_manifest.json"


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "alcedo-film-lab/p1"})
    with urllib.request.urlopen(request, timeout=300) as response:
        path.write_bytes(response.read())


def main() -> int:
    spec = json.loads((SCRIPT_DIR / "sources.json").read_text(encoding="utf-8"))
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    mismatches = []
    for source in spec["sources"]:
        path = SOURCE_DIR / source["file"]
        if not path.exists():
            print(f"download {source['url']}")
            download(source["url"], path)
        actual = sha256_of_file(path)
        matches = actual == source["sha256"]
        if not matches:
            mismatches.append(f"{source['file']}: expected {source['sha256']}, found {actual}")
        entries.append(
            {
                "file": source["file"],
                "url": source["url"],
                "title": source["title"],
                "edition": source["edition"],
                "license": source["license"],
                "use": source["use"],
                "bytes": path.stat().st_size,
                "sha256": actual,
                "sha256_matches_sources_json": matches,
            }
        )
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved": spec["retrieved"], "source_dir": "build/tmp/p1/sources", "files": entries}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    if mismatches:
        print("hash mismatch:\n  " + "\n  ".join(mismatches), file=sys.stderr)
        return 1
    print(f"{len(entries)} files verified; manifest {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
