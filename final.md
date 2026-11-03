# Design and Evaluation of a Custom RISC-V Instruction Extension for Sobel Edge Detection on FPGA

> **Drafting note:** This file contains the main report chapters, following the supplied report format. Add the project-specific introduction and IEEE bibliography, then check that the bibliography entries match the citation numbers used here. Replace every `[TO BE ADDED]` item with measured or approved information before submission. The current implementation is a Sobel-specific custom-instruction coprocessor; it is not yet the planned configurable 2/4/8-MAC AI accelerator.

## CHAPTER 2 — METHODOLOGY

This chapter describes the implemented system, the software-versus-hardware experiment, and the methods used to verify functionality and compare performance. The work uses an incremental hardware/software co-design process: first establish a PicoRV32 baseline, then integrate a custom coprocessor, verify its output against a software reference, and finally evaluate the design on the target FPGA when implementation results are available. Custom instruction interfaces are a common way to couple application-specific execution units to RISC-V processors [2], [6].

### 2.1 Project Approach

The project proceeds through the following stages:

1. **Baseline processor integration:** PicoRV32 is connected to instruction and data memory and configured to expose its Pico Co-Processor Interface (PCPI).
2. **Benchmark definition:** A grayscale 3 × 3 Sobel edge detector is used as a deterministic workload with a byte-exact software reference.
3. **Software baseline:** The CPU computes the Sobel output using RV32I instructions and a sliding 3 × 3 window.
4. **Custom instruction implementation:** A PCPI coprocessor accepts Sobel configuration and execution commands, loads the image through the memory bus, computes output pixels, and writes the result.
5. **Functional verification:** Standalone and full-SoC testbenches compare results against a behavioral golden model.
6. **Performance and FPGA evaluation:** Simulation cycle counts are reported separately from post-implementation timing, area, and power. FPGA results are to be added only after the software-only and accelerator-enabled designs have both been synthesized and implemented under matching conditions.

The project repository includes the custom coprocessor and simulation tests. The documented FPGA demonstration applies to the baseline CPU integration; the current evidence does not establish that the Sobel-enabled design has been tested on the Basys 3 board.

### 2.2 Hardware and Software Requirements

Table 2.1 summarizes the implementation platform and tools. The FPGA family and board are identified in the project documentation; Vivado 2025.2 is the version recorded there. Confirm the exact tool version and device selected in the Vivado project before final submission.

**Table 2.1: Project implementation platform and tools**

| Item | Selection |
|---|---|
| FPGA development board | Digilent Basys 3 |
| FPGA device | Xilinx Artix-7 XC7A35T |
| Processor | PicoRV32, RV32I configuration |
| Accelerator interface | Pico Co-Processor Interface (PCPI) |
| RTL | Verilog |
| Simulation | Icarus Verilog 11.0 |
| FPGA synthesis and implementation | Xilinx Vivado; project documentation records version 2025.2 |
| Board constraints | `RiscV_Basys3_Regular/basys3.xdc` |
| Test firmware and image | `firmware.hex` and `data.hex` |

### 2.3 Sobel Benchmark

The benchmark operates on an 8-bit grayscale image. For each interior pixel, the horizontal and vertical Sobel gradients are computed from the surrounding 3 × 3 neighborhood:

```text
Gx = (p02 + 2p12 + p22) - (p00 + 2p10 + p20)
Gy = (p20 + 2p21 + p22) - (p00 + 2p01 + p02)
output = min(|Gx| + |Gy|, 255)
```

The outermost image border is set to zero. This definition is used by both the software routine and the hardware reference model, so that output comparisons test equivalent behavior.

### 2.4 Software and Hardware Comparison

The software baseline uses a sliding window: it initially loads the neighborhood and then loads only the newly entering column as it moves across a row. This is a more efficient baseline than recomputing each neighborhood with nine independent pixel loads. The hardware implementation keeps three image rows in line buffers and evaluates the gradient datapath in parallel. Its intended advantage is reducing repeated memory reads and instruction execution, rather than relying on a higher processor clock frequency.

The full-SoC firmware runs both methods on the same 8 × 8 image, records processor cycle and retired-instruction counts for each computation, and checks that the two output buffers match. The testbench independently checks both outputs against a golden Sobel model.

For the reported simulation experiment:

```text
simulation speedup = software cycle count / hardware cycle count
cycles per pixel   = measured cycle count / number of image pixels
```

FPGA execution time must be calculated using the measured cycle count and the achieved clock frequency, not by treating simulation cycles as elapsed FPGA time. The FPGA comparison must use the same device, timing constraints, input dimensions, memory implementation, and Vivado implementation settings for both designs.

### 2.5 Verification Method

Verification is performed at two levels:

- **Standalone coprocessor tests:** The PCPI unit is driven directly with a zero-wait memory model. Each output pixel and the returned pixel count are checked against the golden model.
- **Full-SoC integration test:** The PicoRV32 executes the firmware, runs the software and custom-instruction paths, compares their outputs, and records cycle and instruction counts. The testbench also checks the results independently against the golden model.

The simulation regression is run from `RiscV_Basys3_Regular/` using:

```bash
./run_sobel_tests.sh
```

### 2.6 FPGA Evaluation Method

For a fair FPGA comparison, prepare two synthesis configurations:

1. **Software-only baseline:** PicoRV32, memory, and the firmware-running application, without the Sobel coprocessor.
2. **Custom-instruction design:** PicoRV32, the Sobel coprocessor, arbiter, and memory.

The current `top.v` instantiates the coprocessor, so the software run inside that top is not by itself a software-only area baseline. The baseline must omit the accelerator in hardware while preserving the processor, memory resources, clock constraints, and relevant I/O.

For each design, run synthesis and implementation in Vivado. Record resource utilization, post-implementation timing, and power estimates. Use representative switching activity (for example, a SAIF file generated from a representative simulation) for activity-aware power estimation when practical. Vivado power results are estimates whose quality depends on the activity assumptions and implementation data; identify the estimation method in the final report. FPGA implementation and power-analysis practices depend on the target device and design constraints [7], [8].

## CHAPTER 3 — DESIGN AND IMPLEMENTATION

This chapter describes the implemented processor, custom instruction interface, coprocessor datapath, memory system, and test firmware. The architecture is a small PCPI-attached Sobel engine rather than a general matrix or MAC-array accelerator.

### 3.1 System Architecture

PicoRV32 executes ordinary firmware and presents custom instructions on its PCPI interface. The Sobel coprocessor decodes the custom opcode and function fields. When a long-running Sobel operation is in progress, the CPU waits while the coprocessor accesses memory through the bus arbiter. The shared memory contains the firmware and image data.

**[Insert Figure 3.1 here: Original block diagram of the implemented system.]**

*Figure 3.1: Implemented PicoRV32 and Sobel coprocessor architecture. Draw the PicoRV32 core, PCPI control/data signals, Sobel coprocessor, CPU/Sobel bus arbiter, instruction/data memory, clock, and reset. Show the memory bus separately from PCPI. The figure should describe the code in `top.v`, not a proposed MAC-array design.*

Figure 3.1 should make clear that the custom instruction interface controls the accelerator, while image data moves through the memory bus. The two-owner arbiter normally grants the bus to the CPU and transfers ownership to the coprocessor while the CPU is stalled waiting for the PCPI operation.

### 3.2 Custom Instruction Set

The coprocessor uses the RISC-V custom-0 opcode and a function field to distinguish its four supported operations. Table 3.1 summarizes the instruction behavior implemented in the RTL.

**Table 3.1: Implemented Sobel custom instructions**

| Instruction | `funct3` | Operands and result | Function |
|---|---:|---|---|
| `SOBEL_SET` | 0 | `rs1` = image byte address; `rs2` = `{height[31:16], width[15:0]}` | Configure image source and dimensions |
| `SOBEL_RUN` | 1 | `rs1` = output byte address; `rd` = bytes written | Process the configured image |
| `SOBEL_STATUS` | 2 | `rd` = status | Return error, done, and busy flags |
| `SOBEL_RESET` | 3 | No data result | Clear accelerator configuration/state |

The instruction protocol is attached through PicoRV32's PCPI signals. The processor remains stalled while a run is in progress and resumes when the coprocessor reports completion.

### 3.3 Coprocessor Datapath and Control

The coprocessor contains three row buffers, each sized for `MAX_W = 128` bytes. A finite-state machine loads the first rows, computes output pixels, shifts row contents for subsequent rows, and finishes by writing the final border row. The three-row window feeds both gradient calculations in parallel; the absolute values, magnitude sum, and saturation to 255 are then computed combinationally.

The current implementation produces one interior pixel per compute step. It does not contain a configurable 2/4/8-lane MAC array, INT8/INT16/INT32 selectable arithmetic modes, or a scratchpad controller for general matrix operations. These remain possible future extensions rather than results of this implementation.

### 3.4 Memory System and Firmware

The integrated simulation memory uses a 1 KiB instruction memory and an 8 KiB byte-addressable data memory. The data memory is initialized from `data.hex`, and the instruction memory is initialized from `firmware.hex`. The simulation model provides zero-wait access; therefore, its cycle measurements do not represent a registered BRAM implementation or the timing of a physical FPGA memory system.

The test firmware first computes Sobel in software, then invokes `SOBEL_SET` and `SOBEL_RUN`, and finally compares the two output buffers. It records software and hardware cycle counts, retired-instruction counts, pixel count, pass status, and mismatch count in the data memory.

### 3.5 FPGA Prototype and Constraints

The Basys 3 constraints file assigns the system clock, six switch inputs, and four LEDs. The clock constraint is 10 ns (100 MHz). The source top module exposes `clk`, `sw`, and `led`; the current RTL LED behavior mirrors two switch bits and toggles a counter-derived LED.

**[Insert Figure 3.2 here: Photograph of the actual Basys 3 board during the CPU FPGA demonstration.]**

*Figure 3.2: Basys 3 FPGA setup used to demonstrate the PicoRV32 baseline. Label this as a baseline CPU demonstration unless the Sobel-enabled bitstream has also been loaded and verified on the board. Include a short caption identifying what the LEDs demonstrate; do not imply that the image proves Sobel hardware execution unless it was captured during that test.*

Figure 3.2 is intended as hardware evidence, not as a substitute for simulation or implementation reports. If the Sobel-enabled design has not yet been programmed and validated on the board, state that explicitly in the discussion and reserve a separate photograph for that future test.

## CHAPTER 4 — RESULTS AND ANALYSIS

This chapter distinguishes functional and performance results obtained in simulation from FPGA implementation results. The cycle counts below are from an 8 × 8 simulation using the zero-wait memory model. They are not Vivado timing, power, or post-implementation results.

### 4.1 Functional Verification Results

The standalone regression covers deterministic and randomized image data, non-square images, and small or degenerate dimensions. The repository documentation reports that all 11 test cases pass, with output pixels and returned pixel counts checked against the behavioral model.

The full-SoC test runs software and hardware Sobel calculations on the same 8 × 8 image. It checks the firmware pass flag, zero mismatch count, returned pixel count, completion marker, and each output byte against an independent golden result. The test reports success only when software, hardware, and golden outputs agree.

### 4.2 Simulation Performance

Table 4.1 reports the measured 8 × 8 simulation performance. The software baseline uses a sliding window, and the hardware result uses the PCPI coprocessor. These values come from the full-SoC simulation and should be identified as simulated zero-wait-memory results wherever they are quoted.

**Table 4.1: Software and custom-instruction Sobel results in simulation**

| Metric | Software baseline | Custom-instruction hardware |
|---|---:|---:|
| Image size | 8 × 8 pixels | 8 × 8 pixels |
| Total cycles | 5,542 | 175 |
| Cycles per pixel | 86.59 | 2.73 |
| Retired instructions | 1,387 | 11 |
| Simulation speedup | — | 31.67× |
| Output comparison | Pass | Pass |

As shown in Table 4.1, the simulated custom-instruction path takes fewer processor cycles for this workload. This result is consistent with the coprocessor reducing repeated software instruction execution and memory traffic. It is not evidence that the FPGA implementation achieves a 31.67× clock-frequency or wall-clock improvement; FPGA time depends on achieved timing and the implemented memory system.

### 4.3 FPGA Area, Timing, and Power Results

No post-implementation Vivado reports for the software-only and Sobel-enabled designs are present in the current project evidence. Table 4.2 is therefore a results template, not a set of measured values. Populate it only after both configurations have been implemented with the same target part and constraints.

**Table 4.2: FPGA resource, timing, and power comparison — populate from Vivado**

| Metric | Software-only baseline | Sobel custom-instruction design | Unit / source |
|---|---:|---:|---|
| LUTs | [TO BE ADDED] | [TO BE ADDED] | Count; utilization report |
| Flip-flops | [TO BE ADDED] | [TO BE ADDED] | Count; utilization report |
| BRAM tiles | [TO BE ADDED] | [TO BE ADDED] | Count; utilization report |
| DSP slices | [TO BE ADDED] | [TO BE ADDED] | Count; utilization report |
| Worst negative slack (WNS) | [TO BE ADDED] | [TO BE ADDED] | ns; implemented timing report |
| Achieved maximum frequency | [TO BE ADDED] | [TO BE ADDED] | MHz; explain derivation/report |
| Static power | [TO BE ADDED] | [TO BE ADDED] | W; power report |
| Dynamic power | [TO BE ADDED] | [TO BE ADDED] | W; power report and activity assumptions |
| Total on-chip power | [TO BE ADDED] | [TO BE ADDED] | W; power report |
| Workload cycles | [TO BE ADDED] | [TO BE ADDED] | Cycles; equivalent workload |
| Workload execution time | [TO BE ADDED] | [TO BE ADDED] | s or ms; measured/calculated consistently |

The expected area overhead can be calculated from the resource counts as `(accelerated design − baseline) / baseline × 100%`. Report timing against the same 10 ns clock constraint and include whether timing was met. Describe power as an estimate and include the activity source and workload; do not conclude that power necessarily increases merely because logic area increases. The accelerator may draw more instantaneous dynamic power while active, yet complete the task sooner, so energy per image should be compared when suitable power and execution-time data are available.

### 4.4 Discussion

The simulation demonstrates functional agreement and a large cycle-count reduction for the tested image under the modeled memory conditions. The primary architectural mechanism is to replace repeated scalar operations and loads with a dedicated datapath and line-buffered image access. The reported software implementation is already optimized to reuse a sliding window, so the comparison is more meaningful than one against an implementation that reloads all nine pixels for every output.

The current result has important limits. The integrated benchmark is 8 × 8, the simulation memory has zero wait states, and no FPGA area, timing, or power measurements are included in the repository evidence. The custom accelerator also introduces logic and storage that are absent from a software-only implementation. Actual resource overhead and power behavior must be established using matched Vivado runs; they should not be inferred from cycle count alone.

For the final report, compare both FPGA configurations under the same board/device, clock, I/O constraints, memory design, firmware workload, image dimensions, and implementation settings. Include the timing slack and power-analysis assumptions alongside any speedup claim. If the accelerator is not yet tested on the board, describe the board evidence as baseline CPU operation only.

## CHAPTER 5 — CONCLUSION AND FUTURE WORK

### 5.1 Conclusion

This project implemented and simulated a Sobel edge-detection coprocessor connected to a PicoRV32 processor through custom PCPI instructions. The design includes a three-row buffer, a parallel 3 × 3 Sobel datapath, a controller, and a memory-bus arbitration path. Standalone verification covers 11 documented test cases, and the full-SoC simulation compares software and hardware results against an independent golden model.

For the 8 × 8 zero-wait-memory simulation, the software routine took 5,542 cycles and the coprocessor path took 175 cycles, a simulated cycle-count speedup of 31.67×. These figures characterize the simulation only. The project does not yet have documented post-implementation FPGA area, timing, or power results for a matched software-only versus accelerator-enabled comparison, and the simulated speedup must not be presented as an FPGA measurement.

### 5.2 Future Work

The following work is required to complete the FPGA evaluation and extend the design:

1. Build a software-only hardware configuration without the Sobel coprocessor, preserving comparable processor, memory, clock, and I/O conditions.
2. Implement the accelerator-enabled design on the Basys 3 target and verify its operation on the board. Record evidence specific to the Sobel test if claiming on-board accelerator validation.
3. Replace the zero-wait simulation memory with an FPGA-appropriate memory implementation and account for its latency in both configurations.
4. Collect Vivado utilization, timing, and power reports for both configurations using identical constraints and documented activity assumptions.
5. Benchmark larger images and report execution time and, where power data supports it, energy per image.
6. Replace full-row shifting with circular line-buffer indexing to reduce unnecessary data movement.
7. Extend the Sobel-specific prototype toward the broader project goal: a configurable MAC-based AI accelerator with selectable parallelism and operand widths. Treat these features as future work until they are implemented and verified.

---

### Citation-number alignment

The in-text citation numbers in this draft follow the numbering in the earlier project report's reference list: [1] RedMulE; [2] SCAIE-V; [6] the RISC-V instruction-set manual; [7] Xilinx 7-series FPGA data sheet; and [8] the Digilent Basys 3 reference manual. When preparing the final IEEE bibliography, verify and renumber all citations consistently if the final reference list is different.
