"""Assembler-syntax (renderer) extension point.

Each assembler plug-in is a subclass of :class:`Assembler` registered
under the ``dasmos.assembler`` entry-point namespace. Concrete
assemblers render the disassembled trace into a particular textual
syntax — Beebasm, ca65, the JSON output ported from the py8dis fork,
and so on.

The protocol that every concrete assembler implements is declared on
this base class. The methods are abstract where the assembler-syntax
choice is unavoidable (hex literals, comment prefix, ORG directive,
inline label syntax, …) and concrete-with-default where there is a
sensible fallback (the ``hex`` size-dispatcher, the ``fill_directive``
fallback to repeated byte directives, ``binary_format`` returning
``None`` to signal 'unsupported', and so on).

Lifted from py8dis's ``assembler.py`` (49 lines — intentionally thin)
and the protocol-by-convention used across its concrete assemblers.
Two design changes:

- ``pending_assertions`` and ``output_filename`` are now **per-instance**
  rather than class attributes. py8dis kept them on the class, so
  every Assembler instance in the process shared a single dict and
  filename. That made it impossible to drive two assemblers (or two
  disassemblies sharing one assembler dialect) in parallel.
- The protocol is declared explicitly with ``@abstractmethod`` so a
  concrete plug-in that forgets to implement one of the assembler-
  specific methods fails at instantiation, not at first call.
"""

from abc import abstractmethod
from typing import Type

from dasmos.extension import (
    Extension,
    ExtensionError,
    create_extension,
    describe_extension,
    extension,
    list_extensions,
)

KIND = "assembler"
ASSEMBLER_NAMESPACE = f"dasmos.{KIND}"


class Assembler(Extension):
    """Abstract base for assembler-syntax (renderer) plug-ins.

    Concrete subclasses render disassembled output in a particular
    assembler-syntax dialect (Beebasm, ca65, machine-readable JSON, …).
    A given CPU may have several assemblers it can be rendered through
    — the user picks one at the CLI or via the API.

    The methods grouped under "syntax" below are abstract: any
    concrete assembler must override them. The methods grouped under
    "policy" have sensible defaults.
    """

    # If True, instructions with an implicit-accumulator addressing
    # mode (e.g. 6502 ROR/ROL/ASL/LSR) are emitted with an explicit
    # ``A`` suffix (``ROL A``); if False, the suffix is omitted (``ROL``).
    # Subclasses set this on the class or in ``__init__``.
    explicit_a: bool = False

    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        # Per-instance state. py8dis kept these on the class, which
        # silently coupled every instance to the same dict / filename.
        self.pending_assertions: dict[str, int | str] = {}
        self.output_filename: str | None = None

    @classmethod
    def _kind(cls) -> str:
        return KIND

    # -- syntax (abstract) -------------------------------------------------

    @abstractmethod
    def cpus_supported(self) -> list[str]:
        """Names of the CPU plug-ins this assembler can render."""

    @abstractmethod
    def hex2(self, n: int) -> str:
        """Format an 8-bit value as the assembler's hex literal."""

    @abstractmethod
    def hex4(self, n: int) -> str:
        """Format a 16-bit value as the assembler's hex literal."""

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
        """Lines emitted at the top of the disassembly output."""

    @abstractmethod
    def disassembly_end(self) -> list[str]:
        """Lines emitted at the bottom of the disassembly output."""

    @abstractmethod
    def code_start(self, start_addr, end_addr, first: bool) -> list[str]:
        """Lines emitted when starting to render a code block at ``start_addr``."""

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
        """A single-character literal for the byte ``n``, or ``None`` if
        the assembler can't quote that character.
        """

    @abstractmethod
    def string_chr(self, n: int) -> str | None:
        """The character ``n`` as it appears inside a string literal,
        or ``None`` if the assembler can't include that character.
        """

    # -- policy (concrete defaults) ---------------------------------------

    def hex(self, n: int) -> str:
        """Format ``n`` as hex, dispatching to :meth:`hex2` for byte
        values and :meth:`hex4` otherwise.
        """
        if n <= 0xFF:
            return self.hex2(n)
        return self.hex4(n)

    def assert_expr(self, expr: str, value) -> None:
        """Record an assembler-time assertion that ``expr == value``.

        Used by the disassembler to encode invariants it can't itself
        verify (e.g. that a calculated symbol resolves to a known
        address); :meth:`disassembly_end` typically writes them out as
        ``assert`` lines.
        """
        self.pending_assertions[expr] = value

    def set_output_filename(self, filename: str) -> None:
        """Record an output filename hint for assemblers that can save
        the result (beebasm, acme).
        """
        self.output_filename = filename

    def fill_directive(self, value: int, length: int) -> list[str]:
        """Emit ``length`` copies of ``value``.

        Default falls back to a single :meth:`byte_prefix` line with
        the value repeated. Concrete assemblers should override with
        their compact fill idiom (beebasm's ``FOR ... NEXT`` loop,
        acme's ``!fill``, …) — round-trip is byte-identical either
        way.
        """
        prefix = self.byte_prefix()
        value_str = self.hex2(value)
        return [prefix + ", ".join([value_str] * length)]

    def force_zp_instruction(
        self,
        instruction: str,
        prefix: str,
        operand: str,
        suffix: str,
    ) -> str | None:
        """Render an instruction forced to zero-page addressing.

        Returns the rendered line, or ``None`` if the assembler has no
        way to force zero-page addressing (in which case the caller
        falls back to the natural rendering).
        """
        return None

    def force_abs_instruction(
        self,
        instruction: str,
        prefix: str,
        operand: str,
        suffix: str,
    ) -> str | None:
        """Render an instruction forced to absolute addressing.

        Returns the rendered line, or ``None`` if the assembler has no
        way to force absolute addressing (e.g. beebasm).
        """
        return None

    def force_zp_label_prefix(self) -> str:
        """Prefix used to take the low byte of a label for zero-page
        operands. Empty by default.
        """
        return ""

    def translate_binary_operator_names(self) -> dict[str, str]:
        """Map generic binary-operator names (``OR``, ``EOR``, ``DIV``,
        ``MOD``, ``|``, ``&``, ``^``, ``/``, ``%``, ``!=``) to the
        assembler-specific spellings. Empty default — concrete
        assemblers override only what they need.
        """
        return {}

    def translate_unary_operator_names(self) -> dict[str, str]:
        """As :meth:`translate_binary_operator_names`, for unary
        operators (``NOT``, ``!``).
        """
        return {}

    def binary_format(self, s: str) -> str | None:
        """Render a string of ``0``/``1`` digits as a binary literal,
        or return ``None`` if the assembler doesn't support one.
        """
        return None

    def picture_binary(self, s: str) -> str:
        """Convert a ``0``/``1`` string to a visual representation
        (``.``/``#``) for assemblers that support it. Default returns
        the input unchanged.
        """
        return s

    def sanitise(self, s: str) -> str:
        """Last-mile output sanitisation. Default is identity."""
        return s

    def format_comment(self, s: str, indent: int = 1) -> str:
        """Render ``s`` as a single-line comment, prefixed with the
        assembler's :meth:`comment_prefix`.

        ``indent`` is the number of leading indent units; concrete
        assemblers may override to apply their indent convention.
        """
        indent_str = " " * (indent * 4) if indent else ""
        return f"{indent_str}{self.comment_prefix()} {s}"


class AssemblerExtensionError(ExtensionError):
    """Exception raised when an assembler extension cannot be loaded."""
    pass


def create_assembler(assembler_name: str, **kwargs) -> Assembler:
    """Create an assembler instance by name."""
    return create_extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
        **kwargs,
    )


def describe_assembler(assembler_name: str, *, single_line: bool = False) -> str:
    """Get the description of an assembler plug-in."""
    return describe_extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
        single_line=single_line,
    )


def assembler_names() -> list[str]:
    """Get the names of all available assembler plug-ins."""
    return list_extensions(ASSEMBLER_NAMESPACE)


def assembler_type(assembler_name: str) -> Type[Assembler]:
    """Obtain the type of an assembler plug-in by name."""
    return extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
    )
