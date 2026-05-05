"""Semantic format hints for operand bytes.

A :class:`FormatHint` is the **abstract semantic intent** for a
byte (e.g. "this byte is intended as an ASCII character"). It lives
in the IR alongside expressions, labels, classifications, etc., and
is renderer-agnostic — each renderer translates a hint into its own
assembler-specific syntax. For example, a ``CHAR`` hint produces:

- ``ASC("c")`` or ``'c'`` from the beebasm renderer (style-dependent);
- ``"format_hint": "char"`` in the JSON renderer's per-operand record;
- ``'c'`` from a hypothetical ACME renderer;
- a hex literal from any renderer when the byte cannot be expressed
  as a character literal in that assembler's lexical grammar.

The split between the IR (semantic) and renderer (syntactic) is
deliberate: a driver script that says "this byte is a character"
expresses intent once and every output format honours it
appropriately. Putting the syntax decision in the driver script
(via ``d.expr(addr, 'ASC("c")')``) couples the disassembly to a
single assembler dialect.

Hints are populated from two sources:

1. **Explicit driver calls** — e.g. :meth:`Disassembler.char_literal`
   for the ``CHAR`` hint. The driver author knows the byte's intent
   even when no auto-detection heuristic could.
2. **Auto-detection passes** — currently each renderer applies its
   own auto-detect heuristics to printable immediates without
   populating the registry; later refactors may move shared
   heuristics into a single dasmos-side pass that populates hints.
"""

from __future__ import annotations

from enum import Enum

from dasmos.core.memory import BinaryAddr


class FormatHint(Enum):
    """Abstract semantic markers a renderer translates to syntax.

    Each value names *what* a byte represents (a character literal,
    a base-N integer, a flag word, …); each renderer chooses *how*
    to express that in its target assembler's grammar.
    """

    #: This byte is intended as an ASCII character literal. Renderers
    #: should choose the cleanest character-literal syntax their
    #: target assembler offers (``ASC("c")``, ``'c'``, etc.) or fall
    #: back to a hex literal with a warning when the byte cannot be
    #: expressed as a character (non-printable bytes etc.).
    CHAR = "char"

    #: Render in base 10. The renderer's default may already use
    #: decimal for some values (e.g. beebasm's small-int
    #: ``0..9`` rule); an explicit ``DECIMAL`` hint widens that
    #: choice to the whole byte range.
    DECIMAL = "decimal"

    #: Render in base 16 with the assembler's hex sigil
    #: (``&xx`` for beebasm, ``$xx`` for ca65 / ACME, ``0xXX``
    #: for C-style assemblers).
    HEX = "hex"

    #: Render in base 2 with the assembler's binary sigil
    #: (``%01010101`` in beebasm; the bit-pattern form is more
    #: readable than hex for flag words and bitmasks).
    BINARY = "binary"

    #: Render in base 8. Some assemblers (notably beebasm) have no
    #: native octal syntax; renderers that can't express it should
    #: emit a hex / decimal form plus a clarifying inline comment
    #: and warn at render time.
    OCTAL = "octal"


class FormatHintRegistry:
    """Per-disassembly map from binary address to a :class:`FormatHint`.

    Renderers consult this at render time to discover the user's
    semantic intent for an operand byte. The registry is mutated
    only by the driver-API layer (or by auto-detection passes inside
    the disassembler, when those are added); renderers must treat
    it as read-only.

    Last-write-wins semantics — :meth:`add` replaces any prior hint
    at the same address. Hints are typed and unambiguous, so there
    is no idempotency concern (unlike :class:`ExpressionRegistry`
    where multiple passes can re-register the same expression text).
    """

    def __init__(self):
        self._hints: dict[BinaryAddr, FormatHint] = {}

    def __contains__(self, binary_addr) -> bool:
        return BinaryAddr(binary_addr) in self._hints

    def add(self, binary_addr, hint: FormatHint) -> None:
        """Register ``hint`` at ``binary_addr``.

        Replaces any previously-registered hint at the same address.
        """
        self._hints[BinaryAddr(binary_addr)] = hint

    def get(self, binary_addr) -> FormatHint:
        """Return the hint registered at ``binary_addr``.

        Raises ``KeyError`` if there is none — use
        :meth:`get_or_none` if absence is expected.
        """
        return self._hints[BinaryAddr(binary_addr)]

    def get_or_none(self, binary_addr) -> FormatHint | None:
        return self._hints.get(BinaryAddr(binary_addr))
