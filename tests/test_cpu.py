"""Unit tests for dasmos.cpu — the abstract Opcode shape.

Covers the renderer-agnostic shape that every CPU plug-in's
instruction table must satisfy: :class:`FlowControl`,
:class:`OperandKind`, the :class:`Opcode` dataclass, the
:class:`AddressingModeMember` protocol.

Concrete CPU plug-ins (NMOS 6502 first) port their own
``Operation`` and ``AddressingMode`` enums and assemble tables of
:class:`Opcode` against this shape.

The test fixtures here use deliberately small fake enums to exercise
the abstract contract without depending on a real CPU plug-in.
"""

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest

from dasmos.cpu import (
    AddressingModeMember,
    Cpu,
    FlowControl,
    Opcode,
    OperandKind,
)


# ---------------------------------------------------------------------------
# Fake CPU enums for testing the abstract shape
# ---------------------------------------------------------------------------


class _FakeOperation(Enum):
    """Stand-in for a real CPU's Operation enum. Members carry
    string values matching the canonical mnemonic form.
    """

    LDA = "lda"
    JMP = "jmp"
    RTS = "rts"


class _FakeAddressingMode(Enum):
    """Stand-in for a real CPU's AddressingMode enum. Each member
    carries an operand length and an OperandKind — the protocol
    the abstract Opcode shape relies on. The ``name`` is the Python
    identifier (IMPLIED, ABSOLUTE, …); renderers translate to
    syntactic form themselves.

    Note the leading string in each value tuple: it makes each
    member's value unique. Without it, Python collapses
    same-value members into aliases (so ``ABSOLUTE`` and ``INDIRECT``,
    which both have ``(2, ADDRESS_16)``, would be the same member).
    Real CPU plug-ins follow the same pattern — see
    :class:`dasmos.ext.cpus.nmos6502.AddressingMode`.
    """

    IMPLIED   = ("implied",   0, OperandKind.NONE)
    IMMEDIATE = ("immediate", 1, OperandKind.IMMEDIATE)
    ABSOLUTE  = ("absolute",  2, OperandKind.ADDRESS_16)
    INDIRECT  = ("indirect",  2, OperandKind.ADDRESS_16)

    def __init__(self, _label: str, operand_length: int, operand_kind: OperandKind):
        self.operand_length = operand_length
        self.operand_kind = operand_kind


class TestAddressingModeAliasingHazard:
    """Regression-pin for the bug uncovered while porting the NMOS
    6502 table: enum members with identical value tuples collapse
    into aliases, silently merging distinct addressing modes.
    """

    def test_absolute_and_indirect_are_distinct(self):
        # The bug had ABSOLUTE and INDIRECT collapse because they
        # had the same (operand_length, operand_kind) tuple. Adding
        # a unique leading label keeps them distinct.
        assert _FakeAddressingMode.ABSOLUTE is not _FakeAddressingMode.INDIRECT
        assert _FakeAddressingMode.ABSOLUTE != _FakeAddressingMode.INDIRECT


# ---------------------------------------------------------------------------
# FlowControl
# ---------------------------------------------------------------------------


class TestFlowControl:

    def test_has_expected_members(self):
        names = {fc.name for fc in FlowControl}
        assert names == {
            "SEQUENTIAL",
            "JUMP",
            "SUBROUTINE_CALL",
            "CONDITIONAL_BRANCH",
            "RETURN",
            "BREAK",
            "UNDEFINED",
        }


# ---------------------------------------------------------------------------
# OperandKind
# ---------------------------------------------------------------------------


class TestOperandKind:

    def test_has_expected_members(self):
        names = {ok.name for ok in OperandKind}
        assert names == {
            "NONE",
            "IMMEDIATE",
            "ADDRESS_8",
            "ADDRESS_16",
            "ADDRESS_16_INDIRECT",
            "RELATIVE_OFFSET",
        }


# ---------------------------------------------------------------------------
# AddressingModeMember protocol
# ---------------------------------------------------------------------------


class TestAddressingModeMember:

    def test_fake_addressing_mode_satisfies_protocol(self):
        # The protocol is documented; each member provides .name,
        # .operand_length, .operand_kind. Verify our fake satisfies it.
        member = _FakeAddressingMode.ABSOLUTE
        assert isinstance(member, AddressingModeMember)
        assert member.name == "ABSOLUTE"
        assert member.operand_length == 2
        assert member.operand_kind is OperandKind.ADDRESS_16


# ---------------------------------------------------------------------------
# Opcode
# ---------------------------------------------------------------------------


class TestOpcode:

    def test_construction(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        assert op.operation is _FakeOperation.LDA
        assert op.addressing_mode is _FakeAddressingMode.ABSOLUTE
        assert op.flow_control is FlowControl.SEQUENTIAL
        assert op.cycles == 0

    def test_cycles_carried(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
            cycles=4,
        )
        assert op.cycles == 4

    def test_operand_length_delegates_to_addressing_mode(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.IMMEDIATE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        assert op.operand_length == 1

    def test_length_includes_opcode_byte(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        # 1 opcode byte + 2 operand bytes (length() is a method,
        # matching the Classification ABC contract).
        assert op.length() == 3

    def test_length_for_implied_is_one(self):
        op = Opcode(
            operation=_FakeOperation.RTS,
            addressing_mode=_FakeAddressingMode.IMPLIED,
            flow_control=FlowControl.RETURN,
        )
        assert op.length() == 1

    def test_is_code_is_true(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        # Opcodes always represent code (overrides the Classification
        # ABC default of False for data subclasses).
        assert op.is_code() is True

    def test_default_mnemonic_returns_operation_value(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        assert op.default_mnemonic() == "lda"

    def test_is_frozen(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        with pytest.raises(FrozenInstanceError):
            op.operation = _FakeOperation.JMP  # type: ignore[misc]

    def test_equality_is_field_based(self):
        a = Opcode(_FakeOperation.LDA, _FakeAddressingMode.ABSOLUTE,
                   FlowControl.SEQUENTIAL)
        b = Opcode(_FakeOperation.LDA, _FakeAddressingMode.ABSOLUTE,
                   FlowControl.SEQUENTIAL)
        c = Opcode(_FakeOperation.LDA, _FakeAddressingMode.IMMEDIATE,
                   FlowControl.SEQUENTIAL)
        assert a == b
        assert a != c

    def test_is_hashable(self):
        a = Opcode(_FakeOperation.LDA, _FakeAddressingMode.ABSOLUTE,
                   FlowControl.SEQUENTIAL)
        b = Opcode(_FakeOperation.LDA, _FakeAddressingMode.ABSOLUTE,
                   FlowControl.SEQUENTIAL)
        assert {a, b} == {a}

    def test_repr_shows_structural_form(self):
        op = Opcode(
            operation=_FakeOperation.LDA,
            addressing_mode=_FakeAddressingMode.ABSOLUTE,
            flow_control=FlowControl.SEQUENTIAL,
        )
        # Renderer-agnostic repr — the structural form, not a guess
        # at the assembler-syntax mnemonic.
        assert "LDA" in repr(op)
        assert "ABSOLUTE" in repr(op)
        assert "SEQUENTIAL" in repr(op)


class TestRendererMnemonicOverride:
    """The point of the renderer-agnostic Opcode shape: a renderer
    that uses different mnemonics from the canonical MOS form
    (e.g. Acorn MASM's ``LDAIM``, ``LDAIY``, ``JMI``) plugs in via
    a per-(operation, addressing_mode) lookup table that falls back
    to ``default_mnemonic`` for unspecified pairs.

    These tests pin the *contract*, not a specific renderer — the
    real MASM renderer is out of scope here.
    """

    def test_default_renderer_uses_canonical_mnemonic(self):
        op = Opcode(_FakeOperation.JMP, _FakeAddressingMode.ABSOLUTE,
                    FlowControl.JUMP)
        # No table override — renderer picks default.
        masm_table: dict = {}
        key = (op.operation, op.addressing_mode)
        chosen = masm_table.get(key, op.default_mnemonic())
        assert chosen == "jmp"

    def test_masm_style_renderer_overrides_per_op_mode_pair(self):
        # The (JMP, INDIRECT) -> "JMI" pin from the second stardot
        # thread: MASM doesn't just suffix the canonical mnemonic;
        # it uses a wholesale different name. A simple suffix-rewriter
        # would be wrong; a (op, mode) lookup table is correct.
        op = Opcode(_FakeOperation.JMP, _FakeAddressingMode.INDIRECT,
                    FlowControl.JUMP)
        masm_table = {
            (_FakeOperation.JMP, _FakeAddressingMode.INDIRECT): "JMI",
            (_FakeOperation.LDA, _FakeAddressingMode.IMMEDIATE): "LDAIM",
        }
        key = (op.operation, op.addressing_mode)
        chosen = masm_table.get(key, op.default_mnemonic())
        assert chosen == "JMI"

    def test_partial_override_table_falls_back_to_default(self):
        # A renderer with a sparse table should fall back to the
        # canonical mnemonic for pairs it doesn't override.
        op = Opcode(_FakeOperation.RTS, _FakeAddressingMode.IMPLIED,
                    FlowControl.RETURN)
        partial_table = {
            (_FakeOperation.JMP, _FakeAddressingMode.INDIRECT): "JMI",
        }
        key = (op.operation, op.addressing_mode)
        chosen = partial_table.get(key, op.default_mnemonic())
        assert chosen == "rts"


# ---------------------------------------------------------------------------
# Cpu base — abstract opcodes() method
# ---------------------------------------------------------------------------


class TestCpuOpcodesAbstract:

    def test_cpu_subclass_must_implement_opcodes(self):
        # Cpu now has both address_space_size AND opcodes() abstract;
        # a subclass that overrides only one cannot be instantiated.
        class _PartialCpu(Cpu):
            @property
            def address_space_size(self) -> int:
                return 0x10000
            # Missing opcodes()
        with pytest.raises(TypeError):
            _PartialCpu(name="partial")  # type: ignore[abstract]

    def test_cpu_subclass_with_both_can_be_instantiated(self):
        class _FullCpu(Cpu):
            @property
            def address_space_size(self) -> int:
                return 0x10000

            def opcodes(self) -> dict[int, Opcode]:
                return {}

        cpu = _FullCpu(name="full")
        assert cpu.name == "full"
        assert cpu.opcodes() == {}
