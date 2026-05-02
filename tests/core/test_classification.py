"""Unit tests for dasmos.core.classification.

Covers the polymorphic data classifications (Byte, Word, Fill, String)
and the ExpressionRegistry. The string-scanning algorithms and the
rendering methods from py8dis's classification.py are deliberately
deferred — they belong to the disassembly engine port (task #12) and
the assembler/formatter port (task #14) respectively.
"""

import pytest

from dasmos.core.classification import (
    Byte,
    Classification,
    ClassificationError,
    ExpressionRegistry,
    Fill,
    String,
    Word,
)
from dasmos.core.memory import BinaryAddr


class TestClassificationABC:

    def test_abstract_base_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Classification()  # type: ignore[abstract]

    def test_concrete_classes_subclass_classification(self):
        assert issubclass(Byte, Classification)
        assert issubclass(Word, Classification)
        assert issubclass(Fill, Classification)
        assert issubclass(String, Classification)

    def test_is_code_default_false(self):
        # Every data classification reports is_code() == False; the
        # Opcode subclass (lifted with the CPU port) is the only thing
        # that overrides this to True.
        assert Byte(1).is_code() is False
        assert Word(2).is_code() is False
        assert Fill(1, 0).is_code() is False
        assert String(1).is_code() is False


class TestByte:

    def test_records_length(self):
        b = Byte(8)
        assert b.length() == 8

    def test_default_cols_is_none(self):
        b = Byte(8)
        assert b.cols() is None

    def test_explicit_cols_is_carried(self):
        b = Byte(8, cols=4)
        assert b.cols() == 4

    def test_rejects_zero_or_negative_length(self):
        with pytest.raises(ClassificationError, match="length"):
            Byte(0)
        with pytest.raises(ClassificationError, match="length"):
            Byte(-1)

    def test_rejects_zero_or_negative_cols(self):
        with pytest.raises(ClassificationError, match="cols"):
            Byte(8, cols=0)
        with pytest.raises(ClassificationError, match="cols"):
            Byte(8, cols=-1)

    def test_set_length(self):
        b = Byte(4)
        b.set_length(8)
        assert b.length() == 8

    def test_set_length_rejects_invalid(self):
        b = Byte(4)
        with pytest.raises(ClassificationError, match="length"):
            b.set_length(0)


class TestWord:

    def test_records_length(self):
        w = Word(4)
        assert w.length() == 4

    def test_rejects_odd_length(self):
        with pytest.raises(ClassificationError, match="even"):
            Word(3)

    def test_rejects_zero_or_negative_length(self):
        with pytest.raises(ClassificationError, match="length"):
            Word(0)
        with pytest.raises(ClassificationError, match="length"):
            Word(-2)

    def test_set_length_rejects_odd(self):
        w = Word(2)
        with pytest.raises(ClassificationError, match="even"):
            w.set_length(3)


class TestFill:

    def test_records_length_and_value(self):
        f = Fill(16, 0xAA)
        assert f.length() == 16
        assert f.value() == 0xAA

    def test_value_zero_is_valid(self):
        # The most common fill value is 0.
        Fill(1, 0)

    def test_value_max_byte_is_valid(self):
        Fill(1, 0xFF)

    def test_rejects_value_out_of_byte_range(self):
        with pytest.raises(ClassificationError, match="value"):
            Fill(1, -1)
        with pytest.raises(ClassificationError, match="value"):
            Fill(1, 0x100)

    def test_rejects_zero_or_negative_length(self):
        with pytest.raises(ClassificationError, match="length"):
            Fill(0, 0)


class TestString:

    def test_records_length(self):
        s = String(12)
        assert s.length() == 12

    def test_rejects_zero_or_negative_length(self):
        with pytest.raises(ClassificationError, match="length"):
            String(0)

    def test_set_length(self):
        s = String(4)
        s.set_length(8)
        assert s.length() == 8

    def test_does_not_capture_caller_stack(self):
        # py8dis's String.__init__ called find_external_callstack() and
        # held the result on every instance for diagnostic logging
        # purposes — an expensive side effect inside __init__. Dropped
        # in dasmos: a String is just a length.
        s = String(4)
        assert not hasattr(s, "_caller")


class TestExpressionRegistry:

    def test_empty_registry_does_not_contain_anything(self):
        reg = ExpressionRegistry()
        assert BinaryAddr(0x8000) not in reg

    def test_add_makes_address_visible(self):
        reg = ExpressionRegistry()
        reg.add(BinaryAddr(0x8000), "foo + 1")
        assert BinaryAddr(0x8000) in reg
        assert reg.get(BinaryAddr(0x8000)) == "foo + 1"

    def test_add_does_not_overwrite_existing(self):
        # Behaviour preserved from py8dis: the first add wins; later
        # adds for the same address are silently ignored. Allowing
        # this lets multi-pass classifiers be idempotent without
        # special-casing.
        reg = ExpressionRegistry()
        reg.add(BinaryAddr(0x8000), "first")
        reg.add(BinaryAddr(0x8000), "second")
        assert reg.get(BinaryAddr(0x8000)) == "first"

    def test_get_unknown_raises_key_error(self):
        reg = ExpressionRegistry()
        with pytest.raises(KeyError):
            reg.get(BinaryAddr(0x8000))

    def test_get_or_none_unknown_returns_none(self):
        reg = ExpressionRegistry()
        assert reg.get_or_none(BinaryAddr(0x8000)) is None

    def test_get_or_none_known_returns_expression(self):
        reg = ExpressionRegistry()
        reg.add(BinaryAddr(0x8000), "foo + 1")
        assert reg.get_or_none(BinaryAddr(0x8000)) == "foo + 1"

    def test_two_registries_are_independent(self):
        # The justification for the rewrite — module-level expressions
        # dict in py8dis prevented this property.
        reg_a = ExpressionRegistry()
        reg_b = ExpressionRegistry()
        reg_a.add(BinaryAddr(0x8000), "in_a")
        assert reg_b.get_or_none(BinaryAddr(0x8000)) is None
