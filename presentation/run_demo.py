#!/usr/bin/env python3
"""One-command presentation demo.

    python3 presentation/run_demo.py [image] [--no-gif] [--open]

Runs the full pipeline:
    01 image -> 0..255 pixel stream
    02 CPU Sobel edge detection
    03 reconstruct images + hero dashboard
    04 animated pipeline.gif
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
PY = sys.executable


def run(script, *args):
    cmd = [PY, str(BASE / script), *args]
    subprocess.run(cmd, check=True)


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", help="input image (defaults to IMG/sobel_input.png)")
    ap.add_argument("--no-gif", action="store_true", help="skip the animated GIF")
    ap.add_argument("--open", action="store_true", help="open the hero image when done")
    args = ap.parse_args()

    t0 = time.time()
    stage_args = [args.image] if args.image else []
    run("01_image_to_pixels.py", *stage_args)
    run("02_edge_detect.py")
    run("03_pixels_to_image.py")
    if not args.no_gif:
        run("04_make_animation.py")

    elapsed = time.time() - t0
    files = [
        OUT / "pixels.hex",
        OUT / "edges.hex",
        OUT / "01_grayscale.png",
        OUT / "02_edges.png",
        OUT / "02_overlay.png",
        OUT / "03_reconstructed.png",
        OUT / "pipeline_result.png",
    ]
    if not args.no_gif:
        files.append(OUT / "pipeline.gif")

    print()
    print("  \033[1m\033[38;2;120;255;90m" + "═" * 62 + "\033[0m")
    print("  \033[1m\033[38;2;0;229;255m  DEMO READY\033[0m"
          f"  ·  {elapsed:.1f}s total")
    print("  \033[38;2;120;255;90m" + "═" * 62 + "\033[0m")
    for f in files:
        if f.exists():
            print(f"    \033[38;2;150;90;255m{f.name:<26}\033[0m "
                  f"\033[38;2;120;130;155m{human(f.stat().st_size):>9}\033[0m")
    print()
    print("  Hero frame : presentation/output/pipeline_result.png")
    if not args.no_gif:
        print("  Animation  : presentation/output/pipeline.gif")
    print()

    if args.open and (OUT / "pipeline_result.png").exists():
        subprocess.Popen(["xdg-open", str(OUT / "pipeline_result.png")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
