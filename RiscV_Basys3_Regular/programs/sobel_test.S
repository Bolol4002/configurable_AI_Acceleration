# ============================================================================
# sobel_test.S -- software-vs-hardware Sobel self test
#
# Data memory map (data base = 0x2000):
#   0x2000  image            8x8 bytes
#   0x2040  software output  64 bytes
#   0x2080  hardware output  64 bytes
#   0x2100  results:
#           +0  software cycles
#           +4  software instructions
#           +8  hardware cycles
#           +12 hardware instructions
#           +16 pass flag
#           +20 mismatches
#           +24 pixels
#           +28 magic (0xDEADBEEF)
# ============================================================================

.equ IMG_BASE, 0x2000
.equ OUT_SW,   0x2040
.equ OUT_HW,   0x2080
.equ RESULT,   0x2100
.equ IMG_W,    8
.equ IMG_H,    8
.equ PIXELS,   64

.text
_start:
    # zero 128 bytes covering both output buffers
    li    t0, OUT_SW
    li    t1, 32
zero_loop:
    sw    x0, 0(t0)
    addi  t0, t0, 4
    addi  t1, t1, -1
    bne   t1, x0, zero_loop

    # ---------------- software baseline ----------------
    rdcycle s10
    rdinstret s11

    li    s0, IMG_BASE
    li    s1, OUT_SW
    li    s2, IMG_W
    li    s3, IMG_H
    li    s4, 1                  # y = 1
    li    t4, IMG_W-1            # last interior column
    li    t5, IMG_H-1            # last row
    li    t6, 255                # clamp value

    mv    s8, s0                 # top pointer = row y-1, col 0
    add   s6, s0, s2             # mid pointer = row y,   col 0
    add   s9, s6, s2             # bot pointer = row y+1, col 0
    add   s7, s1, s2             # out pointer = out + y*W
    addi  s7, s7, 1              # start at x = 1

sw_yloop:
    bge   s4, t5, sw_done
    li    s5, 1                  # x = 1

    lbu   a0, 0(s8)
    lbu   a1, 1(s8)
    lbu   a2, 2(s8)
    lbu   a3, 0(s6)
    lbu   a4, 1(s6)
    lbu   a5, 2(s6)
    lbu   a6, 0(s9)
    lbu   a7, 1(s9)
    lbu   t0, 2(s9)

sw_xloop:
    # Gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20)
    sub   t1, a2, a0
    sub   t2, t0, a6
    add   t1, t1, t2
    sub   t2, a5, a3
    slli  t2, t2, 1
    add   t1, t1, t2

    # Gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02)
    sub   t2, a6, a0
    sub   t3, t0, a2
    add   t2, t2, t3
    sub   t3, a7, a1
    slli  t3, t3, 1
    add   t2, t2, t3

    # |Gx| + |Gy|
    srai  t3, t1, 31
    xor   t1, t1, t3
    sub   t1, t1, t3

    srai  t3, t2, 31
    xor   t2, t2, t3
    sub   t2, t2, t3

    add   t1, t1, t2

    bgeu  t6, t1, sw_noclamp
    mv    t1, t6
sw_noclamp:
    sb    t1, 0(s7)

    addi  s5, s5, 1
    addi  s7, s7, 1
    bge   s5, t4, sw_xdone

    # slide the 3x3 window one column to the right
    addi  s8, s8, 1
    addi  s6, s6, 1
    addi  s9, s9, 1
    mv    a0, a1
    mv    a1, a2
    lbu   a2, 2(s8)
    mv    a3, a4
    mv    a4, a5
    lbu   a5, 2(s6)
    mv    a6, a7
    mv    a7, t0
    lbu   t0, 2(s9)
    j     sw_xloop

sw_xdone:
    addi  s7, s7, 2
    addi  s8, s8, 3
    addi  s6, s6, 3
    addi  s9, s9, 3
    addi  s4, s4, 1
    j     sw_yloop

sw_done:
    rdcycle   t1
    sub   s10, t1, s10
    rdinstret t1
    sub   s11, t1, s11
    li    t1, RESULT
    sw    s10, 0(t1)
    sw    s11, 4(t1)

    # ---------------- hardware accelerator ----------------
    rdcycle s10
    rdinstret s11

    li    a0, IMG_BASE
    li    a1, (IMG_H << 16) | IMG_W
    sobel_set a0, a1
    li    a0, OUT_HW
    sobel_run a0, a2

    rdcycle   t1
    sub   s10, t1, s10
    rdinstret t1
    sub   s11, t1, s11
    li    t1, RESULT
    sw    s10, 8(t1)
    sw    s11, 12(t1)

    # ---------------- compare ----------------
    li    t0, OUT_SW
    li    t1, OUT_HW
    li    t2, PIXELS
    li    a0, 0                  # mismatch count
cmp_loop:
    lbu   a2, 0(t0)
    lbu   a3, 0(t1)
    beq   a2, a3, cmp_ok
    addi  a0, a0, 1
cmp_ok:
    addi  t0, t0, 1
    addi  t1, t1, 1
    addi  t2, t2, -1
    bne   t2, x0, cmp_loop

    li    t1, RESULT
    sw    a0, 20(t1)
    li    t2, PIXELS
    sw    t2, 24(t1)
    sltiu t3, a0, 1              # pass = (mismatches == 0)
    sw    t3, 16(t1)
    li    t2, 0xDEADBEEF
    sw    t2, 28(t1)

done:
    j     done
