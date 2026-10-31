"""Place the Frontier table of the classic scan method under build/tmp/p6/vendor/. It is not committed (README U27).

Input: NegPy at the commit below, from a local clone (first argument) or a new clone under build/tmp/p6/vendor/NegPy. The script does not run code of that project.
Output: build/tmp/p6/vendor/frontier.npz. It stops with an error if the hash differs. Step: P6, README U61.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR = REPO_ROOT / "build" / "tmp" / "p6" / "vendor"
URL = "https://github.com/marcinz606/NegPy"
COMMIT = "cce849adf4d9183f3e9aad667784d7227f83833e"
TABLE = "negpy/features/exposure/print_luts/frontier.npz"
SHA256 = "bde3fcf411c2ec92ad2ca7d38db65c8eb4865426f261638890fed5efa412fd21"


def main() -> int:
    VENDOR.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        clone = Path(sys.argv[1])
    else:
        clone = VENDOR / "NegPy"
        if not clone.exists():
            subprocess.run(["git", "clone", "--filter=blob:none", URL, str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "checkout", "--quiet", COMMIT], check=True)
    source = clone / TABLE
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != SHA256:
        raise ValueError(f"{source}: SHA-256 {digest}, expected {SHA256}")
    shutil.copyfile(source, VENDOR / "frontier.npz")
    print("frontier.npz", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
