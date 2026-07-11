"""Backend-agnostic macros: definition + invocation rendered per backend.

A driver defines a macro once (``d.define_macro``) and uses it per table
entry. dasmos renders it in each assembler's own macro construct — a
64tass value ``.sfunction`` used inline in ``.byte pack("LDA")``, or a
beebasm code ``MACRO`` that emits the byte, invoked ``pack "LDA"`` per
line — because 64tass has value-returning functions and beebasm does not.
The load-bearing check is that both forms *assemble* to the identical
bytes.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from dasmos.disassembler import Disassembler
from dasmos.exceptions import MacroRenderError
from dasmos.expr import MacroCall, group, param
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


MNEMONICS = ["LDA", "STA", "BRK", "NOP", "CMP", "ROL"]


def _packed(m: str) -> int:
    return ((ord(m[0]) & 0x1F) << 10) | ((ord(m[1]) & 0x1F) << 5) | (ord(m[2]) & 0x1F)


def _build_ir(half: str):
    """Disassemble a lo/hi hash table and register a `pack` macro
    invocation for every byte."""
    data = bytes(
        (_packed(m) & 0xFF) if half == "lo" else (_packed(m) >> 8)
        for m in MNEMONICS
    )
    p = Path(tempfile.mktemp())
    p.write_bytes(data)
    d = Disassembler.create(cpu="6502")
    d.load(p, 0x2000)
    m = param("mnem")
    key = group(
        ((m[0] & 0x1F) * 0x400) + ((m[1] & 0x1F) * 0x20) + (m[2] & 0x1F)
    )
    body = (key & 0xFF) if half == "lo" else (key // 0x100)
    name = f"pack_{half}"
    pack = d.define_macro(name, ["mnem"], body)
    d.byte(0x2000, len(MNEMONICS))
    for i, mn in enumerate(MNEMONICS):
        d.expr(0x2000 + i, pack(mn))
    return d.disassemble(), data


# ---------------------------------------------------------------------------
# API + node
# ---------------------------------------------------------------------------

class TestApi:
    def test_define_macro_returns_call_builder(self):
        d = Disassembler.create(cpu="6502")
        pack = d.define_macro("pack", ["m"], param("m")[0])
        call = pack("LDA")
        assert isinstance(call, MacroCall)
        assert call.name == "pack"
        assert "pack" in d.macros
        assert d.macros["pack"].params == ("m",)


# ---------------------------------------------------------------------------
# Rendering shape
# ---------------------------------------------------------------------------

class TestRenderingShape:
    def test_beebasm_emits_code_macro_and_statement_calls(self):
        ir, _ = _build_ir("lo")
        text = str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
        assert "MACRO pack_lo mnem" in text
        assert "ENDMACRO" in text
        assert "ASC(MID$(mnem, 1, 1))" in text  # string index in the body
        # Each entry is its own invocation line, mnemonic visible.
        assert '    pack_lo "LDA"' in text
        assert '    pack_lo "BRK"' in text
        # Not an inline value call.
        assert 'equb pack_lo("LDA")' not in text.lower()

    def test_tass64_emits_value_function_and_inline_calls(self):
        ir, _ = _build_ir("lo")
        text = str(ir.render(Tass64Renderer()))
        assert "pack_lo .sfunction mnem," in text
        assert 'mnem[0]' in text  # 64tass native string indexing
        # The invocations are values inside a single .byte directive.
        assert '.byte pack_lo("LDA"), pack_lo("STA"), pack_lo("BRK")' in text

    def test_hi_half_uses_integer_division_per_backend(self):
        ir_b, _ = _build_ir("hi")
        assert "DIV &0100" in str(ir_b.render(BeebasmRenderer(boundary_label_prefix="")))
        ir_t, _ = _build_ir("hi")
        assert "/ $0100" in str(ir_t.render(Tass64Renderer()))


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

class TestJson:
    def test_macros_section_and_call_nodes(self):
        ir, _ = _build_ir("lo")
        data = ir.render(JsonRenderer()).data
        macros = data["macros"]
        assert len(macros) == 1
        assert macros[0]["name"] == "pack_lo"
        assert macros[0]["params"] == ["mnem"]
        assert macros[0]["emit"] == "byte"
        # The body tree contains a param leaf and a string-index op.
        def _walk(node):
            yield node
            if isinstance(node, dict):
                for v in node.values():
                    yield from _walk(v)
        nodes = list(_walk(macros[0]["body"]["tree"]))
        assert {"param": "mnem"} in nodes
        assert any(isinstance(n, dict) and n.get("op") == "str_index" for n in nodes)
        # Each table item carries the macro call structurally.
        item = data["items"][0]
        assert item["expressions"][0]["tree"] == {
            "macro_call": "pack_lo", "args": [{"str": "LDA"}],
        }
        assert item["expressions"][0]["text"] == 'pack_lo("LDA")'

    def test_body_text_is_precedence_safe(self):
        # Regression: the JSON body ``text`` must keep the inner
        # (param AND mask) parentheses and spell integer division ``DIV``,
        # so it re-parses to the same value (not ``AND &1f * &400`` or a
        # real-division ``/``).
        ir, _ = _build_ir("hi")   # hi half uses integer division
        body_text = ir.render(JsonRenderer()).data["macros"][0]["body"]["text"]
        assert "(mnem[0] AND &1f)" in body_text     # inner parens kept
        assert " DIV " in body_text                 # integer division
        assert " / " not in body_text


# ---------------------------------------------------------------------------
# Assemble-and-verify
# ---------------------------------------------------------------------------

def _find(name, env):
    e = os.environ.get(env)
    if e and os.path.isfile(e):
        return e
    return shutil.which(name)


BEEBASM = _find("beebasm", "BEEBASM")
TASS64 = _find("64tass", "TASS64")


def _assemble_beebasm(text: str) -> bytes:
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(text)
    r = subprocess.run([BEEBASM, "-i", str(d / "a.asm"), "-o", str(d / "o.bin")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    return (d / "o.bin").read_bytes()


def _assemble_tass64(text: str) -> bytes:
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(text)
    r = subprocess.run([TASS64, "--nostart", "-o", str(d / "o.bin"), str(d / "a.asm")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    return (d / "o.bin").read_bytes()


@pytest.mark.beebasm
@pytest.mark.parametrize("half", ["lo", "hi"])
def test_macro_table_assembles_beebasm(half):
    ir, expected = _build_ir(half)
    text = str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
    assert _assemble_beebasm(text) == expected


@pytest.mark.tass64
@pytest.mark.parametrize("half", ["lo", "hi"])
def test_macro_table_assembles_tass64(half):
    ir, expected = _build_ir(half)
    assert _assemble_tass64(str(ir.render(Tass64Renderer()))) == expected


# ---------------------------------------------------------------------------
# Multiple parameters, word emit, and non-string arguments
# ---------------------------------------------------------------------------

def _mk(data: bytes, load: int = 0x2000):
    p = Path(tempfile.mktemp())
    p.write_bytes(data)
    d = Disassembler.create(cpu="6502")
    d.load(p, load)
    return d


def _build_word_macro():
    """A two-parameter, word-valued macro: mkword(hi, lo) -> hi*256 + lo,
    registered over a Word item so it emits EQUW / .word."""
    d = _mk(bytes([0x34, 0x12, 0x78, 0x56]))  # words 0x1234, 0x5678
    a, b = param("a"), param("b")
    mkword = d.define_macro("mkword", ["a", "b"], a * 0x100 + b, emit="word")
    d.word(0x2000, length=4)
    d.expr(0x2000, mkword(0x12, 0x34))   # int args
    d.expr(0x2002, mkword(0x56, 0x78))
    return d.disassemble(), bytes([0x34, 0x12, 0x78, 0x56])


class TestMultipleParamsAndWord:
    def test_two_param_word_macro_shape(self):
        ir, _ = _build_word_macro()
        bee = str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
        assert "MACRO mkword a, b" in bee          # two named params
        assert "equw" in bee                        # word emit
        assert "mkword &12, &34" in bee             # int args, statement form
        tass = str(ir.render(Tass64Renderer()))
        assert "mkword .sfunction a, b," in tass
        assert ".word mkword($12, $34), mkword($56, $78)" in tass

    @pytest.mark.beebasm
    def test_word_macro_assembles_beebasm(self):
        ir, expected = _build_word_macro()
        assert _assemble_beebasm(
            str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
        ) == expected

    @pytest.mark.tass64
    def test_word_macro_assembles_tass64(self):
        ir, expected = _build_word_macro()
        assert _assemble_tass64(str(ir.render(Tass64Renderer()))) == expected


# ---------------------------------------------------------------------------
# Several macros in one output
# ---------------------------------------------------------------------------

class TestMultipleMacros:
    def _build(self):
        d = _mk(bytes([0x0A, 0x0B]))
        x = param("x")
        lo_m = d.define_macro("lo_nibble", ["x"], x & 0x0F)
        hi_m = d.define_macro("hi_nibble", ["x"], (x >> 4) & 0x0F)
        d.byte(0x2000, 2)
        d.expr(0x2000, lo_m(0x0A))
        d.expr(0x2001, hi_m(0xB0))
        return d.disassemble()

    def test_both_definitions_emitted_once(self):
        text = str(self._build().render(BeebasmRenderer(boundary_label_prefix="")))
        assert text.count("MACRO lo_nibble") == 1
        assert text.count("MACRO hi_nibble") == 1

    @pytest.mark.beebasm
    def test_assembles_beebasm(self):
        text = str(self._build().render(BeebasmRenderer(boundary_label_prefix="")))
        assert _assemble_beebasm(text) == bytes([0x0A, 0x0B])

    @pytest.mark.tass64
    def test_assembles_tass64(self):
        assert _assemble_tass64(str(self._build().render(Tass64Renderer()))) \
            == bytes([0x0A, 0x0B])


class TestDefinitionEmittedOnceRegardlessOfUses:
    def test_one_definition_for_many_invocations(self):
        d = _mk(bytes([0x01, 0x01, 0x01, 0x01]))
        x = param("x")
        inc = d.define_macro("inc", ["x"], x & 0xFF)
        d.byte(0x2000, 4)
        for i in range(4):
            d.expr(0x2000 + i, inc(1))
        text = str(d.disassemble().render(BeebasmRenderer(boundary_label_prefix="")))
        assert text.count("MACRO inc") == 1
        # int arg 1 renders as the small-int decimal ``1`` (AUTO radix).
        assert text.count("    inc 1") == 4          # four invocation lines


# ---------------------------------------------------------------------------
# Macro used as a value (operand / nested) — backend-dependent
# ---------------------------------------------------------------------------

class TestMacroAsOperand:
    def _build(self):
        d = _mk(bytes([0xA9, 0x00, 0x60]))   # lda #0 : rts
        d.entry(0x2000)
        m = param("mnem")
        lobyte = d.define_macro("lobyte", ["mnem"], m[0] & 0x1F)
        d.expr(0x2001, lobyte("LDA"))        # operand at &2001
        return d

    def test_tass64_inlines_the_value(self):
        # 64tass has value functions, so a macro call works as an operand.
        text = str(self._build().disassemble().render(Tass64Renderer()))
        assert 'lda #lobyte("LDA")' in text

    @pytest.mark.tass64
    def test_tass64_operand_assembles(self):
        text = str(self._build().disassemble().render(Tass64Renderer()))
        # lda #<value> : the operand is the second byte (after the opcode).
        assert _assemble_tass64(text)[1] == (ord("L") & 0x1F)

    def test_beebasm_raises_clear_error(self):
        # beebasm has no value function, so a macro can't be an operand —
        # it must fail with an actionable error, not an internal crash.
        ir = self._build().disassemble()
        with pytest.raises(MacroRenderError, match="value"):
            str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
