"""Unit tests for dasmos.core.memory.

Covers the address-type machinery, validation helpers, location classes,
the MemoryImage container and the RuntimeView read-through. Several
tests exist to pin down explicit corrections of py8dis bugs (flagged
"regression" below).
"""

import pytest

from dasmos.core.memory import (
    BinaryAddr,
    BinaryLocation,
    MemoryAccessError,
    MemoryImage,
    RuntimeAddr,
    RuntimeLocation,
    RuntimeView,
    is_valid_binary_addr,
    is_valid_runtime_addr,
)


class TestAddressTypes:

    def test_binary_addr_rejects_runtime_addr_at_construction(self):
        with pytest.raises(AssertionError):
            BinaryAddr(RuntimeAddr(0x8000))

    def test_runtime_addr_rejects_binary_addr_at_construction(self):
        with pytest.raises(AssertionError):
            RuntimeAddr(BinaryAddr(0x8000))

    def test_binary_addr_addition_returns_binary_addr(self):
        addr = BinaryAddr(0x8000) + 0x10
        assert isinstance(addr, BinaryAddr)
        assert addr == 0x8010

    def test_runtime_addr_addition_returns_runtime_addr(self):
        addr = RuntimeAddr(0x8000) + 0x10
        assert isinstance(addr, RuntimeAddr)
        assert addr == 0x8010

    def test_binary_addr_minus_int_returns_binary_addr(self):
        addr = BinaryAddr(0x8010) - 0x10
        assert isinstance(addr, BinaryAddr)
        assert addr == 0x8000

    def test_binary_addr_minus_binary_addr_returns_plain_int(self):
        # Subtracting two same-typed addresses is a delta, not an address.
        # Explicit choice — py8dis's TypedInt only wrapped __add__.
        delta = BinaryAddr(0x8010) - BinaryAddr(0x8000)
        assert type(delta) is int
        assert delta == 0x10

    def test_runtime_addr_minus_runtime_addr_returns_plain_int(self):
        delta = RuntimeAddr(0x9000) - RuntimeAddr(0x8000)
        assert type(delta) is int
        assert delta == 0x1000


class TestAddressValidation:

    def test_is_valid_binary_addr_within_64k(self):
        assert is_valid_binary_addr(0)
        assert is_valid_binary_addr(0xFFFF)
        assert not is_valid_binary_addr(0x10000)
        assert not is_valid_binary_addr(-1)

    def test_is_valid_binary_addr_at_final_when_allowed(self):
        # Regression: pre-port had a typo (`runtime_addr`) here that
        # would have raised NameError instead of validating correctly.
        assert is_valid_binary_addr(0x10000, allow_final_address=True)
        assert not is_valid_binary_addr(0x10001, allow_final_address=True)

    def test_is_valid_runtime_addr_within_64k(self):
        assert is_valid_runtime_addr(0)
        assert is_valid_runtime_addr(0xFFFF)
        assert not is_valid_runtime_addr(0x10000)


class TestLocationEquality:

    def test_binary_location_equality_requires_addr_and_move_id(self):
        a = BinaryLocation(0x8000, 0)
        b = BinaryLocation(0x8000, 0)
        c = BinaryLocation(0x8000, 1)
        d = BinaryLocation(0x8001, 0)
        assert a == b
        assert a != c
        assert a != d

    def test_runtime_location_equality_requires_addr_and_move_id(self):
        a = RuntimeLocation(0x8000, 0)
        b = RuntimeLocation(0x8000, 0)
        c = RuntimeLocation(0x8000, 1)
        assert a == b
        assert a != c

    def test_binary_and_runtime_locations_with_same_value_are_unequal(self):
        # Regression: py8dis's RuntimeLocation.__eq__ compared
        # self.binary_addr (an attribute that doesn't exist on
        # RuntimeLocation) against other.binary_addr, so a careless
        # comparison would AttributeError or silently wrong-answer.
        bl = BinaryLocation(0x8000, 0)
        rl = RuntimeLocation(0x8000, 0)
        assert bl != rl
        assert rl != bl

    def test_locations_are_hashable_and_distinct_in_sets(self):
        s = {
            BinaryLocation(0x8000, 0),
            BinaryLocation(0x8000, 0),  # duplicate of the first
            BinaryLocation(0x8000, 1),  # different move_id
            BinaryLocation(0x8001, 0),  # different addr
            RuntimeLocation(0x8000, 0),  # different type
        }
        assert len(s) == 4


class TestMemoryImage:

    def test_new_image_is_empty(self):
        img = MemoryImage()
        assert not img.is_loaded(0x8000)
        assert not img.is_loaded(0)

    def test_load_makes_bytes_readable(self, tmp_path):
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x12\x34\x56\x78")
        img = MemoryImage()
        start, end = img.load(binary_filepath, 0x8000)
        assert start == BinaryAddr(0x8000)
        assert end == BinaryAddr(0x8004)
        assert img.get_u8(0x8000) == 0x12
        assert img.get_u8(0x8003) == 0x78
        assert img.get_u16_le(0x8000) == 0x3412
        assert img.get_u16_be(0x8000) == 0x1234

    def test_load_records_load_range(self, tmp_path):
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x00" * 0x100)
        img = MemoryImage()
        img.load(binary_filepath, 0x8000)
        assert img.entire_load_range() == (BinaryAddr(0x8000), BinaryAddr(0x8100))

    def test_load_with_correct_md5_succeeds(self, tmp_path):
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x00" * 16)
        img = MemoryImage()
        # md5 of sixteen zero bytes
        img.load(binary_filepath, 0x8000, md5sum="4ae71336e44bf9bf79d2752e234818a5")
        assert img.get_u8(0x8000) == 0x00

    def test_load_with_bad_md5_raises_memory_access_error(self, tmp_path):
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x00" * 16)
        img = MemoryImage()
        with pytest.raises(MemoryAccessError, match="md5"):
            img.load(binary_filepath, 0x8000, md5sum="00000000000000000000000000000000")

    def test_load_missing_file_raises_memory_access_error(self, tmp_path):
        img = MemoryImage()
        with pytest.raises(MemoryAccessError, match="not found"):
            img.load(tmp_path / "does-not-exist.bin", 0x8000)

    def test_load_overflowing_address_space_raises(self, tmp_path):
        binary_filepath = tmp_path / "big.bin"
        binary_filepath.write_bytes(b"\x00" * 0x100)
        img = MemoryImage()
        with pytest.raises(MemoryAccessError, match="overflow"):
            img.load(binary_filepath, 0xFF80)  # 0xFF80 + 0x100 = 0x10080 > 0x10000

    def test_get_u8_at_unloaded_address_raises(self):
        img = MemoryImage()
        with pytest.raises(MemoryAccessError, match="No data"):
            img.get_u8(0x8000)

    def test_entire_load_range_with_no_loads_raises(self):
        img = MemoryImage()
        with pytest.raises(MemoryAccessError, match="No data"):
            img.entire_load_range()

    def test_entire_load_range_spans_multiple_loads(self, tmp_path):
        a = tmp_path / "a.bin"
        a.write_bytes(b"\x00" * 0x10)
        b = tmp_path / "b.bin"
        b.write_bytes(b"\x00" * 0x10)
        img = MemoryImage()
        img.load(a, 0x8000)
        img.load(b, 0x9000)
        assert img.entire_load_range() == (BinaryAddr(0x8000), BinaryAddr(0x9010))

    def test_two_memory_images_are_independent(self, tmp_path):
        # The cleanup that justifies the rewrite from py8dis's
        # module-level globals: two MemoryImages MUST NOT share state.
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x42")
        img_a = MemoryImage()
        img_b = MemoryImage()
        img_a.load(binary_filepath, 0x8000)
        assert img_a.get_u8(0x8000) == 0x42
        assert not img_b.is_loaded(0x8000)
        with pytest.raises(MemoryAccessError):
            img_b.get_u8(0x8000)

    def test_custom_address_space_size(self, tmp_path):
        # 32-bit CPUs to come (ARM, 32016) will need larger spaces.
        # Storage is currently flat; tests that the size knob works
        # even before sparse storage lands.
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\x99")
        img = MemoryImage(address_space_size=0x20000)
        img.load(binary_filepath, 0x10000)
        assert img.get_u8(0x10000) == 0x99


class TestRuntimeView:

    def test_runtime_view_consults_resolver(self, tmp_path):
        binary_filepath = tmp_path / "a.bin"
        binary_filepath.write_bytes(b"\xAA\xBB")
        img = MemoryImage()
        img.load(binary_filepath, 0x8000)

        # Stub resolver: every runtime addr maps to the corresponding
        # binary addr at the load offset. Real one will consult the
        # MoveManager — see task #10. The explicit int() casts model
        # what a real resolver does: it crosses the typed-address
        # boundary deliberately, never by accident.
        def resolver(runtime_addr):
            offset = int(runtime_addr) - 0x9000
            return BinaryLocation(0x8000 + offset, 0)

        view = RuntimeView(img, resolver)
        assert view.get_u8(0x9000) == 0xAA
        assert view.get_u8(0x9001) == 0xBB
        assert view.get_u16_le(0x9000) == 0xBBAA
        assert view.get_u16_be(0x9000) == 0xAABB
