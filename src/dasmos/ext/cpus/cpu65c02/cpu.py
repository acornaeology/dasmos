"""CMOS 65C02 — instruction set and Cpu plug-in.

The 65C02 (often "65SC02" or "WDC65C02" in different vendors' silicon)
is the CMOS evolution of the NMOS 6502. From dasmos's perspective it
is a strict superset of :mod:`dasmos.ext.cpus.cpu6502`:

- 8 new mnemonics: BRA, PHX, PHY, PLX, PLY, STZ, TRB, TSB.
- 2 new addressing modes: ``(zp)`` indirect and ``(addr,X)`` indirect
  (only used by ``JMP (addr,X)``).
- 27 new opcode bytes wiring those into the table.
- A handful of NMOS opcodes that pick up new addressing-mode variants
  (e.g. ``BIT #imm``).

Everything else — addressing modes, mnemonics, flow-control behaviour,
the trace loop — is reused unchanged from the NMOS plug-in. We do
not implement the WDC-specific ``RMB`` / ``SMB`` / ``BBR`` / ``BBS``
instructions: the Acorn 65C02-target ROMs (Tube Client, ANFS) don't
use them.

Undefined opcodes are deliberately left out. On real 65C02 silicon
they are NOPs of varying lengths, but treating arbitrary bytes as
NOPs blurs the trace-vs-data boundary; better to terminate the trace
path cleanly.
"""

from enum import Enum, unique

from dasmos.cpu import (
    Cpu,
    FlowControl,
    Opcode,
    OperandKind,
)
from dasmos.ext.cpus.cpu6502.cpu import (
    OPCODES as NMOS_OPCODES,
    AddressingMode as NmosAddressingMode,
    Operation as NmosOperation,
)

# Canonical registered name of this CPU plug-in. Kept in sync with
# the entry-point key in pyproject.toml under ``[project.entry-points
# ."dasmos.cpu"]``. The lookup is case-insensitive at the dasmos
# layer, but ``CPU_NAME`` is the exact form shown by
# ``dasmos list-cpus`` and emitted in JSON output.
CPU_NAME = "65C02"


class Operation(Enum):
    """The 8 mnemonics 65C02 adds to NMOS 6502.

    The enum is deliberately *additive* — the 56 NMOS mnemonics stay
    in :class:`dasmos.ext.cpus.cpu6502.cpu.Operation` and are reused
    via the :data:`OPCODES` table below. Renderers compare on
    ``operation.value`` (the canonical lowercase mnemonic), so the
    fact that two enum classes are involved is invisible at the
    rendering layer.
    """

    BRA = "bra"
    PHX = "phx"
    PHY = "phy"
    PLX = "plx"
    PLY = "ply"
    STZ = "stz"
    TRB = "trb"
    TSB = "tsb"


@unique
class AddressingMode(Enum):
    """The 2 addressing modes 65C02 adds to NMOS 6502.

    NMOS modes (IMPLIED, ZERO_PAGE, ABSOLUTE_X, …) come from
    :class:`dasmos.ext.cpus.cpu6502.cpu.AddressingMode`; only the
    new ones live here. As with :class:`Operation` the renderer
    dispatches on ``mode.name`` / ``operand_kind`` so split enums
    are transparent downstream.
    """

    ZP_INDIRECT          = ("zp_indirect",          1, OperandKind.ADDRESS_8)            # (zp)
    ABSOLUTE_INDIRECT_X  = ("absolute_indirect_x",  2, OperandKind.ADDRESS_16_INDIRECT)  # JMP (addr,X)

    def __init__(self, _label: str, operand_length: int, operand_kind: OperandKind):
        self.operand_length = operand_length
        self.operand_kind = operand_kind


# ---------------------------------------------------------------------------
# Instruction table
# ---------------------------------------------------------------------------

# Start from the 151 NMOS entries (Opcode instances are immutable
# dataclasses — sharing them across CPU dicts is safe) and overlay
# the 65C02-specific bytes.
OPCODES: dict[int, Opcode] = dict(NMOS_OPCODES)


def _add(byte: int, op: Enum, mode: Enum, flow: FlowControl, *, cycles: int = 0) -> None:
    """Local convenience: add (or override) one entry."""
    OPCODES[byte] = Opcode(op, mode, flow, cycles=cycles)


# 27 new opcode bytes wiring the new mnemonics + new modes into the
# table, ordered by opcode value.
_add(0x04, Operation.TSB,    NmosAddressingMode.ZERO_PAGE,        FlowControl.SEQUENTIAL,         cycles=5)
_add(0x0c, Operation.TSB,    NmosAddressingMode.ABSOLUTE,         FlowControl.SEQUENTIAL,         cycles=6)
_add(0x12, NmosOperation.ORA, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0x14, Operation.TRB,    NmosAddressingMode.ZERO_PAGE,        FlowControl.SEQUENTIAL,         cycles=5)
_add(0x1a, NmosOperation.INC, NmosAddressingMode.ACCUMULATOR,     FlowControl.SEQUENTIAL,         cycles=2)
_add(0x1c, Operation.TRB,    NmosAddressingMode.ABSOLUTE,         FlowControl.SEQUENTIAL,         cycles=6)
_add(0x32, NmosOperation.AND, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0x34, NmosOperation.BIT, NmosAddressingMode.ZERO_PAGE_X,     FlowControl.SEQUENTIAL,         cycles=4)
_add(0x3a, NmosOperation.DEC, NmosAddressingMode.ACCUMULATOR,     FlowControl.SEQUENTIAL,         cycles=2)
_add(0x3c, NmosOperation.BIT, NmosAddressingMode.ABSOLUTE_X,      FlowControl.SEQUENTIAL,         cycles=4)
_add(0x52, NmosOperation.EOR, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0x5a, Operation.PHY,    NmosAddressingMode.IMPLIED,          FlowControl.SEQUENTIAL,         cycles=3)
_add(0x64, Operation.STZ,    NmosAddressingMode.ZERO_PAGE,        FlowControl.SEQUENTIAL,         cycles=3)
_add(0x72, NmosOperation.ADC, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0x74, Operation.STZ,    NmosAddressingMode.ZERO_PAGE_X,      FlowControl.SEQUENTIAL,         cycles=4)
_add(0x7a, Operation.PLY,    NmosAddressingMode.IMPLIED,          FlowControl.SEQUENTIAL,         cycles=4)
_add(0x7c, NmosOperation.JMP, AddressingMode.ABSOLUTE_INDIRECT_X, FlowControl.JUMP,               cycles=6)
_add(0x80, Operation.BRA,    NmosAddressingMode.RELATIVE,         FlowControl.JUMP,               cycles=3)
_add(0x89, NmosOperation.BIT, NmosAddressingMode.IMMEDIATE,       FlowControl.SEQUENTIAL,         cycles=2)
_add(0x92, NmosOperation.STA, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0x9c, Operation.STZ,    NmosAddressingMode.ABSOLUTE,         FlowControl.SEQUENTIAL,         cycles=4)
_add(0x9e, Operation.STZ,    NmosAddressingMode.ABSOLUTE_X,       FlowControl.SEQUENTIAL,         cycles=5)
_add(0xb2, NmosOperation.LDA, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0xd2, NmosOperation.CMP, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0xda, Operation.PHX,    NmosAddressingMode.IMPLIED,          FlowControl.SEQUENTIAL,         cycles=3)
_add(0xf2, NmosOperation.SBC, AddressingMode.ZP_INDIRECT,         FlowControl.SEQUENTIAL,         cycles=5)
_add(0xfa, Operation.PLX,    NmosAddressingMode.IMPLIED,          FlowControl.SEQUENTIAL,         cycles=4)


del _add


class Cmos65C02Cpu(Cpu):
    """The CMOS 65C02 — NMOS 6502 superset with 8 new mnemonics, 2 new
    addressing modes and 27 new opcode bytes.

    Doesn't model the WDC-specific RMB / SMB / BBR / BBS bit-test
    instructions; they're not used by Acorn's 65C02-target ROMs.
    """

    def __init__(self, name: str = CPU_NAME, **kwargs):
        super().__init__(name=name, **kwargs)

    @classmethod
    def brief_description(cls) -> str:
        # The docstring's first line ("The CMOS 65C02 — NMOS 6502
        # superset with 8 new mnemonics, 2 new addressing modes and
        # 27 new opcode bytes.") is too long for the list-cpus
        # table column. Pithier override here.
        return "The CMOS 65C02 — 8 extra mnemonics on top of the 6502."

    @property
    def address_space_size(self) -> int:
        return 0x10000

    def opcodes(self) -> dict[int, Opcode]:
        return OPCODES
