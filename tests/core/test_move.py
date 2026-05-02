"""Unit tests for dasmos.core.move.

Covers MoveDefinition, the MoveManager registry, and the active-move
context manager. Mirrors the small inline tests at the bottom of
py8dis's movemanager.py and adds regression tests for the bugs noted
in the port plan.
"""

import pytest

from dasmos.core.memory import BinaryAddr, BinaryLocation, RuntimeAddr, RuntimeLocation
from dasmos.core.move import (
    BASE_MOVE_ID,
    MoveDefinition,
    MoveError,
    MoveManager,
)


class TestMoveDefinition:

    def test_is_in_move_dest_interior(self):
        md = MoveDefinition(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert md.is_in_move_dest(RuntimeAddr(0x70), include_end_address=False)
        assert md.is_in_move_dest(RuntimeAddr(0x75), include_end_address=False)
        assert not md.is_in_move_dest(RuntimeAddr(0x6F), include_end_address=False)

    def test_is_in_move_dest_end_address(self):
        md = MoveDefinition(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        # 0x70 + 10 = 0x7A is one-past-the-end
        assert not md.is_in_move_dest(RuntimeAddr(0x7A), include_end_address=False)
        assert md.is_in_move_dest(RuntimeAddr(0x7A), include_end_address=True)
        assert not md.is_in_move_dest(RuntimeAddr(0x7B), include_end_address=True)

    def test_is_in_move_src_interior(self):
        md = MoveDefinition(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert md.is_in_move_src(BinaryAddr(0x1900), include_end_address=False)
        assert md.is_in_move_src(BinaryAddr(0x1905), include_end_address=False)
        assert not md.is_in_move_src(BinaryAddr(0x18FF), include_end_address=False)

    def test_convert_binary_to_runtime_round_trips(self):
        md = MoveDefinition(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert md.convert_binary_to_runtime_addr(BinaryAddr(0x1903)) == RuntimeAddr(0x73)

    def test_convert_runtime_to_binary_round_trips(self):
        md = MoveDefinition(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert md.convert_runtime_to_binary_addr(RuntimeAddr(0x73)) == BinaryAddr(0x1903)


class TestMoveManager:

    def test_empty_manager_has_only_base_move(self):
        mm = MoveManager()
        assert mm.is_valid_move_id(BASE_MOVE_ID)
        # No other moves defined yet.
        assert not mm.is_valid_move_id(1)
        assert mm.active_move_ids == []

    def test_add_move_returns_increasing_ids(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        id2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        assert id1 == 1
        assert id2 == 2
        assert mm.is_valid_move_id(id1)
        assert mm.is_valid_move_id(id2)

    def test_add_move_rejects_zero_length(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="length"):
            mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 0)

    def test_add_move_rejects_negative_length(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="length"):
            mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), -1)

    def test_add_move_rejects_dest_equals_src(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="dest"):
            mm.add_move(RuntimeAddr(0x1900), BinaryAddr(0x1900), 10)

    def test_add_move_rejects_overflowing_range(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="overflow"):
            mm.add_move(RuntimeAddr(0xFF80), BinaryAddr(0x1900), 0x100)


class TestBinaryToRuntime:

    def test_b2r_for_unmoved_binary_addr_is_identity(self):
        mm = MoveManager()
        assert mm.b2r(BinaryAddr(0x70)) == RuntimeAddr(0x70)

    def test_b2r_after_add_move_returns_dest(self):
        mm = MoveManager()
        mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert mm.b2r(BinaryAddr(0x1900)) == RuntimeAddr(0x70)
        assert mm.b2r(BinaryAddr(0x1905)) == RuntimeAddr(0x75)

    def test_b2r_outside_any_move_dest_falls_through_to_base(self):
        mm = MoveManager()
        mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        # 0x1909 is outside 0x1900..0x1909 actually wait — len 10 so 0x1900..0x1909 inclusive
        # 0x190A is past the move source
        assert mm.b2r(BinaryAddr(0x190A)) == RuntimeAddr(0x190A)


class TestRuntimeToBinary:
    """The interesting cases — runtime→binary is potentially ambiguous."""

    @pytest.fixture
    def mm_with_three_moves(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        id2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        id3 = mm.add_move(RuntimeAddr(0x900), BinaryAddr(0x2100), 256)
        return mm, id1, id2, id3

    def test_r2b_with_no_relevant_moves_is_identity(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        # 0x2008 is past id2's dest (0x70..0x77) and not in any other dest.
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x2008))
        assert binary_addr == BinaryAddr(0x2008)
        assert move_id == BASE_MOVE_ID

    def test_r2b_unique_move_resolves_unambiguously(self, mm_with_three_moves):
        mm, _, _, id3 = mm_with_three_moves
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x900))
        assert binary_addr == BinaryAddr(0x2100)
        assert move_id == id3

    def test_r2b_ambiguous_returns_none(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        # 0x70 is the dest of id1 and id2; with nothing active, ambiguous.
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
        assert binary_addr is None
        assert move_id is None

    def test_r2b_with_active_move_disambiguates(self, mm_with_three_moves):
        mm, id1, id2, _ = mm_with_three_moves
        with mm.using(id2):
            binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
            assert binary_addr == BinaryAddr(0x2000)
            assert move_id == id2

    def test_r2b_innermost_active_move_wins(self, mm_with_three_moves):
        mm, id1, id2, _ = mm_with_three_moves
        with mm.using(id2):
            with mm.using(id1):
                binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
                assert binary_addr == BinaryAddr(0x1900)
                assert move_id == id1

    def test_r2b_with_specific_move_id_overrides_active_stack(self, mm_with_three_moves):
        mm, id1, id2, _ = mm_with_three_moves
        with mm.using(id2):
            binary_addr, move_id = mm.r2b(RuntimeAddr(0x70), specific_move_id=id1)
            assert binary_addr == BinaryAddr(0x1900)
            assert move_id == id1

    def test_r2b_checked_raises_on_ambiguous(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        with pytest.raises(MoveError, match="[Aa]mbiguous"):
            mm.r2b_checked(RuntimeAddr(0x70))

    def test_r2b_checked_returns_binary_location_when_unambiguous(self, mm_with_three_moves):
        mm, _, _, id3 = mm_with_three_moves
        loc = mm.r2b_checked(RuntimeAddr(0x900))
        assert loc == BinaryLocation(0x2100, id3)


class TestMoveIdsForRuntimeAddr:

    def test_returns_empty_for_unmoved_addr(self):
        mm = MoveManager()
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x500)) == set()

    def test_returns_all_moves_targeting_addr(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        id2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        mm.add_move(RuntimeAddr(0x900), BinaryAddr(0x2100), 256)
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == {id1, id2}

    def test_cache_invalidated_after_add_move(self):
        mm = MoveManager()
        # Populate the cache.
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == set()
        # Add a move; cache must reflect the new state on next read.
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == {id1}


class TestActiveMoveStack:

    def test_using_pushes_and_pops(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert mm.active_move_ids == []
        with mm.using(id1):
            assert mm.active_move_ids == [id1]
        assert mm.active_move_ids == []

    def test_using_nested_lifo(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        id2 = mm.add_move(RuntimeAddr(0x90), BinaryAddr(0x2000), 8)
        with mm.using(id1):
            with mm.using(id2):
                assert mm.active_move_ids == [id1, id2]
            assert mm.active_move_ids == [id1]
        assert mm.active_move_ids == []

    def test_using_pops_on_exception(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with pytest.raises(RuntimeError):
            with mm.using(id1):
                raise RuntimeError("boom")
        assert mm.active_move_ids == []

    def test_using_rejects_invalid_move_id(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="move id"):
            with mm.using(99):
                pass


class TestIndependence:

    def test_two_move_managers_share_no_state(self):
        # The justification for the whole rewrite — module-level
        # globals in py8dis prevent this property.
        mm_a = MoveManager()
        mm_b = MoveManager()
        id1_a = mm_a.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        # mm_b sees no moves.
        assert not mm_b.is_valid_move_id(id1_a)
        assert mm_b.b2r(BinaryAddr(0x1900)) == RuntimeAddr(0x1900)
        # And mm_b's active stack is independent.
        with mm_a.using(id1_a):
            assert mm_a.active_move_ids == [id1_a]
            assert mm_b.active_move_ids == []


class TestLocationCoercion:

    def test_make_binary_location_from_int_uses_topmost_active(self):
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with mm.using(id1):
            loc = mm.make_binary_location(0x1900)
            assert isinstance(loc, BinaryLocation)
            assert loc.binary_addr == BinaryAddr(0x1900)
            assert loc.move_id == id1

    def test_make_binary_location_from_int_with_no_active_uses_base(self):
        mm = MoveManager()
        loc = mm.make_binary_location(0x1900)
        assert loc.move_id == BASE_MOVE_ID

    def test_make_binary_location_passes_through(self):
        mm = MoveManager()
        existing = BinaryLocation(0x1900, BASE_MOVE_ID)
        assert mm.make_binary_location(existing) is existing

    def test_make_runtime_location_from_int_uses_topmost_active(self):
        # Regression: py8dis's make_runloc had a typo (used `binary_loc`
        # in the constructor instead of `runtime_loc`), so this code
        # path raised NameError if exercised.
        mm = MoveManager()
        id1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with mm.using(id1):
            loc = mm.make_runtime_location(0x70)
            assert isinstance(loc, RuntimeLocation)
            assert loc.runtime_addr == RuntimeAddr(0x70)
            assert loc.move_id == id1

    def test_make_runtime_location_passes_through(self):
        mm = MoveManager()
        existing = RuntimeLocation(0x70, BASE_MOVE_ID)
        assert mm.make_runtime_location(existing) is existing
