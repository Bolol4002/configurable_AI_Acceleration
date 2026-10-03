# Design and Evaluation of a Configurable AI Acceleration Extension for an Embedded RISC-V Processor on FPGA

---

## 5.0 Introduction

### 5.1 General Introduction

The rapid proliferation of the Internet of Things (IoT) and embedded computing has fundamentally changed the way data is processed. Modern edge devices — sensors, wearables, drones, industrial controllers, and battery-powered medical monitors — are increasingly required to run artificial intelligence (AI) and machine learning (ML) workloads locally rather than streaming data to the cloud. This shift toward *edge AI* and *TinyML* is motivated by compelling advantages: reduced network congestion, lower latency, better data privacy, and substantially lower energy consumption than remote data-center processing [1], [2], [3], [4]. However, moving intelligent computation to the edge places severe constraints on the underlying hardware. These devices must deliver meaningful throughput and accuracy while operating within power budgets of a few milliwatts to a few hundred milliwatts, and they must fit within tiny silicon or logic budgets.

Conventional embedded processors are poorly matched to this challenge. A typical microcontroller or soft processor is a single-issue, in-order machine that executes instructions sequentially. AI kernels such as matrix multiplication, convolution, and dot products are *data-parallel* by nature — they consist of millions of multiply–accumulate (MAC) operations that can, in principle, be executed concurrently. On a scalar CPU, each of these operations becomes a long sequence of load, multiply, and add instructions. The result is that such workloads suffer from low instruction throughput, severe memory-bandwidth bottlenecks, and very poor energy efficiency [5], [6], [7]. This is a fundamental architectural mismatch rather than a mere implementation deficiency.

Several classes of solutions have emerged to close this gap. At one end of the spectrum are dedicated hardware accelerators designed for neural-network inference and training kernels [1], [4], [5]. On the other end are general-purpose processors that trade efficiency for programmability. Between these extremes lies the approach adopted in this project: extending a general-purpose embedded processor with a *custom, application-specific accelerator* — an approach known in the literature as an Application-Specific Instruction Set Processor (ASIP) [4], [8].

The RISC-V instruction set architecture (ISA) has become the preferred foundation for this kind of design. RISC-V is an open, freely available, modular ISA that provides a stable base (RV32I) and explicitly reserves opcode space for custom and vendor extensions. Because the ISA is open, and because a large ecosystem of open-source cores exists — PicoRV32, Ibex, VexRiscv, and others — researchers can legally and practically modify the instruction set, the decoder, and the datapath to integrate bespoke hardware units [6], [8], [9]. PicoRV32 is an especially attractive baseline for a first research project because of its tiny footprint, its simple and well-documented interface, and the fact that it already provides a PCPI (Pico Co-Processor Interface) through which custom instructions can be offloaded to external hardware [9], [10].

Field-Programmable Gate Arrays (FPGAs) complete the picture. An FPGA provides a reconfigurable fabric built from lookup tables (LUTs), block RAM (BRAM), and embedded DSP slices that can implement multiply–accumulate operations at high speed. FPGAs allow a designer to prototype an entire processor-plus-accelerator system, synthesize it, and measure real timing, area, and power results in a matter of hours [7], [10], [11]. This makes the FPGA the ideal platform for architectural research: multiple accelerator configurations can be explored and compared without committing to fabrication. The Xilinx Artix-7 XC7A35T on the Digilent Basys 3 board, used in this project, is a representative low-cost embedded FPGA with enough resources for a soft RISC-V core and a moderate-size MAC engine [8], [12].

This project therefore sits at the intersection of three enabling technologies: an open embedded ISA (RISC-V), a reconfigurable prototyping platform (FPGA), and data-parallel AI kernels. The central idea is to design a *configurable* AI acceleration extension — a parametrizable MAC-array engine integrated with an embedded RISC-V processor through custom instructions — and to evaluate it quantitatively across several configurations and benchmark workloads [1], [4], [6], [8]. By making the accelerator configurable (number of MAC units, operand widths, and integration approach), the project investigates the area–performance–energy trade-off space that real designers face when building edge-AI systems [5], [7], [11]. The remainder of this report formalizes the problem, states the objectives, defines the scope, presents a literature review, and describes the planned methodology, expected outcomes, budget, and schedule.

---

### 5.2 Problem Statement

(i) Embedded scalar processors such as the PicoRV32 RV32I core execute data-parallel AI workloads — matrix multiplication, convolution, FIR filtering, and dot products — as long sequences of individual load, multiply, and add instructions. Because these cores issue only a single instruction per cycle and expose limited memory bandwidth, running AI kernels in software on such cores results in poor execution time, low throughput, and high energy consumption relative to the parallelism inherent in the algorithms. There is a need to accelerate these kernels without abandoning the programmability and low cost of the embedded processor.

(ii) Existing hardware accelerators are typically fixed-configuration designs that are either tightly specialized to one network topology or deployed as rigid co-processors with limited programmability and little ability to be reconfigured. Off-the-shelf AI IP often cannot be adapted to a given application's accuracy, power, and resource budget, and its integration into an open-source RISC-V core is frequently hampered by a lack of standardized interfaces for custom instruction extension. There is a need for a *configurable* accelerator whose dimensions (number of MAC units, operand width) can be tuned, and which can be integrated into an embedded RISC-V processor cleanly and evaluated on an FPGA.

---

### 5.3 Objectives of the Study

The general objective of this study is **to design and evaluate a configurable AI acceleration extension for an embedded RISC-V processor on an FPGA, quantifying the performance, area, and energy trade-offs across multiple accelerator configurations and representative AI benchmark workloads.**

In line with the general objective, the following are the specific objectives based on the research questions:

(i) To design and implement a configurable multiply–accumulate (MAC) based AI accelerator extension and integrate it with an embedded PicoRV32 RISC-V core on a Xilinx Artix-7 FPGA through custom RISC-V instructions, so that data-parallel AI kernels (matrix multiplication, convolution, dot product, FIR, image filters) are offloaded from software into hardware (solution to problem statement 1).

(ii) To synthesize and evaluate the integrated system across multiple accelerator configurations (2, 4, and 8 MAC units) and benchmark workloads on the FPGA, comparing execution time, speedup, clock frequency, area utilization, and power consumption against the software baseline, in order to establish the configuration trade-off space (solution to problem statement 2).

---

### 5.4 Scope of the Project

This project covers the design, implementation, verification, and FPGA-based evaluation of a configurable AI acceleration extension for an embedded RISC-V processor. The hardware scope includes a baseline RV32I soft-core processor (PicoRV32) implemented on the Digilent Basys 3 board (Xilinx Artix-7 XC7A35T), together with a parameterizable accelerator engine built around a configurable array of MAC units, a scratchpad memory, and a controller. The accelerator is attached to the core through custom RISC-V instructions of the form MATMUL, CONV, MAC, DOT, LOAD_TILE, STORE_TILE, and WAIT, which require modification of the decoder, execute stage, and control logic. A full RTL design, written in SystemVerilog, and a verification environment using SystemVerilog testbenches and/or Cocotb are within scope, including randomized and software-vs-hardware differential testing. On the FPGA side, the project covers synthesis, implementation, timing closure, resource-utilization and power reporting, and on-board demonstration. The evaluation scope is a benchmark suite of 4–6 kernels — matrix multiplication, Sobel edge detection, Gaussian blur, FIR filter, dot product, and a tiny CNN — measured in terms of execution cycles, speedup over the software baseline, maximum clock frequency, LUT/BRAM/DSP utilization, and estimated power. A design-space exploration across 2/4/8-MAC configurations and operand widths (INT8/INT16/INT32) is included, since this exploration constitutes the main research contribution.

The following are explicitly out of scope: full system-on-chip integration with peripherals and operating systems; multi-core clusters; ASIC fabrication or tape-out; on-chip training in floating point; analog or in-memory-computing accelerators; and porting of the accelerator to other FPGA families or processor cores. The project is hardware-oriented and is bounded by the resources of the Basys 3 board; all results are reported at the FPGA-prototype level.

---

### 5.5 Literature Review

A literature survey is a systematic search of published works to locate relevant information on a specific topic, and it is an essential step in research because it (a) identifies what has already been written, (b) reveals interpretable trends in a research area, (c) aggregates empirical findings to support evidence-based practice, (d) helps generate new frameworks, and (e) uncovers topics that require further investigation. This section reviews the literature that motivates and frames the present work using the core papers cited in this project and supporting references from the broader embedded-AI, RISC-V, FPGA, and verification literature [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12].

**The case for edge-AI hardware.** The demand for energy-efficient AI hardware is well established [1], [3], [5]. This review highlights the architectural limitations of conventional digital processors for edge-based AI workloads and motivates the need for dedicated hardware structures such as multiply–accumulate arrays and systolic organizations. The present project follows this direction by implementing a configurable digital accelerator on FPGA instead of relying on a purely software-only approach [7], [11].

**Tightly coupled accelerators for RISC-V.** The base paper for the integration approach is RedMulE [1], a compact FP16 matrix-multiplication engine conceived for tight integration within a cluster of tiny RISC-V cores. RedMulE is a *parametric* accelerator whose datapath width and number of FMAs can be configured; it demonstrates that a tightly coupled accelerator can achieve large gains in energy efficiency and throughput while remaining compact. These observations directly motivate the configurable MAC-array design proposed in this report [1], [4], [5].

**Interfaces for custom instruction extension.** Integrating a custom unit into a RISC-V core requires a well-defined mechanism for offloading instructions. SCAIE-V [2] presents an open-source scalable interface for ISA extensions for RISC-V processors and shows that an interface should support multi-cycle execution, control flow, and memory transactions when the extension becomes complex. This comparison informs the integration strategy adopted in this project, where a lightweight custom-instruction path is sufficient for the proposed accelerator [2], [6], [8].

**Automatic custom-instruction design.** CIDRE [4] shows that custom instructions for RISC-V can yield substantial gains on loop-dominated, data-intensive kernels while keeping area overhead modest. This work supports the chosen ASIP-style design approach and provides a useful benchmark for the expected performance and area trade-offs in this project [4], [9], [10].

Table 5.1 summarizes the core papers retained for this report and their relevance to the project.

| Paper | Main contribution | Relevance to this project |
|---|---|---|
| [1] | RedMulE: compact FP16 matrix-multiplication accelerator for RISC-V | Provides the architectural basis for a tightly coupled, configurable MAC engine |
| [2] | SCAIE-V: scalable interface for ISA extensions | Supports the design of a clean custom-instruction integration path |
| [3] | Analog AI hardware review for neural networks | Supplies the broader motivation for energy-efficient edge-AI hardware |
| [4] | CIDRE: automatic custom-instruction design for RISC-V | Validates the use of custom instructions and the expected speedup/area trade-off |

*Table 5.1: Papers retained for the literature review and their relevance to this project.*

Relevant figures from the reviewed literature can be incorporated into the report to enhance the technical discussion. Among the most useful visuals is the SCAIE-V architecture flow in [2], which illustrates how a base RISC-V core is extended through an ISA-level interface for custom hardware support. In addition, the analog AI review in [3] includes a classification of analog VLSI architectures for neural networks and a memristor-based crossbar array diagram, both of which clearly explain the motivation for MAC-based and in-memory computing approaches in edge-AI hardware. These diagrams are valuable because they visually support the discussion of custom instruction extension, MAC computation, and the hardware-level trade-offs that motivate the proposed configurable accelerator. The project’s own architecture diagram in Fig. 2 already provides the core system-level view, while the external figures in [2] and [3] serve as strong supporting illustrations for the background literature review.

**Research gap.** The reviewed literature covers tightly coupled accelerators [1], custom-instruction interfaces [2], automatic instruction synthesis [4], and the broader need for energy-efficient edge-AI hardware [3]. What is missing is a systematic FPGA-based study of a *configurable* single-core RISC-V accelerator in which the MAC count and operand width are varied and the resulting speedup/area/energy trade-offs are quantified on real FPGA fabric. This project fills that gap.

| S/No. | Author(s) | Year | Journal / Conference / Book | Title | Methodology | Results | Gaps identified |
|---|---|---|---|---|---|---|---|
| 1 | Y. Tortorella, L. Bertaccini, D. Rossi, L. Benini, F. Conti | 2022 | IEEE/ACM International Symposium on Low Power Electronics and Design (ISLPED) | RedMulE: A compact FP16 matrix-multiplication accelerator for adaptive deep learning on RISC-V-based ultra-low-power SoCs | Hardware accelerator design for a compact matrix-multiplication engine on RISC-V; architecture-level performance analysis | Demonstrates strong energy efficiency and throughput with a configurable FP16 accelerator | Focuses mainly on matrix multiplication, not a broader FPGA-based trade-off study across MAC counts and operand widths |
| 2 | M. Damian, J. Oppermann, C. Spang, A. Koch | 2022 | ACM/IEEE Design Automation Conference (DAC) | SCAIE-V: An open-source scalable interface for ISA extensions for RISC-V processors | Design and evaluation of a scalable interface for custom ISA extensions | Provides a practical interface solution for integrating hardware extensions with RISC-V | Does not implement a complete AI accelerator or evaluate configurable MAC-array performance |
| 3 | K. S. Gorde, S. M. Sonavane, S. Hutke, A. Hutke | 2025 | Bulletin of Electrical Engineering and Informatics | Analog artificial intelligence hardware for neural networks: Design trends and considerations | Review of analog AI hardware trends and design considerations | Highlights motivation for energy-efficient edge-AI hardware | Review only; no FPGA implementation or quantitative evaluation of RISC-V accelerator trade-offs |
| 4 | E. Rezunov, N. Zurstraßen, L. M. Reimann, R. Leupers | 2025 | IEEE/ACM International Conference on Computer-Aided Design (ICCAD) | Automatic microarchitecture-aware custom instruction design for RISC-V processors | Automatic custom-instruction generation and microarchitecture-aware design analysis | Shows performance gains with modest area cost for RISC-V kernels | Focused on custom instructions rather than a configurable, FPGA-validated accelerator design |
| 5 | P. Warden, D. Situnayake | 2021 | Book | TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers | Practical guide to deploying tiny ML on embedded devices | Establishes the importance of ultra-low-power AI workloads at the edge | Not a hardware accelerator design; no RISC-V accelerator architecture or FPGA evaluation |
| 6 | A. Waterman, K. Asanović | 2017 | Book | The RISC-V Instruction Set Manual | ISA specification and architectural reference | Defines the extension model and baseline RISC-V design space | Not specific to AI acceleration or FPGA implementation |
| 7 | Xilinx, Inc. | 2023 | Book / Datasheet | 7 Series FPGAs Data Sheet: Overview | FPGA architecture and resource specification reference | Provides resource and timing basis for implementation on Artix-7 devices | No AI accelerator design or performance benchmarking |
| 8 | Digilent, Inc. | 2020 | Book / Datasheet | Basys 3 Artix-7 FPGA Trainer Board Reference Manual | Hardware board documentation and resource summary | Supports hardware integration and FPGA prototyping workflow | Not an AI architecture reference |
| 9 | C. Spear, G. Tumbush | 2012 | Book | SystemVerilog for Verification: A Guide to Learning the Testbench Language Features | Verification methodology for hardware testbenches | Supports functional and regression verification of digital designs | Does not focus on embedded AI accelerator research |
| 10 | P. P. Chu | 2018 | Book | FPGA Prototyping by SystemVerilog Examples: Xilinx Spartan-3 Version | FPGA prototyping and RTL design methodology | Provides design and validation examples for FPGA-based hardware systems | Not specific to RISC-V AI acceleration |
| 11 | B. A. Forouzan | 2013 | Book | Data Communications and Networking | Networking and system-level data communication reference | Useful for understanding data movement and memory communication design | Not directly related to AI accelerator microarchitecture |
| 12 | YouTube explanation channel | 2026 | YouTube video | How FPGAs work — explained in simple terms | Educational video on FPGA fundamentals | Helps clarify FPGA architecture for non-specialist readers | Not a research source; not a technical paper or benchmark capability |

*Table 5.2: Comparative summary of the reviewed literature and identified research gap.*

---

## 6.0 Abstract

The growing deployment of AI and machine learning at the edge has created a strong demand for energy-efficient hardware that can run data-parallel workloads such as matrix multiplication, convolution, and dot products within strict power and cost budgets. Conventional embedded processors — including the single-issue, in-order PicoRV32 RISC-V core — execute these workloads as long sequences of scalar instructions, which results in poor execution time, low throughput, and high energy consumption. At the same time, existing accelerators are typically fixed-configuration designs that cannot be tuned to an application's accuracy, power, or resource budget, and their integration into open-source RISC-V cores is often hindered by the lack of standardized extension interfaces. These two problems motivate the need for a configurable AI acceleration extension for an embedded RISC-V processor.

This project proposes the design and FPGA-based evaluation of a configurable multiply–accumulate (MAC) accelerator engine integrated with a PicoRV32 RV32I core through custom RISC-V instructions (MATMUL, CONV, MAC, DOT, LOAD_TILE, STORE_TILE, WAIT). The system is implemented in SystemVerilog on the Xilinx Artix-7 XC7A35T FPGA of the Digilent Basys 3 board. The accelerator parameterizes the number of MAC units (2/4/8) and the operand width (INT8/INT16/INT32), includes a scratchpad and controller, and is verified with SystemVerilog/Cocotb testbenches including differential testing against software references. A benchmark suite of matrix multiplication, Sobel edge detection, Gaussian blur, FIR filter, dot product, and a tiny CNN is used to measure the design across configurations.

The expected outcome is a working accelerated RISC-V system on FPGA demonstrating multi-fold speedups over the software baseline on AI kernels, with detailed trade-off analysis of speedup, clock frequency, LUT/BRAM/DSP utilization, and power across configurations. Anticipated results include 5–20× speedup on the benchmark kernels for the 8-MAC configuration, a modest (10–30%) increase in logic utilization relative to the baseline core, and an explicit characterization of how performance-per-area scales with MAC count — together with a validated design-space methodology that can guide future edge-AI accelerator design.

---

## 7.0 Methodology

The project was carried out in five phases. First, the problem was identified through a review of existing systems and user requirements. Next, the system requirements were analyzed, and the appropriate hardware and software tools were selected. A system architecture and flowchart were then designed to illustrate the working process. The proposed solution was implemented using the selected technologies. Finally, the developed system was tested under different operating conditions, and its performance was evaluated based on accuracy, efficiency, and reliability.

**1. Problem Identification.** The engineering problem was defined through the literature survey: scalar embedded cores are inefficient for data-parallel AI kernels, and existing accelerators lack configurability and clean RISC-V integration. The gap analysis (Section 5.5) established the need for a configurable MAC-based extension to an embedded RISC-V core evaluated on FPGA.

**2. Requirement Analysis.** Functional requirements include: a working RV32I core on FPGA; a configurable MAC engine; custom instructions for kernel offload; and a benchmark and reporting framework. Technical requirements include the Basys 3 board (Xilinx Artix-7 XC7A35T), Vivado 2025.2 for synthesis and implementation, the RISC-V GCC toolchain for firmware, SystemVerilog and Cocotb for verification, and simulation tools (iverilog/ModelSim as available).

**3. Proposed System Design.** The architecture (Fig. 2) couples the PicoRV32 core to a configurable accelerator over a lightweight memory and custom-instruction interface. The accelerator consists of a MAC array, a scratchpad for operand tiles, a controller/FSM, and a register interface for status. Custom instructions are decoded either through PicoRV32's PCPI port or a minimal extension of the decoder and execute stage.

```
        +------------------------------+
        |  PicoRV32 RV32I Core         |
        |  (decoder / execute)         |<------- firmware.hex (instr mem)
        +-----+----------+-------------+
              | PCPI / custom dec  | mem bus
        +-----v----------+    +-----v-------------+
        |  Custom Inst.  |    |  Scratchpad +     |
        |  Decoder/CTRL  |<-->|  memory system    |
        +----------------+    +-------------------+
              |
        +-----v--------------------------------+
        |  Configurable MAC Array (2/4/8 units)|
        |  INT8 / INT16 / INT32 datapath       |
        +--------------------------------------+
```

*Fig. 2: Proposed architecture — configurable AI acceleration extension for an embedded RISC-V processor on FPGA.*

**4. Implementation.** The baseline PicoRV32 core was first brought up on the Basys 3 board, loading a small firmware image from instruction memory and verifying continuous execution via debug LEDs. The accelerator is then implemented in SystemVerilog with configurable MAC count and operand width, integrated with the core, and benchmark programs are cross-compiled with the RISC-V toolchain. Verification is performed with SystemVerilog testbenches and/or Cocotb, comparing hardware results against software references on randomized inputs.

**5. Testing and Validation (Proposed).** The system is tested with (a) unit tests for each custom instruction, (b) differential tests that compare accelerator outputs with golden software models, (c) regression and randomized tests for pipeline and handshake corner cases, and (d) on-board demonstration on the FPGA. Performance is measured in execution cycles, speedup, maximum clock frequency, LUT/BRAM/DSP utilization, and estimated power for each configuration.

**6. Results and Analysis (Expected).** Results will be tabulated and graphed to compare the 2/4/8-MAC configurations against the software baseline, and discussed against the stated objectives, including any limitations such as memory-bandwidth saturation or timing-closure constraints.

---

## 8.0 Expected Output

The expected outcomes of the project are:

- A functional and reliable configurable AI acceleration extension integrated with the PicoRV32 embedded RISC-V processor on the Basys 3 FPGA, meeting all project requirements.
- A documented custom-instruction set (MATMUL, CONV, MAC, DOT, LOAD_TILE, STORE_TILE, WAIT) with a verified decoder and execution path.
- A benchmark suite (matrix multiplication, Sobel, Gaussian blur, FIR, dot product, tiny CNN) with software baselines and timing data.
- A verified RTL design (SystemVerilog) with a regression test suite, coverage report, and differential (hardware-vs-software) validation results.
- A synthesis and implementation flow producing bitstreams for the 2/4/8-MAC configurations, with timing, area, and power reports.
- A quantitative performance evaluation demonstrating multi-fold speedup (expected 5–20× on the 8-MAC configuration) over the software baseline, with explicit speedup–area–power trade-off graphs.
- A scalable and maintainable design whose MAC count and operand width can be re-parameterized, and which can be enhanced with additional kernels or a larger MAC array in future work.
- A complete research report and (in later phases) a research paper and thesis documenting the design, methodology, and results.

---

## 9.0 Other Relevant Information

### 9.1 Financial Arrangements

The budget is given below:

| S/N | ITEM | DESCRIPTION | REMARK | COST (INR) |
|---|---|---|---|---:|
| 1 | FPGA Development Board | Digilent Basys 3 (Xilinx Artix-7 XC7A35T) | Available in the college laboratory | ₹18,000.00 |
| 2 | Programming and Connection Accessories | USB cable, power adapter, jumper wires, and breadboard | Available in the college laboratory | ₹2,500.00 |
| 3 | Electronic Components | LEDs, resistors, switches, and basic prototyping hardware | To be procured as needed | ₹1,200.00 |
| 4 | Documentation and Printing | Printing of report, charts, and supporting documents | Required for final documentation | ₹800.00 |
|  | **Grand Total** |  |  | **₹22,500.00** |

*Table 9.1: Budget of conducting project.*

### 9.2 Duration

This project will be completed in one year. The proposed schedule is given below:

| SL. NO. | TASK NAME | JUL | AUG | SEP | OCT | NOV | DEC |
|---|---|---|---|---|---|---|---|
| 1 | Literature review | ███ | ███ | | | | |
| 2 | Data collection & system analysis | | ███ | ███ | | | |
| 3 | System Design and Development | | | ███ | ███ | | |
| 4 | Prototype testing & installation | | | | ███ | ███ | |
| 5 | Writing report | | | | | ███ | ███ |
| 6 | Submission | | | | | | ███ |

*Table 9.2: Proposed time schedule.*

---

## 10.0 References

[1] Y. Tortorella, L. Bertaccini, D. Rossi, L. Benini, and F. Conti, “RedMulE: A compact FP16 matrix-multiplication accelerator for adaptive deep learning on RISC-V-based ultra-low-power SoCs,” in Proc. IEEE/ACM Int. Symp. Low Power Electron. Des. (ISLPED), Boston, MA, USA, 2022, pp. 1–6.

[2] M. Damian, J. Oppermann, C. Spang, and A. Koch, “SCAIE-V: An open-source scalable interface for ISA extensions for RISC-V processors,” in Proc. 59th ACM/IEEE Des. Autom. Conf. (DAC), San Francisco, CA, USA, 2022, pp. 1–6, doi: 10.1145/3489517.3530432.

[3] K. S. Gorde, S. M. Sonavane, S. Hutke, and A. Hutke, “Analog artificial intelligence hardware for neural networks: Design trends and considerations,” Bull. Electr. Eng. Inform., vol. 14, no. 6, pp. 4399–4410, Dec. 2025, doi: 10.11591/eei.v14i6.10842.

[4] E. Rezunov, N. Zurstraßen, L. M. Reimann, and R. Leupers, “Automatic microarchitecture-aware custom instruction design for RISC-V processors,” in Proc. IEEE/ACM Int. Conf. Comput.-Aided Design (ICCAD), Munich, Germany, 2025, pp. 1–9, doi: 10.1109/ICCAD66269.2025.11240781.

[5] P. Warden and D. Situnayake, TinyML: Machine learning with TensorFlow Lite on Arduino and ultra-low-power microcontrollers. Sebastopol, CA, USA: O’Reilly Media, 2021.

[6] A. Waterman and K. Asanović, The RISC-V instruction set manual. Berkeley, CA, USA: CS Division, Univ. California, 2017.

[7] Xilinx, Inc., 7 Series FPGAs data sheet: Overview. San Jose, CA, USA, 2023.

[8] Digilent, Inc., Basys 3 Artix-7 FPGA trainer board reference manual. Pullman, WA, USA, 2020.

[9] C. Spear and G. Tumbush, SystemVerilog for verification: A guide to learning the testbench language features, 3rd ed. New York, NY, USA: Springer, 2012.

[10] P. P. Chu, FPGA prototyping by SystemVerilog examples: Xilinx Spartan-3 version. Hoboken, NJ, USA: Wiley, 2018.

[11] B. A. Forouzan, Data communications and networking, 5th ed. New York, NY, USA: McGraw-Hill, 2013.

[12] “How FPGAs work—explained in simple terms,” YouTube video. [Online]. Available: https://www.youtube.com/watch?v=Qp_dWrP4R2s. Accessed: Aug. 31, 2026.

---

## Summary of Reviewed Papers

| Paper | Research focus | Key contribution | Limitation |
|---|---|---|---|
| RedMulE | Matrix multiplication acceleration on RISC-V | Shows a compact, configurable FP16 accelerator for better speed and energy efficiency | Mainly focused on matrix multiply, not full FPGA trade-off study |
| SCAIE-V | Custom ISA interface for RISC-V | Provides a scalable interface for adding hardware extensions | It is an interface design, not a complete AI accelerator |
| Analog AI Hardware Review | Analog AI hardware for neural networks | Reviews energy-efficient analog AI hardware trends | It is only a review, no implementation or FPGA results |
| CIDRE | Custom instruction design for RISC-V | Shows that custom instructions can improve performance with small area cost | It does not directly study a configurable FPGA accelerator |

*Table 10.1: Summary of the research focus, key contribution, and limitation of the reviewed papers.*

---

## CANDIDATES

| Name | Reg. No. | Signature | Date |
|---|---|---|---|
| ……………………………….. | ……………………………….. | ……………………………….. | ………… |
| ……………………………….. | ……………………………….. | ……………………………….. | ………… |
| ……………………………….. | ……………………………….. | ……………………………….. | ………… |
| ……………………………….. | ……………………………….. | ……………………………….. | ………… |

---

## SUPERVISOR

### 1. Comments by Supervisor:

………………………………………………………………………………………………………
……………………………………………………………………..……………………………

………………………………………………………………………………………………………
………………............................................

Date: ……............ Name: ……....……….…………..
Signature: .…………………........

### 2. Comments by Supervisor:

………………………………………………………………………………………………………
……………………………………………………………………..……………………………

………………………………………………………………………………………………………
………………............................................

Date: ……............ Name: ……....……….…………..
Signature: .…………………........
