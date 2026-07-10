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


@pytest.mark.beebasm
@pytest.mark.parametrize("half", ["lo", "hi"])
def test_macro_table_assembles_beebasm(half):
    ir, expected = _build_ir(half)
    text = str(ir.render(BeebasmRenderer(boundary_label_prefix="")))
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(text)
    r = subprocess.run([BEEBASM, "-i", str(d / "a.asm"), "-o", str(d / "o.bin")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    assert (d / "o.bin").read_bytes() == expected


@pytest.mark.tass64
@pytest.mark.parametrize("half", ["lo", "hi"])
def test_macro_table_assembles_tass64(half):
    ir, expected = _build_ir(half)
    text = str(ir.render(Tass64Renderer()))
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(text)
    r = subprocess.run([TASS64, "--nostart", "-o", str(d / "o.bin"), str(d / "a.asm")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    assert (d / "o.bin").read_bytes() == expected
