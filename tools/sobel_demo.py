#!/usr/bin/env python3
"""Run a demo image through the Sobel PCPI coprocessor and build a report figure.

Pipeline:
  1. draw a 128x96 grayscale test scene with Pillow,
  2. write it as sobel_input.hex for tb_sobel_dump.v,
  3. simulate the RTL with Icarus Verilog (which also checks a golden model),
  4. read the dumped hardware output, verify it in Python, and compose
     IMG/sobel_edge_detection.png with the input and the Sobel result.

Usage:  python3 tools/sobel_demo.py
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 128, 96
SCALE = 6

ROOT = Path(__file__).resolve().parent.parent
RTL_DIR = ROOT / "RiscV_Basys3_Regular"
IMG_DIR = ROOT / "IMG"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def make_scene():
    """Draw a simple, edge-rich grayscale scene."""
    img = Image.new("L", (W, H), 0)
    px = img.load()

    for y in range(H):
        for x in range(W):
            if y < 64:
                t = y / 63.0
                px[x, y] = int(70 + 100 * t)
            else:
                px[x, y] = 55

    d = ImageDraw.Draw(img)

    d.ellipse([11, 7, 33, 29], fill=245)

    d.polygon([(36, 42), (61, 20), (86, 42)], fill=105)
    d.rectangle([40, 42, 82, 64], fill=150)
    d.rectangle([55, 52, 63, 64], fill=35)
    d.rectangle([68, 48, 76, 56], fill=210)

    d.rectangle([100, 50, 104, 64], fill=40)
    d.ellipse([88, 26, 116, 54], fill=75)
    d.ellipse([92, 18, 112, 38], fill=85)

    return img


def golden(arr):
    a = arr.astype(np.int32)
    out = np.zeros_like(a)
    p00, p01, p02 = a[:-2, :-2], a[:-2, 1:-1], a[:-2, 2:]
    p10, p12 = a[1:-1, :-2], a[1:-1, 2:]
    p20, p21, p22 = a[2:, :-2], a[2:, 1:-1], a[2:, 2:]
    gx = (p02 + 2 * p12 + p22) - (p00 + 2 * p10 + p20)
    gy = (p20 + 2 * p21 + p22) - (p00 + 2 * p01 + p02)
    out[1:-1, 1:-1] = np.clip(np.abs(gx) + np.abs(gy), 0, 255)
    return out.astype(np.uint8)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def compose(inp, out):
    inp_big = inp.resize((W * SCALE, H * SCALE), Image.NEAREST)
    out_big = out.resize((W * SCALE, H * SCALE), Image.NEAREST)

    margin, gap, label_h = 44, 34, 44
    title_h, footer_h = 58, 46
    pw, ph = inp_big.size
    cw = margin * 2 + pw * 2 + gap
    ch = margin + title_h + label_h + ph + footer_h

    canvas = Image.new("RGB", (cw, ch), "white")
    d = ImageDraw.Draw(canvas)
    f_title = font(FONT_BOLD, 30)
    f_label = font(FONT_BOLD, 22)
    f_foot = font(FONT_REG, 18)

    def center(text, y, f):
        bb = d.textbbox((0, 0), text, font=f)
        d.text(((cw - (bb[2] - bb[0])) / 2, y), text, fill=(20, 20, 20), font=f)

    center("Sobel Edge Detection: RTL Simulation Output", margin // 2 + 4, f_title)

    x0 = margin
    y_img = margin + title_h + label_h
    x1 = x0 + pw + gap

    canvas.paste(inp_big.convert("RGB"), (x0, y_img))
    canvas.paste(out_big.convert("RGB"), (x1, y_img))
    d.rectangle([x0 - 1, y_img - 1, x0 + pw, y_img + ph], outline=(120, 120, 120))
    d.rectangle([x1 - 1, y_img - 1, x1 + pw, y_img + ph], outline=(120, 120, 120))

    d.text((x0, margin + title_h + 8), f"Input image ({W} x {H})",
           fill=(20, 20, 20), font=f_label)
    d.text((x1, margin + title_h + 8), "Sobel magnitude (hardware output)",
           fill=(20, 20, 20), font=f_label)

    foot = ("Hardware output matches the software baseline and the golden model "
            "bit-exactly (0 mismatches).")
    center(foot, y_img + ph + 14, f_foot)

    return canvas


def main():
    RTL_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    scene = make_scene()
    scene.save(IMG_DIR / "sobel_input.png")

    values = np.asarray(scene, dtype=np.uint8).reshape(-1)
    (RTL_DIR / "sobel_input.hex").write_text(
        "".join(f"{v:02x}\n" for v in values)
    )

    print("[1/3] compiling RTL testbench ...")
    subprocess.run(
        ["iverilog", "-g2005", "-o", "/tmp/tb_sobel_dump.vvp",
         "tb_sobel_dump.v", "pcpi_sobel.v"],
        cwd=RTL_DIR, check=True,
    )
    print("[2/3] simulating Sobel coprocessor ...")
    subprocess.run(["vvp", "/tmp/tb_sobel_dump.vvp"], cwd=RTL_DIR, check=True)

    hw = np.array([
        int(line, 16)
        for line in (RTL_DIR / "sobel_output.hex").read_text().split()
    ], dtype=np.uint8).reshape(H, W)

    ref = golden(np.asarray(scene, dtype=np.uint8))
    mismatches = int(np.count_nonzero(hw != ref))
    if mismatches:
        print(f"ERROR: RTL output differs from Python golden model "
              f"({mismatches} bytes)")
        return 1

    print("[3/3] composing figure ...")
    fig = compose(scene, Image.fromarray(hw, "L"))
    out_png = IMG_DIR / "sobel_edge_detection.png"
    fig.save(out_png, dpi=(220, 220))
    print(f"wrote {out_png.relative_to(ROOT)}  ({fig.width}x{fig.height})")
    print("RTL output == software baseline == golden model (0 mismatches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
