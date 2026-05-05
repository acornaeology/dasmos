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
# comment are present on the same line. Roughly: ``&XXXX: `` (7) +
# bytes section (8 = max 3 bytes "XX YY ZZ") + gap + ascii (3-char
# field).
BYTE_COLUMN_TOTAL_WIDTH = 27

# Banner separator width: a row of this many ``*`` characters,
# prefixed by the comment prefix and a space, between the title and
# the surrounding text.
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

    BYTE_COLUMN_FORMATS = ("dasmos", "py8dis")

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
        show_char_literals: bool = True,
        lower_case: bool = True,
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
        # leave it off; the porter and parity tests opt in.
        self.byte_column = byte_column
        # Byte-column flavour:
        # - ``"dasmos"`` (default): ``&xxxx`` prefix, b2r-resolved
        #   address, no move suffix. Reads naturally as part of dasmos
        #   output (``&`` is beebasm's hex sigil).
        # - ``"py8dis"``: bare 4-digit hex, binary address. Inside a
        #   relocated region also append ``:<runtime_hex>[<move_id>]``
        #   so a reader can see both the binary file position AND the
        #   execution address. Use this for byte-for-byte annotation
        #   parity with the legacy py8dis fork's output.
        if byte_column_format not in self.BYTE_COLUMN_FORMATS:
            raise ValueError(
                f"byte_column_format must be one of "
                f"{self.BYTE_COLUMN_FORMATS!r}, got {byte_column_format!r}"
            )
        self.byte_column_format = byte_column_format
        # Default chunking widths for ``Byte`` / ``Word`` blocks
        # whose own ``cols()`` is None (the typical case for blocks
        # registered without an explicit cols=). The porter overrides
        # these (``default_byte_cols=12`` / ``default_word_cols=6``)
        # for its py8dis-compat preset.
        self.default_byte_cols = default_byte_cols
        self.default_word_cols = default_word_cols
        # When True, emit the trailing ``; Automatically generated
        # labels:`` footer block listing every label whose explicit
        # name was synthesised by the Disassembler's auto-label pass.
        # The names themselves are generated by the Disassembler (so
        # all renderers agree on which addresses are named); this flag
        # only controls whether THIS renderer surfaces them in the
        # footer.
        self.show_auto_label_footer = show_auto_label_footer
        # Column at which Markdown-rendered paragraphs in standalone
        # narrative text (banner descriptions, future word-wrapped
        # comments) reflow. Match py8dis-fork's default of 87 so
        # ported drivers produce visually-similar wrapping. The
        # ``;`` prefix and one space are NOT counted in this column —
        # ``textwrap.fill`` operates on the raw text and the ``; ``
        # is added per-line at emit time.
        self.comment_wrap_column = comment_wrap_column
        # When True, append a ``; '<c>'`` hint to immediate-mode
        # instructions whose operand byte is a printable ASCII
        # character. Mirrors py8dis-fork's ``show_char_literals``
        # config. Suppressed when:
        # - the user has registered a custom expression at the
        #   operand byte (the user's symbol takes precedence);
        # - the byte is the ASCII apostrophe (``'``) or double-quote
        #   (``"``), which would form ambiguous comment syntax.
        self.show_char_literals = show_char_literals
        # When True (default), mnemonics and the indexed-mode register
        # suffixes (``,X`` / ``,Y``) and the explicit-accumulator
        # marker (``A``) all render in lowercase: ``sta &20,x``,
        # ``rol a``. Matches py8dis-fork's lowercase house style and
        # the dasmos ``Config.lower_case=True`` default. Set False
        # for the all-uppercase form shown in the official beebasm
        # documentation: ``STA &20,X``, ``ROL A``. Beebasm itself is
        # case-insensitive in the assembly grammar, so both forms
        # round-trip to identical bytes.
        self.lower_case = lower_case

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
                lines.append("")
                lines.append(f"    org {self.hex(ba)}")
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
                lines.append("")
                lines.append(f"    org {self.hex(int(load_end))}")
            lines.append(self.inline_label(self.boundary_end_label))
        lines.append("")
        lines.append(self._save_directive(load_start, load_end))
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

        return TextOutput("\n".join(lines) + "\n")

    def _build_constant_equates(self, ir) -> list[str]:
        """``name = value`` lines for every registered constant
        (deduped by name — multiple registrations of the same
        ``(value, name)`` pair, common when several JSR sites trigger
        the same OSBYTE-hook substitution, collapse to one equate).
        Emitted in registration order.
        """
        seen: set[str] = set()
        lines: list[str] = []
        # Compute name column width across all unique names.
        unique = []
        for c in ir.constants:
            if c.name in seen:
                continue
            seen.add(c.name)
            unique.append(c)
        if not unique:
            return []
        max_name_len = max(len(c.name) for c in unique)
        for c in unique:
            line = (
                f"{c.name.ljust(max_name_len)} = {self.hex(int(c.value))}"
            )
            if c.comment:
                line = f"{line}  {self.comment_prefix()} " + " ".join(
                    c.comment.split()
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
        end = src_addr + move.length
        src_label = self._first_explicit_name(ir, src_addr)

        # Position PC at the move's source binary address. Every
        # move emits this so the moves can appear in any order in
        # the file (each one announces where its source bytes live).
        lines.append("")
        lines.append(f"    org {self.hex(src_addr)}")
        if src_label is not None:
            lines.append(self.inline_label(src_label))
            self._inline_emitted_runtime_addrs.add(src_addr)

        lines.extend(self._emit_move_enter(moves_by_src, move, src_label))
        active_move_id = move_ids.get(id(move))

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

        active_move_dest_label = self._first_explicit_name(
            ir, int(move.dest_runtime_addr),
        )
        lines.extend(self._emit_move_exit(
            move, src_label, active_move_dest_label,
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
            names = sorted(label.explicit_name_texts())
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
            base_names = sorted(label.explicit_name_texts())
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
                    inner_xref = self._format_inline_xref_summary(
                        inner_label, inner_runtime,
                    )
                    if inner_xref is not None:
                        lines.append(inner_xref)
                    for inner_name in sorted(inner_label.explicit_name_texts()):
                        lines.append(f"{inner_name} = {base_name}+{off}")
                    self._inline_emitted_runtime_addrs.add(inner_runtime)

        for ann in ir.annotations.get_for_align(binary_addr, Align.AFTER_LABEL):
            lines.extend(self._render_annotation(ann))
        for ann in ir.annotations.get_for_align(binary_addr, Align.BEFORE_LINE):
            lines.extend(self._render_annotation(ann))

        content_lines = self._render_classification(
            ir, binary_addr, classification, active_move=active_move,
        )

        inline_anns = ir.annotations.get_for_align(binary_addr, Align.INLINE)
        user_inline_text = None
        if inline_anns:
            user_inline_text = "  ".join(
                self._render_annotation_inline(a) for a in inline_anns
            )
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
                line = f"{line}  {self.comment_prefix()} " + " ".join(
                    description.split()
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

    # -- cross-reference emission ---------------------------------------
    #
    # Reference data is computed by the Disassembler and stored in
    # ``Label.references``. The renderer just reads from there.

    def _format_inline_xref_summary(self, label, runtime_addr: int) -> str | None:
        """Format the ``; &<addr> referenced N time(s) by &<r1>, …``
        line for a label, or return ``None`` when the label has no
        recorded references.
        """
        if not label.references:
            return None
        unique_refs = sorted({int(r.binary_addr) for r in label.references})
        count = len(unique_refs)
        word = "time" if count == 1 else "times"
        ref_list = ", ".join(self.hex(r) for r in unique_refs)
        return (
            f"{self.comment_prefix()} {self.hex(runtime_addr)} "
            f"referenced {count} {word} by {ref_list}"
        )

    # -- move-aware emission --------------------------------------------

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
        names = sorted(label.explicit_name_texts())
        return names[0] if names else None

    def _emit_move_enter(
        self,
        moves_by_src: dict[int, "Move"],
        move: "Move",
        src_label: str | None,
    ) -> list[str]:
        """Return the lines that switch beebasm's PC from the source
        position into the relocated destination range.

        Layout::

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
        move: "Move",
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

    # -- auto-generated label footer ------------------------------------

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

    # -- byte-column inline annotation ----------------------------------

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
            for name in sorted(label.explicit_name_texts()):
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

    # -- annotations ------------------------------------------------------

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
        raise TypeError(f"unknown annotation type: {type(ann).__name__}")

    def _render_annotation_inline(self, ann) -> str:
        """Render a Comment or Annotation as the inline (trailing) form.

        Banner inline form is not supported (banners are inherently
        multi-line); attach them at one of the standalone alignments.
        """
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
    def _comment_text_for_asm(ann: Comment, *, inline: bool) -> str:
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
            text = strip_address_uri_links(ann.text)
            if inline:
                # Collapse whitespace for inline rendering even in
                # word_wrap=False mode — the trailing column on the
                # instruction line is the constraint.
                import re as _re
                text = _re.sub(r"\s+", " ", text).strip()
            return text
        return markdown_to_asm_text(ann.text, inline=inline)

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
            title_text = markdown_to_asm_text(banner.title, inline=True)
            out.append(f"{prefix} {title_text}")
        if banner.description:
            if banner.title:
                out.append(prefix)
            description_text = markdown_to_asm_text(
                banner.description, wrap_width=self.comment_wrap_column,
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
                # whatever the user supplied.
                out.append(f"{prefix}     {key.upper()}: {value}")
        return out

    # -- per-classification rendering -------------------------------------

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
            f"BeebasmRenderer does not know how to render {type(c).__name__}"
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
        """Render an 8-bit immediate operand byte.

        Mirrors py8dis-fork's ``uint_formatter`` rule: bare decimal for
        0..9 (more readable for small counts and indices), hex
        otherwise. Beebasm parses both forms identically so the
        rendered text round-trips.
        """
        if 0 <= value <= 9:
            return str(value)
        return self.hex2(value)

    def _immediate_char_hint(self, ir, binary_addr, opcode: Opcode) -> str:
        """Return a `` ; '<c>'`` trailing hint for printable-ASCII
        immediates, or the empty string if the hint should be
        suppressed.

        Suppression conditions (any one is enough):

        - ``show_char_literals`` is False on this renderer.
        - The opcode's addressing mode isn't IMMEDIATE.
        - A user-supplied expression is registered at the operand
          byte: the user has chosen a more meaningful symbol and the
          auto-hint would be redundant noise.
        - The byte isn't printable ASCII (``0x20..0x7E``).
        - The byte is ``'`` or ``"``: a single-quoted hint would form
          ambiguous comment syntax (``; '''`` / ``; '"'``).
        """
        if not self.show_char_literals:
            return ""
        if opcode.addressing_mode.name != "IMMEDIATE":
            return ""
        operand_addr = int(binary_addr) + 1
        if ir.expressions.get_or_none(operand_addr) is not None:
            return ""
        value = ir.memory.get_u8(operand_addr)
        if not (0x20 <= value <= 0x7E):
            return ""
        if value in (0x22, 0x27):  # ", '
            return ""
        return f" ; '{chr(value)}'"

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
            f"BeebasmRenderer does not know how to render addressing mode "
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
            return expr

        kind = opcode.addressing_mode.operand_kind
        using_addr = int(binary_addr)

        if kind is OperandKind.IMMEDIATE:
            # Immediate values aren't addresses; no label lookup.
            return self._format_immediate_byte(
                ir.memory.get_u8(operand_addr),
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
            # they flow through this path naturally.
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

        Per-byte expression overrides (registered via ``d.expr(addr,
        expr)``) substitute for the literal hex when present. Used by
        the ``acorn_sideways_rom`` environment to render the
        copyright-offset byte at ``&8007`` as ``equb copyright -
        rom_header`` instead of its literal value.
        """
        cols = c.cols() or self.default_byte_cols
        n = c.length()
        lines: list[str] = []
        for chunk_start in range(0, n, cols):
            parts: list[str] = []
            for i in range(chunk_start, min(chunk_start + cols, n)):
                addr = int(binary_addr) + i
                expr = ir.expressions.get_or_none(addr)
                if expr is not None:
                    parts.append(expr)
                else:
                    parts.append(self.hex2(ir.memory.get_u8(addr)))
            lines.append(f"    {self.byte_prefix()}{', '.join(parts)}")
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
                    parts.append(expr)
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
        # Join with ", "; first part determines whether we lead with
        # equs or equb.
        first_is_string = parts[0].startswith('"')
        prefix = self.string_prefix() if first_is_string else self.byte_prefix()
        return [f"    {prefix}{', '.join(parts)}"]
