"""Contact sheet of a folder of RAW files from their embedded previews (local only: build/tmp/baseline/night/)."""
import io
import sys
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image, ImageDraw

SOURCE = Path(sys.argv[1])
OUT = Path("D:/Projects/alcedo-film-lab/build/tmp/baseline/night")
OUT.mkdir(parents=True, exist_ok=True)
CELL, COLS = 330, 6
files = sorted(SOURCE.glob("*.ARW"))
rows = (len(files) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * CELL, rows * CELL), (24, 24, 24))
draw = ImageDraw.Draw(sheet)
for i, path in enumerate(files):
    with rawpy.imread(str(path)) as raw:
        thumb = raw.extract_thumb()
        wb = np.round(np.array(raw.camera_whitebalance[:3]) / raw.camera_whitebalance[1], 2).tolist()
    im = Image.open(io.BytesIO(thumb.data)).convert("RGB") if thumb.format == rawpy.ThumbFormat.JPEG else Image.fromarray(thumb.data)
    im.thumbnail((CELL - 4, CELL - 20))
    x, y = (i % COLS) * CELL + 2, (i // COLS) * CELL + 16
    sheet.paste(im, (x, y))
    draw.text((x, y - 14), f"{path.stem} wb {wb}", fill=(255, 255, 120))
sheet.save(OUT / "sheet.jpg", quality=88)
print(len(files))
