"""Beebasm-syntax renderer for dasmos.

Beebasm is the BBC-Micro-style 6502 assembler at
<https://github.com/stardot/beebasm>; full source available locally
at ``/Users/rjs/Code/beebasm`` for unambiguous reference.

This is the reference text-syntax renderer against which the round-trip
property is validated:

.. code-block::

    binary  ──[dasmos]──►  IR  ──[BeebasmRenderer]──►  source
                                                          │
                                                          ▼
                                                       beebasm
                                                          │
                                                          ▼
                                                  binary' (== binary)

The generic rendering walk lives on
:class:`~dasmos.asm_renderer.AssemblerRenderer`; this class supplies only
the beebasm-specific lexical protocol and directives (``&`` hex,
``equb`` / ``equw`` / ``equs`` data, ``;`` comments, ``.foo`` labels,
``save`` / ``cpu`` directives, the ``copyblock`` relocation idiom, and
the beebasm ``FormatHint`` translation).
"""

from __future__ import annotations

import warnings

from dasmos.asm_renderer import AssemblerRenderer
from dasmos.core.format_hint import FormatHint
from dasmos.cpu import Opcode

# Beebasm's mnemonics are the canonical lowercase MOS form, so the
# Operation enum's ``value`` (e.g. ``"lda"``) gives us the right text
# directly via ``Opcode.default_mnemonic()``. No per-pair override
# table needed for Beebasm — see docs/design/decisions.md D-021 for
# why this is structured the way it is.


class BeebasmRenderer(AssemblerRenderer):
    """Beebasm-syntax renderer.

    Produces a beebasm-compatible source listing from a dasmos IR.
    Use the ``beebasm`` command-line tool to assemble back to binary;
    the result should byte-for-byte match the original input — the
    round-trip property dasmos's CI gates on.

    The lexical building blocks (``hex2`` / ``hex4`` / ``byte_prefix``
    / etc.) all match Beebasm: ``&`` for hex, ``equb`` / ``equw`` /
    ``equs`` for data, ``;`` for comments, ``.foo`` for inline labels,
    ``foo = &XXXX`` for explicit labels.
    """

    #: Default prefix used for the inline boundary labels that bracket
    #: the loaded region (``{prefix}start`` / ``{prefix}end``). Beebasm's
    #: ``save`` directive references these so the produced binary
    #: covers exactly the disassembled byte range.
    #:
    #: Override via the constructor's ``boundary_label_prefix`` keyword
    #: to use a different prefix — e.g. ``"pydis_"`` for byte-for-byte
    #: text compatibility with py8dis-fork output during migration
    #: testing — or pass ``""`` (the empty string) to suppress the
    #: marker labels entirely; the ``save`` directive then references
    #: literal hex addresses for the loaded range.
    DEFAULT_BOUNDARY_LABEL_PREFIX = "dasmos_"

    def __init__(
        self,
        name: str = "beebasm",
        *,
        boundary_label_prefix: str | None = None,
        byte_column: bool = False,
        byte_column_format: str = "dasmos",
        default_byte_cols: int = 8,
        default_word_cols: int = 4,
        show_auto_label_footer: bool = True,
        comment_wrap_column: int = 87,
        char_literal_style: str = "asc",
        show_char_comment_hint: bool = True,
        lower_case: bool = True,
        **kwargs,
    ):
        # ``None`` means "use the default"; ``""`` means "suppress".
        resolved_prefix = (
            boundary_label_prefix
            if boundary_label_prefix is not None
            else self.DEFAULT_BOUNDARY_LABEL_PREFIX
        )
        super().__init__(
            name=name,
            boundary_label_prefix=resolved_prefix,
            byte_column=byte_column,
            byte_column_format=byte_column_format,
            default_byte_cols=default_byte_cols,
            default_word_cols=default_word_cols,
            show_auto_label_footer=show_auto_label_footer,
            comment_wrap_column=comment_wrap_column,
            lower_case=lower_case,
            **kwargs,
        )
        # Beebasm wants ``ROL A`` (explicit accumulator), not just ``ROL``.
        self.explicit_a = True
        # Syntax for the OPERAND-REPLACING char form, used ONLY when the
        # driver registers an explicit ``FormatHint.CHAR`` at an operand
        # byte:
        # - ``"asc"`` (default): ``ASC("c")`` — beebasm's first-
        #   character-of-string function.
        # - ``"quote"``: ``'c'`` — the universal single-quoted-char form.
        valid_styles = {"asc", "quote"}
        if char_literal_style not in valid_styles:
            raise ValueError(
                f"char_literal_style must be one of "
                f"{sorted(valid_styles)!r}, got {char_literal_style!r}"
            )
        self.char_literal_style = char_literal_style
        # When True (default), append a ``; '<c>'`` informational comment
        # to immediate-mode instructions whose operand byte happens to be
        # a printable ASCII character.
        self.show_char_comment_hint = show_char_comment_hint

    def cpus_supported(self) -> list[str]:
        # Beebasm itself supports both 6502 and 65C02 (the latter via
        # ``cpu 1``).
        return ["6502", "65C02"]

    def hex2(self, n: int) -> str:
        return f"&{n:02x}"

    def hex4(self, n: int) -> str:
        return f"&{n:04x}"

    def comment_prefix(self) -> str:
        return ";"

    def byte_prefix(self) -> str:
        return "equb "

    def word_prefix(self) -> str:
        return "equw "

    def string_prefix(self) -> str:
        return "equs "

    def inline_label(self, name: str) -> str:
        return f".{name}"

    def explicit_label(
        self, name: str, value, offset: int | None = None, align_column: int = 0,
    ) -> str:
        suffix = "" if offset is None else f"+{offset}"
        # Padding at the equals sign is for the eventual aligned
        # "label = value" block at the top of the output; for inline
        # use the natural form.
        if align_column > 0:
            padded = name.ljust(align_column)
            return f"{padded} = {value}{suffix}"
        return f"{name} = {value}{suffix}"

    def disassembly_start(self) -> list[str]:
        # The CPU-specific ``cpu N`` directive (CMOS variants) is emitted
        # from :meth:`render`, where the IR is in scope so we can read
        # the CPU plug-in's name.
        return []

    def cpu_directive_for(self, cpu_name: str) -> str | None:
        """Return the beebasm ``cpu N`` directive for ``cpu_name``, or
        ``None`` when no directive is needed (the default 6502).

        Beebasm's CPU selector is documented at
        <https://github.com/stardot/beebasm/blob/master/manual.md>:
        ``cpu 0`` (default) selects the NMOS 6502; ``cpu 1`` enables
        the CMOS 65C02 instruction set extensions.
        """
        if cpu_name == "65C02":
            return "cpu 1"
        return None

    def disassembly_end(self) -> list[str]:
        # The ``save`` directive isn't emitted from here any more —
        # it depends on the load range, which only ``render()`` has
        # access to. ``render()`` calls ``_save_directive()`` for that.
        # ``disassembly_end`` is now reserved for whatever truly
        # belongs at the very end (assertions, trailing newlines).
        return []

    def _save_directive(self, load_start, load_end) -> str:
        """Render the ``save`` directive for the loaded range.

        Uses the boundary marker labels when they're configured;
        falls back to literal hex addresses when they're suppressed
        (``boundary_label_prefix=""``).
        """
        if self.emit_boundary_labels:
            save_args = (
                f"{self.boundary_start_label}, {self.boundary_end_label}"
            )
        else:
            save_args = (
                f"{self.hex4(int(load_start))}, {self.hex4(int(load_end))}"
            )
        if self.output_filename is not None:
            return f'save "{self.output_filename}", {save_args}'
        return f"save {save_args}"

    def code_start(self, start_addr, end_addr, first: bool) -> list[str]:
        # Blank line before, ORG line, blank line after — readability
        # plus round-trip stability.
        return ["", f"    org {self.hex4(int(start_addr))}", ""]

    def code_end(self) -> list[str]:
        return []

    def set_origin(self, addr: int) -> list[str]:
        # A blank line then an ``org`` to reposition the assembly PC.
        return ["", f"    org {self.hex(int(addr))}"]

    def pseudopc_start(
        self, *, dest, src, length, move_id, src_label, dest_label,
    ) -> list[str]:
        """Switch beebasm's PC into the relocated destination range.

        Layout::

            <blank>
            ; Move <id>: &<src> to &<dest> for length <N>
                org &<dest>

        The source label (if any) is emitted by the shared walk
        *before* this block, so the source position has its symbolic
        anchor before PC switches away.
        """
        return [
            "",
            (
                f"{self.comment_prefix()} Move {move_id}: "
                f"{self.hex(int(src))} to "
                f"{self.hex(int(dest))} for length "
                f"{length}"
            ),
            f"    org {self.hex(int(dest))}",
        ]

    def pseudopc_end(
        self, *, dest, src, length, move_id, src_label, dest_label,
    ) -> list[str]:
        """Close out a relocated block:

            <blank>
                copyblock <dest>, *, <src>
                clear <dest>, &<dest_end>
                org <src> + (* - <dest>)
            <blank>

        Beebasm's ``copyblock`` copies the assembled bytes from the
        scratch destination range back to the corresponding file
        position. ``clear`` wipes the scratch space so beebasm can
        reuse it. The final ``org`` restores PC to the next position
        in the source binary.

        Falls back to literal hex when no label exists at one of the
        anchors — beebasm accepts both, just less readable.
        """
        src_anchor = src_label or self.hex(int(src))
        dest_anchor = dest_label or self.hex(int(dest))
        dest_end = int(dest) + length
        cp = self.comment_prefix()
        return [
            "",
            "",
            f"    {cp} Copy the newly assembled block of code back to "
            "it's proper place in the binary",
            f"    {cp} file.",
            f"    {cp} (Note the parameter order: "
            "'copyblock <start>,<end>,<dest>')",
            f"    copyblock {dest_anchor}, *, {src_anchor}",
            "",
            f"    {cp} Clear the area of memory we just temporarily "
            "used to assemble the new block,",
            f"    {cp} allowing us to assemble there again if needed",
            f"    clear {dest_anchor}, {self.hex(dest_end)}",
            "",
            f"    {cp} Set the program counter to the next position "
            "in the binary file.",
            f"    org {src_anchor} + (* - {dest_anchor})",
            "",
        ]

    def char_literal(self, n: int) -> str | None:
        # Beebasm accepts single-quoted printable characters except
        # the quote itself.
        if 32 <= n <= 126 and n not in (ord('"'), ord("'")):
            return f"'{chr(n)}'"
        return None

    def string_chr(self, n: int) -> str | None:
        # Inside a double-quoted string: anything printable except the
        # closing quote.
        if 32 <= n <= 126 and n != ord('"'):
            return chr(n)
        return None

    # Beebasm has no value-returning function, so a macro is a code macro
    # that EMITS the datum (``EQUB``/``EQUW``); each invocation is its own
    # statement line (``pack "LDA"``). ``macro_calls_are_values`` stays
    # False (the base default), so the byte-block renderer emits the
    # invocations as statements.
    @property
    def macro_statements_are_supported(self) -> bool:
        # Beebasm has a code-macro (MACRO … ENDMACRO), so a data-item
        # macro call renders natively as its own statement line.
        return True

    def render_macro_definition(self, macro, ir) -> list[str]:
        body = self.render_expression(macro.body, ir)
        directive = {"byte": self.byte_prefix(), "word": self.word_prefix()}.get(
            macro.emit, self.byte_prefix()
        )
        params = ", ".join(macro.params)
        return [
            f"MACRO {macro.name} {params}",
            f"    {directive}{body}",
            "ENDMACRO",
        ]

    def render_macro_statement(self, call, ir) -> list[str]:
        args = ", ".join(self._macro_arg_texts(call, ir))
        return [f"    {call.name} {args}"]

    def render_bitwise_not(self, inner_text: str) -> str:
        # Beebasm spells bitwise complement as the function ``NOT(...)``,
        # not the ``~`` operator (which it doesn't have).
        return f"NOT({inner_text})"

    # Beebasm string functions are 1-based (MID$); character code via
    # ASC. Used only for a non-constant string op (a macro parameter) —
    # constant ones are folded to character literals before rendering.
    def render_string_index(self, string_node, index_node, render) -> str:
        # MID$ is 1-based; fold a constant index to a clean literal
        # position, otherwise render the ``+ 1`` arithmetically.
        from dasmos.core.expr import Int
        if isinstance(index_node, Int):
            pos = str(index_node.value + 1)
        else:
            pos = f"{render(index_node)} + 1"
        return f"ASC(MID$({render(string_node)}, {pos}, 1))"

    def render_string_slice(self, s: str, i: str, j: "str | None") -> str:
        if j is None:
            return f"MID$({s}, {i} + 1)"
        return f"MID$({s}, {i} + 1, {j} - {i})"

    def render_string_length(self, s: str) -> str:
        return f"LEN({s})"

    def fill_directive(self, value: int, length: int) -> list[str]:
        # Beebasm has no native fill-with-value; a FOR/NEXT loop
        # produces exactly N copies at assembly time. The loop
        # variable name is deliberately unusual to avoid colliding
        # with anything a driver script might have declared.
        if length <= 0:
            return []
        return [f"for _dasmos_fill%, 1, {length} : equb {self.hex2(value)} : next"]

    def _render_hinted_immediate(
        self, hint: FormatHint, value: int, operand_addr: int,
    ) -> str:
        """Translate a :class:`FormatHint` to beebasm operand syntax.

        Each branch attempts the natural beebasm form for the hint;
        when beebasm can't express it (or the byte's value can't be
        represented cleanly — e.g. a non-printable byte under
        ``CHAR``), the renderer issues a ``UserWarning`` describing
        the fallback and emits a hex literal.
        """
        if hint is FormatHint.CHAR:
            text = self._render_char_for_explicit_hint(value)
            if text is not None:
                return text
            warnings.warn(
                f"FormatHint.CHAR at &{operand_addr:04x} can't be "
                f"expressed as a beebasm character literal for byte "
                f"&{value:02x} (non-printable); falling back to "
                f"a numeric literal.",
                stacklevel=2,
            )
            return self._format_immediate_byte(value)
        if hint is FormatHint.DECIMAL:
            return str(value)
        if hint is FormatHint.HEX:
            return self.hex2(value)
        if hint is FormatHint.BINARY:
            # Beebasm's ``%`` sigil + 8-bit bit pattern.
            return f"%{value:08b}"
        if hint is FormatHint.OCTAL:
            # Beebasm has no native octal syntax. Emit decimal and
            # warn so the user can pick another representation if
            # the fallback isn't acceptable.
            warnings.warn(
                f"FormatHint.OCTAL at &{operand_addr:04x} — beebasm "
                f"has no octal literal; falling back to decimal "
                f"{value} (octal {value:o}).",
                stacklevel=2,
            )
            return str(value)
        if hint is FormatHint.INKEY:
            return self._render_inkey_immediate(value, operand_addr)
        # Future hint values land here as an explicit, informative
        # error rather than a silent fallthrough.
        raise NotImplementedError(
            f"BeebasmRenderer doesn't yet handle FormatHint.{hint.name}"
        )

    def _render_char_for_explicit_hint(self, value: int) -> str | None:
        """Best-effort beebasm character literal for an explicitly-
        marked ``CHAR`` byte. Returns ``None`` when the byte has no
        clean beebasm character literal (caller falls back to hex
        with a warning).

        Tries the renderer's preferred ``char_literal_style`` first,
        then cross-style fallbacks for the quote chars where the
        primary style can't unambiguously express them.
        """
        if not (0x20 <= value <= 0x7E):
            return None
        c = chr(value)
        # Quote-char cross-fallback: each style's natural form has a
        # blind spot at one of ``'`` / ``"``; the OTHER style covers it.
        if value == 0x22:  # double-quote: clean as 'c' form
            return f"'{c}'"
        if value == 0x27:  # apostrophe: clean as ASC("c") form
            return f'ASC("{c}")'
        # Other printable bytes follow the renderer's preferred style.
        # ``"comment"`` and ``"off"`` styles have no native operand-
        # replacement form; default to ASC for explicit hints since
        # that's the user's "render this AS A CHAR" intent.
        if self.char_literal_style == "quote":
            return f"'{c}'"
        return f'ASC("{c}")'

    def _immediate_char_hint(self, ir, binary_addr, opcode: Opcode) -> str:
        """Return a `` ; '<c>'`` informational comment for IMMEDIATE
        operands whose byte happens to be a printable ASCII character.
        Returns the empty string in every suppression case.

        This is the renderer's *only* auto-detection: a safe trailing
        annotation that doesn't claim "this byte IS a character",
        merely "this byte's ASCII rendering is X". Operand-replacing
        char forms (``ASC("c")`` / ``'c'``) only ever fire from an
        EXPLICIT :class:`FormatHint.CHAR` registration in the IR.

        Suppression conditions:

        - ``show_char_comment_hint`` is False on this renderer.
        - The opcode's addressing mode isn't IMMEDIATE.
        - A user-supplied expression is registered at the operand
          byte (the user's symbol takes precedence).
        - A :class:`FormatHint` is registered at the operand byte —
          the hint already decided how to render this operand, and
          a parallel comment annotation would be redundant or
          contradictory (e.g. a ``BINARY`` hint produces ``%01010101``
          and the user already knows the byte's ASCII rendering
          isn't relevant).
        - The byte isn't printable ASCII (``0x20..0x7E``).
        - The byte is ``'`` or ``"`` — would form ambiguous
          comment syntax (``; '''`` / ``; '"'``).
        """
        if not self.show_char_comment_hint:
            return ""
        if opcode.addressing_mode.name != "IMMEDIATE":
            return ""
        operand_addr = int(binary_addr) + 1
        if ir.expressions.get_or_none(operand_addr) is not None:
            return ""
        if ir.format_hints.get_or_none(operand_addr) is not None:
            return ""
        value = ir.memory.get_u8(operand_addr)
        if not (0x20 <= value <= 0x7E):
            return ""
        if value in (0x22, 0x27):  # ", '
            return ""
        return f" ; '{chr(value)}'"
