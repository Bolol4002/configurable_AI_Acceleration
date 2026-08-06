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
├── report_and_ppt/
│   └── review 1/                  # First supervisor review deliverables
│       ├── report_1.docx          # Review 1 report (Word)
│       ├── report_1.md            # Review 1 report (Markdown source)
│       ├── report_1.pdf           # Review 1 report (PDF)
│       └── Review_1.pptx          # Review 1 presentation
└── RiscV_Basys3_Regular/          # Baseline RISC-V bring-up on Basys 3
    ├── top.v                      # Top-level FPGA integration (PicoRV32 + instr mem + LEDs)
    ├── picorv32.v                 # Open-source PicoRV32 RV32I core (YosysHQ)
    ├── firmware.hex               # Instruction-memory test program
    ├── basys3.xdc                 # Basys 3 pin constraints
    └── docs.md                    # Setup/build/operation notes for the board
```

## Current Status

| Phase | Description | Status |
|-------|-------------|--------|
| 0–1   | Problem definition & literature survey | Done — see `report_and_ppt/review 1/report_1.md` |
| 2     | Baseline PicoRV32 brought up on Basys 3 (CPU + instruction memory, debug LEDs) | Done — see `RiscV_Basys3_Regular/` |
| 3+    | Benchmarks, accelerator RTL, ISA extension, verification, DSE, paper | Planned — see `phases.md` |

### What has been completed

- **Literature review** of four papers (RedMulE, SCAIE-V, analog AI hardware review, CIDRE) with per-paper summaries in `paper_summary.md` and a full literature review + research-gap analysis in the Review 1 report.
- **Review 1 deliverables** — complete project report (introduction, problem statement, objectives, scope, literature review, abstract, methodology, expected output, budget, schedule, references) and presentation.
- **Baseline processor on FPGA** — PicoRV32 core integrated in `top.v` on the Basys 3 board, loading `firmware.hex` from block RAM, with debug LEDs showing program-counter activity to verify continuous execution. The PCPI (Pico Co-Processor Interface) ports are wired out in `top.v`, ready for the accelerator to be attached in a later phase.

### Notes / known limitations

- The baseline bring-up (`RiscV_Basys3_Regular/`) is a CPU-integration test; it does not yet implement calculator/7-segment display functionality.
- `paper/` is git-ignored (source PDFs are not tracked); only their summaries live in the repo.
- `top.v` currently loads firmware via an absolute Windows path in `$readmemh` — update this to a relative path before re-synthesizing.

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
