`timescale 1ns/1ps
// ============================================================================
// top.v -- PicoRV32 + PCPI Sobel coprocessor + unified memory
// ============================================================================

module top(
    input  wire       clk,
    input  wire [5:0] sw,
    output wire [3:0] led
);

    // ==================== RESET ====================
    reg [7:0] reset_cnt = 0;
    wire resetn = &reset_cnt;

    always @(posedge clk)
        if (!resetn)
            reset_cnt <= reset_cnt + 1;

    // ==================== CPU BUS ====================
    wire        cpu_mem_valid;
    wire        cpu_mem_instr;
    wire        cpu_mem_ready;
    wire [31:0] cpu_mem_addr;
    wire [31:0] cpu_mem_wdata;
    wire [31:0] cpu_mem_rdata;
    wire [ 3:0] cpu_mem_wstrb;
    wire        trap;

    // ==================== PCPI ====================
    wire        pcpi_valid;
    wire [31:0] pcpi_insn;
    wire [31:0] pcpi_rs1;
    wire [31:0] pcpi_rs2;
    wire        pcpi_wr;
    wire [31:0] pcpi_rd;
    wire        pcpi_wait;
    wire        pcpi_ready;

    // ==================== SOBEL MEMORY MASTER ====================
    wire        sob_mem_valid;
    wire [31:0] sob_mem_addr;
    wire [31:0] sob_mem_wdata;
    wire [ 3:0] sob_mem_wstrb;
    wire        sob_mem_ready;
    wire [31:0] sob_mem_rdata;

    // ==================== BUS ARBITER ====================
    // The coprocessor only requests the bus while the CPU is stalled on
    // pcpi_wait, so a simple two-owner arbiter is sufficient.
    reg bus_owner;              // 0 = CPU, 1 = Sobel
    wire cpu_grant = (bus_owner == 1'b0);
    wire sob_grant = (bus_owner == 1'b1);

    wire        bus_valid = cpu_grant ? cpu_mem_valid : sob_mem_valid;
    wire [31:0] bus_addr  = cpu_grant ? cpu_mem_addr  : sob_mem_addr;
    wire [31:0] bus_wdata = cpu_grant ? cpu_mem_wdata : sob_mem_wdata;
    wire [ 3:0] bus_wstrb = cpu_grant ? cpu_mem_wstrb : sob_mem_wstrb;
    wire        bus_instr = cpu_grant ? cpu_mem_instr : 1'b0;
    wire        bus_ready;
    wire [31:0] bus_rdata;

    assign cpu_mem_ready = cpu_grant && bus_ready;
    assign cpu_mem_rdata = bus_rdata;
    assign sob_mem_ready = sob_grant && bus_ready;
    assign sob_mem_rdata = bus_rdata;

    always @(posedge clk) begin
        if (!resetn) begin
            bus_owner <= 1'b0;
        end else begin
            if (bus_owner == 1'b0) begin
                if (!cpu_mem_valid && sob_mem_valid)
                    bus_owner <= 1'b1;
            end else begin
                if (!sob_mem_valid)
                    bus_owner <= 1'b0;
            end
        end
    end

    // ==================== CPU ====================
    picorv32 #(
        .ENABLE_PCPI(1)
    ) cpu (
        .clk(clk),
        .resetn(resetn),
        .trap(trap),

        .mem_valid(cpu_mem_valid),
        .mem_instr(cpu_mem_instr),
        .mem_ready(cpu_mem_ready),
        .mem_addr(cpu_mem_addr),
        .mem_wdata(cpu_mem_wdata),
        .mem_wstrb(cpu_mem_wstrb),
        .mem_rdata(cpu_mem_rdata),

        .mem_la_read(),
        .mem_la_write(),
        .mem_la_addr(),
        .mem_la_wdata(),
        .mem_la_wstrb(),

        .pcpi_valid(pcpi_valid),
        .pcpi_insn(pcpi_insn),
        .pcpi_rs1(pcpi_rs1),
        .pcpi_rs2(pcpi_rs2),
        .pcpi_wr(pcpi_wr),
        .pcpi_rd(pcpi_rd),
        .pcpi_wait(pcpi_wait),
        .pcpi_ready(pcpi_ready),

        .irq(32'b0),
        .eoi(),

        .trace_valid(),
        .trace_data()
    );

    // ==================== SOBEL COPROCESSOR ====================
    pcpi_sobel #(
        .MAX_W(128)
    ) u_sobel (
        .clk(clk),
        .resetn(resetn),

        .pcpi_valid(pcpi_valid),
        .pcpi_insn(pcpi_insn),
        .pcpi_rs1(pcpi_rs1),
        .pcpi_rs2(pcpi_rs2),
        .pcpi_wr(pcpi_wr),
        .pcpi_rd(pcpi_rd),
        .pcpi_wait(pcpi_wait),
        .pcpi_ready(pcpi_ready),

        .mem_valid(sob_mem_valid),
        .mem_addr(sob_mem_addr),
        .mem_wdata(sob_mem_wdata),
        .mem_wstrb(sob_mem_wstrb),
        .mem_ready(sob_mem_ready),
        .mem_rdata(sob_mem_rdata)
    );

    // ==================== MEMORY ====================
    soc_mem #(
        .INSTR_WORDS(256),
        .DATA_BYTES(8192),
        .DATA_INIT_BYTES(64),
        .DATA_BASE(32'h0000_2000)
    ) u_mem (
        .clk(clk),
        .mem_valid(bus_valid),
        .mem_instr(bus_instr),
        .mem_addr(bus_addr),
        .mem_wdata(bus_wdata),
        .mem_wstrb(bus_wstrb),
        .mem_ready(bus_ready),
        .mem_rdata(bus_rdata)
    );

    // ==================== DEBUG LED ====================
    reg [25:0] counter = 0;
    always @(posedge clk)
        counter <= counter + 1;

    assign led[0] = sw[0];
    assign led[1] = sw[1];
    assign led[2] = sw[2];
    assign led[3] = counter[25];

endmodule
