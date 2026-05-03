"""Unit tests for dasmos.output.

The Output / TextOutput / StructuredOutput types are the contract
between renderers and their callers: every renderer returns an Output,
every Output is convertible to string via __str__, and structured
outputs additionally expose their data.
"""

import json

import pytest

from dasmos.output import Output, StructuredOutput, TextOutput


class TestOutputABC:

    def test_output_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Output()  # type: ignore[abstract]

    def test_text_output_is_an_output(self):
        assert isinstance(TextOutput("hi"), Output)

    def test_structured_output_is_an_output(self):
        assert isinstance(StructuredOutput({}), Output)


class TestTextOutput:

    def test_str_returns_the_text(self):
        out = TextOutput("hello\nworld")
        assert str(out) == "hello\nworld"

    def test_lines_splits_on_line_boundaries(self):
        out = TextOutput("a\nb\nc")
        assert out.lines() == ["a", "b", "c"]

    def test_lines_for_empty_text(self):
        out = TextOutput("")
        assert out.lines() == []

    def test_repr_is_truncated_for_long_text(self):
        out = TextOutput("x" * 100)
        rep = repr(out)
        assert "TextOutput(" in rep
        assert "length=100" in rep


class TestStructuredOutput:

    def test_str_serialises_to_json(self):
        out = StructuredOutput({"a": 1, "b": [2, 3]})
        # Round-trip through json.loads to make the test indent-agnostic.
        assert json.loads(str(out)) == {"a": 1, "b": [2, 3]}

    def test_str_uses_configured_indent(self):
        out = StructuredOutput({"a": 1}, indent=4)
        # Two-space indent would show 'a' at column 2; four-space at column 4.
        assert '\n    "a"' in str(out)

    def test_str_with_no_indent(self):
        out = StructuredOutput({"a": 1, "b": 2}, indent=None)
        # Compact form has no newlines.
        assert "\n" not in str(out)

    def test_data_returns_the_underlying_data(self):
        d = {"a": 1, "b": 2}
        out = StructuredOutput(d)
        assert out.data is d

    def test_data_is_read_only_view_of_input(self):
        # Caller can mutate the data dict — we don't deep-copy on
        # construction. This documents the live-wrapper behaviour.
        d = {"a": 1}
        out = StructuredOutput(d)
        d["b"] = 2
        assert out.data == {"a": 1, "b": 2}


class TestUniformWriteIdiom:
    """The whole point of Output: same write-to-file works for any
    renderer's output type.
    """

    def test_text_output_can_be_written_via_str(self, tmp_path):
        out = TextOutput("hello world\n")
        path = tmp_path / "out.txt"
        path.write_text(str(out), encoding="utf-8")
        assert path.read_text(encoding="utf-8") == "hello world\n"

    def test_structured_output_can_be_written_via_str(self, tmp_path):
        out = StructuredOutput({"hello": "world"})
        path = tmp_path / "out.json"
        path.write_text(str(out), encoding="utf-8")
        assert json.loads(path.read_text(encoding="utf-8")) == {"hello": "world"}
