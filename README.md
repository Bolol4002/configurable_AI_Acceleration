# Design and Evaluation of a Configurable AI Acceleration Extension for an Embedded RISC-V Processor on FPGA

A research project to design, integrate, and evaluate a configurable MAC-based AI accelerator with a PicoRV32 RISC-V core on the Digilent Basys 3 FPGA (Xilinx Artix-7 XC7A35T), driven by custom RISC-V instructions and quantified across multiple accelerator configurations and benchmark workloads.

## Project Overview

Embedded scalar processors such as PicoRV32 execute data-parallel AI workloads (matrix multiplication, convolution, dot products, FIR filtering, image filters) as long sequences of load/multiply/add instructions, giving poor execution time, throughput, and energy efficiency. Existing accelerators are typically fixed-configuration and hard to integrate into open-source RISC-V cores.

This project closes that gap by building a **configurable** AI acceleration extension — a parameterizable MAC-array engine (2/4/8 MAC units, INT8/INT16/INT32 operand widths) with a scratchpad and controller — integrated with an embedded RISC-V core via custom instructions (`MATMUL`, `CONV`, `MAC`, `DOT`, `LOAD_TILE`, `STORE_TILE`, `WAIT`), and evaluating the speedup / area / power trade-offs on real FPGA fabric.

## Repository Structure

```text
├── paper/                         # Literature survey papers (git-ignored)
├── paper_summary.md               # One-paragraph summaries of each paper
├── phases.md                      # 12-phase research roadmap with timeline
├── tools/                         # Minimal RISC-V assembler + image generator
├── report_and_ppt/
│   └── review 1/                  # First supervisor review deliverables
│       ├── report_1.docx          # Review 1 report (Word)
│       ├── report_1.md            # Review 1 report (Markdown source)
│       ├── report_1.pdf           # Review 1 report (PDF)
│       └── Review_1.pptx          # Review 1 presentation
└── RiscV_Basys3_Regular/          # PicoRV32 + Sobel PCPI accelerator
    ├── top.v                      # CPU + coprocessor + memory bus arbiter
    ├── picorv32.v                 # Open-source PicoRV32 RV32I core (YosysHQ)
    ├── pcpi_sobel.v               # PCPI Sobel coprocessor RTL
    ├── soc_mem.v                  # Instruction + data memory model
    ├── tb_pcpi_sobel.v            # Standalone coprocessor testbench
    ├── tb_sobel_soc.v             # Full SoC integration testbench
    ├── run_sobel_tests.sh         # Rebuild + run all Sobel tests
    ├── programs/sobel_test.S      # Software-vs-hardware firmware
    ├── firmware.hex               # Assembled firmware
    ├── data.hex                   # 8x8 test image
    ├── isa_sobel.md               # Accurate Sobel ISA/microarchitecture notes
    ├── basys3.xdc                 # Basys 3 pin constraints
    └── docs.md                    # Setup/build/operation notes for the board
```

## Current Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0–1   | Problem definition & literature survey | Done — see `report_and_ppt/review 1/report_1.md` |
| 2     | Baseline PicoRV32 brought up on Basys 3 (CPU + instruction memory, debug LEDs) | Done — see `RiscV_Basys3_Regular/` |
| 3–7   | Sobel benchmark, accelerator RTL, custom ISA, verification | Done — `31.67x` simulated speedup, 11/11 unit cases pass |
| 8+    | FPGA implementation, DSE, final evaluation, paper | Planned — see `phases.md` |

### What has been completed

- **Literature review** of four papers (RedMulE, SCAIE-V, analog AI hardware review, CIDRE) with per-paper summaries in `paper_summary.md` and a full literature review + research-gap analysis in the Review 1 report.
- **Review 1 deliverables** — complete project report (introduction, problem statement, objectives, scope, literature review, abstract, methodology, expected output, budget, schedule, references) and presentation.
- **Baseline processor on FPGA** — PicoRV32 core integrated in `top.v` on the Basys 3 board, loading `firmware.hex` from block RAM, with debug LEDs showing program-counter activity to verify continuous execution.
- **Sobel PCPI accelerator** — `pcpi_sobel.v` with three row buffers, a parallel 3x3 gradient datapath, and four custom instructions (`SOBEL_SET`, `SOBEL_RUN`, `SOBEL_STATUS`, `SOBEL_RESET`). Integrated into `top.v` with PCPI enabled and a memory-bus arbiter. Both a standalone coprocessor test and a full software-vs-hardware SoC test pass under Icarus Verilog. See `RiscV_Basys3_Regular/isa_sobel.md`.

### Notes / known limitations

- The Sobel results are Icarus Verilog simulation numbers with a zero-wait memory model; they are not Vivado post-implementation results.
- The integrated firmware test uses an 8x8 image. Larger and degenerate images are covered by the standalone coprocessor testbench.
- `paper/` is git-ignored (source PDFs are not tracked); only their summaries live in the repo.
- The current `picorv32.v` does not include the M extension; the firmware avoids `mul`/`div`.

## Roadmap

The full 12-phase research roadmap (timeline, per-phase deliverables, recommended tools) is documented in `phases.md`. Summary:

1. Problem definition
2. Literature survey
3. Baseline RISC-V core (PicoRV32) — in progress on Basys 3
4. Benchmark selection (matrix mult, Sobel, Gaussian blur, FIR, dot product, tiny CNN)
5. Accelerator architecture (MAC array, scratchpad, controller)
6. ISA extension design (custom instructions + decoder)
7. RTL development (SystemVerilog)
8. Verification (SystemVerilog/Cocotb, differential hardware-vs-software testing)
9. FPGA implementation (synthesis, timing, power, area)
10. Design-space exploration (2/4/8 MAC × INT8/16/32)
11. Final evaluation (cycles, speedup, energy, area)
12. Paper & thesis

## Tools & Target

- **Board:** Digilent Basys 3 — Xilinx Artix-7 XC7A35T
- **Synthesis/Implementation:** Xilinx Vivado 2025.2
- **RTL:** Verilog (baseline), SystemVerilog (planned accelerator)
- **Verification (planned):** SystemVerilog testbenches / Cocotb, iverilog/ModelSim
- **Firmware:** RISC-V GCC toolchain
- **Baseline core:** PicoRV32 (https://github.com/YosysHQ/picorv32) — license: ISC
