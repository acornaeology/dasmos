"""Unit tests for the :mod:`dasmos.core.format_hint` registry.

``FormatHint`` is the **semantic** marker that says how the byte at
a given operand address should be interpreted by a renderer (e.g.
"this byte is intended as an ASCII character"). It is deliberately
abstract — the choice of assembler-specific syntax (``ASC("c")`` vs
``'c'`` vs ``$67`` etc.) belongs to the renderer.

This is the registry-level test: round-tripping values, idempotency,
and the API shape. End-to-end rendering is exercised in the
per-renderer test files.
"""

import pytest

from dasmos.core.format_hint import FormatHint, FormatHintRegistry
from dasmos.core.memory import BinaryAddr


class TestFormatHintEnum:
    """The ``FormatHint`` enum is the contract between the driver
    API (which marks bytes) and renderers (which interpret marks).
    """

    def test_char_member_present(self):
        # The first defined hint. Everything else is future scope.
        assert hasattr(FormatHint, "CHAR")

    def test_char_value_is_stable_string(self):
        # Stable string values let JSON renderers serialise hints
        # without depending on the enum's internal numbering.
        assert FormatHint.CHAR.value == "char"


class TestFormatHintRegistry:

    def test_empty_registry_returns_none(self):
        reg = FormatHintRegistry()
        assert reg.get_or_none(0x8001) is None

    def test_add_then_lookup(self):
        reg = FormatHintRegistry()
        reg.add(0x8001, FormatHint.CHAR)
        assert reg.get_or_none(0x8001) is FormatHint.CHAR

    def test_membership_check(self):
        reg = FormatHintRegistry()
        reg.add(0x8001, FormatHint.CHAR)
        assert 0x8001 in reg
        assert 0x8002 not in reg

    def test_lookup_normalises_address_type(self):
        # Plain ``int`` and ``BinaryAddr`` should look up the same
        # entry — the registry stores by ``BinaryAddr`` internally.
        reg = FormatHintRegistry()
        reg.add(BinaryAddr(0x8001), FormatHint.CHAR)
        assert reg.get_or_none(0x8001) is FormatHint.CHAR
        assert reg.get_or_none(BinaryAddr(0x8001)) is FormatHint.CHAR

    def test_re_add_replaces_previous_hint(self):
        # Hints are typed and unambiguous — the latest call wins.
        # (Contrast with ExpressionRegistry, which is idempotent
        # because the user might register the same expression in
        # multiple passes.)
        reg = FormatHintRegistry()
        reg.add(0x8001, FormatHint.CHAR)
        # No other hint values defined yet, so re-add CHAR with
        # itself; the contract is "last write wins" regardless.
        reg.add(0x8001, FormatHint.CHAR)
        assert reg.get_or_none(0x8001) is FormatHint.CHAR

    def test_get_raises_keyerror_when_missing(self):
        reg = FormatHintRegistry()
        with pytest.raises(KeyError):
            reg.get(0x8001)

    def test_get_returns_value_when_present(self):
        reg = FormatHintRegistry()
        reg.add(0x8001, FormatHint.CHAR)
        assert reg.get(0x8001) is FormatHint.CHAR
