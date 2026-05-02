"""Unit tests for dasmos.disassembler and dasmos.ir.

Test-first walk through the orchestration skeleton: construction,
per-instance manager isolation, the flat driver-script methods that
delegate to the manager classes, the one-shot ``disassemble()`` call,
and the IR's read-only-by-convention exposure of the model.

The trace loop and the leftover-classification pass are not in the
skeleton — they land with the first concrete CPU plug-in (task #18
continues from here).
"""

import pytest

from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.memory import BinaryAddr, RuntimeAddr
from dasmos.core.move import BASE_MOVE_ID
from dasmos.cpu import Cpu, Opcode
from dasmos.disassembler import Disassembler, DisassemblerError
from dasmos.ir import IntermediateRepresentation
from dasmos.output import TextOutput
from dasmos.renderer import Renderer


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _StubCpu(Cpu):
    """A bare-bones Cpu subclass exposing only what the orchestration
    skeleton currently consults: the address-space size and an empty
    opcode table (the trace loop is added in a later port).
    """

    def __init__(self, name: str = "stub", address_space_size: int = 0x10000):
        super().__init__(name=name)
        self._size = address_space_size

    @property
    def address_space_size(self) -> int:
        return self._size

    def opcodes(self) -> dict[int, Opcode]:
        return {}


class _StubRenderer(Renderer):
    """Minimal renderer for testing IR.render() dispatch."""

    def render(self, ir):
        return TextOutput(f"rendered cpu={ir.cpu.name}")


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:

    def test_takes_a_cpu_instance(self):
        cpu = _StubCpu(name="my_cpu")
        d = Disassembler(cpu=cpu)
        assert d.cpu is cpu
        assert d.cpu.name == "my_cpu"

    def test_creates_managers_sized_to_cpu_address_space(self):
        cpu = _StubCpu(address_space_size=0x20000)
        d = Disassembler(cpu=cpu)
        assert d.memory.address_space_size == 0x20000
        assert d.moves.address_space_size == 0x20000

    def test_default_address_space_for_16_bit_cpu(self):
        cpu = _StubCpu()  # default 0x10000
        d = Disassembler(cpu=cpu)
        assert d.memory.address_space_size == 0x10000

    def test_two_disassemblers_have_independent_state(self):
        # The justification for the whole rewrite — module-level state
        # in py8dis prevented this property.
        d1 = Disassembler(cpu=_StubCpu(name="a"))
        d2 = Disassembler(cpu=_StubCpu(name="b"))
        assert d1.memory is not d2.memory
        assert d1.moves is not d2.moves
        assert d1.labels is not d2.labels
        assert d1.classifications is not d2.classifications
        assert d1.expressions is not d2.expressions
        assert d1.config is not d2.config

    def test_factory_with_explicit_instance(self):
        cpu = _StubCpu(name="explicit")
        d = Disassembler.create(cpu=cpu)
        assert d.cpu is cpu

    def test_factory_with_string_requires_registered_plugin(self):
        # No real CPU plug-ins are registered yet (cpu6502 etc. land
        # in task #16). The string lookup raises until that's done.
        from dasmos.cpu import CpuExtensionError
        with pytest.raises(CpuExtensionError):
            Disassembler.create(cpu="nmos6502")


# ---------------------------------------------------------------------------
# Driver-script setup methods (delegating to managers)
# ---------------------------------------------------------------------------


class TestSetupDelegation:

    def test_load_delegates_to_memory(self, tmp_path):
        binary = tmp_path / "a.bin"
        binary.write_bytes(b"\x12\x34\x56\x78")
        d = Disassembler(cpu=_StubCpu())
        start, end = d.load(binary, 0x8000)
        assert start == BinaryAddr(0x8000)
        assert end == BinaryAddr(0x8004)
        assert d.memory.get_u8(0x8000) == 0x12

    def test_load_with_md5_validation(self, tmp_path):
        binary = tmp_path / "a.bin"
        binary.write_bytes(b"\x00" * 16)
        d = Disassembler(cpu=_StubCpu())
        d.load(binary, 0x8000, md5sum="4ae71336e44bf9bf79d2752e234818a5")

    def test_add_move_delegates_to_move_manager(self):
        d = Disassembler(cpu=_StubCpu())
        move_id = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert move_id == 1  # BASE_MOVE_ID + 1
        assert d.moves.is_valid_move_id(move_id)

    def test_using_move_is_a_context_manager(self):
        d = Disassembler(cpu=_StubCpu())
        move_id = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert d.moves.active_move_ids == []
        with d.using_move(move_id):
            assert d.moves.active_move_ids == [move_id]
        assert d.moves.active_move_ids == []


# ---------------------------------------------------------------------------
# Driver-script labelling methods
# ---------------------------------------------------------------------------


class TestLabelDelegation:

    def test_label_creates_a_label(self):
        d = Disassembler(cpu=_StubCpu())
        d.label(0x8000, "start")
        label = d.labels.get_label(0x8000)
        assert label is not None
        assert "start" in label.all_names()

    def test_label_carries_metadata(self):
        d = Disassembler(cpu=_StubCpu())
        d.label(0x8000, "start", description="entry point", length=4)
        label = d.labels.get_label(0x8000)
        assert label.description == "entry point"
        assert label.length == 4

    def test_local_label(self):
        d = Disassembler(cpu=_StubCpu())
        d.local_label(0x8000, "loop", 0x8000, 0x8010)
        label = d.labels.get_label(0x8000)
        assert label.local_labels[BASE_MOVE_ID][0].name == "loop"

    def test_expr_label(self):
        d = Disassembler(cpu=_StubCpu())
        d.expr_label(0x8000, "base + 4")
        label = d.labels.get_label(0x8000)
        assert "base + 4" in label.expressions[BASE_MOVE_ID]


# ---------------------------------------------------------------------------
# Driver-script classification methods
# ---------------------------------------------------------------------------


class TestClassificationDelegation:

    def test_byte_adds_byte_classification(self):
        d = Disassembler(cpu=_StubCpu())
        d.byte(0x8000, 4)
        c = d.classifications.get_classification(0x8000)
        assert isinstance(c, Byte)
        assert c.length() == 4

    def test_word_adds_word_classification(self):
        d = Disassembler(cpu=_StubCpu())
        d.word(0x8000, 4)
        c = d.classifications.get_classification(0x8000)
        assert isinstance(c, Word)
        assert c.length() == 4

    def test_fill_adds_fill_classification(self):
        d = Disassembler(cpu=_StubCpu())
        d.fill(0x8000, 16, 0xFF)
        c = d.classifications.get_classification(0x8000)
        assert isinstance(c, Fill)
        assert c.length() == 16
        assert c.value() == 0xFF

    def test_string_adds_string_classification(self):
        d = Disassembler(cpu=_StubCpu())
        d.string(0x8000, 8)
        c = d.classifications.get_classification(0x8000)
        assert isinstance(c, String)
        assert c.length() == 8


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


class TestExpressions:

    def test_expr_records_per_address(self):
        d = Disassembler(cpu=_StubCpu())
        d.expr(0x8001, "num_lives + 1")
        assert d.expressions.get(0x8001) == "num_lives + 1"


# ---------------------------------------------------------------------------
# disassemble() — the one-shot trace + classify call
# ---------------------------------------------------------------------------


class TestDisassemble:

    def test_returns_an_ir(self):
        d = Disassembler(cpu=_StubCpu())
        ir = d.disassemble()
        assert isinstance(ir, IntermediateRepresentation)

    def test_can_only_be_called_once(self):
        d = Disassembler(cpu=_StubCpu())
        d.disassemble()
        with pytest.raises(DisassemblerError, match="already"):
            d.disassemble()

    def test_post_disassemble_setup_calls_raise(self):
        d = Disassembler(cpu=_StubCpu())
        d.disassemble()
        with pytest.raises(DisassemblerError, match="frozen"):
            d.label(0x8000, "too_late")
        with pytest.raises(DisassemblerError, match="frozen"):
            d.byte(0x8000)
        with pytest.raises(DisassemblerError, match="frozen"):
            d.expr(0x8000, "expr")


# ---------------------------------------------------------------------------
# IR — read-only view of the model
# ---------------------------------------------------------------------------


class TestIR:

    def test_exposes_cpu(self):
        cpu = _StubCpu(name="my_cpu")
        d = Disassembler(cpu=cpu)
        ir = d.disassemble()
        assert ir.cpu is cpu

    def test_exposes_managers(self):
        d = Disassembler(cpu=_StubCpu())
        ir = d.disassemble()
        assert ir.memory is d.memory
        assert ir.moves is d.moves
        assert ir.labels is d.labels
        assert ir.classifications is d.classifications
        assert ir.expressions is d.expressions
        assert ir.config is d.config

    def test_reflects_user_registrations(self):
        d = Disassembler(cpu=_StubCpu())
        d.label(0x8000, "start")
        d.byte(0x8000, 1)
        ir = d.disassemble()
        assert ir.labels.get_label(0x8000) is not None
        assert ir.classifications.is_classified(0x8000)

    def test_render_with_renderer_instance(self):
        d = Disassembler(cpu=_StubCpu(name="rendered_cpu"))
        ir = d.disassemble()
        renderer = _StubRenderer(name="stub")
        out = ir.render(renderer)
        assert isinstance(out, TextOutput)
        assert "rendered_cpu" in str(out)

    def test_render_with_string_requires_registered_plugin(self):
        # No real renderers registered yet (beebasm etc. land in #17).
        d = Disassembler(cpu=_StubCpu())
        ir = d.disassemble()
        from dasmos.renderer import RendererExtensionError
        with pytest.raises(RendererExtensionError):
            ir.render("beebasm")

    def test_render_can_be_called_multiple_times(self):
        # Multiple renderers per IR — D-009.
        d = Disassembler(cpu=_StubCpu(name="x"))
        ir = d.disassemble()
        out_a = ir.render(_StubRenderer(name="a"))
        out_b = ir.render(_StubRenderer(name="b"))
        assert "x" in str(out_a)
        assert "x" in str(out_b)
