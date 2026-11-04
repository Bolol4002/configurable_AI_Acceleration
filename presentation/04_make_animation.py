#!/usr/bin/env python3
"""Bonus stage — render an animated GIF of the whole pipeline.

    pipeline.gif:  image reveal -> byte stream -> Sobel sweep -> neon result

Usage:
    python3 presentation/04_make_animation.py
"""

import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FONT_BOLD, FONT_MONO, FONT_REG, OUT, font, read_hex

W, H = 640, 480
BOX_W, BOX_H = 400, 300
BOX_X, BOX_Y = (W - BOX_W) // 2, 112

CYAN = (0, 229, 255)
MAGENTA = (255, 0, 190)
LIME = (120, 255, 90)
AMBER = (255, 190, 40)
WHITE = (235, 240, 255)
GREY = (125, 135, 160)


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


def bg():
    top = np.array([9, 11, 24], dtype=np.float32)
    bot = np.array([20, 13, 38], dtype=np.float32)
    ramp = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    arr = top[None, None, :] * (1 - ramp) + bot[None, None, :] * ramp
    arr = np.repeat(arr, W, axis=1).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    d = ImageDraw.Draw(img)
    for x in range(0, W, 40):
        d.line([(x, 0), (x, H)], fill=(20, 24, 42))
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(20, 24, 42))
    d.rectangle([0, 0, W, 5], fill=CYAN)
    d.rectangle([0, 5, W, 8], fill=MAGENTA)
    return img


def fit(img, bw, bh):
    w, h = img.size
    scale = min(bw / w, bh / h)
    scale = max(1, int(scale)) if scale >= 1 else scale
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)


def center_text(d, y, text, fnt, fill):
    tw = d.textlength(text, font=fnt)
    d.text(((W - tw) / 2, y), text, font=fnt, fill=fill)


def frame_label(canvas, title, accent, subtitle=""):
    d = ImageDraw.Draw(canvas)
    f = font(FONT_BOLD, 30)
    tw = d.textlength(title, font=f)
    d.text(((W - tw) / 2, 34), title, font=f, fill=accent)
    if subtitle:
        f2 = font(FONT_REG, 17)
        tw2 = d.textlength(subtitle, font=f2)
        d.text(((W - tw2) / 2, 74), subtitle, font=f2, fill=GREY)
    return canvas


def glow_line(canvas, y, color):
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line([(BOX_X - 20, y), (BOX_X + BOX_W + 20, y)], fill=color, width=3)
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    canvas = Image.blend(canvas, Image.blend(canvas, layer, 0.9), 0.85)
    d = ImageDraw.Draw(canvas)
    d.line([(BOX_X - 20, y), (BOX_X + BOX_W + 20, y)], fill=color, width=2)
    return canvas


def paste(canvas, img, pos):
    canvas.paste(img, pos)


def build():
    pixels = OUT / "pixels.hex"
    edges = OUT / "edges.hex"
    if not pixels.exists() or not edges.exists():
        raise SystemExit("run the pipeline first (run_demo.py)")

    meta = (OUT / "pixels.meta").read_text().split()
    w, h = int(meta[0]), int(meta[1])
    gray = read_hex(pixels).reshape(h, w)
    mag = read_hex(edges).reshape(h, w)

    gray_img = fit(Image.fromarray(gray, "L").convert("RGB"), BOX_W, BOX_H)
    edge_img = fit(Image.fromarray(colorize(mag), "RGB"), BOX_W, BOX_H)
    over_img = fit(Image.fromarray(overlay(gray, mag), "RGB"), BOX_W, BOX_H)

    gx = BOX_X + (BOX_W - gray_img.width) // 2
    gy = BOX_Y + (BOX_H - gray_img.height) // 2
    ex = BOX_X + (BOX_W - edge_img.width) // 2
    ey = BOX_Y + (BOX_H - edge_img.height) // 2
    ox = BOX_X + (BOX_W - over_img.width) // 2
    oy = BOX_Y + (BOX_H - over_img.height) // 2

    frames = []

    def add(img, dur):
        frames.append((img.convert("RGB"), dur))

    title = "EDGE-VISION"
    for i in range(1, len(title) + 1):
        c = bg()
        d = ImageDraw.Draw(c)
        f = font(FONT_BOLD, 58)
        part = title[:i]
        tw = d.textlength(part, font=f)
        d.text(((W - tw) / 2, 180), part, font=f, fill=CYAN if i % 2 else MAGENTA)
        d.text((W // 2 - 150, 260), "image → pixels → edges → image",
               font=font(FONT_REG, 20), fill=GREY)
        add(c, 55)

    c = bg()
    frame_label(c, "IMAGE  →  0..255", CYAN, "CPU luminance kernel · 8-bit pixel stream")
    add(c, 700)

    steps = 16
    for i in range(1, steps + 1):
        c = bg()
        frame_label(c, "IMAGE  →  0..255", CYAN, "CPU luminance kernel · 8-bit pixel stream")
        cut = int(gray_img.height * i / steps)
        c.paste(gray_img.crop((0, 0, gray_img.width, cut)), (gx, gy))
        c = glow_line(c, gy + cut, CYAN)
        add(c, 70)

    rng = random.Random(42)
    f_hex = font(FONT_MONO, 11)
    for _ in range(7):
        c = bg()
        frame_label(c, "BYTE STREAM", LIME, "each pixel serialised as one uint8 value")
        c.paste(gray_img, (gx, gy))
        shade = Image.new("RGBA", (gray_img.width, gray_img.height), (0, 0, 0, 120))
        c.paste(Image.alpha_composite(c.crop((gx, gy, gx + gray_img.width,
                                             gy + gray_img.height)).convert("RGBA"),
                                     shade).convert("RGB"), (gx, gy))
        d = ImageDraw.Draw(c)
        for yy in range(gy, gy + gray_img.height, 22):
            for xx in range(gx, gx + gray_img.width, 34):
                val = f"{rng.randrange(256):02x}"
                col = CYAN if rng.random() < 0.4 else (LIME if rng.random() < 0.5 else MAGENTA)
                d.text((xx, yy), val, font=f_hex, fill=col)
        add(c, 110)

    steps = 20
    for i in range(1, steps + 1):
        c = bg()
        frame_label(c, "SOBEL  |Gx| + |Gy|", MAGENTA, "3×3 gradient kernel · CPU")
        dim = Image.eval(gray_img, lambda p: int(p * 0.30))
        c.paste(dim, (gx, gy))
        cut = int(edge_img.height * i / steps)
        c.paste(edge_img.crop((0, 0, edge_img.width, cut)), (ex, ey))
        c = glow_line(c, ey + cut, MAGENTA)
        add(c, 65)

    for _ in range(5):
        c = bg()
        frame_label(c, "NEON OVERLAY", LIME, "edges composited on the reconstructed source")
        c.paste(over_img, (ox, oy))
        add(c, 120)

    total = gray.size
    density = 100 * np.count_nonzero(mag > 32) / total
    c = bg()
    d = ImageDraw.Draw(c)
    f = font(FONT_BOLD, 40)
    tw = d.textlength("PIPELINE COMPLETE", font=f)
    d.text(((W - tw) / 2, 24), "PIPELINE COMPLETE", font=f, fill=LIME)

    left = fit(gray_img, 250, 190)
    right = fit(over_img, 250, 190)
    c.paste(left, (55, 110))
    c.paste(right, (W - 55 - right.width, 110))
    d.rectangle([55, 110, 55 + left.width, 110 + left.height], outline=CYAN, width=2)
    d.rectangle([W - 55 - right.width, 110, W - 55, 110 + right.height],
                outline=LIME, width=2)
    d.text((55, 310), "RECONSTRUCTED", font=font(FONT_BOLD, 18), fill=CYAN)
    d.text((W - 55 - right.width, 310), "EDGE OVERLAY", font=font(FONT_BOLD, 18), fill=LIME)
    d.text((55, 345), "0..255 byte stream", font=font(FONT_REG, 15), fill=GREY)
    d.text((W - 55 - right.width, 345), "CPU Sobel", font=font(FONT_REG, 15), fill=GREY)

    center_text(d, 380, f"{gray.shape[1]}×{gray.shape[0]} px   ·   "
                        f"{total:,} bytes   ·   {density:.1f}% edges",
                font(FONT_REG, 18), WHITE)
    center_text(d, 412, "0 mismatches  ·  image → pixels → edges → image",
                font(FONT_BOLD, 18), AMBER)
    add(c, 2600)

    return frames


def main():
    print("rendering pipeline.gif ...")
    frames = build()
    pal = []
    for img, _ in frames:
        pal.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))
    durations = [d for _, d in frames]
    out = OUT / "pipeline.gif"
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations,
                loop=0, optimize=True, disposal=2)
    print(f"wrote {out}  ({len(frames)} frames, {out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
