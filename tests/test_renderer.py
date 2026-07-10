"""Unit tests for dasmos.renderer.

Covers the contract every renderer plug-in must satisfy:

- :class:`Renderer` — the extension boundary; abstract ``render(ir)``.
- :class:`TextRenderer` — adds the assembler-syntax protocol that
  every text renderer must implement; concrete-with-default helpers.
- :class:`StructuredRenderer` — convenience marker for
  data-emitting renderers; no extra protocol.

The contract previously lived on a single ``Assembler`` class — see
``docs/design/decisions.md`` D-003 for the rename rationale.
"""

import pytest

from dasmos.renderer import Renderer, StructuredRenderer, TextRenderer
from dasmos.output import StructuredOutput, TextOutput


class _MinimalTextRenderer(TextRenderer):
    """Test double implementing every abstract method just enough to
    let the concrete defaults exercise themselves.
    """

    def render(self, ir):
        return TextOutput("rendered")

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

    def set_origin(self, addr):
        return [f"org {addr}"]

    def pseudopc_start(self, *, dest, src, length, move_id,
                       src_label, dest_label):
        return [f"pseudopc {dest}"]

    def pseudopc_end(self, *, dest, src, length, move_id,
                     src_label, dest_label):
        return ["end pseudopc"]

    def char_literal(self, n):
        return chr(n) if 32 <= n < 127 else None

    def string_chr(self, n):
        return chr(n) if 32 <= n < 127 else None


class _MinimalStructuredRenderer(StructuredRenderer):
    """Test double for the structured-output side of the contract."""

    def render(self, ir):
        return StructuredOutput({"rendered": True})


class TestExtensionBoundary:

    def test_renderer_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            Renderer(name="oops")

    def test_text_renderer_cannot_be_instantiated_without_overrides(self):
        with pytest.raises(TypeError):
            TextRenderer(name="oops")

    def test_structured_renderer_cannot_be_instantiated_without_render(self):
        # StructuredRenderer doesn't add abstracts, but it inherits
        # render() abstract from Renderer.
        with pytest.raises(TypeError):
            StructuredRenderer(name="oops")

    def test_minimal_text_renderer_can_be_instantiated(self):
        r = _MinimalTextRenderer(name="minimal")
        assert r.name == "minimal"
        assert r.kind() == "renderer"

    def test_minimal_structured_renderer_can_be_instantiated(self):
        r = _MinimalStructuredRenderer(name="minimal")
        assert r.name == "minimal"
        assert r.kind() == "renderer"


class TestRender:

    def test_text_renderer_returns_text_output(self):
        r = _MinimalTextRenderer(name="t")
        out = r.render(ir=None)
        assert isinstance(out, TextOutput)
        assert str(out) == "rendered"

    def test_structured_renderer_returns_structured_output(self):
        r = _MinimalStructuredRenderer(name="s")
        out = r.render(ir=None)
        assert isinstance(out, StructuredOutput)
        assert out.data == {"rendered": True}


class TestHexDispatch:

    def test_hex_dispatches_to_hex2_for_byte_values(self):
        r = _MinimalTextRenderer(name="r")
        assert r.hex(0x00) == "$00"
        assert r.hex(0xFF) == "$ff"

    def test_hex_dispatches_to_hex4_for_word_values(self):
        r = _MinimalTextRenderer(name="r")
        assert r.hex(0x100) == "$0100"
        assert r.hex(0xFFFF) == "$ffff"


class TestPerInstanceState:

    def test_pending_assertions_is_per_instance(self):
        # Regression: py8dis kept pending_assertions = {} as a CLASS
        # attribute. dasmos puts it on the instance.
        a = _MinimalTextRenderer(name="a")
        b = _MinimalTextRenderer(name="b")
        a.assert_expr("foo", 0x1234)
        assert a.pending_assertions == {"foo": 0x1234}
        assert b.pending_assertions == {}

    def test_output_filename_is_per_instance(self):
        a = _MinimalTextRenderer(name="a")
        b = _MinimalTextRenderer(name="b")
        a.set_output_filename("a.bin")
        assert a.output_filename == "a.bin"
        assert b.output_filename is None


class TestPolicyDefaults:

    def test_explicit_a_defaults_false(self):
        assert _MinimalTextRenderer(name="r").explicit_a is False

    def test_force_zp_instruction_default_returns_none(self):
        r = _MinimalTextRenderer(name="r")
        assert r.force_zp_instruction("lda", "", "addr", "") is None

    def test_force_abs_instruction_default_returns_none(self):
        r = _MinimalTextRenderer(name="r")
        assert r.force_abs_instruction("lda", "", "addr", "") is None

    def test_force_zp_label_prefix_default_empty(self):
        assert _MinimalTextRenderer(name="r").force_zp_label_prefix() == ""

    def test_translate_operator_dicts_default_empty(self):
        r = _MinimalTextRenderer(name="r")
        assert r.translate_binary_operator_names() == {}
        assert r.translate_unary_operator_names() == {}

    def test_binary_format_default_returns_none(self):
        assert _MinimalTextRenderer(name="r").binary_format("10101010") is None

    def test_picture_binary_default_returns_input(self):
        assert _MinimalTextRenderer(name="r").picture_binary("10101010") == "10101010"

    def test_sanitise_default_returns_input(self):
        assert _MinimalTextRenderer(name="r").sanitise("hello") == "hello"

    def test_format_comment_uses_comment_prefix(self):
        assert (
            _MinimalTextRenderer(name="r").format_comment("a comment", indent=0)
            == "; a comment"
        )


class TestFillDirectiveDefault:

    def test_default_repeats_byte_prefix(self):
        r = _MinimalTextRenderer(name="r")
        assert r.fill_directive(0xAA, 3) == ["byte $aa, $aa, $aa"]
