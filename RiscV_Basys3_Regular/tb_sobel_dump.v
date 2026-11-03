// ============================================================================
// tb_sobel_dump.v -- run one arbitrary image through pcpi_sobel and dump out
//
// The input image is loaded from sobel_input.hex (one byte per line). The
// hardware output is written to sobel_output.hex. Every output byte is also
// compared against a behavioural golden model so the dumped image is known
// to be correct before it is turned into a figure for the report.
// ============================================================================

`timescale 1ns/1ps

module tb_sobel_dump;

    localparam integer W      = 128;
    localparam integer H      = 96;
    localparam integer MEM_SZ = 65536;
    localparam [15:0]  IMG    = 16'h1000;
    localparam [15:0]  OUT    = 16'h5000;

    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;

    reg         pcpi_valid = 0;
    reg  [31:0] pcpi_insn = 0;
    reg  [31:0] pcpi_rs1 = 0;
    reg  [31:0] pcpi_rs2 = 0;
    wire        pcpi_wr;
    wire [31:0] pcpi_rd;
    wire        pcpi_wait;
    wire        pcpi_ready;

    wire        mem_valid;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [ 3:0] mem_wstrb;
    wire        mem_ready;
    wire [31:0] mem_rdata;

    reg [7:0] mem [0:MEM_SZ-1];

    wire [15:0] mbase = {mem_addr[15:2], 2'b00};

    assign mem_ready = mem_valid;
    assign mem_rdata = {mem[mbase+3], mem[mbase+2], mem[mbase+1], mem[mbase]};

    always @(posedge clk) begin
        if (mem_valid) begin
            if (mem_wstrb[0]) mem[mbase]   <= mem_wdata[ 7: 0];
            if (mem_wstrb[1]) mem[mbase+1] <= mem_wdata[15: 8];
            if (mem_wstrb[2]) mem[mbase+2] <= mem_wdata[23:16];
            if (mem_wstrb[3]) mem[mbase+3] <= mem_wdata[31:24];
        end
    end

    pcpi_sobel dut (
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
        .mem_valid(mem_valid),
        .mem_addr(mem_addr),
        .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb),
        .mem_ready(mem_ready),
        .mem_rdata(mem_rdata)
    );

    reg [31:0] rd_val;
    integer i, x, y, err;

    task pcpi_op(input [2:0] f3, input [31:0] a1, input [31:0] a2);
        begin
            @(negedge clk);
            pcpi_valid = 1'b1;
            pcpi_insn  = {7'h21, a2[4:0], a1[4:0], f3, 5'd0, 7'h0b};
            pcpi_rs1   = a1;
            pcpi_rs2   = a2;
            @(posedge clk);
            while (!pcpi_ready)
                @(posedge clk);
            rd_val = pcpi_rd;
            @(negedge clk);
            pcpi_valid = 1'b0;
            @(negedge clk);
        end
    endtask

    function [7:0] golden(input integer px, input integer py);
        integer p00, p01, p02, p10, p12, p20, p21, p22;
        integer gx, gy, mag;
        begin
            if ((px < 1) || (py < 1) || (px >= W-1) || (py >= H-1)) begin
                golden = 8'd0;
            end else begin
                p00 = mem[IMG + (py-1)*W + (px-1)];
                p01 = mem[IMG + (py-1)*W + (px  )];
                p02 = mem[IMG + (py-1)*W + (px+1)];
                p10 = mem[IMG + (py  )*W + (px-1)];
                p12 = mem[IMG + (py  )*W + (px+1)];
                p20 = mem[IMG + (py+1)*W + (px-1)];
                p21 = mem[IMG + (py+1)*W + (px  )];
                p22 = mem[IMG + (py+1)*W + (px+1)];
                gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20);
                gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02);
                mag = ((gx < 0) ? -gx : gx) + ((gy < 0) ? -gy : gy);
                if (mag > 255) mag = 255;
                golden = mag[7:0];
            end
        end
    endfunction

    integer f;
    initial begin
        for (i = 0; i < MEM_SZ; i = i + 1)
            mem[i] = 8'd0;

        $readmemh("sobel_input.hex", mem, IMG, IMG + W*H - 1);

        #40 resetn = 1;
        #20;

        pcpi_op(3'd0, IMG, (H << 16) | W);   // SOBEL_SET
        pcpi_op(3'd1, OUT, 32'd0);           // SOBEL_RUN

        err = 0;
        for (y = 0; y < H; y = y + 1) begin
            for (x = 0; x < W; x = x + 1) begin
                if (mem[OUT + y*W + x] !== golden(x, y)) begin
                    err = err + 1;
                    if (err <= 5)
                        $display("  mismatch (%0d,%0d): got %0d exp %0d",
                                 x, y, mem[OUT + y*W + x], golden(x,y));
                end
            end
        end

        if (rd_val !== (W*H)) begin
            $display("  pixel count mismatch: got %0d exp %0d", rd_val, W*H);
            err = err + 1;
        end

        f = $fopen("sobel_output.hex", "w");
        for (i = 0; i < W*H; i = i + 1)
            $fdisplay(f, "%02x", mem[OUT + i]);
        $fclose(f);

        if (err == 0)
            $display("=== SOBEL DUMP PASSED (%0dx%0d, HW == golden) ===", W, H);
        else
            $display("=== SOBEL DUMP FAILED (%0d errors) ===", err);
        $finish;
    end

endmodule
