"""Assembler-neutral expression trees.

A driver authors an operand or data value as an :class:`Expr` — a small,
immutable tree that carries *intent* (a label reference, a difference, a
low byte) and never one assembler's syntax. Each text renderer walks the
tree and emits its own tokens, hex sigil, and — crucially — its own
parenthesisation for its own operator precedence, so beebasm, 64tass and
any future backend render the same tree correctly. The JSON renderer
emits the tree structurally.

See ``docs/design/expression-system.md`` for the full design.

Drivers build trees through the ergonomic DSL re-exported from
``dasmos.expr`` (``ref``, ``sym``, ``lo``, ``hi``, ``hexlit`` …) plus
Python's own operators::

    lo(ref(0x8130) - 1)                 # low byte of (label at 0x8130 - 1)
    (ref(a) - ref(b) - 1) & 0xFF        # masked label difference
    (255 - ref(inkey_key_ctrl)) ^ 128   # INKEY form, backend-neutral

For backward compatibility, a plain ``str`` passed where an ``Expr`` is
expected is wrapped as :class:`Raw` — a pre-formatted string in the
beebasm/py8dis dialect, rendered through the renderer's
``translate_expression`` adapter and emitted verbatim by JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Radix(Enum):
    """How an :class:`Int` literal should be spelled."""

    AUTO = auto()  #: renderer default (0-9 decimal, else hex)
    DEC = auto()
    HEX = auto()
    BIN = auto()
    CHAR = auto()  #: a character literal, e.g. ``'A'``


class UnaryOp(Enum):
    NEG = auto()       #: arithmetic negation, ``-x``
    POS = auto()       #: unary plus, ``+x``
    LOWBYTE = auto()   #: low byte, ``<x`` / ``LO(x)``
    HIGHBYTE = auto()  #: high byte, ``>x`` / ``HI(x)``
    BANKBYTE = auto()  #: bank byte (65816), ``^x`` — reserved
    INVERT = auto()    #: bitwise complement, ``~x``


class BinOp(Enum):
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    AND = auto()
    OR = auto()
    XOR = auto()
    SHL = auto()
    SHR = auto()


def _coerce(value) -> "Expr":
    """Wrap a Python ``int`` as :class:`Int`, pass an :class:`Expr`
    through, and reject anything else. Lets the operator overloads accept
    ``ref(x) - 1`` and ``255 - ref(x)`` naturally.
    """
    if isinstance(value, Expr):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Int(value)
    raise TypeError(
        f"expression operand must be an Expr or int, got "
        f"{type(value).__name__}"
    )


class Expr:
    """Abstract base for expression nodes.

    Supplies Python operator overloads so trees read like arithmetic.
    Concrete nodes are frozen dataclasses, so they are hashable and
    comparable by value.
    """

    # -- arithmetic -------------------------------------------------------
    def __add__(self, other): return Binary(BinOp.ADD, self, _coerce(other))
    def __radd__(self, other): return Binary(BinOp.ADD, _coerce(other), self)
    def __sub__(self, other): return Binary(BinOp.SUB, self, _coerce(other))
    def __rsub__(self, other): return Binary(BinOp.SUB, _coerce(other), self)
    def __mul__(self, other): return Binary(BinOp.MUL, self, _coerce(other))
    def __rmul__(self, other): return Binary(BinOp.MUL, _coerce(other), self)
    def __floordiv__(self, other): return Binary(BinOp.DIV, self, _coerce(other))
    def __mod__(self, other): return Binary(BinOp.MOD, self, _coerce(other))

    # -- bitwise ----------------------------------------------------------
    def __and__(self, other): return Binary(BinOp.AND, self, _coerce(other))
    def __rand__(self, other): return Binary(BinOp.AND, _coerce(other), self)
    def __or__(self, other): return Binary(BinOp.OR, self, _coerce(other))
    def __ror__(self, other): return Binary(BinOp.OR, _coerce(other), self)
    def __xor__(self, other): return Binary(BinOp.XOR, self, _coerce(other))
    def __rxor__(self, other): return Binary(BinOp.XOR, _coerce(other), self)
    def __lshift__(self, other): return Binary(BinOp.SHL, self, _coerce(other))
    def __rshift__(self, other): return Binary(BinOp.SHR, self, _coerce(other))

    # -- unary ------------------------------------------------------------
    def __neg__(self): return Unary(UnaryOp.NEG, self)
    def __pos__(self): return Unary(UnaryOp.POS, self)
    def __invert__(self): return Unary(UnaryOp.INVERT, self)

    # -- string indexing / slicing ---------------------------------------
    def __getitem__(self, key):
        if isinstance(key, slice):
            if key.step is not None:
                raise TypeError("expression slices cannot have a step")
            start = Int(0) if key.start is None else _coerce(key.start)
            stop = None if key.stop is None else _coerce(key.stop)
            return StrSlice(self, start, stop)
        return StrIndex(self, _coerce(key))


@dataclass(frozen=True)
class Int(Expr):
    """An integer literal. ``radix`` controls how it is spelled."""

    value: int
    radix: Radix = Radix.AUTO


@dataclass(frozen=True)
class Ref(Expr):
    """The label at ``runtime_addr``, resolved to its best name at render
    time (falling back to a hex literal when no name exists). Generalises
    the disassembler's late-bound deferred-expression mechanism: a label
    registered *after* the reference still surfaces symbolically.
    """

    runtime_addr: int


@dataclass(frozen=True)
class Sym(Expr):
    """A bare symbolic identifier not tied to a resolvable address — a
    constant name, or a name the porter recovered from a legacy string.
    Emitted verbatim (it is already a valid identifier in every
    assembler).
    """

    name: str


@dataclass(frozen=True)
class Unary(Expr):
    op: UnaryOp
    operand: Expr


@dataclass(frozen=True)
class Binary(Expr):
    op: BinOp
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Group(Expr):
    """Explicit parenthesisation the author wrote for readability, even
    where operator precedence makes it redundant. Always renders its
    parentheses, so ``(255 - x) EOR 128`` keeps its grouping rather than
    collapsing to ``255 - x EOR 128``.
    """

    inner: Expr


@dataclass(frozen=True)
class Raw(Expr):
    """A pre-formatted expression string in the beebasm/py8dis dialect.

    The back-compat / escape-hatch leaf: today's string-based drivers are
    wrapped as ``Raw`` so they render exactly as before (through the
    renderer's ``translate_expression`` adapter). Opaque to structural
    consumers — JSON emits the string as-is.
    """

    text: str


@dataclass(frozen=True)
class Str(Expr):
    """A string literal. Not a numeric value on its own — it is the
    operand of a string operation (:class:`StrIndex`, :class:`StrSlice`,
    :class:`StrLen`) or a string-typed data value.
    """

    text: str


@dataclass(frozen=True)
class StrIndex(Expr):
    """The character code of ``string`` at ``index`` (0-based) — an
    integer value. When both operands are constant it folds to a
    character-literal :class:`Int`; otherwise each backend renders its
    own string-indexing syntax (64tass ``s[i]``, beebasm
    ``ASC(MID$(s, i+1, 1))``).
    """

    string: Expr
    index: Expr


@dataclass(frozen=True)
class StrSlice(Expr):
    """A substring of ``string`` from ``start`` to ``stop`` (exclusive;
    ``stop`` ``None`` means "to the end") — a string value. Folds to a
    :class:`Str` when its operands are constant.
    """

    string: Expr
    start: Expr
    stop: "Expr | None" = None


@dataclass(frozen=True)
class StrLen(Expr):
    """The length of ``string`` — an integer. Folds to an :class:`Int`
    when ``string`` is constant."""

    string: Expr


@dataclass(frozen=True)
class Param(Expr):
    """A macro formal parameter, referenced inside a macro body. Renders
    as the backend's parameter reference (both beebasm and 64tass
    functions use the bare name; 64tass *macros* would use ``\\name``).
    Being non-constant, string operations on a ``Param`` render natively
    rather than folding — which is exactly how a macro keeps the string
    argument symbolic in its body.
    """

    name: str


@dataclass(frozen=True)
class MacroCall(Expr):
    """An invocation of a macro, ``name(args…)`` — a value expression.
    Backends with value macros/functions (64tass ``.sfunction``, ca65
    ``.define``) render it inline in a data directive; those without
    (beebasm, acme) render each call as its own statement line (handled
    by the data-block renderer).
    """

    name: str
    args: tuple


@dataclass(frozen=True)
class MacroDef:
    """A macro definition: ``name(params) -> body``, whose value is
    emitted as ``emit`` (``"byte"`` / ``"word"``). Not an expression — a
    top-level definition the renderer emits once and each
    :class:`MacroCall` refers to.
    """

    name: str
    params: tuple
    body: Expr
    emit: str = "byte"


def fold(e: Expr) -> Expr:
    """Constant-fold string operations (and their sub-trees) as far as
    possible.

    ``StrIndex(Str("BRK"), Int(0))`` → ``Int(ord("B"), CHAR)``;
    ``StrSlice(Str("BRK"), 0, 2)`` → ``Str("BR")``;
    ``StrLen(Str("BRK"))`` → ``Int(3)``. A string op whose operands are
    not all constant is returned with its children folded but otherwise
    intact (a backend then renders it natively). Non-string nodes are
    returned with their children folded so a string op nested inside
    arithmetic still collapses. Idempotent.
    """
    if isinstance(e, StrIndex):
        s, i = fold(e.string), fold(e.index)
        if isinstance(s, Str) and isinstance(i, Int):
            return Int(ord(s.text[i.value]), Radix.CHAR)
        return StrIndex(s, i)
    if isinstance(e, StrSlice):
        s = fold(e.string)
        start = fold(e.start)
        stop = None if e.stop is None else fold(e.stop)
        if (
            isinstance(s, Str) and isinstance(start, Int)
            and (stop is None or isinstance(stop, Int))
        ):
            end = None if stop is None else stop.value
            return Str(s.text[start.value:end])
        return StrSlice(s, start, stop)
    if isinstance(e, StrLen):
        s = fold(e.string)
        if isinstance(s, Str):
            return Int(len(s.text))
        return StrLen(s)
    if isinstance(e, MacroCall):
        return MacroCall(e.name, tuple(fold(a) for a in e.args))
    if isinstance(e, Group):
        return Group(fold(e.inner))
    if isinstance(e, Unary):
        return Unary(e.op, fold(e.operand))
    if isinstance(e, Binary):
        return Binary(e.op, fold(e.left), fold(e.right))
    return e


# ---------------------------------------------------------------------------
# Driver-facing DSL (re-exported from ``dasmos.expr``)
# ---------------------------------------------------------------------------

def ref(runtime_addr: int) -> Ref:
    """Reference the label at ``runtime_addr`` (resolved at render time)."""
    return Ref(int(runtime_addr))


def sym(name: str) -> Sym:
    """Reference a bare symbolic name, emitted verbatim."""
    return Sym(name)


def lit(value: int, radix: Radix = Radix.AUTO) -> Int:
    """An integer literal with an explicit ``radix`` (default AUTO)."""
    return Int(int(value), radix)


def hexlit(value: int) -> Int:
    """An integer literal forced to hex (``&`` / ``$``)."""
    return Int(int(value), Radix.HEX)


def declit(value: int) -> Int:
    """An integer literal forced to decimal."""
    return Int(int(value), Radix.DEC)


def char(value: int) -> Int:
    """An integer literal rendered as a character literal (``'A'``)."""
    return Int(int(value), Radix.CHAR)


def lo(operand) -> Unary:
    """Low byte of ``operand`` (``<`` / ``LO``)."""
    return Unary(UnaryOp.LOWBYTE, _coerce(operand))


def hi(operand) -> Unary:
    """High byte of ``operand`` (``>`` / ``HI``)."""
    return Unary(UnaryOp.HIGHBYTE, _coerce(operand))


def group(operand) -> Group:
    """Force explicit parentheses around ``operand``."""
    return Group(_coerce(operand))


def string(text: str) -> Str:
    """A string literal — index it (``string("BRK")[0]``) or slice it to
    build character/substring expressions."""
    return Str(text)


def param(name: str) -> Param:
    """A macro formal parameter, for use inside a macro body."""
    return Param(name)


def macro_arg(value) -> Expr:
    """Coerce a macro-call argument: a ``str`` becomes a string literal
    :class:`Str` (macro args are values, not dialect expressions), an
    ``int`` an :class:`Int`, and an :class:`Expr` passes through."""
    if isinstance(value, str):
        return Str(value)
    return _coerce(value)


def str_len(s) -> StrLen:
    """The length of a string expression."""
    return StrLen(_coerce_str(s))


def _coerce_str(value) -> Expr:
    if isinstance(value, str):
        return Str(value)
    return _coerce(value)


def raw(text: str) -> Raw:
    """Wrap a pre-formatted dialect string as an opaque expression."""
    return Raw(text)


_CANONICAL_BINOP = {
    BinOp.ADD: "+", BinOp.SUB: "-", BinOp.MUL: "*", BinOp.DIV: "/",
    BinOp.MOD: "MOD", BinOp.AND: "AND", BinOp.OR: "OR", BinOp.XOR: "EOR",
    BinOp.SHL: "<<", BinOp.SHR: ">>",
}


def canonical_text(e: Expr) -> str:
    """A neutral, IR-free string form of ``e`` for name tables,
    dedup, and the JSON ``text`` field. Uses the historical
    beebasm-flavoured spelling (``&`` hex, ``AND``/``EOR``). A
    :class:`Ref` renders as a bare hex address (no labels to consult
    here); resolved names come from a renderer's
    ``render_expression`` instead.
    """
    e = fold(e)
    if isinstance(e, Raw):
        return e.text
    if isinstance(e, Sym):
        return e.name
    if isinstance(e, Param):
        return e.name
    if isinstance(e, MacroCall):
        return f"{e.name}({', '.join(canonical_text(a) for a in e.args)})"
    if isinstance(e, Str):
        return f'"{e.text}"'
    if isinstance(e, StrIndex):
        return f"{canonical_text(e.string)}[{canonical_text(e.index)}]"
    if isinstance(e, StrSlice):
        stop = "" if e.stop is None else canonical_text(e.stop)
        return f"{canonical_text(e.string)}[{canonical_text(e.start)}:{stop}]"
    if isinstance(e, StrLen):
        return f"len({canonical_text(e.string)})"
    if isinstance(e, Ref):
        a = e.runtime_addr
        return f"&{a:02x}" if a <= 0xFF else f"&{a:04x}"
    if isinstance(e, Int):
        v = e.value
        if e.radix is Radix.DEC:
            return str(v)
        if e.radix is Radix.HEX:
            return f"&{v:02x}" if v <= 0xFF else f"&{v:04x}"
        if e.radix is Radix.BIN:
            return f"%{v:08b}"
        if e.radix is Radix.CHAR and 0x20 <= v <= 0x7E:
            return f"'{chr(v)}'"
        return str(v) if 0 <= v <= 9 else (
            f"&{v:02x}" if v <= 0xFF else f"&{v:04x}"
        )
    if isinstance(e, Group):
        return f"({canonical_text(e.inner)})"
    if isinstance(e, Unary):
        inner = canonical_text(e.operand)
        if e.op is UnaryOp.LOWBYTE:
            return f"<({inner})"
        if e.op is UnaryOp.HIGHBYTE:
            return f">({inner})"
        token = {UnaryOp.NEG: "-", UnaryOp.POS: "+", UnaryOp.INVERT: "~"}[e.op]
        return f"{token}{inner}"
    if isinstance(e, Binary):
        return (
            f"{canonical_text(e.left)} {_CANONICAL_BINOP[e.op]} "
            f"{canonical_text(e.right)}"
        )
    raise TypeError(f"cannot canonicalise expression node {type(e).__name__}")


def as_expr(value) -> Expr:
    """Coerce a driver-supplied value to an :class:`Expr`: an ``Expr`` is
    returned unchanged, an ``int`` becomes :class:`Int`, and a ``str``
    becomes :class:`Raw` (the back-compat path). Used by the IR stores so
    both structured and legacy string values are accepted uniformly.
    """
    if isinstance(value, Expr):
        return value
    if isinstance(value, str):
        return Raw(value)
    return _coerce(value)
