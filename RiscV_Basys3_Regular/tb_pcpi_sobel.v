// ============================================================================
// tb_pcpi_sobel.v -- standalone functional testbench for pcpi_sobel
//
// Drives the PCPI slave directly with a zero-wait memory model and compares
// every output byte against a behavioural golden model.  Covers normal
// images, odd dimensions, degenerate dimensions and random pixel data.
// ============================================================================

`timescale 1ns/1ps

module tb_pcpi_sobel;

    localparam MAX_W   = 128;
    localparam MEM_SZ  = 65536;

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

    pcpi_sobel #(.MAX_W(MAX_W)) dut (
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
    integer i, x, y, err, total_err, cases;

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

    function [7:0] golden(input integer base, input integer w,
                          input integer h, input integer px,
                          input integer py);
        integer p00, p01, p02, p10, p12, p20, p21, p22;
        integer gx, gy, mag;
        begin
            if ((px < 1) || (py < 1) || (px >= w-1) || (py >= h-1)) begin
                golden = 8'd0;
            end else begin
                p00 = mem[base + (py-1)*w + (px-1)];
                p01 = mem[base + (py-1)*w + (px  )];
                p02 = mem[base + (py-1)*w + (px+1)];
                p10 = mem[base + (py  )*w + (px-1)];
                p12 = mem[base + (py  )*w + (px+1)];
                p20 = mem[base + (py+1)*w + (px-1)];
                p21 = mem[base + (py+1)*w + (px  )];
                p22 = mem[base + (py+1)*w + (px+1)];
                gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20);
                gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02);
                mag = ((gx < 0) ? -gx : gx) + ((gy < 0) ? -gy : gy);
                if (mag > 255) mag = 255;
                golden = mag[7:0];
            end
        end
    endfunction

    task run_case(input integer w, input integer h,
                  input integer img_base, input integer out_base,
                  input integer randomize, input [127:0] name);
        integer px, py, exp, got, nerr;
        begin
            for (i = 0; i < w*h; i = i + 1) begin
                if (randomize)
                    mem[img_base + i] = $random;
                else
                    mem[img_base + i] = 10 + (i / w) * 5 + (i % w) * 10;
            end
            for (i = 0; i < w*h; i = i + 1)
                mem[out_base + i] = 8'hA5;

            pcpi_op(3'd0, img_base, (h << 16) | w);   // SET
            pcpi_op(3'd1, out_base, 32'd0);           // RUN

            nerr = 0;
            for (py = 0; py < h; py = py + 1) begin
                for (px = 0; px < w; px = px + 1) begin
                    exp = golden(img_base, w, h, px, py);
                    got = mem[out_base + py*w + px];
                    if (got !== exp) begin
                        nerr = nerr + 1;
                        if (nerr <= 4)
                            $display("    mismatch (%0d,%0d): got %0d exp %0d",
                                     px, py, got, exp);
                    end
                end
            end

            if (rd_val !== (w*h)) begin
                $display("    pixel count mismatch: got %0d exp %0d",
                         rd_val, w*h);
                nerr = nerr + 1;
            end

            if (nerr == 0) begin
                $display("  PASS  %0s  (%0dx%0d, %0d pixels)",
                         name, w, h, w*h);
            end else begin
                $display("  FAIL  %0s  (%0d errors)", name, nerr);
                total_err = total_err + 1;
            end
            cases = cases + 1;
        end
    endtask

    initial begin
        total_err = 0;
        cases = 0;
        for (i = 0; i < MEM_SZ; i = i + 1)
            mem[i] = 8'd0;

        $display("=== pcpi_sobel standalone test ===");
        #40 resetn = 1;

        run_case(8,  8,  16'h1000, 16'h3000, 0, "ramp 8x8");
        run_case(16, 16, 16'h1000, 16'h3000, 1, "random 16x16");
        run_case(5,  3,  16'h1000, 16'h3000, 1, "random 5x3");
        run_case(3,  5,  16'h1000, 16'h3000, 1, "random 3x5");
        run_case(3,  3,  16'h1000, 16'h3000, 1, "random 3x3");
        run_case(2,  7,  16'h1000, 16'h3000, 1, "degenerate 2x7");
        run_case(7,  2,  16'h1000, 16'h3000, 1, "degenerate 7x2");
        run_case(1,  1,  16'h1000, 16'h3000, 0, "degenerate 1x1");
        run_case(1,  9,  16'h1000, 16'h3000, 0, "degenerate 1x9");
        run_case(9,  1,  16'h1000, 16'h3000, 0, "degenerate 9x1");
        run_case(32, 20, 16'h1000, 16'h3000, 1, "random 32x20");

        if (total_err == 0)
            $display("=== TEST PASSED (%0d cases) ===", cases);
        else
            $display("=== TEST FAILED (%0d/%0d cases) ===", total_err, cases);
        $finish;
    end

endmodule
