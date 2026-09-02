"""Polymorphic byte-classification types and the expression registry.

Every classified byte in the loaded image is the start of (or a
continuation of) a :class:`Classification` instance. The first byte
holds the object; the remaining bytes of a multi-byte classification
are marked with a sentinel saying 'I'm part of an existing
classification' (see :mod:`dasmos.core.disassembly`, ported separately).

The four data classifications live here. The :class:`Opcode` class
(which marks a span as code) lives with the CPU plug-in because its
behaviour is CPU-specific.

Design points:

- The four data classes inherit from :class:`Classification`, an
  abstract base; the explicit ABC documents the polymorphism contract.
- Each classification is **pure data**. Rendering belongs to the
  renderer layer, not on the model objects, so the model can be
  serialised, snapshot-tested, and walked without dragging a renderer
  along.
- The :class:`ExpressionRegistry` is a class, not a module-level
  ``expressions`` dict. Multiple instances coexist without
  interference.
- Validation failures raise :class:`ClassificationError` rather than
  firing assertions.
- The "inside a multi-byte classification" marker is a sentinel
  object owned by the disassembly module rather than a magic ``0``
  that could be confused with a real value.
- The string-scanning algorithms (``stringterm_binary``,
  ``stringhi_binary``, ``stringn_binary``, ``autostring``,
  ``classify_leftovers``) and the operand-rendering helpers
  (``get_constant8/16``, ``get_address8/16``, ``check_expr``) live
  with the disassembly engine and the renderer abstraction respectively.
"""

from abc import ABC, abstractmethod

from dasmos.core.expr import Expr, as_expr
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


class IncludedBinary(Classification):
    """Marks a span whose bytes are supplied by an *external* file at
    assembly time.

    The span still **owns** its loaded bytes exactly like :class:`Byte`
    (the tracer won't enter it and nothing is left unaccounted for), but
    the renderer emits an include directive (beebasm ``incbin "path"``;
    64tass ``.binary "path"``) instead of ``equb`` lines. The owned
    bytes are the canonical payload: :meth:`IntermediateRepresentation
    .write_included_binaries` writes them to ``path`` so an assembler
    reads back exactly what dasmos accounted for, keeping the round-trip
    self-consistent even though the data lives in a separate file.

    ``path`` is the include path as it should appear in the directive
    (and the relative path the payload is written to) — typically a
    bare filename sitting next to the listing.
    """

    def __init__(self, length: int, path: str):
        _validate_positive_length(length)
        if not isinstance(path, str) or not path:
            raise ClassificationError(
                f"IncludedBinary path must be a non-empty string; got {path!r}"
            )
        self._length = length
        self._path = path

    def length(self) -> int:
        return self._length

    def path(self) -> str:
        return self._path


class ExpressionRegistry:
    """Per-disassembly mapping from binary address to a user-supplied
    operand expression.

    Used to render an instruction like ``LDA #3`` as
    ``LDA #initial_lives + 1`` when the user has registered the
    expression at the operand address.

    Values are :class:`~dasmos.core.expr.Expr` trees. A plain ``str`` (or
    ``int``) passed to :meth:`add` is coerced via
    :func:`~dasmos.core.expr.as_expr` — a string becomes a
    :class:`~dasmos.core.expr.Raw` node so legacy dialect strings keep
    rendering exactly as before.
    """

    def __init__(self):
        self._expressions: dict[BinaryAddr, Expr] = {}
        #: Addresses whose expression was registered *explicitly* by a
        #: driver (``Disassembler.expr``), as opposed to auto-synthesised
        #: (``code_ptr`` / ``rts_code_ptr``). Explicit registrations win
        #: over auto ones regardless of call order.
        self._explicit: set[BinaryAddr] = set()

    def __contains__(self, binary_addr) -> bool:
        return BinaryAddr(binary_addr) in self._expressions

    def add(self, binary_addr, expression, *, explicit: bool = False) -> None:
        """Register ``expression`` (an :class:`Expr`, ``str`` or ``int``)
        at ``binary_addr``.

        Precedence, independent of call order:

        - An **explicit** registration (a driver's ``d.expr``) always wins
          — it overwrites a previously auto-synthesised expression, and is
          itself first-write-wins against other explicit registrations.
        - An **auto** registration (``code_ptr`` and friends, default) is
          idempotent and never overwrites anything — so a multi-pass
          classifier can add freely, and a driver's explicit override at
          the same address takes precedence whether it ran before or
          after the auto one.
        """
        binary_addr = BinaryAddr(binary_addr)
        present = binary_addr in self._expressions
        if explicit:
            if binary_addr not in self._explicit:
                # First explicit write wins over anything auto.
                self._expressions[binary_addr] = as_expr(expression)
                self._explicit.add(binary_addr)
        elif not present:
            self._expressions[binary_addr] = as_expr(expression)

    def get(self, binary_addr) -> Expr:
        """Return the expression registered at ``binary_addr``.

        Raises ``KeyError`` if there is none — use
        :meth:`get_or_none` if absence is expected.
        """
        return self._expressions[BinaryAddr(binary_addr)]

    def get_or_none(self, binary_addr) -> "Expr | None":
        return self._expressions.get(BinaryAddr(binary_addr))
