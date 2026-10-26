# Sobel Edge Detection with a Custom RISC-V Instruction Extension

**Status: implemented and verified in simulation.** This document describes the
code that now exists under `RiscV_Basys3_Regular/`. Detailed ISA and
microarchitecture notes are in `RiscV_Basys3_Regular/isa_sobel.md`.

## 1. Benchmark Choice

Grayscale 3×3 Sobel:

```
Gx = [-1  0 +1]      Gy = [-1 -2 -1]
     [-2  0 +2]           [ 0  0  0]
     [-1  0 +1]           [+1 +2 +1]

mag = clamp(|Gx| + |Gy|, 0, 255)
```

Sobel is a good vehicle for this project because it is data-parallel,
memory-bound, deterministic, and easy to check bit-exactly against software.

## 2. Architecture

`RiscV_Basys3_Regular/pcpi_sobel.v` is a PCPI coprocessor with:

* **Three line buffers** (`line0`, `line1`, `line2`), 128 bytes each.
* A **parallel 3×3 datapath**: all nine window bytes feed both gradient sums in
  the same combinational path. `|Gx|`, `|Gy|`, their sum, and the clamp are also
  evaluated in parallel. One interior pixel is produced per clock.
* An FSM that streams the image row by row:
  `ROW0 → LOAD×3 → COMPUTE → SHIFT+LOAD → COMPUTE → … → ROWLAST → DONE`.
* A memory master using the PicoRV32 convention: word-aligned address plus byte
  strobe. The coprocessor reads each source pixel **once** and writes each
  output pixel **once**.

`RiscV_Basys3_Regular/top.v` integrates the pieces:

* PicoRV32 is instantiated with `ENABLE_PCPI(1)`.
* A two-owner bus arbiter gives the CPU the memory bus normally and gives it to
  the coprocessor while the CPU is stalled on `pcpi_wait`.
* `soc_mem.v` provides 1 KiB of instruction memory and 8 KiB of byte-addressable
  data memory.

The speedup comes from removing redundant memory traffic and instruction
execution, not from a faster adder. A sliding-window software implementation
still needs three byte loads per interior pixel; the line-buffered hardware
needs one amortised load.

## 3. Custom ISA

Encoding: `opcode = 7'b0001011` (custom-0), `funct7 = 7'b0100001`, R-type
operand fields.

| Mnemonic | funct3 | rs1 | rs2 | rd | Semantics |
|---|---|---|---|---|---|
| `SOBEL_SET` | 0 | image address | `{H[31:16], W[15:0]}` | — | Configure image |
| `SOBEL_RUN` | 1 | output address | — | bytes written | Run full image |
| `SOBEL_STATUS` | 2 | — | — | status | Read status |
| `SOBEL_RESET` | 3 | — | — | — | Clear configuration |

Borders are zero. `SOBEL_RUN` returns `W*H`. Widths above `MAX_W = 128` set the
error bit in `SOBEL_STATUS`.

## 4. Implementation Files

| File | Purpose |
|---|---|
| `RiscV_Basys3_Regular/pcpi_sobel.v` | Coprocessor RTL |
| `RiscV_Basys3_Regular/soc_mem.v` | Unified instruction/data memory |
| `RiscV_Basys3_Regular/top.v` | CPU + coprocessor + arbiter |
| `RiscV_Basys3_Regular/tb_pcpi_sobel.v` | Standalone coprocessor test |
| `RiscV_Basys3_Regular/tb_sobel_soc.v` | Full SoC test |
| `RiscV_Basys3_Regular/programs/sobel_test.S` | SW-vs-HW firmware |
| `RiscV_Basys3_Regular/firmware.hex` | Assembled firmware |
| `RiscV_Basys3_Regular/data.hex` | 8×8 ramp image |
| `RiscV_Basys3_Regular/run_sobel_tests.sh` | One-command regression |
| `tools/rv32asm.py` | Minimal RV32I + Sobel-PCPI assembler |
| `tools/gen_sobel_data.py` | Test-image generator |

There is no RISC-V GCC toolchain on this machine, so the firmware is assembled
by a small Python assembler. It supports the RV32I subset used by the test plus
the four Sobel instructions.

## 5. Verification

Run:

```bash
cd RiscV_Basys3_Regular
./run_sobel_tests.sh
```

### 5.1 Standalone coprocessor test

The testbench drives the PCPI slave directly with a zero-wait memory model and
compares every output byte against a behavioural golden model. It covers:

* 8×8 deterministic ramp,
* random 16×16 and 32×20 images,
* non-square 5×3 and 3×5 images,
* degenerate 1×1, 1×9, 9×1, 2×7 and 7×2 images.

Result: **11/11 cases pass**, including exact pixel counts.

### 5.2 Full SoC test

The firmware computes Sobel in software, runs it through `SOBEL_SET` +
`SOBEL_RUN`, compares the two output buffers, and records cycle/instruction
counts. The testbench independently checks both buffers against the golden
model.

Measured with Icarus Verilog 11.0 on an 8×8 image:

| Metric | Software | Hardware |
|---|---|---|
| cycles | 5542 | 175 |
| cycles/pixel | 86.59 | 2.73 |
| instructions | 1387 | 11 |
| speedup | — | **31.67×** |

The software baseline uses a sliding 3×3 window (3 loads/pixel), not a naive
9-load loop. These are simulated zero-wait-memory numbers, not FPGA
post-implementation results.

## 6. Honest Limitations

* Single memory port: row loading and computation do not overlap.
* Row shifting copies the full 128-byte buffers; a circular row buffer would be
  cheaper.
* `SOBEL_RUN` stalls the CPU for the whole image; there is no DMA/compute
  overlap.
* `soc_mem.v` is a zero-wait simulation memory. A real Basys 3 design should use
  BRAM with a registered read and wait states.
* Only the 8×8 integrated test is compiled into `firmware.hex`; larger images
  are exercised in the standalone coprocessor testbench.

## 7. Next Phase

The next steps are the Phase 9 design-space exploration:

1. Replace the shift loop with a circular three-row buffer.
2. Parameterise 2/4/8 parallel gradient lanes.
3. Support INT8/INT16/INT32 operand configurations.
4. Sweep area, Fmax, power, and cycles/pixel in Vivado.
5. Benchmark larger images where setup overhead is amortised.
