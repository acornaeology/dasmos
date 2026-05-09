"""JSON structured-output renderer for dasmos.

Emits a JSON-serialisable dictionary:

.. code-block:: python

    {
      "meta": {"load_addr": int, "end_addr": int},
      "constants": [{"name": str, "value": int, "comment": str?}, ...],
      "subroutines": [{"addr": int, "name": str?, ..., "fall_through": True?}],
      "banners": [{"addr": int, "title": str?, "description": str?, ...}],
      "external_labels": {"name": int, ...},
      "memory_map": [{"addr": int, "name": str, "length": int?, ...}],
      "items": [
        {
          "addr": int,             # runtime_addr
          "bytes": [int, ...],
          "binary_addr": int?,     # only if differs from runtime_addr
          "labels": [str, ...]?,
          "sub_labels": {addr: [str, ...]}?,
          "comments_before": [str, ...]?,
          "comment_inline": str?,
          "comments_after": [str, ...]?,
          "references": [int, ...]?,
          "type": "code"|"string"|"word"|"fill"|"byte",
          # type-specific: mnemonic/operand/target/target_label,
          #                values/expressions, value/length, string
        }
      ]
    }

This renderer doesn't need the assembler-syntax protocol (no equ/
mnemonic/comment-prefix concerns), so it derives directly from
:class:`dasmos.renderer.Renderer` rather than ``TextRenderer``.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from dasmos.core.annotations import Align, Annotation, Banner, Comment
from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.format_hint import FormatHint
from dasmos.core.markdown_asm import markdown_normalize_headings
from dasmos.core.memory import BinaryAddr, RuntimeAddr
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import StructuredOutput
from dasmos.renderer import Renderer

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


class JsonRenderer(Renderer[StructuredOutput]):
    """JSON structured-output renderer.

    See module docstring for the full schema.
    """

    def __init__(self, name: str = "json", *, indent: int | None = 2, **kwargs):
        super().__init__(name=name, **kwargs)
        self._indent = indent

    def cpus_supported(self) -> list[str]:
        # CPU-agnostic — we just read mnemonic / operand info from the
        # Opcode classification, no syntax-specific output.
        return ["6502", "65C02"]

    def render(self, ir: "IntermediateRepresentation") -> StructuredOutput:
        data = {
            "meta": self._build_meta(ir),
            "constants": self._build_constants(ir),
            "subroutines": self._build_subroutines(ir),
            "banners": self._build_banners(ir),
            "external_labels": self._build_external_labels(ir),
            "memory_map": self._build_memory_map(ir),
            "items": self._build_items(ir),
        }
        return StructuredOutput(data, indent=self._indent)

    # -- top-level sections ---------------------------------------------

    def _build_meta(self, ir) -> dict[str, int]:
        try:
            start, end = ir.memory.entire_load_range()
        except Exception:
            return {"load_addr": 0, "end_addr": 0}
        return {"load_addr": int(start), "end_addr": int(end)}

    def _build_constants(self, ir) -> list[dict[str, Any]]:
        """``constants`` registered via :meth:`Disassembler.constant`,
        in driver-registration order. Each entry is ``{name, value}``
        with optional ``comment``.
        """
        out: list[dict[str, Any]] = []
        for c in ir.constants:
            entry: dict[str, Any] = {"name": c.name, "value": c.value}
            if c.comment:
                entry["comment"] = markdown_normalize_headings(c.comment)
            out.append(entry)
        return out

    def _build_subroutines(self, ir) -> list[dict[str, Any]]:
        """``subroutines`` registered via
        :meth:`Disassembler.subroutine`. Each entry: ``addr`` (runtime),
        optional ``binary_addr``, optional ``name``, ``title``,
        ``description``, ``on_entry``, ``on_exit``, plus
        ``fall_through: True`` when the subroutine's last code item
        doesn't terminate control flow.

        Fall-through detection: walk forward to the next subroutine
        in the same move region, compare the previous item's mnemonic
        against ``RTS`` / ``JMP`` / ``BRK`` / ``RTI``; anything else
        is a fall-through.
        """
        items = self._build_items(ir)
        return self._build_subroutines_with_fall_through(ir, items)

    def _build_subroutines_with_fall_through(
        self, ir, items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        # Index code items by binary address (sorted), so the
        # fall-through walk can bisect to find the last item before
        # the NEXT subroutine.
        import bisect
        code_pairs = [
            (it.get("binary_addr", it["addr"]), it)
            for it in items if it.get("type") == "code"
        ]
        code_bas = [ba for ba, _ in code_pairs]

        # Group subs by move_id so fall-through only considers subs
        # in the SAME relocated region.
        by_move: dict[int | None, list[tuple[int, Any]]] = {}
        for sub in ir.subroutines:
            ba = sub.binary_addr
            if ba is None:
                continue
            by_move.setdefault(sub.move_id, []).append((int(ba), sub))
        for mid in by_move:
            by_move[mid].sort(key=lambda x: x[0])
        # Map each sub's runtime addr → next sub's binary addr in the
        # same move region (None for the last in the region).
        next_sub_ba: dict[int, int] = {}
        for group in by_move.values():
            for i in range(len(group) - 1):
                _, sub = group[i]
                next_ba, _ = group[i + 1]
                next_sub_ba[int(sub.runtime_addr)] = next_ba

        TERMINATORS = {"rts", "jmp", "brk", "rti"}
        result: list[dict[str, Any]] = []
        for sub in ir.subroutines:
            entry: dict[str, Any] = {"addr": int(sub.runtime_addr)}
            # Mirror the per-item convention: only surface
            # ``binary_addr`` when the subroutine is in a relocated
            # region (binary != runtime). Emitting it unconditionally
            # broke downstream consumers (e.g. the acornaeology site
            # generator) that join subroutine entries to per-address
            # items by ``(addr, binary_addr)`` — items omit it when
            # binary == runtime, so subs must too.
            if (
                sub.binary_addr is not None
                and int(sub.binary_addr) != int(sub.runtime_addr)
            ):
                entry["binary_addr"] = int(sub.binary_addr)
            if sub.name:
                entry["name"] = sub.name
            if sub.title:
                entry["title"] = markdown_normalize_headings(sub.title)
            if sub.description:
                entry["description"] = markdown_normalize_headings(
                    sub.description,
                )
            if sub.on_entry:
                entry["on_entry"] = {
                    reg: markdown_normalize_headings(text)
                    for reg, text in sub.on_entry.items()
                }
            if sub.on_exit:
                entry["on_exit"] = {
                    reg: markdown_normalize_headings(text)
                    for reg, text in sub.on_exit.items()
                }

            ra = int(sub.runtime_addr)
            ba = sub.binary_addr
            if ba is not None and ra in next_sub_ba and code_bas:
                lo = bisect.bisect_left(code_bas, int(ba))
                hi = bisect.bisect_left(code_bas, next_sub_ba[ra])
                if lo < hi:
                    last_item = code_pairs[hi - 1][1]
                    mnemonic = last_item["mnemonic"].lower()
                    if mnemonic not in TERMINATORS:
                        entry["fall_through"] = True
            result.append(entry)
        return result

    def _build_banners(self, ir) -> list[dict[str, Any]]:
        """Standalone ``Banner`` annotations — the dasmos analogue of
        py8dis's ``data_banner``: a visual section header for a data
        region, with no associated code-entry-point semantics.

        Lives in its own top-level array (parallel to ``subroutines``)
        so consumers can tell "subroutine entry point" from "data
        region with header". py8dis-fork conflates the two by putting
        ``data_banner`` entries in ``subroutines``; dasmos's locked
        design separates them (``feedback_critical_porting.md``), and
        the JSON schema reflects that.

        Each entry: ``{addr, [binary_addr], [name], [title],
        [description], [on_entry], [on_exit]}``. Banners attached as
        a side-effect of ``d.subroutine()`` are NOT included here —
        their data is already on the corresponding ``subroutines``
        entry.
        """
        # Addresses with a real subroutine — skip their internal Banner.
        sub_addrs: set[int] = {
            int(sub.binary_addr) for sub in ir.subroutines
            if sub.binary_addr is not None
        }

        result: list[dict[str, Any]] = []
        for binary_addr, anns in sorted(
            ir.annotations.items(), key=lambda kv: int(kv[0]),
        ):
            ba = int(binary_addr)
            if ba in sub_addrs:
                continue
            try:
                runtime_addr = int(ir.moves.b2r(BinaryAddr(ba)))
            except Exception:
                runtime_addr = ba
            for ann in anns:
                if not isinstance(ann, Banner):
                    continue
                entry: dict[str, Any] = {"addr": runtime_addr}
                if ba != runtime_addr:
                    entry["binary_addr"] = ba
                # If a label exists at this runtime address, take its
                # first explicit name as the banner's ``name``. Matches
                # py8dis's data_banner shape, where the second
                # positional arg becomes the entry's ``name``.
                # Insertion order picks the structural / first-
                # registered name (matches the asm renderer choice).
                label = ir.labels.get_label(runtime_addr)
                if label is not None:
                    names = label.explicit_names_in_insertion_order()
                    if names:
                        entry["name"] = names[0]
                if ann.title:
                    entry["title"] = markdown_normalize_headings(ann.title)
                if ann.description:
                    entry["description"] = markdown_normalize_headings(
                        ann.description,
                    )
                if ann.on_entry:
                    entry["on_entry"] = {
                        reg: markdown_normalize_headings(text)
                        for reg, text in ann.on_entry.items()
                    }
                if ann.on_exit:
                    entry["on_exit"] = {
                        reg: markdown_normalize_headings(text)
                        for reg, text in ann.on_exit.items()
                    }
                result.append(entry)
                # First banner per address wins; ignore extras.
                break
        return result

    def _build_external_labels(self, ir) -> dict[str, int]:
        """Labels whose runtime address has no loaded byte — OS entry
        points, hardware registers, etc.

        Returns ``{name: runtime_addr}`` (one entry per name; aliases
        each appear). Sorted by address then name for determinism.
        """
        result: dict[str, int] = {}
        entries: list[tuple[int, str]] = []
        for runtime_addr_obj, label in ir.labels.items():
            runtime_addr = int(runtime_addr_obj)
            if self._label_address_is_in_range(ir, runtime_addr):
                continue
            for name in sorted(label.explicit_name_texts()):
                entries.append((runtime_addr, name))
        entries.sort()
        for runtime_addr, name in entries:
            # First name wins for any collisions (deterministic).
            result.setdefault(name, runtime_addr)
        return result

    def _build_memory_map(self, ir) -> list[dict[str, Any]]:
        """Memory-map entries for outside-ROM labels carrying metadata
        (``description=`` / ``length=`` / ``group=`` / ``access=``).

        Includes any labelled, out-of-range address whose Label has
        at least one of those metadata fields set — a row authored
        purely with ``length`` / ``access`` and no narrative still
        belongs in the rendered memory map.
        """
        result: list[dict[str, Any]] = []
        for runtime_addr_obj, label in sorted(
            ir.labels.items(), key=lambda kv: int(kv[0]),
        ):
            runtime_addr = int(runtime_addr_obj)
            if self._label_address_is_in_range(ir, runtime_addr):
                continue
            has_metadata = (
                label.description
                or label.length is not None
                or label.group is not None
                or label.access is not None
            )
            if not has_metadata:
                continue
            names = label.explicit_names_in_insertion_order()
            if not names:
                continue
            entry: dict[str, Any] = {
                "addr": runtime_addr,
                "name": names[0],
            }
            if label.length is not None:
                entry["length"] = label.length
            if label.group is not None:
                entry["group"] = label.group
            if label.access is not None:
                entry["access"] = label.access
            if label.description:
                entry["description"] = label.description
            result.append(entry)
        return result

    def _build_items(self, ir) -> list[dict[str, Any]]:
        """Walk classifications in binary order; emit one entry per
        classification start.
        """
        items: list[dict[str, Any]] = []
        try:
            load_start, load_end = ir.memory.entire_load_range()
        except Exception:
            return items
        for binary_addr, classification in ir.classifications.iter_classified_starts():
            ba = int(binary_addr)
            if not (int(load_start) <= ba < int(load_end)):
                continue
            items.append(self._build_item(ir, ba, classification))
        return items

    # -- per-item rendering ---------------------------------------------

    def _build_item(self, ir, binary_addr: int, c) -> dict[str, Any]:
        runtime_addr = int(ir.moves.b2r(BinaryAddr(binary_addr)))
        length = c.length()
        raw_bytes = [
            ir.memory.get_u8(binary_addr + i) for i in range(length)
        ]

        entry: dict[str, Any] = {
            "addr": runtime_addr,
            "bytes": raw_bytes,
        }
        if binary_addr != runtime_addr:
            entry["binary_addr"] = binary_addr

        # Labels at the runtime address. Insertion order so the JSON
        # ``labels`` array matches the asm renderer's display sequence.
        label = ir.labels.get_label(runtime_addr)
        if label is not None:
            names = label.explicit_names_in_insertion_order()
            if names:
                entry["labels"] = names

        # Mid-instruction labels (sub-labels at addr+1..addr+length-1).
        sub_labels: dict[int, list[str]] = {}
        for off in range(1, length):
            inner_runtime = int(ir.moves.b2r(BinaryAddr(binary_addr + off)))
            inner_label = ir.labels.get_label(inner_runtime)
            if inner_label is None:
                continue
            inner_names = inner_label.explicit_names_in_insertion_order()
            if inner_names:
                sub_labels[inner_runtime] = inner_names
        if sub_labels:
            entry["sub_labels"] = sub_labels

        # ``comments_before`` is emitted in PER-BYTE-OFFSET order:
        # for each byte position within the classification, output
        # the annotations at that position, THEN the xref summary
        # for that position. This interleaves the xref for a sub-
        # label (e.g. ``language_handler_lo`` at offset 1 of a JMP)
        # with any annotations attached to the same offset, rather
        # than bulk-appending xrefs at the end.
        cb = self._build_comments_before(ir, binary_addr, length)
        if cb:
            entry["comments_before"] = cb
        # INLINE / AFTER annotations are bulk-aggregated since they
        # don't interleave with xref summaries.
        ci, ca = self._gather_inline_after(ir, binary_addr, length)
        if ci:
            entry["comment_inline"] = ci
        if ca:
            entry["comments_after"] = ca

        # Cross-references — runtime addrs that reference this label.
        if label is not None and label.references:
            refs = sorted({
                int(ir.moves.b2r(BinaryAddr(int(r.binary_addr))))
                for r in label.references
            })
            entry["references"] = refs

        # Classification-specific.
        if isinstance(c, Opcode):
            self._fill_code_fields(ir, binary_addr, c, entry)
        elif isinstance(c, String):
            entry["type"] = "string"
            entry["string"] = "".join(
                chr(b & 0x7f) if 32 <= (b & 0x7f) < 127 else "."
                for b in raw_bytes
            )
        elif isinstance(c, Word):
            entry["type"] = "word"
            entry["values"] = [
                raw_bytes[i] | (raw_bytes[i + 1] << 8)
                for i in range(0, length, 2)
            ]
            exprs = self._collect_expressions(ir, binary_addr, length, 2)
            if exprs:
                entry["expressions"] = exprs
            hints = self._collect_format_hints(ir, binary_addr, length, 2)
            if hints:
                entry["format_hints"] = hints
        elif isinstance(c, Fill):
            entry["type"] = "fill"
            entry["value"] = c.value()
            entry["length"] = length
        elif isinstance(c, Byte):
            entry["type"] = "byte"
            entry["values"] = list(raw_bytes)
            exprs = self._collect_expressions(ir, binary_addr, length, 1)
            if exprs:
                entry["expressions"] = exprs
            hints = self._collect_format_hints(ir, binary_addr, length, 1)
            if hints:
                entry["format_hints"] = hints

        return entry

    def _fill_code_fields(self, ir, binary_addr: int, opcode: Opcode, entry: dict) -> None:
        entry["type"] = "code"
        entry["mnemonic"] = opcode.default_mnemonic()
        operand = self._operand_text(ir, binary_addr, opcode)
        if operand is not None:
            entry["operand"] = operand
        # Surface any FormatHint registered at the operand byte as
        # structured metadata. Consumers (e.g. the acornaeology site
        # generator) get the abstract semantic alongside the rendered
        # text, so they can present their own visual representation
        # if desired (HTML char glyph, hex+decimal both, etc.).
        operand_addr = binary_addr + 1
        hint = ir.format_hints.get_or_none(operand_addr)
        if hint is not None:
            entry["format_hint"] = hint.value
        target = self._target_runtime(ir, binary_addr, opcode)
        if target is not None:
            entry["target"] = target
            target_label = ir.labels.get_label(target)
            if target_label is not None:
                # ``target_label`` carries the EXPLICIT name only —
                # expression aliases (``dispatch_0_hi-1``,
                # ``evntv+1``) are emitted in the ``operand`` text
                # but not as a target_label.
                name = self._first_explicit_name(target_label)
                if name is not None:
                    entry["target_label"] = name

    # -- helpers --------------------------------------------------------

    def _operand_text(self, ir, binary_addr: int, opcode: Opcode) -> str | None:
        """Reproduce the operand text that goes into the ``operand``
        field of a code item.

        Formatting:

        - Implied → no operand.
        - Accumulator → no operand (the bare ``lsr`` / ``ror`` /
          ``rol`` / ``asl`` mnemonic is unambiguous on the 6502).
        - Immediate values 0..9 → decimal (``#0``); 10..255 → hex
          (``#&7f``).
        - Index-register suffix is lowercase (``,y`` / ``,x``).
        - Address-style operands resolve to a label name when one
          exists, otherwise the hex literal.
        - Relative-branch arithmetic in runtime space.
        """
        mode = opcode.addressing_mode
        kind = mode.operand_kind
        operand_addr = binary_addr + 1
        mode_name = mode.name

        if mode_name == "IMPLIED":
            return None
        if mode_name == "ACCUMULATOR":
            # The bare ``lsr`` / ``ror`` / ``rol`` / ``asl`` mnemonic
            # is unambiguous on the 6502 — no implicit ``A`` operand.
            return None

        # User-supplied expression at the operand address takes
        # precedence (matches operand resolution in BeebasmRenderer).
        # Expression text doesn't carry mode-specific punctuation, so
        # we still apply the ``#`` prefix for immediate operands here.
        expr = ir.expressions.get_or_none(operand_addr)
        symbol: str
        if expr is not None:
            symbol = ("#" + expr) if kind is OperandKind.IMMEDIATE else expr
        elif kind is OperandKind.IMMEDIATE:
            value = ir.memory.get_u8(operand_addr)
            hint = ir.format_hints.get_or_none(operand_addr)
            if hint is not None:
                symbol = "#" + self._format_immediate_with_hint(
                    hint, value, operand_addr,
                )
            else:
                symbol = "#" + self._small_int(value)
        elif kind is OperandKind.ADDRESS_8:
            v = ir.memory.get_u8(operand_addr)
            symbol = self._addr_label_or_hex(ir, v, width=8)
        elif kind in (OperandKind.ADDRESS_16, OperandKind.ADDRESS_16_INDIRECT):
            v = ir.memory.get_u16_le(operand_addr)
            symbol = self._addr_label_or_hex(ir, v, width=16)
        elif kind is OperandKind.RELATIVE_OFFSET:
            offset = ir.memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            base_runtime = int(ir.moves.b2r(BinaryAddr(binary_addr)))
            target = base_runtime + opcode.length() + offset
            symbol = self._addr_label_or_hex(ir, target, width=16)
        else:
            return None

        # Mode-specific wrapping. Index-register letters are lowercase.
        if mode_name in ("ZERO_PAGE", "ABSOLUTE", "RELATIVE", "IMMEDIATE"):
            return symbol
        if mode_name in ("ZERO_PAGE_X", "ABSOLUTE_X"):
            return f"{symbol},x"
        if mode_name in ("ZERO_PAGE_Y", "ABSOLUTE_Y"):
            return f"{symbol},y"
        if mode_name == "INDIRECT":
            return f"({symbol})"
        if mode_name == "INDEXED_INDIRECT":
            return f"({symbol},x)"
        if mode_name == "INDIRECT_INDEXED":
            return f"({symbol}),y"
        if mode_name == "ZP_INDIRECT":
            return f"({symbol})"
        if mode_name == "ABSOLUTE_INDIRECT_X":
            return f"({symbol},x)"
        return symbol

    @staticmethod
    def _small_int(n: int) -> str:
        """Format a byte as a small-int operand: values 0-9 as decimal,
        10..255 as ``&xx`` hex.
        """
        if n < 10:
            return str(n)
        return f"&{n:02x}"

    def _format_immediate_with_hint(
        self, hint: FormatHint, value: int, operand_addr: int,
    ) -> str:
        """Translate a :class:`FormatHint` to JSON-renderer operand
        text (without the ``#`` prefix — the caller adds that).

        The JSON renderer's syntax is beebasm-flavoured (``&`` for
        hex, ``%`` for binary) so the rendered text reads naturally
        for the typical BBC/6502 audience and matches the asm output
        from the beebasm renderer at the same byte. Hints are
        best-effort: this dispatcher emits a ``UserWarning`` and
        falls back to a numeric form when the hint can't be
        expressed.
        """
        if hint is FormatHint.CHAR:
            text = self._render_char_for_explicit_hint(value)
            if text is not None:
                return text
            warnings.warn(
                f"FormatHint.CHAR at &{operand_addr:04x} can't be "
                f"expressed as a character literal for byte "
                f"&{value:02x} (non-printable); falling back to "
                f"a numeric literal.",
                stacklevel=2,
            )
            return self._small_int(value)
        if hint is FormatHint.DECIMAL:
            return str(value)
        if hint is FormatHint.HEX:
            return f"&{value:02x}"
        if hint is FormatHint.BINARY:
            return f"%{value:08b}"
        if hint is FormatHint.OCTAL:
            warnings.warn(
                f"FormatHint.OCTAL at &{operand_addr:04x} — JSON "
                f"renderer has no octal sigil; falling back to "
                f"decimal {value} (octal {value:o}). Consumers can "
                f"read the ``format_hint: \"octal\"`` field on the "
                f"item to render their own representation.",
                stacklevel=2,
            )
            return str(value)
        if hint is FormatHint.INKEY:
            return self._render_inkey_immediate(value, operand_addr)
        raise NotImplementedError(
            f"JsonRenderer doesn't yet handle FormatHint.{hint.name}"
        )

    def _render_inkey_immediate(self, value: int, operand_addr: int) -> str:
        """Translate :class:`FormatHint.INKEY` to the symbolic
        ``(255 - inkey_key_<name>) EOR 128`` form, mirroring the
        beebasm renderer (see its ``_render_inkey_immediate`` for
        the encoding rationale). The JSON ``format_hint`` field on
        the item still surfaces ``"inkey"`` so downstream consumers
        can render their own representation if they want.
        """
        from dasmos.ext.environments.acorn_mos.enums import INKEY_ENUM
        inkey_key = (255 - value) ^ 0x80
        name = INKEY_ENUM.get(inkey_key)
        if name is None:
            warnings.warn(
                f"FormatHint.INKEY at &{operand_addr:04x} — byte "
                f"&{value:02x} doesn't decode to a named BBC INKEY "
                f"scan code; falling back to a hex literal.",
                stacklevel=2,
            )
            return f"&{value:02x}"
        return f"(255 - {name}) EOR 128"

    @staticmethod
    def _render_char_for_explicit_hint(value: int) -> str | None:
        """Best-effort character-literal text for the JSON renderer.

        Uses the universal ``'c'`` form (works for nearly every
        printable byte). The double-quote (``0x22``) renders as
        ``'"'`` (single-quoted double-quote, unambiguous). The
        apostrophe (``0x27``) has no clean ``'c'`` form, so this
        method returns ``None`` for it (caller falls back to a
        numeric literal with a warning).

        Non-printable bytes also return ``None``.
        """
        if not (0x20 <= value <= 0x7E):
            return None
        if value == 0x27:
            return None
        return f"'{chr(value)}'"

    def _addr_label_or_hex(self, ir, addr: int, *, width: int) -> str:
        label = ir.labels.get_label(addr)
        if label is not None:
            name = self._first_registered_name(label)
            if name is not None:
                return name
        return f"&{addr:02x}" if width == 8 else f"&{addr:04x}"

    @staticmethod
    def _first_registered_name(label) -> str | None:
        """The first registered name (or expression alias) for this
        label, in insertion order across all move_ids. INSERTION order
        wins, not alphabetical.

        Falls back to expression text when no explicit name exists
        — this is how aliases like ``evntv+1`` (registered via
        ``expr_label`` because ``+`` isn't valid in a label
        identifier) get returned for operand resolution.
        """
        name = JsonRenderer._first_explicit_name(label)
        if name is not None:
            return name
        for expr_list in label.expressions.values():
            for expr in expr_list:
                return expr
        return None

    @staticmethod
    def _first_explicit_name(label) -> str | None:
        """The first EXPLICIT name (no expression aliases) for this
        label. Used for the ``target_label`` field, which cites real
        label names only — expression aliases are confined to the
        ``operand`` text.
        """
        for name_list in label.explicit_names.values():
            for explicit in name_list:
                return explicit.text
        return None

    def _target_runtime(self, ir, binary_addr: int, opcode: Opcode) -> int | None:
        """Compute the runtime address of an opcode's branch / address
        operand (the ``target`` field). ``None`` for no-target modes.
        """
        mode = opcode.addressing_mode
        kind = mode.operand_kind
        operand_addr = binary_addr + 1

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
            base_runtime = int(ir.moves.b2r(BinaryAddr(binary_addr)))
            return base_runtime + opcode.length() + offset
        return None

    def _collect_expressions(
        self, ir, binary_addr: int, length: int, element_size: int,
    ) -> list[str | None] | None:
        """List of expression strings parallel to the values, with
        ``None`` where no expression exists. Returns ``None`` when no
        element has an expression — the caller omits the
        ``expressions`` key entirely in that case.
        """
        out: list[str | None] = []
        has_any = False
        for i in range(0, length, element_size):
            e = ir.expressions.get_or_none(binary_addr + i)
            if e is not None:
                has_any = True
            out.append(e)
        return out if has_any else None

    def _collect_format_hints(
        self, ir, binary_addr: int, length: int, element_size: int,
    ) -> list[str | None] | None:
        """List of FormatHint values parallel to the item's values,
        with ``None`` where no hint is set. Returns ``None`` when no
        element has a hint — the caller omits the ``format_hints``
        key entirely in that case.

        Each populated entry is the hint's ``.value`` string —
        ``"binary"``, ``"hex"``, ``"decimal"``, ``"char"``,
        ``"inkey"``, or ``"octal"`` — so consumers can render the
        author-intended representation without re-deriving from the
        raw integer. The beebasm renderer uses the same hints in
        :meth:`BeebasmRenderer._render_byte` and
        ``_render_hinted_immediate``; surfacing them in JSON keeps
        the two output paths in lockstep.
        """
        out: list[str | None] = []
        has_any = False
        for i in range(0, length, element_size):
            hint = ir.format_hints.get_or_none(binary_addr + i)
            if hint is not None:
                has_any = True
                out.append(hint.value)
            else:
                out.append(None)
        return out if has_any else None

    def _build_comments_before(
        self, ir, binary_addr: int, length: int,
    ) -> list[str]:
        """Build the ``comments_before`` list, interleaving the
        xref summary for each byte offset with the annotations
        attached at that offset.

        For each byte position within the classification:

        1. ``BEFORE_LABEL`` annotations (banner separator + title +
           description, freeform comments registered with the
           default alignment).
        2. The xref summary for that byte (when the address has
           incoming references — this is the
           ``&xxxx referenced N times by …`` line).
        3. ``BEFORE_LINE`` annotations (line-aligned comments).
        """
        out: list[str] = []
        for i in range(length):
            byte_addr = binary_addr + i
            for ann in ir.annotations.get_for_align(byte_addr, Align.BEFORE_LABEL):
                out.extend(self._annotation_texts(ann))
            xref = self._format_xref_summary_text(ir, byte_addr, 1)
            if xref is not None:
                out.append(xref)
            for ann in ir.annotations.get_for_align(byte_addr, Align.BEFORE_LINE):
                out.extend(self._annotation_texts(ann))
        return out

    def _gather_inline_after(
        self, ir, binary_addr: int, length: int,
    ) -> tuple[str | None, list[str]]:
        """Bulk-aggregate the inline + after-{label,line} buckets.

        These don't interleave with xref summaries (xrefs appear
        BEFORE the item, not after), so the simpler bulk collection
        is correct for them. INLINE entries flatten to a single
        space-joined string; AFTER_* entries become a flat list.
        """
        inline: str | None = None
        after: list[str] = []
        for i in range(length):
            byte_addr = binary_addr + i
            for ann in ir.annotations.get_for_align(byte_addr, Align.INLINE):
                text = self._annotation_text(ann)
                if not text:
                    continue
                inline = text if inline is None else f"{inline} {text}"
            for ann in ir.annotations.get_for_align(byte_addr, Align.AFTER_LABEL):
                after.extend(self._annotation_texts(ann))
            for ann in ir.annotations.get_for_align(byte_addr, Align.AFTER_LINE):
                after.extend(self._annotation_texts(ann))
        return inline, after

    # Banner separator (87 ``*`` characters) — emitted as a
    # comments_before entry preceding the title/description.
    _BANNER_SEPARATOR = "*" * 87

    def _annotation_texts(self, ann) -> list[str]:
        """Render an annotation as one or more comments_before entries.

        A Banner becomes [separator, body], where body joins:

        - The title (if any).
        - The description (if any).
        - The ``On Entry:`` block (if ``on_entry`` non-empty),
          one ``    <REG>: <desc>`` line per entry.
        - The ``On Exit:`` block (if ``on_exit`` non-empty), same
          format.

        Each section is separated by ``\\n\\n`` so the rendering is
        emitted as a single comments_before entry. Comments and bare
        Annotations each become a single entry.
        """
        if isinstance(ann, Banner):
            out = [self._BANNER_SEPARATOR]
            parts = []
            if ann.title:
                parts.append(markdown_normalize_headings(ann.title))
            if ann.description:
                parts.append(markdown_normalize_headings(ann.description))
            if ann.on_entry:
                parts.append(self._format_register_block("On Entry", ann.on_entry))
            if ann.on_exit:
                parts.append(self._format_register_block("On Exit", ann.on_exit))
            if parts:
                out.append("\n\n".join(parts))
            return out
        if isinstance(ann, Comment):
            return [markdown_normalize_headings(ann.text)]
        if isinstance(ann, Annotation):
            return [markdown_normalize_headings(ann.text)]
        return []

    @staticmethod
    def _format_register_block(label: str, mapping: dict[str, str]) -> str:
        """Format a single ``On Entry:`` / ``On Exit:`` block for the
        banner body. Layout: header line, then one
        ``    <REG>: <description>`` line per dict entry. Register
        names are uppercased on output regardless of the case the
        driver registered them in.
        """
        lines = [f"{label}:"]
        for reg, desc in mapping.items():
            lines.append(f"    {reg.upper()}: {markdown_normalize_headings(desc)}")
        return "\n".join(lines)

    @staticmethod
    def _annotation_text(ann) -> str:
        # Legacy single-text accessor, kept only for the inline
        # path which doesn't accept multi-line entries (used by
        # ``_gather_annotations`` for INLINE bucket).
        if isinstance(ann, Comment):
            return markdown_normalize_headings(ann.text)
        if isinstance(ann, Banner):
            parts = []
            if ann.title:
                parts.append(markdown_normalize_headings(ann.title))
            if ann.description:
                parts.append(markdown_normalize_headings(ann.description))
            return " ".join(parts)
        if isinstance(ann, Annotation):
            return markdown_normalize_headings(ann.text)
        return ""

    @staticmethod
    def _format_xref_summary_text(ir, binary_addr: int, length: int) -> str | None:
        """Build the ``&<addr> referenced N time(s) by &<r1>, ...``
        text emitted as a comments_before entry on every labelled item
        with incoming references.

        - The cited address is the BINARY address of the item.
        - Each ref is emitted as the RUNTIME address of the JSR/branch
          via that ref's specific ``move_id``, with a ``[<move_id>]``
          suffix when the move id is non-zero (so a ref from inside a
          relocated region reads as ``&0030[1]``, not ``&933e``).
        """
        runtime_addr = int(ir.moves.b2r(BinaryAddr(binary_addr)))
        label = ir.labels.get_label(runtime_addr)
        if label is None or not label.references:
            return None
        # Collect unique (ref_runtime, move_id) pairs.
        seen: list[tuple[int, int]] = []
        seen_set: set[tuple[int, int]] = set()
        for ref in label.references:
            ba = int(ref.binary_addr)
            mid = int(getattr(ref, "move_id", 0) or 0)
            move_def = ir.moves.all_moves[mid]
            ref_runtime = int(
                move_def.convert_binary_to_runtime_addr(BinaryAddr(ba))
            )
            key = (ref_runtime, mid)
            if key not in seen_set:
                seen_set.add(key)
                seen.append(key)
        seen.sort()
        if not seen:
            return None
        count = len(seen)
        word = "time" if count == 1 else "times"
        parts = []
        for ref_runtime, mid in seen:
            if mid:
                parts.append(f"&{ref_runtime:04x}[{mid}]")
            else:
                parts.append(f"&{ref_runtime:04x}")
        return (
            f"&{binary_addr:04x} referenced {count} {word} by "
            + ", ".join(parts)
        )

    @staticmethod
    def _label_address_is_in_range(ir, runtime_addr: int) -> bool:
        """True iff the runtime address has a loaded byte (directly or
        via a move)."""
        binary_addr, _ = ir.moves.r2b(RuntimeAddr(runtime_addr))
        if binary_addr is None:
            return False
        return ir.memory.is_loaded(int(binary_addr))
