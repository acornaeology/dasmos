"""Unit tests for IndexRegion / RegionManager (Layer B core)."""

from __future__ import annotations

import pytest

from dasmos.core.regions import IndexRegion, RegionError, RegionManager


class TestIndexRegion:

    def test_window_bounds_are_inclusive_offsets(self):
        r = IndexRegion(anchor_addr=0x0E00, name="fsm_sector0", lo=-6, hi=3)
        assert r.start == 0x0DFA
        assert r.end == 0x0E03
        assert r.contains(0x0DFA)
        assert r.contains(0x0E03)
        assert not r.contains(0x0DF9)
        assert not r.contains(0x0E04)

    def test_offset_is_signed_from_anchor(self):
        r = IndexRegion(anchor_addr=0x0E00, name="fsm_sector0", lo=-6, hi=3)
        assert r.offset_of(0x0DFD) == -3
        assert r.offset_of(0x0E03) == 3
        assert r.offset_of(0x0E00) == 0

    def test_slot_expression_arithmetic_form(self):
        r = IndexRegion(anchor_addr=0x0E00, name="fsm_sector0", lo=-6, hi=3)
        assert r.slot_expression(-3) == "fsm_sector0-3"
        assert r.slot_expression(3) == "fsm_sector0+3"

    def test_slot_name_identifier_form(self):
        r = IndexRegion(anchor_addr=0x0E00, name="fsm_sector0", lo=-6, hi=3)
        assert r.slot_name(-3) == "fsm_sector0_m3"
        assert r.slot_name(3) == "fsm_sector0_p3"


class TestRegionManagerDisjointness:

    def test_adds_disjoint_regions(self):
        m = RegionManager()
        m.add(IndexRegion(0x0E00, "a", -3, 3))
        m.add(IndexRegion(0x1000, "b", -3, 3))
        assert len(m) == 2

    def test_touching_windows_are_allowed_when_not_overlapping(self):
        # a owns ..&0E03, b owns &0E04.. — adjacent, not overlapping.
        m = RegionManager()
        m.add(IndexRegion(0x0E00, "a", 0, 3))
        m.add(IndexRegion(0x0E04, "b", 0, 3))
        assert len(m) == 2

    def test_overlapping_windows_raise_with_clear_message(self):
        m = RegionManager()
        m.add(IndexRegion(0x0E00, "fsm_sector0", -6, 3))
        with pytest.raises(RegionError) as exc:
            m.add(IndexRegion(0x0E02, "other", -4, 4))
        msg = str(exc.value)
        assert "fsm_sector0" in msg and "other" in msg
        assert "disjoint" in msg

    def test_inverted_window_raises(self):
        m = RegionManager()
        with pytest.raises(RegionError, match="inverted window"):
            m.add(IndexRegion(0x0E00, "bad", 3, -3))


class TestRegionManagerLookup:

    def test_region_and_offset_for_hit(self):
        m = RegionManager()
        m.add(IndexRegion(0x0E00, "fsm_sector0", -6, 3))
        region, offset = m.region_and_offset_for(0x0DFD)
        assert region.name == "fsm_sector0"
        assert offset == -3

    def test_region_and_offset_for_miss(self):
        m = RegionManager()
        m.add(IndexRegion(0x0E00, "fsm_sector0", -6, 3))
        assert m.region_and_offset_for(0x1234) is None
