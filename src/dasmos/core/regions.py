"""Indexed base-address *regions* — author-declared windows around an
anchor label whose in-window addresses render relative to the anchor
(``fsm_sector0-3,X``) instead of as bare addresses.

This is "Layer B" of the indexed-base work; see
``docs/design/reference-kinds-memo.md``. A region is a naming *lens*
over a runtime-address window: it names the *gaps* around an anchor,
yielding to any explicit label an author placed inside the window.

Windows must be disjoint — two regions whose inclusive
``[anchor+lo, anchor+hi]`` ranges intersect are rejected at declaration
time, so ``anchor±k`` resolution is never ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass

from dasmos.exceptions import DasmosError


class RegionError(DasmosError):
    """Raised on an invalid or overlapping index-region declaration."""


@dataclass(frozen=True)
class IndexRegion:
    """One author-declared indexing region.

    ``anchor_addr`` is a runtime address carrying the explicit label
    ``name``; the region owns the inclusive offset window
    ``[lo, hi]`` around it (``lo`` typically ≤ 0, ``hi`` ≥ 0). Offset 0
    is the anchor itself, never a gap.

    ``named_slots`` selects how in-window gaps are named: ``False``
    (default) renders the arithmetic form ``name±k``; ``True`` gives
    each gap a distinct identifier ``name_m<k>`` / ``name_p<k>``.
    """

    anchor_addr: int
    name: str
    lo: int
    hi: int
    description: str | None = None
    group: str | None = None
    access: str | None = None
    named_slots: bool = False

    @property
    def start(self) -> int:
        """Lowest runtime address in the window (inclusive)."""
        return self.anchor_addr + self.lo

    @property
    def end(self) -> int:
        """Highest runtime address in the window (inclusive)."""
        return self.anchor_addr + self.hi

    def contains(self, runtime_addr: int) -> bool:
        return self.start <= runtime_addr <= self.end

    def offset_of(self, runtime_addr: int) -> int:
        """Signed displacement of ``runtime_addr`` from the anchor."""
        return int(runtime_addr) - self.anchor_addr

    def overlaps(self, other: "IndexRegion") -> bool:
        return self.start <= other.end and other.start <= self.end

    def slot_expression(self, offset: int) -> str:
        """The ``name±k`` arithmetic form for a gap at ``offset`` (≠ 0).
        Reassembles to the same bytes as the literal address."""
        if offset > 0:
            return f"{self.name}+{offset}"
        return f"{self.name}-{-offset}"

    def slot_name(self, offset: int) -> str:
        """The ``name_p<k>`` / ``name_m<k>`` identifier for a named-slot
        gap at ``offset`` (≠ 0)."""
        if offset > 0:
            return f"{self.name}_p{offset}"
        return f"{self.name}_m{-offset}"


class RegionManager:
    """Owns the set of declared :class:`IndexRegion`s, enforcing that
    their windows are disjoint and answering point lookups."""

    def __init__(self) -> None:
        self._regions: list[IndexRegion] = []

    def add(self, region: IndexRegion) -> IndexRegion:
        """Register ``region`` after validating it. Raises
        :class:`RegionError` on an empty/inverted window or an overlap
        with an already-registered region."""
        if region.lo > region.hi:
            raise RegionError(
                f"index region {region.name!r} has an inverted window "
                f"(lo={region.lo} > hi={region.hi})"
            )
        for existing in self._regions:
            if region.overlaps(existing):
                raise RegionError(
                    f"index region {region.name!r} "
                    f"(&{region.start:04x}-&{region.end:04x}) overlaps "
                    f"{existing.name!r} "
                    f"(&{existing.start:04x}-&{existing.end:04x}); "
                    f"index-region windows must be disjoint"
                )
        self._regions.append(region)
        return region

    def region_and_offset_for(
        self, runtime_addr: int,
    ) -> tuple[IndexRegion, int] | None:
        """Return ``(region, offset)`` for the region whose window
        contains ``runtime_addr``, or ``None``. Windows are disjoint, so
        at most one matches."""
        for region in self._regions:
            if region.contains(runtime_addr):
                return region, region.offset_of(runtime_addr)
        return None

    @property
    def all_regions(self) -> list[IndexRegion]:
        return list(self._regions)

    def __len__(self) -> int:
        return len(self._regions)
