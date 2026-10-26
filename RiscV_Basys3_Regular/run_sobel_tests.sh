#!/usr/bin/env bash
# Rebuild firmware/data and run both Sobel testbenches with Icarus Verilog.
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] assembling firmware..."
python3 ../tools/rv32asm.py programs/sobel_test.S firmware.hex

echo "[2/4] generating test image..."
python3 ../tools/gen_sobel_data.py data.hex

echo "[3/4] standalone coprocessor test..."
iverilog -g2005 -o /tmp/tb_pcpi_sobel.vvp tb_pcpi_sobel.v pcpi_sobel.v
vvp /tmp/tb_pcpi_sobel.vvp

echo
echo "[4/4] full SoC integration test..."
iverilog -g2005 -o /tmp/tb_sobel_soc.vvp \
    tb_sobel_soc.v top.v soc_mem.v pcpi_sobel.v picorv32.v
vvp /tmp/tb_sobel_soc.vvp
