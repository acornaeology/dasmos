"""Comments and annotations attached to binary addresses.

A driver-script call like ``d.comment(addr, "text")`` deposits a
:class:`Comment` in an :class:`AnnotationStore`; the renderer reads
the store at render-time and emits each comment at the correct
position relative to the code line.

Per ``docs/design/decisions.md`` D-020, this is its own manager class
held by the :class:`~dasmos.disassembler.Disassembler` (alongside
:class:`MemoryImage`, :class:`MoveManager`, :class:`LabelManager`,
:class:`ClassificationStore`, …) — separate, focused, instance-scoped.

This first cut handles the load-bearing alignment positions that drive
the bulk of the surveyed driver scripts: ``BEFORE_LABEL`` (standalone
comment above the line), ``INLINE`` (trailing on the code line), and
``BEFORE_LINE`` / ``AFTER_LINE`` for vertical separation. ``Annotation``
is the verbatim sibling of :class:`Comment` for raw assembler-source
text the driver wants emitted.

Deferred from this first cut:

- Markdown-to-plaintext rendering of comment text — lands with the
  :mod:`markdown_asm` port (task #26).
- Word-wrapping of long standalone comments — the field is carried
  but unused; the renderer emits the text as given.
- Inline-comment column alignment — the renderer uses a fixed
  trailing offset for now.
- Per-move-id annotation discrimination — the store is indexed by
  bare :class:`BinaryAddr`; the move_id from the Disassembler call
  is honoured to resolve the address but not stored.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from dasmos.core.memory import BinaryAddr


class Align(Enum):
    """Where a comment or annotation appears relative to a line.

    The five positions match py8dis's convention so the porter has a
    1:1 mapping. Most driver-script calls use ``BEFORE_LABEL`` (the
    default) or ``INLINE``; the others are rarer.
    """

    BEFORE_LABEL = "before_label"
    """Standalone, above the line's labels and code."""

    AFTER_LABEL = "after_label"
    """Standalone, between the line's labels and the code."""

    BEFORE_LINE = "before_line"
    """Standalone, just above the code (after any labels)."""

    AFTER_LINE = "after_line"
    """Standalone, just below the code line."""

    INLINE = "inline"
    """Trailing on the same line as the code, after the operands."""


@dataclass
class Comment:
    """A user comment at a specific address.

    The text is stored verbatim; the renderer applies the assembler's
    comment prefix (``;`` for Beebasm) at render time.
    """

    text: str
    align: Align = Align.BEFORE_LABEL
    word_wrap: bool = True
    indent: int = 0
    auto_generated: bool = False
    priority: Optional[int] = None


@dataclass
class Annotation:
    """A raw assembler-source string at a specific address.

    Unlike :class:`Comment`, the text is emitted verbatim — no
    comment prefix is added. Use this for emitting assembler
    directives the driver wants inline (e.g. an explicit ``equb``).
    """

    text: str
    align: Align = Align.BEFORE_LABEL
    priority: Optional[int] = None


# Type alias for store entries.
Entry = Union[Comment, Annotation]


class AnnotationStore:
    """Per-disassembly registry of :class:`Comment` and
    :class:`Annotation` entries keyed by binary address.

    A single address can carry multiple entries; insertion order is
    preserved. The renderer is responsible for iterating entries in
    the right order and at the right rendering position.
    """

    def __init__(self):
        self._entries: dict[BinaryAddr, list[Entry]] = {}

    def add(self, binary_addr, entry: Entry) -> None:
        """Append ``entry`` at ``binary_addr``."""
        addr = self._key(binary_addr)
        self._entries.setdefault(addr, []).append(entry)

    def get(self, binary_addr) -> list[Entry]:
        """Return a list of entries at ``binary_addr`` (insertion order)."""
        addr = self._key(binary_addr)
        return list(self._entries.get(addr, []))

    def get_for_align(self, binary_addr, align: Align) -> list[Entry]:
        """Return entries at ``binary_addr`` whose alignment matches."""
        return [e for e in self.get(binary_addr) if e.align is align]

    def __contains__(self, binary_addr) -> bool:
        return self._key(binary_addr) in self._entries

    def __iter__(self):
        return iter(self._entries)

    def items(self):
        return self._entries.items()

    @staticmethod
    def _key(binary_addr) -> BinaryAddr:
        if isinstance(binary_addr, BinaryAddr):
            return binary_addr
        return BinaryAddr(int(binary_addr))
