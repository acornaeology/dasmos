"""Unit tests for dasmos.core.disassembly.

Covers the ClassificationStore — the registry of byte-classifications
keyed by binary address. The wider disassembly-engine concerns from
py8dis (label-name suggestion, the output engine, constants,
comments, annotations) are deferred to the formatter and orchestration
ports because they depend on the assembler/trace layers that have not
yet been ported.
"""

import pytest

from dasmos.core.classification import Byte, Fill, String, Word
from dasmos.core.disassembly import (
    INSIDE_A_CLASSIFICATION,
    ClassificationError,
    ClassificationStore,
)
from dasmos.core.memory import BinaryAddr


class TestClassificationStore:

    def test_empty_store_has_nothing_classified(self):
        store = ClassificationStore()
        assert not store.is_classified(0x8000)
        assert store.get_classification(0x8000) is None

    def test_add_classification_records_at_start(self):
        store = ClassificationStore()
        b = Byte(4)
        store.add_classification(0x8000, b)
        assert store.get_classification(0x8000) is b

    def test_add_classification_marks_following_bytes_inside(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        for offset in (1, 2, 3):
            assert store.get_classification(0x8000 + offset) is INSIDE_A_CLASSIFICATION

    def test_add_classification_does_not_mark_byte_after_end(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        # 0x8004 is one past the end; should still be unclassified.
        assert not store.is_classified(0x8004)

    def test_is_classified_single_byte(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        assert store.is_classified(0x8000)
        assert store.is_classified(0x8001)
        assert store.is_classified(0x8003)
        assert not store.is_classified(0x8004)

    def test_is_classified_range_true_if_any_byte_classified(self):
        store = ClassificationStore()
        store.add_classification(0x8002, Byte(1))
        # The 4-byte range starting at 0x8000 covers the classified
        # byte at 0x8002, so the range is "classified".
        assert store.is_classified(0x8000, length=4)

    def test_is_classified_range_false_when_none_classified(self):
        store = ClassificationStore()
        assert not store.is_classified(0x8000, length=4)

    def test_add_overlapping_classification_raises(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        with pytest.raises(ClassificationError, match="already classified"):
            store.add_classification(0x8002, Byte(2))

    def test_add_at_already_classified_addr_raises(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(1))
        with pytest.raises(ClassificationError, match="already classified"):
            store.add_classification(0x8000, Byte(1))

    def test_get_classification_for_unclassified_addr_returns_none(self):
        store = ClassificationStore()
        assert store.get_classification(0x9000) is None

    def test_iter_classified_starts_yields_only_starts(self):
        store = ClassificationStore()
        b1 = Byte(4)
        b2 = Word(2)
        store.add_classification(0x8000, b1)
        store.add_classification(0x8004, b2)
        starts = list(store.iter_classified_starts())
        # Sorted by binary address; only the starts, not the inside markers.
        assert starts == [
            (BinaryAddr(0x8000), b1),
            (BinaryAddr(0x8004), b2),
        ]

    def test_two_stores_are_independent(self):
        # Justification for the rewrite — module-level classifications
        # array in py8dis prevented this property.
        a = ClassificationStore()
        b = ClassificationStore()
        a.add_classification(0x8000, Byte(4))
        assert a.is_classified(0x8000)
        assert not b.is_classified(0x8000)


class TestSplitClassification:
    """py8dis's split_classification, lifted with deliberate behaviour:
    splitting in the interior of a classification replaces the
    original (whatever its type) with two Byte classifications. Used at
    move boundaries where exact type preservation is unimportant — the
    bytes themselves are unchanged.
    """

    def test_split_at_unclassified_addr_is_noop(self):
        store = ClassificationStore()
        store.split_at(0x8000)
        assert not store.is_classified(0x8000)

    def test_split_at_start_of_classification_is_noop(self):
        # py8dis's split_classification only fires when the addr is an
        # INSIDE marker — at the start of a classification it does
        # nothing. (Splitting at the start would have nothing to do.)
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        store.split_at(0x8000)
        assert isinstance(store.get_classification(0x8000), Byte)
        assert store.get_classification(0x8000).length() == 4

    def test_split_in_interior_replaces_with_two_bytes(self):
        store = ClassificationStore()
        store.add_classification(0x8000, Word(4))
        store.split_at(0x8002)
        # Both halves become Byte regardless of the original type.
        first = store.get_classification(0x8000)
        second = store.get_classification(0x8002)
        assert isinstance(first, Byte)
        assert first.length() == 2
        assert isinstance(second, Byte)
        assert second.length() == 2
        # The split marker bytes inside the new shorter classifications
        # are still INSIDE markers if the new lengths are > 1.
        assert store.get_classification(0x8001) is INSIDE_A_CLASSIFICATION
        assert store.get_classification(0x8003) is INSIDE_A_CLASSIFICATION

    def test_split_at_one_past_end_is_noop(self):
        # 0x8004 is unclassified; same as the unclassified-addr test
        # but from the perspective of "the end of an existing block".
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(4))
        store.split_at(0x8004)
        assert isinstance(store.get_classification(0x8000), Byte)
        assert store.get_classification(0x8000).length() == 4
        assert not store.is_classified(0x8004)


class TestRemoveClassification:
    """``remove`` / ``remove_range`` — the public clearing primitives
    that back the driver-side classification override (#25). Unlike
    :meth:`split_at` (which converts a span into shorter Bytes),
    ``remove`` clears the WHOLE enclosing span — start byte plus every
    ``INSIDE_A_CLASSIFICATION`` marker — so the bytes return to the
    unclassified state and a later pass (the trace, or a fresh
    ``add_classification``) can claim them. The bytes themselves are
    never touched, so the round-trip oracle is unaffected.
    """

    def test_remove_unclassified_is_noop_and_returns_none(self):
        store = ClassificationStore()
        assert store.remove(0x8000) is None
        assert not store.is_classified(0x8000)

    def test_remove_at_start_clears_whole_span(self):
        store = ClassificationStore()
        original = Byte(3)
        store.add_classification(0x8000, original)
        removed = store.remove(0x8000)
        assert removed is original
        for addr in (0x8000, 0x8001, 0x8002):
            assert not store.is_classified(addr)
            assert store.get_classification(addr) is None

    def test_remove_from_interior_clears_whole_enclosing_span(self):
        # Clearing must walk back to the start and drop the entire
        # classification, not just the addressed byte — otherwise an
        # orphaned INSIDE marker would corrupt the store.
        store = ClassificationStore()
        store.add_classification(0x8000, Word(4))
        removed = store.remove(0x8002)
        assert isinstance(removed, Word)
        for addr in (0x8000, 0x8001, 0x8002, 0x8003):
            assert not store.is_classified(addr)

    def test_remove_then_add_succeeds_with_no_overlap_error(self):
        # The whole point: after removing, the span is reclaimable.
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(3))
        store.remove(0x8000)
        # Would have raised ClassificationError before the remove.
        store.add_classification(0x8000, Word(2))
        assert isinstance(store.get_classification(0x8000), Word)

    def test_remove_leaves_neighbouring_classifications_intact(self):
        store = ClassificationStore()
        keep_before = Byte(1)
        target = Byte(3)
        keep_after = Byte(1)
        store.add_classification(0x7fff, keep_before)
        store.add_classification(0x8000, target)
        store.add_classification(0x8003, keep_after)
        store.remove(0x8001)
        assert store.get_classification(0x7fff) is keep_before
        assert store.get_classification(0x8003) is keep_after
        for addr in (0x8000, 0x8001, 0x8002):
            assert not store.is_classified(addr)

    def test_remove_range_clears_every_overlapping_span(self):
        # remove_range clears all classifications overlapping the range,
        # including a span that STARTS before the range start (clearing
        # the whole of that span, per override semantics).
        store = ClassificationStore()
        store.add_classification(0x8000, Byte(2))   # 0x8000-0x8001
        store.add_classification(0x8002, Word(2))   # 0x8002-0x8003
        store.add_classification(0x8004, Byte(1))   # 0x8004
        removed = store.remove_range(0x8001, 4)     # touches all three
        assert len(removed) == 3
        for addr in range(0x8000, 0x8005):
            assert not store.is_classified(addr)

    def test_remove_range_on_clear_region_is_noop(self):
        store = ClassificationStore()
        assert store.remove_range(0x8000, 4) == []
