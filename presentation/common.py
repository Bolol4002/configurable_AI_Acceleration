#!/usr/bin/env python3
"""Shared image / hex helpers for the presentation pipeline."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
OUT = BASE / "output"
INPUT_GLOB = ("input.png", "input.jpg", "input.jpeg", "input.bmp", "input.webp")
FALLBACK = ROOT / "IMG" / "sobel_input.png"

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def resolve_input(arg=None):
    """Pick the demo image: CLI arg > presentation/input.* > IMG/sobel_input.png."""
    if arg:
        p = Path(arg).expanduser()
        if not p.is_absolute():
            # relative paths resolve against the cwd first, then the repo root,
            # so "IMG/x.png" works from inside presentation/ as well as above it
            for base in (Path.cwd(), ROOT):
                if (base / p).exists():
                    return base / p
            p = Path.cwd() / p
        if not p.exists():
            raise FileNotFoundError(f"input image not found: {p}")
        return p
    for name in INPUT_GLOB:
        p = BASE / name
        if p.exists():
            return p
    if FALLBACK.exists():
        return FALLBACK
    raise FileNotFoundError(
        "no input image found; pass one as an argument or drop input.png "
        "into the presentation folder"
    )


def load_grayscale(path, max_side=160):
    """Load an image, convert to 8-bit grayscale (0..255), cap the resolution."""
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        img.seek(0)
    img = img.convert("L")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                         Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


def write_hex(path, arr):
    values = np.asarray(arr, dtype=np.uint8).reshape(-1)
    Path(path).write_text("".join(f"{int(v):02x}\n" for v in values))
    return len(values)


def read_hex(path):
    tokens = Path(path).read_text().split()
    return np.array([int(t, 16) for t in tokens], dtype=np.uint8)


def upscale(arr, scale):
    img = Image.fromarray(np.asarray(arr, dtype=np.uint8), "L")
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def ensure_out():
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT
