# Sobel PCPI Coprocessor — Implementation Notes

This document describes the Sobel edge-detection extension that actually exists
in `RiscV_Basys3_Regular/`. It replaces the earlier forward-looking description
in `../sobel_instr.md`.

## 1. Files

| File | Purpose |
|---|---|
| `pcpi_sobel.v` | PCPI Sobel coprocessor (line buffers + parallel 3×3 datapath + FSM) |
| `soc_mem.v` | Unified instruction/data memory with byte lane writes |
| `top.v` | PicoRV32 + coprocessor + memory bus arbiter |
| `tb_pcpi_sobel.v` | Standalone coprocessor test against a golden model |
| `tb_sobel_soc.v` | Full CPU + coprocessor integration test |
| `programs/sobel_test.S` | Firmware: software Sobel, hardware Sobel, compare |
| `firmware.hex` | Assembled firmware (padded to 256 words) |
| `data.hex` | 8×8 test image |
| `run_sobel_tests.sh` | Rebuild and run both testbenches |

The RISC-V assembler and image generator live in `../tools/` because no RISC-V
toolchain is installed on the development machine.

## 2. Architecture

```
PicoRV32 (RV32I)
  │  PCPI: valid/insn/rs1/rs2/wr/rd/wait/ready
  ▼
pcpi_sobel
  ├─ 3 row buffers (line0/line1/line2), MAX_W = 128 bytes each
  ├─ parallel 3×3 window datapath
  │     Gx and Gy evaluated simultaneously from all 9 pixels
  │     |Gx| + |Gy| and clamp in the same combinational path
  ├─ FSM: ROW0 → LOAD×3 → COMPUTE → SHIFT → LOAD → ... → ROWLAST → DONE
  └─ memory master: word-aligned address + byte strobe
  │
  ▼
bus arbiter in top.v
  ├─ CPU owns the bus normally
  └─ coprocessor owns it while the CPU is stalled on pcpi_wait
  │
  ▼
soc_mem
  ├─ 0x0000_0000 .. 0x0000_03FF  instruction memory (1 KiB)
  └─ 0x0000_2000 .. 0x0000_3FFF  data memory (8 KiB)
```

The important property is **memory traffic**, not faster arithmetic:

* each source pixel is read exactly once (`H*W` reads),
* each output pixel is written exactly once (`H*W` writes),
* software needs at least three byte loads per interior pixel even with a
  sliding-window implementation.

The datapath is fully parallel: the nine window bytes feed both gradient sums
at once, and both absolute values plus the magnitude/clamp are evaluated
combinationally. One interior pixel is produced per clock.

Borders are defined to be zero, matching the software baseline.

## 3. ISA

Encoding: custom-0 opcode `7'b0001011`, `funct7 = 7'b0100001`, R-type fields.

| Mnemonic | funct3 | rs1 | rs2 | rd | Semantics |
|---|---|---|---|---|---|
| `SOBEL_SET` | 0 | image byte address | `{height[31:16], width[15:0]}` | — | Configure image |
| `SOBEL_RUN` | 1 | output byte address | — | bytes written | Run full image |
| `SOBEL_STATUS` | 2 | — | — | `{error, done, busy}` | Read status |
| `SOBEL_RESET` | 3 | — | — | — | Clear config and line buffers |

The width is clamped to `MAX_W`; if the requested width is larger, `error` is
set and `SOBEL_STATUS[31]` becomes one. `SOBEL_RUN` returns `W*H` in `rd`.

### Encoding helpers

```text
insn = (0x21 << 25) | (rs2 << 20) | (rs1 << 15) |
       (funct3 << 12) | (rd << 7) | 0x0B
```

## 4. Usage

```c
// image and output are byte arrays
SOBEL_SET(img, ((uint32_t)H << 16) | W);
uint32_t pixels = SOBEL_RUN(out);   // returns W*H
```

In the current hand-written firmware the two instructions are emitted by the
assembler as:

```asm
li    a0, IMG_BASE
li    a1, (IMG_H << 16) | IMG_W
sobel_set a0, a1
li    a0, OUT_HW
sobel_run a0, a2
```

## 5. Verification

Run all tests:

```bash
cd RiscV_Basys3_Regular
./run_sobel_tests.sh
```

### Standalone coprocessor test

`tb_pcpi_sobel.v` drives PCPI directly and compares every output byte with a
behavioural golden model. It covers the 8×8 ramp, random images, non-square
images, and degenerate widths/heights (1×1, 1×9, 9×1, 2×7, 7×2).

Result: **11/11 cases pass**.

### Full SoC test

`tb_sobel_soc.v` runs `firmware.hex` on PicoRV32 with PCPI enabled. The firmware

1. clears both output buffers,
2. computes Sobel in software (sliding 3×3 window, 3 loads/pixel),
3. runs `SOBEL_SET` + `SOBEL_RUN`,
4. compares the two buffers byte-for-byte,
5. stores cycle and instruction counts plus a magic value.

The testbench also checks both buffers against an independent golden model.

Measured on Icarus Verilog 11.0, 8×8 image:

| Metric | Software | Hardware |
|---|---|---|
| cycles | 5542 | 175 |
| cycles/pixel | 86.59 | 2.73 |
| instructions | 1387 | 11 |
| speedup | — | **31.67×** |

These are simulation numbers for the zero-wait memory model in `soc_mem.v`.
They are not FPGA post-implementation numbers. The software baseline already
uses a sliding window (3 loads/pixel), not the naive 9-load version, so the
hardware advantage is primarily the elimination of redundant loads and
instruction fetch/decode work.

## 6. Current Limitations

* One memory port: row loading and pixel computation do not overlap, so the
  steady-state cost is about one read plus one write per pixel.
* `MAX_W` is 128 and row shifting copies the whole buffer. A circular row
  buffer would remove that shift cost and the associated registers.
* `SOBEL_RUN` stalls the CPU for the whole image; there is no DMA overlap.
* `soc_mem.v` is a simulation-friendly zero-wait model. A real FPGA memory
  should use block RAM with a registered read and wait states.
* `DATA_INIT_BYTES` in `top.v` is set to 64 for the 8×8 test image.

## 7. Next Steps

* Replace the shift loop with a circular 3-row buffer.
* Add output buffering so two pixels can be computed per cycle while still
  performing one memory transaction per cycle.
* Parameterise the gradient engine for 2/4/8 parallel pixels for the Phase 9
  design-space exploration.
* Synthesise in Vivado and record LUT/FF/BRAM/DSP, Fmax, and power.
* Benchmark larger images (32×32, 64×64) where setup overhead is amortised.
