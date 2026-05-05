"""Tests for ``dasmos.core.markdown_asm`` — the Markdown-to-asm
plaintext renderer used by text-syntax renderers (BeebasmRenderer
etc.) when collapsing rich-comment source text down to the kind of
text that fits inside a ``;`` comment.

Each driver-script ``comment(addr, text, ...)`` call stores ``text``
verbatim in the IR. Structured renderers (JsonRenderer) keep it
intact so downstream HTML processors can resolve the markdown to
real anchors. Text renderers (BeebasmRenderer) feed it through this
module FIRST to strip markup the assembler doesn't care about.

The authoring conventions this module supports are documented at
``acornaeology.github.io/AUTHORING.md`` (§1 Inline-comment Markdown,
§2 Block markdown in subroutine descriptions). Address links use
the custom ``[label](address:HEX[?hex])`` URI scheme.
"""

import pytest

from dasmos.core.markdown_asm import (
    markdown_to_asm_text,
    strip_address_uri_links,
)


class TestStripAddressUriLinks:
    """The minimal regex-only stripper used when the caller wants to
    preserve literal text layout (e.g. banner separators with rows of
    asterisks would be munged by full Markdown parsing). Strips just
    the custom address-link syntax.
    """

    def test_no_links_passes_through(self):
        assert strip_address_uri_links("plain text, no links") == \
            "plain text, no links"

    def test_simple_link_collapses_to_label(self):
        assert strip_address_uri_links("see [foo](address:E000)") == \
            "see foo"

    def test_hex_flag_appends_hex(self):
        assert strip_address_uri_links(
            "call [foo](address:E000?hex)"
        ) == "call foo (&E000)"

    def test_hex_flag_uppercases_hex(self):
        assert strip_address_uri_links(
            "[bar](address:abcd?hex)"
        ) == "bar (&ABCD)"

    def test_version_qualifier_is_stripped(self):
        # @VERSION is for cross-version site-gen output; in asm it's
        # silently dropped.
        assert strip_address_uri_links(
            "[bar](address:E000@1.10)"
        ) == "bar"

    def test_version_with_hex_flag(self):
        assert strip_address_uri_links(
            "[bar](address:E000@1.10?hex)"
        ) == "bar (&E000)"

    def test_backticks_around_label_are_stripped(self):
        # The author may wrap the label in backticks for HTML <code>
        # styling. In asm those are decoration, drop them.
        assert strip_address_uri_links(
            "see [`foo`](address:E000)"
        ) == "see foo"

    def test_multiple_links_in_one_text(self):
        text = ("call [a](address:E000) then [b](address:F000?hex)")
        assert strip_address_uri_links(text) == \
            "call a then b (&F000)"

    def test_unknown_flag_falls_back_to_label_only(self):
        # Unknown flags should not raise; collapse to label.
        assert strip_address_uri_links(
            "[foo](address:E000?weird)"
        ) == "foo"


class TestMarkdownToAsmTextInline:
    """Inline mode: collapse the whole document to a single line
    suitable for a trailing ``;`` comment after an instruction. All
    block structure flattens to spaces.
    """

    def test_empty_string(self):
        assert markdown_to_asm_text("", inline=True) == ""

    def test_plain_text_passes_through(self):
        assert markdown_to_asm_text("plain text", inline=True) == \
            "plain text"

    def test_emphasis_markers_stripped(self):
        assert markdown_to_asm_text(
            "see *foo* and **bar**", inline=True,
        ) == "see foo and bar"

    def test_inline_code_backticks_stripped(self):
        assert markdown_to_asm_text(
            "use `LDA #&7c` here", inline=True,
        ) == "use LDA #&7c here"

    def test_address_link_no_flag_gives_label(self):
        assert markdown_to_asm_text(
            "see [foo](address:E000)", inline=True,
        ) == "see foo"

    def test_address_link_hex_flag_gives_label_and_hex(self):
        assert markdown_to_asm_text(
            "call [foo](address:E000?hex)", inline=True,
        ) == "call foo (&E000)"

    def test_ordinary_url_collapses_to_label(self):
        # Asm has no hypertext; ordinary links drop the URL.
        assert markdown_to_asm_text(
            "[website](https://example.com)", inline=True,
        ) == "website"

    def test_multiline_collapses_to_single_line(self):
        assert markdown_to_asm_text(
            "line one\nline two", inline=True,
        ) == "line one line two"


class TestMarkdownToAsmTextBlock:
    """Block (non-inline) mode: paragraphs separated by blank lines,
    lists with bullet markers, tables as pipe layout.
    """

    def test_single_paragraph(self):
        assert markdown_to_asm_text("a paragraph") == "a paragraph"

    def test_two_paragraphs_separated_by_blank_line(self):
        assert markdown_to_asm_text("first\n\nsecond") == "first\n\nsecond"

    def test_unordered_list(self):
        out = markdown_to_asm_text("- one\n- two\n- three")
        assert out == "- one\n- two\n- three"

    def test_ordered_list(self):
        out = markdown_to_asm_text("1. one\n2. two\n3. three")
        assert "1. one" in out
        assert "2. two" in out
        assert "3. three" in out

    def test_code_fence_indented_with_language_banner(self):
        out = markdown_to_asm_text("```6502\nLDA #&55\n```")
        assert "[6502]" in out
        assert "    LDA #&55" in out

    def test_address_link_in_paragraph(self):
        out = markdown_to_asm_text(
            "Calls [setup](address:E000?hex) before exiting."
        )
        assert "Calls setup (&E000) before exiting." in out

    def test_word_wrap_at_specified_width(self):
        text = "This is a fairly long sentence that should wrap."
        out = markdown_to_asm_text(text, wrap_width=20)
        # Each emitted line is <= 20 chars (modulo the no-break-on-
        # hyphens / no-break-long-words guards).
        for line in out.split("\n"):
            assert len(line) <= 30, f"line too long: {line!r}"

    def test_table_renders_as_pipe_layout(self):
        text = (
            "| Reg | Use     |\n"
            "|-----|---------|\n"
            "| A   | call    |\n"
            "| X   | param   |\n"
        )
        out = markdown_to_asm_text(text)
        # Contains the column headers, separator, and rows in pipe
        # form (we don't pin the exact spacing — just structural).
        assert "| Reg" in out
        assert "| Use" in out
        assert "| A" in out
        assert "| X" in out


class TestHtmlEntityUnescape:
    """HTML named / numeric entities in Markdown source — expanded to
    their Unicode equivalents in the asm output. Authors mix raw
    arrows (``→``) and entity refs (``&rarr;``) interchangeably; the
    asm output should normalise to the raw character.
    """

    def test_named_entity_arrow_becomes_unicode(self):
        assert markdown_to_asm_text("A &rarr; B", inline=True) == "A → B"

    def test_named_entity_amp_becomes_ampersand(self):
        # Ampersand is the canonical case — `&amp;` → `&`. Important
        # because Markdown source authored alongside HTML often
        # double-escapes when the original asm semantics use ``&``
        # (the BBC hex sigil) literally.
        assert markdown_to_asm_text("A &amp; B", inline=True) == "A & B"

    def test_decimal_numeric_entity_arrow(self):
        # &#8594; is the decimal numeric form of →.
        assert markdown_to_asm_text("A &#8594; B", inline=True) == "A → B"

    def test_hex_numeric_entity_arrow(self):
        # &#x2192; is the hex numeric form of →.
        assert markdown_to_asm_text("A &#x2192; B", inline=True) == "A → B"

    def test_entity_inside_table_cell(self):
        # The originally-reported case: a Markdown table whose cells
        # contain ``&rarr;`` should render with ``→`` in the pipe
        # layout.
        text = (
            "| stage | direction |\n"
            "|-------|-----------|\n"
            "| SCOUT | A &rarr; B |\n"
        )
        out = markdown_to_asm_text(text)
        assert "A → B" in out
        assert "&rarr;" not in out

    def test_unicode_arrow_passes_through_untouched(self):
        # Already-Unicode arrows must NOT be double-processed.
        assert markdown_to_asm_text("A → B", inline=True) == "A → B"
