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

from pathlib import Path
from typing import Any

from dasmos.core.classification import Byte, ExpressionRegistry, Fill, String, Word
from dasmos.core.config import Config
from dasmos.core.disassembly import ClassificationStore
from dasmos.core.labels import LabelManager
from dasmos.core.memory import MemoryImage
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

    def expr(self, binary_addr, expression: str):
        """Override the rendered operand at ``binary_addr`` with
        ``expression`` (e.g. ``"num_lives + 1"``).
        """
        self._raise_if_disassembled("expr")
        self._expressions.add(binary_addr, expression)

    # -- the trace + render entry point ---------------------------------

    def disassemble(self) -> IntermediateRepresentation:
        """Run the trace loop, classify leftovers, and return an IR.

        One-shot: calling twice raises :class:`DisassemblerError`.

        The trace loop and the leftover-classification pass are added
        in a subsequent port (task #18 continues from here once the
        first concrete CPU plug-in lands; for now ``disassemble`` just
        builds the IR over whatever the user has registered).
        """
        if self._disassembled:
            raise DisassemblerError(
                "disassemble() has already been called on this Disassembler"
            )
        # TODO (task #16-#18): run the trace loop here.
        # TODO (task #16-#18): classify_leftovers as Byte() to fill any
        #     loaded-but-unclassified bytes.
        self._disassembled = True
        return IntermediateRepresentation(self)

    # -- internals ------------------------------------------------------

    def _raise_if_disassembled(self, op: str) -> None:
        if self._disassembled:
            raise DisassemblerError(
                f"{op}() called after disassemble(); the model is frozen"
            )
