"""Tests for the beebasm/py8dis dialect expression parser.

The parser turns legacy driver-authored strings into structured
:class:`~dasmos.core.expr.Expr` trees at registration time, so existing
drivers migrate onto the neutral system with no edits. Anything outside
the grammar falls back to :class:`~dasmos.core.expr.Raw`.
"""

import pytest

from dasmos.core.expr import (
    BinOp,
    Binary,
    Group,
    Int,
    Radix,
    Raw,
    Sym,
    UnaryOp,
    hi,
    lo,
)
from dasmos.core.expr_parse import (
    ExprParseError,
    parse_expression,
    parse_or_raw,
)


class TestParse:
    def test_bare_identifier(self):
        assert parse_expression("reset") == Sym("reset")

    def test_hex_and_decimal_literals(self):
        assert parse_expression("&81") == Int(0x81, Radix.HEX)
        assert parse_expression("1") == Int(1, Radix.DEC)

    def test_label_minus_hex(self):
        assert parse_expression("imm_op_dispatch_lo-&81") == Binary(
            BinOp.SUB, Sym("imm_op_dispatch_lo"), Int(0x81, Radix.HEX),
        )

    def test_label_minus_decimal(self):
        assert parse_expression("dispatch_0_lo-1") == Binary(
            BinOp.SUB, Sym("dispatch_0_lo"), Int(1, Radix.DEC),
        )

    def test_label_difference_chain_is_left_assoc(self):
        # a - b - 1  ==  (a - b) - 1
        e = parse_expression("syn_iam - cmd_syntax_strings - 2")
        assert e == Binary(
            BinOp.SUB,
            Binary(BinOp.SUB, Sym("syn_iam"), Sym("cmd_syntax_strings")),
            Int(2, Radix.DEC),
        )

    def test_hi_lo_functions(self):
        assert parse_expression("HI(star_run-1)") == hi(
            Binary(BinOp.SUB, Sym("star_run"), Int(1, Radix.DEC))
        )
        assert parse_expression("LO(star_run-1)") == lo(
            Binary(BinOp.SUB, Sym("star_run"), Int(1, Radix.DEC))
        )

    def test_lt_gt_byte_select_prefix(self):
        # <(rx_imm_peek-1): the parens are consumed by the byte-select,
        # not preserved as a Group (it re-parenthesises when rendering).
        assert parse_expression("<(rx_imm_peek-1)") == lo(
            Binary(BinOp.SUB, Sym("rx_imm_peek"), Int(1, Radix.DEC))
        )
        assert parse_expression(">(foo)") == hi(Sym("foo"))

    def test_masked_difference_preserves_group(self):
        e = parse_expression("(syn_opt_dir - cmd_syntax_strings - 1) AND &FF")
        assert e == Binary(
            BinOp.AND,
            Group(Binary(
                BinOp.SUB,
                Binary(BinOp.SUB, Sym("syn_opt_dir"), Sym("cmd_syntax_strings")),
                Int(1, Radix.DEC),
            )),
            Int(0xFF, Radix.HEX),
        )

    def test_bitwise_keywords(self):
        assert parse_expression("a EOR b").op is BinOp.XOR
        assert parse_expression("a OR b").op is BinOp.OR
        assert parse_expression("a AND b").op is BinOp.AND

    def test_precedence_and_binds_looser_than_minus(self):
        # a - b AND c  ==  (a - b) AND c  (AND has lower precedence)
        e = parse_expression("a - b AND c")
        assert e.op is BinOp.AND
        assert e.left == Binary(BinOp.SUB, Sym("a"), Sym("b"))


class TestParseErrors:
    @pytest.mark.parametrize("bad", ["", "1 +", "(a", "@weird", "a b"])
    def test_malformed_raises(self, bad):
        with pytest.raises(ExprParseError):
            parse_expression(bad)

    def test_parse_or_raw_falls_back(self):
        assert parse_or_raw("@nonsense!") == Raw("@nonsense!")
        # A valid expression still parses structurally.
        assert parse_or_raw("foo-1") == Binary(
            BinOp.SUB, Sym("foo"), Int(1, Radix.DEC),
        )
