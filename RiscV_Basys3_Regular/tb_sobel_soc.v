// ============================================================================
// tb_sobel_soc.v -- full PicoRV32 + Sobel-PCPI + memory integration test
//
// Runs the firmware in firmware.hex (assembled from programs/sobel_test.S).
// The firmware:
//   1. computes Sobel in software into OUT_SW
//   2. computes it with SOBEL_SET + SOBEL_RUN into OUT_HW
//   3. compares the two byte-for-byte
//   4. records cycles / instructions / mismatch count / a magic value
// This testbench independently checks the results against a golden model and
// reports the measured speedup.
// ============================================================================

`timescale 1ns/1ps

module tb_sobel_soc;

    localparam [31:0] DATA_BASE = 32'h0000_2000;
    localparam [31:0] IMG_BASE  = 32'h0000_2000;
    localparam [31:0] OUT_SW    = 32'h0000_2040;
    localparam [31:0] OUT_HW    = 32'h0000_2080;
    localparam [31:0] RESULT    = 32'h0000_2100;
    localparam integer PIXELS   = 64;
    localparam integer W = 8;
    localparam integer H = 8;

    reg clk = 0;
    reg [5:0] sw = 0;
    wire [3:0] led;

    always #5 clk = ~clk;

    top dut (
        .clk(clk),
        .sw(sw),
        .led(led)
    );

    integer cycles = 0;
    always @(posedge clk)
        cycles <= cycles + 1;

    function [7:0] db(input integer addr);
        begin
            db = dut.u_mem.data_mem[addr - DATA_BASE];
        end
    endfunction

    function [31:0] dw(input integer addr);
        integer k;
        reg [31:0] v;
        begin
            v = 32'd0;
            for (k = 0; k < 4; k = k + 1)
                v = v | (db(addr + k) << (8*k));
            dw = v;
        end
    endfunction

    function [7:0] golden(input integer px, input integer py);
        integer p00, p01, p02, p10, p12, p20, p21, p22;
        integer gx, gy, mag;
        begin
            if ((px < 1) || (py < 1) || (px >= W-1) || (py >= H-1)) begin
                golden = 8'd0;
            end else begin
                p00 = db(IMG_BASE + (py-1)*W + (px-1));
                p01 = db(IMG_BASE + (py-1)*W + (px  ));
                p02 = db(IMG_BASE + (py-1)*W + (px+1));
                p10 = db(IMG_BASE + (py  )*W + (px-1));
                p12 = db(IMG_BASE + (py  )*W + (px+1));
                p20 = db(IMG_BASE + (py+1)*W + (px-1));
                p21 = db(IMG_BASE + (py+1)*W + (px  ));
                p22 = db(IMG_BASE + (py+1)*W + (px+1));
                gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20);
                gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02);
                mag = ((gx < 0) ? -gx : gx) + ((gy < 0) ? -gy : gy);
                if (mag > 255) mag = 255;
                golden = mag[7:0];
            end
        end
    endfunction

    integer x, y, err, timeout;
    reg [31:0] sw_cycles, sw_instret, hw_cycles, hw_instret;
    reg [31:0] pass, mismatches, pixels, magic;

    initial begin
        $display("=== Sobel SoC integration test ===");
        timeout = 0;
        // wait for the 256-cycle reset counter plus firmware completion
        while ((dw(RESULT + 28) != 32'hDEADBEEF) && (timeout <= 200000)) begin
            @(posedge clk);
            timeout = timeout + 1;
        end
        if (timeout > 200000) begin
            $display("TIMEOUT after %0d cycles (magic=%08x)", timeout,
                     dw(RESULT + 28));
            $finish;
        end

        sw_cycles  = dw(RESULT + 0);
        sw_instret = dw(RESULT + 4);
        hw_cycles  = dw(RESULT + 8);
        hw_instret = dw(RESULT + 12);
        pass       = dw(RESULT + 16);
        mismatches = dw(RESULT + 20);
        pixels     = dw(RESULT + 24);
        magic      = dw(RESULT + 28);

        $display("");
        $display("firmware results:");
        $display("  SW cycles        : %0d  (%0.2f cycles/pixel)",
                 sw_cycles, sw_cycles / (PIXELS * 1.0));
        $display("  SW instructions  : %0d  (%0.2f insn/pixel)",
                 sw_instret, sw_instret / (PIXELS * 1.0));
        $display("  HW cycles        : %0d  (%0.2f cycles/pixel)",
                 hw_cycles, hw_cycles / (PIXELS * 1.0));
        $display("  HW instructions  : %0d", hw_instret);
        $display("  speedup          : %0.2fx", sw_cycles / (hw_cycles * 1.0));
        $display("  pass / mismatch  : %0d / %0d", pass, mismatches);
        $display("");

        err = 0;
        if (pass !== 32'd1)      begin $display("ERROR: pass flag != 1"); err = err+1; end
        if (mismatches !== 32'd0) begin $display("ERROR: firmware mismatches != 0"); err = err+1; end
        if (pixels !== PIXELS)    begin $display("ERROR: pixel count %0d", pixels); err = err+1; end
        if (magic !== 32'hDEADBEEF) begin $display("ERROR: bad magic"); err = err+1; end
        if (sw_cycles == 0 || hw_cycles == 0) begin
            $display("ERROR: zero cycle count");
            err = err + 1;
        end

        for (y = 0; y < H; y = y + 1) begin
            for (x = 0; x < W; x = x + 1) begin
                if (db(OUT_SW + y*W + x) !== golden(x, y)) begin
                    $display("ERROR: SW golden mismatch at (%0d,%0d): %0d vs %0d",
                             x, y, db(OUT_SW + y*W + x), golden(x,y));
                    err = err + 1;
                end
                if (db(OUT_HW + y*W + x) !== golden(x, y)) begin
                    $display("ERROR: HW golden mismatch at (%0d,%0d): %0d vs %0d",
                             x, y, db(OUT_HW + y*W + x), golden(x,y));
                    err = err + 1;
                end
            end
        end

        if (err == 0)
            $display("=== SOBEL SOC TEST PASSED (HW == SW == golden) ===");
        else
            $display("=== SOBEL SOC TEST FAILED (%0d errors) ===", err);
        $finish;
    end

endmodule
