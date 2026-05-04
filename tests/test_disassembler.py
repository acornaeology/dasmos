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

    def test_factory_with_string_resolves_via_stevedore(self):
        # 6502 is registered; the factory should find it and build a
        # working Disassembler.
        d = Disassembler.create(cpu="6502")
        assert d.cpu.name == "6502"
        assert d.cpu.address_space_size == 0x10000
        # And the opcode table is populated.
        assert len(d.cpu.opcodes()) == 151

    def test_factory_with_unknown_string_raises(self):
        from dasmos.cpu import CpuExtensionError
        with pytest.raises(CpuExtensionError):
            Disassembler.create(cpu="z80_doesnt_exist_yet")

    def test_factory_lookup_is_case_insensitive(self):
        # The 65C02 plug-in is registered with an uppercase 'C'.
        # A user typing "65c02" or "65C02" should both resolve.
        d_lower = Disassembler.create(cpu="65c02")
        d_upper = Disassembler.create(cpu="65C02")
        # Whichever form the user types, the disassembler reports the
        # canonical registered name.
        assert d_lower.cpu.name == "65C02"
        assert d_upper.cpu.name == "65C02"


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
        from dasmos.core.move import Move
        d = Disassembler(cpu=_StubCpu())
        move = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert isinstance(move, Move)
        assert move._move_id == 1  # BASE_MOVE_ID + 1
        assert d.moves.is_valid_move_id(move._move_id)

    def test_move_is_a_context_manager(self):
        d = Disassembler(cpu=_StubCpu())
        move = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert d.moves.active_move_ids == []
        with move:
            assert d.moves.active_move_ids == [move._move_id]
        assert d.moves.active_move_ids == []

    def test_add_move_accepts_optional_name(self):
        d = Disassembler(cpu=_StubCpu())
        move = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10, name="nmi_write")
        assert move.name == "nmi_write"

    def test_add_move_fabricates_name_when_omitted(self):
        d = Disassembler(cpu=_StubCpu())
        move = d.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        # Some non-empty fabricated name; exact form is implementation
        # detail.
        assert move.name and isinstance(move.name, str)


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
# constants — named values (BBC hardware addresses, magic numbers)
# ---------------------------------------------------------------------------


class TestConstants:
    """``constant(value, name)`` records a named value AND registers
    an optional label at the same address (so the asm equate emission
    is unchanged from when the porter routed py8dis ``constant()``
    calls to ``optional_label()``). The constants list itself is the
    additional handle the JSON renderer reads.
    """

    def test_records_named_value(self):
        d = Disassembler(cpu=_StubCpu())
        d.constant(0xFE60, "system_via_orb")
        constants = d.constants
        assert len(constants) == 1
        assert constants[0].name == "system_via_orb"
        assert constants[0].value == 0xFE60
        assert constants[0].comment is None

    def test_records_optional_comment(self):
        d = Disassembler(cpu=_StubCpu())
        d.constant(0xFE60, "system_via_orb", comment="System VIA port B")
        assert d.constants[0].comment == "System VIA port B"

    def test_does_not_pollute_label_space(self):
        # constant() must NOT add a label at the value's runtime
        # address — that would cause hook-registered constants
        # (e.g. ``osbyte_clear_escape = &7c``) to make any
        # unrelated zero-page operand at &7c suddenly resolve as
        # ``lda osbyte_clear_escape`` (false positive). Mirrors
        # py8dis where ``constant()`` populates a separate
        # ``disassembly.constants`` list, not LabelManager.
        d = Disassembler(cpu=_StubCpu())
        d.constant(0x7c, "osbyte_clear_escape")
        # The constant is recorded.
        assert d.constants[0].name == "osbyte_clear_escape"
        # But NO label was added at runtime &7c.
        assert d.labels.get_label(0x7c) is None

    def test_constants_exposed_on_ir(self):
        d = Disassembler(cpu=_StubCpu())
        d.constant(0xFE60, "system_via_orb")
        ir = d.disassemble()
        assert ir.constants[0].name == "system_via_orb"

    def test_constants_post_disassemble_raises(self):
        d = Disassembler(cpu=_StubCpu())
        d.disassemble()
        with pytest.raises(DisassemblerError, match="frozen"):
            d.constant(0xFE60, "system_via_orb")


# ---------------------------------------------------------------------------
# subroutines — entry points with name + optional banner metadata
# ---------------------------------------------------------------------------


class TestSubroutines:
    """``subroutine()`` already seeds the trace and registers a label
    + banner annotation. The new behaviour is a SubroutineEntry record
    on a parallel ``ir.subroutines`` list — needed for the JSON
    renderer's ``subroutines`` section (mirrors py8dis-fork schema).
    """

    def test_records_subroutine_entry(self):
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(0x8000, "init")
        subs = d.subroutines
        assert len(subs) == 1
        assert subs[0].runtime_addr == 0x8000
        assert subs[0].name == "init"

    def test_records_banner_metadata(self):
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(
            0x8000, "init",
            title="Initialise NMI workspace",
            description="Copies 97 bytes from ROM to ZP.",
            on_entry={"a": "must be zero"},
            on_exit={"y": "preserved"},
        )
        sub = d.subroutines[0]
        assert sub.title == "Initialise NMI workspace"
        assert sub.description == "Copies 97 bytes from ROM to ZP."
        assert sub.on_entry == {"a": "must be zero"}
        assert sub.on_exit == {"y": "preserved"}

    def test_anonymous_subroutine_records_entry_with_no_name(self):
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(0x8000)
        sub = d.subroutines[0]
        assert sub.runtime_addr == 0x8000
        assert sub.name is None

    def test_subroutines_exposed_on_ir(self):
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(0x8000, "init")
        ir = d.disassemble()
        assert ir.subroutines[0].name == "init"

    def test_existing_seeding_and_label_behaviour_preserved(self):
        # subroutine() must STILL seed the trace and define a label
        # — those are the load-bearing behaviours from before the
        # SubroutineEntry record was added.
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(0x8000, "init")
        # Trace seeded:
        from dasmos.core.memory import BinaryAddr
        assert BinaryAddr(0x8000) in d._entry_points
        # Label defined:
        label = d.labels.get_label(0x8000)
        assert label is not None
        assert "init" in label.explicit_name_texts()

    def test_is_entry_point_false_skips_trace_and_marks_label_optional(self):
        # Used by Environment plug-ins to document out-of-image OS
        # calls (e.g. ``osbyte`` at &FFF4 lives in MOS ROM, NOT in
        # any disassembled binary — seeding the trace from there
        # would chase unloaded memory, and the label should only
        # surface when actually JSR'd to).
        from dasmos.core.memory import BinaryAddr
        d = Disassembler(cpu=_StubCpu())
        d.subroutine(0xfff4, "osbyte", is_entry_point=False)
        assert BinaryAddr(0xfff4) not in d._entry_points
        # SubroutineEntry recorded regardless.
        assert d.subroutines[0].name == "osbyte"
        # Label registered as OPTIONAL (label-level ``required``
        # flag stays False).
        label = d.labels.get_label(0xfff4)
        assert label is not None
        assert "osbyte" in label.explicit_name_texts()
        assert label.required is False


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

    def test_render_with_unknown_string_raises(self):
        d = Disassembler(cpu=_StubCpu())
        ir = d.disassemble()
        from dasmos.renderer import RendererExtensionError
        with pytest.raises(RendererExtensionError):
            ir.render("ca65_doesnt_exist_yet")

    def test_render_can_be_called_multiple_times(self):
        # Multiple renderers per IR — D-009.
        d = Disassembler(cpu=_StubCpu(name="x"))
        ir = d.disassemble()
        out_a = ir.render(_StubRenderer(name="a"))
        out_b = ir.render(_StubRenderer(name="b"))
        assert "x" in str(out_a)
        assert "x" in str(out_b)
