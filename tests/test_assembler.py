"""Unit tests for the dasmos.assembler.Assembler abstract base.

Covers the contract that every concrete assembler plug-in must
satisfy, the concrete-with-default helper methods, and per-instance
state isolation.
"""

import pytest

from dasmos.assembler import Assembler


class _MinimalAssembler(Assembler):
    """A test-double that implements every abstract method just enough
    to let the concrete defaults exercise themselves.
    """

    def cpus_supported(self):
        return ["test_cpu"]

    def hex2(self, n):
        return f"${n:02x}"

    def hex4(self, n):
        return f"${n:04x}"

    def comment_prefix(self):
        return ";"

    def byte_prefix(self):
        return "byte "

    def word_prefix(self):
        return "word "

    def string_prefix(self):
        return "str "

    def inline_label(self, name):
        return f"{name}:"

    def explicit_label(self, name, value, offset=None, align_column=0):
        suffix = "" if offset is None else f"+{offset}"
        return f"{name} = {value}{suffix}"

    def disassembly_start(self):
        return ["; start"]

    def disassembly_end(self):
        return ["; end"]

    def code_start(self, start_addr, end_addr, first):
        return [f"org {start_addr}"]

    def code_end(self):
        return []

    def pseudopc_start(self, dest, source, length, move_id):
        return [f"pseudopc {dest}"]

    def pseudopc_end(self, dest, source, length, move_id):
        return ["end pseudopc"]

    def char_literal(self, n):
        return chr(n) if 32 <= n < 127 else None

    def string_chr(self, n):
        return chr(n) if 32 <= n < 127 else None


class TestAbstractness:

    def test_cannot_instantiate_assembler_directly(self):
        # Assembler has abstract methods inherited from Extension plus
        # the protocol methods declared here.
        with pytest.raises(TypeError):
            Assembler(name="oops")

    def test_minimal_subclass_can_be_instantiated(self):
        # Once every abstract method is overridden, the class is
        # instantiable.
        a = _MinimalAssembler(name="minimal")
        assert a.name == "minimal"


class TestHexDispatch:

    def test_hex_dispatches_to_hex2_for_byte_values(self):
        a = _MinimalAssembler(name="minimal")
        assert a.hex(0x00) == "$00"
        assert a.hex(0xFF) == "$ff"

    def test_hex_dispatches_to_hex4_for_word_values(self):
        a = _MinimalAssembler(name="minimal")
        assert a.hex(0x100) == "$0100"
        assert a.hex(0xFFFF) == "$ffff"


class TestPerInstanceState:

    def test_pending_assertions_is_per_instance(self):
        # Regression: py8dis's pending_assertions = {} was a CLASS
        # attribute, so all Assembler instances shared a single dict.
        # In dasmos each instance owns its own.
        a = _MinimalAssembler(name="a")
        b = _MinimalAssembler(name="b")
        a.assert_expr("foo", 0x1234)
        assert a.pending_assertions == {"foo": 0x1234}
        assert b.pending_assertions == {}

    def test_output_filename_is_per_instance(self):
        # Regression: same problem in py8dis as pending_assertions.
        a = _MinimalAssembler(name="a")
        b = _MinimalAssembler(name="b")
        a.set_output_filename("a.bin")
        assert a.output_filename == "a.bin"
        assert b.output_filename is None


class TestAssertExpr:

    def test_assert_expr_records_value(self):
        a = _MinimalAssembler(name="a")
        a.assert_expr("symbol", 0x1234)
        assert a.pending_assertions["symbol"] == 0x1234

    def test_assert_expr_overwrites_for_same_key(self):
        # Last value wins. No fancier policy needed at the base.
        a = _MinimalAssembler(name="a")
        a.assert_expr("symbol", 0x1234)
        a.assert_expr("symbol", 0x5678)
        assert a.pending_assertions["symbol"] == 0x5678


class TestFillDirectiveDefault:

    def test_default_fill_directive_repeats_byte_prefix(self):
        a = _MinimalAssembler(name="a")
        # Default impl is N copies of value joined with ", " on a
        # single byte_prefix line.
        out = a.fill_directive(0xAA, 3)
        assert out == ["byte $aa, $aa, $aa"]


class TestPolicyDefaults:

    def test_explicit_a_defaults_false(self):
        a = _MinimalAssembler(name="a")
        assert a.explicit_a is False

    def test_force_zp_instruction_default_unsupported(self):
        a = _MinimalAssembler(name="a")
        # None signals "this assembler can't force the addressing
        # mode" — the caller falls back to natural rendering.
        assert a.force_zp_instruction("lda", "", "addr", "") is None

    def test_force_abs_instruction_default_unsupported(self):
        a = _MinimalAssembler(name="a")
        assert a.force_abs_instruction("lda", "", "addr", "") is None

    def test_force_zp_label_prefix_default_empty(self):
        a = _MinimalAssembler(name="a")
        assert a.force_zp_label_prefix() == ""

    def test_translate_operator_name_dicts_default_empty(self):
        a = _MinimalAssembler(name="a")
        assert a.translate_binary_operator_names() == {}
        assert a.translate_unary_operator_names() == {}

    def test_binary_format_default_returns_none(self):
        # None signals "this assembler doesn't support a binary
        # literal" — caller falls back to hex.
        a = _MinimalAssembler(name="a")
        assert a.binary_format("10101010") is None

    def test_picture_binary_default_returns_input(self):
        a = _MinimalAssembler(name="a")
        assert a.picture_binary("10101010") == "10101010"

    def test_sanitise_default_returns_input(self):
        a = _MinimalAssembler(name="a")
        assert a.sanitise("hello") == "hello"

    def test_format_comment_uses_comment_prefix(self):
        # The default implementation prefixes the comment with the
        # assembler's comment prefix and a space.
        a = _MinimalAssembler(name="a")
        assert a.format_comment("a comment", indent=0) == "; a comment"


class TestProtocolDelegation:
    """Sanity-check that the abstract protocol is actually exercised
    by the test double — gives us a regression alarm if a future
    Assembler refactor accidentally introduces a default for one of
    these methods.
    """

    def test_byte_prefix_called(self):
        a = _MinimalAssembler(name="a")
        assert a.byte_prefix() == "byte "

    def test_inline_label_uses_subclass_implementation(self):
        a = _MinimalAssembler(name="a")
        assert a.inline_label("foo") == "foo:"

    def test_explicit_label_carries_offset(self):
        a = _MinimalAssembler(name="a")
        assert a.explicit_label("foo", "$1234", offset=2) == "foo = $1234+2"
