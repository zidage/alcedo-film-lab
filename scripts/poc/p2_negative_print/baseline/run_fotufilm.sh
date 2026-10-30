#!/bin/bash
R=/opt/squashfs-root/usr/lib/fotufilm
export FOTUFILM_RESOURCES=$R/resources FOTUFILM_STOCKS=$R/resources/Stocks
export LD_LIBRARY_PATH=$R/lib:/usr/lib/wsl/lib
exec python3 /mnt/d/Projects/alcedo-film-lab/build/tmp/baseline/scripts/render_fotufilm.py \
  '{"auto": {}, "endura": {"medium": "endura-premier"}}' "$@"
