"""Render Markdown comment / description text as plaintext for asm.

Driver scripts write rich source text — full CommonMark plus GFM
tables, plus the custom ``[label](address:HEX[?hex])`` cross-
reference links documented in the acornaeology authoring guide
(``acornaeology.github.io/AUTHORING.md`` §1, §2). The structured
JSON renderer keeps that source verbatim so downstream HTML
processors can resolve the markdown to real anchors. Text-syntax
renderers (BeebasmRenderer etc.) feed the source through THIS
module first to strip the markup the assembler doesn't care about:

- Paragraphs are word-wrapped to a configurable width.
- Lists carry plain-text bullets (``-`` or ``N.``).
- Tables render as pipe tables with padded columns.
- Fenced code blocks indent four spaces with a ``[lang]`` banner.
- Emphasis / strong / inline-code markers strip away.
- ``[label](address:HEX)`` collapses to ``label`` (or
  ``label (&HEX)`` with the ``?hex`` flag).
- Ordinary Markdown links collapse to their label text.
- ``@VERSION`` qualifiers are silently dropped (asm context is
  always the current version).

Two entry points:

- :func:`markdown_to_asm_text` — full CommonMark parse via
  ``mistletoe``. Use when the caller wants markdown structure to be
  honoured (paragraphs / lists / tables in subroutine descriptions).
- :func:`strip_address_uri_links` — regex-only stripper that
  preserves literal text layout. Use when the source is already
  plaintext-shaped (banner separators with rows of asterisks would
  be turned into thematic breaks by the markdown parser).
"""

from __future__ import annotations

import re
import textwrap
import warnings


# Match the ``[label](address:HEX[@version][?flag])`` shape used in
# acornaeology driver scripts. Capture the label, the hex (4+ digits),
# and the optional flag — the optional ``@version`` is ignored in asm
# output (a comment in a listing always refers to the current version,
# so the version qualifier is redundant here, even though downstream
# site-gen needs it for cross-version pages).
_ADDRESS_URI_LINK_RE = re.compile(
    r"\[(?P<label>[^\]\[]+)\]\(address:"
    r"(?P<hex>[0-9A-Fa-f]{4,})"
    r"(?:@[^)?]+)?"
    r"(?:\?(?P<flag>[^)]*))?"
    r"\)",
    re.IGNORECASE,
)

# Same shape but as the ``target`` of a parsed mistletoe Link token.
# The label is gone (mistletoe gives it as the link's children), and
# we just care about the hex / flag here.
_ADDRESS_URI_TARGET_RE = re.compile(
    r"^address:"
    r"(?P<hex>[0-9A-Fa-f]{4,})"
    r"(?:@[^?]+)?"
    r"(?:\?(?P<flag>[^&]*))?"
    r"$",
    re.IGNORECASE,
)


# Track flags we've already warned about so each unknown flag fires
# only ONCE per process. Without this, a 1000-line driver with a
# typo'd flag would emit 1000 warnings.
_warned_flags: set[str] = set()


def strip_address_uri_links(text: str) -> str:
    """Replace ``[label](address:HEX[?hex])`` with plain text — no
    markdown parser involved, just the regex.

    Use when the surrounding text needs to keep its literal layout
    (banner separators, ASCII-art tables) and full Markdown parsing
    would re-flow whitespace, drop blank lines, or interpret rows of
    punctuation as thematic breaks.

    Without a flag: the link collapses to the label text alone:
        ``see [foo](address:E000)`` → ``see foo``

    With ``?hex``: the hex is appended uppercased in parentheses:
        ``see [foo](address:E000?hex)`` → ``see foo (&E000)``

    An ``@version`` suffix is silently stripped. Unknown flags warn
    once per flag value and collapse as if no flag were present.
    Backticks around the label are removed (they're HTML-only
    decoration).
    """

    def rewrite(match: re.Match[str]) -> str:
        label = match.group("label").replace("`", "")
        hex_str = match.group("hex")
        flag = (match.group("flag") or "").lower()
        if not flag:
            return label
        if flag == "hex":
            return f"{label} (&{hex_str.upper()})"
        if flag not in _warned_flags:
            _warned_flags.add(flag)
            warnings.warn(
                f"unknown flag '?{flag}' in address: URI — "
                f"rendering label only in asm output",
                stacklevel=2,
            )
        return label

    return _ADDRESS_URI_LINK_RE.sub(rewrite, text)


def markdown_to_asm_text(
    text: str,
    *,
    inline: bool = False,
    wrap_width: int | None = None,
) -> str:
    """Render ``text`` (CommonMark + GFM tables) as plaintext for asm.

    - ``inline=True`` collapses the rendered output to a single line,
      suitable for an inline ``;`` comment after an instruction.
    - ``wrap_width=N`` wraps prose paragraphs and list items at column
      N. Tables and code fences are laid out structurally and ignore
      the wrap.

    Returns the plaintext with paragraphs separated by blank lines and
    no trailing newline.
    """
    import mistletoe
    with _AsmTextRenderer(wrap_width=wrap_width, inline=inline) as renderer:
        doc = mistletoe.Document(text)
        return renderer.render(doc)


# ----------------------------------------------------------------------
# Internals: mistletoe renderer that emits asm-comment plaintext.
# ----------------------------------------------------------------------

from mistletoe.base_renderer import BaseRenderer  # noqa: E402


class _AsmTextRenderer(BaseRenderer):
    """Render a mistletoe Document as asm-comment plaintext.

    Public callers go through :func:`markdown_to_asm_text`; this
    class is the mistletoe-side machinery.
    """

    def __init__(self, wrap_width: int | None = None, inline: bool = False):
        super().__init__()
        self.wrap_width = wrap_width
        self.inline = inline
        self._indent = ""
        self._list_markers: list[tuple[str, int | None]] = []

    # -- document --------------------------------------------------

    def render_document(self, token):
        text = self.render_inner(token).rstrip("\n")
        if self.inline:
            text = re.sub(r"\s+", " ", text).strip()
        return text

    # -- block tokens ---------------------------------------------

    def render_paragraph(self, token):
        text = self.render_inner(token)
        if self.wrap_width and not self.inline:
            text = textwrap.fill(
                text, width=self.wrap_width,
                break_long_words=False, break_on_hyphens=False,
            )
        return text + "\n\n"

    def render_heading(self, token):
        return self.render_inner(token) + "\n\n"

    def render_quote(self, token):
        inner = self.render_inner(token).rstrip("\n")
        quoted = "\n".join(
            "> " + line if line else ">" for line in inner.split("\n")
        )
        return quoted + "\n\n"

    def render_thematic_break(self, token):
        return "----\n\n"

    def render_list(self, token):
        start = getattr(token, "start", None)
        if start is None:
            self._list_markers.append(("unordered", None))
        else:
            self._list_markers.append(("ordered", start))
        try:
            inner = self.render_inner(token).rstrip("\n")
        finally:
            self._list_markers.pop()
        return inner + "\n\n"

    def render_list_item(self, token):
        kind, counter = self._list_markers[-1]
        if kind == "ordered":
            marker = f"{counter}. "
            self._list_markers[-1] = ("ordered", counter + 1)
        else:
            marker = "- "
        outer_indent = self._indent
        marker_indent = outer_indent + " " * len(marker)
        self._indent = marker_indent
        try:
            body = self.render_inner(token).rstrip("\n")
        finally:
            self._indent = outer_indent

        if not body:
            return outer_indent + marker + "\n"

        wrapped_paragraphs = []
        first = True
        for para in _split_paragraphs(body):
            if self.wrap_width and _should_wrap(para):
                init = (outer_indent + marker) if first else marker_indent
                wrapped = textwrap.fill(
                    para, width=self.wrap_width,
                    initial_indent=init, subsequent_indent=marker_indent,
                    break_long_words=False, break_on_hyphens=False,
                )
                wrapped_paragraphs.append(wrapped)
            else:
                lines = para.split("\n")
                out_lines = []
                for i, line in enumerate(lines):
                    prefix = (outer_indent + marker) if (first and i == 0) \
                        else marker_indent
                    out_lines.append(prefix + line if line else "")
                wrapped_paragraphs.append("\n".join(out_lines))
            first = False
        return "\n\n".join(wrapped_paragraphs) + "\n"

    def render_table(self, token):
        header = token.header
        header_cells = [self._render_cell(c) for c in header.children]
        body_rows = []
        for row in token.children:
            body_rows.append([self._render_cell(c) for c in row.children])
        col_count = len(header_cells)
        widths = [len(h) for h in header_cells]
        for row in body_rows:
            for i, cell in enumerate(row):
                if i < col_count:
                    widths[i] = max(widths[i], len(cell))

        def format_row(cells):
            padded = [
                cells[i].ljust(widths[i])
                if i < len(cells) else " " * widths[i]
                for i in range(col_count)
            ]
            return "| " + " | ".join(padded) + " |"

        sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        lines = [format_row(header_cells), sep]
        for row in body_rows:
            lines.append(format_row(row))
        return "\n".join(lines) + "\n\n"

    def render_table_row(self, token):
        return ""

    def render_table_cell(self, token):
        return self._render_cell(token)

    def _render_cell(self, token):
        return self.render_inner(token).strip()

    def render_block_code(self, token):
        content = getattr(token, "content", None)
        if content is None:
            content = "".join(
                getattr(c, "content", "") for c in token.children
            )
        content = content.rstrip("\n")
        language = getattr(token, "language", "") or ""
        body_lines = [
            "    " + line if line else "" for line in content.split("\n")
        ]
        out = "\n".join(body_lines)
        if language:
            out = f"[{language}]\n" + out
        return out + "\n\n"

    # -- span tokens -----------------------------------------------

    def render_strong(self, token):
        return self.render_inner(token)

    def render_emphasis(self, token):
        return self.render_inner(token)

    def render_strikethrough(self, token):
        return self.render_inner(token)

    def render_inline_code(self, token):
        return self.render_inner(token)

    def render_line_break(self, token):
        return "\n" if not getattr(token, "soft", False) else " "

    def render_raw_text(self, token):
        return token.content

    def render_escape_sequence(self, token):
        return self.render_inner(token)

    def render_link(self, token):
        label = self.render_inner(token)
        target = getattr(token, "target", "") or ""
        match = _ADDRESS_URI_TARGET_RE.match(target)
        if match:
            flag = (match.group("flag") or "").lower()
            hex_str = match.group("hex")
            if flag == "hex":
                return f"{label} (&{hex_str.upper()})"
            if flag and flag not in _warned_flags:
                _warned_flags.add(flag)
                warnings.warn(
                    f"unknown flag '?{flag}' in address: URI — "
                    f"rendering label only in asm output",
                    stacklevel=2,
                )
            return label
        # Ordinary URLs collapse to label text — asm has no hypertext.
        return label

    def render_auto_link(self, token):
        return getattr(token, "target", self.render_inner(token))

    def render_image(self, token):
        return self.render_inner(token)


def _split_paragraphs(text: str) -> list[str]:
    """Split a block of rendered text into paragraphs separated by
    one or more blank lines, returning a list of paragraph strings
    with no trailing/leading blank lines.
    """
    out = []
    current = []
    for line in text.split("\n"):
        if line.strip() == "":
            if current:
                out.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        out.append("\n".join(current))
    return out


def _should_wrap(paragraph: str) -> bool:
    """Heuristic: prose paragraphs wrap; structural blocks don't.

    Tables (pipe-starting lines) and indented code blocks are left
    alone so their layout survives.
    """
    first = paragraph.lstrip().splitlines()[0] if paragraph else ""
    if first.startswith("|") or first.startswith("    ") or first.startswith("["):
        return False
    return True
