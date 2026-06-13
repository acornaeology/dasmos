"""Pluggable custom data types.

A :class:`DataType` is a registrable, domain-specific interpretation of
a fixed-width run of bytes — e.g. the BBC BASIC packed 5-byte floating-
point format. It bundles two things:

- the type's **width** (how many bytes it spans), so a driver never has
  to repeat the length at the call site, and
- a **decoder** ``bytes -> DecodedValue`` producing a human-readable
  (and optionally structured) value.

The crucial design constraint is the byte-faithful round-trip oracle:
many domain types (the BBC 5-byte float is the motivating case — non-
IEEE, excess-128 exponent, implied leading 1) have *no* assembler
literal that re-assembles to the exact bytes. Fidelity therefore
*requires* emitting the raw bytes; the decoded value can only ever be
an **annotation** alongside them. So a typed region is always
classified as :class:`~dasmos.core.classification.Byte` for emission,
and the decoded value rides along as a
:class:`~dasmos.core.annotations.DecodedAnnotation`.

Decoding happens **eagerly**, when the driver (or an environment)
classifies the region — the bytes are in hand and we are already in
Python. Nothing is deferred to render time, so renderers need no
per-type knowledge, no registry lookup, and no fallback machinery: an
asm renderer emits the decoded text as an inline comment; the JSON
renderer surfaces it as a structured field. This is deliberately
*less* machinery than a render-time, renderer-overridable type plug-in
would need — the only renderer-specific decision (a native literal) is
moot when no literal round-trips.

Ownership mirrors the ``INKEY`` precedent: the decoder is contributed
by an environment (e.g. ``bbc_basic_6502`` registers ``bbc_float5``)
rather than living in core, so core stays machine-agnostic. A driver
can also pass a :class:`DataType` instance (or a bare callable plus an
explicit length) directly for a one-off, env-free decode.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DecodedValue:
    """The decoded interpretation of a typed-data region.

    - ``type_name`` names the data type (e.g. ``"bbc_float5"``); it is
      surfaced to readers so the listing says *what* the region is, not
      just its value.
    - ``text`` is the human-readable form an asm renderer emits as an
      inline comment (e.g. ``"2.718281828"``).
    - ``value`` is an optional JSON-serialisable structured value (e.g.
      the ``float`` itself) the JSON renderer surfaces alongside the
      text, so downstream consumers get the typed value, not just a
      string.
    """

    type_name: str
    text: str
    value: Optional[Any] = None


class DataType(ABC):
    """A registrable, fixed-width custom data type.

    Subclasses declare a :attr:`name` and :attr:`length` and implement
    :meth:`decode`. Because the type owns its width, a driver calls
    ``d.typed_data(addr, "bbc_float5")`` with no length argument — the
    width is implied by the type (see
    :meth:`~dasmos.disassembler.Disassembler.typed_data`).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The type's registry name (e.g. ``"bbc_float5"``)."""

    @property
    @abstractmethod
    def length(self) -> int:
        """The fixed number of bytes a value of this type spans."""

    @abstractmethod
    def decode(self, raw: bytes) -> DecodedValue:
        """Decode ``raw`` (exactly :attr:`length` bytes) into a
        :class:`DecodedValue`. The bytes are never mutated — decoding
        is read-only, so the round-trip oracle is unaffected.
        """
