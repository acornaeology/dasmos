"""The :class:`Disassembler` orchestration class.

The Disassembler is the single object a driver script (or CLI
invocation) interacts with: it owns one of each manager class
(memory, moves, labels, classifications, expressions, config), wires
them together with the CPU plug-in's address-space sizing, and
exposes the flat driver-script API documented in
``docs/design/architecture.md``.

This is the *skeleton* — the trace loop, the leftover-classification
pass, and the full driver-script API land in subsequent ports
(tasks #16–#19).

Per ``docs/design/decisions.md``:

- D-004: each model concern is its own manager class held by the
  Disassembler.
- D-008: instance constructor takes ``cpu=`` directly; the
  :meth:`Disassembler.create` factory accepts a string and resolves
  via Stevedore.
- D-009: :meth:`disassemble` returns an
  :class:`~dasmos.ir.IntermediateRepresentation`; rendering happens on
  the IR.
- D-010: multiple binaries per Disassembler.
- D-011: flat driver-script methods.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from dasmos.core.annotations import Align, AnnotationStore, Banner, Comment
from dasmos.core.classification import Byte, ExpressionRegistry, Fill, String, Word
from dasmos.core.config import Config
from dasmos.core.disassembly import (
    ClassificationError,
    ClassificationStore,
)
from dasmos.core.labels import LabelManager
from dasmos.core.memory import BinaryAddr, MemoryImage
from dasmos.core.move import MoveManager
from dasmos.cpu import Cpu, create_cpu
from dasmos.exceptions import DasmosError
from dasmos.ir import IntermediateRepresentation


class DisassemblerError(DasmosError):
    """Raised on misuse of the :class:`Disassembler` orchestration."""


class Disassembler:
    """The orchestration class.

    Owns one instance of each manager class; delegates the flat
    driver-script API to those managers; produces an
    :class:`~dasmos.ir.IntermediateRepresentation` via
    :meth:`disassemble`.
    """

    def __init__(self, cpu: Cpu):
        self._cpu = cpu
        self._config = Config()
        size = cpu.address_space_size
        self._memory = MemoryImage(address_space_size=size)
        self._moves = MoveManager(address_space_size=size)
        self._labels = LabelManager(self._moves)
        self._classifications = ClassificationStore()
        self._expressions = ExpressionRegistry()
        self._annotations = AnnotationStore()
        self._entry_points: list[BinaryAddr] = []
        self._traced: set[int] = set()
        self._disassembled = False

    # -- factory ---------------------------------------------------------

    @classmethod
    def create(cls, cpu: str | Cpu, **cpu_kwargs: Any) -> "Disassembler":
        """Construct a :class:`Disassembler` with a string-named CPU
        plug-in or with an explicit instance.

        Strings are resolved via Stevedore from the ``dasmos.cpu``
        entry-point namespace; extra ``cpu_kwargs`` are forwarded to
        the plug-in's constructor. Instances are used directly.
        """
        if isinstance(cpu, str):
            cpu = create_cpu(cpu, **cpu_kwargs)
        return cls(cpu=cpu)

    # -- accessors -------------------------------------------------------

    @property
    def cpu(self) -> Cpu:
        return self._cpu

    @property
    def memory(self) -> MemoryImage:
        return self._memory

    @property
    def moves(self) -> MoveManager:
        return self._moves

    @property
    def labels(self) -> LabelManager:
        return self._labels

    @property
    def classifications(self) -> ClassificationStore:
        return self._classifications

    @property
    def expressions(self) -> ExpressionRegistry:
        return self._expressions

    @property
    def annotations(self) -> AnnotationStore:
        return self._annotations

    @property
    def config(self) -> Config:
        return self._config

    # -- driver-script API: setup ---------------------------------------

    def load(self, filepath, binary_addr, md5sum: str | None = None):
        """Load a binary file at ``binary_addr``. Delegates to
        :class:`~dasmos.core.memory.MemoryImage.load`.
        """
        self._raise_if_disassembled("load")
        return self._memory.load(filepath, binary_addr, md5sum=md5sum)

    def add_move(self, dest_runtime_addr, src_binary_addr, length: int) -> int:
        """Register a relocation. Returns the move_id."""
        self._raise_if_disassembled("add_move")
        return self._moves.add_move(dest_runtime_addr, src_binary_addr, length)

    def using_move(self, move_id: int):
        """Push ``move_id`` onto the active-move stack for the duration
        of the ``with`` block. Replaces py8dis's ``with move_id:``
        idiom (D-006 / D-011).
        """
        return self._moves.using(move_id)

    # -- driver-script API: entry points --------------------------------

    def entry(self, runtime_addr, name: str | None = None, **label_kwargs):
        """Register a code entry point at ``runtime_addr``.

        The trace loop will start here. If ``name`` is given, also
        defines a label at the same runtime address (any extra kwargs
        are forwarded to :meth:`label`).

        The runtime address is resolved to a binary address via the
        active-move stack on the move manager — entry points outside
        any move identity-map.
        """
        self._raise_if_disassembled("entry")
        binary_loc = self._moves.r2b_checked(runtime_addr)
        self._entry_points.append(binary_loc.binary_addr)
        if name is not None:
            self.label(runtime_addr, name, **label_kwargs)

    # -- driver-script API: labels --------------------------------------

    def label(self, runtime_addr, name: str, **kwargs):
        """Define a label. Delegates to
        :meth:`~dasmos.core.labels.LabelManager.add_label`.
        """
        self._raise_if_disassembled("label")
        return self._labels.add_label(runtime_addr, name, **kwargs)

    def local_label(self, runtime_addr, name: str, start_addr, end_addr, **kwargs):
        """Define a label scoped to ``[start_addr, end_addr)``."""
        self._raise_if_disassembled("local_label")
        return self._labels.add_local_label(
            runtime_addr, name, start_addr, end_addr, **kwargs,
        )

    def expr_label(self, runtime_addr, expression: str, **kwargs):
        """Register an expression to be used as a label reference."""
        self._raise_if_disassembled("expr_label")
        return self._labels.add_expression(runtime_addr, expression, **kwargs)

    # -- driver-script API: data classification -------------------------

    def byte(self, binary_addr, length: int = 1, cols: int | None = None):
        """Mark ``length`` bytes at ``binary_addr`` as raw bytes."""
        self._raise_if_disassembled("byte")
        self._classifications.add_classification(binary_addr, Byte(length, cols))

    def word(self, binary_addr, length: int = 2, cols: int | None = None):
        """Mark ``length`` bytes at ``binary_addr`` as 16-bit words."""
        self._raise_if_disassembled("word")
        self._classifications.add_classification(binary_addr, Word(length, cols))

    def fill(self, binary_addr, length: int, value: int):
        """Mark a run of ``length`` identical ``value`` bytes."""
        self._raise_if_disassembled("fill")
        self._classifications.add_classification(binary_addr, Fill(length, value))

    def string(self, binary_addr, length: int):
        """Mark ``length`` bytes at ``binary_addr`` as a string."""
        self._raise_if_disassembled("string")
        self._classifications.add_classification(binary_addr, String(length))

    # -- driver-script API: expressions ---------------------------------

    def expr(
        self,
        runtime_addr,
        expression: str,
        *,
        move_id: int | None = None,
    ):
        """Override the rendered operand at ``runtime_addr`` with the
        given ``expression``.

        ``runtime_addr`` is the runtime address of the **operand byte**
        — typically one past the opcode for a single-byte-opcode CPU
        like the 6502. For example, an ``LDA #$03`` instruction at
        ``&8000`` has its operand byte at ``&8001``; calling
        ``d.expr(0x8001, "num_lives + 1")`` makes the renderer emit
        ``lda #num_lives + 1`` for that instruction.

        The expression is emitted verbatim — the driver is responsible
        for ensuring any names it references are valid in the rendered
        output (typically by also defining them via :meth:`label` or
        an external constant the assembler resolves).
        """
        self._raise_if_disassembled("expr")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._expressions.add(binary_addr, expression)

    # -- driver-script API: comments / annotations ----------------------

    def _resolve_to_binary_addr(
        self, runtime_addr, move_id: int | None,
    ) -> BinaryAddr:
        """Resolve a runtime address to its binary address via the
        move manager.

        Without ``move_id``, uses the active-move stack
        (:meth:`MoveManager.r2b_checked`); with an explicit
        ``move_id``, requires the address to map under that specific
        move and raises :class:`DisassemblerError` on failure.

        Common to every driver method that takes a runtime address.
        """
        if move_id is None:
            return self._moves.r2b_checked(runtime_addr).binary_addr
        from dasmos.core.memory import RuntimeAddr
        binary_addr, _ = self._moves.r2b(
            RuntimeAddr(runtime_addr), specific_move_id=move_id,
        )
        if binary_addr is None:
            raise DisassemblerError(
                f"runtime address 0x{int(runtime_addr):x} "
                f"does not map under move {move_id}"
            )
        return BinaryAddr(binary_addr)

    def comment(
        self,
        runtime_addr,
        text: str,
        *,
        align: Align = Align.BEFORE_LABEL,
        word_wrap: bool = True,
        indent: int = 0,
        move_id: int | None = None,
    ) -> None:
        """Attach a comment at ``runtime_addr``.

        ``align`` controls where the comment is rendered relative to
        the code line — ``BEFORE_LABEL`` (the default) puts it on
        its own line above any labels at the address; ``INLINE``
        appends it to the code line itself; the other positions
        (``AFTER_LABEL``, ``BEFORE_LINE``, ``AFTER_LINE``) cover
        less-common arrangements.

        The runtime address is resolved to a binary address via the
        active-move stack on the move manager, or via the explicit
        ``move_id`` if given.
        """
        self._raise_if_disassembled("comment")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._annotations.add(
            binary_addr,
            Comment(text=text, align=align, word_wrap=word_wrap, indent=indent),
        )

    def banner(
        self,
        runtime_addr,
        *,
        title: str = "",
        description: str = "",
        align: Align = Align.BEFORE_LABEL,
        move_id: int | None = None,
    ) -> None:
        """Attach a multi-line decorated comment block at
        ``runtime_addr`` — visual separation only; does not register
        an entry point.

        Use this for data regions you want to mark visually without
        the trace engine treating the address as code. (Replaces
        py8dis's ``subroutine(..., is_entry_point=False, hook=None)``
        idiom — see ``docs/design/commands-sweep-memo.md`` C2/C3.)

        For a subroutine that needs both visual separation AND
        entry-point registration, call :meth:`subroutine` with the
        same ``title`` / ``description`` kwargs.
        """
        self._raise_if_disassembled("banner")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._annotations.add(
            binary_addr,
            Banner(title=title, description=description, align=align),
        )

    def subroutine(
        self,
        runtime_addr,
        name: str | None = None,
        *,
        title: str = "",
        description: str = "",
        move_id: int | None = None,
    ) -> None:
        """Register a code entry point at ``runtime_addr``.

        Always seeds the trace from this address. If ``name`` is
        given, also defines a label there. If ``title`` or
        ``description`` is given, also attaches a banner-style
        comment block via :meth:`banner`.

        Replaces py8dis's ``subroutine(addr, name, ...)`` with the
        ``is_entry_point=True`` semantics implicit; the C2/C3 split
        (per the commands-sweep memo) means the
        ``is_entry_point=False`` data-banner case is now its own
        method, :meth:`banner`.
        """
        self._raise_if_disassembled("subroutine")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._entry_points.append(binary_addr)
        if name is not None:
            self._labels.add_label(runtime_addr, name, move_id=move_id)
        if title or description:
            self._annotations.add(
                binary_addr,
                Banner(title=title, description=description),
            )

    # -- the trace + render entry point ---------------------------------

    def disassemble(self) -> IntermediateRepresentation:
        """Run the trace loop, classify leftovers, and return an IR.

        One-shot: calling twice raises :class:`DisassemblerError`.

        The trace follows control flow from every registered entry
        point, classifying each instruction. Bytes loaded but not
        reached by trace (and not pre-classified by the user) are
        marked as :class:`~dasmos.core.classification.Byte` by the
        leftover pass.
        """
        if self._disassembled:
            raise DisassemblerError(
                "disassemble() has already been called on this Disassembler"
            )
        self._trace()
        self._classify_leftovers()
        self._disassembled = True
        return IntermediateRepresentation(self)

    # -- internals: trace loop ------------------------------------------

    def _trace(self) -> None:
        """Walk control flow from every registered entry point.

        For each binary address visited:

        - look up the opcode byte in the CPU's instruction table;
        - if recognised, classify the address span (skipping if the
          user has manually classified any of the bytes already);
        - compute the next addresses via
          :meth:`Opcode.next_addresses`;
        - enqueue any that fall inside loaded memory.

        Visited addresses are tracked so the trace terminates on
        cycles. Addresses outside loaded memory, undefined opcodes,
        and operand bytes that aren't loaded all silently terminate
        their respective trace paths.
        """
        opcodes = self._cpu.opcodes()
        pending: deque[int] = deque(int(a) for a in self._entry_points)

        while pending:
            addr = pending.popleft()
            if addr in self._traced:
                continue
            self._traced.add(addr)

            if not self._memory.is_loaded(addr):
                continue
            opcode_byte = self._memory.get_u8(addr)
            opcode = opcodes.get(opcode_byte)
            if opcode is None:
                # Undefined opcode — terminate this path.
                continue
            if not self._memory.is_loaded(addr, opcode.length()):
                # The opcode byte is loaded but its operand isn't —
                # we can't safely classify (and the renderer would
                # crash trying to read the operand). Terminate this
                # path; the opcode byte falls through to the leftover
                # pass as a Byte(1).
                continue

            # Classify (skip if any byte in the range is already
            # classified — could be a manual byte() call or a prior
            # trace path overlapping us).
            if not self._classifications.is_classified(addr, opcode.length()):
                try:
                    self._classifications.add_classification(addr, opcode)
                except ClassificationError:
                    # Defensive — is_classified should have caught
                    # this. Continue tracing regardless.
                    pass

            # Continue tracing whether we classified or not — the
            # control flow is determined by the opcode, not by who
            # owns the classification record.
            for next_addr in opcode.next_addresses(self._memory, addr):
                if 0 <= next_addr < self._memory.address_space_size:
                    pending.append(next_addr)

    def _classify_leftovers(self) -> None:
        """Mark every loaded-but-unclassified byte as a 1-byte
        :class:`~dasmos.core.classification.Byte`.

        Iterates all loaded ranges; any byte not already classified
        (either by trace or by a user driver-script call) becomes a
        ``Byte(1)``. This guarantees the renderer sees a complete
        classification of the loaded image.
        """
        for start, end in self._memory.load_ranges:
            for addr in range(int(start), int(end)):
                if self._memory.is_loaded(addr) and not self._classifications.is_classified(addr):
                    self._classifications.add_classification(addr, Byte(1))

    # -- internals ------------------------------------------------------

    def _raise_if_disassembled(self, op: str) -> None:
        if self._disassembled:
            raise DisassemblerError(
                f"{op}() called after disassemble(); the model is frozen"
            )
