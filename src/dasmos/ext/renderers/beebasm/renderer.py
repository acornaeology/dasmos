"""Beebasm-syntax renderer for dasmos.

Beebasm is the BBC-Micro-style 6502 assembler at
<https://github.com/stardot/beebasm>; full source available locally
at ``/Users/rjs/Code/beebasm`` for unambiguous reference.

This is the **first text-syntax renderer** dasmos ships. It is the
reference implementation against which the round-trip property is
validated:

.. code-block::

    binary  ──[dasmos]──►  IR  ──[BeebasmRenderer]──►  source
                                                          │
                                                          ▼
                                                       beebasm
                                                          │
                                                          ▼
                                                  binary' (== binary)

Lifted from py8dis's ``beebasm.py`` (333 lines) plus the rendering
helpers from ``mainformatter.py``. The split between "compute
operand text" and "emit surrounding line" is dasmos-specific; py8dis
mixed both in the same class.

Deferred from this first cut (lands with later ports):

- Inline hex-dump comments (need :class:`AnnotationStore`).
- Standalone comment / banner / annotation rendering (need
  :mod:`comment` + :mod:`markdown_asm` ports).
- Constant table emission (``equb foo = &XX``) — needs
  :class:`ConstantStore`.
- External / optional label definitions at the top of the output —
  need :class:`OptionalLabelStore`.
- ``pseudopc_start`` / ``pseudopc_end`` for relocated blocks —
  needs the move-manager-aware emit pass.
- CPU-state hints in inline comments.
- Cycle counts.

The rendering walk is currently linear over
:meth:`ClassificationStore.iter_classified_starts`, which is enough
for the first round-trip slice (no relocations).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.core.annotations import Align, Annotation, Comment
from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import TextOutput
from dasmos.renderer import TextRenderer

# Trailing column for inline comments. A future config knob; matches
# py8dis's default.
INLINE_COMMENT_COLUMN = 40

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


# Beebasm's mnemonics are the canonical lowercase MOS form, so the
# Operation enum's ``value`` (e.g. ``"lda"``) gives us the right text
# directly via ``Opcode.default_mnemonic()``. No per-pair override
# table needed for Beebasm — see docs/design/decisions.md D-021 for
# why this is structured the way it is.


class BeebasmRenderer(TextRenderer):
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
    #: covers exactly the disassembled byte range. Override via the
    #: constructor's ``boundary_label_prefix`` keyword to use a
    #: different prefix — e.g. ``"pydis_"`` for byte-for-byte text
    #: compatibility with py8dis-fork output during migration testing.
    DEFAULT_BOUNDARY_LABEL_PREFIX = "dasmos_"

    def __init__(
        self,
        name: str = "beebasm",
        *,
        boundary_label_prefix: str | None = None,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        # Beebasm wants ``ROL A`` (explicit accumulator), not just ``ROL``.
        self.explicit_a = True
        self.boundary_label_prefix = (
            boundary_label_prefix
            if boundary_label_prefix is not None
            else self.DEFAULT_BOUNDARY_LABEL_PREFIX
        )

    @property
    def boundary_start_label(self) -> str:
        """The ``.label`` placed at the start of the loaded region."""
        return f"{self.boundary_label_prefix}start"

    @property
    def boundary_end_label(self) -> str:
        """The ``.label`` placed one past the end of the loaded region."""
        return f"{self.boundary_label_prefix}end"

    # -- lexical building blocks ------------------------------------------

    def cpus_supported(self) -> list[str]:
        # Beebasm itself supports both 6502 and 65C02 (via ``cpu 1``);
        # dasmos's NMOS 6502 plug-in is named ``nmos6502``.
        return ["nmos6502", "cmos65c02"]

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
        # The 65C02 ``cpu 1`` directive belongs here when the CPU is
        # CMOS — defer until we expose a CPU-flavour hint on the IR.
        return []

    def disassembly_end(self) -> list[str]:
        # ``save <start>, <end>`` references the boundary labels
        # render() emits around the loaded range, so beebasm produces
        # a binary identical in size. The label prefix is
        # configurable — see DEFAULT_BOUNDARY_LABEL_PREFIX.
        out: list[str] = [""]
        save_args = f"{self.boundary_start_label}, {self.boundary_end_label}"
        if self.output_filename is not None:
            out.append(f'save "{self.output_filename}", {save_args}')
        else:
            out.append(f"save {save_args}")
        return out

    def code_start(self, start_addr, end_addr, first: bool) -> list[str]:
        # Blank line before, ORG line, blank line after — matches
        # py8dis's spacing for readability and round-trip stability.
        return ["", f"    org {self.hex4(int(start_addr))}", ""]

    def code_end(self) -> list[str]:
        return []

    def pseudopc_start(self, dest, source, length, move_id) -> list[str]:
        # Relocation block emission is deferred — see module docstring.
        return []

    def pseudopc_end(self, dest, source, length, move_id) -> list[str]:
        return []

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

    def fill_directive(self, value: int, length: int) -> list[str]:
        # Beebasm has no native fill-with-value; a FOR/NEXT loop
        # produces exactly N copies at assembly time. The loop
        # variable name is deliberately unusual to avoid colliding
        # with anything a driver script might have declared.
        if length <= 0:
            return []
        return [f"for _dasmos_fill%, 1, {length} : equb {self.hex2(value)} : next"]

    # -- the rendering walk ------------------------------------------------

    def render(self, ir: "IntermediateRepresentation") -> TextOutput:
        """Walk the IR's classifications in binary-address order and
        emit a beebasm source listing.

        Emits ``ORG`` at the start of the loaded range, the marker
        labels (``{boundary_label_prefix}start`` /
        ``{boundary_label_prefix}end``) so the trailing ``save``
        directive bounds exactly the disassembled range, and the
        per-classification line(s) for each entry in the
        :class:`ClassificationStore`.
        """
        lines: list[str] = []
        lines.extend(self.disassembly_start())

        try:
            load_start, load_end = ir.memory.entire_load_range()
        except Exception:
            # No data loaded — nothing to render.
            lines.extend(self.disassembly_end())
            return TextOutput("\n".join(lines) + "\n")

        # ORG + start marker.
        lines.extend(self.code_start(load_start, load_end, first=True))
        lines.append(self.inline_label(self.boundary_start_label))

        # Walk classifications in order. Anything between classified
        # addresses is unclassified-loaded data (already covered by
        # the leftover-classification pass) so iter_classified_starts
        # produces a complete walk.
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            # Skip anything outside the loaded range — happens when
            # the user adds classifications manually before loading.
            if not (int(load_start) <= int(binary_addr) < int(load_end)):
                continue

            # Emit BEFORE_LABEL annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.BEFORE_LABEL):
                lines.append(self._render_annotation(ann))

            # Emit any inline labels at this address (sorted for
            # deterministic output).
            label = ir.labels.get_label(int(binary_addr))
            if label is not None:
                for name in sorted(label.all_names()):
                    lines.append(self.inline_label(name))

            # Emit AFTER_LABEL annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.AFTER_LABEL):
                lines.append(self._render_annotation(ann))

            # Emit BEFORE_LINE annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.BEFORE_LINE):
                lines.append(self._render_annotation(ann))

            # Emit the classification's text line(s).
            content_lines = self._render_classification(ir, binary_addr, classification)

            # Append any INLINE comments to the last content line.
            inline_anns = ir.annotations.get_for_align(int(binary_addr), Align.INLINE)
            if inline_anns and content_lines:
                inline_text = "  ".join(
                    self._render_annotation_inline(a) for a in inline_anns
                )
                last = content_lines[-1]
                # Pad to the inline-comment column if there's room.
                if len(last) < INLINE_COMMENT_COLUMN:
                    last = last.ljust(INLINE_COMMENT_COLUMN)
                else:
                    last = last + "  "
                content_lines[-1] = f"{last}{inline_text}"

            lines.extend(content_lines)

            # Emit AFTER_LINE annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.AFTER_LINE):
                lines.append(self._render_annotation(ann))

        # End marker + save directive.
        lines.append(self.inline_label(self.boundary_end_label))
        lines.extend(self.disassembly_end())

        return TextOutput("\n".join(lines) + "\n")

    # -- annotations ------------------------------------------------------

    def _render_annotation(self, ann) -> str:
        """Render a Comment or Annotation as a standalone line."""
        if isinstance(ann, Comment):
            indent = " " * (ann.indent * 4) if ann.indent else ""
            return f"{indent}{self.comment_prefix()} {ann.text}"
        if isinstance(ann, Annotation):
            return ann.text
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    def _render_annotation_inline(self, ann) -> str:
        """Render a Comment or Annotation as the inline (trailing) form."""
        if isinstance(ann, Comment):
            return f"{self.comment_prefix()} {ann.text}"
        if isinstance(ann, Annotation):
            return ann.text
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    # -- per-classification rendering -------------------------------------

    def _render_classification(
        self, ir, binary_addr, c
    ) -> list[str]:
        """Dispatch to the right per-type rendering method."""
        if isinstance(c, Opcode):
            return [self._render_opcode(ir, binary_addr, c)]
        if isinstance(c, Byte):
            return self._render_byte(ir, binary_addr, c)
        if isinstance(c, Word):
            return self._render_word(ir, binary_addr, c)
        if isinstance(c, Fill):
            return ["    " + self.fill_directive(c.value(), c.length())[0]]
        if isinstance(c, String):
            return self._render_string(ir, binary_addr, c)
        raise TypeError(
            f"BeebasmRenderer does not know how to render {type(c).__name__}"
        )

    def _render_opcode(self, ir, binary_addr, opcode: Opcode) -> str:
        """Format a single instruction line."""
        mnemonic = opcode.default_mnemonic()
        operand = self._render_operand(ir, binary_addr, opcode)
        if operand:
            return f"    {mnemonic} {operand}"
        return f"    {mnemonic}"

    def _render_operand(self, ir, binary_addr, opcode: Opcode) -> str:
        """Format the operand for an opcode based on its addressing
        mode. Uses a label name in place of the literal address when
        a label is registered at the target.
        """
        mode = opcode.addressing_mode
        kind = mode.operand_kind
        operand_addr = int(binary_addr) + 1
        # Identify mode shape by name; this is a per-renderer concern
        # so the dispatch lives here, not on the CPU plug-in.
        mode_name = mode.name

        if mode_name == "IMPLIED":
            return ""
        if mode_name == "ACCUMULATOR":
            return "A" if self.explicit_a else ""

        if mode_name == "IMMEDIATE":
            v = ir.memory.get_u8(operand_addr)
            return f"#{self.hex2(v)}"

        # Direct addressing — the operand IS the target address.
        if mode_name == "ZERO_PAGE":
            v = ir.memory.get_u8(operand_addr)
            return self._addr_text(ir, v, width=8)
        if mode_name == "ZERO_PAGE_X":
            v = ir.memory.get_u8(operand_addr)
            return f"{self._addr_text(ir, v, width=8)},X"
        if mode_name == "ZERO_PAGE_Y":
            v = ir.memory.get_u8(operand_addr)
            return f"{self._addr_text(ir, v, width=8)},Y"

        if mode_name == "ABSOLUTE":
            v = ir.memory.get_u16_le(operand_addr)
            return self._addr_text(ir, v, width=16)
        if mode_name == "ABSOLUTE_X":
            v = ir.memory.get_u16_le(operand_addr)
            return f"{self._addr_text(ir, v, width=16)},X"
        if mode_name == "ABSOLUTE_Y":
            v = ir.memory.get_u16_le(operand_addr)
            return f"{self._addr_text(ir, v, width=16)},Y"

        if mode_name == "INDIRECT":
            v = ir.memory.get_u16_le(operand_addr)
            return f"({self._addr_text(ir, v, width=16)})"
        if mode_name == "INDEXED_INDIRECT":  # (zp,X)
            v = ir.memory.get_u8(operand_addr)
            return f"({self._addr_text(ir, v, width=8)},X)"
        if mode_name == "INDIRECT_INDEXED":  # (zp),Y
            v = ir.memory.get_u8(operand_addr)
            return f"({self._addr_text(ir, v, width=8)}),Y"

        if mode_name == "RELATIVE":
            offset = ir.memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            target = int(binary_addr) + opcode.length() + offset
            return self._addr_text(ir, target, width=16)

        raise ValueError(
            f"BeebasmRenderer does not know how to render addressing mode "
            f"{mode_name!r}"
        )

    def _addr_text(self, ir, addr: int, *, width: int) -> str:
        """Render an address operand: a label name if one is registered,
        otherwise the appropriate hex literal.
        """
        label = ir.labels.get_label(addr)
        if label is not None:
            names = sorted(label.all_names())
            if names:
                return names[0]
        return self.hex2(addr) if width == 8 else self.hex4(addr)

    def _render_byte(self, ir, binary_addr, c: Byte) -> list[str]:
        """Render a Byte block as one or more ``equb`` lines."""
        cols = c.cols() or 8
        values = [
            ir.memory.get_u8(int(binary_addr) + i) for i in range(c.length())
        ]
        lines = []
        for chunk_start in range(0, len(values), cols):
            chunk = values[chunk_start:chunk_start + cols]
            text = ", ".join(self.hex2(v) for v in chunk)
            lines.append(f"    {self.byte_prefix()}{text}")
        return lines

    def _render_word(self, ir, binary_addr, c: Word) -> list[str]:
        """Render a Word block as one or more ``equw`` lines."""
        cols = c.cols() or 4
        words = [
            ir.memory.get_u16_le(int(binary_addr) + i * 2)
            for i in range(c.length() // 2)
        ]
        lines = []
        for chunk_start in range(0, len(words), cols):
            chunk = words[chunk_start:chunk_start + cols]
            text = ", ".join(self._addr_text(ir, w, width=16) for w in chunk)
            lines.append(f"    {self.word_prefix()}{text}")
        return lines

    def _render_string(self, ir, binary_addr, c: String) -> list[str]:
        """Render a String classification.

        Naive first cut: emits ``equs`` for runs of printable
        characters and ``equb`` for non-printable bytes, on a single
        line. Round-trip-correct; not necessarily the prettiest
        rendering py8dis produces.
        """
        bytes_ = [
            ir.memory.get_u8(int(binary_addr) + i) for i in range(c.length())
        ]
        parts: list[str] = []
        run: list[int] = []

        def flush_run():
            if not run:
                return
            text = "".join(chr(b) for b in run)
            parts.append(f'"{text}"')
            run.clear()

        for b in bytes_:
            if self.string_chr(b) is not None:
                run.append(b)
            else:
                flush_run()
                parts.append(self.hex2(b))
        flush_run()

        if not parts:
            return []
        # Join with ", "; first part determines whether we lead with
        # equs or equb.
        first_is_string = parts[0].startswith('"')
        prefix = self.string_prefix() if first_is_string else self.byte_prefix()
        return [f"    {prefix}{', '.join(parts)}"]
