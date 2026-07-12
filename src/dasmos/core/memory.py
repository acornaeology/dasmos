"""Memory model for the dasmos disassembler.

Owns the loaded binary bytes and the address-type machinery that
distinguishes 'where the bytes live in the file' (BinaryAddr) from
'where the CPU sees them at runtime' (RuntimeAddr). The two are
distinct only when the user has registered a relocation via the
MoveManager.

Design points:

- All state lives on a :class:`MemoryImage` instance — no
  module-level globals. Multiple ``MemoryImage`` instances coexist
  freely, so two disassemblies can run in the same process.
- Failures raise :class:`MemoryAccessError` rather than terminating
  the process.
- :class:`RuntimeView` takes an injected resolver callable rather than
  reaching into a sibling module, avoiding a cyclic import.
- The address-space size is parameterised (default ``0x10000`` for
  6502); a flat ``list`` still backs storage. Sparse storage will be
  needed when 32-bit CPUs (ARM, 32016) land — TODO at that point.
- Cross-type comparisons of :class:`BinaryLocation` and
  :class:`RuntimeLocation` return ``False`` rather than raising.
- Same-typed address subtraction explicitly returns plain ``int`` —
  a delta is not an address.
"""

import hashlib
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from dasmos.exceptions import DasmosError


DEFAULT_ADDRESS_SPACE_SIZE = 0x10000


class MemoryAccessError(DasmosError):
    """Raised on any failure loading or reading the memory image."""


class TypedInt(int):
    """An ``int`` subclass that preserves its leaf type through
    addition and through subtraction of an untyped offset.

    Subtraction of two same-typed addresses returns plain ``int`` —
    that's a delta, not an address — and is the only operation that
    deliberately drops typing.
    """

    def __add__(self, other):
        return self.__class__(super().__add__(other))

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if isinstance(other, type(self)):
            return int(self) - int(other)
        return self.__class__(super().__sub__(other))


class BinaryAddr(TypedInt):
    """Address of data at *load* time."""

    def __new__(cls, value):
        assert not isinstance(value, RuntimeAddr), (
            "Cannot construct a BinaryAddr from a RuntimeAddr"
        )
        return super().__new__(cls, value)


class RuntimeAddr(TypedInt):
    """Address of data at *execution* time."""

    def __new__(cls, value):
        assert not isinstance(value, BinaryAddr), (
            "Cannot construct a RuntimeAddr from a BinaryAddr"
        )
        return super().__new__(cls, value)


def is_valid_binary_addr(binary_addr, allow_final_address: bool = False) -> bool:
    """True iff ``binary_addr`` falls within the 16-bit address space.

    Pass ``allow_final_address=True`` to admit the one-past-the-end
    address (useful when expressing ranges as ``[start, end)``).
    """
    assert not isinstance(binary_addr, RuntimeAddr)
    upper = DEFAULT_ADDRESS_SPACE_SIZE
    if allow_final_address:
        return 0 <= binary_addr <= upper
    return 0 <= binary_addr < upper


def is_valid_runtime_addr(runtime_addr, allow_final_address: bool = False) -> bool:
    """True iff ``runtime_addr`` falls within the 16-bit address space."""
    assert not isinstance(runtime_addr, BinaryAddr)
    upper = DEFAULT_ADDRESS_SPACE_SIZE
    if allow_final_address:
        return 0 <= runtime_addr <= upper
    return 0 <= runtime_addr < upper


class BinaryLocation:
    """A binary address paired with a ``move_id``.

    The ``move_id`` discriminates between distinct relocations of the
    same binary chunk into different runtime regions — see
    :mod:`dasmos.core.move`.
    """

    __slots__ = ("binary_addr", "move_id")

    def __init__(self, binary_addr, move_id):
        assert binary_addr is not None
        assert move_id is not None
        self.binary_addr = BinaryAddr(binary_addr)
        self.move_id = move_id

    def __eq__(self, other):
        if isinstance(other, BinaryLocation):
            return (
                self.binary_addr == other.binary_addr
                and self.move_id == other.move_id
            )
        return NotImplemented

    def __hash__(self):
        return hash((BinaryLocation, int(self.binary_addr), self.move_id))

    def __repr__(self):
        return f"BinaryLocation({self})"

    def __str__(self):
        result = hex(self.binary_addr)
        if self.move_id != 0:
            result += f"[{self.move_id}]"
        return result


class ReferenceKind(Enum):
    """How an operand's *named* address relates to the location the
    instruction actually accesses.

    CPU-agnostic. The four members are the orthogonal 2×2 of two
    yes/no questions that every load/store addressing mode answers,
    independent of instruction set:

    ============================ ================= =====================
    axis ↓ / axis →              names the address names a *base*
                                 directly          (+ a runtime index)
    ============================ ================= =====================
    location holds the datum     ``DIRECT``        ``INDEXED``
    location holds a *pointer*   ``POINTER``       ``INDEXED_POINTER``
    ============================ ================= =====================

    A CPU plug-in maps each of its addressing modes onto one member via
    ``AddressingMode.reference_kind`` — that mapping is the only
    ISA-specific part. Modes whose effective address comes purely from
    a *register* (no symbol in the operand — Z80 ``(IX+d)``, ARM
    ``[r1,#off]``) name no address and simply record no reference; the
    upstream :class:`~dasmos.cpu.OperandKind` decides that. A plug-in
    that never sets ``reference_kind`` gets :attr:`DIRECT` everywhere,
    i.e. pre-classification behaviour.

    The only contract consumers depend on is the derived boolean
    :attr:`touches_named_address`; the richer 4-way split is headroom
    for renderer wording and future features. See
    ``docs/design/reference-kinds-memo.md``.

    Examples across ISAs (illustrative, not definitional):

    - ``DIRECT`` — 6502 ``lda addr`` / ``lda zp``; 6809 ``lda >addr``;
      8086 ``mov ax,[disp]``; ARM PC-relative ``ldr r0,label``.
    - ``POINTER`` — 6502 ``jmp (addr)`` / ``lda (zp),Y``; 6809
      ``lda [addr]``; 8086 ``jmp [mem]``.
    - ``INDEXED`` — 6502 ``lda addr,X`` / ``lda zp,X``; 6809
      ``lda addr,X``; 8086 ``mov ax,table[bx]``.
    - ``INDEXED_POINTER`` — 6502 ``lda (zp,X)``; 6809 ``lda [addr,X]``.
    """

    DIRECT = "direct"
    """The operand is the exact address accessed — the named location
    holds the datum. (6502 ``zero_page`` / ``absolute`` data and
    control-flow ``absolute``.)"""

    POINTER = "pointer"
    """The operand names a location whose *contents* form the target;
    the named location itself is read to fetch the pointer. The named
    address is therefore genuinely accessed. (6502 ``JMP (addr)``;
    ``(zp),Y`` — the pointer sits at exactly the named address.)"""

    INDEXED = "indexed"
    """The operand names a *base*; the location touched is the base
    combined with a runtime index/register. The named byte is touched
    only if the index happens to be zero, which the disassembler cannot
    assume. (6502 ``zero_page,X/Y``; ``absolute,X/Y``.)"""

    INDEXED_POINTER = "indexed_pointer"
    """The operand names a *base*; the pointer is fetched from
    ``base + index``, so the named byte is again base-only. (6502
    ``(zp,X)`` — note this classifies oppositely to the visually
    similar ``(zp),Y``, whose pointer sits at the named address.)"""

    @property
    def touches_named_address(self) -> bool:
        """``True`` when the named address is genuinely read or written
        (:attr:`DIRECT` / :attr:`POINTER`), ``False`` when the operand
        is only an indexing base (:attr:`INDEXED` /
        :attr:`INDEXED_POINTER`).

        This boolean — not the specific member — is the contract every
        consumer depends on: an address is a real, owned memory location
        iff at least one reference to it satisfies this predicate.
        """
        return self in (ReferenceKind.DIRECT, ReferenceKind.POINTER)


class Reference:
    """A single use site of a label: *where* it is referenced (a
    :class:`BinaryLocation`) and *how* (a :class:`ReferenceKind`).

    Exposes ``binary_addr`` / ``move_id`` as delegating properties so
    code that predates the ``kind`` field — e.g. renderers doing
    ``int(r.binary_addr)`` — keeps working unchanged.
    """

    __slots__ = ("location", "kind")

    def __init__(self, location: BinaryLocation, kind: ReferenceKind = ReferenceKind.DIRECT):
        assert location is not None
        self.location = location
        self.kind = kind

    @property
    def binary_addr(self):
        return self.location.binary_addr

    @property
    def move_id(self):
        return self.location.move_id

    def __eq__(self, other):
        if isinstance(other, Reference):
            return self.location == other.location and self.kind == other.kind
        return NotImplemented

    def __hash__(self):
        return hash((Reference, self.location, self.kind))

    def __repr__(self):
        return f"Reference({self.location}, {self.kind.name})"


class RuntimeLocation:
    """A runtime address paired with a ``move_id``."""

    __slots__ = ("runtime_addr", "move_id")

    def __init__(self, runtime_addr, move_id):
        assert runtime_addr is not None
        assert move_id is not None
        self.runtime_addr = RuntimeAddr(runtime_addr)
        self.move_id = move_id

    def __eq__(self, other):
        if isinstance(other, RuntimeLocation):
            return (
                self.runtime_addr == other.runtime_addr
                and self.move_id == other.move_id
            )
        return NotImplemented

    def __hash__(self):
        return hash((RuntimeLocation, int(self.runtime_addr), self.move_id))

    def __repr__(self):
        return f"RuntimeLocation({self})"

    def __str__(self):
        result = hex(self.runtime_addr)
        if self.move_id != 0:
            result += f":{self.move_id}"
        return result


class MemoryImage:
    """The loaded binary bytes plus per-load range tracking.

    All state lives on the instance — multiple ``MemoryImage``
    instances coexist without interference.

    Storage is currently a flat list sized to the address space. For
    very large 32-bit address spaces (ARM, 32016) this becomes
    impractical and the storage will need to be reworked into a sparse
    structure; TODO when the first 32-bit CPU plug-in lands.
    """

    def __init__(self, address_space_size: int = DEFAULT_ADDRESS_SPACE_SIZE):
        self._address_space_size = address_space_size
        self._bytes: list[int | None] = [None] * address_space_size
        self._load_ranges: list[tuple[BinaryAddr, BinaryAddr]] = []

    @property
    def address_space_size(self) -> int:
        return self._address_space_size

    def load(
        self,
        filepath,
        binary_addr,
        md5sum: str | None = None,
    ) -> tuple[BinaryAddr, BinaryAddr]:
        """Load the contents of ``filepath`` at ``binary_addr``.

        Returns ``(start, end)`` of the loaded range as a half-open
        interval. Raises :class:`MemoryAccessError` if the file is
        missing, the load would overflow the address space, or the
        optional md5 check fails.
        """
        binary_addr = BinaryAddr(binary_addr)
        try:
            data = Path(filepath).read_bytes()
        except FileNotFoundError as ex:
            raise MemoryAccessError(f"File not found: {filepath}") from ex

        end = int(binary_addr) + len(data)
        if end > self._address_space_size:
            raise MemoryAccessError(
                f"load() would overflow memory: "
                f"0x{int(binary_addr):x} + {len(data)} bytes "
                f"exceeds 0x{self._address_space_size:x}"
            )

        if md5sum is not None:
            actual = hashlib.md5(data).hexdigest()
            if actual != md5sum:
                raise MemoryAccessError(
                    f"md5sum mismatch loading {filepath}: "
                    f"expected {md5sum}, got {actual}"
                )

        for i, b in enumerate(data):
            self._bytes[int(binary_addr) + i] = b
        end_addr = BinaryAddr(end)
        self._load_ranges.append((binary_addr, end_addr))
        return binary_addr, end_addr

    def is_loaded(self, binary_addr, n: int = 1) -> bool:
        """True iff ``n`` bytes starting at ``binary_addr`` are all loaded."""
        for i in range(n):
            addr = int(binary_addr) + i
            if not (0 <= addr < self._address_space_size):
                return False
            if self._bytes[addr] is None:
                return False
        return True

    def get_u8(self, binary_addr) -> int:
        """Read one byte at ``binary_addr``."""
        if not self.is_loaded(binary_addr):
            raise MemoryAccessError(
                f"No data loaded at binary address 0x{int(binary_addr):x}"
            )
        return self._bytes[int(binary_addr)]

    def get_u16_le(self, binary_addr) -> int:
        """Read a little-endian 16-bit word at ``binary_addr``."""
        lo = self.get_u8(binary_addr)
        hi = self.get_u8(int(binary_addr) + 1)
        return lo | (hi << 8)

    def get_u16_be(self, binary_addr) -> int:
        """Read a big-endian 16-bit word at ``binary_addr``."""
        hi = self.get_u8(binary_addr)
        lo = self.get_u8(int(binary_addr) + 1)
        return (hi << 8) | lo

    def entire_load_range(self) -> tuple[BinaryAddr, BinaryAddr]:
        """The (min start, max end) across every successful load.

        Raises :class:`MemoryAccessError` if no data has been loaded.
        """
        if not self._load_ranges:
            raise MemoryAccessError("No data has been loaded")
        start = min(s for s, _ in self._load_ranges)
        end = max(e for _, e in self._load_ranges)
        return BinaryAddr(start), BinaryAddr(end)

    @property
    def load_ranges(self) -> list[tuple[BinaryAddr, BinaryAddr]]:
        """A snapshot of every ``[start, end)`` range loaded so far."""
        return list(self._load_ranges)


class RuntimeView:
    """Read-through view of a :class:`MemoryImage` indexed by
    :class:`RuntimeAddr`.

    The runtime→binary resolver is injected; in production it consults
    the :class:`~dasmos.core.move.MoveManager`, but tests can pass any
    callable that returns a :class:`BinaryLocation`.
    """

    def __init__(
        self,
        memory: MemoryImage,
        resolver: Callable[[RuntimeAddr], BinaryLocation],
    ):
        self._memory = memory
        self._resolver = resolver

    def get_u8(self, runtime_addr) -> int:
        loc = self._resolver(RuntimeAddr(runtime_addr))
        return self._memory.get_u8(loc.binary_addr)

    def get_u16_le(self, runtime_addr) -> int:
        loc = self._resolver(RuntimeAddr(runtime_addr))
        return self._memory.get_u16_le(loc.binary_addr)

    def get_u16_be(self, runtime_addr) -> int:
        loc = self._resolver(RuntimeAddr(runtime_addr))
        return self._memory.get_u16_be(loc.binary_addr)
