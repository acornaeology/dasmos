"""Unit tests for dasmos.core.annotations.

Tests the AnnotationStore data layer in isolation — the renderer
integration is exercised end-to-end in test_driver_roundtrip.py
under TestComments.
"""

import pytest

from dasmos.core.annotations import (
    Align,
    Annotation,
    AnnotationStore,
    Banner,
    Comment,
)
from dasmos.core.memory import BinaryAddr


class TestAlign:

    def test_has_expected_members(self):
        names = {a.name for a in Align}
        assert names == {
            "BEFORE_LABEL",
            "AFTER_LABEL",
            "BEFORE_LINE",
            "AFTER_LINE",
            "INLINE",
        }


class TestComment:

    def test_default_alignment_is_before_label(self):
        c = Comment(text="hi")
        assert c.align is Align.BEFORE_LABEL
        assert c.word_wrap is True
        assert c.indent == 0
        assert c.auto_generated is False
        assert c.priority is None

    def test_inline_comment(self):
        c = Comment(text="trailing", align=Align.INLINE)
        assert c.align is Align.INLINE


class TestAnnotation:

    def test_default_alignment_is_before_label(self):
        a = Annotation(text="!align 256")
        assert a.align is Align.BEFORE_LABEL


class TestBanner:

    def test_default_construction_is_empty(self):
        b = Banner()
        assert b.title == ""
        assert b.description == ""
        assert b.align is Align.BEFORE_LABEL
        assert b.auto_generated is False
        assert b.priority is None

    def test_title_only(self):
        b = Banner(title="reset entry point")
        assert b.title == "reset entry point"
        assert b.description == ""

    def test_title_and_description(self):
        b = Banner(
            title="ram_test",
            description="Probes pages upward from &1800.",
        )
        assert b.title == "ram_test"
        assert "Probes pages" in b.description

    def test_can_be_stored_in_annotation_store(self):
        store = AnnotationStore()
        b = Banner(title="hello")
        store.add(0x8000, b)
        assert store.get(0x8000) == [b]
        assert store.get_for_align(0x8000, Align.BEFORE_LABEL) == [b]


class TestAnnotationStore:

    def test_empty_store_contains_nothing(self):
        store = AnnotationStore()
        assert 0x8000 not in store
        assert store.get(0x8000) == []

    def test_add_comment(self):
        store = AnnotationStore()
        c = Comment(text="hello")
        store.add(0x8000, c)
        assert 0x8000 in store
        assert store.get(0x8000) == [c]

    def test_multiple_entries_at_same_address_preserve_insertion_order(self):
        # Use distinct alignments so no duplicate-warning fires —
        # this test is about insertion order, not the duplicate
        # check. (The duplicate-warning behaviour is covered in
        # ``TestAnnotationStoreDuplicateWarning`` below.)
        store = AnnotationStore()
        a = Comment(text="first", align=Align.BEFORE_LABEL)
        b = Comment(text="second", align=Align.BEFORE_LINE)
        c = Comment(text="third", align=Align.AFTER_LINE)
        store.add(0x8000, a)
        store.add(0x8000, b)
        store.add(0x8000, c)
        assert store.get(0x8000) == [a, b, c]

    def test_get_for_align_filters_by_alignment(self):
        store = AnnotationStore()
        before = Comment(text="b", align=Align.BEFORE_LABEL)
        inline = Comment(text="i", align=Align.INLINE)
        after = Comment(text="a", align=Align.AFTER_LINE)
        for c in (before, inline, after):
            store.add(0x8000, c)
        assert store.get_for_align(0x8000, Align.BEFORE_LABEL) == [before]
        assert store.get_for_align(0x8000, Align.INLINE) == [inline]
        assert store.get_for_align(0x8000, Align.AFTER_LINE) == [after]
        assert store.get_for_align(0x8000, Align.AFTER_LABEL) == []

    def test_can_store_annotations_alongside_comments(self):
        store = AnnotationStore()
        c = Comment(text="a comment")
        a = Annotation(text="!align 256")
        store.add(0x8000, c)
        store.add(0x8000, a)
        assert store.get(0x8000) == [c, a]

    def test_two_stores_are_independent(self):
        # Justification for the rewrite — module-level state in
        # py8dis prevented this property.
        s1 = AnnotationStore()
        s2 = AnnotationStore()
        s1.add(0x8000, Comment(text="in s1"))
        assert 0x8000 in s1
        assert 0x8000 not in s2

    def test_iter_yields_addresses(self):
        # Use distinct alignments at &8000 to avoid the
        # duplicate-warning — this test is about address iteration,
        # not duplicate handling.
        store = AnnotationStore()
        store.add(0x8000, Comment(text="a", align=Align.BEFORE_LABEL))
        store.add(0x9000, Comment(text="b"))
        store.add(0x8000, Comment(text="c", align=Align.INLINE))
        assert set(int(a) for a in store) == {0x8000, 0x9000}

    def test_items_yields_address_entries_pairs(self):
        store = AnnotationStore()
        store.add(0x8000, Comment(text="a"))
        store.add(0x9000, Comment(text="b"))
        result = {int(a): [e.text for e in entries] for a, entries in store.items()}
        assert result == {0x8000: ["a"], 0x9000: ["b"]}


class TestAnnotationStoreDuplicateWarning:
    """A second annotation at the same (address, align, type) is
    almost always a driver-script bug — likely a copy-paste error,
    or an attempt to OVERRIDE an earlier comment that ends up
    appending instead. We warn (don't raise) so the disassembly
    still completes; both entries are stored, and the user sees
    the warning to decide how to fix it.
    """

    def test_duplicate_comment_same_align_warns(self):
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Comment(text="first"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Comment(text="second"))
        # Exactly one warning, and it identifies the address +
        # alignment + the existing entry's text so the user can
        # locate the earlier comment.
        assert len(caught) == 1
        msg = str(caught[0].message)
        assert "8000" in msg
        assert "before_label" in msg.lower() or "BEFORE_LABEL" in msg
        # Both entries are still stored.
        assert len(store.get(0x8000)) == 2

    def test_duplicate_comment_different_align_no_warning(self):
        # A BEFORE_LABEL comment plus an INLINE comment at the same
        # address is a common pattern (the latter is a trailing
        # remark on the instruction). No warning.
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Comment(text="header", align=Align.BEFORE_LABEL))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Comment(text="trailer", align=Align.INLINE))
        assert caught == []

    def test_comment_alongside_banner_no_warning(self):
        # Comment + Banner at the same (addr, align) is OK — the
        # check is per-type. The renderer interleaves them by
        # alignment bucket regardless.
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Banner(title="A subroutine"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Comment(text="leading remark"))
        assert caught == []

    def test_duplicate_banner_same_align_warns(self):
        # Two banners at the same address — typically a driver bug
        # (e.g. ``subroutine()`` called twice for the same addr).
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Banner(title="First"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Banner(title="Second"))
        assert len(caught) == 1
        assert "Banner" in str(caught[0].message)

    def test_duplicate_annotation_same_align_warns(self):
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Annotation(text="!align 256"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Annotation(text="!align 256"))
        assert len(caught) == 1

    def test_three_duplicates_emit_two_warnings(self):
        # Each duplicate after the first triggers a warning.
        import warnings
        store = AnnotationStore()
        store.add(0x8000, Comment(text="first"))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            store.add(0x8000, Comment(text="second"))
            store.add(0x8000, Comment(text="third"))
        assert len(caught) == 2
