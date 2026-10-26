`timescale 1ns/1ps
// ============================================================================
// pcpi_sobel.v -- PCPI-attached 3x3 Sobel edge-detection coprocessor
//
// Streaming 3-row line-buffer design:
//   * each source pixel is read from memory exactly once (H*W reads)
//   * every output pixel is written exactly once (H*W writes)
//   * the full 3x3 window, both gradients, both absolute values and the
//     magnitude/clamp are evaluated in a single parallel combinational path
//
// Custom ISA (opcode 7'b0001011, funct7 7'b0100001, funct3 selects op):
//   funct3=0  SOBEL_SET     rs1 = image byte address
//                           rs2 = {height[31:16], width[15:0]}
//   funct3=1  SOBEL_RUN     rs1 = output byte address
//                           rd  = number of bytes written
//   funct3=2  SOBEL_STATUS  rd  = {29'b0, error, done, busy}
//   funct3=3  SOBEL_RESET   clear configuration
//
// Memory master is byte-addressed but drives a word-aligned address plus a
// byte strobe, matching the PicoRV32 native memory-port convention.
// ============================================================================

module pcpi_sobel #(
    parameter MAX_W = 128
) (
    input  wire        clk,
    input  wire        resetn,

    // PCPI slave ------------------------------------------------------------
    input  wire        pcpi_valid,
    input  wire [31:0] pcpi_insn,
    input  wire [31:0] pcpi_rs1,
    input  wire [31:0] pcpi_rs2,
    output reg         pcpi_wr,
    output reg  [31:0] pcpi_rd,
    output reg         pcpi_wait,
    output reg         pcpi_ready,

    // Memory master ---------------------------------------------------------
    output reg         mem_valid,
    output reg  [31:0] mem_addr,
    output reg  [31:0] mem_wdata,
    output reg  [ 3:0] mem_wstrb,
    input  wire        mem_ready,
    input  wire [31:0] mem_rdata
);

    localparam [6:0] SOBEL_OPCODE = 7'b0001011;
    localparam [6:0] SOBEL_FUNCT7 = 7'b0100001;

    localparam [2:0] OP_SET    = 3'd0;
    localparam [2:0] OP_RUN    = 3'd1;
    localparam [2:0] OP_STATUS = 3'd2;
    localparam [2:0] OP_RESET  = 3'd3;

    localparam [2:0] S_IDLE    = 3'd0;
    localparam [2:0] S_ROW0    = 3'd1;
    localparam [2:0] S_LOAD    = 3'd2;
    localparam [2:0] S_COMPUTE = 3'd3;
    localparam [2:0] S_SHIFT   = 3'd4;
    localparam [2:0] S_ROWLAST = 3'd5;
    localparam [2:0] S_DONE    = 3'd6;
    localparam       IDX_BITS  = (MAX_W <= 2) ? 1 : $clog2(MAX_W);

    reg [2:0]  state;

    // ------------------------------------------------------------------
    // Decode
    // ------------------------------------------------------------------
    wire        dec_match  = pcpi_valid &&
                             (pcpi_insn[6:0]   == SOBEL_OPCODE) &&
                             (pcpi_insn[31:25] == SOBEL_FUNCT7);
    wire [2:0]  dec_funct3 = pcpi_insn[14:12];

    reg         pcpi_valid_q;
    always @(posedge clk)
        pcpi_valid_q <= resetn ? pcpi_valid : 1'b0;

    wire cmd_start = dec_match && !pcpi_valid_q && (state == S_IDLE);

    // ------------------------------------------------------------------
    // State / configuration
    // ------------------------------------------------------------------
    reg [2:0]  cmd;
    reg        error;

    reg [31:0] img_base;
    reg [15:0] img_w;
    reg [15:0] img_h;

    reg [31:0] row_addr;    // next byte to fetch while loading a row
    reg [31:0] out_addr;    // next byte to store
    reg [15:0] y;           // output row being produced (1 .. H-2)
    reg [15:0] col;         // column currently being produced/loaded
    reg [15:0] ld_cnt;      // byte index inside the row being loaded
    reg [1:0]  ld_buf;      // 0/1/2 -> line0/line1/line2
    reg        init_done;   // first three rows are loaded
    reg [31:0] pix_count;   // bytes written for the current RUN

    wire [IDX_BITS-1:0] cidx  = col[IDX_BITS-1:0];
    wire [IDX_BITS-1:0] cmidx = cidx - 1'b1;
    wire [IDX_BITS-1:0] cpidx = cidx + 1'b1;
    wire [IDX_BITS-1:0] lidx  = ld_cnt[IDX_BITS-1:0];

    // Three full rows of pixels.  Indexed combinationally by the datapath.
    reg [7:0] line0 [0:MAX_W-1];
    reg [7:0] line1 [0:MAX_W-1];
    reg [7:0] line2 [0:MAX_W-1];

    integer i;
    integer j;
    initial begin
        for (i = 0; i < MAX_W; i = i + 1) begin
            line0[i] = 8'd0;
            line1[i] = 8'd0;
            line2[i] = 8'd0;
        end
    end

    // ------------------------------------------------------------------
    // Parallel 3x3 datapath
    // ------------------------------------------------------------------
    reg signed [12:0] gx;
    reg signed [12:0] gy;
    reg        [12:0] agx;
    reg        [12:0] agy;
    reg        [12:0] mag;
    reg        [7:0]  out_byte;

    always @(*) begin
        gx = 13'sd0;
        gy = 13'sd0;

        if ((state == S_COMPUTE) && (img_w > 16'd2) &&
            (col > 16'd0) && (col < img_w - 16'd1)) begin
            // Gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20)
            gx = $signed({5'b0, line0[cpidx]}) +
                 $signed({4'b0, line1[cpidx], 1'b0}) +
                 $signed({5'b0, line2[cpidx]}) -
                 $signed({5'b0, line0[cmidx]}) -
                 $signed({4'b0, line1[cmidx], 1'b0}) -
                 $signed({5'b0, line2[cmidx]});

            // Gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02)
            gy = $signed({5'b0, line2[cmidx]}) +
                 $signed({4'b0, line2[cidx],  1'b0}) +
                 $signed({5'b0, line2[cpidx]}) -
                 $signed({5'b0, line0[cmidx]}) -
                 $signed({4'b0, line0[cidx],  1'b0}) -
                 $signed({5'b0, line0[cpidx]});
        end

        agx = gx[12] ? -gx : gx;
        agy = gy[12] ? -gy : gy;
        mag = agx + agy;

        if ((state != S_COMPUTE) || (img_w <= 16'd2) ||
            (col == 16'd0) || (col == img_w - 16'd1))
            out_byte = 8'd0;
        else if (mag > 13'd255)
            out_byte = 8'd255;
        else
            out_byte = mag[7:0];
    end

    // ------------------------------------------------------------------
    // Memory request generation
    // ------------------------------------------------------------------
    reg [7:0] rd_byte;
    always @(*) begin
        case (row_addr[1:0])
            2'd0: rd_byte = mem_rdata[7:0];
            2'd1: rd_byte = mem_rdata[15:8];
            2'd2: rd_byte = mem_rdata[23:16];
            default: rd_byte = mem_rdata[31:24];
        endcase
    end

    always @(*) begin
        mem_valid = 1'b0;
        mem_addr  = 32'b0;
        mem_wdata = 32'b0;
        mem_wstrb = 4'b0000;

        case (state)
            S_ROW0, S_ROWLAST: begin
                mem_valid = 1'b1;
                mem_addr  = {out_addr[31:2], 2'b00};
                mem_wstrb = 4'b0001 << out_addr[1:0];
                mem_wdata = 32'b0;
            end
            S_LOAD: begin
                mem_valid = 1'b1;
                mem_addr  = {row_addr[31:2], 2'b00};
                mem_wstrb = 4'b0000;
            end
            S_COMPUTE: begin
                mem_valid = 1'b1;
                mem_addr  = {out_addr[31:2], 2'b00};
                mem_wstrb = 4'b0001 << out_addr[1:0];
                mem_wdata = {24'b0, out_byte} << (8 * out_addr[1:0]);
            end
            default: begin
                mem_valid = 1'b0;
            end
        endcase
    end

    wire access_done = mem_valid && mem_ready;

    // ------------------------------------------------------------------
    // PCPI / FSM
    // ------------------------------------------------------------------
    wire busy = (state != S_IDLE) && (state != S_DONE);

    always @(*) begin
        pcpi_wait  = busy;
        pcpi_ready = (state == S_DONE);
    end

    always @(*) begin
        pcpi_rd = 32'b0;
        if (state == S_DONE) begin
            if (cmd == OP_RUN)
                pcpi_rd = pix_count;
            else if (cmd == OP_STATUS)
                pcpi_rd = {29'b0, error, 1'b1, 1'b0};
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state      <= S_IDLE;
            cmd        <= OP_SET;
            error      <= 1'b0;
            pcpi_wr    <= 1'b0;
            img_base   <= 32'b0;
            img_w      <= 16'd0;
            img_h      <= 16'd0;
            row_addr   <= 32'b0;
            out_addr   <= 32'b0;
            y          <= 16'd0;
            col        <= 16'd0;
            ld_cnt     <= 16'd0;
            ld_buf     <= 2'd0;
            init_done  <= 1'b0;
            pix_count  <= 32'b0;
        end else begin
            case (state)
                // ------------------------------------------------
                S_IDLE: begin
                    if (cmd_start) begin
                        cmd     <= dec_funct3;
                        case (dec_funct3)
                            OP_SET: begin
                                img_base <= pcpi_rs1;
                                img_h    <= pcpi_rs2[31:16];
                                if (pcpi_rs2[15:0] > MAX_W) begin
                                    img_w <= MAX_W;
                                    error <= 1'b1;
                                end else begin
                                    img_w <= pcpi_rs2[15:0];
                                    error <= 1'b0;
                                end
                                pcpi_wr <= 1'b0;
                                state   <= S_DONE;
                            end
                            OP_RUN: begin
                                pcpi_wr   <= 1'b1;
                                out_addr  <= pcpi_rs1;
                                row_addr  <= img_base;
                                y         <= 16'd1;
                                col       <= 16'd0;
                                ld_cnt    <= 16'd0;
                                ld_buf    <= 2'd0;
                                init_done <= 1'b0;
                                pix_count <= 32'b0;
                                if ((img_w == 16'd0) || (img_h == 16'd0))
                                    state <= S_DONE;
                                else
                                    state <= S_ROW0;
                            end
                            OP_STATUS: begin
                                pcpi_wr <= 1'b1;
                                state   <= S_DONE;
                            end
                            OP_RESET: begin
                                pcpi_wr   <= 1'b0;
                                img_base  <= 32'b0;
                                img_w     <= 16'd0;
                                img_h     <= 16'd0;
                                error     <= 1'b0;
                                pix_count <= 32'b0;
                                for (j = 0; j < MAX_W; j = j + 1) begin
                                    line0[j] <= 8'd0;
                                    line1[j] <= 8'd0;
                                    line2[j] <= 8'd0;
                                end
                                state <= S_DONE;
                            end
                            default: begin
                                pcpi_wr <= 1'b0;
                                state   <= S_DONE;
                            end
                        endcase
                    end
                end

                // ------------------------------------------------
                // Row 0 is always a zero border row.
                S_ROW0: begin
                    if (access_done) begin
                        pix_count <= pix_count + 32'd1;
                        out_addr  <= out_addr + 32'd1;
                        if (col == img_w - 16'd1) begin
                            col <= 16'd0;
                            if (img_h == 16'd1)
                                state <= S_DONE;
                            else if (img_h == 16'd2)
                                state <= S_ROWLAST;
                            else begin
                                ld_buf    <= 2'd0;
                                ld_cnt    <= 16'd0;
                                init_done <= 1'b0;
                                state     <= S_LOAD;
                            end
                        end else begin
                            col <= col + 16'd1;
                        end
                    end
                end

                // ------------------------------------------------
                // Load one complete row (W bytes) into ld_buf.
                S_LOAD: begin
                    if (access_done) begin
                        case (ld_buf)
                            2'd0: line0[lidx] <= rd_byte;
                            2'd1: line1[lidx] <= rd_byte;
                            default: line2[lidx] <= rd_byte;
                        endcase

                        row_addr <= row_addr + 32'd1;

                        if (ld_cnt == img_w - 16'd1) begin
                            ld_cnt <= 16'd0;
                            if (!init_done) begin
                                if (ld_buf == 2'd0)
                                    ld_buf <= 2'd1;
                                else if (ld_buf == 2'd1)
                                    ld_buf <= 2'd2;
                                else begin
                                    init_done <= 1'b1;
                                    y         <= 16'd1;
                                    col       <= 16'd0;
                                    state     <= S_COMPUTE;
                                end
                            end else begin
                                y     <= y + 16'd1;
                                col   <= 16'd0;
                                state <= S_COMPUTE;
                            end
                        end else begin
                            ld_cnt <= ld_cnt + 16'd1;
                        end
                    end
                end

                // ------------------------------------------------
                // Produce one full interior row (W bytes, borders zero).
                S_COMPUTE: begin
                    if (access_done) begin
                        pix_count <= pix_count + 32'd1;
                        out_addr  <= out_addr + 32'd1;
                        if (col == img_w - 16'd1) begin
                            col <= 16'd0;
                            if (y == img_h - 16'd2)
                                state <= S_ROWLAST;
                            else
                                state <= S_SHIFT;
                        end else begin
                            col <= col + 16'd1;
                        end
                    end
                end

                // ------------------------------------------------
                // Shift the three row buffers down one row.
                S_SHIFT: begin
                    for (j = 0; j < MAX_W; j = j + 1) begin
                        line0[j] <= line1[j];
                        line1[j] <= line2[j];
                    end
                    ld_buf <= 2'd2;
                    ld_cnt <= 16'd0;
                    state  <= S_LOAD;
                end

                // ------------------------------------------------
                // Last output row is a zero border row.
                S_ROWLAST: begin
                    if (access_done) begin
                        pix_count <= pix_count + 32'd1;
                        out_addr  <= out_addr + 32'd1;
                        if (col == img_w - 16'd1)
                            state <= S_DONE;
                        else
                            col <= col + 16'd1;
                    end
                end

                // ------------------------------------------------
                S_DONE: begin
                    if (!pcpi_valid)
                        state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
