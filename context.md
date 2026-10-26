# Project Context

Session notes for the configurable AI acceleration project. Written 2026-10-04.

> **Update 2026-10-26:** The Sobel phase is now implemented and verified, so the
> "baseline CPU only" state below is historical. See `RiscV_Basys3_Regular/isa_sobel.md`
> and `sobel_instr.md`. Added `pcpi_sobel.v`, `soc_mem.v`, a PCPI arbiter in
> `top.v`, a minimal RV32I assembler, firmware, and two iverilog testbenches.
> Both testbenches pass; the integrated SW-vs-HW test measures 5542 vs 175
> cycles on an 8x8 image (31.67x, zero-wait memory simulation).

## Project

Design and evaluation of a configurable AI acceleration extension for an embedded
RISC-V processor on FPGA (Digilent Basys 3, XC7A35T, Vivado 2025.2). Core is
PicoRV32. 12-phase roadmap lives in `phases.md`.

## Current state: baseline CPU only

Actual files in `RiscV_Basys3_Regular/`:

- `picorv32.v` — unmodified upstream core
- `top.v` — CPU + instruction memory + debug LEDs
- `firmware.hex` — 4 instructions (`93001000 / 93801000 / 93801000 / 6F000000`, a
  bare `lui`/`addi`/`jal x0` loop)
- `basys3.xdc`, `docs.md`

`docs.md` §9 lists unresolved problems: calculator functionality incomplete, no
seven-seg output, CPU/instruction-memory integration still needs debugging,
memory interface timing unverified.

**Phases 0-2 are the only ones with real artifacts. No accelerator exists.**

## sobel_instr.md is a spec, not a record of work

`sobel_instr.md` (untracked) is written entirely in past tense ("What Was Added",
"All 64 pixels MATCH", "Phase 6 ✅ Done") but describes an implementation that does
not exist. Verified against the working tree and full git history:

- All 8 claimed files are missing: `pcpi_sobel.sv`, `sobel_testbench.v`,
  `sobel_sw.c`, `sobel_hw_test.c`, `sobel_hw_test.hex`, `isa_sobel.md`,
  `PHASE3_6_REPORT.md`, `README_SOBEL.md`
- `top.v` was never modified — all 8 PCPI ports dangle at `top.v:61-68`
- No RISC-V toolchain was installed, so the claimed firmware hex could not have
  been compiled

Treat the doc as a forward-looking design proposal. Its arithmetic (§5.2 hand-trace:
Gx=80, Gy=40, mag=120) was checked and is correct.

## The design it specifies

Streaming sliding-window Sobel, not a frame buffer. Two rows in shift registers, a
3×3 window slides across them, one output byte per pixel. Sobel kernels reduce to
adds/subs/shift-by-1 for the ×2 terms, so no multipliers and no DSP slice — hence
§7.2's "0-1 DSP48E1". L1 magnitude (`|Gx|+|Gy|`) avoids a square root.

ISA: 7 instructions under `funct7 = 0x21`, split by `funct3` —
setup (`SOBEL_SET_IMG`, `SOBEL_CFG`), datamovement (`SOBEL_LOAD_ROW`),
control (`SOBEL_RUN_PIXEL`, `SOBEL_RUN_BLOCK`, `SOBEL_GET_STATUS`, `SOBEL_RESET`).

`SOBEL_RUN_PIXEL` returning through `pcpi_rd[7:0]` is the useful one: firmware can
compare against a software golden after every single pixel to localize bugs.

Sobel is framed as a vehicle, not the goal. The thesis contribution is Phase 9:
sweep 2/4/8 MACs x INT8/16/32 and plot area/power/frequency/speedup curves.

## Where the speedup comes from

**Not** faster arithmetic — the ~16 adds/subs are the same either way. The win is
eliminating redundant memory traffic: software needs 9 byte-loads per output pixel
(~9x redundant reads of the image); the line-buffered window reads each byte once.

| | SW (RV32I) | HW (line-buffered) |
|---|---|---|
| loads | ~9 `lb` | ~1 amortized |
| ALU ops | ~16 gradient + ~6 addr | 0 (inside FSM) |
| instructions | ~30 | 1-2 |

`top.v:96` sets `assign mem_ready = mem_valid` (zero-wait memory), so PicoRV32 runs
~1.4 CPI on this mix → SW ~40-50 cycles/pixel; HW ~1-2 → **20-40x speedup**, not
the doc's claimed 4-8x (its own numbers don't reach its own conclusion).

Corollary: **if the accelerator still does 9 reads/pixel, it gains nothing.** The
line buffers are the contribution. This is also why Phase 9 helps — more MACs
amortize the same memory read, so speedup grows with MAC count.

## Blockers found

**1. PCPI is disabled in the current build.** `picorv32.v:75` defaults
`ENABLE_PCPI = 0` and `top.v:41` instantiates `picorv32 cpu (` with no parameter
overrides. The PCPI wires exist but are inert; a coprocessor would never see
`pcpi_valid`. Fix: `picorv32 #(.ENABLE_PCPI(1)) cpu (...)`. Not mentioned in the doc.

**2. No memory path to the coprocessor.** The spec's `SOBEL_LOAD_ROW(src_addr)` and
`RUN_BLOCK(out_base, count_px)` assume the accelerator can dereference pointers.
PCPI carries only `insn/rs1/rs2/rd/wr/wait/ready` — no memory bus. Must either push
pixels one per instruction through `rs1` (simple, slow, undercuts the speedup) or
arbitrate the CPU's `mem_valid/mem_addr/mem_wdata` in `top.v` so the accelerator
can DMA while the CPU stalls on `pcpi_wait`. The second is the real design and needs
a bus-arbitration FSM plus a memory-access FSM, neither of which is in the doc.

**3. Broken asm macros.** `asm volatile(".word %0" :: "i"(INSN_RUN_BLOCK(out, n)))`
needs a compile-time constant, but `out`/`n` are runtime values. Operands must be
moved into registers and encoded with `.insn`.

**4. `$readmemh` has a hardcoded Windows path** at `top.v:81`
(`E:/riscv_new/riscv_cpu_new/...`).

**5. Doc bookkeeping errors:** §5.2 golden covers 36 interior pixels but §5.3 reports
64/64; §2.3(a) describes 3 rows of buffering but §2.2/§7.2 count only 2; §4 writes
results to memory while §3's `RUN_PIXEL` returns via `pcpi_rd`.

## Measurement plan

PicoRV32 has `ENABLE_COUNTERS = 1` by default (`picorv32.v:63`), so `rdcycle` and
`rdinstret` work out of the box — exact cycle and instruction counts come from inside
the same simulation for both versions. No external instrumentation needed.

1. `sudo apt install gcc-riscv64-unknown-elf` (10.2.0 is in apt cache, installs cleanly)
2. `sobel_sw.c` (pure C, `-O2`) and `sobel_hw.c` (same + custom ISA), both storing
   `rdcycle()` and a result checksum to fixed memory addresses
3. Testbench runs `picorv32 #(.ENABLE_PCPI(1))` + `pcpi_sobel.sv`, reads those
   addresses, prints HW==SW match plus cycles SW / cycles HW / cycles-per-output-pixel
4. Sweep image size (8x8, 32x32, 128x128, 256x256), plot cycles/pixel. Only the
   large-image asymptote is a defensible speedup number — small images are dominated
   by setup overhead
5. Vivado separately for LUT/FF/BRAM/DSP, Fmax, power

Toolchain status: `iverilog` 11.0 available. `vvp` available. No RISC-V compiler
installed (fixable per step 1).

## Credibility risk

A reviewer will ask why software can't just do this. Partly it can — with `restrict`
and a hand-sliding-window loop a good SW implementation gets maybe 2x better than the
naive one. Benchmarking against a naive C loop makes the 30x a strawman and gets the
paper rejected.

So: benchmark against the best SW implementation that can be written, report honestly,
and frame the contribution as "reduces memory traffic 9x, which matters when memory is
the bottleneck." A real Basys 3 BRAM design with wait states makes loads far more
expensive than this zero-wait sim, which increases the measured speedup.

## Next steps

Suggested order, cheapest information first:

1. Install the toolchain, build the SW baseline, measure cycles/pixel on plain
   picorv32. This tells us whether there's a real result before writing any coprocessor.
2. Decide the memory architecture (push-via-rs1 vs bus-arbitrated DMA) — this is the
   one genuine design decision outstanding and everything else depends on it.
3. Fix `top.v`: enable PCPI, fix the `$readmemh` path, wire the coprocessor.
4. Only then rewrite `sobel_instr.md` to describe what actually exists.

`sobel_instr.md` is currently untracked. Nothing has been committed this session.