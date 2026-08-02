module top(
    input clk,
    input [5:0] sw,
    output [3:0] led
);

// ==================== CPU BUS ====================

wire trap;
wire        mem_valid;
wire        mem_instr;
wire        mem_ready;
wire [31:0] mem_addr;
wire [31:0] mem_wdata;
wire [3:0]  mem_wstrb;
reg  [31:0] mem_rdata;
reg mem_ready_reg = 0;


// ==================== INSTRUCTION MEMORY ====================

reg [31:0] instr_mem [0:255];


// ==================== RESET ====================

reg [7:0] reset_cnt = 0;
wire resetn = &reset_cnt;

always @(posedge clk)
begin
    if (!resetn)
        reset_cnt <= reset_cnt + 1;


end


// ==================== CPU ====================

picorv32 cpu (
    .clk(clk),
    .resetn(resetn),
    .trap(trap),

    .mem_valid(mem_valid),
    .mem_instr(mem_instr),
    .mem_ready(mem_ready),

    .mem_addr(mem_addr),
    .mem_wdata(mem_wdata),
    .mem_wstrb(mem_wstrb),
    .mem_rdata(mem_rdata),

    .mem_la_read(),
    .mem_la_write(),
    .mem_la_addr(),
    .mem_la_wdata(),
    .mem_la_wstrb(),

    .pcpi_valid(),
    .pcpi_insn(),
    .pcpi_rs1(),
    .pcpi_rs2(),
    .pcpi_wr(1'b0),
    .pcpi_rd(32'b0),
    .pcpi_wait(1'b0),
    .pcpi_ready(1'b0),

    .irq(32'b0),
    .eoi(),

    .trace_valid(),
    .trace_data()
);


// ==================== LOAD FIRMWARE ====================

initial begin
    $readmemh("E:/riscv_new/riscv_cpu_new/riscv_cpu_new.srcs/sources_1/new/firmware.hex", instr_mem);
end


// ==================== MEMORY ====================

always @(*) begin

    if (mem_addr < 32'h00000100)
        mem_rdata = instr_mem[mem_addr[9:2]];
    else
        mem_rdata = 32'h00000013;

end

assign mem_ready = mem_valid;

// ==================== DEBUG LED ====================
// 我們直接看 CPU program counter 變化

reg [25:0] counter = 0;

always @(posedge clk)
begin
    counter <= counter + 1;
end

assign led[0] = mem_addr[2];
assign led[1] = mem_addr[3];
assign led[2] = mem_addr[4];
assign led[3] = counter[25];

endmodule