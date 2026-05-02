"""Polymorphic byte-classification types and the expression registry.

Every classified byte in the loaded image is the start of (or a
continuation of) a :class:`Classification` instance. The first byte
holds the object; the remaining bytes of a multi-byte classification
are marked with a sentinel saying 'I'm part of an existing
classification' (see :mod:`dasmos.core.disassembly`, ported separately).

The four data classifications live here. The :class:`Opcode` class
(which marks a span as code) lives with the CPU plug-in because its
behaviour is CPU-specific.

Lifted from py8dis's ``classification.py`` (482 lines) with the
following design changes:

- The four data classes inherit from :class:`Classification`, an
  abstract base. py8dis used duck-typing; the explicit ABC documents
  the polymorphism contract.
- Each classification is now **pure data**. py8dis baked the
  rendering method (``as_string_list``) into every class, calling
  into ``mainformatter`` and the configured assembler. That tangles
  model with renderer; the rendering moves to the formatter layer
  with the assembler port (task #14).
- The :class:`ExpressionRegistry` is a class, not a module-level
  ``expressions`` dict. Multiple instances coexist without
  interference.
- :class:`String`'s constructor no longer captures a callstack via
  ``utils.find_external_callstack()`` — it was an expensive side
  effect for diagnostics-only data nobody read in practice.
- Validation failures raise :class:`ClassificationError` instead of
  firing assertions.
- The ``INSIDE_A_CLASSIFICATION = 0`` magic constant from py8dis is
  not exported here — the disassembly port (task #12) will use a
  proper sentinel object that can't be confused with a real value.
- The string-scanning algorithms (``stringterm_binary``,
  ``stringhi_binary``, ``stringn_binary``, ``autostring``,
  ``classify_leftovers``) and the operand-rendering helpers
  (``get_constant8/16``, ``get_address8/16``, ``check_expr``) are
  not in this module — they belong with the disassembly engine and
  the assembler abstraction respectively.
"""

from abc import ABC, abstractmethod

from dasmos.core.memory import BinaryAddr
from dasmos.exceptions import DasmosError


class ClassificationError(DasmosError):
    """Raised on invalid classification construction or mutation."""


class Classification(ABC):
    """Polymorphic base for byte-classification objects.

    Every concrete subclass declares a length (in bytes) and reports
    whether it represents code or data via :meth:`is_code`.
    """

    @abstractmethod
    def length(self) -> int:
        """The number of bytes this classification covers."""

    def is_code(self, binary_addr=None) -> bool:
        """True iff this classification represents executable code.

        The optional ``binary_addr`` argument is for CPU
        :class:`Opcode` subclasses whose code-or-data nature can vary
        by address (e.g. unconditional branches followed by inline
        data). Data subclasses ignore it and always return False.
        """
        return False


def _validate_positive_length(length: int) -> None:
    if not isinstance(length, int) or length <= 0:
        raise ClassificationError(f"length must be a positive integer; got {length!r}")


def _validate_positive_cols(cols: int | None) -> None:
    if cols is None:
        return
    if not isinstance(cols, int) or cols <= 0:
        raise ClassificationError(f"cols must be a positive integer; got {cols!r}")


class Byte(Classification):
    """Marks a span of binary as raw bytes.

    ``cols`` controls the number of bytes per emitted line in the
    rendered output (the formatter layer reads this); ``None`` means
    'use the formatter default'.
    """

    def __init__(self, length: int, cols: int | None = None):
        _validate_positive_length(length)
        _validate_positive_cols(cols)
        self._length = length
        self._cols = cols

    def length(self) -> int:
        return self._length

    def cols(self) -> int | None:
        return self._cols

    def set_length(self, length: int) -> None:
        _validate_positive_length(length)
        self._length = length


class Word(Classification):
    """Marks a span of binary as 16-bit words.

    ``length`` is in bytes and must be even.
    """

    def __init__(self, length: int, cols: int | None = None):
        _validate_positive_length(length)
        if length % 2 != 0:
            raise ClassificationError(
                f"Word length must be even (in bytes); got {length}"
            )
        _validate_positive_cols(cols)
        self._length = length
        self._cols = cols

    def length(self) -> int:
        return self._length

    def cols(self) -> int | None:
        return self._cols

    def set_length(self, length: int) -> None:
        _validate_positive_length(length)
        if length % 2 != 0:
            raise ClassificationError(
                f"Word length must be even (in bytes); got {length}"
            )
        self._length = length


class Fill(Classification):
    """Marks a run of identical bytes for compact emission.

    Renders to one assembler directive (a beebasm
    ``FOR n : equb v : NEXT`` loop, an acme ``!fill`` etc.) instead
    of one ``equb`` line per ~12 bytes. Round-trip identical because
    the directive expands to the same N bytes at assembly.
    """

    def __init__(self, length: int, value: int):
        _validate_positive_length(length)
        if not isinstance(value, int) or not (0 <= value <= 0xFF):
            raise ClassificationError(
                f"Fill value must be a byte (0..255); got {value!r}"
            )
        self._length = length
        self._value = value

    def length(self) -> int:
        return self._length

    def value(self) -> int:
        return self._value


class String(Classification):
    """Marks a span of binary as a string.

    The actual character interpretation lives with the assembler — a
    String classification just records 'this many bytes form a string'.
    """

    def __init__(self, length: int):
        _validate_positive_length(length)
        self._length = length

    def length(self) -> int:
        return self._length

    def set_length(self, length: int) -> None:
        _validate_positive_length(length)
        self._length = length


class ExpressionRegistry:
    """Per-disassembly mapping from binary address to a user-supplied
    operand expression.

    Used to render an instruction like ``LDA #3`` as
    ``LDA #initial_lives + 1`` when the user has registered the
    expression at the operand address.
    """

    def __init__(self):
        self._expressions: dict[BinaryAddr, str] = {}

    def __contains__(self, binary_addr) -> bool:
        return BinaryAddr(binary_addr) in self._expressions

    def add(self, binary_addr, expression: str) -> None:
        """Register ``expression`` at ``binary_addr``.

        Silently ignored if an expression is already registered at
        that address — preserves py8dis's idempotent-registration
        behaviour, which lets multi-pass classifiers add expressions
        without special-casing duplicates.
        """
        binary_addr = BinaryAddr(binary_addr)
        if binary_addr not in self._expressions:
            self._expressions[binary_addr] = expression

    def get(self, binary_addr) -> str:
        """Return the expression registered at ``binary_addr``.

        Raises ``KeyError`` if there is none — use
        :meth:`get_or_none` if absence is expected.
        """
        return self._expressions[BinaryAddr(binary_addr)]

    def get_or_none(self, binary_addr) -> str | None:
        return self._expressions.get(BinaryAddr(binary_addr))
