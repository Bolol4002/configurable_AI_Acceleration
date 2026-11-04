#!/usr/bin/env python3
"""Stage 2 — CPU Sobel edge detection over the 0..255 pixel stream.

    pixels.hex  ->  gradient (Gx, Gy)  ->  |Gx| + |Gy|  ->  edges.hex

Usage:
    python3 presentation/02_edge_detect.py [--pixels FILE] [--out DIR]
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visuals as v
from common import OUT, read_hex, write_hex


def infer_shape(values, pixels_path):
    meta = Path(pixels_path).with_suffix(".meta")
    if meta.exists():
        w, h = [int(x) for x in meta.read_text().split()]
        return h, w
    npy = OUT / "01_grayscale.npy"
    if npy.exists():
        return np.load(npy).shape
    side = int(round(len(values) ** 0.5))
    if side * side != len(values):
        raise SystemExit(
            f"cannot infer image shape for {len(values)} values; "
            "run 01_image_to_pixels.py first"
        )
    return side, side


def colorize(mag):
    t = np.asarray(mag, dtype=np.float32) / 255.0
    stops = [0.0, 0.40, 0.75, 1.0]
    r = np.interp(t, stops, [6, 0, 255, 255])
    g = np.interp(t, stops, [10, 210, 70, 255])
    b = np.interp(t, stops, [26, 255, 220, 255])
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def overlay(gray, mag):
    base = np.stack(
        [gray * 0.20, gray * 0.24, gray * 0.42], axis=-1
    ).astype(np.float32)
    t = (np.asarray(mag, dtype=np.float32) / 255.0)[..., None]
    neon = np.array([0.0, 0.95, 1.0], dtype=np.float32) * 255.0
    hot = np.array([1.0, 0.25, 0.95], dtype=np.float32) * 255.0
    mix = neon * (1.0 - t) + hot * t
    return np.clip(base + mix * t, 0, 255).astype(np.uint8)


def sobel(a):
    a = a.astype(np.int32)
    h, w = a.shape
    out = np.zeros((h, w), dtype=np.int32)
    bands = 64
    edges = np.linspace(1, max(1, h - 1), bands + 1).astype(int)
    work = 0.0
    for i in v.progress(bands, "Sobel gradient sweep", delay=0.006):
        if i == 0:
            continue
        y0 = max(1, int(edges[i - 1]))
        y1 = min(h - 1, int(edges[i]))
        if y1 <= y0:
            continue
        tb = time.perf_counter()
        top = a[y0 - 1:y1 - 1]
        mid = a[y0:y1]
        bot = a[y0 + 1:y1 + 1]
        gx = (top[:, 2:] + 2 * mid[:, 2:] + bot[:, 2:]) - (
            top[:, :-2] + 2 * mid[:, :-2] + bot[:, :-2]
        )
        gy = (bot[:, :-2] + 2 * bot[:, 1:-1] + bot[:, 2:]) - (
            top[:, :-2] + 2 * top[:, 1:-1] + top[:, 2:]
        )
        out[y0:y1, 1:-1] = np.abs(gx) + np.abs(gy)
        work += time.perf_counter() - tb
    return np.clip(out, 0, 255).astype(np.uint8), work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pixels", default=str(OUT / "pixels.hex"))
    args = ap.parse_args()

    v.banner(
        "RISC-V  ×  EDGE-VISION  PIPELINE",
        "stage 2 · CPU Sobel edge detection on the pixel stream",
    )
    v.stage(2, 3, "PIXELS → EDGES", "3×3 Sobel operator · |Gx| + |Gy| magnitude")

    pixels_path = Path(args.pixels)
    if not pixels_path.exists():
        raise SystemExit(f"missing {pixels_path}; run 01_image_to_pixels.py first")

    raw = read_hex(pixels_path)
    h, w = infer_shape(raw, pixels_path)
    gray = raw.reshape(h, w)

    v.kv("input stream", pixels_path.name)
    v.kv("image", f"{w} x {h}", "px")
    v.kv("bytes consumed", f"{raw.size:,}", "uint8")
    v.note("kernel:  Gx = [ -1 0 +1 ; -2 0 +2 ; -1 0 +1 ]", v.CYAN)
    v.note("         Gy = [ -1 -2 -1 ;  0 0  0 ; +1 +2 +1 ]", v.CYAN)
    print()

    mag, dt = sobel(gray)

    interior = max(1, (h - 2) * (w - 2))
    edge_px = int(np.count_nonzero(mag > 32))
    strong = int(np.count_nonzero(mag > 128))
    ops = interior * 20
    mpps = (h * w) / max(dt, 1e-9) / 1e6

    print()
    v.kv("pixels processed", f"{h * w:,}", "px", v.LIME)
    v.kv("arithmetic ops", f"{ops:,}", "est. scalar ops", v.AMBER)
    v.kv("edge pixels", f"{edge_px:,}", f"({100 * edge_px / (h * w):.1f}%)", v.CYAN)
    v.kv("strong edges", f"{strong:,}", "|G| > 128", v.MAGENTA)
    v.kv("peak gradient", f"{int(mag.max())}", "/ 255", v.LIME)
    v.kv("mean gradient", f"{mag.mean():.2f}", "/ 255", v.CYAN)
    v.kv("CPU time", f"{dt * 1000:.2f}", "ms", v.AMBER)
    v.kv("throughput", f"{mpps:.2f}", "Mpixel/s", v.LIME)

    out = OUT
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "02_edges.npy", mag)
    write_hex(out / "edges.hex", mag)
    scale = max(2, 640 // max(w, h))
    Image.fromarray(colorize(mag), "RGB").resize(
        (w * scale, h * scale), Image.NEAREST
    ).save(out / "02_edges.png")
    Image.fromarray(overlay(gray, mag), "RGB").resize(
        (w * scale, h * scale), Image.NEAREST
    ).save(out / "02_overlay.png")

    print()
    v.rule()
    v.note("STRONGEST GRADIENT VALUES IN THE STREAM", v.MAGENTA)
    v.rule()
    top = np.sort(mag.reshape(-1))[-16:][::-1]
    print("  " + "  ".join(v.fg(f"{int(x):3d}", v._lerp(v.CYAN, v.MAGENTA, x / 255))
                            for x in top))

    print()
    v.rule()
    v.note("EDGE MAP PREVIEW", v.MAGENTA)
    v.rule()
    v.pixel_preview(mag, cols=44, palette="neon",
                    title="Sobel |Gx|+|Gy| — cyan/magenta = strong edge")

    print()
    v.note(f"wrote {out / 'edges.hex'}", v.LIME)
    v.note(f"wrote {out / '02_edges.png'}", v.LIME)
    v.note(f"wrote {out / '02_overlay.png'}", v.LIME)
    print()
    print("  " + v.bold(v.gradient("STAGE 2 COMPLETE — edge map serialised back to bytes")))
    print()


if __name__ == "__main__":
    main()
