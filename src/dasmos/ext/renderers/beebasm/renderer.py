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

from dasmos.core.annotations import Align, Annotation, Banner, Comment
from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.memory import BinaryAddr
from dasmos.core.move import MoveDefinition
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import TextOutput
from dasmos.renderer import TextRenderer

# Trailing column for inline comments. A future config knob; matches
# py8dis's default.
INLINE_COMMENT_COLUMN = 40

# When ``byte_column`` is enabled, instructions are padded further so
# the byte annotation has room before any user comment. Matches py8dis.
INSTRUCTION_PAD_WITH_BYTE_COLUMN = 70

# Total width occupied by a byte-column annotation
# (``<addr>: <hex>  <ascii>``) — used when both byte column and user
# comment are present on the same line. Roughly: ``&XXXX: `` (7) +
# bytes section (8 = max 3 bytes "XX YY ZZ") + gap + ascii (3-char
# field). Matches the visual width of py8dis's column.
BYTE_COLUMN_TOTAL_WIDTH = 27

# Banner separator width: a row of this many ``*`` characters,
# prefixed by the comment prefix and a space, between the title and
# the surrounding text. Matches py8dis's default of 87.
BANNER_SEPARATOR_WIDTH = 87

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
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        # Beebasm wants ``ROL A`` (explicit accumulator), not just ``ROL``.
        self.explicit_a = True
        # ``None`` means "use the default"; ``""`` means "suppress".
        self.boundary_label_prefix = (
            boundary_label_prefix
            if boundary_label_prefix is not None
            else self.DEFAULT_BOUNDARY_LABEL_PREFIX
        )
        # When True, attach a ``; <addr>: <hex bytes>  <ascii>``
        # annotation to the first content line of every classification.
        # Off by default — drivers that want a clean rendered listing
        # leave it off; the porter and py8dis-parity tests opt in.
        self.byte_column = byte_column

    @property
    def emit_boundary_labels(self) -> bool:
        """True iff this renderer is configured to emit start/end
        marker labels around the loaded range. False when
        ``boundary_label_prefix`` is the empty string.
        """
        return bool(self.boundary_label_prefix)

    @property
    def boundary_start_label(self) -> str | None:
        """The ``.label`` placed at the start of the loaded region,
        or ``None`` if marker labels are suppressed.
        """
        if not self.emit_boundary_labels:
            return None
        return f"{self.boundary_label_prefix}start"

    @property
    def boundary_end_label(self) -> str | None:
        """The ``.label`` placed one past the end of the loaded region,
        or ``None`` if marker labels are suppressed.
        """
        if not self.emit_boundary_labels:
            return None
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
        if cpu_name == "cmos65c02":
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

    def _reset_render_state(self) -> None:
        """Reset per-render tracking state. Called at the start of
        every :meth:`render` call so the renderer is reusable across
        multiple IRs.
        """
        # Runtime addresses of out-of-range labels we resolved to a
        # name during operand rendering. The explicit-label table at
        # the top of the output emits these (plus all required
        # out-of-range labels regardless of usage).
        self._used_external_labels: set[int] = set()
        # Per-label use sites collected during the reference-tracking
        # pre-pass (binary addresses of opcodes whose operand resolves
        # to a name on this label). Keyed by runtime address.
        self._label_references: dict[int, list[int]] = {}

    def render(self, ir: "IntermediateRepresentation") -> TextOutput:
        """Walk the IR's classifications in binary-address order and
        emit a beebasm source listing.

        Emits an explicit-label table for out-of-range labels (the
        ``name = &xxxx`` block at the top), then ``ORG`` at the start
        of the loaded range, the marker labels
        (``{boundary_label_prefix}start`` /
        ``{boundary_label_prefix}end``) so the trailing ``save``
        directive bounds exactly the disassembled range, and the
        per-classification line(s) for each entry in the
        :class:`ClassificationStore`.
        """
        self._reset_render_state()

        lines: list[str] = []
        lines.extend(self.disassembly_start())

        # CPU-flavour directive (e.g. ``cpu 1`` for 65C02).
        cpu_directive = self.cpu_directive_for(ir.cpu.name)
        if cpu_directive is not None:
            lines.append(cpu_directive)

        try:
            load_start, load_end = ir.memory.entire_load_range()
        except Exception:
            # No data loaded — nothing to render.
            lines.extend(self.disassembly_end())
            return TextOutput("\n".join(lines) + "\n")

        # Pre-pass: walk every classified opcode, resolve its operand
        # to a target address, and record use sites against any label
        # found there. The body walk below uses this to emit per-label
        # xref summaries; the trailing frequency table also reads it.
        self._compute_references(ir)

        # ORG + optional start marker (omitted when prefix is empty).
        lines.extend(self.code_start(load_start, load_end, first=True))
        if self.boundary_start_label is not None:
            lines.append(self.inline_label(self.boundary_start_label))

        # Pre-compute move-region boundaries: ``{src_binary_addr: move_def}``
        # for every registered (non-base) move. The body walk uses this to
        # detect when iteration enters or exits a relocated region.
        moves_by_src = self._moves_by_src_addr(ir)
        active_move = None
        active_move_src_label: str | None = None
        active_move_dest_label: str | None = None

        # Walk classifications in order. Anything between classified
        # addresses is unclassified-loaded data (already covered by
        # the leftover-classification pass) so iter_classified_starts
        # produces a complete walk.
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            # Skip anything outside the loaded range — happens when
            # the user adds classifications manually before loading.
            if not (int(load_start) <= int(binary_addr) < int(load_end)):
                continue

            # Move-region exit: if the iteration has stepped past the
            # end of the active relocated block, emit the close-out
            # directives and resume in the source-PC context.
            if active_move is not None and int(binary_addr) >= (
                int(active_move.src_binary_addr) + active_move.length
            ):
                lines.extend(self._emit_move_exit(
                    active_move, active_move_src_label, active_move_dest_label,
                ))
                active_move = None
                active_move_src_label = None
                active_move_dest_label = None

            # Move-region entry: if this binary address is the start
            # of a relocation, anchor the source label here, switch PC
            # to the destination, and remember the labels we need for
            # the close-out.
            if active_move is None and int(binary_addr) in moves_by_src:
                move = moves_by_src[int(binary_addr)]
                active_move_src_label = self._first_explicit_name(
                    ir, int(binary_addr),
                )
                active_move_dest_label = self._first_explicit_name(
                    ir, int(move.dest_runtime_addr),
                )
                if active_move_src_label is not None:
                    lines.append(self.inline_label(active_move_src_label))
                lines.extend(self._emit_move_enter(
                    moves_by_src, move, active_move_src_label,
                ))
                active_move = move

            # Map binary → runtime so label lookups work even when
            # this byte belongs to a relocation. Without a move,
            # b2r is the identity.
            runtime_addr = int(ir.moves.b2r(BinaryAddr(int(binary_addr))))

            # Emit BEFORE_LABEL annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.BEFORE_LABEL):
                lines.extend(self._render_annotation(ann))

            # Emit any inline labels at this address (sorted for
            # deterministic output). Labels are keyed by RUNTIME
            # address — see D-006 / the move-manager design.
            # Local labels are NOT emitted inline — they appear only
            # in the explicit-definition table at the top, since
            # beebasm has no native scoped-label syntax.
            label = ir.labels.get_label(runtime_addr)
            if label is not None:
                # Emit the cross-reference summary above the label
                # name(s) when this label is referenced from anywhere.
                xref = self._format_inline_xref_summary(runtime_addr)
                if xref is not None:
                    lines.append(xref)
                for name in sorted(label.explicit_name_texts()):
                    lines.append(self.inline_label(name))

            # Emit AFTER_LABEL annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.AFTER_LABEL):
                lines.extend(self._render_annotation(ann))

            # Emit BEFORE_LINE annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.BEFORE_LINE):
                lines.extend(self._render_annotation(ann))

            # Emit the classification's text line(s).
            content_lines = self._render_classification(ir, binary_addr, classification)

            # Optional byte-column annotation on the first content
            # line: ``; <addr>: <hex bytes>  <ascii>``. Provides the
            # py8dis-style address+raw-bytes column for review/parity.
            inline_anns = ir.annotations.get_for_align(int(binary_addr), Align.INLINE)
            user_inline_text = None
            if inline_anns:
                user_inline_text = "  ".join(
                    self._render_annotation_inline(a) for a in inline_anns
                )
            if self.byte_column and content_lines:
                runtime_addr_for_bc = int(
                    ir.moves.b2r(BinaryAddr(int(binary_addr)))
                )
                byte_col_text = self._format_byte_column(
                    ir, int(binary_addr), runtime_addr_for_bc,
                    classification.length(),
                )
                first = content_lines[0]
                if len(first) < INSTRUCTION_PAD_WITH_BYTE_COLUMN:
                    first = first.ljust(INSTRUCTION_PAD_WITH_BYTE_COLUMN)
                else:
                    first = first + "  "
                first = f"{first}{byte_col_text}"
                # If the inline user comment is on the same (first==
                # last) line, append it after the byte column so we
                # don't double-attach it below.
                if user_inline_text and len(content_lines) == 1:
                    first = first.ljust(
                        INSTRUCTION_PAD_WITH_BYTE_COLUMN + BYTE_COLUMN_TOTAL_WIDTH,
                    ) + f"  {user_inline_text}"
                    user_inline_text = None
                content_lines[0] = first

            # Append any INLINE user comment to the last content line
            # (preserves multi-line equb behavior). When byte_column
            # placed it on a single-line content already, user_inline_text
            # is cleared above.
            if user_inline_text and content_lines:
                last = content_lines[-1]
                if len(last) < INLINE_COMMENT_COLUMN:
                    last = last.ljust(INLINE_COMMENT_COLUMN)
                else:
                    last = last + "  "
                content_lines[-1] = f"{last}{user_inline_text}"

            lines.extend(content_lines)

            # Emit AFTER_LINE annotations at this address.
            for ann in ir.annotations.get_for_align(int(binary_addr), Align.AFTER_LINE):
                lines.extend(self._render_annotation(ann))

        # If iteration ended while still inside a relocated region,
        # emit its close-out directives now.
        if active_move is not None:
            lines.extend(self._emit_move_exit(
                active_move, active_move_src_label, active_move_dest_label,
            ))
            active_move = None

        # Optional end marker, save directive, any trailing close-out.
        if self.boundary_end_label is not None:
            lines.append(self.inline_label(self.boundary_end_label))
        lines.append("")
        lines.append(self._save_directive(load_start, load_end))
        lines.extend(self.disassembly_end())

        # End-of-file label-reference frequency table.
        freq_lines = self._build_label_frequency_table(ir)
        if freq_lines:
            lines.append("")
            lines.extend(freq_lines)

        # End-of-file stats block.
        stats_lines = self._build_stats_block(ir)
        if stats_lines:
            lines.append("")
            lines.extend(stats_lines)

        # Build the explicit-label table for out-of-range labels —
        # required ones always emit; optional ones only if used.
        # The table goes before the ORG, so prepend it now that the
        # body has been rendered (and uses tracked). A
        # ``; Memory locations`` header sits above non-empty tables to
        # make the rendered output read as a memory map.
        table_lines = self._build_explicit_label_table(ir)
        if table_lines:
            header = [f"{self.comment_prefix()} Memory locations"]
            lines = header + table_lines + [""] + lines

        return TextOutput("\n".join(lines) + "\n")

    def _build_explicit_label_table(self, ir) -> list[str]:
        """Return ``name = &xxxx`` definition lines for out-of-range
        labels:

        - All required out-of-range labels (every name).
        - Optional out-of-range labels whose runtime address was
          looked up by name during operand resolution (recorded in
          :attr:`_used_external_labels`).

        Names are aligned at the equals sign for readability.
        Sorted by address then by name for deterministic output.
        Each entry carries an optional description (from the
        ``description=`` kwarg of :meth:`Disassembler.label`); when
        present it is emitted as a trailing ``;`` comment, with
        embedded newlines collapsed to single spaces.
        """
        entries: list[tuple[str, int, str | None]] = []
        for runtime_addr_obj, label in ir.labels.items():
            runtime_addr = int(runtime_addr_obj)
            in_range = self._label_address_is_in_range(ir, runtime_addr)
            description = label.description

            # Local labels go in the table regardless of whether
            # their address is in range — beebasm has no native
            # local-label syntax, so we express the scoped name as
            # an explicit definition.
            local_names = sorted({
                ll.name
                for ll_list in label.local_labels.values()
                for ll in ll_list
            })
            for name in local_names:
                entries.append((name, runtime_addr, description))

            # Explicit names: an in-range label whose address is the
            # *start* of a classification is emitted inline as ``.name``
            # by the body walk — skip the table. But a label whose
            # address falls inside a multi-byte classification (e.g.
            # the operand byte of a branch instruction, used as a base
            # for indexed addressing) has no inline anchor — it goes
            # in the table as ``name = &xxxx``. Out-of-range labels
            # obey the required/optional rule as before.
            inline_anchor = (
                in_range
                and self._label_address_is_classification_start(ir, runtime_addr)
            )
            if inline_anchor:
                continue
            explicit_names = sorted({
                name.text
                for name_list in label.explicit_names.values()
                for name in name_list
            })
            if not explicit_names:
                continue
            if (
                not in_range
                and not label.required
                and runtime_addr not in self._used_external_labels
            ):
                continue
            for name in explicit_names:
                entries.append((name, runtime_addr, description))

        if not entries:
            return []

        max_name_len = max(len(name) for name, _, _ in entries)
        # Sort: address ascending, then name for stable ordering.
        entries.sort(key=lambda e: (e[1], e[0]))
        lines: list[str] = []
        for name, addr, description in entries:
            line = f"{name.ljust(max_name_len)} = {self.hex(addr)}"
            if description:
                line = f"{line}  {self.comment_prefix()} " + " ".join(
                    description.split()
                )
            lines.append(line)
        return lines

    # -- cross-reference tracking + emission -----------------------------

    def _compute_references(self, ir) -> None:
        """Pre-pass: walk every classified opcode, resolve its operand
        to a runtime target address, and record the use site against
        any label found at that address.

        Stored in :attr:`_label_references` keyed by runtime address.
        Also populates :attr:`_used_external_labels` for out-of-range
        labels — same set the body walk would populate via ``_addr_text``.
        Re-running render on the same renderer instance starts from a
        fresh map (``_reset_render_state`` clears it).
        """
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            if not isinstance(classification, Opcode):
                continue
            target = self._operand_label_target(ir, int(binary_addr), classification)
            if target is None:
                continue
            label = ir.labels.get_label(target)
            if label is None or not label.explicit_name_texts():
                continue
            self._label_references.setdefault(target, []).append(int(binary_addr))
            if not self._label_address_is_in_range(ir, target):
                self._used_external_labels.add(target)

    def _operand_label_target(
        self, ir, binary_addr: int, opcode: Opcode,
    ) -> int | None:
        """Return the runtime address an opcode's operand resolves to
        for label-lookup purposes, or ``None`` if the operand is not
        an address (immediate / no-operand) or is overridden by a
        user expression at the operand position.
        """
        # User expression override at the operand byte → no label
        # lookup happens at render time, so don't record a reference.
        operand_addr = binary_addr + 1
        if ir.expressions.get_or_none(operand_addr) is not None:
            return None
        kind = opcode.addressing_mode.operand_kind
        if kind in (OperandKind.NONE, OperandKind.IMMEDIATE):
            return None
        if kind is OperandKind.ADDRESS_8:
            return ir.memory.get_u8(operand_addr)
        if kind in (OperandKind.ADDRESS_16, OperandKind.ADDRESS_16_INDIRECT):
            return ir.memory.get_u16_le(operand_addr)
        if kind is OperandKind.RELATIVE_OFFSET:
            offset = ir.memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            return binary_addr + opcode.length() + offset
        return None

    def _format_inline_xref_summary(self, runtime_addr: int) -> str | None:
        """Format the ``; &<addr> referenced N time(s) by &<r1>, …``
        line for a label, or return ``None`` when the label has no
        recorded references.
        """
        refs = self._label_references.get(runtime_addr)
        if not refs:
            return None
        unique_refs = sorted(set(refs))
        count = len(unique_refs)
        word = "time" if count == 1 else "times"
        ref_list = ", ".join(self.hex(r) for r in unique_refs)
        return (
            f"{self.comment_prefix()} {self.hex(runtime_addr)} "
            f"referenced {count} {word} by {ref_list}"
        )

    # -- move-aware emission --------------------------------------------

    @staticmethod
    def _moves_by_src_addr(ir) -> dict[int, "MoveDefinition"]:
        """Sorted ``{src_binary_addr: MoveDefinition}`` for every
        registered (non-base) relocation. The base move (id 0) is
        skipped since it's the identity 1:1 mapping over the whole
        address space.
        """
        out: dict[int, "MoveDefinition"] = {}
        for move_id, defn in enumerate(ir.moves._move_definitions):
            if move_id == 0:
                continue  # base move = identity, no relocation directives
            out[int(defn.src_binary_addr)] = defn
        return out

    @staticmethod
    def _first_explicit_name(ir, runtime_addr: int) -> str | None:
        """First (alphabetically) explicit name on the label at this
        runtime address, or ``None``. Used as the symbolic anchor for
        relocation directives — beebasm's ``copyblock`` / ``clear`` /
        ``org`` need named anchors to reference.
        """
        label = ir.labels.get_label(runtime_addr)
        if label is None:
            return None
        names = sorted(label.explicit_name_texts())
        return names[0] if names else None

    def _emit_move_enter(
        self,
        moves_by_src: dict[int, "MoveDefinition"],
        move: "MoveDefinition",
        src_label: str | None,
    ) -> list[str]:
        """Return the lines that switch beebasm's PC from the source
        position into the relocated destination range.

        Mirrors py8dis's pattern (without the ``Move N:`` move-id since
        we don't expose move ids the same way):

            <blank>
            ; Move <id>: &<src> to &<dest> for length <N>
                org &<dest>

        The source label (if any) is emitted by the caller *before*
        this block, so the source position has its symbolic anchor
        before PC switches away.
        """
        # Compute the move id by reverse lookup (cheap — typically very
        # few moves per ROM).
        move_id = next(
            i for i, src in enumerate(sorted(moves_by_src))
            if moves_by_src[src] is move
        ) + 1
        return [
            "",
            (
                f"{self.comment_prefix()} Move {move_id}: "
                f"{self.hex(int(move.src_binary_addr))} to "
                f"{self.hex(int(move.dest_runtime_addr))} for length "
                f"{move.length}"
            ),
            f"    org {self.hex(int(move.dest_runtime_addr))}",
        ]

    def _emit_move_exit(
        self,
        move: "MoveDefinition",
        src_label: str | None,
        dest_label: str | None,
    ) -> list[str]:
        """Return the lines that close out a relocated block:

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
        src_anchor = src_label or self.hex(int(move.src_binary_addr))
        dest_anchor = dest_label or self.hex(int(move.dest_runtime_addr))
        dest_end = int(move.dest_runtime_addr) + move.length
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

    # -- end-of-file stats block ----------------------------------------

    def _build_stats_block(self, ir) -> list[str]:
        """Build the trailing ``; Stats:`` block — one-glance summary
        of the disassembly's composition. Mirrors the py8dis layout so
        consumers comparing outputs see familiar shape; the numbers
        come from walking the classification store.
        """
        code_bytes = 0
        data_bytes = 0
        instruction_count = 0
        byte_count = 0
        word_count = 0
        string_byte_count = 0
        string_count = 0
        for _addr, c in ir.classifications.iter_classified_starts():
            length = c.length()
            if isinstance(c, Opcode):
                code_bytes += length
                instruction_count += 1
            else:
                data_bytes += length
                if isinstance(c, Byte):
                    byte_count += length
                elif isinstance(c, Word):
                    word_count += length
                elif isinstance(c, String):
                    string_byte_count += length
                    string_count += 1
                elif isinstance(c, Fill):
                    byte_count += length
        total = code_bytes + data_bytes
        if total == 0:
            return []
        code_pct = 100.0 * code_bytes / total
        data_pct = 100.0 * data_bytes / total
        cp = self.comment_prefix()
        return [
            f"{cp} Stats:",
            f"{cp}     Total size (Code + Data) = {total} bytes",
            f"{cp}     Code                     = {code_bytes} bytes ({code_pct:.0f}%)",
            f"{cp}     Data                     = {data_bytes} bytes ({data_pct:.0f}%)",
            f"{cp}",
            f"{cp}     Number of instructions   = {instruction_count}",
            f"{cp}     Number of data bytes     = {byte_count} bytes",
            f"{cp}     Number of data words     = {word_count} bytes",
            f"{cp}     Number of string bytes   = {string_byte_count} bytes",
            f"{cp}     Number of strings        = {string_count}",
        ]

    # -- byte-column inline annotation ----------------------------------

    def _format_byte_column(
        self, ir, binary_addr: int, runtime_addr: int, length: int,
    ) -> str:
        """Format the inline ``; <addr>: <hex bytes>  <ascii>``
        annotation py8dis attaches to every line. Includes up to
        :data:`BYTE_COLUMN_MAX_BYTES` bytes; truncated runs are marked
        with ``...``.

        ``binary_addr`` is where to read the bytes from;
        ``runtime_addr`` is what to print as the address (so move-
        relocated code shows its execution address, matching the
        operand label resolution).
        """
        max_bytes = 3
        actual_bytes_to_show = min(length, max_bytes)
        bytes_values = [
            ir.memory.get_u8(binary_addr + i)
            for i in range(actual_bytes_to_show)
            if ir.memory.is_loaded(binary_addr + i)
        ]
        hex_text = " ".join(self.hex2(v).removeprefix("&") for v in bytes_values)
        if length > max_bytes:
            hex_text = f"{hex_text}..."
        # Pad bytes column to max width: 3 bytes ("XX YY ZZ") + ellipsis
        # ("...") = 11 chars maximum.
        hex_field = hex_text.ljust(11)
        ascii_chars = "".join(
            chr(v) if 0x20 <= v < 0x7f else "." for v in bytes_values
        )
        if length > max_bytes:
            ascii_chars = f"{ascii_chars}..."
        ascii_field = ascii_chars.ljust(6)
        return (
            f"{self.comment_prefix()} {self.hex(runtime_addr)}: "
            f"{hex_field} {ascii_field}"
        )

    def _build_label_frequency_table(self, ir) -> list[str]:
        """Build the ``; Label references by decreasing frequency:``
        block emitted at the end of the output.

        One line per label that has at least one reference, sorted by
        reference count descending then name ascending. Each label
        contributes one row per explicit name (so aliases all show).
        When boundary labels are emitted and the load-start address
        has any references, an alias row for the boundary-start name
        also appears (so a memory-map-style summary shows both the
        user's name and the synthetic boundary name at that address).
        Counts are right-aligned at a column slightly wider than the
        longest name for readability.
        """
        rows: list[tuple[str, int]] = []
        for runtime_addr, refs in self._label_references.items():
            label = ir.labels.get_label(runtime_addr)
            if label is None:
                continue
            count = len(set(refs))
            for name in sorted(label.explicit_name_texts()):
                rows.append((name, count))
        # Boundary-label aliases at the start/end of the loaded range.
        if self.emit_boundary_labels:
            try:
                load_start, load_end = ir.memory.entire_load_range()
            except Exception:
                load_start = load_end = None
            if load_start is not None:
                start_refs = self._label_references.get(int(load_start), [])
                if start_refs:
                    rows.append(
                        (self.boundary_start_label, len(set(start_refs))),
                    )
            if load_end is not None:
                end_refs = self._label_references.get(int(load_end), [])
                if end_refs:
                    rows.append(
                        (self.boundary_end_label, len(set(end_refs))),
                    )
        if not rows:
            return []
        rows.sort(key=lambda r: (-r[1], r[0]))
        max_name_len = max(len(name) for name, _ in rows)
        max_count_width = max(len(str(c)) for _, c in rows)
        lines = [f"{self.comment_prefix()} Label references by decreasing frequency:"]
        for name, count in rows:
            label_part = f"{name}:".ljust(max_name_len + 2)
            count_part = str(count).rjust(max_count_width)
            lines.append(f"{self.comment_prefix()}     {label_part} {count_part}")
        return lines

    # -- annotations ------------------------------------------------------

    def _render_annotation(self, ann) -> list[str]:
        """Render a Comment / Annotation / Banner as standalone line(s).

        Always returns a list so multi-line entries (Banner) and
        single-line entries (Comment, Annotation) share the same
        caller pattern.
        """
        if isinstance(ann, Banner):
            return self._render_banner_lines(ann)
        if isinstance(ann, Comment):
            indent = " " * (ann.indent * 4) if ann.indent else ""
            return [f"{indent}{self.comment_prefix()} {ann.text}"]
        if isinstance(ann, Annotation):
            return [ann.text]
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    def _render_annotation_inline(self, ann) -> str:
        """Render a Comment or Annotation as the inline (trailing) form.

        Banner inline form is not supported (banners are inherently
        multi-line); attach them at one of the standalone alignments.
        """
        if isinstance(ann, Comment):
            return f"{self.comment_prefix()} {ann.text}"
        if isinstance(ann, Annotation):
            return ann.text
        if isinstance(ann, Banner):
            raise ValueError(
                "Banner cannot be rendered inline; use a standalone "
                "Align position (BEFORE_LABEL, AFTER_LABEL, etc.)"
            )
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    def _render_banner_lines(self, banner: Banner) -> list[str]:
        """Render a Banner as a multi-line decorated comment block.

        The format follows py8dis: a separator line of
        :data:`BANNER_SEPARATOR_WIDTH` asterisks, the title, a blank
        comment line, then the description. Description text is
        emitted with explicit line breaks preserved (no word-wrap in
        this first cut — that lands with the markdown_asm port).
        """
        prefix = self.comment_prefix()
        sep = f"{prefix} " + ("*" * BANNER_SEPARATOR_WIDTH)
        out: list[str] = [sep]
        if banner.title:
            out.append(f"{prefix} {banner.title}")
        if banner.description:
            if banner.title:
                out.append(prefix)
            for line in banner.description.split("\n"):
                if line:
                    out.append(f"{prefix} {line}")
                else:
                    out.append(prefix)
        return out

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
        mode.

        Operand symbol is resolved with this priority:

        1. A user-supplied expression at the operand address
           (registered via ``d.expr(...)``) — used verbatim.
        2. A label name registered at the target address (for
           address-style operands).
        3. The literal hex value of the operand.

        Mode-specific syntax (``#``, ``,X``, parens, …) wraps the
        resolved symbol.
        """
        mode = opcode.addressing_mode
        kind = mode.operand_kind
        operand_addr = int(binary_addr) + 1
        mode_name = mode.name

        # No-operand modes ignore expressions entirely.
        if mode_name == "IMPLIED":
            return ""
        if mode_name == "ACCUMULATOR":
            return "A" if self.explicit_a else ""

        # Resolve the unwrapped symbol (without mode-specific
        # punctuation like # or parens).
        symbol = self._resolve_operand_symbol(
            ir, binary_addr, opcode, operand_addr,
        )

        # Wrap with mode-specific syntax.
        if mode_name == "IMMEDIATE":
            return f"#{symbol}"
        if mode_name in ("ZERO_PAGE", "ABSOLUTE", "RELATIVE"):
            return symbol
        if mode_name in ("ZERO_PAGE_X", "ABSOLUTE_X"):
            return f"{symbol},X"
        if mode_name in ("ZERO_PAGE_Y", "ABSOLUTE_Y"):
            return f"{symbol},Y"
        if mode_name == "INDIRECT":
            return f"({symbol})"
        if mode_name == "INDEXED_INDIRECT":  # (zp,X)
            return f"({symbol},X)"
        if mode_name == "INDIRECT_INDEXED":  # (zp),Y
            return f"({symbol}),Y"
        # 65C02 additions:
        if mode_name == "ZP_INDIRECT":  # (zp)
            return f"({symbol})"
        if mode_name == "ABSOLUTE_INDIRECT_X":  # JMP (addr,X)
            return f"({symbol},X)"

        raise ValueError(
            f"BeebasmRenderer does not know how to render addressing mode "
            f"{mode_name!r}"
        )

    def _resolve_operand_symbol(
        self, ir, binary_addr, opcode, operand_addr,
    ) -> str:
        """Resolve the unwrapped operand symbol — expression / label /
        hex literal — without applying mode-specific punctuation.

        ``binary_addr`` is the address of the opcode byte; passed
        through to label lookup for local-label scope checking.
        """
        # 1. User-supplied expression takes precedence over everything.
        expr = ir.expressions.get_or_none(operand_addr)
        if expr is not None:
            return expr

        kind = opcode.addressing_mode.operand_kind
        using_addr = int(binary_addr)

        if kind is OperandKind.IMMEDIATE:
            # Immediate values aren't addresses; no label lookup.
            return self.hex2(ir.memory.get_u8(operand_addr))

        if kind is OperandKind.ADDRESS_8:
            v = ir.memory.get_u8(operand_addr)
            return self._addr_text(ir, v, width=8, using_binary_addr=using_addr)

        if kind in (OperandKind.ADDRESS_16, OperandKind.ADDRESS_16_INDIRECT):
            v = ir.memory.get_u16_le(operand_addr)
            return self._addr_text(ir, v, width=16, using_binary_addr=using_addr)

        if kind is OperandKind.RELATIVE_OFFSET:
            offset = ir.memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            target = int(binary_addr) + opcode.length() + offset
            return self._addr_text(
                ir, target, width=16, using_binary_addr=using_addr,
            )

        # Defensive — the mode-name dispatch in _render_operand
        # should have caught NONE before we got here.
        raise ValueError(f"unresolvable operand kind: {kind}")

    def _addr_text(
        self,
        ir,
        addr: int,
        *,
        width: int,
        using_binary_addr: int | None = None,
    ) -> str:
        """Render an address operand: a label name if one is
        registered, otherwise the appropriate hex literal.

        ``using_binary_addr`` is the binary address of the
        instruction that's referencing ``addr`` (typically the opcode
        byte). It's used for **local-label scope checking**: if a
        local label exists at ``addr`` and ``using_binary_addr`` is
        within its scope, the local label name wins over any explicit
        name at ``addr``.

        When the label resolves to an out-of-range address (no loaded
        byte for it, even via a move), the runtime address is recorded
        so the explicit-label table at the top of the output can
        include it.
        """
        label = ir.labels.get_label(addr)
        if label is not None:
            # Prefer a local label whose scope contains the using
            # site. Local labels are scoped — they only contribute a
            # name when the using site is in their range.
            if using_binary_addr is not None:
                local_name = self._local_label_in_scope(label, using_binary_addr)
                if local_name is not None:
                    return local_name
            # Fall back to the first explicit name. We deliberately
            # exclude local labels here — those are out of scope and
            # have no business naming this operand.
            names = sorted(label.explicit_name_texts())
            if names:
                if not self._label_address_is_in_range(ir, addr):
                    self._used_external_labels.add(addr)
                return names[0]
        return self.hex2(addr) if width == 8 else self.hex4(addr)

    @staticmethod
    def _local_label_in_scope(label, using_binary_addr: int) -> str | None:
        """If any local label on ``label`` has a scope containing
        ``using_binary_addr``, return its name. Otherwise ``None``.
        """
        for ll_list in label.local_labels.values():
            for ll in ll_list:
                if ll.start_addr <= using_binary_addr < ll.end_addr:
                    return ll.name
        return None

    def _label_address_is_classification_start(
        self, ir, runtime_addr: int,
    ) -> bool:
        """True iff the runtime address has an inline anchor in the
        body walk — i.e. it maps to the start of a classification, AND
        the body walk's binary→runtime round-trip lands back on this
        runtime address.

        The second check matters under moves: a label at runtime
        ``&F859`` (the binary source of a move) maps to binary
        ``&F859``, but ``b2r(&F859)`` is the *move destination*
        ``&0100``, not ``&F859`` — so the body walk would emit any
        label found at runtime ``&0100`` there, missing the source-
        address label entirely. Returning False here pushes the label
        into the equate table where it gets a concrete ``= &xxxx``
        anchor.
        """
        from dasmos.core.disassembly import INSIDE_A_CLASSIFICATION
        from dasmos.core.memory import RuntimeAddr
        binary_addr, _ = ir.moves.r2b(RuntimeAddr(runtime_addr))
        if binary_addr is None:
            return False
        # A label at a move-source binary address gets its inline
        # anchor from the move-enter emission (the body walk emits
        # ``.<src_label>`` just before the ``org &<dest>`` switch).
        # Treat that as an inline anchor here so we don't double-
        # define the symbol via the equate table.
        if int(binary_addr) == runtime_addr and int(binary_addr) in self._moves_by_src_addr(ir):
            return True
        if int(ir.moves.b2r(binary_addr)) != runtime_addr:
            return False
        c = ir.classifications.get_classification(int(binary_addr))
        # ``None`` = no classification at this byte (in-range but
        # unclassified — rare; treat like "needs equate"). The
        # ``INSIDE_A_CLASSIFICATION`` sentinel marks an interior byte
        # — also no inline anchor. Only a Classification object means
        # this is the start of one.
        return c is not None and c is not INSIDE_A_CLASSIFICATION

    def _label_address_is_in_range(self, ir, runtime_addr: int) -> bool:
        """True iff the runtime address has a corresponding loaded
        byte — directly or via a move.

        Out-of-range labels (zero-page workspace, OS-call vectors,
        hardware registers) get emitted as ``name = &xxxx`` definitions
        at the top of the output rather than inline at a classification.
        """
        from dasmos.core.memory import RuntimeAddr
        binary_addr, _ = ir.moves.r2b(RuntimeAddr(runtime_addr))
        if binary_addr is None:
            return False
        return ir.memory.is_loaded(int(binary_addr))

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
