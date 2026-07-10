"""Parser for the beebasm / py8dis expression dialect.

Turns a legacy driver-authored operand string such as
``"(syn_opt_dir - cmd_syntax_strings - 1) AND &FF"`` or ``"HI(star_run-1)"``
into an assembler-neutral :class:`~dasmos.core.expr.Expr` tree, so
existing string-based drivers migrate to the structured system with no
edits: :meth:`Disassembler.expr` / :meth:`Disassembler.expr_label` parse
their string arguments through here.

Identifiers become :class:`~dasmos.core.expr.Sym` nodes (rendered
verbatim), so no address resolution is needed. Anything that does not
parse cleanly falls back to a :class:`~dasmos.core.expr.Raw` node (the
caller catches :class:`ExprParseError`), preserving today's behaviour for
exotic strings.

The grammar and precedence follow beebasm (``beebasm/src/expression.cpp``):
``* / MOD DIV << >>`` (tightest binary), then ``+ -``, then ``AND``, then
``OR`` / ``EOR``; unary ``-`` and the byte-selects ``< > HI( LO(`` bind
tighter than any binary operator.
"""

from __future__ import annotations

import re

from dasmos.core.expr import (
    BinOp,
    Binary,
    Expr,
    Group,
    Int,
    Radix,
    Raw,
    Sym,
    Unary,
    UnaryOp,
    hi,
    lo,
)


class ExprParseError(ValueError):
    """Raised when a dialect string cannot be parsed as an expression."""


# Binary operator token → (BinOp, precedence). Higher precedence binds
# tighter. Keyword operators (AND/OR/EOR/MOD/DIV) are matched as whole
# words by the tokenizer.
_BINARY_OPS = {
    "*": (BinOp.MUL, 6), "/": (BinOp.DIV, 6),
    "MOD": (BinOp.MOD, 6), "DIV": (BinOp.DIV, 6),
    "<<": (BinOp.SHL, 6), ">>": (BinOp.SHR, 6),
    "+": (BinOp.ADD, 5), "-": (BinOp.SUB, 5),
    "AND": (BinOp.AND, 3),
    "OR": (BinOp.OR, 2), "EOR": (BinOp.XOR, 2),
}

_KEYWORDS = {"AND", "OR", "EOR", "MOD", "DIV", "HI", "LO"}

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<hex>&[0-9A-Fa-f]+)
      | (?P<dec>\d+)
      | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<shl><<)
      | (?P<shr>>>)
      | (?P<op>[+\-*/()<>])
    )
    """,
    re.VERBOSE,
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    n = len(text)
    while pos < n:
        if text[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ExprParseError(f"unexpected character {text[pos]!r} in {text!r}")
        pos = m.end()
        if m.lastgroup == "hex":
            tokens.append(("hex", m.group()))
        elif m.lastgroup == "dec":
            tokens.append(("dec", m.group()))
        elif m.lastgroup == "ident":
            word = m.group()
            upper = word.upper()
            if upper in _KEYWORDS:
                tokens.append(("kw", upper))
            else:
                tokens.append(("ident", word))
        elif m.lastgroup in ("shl", "shr"):
            tokens.append(("op", m.group()))
        else:
            tokens.append(("op", m.group()))
    return tokens


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self._tokens = tokens
        self._i = 0

    def _peek(self):
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _next(self):
        tok = self._peek()
        self._i += 1
        return tok

    def _expect_op(self, value: str) -> None:
        tok = self._next()
        if tok != ("op", value):
            raise ExprParseError(f"expected {value!r}, got {tok!r}")

    def parse(self) -> Expr:
        e = self._parse_binary(0)
        if self._peek() is not None:
            raise ExprParseError(f"trailing tokens: {self._tokens[self._i:]!r}")
        return e

    def _binary_op(self):
        """Return ``(token_value, BinOp, precedence)`` if the next token is
        a binary operator, else ``None``."""
        tok = self._peek()
        if tok is None:
            return None
        kind, value = tok
        if kind == "kw" and value in _BINARY_OPS:
            return value, *_BINARY_OPS[value]
        if kind == "op" and value in _BINARY_OPS:
            return value, *_BINARY_OPS[value]
        return None

    def _parse_binary(self, min_prec: int) -> Expr:
        left = self._parse_unary()
        while True:
            op = self._binary_op()
            if op is None or op[2] < min_prec:
                break
            _value, binop, prec = op
            self._next()
            right = self._parse_binary(prec + 1)  # left-associative
            left = Binary(binop, left, right)
        return left

    def _parse_unary(self) -> Expr:
        tok = self._peek()
        if tok == ("op", "-"):
            self._next()
            return Unary(UnaryOp.NEG, self._parse_unary())
        if tok == ("op", "+"):
            self._next()
            return Unary(UnaryOp.POS, self._parse_unary())
        if tok == ("op", "<"):
            self._next()
            return self._byte_select(lo, self._parse_unary())
        if tok == ("op", ">"):
            self._next()
            return self._byte_select(hi, self._parse_unary())
        return self._parse_primary()

    @staticmethod
    def _byte_select(fn, operand: Expr) -> Expr:
        # A byte-select renders its own parentheses, so an explicit Group
        # directly inside it is redundant — unwrap one level.
        if isinstance(operand, Group):
            operand = operand.inner
        return fn(operand)

    def _parse_primary(self) -> Expr:
        tok = self._next()
        if tok is None:
            raise ExprParseError("unexpected end of expression")
        kind, value = tok
        if kind == "hex":
            return Int(int(value[1:], 16), Radix.HEX)
        if kind == "dec":
            return Int(int(value), Radix.DEC)
        if kind == "ident":
            return Sym(value)
        if kind == "kw" and value in ("HI", "LO"):
            # Byte-select function: HI( expr ).
            self._expect_op("(")
            inner = self._parse_binary(0)
            self._expect_op(")")
            fn = hi if value == "HI" else lo
            return fn(inner)
        if tok == ("op", "("):
            inner = self._parse_binary(0)
            self._expect_op(")")
            return Group(inner)
        raise ExprParseError(f"unexpected token {tok!r}")


def parse_expression(text: str) -> Expr:
    """Parse a beebasm/py8dis dialect string into an :class:`Expr`.

    Raises :class:`ExprParseError` if the string is not a well-formed
    expression in the supported grammar.
    """
    tokens = _tokenize(text)
    if not tokens:
        raise ExprParseError("empty expression")
    return _Parser(tokens).parse()


def parse_or_raw(text: str) -> Expr:
    """Parse ``text`` into a structured :class:`Expr`, or fall back to a
    :class:`~dasmos.core.expr.Raw` node if it is not in the supported
    dialect grammar (preserving today's verbatim behaviour)."""
    try:
        return parse_expression(text)
    except ExprParseError:
        return Raw(text)
