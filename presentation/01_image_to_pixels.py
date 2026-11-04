#!/usr/bin/env python3
"""Stage 1 — turn an image into a flat stream of 0..255 pixel values on the CPU.

    image  ->  RGB -> CPU luminance kernel -> uint8 matrix -> pixels.hex

Usage:
    python3 presentation/01_image_to_pixels.py [image] [--max-side 160]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visuals as v
from common import ensure_out, resolve_input, write_hex

LUM = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", help="input image (defaults to IMG/sobel_input.png)")
    ap.add_argument("--max-side", type=int, default=160)
    args = ap.parse_args()

    v.banner(
        "RISC-V  ×  EDGE-VISION  PIPELINE",
        "stage 1 · image  →  0..255 pixel stream  (CPU)",
    )
    v.stage(1, 3, "IMAGE → PIXELS", "CPU luminance kernel + byte serialisation")

    src = resolve_input(args.image)
    v.kv("source", src.name)
    v.kv("decoder", "Pillow RGB", "8-bit")
    v.note("formula:  Y = 0.299·R + 0.587·G + 0.114·B", v.CYAN)
    print()

    img = Image.open(src)
    if getattr(img, "is_animated", False):
        img.seek(0)
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, args.max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                         Image.LANCZOS)
    rgb = np.asarray(img, dtype=np.float32)

    for _ in v.progress(100, "CPU luminance conversion", delay=0.003):
        pass

    gray = np.clip(np.tensordot(rgb, LUM, axes=([2], [0])), 0, 255).astype(np.uint8)

    for _ in v.progress(60, "serialising bytes", delay=0.004):
        pass

    out = ensure_out()
    np.save(out / "01_grayscale.npy", gray)
    Image.fromarray(gray, "L").resize(
        (gray.shape[1] * 5, gray.shape[0] * 5), Image.NEAREST
    ).save(out / "01_grayscale.png")
    nbytes = write_hex(out / "pixels.hex", gray)
    (out / "pixels.meta").write_text(f"{gray.shape[1]} {gray.shape[0]}\n")

    print()
    v.kv("resolution", f"{gray.shape[1]} x {gray.shape[0]}", "px", v.LIME)
    v.kv("pixels", f"{nbytes:,}", "samples", v.LIME)
    v.kv("range", f"{gray.min()} .. {gray.max()}", "0..255", v.AMBER)
    v.kv("mean", f"{gray.mean():.2f}", "intensity", v.CYAN)
    v.kv("unique levels", f"{len(np.unique(gray))}", "of 256", v.MAGENTA)

    print()
    v.rule()
    v.note("FIRST 64 BYTES OF THE PIXEL STREAM", v.MAGENTA)
    v.rule()
    v.hex_rain(rows=4, cols=40)
    v.hexdump(gray, limit=64)

    print()
    v.rule()
    v.note("INTENSITY HISTOGRAM", v.MAGENTA)
    v.rule()
    v.histogram(gray)

    print()
    v.rule()
    v.note("LIVE PIXEL GRID", v.MAGENTA)
    v.rule()
    v.pixel_preview(gray, cols=44, title=f"{src.name} → {gray.shape[1]}×{gray.shape[0]} grayscale")

    print()
    v.note(f"wrote {out / 'pixels.hex'}  ({nbytes} bytes)", v.LIME)
    v.note(f"wrote {out / '01_grayscale.png'}", v.LIME)
    print()
    print("  " + v.bold(v.gradient("STAGE 1 COMPLETE — pixel stream ready for the edge kernel")))
    print()


if __name__ == "__main__":
    main()
