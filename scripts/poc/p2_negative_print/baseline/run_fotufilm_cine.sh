#!/bin/bash
# Fotufilm with the Vision3 stocks: patches the stock id of the driver through STOCK.
R=/opt/squashfs-root/usr/lib/fotufilm
export FOTUFILM_RESOURCES=$R/resources FOTUFILM_STOCKS=$R/resources/Stocks
export LD_LIBRARY_PATH=$R/lib:/usr/lib/wsl/lib
D=/mnt/d/Projects/alcedo-film-lab/build/tmp/baseline/scripts
for pair in "5207 vision250d" "5219 vision500t"; do set -- $pair; NAME=$1; STOCK=$2; shift 2
  sed "s/\"stock\": \"portra400\"/\"stock\": \"$STOCK\"/" $D/render_fotufilm.py > /tmp/rf_$NAME.py
  python3 /tmp/rf_$NAME.py "{\"$NAME\": {}}" $FILES
done
