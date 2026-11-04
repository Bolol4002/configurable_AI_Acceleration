#!/usr/bin/env python3
"""Shared terminal eye-candy for the presentation pipeline.

Everything here is pure standard library + numpy. Colours are 24-bit ANSI so
the demo looks the same on any modern terminal. Set NO_COLOR=1 to disable.
"""

import os
import shutil
import sys
import time

import numpy as np

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

CYAN = (0, 229, 255)
MAGENTA = (255, 0, 190)
LIME = (120, 255, 90)
AMBER = (255, 190, 40)
VIOLET = (150, 90, 255)
WHITE = (235, 240, 255)
GREY = (110, 120, 140)
RED = (255, 70, 90)


def _color_enabled():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return sys.stdout.isatty()


COLOR = _color_enabled()


def fg(text, rgb):
    if not COLOR:
        return str(text)
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}{RESET}"


def bg(text, rgb):
    if not COLOR:
        return str(text)
    return f"\033[48;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}{RESET}"


def bold(text):
    return f"{BOLD}{text}{RESET}" if COLOR else str(text)


def dim(text):
    return f"{DIM}{text}{RESET}" if COLOR else str(text)


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient(text, a=CYAN, b=MAGENTA):
    if not COLOR or not text:
        return text
    out = []
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        out.append(fg(ch, _lerp(a, b, i / n)))
    return "".join(out)


def banner(title, subtitle=""):
    width = max(len(title) + 8, 66)
    inner = width - 2
    print()
    print(fg("╔" + "═" * inner + "╗", CYAN))
    print(
        fg("║", CYAN)
        + " " * 2
        + bold(gradient(title.center(inner - 4), CYAN, MAGENTA))
        + " " * 2
        + fg("║", CYAN)
    )
    if subtitle:
        print(
            fg("║", CYAN)
            + " " * 2
            + fg(subtitle.center(inner - 4), GREY)
            + " " * 2
            + fg("║", CYAN)
        )
    print(fg("╚" + "═" * inner + "╝", CYAN))
    print()


def stage(number, total, title, subtitle=""):
    tag = f" STAGE {number}/{total} "
    print()
    print(fg("▚" * 3, MAGENTA) + bg(bold(tag), (30, 30, 55)) + fg("▞" * 3, CYAN))
    print("  " + bold(gradient(title, CYAN, LIME)))
    if subtitle:
        print("  " + fg(subtitle, GREY))
    print(fg("─" * 66, (45, 50, 70)))


def rule(char="─", width=66, rgb=(45, 50, 70)):
    print(fg(char * width, rgb))


def kv(label, value, unit="", rgb=CYAN):
    dots = "." * max(3, 28 - len(label))
    print(f"  {fg(label, GREY)} {dim(dots)} {bold(fg(f'{value}', rgb))} {dim(unit)}")


def note(text, rgb=GREY):
    print("  " + fg(text, rgb))


def hexdump(data, limit=64, per_line=16):
    data = np.asarray(data, dtype=np.uint8).reshape(-1)[:limit]
    for row in range(0, len(data), per_line):
        chunk = data[row:row + per_line]
        addr = fg(f"{row:04x}", VIOLET)
        cells = " ".join(fg(f"{v:02x}", _lerp(CYAN, MAGENTA, v / 255.0)) for v in chunk)
        print(f"  {addr}  {cells}")


def histogram(arr, width=48, bins=16):
    a = np.asarray(arr, dtype=np.uint8).reshape(-1)
    counts, edges = np.histogram(a, bins=bins, range=(0, 256))
    peak = counts.max() or 1
    for i, c in enumerate(counts):
        lo, hi = int(edges[i]), int(edges[i + 1]) - 1
        bar_len = int(round((c / peak) * width))
        bar = "█" * bar_len
        col = _lerp(CYAN, MAGENTA, i / max(bins - 1, 1))
        print(
            f"  {fg(f'{lo:3d}-{hi:3d}', GREY)} "
            f"{fg(bar, col)}{' ' * (width - bar_len)} {dim(f'{c:5d}')}"
        )


def _ramp_colors(values, stops, colors):
    vals = np.asarray(values, dtype=np.float32) / 255.0
    stops = np.asarray(stops, dtype=np.float32)
    colors = np.asarray(colors, dtype=np.float32)
    out = np.empty((*vals.shape, 3), dtype=np.float32)
    for k in range(3):
        out[..., k] = np.interp(vals, stops, colors[:, k])
    return out.astype(np.uint8)


def pixel_preview(arr, cols=44, title="", chars="  ", palette="gray"):
    a = np.asarray(arr, dtype=np.uint8)
    if a.ndim != 2:
        raise ValueError("pixel_preview expects a 2-D grayscale array")
    h, w = a.shape
    rows = max(1, int(round(cols * (h / w) * 0.5)))
    ys = np.linspace(0, h - 1, rows).astype(int)
    xs = np.linspace(0, w - 1, cols).astype(int)
    small = a[np.ix_(ys, xs)]
    if palette == "neon":
        rgb = _ramp_colors(
            small,
            [0.0, 0.30, 0.70, 1.0],
            [(8, 10, 24), (0, 200, 255), (255, 60, 220), (255, 255, 255)],
        )
    else:
        rgb = _ramp_colors(
            small,
            [0.0, 0.5, 1.0],
            [(14, 16, 32), (110, 125, 160), (238, 242, 255)],
        )
    if title:
        print("  " + fg(title, GREY))
    if not COLOR:
        ramp = " .:-=+*#%@"
        for row in small:
            print("  " + "".join(ramp[min(len(ramp) - 1, int(v) * len(ramp) // 256)]
                                  for v in row))
    else:
        for row in rgb:
            print("  " + "".join(bg(chars, (int(c[0]), int(c[1]), int(c[2])))
                                 for c in row))
    print("  " + dim(f"{w} x {h} px  ·  sampled to {cols} x {rows}"))


def progress(total, label="processing", width=36, delay=0.006):
    """Generator yielding 0..total while drawing a gradient progress bar."""
    total = max(1, int(total))
    tty = sys.stdout.isatty()
    t0 = time.time()
    for i in range(total + 1):
        frac = i / total
        if tty:
            filled = int(width * frac)
            bar = []
            for j in range(width):
                if j < filled:
                    bar.append(fg("█", _lerp(CYAN, MAGENTA, j / max(width - 1, 1))))
                else:
                    bar.append(fg("░", (38, 42, 60)))
            pct = f"{frac * 100:5.1f}%"
            spinner = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"[i % 10]
            sys.stdout.write(
                f"\r  {fg(spinner, LIME)} {fg(label, GREY):<28} "
                f"{''.join(bar)} {bold(pct)} "
            )
            sys.stdout.flush()
        if delay:
            time.sleep(delay)
        yield i
    if tty:
        dt = time.time() - t0
        sys.stdout.write(f"\r  {fg('✔', LIME)} {fg(label, GREY):<28} "
                         f"{' ' * width} {bold(f'{dt:0.2f}s')}\n")
        sys.stdout.flush()
    else:
        print(f"  {label}: done")


def hex_rain(rows=6, cols=48, delay=0.03):
    """Quick Matrix-style hex burst before the pixel dump."""
    if not sys.stdout.isatty():
        return
    rng = np.random.default_rng(7)
    for _ in range(rows):
        cells = []
        for _ in range(cols):
            v = int(rng.integers(0, 256))
            if rng.random() < 0.12:
                cells.append(fg(f"{v:02x}", WHITE))
            elif rng.random() < 0.5:
                cells.append(fg(f"{v:02x}", _lerp(CYAN, LIME, rng.random())))
            else:
                cells.append(dim(f"{v:02x}"))
        print("  " + " ".join(cells))
        time.sleep(delay)


def terminal_width(default=80):
    try:
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def type_out(text, delay=0.012):
    if not sys.stdout.isatty():
        print(text)
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")
