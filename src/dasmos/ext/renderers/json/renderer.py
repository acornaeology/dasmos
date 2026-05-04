"""JSON structured-output renderer for dasmos.

Emits a JSON-serialisable dictionary with the same schema as the
acornaeology py8dis fork's ``structured.py`` (``emit_structured()``):

.. code-block:: python

    {
      "meta": {"load_addr": int, "end_addr": int},
      "constants": [{"name": str, "value": int, "comment": str?}, ...],
      "subroutines": [{"addr": int, "name": str?, ..., "fall_through": True?}],
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

The schema mirror is deliberate so the parity test can deep-diff
dasmos output against the vendored py8dis snapshot for the same ROM
(see ``tests/test_nfs_roundtrip.py`` and the
``project_jsonrenderer_schema`` memory). Schema can evolve later
once py8dis-fork parity is achieved.

This renderer doesn't need the assembler-syntax protocol (no equ/
mnemonic/comment-prefix concerns), so it derives directly from
:class:`dasmos.renderer.Renderer` rather than ``TextRenderer``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dasmos.core.annotations import Align, Annotation, Banner, Comment
from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.memory import BinaryAddr, RuntimeAddr
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import StructuredOutput
from dasmos.renderer import Renderer

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


class JsonRenderer(Renderer[StructuredOutput]):
    """JSON structured-output renderer.

    Output keys match py8dis-fork's ``emit_structured()`` so the
    rendered dict can be diffed directly against py8dis output for
    the same ROM. See module docstring for the full schema.
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
        in driver-registration order. py8dis-fork schema: each entry
        is ``{name, value}`` with optional ``comment``.
        """
        out: list[dict[str, Any]] = []
        for c in ir.constants:
            entry: dict[str, Any] = {"name": c.name, "value": c.value}
            if c.comment:
                entry["comment"] = c.comment
            out.append(entry)
        return out

    def _build_subroutines(self, ir) -> list[dict[str, Any]]:
        """``subroutines`` registered via
        :meth:`Disassembler.subroutine`. Each entry mirrors the
        py8dis-fork schema: ``addr`` (runtime), optional ``binary_addr``,
        optional ``name``, ``title``, ``description``, ``on_entry``,
        ``on_exit``, plus ``fall_through: True`` when the subroutine's
        last code item doesn't terminate control flow.

        Fall-through detection mirrors py8dis: walk forward to the
        next subroutine in the same move region, compare the previous
        item's mnemonic against ``RTS``/``JMP``/``BRK``/``RTI``;
        anything else is a fall-through. The "ALWAYS branch" inline-
        comment heuristic py8dis uses is omitted here for now (it
        depends on optional cycle-count annotations dasmos doesn't
        yet emit).
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
            if sub.binary_addr is not None:
                entry["binary_addr"] = int(sub.binary_addr)
            if sub.name:
                entry["name"] = sub.name
            if sub.title:
                entry["title"] = sub.title
            if sub.description:
                entry["description"] = sub.description
            if sub.on_entry:
                entry["on_entry"] = dict(sub.on_entry)
            if sub.on_exit:
                entry["on_exit"] = dict(sub.on_exit)

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
        (``description=`` / future ``length=`` / ``group=`` / ``access=``).

        py8dis includes only labels that have at least one of
        description / length / group / access. dasmos labels currently
        carry only ``description``; the other three slots stay
        unpopulated until that infrastructure lands.
        """
        result: list[dict[str, Any]] = []
        for runtime_addr_obj, label in sorted(
            ir.labels.items(), key=lambda kv: int(kv[0]),
        ):
            runtime_addr = int(runtime_addr_obj)
            if self._label_address_is_in_range(ir, runtime_addr):
                continue
            if not label.description:
                continue
            names = sorted(label.explicit_name_texts())
            if not names:
                continue
            entry: dict[str, Any] = {
                "addr": runtime_addr,
                "name": names[0],
                "description": label.description,
            }
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

        # Labels at the runtime address.
        label = ir.labels.get_label(runtime_addr)
        if label is not None:
            names = sorted(label.explicit_name_texts())
            if names:
                entry["labels"] = names

        # Mid-instruction labels (sub-labels at addr+1..addr+length-1).
        sub_labels: dict[int, list[str]] = {}
        for off in range(1, length):
            inner_runtime = int(ir.moves.b2r(BinaryAddr(binary_addr + off)))
            inner_label = ir.labels.get_label(inner_runtime)
            if inner_label is None:
                continue
            inner_names = sorted(inner_label.explicit_name_texts())
            if inner_names:
                sub_labels[inner_runtime] = inner_names
        if sub_labels:
            entry["sub_labels"] = sub_labels

        # py8dis-fork emits comments_before in PER-BYTE-OFFSET order:
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

        return entry

    def _fill_code_fields(self, ir, binary_addr: int, opcode: Opcode, entry: dict) -> None:
        entry["type"] = "code"
        entry["mnemonic"] = opcode.default_mnemonic()
        operand = self._operand_text(ir, binary_addr, opcode)
        if operand is not None:
            entry["operand"] = operand
        target = self._target_runtime(ir, binary_addr, opcode)
        if target is not None:
            entry["target"] = target
            target_label = ir.labels.get_label(target)
            if target_label is not None:
                # ``target_label`` carries the EXPLICIT name only —
                # expression aliases (``dispatch_0_hi-1``,
                # ``evntv+1``) are emitted in the ``operand`` text
                # but not as a target_label per py8dis convention.
                name = self._first_explicit_name(target_label)
                if name is not None:
                    entry["target_label"] = name

    # -- helpers --------------------------------------------------------

    def _operand_text(self, ir, binary_addr: int, opcode: Opcode) -> str | None:
        """Reproduce the operand text py8dis-fork emits — used by the
        JSON parity oracle to diff against py8dis's structured output.

        Formatting matches py8dis exactly:

        - Implied → no operand.
        - Accumulator → ``A`` (uppercase, regardless of lower_case).
        - Immediate values 0..9 → decimal (``#0``); 10..255 → hex
          (``#&7f``). Mirrors py8dis ``mainformatter.uint_formatter``.
        - Index-register suffix is lowercase (``,y`` / ``,x``) — py8dis
          drivers run with ``lower_case=True``.
        - Address-style operands resolve to a label name when one
          exists, otherwise the hex literal.
        - Relative-branch arithmetic in runtime space (mirrors py8dis
          ``OpcodeConditionalBranch.target``).
        """
        mode = opcode.addressing_mode
        kind = mode.operand_kind
        operand_addr = binary_addr + 1
        mode_name = mode.name

        if mode_name == "IMPLIED":
            return None
        if mode_name == "ACCUMULATOR":
            # py8dis omits the implicit ``A`` operand entirely when
            # ``lower_case=True`` (its drivers' default) — the bare
            # ``lsr`` / ``ror`` / ``rol`` / ``asl`` mnemonic is
            # unambiguous on the 6502. Returning None keeps the JSON
            # diffable against py8dis output.
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
            symbol = "#" + self._small_int(ir.memory.get_u8(operand_addr))
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

        # Mode-specific wrapping. Index-register letters lowercase to
        # match py8dis (``lower_case=True`` on its drivers).
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
        """Mirror py8dis ``mainformatter.uint_formatter``: values 0-9
        as decimal, 10..255 as ``&xx`` hex.
        """
        if n < 10:
            return str(n)
        return f"&{n:02x}"

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
        label, in insertion order across all move_ids. Mirrors
        py8dis-fork's ``Label.get_already_emitted_name`` —
        INSERTION order wins, not alphabetical.

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
        label. Used for the ``target_label`` field where py8dis only
        cites real label names, not the expression aliases that show
        up in ``operand`` text.
        """
        for name_list in label.explicit_names.values():
            for explicit in name_list:
                return explicit.text
        return None

    def _target_runtime(self, ir, binary_addr: int, opcode: Opcode) -> int | None:
        """Compute the runtime address of an opcode's branch / address
        operand (the ``target`` field). ``None`` for no-target modes.
        Mirrors py8dis ``OpcodeXxx.target``.
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
        element has an expression (matches py8dis behaviour: omit the
        ``expressions`` key entirely if not used).
        """
        out: list[str | None] = []
        has_any = False
        for i in range(0, length, element_size):
            e = ir.expressions.get_or_none(binary_addr + i)
            if e is not None:
                has_any = True
            out.append(e)
        return out if has_any else None

    def _build_comments_before(
        self, ir, binary_addr: int, length: int,
    ) -> list[str]:
        """Build the ``comments_before`` list, interleaving the
        xref summary for each byte offset with the annotations
        attached at that offset (mirrors py8dis-fork ordering).

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

    # py8dis-style banner separator (87 ``*`` characters) — emitted
    # as a comments_before entry preceding the title/description so
    # the parity diff sees the same shape as py8dis output.
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

        Each section is separated by ``\\n\\n`` — mirroring
        py8dis-fork ``mainformatter`` so the parity test sees the
        same text as a single comments_before entry. Comments and
        bare Annotations each become a single entry.
        """
        if isinstance(ann, Banner):
            out = [self._BANNER_SEPARATOR]
            parts = []
            if ann.title:
                parts.append(ann.title)
            if ann.description:
                parts.append(ann.description)
            if ann.on_entry:
                parts.append(self._format_register_block("On Entry", ann.on_entry))
            if ann.on_exit:
                parts.append(self._format_register_block("On Exit", ann.on_exit))
            if parts:
                out.append("\n\n".join(parts))
            return out
        if isinstance(ann, Comment):
            return [ann.text]
        if isinstance(ann, Annotation):
            return [ann.text]
        return []

    @staticmethod
    def _format_register_block(label: str, mapping: dict[str, str]) -> str:
        """Format a single ``On Entry:`` / ``On Exit:`` block for the
        banner body. py8dis-fork format: header line, then one
        ``    <REG>: <description>`` line per dict entry. Register
        names are uppercased to match py8dis's convention (its
        drivers register lowercase keys but the formatter uppercases
        them on output).
        """
        lines = [f"{label}:"]
        for reg, desc in mapping.items():
            lines.append(f"    {reg.upper()}: {desc}")
        return "\n".join(lines)

    @staticmethod
    def _annotation_text(ann) -> str:
        # Legacy single-text accessor, kept only for the inline
        # path which doesn't accept multi-line entries (used by
        # ``_gather_annotations`` for INLINE bucket).
        if isinstance(ann, Comment):
            return ann.text
        if isinstance(ann, Banner):
            parts = []
            if ann.title:
                parts.append(ann.title)
            if ann.description:
                parts.append(ann.description)
            return " ".join(parts)
        if isinstance(ann, Annotation):
            return ann.text
        return ""

    @staticmethod
    def _format_xref_summary_text(ir, binary_addr: int, length: int) -> str | None:
        """Build the ``&<addr> referenced N time(s) by &<r1>, ...``
        text py8dis emits as a comments_before entry on every
        labelled item with incoming references. Mirrors py8dis
        ``mainformatter._format_xrefs`` exactly:

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
            move_def = ir.moves._move_definitions[mid]
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
