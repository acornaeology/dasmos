"""Renderer extension point.

A *renderer* turns the disassembly model — the
:class:`~dasmos.ir.IntermediateRepresentation` — into output. Several
renderers can run on the same IR: a single trace can produce both a
Beebasm assembly source file and a structured JSON document.

Two abstract levels:

- :class:`Renderer` — the extension boundary. Every renderer
  registered under ``dasmos.renderer`` derives from this. Defines
  only one method: ``render(ir) -> Output``.
- :class:`TextRenderer` — for renderers that produce assembler-syntax
  source text (Beebasm, ca65, acme, …). Adds the syntax protocol
  (``hex2``, ``byte_prefix``, ``comment_prefix``, …) every text
  renderer must implement. Returns :class:`~dasmos.output.TextOutput`.
- :class:`StructuredRenderer` — for renderers that produce structured
  data (Json, …). Returns :class:`~dasmos.output.StructuredOutput`.

Both ``TextRenderer`` and ``StructuredRenderer`` are conveniences;
nothing prevents a renderer from subclassing :class:`Renderer`
directly if neither of the conveniences fits.

Design points (see ``docs/design/decisions.md`` D-003, D-009, D-015):

- The extension is named ``renderer`` rather than ``assembler``
  because the JSON renderer isn't a text-syntax assembler.
- ``pending_assertions`` and ``output_filename`` are per-instance,
  not class-level, so two renderer instances do not share state.
- The protocol is declared with ``@abstractmethod``: a plug-in that
  forgets to implement one of the syntax methods fails at
  instantiation, not on first call.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Generic, Type, TypeVar

from dasmos.extension import (
    Extension,
    ExtensionError,
    create_extension,
    describe_extension,
    extension,
    list_extensions,
)
from dasmos.output import Output, StructuredOutput, TextOutput

if TYPE_CHECKING:
    from dasmos.ir import IntermediateRepresentation


KIND = "renderer"
RENDERER_NAMESPACE = f"dasmos.{KIND}"

T = TypeVar("T", bound=Output)


class Renderer(Extension, Generic[T]):
    """Extension boundary for output renderers.

    Concrete renderers consume an
    :class:`~dasmos.ir.IntermediateRepresentation` and produce an
    :class:`~dasmos.output.Output` subclass.
    """

    @classmethod
    def _kind(cls) -> str:
        return KIND

    @abstractmethod
    def render(self, ir: "IntermediateRepresentation") -> T:
        """Produce output from an IR."""


class TextRenderer(Renderer[TextOutput]):
    """Base for text-syntax (assembler-source) renderers.

    Adds the assembler-syntax protocol every text renderer must
    implement. The methods grouped under "syntax" below are abstract;
    those under "policy" have sensible defaults.
    """

    explicit_a: bool = False

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.pending_assertions: dict[str, int | str] = {}
        self.output_filename: str | None = None

    # -- syntax (abstract) -------------------------------------------------

    @abstractmethod
    def cpus_supported(self) -> list[str]:
        """Names of the CPU plug-ins this renderer can target."""

    @abstractmethod
    def hex2(self, n: int) -> str:
        """Format an 8-bit value as the renderer's hex literal."""

    @abstractmethod
    def hex4(self, n: int) -> str:
        """Format a 16-bit value as the renderer's hex literal."""

    @abstractmethod
    def comment_prefix(self) -> str:
        """The character(s) introducing a line comment."""

    @abstractmethod
    def byte_prefix(self) -> str:
        """The directive that emits raw bytes (e.g. ``equb``)."""

    @abstractmethod
    def word_prefix(self) -> str:
        """The directive that emits 16-bit words (e.g. ``equw``)."""

    @abstractmethod
    def string_prefix(self) -> str:
        """The directive that emits a string (e.g. ``equs``)."""

    @abstractmethod
    def inline_label(self, name: str) -> str:
        """Render an inline label definition (e.g. ``.foo`` or ``foo:``)."""

    @abstractmethod
    def explicit_label(
        self,
        name: str,
        value,
        offset: int | None = None,
        align_column: int = 0,
    ) -> str:
        """Render an ``name = value`` definition."""

    @abstractmethod
    def disassembly_start(self) -> list[str]:
        """Lines emitted at the top of the output."""

    @abstractmethod
    def disassembly_end(self) -> list[str]:
        """Lines emitted at the bottom of the output."""

    @abstractmethod
    def code_start(self, start_addr, end_addr, first: bool) -> list[str]:
        """Lines emitted when starting to render a code block."""

    @abstractmethod
    def code_end(self) -> list[str]:
        """Lines emitted when ending a code block."""

    @abstractmethod
    def pseudopc_start(self, dest, source, length, move_id) -> list[str]:
        """Lines emitted when entering a pseudopc (relocated) block."""

    @abstractmethod
    def pseudopc_end(self, dest, source, length, move_id) -> list[str]:
        """Lines emitted when leaving a pseudopc block."""

    @abstractmethod
    def char_literal(self, n: int) -> str | None:
        """A single-character literal for the byte ``n``, or ``None``."""

    @abstractmethod
    def string_chr(self, n: int) -> str | None:
        """The character ``n`` as it appears inside a string literal,
        or ``None`` if the assembler can't include that character.
        """

    # -- policy (concrete defaults) ---------------------------------------

    def hex(self, n: int) -> str:
        if n <= 0xFF:
            return self.hex2(n)
        return self.hex4(n)

    def assert_expr(self, expr: str, value) -> None:
        self.pending_assertions[expr] = value

    def set_output_filename(self, filename: str) -> None:
        self.output_filename = filename

    def fill_directive(self, value: int, length: int) -> list[str]:
        prefix = self.byte_prefix()
        value_str = self.hex2(value)
        return [prefix + ", ".join([value_str] * length)]

    def force_zp_instruction(
        self, instruction: str, prefix: str, operand: str, suffix: str,
    ) -> str | None:
        return None

    def force_abs_instruction(
        self, instruction: str, prefix: str, operand: str, suffix: str,
    ) -> str | None:
        return None

    def force_zp_label_prefix(self) -> str:
        return ""

    def translate_binary_operator_names(self) -> dict[str, str]:
        return {}

    def translate_unary_operator_names(self) -> dict[str, str]:
        return {}

    def binary_format(self, s: str) -> str | None:
        return None

    def picture_binary(self, s: str) -> str:
        return s

    def sanitise(self, s: str) -> str:
        return s

    def format_comment(self, s: str, indent: int = 1) -> str:
        indent_str = " " * (indent * 4) if indent else ""
        return f"{indent_str}{self.comment_prefix()} {s}"


class StructuredRenderer(Renderer[StructuredOutput]):
    """Base for structured-data renderers (Json, …).

    No additional protocol beyond :meth:`Renderer.render` — concrete
    structured renderers consume the IR however they like and return
    a :class:`~dasmos.output.StructuredOutput`.
    """


class RendererExtensionError(ExtensionError):
    """Exception raised when a renderer extension cannot be loaded."""
    pass


def create_renderer(renderer_name: str, **kwargs) -> Renderer:
    """Create a renderer instance by name."""
    return create_extension(
        kind=KIND,
        namespace=RENDERER_NAMESPACE,
        name=renderer_name,
        exception_type=RendererExtensionError,
        **kwargs,
    )


def describe_renderer(renderer_name: str, *, single_line: bool = False) -> str:
    """Get the description of a renderer plug-in."""
    return describe_extension(
        kind=KIND,
        namespace=RENDERER_NAMESPACE,
        name=renderer_name,
        exception_type=RendererExtensionError,
        single_line=single_line,
    )


def renderer_names() -> list[str]:
    """Get the names of all available renderer plug-ins."""
    return list_extensions(RENDERER_NAMESPACE)


def renderer_type(renderer_name: str) -> Type[Renderer]:
    """Obtain the type of a renderer plug-in by name."""
    return extension(
        kind=KIND,
        namespace=RENDERER_NAMESPACE,
        name=renderer_name,
        exception_type=RendererExtensionError,
    )
