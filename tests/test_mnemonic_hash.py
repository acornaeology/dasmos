"""The BBC BASIC II inline-assembler mnemonic-hash expressions.

BASIC 2's embedded 6502 assembler stores each mnemonic as a 15-bit
"packed name" hash — the low 5 bits of each of its three letters packed
MSB-first — split across two parallel byte tables (`asm_mnemonic_lo` /
`asm_mnemonic_hi`). Its disassembly driver (in the sibling `bbc-basic`
repo) renders each table byte not as a raw `equb` but as the *expression*
that recomputes it, so the listing documents the hash and reassembles to
the original ROM byte:

    (('L' AND &1F) * &400 + ('D' AND &1F) * &20 + ('A' AND &1F)) AND &FF

These exercise the whole expression system on a real, non-trivial case:
character literals, bitwise ``AND`` masks, multiplication, addition,
integer division (``DIV`` / ``/``), and grouping — and prove they render
and *assemble* correctly on both backends (beebasm's ``AND``/``DIV``/``&``
vs 64tass's ``&``/``/``/``$``). The load-bearing assertion is that the
assembled byte equals the hash computed independently in Python.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from dasmos.core.expr_parse import parse_expression
from dasmos.expr import Expr, char, group, string
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


# A representative slice of the BASIC 2 assembler's mnemonic set.
MNEMONICS = ["LDA", "STA", "JMP", "NOP", "BRK", "ROL", "CMP", "BEQ"]


def _packed_key(m: str) -> int:
    """The 15-bit packed-name key: low 5 bits of each letter, MSB-first."""
    return (
        ((ord(m[0]) & 0x1F) << 10)
        | ((ord(m[1]) & 0x1F) << 5)
        | (ord(m[2]) & 0x1F)
    )


def _hash_string(m: str, half: str) -> str:
    """The exact beebasm-dialect string the bbc-basic driver emits."""
    key = (
        f"(('{m[0]}' AND &1F) * &400 + ('{m[1]}' AND &1F) * &20 "
        f"+ ('{m[2]}' AND &1F))"
    )
    return f"{key} {'AND &FF' if half == 'lo' else 'DIV &100'}"


def _hash_dsl(m: str, half: str) -> Expr:
    """The same computation built with the neutral DSL (no strings)."""
    key = (
        (char(ord(m[0])) & 0x1F) * 0x400
        + (char(ord(m[1])) & 0x1F) * 0x20
        + (char(ord(m[2])) & 0x1F)
    )
    return (group(key) & 0xFF) if half == "lo" else (group(key) // 0x100)


def _hash_str_dsl(m: str, half: str) -> Expr:
    """The macro-friendly form: index a single mnemonic *string* rather
    than spell out three character literals. Constant-folds to exactly
    the same tree as :func:`_hash_dsl`."""
    s = string(m)
    key = (s[0] & 0x1F) * 0x400 + (s[1] & 0x1F) * 0x20 + (s[2] & 0x1F)
    return (group(key) & 0xFF) if half == "lo" else (group(key) // 0x100)


# ---------------------------------------------------------------------------
# Rendering (no assembler needed)
# ---------------------------------------------------------------------------

class TestRendering:
    def test_parsed_string_renders_per_backend(self):
        e = parse_expression(_hash_string("LDA", "lo"))
        assert BeebasmRenderer().render_expression(e, None) == (
            "(('L' AND &1f) * &0400 + ('D' AND &1f) * &20 "
            "+ ('A' AND &1f)) AND &ff"
        )
        assert Tass64Renderer().render_expression(e, None) == (
            "(('L' & $1f) * $0400 + ('D' & $1f) * $20 "
            "+ ('A' & $1f)) & $ff"
        )

    def test_integer_division_spelling_differs(self):
        e = parse_expression(_hash_string("LDA", "hi"))
        assert BeebasmRenderer().render_expression(e, None).endswith("DIV &0100")
        assert Tass64Renderer().render_expression(e, None).endswith("/ $0100")

    def test_dsl_and_parsed_render_identically(self):
        bee = BeebasmRenderer()
        bee_folded = BeebasmRenderer(fold_string_ops=True)
        for m in MNEMONICS:
            for half in ("lo", "hi"):
                base = bee.render_expression(parse_expression(_hash_string(m, half)), None)
                # The char-literal DSL matches the parsed dialect string.
                assert bee.render_expression(_hash_dsl(m, half), None) == base
                # The string-indexing DSL keeps "BRK" visible by default,
                # so it differs — but folds to the same char form.
                readable = bee.render_expression(_hash_str_dsl(m, half), None)
                assert f'"{m}"' in readable and readable != base
                assert bee_folded.render_expression(_hash_str_dsl(m, half), None) == base

    def test_string_form_keeps_mnemonic_visible(self):
        # 64tass renders the readable native form with the string intact.
        e = _hash_str_dsl("BRK", "lo")
        text = Tass64Renderer().render_expression(e, None)
        assert text == (
            '(("BRK"[0] & $1f) * $0400 + ("BRK"[1] & $1f) * $20 '
            '+ ("BRK"[2] & $1f)) & $ff'
        )


# ---------------------------------------------------------------------------
# Assemble-and-verify: the byte must equal the independently-computed hash
# ---------------------------------------------------------------------------

def _find(name: str, env: str) -> str | None:
    return (
        (os.environ.get(env) if os.environ.get(env)
         and os.path.isfile(os.environ[env]) else None)
        or shutil.which(name)
    )


BEEBASM = _find("beebasm", "BEEBASM")
TASS64 = _find("64tass", "TASS64")


def _assemble_beebasm(expr_text: str) -> int:
    td = Path(tempfile.mkdtemp())
    (td / "a.asm").write_text(
        f'    org 0\n    equb {expr_text}\n    save "o.bin", 0, 1\n'
    )
    r = subprocess.run([BEEBASM, "-i", str(td / "a.asm")],
                       capture_output=True, text=True, cwd=td)
    assert (td / "o.bin").exists(), f"beebasm failed: {r.stderr}"
    return (td / "o.bin").read_bytes()[0]


def _assemble_tass64(expr_text: str) -> int:
    td = Path(tempfile.mkdtemp())
    (td / "a.asm").write_text(f"* = 0\n.byte {expr_text}\n")
    r = subprocess.run([TASS64, "--nostart", "-o", str(td / "o.bin"),
                        str(td / "a.asm")],
                       capture_output=True, text=True, cwd=td)
    assert (td / "o.bin").exists(), f"64tass failed: {r.stderr}"
    return (td / "o.bin").read_bytes()[0]


@pytest.mark.beebasm
@pytest.mark.parametrize("m", MNEMONICS)
def test_hash_assembles_to_expected_byte_beebasm(m):
    key = _packed_key(m)
    render = BeebasmRenderer().render_expression
    assert _assemble_beebasm(render(parse_expression(_hash_string(m, "lo")), None)) \
        == (key & 0xFF)
    assert _assemble_beebasm(render(parse_expression(_hash_string(m, "hi")), None)) \
        == (key >> 8)
    # The DSL-built trees (char literals and string indexing) assemble to
    # the same bytes as the parsed string.
    for build in (_hash_dsl, _hash_str_dsl):
        assert _assemble_beebasm(render(build(m, "lo"), None)) == (key & 0xFF)
        assert _assemble_beebasm(render(build(m, "hi"), None)) == (key >> 8)


@pytest.mark.tass64
@pytest.mark.parametrize("m", MNEMONICS)
def test_hash_assembles_to_expected_byte_tass64(m):
    key = _packed_key(m)
    render = Tass64Renderer().render_expression
    assert _assemble_tass64(render(parse_expression(_hash_string(m, "lo")), None)) \
        == (key & 0xFF)
    assert _assemble_tass64(render(parse_expression(_hash_string(m, "hi")), None)) \
        == (key >> 8)
    for build in (_hash_dsl, _hash_str_dsl):
        assert _assemble_tass64(render(build(m, "lo"), None)) == (key & 0xFF)
        assert _assemble_tass64(render(build(m, "hi"), None)) == (key >> 8)
