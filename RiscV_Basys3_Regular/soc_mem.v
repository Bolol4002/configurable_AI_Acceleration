`timescale 1ns/1ps
// ============================================================================
// soc_mem.v -- simple unified instruction/data memory for the Sobel SoC
//
//   0x0000_0000 .. 0x0000_03FF : 1 KiB instruction memory (256 x 32-bit)
//   0x0000_2000 .. 0x0000_3FFF : 8 KiB byte-addressable data memory
//
// Reads are zero-wait (combinational).  Writes are byte enabled.  The bus
// address is word aligned and bytes are selected with mem_wstrb, matching the
// PicoRV32 native memory-port protocol.
// ============================================================================

module soc_mem #(
    parameter INSTR_WORDS = 256,
    parameter DATA_BYTES  = 8192,
    parameter DATA_INIT_BYTES = 8192,
    parameter [31:0] DATA_BASE = 32'h0000_2000
) (
    input  wire        clk,
    input  wire        mem_valid,
    input  wire        mem_instr,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [ 3:0] mem_wstrb,
    output wire        mem_ready,
    output reg  [31:0] mem_rdata
);

    reg [31:0] instr_mem [0:INSTR_WORDS-1];
    reg [ 7:0] data_mem  [0:DATA_BYTES-1];

    integer i;
    initial begin
        for (i = 0; i < DATA_BYTES; i = i + 1)
            data_mem[i] = 8'd0;
        $readmemh("firmware.hex", instr_mem);
        $readmemh("data.hex", data_mem, 0, DATA_INIT_BYTES-1);
    end

    wire in_data = (mem_addr >= DATA_BASE) &&
                   (mem_addr <  (DATA_BASE + DATA_BYTES - 32'd3));
    wire [31:0] didx = mem_addr - DATA_BASE;
    wire in_instr = (mem_addr < (INSTR_WORDS * 4));

    always @(*) begin
        if (in_data)
            mem_rdata = {data_mem[didx+3], data_mem[didx+2],
                         data_mem[didx+1], data_mem[didx]};
        else if (in_instr)
            mem_rdata = instr_mem[mem_addr[9:2]];
        else
            mem_rdata = 32'h0000_0013;   // NOP
    end

    always @(posedge clk) begin
        if (mem_valid && (mem_wstrb != 4'b0000) && in_data) begin
            if (mem_wstrb[0]) data_mem[didx]   <= mem_wdata[ 7: 0];
            if (mem_wstrb[1]) data_mem[didx+1] <= mem_wdata[15: 8];
            if (mem_wstrb[2]) data_mem[didx+2] <= mem_wdata[23:16];
            if (mem_wstrb[3]) data_mem[didx+3] <= mem_wdata[31:24];
        end
    end

    assign mem_ready = mem_valid;

endmodule
