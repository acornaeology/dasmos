"""JSON structured-output renderer for dasmos.

Emits a JSON-serialisable dictionary:

.. code-block:: python

    {
      # schema_version bumps on every breaking shape change; absent in
      # docs from dasmos <= 1.14.0 (treat as 1: references were [int]).
      # ``title`` / ``description`` are the optional provenance header
      # (Disassembler.set_file_header) — additive, present only when set.
      "meta": {"schema_version": int, "load_addr": int, "end_addr": int,
               "title": str?, "description": str?},
      "constants": [{"name": str, "value": int, "comment": str?}, ...],
      "macros": [{"name": str, "params": [str, ...], "emit": str,
                  "body": {"text": str, "tree": <expr>}}, ...],
      "subroutines": [{"addr": int, "name": str?, ..., "fall_through": True?,
                       "align": "before_label"|...?}],
      # banners[] carries each Banner annotation as its own record;
      # multiple records may share an addr when the driver / env
      # attaches more than one banner at the same address with
      # different alignments (e.g. acorn_sideways_rom emits a
      # before_label section header AND an after_label bit-decode
      # banner at &8006).
      "banners": [{"addr": int, "title": str?, "description": str?,
                   "align": "before_label"|"after_label"|"before_line"|"after_line", ...}],
      "external_labels": {"name": int, ...},
      # Out-of-load-range labels carrying map metadata. ``access`` is an
      # ordered subset of ["r","w","b"] (read / write / indexing base) —
      # r/w are author-declared, b is derived from indexed references (or
      # author-asserted via d.index_base). A ["b"]-only row is an indexing
      # base: documented in place, but the literal byte is never touched.
      "memory_map": [{"addr": int, "name": str, "length": int?,
                      "group": str?, "access": ["r"|"w"|"b", ...]?, ...}],
      # Author-declared indexing regions (d.index_region): in-window
      # neighbours of the anchor render as anchor±k / named slots.
      "regions": [{"anchor": int, "name": str, "window": [lo, hi],
                   "named_slots": bool, ...}],
      "items": [
        {
          "addr": int,             # runtime_addr
          "bytes": [int, ...],
          "binary_addr": int?,     # only if differs from runtime_addr
          "labels": [str, ...]?,
          "sub_labels": {addr: [str, ...]}?,
          # Per-align comment buckets — full Align distinction
          # preserved (#16). Each list is per-byte-offset order.
          "comments_before_label": [str, ...]?,
          "comments_after_label":  [str, ...]?,
          "comments_before_line":  [str, ...]?,
          "comments_after_line":   [str, ...]?,
          "comment_inline":        str?,
          # Auto-generated cross-reference summary (one entry per
          # labelled byte address with incoming references), kept
          # separate from user comments (#16).
          "xref_summaries": [str, ...]?,
          # Structured incoming references: caller runtime addr, its
          # ReferenceKind (direct/pointer/indexed/indexed_pointer), and
          # move_id when non-zero. xref_summaries is prose derived from
          # this same data.
          "references": [{"addr": int, "kind": str, "move_id": int?}, ...]?,
          "type": "code"|"string"|"word"|"fill"|"byte",
          # type-specific: mnemonic/operand/target/target_label,
          #                values/expressions, value/length, string,
          #                format_hints, format_hint
          #
          # A driver-authored operand/data expression is emitted as an
          # object carrying BOTH a ready text rendering and a structured
          # tree, so a consumer can use the text directly or build its
          # own from the tree:
          #   {"text": str,
          #    "tree": <expr>}
          # where <expr> is one of:
          #   {"int": int, "radix": "auto"|"dec"|"hex"|"bin"|"char"}
          #   {"sym": str}                       # bare name
          #   {"ref": int, "name": str|null}     # label at a runtime addr
          #   {"raw": str}                       # unparsed dialect string
          #   {"str": str}                       # string literal
          #   {"op": "str_index", "string": <expr>, "index": <expr>}
          #   {"op": "str_slice", "string": <expr>,
          #    "start": <expr>, "stop": <expr>|null}
          #   {"op": "str_len", "string": <expr>}
          #   {"param": str}                     # macro formal parameter
          #   {"macro_call": str, "args": [<expr>, ...]}
          #   {"group": <expr>}                  # explicit parentheses
          #   {"op": "lowbyte"|"highbyte"|"neg"|"pos"|"invert"|"bankbyte",
          #    "operand": <expr>}
          #   {"op": "add"|"sub"|"mul"|"div"|"mod"|"and"|"or"|"xor"|
          #          "shl"|"shr",
          #    "left": <expr>, "right": <expr>}
          # Code items carry it as "expr" (operand keeps the full text
          # incl. #/,X); word/byte items as the "expressions" array
          # (element null where no expression at that value).
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
    canonical_text,
)
from dasmos.core.format_hint import FormatHint
from dasmos.core.markdown_asm import markdown_normalize_headings
from dasmos.core.memory import BinaryAddr, RuntimeAddr
from dasmos.cpu import Opcode, OperandKind
from dasmos.output import StructuredOutput
from dasmos.renderer import Renderer

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


#: Version of the JSON output schema, emitted as ``meta.schema_version``.
#: Bumped on every breaking change to the shape so consumers can branch.
#: Any breaking change to the emitted JSON MUST bump this — a consumer's
#: version gate is only as reliable as this number.
#:
#: History:
#:
#: - *(absent)* — pre-versioning schema through dasmos 1.14.0;
#:   ``references`` was a bare ``[int]`` list.
#: - ``2`` — ``references`` became structured objects
#:   (``{addr, kind, move_id?}``); ``expressions[i]`` was a plain
#:   *string*; no ``macros`` section.
#: - ``3`` — driver expressions became assembler-neutral trees:
#:   ``expressions[i]`` is now an OBJECT ``{"text", "tree"}`` (breaking),
#:   code items gained an ``expr`` object, and a top-level ``macros``
#:   section was added. See ``docs/design/json-schema-v3.md``.
#: - ``4`` — memory access became orthogonal R/W/B flags: a map entry's
#:   ``access`` is now an ordered ARRAY subset of ``["r", "w", "b"]``
#:   (was a scalar ``"r"``/``"w"``/``"rw"`` string), and the separate
#:   top-level ``index_bases`` array was folded back into ``memory_map``
#:   (bases are ordinary rows carrying ``b`` in ``access``). See
#:   ``docs/design/json-schema-v4.md``.
JSON_SCHEMA_VERSION = 4


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
            "macros": self._build_macros(ir),
            "subroutines": self._build_subroutines(ir),
            "banners": self._build_banners(ir),
            "external_labels": self._build_external_labels(ir),
            "memory_map": self._build_memory_map(ir),
            "regions": self._build_regions(ir),
            "items": self._build_items(ir),
        }
        return StructuredOutput(data, indent=self._indent)

    # -- top-level sections ---------------------------------------------

    def _build_macros(self, ir) -> list[dict]:
        """Driver-defined macros: name, parameter names, the emitted data
        kind, and the body as both ready text and a structured tree
        (parameters appear as ``{"param": name}`` leaves)."""
        out = []
        for macro in ir.macros.values():
            out.append({
                "name": macro.name,
                "params": list(macro.params),
                "emit": macro.emit,
                "body": {
                    "text": self._expr_text(macro.body, ir),
                    "tree": self._expr_tree(macro.body, ir),
                },
            })
        return out

    def _build_meta(self, ir) -> dict[str, Any]:
        try:
            start, end = ir.memory.entire_load_range()
        except Exception:
            start, end = 0, 0
        meta: dict[str, Any] = {
            "schema_version": JSON_SCHEMA_VERSION,
            "load_addr": int(start),
            "end_addr": int(end),
        }
        # Provenance header (see Disassembler.set_file_header) — additive,
        # optional keys; absent when the driver set no header. The
        # description keeps its source Markdown verbatim, like comments.
        header = ir.file_header
        if header is not None and not header.is_empty():
            if header.title:
                meta["title"] = header.title
            if header.description:
                meta["description"] = header.description
        # Load-and-run program metadata (see Disassembler.program) —
        # additive, optional keys; present only when the driver declared
        # exec/reload/load addresses. Each declared address is surfaced
        # under ``meta.program`` so a consumer can reproduce the DFS
        # header a beebasm ``save`` would carry.
        program = ir.program
        if program is not None:
            declared = {
                key: value
                for key, value in (
                    ("load_addr", program.load_addr),
                    ("exec_addr", program.exec_addr),
                    ("reload_addr", program.reload_addr),
                )
                if value is not None
            }
            if declared:
                meta["program"] = declared
        return meta

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
                # Surface the banner's align so consumers can render
                # at the correct visual position (#16). Lowercase
                # enum value matching the format_hints convention.
                entry["align"] = ann.align.value
                result.append(entry)
                # All banners at the address are emitted (#18); each
                # carries its own align field so consumers can place
                # them around the labelled byte without losing the
                # ones at non-default alignments. The asm renderer
                # already emits all of them; the JSON path used to
                # ``break`` here and lose every banner past the first.
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

        Indexing bases live here too, as ordinary rows carrying ``b`` in
        their ``access`` array (a ``["b"]``-only row is a base: the
        literal byte is never touched, only indexed through). The ``b``
        flag — not physical removal from the map — is how the model says
        "this byte isn't owned", so a base can sit in place within the
        surrounding workspace/ZP layout.
        """
        return self._collect_map_rows(ir)

    def _build_regions(self, ir) -> list[dict[str, Any]]:
        """Indexing regions declared via ``d.index_region()`` — one row
        per region documenting its anchor, name, offset window, and the
        naming style used for in-window gaps."""
        result: list[dict[str, Any]] = []
        for region in ir.index_regions:
            entry: dict[str, Any] = {
                "anchor": region.anchor_addr,
                "name": region.name,
                "window": [region.lo, region.hi],
                "named_slots": region.named_slots,
            }
            if region.group is not None:
                entry["group"] = region.group
            if region.description:
                entry["description"] = region.description
            result.append(entry)
        return result

    def _collect_map_rows(self, ir) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        ungrouped: list[tuple[int, str]] = []
        for runtime_addr_obj, label in sorted(
            ir.labels.items(), key=lambda kv: int(kv[0]),
        ):
            runtime_addr = int(runtime_addr_obj)
            if self._label_address_is_in_range(ir, runtime_addr):
                continue
            # Only author-supplied metadata puts an address on the map;
            # a bare indexing base with no metadata (b derived purely
            # from its references) stays off it, as before.
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
            else:
                ungrouped.append((runtime_addr, names[0]))
            access = label.access_flags()
            if access:
                entry["access"] = access
            if label.description:
                entry["description"] = label.description
            result.append(entry)
        self._warn_ungrouped_map_entries(ungrouped)
        return result

    @staticmethod
    def _warn_ungrouped_map_entries(ungrouped: list[tuple[int, str]]) -> None:
        """Interim aid for the #43 group audit: a memory-map row with no
        ``group=`` can't sit in place within the surrounding
        workspace/ZP layout (schema v4 folds indexing bases into
        ``memory_map``, so bases need grouping like everything else).

        Emit one consolidated ``UserWarning`` naming the offending
        addresses rather than one per row, so a driver with many bare
        entries produces a single actionable message. This is a
        stop-gap; the full fix is per-driver ``group=`` annotation
        (dasmos#43).
        """
        if not ungrouped:
            return
        listed = ", ".join(f"{name} (&{addr:04x})" for addr, name in ungrouped)
        count = len(ungrouped)
        subject = (
            "1 memory-map entry lacks"
            if count == 1
            else f"{count} memory-map entries lack"
        )
        warnings.warn(
            f"{subject} a group= and cannot be placed within the "
            f"surrounding memory layout: {listed}. Add group= to each "
            f"(see dasmos#43).",
            stacklevel=2,
        )

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

        # Per-item comment fields preserve dasmos's full 5-way
        # ``Align`` distinction (#16). Each align bucket gets its own
        # field; consumers read the right one and render at the
        # corresponding visual position. ``comment_inline`` stays
        # singular (always one trailing comment per line in beebasm).
        # The xref summary (auto-generated, not user-authored) lives
        # in its own ``xref_summaries`` field rather than being mixed
        # into a comment list.
        cb_label, ca_label, cb_line, ca_line = self._build_comments_split(
            ir, binary_addr, length,
        )
        if cb_label:
            entry["comments_before_label"] = cb_label
        if ca_label:
            entry["comments_after_label"] = ca_label
        if cb_line:
            entry["comments_before_line"] = cb_line
        if ca_line:
            entry["comments_after_line"] = ca_line
        ci = self._gather_inline(ir, binary_addr, length)
        if ci:
            entry["comment_inline"] = ci
        decoded = self._gather_decoded(ir, binary_addr, length)
        if decoded:
            entry["decoded"] = decoded if len(decoded) > 1 else decoded[0]
        xrefs = self._build_xref_summaries(ir, binary_addr, length)
        if xrefs:
            entry["xref_summaries"] = xrefs

        # Cross-references — structured, per-reference: the caller's
        # runtime address, its ReferenceKind, and (when non-zero) the
        # move it runs under. Consumers read the kind straight from here
        # rather than parsing it out of the xref-summary prose.
        records = self._collect_reference_records(ir, binary_addr)
        if records:
            entry["references"] = [
                {
                    "addr": rt,
                    "kind": kind.value,
                    **({"move_id": mid} if mid else {}),
                }
                for rt, mid, kind in records
            ]

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
        # When the operand value came from a driver-registered
        # expression, also surface it structurally (text + tree) so a
        # consumer can re-render it to any assembler or evaluate it,
        # rather than parse the ``operand`` string. ``operand`` keeps the
        # full ready text (with ``#`` / ``,X`` mode punctuation); the
        # ``expr`` object carries just the expression.
        operand_expr = ir.expressions.get_or_none(binary_addr + 1)
        if operand_expr is not None:
            entry["expr"] = self._expr_object(operand_expr, ir)
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
            expr_text = self._expr_text(expr, ir)
            symbol = (
                ("#" + expr_text) if kind is OperandKind.IMMEDIATE
                else expr_text
            )
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
        printable byte). The two quote chars each have a blind spot in
        that form, covered by a cross-fallback that mirrors the beebasm
        renderer at the same byte (#30):

        - double-quote (``0x22``) renders as ``'"'`` (single-quoted,
          unambiguous);
        - apostrophe (``0x27``) has no clean ``'c'`` form, so it renders
          as ``ASC("'")`` — the same form the beebasm renderer emits.

        Only genuinely non-printable bytes return ``None`` (the caller
        then falls back to a numeric literal with a warning).
        """
        if not (0x20 <= value <= 0x7E):
            return None
        if value == 0x27:
            return f'ASC("{chr(value)}")'
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
                return canonical_text(expr)
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
    ) -> list[dict | None] | None:
        """List of expression objects (``{"text", "tree"}``) parallel to
        the values, with ``None`` where no expression exists. Returns
        ``None`` when no element has an expression — the caller omits the
        ``expressions`` key entirely in that case.
        """
        out: list[dict | None] = []
        has_any = False
        for i in range(0, length, element_size):
            e = ir.expressions.get_or_none(binary_addr + i)
            if e is not None:
                has_any = True
                out.append(self._expr_object(e, ir))
            else:
                out.append(None)
        return out if has_any else None

    #: Beebasm-flavoured operator precedence (higher binds tighter), used
    #: to parenthesise the JSON ``text`` rendering so it is unambiguous
    #: and re-parseable — not merely decorative. Mirrors the beebasm text
    #: renderer's table.
    _TEXT_ATOM_PREC = 1000
    _TEXT_BINARY_PREC = {
        BinOp.MUL: 6, BinOp.DIV: 6, BinOp.MOD: 6, BinOp.SHL: 6, BinOp.SHR: 6,
        BinOp.ADD: 5, BinOp.SUB: 5,
        BinOp.AND: 3, BinOp.OR: 2, BinOp.XOR: 2,
    }
    _TEXT_BINARY_TOKEN = {
        BinOp.ADD: "+", BinOp.SUB: "-", BinOp.MUL: "*", BinOp.DIV: "DIV",
        BinOp.MOD: "MOD", BinOp.AND: "AND", BinOp.OR: "OR", BinOp.XOR: "EOR",
        BinOp.SHL: "<<", BinOp.SHR: ">>",
    }

    def _expr_text(self, e: Expr, ir) -> str:
        """Render an :class:`~dasmos.core.expr.Expr` as JSON operand text.

        JSON keeps the historical beebasm-flavoured operand spelling
        (``&`` hex, ``AND``/``EOR``, ``DIV`` integer division, ``<(...)``
        byte-select). A :class:`~dasmos.core.expr.Raw` node — a legacy
        dialect string — is emitted verbatim. String operations keep the
        string visible (``"BRK"[0]``). Parentheses are inserted per
        operator precedence so the text is a faithful, re-parseable
        rendering (the structured ``tree`` remains authoritative).
        """
        return self._expr_text_prec(e, ir)[0]

    def _expr_text_prec(self, e: Expr, ir) -> tuple[str, int]:
        """``(text, precedence)`` for ``e`` — precedence is the top
        operator's, or :attr:`_TEXT_ATOM_PREC` for a leaf, so the caller
        knows whether to wrap it in parentheses."""
        atom = self._TEXT_ATOM_PREC
        if isinstance(e, Raw):
            return e.text, atom
        if isinstance(e, Param):
            return e.name, atom
        if isinstance(e, MacroCall):
            args = ", ".join(self._expr_text(a, ir) for a in e.args)
            return f"{e.name}({args})", atom
        if isinstance(e, Str):
            return f'"{e.text}"', atom
        if isinstance(e, StrIndex):
            return (
                f"{self._expr_text(e.string, ir)}[{self._expr_text(e.index, ir)}]",
                atom,
            )
        if isinstance(e, StrSlice):
            stop = "" if e.stop is None else self._expr_text(e.stop, ir)
            return (
                f"{self._expr_text(e.string, ir)}"
                f"[{self._expr_text(e.start, ir)}:{stop}]",
                atom,
            )
        if isinstance(e, StrLen):
            return f"len({self._expr_text(e.string, ir)})", atom
        if isinstance(e, Sym):
            return e.name, atom
        if isinstance(e, Ref):
            return self._addr_label_or_hex(ir, int(e.runtime_addr), width=16), atom
        if isinstance(e, Int):
            return self._expr_int_text(e), atom
        if isinstance(e, Group):
            return f"({self._expr_text(e.inner, ir)})", atom
        if isinstance(e, Unary):
            # Function-like (bracketed) forms: byte-selects, bitwise NOT
            # (beebasm-flavoured ``NOT(...)``), bank byte.
            _bracket = {
                UnaryOp.LOWBYTE: "<", UnaryOp.HIGHBYTE: ">",
                UnaryOp.INVERT: "NOT", UnaryOp.BANKBYTE: "^",
            }
            if e.op in _bracket:
                operand = (
                    e.operand.inner if isinstance(e.operand, Group)
                    else e.operand
                )
                inner = self._expr_text(operand, ir)
                return f"{_bracket[e.op]}({inner})", atom
            token = {UnaryOp.NEG: "-", UnaryOp.POS: "+"}[e.op]
            inner, inner_prec = self._expr_text_prec(e.operand, ir)
            if inner_prec < 8:
                inner = f"({inner})"
            return f"{token}{inner}", 8
        if isinstance(e, Binary):
            prec = self._TEXT_BINARY_PREC[e.op]
            left = self._text_child(e.left, ir, prec, right=False)
            right = self._text_child(e.right, ir, prec, right=True)
            return f"{left} {self._TEXT_BINARY_TOKEN[e.op]} {right}", prec
        raise TypeError(f"cannot render expression node {type(e).__name__}")

    def _text_child(self, child, ir, parent_prec: int, *, right: bool) -> str:
        text, child_prec = self._expr_text_prec(child, ir)
        needs = child_prec < parent_prec or (right and child_prec == parent_prec)
        return f"({text})" if needs else text

    @staticmethod
    def _expr_int_text(node: Int) -> str:
        v = node.value
        if node.radix is Radix.DEC:
            return str(v)
        if node.radix is Radix.HEX:
            return f"&{v:02x}" if v <= 0xFF else f"&{v:04x}"
        if node.radix is Radix.BIN:
            return f"%{v:08b}"
        if node.radix is Radix.CHAR and 0x20 <= v <= 0x7E:
            return f"'{chr(v)}'"
        # AUTO / CHAR fallback: small decimals bare, else hex.
        if 0 <= v <= 9:
            return str(v)
        return f"&{v:02x}" if v <= 0xFF else f"&{v:04x}"

    # -- structured expression serialisation ------------------------------

    _UNARY_OP_NAME = {
        UnaryOp.NEG: "neg", UnaryOp.POS: "pos", UnaryOp.INVERT: "invert",
        UnaryOp.LOWBYTE: "lowbyte", UnaryOp.HIGHBYTE: "highbyte",
        UnaryOp.BANKBYTE: "bankbyte",
    }
    _BINARY_OP_NAME = {
        BinOp.ADD: "add", BinOp.SUB: "sub", BinOp.MUL: "mul",
        BinOp.DIV: "div", BinOp.MOD: "mod", BinOp.AND: "and",
        BinOp.OR: "or", BinOp.XOR: "xor", BinOp.SHL: "shl", BinOp.SHR: "shr",
    }
    _RADIX_NAME = {
        Radix.AUTO: "auto", Radix.DEC: "dec", Radix.HEX: "hex",
        Radix.BIN: "bin", Radix.CHAR: "char",
    }

    def _expr_object(self, e: Expr, ir) -> dict:
        """An expression as a JSON object carrying both a ready-to-use
        ``text`` rendering and a ``tree`` a consumer can walk to build
        its own. Every operand/data expression is emitted this way so no
        consumer is forced to parse text, yet none has to walk the tree
        just to display something.
        """
        return {"text": self._expr_text(e, ir), "tree": self._expr_tree(e, ir)}

    def _expr_tree(self, e: Expr, ir) -> dict:
        """The structured form of ``e`` — a small tagged tree mirroring
        :mod:`dasmos.core.expr`. Leaves: ``{"int": v, "radix": r}``,
        ``{"sym": name}``, ``{"ref": addr, "name": name_or_null}``,
        ``{"raw": text}``, ``{"str": text}``. Composites carry an ``op``
        tag plus operands. String ops are preserved structurally so a
        consumer can render or fold them itself.
        """
        if isinstance(e, Raw):
            return {"raw": e.text}
        if isinstance(e, Param):
            return {"param": e.name}
        if isinstance(e, MacroCall):
            return {"macro_call": e.name,
                    "args": [self._expr_tree(a, ir) for a in e.args]}
        if isinstance(e, Str):
            return {"str": e.text}
        if isinstance(e, StrIndex):
            return {"op": "str_index",
                    "string": self._expr_tree(e.string, ir),
                    "index": self._expr_tree(e.index, ir)}
        if isinstance(e, StrSlice):
            return {"op": "str_slice",
                    "string": self._expr_tree(e.string, ir),
                    "start": self._expr_tree(e.start, ir),
                    "stop": None if e.stop is None else self._expr_tree(e.stop, ir)}
        if isinstance(e, StrLen):
            return {"op": "str_len", "string": self._expr_tree(e.string, ir)}
        if isinstance(e, Sym):
            return {"sym": e.name}
        if isinstance(e, Ref):
            addr = int(e.runtime_addr)
            label = ir.labels.get_label(addr)
            name = self._first_registered_name(label) if label else None
            return {"ref": addr, "name": name}
        if isinstance(e, Int):
            return {"int": e.value, "radix": self._RADIX_NAME[e.radix]}
        if isinstance(e, Group):
            return {"group": self._expr_tree(e.inner, ir)}
        if isinstance(e, Unary):
            return {
                "op": self._UNARY_OP_NAME[e.op],
                "operand": self._expr_tree(e.operand, ir),
            }
        if isinstance(e, Binary):
            return {
                "op": self._BINARY_OP_NAME[e.op],
                "left": self._expr_tree(e.left, ir),
                "right": self._expr_tree(e.right, ir),
            }
        raise TypeError(f"cannot serialise expression node {type(e).__name__}")

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

    def _build_comments_split(
        self, ir, binary_addr: int, length: int,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Build the four per-align comment lists for an item:
        ``(before_label, after_label, before_line, after_line)``.

        Each list is collected in PER-BYTE-OFFSET order: for each
        byte position within the classification, walk the matching
        align bucket. This preserves the cross-byte interleaving
        consumers may need to render mid-instruction labels' comments
        in the right local order.

        Banners are skipped at the leaf (per #15 — they belong only
        in the top-level ``banners[]`` / ``subroutines[]`` records).
        Auto-generated xref summaries are not included here either —
        those live in the dedicated ``xref_summaries`` field.
        """
        before_label: list[str] = []
        after_label: list[str] = []
        before_line: list[str] = []
        after_line: list[str] = []
        for i in range(length):
            byte_addr = binary_addr + i
            for ann in ir.annotations.get_for_align(byte_addr, Align.BEFORE_LABEL):
                before_label.extend(self._annotation_texts(ann))
            for ann in ir.annotations.get_for_align(byte_addr, Align.AFTER_LABEL):
                after_label.extend(self._annotation_texts(ann))
            for ann in ir.annotations.get_for_align(byte_addr, Align.BEFORE_LINE):
                before_line.extend(self._annotation_texts(ann))
            for ann in ir.annotations.get_for_align(byte_addr, Align.AFTER_LINE):
                after_line.extend(self._annotation_texts(ann))
        return before_label, after_label, before_line, after_line

    def _build_xref_summaries(
        self, ir, binary_addr: int, length: int,
    ) -> list[str]:
        """Auto-generated cross-reference summary text per labelled
        byte within the item — separate field from user comments
        (#16). One entry per byte address that has incoming
        references; format is ``"&XXXX referenced N times by &YY, …"``
        as built by :meth:`_format_xref_summary_text`.
        """
        out: list[str] = []
        for i in range(length):
            xref = self._format_xref_summary_text(ir, binary_addr + i, 1)
            if xref is not None:
                out.append(xref)
        return out

    def _gather_inline(
        self, ir, binary_addr: int, length: int,
    ) -> str | None:
        """Bulk-aggregate the INLINE bucket. Multiple inline
        annotations across the item's bytes flatten to a single
        space-joined string (asm convention: at most one inline
        comment per line, but env analysers may stack them).

        Decoded-value annotations (#27) are folded in here too (#28):
        their human display text — ``"<label> <text>  <note>"`` via
        :meth:`DecodedAnnotation.display_text` — is what the beebasm
        renderer shows inline, so a JSON consumer rendering the
        standard comment channels sees the same thing without having to
        special-case the structured ``decoded`` field (which is still
        emitted separately for programmatic use). Decoded pieces render
        before free-form inline comments, matching the beebasm order.
        """
        decoded_pieces: list[str] = []
        comment_pieces: list[str] = []
        for i in range(length):
            byte_addr = binary_addr + i
            for ann in ir.annotations.get_for_align(byte_addr, Align.INLINE):
                if isinstance(ann, DecodedAnnotation):
                    decoded_pieces.append(ann.display_text())
                    continue
                text = self._annotation_text(ann)
                if not text:
                    continue
                comment_pieces.append(text)
        pieces = decoded_pieces + comment_pieces
        return " ".join(pieces) if pieces else None

    def _gather_decoded(
        self, ir, binary_addr: int, length: int,
    ) -> list[dict]:
        """Collect decoded-value annotations (#27) across the item's
        bytes as structured records ``{type, text, value?, comment?}``.

        Surfaced as a first-class ``decoded`` field rather than folded
        into ``comment_inline`` — the whole point of a typed region is
        that downstream consumers get the typed value, not a string.
        ``value`` and ``comment`` are omitted when absent.
        """
        out: list[dict] = []
        for i in range(length):
            for ann in ir.annotations.get_for_align(
                binary_addr + i, Align.INLINE,
            ):
                if not isinstance(ann, DecodedAnnotation):
                    continue
                rec: dict = {
                    "type": ann.decoded.type_name,
                    "text": ann.decoded.text,
                }
                if ann.decoded.value is not None:
                    rec["value"] = ann.decoded.value
                if ann.comment:
                    rec["comment"] = ann.comment
                out.append(rec)
        return out

    def _annotation_texts(self, ann) -> list[str]:
        """Render an annotation as one or more comments_before /
        comments_after entries.

        Banners are deliberately skipped — they surface in the
        top-level :meth:`_build_banners` array (or in the
        ``subroutines[]`` array via
        :meth:`_build_subroutines_with_fall_through` for subroutine
        entries). Including them here too produced the duplication
        in #15 where the same Banner appeared as a structured record
        AND as a stringified separator+body in ``comments_*``,
        forcing downstream consumers to de-dupe by address. Comments
        and bare Annotations each become a single entry.
        """
        if isinstance(ann, Banner):
            return []
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
        # ``_gather_annotations`` for INLINE bucket). Banners are
        # skipped for the same reason as in ``_annotation_texts``
        # (#15) — they belong in the top-level ``banners[]`` array,
        # not in per-item comment fields.
        if isinstance(ann, Comment):
            return markdown_normalize_headings(ann.text)
        if isinstance(ann, Banner):
            return ""
        if isinstance(ann, Annotation):
            return markdown_normalize_headings(ann.text)
        return ""

    @staticmethod
    def _collect_reference_records(ir, binary_addr: int):
        """The single structured source of incoming references for the
        label at ``binary_addr``'s runtime address.

        Returns a sorted, deduplicated ``list[(ref_runtime_addr,
        move_id, ReferenceKind)]``. Each caller is resolved to a runtime
        address via *its own* ``move_id`` (so a ref from inside a
        relocated region reads as ``&0030[1]``, not ``&933e``). Both the
        machine-readable ``references`` field and the derived
        ``xref_summaries`` prose read from here, so the two can never
        drift.

        When a single caller/move reaches the target both directly and
        as an index base (two instructions resolving to the same runtime
        address under the same move), the touching kind wins — a genuine
        access is never masked by a base-only one.
        """
        runtime_addr = int(ir.moves.b2r(BinaryAddr(binary_addr)))
        label = ir.labels.get_label(runtime_addr)
        if label is None or not label.references:
            return []
        by_key: dict[tuple[int, int], "ReferenceKind"] = {}
        for ref in label.references:
            ba = int(ref.binary_addr)
            mid = int(getattr(ref, "move_id", 0) or 0)
            move_def = ir.moves.all_moves[mid]
            ref_runtime = int(
                move_def.convert_binary_to_runtime_addr(BinaryAddr(ba))
            )
            key = (ref_runtime, mid)
            existing = by_key.get(key)
            if existing is None or (
                not existing.touches_named_address
                and ref.kind.touches_named_address
            ):
                by_key[key] = ref.kind
        return [
            (rt, mid, kind) for (rt, mid), kind in sorted(by_key.items())
        ]

    @staticmethod
    def _format_xref_summary_text(ir, binary_addr: int, length: int) -> str | None:
        """Build the ``&<addr> referenced N time(s) by &<r1>, ...``
        text emitted as a comments_before entry on every labelled item
        with incoming references. Derived entirely from
        :meth:`_collect_reference_records`.

        - The cited address is the BINARY address of the item.
        - Each ref is the RUNTIME address of the caller via its specific
          ``move_id``, with a ``[<move_id>]`` suffix when non-zero.
        - Sites that use the address only as an indexing base are
          reported separately as "used as index base", so the text never
          implies a byte is read or written when it is not.
        """
        records = JsonRenderer._collect_reference_records(ir, binary_addr)
        if not records:
            return None
        # Records are deduped per (addr, move) with the touching kind
        # winning, so these two lists are disjoint by construction.
        touching = [
            (rt, mid) for rt, mid, kind in records
            if kind.touches_named_address
        ]
        base_only = [
            (rt, mid) for rt, mid, kind in records
            if not kind.touches_named_address
        ]

        def clause(verb: str, seen: list[tuple[int, int]]) -> str:
            count = len(seen)
            word = "time" if count == 1 else "times"
            parts = [
                f"&{rt:04x}[{mid}]" if mid else f"&{rt:04x}"
                for rt, mid in seen
            ]
            return f"{verb} {count} {word} by " + ", ".join(parts)

        clauses: list[str] = []
        if touching:
            clauses.append(clause("referenced", touching))
        if base_only:
            clauses.append(clause("used as index base", base_only))
        return f"&{binary_addr:04x} " + "; also ".join(clauses)

    @staticmethod
    def _label_address_is_in_range(ir, runtime_addr: int) -> bool:
        """True iff the runtime address has a loaded byte (directly or
        via a move)."""
        binary_addr, _ = ir.moves.r2b(RuntimeAddr(runtime_addr))
        if binary_addr is None:
            return False
        return ir.memory.is_loaded(int(binary_addr))
