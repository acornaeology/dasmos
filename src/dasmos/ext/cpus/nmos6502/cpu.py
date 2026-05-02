"""NMOS 6502 — instruction set, addressing modes, and the Cpu plug-in.

The classic MOS 6502 (also known as the 6502A in some Acorn
contexts) — the processor at the heart of the BBC Micro, the Acorn
Electron, the Commodore 64 and many others. This module ports the
opcode table from py8dis's ``cpu6502.py`` (1,495 lines) into the
dasmos plug-in shape:

- :class:`Operation` — enum of the 56 distinct mnemonics (canonical
  lowercase MOS form as the value).
- :class:`AddressingMode` — enum of the 13 addressing modes the NMOS
  6502 supports; each member carries its operand length (in bytes)
  and operand kind (immediate / address / relative offset / none).
- :data:`OPCODES` — the 151-entry instruction table mapping opcode
  byte to :class:`~dasmos.cpu.Opcode`. Bytes not in the dict are
  *undocumented* opcodes and are deliberately omitted (matching
  py8dis); the trace engine treats them as undefined.
- :class:`Nmos6502Cpu` — the plug-in class registered under the
  ``dasmos.cpu`` entry-point namespace.

**Renderer-agnostic.** This module makes no commitment to a
particular assembler-syntax mnemonic for any opcode. ``Operation``
member values are the canonical lowercase MOS form (``"lda"``,
``"jsr"``, …); renderers that follow that convention (Beebasm,
acme, ca65) get them for free via :meth:`Opcode.default_mnemonic`.
Renderers that use a different convention (e.g. Acorn MASM's
``LDAIM`` / ``LDAIY`` / ``JMI``) provide a per-pair lookup table.
See ``docs/design/decisions.md`` D-021.
"""

from enum import Enum, unique

from dasmos.cpu import (
    AddressingModeMember,
    Cpu,
    FlowControl,
    Opcode,
    OperandKind,
)


class Operation(Enum):
    """The 56 NMOS 6502 mnemonics. Member ``value`` is the canonical
    lowercase MOS form.
    """

    ADC = "adc"
    AND = "and"
    ASL = "asl"
    BCC = "bcc"
    BCS = "bcs"
    BEQ = "beq"
    BIT = "bit"
    BMI = "bmi"
    BNE = "bne"
    BPL = "bpl"
    BRK = "brk"
    BVC = "bvc"
    BVS = "bvs"
    CLC = "clc"
    CLD = "cld"
    CLI = "cli"
    CLV = "clv"
    CMP = "cmp"
    CPX = "cpx"
    CPY = "cpy"
    DEC = "dec"
    DEX = "dex"
    DEY = "dey"
    EOR = "eor"
    INC = "inc"
    INX = "inx"
    INY = "iny"
    JMP = "jmp"
    JSR = "jsr"
    LDA = "lda"
    LDX = "ldx"
    LDY = "ldy"
    LSR = "lsr"
    NOP = "nop"
    ORA = "ora"
    PHA = "pha"
    PHP = "php"
    PLA = "pla"
    PLP = "plp"
    ROL = "rol"
    ROR = "ror"
    RTI = "rti"
    RTS = "rts"
    SBC = "sbc"
    SEC = "sec"
    SED = "sed"
    SEI = "sei"
    STA = "sta"
    STX = "stx"
    STY = "sty"
    TAX = "tax"
    TAY = "tay"
    TSX = "tsx"
    TXA = "txa"
    TXS = "txs"
    TYA = "tya"


@unique
class AddressingMode(Enum):
    """The 13 addressing modes available on the NMOS 6502.

    Each member's ``value`` is a ``(label, operand_length, operand_kind)``
    triple; the leading ``label`` is what makes each member's value
    unique (otherwise Python's :class:`enum.Enum` collapses members
    with identical values into aliases — multiple modes share the
    same operand length and kind, so ABSOLUTE / ABSOLUTE_X / ABSOLUTE_Y
    / INDIRECT all otherwise look identical). The ``@unique`` decorator
    is belt-and-braces to catch that mistake at class-creation time.
    """

    IMPLIED            = ("implied",            0, OperandKind.NONE)
    ACCUMULATOR        = ("accumulator",        0, OperandKind.NONE)
    IMMEDIATE          = ("immediate",          1, OperandKind.IMMEDIATE)
    ZERO_PAGE          = ("zero_page",          1, OperandKind.ADDRESS_8)
    ZERO_PAGE_X        = ("zero_page_x",        1, OperandKind.ADDRESS_8)
    ZERO_PAGE_Y        = ("zero_page_y",        1, OperandKind.ADDRESS_8)
    ABSOLUTE           = ("absolute",           2, OperandKind.ADDRESS_16)
    ABSOLUTE_X         = ("absolute_x",         2, OperandKind.ADDRESS_16)
    ABSOLUTE_Y         = ("absolute_y",         2, OperandKind.ADDRESS_16)
    INDIRECT           = ("indirect",           2, OperandKind.ADDRESS_16_INDIRECT)   # JMP (addr)
    INDEXED_INDIRECT   = ("indexed_indirect",   1, OperandKind.ADDRESS_8)    # (zp,X)
    INDIRECT_INDEXED   = ("indirect_indexed",   1, OperandKind.ADDRESS_8)    # (zp),Y
    RELATIVE           = ("relative",           1, OperandKind.RELATIVE_OFFSET)  # branches

    def __init__(self, _label: str, operand_length: int, operand_kind: OperandKind):
        # _label is only present to disambiguate the value tuples — see class docstring.
        self.operand_length = operand_length
        self.operand_kind = operand_kind


# ---------------------------------------------------------------------------
# Instruction table
# ---------------------------------------------------------------------------
#
# 151 entries — every documented NMOS 6502 opcode. The undocumented
# opcodes (the so-called "illegal" ones) are deliberately omitted,
# matching py8dis's stance. Bytes not in this dict are treated as
# undefined by the trace engine.
#
# The table was generated mechanically from py8dis/cpu6502.py via the
# script in commit message; cycle counts come from that table where
# they were given as plain integers (cycle counts with extra-cycle
# letters like "4f" and "5b" are recorded as 0 here pending a proper
# cycle model — see TODO at end of module).
#
# CPU-state-update side effects (which py8dis's per-opcode `update=`
# callbacks model) are not in the table — those land with the
# CpuState port (post-trace label-naming heuristics, planned for the
# orchestration trace-loop port).

OPCODES: dict[int, Opcode] = {
    0x00: Opcode(Operation.BRK, AddressingMode.IMPLIED,           FlowControl.BREAK,              cycles=7),
    0x01: Opcode(Operation.ORA, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0x05: Opcode(Operation.ORA, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x06: Opcode(Operation.ASL, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0x08: Opcode(Operation.PHP, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=3),
    0x09: Opcode(Operation.ORA, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0x0a: Opcode(Operation.ASL, AddressingMode.ACCUMULATOR,       FlowControl.SEQUENTIAL,         cycles=2),
    0x0d: Opcode(Operation.ORA, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x0e: Opcode(Operation.ASL, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0x10: Opcode(Operation.BPL, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0x11: Opcode(Operation.ORA, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0x15: Opcode(Operation.ORA, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x16: Opcode(Operation.ASL, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0x18: Opcode(Operation.CLC, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x19: Opcode(Operation.ORA, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0x1d: Opcode(Operation.ORA, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0x1e: Opcode(Operation.ASL, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
    0x20: Opcode(Operation.JSR, AddressingMode.ABSOLUTE,          FlowControl.SUBROUTINE_CALL,    cycles=6),
    0x21: Opcode(Operation.AND, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0x24: Opcode(Operation.BIT, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x25: Opcode(Operation.AND, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x26: Opcode(Operation.ROL, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0x28: Opcode(Operation.PLP, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=4),
    0x29: Opcode(Operation.AND, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0x2a: Opcode(Operation.ROL, AddressingMode.ACCUMULATOR,       FlowControl.SEQUENTIAL,         cycles=2),
    0x2c: Opcode(Operation.BIT, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x2d: Opcode(Operation.AND, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x2e: Opcode(Operation.ROL, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0x30: Opcode(Operation.BMI, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0x31: Opcode(Operation.AND, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0x35: Opcode(Operation.AND, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x36: Opcode(Operation.ROL, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0x38: Opcode(Operation.SEC, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x39: Opcode(Operation.AND, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0x3d: Opcode(Operation.AND, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0x3e: Opcode(Operation.ROL, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
    0x40: Opcode(Operation.RTI, AddressingMode.IMPLIED,           FlowControl.RETURN,             cycles=6),
    0x41: Opcode(Operation.EOR, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0x45: Opcode(Operation.EOR, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x46: Opcode(Operation.LSR, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0x48: Opcode(Operation.PHA, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=3),
    0x49: Opcode(Operation.EOR, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0x4a: Opcode(Operation.LSR, AddressingMode.ACCUMULATOR,       FlowControl.SEQUENTIAL,         cycles=2),
    0x4c: Opcode(Operation.JMP, AddressingMode.ABSOLUTE,          FlowControl.JUMP,               cycles=3),
    0x4d: Opcode(Operation.EOR, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x4e: Opcode(Operation.LSR, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0x50: Opcode(Operation.BVC, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0x51: Opcode(Operation.EOR, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0x55: Opcode(Operation.EOR, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x56: Opcode(Operation.LSR, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0x58: Opcode(Operation.CLI, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x59: Opcode(Operation.EOR, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0x5d: Opcode(Operation.EOR, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0x5e: Opcode(Operation.LSR, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
    0x60: Opcode(Operation.RTS, AddressingMode.IMPLIED,           FlowControl.RETURN,             cycles=6),
    0x61: Opcode(Operation.ADC, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0x65: Opcode(Operation.ADC, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x66: Opcode(Operation.ROR, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0x68: Opcode(Operation.PLA, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=4),
    0x69: Opcode(Operation.ADC, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0x6a: Opcode(Operation.ROR, AddressingMode.ACCUMULATOR,       FlowControl.SEQUENTIAL,         cycles=2),
    0x6c: Opcode(Operation.JMP, AddressingMode.INDIRECT,          FlowControl.JUMP,               cycles=5),
    0x6d: Opcode(Operation.ADC, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x6e: Opcode(Operation.ROR, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0x70: Opcode(Operation.BVS, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0x71: Opcode(Operation.ADC, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0x75: Opcode(Operation.ADC, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x76: Opcode(Operation.ROR, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0x78: Opcode(Operation.SEI, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x79: Opcode(Operation.ADC, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0x7d: Opcode(Operation.ADC, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0x7e: Opcode(Operation.ROR, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
    0x81: Opcode(Operation.STA, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0x84: Opcode(Operation.STY, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x85: Opcode(Operation.STA, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x86: Opcode(Operation.STX, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0x88: Opcode(Operation.DEY, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x8a: Opcode(Operation.TXA, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x8c: Opcode(Operation.STY, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x8d: Opcode(Operation.STA, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x8e: Opcode(Operation.STX, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0x90: Opcode(Operation.BCC, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0x91: Opcode(Operation.STA, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL,         cycles=6),
    0x94: Opcode(Operation.STY, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x95: Opcode(Operation.STA, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0x96: Opcode(Operation.STX, AddressingMode.ZERO_PAGE_Y,       FlowControl.SEQUENTIAL,         cycles=4),
    0x98: Opcode(Operation.TYA, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x99: Opcode(Operation.STA, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL,         cycles=5),
    0x9a: Opcode(Operation.TXS, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0x9d: Opcode(Operation.STA, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=5),
    0xa0: Opcode(Operation.LDY, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xa1: Opcode(Operation.LDA, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0xa2: Opcode(Operation.LDX, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xa4: Opcode(Operation.LDY, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xa5: Opcode(Operation.LDA, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xa6: Opcode(Operation.LDX, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xa8: Opcode(Operation.TAY, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xa9: Opcode(Operation.LDA, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xaa: Opcode(Operation.TAX, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xac: Opcode(Operation.LDY, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xad: Opcode(Operation.LDA, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xae: Opcode(Operation.LDX, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xb0: Opcode(Operation.BCS, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0xb1: Opcode(Operation.LDA, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0xb4: Opcode(Operation.LDY, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0xb5: Opcode(Operation.LDA, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0xb6: Opcode(Operation.LDX, AddressingMode.ZERO_PAGE_Y,       FlowControl.SEQUENTIAL,         cycles=4),
    0xb8: Opcode(Operation.CLV, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xb9: Opcode(Operation.LDA, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0xba: Opcode(Operation.TSX, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xbc: Opcode(Operation.LDY, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0xbd: Opcode(Operation.LDA, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0xbe: Opcode(Operation.LDX, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0xc0: Opcode(Operation.CPY, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xc1: Opcode(Operation.CMP, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0xc4: Opcode(Operation.CPY, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xc5: Opcode(Operation.CMP, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xc6: Opcode(Operation.DEC, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0xc8: Opcode(Operation.INY, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xc9: Opcode(Operation.CMP, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xca: Opcode(Operation.DEX, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xcc: Opcode(Operation.CPY, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xcd: Opcode(Operation.CMP, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xce: Opcode(Operation.DEC, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0xd0: Opcode(Operation.BNE, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0xd1: Opcode(Operation.CMP, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0xd5: Opcode(Operation.CMP, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0xd6: Opcode(Operation.DEC, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0xd8: Opcode(Operation.CLD, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xd9: Opcode(Operation.CMP, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0xdd: Opcode(Operation.CMP, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0xde: Opcode(Operation.DEC, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
    0xe0: Opcode(Operation.CPX, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xe1: Opcode(Operation.SBC, AddressingMode.INDEXED_INDIRECT,  FlowControl.SEQUENTIAL,         cycles=6),
    0xe4: Opcode(Operation.CPX, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xe5: Opcode(Operation.SBC, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=3),
    0xe6: Opcode(Operation.INC, AddressingMode.ZERO_PAGE,         FlowControl.SEQUENTIAL,         cycles=5),
    0xe8: Opcode(Operation.INX, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xe9: Opcode(Operation.SBC, AddressingMode.IMMEDIATE,         FlowControl.SEQUENTIAL,         cycles=2),
    0xea: Opcode(Operation.NOP, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xec: Opcode(Operation.CPX, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xed: Opcode(Operation.SBC, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=4),
    0xee: Opcode(Operation.INC, AddressingMode.ABSOLUTE,          FlowControl.SEQUENTIAL,         cycles=6),
    0xf0: Opcode(Operation.BEQ, AddressingMode.RELATIVE,          FlowControl.CONDITIONAL_BRANCH),
    0xf1: Opcode(Operation.SBC, AddressingMode.INDIRECT_INDEXED,  FlowControl.SEQUENTIAL),
    0xf5: Opcode(Operation.SBC, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=4),
    0xf6: Opcode(Operation.INC, AddressingMode.ZERO_PAGE_X,       FlowControl.SEQUENTIAL,         cycles=6),
    0xf8: Opcode(Operation.SED, AddressingMode.IMPLIED,           FlowControl.SEQUENTIAL,         cycles=2),
    0xf9: Opcode(Operation.SBC, AddressingMode.ABSOLUTE_Y,        FlowControl.SEQUENTIAL),
    0xfd: Opcode(Operation.SBC, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL),
    0xfe: Opcode(Operation.INC, AddressingMode.ABSOLUTE_X,        FlowControl.SEQUENTIAL,         cycles=7),
}

# TODO: Page-crossing cycle penalties (the "f", "a", "b" suffixes in
# py8dis's cycle counts) are dropped — opcodes with them carry
# ``cycles=0``. Add a proper cycle model when an upstream consumer
# actually needs cycle accuracy.

# TODO: Per-opcode CPU-state-update side effects (py8dis's `update=`
# callbacks: `update_clear_nza`, `update_ORA_immediate`, etc.) land
# with the CpuState port — they're for post-trace label-naming
# heuristics and aren't needed by the trace loop itself.


class Nmos6502Cpu(Cpu):
    """The classic NMOS 6502.

    16-bit address space; the 56 documented mnemonics across 13
    addressing modes; 151 documented opcodes (undocumented opcodes
    deliberately omitted).
    """

    def __init__(self, name: str = "nmos6502", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def address_space_size(self) -> int:
        return 0x10000

    def opcodes(self) -> dict[int, Opcode]:
        return OPCODES
