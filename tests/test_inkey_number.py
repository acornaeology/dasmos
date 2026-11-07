"""Bytes holding negative INKEY numbers render as their key's name.

A negative INKEY number is the byte BASIC's ``INKEY(-n)`` and OSBYTE &81
with Y = &FF take in X: -2 (&FE) for CTRL, -103 (&99) for ','.
:meth:`~dasmos.Disassembler.inkey_number` declares one or more such bytes,
an immediate operand or a table, and they render as
``inkey_key_<name>``. :meth:`~dasmos.Disassembler.inkey_code` is its
OSBYTE &79 counterpart, whose byte is the internal key number EOR &80.

Either way the disassembly defines the ``inkey_key_<name>`` constants it
uses, so the source assembles without the driver defining them.
"""

import os
import shutil
import subprocess
import warnings

import pytest

from dasmos.core.format_hint import FormatHint
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _find(var, name):
    env = os.environ.get(var)
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which(name)


BEEBASM = _find("BEEBASM", "beebasm")
TASS64 = _find("TASS64", "64tass")

LDX_IMM, LDA_IMM, RTS = 0xA2, 0xA9, 0x60

# &1000 LDX #&FE ; &1002 LDA #&99 ; &1004 RTS ; &1005 table: ',' '.' 'A' 'Z'
PROGRAM = bytes([LDX_IMM, 0xFE, LDA_IMM, 0x99, RTS, 0x99, 0x98, 0xBE, 0x9E])
TABLE_ADDR = 0x1005


def _disassembler(tmp_path, program=PROGRAM, environments=()):
    binpath = tmp_path / "p.bin"
    binpath.write_bytes(program)
    d = Disassembler.create(cpu="6502", environments=list(environments))
    d.load(binpath, 0x1000)
    d.entry(0x1000)
    return d


def _keyed(d):
    d.inkey_number(0x1001)
    d.inkey_number(0x1003)
    d.byte(TABLE_ADDR, 4)
    d.inkey_number(TABLE_ADDR, 4)
    return d


def _beebasm_text(ir):
    r = BeebasmRenderer()
    r.set_output_filename("OUT")
    return str(ir.render(r))


def _constants(ir):
    return {c.name: c.value for c in ir.constants}


class TestInkeyNumber:

    def test_marks_each_byte(self, tmp_path):
        ir = _keyed(_disassembler(tmp_path)).disassemble()
        for addr in (0x1001, 0x1003, *range(TABLE_ADDR, TABLE_ADDR + 4)):
            assert ir.format_hints.get_or_none(addr) is FormatHint.INKEY_NUMBER

    def test_count_defaults_to_one(self, tmp_path):
        d = _disassembler(tmp_path)
        d.byte(TABLE_ADDR, 4)
        d.inkey_number(TABLE_ADDR)
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(TABLE_ADDR) is FormatHint.INKEY_NUMBER
        assert ir.format_hints.get_or_none(TABLE_ADDR + 1) is None

    def test_immediate_operands_render_as_names(self, tmp_path):
        text = _beebasm_text(_keyed(_disassembler(tmp_path)).disassemble())
        assert "ldx #inkey_key_ctrl" in text
        assert "lda #inkey_key_comma" in text

    def test_table_renders_as_names(self, tmp_path):
        text = _beebasm_text(_keyed(_disassembler(tmp_path)).disassemble())
        assert (
            "equb inkey_key_comma, inkey_key_full_stop, inkey_key_a, inkey_key_z"
            in text
        )

    def test_defines_the_constants_it_uses(self, tmp_path):
        ir = _keyed(_disassembler(tmp_path)).disassemble()
        assert _constants(ir) == {
            "inkey_key_ctrl": 0xFE,
            "inkey_key_comma": 0x99,
            "inkey_key_full_stop": 0x98,
            "inkey_key_a": 0xBE,
            "inkey_key_z": 0x9E,
        }

    def test_needs_no_environment(self, tmp_path):
        # The key names are Acorn's, but declaring them is enough: the
        # acorn_mos environment need not be in use.
        text = _beebasm_text(_keyed(_disassembler(tmp_path)).disassemble())
        assert "inkey_key_ctrl" in text

    def test_unnamed_byte_falls_back_to_hex_with_a_warning(self, tmp_path):
        # &55 is not a negative INKEY number.
        d = _disassembler(tmp_path, bytes([LDX_IMM, 0x55, RTS]))
        d.inkey_number(0x1001)
        ir = d.disassemble()
        with pytest.warns(UserWarning, match="INKEY number"):
            text = _beebasm_text(ir)
        assert "ldx #&55" in text
        assert _constants(ir) == {}

    def test_explicit_expression_wins_and_defines_nothing(self, tmp_path):
        d = _disassembler(tmp_path, bytes([LDX_IMM, 0xFE, RTS]))
        d.inkey_number(0x1001)
        d.expr(0x1001, "&FE")
        ir = d.disassemble()
        assert "ldx #&fe" in _beebasm_text(ir).lower()
        assert "inkey_key_ctrl" not in _constants(ir)

    def test_driver_constant_is_not_duplicated(self, tmp_path):
        d = _disassembler(tmp_path, bytes([LDX_IMM, 0xFE, RTS]))
        d.constant(0xFE, "inkey_key_ctrl", "CTRL")
        d.inkey_number(0x1001)
        ir = d.disassemble()
        assert [c.name for c in ir.constants].count("inkey_key_ctrl") == 1

    def test_json_surfaces_the_hint_and_the_name(self, tmp_path):
        data = _keyed(_disassembler(tmp_path)).disassemble().render(JsonRenderer()).data
        items = {it["addr"]: it for it in data["items"]}
        assert items[0x1000]["operand"] == "#inkey_key_ctrl"
        assert items[0x1000]["format_hint"] == "inkey_number"
        assert items[TABLE_ADDR]["format_hints"] == ["inkey_number"] * 4

    def test_json_hint_stays_off_a_one_byte_instruction(self, tmp_path):
        # The RTS at &1004 is followed by the hinted table: the hint on
        # &1005 belongs to the table, not to the RTS, which has no
        # operand byte.
        data = _keyed(_disassembler(tmp_path)).disassemble().render(JsonRenderer()).data
        rts = next(it for it in data["items"] if it["addr"] == 0x1004)
        assert "format_hint" not in rts

    @pytest.mark.beebasm
    def test_beebasm_round_trip(self, tmp_path):
        text = _beebasm_text(_keyed(_disassembler(tmp_path)).disassemble())
        (tmp_path / "out.asm").write_text(text, encoding="utf-8")
        result = subprocess.run(
            [BEEBASM, "-i", "out.asm"], capture_output=True, text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"{text}\n{result.stderr}"
        assert (tmp_path / "OUT").read_bytes() == PROGRAM

    @pytest.mark.tass64
    def test_tass64_round_trip(self, tmp_path):
        ir = _keyed(_disassembler(tmp_path)).disassemble()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            text = str(ir.render(Tass64Renderer()))
        (tmp_path / "out.asm").write_text(text, encoding="utf-8")
        result = subprocess.run(
            [TASS64, "--nostart", "-q", "-o", "OUT", "out.asm"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"{text}\n{result.stderr}"
        assert "inkey_key_ctrl" in text
        assert (tmp_path / "OUT").read_bytes() == PROGRAM


class TestInkeyCodeDefinesItsConstant:
    """``inkey_code`` used to reference ``inkey_key_<name>`` without
    defining it unless an OSBYTE &79 call nearby had."""

    # LDX #&81 ; RTS — internal key 1 (CTRL) EOR &80, no OSBYTE call.
    PROGRAM = bytes([LDX_IMM, 0x81, RTS])

    def test_defines_the_constant(self, tmp_path):
        d = _disassembler(tmp_path, self.PROGRAM)
        d.inkey_code(0x1001)
        assert _constants(d.disassemble()) == {"inkey_key_ctrl": 0xFE}

    @pytest.mark.beebasm
    def test_beebasm_round_trip(self, tmp_path):
        d = _disassembler(tmp_path, self.PROGRAM)
        d.inkey_code(0x1001)
        text = _beebasm_text(d.disassemble())
        (tmp_path / "out.asm").write_text(text, encoding="utf-8")
        result = subprocess.run(
            [BEEBASM, "-i", "out.asm"], capture_output=True, text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, f"{text}\n{result.stderr}"
        assert "ldx #(255 - inkey_key_ctrl) EOR 128" in text
        assert (tmp_path / "OUT").read_bytes() == self.PROGRAM


class TestOsbyteHooksUseTheHints:

    def test_osbyte_81_key_test_is_an_inkey_number(self, tmp_path):
        # LDY #&FF ; LDX #&FE ; LDA #&81 ; JSR OSBYTE ; RTS
        program = bytes([0xA0, 0xFF, LDX_IMM, 0xFE, LDA_IMM, 0x81,
                         0x20, 0xF4, 0xFF, RTS])
        ir = _disassembler(tmp_path, program, ["acorn_mos"]).disassemble()
        assert ir.format_hints.get_or_none(0x1003) is FormatHint.INKEY_NUMBER
        assert ir.expressions.get_or_none(0x1003) is None
        assert "ldx #inkey_key_ctrl" in _beebasm_text(ir)
        assert _constants(ir)["inkey_key_ctrl"] == 0xFE

    def test_osbyte_79_key_test_is_an_inkey_code(self, tmp_path):
        # LDX #&81 ; LDA #&79 ; JSR OSBYTE ; RTS
        program = bytes([LDX_IMM, 0x81, LDA_IMM, 0x79, 0x20, 0xF4, 0xFF, RTS])
        ir = _disassembler(tmp_path, program, ["acorn_mos"]).disassemble()
        assert ir.format_hints.get_or_none(0x1001) is FormatHint.INKEY
        assert [c.name for c in ir.constants].count("inkey_key_ctrl") == 1
