"""64tass-syntax renderer for dasmos.

64tass is the multi-pass 6502-family assembler at
<https://sourceforge.net/projects/tass64/>. It is the **second**
text-syntax backend dasmos ships, added to prove the assembler-backend
interface is genuinely generic: this class supplies only 64tass's
lexical protocol and directives, while the whole rendering walk is
inherited unchanged from
:class:`~dasmos.asm_renderer.AssemblerRenderer`.

Where beebasm and 64tass differ, and why it matters for the interface:

- **Hex**: ``$`` sigil, not beebasm's ``&`` — exercises the
  :meth:`~dasmos.renderer.TextRenderer.address_link_hex` seam so the
  ``?hex`` cross-reference form in comments renders ``$E000``.
- **Data**: ``.byte`` / ``.word`` / ``.text`` rather than
  ``equb`` / ``equw`` / ``equs``.
- **Labels**: bare ``name`` at column 0 (no ``.`` prefix).
- **Fill**: native ``.fill n, v`` rather than beebasm's ``FOR … NEXT``.
- **Relocation**: native ``.logical`` / ``.here`` pseudo-PC — the
  cleanest possible expression of a move. This is the payoff: the same
  shared walk that drives beebasm's ``copyblock`` idiom drives 64tass's
  phase directive through the ``pseudopc_start`` / ``pseudopc_end``
  hooks, with 64tass needing no explicit copy-back (``.here`` restores
  the compile offset itself).
- **Save**: 64tass writes the binary via the ``-o`` command-line flag,
  so there is no in-source ``save`` directive (the base's ``None``
  default applies) and no start/end boundary labels are emitted.

The round-trip property (binary → dasmos → 64tass → binary') is
validated the same way beebasm's is; see ``tests/test_tass64.py``.
"""

from __future__ import annotations

import re

from dasmos.asm_renderer import AssemblerRenderer
from dasmos.core.expr import BinOp

# Beebasm/py8dis hex literal (``&HH``) as it appears embedded in a
# driver-authored expression string. In that dialect ``&`` is *always*
# the hex sigil (bitwise-AND is the ``AND`` keyword), so rewriting every
# ``&<hexdigits>`` to 64tass's ``$<hexdigits>`` is unambiguous.
_BEEBASM_HEX_IN_EXPR_RE = re.compile(r"&([0-9A-Fa-f]+)")

# Beebasm's expression operators / functions and their 64tass spellings.
# Applied after the hex rewrite. Word-boundaried so they only match
# whole tokens (``\bOR\b`` does not fire inside ``EOR``). ``HI(``/``LO(``
# are beebasm's hi/lo-byte functions; 64tass uses the ``>``/``<`` unary
# operators, which keep the parentheses that follow.
_BEEBASM_EXPR_SUBS = (
    (re.compile(r"\bHI\("), ">("),
    (re.compile(r"\bLO\("), "<("),
    (re.compile(r"\bAND\b"), "&"),
    (re.compile(r"\bEOR\b"), "^"),
    (re.compile(r"\bOR\b"), "|"),
)


class Tass64Renderer(AssemblerRenderer):
    """64tass-syntax renderer.

    Produces a 64tass-compatible source listing from a dasmos IR.
    Assemble back to a raw binary with ``64tass --nostart -o out.bin
    in.asm``; the result should byte-for-byte match the original input.
    """

    def __init__(self, name: str = "64tass", **kwargs):
        # 64tass saves via the ``-o`` flag, not an in-source directive,
        # so the start/end marker labels beebasm needs for its ``save``
        # have no referent here — suppress them by default (empty
        # prefix). A caller can still opt in via boundary_label_prefix.
        kwargs.setdefault("boundary_label_prefix", "")
        super().__init__(name=name, **kwargs)
        # 64tass accepts the explicit-accumulator form (``rol a``); emit
        # it for parity with the disassembler's intent and beebasm.
        self.explicit_a = True

    # -- CPU targeting ----------------------------------------------------

    def cpus_supported(self) -> list[str]:
        return ["6502", "65C02"]

    def cpu_directive_for(self, cpu_name: str) -> str | None:
        # 64tass selects the instruction set with ``.cpu "<name>"``.
        # The default 6502 needs no directive; the CMOS 65C02 does.
        if cpu_name == "65C02":
            return '.cpu "65c02"'
        return None

    # -- lexical building blocks ------------------------------------------

    def hex2(self, n: int) -> str:
        return f"${n:02x}"

    def hex4(self, n: int) -> str:
        return f"${n:04x}"

    def comment_prefix(self) -> str:
        return ";"

    def byte_prefix(self) -> str:
        return ".byte "

    def word_prefix(self) -> str:
        return ".word "

    def string_prefix(self) -> str:
        return ".text "

    def inline_label(self, name: str) -> str:
        # 64tass defines a label by placing the bare name at column 0.
        return name

    def explicit_label(
        self, name: str, value, offset: int | None = None, align_column: int = 0,
    ) -> str:
        suffix = "" if offset is None else f"+{offset}"
        if align_column > 0:
            padded = name.ljust(align_column)
            return f"{padded} = {value}{suffix}"
        return f"{name} = {value}{suffix}"

    def address_link_hex(self, hex_str: str) -> str:
        # ``?hex`` cross-reference links flatten to 64tass's ``$`` sigil.
        return f"${hex_str.upper()}"

    def disassembly_start(self) -> list[str]:
        return []

    def disassembly_end(self) -> list[str]:
        return []

    def code_start(self, start_addr, end_addr, first: bool) -> list[str]:
        return ["", f"    * = {self.hex4(int(start_addr))}", ""]

    def code_end(self) -> list[str]:
        return []

    def set_origin(self, addr: int) -> list[str]:
        # A blank line then ``* =`` to reposition the assembly PC.
        return ["", f"    * = {self.hex(int(addr))}"]

    def pseudopc_start(
        self, *, dest, src, length, move_id, src_label, dest_label,
    ) -> list[str]:
        """Enter a relocated block via 64tass's ``.logical``.

        The shared walk has already positioned the output at ``src``
        (``* = <src>``); ``.logical <dest>`` sets the logical program
        counter to ``dest`` while output continues at ``src``, so the
        block's bytes are written to their file position but resolve as
        if executing at ``dest``.
        """
        cp = self.comment_prefix()
        return [
            "",
            (
                f"{cp} Move {move_id}: {self.hex(int(src))} to "
                f"{self.hex(int(dest))} for length {length}"
            ),
            f"    .logical {self.hex(int(dest))}",
        ]

    def pseudopc_end(
        self, *, dest, src, length, move_id, src_label, dest_label,
    ) -> list[str]:
        """Leave a relocated block via 64tass's ``.here``.

        Unlike beebasm — which needs ``copyblock`` to move the assembled
        bytes back to their file position — 64tass never moved the
        output pointer, so ``.here`` alone re-locks the logical PC to the
        output position. No copy-back, no restore-``org``.
        """
        return ["    .here", ""]

    def char_literal(self, n: int) -> str | None:
        # 64tass single-quoted character constant, printable except the
        # quote characters.
        if 32 <= n <= 126 and n not in (ord('"'), ord("'")):
            return f"'{chr(n)}'"
        return None

    def string_chr(self, n: int) -> str | None:
        # Inside a double-quoted ``.text`` string: anything printable
        # except the closing quote.
        if 32 <= n <= 126 and n != ord('"'):
            return chr(n)
        return None

    def fill_directive(self, value: int, length: int) -> list[str]:
        # 64tass has a native fill: ``.fill <count>, <value>``.
        if length <= 0:
            return []
        return [f".fill {length}, {self.hex2(value)}"]

    # -- data / expression syntax -----------------------------------------

    def _string_line_directive(
        self, *, first_is_string: bool, has_string: bool,
    ) -> str:
        # 64tass's ``.byte`` rejects a multi-character string literal
        # ("too large for a 8 bit unsigned integer"); ``.text`` accepts
        # a mix of strings and bytes. So prefer ``.text`` whenever any
        # part is a string, even when the line leads with a raw byte.
        return self.string_prefix() if has_string else self.byte_prefix()

    # 64tass operator spellings and C-like precedence (higher binds
    # tighter): `* / %` > `+ -` > `<< >>` > `&` > `^` > `|`. This differs
    # from beebasm's table (where shifts share MUL's level and AND/OR/EOR
    # rank differently), which is exactly why the shared expression walker
    # parenthesises per backend.
    _BINARY_PRECEDENCE = {
        BinOp.MUL: 8, BinOp.DIV: 8, BinOp.MOD: 8,
        BinOp.ADD: 7, BinOp.SUB: 7,
        BinOp.SHL: 6, BinOp.SHR: 6,
        BinOp.AND: 4,
        BinOp.XOR: 3,
        BinOp.OR: 2,
    }

    def _binary_token(self, op: BinOp) -> str:
        return {
            BinOp.ADD: "+", BinOp.SUB: "-", BinOp.MUL: "*", BinOp.DIV: "/",
            BinOp.MOD: "%", BinOp.AND: "&", BinOp.OR: "|",
            BinOp.XOR: "^", BinOp.SHL: "<<", BinOp.SHR: ">>",
        }[op]

    def translate_expression(self, expr: str) -> str:
        # Driver-authored (and INKEY-derived) expressions use beebasm's
        # dialect: ``&HH`` hex, ``HI``/``LO`` byte functions, and the
        # ``AND`` / ``EOR`` / ``OR`` bitwise-operator keywords. Rewrite
        # each to 64tass syntax. Hex first (so ``&FF`` → ``$FF`` before
        # any operator pass), then the operators/functions.
        expr = _BEEBASM_HEX_IN_EXPR_RE.sub(r"$\1", expr)
        for pattern, repl in _BEEBASM_EXPR_SUBS:
            expr = pattern.sub(repl, expr)
        return expr
