"""Document-level file header (provenance prose).

A :class:`FileHeader` is optional, backend-agnostic prose a driver sets to
describe *what* a disassembly is and *where it came from* — title, and a
free-text description (source ROM, hashes, notes). It is emitted as a
comment block at the very top of an assembler listing (each renderer
supplies only its comment prefix), and surfaces in the JSON ``meta``.

dasmos holds only the text; it hardcodes no project-specific provenance,
so the header stays reusable across every disassembly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileHeader:
    """Provenance prose for the top of a listing.

    ``title`` is a single line; ``description`` is free-text (Markdown,
    like comments) that may span several lines. Either may be ``None``.
    """

    title: str | None = None
    description: str | None = None

    def is_empty(self) -> bool:
        return not (self.title or self.description)
