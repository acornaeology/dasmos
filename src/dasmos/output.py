"""Renderer output types.

Every :class:`~dasmos.renderer.Renderer` returns a subclass of
:class:`Output`. ``Output`` is always convertible to ``str`` via
``__str__``; concrete subclasses can expose richer accessors for
callers that want structured data without going through serialisation
and back.

This means a uniform write-to-file idiom works for every output type:

.. code-block:: python

    Path("out.asm").write_text(str(beebasm_output))
    Path("out.json").write_text(str(json_output))

…while structured renderers still expose their data:

.. code-block:: python

    data: dict = json_output.data
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any


class Output(ABC):
    """Base class for renderer output. Always stringifiable."""

    @abstractmethod
    def __str__(self) -> str:
        """Return the canonical serialised form."""


class TextOutput(Output):
    """Output produced by a text-syntax renderer (Beebasm, ca65, …)."""

    def __init__(self, text: str):
        self._text = text

    def __str__(self) -> str:
        return self._text

    def lines(self) -> list[str]:
        """Return the output split on line boundaries."""
        return self._text.splitlines()

    def __repr__(self) -> str:
        head = self._text[:60].replace("\n", "\\n")
        suffix = "…" if len(self._text) > 60 else ""
        return f"TextOutput({head!r}{suffix}, length={len(self._text)})"


class StructuredOutput(Output):
    """Output produced by a data-emitting renderer (Json, …).

    The underlying ``data`` is exposed for direct structured access via
    :attr:`data`. ``__str__`` serialises it to JSON with the configured
    indent; if a different serialisation is wanted, use ``data``
    directly and serialise yourself.
    """

    def __init__(self, data: Any, *, indent: int | None = 2):
        self._data = data
        self._indent = indent

    @property
    def data(self) -> Any:
        return self._data

    def __str__(self) -> str:
        return json.dumps(self._data, indent=self._indent)

    def __repr__(self) -> str:
        return f"StructuredOutput(data={type(self._data).__name__})"
