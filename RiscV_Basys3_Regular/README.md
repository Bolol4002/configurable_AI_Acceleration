## 1. Project Name

RISC-V FPGA CPU Integration Project on Basys 3 Development Board

This project attempts to integrate an open-source PicoRV32 RISC-V CPU core into the Basys 3 FPGA development board using Verilog HDL and Xilinx Vivado. The original goal was to build a simple CPU-based calculator system, but the final implementation mainly focused on CPU integration testing, memory interface debugging, and FPGA hardware verification.

---

## 2. Development Board Used

* Digilent Basys 3 FPGA Development Board
* FPGA Device: Xilinx Artix-7 XC7A35T

---

## 3. Development Tools and Versions

The following tools were used during project development.

* Xilinx Vivado Design Suite 2025.2
* Basys 3 FPGA Development Board
* Verilog HDL
* PicoRV32 Open-Source RISC-V CPU Core

---

## 4. Project Folder Structure

Project files are organized as follows.

```text
project/

├── top.v
├── picorv32.v
├── firmware.hex
├── basys3.xdc
└── README.md
```

File descriptions:

* top.v → Top-level FPGA integration module
* picorv32.v → Open-source RISC-V CPU core
* firmware.hex → Instruction memory test program
* basys3.xdc → Basys 3 FPGA pin constraint file

---

## 5. How to Generate Bitstream

Open the project in Vivado.

Run the following design flow.

1. Run Synthesis
2. Run Implementation
3. Generate Bitstream

After successful bitstream generation, continue hardware programming.

---

## 6. How to Load or Modify RISC-V Program

The CPU instruction program is stored in firmware.hex.

To modify the program:

1. Edit firmware.hex
2. Save the modified instruction data
3. Re-run Synthesis
4. Re-run Implementation
5. Generate Bitstream again

The instruction memory is loaded using the following Verilog code.

```verilog
initial begin
    $readmemh("firmware.hex", instr_mem);
end
```

---

## 7. How to Program FPGA Board

Connect the Basys 3 board to the computer.

In Vivado:

1. Open Hardware Manager
2. Open Target
3. Program Device
4. Select generated bitstream
5. Program FPGA

After programming, observe hardware output behavior.

---

## 8. How to Operate and Test

This project currently performs CPU execution verification.

Testing procedure:

1. Power on Basys 3 board
2. Program FPGA using Vivado
3. CPU loads firmware.hex instructions
4. Observe LED behavior

LED output meaning:

* LED0 → mem_addr[2]
* LED1 → mem_addr[3]
* LED2 → mem_addr[4]
* LED3 → Clock counter blinking signal

The LED behavior is used to verify whether the CPU is continuously executing instructions.

---

## 9. Known Problems

Several issues remain unresolved.

* Full calculator functionality was not completed
* Seven-segment display output was not completed
* CPU and instruction memory integration still requires further debugging
* Memory interface timing behavior requires additional verification

The project currently focuses on CPU integration testing rather than complete application functionality.

---

## 10. External Resources and License Information

This project is partially based on external open-source resources.

Main external sources:

* PicoRV32 Open-Source CPU Core
* Xilinx Vivado Design Suite
* Digilent Basys 3 FPGA Board Documentation

Original PicoRV32 source:

https://github.com/YosysHQ/picorv32

Acknowledgment:

This project uses the PicoRV32 open-source RISC-V CPU core developed by Clifford Wolf. The project code was modified and integrated for educational FPGA system development purposes.
