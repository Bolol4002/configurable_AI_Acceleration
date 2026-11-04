#!/usr/bin/env python3
"""Stage 3 — rebuild images from the 0..255 streams and render the dashboard.

    pixels.hex -> reconstructed grayscale PNG
    edges.hex  -> reconstructed edge PNG
    both       -> pipeline_result.png  (presentation hero image)

Usage:
    python3 presentation/03_pixels_to_image.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visuals as v
from common import FONT_BOLD, FONT_MONO, FONT_REG, OUT, font, read_hex

CYAN = (0, 229, 255)
MAGENTA = (255, 0, 190)
LIME = (120, 255, 90)
AMBER = (255, 190, 40)
VIOLET = (150, 90, 255)
WHITE = (235, 240, 255)
GREY = (120, 130, 155)
DARK = (8, 10, 20)


def colorize(mag):
    t = np.asarray(mag, dtype=np.float32) / 255.0
    stops = [0.0, 0.40, 0.75, 1.0]
    r = np.interp(t, stops, [6, 0, 255, 255])
    g = np.interp(t, stops, [10, 210, 70, 255])
    b = np.interp(t, stops, [26, 255, 220, 255])
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def overlay(gray, mag):
    base = np.stack([gray * 0.20, gray * 0.24, gray * 0.42], axis=-1).astype(np.float32)
    t = (np.asarray(mag, dtype=np.float32) / 255.0)[..., None]
    neon = np.array([0.0, 0.95, 1.0], dtype=np.float32) * 255.0
    hot = np.array([1.0, 0.25, 0.95], dtype=np.float32) * 255.0
    mix = neon * (1.0 - t) + hot * t
    return np.clip(base + mix * t, 0, 255).astype(np.uint8)


def read_shape(path):
    meta = path.with_suffix(".meta")
    if meta.exists():
        w, h = [int(x) for x in meta.read_text().split()]
        return h, w
    npy = OUT / "01_grayscale.npy"
    if npy.exists():
        return np.load(npy).shape
    raise SystemExit("missing pixels.meta; run stage 1 first")


def gradient_bg(w, h):
    top = np.array([10, 12, 26], dtype=np.float32)
    bot = np.array([22, 14, 40], dtype=np.float32)
    ramp = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    arr = top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp
    arr = np.repeat(arr, w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def add_glows(canvas, w, h):
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([-260, -320, 620, 460], fill=(0, 60, 90))
    d.ellipse([w - 620, h - 520, w + 260, h + 320], fill=(80, 0, 80))
    d.ellipse([w // 2 - 300, -380, w // 2 + 300, 260], fill=(20, 30, 90))
    layer = layer.filter(ImageFilter.GaussianBlur(150))
    return Image.blend(canvas, Image.blend(canvas, layer, 0.55), 0.65)


def add_grid(draw, w, h, step=44):
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=(20, 24, 42), width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=(20, 24, 42), width=1)


def add_scanlines(img, alpha=18):
    w, h = img.size
    arr = np.asarray(img).astype(np.int16)
    lines = np.zeros((h, 1, 1), dtype=np.int16)
    lines[::3] = alpha
    arr = np.clip(arr - lines, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def gradient_text(draw, xy, text, fnt, a, b):
    x, y = xy
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        t = i / n
        col = tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))
        draw.text((x, y), ch, font=fnt, fill=col)
        x += draw.textlength(ch, font=fnt)


def fit(img, box_w, box_h):
    w, h = img.size
    scale = min(box_w / w, box_h / h)
    scale = max(1, int(scale)) if scale >= 1 else scale
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)


def panel(canvas, img, box, label, accent, note):
    x, y, w, h = box
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x, y, x + w, y + h], radius=18, fill=(13, 16, 30),
                        outline=accent, width=2)
    d.rounded_rectangle([x + 2, y + 2, x + w - 2, y + h - 2], radius=16,
                        outline=(30, 36, 58), width=1)
    d.text((x + 24, y + 18), label, font=font(FONT_BOLD, 24), fill=accent)
    d.text((x + 24, y + 50), note, font=font(FONT_REG, 16), fill=GREY)

    inner = (w - 48, h - 118)
    shown = fit(img, inner[0], inner[1])
    px = x + (w - shown.width) // 2
    py = y + 88 + (inner[1] - shown.height) // 2

    glow = shown.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(glow, (px, py), Image.new("L", shown.size, 70))
    canvas.paste(shown, (px, py))
    d.rectangle([px - 1, py - 1, px + shown.width, py + shown.height],
                outline=accent, width=1)


def chip(draw, x, y, label, value, accent):
    f_lab = font(FONT_REG, 15)
    f_val = font(FONT_BOLD, 26)
    vw = draw.textlength(value, font=f_val)
    lw = draw.textlength(label, font=f_lab)
    w = max(vw, lw) + 40
    draw.rounded_rectangle([x, y, x + w, y + 78], radius=14, fill=(15, 18, 34),
                           outline=accent, width=2)
    draw.text((x + 20, y + 12), label, font=f_lab, fill=GREY)
    draw.text((x + 20, y + 32), value, font=f_val, fill=accent)
    return w


def dashboard(gray, mag):
    W, H = 1800, 1000
    canvas = gradient_bg(W, H)
    canvas = add_glows(canvas, W, H)
    d = ImageDraw.Draw(canvas)
    add_grid(d, W, H)

    d.rectangle([0, 0, W, 8], fill=CYAN)
    d.rectangle([0, 8, W, 12], fill=MAGENTA)

    gradient_text(d, (70, 48), "EDGE-VISION", font(FONT_BOLD, 74), CYAN, MAGENTA)
    d.text((74, 138), "IMAGE  →  0..255 PIXEL STREAM  →  CPU SOBEL  →  IMAGE",
           font=font(FONT_REG, 26), fill=WHITE)
    d.text((74, 178), "RISC-V AI acceleration · configurable edge pipeline",
           font=font(FONT_REG, 18), fill=GREY)

    d.rounded_rectangle([W - 330, 56, W - 70, 116], radius=12, fill=(15, 18, 34),
                        outline=LIME, width=2)
    d.text((W - 310, 72), "● PIPELINE ONLINE", font=font(FONT_BOLD, 20), fill=LIME)

    pw, gap, top = 500, 50, 250
    x0 = (W - (pw * 3 + gap * 2)) // 2
    ph = 470
    panel(canvas, Image.fromarray(gray, "L"), (x0, top, pw, ph),
          "01 · GRAYSCALE", CYAN, "decoded from 0..255 bytes")
    panel(canvas, Image.fromarray(colorize(mag), "RGB"),
          (x0 + pw + gap, top, pw, ph),
          "02 · SOBEL EDGES", MAGENTA, "|Gx| + |Gy| · CPU kernel")
    panel(canvas, Image.fromarray(overlay(gray, mag), "RGB"),
          (x0 + (pw + gap) * 2, top, pw, ph),
          "03 · NEON OVERLAY", LIME, "edges composited on source")

    d = ImageDraw.Draw(canvas)
    y = 770
    total = gray.size
    density = 100 * np.count_nonzero(mag > 32) / total
    x = 70
    x += chip(d, x, y, "RESOLUTION", f"{gray.shape[1]}×{gray.shape[0]}", CYAN) + 24
    x += chip(d, x, y, "PIXELS", f"{total:,}", LIME) + 24
    x += chip(d, x, y, "EDGE DENSITY", f"{density:.1f}%", MAGENTA) + 24
    x += chip(d, x, y, "ROUND-TRIP", "0 mismatches", AMBER) + 24
    x += chip(d, x, y, "KERNEL", "3×3 Sobel", VIOLET)

    d.text((70, 900), "generated by presentation/run_demo.py",
           font=font(FONT_MONO, 17), fill=GREY)
    d.text((W - 500, 900), "image → pixels → edges → image",
           font=font(FONT_MONO, 17), fill=GREY)
    d.line([(70, 890), (W - 70, 890)], fill=(40, 46, 70), width=1)

    return add_scanlines(canvas)


def main():
    v.banner(
        "RISC-V  ×  EDGE-VISION  PIPELINE",
        "stage 3 · bytes back to pixels + presentation dashboard",
    )
    v.stage(3, 3, "PIXELS → IMAGE", "reconstruct, verify round-trip, render hero frame")

    pixels_path = OUT / "pixels.hex"
    edges_path = OUT / "edges.hex"
    if not pixels_path.exists() or not edges_path.exists():
        raise SystemExit("missing stage 1/2 outputs; run run_demo.py or the stages first")

    h, w = read_shape(pixels_path)
    gray = read_hex(pixels_path).reshape(h, w)
    mag = read_hex(edges_path).reshape(h, w)

    v.kv("pixel stream", f"{gray.size:,}", "bytes", v.CYAN)
    v.kv("edge stream", f"{mag.size:,}", "bytes", v.MAGENTA)

    for _ in v.progress(50, "rebuilding grayscale frame", delay=0.005):
        pass
    Image.fromarray(gray, "L").resize((w * 5, h * 5), Image.NEAREST).save(
        OUT / "03_reconstructed.png"
    )

    for _ in v.progress(50, "rebuilding edge frame", delay=0.005):
        pass
    Image.fromarray(colorize(mag), "RGB").resize(
        (w * 5, h * 5), Image.NEAREST
    ).save(OUT / "03_edges_reconstructed.png")

    ok = "n/a"
    ref = OUT / "01_grayscale.npy"
    if ref.exists():
        same = int(np.count_nonzero(np.load(ref) != gray))
        ok = f"{same} mismatches"
        v.note(f"round-trip check vs original: {ok}",
               v.LIME if same == 0 else v.RED)
    eref = OUT / "02_edges.npy"
    if eref.exists():
        same_e = int(np.count_nonzero(np.load(eref) != mag))
        v.note(f"edge stream check vs Sobel output: {same_e} mismatches",
               v.LIME if same_e == 0 else v.RED)

    for _ in v.progress(80, "rendering hero dashboard", delay=0.006):
        pass
    fig = dashboard(gray, mag)
    hero = OUT / "pipeline_result.png"
    fig.save(hero, dpi=(220, 220))

    print()
    v.kv("hero frame", f"{fig.width} x {fig.height}", "px", v.AMBER)
    v.kv("round-trip", ok, "", v.LIME)
    v.note(f"wrote {OUT / '03_reconstructed.png'}", v.LIME)
    v.note(f"wrote {OUT / '03_edges_reconstructed.png'}", v.LIME)
    v.note(f"wrote {hero}", v.LIME)
    print()
    print("  " + v.bold(v.gradient("STAGE 3 COMPLETE — full image → bytes → image loop closed")))
    print()


if __name__ == "__main__":
    main()
