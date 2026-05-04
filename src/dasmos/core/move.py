"""Move (relocation) registry for the dasmos disassembler.

A *move* registers that a span of bytes loaded at one binary address
will, at runtime, appear at a different address. This is how the
disassembler reasons about ROMs that copy fragments of themselves into
RAM, or about overlays that share a runtime region.

A binary address can be the source of at most one move (because every
byte in the binary needs a single classification). A runtime address
may be the destination of more than one move — disambiguation is
driven by the active-move stack.

Design points:

- All state lives on a :class:`MoveManager` instance — no module-level
  globals.
- :class:`Move` is the public handle returned by
  :meth:`MoveManager.add_move`. It carries name + dest + src + length
  and is itself a context manager — ``with move: ...`` pushes the
  move onto the active-move stack for the duration of the block.
- Internally MoveManager indexes moves by an integer position; that
  position is an implementation detail and is not part of the public
  API.
- :meth:`MoveManager.r2b_checked` raises :class:`MoveError` rather
  than terminating the process, and does not require a renderer to
  be configured.
- The cache that powers :meth:`MoveManager.move_ids_for_runtime_addr`
  is invalidated explicitly on every ``add_move``.
- ``add_move`` raises :class:`MoveError` for length ≤ 0, dest == src,
  overflowing the address space, or a duplicate explicit name.
"""

from collections import defaultdict

from dasmos.core.memory import (
    DEFAULT_ADDRESS_SPACE_SIZE,
    BinaryAddr,
    BinaryLocation,
    RuntimeAddr,
    RuntimeLocation,
    is_valid_binary_addr,
    is_valid_runtime_addr,
)
from dasmos.exceptions import DasmosError


# Internal sentinel for "the implicit identity-mapping move that
# covers the whole address space 1:1". Used in BinaryLocation /
# RuntimeLocation move_id fields when no user-declared move applies.
# Not exposed as a public Move handle — drivers never need to reason
# about it.
BASE_MOVE_ID = 0


class MoveError(DasmosError):
    """Raised on illegal move operations or ambiguous resolution."""


class Move:
    """A registered relocation: ``length`` bytes at ``src_binary_addr``
    map to ``dest_runtime_addr`` at execution time, identified by
    ``name``.

    Returned by :meth:`Disassembler.add_move`. Use as a context
    manager to scope annotations under the move::

        nmi_write = d.add_move(0x0D0A, 0xBCDF, 14, name="nmi_write")
        with nmi_write:
            d.byte(0x0D0A, length=14)

    Equality and hashing are by identity — a Move belongs to exactly
    one :class:`MoveManager` and isn't comparable across managers.
    """

    __slots__ = (
        "name",
        "dest_runtime_addr",
        "src_binary_addr",
        "length",
        "_manager",
        "_move_id",
    )

    def __init__(
        self,
        dest_runtime_addr,
        src_binary_addr,
        length: int,
        *,
        name: str,
        manager: "MoveManager",
        move_id: int,
    ):
        # All fields are required. Move objects are only ever
        # legitimately constructed by :meth:`MoveManager.add_move`,
        # which supplies the back-reference and registry id. Tests
        # that need a Move for geometry-only assertions should
        # likewise go through a MoveManager.
        if not name:
            raise MoveError("Move requires a non-empty name")
        if length <= 0:
            raise MoveError(
                f"Move length must be positive: got {length} for "
                f"name={name!r}"
            )
        self.name = name
        self.dest_runtime_addr = RuntimeAddr(dest_runtime_addr)
        self.src_binary_addr = BinaryAddr(src_binary_addr)
        self.length = length
        self._manager = manager
        self._move_id = move_id

    def __enter__(self) -> "Move":
        self._manager._push_active(self._move_id)
        return self

    def __exit__(self, *exc) -> None:
        self._manager._pop_active(self._move_id)

    def __repr__(self) -> str:
        return (
            f"Move(name={self.name!r}, "
            f"dest=0x{int(self.dest_runtime_addr):04x}, "
            f"src=0x{int(self.src_binary_addr):04x}, "
            f"length={self.length})"
        )

    # -- geometry helpers ----------------------------------------------

    def is_in_move_dest(self, runtime_addr, *, include_end_address: bool) -> bool:
        assert not isinstance(runtime_addr, BinaryAddr)
        end = int(self.dest_runtime_addr) + self.length
        if include_end_address:
            return self.dest_runtime_addr <= runtime_addr <= end
        return self.dest_runtime_addr <= runtime_addr < end

    def is_in_move_src(self, binary_addr, *, include_end_address: bool) -> bool:
        assert not isinstance(binary_addr, RuntimeAddr)
        end = int(self.src_binary_addr) + self.length
        if include_end_address:
            return self.src_binary_addr <= binary_addr <= end
        return self.src_binary_addr <= binary_addr < end

    def convert_binary_to_runtime_addr(self, binary_addr) -> RuntimeAddr:
        assert not isinstance(binary_addr, RuntimeAddr)
        assert self.is_in_move_src(binary_addr, include_end_address=True)
        offset = int(binary_addr) - int(self.src_binary_addr)
        return RuntimeAddr(int(self.dest_runtime_addr) + offset)

    def convert_runtime_to_binary_addr(self, runtime_addr) -> BinaryAddr:
        assert not isinstance(runtime_addr, BinaryAddr)
        assert self.is_in_move_dest(runtime_addr, include_end_address=True)
        offset = int(runtime_addr) - int(self.dest_runtime_addr)
        return BinaryAddr(int(self.src_binary_addr) + offset)


class MoveManager:
    """Per-disassembly registry of relocations and runtime↔binary mapping.

    No module-level state — multiple ``MoveManager`` instances coexist
    without interference, in tests and in production driver scripts
    that disassemble more than one binary.
    """

    def __init__(self, address_space_size: int = DEFAULT_ADDRESS_SPACE_SIZE):
        self._address_space_size = address_space_size
        # The base move covers the entire address space 1:1 — that's
        # how an unrelocated address resolves to itself. It's stored
        # at index 0 / BASE_MOVE_ID and is not exposed publicly.
        base = Move(
            RuntimeAddr(0),
            BinaryAddr(0),
            address_space_size,
            name="<base>",
            manager=self,
            move_id=BASE_MOVE_ID,
        )
        self._moves: list[Move] = [base]
        self._move_id_for_binary_addr: list[int] = [BASE_MOVE_ID] * address_space_size
        self._active_move_ids: list[int] = []
        self._cache: dict[RuntimeAddr, set[int]] | None = None

    @property
    def address_space_size(self) -> int:
        """The address-space size this manager was constructed with."""
        return self._address_space_size

    @property
    def active_move_ids(self) -> list[int]:
        """A snapshot of the active-move stack; outermost first."""
        return list(self._active_move_ids)

    @property
    def moves(self) -> list[Move]:
        """All user-declared moves, in declaration order. Excludes the
        internal base move.
        """
        return list(self._moves[1:])

    @property
    def all_moves(self) -> list[Move]:
        """All moves including the internal base move at index 0.
        Used by renderers that need to walk every move with its
        positional id.
        """
        return list(self._moves)

    def is_valid_move_id(self, move_id: int) -> bool:
        return move_id == BASE_MOVE_ID or 0 <= move_id < len(self._moves)

    def move_for_id(self, move_id: int) -> Move:
        """Look up a Move by its internal id. For consumers that
        receive a bare ``move_id`` (e.g. via the IR's
        ``BinaryLocation.move_id``) and need the full Move handle.
        """
        if not self.is_valid_move_id(move_id):
            raise MoveError(f"unknown move id: {move_id}")
        return self._moves[move_id]

    def add_move(
        self,
        dest_runtime_addr,
        src_binary_addr,
        length: int,
        *,
        name: str | None = None,
    ) -> Move:
        """Register a relocation; return the :class:`Move` handle.

        ``name`` is the human-readable identity of the move (used in
        diagnostics, JSON output, and the ``@move-name`` URI variant
        in markdown comments). When omitted, a fabricated
        ``move_<index>`` name is used; provide one explicitly when
        the same destination is the target of more than one move so
        readers / cross-references can disambiguate.

        Source bytes are 'stolen' from any prior overlapping move —
        the last ``add_move`` covering a given binary address wins.
        """
        if length <= 0:
            raise MoveError(f"move length must be positive: got {length}")
        dest_runtime_addr = RuntimeAddr(dest_runtime_addr)
        src_binary_addr = BinaryAddr(src_binary_addr)
        if int(dest_runtime_addr) == int(src_binary_addr):
            raise MoveError(
                f"move dest equals src (0x{int(dest_runtime_addr):x}); "
                "such a move is a no-op and refused to surface accidental copies"
            )
        if not is_valid_runtime_addr(dest_runtime_addr):
            raise MoveError(
                f"move dest 0x{int(dest_runtime_addr):x} outside address space"
            )
        if not is_valid_binary_addr(src_binary_addr):
            raise MoveError(
                f"move src 0x{int(src_binary_addr):x} outside address space"
            )
        if int(dest_runtime_addr) + length > self._address_space_size:
            raise MoveError(
                f"move would overflow address space at dest: "
                f"0x{int(dest_runtime_addr):x} + {length} > 0x{self._address_space_size:x}"
            )
        if int(src_binary_addr) + length > self._address_space_size:
            raise MoveError(
                f"move would overflow address space at src: "
                f"0x{int(src_binary_addr):x} + {length} > 0x{self._address_space_size:x}"
            )

        move_id = len(self._moves)
        if name is None:
            name = f"move_{move_id}"
        else:
            for existing in self._moves[1:]:
                if existing.name == name:
                    raise MoveError(
                        f"move name {name!r} already used by an earlier "
                        f"add_move; pick a unique name."
                    )

        new_move = Move(
            dest_runtime_addr,
            src_binary_addr,
            length,
            name=name,
            manager=self,
            move_id=move_id,
        )
        self._moves.append(new_move)
        for i in range(length):
            self._move_id_for_binary_addr[int(src_binary_addr) + i] = move_id

        # Mutating the registry invalidates the runtime→move-ids cache.
        self._cache = None
        return new_move

    # -- internal: active-move stack management (used by Move.__enter__
    # / Move.__exit__) ---------------------------------------------------

    def _push_active(self, move_id: int) -> None:
        if not self.is_valid_move_id(move_id):
            raise MoveError(
                f"can't activate move id {move_id}: not registered with "
                f"this MoveManager (registry has "
                f"{len(self._moves) - 1} user-declared moves: ids "
                f"1..{len(self._moves) - 1}). This usually means a "
                f"Move was used with the wrong Disassembler, or a "
                f"Move was constructed directly without going through "
                f"MoveManager.add_move()."
            )
        self._active_move_ids.append(move_id)

    def _pop_active(self, move_id: int) -> None:
        if not self._active_move_ids:
            raise MoveError(
                f"can't deactivate move id {move_id}: active-move "
                f"stack is empty. This can only happen when the "
                f"with-statement protocol is broken (e.g. __exit__ "
                f"called without a matching __enter__)."
            )
        popped = self._active_move_ids.pop()
        if popped != move_id:
            # Restore the popped element so the stack stays consistent
            # for any caller that catches the exception.
            self._active_move_ids.append(popped)
            raise MoveError(
                f"move-stack discipline violated: tried to deactivate "
                f"move id {move_id} but the topmost active move is "
                f"{popped}. with-blocks for moves must nest in LIFO "
                f"order; manual stack manipulation will trip this check."
            )

    def b2r(self, binary_addr) -> RuntimeAddr:
        """Convert a binary address to its (unique) runtime address."""
        binary_addr = BinaryAddr(binary_addr)
        assert is_valid_binary_addr(binary_addr)
        move_id = self._move_id_for_binary_addr[int(binary_addr)]
        md = self._moves[move_id]
        return md.convert_binary_to_runtime_addr(binary_addr)

    def r2b(
        self,
        runtime_addr,
        specific_move_id: int | None = None,
    ) -> tuple[BinaryAddr | None, int | None]:
        """Convert a runtime address to ``(binary_addr, move_id)``.

        - With ``specific_move_id``: use that move directly.
        - With no relevant moves at the runtime address: identity-map
          to ``(BinaryAddr(runtime_addr), BASE_MOVE_ID)``.
        - With one relevant move: use it.
        - With multiple relevant moves: pick the most-recently-active one
          on the move stack; if none of the candidates is active, return
          ``(None, None)`` to signal ambiguity.
        """
        runtime_addr = RuntimeAddr(runtime_addr)

        if specific_move_id is None:
            relevant = self.move_ids_for_runtime_addr(runtime_addr)
            if not relevant:
                return BinaryAddr(int(runtime_addr)), BASE_MOVE_ID
            if len(relevant) == 1:
                specific_move_id = next(iter(relevant))
            else:
                # Walk the active stack from most-recent backwards.
                specific_move_id = None
                for active in reversed(self._active_move_ids):
                    if active in relevant:
                        specific_move_id = active
                        break
                if specific_move_id is None:
                    return None, None

        md = self._moves[specific_move_id]
        if md.is_in_move_dest(runtime_addr, include_end_address=True):
            return md.convert_runtime_to_binary_addr(runtime_addr), specific_move_id
        return None, None

    def r2b_checked(self, runtime_addr) -> BinaryLocation:
        """Like :meth:`r2b` but raises on ambiguous resolution."""
        runtime_addr = RuntimeAddr(runtime_addr)
        binary_addr, move_id = self.r2b(runtime_addr)
        if binary_addr is None:
            raise MoveError(
                f"Ambiguous runtime address 0x{int(runtime_addr):x}: "
                f"multiple moves target this address and none of them is "
                f"on the active-move stack {self._active_move_ids}"
            )
        return BinaryLocation(binary_addr, move_id)

    def move_ids_for_runtime_addr(self, runtime_addr) -> set[int]:
        """All move_ids whose dest range covers ``runtime_addr``.

        The base move (BASE_MOVE_ID) is excluded — it always covers
        the whole space and would drown out the signal.
        """
        runtime_addr = RuntimeAddr(runtime_addr)
        assert is_valid_runtime_addr(runtime_addr, allow_final_address=True)
        if self._cache is None:
            self._rebuild_cache()
        return self._cache.get(runtime_addr, set())

    def _rebuild_cache(self) -> None:
        cache: dict[RuntimeAddr, set[int]] = defaultdict(set)
        for binary_addr_int, move_id in enumerate(self._move_id_for_binary_addr):
            if move_id == BASE_MOVE_ID:
                continue
            runtime_addr = self.b2r(BinaryAddr(binary_addr_int))
            cache[runtime_addr].add(move_id)
        self._cache = dict(cache)

    def make_binary_location(self, binary_loc) -> BinaryLocation:
        """Coerce an int or :class:`BinaryLocation` to a
        :class:`BinaryLocation`, using the topmost active move (or
        BASE_MOVE_ID) for the move_id when an int is given.
        """
        if isinstance(binary_loc, BinaryLocation):
            return binary_loc
        last_active = (
            self._active_move_ids[-1] if self._active_move_ids else BASE_MOVE_ID
        )
        return BinaryLocation(BinaryAddr(int(binary_loc)), last_active)

    def make_runtime_location(self, runtime_loc) -> RuntimeLocation:
        """Coerce an int or :class:`RuntimeLocation` to a
        :class:`RuntimeLocation`, using the topmost active move (or
        BASE_MOVE_ID) for the move_id when an int is given.
        """
        if isinstance(runtime_loc, RuntimeLocation):
            return runtime_loc
        last_active = (
            self._active_move_ids[-1] if self._active_move_ids else BASE_MOVE_ID
        )
        return RuntimeLocation(RuntimeAddr(int(runtime_loc)), last_active)
