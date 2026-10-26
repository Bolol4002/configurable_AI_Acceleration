#!/usr/bin/env python3
"""Generate data.hex for the 8x8 Sobel self-test.

The image is the deterministic ramp used in the design notes:
    data[y][x] = 10 + y*5 + x*10
"""

import sys

W = 8
H = 8


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data.hex"
    with open(out, "w") as f:
        for y in range(H):
            for x in range(W):
                f.write("%02x\n" % (10 + y * 5 + x * 10))
    print("wrote %dx%d image to %s" % (W, H, out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
