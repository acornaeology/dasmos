"""End-to-end trace-loop tests.

Covers :meth:`Opcode.next_addresses` for each ``FlowControl`` case
and the :meth:`Disassembler._trace` walk against tiny hand-built
NMOS 6502 binaries.

Includes :meth:`Disassembler._classify_leftovers` so the assertions
about "every loaded byte is classified" hold post-disassemble.
"""

import pytest

from dasmos.core.classification import Byte, String
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
        # later trying to read the operand). Both bytes fall to the
        # leftover pass, which aggregates them into one Byte(2).
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xad\x00")  # 2 bytes — opcode wants 3
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        run = ir.classifications.get_classification(0x8000)
        assert isinstance(run, Byte)
        assert run.length() == 2

    def test_trace_terminates_on_undefined_opcode(self, tmp_path):
        # 0x8000: $03 (an undocumented opcode; py8dis omits it)
        # 0x8001: RTS (60)  ← unreached because trace terminated at $03
        # Both unreached bytes aggregate into one Byte(2).
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x03\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        run = ir.classifications.get_classification(0x8000)
        assert isinstance(run, Byte)
        assert run.length() == 2

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


class TestTraceUnderOverlappingMoves:
    """Tracer behaviour when ``add_move`` regions overlap.

    Each ``add_move`` overwrites :data:`MoveManager._move_id_for_binary_addr`
    last-wins, so a later move steals bytes from an earlier one. The
    tracer must classify in terms of EFFECTIVE ownership (the post-
    last-wins map), not the original declared geometry of every
    registered move. It must also follow control-flow targets
    expressed as runtime addresses through the move map back to
    binary addresses, so calls into / branches into moved regions
    classify the destination bytes as code.

    These tests pin the four NFS-3.34 ROM symptoms (BCS at &9367,
    BEQ/BNE at &9508/&950c, STA at &962a) at unit scale.
    """

    def test_opcode_inside_later_overlapping_move_classifies_as_code(
        self, tmp_path,
    ):
        # Layout (binary):
        #   0x8000: NOP   (ea)        — owned by move 1 only
        #   0x8001: BCS+0 (b0 00)     — opcode owned by move 2 (stole
        #                               bytes 0x8001..0x8002 from move 1)
        #   0x8003: RTS   (60)        — owned by move 2 (also the
        #                               taken-branch target: BCS+0
        #                               targets fall_through = 0x8003)
        #
        # Moves:
        #   move 1: src 0x8000, len 2 → runtime 0x9000 (covers 0x8000-1)
        #   move 2: src 0x8001, len 3 → runtime 0x9100 (covers 0x8001-3,
        #                               steals 0x8001 from move 1)
        # After last-wins: 0x8000→1, 0x8001..0x8003→2.
        # The BCS at 0x8001 has both opcode + operand bytes (0x8001
        # and 0x8002) owned by move 2 — it does NOT genuinely
        # straddle. On master the straddle check iterates ALL moves'
        # declared geometry, sees move 1's original src+len boundary
        # at 0x8002, and falsely reports a straddle — so the BCS
        # falls through as ``equb &b0`` instead of an opcode.
        # Mirrors NFS-3.34's BCS at &9367 (Bug A).
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xea\xb0\x00\x60")

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.add_move(0x9000, 0x8000, 2)
        d.add_move(0x9100, 0x8001, 3)
        d.entry(0x8001)
        ir = d.disassemble()

        bcs = ir.classifications.get_classification(0x8001)
        assert isinstance(bcs, Opcode), (
            f"expected BCS opcode at 0x8001, got {bcs!r}"
        )
        assert bcs.operation is Operation.BCS

    def test_jsr_into_moved_region_classifies_target(self, tmp_path):
        # Layout (binary):
        #   0x8000: JSR $0100 (20 00 01) — calls into moved subroutine
        #   0x8003: RTS       (60)        — return after JSR
        #   0x8004..0x8009: filler bytes (leftover-aggregated)
        #   0x800a: NOP       (ea)        — subroutine, runtime 0x0100
        #   0x800b: RTS       (60)        — runtime 0x0101
        #
        # The JSR target operand reads as &0100 — a RUNTIME address
        # that has no binary correspondent (zero-page isn't loaded).
        # Master's tracer queues the operand value as a binary addr
        # directly: is_loaded(0x0100) is False, the trace path dies,
        # and the subroutine bytes never classify as code. The
        # leftover pass marks them ``equb``.
        # Mirrors NFS-3.34's JSR-into-moved-subroutine pattern that
        # leaves &9508/&950c/&962a unclassified (Bug B).
        binary = tmp_path / "p.bin"
        binary.write_bytes(
            b"\x20\x00\x01\x60\x00\x00\x00\x00\x00\x00\xea\x60"
        )

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.add_move(0x0100, 0x800a, 2)
        d.entry(0x8000)
        ir = d.disassemble()

        jsr = ir.classifications.get_classification(0x8000)
        assert isinstance(jsr, Opcode) and jsr.operation is Operation.JSR

        sub_nop = ir.classifications.get_classification(0x800a)
        assert isinstance(sub_nop, Opcode), (
            f"expected NOP at moved-subroutine binary 0x800a, got "
            f"{sub_nop!r}"
        )
        assert sub_nop.operation is Operation.NOP
        sub_rts = ir.classifications.get_classification(0x800b)
        assert isinstance(sub_rts, Opcode), (
            f"expected RTS at moved-subroutine binary 0x800b, got "
            f"{sub_rts!r}"
        )
        assert sub_rts.operation is Operation.RTS

    def test_jsr_inside_moved_region_targeting_other_moved_region(
        self, tmp_path,
    ):
        # Layout (binary):
        #   0x8000: NOP       (ea)        — outside any move (entry)
        #   0x8001: JMP $0100 (4c 00 01)  — jumps into move 1's runtime
        #   0x8004: filler
        #   0x8005: JSR $0200 (20 00 02)  — JSR INSIDE move 1, calls
        #                                   into move 2's runtime
        #   0x8008: RTS       (60)        — inside move 1
        #   0x8009: filler
        #   0x800a: NOP       (ea)        — subroutine in move 2,
        #                                   runtime 0x0200
        #   0x800b: RTS       (60)
        #
        # Moves:
        #   move 1: src 0x8005, len 4 → runtime 0x0100..0x0103
        #   move 2: src 0x800a, len 2 → runtime 0x0200..0x0201
        #
        # This stresses BOTH:
        #   - Trace step pushed on the active-move stack matches the
        #     binary's owning move (so r2b disambiguation prefers
        #     move 1 if there were ambiguity).
        #   - The JSR's runtime target &0200 must r2b through move 2
        #     to binary 0x800a — operand value &0200 is NOT a valid
        #     binary address.
        binary = tmp_path / "p.bin"
        binary.write_bytes(
            b"\xea"          # 0x8000: NOP
            b"\x4c\x00\x01"  # 0x8001: JMP &0100  (into move 1)
            b"\x00"          # 0x8004: filler
            b"\x20\x00\x02"  # 0x8005: JSR &0200  (into move 2)
            b"\x60"          # 0x8008: RTS
            b"\x00"          # 0x8009: filler
            b"\xea"          # 0x800a: NOP
            b"\x60"          # 0x800b: RTS
        )

        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.add_move(0x0100, 0x8005, 4)
        d.add_move(0x0200, 0x800a, 2)
        d.entry(0x8000)
        ir = d.disassemble()

        # The outer JMP into move 1 must reach the JSR at binary 0x8005.
        jsr = ir.classifications.get_classification(0x8005)
        assert isinstance(jsr, Opcode), (
            f"expected JSR at 0x8005 (inside move 1), got {jsr!r}"
        )
        assert jsr.operation is Operation.JSR

        # The JSR target inside move 2 must be classified.
        target_nop = ir.classifications.get_classification(0x800a)
        assert isinstance(target_nop, Opcode), (
            f"expected NOP at 0x800a (inside move 2), got {target_nop!r}"
        )
        target_rts = ir.classifications.get_classification(0x800b)
        assert isinstance(target_rts, Opcode), (
            f"expected RTS at 0x800b (inside move 2), got {target_rts!r}"
        )
        assert target_rts.operation is Operation.RTS


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

    def test_loaded_unreached_bytes_aggregate_into_one_run(self, tmp_path):
        # Three bytes loaded; only the first is reached as code. The
        # leftover pass groups consecutive unclassified bytes between
        # labels (or other classification boundaries) into a single
        # multi-byte ``Byte`` so the renderer emits one ``equb`` row
        # per run, not one row per byte.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x60\x99\xaa")  # RTS, then two unreached
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        # Both trailing bytes belong to one Byte(2) classification at
        # 0x8001; the address 0x8002 is INSIDE_A_CLASSIFICATION.
        run = ir.classifications.get_classification(0x8001)
        assert isinstance(run, Byte)
        assert run.length() == 2
        assert ir.classifications.get_classification(0x8002) is INSIDE_A_CLASSIFICATION

    def test_no_entries_aggregates_everything_into_one_byte_run(self, tmp_path):
        # Without entry points, trace doesn't run; leftover pass
        # classifies every loaded byte. The whole loaded range
        # collapses to a single ``Byte`` of the full length.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\x01\x02\x03\x04")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        ir = d.disassemble()

        run = ir.classifications.get_classification(0x8000)
        assert isinstance(run, Byte)
        assert run.length() == 4

    def test_label_breaks_byte_run(self, tmp_path):
        # A label inside an unclassified region starts a new run, so
        # the renderer can emit a ``.label`` line at the right place.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xff" * 8)
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.label(0x8004, "midpoint")
        ir = d.disassemble()

        # First run covers 0x8000-0x8003 (4 bytes).
        first = ir.classifications.get_classification(0x8000)
        assert isinstance(first, Byte)
        assert first.length() == 4
        # Second run starts at the labelled address.
        second = ir.classifications.get_classification(0x8004)
        assert isinstance(second, Byte)
        assert second.length() == 4

    def test_explicit_byte_length_preserved_against_aggregation(self, tmp_path):
        # When a driver explicitly classifies bytes via d.byte(addr,
        # length=N), the leftover pass must NOT extend or replace
        # that. Surrounding unreached bytes still aggregate, but the
        # explicit run is independent.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"\xff" * 8)
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.byte(0x8003, length=2)  # explicit 2-byte run at 0x8003
        ir = d.disassemble()

        # Explicit classification preserved.
        explicit = ir.classifications.get_classification(0x8003)
        assert isinstance(explicit, Byte)
        assert explicit.length() == 2
        # Bytes before it form their own run (3 bytes: 0x8000-0x8002).
        before = ir.classifications.get_classification(0x8000)
        assert isinstance(before, Byte)
        assert before.length() == 3
        # Bytes after form their own run (3 bytes: 0x8005-0x8007).
        after = ir.classifications.get_classification(0x8005)
        assert isinstance(after, Byte)
        assert after.length() == 3


class TestStringRunDetection:
    """Heuristic that promotes runs of unclassified printable ASCII
    bytes to ``String`` classifications, parallel to py8dis-fork's
    ``classification.autostring`` but expressed declaratively via
    ``Disassembler.string_detection_min_length`` instead of py8dis's
    ``go(post_trace_steps=lambda: autostring(N))`` closure.

    Runs after :meth:`_trace` and before :meth:`_classify_leftovers`
    so the leftover pass sees a smaller residue (the heuristic
    doesn't displace the leftover behaviour, just consumes printable
    runs first).
    """

    def test_default_min_length_is_three(self, tmp_path):
        # ``"OK"`` (2 chars) stays as bytes; ``"OK!"`` (3 chars) gets
        # promoted to a String classification.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"OK\x00OK!")  # 6 bytes
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        ir = d.disassemble()

        # 0x8000-0x8001 ("OK", 2 chars) — too short, falls to leftover
        # pass which sees printable bytes followed by 0x00 (NUL is
        # non-printable, breaks the leftover run too).
        run_at_8000 = ir.classifications.get_classification(0x8000)
        assert isinstance(run_at_8000, Byte)
        # 0x8003 ("OK!" 3 chars) — meets min_length=3, classified as
        # String.
        s = ir.classifications.get_classification(0x8003)
        assert isinstance(s, String)
        assert s.length() == 3

    def test_min_length_is_configurable(self, tmp_path):
        # With min_length=4, ``"OK!"`` doesn't qualify; ``"HELLO"``
        # does.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"OK!\x00HELLO")
        d = Disassembler.create(cpu="6502", string_detection_min_length=4)
        d.load(binary, 0x8000)
        ir = d.disassemble()

        # ``OK!`` falls to Byte (3 chars, below threshold of 4).
        c = ir.classifications.get_classification(0x8000)
        assert isinstance(c, Byte)
        # ``HELLO`` is 5 chars — String.
        s = ir.classifications.get_classification(0x8004)
        assert isinstance(s, String)
        assert s.length() == 5

    def test_none_disables_detection(self, tmp_path):
        # min_length=None → don't run the heuristic at all. The
        # printable run remains unclassified and falls to the
        # leftover Byte aggregator.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLO")
        d = Disassembler.create(cpu="6502", string_detection_min_length=None)
        d.load(binary, 0x8000)
        ir = d.disassemble()

        c = ir.classifications.get_classification(0x8000)
        assert isinstance(c, Byte)
        assert c.length() == 5

    def test_breaks_at_label(self, tmp_path):
        # A real label inside a printable run starts a new
        # classification — the heuristic wouldn't otherwise know
        # the author distinguishes the suffix as its own thing.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLOWORLD")  # 10 printable
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.label(0x8005, "world")           # break the run here
        ir = d.disassemble()

        first = ir.classifications.get_classification(0x8000)
        assert isinstance(first, String)
        assert first.length() == 5
        second = ir.classifications.get_classification(0x8005)
        assert isinstance(second, String)
        assert second.length() == 5

    def test_breaks_at_non_printable(self, tmp_path):
        # A non-printable byte (e.g. NUL terminator) breaks the run.
        # The terminator stays unclassified and falls to leftover.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLO\x00WORLD")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        ir = d.disassemble()

        first = ir.classifications.get_classification(0x8000)
        assert isinstance(first, String)
        assert first.length() == 5
        # 0x8005 is the NUL — falls to leftover Byte; aggregation may
        # extend it through unclassified neighbours, but the type is
        # Byte regardless.
        nul = ir.classifications.get_classification(0x8005)
        assert isinstance(nul, Byte)
        # WORLD starts at 0x8006.
        second = ir.classifications.get_classification(0x8006)
        assert isinstance(second, String)
        assert second.length() == 5

    def test_skips_already_classified(self, tmp_path):
        # When the driver explicitly classifies bytes via d.byte(...)
        # / d.string(...), the heuristic must not displace that.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLO")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.byte(0x8002, length=1)           # explicit single byte mid-run
        ir = d.disassemble()

        # Pre-classified byte at 0x8002 stays as Byte(1).
        explicit = ir.classifications.get_classification(0x8002)
        assert isinstance(explicit, Byte)
        assert explicit.length() == 1
        # Surrounding printable runs become Strings IF they meet the
        # threshold individually. 0x8000-0x8001 is just 2 chars — too
        # short, falls to leftover Byte. 0x8003-0x8004 is 2 chars —
        # also too short.
        before = ir.classifications.get_classification(0x8000)
        assert isinstance(before, Byte)
        after = ir.classifications.get_classification(0x8003)
        assert isinstance(after, Byte)

    def test_breaks_at_move_boundary(self, tmp_path):
        # A printable run that crosses a move source-boundary must
        # split — the asm renderer emits each classification at one
        # runtime range, and a String straddling a boundary would
        # write past the destination's end (beebasm "Trying to
        # assemble over existing code").
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLOWORLD")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.add_move(0x0100, 0x8005, 5)      # WORLD relocates to 0x0100
        ir = d.disassemble()

        # First half stops at the move boundary, even though the
        # printable bytes continue.
        first = ir.classifications.get_classification(0x8000)
        assert isinstance(first, String)
        assert first.length() == 5
        # Second half is its own classification.
        second = ir.classifications.get_classification(0x8005)
        assert isinstance(second, String)
        assert second.length() == 5

    def test_breaks_at_annotation(self, tmp_path):
        # An annotated byte inside an otherwise-detectable string run
        # starts a new classification, so the annotation lands on a
        # classification boundary where the renderer can attach it.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLOWORLD")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        d.comment(0x8005, "Note here")
        ir = d.disassemble()

        first = ir.classifications.get_classification(0x8000)
        assert isinstance(first, String)
        assert first.length() == 5
        second = ir.classifications.get_classification(0x8005)
        assert isinstance(second, String)
        assert second.length() == 5

    def test_property_can_be_set_after_construction(self, tmp_path):
        # The setting is also exposed as a plain attribute so drivers
        # that build the Disassembler one way and tune it later still
        # work.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"HELLO")
        d = Disassembler.create(cpu="6502")
        d.string_detection_min_length = None
        d.load(binary, 0x8000)
        ir = d.disassemble()

        # Heuristic disabled — leftover aggregation classifies all
        # five printable bytes as one Byte run.
        c = ir.classifications.get_classification(0x8000)
        assert isinstance(c, Byte)
        assert c.length() == 5

    def test_high_bit_byte_is_not_printable(self, tmp_path):
        # 0x80–0xFF are NOT considered printable (matches py8dis
        # ``utils.isprint``). A run with high-bit bytes stops at the
        # first one.
        binary = tmp_path / "p.bin"
        binary.write_bytes(b"FOO\x80BAR")
        d = Disassembler.create(cpu="6502")
        d.load(binary, 0x8000)
        ir = d.disassemble()

        foo = ir.classifications.get_classification(0x8000)
        assert isinstance(foo, String)
        assert foo.length() == 3
        bar = ir.classifications.get_classification(0x8004)
        assert isinstance(bar, String)
        assert bar.length() == 3
