"""Internal text utilities.

Small helpers used by :mod:`dasmos.extension` for rendering extension
descriptions. Internal (underscore-prefixed module) — not part of the
public API.
"""


def _is_blank(line: str) -> bool:
    return not line or line.isspace()


def strip_lines(text: str) -> str:
    """Remove leading and trailing blank lines.

    Args:
        text: The text to process.

    Returns:
        The text with any leading and trailing blank-or-whitespace-only lines
        removed. Interior blank lines are preserved.
    """
    lines = text.splitlines()
    start = 0
    while start < len(lines) and _is_blank(lines[start]):
        start += 1
    end = len(lines)
    while end > start and _is_blank(lines[end - 1]):
        end -= 1
    return "\n".join(lines[start:end])


def normalize_name(name: str) -> str:
    """Normalise a name by converting hyphens to underscores."""
    return name.replace("-", "_")


def first_line(text: str) -> str:
    """Extract the first non-empty line from text.

    Useful for displaying descriptions in tables where multi-line text wraps
    awkwardly.

    Args:
        text: The text to extract the first line from.

    Returns:
        The first non-empty line, stripped of leading/trailing whitespace.
        Returns empty string if text is empty or contains only whitespace.
    """
    if not text:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
