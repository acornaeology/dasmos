"""Shared assembler-source rendering walk.

:class:`AssemblerRenderer` is the concrete base for every text-syntax
(assembler-source) renderer. It owns the whole rendering walk — the IR
traversal, relocation/move emission, per-classification rendering,
operand resolution, label / cross-reference / stats / annotation
emission — expressed entirely in terms of the abstract lexical protocol
declared on :class:`~dasmos.renderer.TextRenderer` (``hex2`` / ``hex4`` /
``comment_prefix`` / ``byte_prefix`` / ``inline_label`` / the
``pseudopc_*`` relocation hooks / …).

Concrete backends — :class:`~dasmos.ext.renderers.beebasm.BeebasmRenderer`
and the 64tass renderer — subclass this and supply only that lexical
protocol plus their assembler-specific directives (save, cpu-select,
fill, relocation idiom, FormatHint translation). The shared walk here is
what keeps a second backend small: it is written once and driven by the
subclass's syntax methods.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from dasmos.core.annotations import (
    Align,
    Annotation,
    Banner,
    Comment,
    DecodedAnnotation,
)
from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.expr import (
    BinOp,
    Binary,
    Expr,
    Group,
    Int,
    MacroCall,
    Param,
    Radix,
    Raw,
    Ref,
    Str,
    StrIndex,
    StrLen,
    StrSlice,
    Sym,
    Unary,
    UnaryOp,
    fold,
)
from dasmos.core.format_hint import FormatHint
from dasmos.core.markdown_asm import markdown_to_asm_text, strip_address_uri_links
from dasmos.core.memory import BinaryAddr
from dasmos.core.move import Move
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import TextOutput
from dasmos.renderer import TextRenderer

# Trailing column for inline comments. A future config knob.
INLINE_COMMENT_COLUMN = 40

# When ``byte_column`` is enabled, instructions are padded further so
# the byte annotation has room before any user comment.
INSTRUCTION_PAD_WITH_BYTE_COLUMN = 70

# Total width occupied by a byte-column annotation
# (``<addr>: <hex>  <ascii>``) — used when both byte column and user
# comment are present on the same line.
BYTE_COLUMN_TOTAL_WIDTH = 27

# Banner separator width: a row of this many ``*`` characters, prefixed
# by the comment prefix and a space, between the title and the
# surrounding text.
BANNER_SEPARATOR_WIDTH = 87

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


class AssemblerRenderer(TextRenderer):
    """Concrete base holding the shared assembler-source rendering walk.

    Subclasses supply the lexical protocol (``hex2`` / ``byte_prefix`` /
    ``inline_label`` / …), the relocation hooks (``pseudopc_start`` /
    ``pseudopc_end``), and any assembler-specific directives; this class
    supplies everything else — the IR walk, move emission, operand
    resolution, and the label / xref / stats / annotation blocks.
    """

    #: Recognised byte-column flavours (see ``byte_column_format``).
    BYTE_COLUMN_FORMATS = ("dasmos", "py8dis")

    def __init__(
        self,
        name: str,
        *,
        boundary_label_prefix: str = "",
        byte_column: bool = False,
        byte_column_format: str = "dasmos",
        default_byte_cols: int = 8,
        default_word_cols: int = 4,
        show_auto_label_footer: bool = True,
        comment_wrap_column: int = 87,
        lower_case: bool = True,
        fold_string_ops: bool = False,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        # ``""`` means "suppress the start/end marker labels"; any other
        # value is the prefix for the ``{prefix}start`` / ``{prefix}end``
        # inline labels that bracket the loaded range.
        self.boundary_label_prefix = boundary_label_prefix
        # When True, attach a ``; <addr>: <hex bytes>  <ascii>``
        # annotation to the first content line of every classification.
        self.byte_column = byte_column
        if byte_column_format not in self.BYTE_COLUMN_FORMATS:
            raise ValueError(
                f"byte_column_format must be one of "
                f"{self.BYTE_COLUMN_FORMATS!r}, got {byte_column_format!r}"
            )
        self.byte_column_format = byte_column_format
        # Default chunking widths for ``Byte`` / ``Word`` blocks whose
        # own ``cols()`` is None.
        self.default_byte_cols = default_byte_cols
        self.default_word_cols = default_word_cols
        # When True, emit the trailing ``; Automatically generated
        # labels:`` footer block.
        self.show_auto_label_footer = show_auto_label_footer
        # Column at which Markdown-rendered narrative text reflows.
        self.comment_wrap_column = comment_wrap_column
        # When True, mnemonics and register-suffix letters render in
        # lowercase.
        self.lower_case = lower_case
        # Readability vs terseness for string operations. Default False:
        # keep the string visible by rendering the op in this assembler's
        # native syntax (``"BRK"[0]`` / ``ASC(MID$("BRK",1,1))``), which
        # is the whole point of a readable disassembly. Set True to
        # constant-fold string ops to their value (``'B'``) for terse
        # output. Either way, a string op the backend cannot express
        # natively is folded as a fallback (and must be constant to do
        # so). Drivers wanting per-expression control can fold selected
        # expressions themselves before registering them.
        self.fold_string_ops = fold_string_ops

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

    # -- output/CPU directives (overridable defaults) ---------------------

    def cpu_directive_for(self, cpu_name: str) -> str | None:
        """A directive selecting the target CPU, or ``None`` when the
        assembler needs none. Default: none. Backends whose assembler
        has a CPU selector override this (beebasm ``cpu N``; 64tass
        ``.cpu``).
        """
        return None

    def _save_directive(self, load_start, load_end) -> str | None:
        """A directive writing the loaded range to a binary file, or
        ``None`` when the assembler saves via a command-line flag
        instead. Default: ``None`` (no in-source save). Beebasm
        overrides with its ``save`` directive; 64tass leaves it to the
        ``-o`` flag.
        """
        return None

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
        # Runtime addresses whose label got emitted inline during the
        # body walk (in any move's emission, or in the main walk).
        # Consulted by :meth:`_build_explicit_label_table` to suppress
        # equates that would duplicate an inline definition — needed
        # because the heuristic ``_label_address_is_classification_start``
        # uses ``b2r`` (most-recent move) and so misses inline anchors
        # from a non-most-recent move's body emission.
        self._inline_emitted_runtime_addrs: set[int] = set()

    def render(self, ir: "IntermediateRepresentation") -> TextOutput:
        """Walk the IR's classifications and emit a beebasm source
        listing.

        Emission order (``org &<move-src>`` appears in the file BEFORE
        ``org &<load-start>``):

        1. Explicit-label table for out-of-range labels (prepended at
           the end so it can include externals discovered during the
           body walk).
        2. **Move regions FIRST**, in source-binary-address order.
           Each move emits ``org <src>`` to position PC, the source
           label inline, the move-enter directive (``org <dest>``),
           the bytes of the move's source range under that move's
           runtime mapping, and the move-exit directives
           (``copyblock`` / ``clear`` / restore).
        3. ``ORG`` at the start of the loaded range and the boundary
           start marker.
        4. The main code: the classifications in binary order,
           SKIPPING any byte covered by a move's source range (already
           emitted in step 2).
        5. Boundary end marker, ``save`` directive, end-of-file
           footer blocks.

        Why moves first: a zero-page label that lives in a moved
        region's destination has its inline ``.<name>`` anchor inside
        the move's body. If the move's body comes AFTER main code in
        the file, the first reference to that label from main code is
        a forward reference; beebasm assumes absolute (3 bytes) on
        pass 1, realises zero-page (2 bytes) on pass 2, the code
        shifts, and the assembler errors with "Assembled object code
        has changed between 1st and 2nd pass". Emitting moves first
        makes every such inline anchor naturally precede its uses.

        Overlapping moves (e.g. NFS-3.65's ``move(0x16, 0x9324, 0x61)``
        and ``move(0x400, 0x9365, 0x100)``) emit each source byte
        TWICE — once under each containing move's runtime mapping.
        beebasm's ``copyblock`` for the second move overwrites the
        first move's bytes in the overlap region; both renderings
        produce identical opcode bytes for the same source bytes, so
        byte-equality holds.
        """
        self._reset_render_state()

        lines: list[str] = []
        lines.extend(self.disassembly_start())

        cpu_directive = self.cpu_directive_for(ir.cpu.name)
        if cpu_directive is not None:
            lines.append(cpu_directive)

        try:
            load_start, load_end = ir.memory.entire_load_range()
        except Exception:
            lines.extend(self.disassembly_end())
            return TextOutput("\n".join(lines) + "\n")

        moves_by_src = self._moves_by_src_addr(ir)
        # Map ``Move`` → 1-based id (for the byte-column
        # ``[<move_id>]`` suffix in the ``"py8dis"`` byte-column
        # format). Built once per render so each move-enter doesn't
        # recompute it.
        move_ids: dict[int, int] = {
            id(move): i + 1
            for i, src in enumerate(sorted(moves_by_src))
            for move in [moves_by_src[src]]
        }

        # PHASE 1: emit move regions first, in source-binary-address
        # order. Each move's emission is self-contained: org-to-src,
        # source label, move-enter, body, move-exit.
        for src_addr in sorted(moves_by_src):
            move = moves_by_src[src_addr]
            lines.extend(
                self._emit_move_section(ir, move, moves_by_src, move_ids)
            )

        # PHASE 2: main code. ``org`` to the load start (resetting
        # PC after the moves' restore-to-source positions left it
        # somewhere arbitrary) plus the boundary start marker.
        lines.extend(self.code_start(load_start, load_end, first=True))
        if self.boundary_start_label is not None:
            lines.append(self.inline_label(self.boundary_start_label))

        # Skip ranges: any binary address covered by ANY move's
        # source range was emitted in phase 1.
        move_src_ranges = [
            (src, src + mv.length) for src, mv in moves_by_src.items()
        ]

        # Track PC through the walk so we can emit ``org &<addr>``
        # whenever we resume after a skipped (move-source) range —
        # the main walk needs to resume at the byte just after the
        # last move source.
        expected_pc = int(load_start)
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            ba = int(binary_addr)
            if not (int(load_start) <= ba < int(load_end)):
                continue
            if any(s <= ba < e for s, e in move_src_ranges):
                continue
            if ba != expected_pc:
                lines.extend(self.set_origin(ba))
                expected_pc = ba
            lines.extend(self._emit_classification_at(
                ir, ba, classification,
                active_move=None, active_move_id=None,
            ))
            expected_pc = ba + classification.length()

        # Position PC at load_end before emitting the boundary end
        # marker so the label takes the load_end value (otherwise the
        # marker lands wherever the last classification's last byte
        # ended, which can be earlier when a move source extends to
        # load_end).
        if self.boundary_end_label is not None:
            if expected_pc != int(load_end):
                lines.extend(self.set_origin(int(load_end)))
            lines.append(self.inline_label(self.boundary_end_label))
        save = self._save_directive(load_start, load_end)
        if save is not None:
            lines.append("")
            lines.append(save)
        lines.extend(self.disassembly_end())

        # End-of-file label-reference frequency table.
        freq_lines = self._build_label_frequency_table(ir)
        if freq_lines:
            lines.append("")
            lines.extend(freq_lines)

        # Auto-generated label footer block.
        auto_lines = self._build_auto_label_footer(ir)
        if auto_lines:
            lines.append("")
            lines.extend(auto_lines)

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

        # Constants (registered via Disassembler.constant) are
        # tracked separately from labels — emit them as their own
        # equate block above the memory-map: ``name = value`` lines
        # distinct from label equates.
        constant_lines = self._build_constant_equates(ir)
        if constant_lines:
            header = [f"{self.comment_prefix()} Constants"]
            lines = header + constant_lines + [""] + lines

        # Macro definitions sit at the very top, above their uses.
        macro_lines = self._build_macro_definitions(ir)
        if macro_lines:
            header = [f"{self.comment_prefix()} Macros", ""]
            lines = header + macro_lines + lines

        return TextOutput("\n".join(lines) + "\n")

    def _build_constant_equates(self, ir) -> list[str]:
        """``name = value`` lines for every registered constant
        (deduped by name — multiple registrations of the same
        ``(value, name)`` pair, common when several JSR sites trigger
        the same OSBYTE-hook substitution, collapse to one equate).
        Emitted in registration order.

        A constant that exactly duplicates a label definition (same
        name at the same address, where the label is itself emitted) is
        skipped: the label table already defines ``name = &xxxx`` and
        beebasm rejects a second definition. This happens when a driver
        registers a hardware-register constant whose address an active
        environment also labels — e.g. a ``scsi_data`` constant at
        &FC40 alongside the ``scsi_data`` label from the Acorn
        environment.
        """
        # (name, addr) pairs the label table / inline definitions emit.
        label_defs: set[tuple[str, int]] = set()
        for addr_obj, label in ir.labels.items():
            addr = int(addr_obj)
            names = {
                n.text
                for name_list in label.explicit_names.values()
                for n in name_list
            }
            if not names:
                continue
            will_emit = (
                self._label_address_is_in_range(ir, addr)
                or label.required
                or addr in self._used_external_labels
            )
            if will_emit:
                for nm in names:
                    label_defs.add((nm, addr))

        seen: set[str] = set()
        lines: list[str] = []
        # Compute name column width across all unique names.
        unique = []
        for c in ir.constants:
            if c.name in seen:
                continue
            seen.add(c.name)
            if (c.name, int(c.value)) in label_defs:
                continue  # duplicate of an emitted label definition
            unique.append(c)
        if not unique:
            return []
        max_name_len = max(len(c.name) for c in unique)
        for c in unique:
            line = (
                f"{c.name.ljust(max_name_len)} = {self.hex(int(c.value))}"
            )
            if c.comment:
                line = (
                    f"{line}  {self.comment_prefix()} "
                    f"{markdown_to_asm_text(c.comment, inline=True, hex_format=self.address_link_hex)}"
                )
            lines.append(line)
        return lines

    def _emit_move_section(
        self, ir, move, moves_by_src, move_ids,
    ) -> list[str]:
        """Emit one move's full body: ``org <src>``, source label,
        ``org <dest>``, the move's classifications, ``copyblock`` /
        ``clear`` / restore.

        Each move's body walks the classifications in
        ``[src, src + length)`` with this move forced as the active
        runtime mapping (so ``b2r`` for those bytes routes through
        THIS move's ``dest_runtime_addr``, regardless of whether
        another later-registered move's source range also overlaps
        these binary addresses — overlap handling is by emitting each
        containing move's view of the bytes; beebasm's ``copyblock``
        for the second move overwrites the first in the file).
        """
        lines: list[str] = []
        src_addr = int(move.src_binary_addr)
        dest_addr = int(move.dest_runtime_addr)
        length = move.length
        end = src_addr + length
        move_id = move_ids.get(id(move))
        src_label = self._first_explicit_name(ir, src_addr)
        dest_label = self._first_explicit_name(ir, dest_addr)

        # Position PC at the move's source binary address. Every
        # move emits this so the moves can appear in any order in
        # the file (each one announces where its source bytes live).
        lines.extend(self.set_origin(src_addr))
        if src_label is not None:
            lines.append(self.inline_label(src_label))
            self._inline_emitted_runtime_addrs.add(src_addr)

        # Switch PC into the relocated destination range via the
        # backend's pseudo-PC hook (beebasm ``org``+``copyblock`` idiom;
        # 64tass ``.logical``/``.here``).
        lines.extend(self.pseudopc_start(
            dest=dest_addr, src=src_addr, length=length,
            move_id=move_id, src_label=src_label, dest_label=dest_label,
        ))
        active_move_id = move_id

        # Walk classifications inside the move's source range. The
        # source label was already emitted above (it's at runtime
        # src_addr, no move) — the body walk's lookup at the first
        # byte uses the move's mapping (runtime = dest_addr) so it
        # naturally sees a different label (or none).
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            ba = int(binary_addr)
            if not (src_addr <= ba < end):
                continue
            lines.extend(self._emit_classification_at(
                ir, ba, classification,
                active_move=move, active_move_id=active_move_id,
            ))

        lines.extend(self.pseudopc_end(
            dest=dest_addr, src=src_addr, length=length,
            move_id=move_id, src_label=src_label, dest_label=dest_label,
        ))
        return lines

    def _emit_classification_at(
        self,
        ir,
        binary_addr: int,
        classification,
        *,
        active_move,
        active_move_id: int | None,
    ) -> list[str]:
        """Emit one classification's full output: surrounding
        annotations, inline labels, the rendered text line(s), the
        optional byte-column annotation, and any inline user comment.

        ``active_move`` is the move whose runtime mapping should be
        used for label lookups at this address (None outside any
        move).
        """
        lines: list[str] = []

        # Resolve runtime via the SPECIFIC active move when given —
        # ``ir.moves.b2r`` would pick the most-recently-registered
        # move covering this binary address, which under overlap
        # would route move 1's emission through move 2's mapping.
        if active_move is not None:
            runtime_addr = (
                int(active_move.dest_runtime_addr)
                + (binary_addr - int(active_move.src_binary_addr))
            )
        else:
            runtime_addr = int(ir.moves.b2r(BinaryAddr(binary_addr)))

        for ann in ir.annotations.get_for_align(binary_addr, Align.BEFORE_LABEL):
            lines.extend(self._render_annotation(ann))

        # Inline labels at this runtime address. Skip if a previous
        # body walk has already emitted the inline anchor — this
        # happens for multi-source-same-destination moves: the label
        # at the shared destination is emitted once (during the move
        # whose body walk reaches the address first), and the
        # subsequent moves' body walks hit the same runtime address
        # and would otherwise re-emit ``.<name>`` (which beebasm
        # rejects with "Symbol already defined"). The ``copyblock``
        # / ``clear`` directives in the per-move trailers still
        # resolve the name correctly via the single inline definition.
        label = ir.labels.get_label(runtime_addr)
        if (
            label is not None
            and runtime_addr not in self._inline_emitted_runtime_addrs
        ):
            xref = self._format_inline_xref_summary(label, runtime_addr)
            if xref is not None:
                lines.append(xref)
            # Insertion order, not alphabetical — preserves the label
            # author's intended sequence at addresses with multiple
            # names. The first-registered name is the structural one
            # and should lead.
            names = label.explicit_names_in_insertion_order()
            for name in names:
                lines.append(self.inline_label(name))
            if names:
                self._inline_emitted_runtime_addrs.add(runtime_addr)
            # Mid-instruction labels INSIDE this classification's span
            # get expressed as ``<midname> = <base>+<offset>``. Works
            # inside a moved region too: both the base and the
            # mid-instr label are inline-anchored at runtime
            # ``move.dest + (binary_addr - move.src) + offset`` and
            # beebasm evaluates ``base+offset`` at assembly time
            # against the inline anchor's PC, which IS at the base's
            # runtime. (Example: ``tube_cmd_lo = tube_dispatch_cmd+1``
            # inside move 1 of NFS-3.65.)
            base_names = label.explicit_names_in_insertion_order()
            if base_names:
                base_name = base_names[0]
                for off in range(1, classification.length()):
                    inner_binary = binary_addr + off
                    if active_move is not None:
                        inner_runtime = (
                            int(active_move.dest_runtime_addr)
                            + (inner_binary - int(active_move.src_binary_addr))
                        )
                    else:
                        inner_runtime = inner_binary
                    inner_label = ir.labels.get_label(inner_runtime)
                    if inner_label is None:
                        continue
                    # Mid-instruction labels live inside an opcode's
                    # operand bytes — the addr the human cares about
                    # is the BINARY one (where the byte sits in the
                    # ROM dump). Inside a relocated region, the
                    # runtime address is artificial: it's the dest
                    # of the move, not where you'd find the byte in
                    # the ROM file. Match py8dis-fork's xref-summary
                    # convention (binary addresses both for the
                    # cited label AND its referencing sites) so a
                    # ROM-author reading the listing alongside a hex
                    # dump can correlate without translating.
                    inner_xref = self._format_inline_xref_summary(
                        inner_label, inner_binary,
                    )
                    if inner_xref is not None:
                        lines.append(inner_xref)
                    # Emit any BEFORE_LABEL / BEFORE_LINE annotations
                    # attached at the mid-class binary address right
                    # before the equate line — the equate plays the
                    # role of the inline label, so these annotations
                    # belong above it (matches the structure py8dis
                    # uses when the same address has a real
                    # classification of its own).
                    for ann in ir.annotations.get_for_align(
                        inner_binary, Align.BEFORE_LABEL,
                    ):
                        lines.extend(self._render_annotation(ann))
                    for ann in ir.annotations.get_for_align(
                        inner_binary, Align.BEFORE_LINE,
                    ):
                        lines.extend(self._render_annotation(ann))
                    for inner_name in inner_label.explicit_names_in_insertion_order():
                        lines.append(f"{inner_name} = {base_name}+{off}")
                    self._inline_emitted_runtime_addrs.add(inner_runtime)

        for ann in ir.annotations.get_for_align(binary_addr, Align.AFTER_LABEL):
            lines.extend(self._render_annotation(ann))
        for ann in ir.annotations.get_for_align(binary_addr, Align.BEFORE_LINE):
            lines.extend(self._render_annotation(ann))

        content_lines = self._render_classification(
            ir, binary_addr, classification, active_move=active_move,
        )

        # Gather inline comments from EVERY byte covered by this
        # classification, not just the start address. Driver scripts
        # commonly attach an inline comment to an operand byte (the
        # ``dead`` token in NFS-3.65 &9B4F sits inside a 3-byte JMP
        # at &9B4D); without this, the operand-byte comment is
        # silently dropped.
        # Decoded-value annotations (#27) render BEFORE free-form inline
        # comments — the decoded value answers "what is this region",
        # the comment elaborates. Collecting them into separate lists
        # makes that ordering deterministic regardless of the order the
        # driver registered them in.
        decoded_pieces: list[str] = []
        comment_pieces: list[str] = []
        for off in range(classification.length()):
            for ann in ir.annotations.get_for_align(
                binary_addr + off, Align.INLINE,
            ):
                rendered = self._render_annotation_inline(ann)
                if isinstance(ann, DecodedAnnotation):
                    decoded_pieces.append(rendered)
                else:
                    comment_pieces.append(rendered)
        ordered_pieces: list[str] = []
        for rendered in decoded_pieces + comment_pieces:
            # Strip the ``;`` prefix on all but the first piece so the
            # join reads as one comment, not several.
            if ordered_pieces:
                prefix = self.comment_prefix() + " "
                if rendered.startswith(prefix):
                    rendered = rendered[len(prefix):]
            ordered_pieces.append(rendered)
        user_inline_text = "  ".join(ordered_pieces) if ordered_pieces else None
        if self.byte_column and content_lines:
            line_byte_counts = self._line_byte_counts(classification)
            cumulative = 0
            for idx in range(len(content_lines)):
                line_binary = binary_addr + cumulative
                line_byte_count = (
                    line_byte_counts[idx]
                    if idx < len(line_byte_counts)
                    else classification.length() - cumulative
                )
                if active_move is not None:
                    runtime_for_bc = (
                        int(active_move.dest_runtime_addr)
                        + (line_binary - int(active_move.src_binary_addr))
                    )
                else:
                    runtime_for_bc = int(
                        ir.moves.b2r(BinaryAddr(line_binary))
                    )
                byte_col_text = self._format_byte_column(
                    ir, line_binary, runtime_for_bc, line_byte_count,
                    active_move=active_move,
                    active_move_id=active_move_id,
                )
                text = content_lines[idx]
                if len(text) < INSTRUCTION_PAD_WITH_BYTE_COLUMN:
                    text = text.ljust(INSTRUCTION_PAD_WITH_BYTE_COLUMN)
                else:
                    text = text + "  "
                text = f"{text}{byte_col_text}"
                is_last = idx == len(content_lines) - 1
                if is_last and user_inline_text:
                    text = text.ljust(
                        INSTRUCTION_PAD_WITH_BYTE_COLUMN
                        + BYTE_COLUMN_TOTAL_WIDTH,
                    ) + f"  {user_inline_text}"
                    user_inline_text = None
                content_lines[idx] = text
                cumulative += line_byte_count

        if user_inline_text and content_lines:
            last = content_lines[-1]
            if len(last) < INLINE_COMMENT_COLUMN:
                last = last.ljust(INLINE_COMMENT_COLUMN)
            else:
                last = last + "  "
            content_lines[-1] = f"{last}{user_inline_text}"

        lines.extend(content_lines)

        for ann in ir.annotations.get_for_align(binary_addr, Align.AFTER_LINE):
            lines.extend(self._render_annotation(ann))
        return lines

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
            #
            # Authoritative test: did the body walk actually emit the
            # inline anchor? Tracked in ``_inline_emitted_runtime_addrs``
            # during the walk. The fallback heuristic
            # ``_label_address_is_classification_start`` is kept for
            # the rare case of labels whose address has no body-walk
            # emission yet (e.g. user added them after rendering
            # started — currently impossible but the codepath is
            # defensive).
            if runtime_addr in self._inline_emitted_runtime_addrs:
                continue
            inline_anchor = (
                in_range
                and self._label_address_is_classification_start(ir, runtime_addr)
            )
            if inline_anchor:
                continue
            # Mid-instruction labels with a named base are emitted
            # inline under the base as ``name = base+offset`` — skip
            # the equate table to avoid double-definition.
            if (
                in_range
                and self._label_has_inline_offset_base(ir, runtime_addr)
            ):
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
                line = (
                    f"{line}  {self.comment_prefix()} "
                    f"{markdown_to_asm_text(description, inline=True, hex_format=self.address_link_hex)}"
                )
            lines.append(line)
            # If this address has tracked references, follow the equate
            # with a ``; &xxxx referenced N times by …`` summary. The
            # body walk would normally emit this inline, but
            # mid-instruction labels (which dominate this table) have
            # no inline body-walk anchor.
            label_at_addr = ir.labels.get_label(addr)
            if label_at_addr is not None:
                xref = self._format_inline_xref_summary(label_at_addr, addr)
                if xref is not None:
                    lines.append(xref)
        return lines

    def _format_inline_xref_summary(self, label, runtime_addr: int) -> str | None:
        """Format the ``; &<addr> referenced N time(s) by &<r1>, …``
        line for a label, or return ``None`` when the label has no
        recorded references.

        References that only use this address as an *indexing base*
        (``ReferenceKind`` that doesn't touch the named byte) are
        reported separately as "used as index base", so the summary
        never implies a location is read or written when it is not.
        """
        if not label.references:
            return None
        direct = sorted({
            int(r.binary_addr)
            for r in label.references
            if r.kind.touches_named_address
        })
        indexed = sorted({
            int(r.binary_addr)
            for r in label.references
            if not r.kind.touches_named_address
        })
        # A binary addr classified both ways (different opcodes) counts
        # as a genuine access; keep it out of the index-base list.
        indexed = [ba for ba in indexed if ba not in set(direct)]
        prefix = f"{self.comment_prefix()} {self.hex(runtime_addr)}"
        clauses: list[str] = []
        if direct:
            clauses.append(self._xref_clause("referenced", direct))
        if indexed:
            clauses.append(self._xref_clause("used as index base", indexed))
        return f"{prefix} {'; also '.join(clauses)}"

    def _xref_clause(self, verb: str, refs: list[int]) -> str:
        """``<verb> N time(s) by &r1, &r2, …`` for a set of ref addrs."""
        count = len(refs)
        word = "time" if count == 1 else "times"
        ref_list = ", ".join(self.hex(r) for r in refs)
        return f"{verb} {count} {word} by {ref_list}"

    @staticmethod
    def _moves_by_src_addr(ir) -> dict[int, "Move"]:
        """Sorted ``{src_binary_addr: Move}`` for every
        registered (non-base) relocation. The base move (id 0) is
        skipped since it's the identity 1:1 mapping over the whole
        address space.
        """
        out: dict[int, "Move"] = {}
        for move_id, defn in enumerate(ir.moves.all_moves):
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
        names = label.explicit_names_in_insertion_order()
        return names[0] if names else None

    def _build_stats_block(self, ir) -> list[str]:
        """Build the trailing ``; Stats:`` block — one-glance summary
        of the disassembly's composition. The numbers come from walking
        the classification store.
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

    def _build_auto_label_footer(self, ir) -> list[str]:
        """``; Automatically generated labels:`` block listing every
        label whose explicit name was synthesised by the Disassembler's
        auto-label pass (``is_autogenerated=True``). Empty when none.

        Suppressed entirely when ``show_auto_label_footer`` is False.
        """
        if not self.show_auto_label_footer:
            return []
        names: list[str] = []
        for _runtime_addr, label in ir.labels.items():
            for name_list in label.explicit_names.values():
                for explicit in name_list:
                    if explicit.is_autogenerated:
                        names.append(explicit.text)
        if not names:
            return []
        cp = self.comment_prefix()
        lines = [f"{cp} Automatically generated labels:"]
        for name in sorted(set(names)):
            lines.append(f"{cp}     {name}")
        return lines

    def _line_byte_counts(self, classification) -> list[int]:
        """How many bytes does each rendered content line cover?

        Mirrors how :meth:`_render_byte` / :meth:`_render_word` /
        :meth:`_render_string` chunk the underlying classification
        into rows. Body walk uses this to attach a byte-column
        annotation per row — every ``equb`` row gets its own
        ``; <addr>: <bytes>  <ascii>``.
        """
        if isinstance(classification, Byte):
            cols = classification.cols() or self.default_byte_cols
            n = classification.length()
            full_rows = n // cols
            tail = n - full_rows * cols
            counts = [cols] * full_rows
            if tail:
                counts.append(tail)
            return counts
        if isinstance(classification, Word):
            cols = classification.cols() or self.default_word_cols
            n_bytes = classification.length()
            n_words = n_bytes // 2
            row_bytes = cols * 2
            full_rows = n_words // cols
            tail_words = n_words - full_rows * cols
            counts = [row_bytes] * full_rows
            if tail_words:
                counts.append(tail_words * 2)
            return counts
        # Opcode / String / Fill — one row covering the whole length.
        return [classification.length()]

    def _format_byte_column(
        self,
        ir,
        binary_addr: int,
        runtime_addr: int,
        length: int,
        *,
        active_move=None,
        active_move_id: int | None = None,
    ) -> str:
        """Format the inline ``; <addr>: <hex bytes>  <ascii>``
        annotation. Two flavours, picked by ``byte_column_format``:

        - ``"dasmos"``: ``<comment_prefix> &<runtime_addr>: <bytes>  <ascii>``.
          The ``&`` is beebasm's hex sigil; the address is the b2r-
          resolved runtime so it matches operand-label resolution.
        - ``"py8dis"``: ``<comment_prefix> <binary_addr>: <bytes>  <ascii>``,
          with bare 4-digit hex and the binary file position. Inside
          a relocated region, also append
          ``:<runtime_hex>[<move_id>]`` so a reader can see both the
          file address and the execution address. Use this format for
          byte-for-byte annotation parity with py8dis output.

        Up to 3 bytes are shown; longer runs are truncated with ``...``.
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
        cp = self.comment_prefix()
        if self.byte_column_format == "py8dis":
            text = f"{cp} {binary_addr:04x}: {hex_field} {ascii_field}"
            if active_move is not None and active_move_id is not None:
                # Compute the runtime address WITHIN this move, not
                # via b2r (b2r picks the most-recently-active move
                # for the binary addr; we want the active body-walk
                # context's specific move).
                offset = binary_addr - int(active_move.src_binary_addr)
                runtime_in_move = int(active_move.dest_runtime_addr) + offset
                text = (
                    f"{text.rstrip()} :{runtime_in_move:04x}"
                    f"[{active_move_id}]"
                )
                # Re-pad so the user comment column lines up.
                text = text.ljust(
                    len(cp) + 1 + 6 + 11 + 1 + 6 + 1 + 4 + 1 + 4 + 1 + 1
                )
            return text
        return f"{cp} {self.hex(runtime_addr)}: {hex_field} {ascii_field}"

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
        for _runtime_addr, label in ir.labels.items():
            if not label.references:
                continue
            count = len({int(r.binary_addr) for r in label.references})
            # Use ``all_names_by_move_id`` so expression-style names
            # (registered via ``d.expr_label(addr, "<base>-1")``)
            # appear in the frequency table too, alongside regular
            # explicit names. py8dis-fork includes expressions in
            # this footer; without doing the same, dasmos drops
            # rows like ``dispatch_0_lo-1: 1`` from the bottom-of-
            # listing summary.
            seen: set[str] = set()
            for names in label.all_names_by_move_id().values():
                for name in names:
                    if name in seen:
                        continue
                    seen.add(name)
                    rows.append((name, count))
        # Boundary-label aliases at the start/end of the loaded range.
        if self.emit_boundary_labels:
            try:
                load_start, load_end = ir.memory.entire_load_range()
            except Exception:
                load_start = load_end = None
            for boundary_addr, boundary_name in (
                (load_start, self.boundary_start_label),
                (load_end, self.boundary_end_label),
            ):
                if boundary_addr is None:
                    continue
                label = ir.labels.get_label(int(boundary_addr))
                if label is None or not label.references:
                    continue
                rows.append((
                    boundary_name,
                    len({int(r.binary_addr) for r in label.references}),
                ))
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

    def _render_annotation(self, ann) -> list[str]:
        """Render a Comment / Annotation / Banner as standalone line(s).

        Comment text is treated as Markdown — full CommonMark plus
        GFM tables, plus the custom ``[label](address:HEX[?hex])``
        cross-reference URI scheme — and rendered down to plaintext
        for the asm comment. The structured JSON renderer (see
        ``JsonRenderer``) keeps the source markdown verbatim so
        downstream HTML processors can resolve the anchors. See
        ``acornaeology.github.io/AUTHORING.md`` §1, §2 for the
        markdown conventions.

        Always returns a list so multi-line entries (Banner) and
        single-line entries (Comment, Annotation) share the same
        caller pattern.
        """
        if isinstance(ann, Banner):
            return self._render_banner_lines(ann)
        if isinstance(ann, Comment):
            indent = " " * (ann.indent * 4) if ann.indent else ""
            text = self._comment_text_for_asm(ann, inline=False)
            # Multi-line comment text gets one ``;`` line per source
            # line so beebasm doesn't choke on a bare second/third
            # line. Empty source lines emit just ``;`` (no trailing
            # space) for visual cleanliness.
            return [
                f"{indent}{self.comment_prefix()} {line}" if line
                else f"{indent}{self.comment_prefix()}"
                for line in text.split("\n")
            ]
        if isinstance(ann, Annotation):
            return [ann.text]
        if isinstance(ann, DecodedAnnotation):
            return [f"{self.comment_prefix()} {self._decoded_text(ann)}"]
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    def _render_annotation_inline(self, ann) -> str:
        """Render a Comment or Annotation as the inline (trailing) form.

        Banner inline form is not supported (banners are inherently
        multi-line); attach them at one of the standalone alignments.
        """
        if isinstance(ann, DecodedAnnotation):
            return f"{self.comment_prefix()} {self._decoded_text(ann)}"
        if isinstance(ann, Comment):
            text = self._comment_text_for_asm(ann, inline=True)
            return f"{self.comment_prefix()} {text}"
        if isinstance(ann, Annotation):
            return ann.text
        if isinstance(ann, Banner):
            raise ValueError(
                "Banner cannot be rendered inline; use a standalone "
                "Align position (BEFORE_LABEL, AFTER_LABEL, etc.)"
            )
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    @staticmethod
    def _decoded_text(ann: DecodedAnnotation) -> str:
        """Plain-text body for a decoded-value annotation (#27):
        ``<label> <text>`` plus an optional trailing human note. The
        composition is shared with the JSON renderer via
        :meth:`DecodedAnnotation.display_text` so the two forms stay in
        step (#28).
        """
        return ann.display_text()

    def _comment_text_for_asm(self, ann: Comment, *, inline: bool) -> str:
        """Convert a Comment's source text to asm-suitable plaintext.

        Honours the Comment's ``word_wrap`` flag:

        - ``word_wrap=True`` (default) → full Markdown parse via
          :func:`dasmos.core.markdown_asm.markdown_to_asm_text`. Use
          when the source text is prose / list / table content.
        - ``word_wrap=False`` → regex-only address-link stripper via
          :func:`dasmos.core.markdown_asm.strip_address_uri_links`.
          Use when the source text is shape-sensitive (banner
          separators with rows of asterisks would be munged by full
          markdown parsing).

        Inline comments collapse all whitespace to single spaces so
        they fit on the trailing position after the instruction.
        """
        from dasmos.core.markdown_asm import (
            markdown_to_asm_text,
            strip_address_uri_links,
        )
        if not ann.word_wrap:
            text = strip_address_uri_links(
                ann.text, hex_format=self.address_link_hex,
            )
            if inline:
                # Collapse whitespace for inline rendering even in
                # word_wrap=False mode — the trailing column on the
                # instruction line is the constraint.
                import re as _re
                text = _re.sub(r"\s+", " ", text).strip()
            return text
        return markdown_to_asm_text(
            ann.text, inline=inline, hex_format=self.address_link_hex,
        )

    def _render_banner_lines(self, banner: Banner) -> list[str]:
        """Render a Banner as a multi-line decorated comment block.

        Layout: a separator line of :data:`BANNER_SEPARATOR_WIDTH`
        asterisks, the title, a blank comment line, then the
        description.

        Both ``title`` and ``description`` go through the Markdown-to-
        asm-text converter (``dasmos.core.markdown_asm``), so backticks,
        emphasis, address-link URIs, HTML entities (``&rarr;`` /
        ``&amp;`` / numeric forms), and structured blocks (lists,
        tables) flatten to plaintext for the asm output. The structured
        JSON renderer keeps the source markdown verbatim so downstream
        HTML processors can resolve anchors.

        ``on_entry`` / ``on_exit`` register-usage dicts (when present)
        each render as a ``; On Entry:`` / ``; On Exit:`` sub-block,
        with one ``;     <REG>: <description>`` line per dict entry.
        The dict round-trips through the IR as structured data so a
        future JSON renderer can emit it as a real dict.
        """
        from dasmos.core.markdown_asm import markdown_to_asm_text

        prefix = self.comment_prefix()
        sep = f"{prefix} " + ("*" * BANNER_SEPARATOR_WIDTH)
        out: list[str] = [sep]
        if banner.title:
            # Titles are conceptually a single inline phrase; collapse
            # any incidental wrap-style whitespace and strip Markdown.
            title_text = markdown_to_asm_text(
                banner.title, inline=True, hex_format=self.address_link_hex,
            )
            out.append(f"{prefix} {title_text}")
        if banner.description:
            if banner.title:
                out.append(prefix)
            description_text = markdown_to_asm_text(
                banner.description, wrap_width=self.comment_wrap_column,
                hex_format=self.address_link_hex,
            )
            for line in description_text.split("\n"):
                if line:
                    out.append(f"{prefix} {line}")
                else:
                    out.append(prefix)
        for label_text, mapping in (
            ("On Entry:", banner.on_entry),
            ("On Exit:", banner.on_exit),
        ):
            if not mapping:
                continue
            if out and out[-1] != prefix:
                out.append(prefix)
            out.append(f"{prefix} {label_text}")
            for key, value in mapping.items():
                # Register names render uppercase; the value text is
                # user-supplied prose with the same Markdown conventions
                # as descriptions, so flatten through the same helper.
                value_text = markdown_to_asm_text(
                    value, inline=True, hex_format=self.address_link_hex,
                )
                out.append(f"{prefix}     {key.upper()}: {value_text}")
        return out

    def _render_classification(
        self, ir, binary_addr, c, *, active_move=None,
    ) -> list[str]:
        """Dispatch to the right per-type rendering method.

        ``active_move`` (when given) is the move whose runtime mapping
        should be used for relative-branch arithmetic — needed when
        an instruction's bytes appear under more than one move (the
        same source byte sequence is emitted under each containing
        move's mapping during phase 1, and a relative branch resolves
        to a different runtime in each).
        """
        if isinstance(c, Opcode):
            return [self._render_opcode(
                ir, binary_addr, c, active_move=active_move,
            )]
        if isinstance(c, Byte):
            return self._render_byte(ir, binary_addr, c)
        if isinstance(c, Word):
            return self._render_word(ir, binary_addr, c)
        if isinstance(c, Fill):
            return ["    " + self.fill_directive(c.value(), c.length())[0]]
        if isinstance(c, String):
            return self._render_string(ir, binary_addr, c)
        raise TypeError(
            f"{type(self).__name__} does not know how to render "
            f"{type(c).__name__}"
        )

    def _render_opcode(
        self, ir, binary_addr, opcode: Opcode, *, active_move=None,
    ) -> str:
        """Format a single instruction line."""
        mnemonic = self._apply_case(opcode.default_mnemonic())
        operand = self._render_operand(
            ir, binary_addr, opcode, active_move=active_move,
        )
        char_hint = self._immediate_char_hint(ir, binary_addr, opcode)
        if operand:
            return f"    {mnemonic} {operand}{char_hint}"
        return f"    {mnemonic}"

    def _apply_case(self, text: str) -> str:
        """Apply the renderer's ``lower_case`` setting to ``text``.

        Used for tokens the renderer owns the casing of: mnemonics,
        register-suffix letters (``X`` / ``Y``), the explicit-
        accumulator marker (``A``). Labels, expressions, and
        user-supplied data keep their author-supplied case.
        """
        return text.lower() if self.lower_case else text.upper()

    def _format_immediate_byte(self, value: int) -> str:
        """Render an 8-bit immediate operand byte using the renderer's
        default heuristic.

        Mirrors py8dis-fork's ``uint_formatter`` rule: bare decimal for
        0..9 (more readable for small counts and indices), hex
        otherwise. Beebasm parses both forms identically so the
        rendered text round-trips.

        Used as the fallback when no :class:`FormatHint` is set at the
        operand byte and the auto-detect heuristic for printable-as-
        char doesn't fire.
        """
        if 0 <= value <= 9:
            return str(value)
        return self.hex2(value)

    def _render_immediate_with_hints(
        self, ir, operand_addr: int, value: int,
    ) -> str:
        """Choose an operand text for an IMMEDIATE byte, honouring
        any :class:`FormatHint` registered at ``operand_addr``.

        Decision order:

        1. Explicit hint at this byte → dispatch on the hint
           (``CHAR``, ``DECIMAL``, ``HEX``, ``BINARY``, ``OCTAL``).
           The renderer translates each abstract semantic into its
           target assembler's syntax. Hints are best-effort: if
           beebasm can't natively express a hint (e.g. no octal
           syntax), the renderer warns and falls back to a sensible
           equivalent.
        2. No hint → small-int decimal / hex via
           :meth:`_format_immediate_byte` (the renderer's default).
           The trailing ``; 'c'`` comment hint, when enabled, is
           appended later in :meth:`_render_opcode` via
           :meth:`_immediate_char_hint`; it never replaces the
           operand text.
        """
        hint = ir.format_hints.get_or_none(operand_addr)
        if hint is not None:
            return self._render_hinted_immediate(hint, value, operand_addr)
        return self._format_immediate_byte(value)

    # -- FormatHint translation (overridable defaults) --------------------
    #
    # These provide a generic, assembler-neutral rendering for each
    # semantic :class:`FormatHint`, so a backend subclassing
    # :class:`AssemblerRenderer` renders hints without reimplementing
    # anything. Backends override the pieces their syntax differs on —
    # the beebasm renderer, for instance, replaces the CHAR form
    # (``ASC("c")``) and the ``; 'c'`` comment hint. The BINARY form uses
    # :meth:`binary_literal`; the hex sigil comes from :meth:`hex2`; so a
    # backend usually only needs to touch CHAR handling.

    def binary_literal(self, value: int) -> str:
        """8-bit binary literal for a ``FormatHint.BINARY`` byte.

        Defaults to the ``%01010101`` form shared by beebasm and 64tass;
        override for an assembler that spells binary differently.
        """
        return f"%{value:08b}"

    def _render_hinted_immediate(
        self, hint: FormatHint, value: int, operand_addr: int,
    ) -> str:
        """Translate a :class:`FormatHint` to operand syntax.

        Generic default; each branch falls back sensibly (with a
        ``UserWarning``) when the value can't be expressed cleanly.
        """
        if hint is FormatHint.CHAR:
            text = self._render_char_for_explicit_hint(value)
            if text is not None:
                return text
            warnings.warn(
                f"FormatHint.CHAR at {self.hex(operand_addr)} can't be "
                f"expressed as a character literal for byte "
                f"{self.hex2(value)} (non-printable); falling back to "
                f"a numeric literal.",
                stacklevel=2,
            )
            return self._format_immediate_byte(value)
        if hint is FormatHint.DECIMAL:
            return str(value)
        if hint is FormatHint.HEX:
            return self.hex2(value)
        if hint is FormatHint.BINARY:
            return self.binary_literal(value)
        if hint is FormatHint.OCTAL:
            warnings.warn(
                f"FormatHint.OCTAL at {self.hex(operand_addr)} — this "
                f"assembler has no octal literal configured; falling "
                f"back to decimal {value} (octal {value:o}).",
                stacklevel=2,
            )
            return str(value)
        if hint is FormatHint.INKEY:
            return self._render_inkey_immediate(value, operand_addr)
        raise NotImplementedError(
            f"{type(self).__name__} doesn't yet handle "
            f"FormatHint.{hint.name}"
        )

    def _render_char_for_explicit_hint(self, value: int) -> str | None:
        """Character literal for an explicitly-marked ``CHAR`` byte, or
        ``None`` when the byte has no clean literal (caller falls back to
        hex with a warning). Default is the universal single-quoted form
        ``'c'``; backends whose char syntax differs override this.
        """
        if not (0x20 <= value <= 0x7E) or value == 0x27:
            return None
        return f"'{chr(value)}'"

    def _immediate_char_hint(self, ir, binary_addr, opcode: Opcode) -> str:
        """Optional trailing ``; '<c>'`` informational comment for a
        printable IMMEDIATE operand byte. Default: none. Backends that
        want the safe annotation (beebasm) override this.
        """
        return ""

    def _render_inkey_immediate(self, value: int, operand_addr: int) -> str:
        """Symbolic form for a ``FormatHint.INKEY`` byte.

        The disassembled byte is ``(255 - inkey_key) EOR 128`` (mod 256);
        invert to recover the named BBC negative INKEY scan code. Machine-
        agnostic: the INKEY table is lazy-imported from the ``acorn_mos``
        environment. Bytes that don't decode to a named key fall back to
        a hex literal with a one-time warning.
        """
        from dasmos.ext.environments.acorn_mos.enums import INKEY_ENUM
        inkey_key = (255 - value) ^ 0x80
        name = INKEY_ENUM.get(inkey_key)
        if name is None:
            warnings.warn(
                f"FormatHint.INKEY at {self.hex(operand_addr)} — byte "
                f"{self.hex2(value)} doesn't decode to a named BBC INKEY "
                f"scan code; falling back to a hex literal.",
                stacklevel=2,
            )
            return self.hex2(value)
        # ``(255 - inkey_key) EOR 128`` as an assembler-neutral tree, so
        # each backend renders its own XOR token (beebasm ``EOR``, 64tass
        # ``^``). The Group keeps the readability parens.
        e = Binary(
            BinOp.XOR,
            Group(Int(255, Radix.DEC) - Sym(name)),
            Int(128, Radix.DEC),
        )
        return self.render_expression(e, None)

    def _render_operand(
        self, ir, binary_addr, opcode: Opcode, *, active_move=None,
    ) -> str:
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
            return self._apply_case("A") if self.explicit_a else ""

        # Resolve the unwrapped symbol (without mode-specific
        # punctuation like # or parens).
        symbol = self._resolve_operand_symbol(
            ir, binary_addr, opcode, operand_addr,
            active_move=active_move,
        )

        # Register-suffix letters owned by the renderer (X / Y) follow
        # the ``lower_case`` setting. The user-resolved ``symbol``
        # (label / expression / hex literal) keeps its own case.
        x = self._apply_case("X")
        y = self._apply_case("Y")

        # Wrap with mode-specific syntax.
        if mode_name == "IMMEDIATE":
            return f"#{symbol}"
        if mode_name in ("ZERO_PAGE", "ABSOLUTE", "RELATIVE"):
            return symbol
        if mode_name in ("ZERO_PAGE_X", "ABSOLUTE_X"):
            return f"{symbol},{x}"
        if mode_name in ("ZERO_PAGE_Y", "ABSOLUTE_Y"):
            return f"{symbol},{y}"
        if mode_name == "INDIRECT":
            return f"({symbol})"
        if mode_name == "INDEXED_INDIRECT":  # (zp,X)
            return f"({symbol},{x})"
        if mode_name == "INDIRECT_INDEXED":  # (zp),Y
            return f"({symbol}),{y}"
        # 65C02 additions:
        if mode_name == "ZP_INDIRECT":  # (zp)
            return f"({symbol})"
        if mode_name == "ABSOLUTE_INDIRECT_X":  # JMP (addr,X)
            return f"({symbol},{x})"

        raise ValueError(
            f"{type(self).__name__} does not know how to render addressing mode "
            f"{mode_name!r}"
        )

    def _resolve_operand_symbol(
        self, ir, binary_addr, opcode, operand_addr, *, active_move=None,
    ) -> str:
        """Resolve the unwrapped operand symbol — expression / label /
        hex literal — without applying mode-specific punctuation.

        ``binary_addr`` is the address of the opcode byte; passed
        through to label lookup for local-label scope checking.
        ``active_move`` (optional) is the move whose runtime mapping
        the relative-branch arithmetic should use; without it we fall
        back to ``ir.moves.b2r`` which picks the most-recently-
        registered containing move.
        """
        # 1. User-supplied expression takes precedence over everything.
        expr = ir.expressions.get_or_none(operand_addr)
        if expr is not None:
            return self.render_expression(expr, ir, active_move=active_move)

        kind = opcode.addressing_mode.operand_kind
        using_addr = int(binary_addr)

        if kind is OperandKind.IMMEDIATE:
            # Immediate values aren't addresses; no label lookup.
            value = ir.memory.get_u8(operand_addr)
            return self._render_immediate_with_hints(
                ir, operand_addr, value,
            )

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
            # Branch-target arithmetic in runtime space so a branch
            # inside a moved region resolves to the right runtime
            # label. With moves-first emission, the SAME source byte
            # may be emitted under more than one move (overlap
            # region); ``active_move`` pins this resolution to the
            # move whose body we're currently rendering. Outside a
            # move (or when called without active_move), b2r is the
            # identity / picks the only / most-recent containing move.
            if active_move is not None:
                base_runtime = (
                    int(active_move.dest_runtime_addr)
                    + (int(binary_addr) - int(active_move.src_binary_addr))
                )
            else:
                base_runtime = int(
                    ir.moves.b2r(BinaryAddr(int(binary_addr)))
                )
            target = base_runtime + opcode.length() + offset
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
            # have no business naming this operand. Auto-generated
            # names land in the same ``explicit_names`` collection so
            # they flow through this path naturally. Insertion order
            # picks the structural / first-registered name when an
            # address has multiple aliases.
            names = label.explicit_names_in_insertion_order()
            if names:
                if not self._label_address_is_in_range(ir, addr):
                    self._used_external_labels.add(addr)
                return names[0]
            # No explicit name — fall back to an expression. Drivers
            # use ``d.expr_label(addr, "<base>-1")`` to register a
            # use-site form for an address that's a one-byte-before-
            # base offset (the classic ``LDA dispatch_lo-1,X``
            # pattern). py8dis renders those operands using the
            # expression form too; without this fallback dasmos's
            # operand stays as raw hex.
            for expr_list in label.expressions.values():
                if expr_list:
                    if not self._label_address_is_in_range(ir, addr):
                        self._used_external_labels.add(addr)
                    return self.render_expression(expr_list[0], ir)
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

    def _label_has_inline_offset_base(self, ir, runtime_addr: int) -> bool:
        """True iff the runtime address is inside a multi-byte
        classification AND that classification's start has an explicit
        name AND the label sits at its NATURAL runtime (not a move-
        dest variant — those can't reach an inline anchor). The body
        walk emits ``<name> = <base>+<offset>`` for such labels right
        under the base, so they shouldn't also appear in the equate
        table.
        """
        from dasmos.core.disassembly import INSIDE_A_CLASSIFICATION
        from dasmos.core.memory import BinaryAddr, RuntimeAddr
        binary_loc, _ = ir.moves.r2b(RuntimeAddr(runtime_addr))
        if binary_loc is None:
            return False
        binary_addr = int(binary_loc)
        # Mid-instruction labels inside moved regions (where b2r
        # doesn't round-trip) get literal-hex equates instead.
        if int(ir.moves.b2r(BinaryAddr(binary_addr))) != runtime_addr:
            return False
        c = ir.classifications.get_classification(binary_addr)
        if c is not INSIDE_A_CLASSIFICATION:
            return False
        start = binary_addr - 1
        while start >= 0:
            sc = ir.classifications.get_classification(start)
            if sc is None:
                return False
            if sc is not INSIDE_A_CLASSIFICATION:
                break
            start -= 1
        if start < 0:
            return False
        start_runtime = int(ir.moves.b2r(BinaryAddr(start)))
        base_label = ir.labels.get_label(start_runtime)
        return (
            base_label is not None and bool(base_label.explicit_name_texts())
        )

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
        """Render a Byte block as one or more ``equb`` lines.

        Per-byte resolution order:

        1. Expression override (``d.expr(addr, expr)``) — used by the
           ``acorn_sideways_rom`` environment to render the copyright-
           offset byte at ``&8007`` as
           ``equb copyright - language_entry``.
        2. Format hint (``d.format_hint(addr, FormatHint.BINARY)``)
           — dispatched through the same hint switch as the
           operand-immediate path, so a byte tagged ``BINARY``
           renders as ``%10000010`` instead of ``&82``. Used for
           bitfield bytes like the sideways-ROM ``rom_type`` byte.
        3. Default — ``hex2`` literal.
        """
        cols = c.cols() or self.default_byte_cols
        n = c.length()
        lines: list[str] = []
        run: list[str] = []  # accumulated ``equb`` value parts

        def flush() -> None:
            for cs in range(0, len(run), cols):
                lines.append(
                    f"    {self.byte_prefix()}{', '.join(run[cs:cs + cols])}"
                )
            run.clear()

        for i in range(n):
            addr = int(binary_addr) + i
            expr = ir.expressions.get_or_none(addr)
            # A macro invocation on a backend without value macros is a
            # statement, not a value — flush the run and emit its line(s).
            if isinstance(expr, MacroCall) and not self.macro_calls_are_values:
                flush()
                lines.extend(self.render_macro_statement(expr, ir))
                continue
            if expr is not None:
                run.append(self.render_expression(expr, ir))
                continue
            value = ir.memory.get_u8(addr)
            hint = ir.format_hints.get_or_none(addr)
            if hint is not None:
                run.append(self._render_hinted_immediate(hint, value, addr))
            else:
                run.append(self.hex2(value))
        flush()
        return lines

    def _render_word(self, ir, binary_addr, c: Word) -> list[str]:
        """Render a Word block as one or more ``equw`` lines.

        Per-word expression overrides (registered via ``d.expr(addr,
        expr)`` against the word's binary address) substitute for the
        word value's address-to-name resolution. Used by
        :meth:`Disassembler.code_ptr` to emit ``equw target`` (or
        ``equw target-1`` for the RTS variant) for adjacent
        pointer-into-code byte pairs.
        """
        cols = c.cols() or self.default_word_cols
        n_words = c.length() // 2
        lines: list[str] = []
        for chunk_start in range(0, n_words, cols):
            parts: list[str] = []
            for i in range(chunk_start, min(chunk_start + cols, n_words)):
                word_binary = int(binary_addr) + i * 2
                expr = ir.expressions.get_or_none(word_binary)
                if expr is not None:
                    parts.append(self.render_expression(expr, ir))
                else:
                    w = ir.memory.get_u16_le(word_binary)
                    parts.append(self._addr_text(ir, w, width=16))
            lines.append(f"    {self.word_prefix()}{', '.join(parts)}")
        return lines

    def _render_string(self, ir, binary_addr, c: String) -> list[str]:
        """Render a String classification.

        Naive first cut: emits ``equs`` for runs of printable
        characters and ``equb`` for non-printable bytes, on a single
        line. Round-trip-correct; not the prettiest possible rendering.
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
        first_is_string = parts[0].startswith('"')
        has_string = any(p.startswith('"') for p in parts)
        prefix = self._string_line_directive(
            first_is_string=first_is_string, has_string=has_string,
        )
        return [f"    {prefix}{', '.join(parts)}"]

    def _string_line_directive(
        self, *, first_is_string: bool, has_string: bool,
    ) -> str:
        """Directive introducing a data line that mixes quoted-string
        runs with raw bytes.

        Default: the first element decides — beebasm's ``equs`` / ``equb``
        both accept a mixed comma list, so leading with either works.
        A backend whose byte directive rejects multi-character string
        literals (64tass's ``.byte``) overrides this to prefer the
        string directive (``.text``) whenever any part is a string.
        """
        return self.string_prefix() if first_is_string else self.byte_prefix()

    def translate_expression(self, expr: str) -> str:
        """Render a :class:`~dasmos.core.expr.Raw` node's text.

        ``Raw`` is the fallback for a driver string that
        :mod:`dasmos.core.expr_parse` could not parse into a structured
        tree — it is emitted verbatim in the beebasm/py8dis dialect it
        was authored in. Structured trees never reach here; they go
        through :meth:`render_expression`, which emits each backend's own
        syntax directly. Default is verbatim; a backend could override to
        best-effort-adapt an unparseable string, but in practice the
        parser covers the whole dialect grammar, so this is rarely (if
        ever) exercised.
        """
        return expr

    # -- structured expression rendering ----------------------------------
    #
    # A driver-authored expression is an assembler-neutral
    # :class:`~dasmos.core.expr.Expr` tree. ``render_expression`` walks it
    # and emits this backend's syntax, inserting parentheses per this
    # backend's own operator precedence so the emitted text evaluates to
    # the tree's meaning regardless of how the assembler's grammar ranks
    # its operators. Token spellings and precedence come from overridable
    # tables; a backend usually only sets those two.

    #: Sentinel precedence for atoms (literals, names) — binds tighter
    #: than any operator, so an atom child never gets wrapped.
    _ATOM_PRECEDENCE = 1000

    #: Binary-operator precedence (higher binds tighter). Default is
    #: beebasm's table (from ``beebasm/src/expression.cpp``). 64tass
    #: overrides with its C-like ranking.
    _BINARY_PRECEDENCE = {
        BinOp.MUL: 6, BinOp.DIV: 6, BinOp.MOD: 6,
        BinOp.SHL: 6, BinOp.SHR: 6,
        BinOp.ADD: 5, BinOp.SUB: 5,
        BinOp.AND: 3,
        BinOp.OR: 2, BinOp.XOR: 2,
    }

    #: Unary-operator precedence. Byte-selects bind tighter than
    #: arithmetic negation in both beebasm and 64tass.
    _UNARY_PRECEDENCE = {
        UnaryOp.NEG: 8, UnaryOp.POS: 8, UnaryOp.INVERT: 8,
        UnaryOp.LOWBYTE: 10, UnaryOp.HIGHBYTE: 10, UnaryOp.BANKBYTE: 10,
    }

    def _binary_token(self, op: BinOp) -> str:
        """This backend's spelling of a binary operator (beebasm form by
        default; 64tass overrides the bitwise/division operators).

        ``BinOp.DIV`` is *integer* division — beebasm's ``DIV`` keyword,
        not ``/`` (which is real division in beebasm). Assemblers that
        spell integer division ``/`` (64tass, acme) override it.
        """
        return {
            BinOp.ADD: "+", BinOp.SUB: "-", BinOp.MUL: "*", BinOp.DIV: "DIV",
            BinOp.MOD: "MOD", BinOp.AND: "AND", BinOp.OR: "OR",
            BinOp.XOR: "EOR", BinOp.SHL: "<<", BinOp.SHR: ">>",
        }[op]

    def render_expression(self, e: Expr, ir, *, active_move=None) -> str:
        """Render an :class:`~dasmos.core.expr.Expr` to this backend's
        operand/data syntax.

        String operations render in this backend's native syntax so the
        string stays visible (``"BRK"[0]``), keeping the disassembly
        readable — unless ``fold_string_ops`` is set, in which case
        constant string ops are folded to their value (``'B'``) for terse
        output. A string op the backend can't express natively is folded
        as a fallback (see :meth:`_emit_string_op`).
        """
        if self.fold_string_ops:
            e = fold(e)
        text, _ = self._emit_expr(e, ir, active_move)
        return text

    def _emit_expr(self, e: Expr, ir, active_move) -> tuple[str, int]:
        """Return ``(text, precedence)`` for ``e`` — precedence is that of
        the top operator, or :attr:`_ATOM_PRECEDENCE` for a leaf, so the
        caller knows whether to parenthesise it."""
        if isinstance(e, Raw):
            # Legacy dialect string — dialect-translate, treat as opaque
            # atom (it already carries its own parenthesisation).
            return self.translate_expression(e.text), self._ATOM_PRECEDENCE
        if isinstance(e, Int):
            return self._render_int_node(e), self._ATOM_PRECEDENCE
        if isinstance(e, Sym):
            return e.name, self._ATOM_PRECEDENCE
        if isinstance(e, Ref):
            return (
                self._render_ref_node(ir, e, active_move),
                self._ATOM_PRECEDENCE,
            )
        if isinstance(e, Group):
            inner, _ = self._emit_expr(e.inner, ir, active_move)
            return f"({inner})", self._ATOM_PRECEDENCE
        if isinstance(e, Str):
            return f'"{e.text}"', self._ATOM_PRECEDENCE
        if isinstance(e, Param):
            return self.param_ref(e.name), self._ATOM_PRECEDENCE
        if isinstance(e, MacroCall):
            return (
                self.render_macro_value_call(e, ir, active_move),
                self._ATOM_PRECEDENCE,
            )
        if isinstance(e, (StrIndex, StrSlice, StrLen)):
            return self._emit_string_op(e, ir, active_move), self._ATOM_PRECEDENCE
        if isinstance(e, Unary):
            return self._emit_unary(e, ir, active_move)
        if isinstance(e, Binary):
            return self._emit_binary(e, ir, active_move)
        raise TypeError(
            f"{type(self).__name__} cannot render expression node "
            f"{type(e).__name__}"
        )

    def _emit_string_op(self, e, ir, active_move) -> str:
        """Render a string operation in this backend's native syntax so
        the string stays visible.

        If this backend has no native form for it
        (:class:`NotImplementedError` from the render hook), fall back to
        constant-folding: a constant string op still renders (as its
        value); a non-constant one that the backend can't express is a
        genuine error — the driver must make the operand constant.
        """
        s_of = lambda x: self._emit_expr(x, ir, active_move)[0]
        try:
            if isinstance(e, StrIndex):
                return self.render_string_index(e.string, e.index, s_of)
            if isinstance(e, StrLen):
                return self.render_string_length(s_of(e.string))
            stop = None if e.stop is None else s_of(e.stop)
            return self.render_string_slice(s_of(e.string), s_of(e.start), stop)
        except NotImplementedError:
            folded = fold(e)
            if folded is e or isinstance(folded, (StrIndex, StrSlice, StrLen)):
                raise  # non-constant AND unsupported here — genuinely can't
            return self._emit_expr(folded, ir, active_move)[0]

    def render_string_index(self, string_node, index_node, render) -> str:
        """Character code of ``string_node`` at ``index_node`` (0-based).

        ``render`` renders a sub-expression to text. Given the nodes (not
        just text) so a backend can adapt a constant index cleanly (e.g.
        beebasm's 1-based ``MID$``). Default: unsupported — a backend with
        no string indexing relies on :func:`~dasmos.core.expr.fold`.
        """
        raise NotImplementedError(
            f"{type(self).__name__} has no native string indexing"
        )

    def render_string_slice(self, s: str, i: str, j: "str | None") -> str:
        raise NotImplementedError(
            f"{type(self).__name__} cannot render non-constant string slicing"
        )

    def render_string_length(self, s: str) -> str:
        raise NotImplementedError(
            f"{type(self).__name__} cannot render non-constant string length"
        )

    # -- macros -----------------------------------------------------------
    #
    # A driver-defined macro (dasmos.core.expr.MacroDef) is emitted once as
    # a definition; each MacroCall refers to it. Backends split on whether
    # a macro invocation is a *value* (usable inside a data directive —
    # 64tass .sfunction, ca65 .define) or a *statement* (its own line —
    # beebasm, acme). ``macro_calls_are_values`` selects the path; the
    # data-block renderer emits per-line invocations for the statement
    # case.

    @property
    def macro_calls_are_values(self) -> bool:
        """True iff a macro invocation can appear inside a data directive
        / expression (a value function). False when each invocation must
        be its own statement line."""
        return False

    def param_ref(self, name: str) -> str:
        """How a macro formal parameter is referenced in a body. Default:
        the bare name (beebasm; 64tass functions). A backend whose macro
        params use sigils (64tass ``.macro`` ``\\name``) overrides."""
        return name

    def render_macro_value_call(self, call, ir, active_move) -> str:
        """A macro invocation used as a value. Only valid when
        :attr:`macro_calls_are_values`; otherwise the data-block renderer
        must intercept and emit a statement instead."""
        if not self.macro_calls_are_values:
            raise NotImplementedError(
                f"{type(self).__name__} has no value macros; a MacroCall "
                f"must be emitted as a statement line"
            )
        args = ", ".join(
            self.render_expression(a, ir, active_move=active_move)
            for a in call.args
        )
        return f"{call.name}({args})"

    def _macro_arg_texts(self, call, ir) -> list[str]:
        return [self.render_expression(a, ir) for a in call.args]

    def render_macro_statement(self, call, ir) -> list[str]:
        """A macro invocation as its own statement line(s). Backends
        without value macros (beebasm, acme) override this."""
        raise NotImplementedError(
            f"{type(self).__name__} cannot render a macro invocation as a "
            f"statement"
        )

    def render_macro_definition(self, macro, ir) -> list[str]:
        """The definition block for a macro. Each backend emits its own
        construct (64tass ``.sfunction``; beebasm ``MACRO``…``ENDMACRO``)."""
        raise NotImplementedError(
            f"{type(self).__name__} cannot render macro definitions"
        )

    def _build_macro_definitions(self, ir) -> list[str]:
        """The macro-definitions block, emitted once above the body."""
        lines: list[str] = []
        for macro in ir.macros.values():
            block = self.render_macro_definition(macro, ir)
            if block:
                lines.extend(block)
                lines.append("")
        return lines

    def _render_int_node(self, node: Int) -> str:
        v = node.value
        if node.radix is Radix.CHAR:
            lit = self.char_literal(v)
            return lit if lit is not None else self._auto_int(v)
        if node.radix is Radix.DEC:
            return str(v)
        if node.radix is Radix.HEX:
            return self.hex(v)
        if node.radix is Radix.BIN:
            return self.binary_literal(v)
        return self._auto_int(v)

    def _auto_int(self, v: int) -> str:
        """AUTO radix: small non-negative ints decimal, else hex — the
        same heuristic as :meth:`_format_immediate_byte`, extended to
        16-bit via :meth:`hex`."""
        if 0 <= v <= 9:
            return str(v)
        return self.hex(v)

    def _render_ref_node(self, ir, node: Ref, active_move) -> str:
        """Resolve a :class:`Ref` to its label's best name, or a hex
        literal when the address has no name."""
        return self._addr_text(ir, int(node.runtime_addr), width=16)

    #: Unary operators rendered as a *function-like* form that brackets
    #: its own operand (so operand precedence is irrelevant and no
    #: ambiguity can arise). The rest (NEG/POS) are prefix operators.
    _UNARY_FUNCTION_OPS = frozenset(
        {UnaryOp.LOWBYTE, UnaryOp.HIGHBYTE, UnaryOp.INVERT, UnaryOp.BANKBYTE}
    )

    def _emit_unary(self, e: Unary, ir, active_move) -> tuple[str, int]:
        if e.op in self._UNARY_FUNCTION_OPS:
            # Bracketed forms: an explicit Group directly inside would
            # double the parens — unwrap one level.
            operand = e.operand.inner if isinstance(e.operand, Group) else e.operand
            inner, _ = self._emit_expr(operand, ir, active_move)
            render = {
                UnaryOp.LOWBYTE: self.render_lowbyte,
                UnaryOp.HIGHBYTE: self.render_highbyte,
                UnaryOp.INVERT: self.render_bitwise_not,
                UnaryOp.BANKBYTE: self.render_bank_byte,
            }[e.op]
            return render(inner), self._ATOM_PRECEDENCE
        prec = self._UNARY_PRECEDENCE[e.op]
        inner = self._emit_child(e.operand, ir, active_move, prec, right=True)
        token = {UnaryOp.NEG: "-", UnaryOp.POS: "+"}[e.op]
        return f"{token}{inner}", prec

    def _emit_binary(self, e: Binary, ir, active_move) -> tuple[str, int]:
        prec = self._BINARY_PRECEDENCE[e.op]
        # All supported binary operators are left-associative: a left
        # child of equal precedence needs no parens, a right child of
        # equal precedence does.
        left = self._emit_child(e.left, ir, active_move, prec, right=False)
        right = self._emit_child(e.right, ir, active_move, prec, right=True)
        return f"{left} {self._binary_token(e.op)} {right}", prec

    def _emit_child(self, child, ir, active_move, parent_prec, *, right) -> str:
        text, child_prec = self._emit_expr(child, ir, active_move)
        needs = child_prec < parent_prec or (right and child_prec == parent_prec)
        return f"({text})" if needs else text

    def render_lowbyte(self, inner_text: str) -> str:
        """Low byte of an already-rendered sub-expression. Default form
        ``<(...)`` (valid in beebasm and 64tass); a backend may override
        (e.g. beebasm ``LO(...)``)."""
        return f"<({inner_text})"

    def render_highbyte(self, inner_text: str) -> str:
        """High byte of an already-rendered sub-expression."""
        return f">({inner_text})"

    def render_bitwise_not(self, inner_text: str) -> str:
        """Bitwise complement of an already-rendered sub-expression.
        Default ``~(...)`` (64tass, ca65, acme); beebasm overrides with
        its function form ``NOT(...)``."""
        return f"~({inner_text})"

    def render_bank_byte(self, inner_text: str) -> str:
        """Bank byte (bits 16-23) of an already-rendered sub-expression —
        a 65816 concept. Unsupported by default; a backend targeting the
        65816 overrides it (64tass ``^``)."""
        raise NotImplementedError(
            f"{type(self).__name__} has no bank-byte operator"
        )
