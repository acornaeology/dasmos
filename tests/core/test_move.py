"""Unit tests for dasmos.core.move.

Covers the Move handle, the MoveManager registry, and the
active-move context-manager protocol. Mirrors the small inline tests
at the bottom of py8dis's movemanager.py and adds regression tests
for the bugs noted in the port plan.
"""

import pytest

from dasmos.core.memory import BinaryAddr, BinaryLocation, RuntimeAddr, RuntimeLocation
from dasmos.core.move import (
    BASE_MOVE_ID,
    Move,
    MoveError,
    MoveManager,
)


@pytest.fixture
def geometry_move():
    """Return a Move configured for geometry-method testing.

    Constructed via a real MoveManager (the only legitimate way to
    obtain a Move) — there is no standalone geometry-only Move
    factory because Moves are bound to their manager and that
    binding is load-bearing for context-manager use elsewhere.
    """
    mm = MoveManager()
    return mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)


class TestMoveGeometry:
    """Geometry helpers — purely on the Move's static fields."""

    def test_is_in_move_dest_interior(self, geometry_move):
        m = geometry_move
        assert m.is_in_move_dest(RuntimeAddr(0x70), include_end_address=False)
        assert m.is_in_move_dest(RuntimeAddr(0x75), include_end_address=False)
        assert not m.is_in_move_dest(RuntimeAddr(0x6F), include_end_address=False)

    def test_is_in_move_dest_end_address(self, geometry_move):
        m = geometry_move
        # 0x70 + 10 = 0x7A is one-past-the-end
        assert not m.is_in_move_dest(RuntimeAddr(0x7A), include_end_address=False)
        assert m.is_in_move_dest(RuntimeAddr(0x7A), include_end_address=True)
        assert not m.is_in_move_dest(RuntimeAddr(0x7B), include_end_address=True)

    def test_is_in_move_src_interior(self, geometry_move):
        m = geometry_move
        assert m.is_in_move_src(BinaryAddr(0x1900), include_end_address=False)
        assert m.is_in_move_src(BinaryAddr(0x1905), include_end_address=False)
        assert not m.is_in_move_src(BinaryAddr(0x18FF), include_end_address=False)

    def test_convert_binary_to_runtime_round_trips(self, geometry_move):
        assert geometry_move.convert_binary_to_runtime_addr(
            BinaryAddr(0x1903),
        ) == RuntimeAddr(0x73)

    def test_convert_runtime_to_binary_round_trips(self, geometry_move):
        assert geometry_move.convert_runtime_to_binary_addr(
            RuntimeAddr(0x73),
        ) == BinaryAddr(0x1903)


class TestMoveConstructor:
    """Direct construction errors — these only fire when someone
    bypasses :meth:`MoveManager.add_move` and constructs a Move by
    hand. Exercise the validation messages so they don't regress.
    """

    def test_rejects_empty_name(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="non-empty name"):
            Move(
                RuntimeAddr(0x70), BinaryAddr(0x1900), 10,
                name="", manager=mm, move_id=99,
            )

    def test_rejects_zero_length(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="length must be positive"):
            Move(
                RuntimeAddr(0x70), BinaryAddr(0x1900), 0,
                name="x", manager=mm, move_id=99,
            )

    def test_rejects_negative_length(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="length must be positive"):
            Move(
                RuntimeAddr(0x70), BinaryAddr(0x1900), -1,
                name="x", manager=mm, move_id=99,
            )


class TestMoveManager:

    def test_empty_manager_has_only_base_move(self):
        mm = MoveManager()
        assert mm.is_valid_move_id(BASE_MOVE_ID)
        # No other moves defined yet.
        assert not mm.is_valid_move_id(1)
        assert mm.active_move_ids == []

    def test_add_move_returns_increasing_ids(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        m2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        assert m1._move_id == 1
        assert m2._move_id == 2
        assert mm.is_valid_move_id(m1._move_id)
        assert mm.is_valid_move_id(m2._move_id)

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
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        m2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        m3 = mm.add_move(RuntimeAddr(0x900), BinaryAddr(0x2100), 256)
        return mm, m1, m2, m3

    def test_r2b_with_no_relevant_moves_is_identity(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        # 0x2008 is past m2's dest (0x70..0x77) and not in any other dest.
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x2008))
        assert binary_addr == BinaryAddr(0x2008)
        assert move_id == BASE_MOVE_ID

    def test_r2b_unique_move_resolves_unambiguously(self, mm_with_three_moves):
        mm, _, _, m3 = mm_with_three_moves
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x900))
        assert binary_addr == BinaryAddr(0x2100)
        assert move_id == m3._move_id

    def test_r2b_ambiguous_returns_none(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        # 0x70 is the dest of m1 and m2; with nothing active, ambiguous.
        binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
        assert binary_addr is None
        assert move_id is None

    def test_r2b_with_active_move_disambiguates(self, mm_with_three_moves):
        mm, m1, m2, _ = mm_with_three_moves
        with m2:
            binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
            assert binary_addr == BinaryAddr(0x2000)
            assert move_id == m2._move_id

    def test_r2b_innermost_active_move_wins(self, mm_with_three_moves):
        mm, m1, m2, _ = mm_with_three_moves
        with m2:
            with m1:
                binary_addr, move_id = mm.r2b(RuntimeAddr(0x70))
                assert binary_addr == BinaryAddr(0x1900)
                assert move_id == m1._move_id

    def test_r2b_with_specific_move_id_overrides_active_stack(self, mm_with_three_moves):
        mm, m1, m2, _ = mm_with_three_moves
        with m2:
            binary_addr, move_id = mm.r2b(
                RuntimeAddr(0x70), specific_move_id=m1._move_id,
            )
            assert binary_addr == BinaryAddr(0x1900)
            assert move_id == m1._move_id

    def test_r2b_checked_raises_on_ambiguous(self, mm_with_three_moves):
        mm, _, _, _ = mm_with_three_moves
        with pytest.raises(MoveError, match="[Aa]mbiguous"):
            mm.r2b_checked(RuntimeAddr(0x70))

    def test_r2b_checked_returns_binary_location_when_unambiguous(self, mm_with_three_moves):
        mm, _, _, m3 = mm_with_three_moves
        loc = mm.r2b_checked(RuntimeAddr(0x900))
        assert loc == BinaryLocation(0x2100, m3._move_id)


class TestMoveIdsForRuntimeAddr:

    def test_returns_empty_for_unmoved_addr(self):
        mm = MoveManager()
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x500)) == set()

    def test_returns_all_moves_targeting_addr(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        m2 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x2000), 8)
        mm.add_move(RuntimeAddr(0x900), BinaryAddr(0x2100), 256)
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == {m1._move_id, m2._move_id}

    def test_cache_invalidated_after_add_move(self):
        mm = MoveManager()
        # Populate the cache.
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == set()
        # Add a move; cache must reflect the new state on next read.
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert mm.move_ids_for_runtime_addr(RuntimeAddr(0x70)) == {m1._move_id}


class TestActiveMoveStack:

    def test_with_pushes_and_pops(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        assert mm.active_move_ids == []
        with m1:
            assert mm.active_move_ids == [m1._move_id]
        assert mm.active_move_ids == []

    def test_with_nested_lifo(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        m2 = mm.add_move(RuntimeAddr(0x90), BinaryAddr(0x2000), 8)
        with m1:
            with m2:
                assert mm.active_move_ids == [m1._move_id, m2._move_id]
            assert mm.active_move_ids == [m1._move_id]
        assert mm.active_move_ids == []

    def test_with_pops_on_exception(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with pytest.raises(RuntimeError):
            with m1:
                raise RuntimeError("boom")
        assert mm.active_move_ids == []

    def test_push_active_with_unknown_id_raises_with_diagnostic(self):
        # Hand-poke an out-of-range id via the Move's internal field
        # to exercise the diagnostic path. This shouldn't happen
        # under normal use — Move objects come from add_move, which
        # always supplies a valid id — but the error message guides
        # diagnosis when it does.
        mm = MoveManager()
        m = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        m._move_id = 99
        with pytest.raises(
            MoveError,
            match="not registered with this MoveManager",
        ):
            with m:
                pass

    def test_pop_active_on_empty_stack_raises_with_diagnostic(self):
        mm = MoveManager()
        with pytest.raises(MoveError, match="active-move stack is empty"):
            mm._pop_active(1)


class TestIndependence:

    def test_two_move_managers_share_no_state(self):
        # The justification for the whole rewrite — module-level
        # globals in py8dis prevent this property.
        mm_a = MoveManager()
        mm_b = MoveManager()
        m1_a = mm_a.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        # mm_b sees no moves.
        assert not mm_b.is_valid_move_id(m1_a._move_id)
        assert mm_b.b2r(BinaryAddr(0x1900)) == RuntimeAddr(0x1900)
        # And mm_b's active stack is independent.
        with m1_a:
            assert mm_a.active_move_ids == [m1_a._move_id]
            assert mm_b.active_move_ids == []


class TestLocationCoercion:

    def test_make_binary_location_from_int_uses_topmost_active(self):
        mm = MoveManager()
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with m1:
            loc = mm.make_binary_location(0x1900)
            assert isinstance(loc, BinaryLocation)
            assert loc.binary_addr == BinaryAddr(0x1900)
            assert loc.move_id == m1._move_id

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
        m1 = mm.add_move(RuntimeAddr(0x70), BinaryAddr(0x1900), 10)
        with m1:
            loc = mm.make_runtime_location(0x70)
            assert isinstance(loc, RuntimeLocation)
            assert loc.runtime_addr == RuntimeAddr(0x70)
            assert loc.move_id == m1._move_id

    def test_make_runtime_location_passes_through(self):
        mm = MoveManager()
        existing = RuntimeLocation(0x70, BASE_MOVE_ID)
        assert mm.make_runtime_location(existing) is existing
