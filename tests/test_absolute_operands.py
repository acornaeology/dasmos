"""Absolute-mode instructions whose operand is below ``&100`` (#46).

An instruction can be *encoded* with absolute addressing even though
its operand fits in zero page (``8D 85 00`` is ``STA &0085``, three
bytes). Both beebasm and 64tass pick the shortest encoding a mnemonic
offers, so naively rendering ``sta &85`` reassembles to the two-byte
zero-page form (``85 85``) and every later address shifts. Some Acorn
code (the Level 2 file server, Econet utilities) does exactly this.

The rule both assemblers apply (beebasm ``assemble.cpp``) is precise:
the zero-page form is chosen iff the value is below ``&100`` *and* the
mnemonic has the matching zero-page mode (``ZP`` / ``ZP,X`` / ``ZP,Y``).
So ``LDA abs,Y`` is safe (LDA has no ``zp,Y``) while ``LDX abs,Y`` is
not. The renderer must force absolute addressing exactly when that
rule would otherwise shrink the instruction:

- 64tass has operand-size syntax: ``sta @w data_0085``;
- beebasm has none, so the instruction is emitted as its bytes
  (``equb &8d : equw data_0085``) with the instruction kept visible in
  a trailing comment.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.core.annotations import Align
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("beebasm")


def _find_tass64() -> str | None:
    env = os.environ.get("TASS64")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("64tass")


BEEBASM = _find_beebasm()
TASS64 = _find_tass64()


# The program from the issue report, plus the indexed variants:
#   2000  8D 85 00   STA &0085      (absolute; STA has zp)      -> force
#   2003  AD 70 00   LDA &0070      (absolute; LDA has zp)      -> force
#   2006  BD 70 00   LDA &0070,X    (abs,X; LDA has zp,X)       -> force
#   2009  B9 70 00   LDA &0070,Y    (abs,Y; LDA has NO zp,Y)    -> safe
#   200C  BE 70 00   LDX &0070,Y    (abs,Y; LDX has zp,Y)       -> force
#   200F  AD 00 30   LDA &3000      (operand >= &100)           -> safe
#   2012  60         RTS
PROGRAM = bytes([
    0x8D, 0x85, 0x00,
    0xAD, 0x70, 0x00,
    0xBD, 0x70, 0x00,
    0xB9, 0x70, 0x00,
    0xBE, 0x70, 0x00,
    0xAD, 0x00, 0x30,
    0x60,
])


def _disassemble(tmp_path, binary=PROGRAM, *, cpu="6502", configure=None):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(binary)
    d = Disassembler.create(cpu=cpu)
    d.load(binpath, 0x2000)
    d.entry(0x2000)
    if configure is not None:
        configure(d)
    return d.disassemble()


def _code_lines(text):
    """The indented body lines of a listing, stripped."""
    return [ln.strip() for ln in text.splitlines() if ln.startswith("    ")]


def _beebasm_round_trip(tmp_path, text):
    asm_path = tmp_path / "out.asm"
    asm_path.write_text(text, encoding="utf-8")
    out_path = tmp_path / "out.bin"
    result = subprocess.run(
        [BEEBASM, "-i", str(asm_path), "-o", str(out_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"beebasm failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    return out_path.read_bytes()


def _tass64_round_trip(tmp_path, text):
    asm_path = tmp_path / "out.asm"
    asm_path.write_text(text, encoding="utf-8")
    out_path = tmp_path / "out.bin"
    result = subprocess.run(
        [TASS64, "--nostart", "-q", "-o", str(out_path), str(asm_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"64tass failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    return out_path.read_bytes()


class TestBeebasmRendering:

    def test_absolute_store_to_zero_page_is_emitted_as_bytes(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        assert any(
            ln.startswith("equb &8d : equw data_0085") for ln in lines
        ), lines

    def test_forced_line_keeps_the_instruction_visible(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        forced = next(ln for ln in lines if ln.startswith("equb &8d"))
        assert "; sta data_0085" in forced
        assert "absolute" in forced

    def test_absolute_x_with_zero_page_x_form_is_forced(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        assert any(ln.startswith("equb &bd : equw data_0070") for ln in lines)

    def test_absolute_y_without_zero_page_y_form_renders_normally(self, tmp_path):
        # LDA has no zp,Y mode, so beebasm keeps the absolute encoding.
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        assert "lda data_0070,y" in lines

    def test_ldx_absolute_y_is_forced(self, tmp_path):
        # LDX *does* have zp,Y, so abs,Y would shrink.
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        assert any(ln.startswith("equb &be : equw data_0070") for ln in lines)

    def test_operand_above_zero_page_renders_normally(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(BeebasmRenderer())))
        assert "lda data_3000" in lines

    def test_genuine_zero_page_instruction_is_unaffected(self, tmp_path):
        # 85 85 is the real 2-byte zero-page STA: render as normal.
        text = str(_disassemble(tmp_path, bytes([0x85, 0x85, 0x60]))
                   .render(BeebasmRenderer()))
        assert "sta data_0085" in _code_lines(text)
        assert "equb" not in text

    def test_user_inline_comment_still_attaches(self, tmp_path):
        ir = _disassemble(
            tmp_path,
            configure=lambda d: d.comment(0x2000, "save the result", align=Align.INLINE),
        )
        lines = _code_lines(str(ir.render(BeebasmRenderer())))
        forced = next(ln for ln in lines if ln.startswith("equb &8d"))
        assert "save the result" in forced


@pytest.mark.beebasm
class TestBeebasmRoundTrip:

    def test_issue_program_round_trips(self, tmp_path):
        # Exactly the reproduction from the issue.
        original = bytes([0x8D, 0x85, 0x00, 0xAD, 0x70, 0x00, 0x60])
        text = str(_disassemble(tmp_path, original).render(BeebasmRenderer()))
        assert _beebasm_round_trip(tmp_path, text) == original

    def test_all_modes_round_trip(self, tmp_path):
        text = str(_disassemble(tmp_path).render(BeebasmRenderer()))
        assert _beebasm_round_trip(tmp_path, text) == PROGRAM

    def test_round_trip_with_byte_column(self, tmp_path):
        text = str(_disassemble(tmp_path).render(BeebasmRenderer(byte_column=True)))
        assert _beebasm_round_trip(tmp_path, text) == PROGRAM

    def test_65c02_stz_absolute_round_trips(self, tmp_path):
        # 65C02 STZ has both abs (9C) and zp (64) forms.
        original = bytes([0x9C, 0x85, 0x00, 0x60])
        text = str(
            _disassemble(tmp_path, original, cpu="65c02").render(BeebasmRenderer())
        )
        assert _beebasm_round_trip(tmp_path, text) == original


class TestTass64Rendering:

    def test_forced_absolute_uses_w_size_prefix(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(Tass64Renderer())))
        assert "sta @w data_0085" in lines
        assert "lda @w data_0070,x" in lines
        assert "ldx @w data_0070,y" in lines

    def test_safe_absolute_y_has_no_size_prefix(self, tmp_path):
        lines = _code_lines(str(_disassemble(tmp_path).render(Tass64Renderer())))
        assert "lda data_0070,y" in lines


@pytest.mark.tass64
class TestTass64RoundTrip:

    def test_all_modes_round_trip(self, tmp_path):
        text = str(_disassemble(tmp_path).render(Tass64Renderer()))
        assert _tass64_round_trip(tmp_path, text) == PROGRAM
