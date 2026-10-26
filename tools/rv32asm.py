#!/usr/bin/env python3
"""Tiny RV32I + Sobel-PCPI assembler.

This exists only because the development machine does not have a RISC-V
toolchain.  It supports exactly the instructions used by the Sobel firmware
plus a few conveniences.  `li` always expands to two instructions so that
label addresses can be resolved in a single fixed-size first pass.

Usage:
    python3 tools/rv32asm.py programs/sobel_test.S firmware.hex
"""

import re
import sys

REGS = {
    "zero": 0, "x0": 0, "ra": 1, "x1": 1, "sp": 2, "x2": 2,
    "gp": 3, "x3": 3, "tp": 4, "x4": 4, "t0": 5, "x5": 5,
    "t1": 6, "x6": 6, "t2": 7, "x7": 7, "s0": 8, "fp": 8,
    "x8": 8, "s1": 9, "x9": 9,
}
for _i in range(10, 18):
    REGS["a%d" % (_i - 10)] = _i
    REGS["x%d" % _i] = _i
for _i in range(18, 28):
    REGS["s%d" % (_i - 16)] = _i
    REGS["x%d" % _i] = _i
REGS.update({"t3": 28, "x28": 28, "t4": 29, "x29": 29,
             "t5": 30, "x30": 30, "t6": 31, "x31": 31})

CUSTOM_OPCODE = 0b0001011
CUSTOM_FUNCT7 = 0b0100001


def reg(tok):
    tok = tok.strip()
    if tok not in REGS:
        raise ValueError("unknown register %r" % tok)
    return REGS[tok]


def r_type(f7, rs2, rs1, f3, rd, op):
    return ((f7 & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | \
           ((f3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def i_type(imm, rs1, f3, rd, op):
    imm &= 0xFFF
    return (imm << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | \
           ((rd & 0x1F) << 7) | (op & 0x7F)


def s_type(imm, rs2, rs1, f3, op):
    imm &= 0xFFF
    return (((imm >> 5) & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | \
           ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) | \
           ((imm & 0x1F) << 7) | (op & 0x7F)


def b_type(imm, rs2, rs1, f3, op):
    imm &= 0x1FFF
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | \
           ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | \
           ((f3 & 0x7) << 12) | (((imm >> 1) & 0xF) << 8) | \
           (((imm >> 11) & 1) << 7) | (op & 0x7F)


def u_type(imm, rd, op):
    return ((imm >> 12) & 0xFFFFF) << 12 | ((rd & 0x1F) << 7) | (op & 0x7F)


def j_type(imm, rd, op):
    imm &= 0x1FFFFF
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | \
           (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | \
           ((rd & 0x1F) << 7) | (op & 0x7F)


def custom(f3, rd, rs1, rs2):
    return r_type(CUSTOM_FUNCT7, rs2, rs1, f3, rd, CUSTOM_OPCODE)


def eval_expr(expr, symbols):
    expr = expr.strip()

    def repl(m):
        name = m.group(0)
        if name not in symbols:
            raise ValueError("undefined symbol %r in %r" % (name, expr))
        return str(symbols[name])

    return int(eval(re.sub(r"(?<![0-9A-Za-z_])[A-Za-z_]\w*", repl, expr),
                    {"__builtins__": {}}, {}))


def split_operands(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_mem_operand(op):
    m = re.match(r"^(.*)\(\s*([A-Za-z0-9_]+)\s*\)$", op.strip())
    if not m:
        raise ValueError("bad memory operand %r" % op)
    return m.group(1).strip() or "0", m.group(2).strip()


def strip_comment(line):
    for marker in ("#", "//"):
        if marker in line:
            line = line.split(marker, 1)[0]
    return line.strip()


def is_data_directive(mn):
    return mn in (".word", ".byte", ".half", ".ascii", ".asciz")


class Asm:
    def __init__(self):
        self.symbols = {}
        self.items = []       # (kind, payload)

    def scan_line(self, raw, pc):
        line = strip_comment(raw)
        if not line:
            return pc

        m = re.match(r"^([A-Za-z_.]\w*):\s*(.*)$", line)
        if m:
            name = m.group(1)
            self.symbols[name] = pc
            line = m.group(2).strip()
            if not line:
                return pc

        if line.startswith(".equ"):
            body = line[4:].strip()
            name, val = body.split(",", 1)
            self.symbols[name.strip()] = eval_expr(val, self.symbols)
            return pc

        if line.startswith(".text") or line.startswith(".data"):
            return pc

        mnemonic = line.split()[0]
        if mnemonic == "li":
            return pc + 8
        return pc + 4

    def assemble_line(self, raw, pc):
        line = strip_comment(raw)
        if not line:
            return pc, []

        m = re.match(r"^([A-Za-z_.]\w*):\s*(.*)$", line)
        if m:
            line = m.group(2).strip()
            if not line:
                return pc, []

        if line.startswith(".equ") or line.startswith(".text") or \
                line.startswith(".data"):
            return pc, []

        toks = line.replace(",", " , ").split()
        mn = toks[0]
        rest = " ".join(toks[1:])
        ops = split_operands(rest)

        if mn == "li":
            imm = eval_expr(ops[1], self.symbols)
            rd = reg(ops[0])
            hi = ((imm + 0x800) >> 12) & 0xFFFFF
            lo = imm & 0xFFF
            return pc + 8, [u_type(hi << 12, rd, 0x37),
                            i_type(lo, rd, 0, rd, 0x13)]

        if mn == "mv":
            return pc + 4, [i_type(0, reg(ops[1]), 0, reg(ops[0]), 0x13)]

        if mn == "nop":
            return pc + 4, [i_type(0, 0, 0, 0, 0x13)]

        if mn == "j":
            off = eval_expr(ops[0], self.symbols) - pc
            return pc + 4, [j_type(off, 0, 0x6F)]

        if mn == "beqz":
            off = eval_expr(ops[1], self.symbols) - pc
            return pc + 4, [b_type(off, 0, reg(ops[0]), 0, 0x63)]

        if mn == "bnez":
            off = eval_expr(ops[1], self.symbols) - pc
            return pc + 4, [b_type(off, 0, reg(ops[0]), 1, 0x63)]

        r_ops = {
            "add": (0, 0x33), "sub": (0x20, 0x33), "sll": (0, 0x33),
            "slt": (0, 0x33), "sltu": (0, 0x33), "xor": (0, 0x33),
            "srl": (0, 0x33), "sra": (0x20, 0x33), "or": (0, 0x33),
            "and": (0, 0x33),
        }
        if mn in r_ops:
            f7, op = r_ops[mn]
            f3 = {"add": 0, "sub": 0, "sll": 1, "slt": 2, "sltu": 3,
                  "xor": 4, "srl": 5, "sra": 5, "or": 6, "and": 7}[mn]
            return pc + 4, [r_type(f7, reg(ops[2]), reg(ops[1]), f3,
                                   reg(ops[0]), op)]

        i_ops = {
            "addi": (0, 0x13), "slti": (2, 0x13), "sltiu": (3, 0x13),
            "xori": (4, 0x13), "ori": (6, 0x13), "andi": (7, 0x13),
            "slli": (1, 0x13), "srli": (5, 0x13), "srai": (5, 0x13),
        }
        if mn in i_ops:
            f3, op = i_ops[mn]
            imm = eval_expr(ops[2], self.symbols)
            if mn == "srai":
                imm = (0x400 | (imm & 0x1F))
            return pc + 4, [i_type(imm, reg(ops[1]), f3, reg(ops[0]), op)]

        loads = {"lb": (0, 0x03), "lh": (1, 0x03), "lw": (2, 0x03),
                 "lbu": (4, 0x03), "lhu": (5, 0x03)}
        if mn in loads:
            f3, op = loads[mn]
            imm, base = parse_mem_operand(ops[1])
            return pc + 4, [i_type(eval_expr(imm, self.symbols),
                                   reg(base), f3, reg(ops[0]), op)]

        stores = {"sb": (0, 0x23), "sh": (1, 0x23), "sw": (2, 0x23)}
        if mn in stores:
            f3, op = stores[mn]
            imm, base = parse_mem_operand(ops[1])
            return pc + 4, [s_type(eval_expr(imm, self.symbols),
                                   reg(ops[0]), reg(base), f3, op)]

        branches = {"beq": 0, "bne": 1, "blt": 4, "bge": 5,
                    "bltu": 6, "bgeu": 7}
        if mn in branches:
            off = eval_expr(ops[2], self.symbols) - pc
            return pc + 4, [b_type(off, reg(ops[1]), reg(ops[0]),
                                   branches[mn], 0x63)]

        if mn == "lui":
            return pc + 4, [u_type(eval_expr(ops[1], self.symbols) << 12,
                                   reg(ops[0]), 0x37)]
        if mn == "auipc":
            return pc + 4, [u_type(eval_expr(ops[1], self.symbols) << 12,
                                   reg(ops[0]), 0x17)]

        if mn == "jal":
            off = eval_expr(ops[1], self.symbols) - pc
            return pc + 4, [j_type(off, reg(ops[0]), 0x6F)]

        if mn == "jalr":
            if len(ops) == 2 and "(" in ops[1]:
                imm, base = parse_mem_operand(ops[1])
                return pc + 4, [i_type(eval_expr(imm, self.symbols),
                                       reg(base), 0, reg(ops[0]), 0x67)]
            return pc + 4, [i_type(eval_expr(ops[2], self.symbols),
                                   reg(ops[1]), 0, reg(ops[0]), 0x67)]

        if mn == "rdcycle":
            return pc + 4, [i_type(0xC00, 0, 2, reg(ops[0]), 0x73)]
        if mn == "rdinstret":
            return pc + 4, [i_type(0xC02, 0, 2, reg(ops[0]), 0x73)]

        if mn == "sobel_set":
            return pc + 4, [custom(0, 0, reg(ops[0]), reg(ops[1]))]
        if mn == "sobel_run":
            return pc + 4, [custom(1, reg(ops[1]), reg(ops[0]), 0)]
        if mn == "sobel_status":
            return pc + 4, [custom(2, reg(ops[0]), 0, 0)]
        if mn == "sobel_reset":
            return pc + 4, [custom(3, 0, 0, 0)]

        raise ValueError("unsupported instruction: %r" % line)


def assemble(path):
    with open(path) as f:
        lines = f.readlines()

    a = Asm()
    pc = 0
    for line in lines:
        pc = a.scan_line(line, pc)

    words = []
    pc = 0
    for line in lines:
        pc, ws = a.assemble_line(line, pc)
        words.extend(ws)
    return words


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    words = assemble(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        for w in words:
            f.write("%08x\n" % (w & 0xFFFFFFFF))
        for _ in range(len(words), 256):
            f.write("00000013\n")       # NOP padding for fixed-size BRAM init
    print("wrote %d instructions (%d bytes) to %s" %
          (len(words), len(words) * 4, sys.argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
