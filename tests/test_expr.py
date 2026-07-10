"""Tests for the assembler-neutral expression system.

Covers (a) the DSL / operator overloads that build trees, (b) rendering
a tree to beebasm and 64tass syntax — including per-backend operator
tokens and precedence-driven parenthesisation — and (c) `Ref`
resolution against a real IR.
"""

import pytest

from dasmos.disassembler import Disassembler
from dasmos.expr import (
    Binary,
    BinOp,
    Int,
    Radix,
    Raw,
    Ref,
    Sym,
    Unary,
    UnaryOp,
    char,
    declit,
    hexlit,
    hi,
    lo,
    ref,
    sym,
    as_expr,
)
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


# ---------------------------------------------------------------------------
# Construction — operator overloads build the expected tree
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_sub_of_ref_and_int(self):
        e = ref(0x9000) - 1
        assert e == Binary(BinOp.SUB, Ref(0x9000), Int(1, Radix.AUTO))

    def test_int_on_the_left_uses_reflected_op(self):
        e = 255 - ref(0x70)
        assert e == Binary(BinOp.SUB, Int(255), Ref(0x70))

    def test_bitwise_and_xor(self):
        assert (sym("a") & 0xFF) == Binary(BinOp.AND, Sym("a"), Int(0xFF))
        assert (sym("a") ^ 128) == Binary(BinOp.XOR, Sym("a"), Int(128))

    def test_byte_selects(self):
        assert lo(sym("x")) == Unary(UnaryOp.LOWBYTE, Sym("x"))
        assert hi(ref(0x8000)) == Unary(UnaryOp.HIGHBYTE, Ref(0x8000))

    def test_radix_helpers(self):
        assert hexlit(0x81) == Int(0x81, Radix.HEX)
        assert declit(10) == Int(10, Radix.DEC)
        assert char(0x41) == Int(0x41, Radix.CHAR)

    def test_as_expr_coercion(self):
        assert as_expr("foo-1") == Raw("foo-1")
        assert as_expr(5) == Int(5)
        assert as_expr(ref(0x10)) == Ref(0x10)

    def test_nodes_are_hashable_and_frozen(self):
        {ref(0x10), sym("a"), Int(1)}  # hashable
        with pytest.raises(Exception):
            ref(0x10).runtime_addr = 5  # frozen


# ---------------------------------------------------------------------------
# Rendering — Sym/Int trees need no IR
# ---------------------------------------------------------------------------

class TestRendering:
    def setup_method(self):
        self.bee = BeebasmRenderer()
        self.tass = Tass64Renderer()

    def r_bee(self, e):
        return self.bee.render_expression(e, None)

    def r_tass(self, e):
        return self.tass.render_expression(e, None)

    def test_hex_literal_per_backend(self):
        assert self.r_bee(hexlit(0x81)) == "&81"
        assert self.r_tass(hexlit(0x81)) == "$81"

    def test_auto_radix_small_decimal_else_hex(self):
        assert self.r_bee(Int(5)) == "5"
        assert self.r_bee(Int(0x81)) == "&81"
        assert self.r_tass(Int(0x81)) == "$81"

    def test_simple_subtraction(self):
        assert self.r_bee(sym("foo") - 1) == "foo - 1"
        assert self.r_tass(sym("foo") - 1) == "foo - 1"

    def test_bitwise_tokens_differ(self):
        assert self.r_bee(sym("a") & hexlit(0xFF)) == "a AND &ff"
        assert self.r_tass(sym("a") & hexlit(0xFF)) == "a & $ff"
        assert self.r_bee(sym("a") ^ sym("b")) == "a EOR b"
        assert self.r_tass(sym("a") ^ sym("b")) == "a ^ b"

    def test_byte_select_parenthesises_operand(self):
        assert self.r_bee(lo(sym("x") - 1)) == "<(x - 1)"
        assert self.r_tass(hi(sym("x") - 1)) == ">(x - 1)"

    def test_mask_needs_no_parens_by_precedence(self):
        # AND binds looser than '-' in BOTH assemblers, so (a-b) AND c
        # renders without parens and still means (a-b) AND c.
        e = (sym("a") - sym("b")) & hexlit(0xFF)
        assert self.r_bee(e) == "a - b AND &ff"
        assert self.r_tass(e) == "a - b & $ff"

    def test_inkey_form_is_backend_neutral(self):
        # declit keeps 255/128 decimal (AUTO radix would render >9 as
        # hex). EOR/^ binds looser than '-', so the subtraction needs no
        # parens yet still evaluates as (255 - k) EOR 128.
        e = (declit(255) - sym("k")) ^ declit(128)
        assert self.r_bee(e) == "255 - k EOR 128"
        assert self.r_tass(e) == "255 - k ^ 128"

    def test_right_associativity_forces_parens(self):
        # a - (b - c): the right child of a left-assoc '-' at equal
        # precedence must be parenthesised to preserve the value.
        e = sym("a") - (sym("b") - sym("c"))
        assert self.r_bee(e) == "a - (b - c)"
        assert self.r_tass(e) == "a - (b - c)"

    def test_left_associativity_needs_no_parens(self):
        e = sym("a") - sym("b") - sym("c")   # (a - b) - c
        assert self.r_bee(e) == "a - b - c"

    def test_raw_node_renders_verbatim(self):
        # Raw is the rare fallback for a string the dialect parser could
        # not structure. It is emitted verbatim by both backends (the old
        # 64tass regex adapter was retired once the parser covered the
        # whole grammar); real driver strings parse to structured nodes
        # and never hit this path.
        assert self.r_bee(Raw("x-&81")) == "x-&81"
        assert self.r_tass(Raw("x-&81")) == "x-&81"


# ---------------------------------------------------------------------------
# Ref resolution against a real IR
# ---------------------------------------------------------------------------

class TestRefResolution:
    def _ir(self, tmp_path, configure):
        binary = bytes([0xEA] * 8)
        p = tmp_path / "in.bin"
        p.write_bytes(binary)
        d = Disassembler.create(cpu="6502")
        d.load(p, 0x2000)
        configure(d)
        return d.disassemble()

    def test_ref_resolves_to_label_name(self, tmp_path):
        ir = self._ir(tmp_path, lambda d: d.label(0x2004, "target"))
        bee = BeebasmRenderer()
        assert bee.render_expression(lo(ref(0x2004) - 1), ir) == "<(target - 1)"

    def test_ref_without_name_falls_back_to_hex(self, tmp_path):
        ir = self._ir(tmp_path, lambda d: None)
        bee = BeebasmRenderer()
        tass = Tass64Renderer()
        assert bee.render_expression(ref(0x2004), ir) == "&2004"
        assert tass.render_expression(ref(0x2004), ir) == "$2004"
