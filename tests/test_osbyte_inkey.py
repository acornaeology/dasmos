"""OSBYTE &81 reads X and Y together (#59).

- Y = &FF: X is a negative INKEY number, and the call tests whether that
  key is pressed — BASIC's ``INKEY(-2)`` passes X = &FE for CTRL. (X = 0
  reads the OS version instead.)
- Y = 0-&7F: X + 256 * Y is a time limit in centiseconds, and the call
  waits up to that long for any key.

OSBYTE &79's X is different: an internal key number EOR &80, rendered
as ``(255 - inkey_key_<name>) EOR 128``. Its Y is not involved.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.core.annotations import Align, Comment
from dasmos.core.format_hint import FormatHint
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer

BEEBASM = os.environ.get("BEEBASM") or shutil.which("beebasm")

LDX_IMM, LDY_IMM, LDA_IMM, LDX_ZP = 0xA2, 0xA0, 0xA9, 0xA6
JSR_OSBYTE = [0x20, 0xF4, 0xFF]
RTS = 0x60


def _ir(tmp_path, program):
    binpath = tmp_path / "p.bin"
    binpath.write_bytes(bytes(program))
    d = Disassembler.create(cpu="6502", environments=["acorn_mos"])
    d.load(binpath, 0x1000)
    d.entry(0x1000)
    return d, d.disassemble()


def _inline_at(ir, binary_addr):
    for ann in ir.annotations.get_for_align(binary_addr, Align.INLINE):
        if isinstance(ann, Comment):
            return ann.text
    return None


def _constants(d):
    return {(c.name, c.value) for c in d.constants}


# LDY #y ; LDX #x ; LDA #&81 ; JSR OSBYTE ; RTS — the JSR is at &1006 and
# the LDX operand at &1003.
def _osbyte_81(y, x):
    return [LDY_IMM, y, LDX_IMM, x, LDA_IMM, 0x81, *JSR_OSBYTE, RTS]


class TestKeyScan:

    def test_names_the_key(self, tmp_path):
        _d, ir = _ir(tmp_path, _osbyte_81(0xFF, 0xFE))
        assert _inline_at(ir, 0x1006) == "Test for ctrl key pressed"

    def test_x_is_the_inkey_number_itself(self, tmp_path):
        d, ir = _ir(tmp_path, _osbyte_81(0xFF, 0xFE))
        assert ("inkey_key_ctrl", 0xFE) in _constants(d)
        assert ir.format_hints.get_or_none(0x1003) is FormatHint.INKEY_NUMBER
        assert ir.expressions.get_or_none(0x1003) is None

    def test_x_unknown_describes_the_scan(self, tmp_path):
        # LDY #&FF ; LDX &70 ; LDA #&81 ; JSR OSBYTE
        _d, ir = _ir(
            tmp_path, [LDY_IMM, 0xFF, LDX_ZP, 0x70, LDA_IMM, 0x81, *JSR_OSBYTE, RTS],
        )
        assert _inline_at(ir, 0x1006) == (
            "Test whether the key with negative INKEY number X is pressed"
        )

    def test_x_zero_reads_the_os_version(self, tmp_path):
        _d, ir = _ir(tmp_path, _osbyte_81(0xFF, 0x00))
        assert _inline_at(ir, 0x1006) == "Read the OS version (INKEY(-256))"

    @pytest.mark.beebasm
    def test_beebasm_round_trip(self, tmp_path):
        program = _osbyte_81(0xFF, 0xFE)
        _d, ir = _ir(tmp_path, program)
        r = BeebasmRenderer()
        r.set_output_filename("OUT")
        text = str(ir.render(r))
        (tmp_path / "out.asm").write_text(text, encoding="utf-8")
        result = subprocess.run(
            [BEEBASM, "-i", "out.asm"], capture_output=True, text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"{text}\n{result.stderr}"
        assert "ldx #inkey_key_ctrl" in text
        assert (tmp_path / "OUT").read_bytes() == bytes(program)


class TestTimedWait:

    def test_is_not_read_as_a_key_scan(self, tmp_path):
        # The issue's Dunjunz case: LDX #&F4 ; LDY #1 waits up to &1F4
        # centiseconds. X's top bit is set, but Y says it's a time limit.
        program = [LDX_IMM, 0xF4, LDY_IMM, 0x01, LDA_IMM, 0x81, *JSR_OSBYTE, RTS]
        d, ir = _ir(tmp_path, program)
        assert not any(name.startswith("inkey_key_") for name, _ in _constants(d))
        assert ir.format_hints.get_or_none(0x1001) is None
        assert _inline_at(ir, 0x1006) == "Read a key, waiting up to 500 centiseconds"

    def test_time_limit_unknown(self, tmp_path):
        # LDX &70 ; LDY #2 ; LDA #&81 ; JSR OSBYTE
        program = [LDX_ZP, 0x70, LDY_IMM, 0x02, LDA_IMM, 0x81, *JSR_OSBYTE, RTS]
        _d, ir = _ir(tmp_path, program)
        assert _inline_at(ir, 0x1006) == (
            "Read a key, waiting up to the time limit in X and Y (centiseconds)"
        )


class TestYUnknown:

    def test_is_not_read_as_a_key_scan(self, tmp_path):
        # LDX #&FE ; LDA #&81 ; JSR OSBYTE, with Y set elsewhere.
        program = [LDX_IMM, 0xFE, LDA_IMM, 0x81, *JSR_OSBYTE, RTS]
        d, ir = _ir(tmp_path, program)
        assert not any(name.startswith("inkey_key_") for name, _ in _constants(d))
        assert ir.format_hints.get_or_none(0x1001) is None

    def test_describes_both_modes(self, tmp_path):
        program = [LDX_IMM, 0xFE, LDA_IMM, 0x81, *JSR_OSBYTE, RTS]
        _d, ir = _ir(tmp_path, program)
        assert _inline_at(ir, 0x1004) == (
            "Read a key within the time limit in X and Y, or with Y = &FF "
            "test for the key with negative INKEY number X"
        )


class TestOsbyte79Unchanged:

    def test_scan_code_form(self, tmp_path):
        # LDX #&81 ; LDA #&79 ; JSR OSBYTE — internal key 1 (CTRL) EOR &80.
        program = [LDX_IMM, 0x81, LDA_IMM, 0x79, *JSR_OSBYTE, RTS]
        d, ir = _ir(tmp_path, program)
        assert _inline_at(ir, 0x1004) == "Test for ctrl key pressed"
        assert ir.format_hints.get_or_none(0x1001) is FormatHint.INKEY
        assert ("inkey_key_ctrl", 0xFE) in _constants(d)
