"""Exhaustive coverage of every expression operator.

One row per operator, checked three ways:

- **construction** — the DSL / Python operator builds the expected node;
- **rendering** — it renders the expected token on beebasm and 64tass;
- **assembly** — with constant operands it assembles to a known byte on
  each real assembler (gated by ``@pytest.mark.beebasm`` / ``tass64``).

If an operator is added to :mod:`dasmos.core.expr`, add a row here.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from dasmos.core.expr import Binary, BinOp, Unary, UnaryOp
from dasmos.expr import hexlit, hi, lo
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


# name, expr-builder, expected assembled byte, beebasm token, 64tass token.
# The builder uses the public DSL / Python operators; masks keep the
# result in 0..255 so it fits an EQUB / .byte.
BINARY_OPS = [
    ("add", lambda: hexlit(0x30) + hexlit(0x05), 0x35, "+", "+"),
    ("sub", lambda: hexlit(0x30) - hexlit(0x05), 0x2B, "-", "-"),
    ("mul", lambda: hexlit(0x08) * hexlit(0x03), 0x18, "*", "*"),
    ("div", lambda: hexlit(0x40) // hexlit(0x10), 0x04, "DIV", "/"),
    ("mod", lambda: hexlit(0x0A) % hexlit(0x03), 0x01, "MOD", "%"),
    ("and", lambda: hexlit(0xFF) & hexlit(0x0F), 0x0F, "AND", "&"),
    ("or",  lambda: hexlit(0x30) | hexlit(0x0F), 0x3F, "OR", "|"),
    ("xor", lambda: hexlit(0xFF) ^ hexlit(0x0F), 0xF0, "EOR", "^"),
    ("shl", lambda: (hexlit(0x08) << 3) & 0xFF, 0x40, "<<", "<<"),
    ("shr", lambda: hexlit(0x0140) >> 4, 0x14, ">>", ">>"),
]

# name, builder, expected byte, beebasm rendering fragment, 64tass fragment.
UNARY_OPS = [
    ("neg", lambda: (-hexlit(0x01)) & 0xFF, 0xFF, "-&01", "-$01"),
    ("pos", lambda: +hexlit(0x05), 0x05, "+&05", "+$05"),
    ("invert", lambda: (~hexlit(0x0F)) & 0xFF, 0xF0, "NOT(&0f)", "~($0f)"),
    ("lowbyte", lambda: lo(hexlit(0x1234)), 0x34, "<(&1234)", "<($1234)"),
    ("highbyte", lambda: hi(hexlit(0x1234)), 0x12, ">(&1234)", ">($1234)"),
]

_BINOP = {
    "add": BinOp.ADD, "sub": BinOp.SUB, "mul": BinOp.MUL, "div": BinOp.DIV,
    "mod": BinOp.MOD, "and": BinOp.AND, "or": BinOp.OR, "xor": BinOp.XOR,
    "shl": BinOp.SHL, "shr": BinOp.SHR,
}


# ---------------------------------------------------------------------------
# Construction — the operator builds the right node
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [n for n, *_ in BINARY_OPS])
def test_binary_operator_builds_node(name):
    # The top node of each builder is the expected BinOp (some masks wrap
    # it — check the underlying operator is present in the tree).
    e = dict((n, b) for n, b, *_ in BINARY_OPS)[name]()
    found = _find_binops(e)
    assert _BINOP[name] in found


def test_unary_operators_build_nodes():
    assert isinstance((-hexlit(1)), Unary) and (-hexlit(1)).op is UnaryOp.NEG
    assert (+hexlit(1)).op is UnaryOp.POS
    assert (~hexlit(1)).op is UnaryOp.INVERT
    assert lo(hexlit(1)).op is UnaryOp.LOWBYTE
    assert hi(hexlit(1)).op is UnaryOp.HIGHBYTE


def _find_binops(e):
    out = set()
    if isinstance(e, Binary):
        out.add(e.op)
        out |= _find_binops(e.left) | _find_binops(e.right)
    if isinstance(e, Unary):
        out |= _find_binops(e.operand)
    return out


# ---------------------------------------------------------------------------
# Rendering — expected token per backend (no assembler needed)
# ---------------------------------------------------------------------------

class TestRendering:
    def setup_method(self):
        self.bee = BeebasmRenderer()
        self.tass = Tass64Renderer()

    @pytest.mark.parametrize("name,builder,_byte,btok,ttok", BINARY_OPS)
    def test_binary_token(self, name, builder, _byte, btok, ttok):
        e = builder()
        assert f" {btok} " in self.bee.render_expression(e, None)
        assert f" {ttok} " in self.tass.render_expression(e, None)

    @pytest.mark.parametrize("name,builder,_byte,bfrag,tfrag", UNARY_OPS)
    def test_unary_fragment(self, name, builder, _byte, bfrag, tfrag):
        e = builder()
        assert bfrag in self.bee.render_expression(e, None)
        assert tfrag in self.tass.render_expression(e, None)

    def test_bank_byte_is_unsupported_on_6502_backends(self):
        # BANKBYTE is a reserved 65816 concept with no 6502 spelling.
        e = Unary(UnaryOp.BANKBYTE, hexlit(0x12))
        for r in (self.bee, self.tass):
            with pytest.raises(NotImplementedError):
                r.render_expression(e, None)


# ---------------------------------------------------------------------------
# Assembly — the strong guarantee: each operator assembles to a known byte
# ---------------------------------------------------------------------------

def _find(name, env):
    e = os.environ.get(env)
    if e and os.path.isfile(e):
        return e
    return shutil.which(name)


BEEBASM = _find("beebasm", "BEEBASM")
TASS64 = _find("64tass", "TASS64")


def _assemble_beebasm(operand_text):
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(f'org 0\nequb {operand_text}\nsave "o.bin", 0, 1\n')
    r = subprocess.run([BEEBASM, "-i", str(d / "a.asm")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    return (d / "o.bin").read_bytes()[0]


def _assemble_tass64(operand_text):
    d = Path(tempfile.mkdtemp())
    (d / "a.asm").write_text(f"* = 0\n.byte {operand_text}\n")
    r = subprocess.run([TASS64, "--nostart", "-o", str(d / "o.bin"), str(d / "a.asm")],
                       capture_output=True, text=True, cwd=d)
    assert (d / "o.bin").exists(), r.stderr
    return (d / "o.bin").read_bytes()[0]


@pytest.mark.beebasm
@pytest.mark.parametrize("name,builder,expected",
                         [(n, b, x) for n, b, x, *_ in BINARY_OPS + UNARY_OPS])
def test_operator_assembles_beebasm(name, builder, expected):
    text = BeebasmRenderer().render_expression(builder(), None)
    assert _assemble_beebasm(text) == expected


@pytest.mark.tass64
@pytest.mark.parametrize("name,builder,expected",
                         [(n, b, x) for n, b, x, *_ in BINARY_OPS + UNARY_OPS])
def test_operator_assembles_tass64(name, builder, expected):
    text = Tass64Renderer().render_expression(builder(), None)
    assert _assemble_tass64(text) == expected
