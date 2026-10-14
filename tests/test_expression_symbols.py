"""Every label an emitted expression names must be defined (#47).

An optional label is only given a definition (``name = &xxxx``) when
the listing references it. Expressions can reference a label by *name*
(a :class:`~dasmos.core.expr.Sym`, e.g. the ``acorn_mos`` environment's
``fscv+1`` alias for ``&021F``, or a driver's ``d.expr(addr, "ptr+1")``)
rather than by address. Such a use must count as a reference to the
named label, otherwise the listing says ``lda fscv + 1,x`` without
defining ``fscv`` and the assembler rejects it.
"""

import os
import re
import shutil
import subprocess

import pytest

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

# From the issue: LDA &021F,X (FSCV+1,X); NOP x3; RTS.
ISSUE_PROGRAM = bytes([0xBD, 0x1F, 0x02, 0xEA, 0xEA, 0xEA, 0x60])


def _disassemble(tmp_path, binary, *, environments=(), configure=None):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(binary)
    d = Disassembler.create("6502", environments=list(environments))
    d.load(binpath, 0x2000)
    d.entry(0x2000)
    if configure is not None:
        configure(d)
    return d.disassemble()


def _definitions(text, name):
    """The ``name = value`` definition lines for ``name``."""
    pattern = re.compile(rf"^{re.escape(name)}\s*=\s*(\S+)", re.MULTILINE)
    return pattern.findall(text)


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


class TestEnvironmentAliasDefinesItsBase:

    def test_offset_alias_alone_defines_base_label(self, tmp_path):
        ir = _disassemble(tmp_path, ISSUE_PROGRAM, environments=["acorn_mos"])
        text = str(ir.render(BeebasmRenderer()))
        assert "lda fscv + 1,x" in text
        assert _definitions(text, "fscv") == ["&021e"]

    def test_base_also_referenced_is_defined_once(self, tmp_path):
        # STA &021E,X as well: the definition was already emitted before
        # the fix; it must still appear exactly once.
        program = bytes([0xBD, 0x1F, 0x02, 0x9D, 0x1E, 0x02, 0x60])
        ir = _disassemble(tmp_path, program, environments=["acorn_mos"])
        text = str(ir.render(BeebasmRenderer()))
        assert _definitions(text, "fscv") == ["&021e"]

    def test_unreferenced_vectors_stay_undefined(self, tmp_path):
        # Only the label the expression names is pulled in — not every
        # optional label the environment registers.
        ir = _disassemble(tmp_path, ISSUE_PROGRAM, environments=["acorn_mos"])
        text = str(ir.render(BeebasmRenderer()))
        assert _definitions(text, "evntv") == []
        assert _definitions(text, "brkv") == []

    def test_64tass_defines_base_label(self, tmp_path):
        ir = _disassemble(tmp_path, ISSUE_PROGRAM, environments=["acorn_mos"])
        text = str(ir.render(Tass64Renderer()))
        assert _definitions(text, "fscv") == ["$021e"]


class TestDriverExpressionDefinesNamedLabel:

    def _configure(self, d):
        d.optional_label(0x0070, "ptr")
        d.expr(0x2001, "ptr+1")

    def test_symbolic_operand_defines_optional_label(self, tmp_path):
        # LDA &71 rendered via a driver expression naming ``ptr``.
        ir = _disassemble(
            tmp_path, bytes([0xA5, 0x71, 0x60]), configure=self._configure,
        )
        text = str(ir.render(BeebasmRenderer()))
        assert "lda ptr+1" in text or "lda ptr + 1" in text
        assert _definitions(text, "ptr") == ["&70"]


@pytest.mark.beebasm
class TestBeebasmRoundTrip:

    def test_issue_program_round_trips(self, tmp_path):
        ir = _disassemble(tmp_path, ISSUE_PROGRAM, environments=["acorn_mos"])
        text = str(ir.render(BeebasmRenderer()))
        assert _beebasm_round_trip(tmp_path, text) == ISSUE_PROGRAM

    def test_driver_expression_round_trips(self, tmp_path):
        program = bytes([0xA5, 0x71, 0x60])
        ir = _disassemble(
            tmp_path, program,
            configure=TestDriverExpressionDefinesNamedLabel()._configure,
        )
        text = str(ir.render(BeebasmRenderer()))
        assert _beebasm_round_trip(tmp_path, text) == program


@pytest.mark.tass64
class TestTass64RoundTrip:

    def test_issue_program_round_trips(self, tmp_path):
        ir = _disassemble(tmp_path, ISSUE_PROGRAM, environments=["acorn_mos"])
        text = str(ir.render(Tass64Renderer()))
        assert _tass64_round_trip(tmp_path, text) == ISSUE_PROGRAM
