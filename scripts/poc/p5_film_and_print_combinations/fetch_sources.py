"""Download the source files of step P5.

Input: sources.json (URL, expected SHA-256, license, and use of each file).
Output: build/tmp/p5/sources/. The files are not committed.
Step: P5, ROADMAP section 8. A hash that differs stops the script with an error.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parents[2] / "build" / "tmp" / "p5" / "sources"


def main() -> int:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for source in json.loads((SCRIPT_DIR / "sources.json").read_text(encoding="utf-8"))["sources"]:
        path = SOURCE_DIR / source["file"]
        if not path.exists():
            request = urllib.request.Request(source["url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                path.write_bytes(response.read())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != source["sha256"]:
            raise RuntimeError(f"{source['file']}: SHA-256 {digest}, expected {source['sha256']}")
        print("ok", source["file"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
