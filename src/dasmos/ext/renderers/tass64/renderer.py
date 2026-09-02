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

import warnings

from dasmos.asm_renderer import AssemblerRenderer
from dasmos.core.expr import BinOp


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

    def build_command(self) -> list[str] | None:
        """The 64tass invocation that assembles this listing to a raw
        binary. 64tass has no in-source save directive, so the output name
        is always given with ``-o`` (``build_output_name``, else the save
        ``output_filename``, else a placeholder); ``--nostart`` strips the
        load-address header so the file is the raw ROM image."""
        listing = self.listing_filename or "<listing>.asm"
        output = self.build_output_name or self.output_filename or "<output.bin>"
        return [
            "Assemble with 64tass:",
            f"64tass --nostart -o {output} {listing}",
        ]

    def _save_directive(self, load_start, load_end, program=None) -> str | None:
        """64tass writes the binary via ``-o``, so there is never an
        in-source save directive. Load-and-run exec/reload metadata
        (#45) has no representation in a raw 64tass output, so it is
        warned about and omitted; the raw payload is unaffected.
        """
        if program is not None and (
            program.exec_addr is not None or program.reload_addr is not None
        ):
            warnings.warn(
                "64tass has no exec/reload save directive; the declared "
                "exec/reload program metadata is omitted. The raw binary "
                "(and so fantasm verify) is unaffected. Use the beebasm "
                "backend to emit a *RUN-able file with a DFS header.",
                UserWarning,
                stacklevel=2,
            )
        return None

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

    def included_binary_directive(self, path: str) -> list[str]:
        # 64tass includes an external file with ``.binary "<path>"``
        # (raw bytes, no header). The file must sit next to the listing
        # (write it with ir.write_included_binaries).
        return [f'.binary "{path}"']

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

    # 64tass has a value-returning function (.sfunction) usable inside a
    # data directive, so a macro invocation is a value: ``.byte
    # pack("LDA")``.
    @property
    def macro_calls_are_values(self) -> bool:
        return True

    def render_macro_definition(self, macro, ir) -> list[str]:
        body = self.render_expression(macro.body, ir)
        params = ", ".join(macro.params)
        return [f"{macro.name} .sfunction {params}, {body}"]

    # 64tass has native string indexing/slicing/length, so a non-constant
    # string op (e.g. a macro parameter) renders directly.
    def render_string_index(self, string_node, index_node, render) -> str:
        return f"{render(string_node)}[{render(index_node)}]"

    def render_string_slice(self, s: str, i: str, j: "str | None") -> str:
        return f"{s}[{i}:{j if j is not None else ''}]"

    def render_string_length(self, s: str) -> str:
        return f"len({s})"

    # No ``translate_expression`` override is needed: driver-authored
    # dialect strings are parsed into structured Expr trees at
    # registration time (dasmos.core.expr_parse) and rendered through the
    # tokens/precedence above, so nothing beebasm-flavoured reaches this
    # backend. A Raw node (an unparseable string) falls back to the base
    # verbatim behaviour, which the round-trip oracle confirms is never
    # exercised by the sibling ROMs.
