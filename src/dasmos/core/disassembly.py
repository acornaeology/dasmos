"""Per-binary-address classification storage.

The disassembly process is fundamentally about deciding, for each
binary byte, what kind of thing it is — code, raw data, a string, a
fill, etc. The :class:`ClassificationStore` is the registry that
records those decisions.

A classification has a length in bytes; the first byte holds the
:class:`~dasmos.core.classification.Classification` object and the
remaining bytes are marked with the sentinel
:data:`INSIDE_A_CLASSIFICATION` so the store knows they have been
spoken for.

Design points:

- The :data:`INSIDE_A_CLASSIFICATION` sentinel is a proper
  ``object()`` rather than a magic integer. ``is`` comparisons are
  unambiguous; the type checker can also see the discriminator.
- All state lives on a :class:`ClassificationStore` instance — no
  module-level 64K ``classifications`` list. Two stores coexist.
- The store is dict-backed rather than list-backed, which scales
  gracefully when 32-bit CPUs land. Random access is still O(1).
- :meth:`ClassificationStore.add_classification` raises
  :class:`ClassificationError` on overlap rather than asserting.
- :meth:`ClassificationStore.split_at` replaces the original
  classification with two :class:`Byte` classifications when split
  in the interior; no-op at start, end, or on an unclassified
  address.
"""

from typing import Iterator

from dasmos.core.classification import Byte, Classification
from dasmos.core.memory import BinaryAddr
from dasmos.exceptions import DasmosError


class ClassificationError(DasmosError):
    """Raised on invalid classification operations (e.g. overlap)."""


# Sentinel marking a byte that is the second-or-later byte of an
# existing multi-byte classification. ``object()`` gives us a
# guaranteed-unique value so ``is`` comparisons are safe.
INSIDE_A_CLASSIFICATION = object()


class ClassificationStore:
    """Per-disassembly registry of which bytes have been classified
    and how.

    Three states for any given binary address:

    - ``None`` (or unset) — the byte has no classification yet.
    - :data:`INSIDE_A_CLASSIFICATION` — the byte is part of an
      existing multi-byte classification that started at an earlier
      address.
    - a :class:`~dasmos.core.classification.Classification` instance —
      this byte is the *start* of a classification of that type and
      length.
    """

    def __init__(self):
        self._classifications: dict[int, Classification | object] = {}

    def add_classification(self, binary_addr, classification: Classification) -> None:
        """Record a classification starting at ``binary_addr``.

        Raises :class:`ClassificationError` if any byte in the
        classification's range is already classified.
        """
        binary_addr = int(BinaryAddr(binary_addr))
        length = classification.length()
        if self.is_classified(binary_addr, length=length):
            raise ClassificationError(
                f"Binary address 0x{binary_addr:x} (length {length}) is "
                f"already classified — would overlap an existing entry"
            )
        self._classifications[binary_addr] = classification
        for i in range(1, length):
            self._classifications[binary_addr + i] = INSIDE_A_CLASSIFICATION

    def is_classified(self, binary_addr, length: int = 1) -> bool:
        """True iff *any* byte in the range is classified."""
        binary_addr = int(BinaryAddr(binary_addr))
        for i in range(length):
            if (binary_addr + i) in self._classifications:
                return True
        return False

    def get_classification(self, binary_addr):
        """Return the value stored at ``binary_addr``.

        Returns ``None`` if unset, the sentinel
        :data:`INSIDE_A_CLASSIFICATION` if this byte is the
        second-or-later byte of an existing classification, or the
        :class:`Classification` object itself if this byte is the start.
        """
        return self._classifications.get(int(BinaryAddr(binary_addr)))

    def iter_classified_starts(self) -> Iterator[tuple[BinaryAddr, Classification]]:
        """Yield ``(addr, classification)`` for each *start* address,
        sorted by address. Inside-marker bytes are skipped.
        """
        for addr_int in sorted(self._classifications):
            value = self._classifications[addr_int]
            if isinstance(value, Classification):
                yield BinaryAddr(addr_int), value

    def split_at(self, binary_addr) -> None:
        """If ``binary_addr`` falls in the interior of an existing
        multi-byte classification, replace the original with two
        :class:`Byte` classifications (a left half ending just before
        ``binary_addr`` and a right half starting at ``binary_addr``).

        No-op if ``binary_addr`` is unclassified, is the start of an
        existing classification, or is one-past-the-end.

        The replacement is always Byte regardless of the original
        type. Used at move boundaries where exact type preservation
        is unimportant because the underlying bytes are unchanged.
        """
        binary_addr_int = int(BinaryAddr(binary_addr))
        value = self._classifications.get(binary_addr_int)
        if value is not INSIDE_A_CLASSIFICATION:
            # Either unclassified, the start of a classification, or
            # one-past-the-end — none of these need splitting.
            return

        # Walk back to the start of the classification.
        start_int = binary_addr_int
        while self._classifications.get(start_int) is INSIDE_A_CLASSIFICATION:
            start_int -= 1
            if start_int < 0:
                raise ClassificationError(
                    "INSIDE marker at 0 with no preceding start — store is corrupt"
                )

        original = self._classifications[start_int]
        original_length = original.length()
        first_split_length = binary_addr_int - start_int
        second_split_length = original_length - first_split_length

        # Replace the start with a Byte of the truncated length.
        self._classifications[start_int] = Byte(first_split_length)
        # The inside markers between (start_int+1, binary_addr_int) are
        # already INSIDE_A_CLASSIFICATION — leave them alone for the
        # left half.
        # Insert a new Byte at the split point. Inside markers from
        # (binary_addr_int+1, start_int+original_length) are already
        # INSIDE_A_CLASSIFICATION — they belong to the right half now.
        self._classifications[binary_addr_int] = Byte(second_split_length)
