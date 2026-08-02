I actually wouldn't make this just an **8-phase timeline**. I'd make it a **12-phase research roadmap**. This is much closer to how graduate students and architecture researchers execute projects. It also maps cleanly to your professor's review meetings.

---

# Overall Project

**Title (Working)**

> **Design and Evaluation of a Configurable AI Acceleration Extension for an Embedded RISC-V Processor on FPGA**

Duration: **8–12 months**

Expected Deliverables

* Literature Survey
* Problem Statement
* Architecture Design
* RTL
* Verification
* FPGA Prototype
* Benchmark Results
* Research Paper
* Final Thesis

---

# Phase 0 — Problem Definition (Week 1)

## Goal

Understand **why** this project should exist.

Don't touch Verilog yet.

---

## Questions to answer

* What problem am I solving?
* Who faces this problem?
* Why isn't existing hardware enough?
* Why use FPGA?
* Why RISC-V?
* Why embedded AI?

---

## Deliverables

A 2-page proposal containing

* Problem Statement
* Objectives
* Scope
* Expected Contributions

---

# Phase 1 — Literature Survey (Weeks 2–5)

This is arguably the most important phase.

Read approximately **20–30 papers**.

---

## Study Topics

### RISC-V

* ISA
* Custom Instructions
* Opcodes
* Extensions
* Privileged vs User ISA

---

### Processor Architecture

* Pipeline
* ALU
* Decoder
* Register File
* Memory
* Control Unit

---

### AI Accelerators

Study

* Google TPU
* TinyML accelerators
* MAC arrays
* Systolic arrays
* DSP blocks

---

### FPGA Implementation

Understand

* LUTs
* BRAM
* DSP slices
* Timing
* Routing

---

### Existing Papers

Collect information like

| Paper | Accelerator | FPGA | Speedup | Limitation |
| ----- | ----------- | ---- | ------- | ---------- |

---

## Deliverables

Literature Survey Report

Research Gap

Problem Statement

Novelty

---

# Phase 2 — Baseline Processor (Weeks 6–7)

Choose

* PicoRV32
* Ibex
* VexRiscv

(I recommend PicoRV32 for a first research project.)

---

## Learn

Architecture

Pipeline

Decoder

Register File

Memory Interface

---

## Build

Compile

Simulate

Run programs

Measure

* CPI
* Clock Frequency
* Execution Time

---

Deliverables

Working processor

Benchmark results

Architecture understanding

---

# Phase 3 — Benchmark Selection (Week 8)

Before building hardware

Decide

"What exactly will I accelerate?"

---

Possible benchmarks

* Matrix multiplication
* Sobel
* Gaussian Blur
* FIR Filter
* Dot Product
* Tiny CNN

---

Choose around

4–6 benchmarks.

---

Deliverables

Benchmark suite

Software implementation

Baseline timing

---

# Phase 4 — Accelerator Architecture (Weeks 9–12)

This is the architecture phase.

Design

* MAC Unit
* Matrix Engine
* Convolution Engine
* Scratchpad
* Controller

---

Questions

How many MAC units?

Operand width?

INT8?

INT16?

INT32?

Pipeline?

Latency?

Area?

---

Draw diagrams.

---

Deliverables

Architecture Document

RTL block diagram

Timing diagram

Instruction format

---

# Phase 5 — ISA Extension (Weeks 13–15)

Design new instructions.

Example

```
MATMUL

CONV

MAC

DOT

LOAD_TILE

STORE_TILE

WAIT
```

Modify

* Decoder
* Execute stage
* Control Unit

---

Deliverables

Instruction Encoding

ISA Documentation

Decoder Design

---

# Phase 6 — RTL Development (Weeks 16–22)

Implement

Accelerator

Controller

Decoder

Pipeline modifications

Memory Interface

Register Interface

---

Languages

SystemVerilog

---

Deliverables

RTL

Waveforms

Simulation

---

# Phase 7 — Verification (Weeks 23–26)

Probably the most underestimated phase.

Develop

SystemVerilog Testbenches

or

Cocotb

---

Verify

Correctness

Corner Cases

Instruction execution

Pipeline hazards

Random testing

---

Compare

Hardware

vs

Software

---

Deliverables

Coverage Report

Test Report

Regression Suite

---

# Phase 8 — FPGA Implementation (Weeks 27–30)

Synthesize

Implement

Generate

Timing

Power

Area

Bitstream

---

Run

On FPGA

Measure

Frequency

Latency

---

Deliverables

FPGA Demo

Timing Report

Power Report

Area Report

---

# Phase 9 — Design Space Exploration (Weeks 31–34)

This is where the paper begins.

Evaluate

Configuration A

```
2 MAC
```

Configuration B

```
4 MAC
```

Configuration C

```
8 MAC
```

Compare

Area

Power

Performance

Frequency

---

Create graphs.

---

Deliverables

Trade-off Analysis

Performance Graphs

---

# Phase 10 — Final Evaluation (Weeks 35–37)

Run

All benchmarks.

Measure

Execution Time

Cycles

Speedup

Energy

Power

Area

---

Compare

Baseline CPU

Accelerated CPU

---

Create

Tables

Graphs

Discussion

---

Deliverables

Complete Results

Performance Analysis

---

# Phase 11 — Paper Writing (Weeks 38–42)

Write

Abstract

Introduction

Related Work

Methodology

Architecture

Implementation

Results

Discussion

Conclusion

Future Work

---

Prepare

Presentation

Poster

Demo

---

Deliverables

Research Paper

Presentation

Thesis

---

# Entire Timeline

```text
Phase 0
Problem Definition
        │
        ▼
Phase 1
Literature Survey
        │
        ▼
Phase 2
Baseline RISC-V Core
        │
        ▼
Phase 3
Benchmark Selection
        │
        ▼
Phase 4
Accelerator Architecture
        │
        ▼
Phase 5
ISA Extension Design
        │
        ▼
Phase 6
RTL Development
        │
        ▼
Phase 7
Verification
        │
        ▼
Phase 8
FPGA Implementation
        │
        ▼
Phase 9
Design Space Exploration
        │
        ▼
Phase 10
Performance Evaluation
        │
        ▼
Phase 11
Paper & Thesis
```

---

# Skills You'll Gain

By the end of this roadmap, you will have worked with:

* **Computer Architecture:** RISC-V ISA, pipelines, datapaths, control units, custom instruction design.
* **Digital Design:** SystemVerilog RTL, FSMs, datapath integration, FPGA implementation.
* **Verification:** Testbench development, Cocotb/SystemVerilog, regression testing, functional validation.
* **FPGA Design:** Synthesis, timing closure, resource utilization, power estimation.
* **Embedded Systems:** Benchmarking, performance analysis, hardware/software co-design.
* **Research:** Literature surveys, identifying research gaps, experimental methodology, quantitative evaluation, technical writing.

---

## One important recommendation

Since your long-term goal is **ASIC Design Verification and computer architecture**, I would also maintain a **parallel personal project**: continue developing your own RV32I CPU from scratch.

Treat the projects differently:

* **Personal CPU:** Learn every architectural component by implementing it yourself.
* **Research Project:** Reuse a mature open-source core and focus on the accelerator, integration, verification, and quantitative evaluation.

That combination gives you both deep understanding and a research-grade project without forcing one project to satisfy both objectives.

