"""Tests for the CMOS 65C02 CPU plug-in.

Mirrors the structure of :mod:`tests.test_cpu6502`. The 65C02 is a
strict superset of NMOS 6502, so the new ground here is:

- The 8 new mnemonics (BRA, PHX, PHY, PLX, PLY, STZ, TRB, TSB).
- The 2 new addressing modes (``(zp)`` and ``(addr,X)`` for JMP).
- 27 new opcode bytes wiring those into the table, plus a handful of
  NMOS opcodes picking up new variants (``BIT #imm``, ``INC A``,
  ``DEC A``).
- 178 entries total (151 inherited from NMOS + 27 new bytes).

A small round-trip exercise at the end exercises a 65C02-only opcode
through the BeebasmRenderer to confirm the renderer dispatches the
new addressing modes and emits the ``cpu 1`` directive.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dasmos.cpu import FlowControl, OperandKind
from dasmos.disassembler import Disassembler
from dasmos.ext.cpus.cpu65c02 import (
    AddressingMode,
    Cmos65C02Cpu,
    OPCODES,
    Operation,
)
from dasmos.ext.cpus.cpu6502 import (
    AddressingMode as NmosAddressingMode,
    Operation as NmosOperation,
)


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    found = shutil.which("beebasm")
    if found:
        return found
    fallback = "/Users/rjs/Code/beebasm/beebasm"
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return None


_BEEBASM = _find_beebasm()


class TestPluginRegistration:

    def test_loadable_via_stevedore(self):
        d = Disassembler.create(cpu="65C02")
        assert isinstance(d._cpu, Cmos65C02Cpu)

    def test_address_space_is_64k(self):
        cpu = Cmos65C02Cpu()
        assert cpu.address_space_size == 0x10000

    def test_brief_description_overrides_docstring_first_line(self):
        # 65C02 overrides brief_description because the docstring's
        # first line is too long for the list-cpus table column.
        brief = Cmos65C02Cpu.brief_description()
        assert "\n" not in brief
        assert "8 extra mnemonics" in brief
        # The docstring's first line is NOT what brief returns.
        assert brief != Cmos65C02Cpu.full_description().splitlines()[0]

    def test_full_description_is_the_complete_docstring(self):
        full = Cmos65C02Cpu.full_description()
        # Multi-paragraph and includes the WDC-instructions caveat.
        assert "\n" in full
        assert "WDC" in full


class TestOperationEnum:

    def test_has_eight_extra_mnemonics(self):
        # Only the *additions* live in this enum; the 56 NMOS
        # mnemonics are imported by reference where needed.
        assert len(Operation) == 8

    def test_member_values_are_lowercase_canonical(self):
        for member in Operation:
            assert member.value == member.name.lower()
            assert member.value.isalpha()

    def test_extras_are_specifically_the_65c02_additions(self):
        names = {m.name for m in Operation}
        assert names == {"BRA", "PHX", "PHY", "PLX", "PLY", "STZ", "TRB", "TSB"}


class TestAddressingModeEnum:

    def test_has_two_extra_modes(self):
        assert len(AddressingMode) == 2

    def test_zp_indirect_is_one_byte_address_8(self):
        m = AddressingMode.ZP_INDIRECT
        assert m.operand_length == 1
        assert m.operand_kind == OperandKind.ADDRESS_8

    def test_absolute_indirect_x_is_two_byte_address_16_indirect(self):
        m = AddressingMode.ABSOLUTE_INDIRECT_X
        assert m.operand_length == 2
        assert m.operand_kind == OperandKind.ADDRESS_16_INDIRECT


class TestOpcodeTable:

    def test_total_opcode_count_is_178(self):
        # 151 NMOS + 27 65C02-additions = 178 documented opcodes.
        assert len(OPCODES) == 178

    def test_all_keys_are_valid_byte_values(self):
        for byte in OPCODES:
            assert 0 <= byte <= 0xFF

    def test_inherits_nmos_opcodes_unchanged(self):
        # A handful of NMOS opcodes that 65C02 leaves alone — they
        # come through with the NMOS Operation enum members.
        assert OPCODES[0xa9].operation is NmosOperation.LDA
        assert OPCODES[0x60].operation is NmosOperation.RTS
        assert OPCODES[0x20].operation is NmosOperation.JSR


class TestSpotCheckedNew65C02Opcodes:

    def test_bra_is_relative_unconditional_jump(self):
        op = OPCODES[0x80]
        assert op.operation is Operation.BRA
        assert op.addressing_mode is NmosAddressingMode.RELATIVE
        assert op.flow_control is FlowControl.JUMP

    def test_stz_absolute(self):
        op = OPCODES[0x9c]
        assert op.operation is Operation.STZ
        assert op.addressing_mode is NmosAddressingMode.ABSOLUTE

    def test_phx_phy_plx_ply_are_implied(self):
        for byte, expected in [
            (0xda, Operation.PHX),
            (0x5a, Operation.PHY),
            (0xfa, Operation.PLX),
            (0x7a, Operation.PLY),
        ]:
            assert OPCODES[byte].operation is expected
            assert OPCODES[byte].addressing_mode is NmosAddressingMode.IMPLIED

    def test_jmp_indirect_x_uses_new_addressing_mode(self):
        op = OPCODES[0x7c]
        assert op.operation is NmosOperation.JMP
        assert op.addressing_mode is AddressingMode.ABSOLUTE_INDIRECT_X
        assert op.flow_control is FlowControl.JUMP

    def test_lda_zp_indirect(self):
        # 0xb2 = LDA (zp) — new in 65C02.
        op = OPCODES[0xb2]
        assert op.operation is NmosOperation.LDA
        assert op.addressing_mode is AddressingMode.ZP_INDIRECT

    def test_inc_a_uses_accumulator_mode(self):
        # 0x1a = INC A — accumulator-mode INC is new in 65C02.
        op = OPCODES[0x1a]
        assert op.operation is NmosOperation.INC
        assert op.addressing_mode is NmosAddressingMode.ACCUMULATOR

    def test_bit_immediate_is_new_variant(self):
        # 0x89 = BIT #imm — only affects Z on 65C02; new in 65C02.
        op = OPCODES[0x89]
        assert op.operation is NmosOperation.BIT
        assert op.addressing_mode is NmosAddressingMode.IMMEDIATE


@pytest.mark.beebasm
class TestRoundTripVia65C02:
    """Tiny end-to-end: assemble a 65C02-only opcode, disassemble via
    the new plug-in, render via BeebasmRenderer (which must emit the
    ``cpu 1`` directive and dispatch the new addressing modes), and
    confirm the result re-assembles to the same bytes."""

    def test_lda_zp_indirect_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        # Source program using a 65C02-only opcode (LDA (zp)).
        src = """
            cpu 1
            org &8000
        .start
            lda (&70)
            rts
        save "step1.bin", start, P%
        """
        asm_in = tmp_path / "in.asm"
        asm_in.write_text(src, encoding="utf-8")
        result = subprocess.run(
            [_BEEBASM, "-i", str(asm_in)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, result.stderr
        original = (tmp_path / "step1.bin").read_bytes()

        # Disassemble + render via 65C02 plug-in. Disable auto-labels
        # so the operand resolves to its literal hex form — this test
        # is pinning the addressing-mode SHAPE (the parentheses
        # around a zp operand), not the symbol resolution.
        bin_path = tmp_path / "in.bin"
        bin_path.write_bytes(original)
        d = Disassembler.create(cpu="65C02", auto_labels_enabled=False)
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        ir = d.disassemble()
        text = str(ir.render("beebasm"))

        # The renderer emits ``cpu 1`` so beebasm enables 65C02 mode.
        assert "cpu 1" in text
        # The new addressing mode renders as ``(symbol)``.
        assert "lda (&70)" in text

        # Re-assemble and verify byte equality. The renderer's
        # ``save dasmos_start, dasmos_end`` has no filename embedded;
        # beebasm needs ``-o`` to know where to write.
        asm_out = tmp_path / "out.asm"
        asm_out.write_text(text, encoding="utf-8")
        rebuilt_path = tmp_path / "rebuilt.bin"
        result = subprocess.run(
            [_BEEBASM, "-i", str(asm_out), "-o", str(rebuilt_path)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed:\n=== source ===\n{text}\n"
            f"=== stderr ===\n{result.stderr}"
        )
        rebuilt = rebuilt_path.read_bytes()
        assert rebuilt == original

    def test_jmp_indirect_x_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        # JMP (addr,X) — the most exotic 65C02-only addressing mode.
        # Use a vector at &9000; the X-indexed indirect JMP picks one
        # of two destinations.
        src = """
            cpu 1
            org &8000
        .start
            ldx #0
            jmp (table,X)
        .a
            rts
        .b
            rts
        .table
            equw a, b
        save "step1.bin", start, P%
        """
        asm_in = tmp_path / "in.asm"
        asm_in.write_text(src, encoding="utf-8")
        result = subprocess.run(
            [_BEEBASM, "-i", str(asm_in)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, result.stderr
        original = (tmp_path / "step1.bin").read_bytes()

        bin_path = tmp_path / "in.bin"
        bin_path.write_bytes(original)
        d = Disassembler.create(cpu="65C02")
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        ir = d.disassemble()
        text = str(ir.render("beebasm"))

        assert "cpu 1" in text
        # JMP (addr,X) renders with the indirect-X parens.
        # Look for a jmp line containing both parens and ,X.
        jmp_lines = [
            line for line in text.splitlines()
            if line.strip().startswith("jmp ") and "(" in line and ",X)" in line
        ]
        assert jmp_lines, (
            f"expected `jmp (...,X)` in output:\n{text}"
        )
