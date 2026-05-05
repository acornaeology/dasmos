"""Intermediate Representation — the disassembly model exposed to renderers.

The :class:`IntermediateRepresentation` is what
:meth:`Disassembler.disassemble <dasmos.disassembler.Disassembler.disassemble>`
returns. It is a **live read-only wrapper** over the Disassembler's
manager classes — there is no deep copy, so it is cheap to obtain and
inexpensive to discard.

The contract is "read-only by convention". The IR exposes the
underlying manager objects (which themselves have read methods).
Renderers should not call mutating methods on the manager objects;
nothing prevents them from doing so but the result is undefined.

The IR is also the single place a renderer is dispatched from:

.. code-block:: python

    ir = d.disassemble()
    text_output = ir.render("beebasm")          # str-name lookup
    json_output = ir.render(JsonRenderer(...))  # explicit instance

See ``docs/design/architecture.md`` and ``docs/design/decisions.md``
(D-009) for the full rationale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dasmos.output import Output

if TYPE_CHECKING:
    from dasmos.core.annotations import AnnotationStore
    from dasmos.core.classification import ExpressionRegistry
    from dasmos.core.config import Config
    from dasmos.core.disassembly import ClassificationStore
    from dasmos.core.format_hint import FormatHintRegistry
    from dasmos.core.labels import LabelManager
    from dasmos.core.memory import MemoryImage
    from dasmos.core.move import MoveManager
    from dasmos.cpu import Cpu
    from dasmos.disassembler import Disassembler
    from dasmos.renderer import Renderer


class IntermediateRepresentation:
    """Read-only view of a disassembly model.

    Returned from :meth:`~dasmos.disassembler.Disassembler.disassemble`.
    Renderers consume this; they should not call mutating methods on
    the underlying managers.
    """

    def __init__(self, disassembler: "Disassembler"):
        self._disassembler = disassembler

    @property
    def cpu(self) -> "Cpu":
        return self._disassembler.cpu

    @property
    def memory(self) -> "MemoryImage":
        return self._disassembler.memory

    @property
    def moves(self) -> "MoveManager":
        return self._disassembler.moves

    @property
    def labels(self) -> "LabelManager":
        return self._disassembler.labels

    @property
    def classifications(self) -> "ClassificationStore":
        return self._disassembler.classifications

    @property
    def expressions(self) -> "ExpressionRegistry":
        return self._disassembler.expressions

    @property
    def format_hints(self) -> "FormatHintRegistry":
        """Renderer-agnostic format hints registered via
        :meth:`Disassembler.format_hint` /
        :meth:`Disassembler.char_literal`. Renderers consult this
        registry at render time to honour the user's semantic
        intent for an operand byte.
        """
        return self._disassembler.format_hints

    @property
    def annotations(self) -> "AnnotationStore":
        return self._disassembler.annotations

    @property
    def config(self) -> "Config":
        return self._disassembler.config

    @property
    def constants(self):
        """Named values registered via
        :meth:`Disassembler.constant`. Returned in registration order.
        """
        return self._disassembler.constants

    @property
    def subroutines(self):
        """Subroutine metadata records registered via
        :meth:`Disassembler.subroutine`. Returned in registration
        order.
        """
        return self._disassembler.subroutines

    def render(self, renderer: "Renderer | str", **kwargs: Any) -> Output:
        """Render this IR via the named or supplied renderer.

        ``renderer`` may be:

        - a string — the renderer plug-in name; resolved via Stevedore
          using :func:`~dasmos.renderer.create_renderer`. Extra
          ``kwargs`` are forwarded to the renderer's constructor.
        - a :class:`~dasmos.renderer.Renderer` instance — used
          directly; ``kwargs`` are ignored.
        """
        if isinstance(renderer, str):
            from dasmos.renderer import create_renderer
            renderer = create_renderer(renderer, **kwargs)
        return renderer.render(self)
