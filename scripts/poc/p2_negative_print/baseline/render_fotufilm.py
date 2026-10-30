"""Local baseline run of the Fotufilm engine v1.14.1 (Apache-2.0; profiles CC BY-SA 4.0): an external comparison only.
Portra 400, no grain. The engine decodes the RAW itself. Output Display P3 is converted to sRGB (clip) for review.
Run in distro ff24 with FOTUFILM_RESOURCES, FOTUFILM_STOCKS, LD_LIBRARY_PATH set."""
import ctypes as C
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

BASE = Path("/mnt/d/Projects/alcedo-film-lab/build/tmp/baseline")
LIB = Path("/mnt/d/Projects/pu-erh_lab/alcedo_studio/tests/resources/sample_images/raw/camera")
OUT = BASE / "out_fotufilm"
P3_TO_SRGB = np.array([[1.2249, -0.2247, -0.0002], [-0.0420, 1.0419, 0.0001], [-0.0197, -0.0786, 1.0979]])


class Target(C.Structure):
    _fields_ = [("max_edge", C.c_uint32), ("format", C.c_int32), ("pixels", C.c_void_p), ("row_bytes", C.c_size_t), ("capacity", C.c_size_t)]


class Info(C.Structure):
    _fields_ = [("width", C.c_uint32), ("height", C.c_uint32), ("milliseconds", C.c_double)]


lib = C.CDLL("libfotufilm.so")
lib.fotufilm_engine_create.restype = C.c_void_p
lib.fotufilm_engine_create.argtypes = [C.POINTER(C.c_char_p)]
lib.fotufilm_engine_describe.restype = C.c_char_p
lib.fotufilm_engine_describe.argtypes = [C.c_void_p]
lib.fotufilm_image_open.restype = C.c_void_p
lib.fotufilm_image_open.argtypes = [C.c_void_p, C.c_char_p, C.POINTER(C.c_char_p)]
lib.fotufilm_render_size.argtypes = [C.c_void_p, C.c_uint32, C.POINTER(C.c_uint32), C.POINTER(C.c_uint32)]
lib.fotufilm_render.argtypes = [C.c_void_p, C.c_void_p, C.c_char_p, C.POINTER(Target), C.POINTER(Info), C.POINTER(C.c_char_p)]
lib.fotufilm_image_release.argtypes = [C.c_void_p]

err = C.c_char_p()
engine = lib.fotufilm_engine_create(C.byref(err))
if not engine:
    sys.exit(f"engine: {err.value}")
described = json.loads(lib.fotufilm_engine_describe(engine))
print("backend", described.get("backend"), [s["id"] for s in described["stocks"]][:60], flush=True)

VARIANTS = json.loads(sys.argv[1])
index = json.loads((BASE / "input/index.json").read_text())
names = sys.argv[2:] or list(index)
for name in names:
    image = lib.fotufilm_image_open(engine, (str(LIB / index[name]["file"]) if not index[name]["file"].startswith("D:/") else "/mnt/d/" + index[name]["file"][3:]).encode(), C.byref(err))
    if not image:
        print(name, "open failed", err.value, flush=True)
        continue
    w, h = C.c_uint32(), C.c_uint32()
    lib.fotufilm_render_size(image, 1000, C.byref(w), C.byref(h))
    for variant, settings in VARIANTS.items():
        buffer = np.zeros((h.value, w.value, 4), np.uint8)
        target = Target(1000, 0, buffer.ctypes.data_as(C.c_void_p), w.value * 4, buffer.size)
        request = {"edit": {"stock": "portra400", "params": {"grain": 0}}, "profileRequest": settings}
        info = Info()
        t = time.time()
        code = lib.fotufilm_render(engine, image, json.dumps(request).encode(), C.byref(target), C.byref(info), C.byref(err))
        if code != 0:
            print(name, variant, "render failed", code, err.value, flush=True)
            continue
        code_values = buffer[..., :3] / 255.0
        linear = np.where(code_values <= 0.04045, code_values / 12.92, ((code_values + 0.055) / 1.055) ** 2.4)
        srgb_linear = np.clip(linear @ P3_TO_SRGB.T, 0, 1)
        srgb = np.where(srgb_linear <= 0.0031308, srgb_linear * 12.92, 1.055 * srgb_linear ** (1 / 2.4) - 0.055)
        Image.fromarray((srgb * 255 + 0.5).astype(np.uint8)).save(OUT / f"{name}__{variant}.png")
        print(name, variant, (w.value, h.value), f"{time.time() - t:.1f} s", "mean", round(float(srgb.mean()), 3), flush=True)
    lib.fotufilm_image_release(image)
