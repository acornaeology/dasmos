"""Public expression DSL for driver scripts.

Import the builders here to construct assembler-neutral operand and data
values, then pass them to :meth:`Disassembler.expr` /
:meth:`Disassembler.expr_label`::

    from dasmos.expr import ref, sym, lo, hi, hexlit

    d.expr(0x8020, lo(ref(dispatch_lo) - 1))
    d.expr(addr, (ref(a) - ref(b) - 1) & 0xFF)

The node classes (:class:`Int`, :class:`Ref`, …) are re-exported too for
type annotations and structural inspection. See
``docs/design/expression-system.md``.
"""

from dasmos.core.expr import (
    BinOp,
    Binary,
    Expr,
    Int,
    Radix,
    Raw,
    Ref,
    Sym,
    Unary,
    UnaryOp,
    as_expr,
    char,
    declit,
    hexlit,
    hi,
    lit,
    lo,
    raw,
    ref,
    sym,
)

__all__ = [
    # builders
    "ref",
    "sym",
    "lit",
    "hexlit",
    "declit",
    "char",
    "lo",
    "hi",
    "raw",
    "as_expr",
    # nodes / enums
    "Expr",
    "Int",
    "Ref",
    "Sym",
    "Unary",
    "Binary",
    "Raw",
    "Radix",
    "UnaryOp",
    "BinOp",
]
