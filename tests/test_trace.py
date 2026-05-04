"""End-to-end trace-loop tests.

Covers :meth:`Opcode.next_addresses` for each ``FlowControl`` case
and the :meth:`Disassembler._trace` walk against tiny hand-built
NMOS 6502 binaries.

Includes :meth:`Disassembler._classify_leftovers` so the assertions
about "every loaded byte is classified" hold post-disassemble.
"""

import pytest

from dasmos.core.classification import Byte
from dasmos.core.disassembly import INSIDE_A_CLASSIFICATION
from dasmos.core.memory import BinaryAddr, MemoryImage, RuntimeAddr
from dasmos.cpu import FlowControl, Opcode, OperandKind
from dasmos.disassembler import Disassembler
from dasmos.ext.cpus.cpu6502 import (
    OPCODES,
    AddressingMode,
    Operation,
)


# ---------------------------------------------------------------------------
# Opcode.next_addresses against a hand-built memory image
# ---------------------------------------------------------------------------


def _memory_with(bytes_: bytes, at: int = 0x8000) -> MemoryImage:
    """Construct a MemoryImage prefilled with ``bytes_`` at ``at``."""
    img = MemoryImage()
    for i, b in enumerate(bytes_):
        img._bytes[at + i] = b
    img._load_ranges.append((BinaryAddr(at), BinaryAddr(at + len(bytes_))))
    return img


class TestOpcodeNextAddresses:

    def test_sequential_returns_fall_through(self):
        # LDA #$42 at 0x8000 (2 bytes); next addr = 0x8002.
        memory = _memory_with(b"\xa9\x42")
        op = OPCODES[0xA9]
        assert op.next_addresses(memory, 0x8000) == [0x8002]

    def test_return_returns_empty_list(self):
        # RTS at 0x8000 (1 byte). No next addresses.
        memory = _memory_with(b"\x60")
        op = OPCODES[0x60]
        assert op.next_addresses(memory, 0x8000) == []

    def test_break_returns_empty_list(self):
        # BRK at 0x8000.
        memory = _memory_with(b"\x00")
        op = OPCODES[0x00]
        assert op.next_addresses(memory, 0x8000) == []

    def test_jump_absolute_returns_target(self):
        # JMP $9000 at 0x8000 (3 bytes).
        memory = _memory_with(b"\x4c\x00\x90")
        op = OPCODES[0x4C]
        assert op.next_addresses(memory, 0x8000) == [0x9000]

    def test_jump_indirect_follows_pointer(self):
        # JMP ($8003) at 0x8000; pointer at 0x8003 = $9000.
        memory = _memory_with(b"\x6c\x03\x80\x00\x90")
        op = OPCODES[0x6C]
        assert op.next_addresses(memory, 0x8000) == [0x9000]

    def test_jump_indirect_drops_target_when_pointer_not_loaded(self):
        # JMP ($9000) at 0x8000 — pointer's bytes aren't in memory.
        memory = _memory_with(b"\x6c\x00\x90")
        op = OPCODES[0x6C]
        # Path narrows to no successors — better that than a crash.
        assert op.next_addresses(memory, 0x8000) == []

    def test_subroutine_call_returns_target_and_fall_through(self):
        # JSR $9000 at 0x8000 (3 bytes); fall_through = 0x8003.
        memory = _memory_with(b"\x20\x00\x90")
        op = OPCODES[0x20]
        result = op.next_addresses(memory, 0x8000)
        assert set(result) == {0x9000, 0x8003}

    def test_conditional_branch_returns_target_and_fall_through(self):
        # BNE +5 at 0x8000 (2 bytes); fall_through = 0x8002;
        # target = 0x8002 + 0x05 = 0x8007.
        memory = _memory_with(b"\xd0\x05")
        op = OPCODES[0xD0]
        result = op.next_addresses(memory, 0x8000)
        assert set(result) == {0x8002, 0x8007}

    def test_conditional_branch_negative_offset(self):
        # BNE -5 at 0x8000 — offset 0xFB = -5; target = 0x8002 - 5 = 0x7FFD.
        memory = _memory_with(b"\xd0\xfb")
        op = OPCODES[0xD0]
        result = op.next_addresses(memory, 0x8000)
        assert set(result) == {0x8002, 0x7FFD}


# ---------------------------------------------------------------------------
# Disassembler trace + leftover classification, end-to-end
# ---------------------------------------------------------------------------


class TestTraceLoop:

    def test_simple_program_traced_completely(self, tmp_path):
        # 0x8000: LDA #$42  (a9 42)
        # 0x8002: RTS       (60)
        binary = tmp_path / "tiny.bin"
        binary.write_bytes(b"\xa9\x42\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # LDA at 0x8000 spans 0x8000-0x8001.
        lda = ir.classifications.get_classification(0x8000)
        assert isinstance(lda, Opcode)
        assert lda.operation is Operation.LDA
        assert ir.classifications.get_classification(0x8001) is INSIDE_A_CLASSIFICATION

        # RTS at 0x8002.
        rts = ir.classifications.get_classification(0x8002)
        assert isinstance(rts, Opcode)
        assert rts.operation is Operation.RTS

    def test_jsr_follows_target_and_falls_through(self, tmp_path):
        # 0x8000: JSR $8006 (20 06 80)
        # 0x8003: NOP       (ea)
        # 0x8004: RTS       (60)
        # 0x8005: $42       (data; not reached by trace)
        # 0x8006: NOP       (ea)
        # 0x8007: RTS       (60)
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x20\x06\x80\xea\x60\x42\xea\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # JSR target reached.
        target_nop = ir.classifications.get_classification(0x8006)
        assert isinstance(target_nop, Opcode) and target_nop.operation is Operation.NOP
        target_rts = ir.classifications.get_classification(0x8007)
        assert isinstance(target_rts, Opcode) and target_rts.operation is Operation.RTS

        # Fall-through after JSR also reached.
        ft_nop = ir.classifications.get_classification(0x8003)
        assert isinstance(ft_nop, Opcode) and ft_nop.operation is Operation.NOP
        ft_rts = ir.classifications.get_classification(0x8004)
        assert isinstance(ft_rts, Opcode) and ft_rts.operation is Operation.RTS

        # The unreachable byte at 0x8005 gets classified as Byte by
        # the leftover pass.
        leftover = ir.classifications.get_classification(0x8005)
        assert isinstance(leftover, Byte)
        assert leftover.length() == 1

    def test_unconditional_jump_does_not_fall_through(self, tmp_path):
        # 0x8000: JMP $8004 (4c 04 80)
        # 0x8003: $99       (data; unreachable — JMP doesn't fall through)
        # 0x8004: RTS       (60)
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x4c\x04\x80\x99\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # JMP classified.
        jmp = ir.classifications.get_classification(0x8000)
        assert isinstance(jmp, Opcode) and jmp.operation is Operation.JMP

        # The "fall-through" byte at 0x8003 is NOT reached by trace —
        # JMP has no fall-through. It gets classified as Byte by the
        # leftover pass.
        unreachable = ir.classifications.get_classification(0x8003)
        assert isinstance(unreachable, Byte)

        # Target RTS is reached.
        rts = ir.classifications.get_classification(0x8004)
        assert isinstance(rts, Opcode) and rts.operation is Operation.RTS

    def test_conditional_branch_follows_both_paths(self, tmp_path):
        # Layout designed so both branch arms classify code:
        # 0x8000: LDA #$00  (a9 00)
        # 0x8002: BEQ +1    (f0 01)  — target = 0x8004 + 1 = 0x8005
        # 0x8004: RTS       (60)     ← fall-through (taken if !zero)
        # 0x8005: NOP       (ea)     ← branch target (taken if zero)
        # 0x8006: RTS       (60)     ← falls through from NOP
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xa9\x00\xf0\x01\x60\xea\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # All instructions traced.
        for byte_addr, expected_op in [
            (0x8000, Operation.LDA),
            (0x8002, Operation.BEQ),
            (0x8004, Operation.RTS),
            (0x8005, Operation.NOP),
            (0x8006, Operation.RTS),
        ]:
            c = ir.classifications.get_classification(byte_addr)
            assert isinstance(c, Opcode), f"0x{byte_addr:04x} not an opcode"
            assert c.operation is expected_op, (
                f"0x{byte_addr:04x} expected {expected_op.name}, got {c.operation.name}"
            )

    def test_jmp_indirect_followed_when_pointer_loaded(self, tmp_path):
        # 0x8000: JMP ($8003)  (6c 03 80)
        # 0x8003: $06 $80      (the pointer; → $8005)
        # 0x8005: NOP          (ea)
        # 0x8006: RTS          (60)
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x6c\x03\x80\x05\x80\xea\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        # Mark the pointer as data so it doesn't get traced as code.
        d.word(0x8003, 2)
        d.entry(0x8000)
        ir = d.disassemble()

        # JMP classified.
        jmp = ir.classifications.get_classification(0x8000)
        assert isinstance(jmp, Opcode) and jmp.operation is Operation.JMP

        # Target reached via the indirection.
        target = ir.classifications.get_classification(0x8005)
        assert isinstance(target, Opcode) and target.operation is Operation.NOP
        rts = ir.classifications.get_classification(0x8006)
        assert isinstance(rts, Opcode) and rts.operation is Operation.RTS

    def test_trace_terminates_when_operand_bytes_unloaded(self, tmp_path):
        # 0x8000: 0xAD (LDA $XXXX — needs 2 operand bytes)
        # but only 0x8000 and 0x8001 are loaded. The trace must NOT
        # classify the partial instruction (the renderer would crash
        # later trying to read the operand). Both bytes get the
        # leftover Byte(1) treatment.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xad\x00")  # 2 bytes — opcode wants 3
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # Both bytes are leftover Byte(1) — no Opcode classification.
        for addr in (0x8000, 0x8001):
            c = ir.classifications.get_classification(addr)
            assert isinstance(c, Byte), (
                f"0x{addr:04x} should have been left as Byte; got {c!r}"
            )

    def test_trace_terminates_on_undefined_opcode(self, tmp_path):
        # 0x8000: $03 (an undocumented opcode; py8dis omits it)
        # 0x8001: RTS (60)  ← unreached because trace terminated at $03
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x03\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # 0x8000 wasn't classified as an opcode (undefined → leftover Byte).
        c0 = ir.classifications.get_classification(0x8000)
        assert isinstance(c0, Byte)

        # 0x8001 also leftover Byte (trace didn't reach it).
        c1 = ir.classifications.get_classification(0x8001)
        assert isinstance(c1, Byte)

    def test_trace_handles_cycle(self, tmp_path):
        # 0x8000: JMP $8000  (4c 00 80) — infinite loop to itself.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x4c\x00\x80")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        # Must terminate; the visited-set breaks the cycle.
        ir = d.disassemble()

        jmp = ir.classifications.get_classification(0x8000)
        assert isinstance(jmp, Opcode) and jmp.operation is Operation.JMP

    def test_trace_skips_pre_classified_data_in_path(self, tmp_path):
        # 0x8000: NOP       (ea)  — falls through to 0x8001
        # 0x8001: NOP       (ea)  — manually pre-classified as Byte;
        #                          trace would otherwise re-classify
        #                          this as a NOP opcode
        # 0x8002: RTS       (60)
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xea\xea\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.byte(0x8001, 1)  # pre-classify the in-path byte as data
        d.entry(0x8000)
        ir = d.disassemble()

        # The pre-classified byte stays a Byte (trace doesn't overwrite).
        manual = ir.classifications.get_classification(0x8001)
        assert isinstance(manual, Byte)

        # Trace continued past the pre-classified data and reached RTS.
        # py8dis-compatible: trace doesn't terminate at user-classified
        # data; it just doesn't re-classify there.
        rts = ir.classifications.get_classification(0x8002)
        assert isinstance(rts, Opcode) and rts.operation is Operation.RTS


class TestEntryRegistration:

    def test_entry_appends_to_entry_points(self, tmp_path):
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x60")  # RTS
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        assert d._entry_points == [BinaryAddr(0x8000)]

    def test_entry_with_name_creates_label(self, tmp_path):
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x60")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000, name="start")
        label = d.labels.get_label(0x8000)
        assert label is not None
        assert "start" in label.all_names()

    def test_entry_after_disassemble_raises(self, tmp_path):
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x60")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.disassemble()
        from dasmos.disassembler import DisassemblerError
        with pytest.raises(DisassemblerError):
            d.entry(0x8000)


class TestLeftoverClassification:

    def test_loaded_unreached_bytes_become_byte(self, tmp_path):
        # Three bytes loaded; only the first is reached as code.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x60\x99\xaa")  # RTS, then two unreached
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # The two unreached bytes become individual Byte(1)s.
        for addr in (0x8001, 0x8002):
            c = ir.classifications.get_classification(addr)
            assert isinstance(c, Byte)
            assert c.length() == 1

    def test_no_entries_classifies_everything_as_byte(self, tmp_path):
        # Without entry points, trace doesn't run; leftover pass
        # classifies every loaded byte as Byte.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x01\x02\x03\x04")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        ir = d.disassemble()

        for addr in (0x8000, 0x8001, 0x8002, 0x8003):
            c = ir.classifications.get_classification(addr)
            assert isinstance(c, Byte)
