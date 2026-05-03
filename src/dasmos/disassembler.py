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

    def __init__(
        self,
        cpu: Cpu,
        *,
        environments: tuple = (),
        auto_labels_enabled: bool = True,
        auto_label_data_prefix: str = "l",
        auto_label_code_prefix: str = "c",
        auto_label_subroutine_prefix: str = "sub_c",
        auto_label_loop_prefix: str = "loop_c",
        auto_label_loop_limit: int = 256,
    ):
        self._cpu = cpu
        self._config = Config()
        # Subroutine hooks: callables fired by the trace when it
        # processes a JSR whose target runtime address is a key here.
        # Hook signature: ``(disassembler, jsr_binary_addr) -> int``,
        # returning the binary address where the trace continues.
        self._subroutine_hooks: dict[int, object] = {}
        # Auto-label generation policy. Each prefix is configurable so
        # a domain label that happens to start with the same prefix
        # doesn't collide with a synthesised one. Defaults match
        # py8dis's naming scheme.
        self.auto_labels_enabled = auto_labels_enabled
        self.auto_label_data_prefix = auto_label_data_prefix
        self.auto_label_code_prefix = auto_label_code_prefix
        self.auto_label_subroutine_prefix = auto_label_subroutine_prefix
        self.auto_label_loop_prefix = auto_label_loop_prefix
        self.auto_label_loop_limit = auto_label_loop_limit
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
        # Environments registered via constructor activate
        # immediately. Environments needing loaded memory should be
        # activated explicitly via use_environment() AFTER load().
        for env in environments:
            self.use_environment(env)

    # -- factory ---------------------------------------------------------

    @classmethod
    def create(cls, cpu: str | Cpu, **kwargs: Any) -> "Disassembler":
        """Construct a :class:`Disassembler` with a string-named CPU
        plug-in or with an explicit instance.

        Strings are resolved via Stevedore from the ``dasmos.cpu``
        entry-point namespace. Keyword arguments are partitioned: any
        kwarg whose name matches a parameter of :meth:`__init__` (e.g.
        ``auto_labels_enabled``, ``auto_label_subroutine_prefix``) is
        forwarded to the Disassembler; the rest go to the CPU plug-in's
        constructor. Instances are used directly.
        """
        import inspect
        disassembler_param_names = set(
            inspect.signature(cls.__init__).parameters
        ) - {"self", "cpu"}
        disassembler_kwargs = {
            k: v for k, v in kwargs.items() if k in disassembler_param_names
        }
        cpu_kwargs = {
            k: v for k, v in kwargs.items() if k not in disassembler_param_names
        }
        if isinstance(cpu, str):
            cpu = create_cpu(cpu, **cpu_kwargs)
        elif cpu_kwargs:
            raise DisassemblerError(
                f"Disassembler.create() got unexpected keyword arguments "
                f"{sorted(cpu_kwargs)} (CPU instance supplied — kwargs only "
                f"forward to the CPU constructor when ``cpu`` is a string)."
            )
        return cls(cpu=cpu, **disassembler_kwargs)

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

    # -- driver-script API: environments --------------------------------

    def use_environment(self, env) -> None:
        """Activate an environment plug-in on this disassembler.

        ``env`` may be a string (the registered name, resolved via
        Stevedore) or an :class:`~dasmos.environment.Environment`
        instance.

        Environments are **composable**: calling ``use_environment``
        more than once layers their effects in order. Activating the
        same environment twice is a harmless no-op (the underlying
        managers deduplicate registrations).

        Constructor sugar: ``Disassembler.create(cpu=...,
        environments=[...])`` activates each environment immediately
        in order. Environments that need loaded memory (e.g. one that
        inspects bytes at the ROM header) should be activated AFTER
        :meth:`load` rather than via the constructor kwarg.
        """
        from dasmos.environment import Environment, create_environment
        self._raise_if_disassembled("use_environment")
        if isinstance(env, str):
            env = create_environment(env)
        if not isinstance(env, Environment):
            raise TypeError(
                f"use_environment expected str or Environment, "
                f"got {type(env).__name__}"
            )
        env.setup(self)

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

    def optional_label(self, runtime_addr, name: str, **kwargs):
        """Define a label that the renderer emits only if it's
        referenced.

        Typical use: registering names for many out-of-range
        addresses (zero-page workspace, OS calls, hardware registers)
        without cluttering the rendered output with definitions for
        the ones that aren't actually referenced. Required labels
        (the default :meth:`label`) are always emitted; optional
        labels are emitted only when used.
        """
        self._raise_if_disassembled("optional_label")
        return self._labels.add_label(
            runtime_addr, name, is_optional=True, **kwargs,
        )

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

    # -- driver-script API: subroutine hooks ----------------------------

    def hook_subroutine(self, runtime_addr, name: str, hook) -> None:
        """Register a callable the trace fires when it processes a JSR
        whose operand resolves to ``runtime_addr``. Used for the
        inline-string idiom and similar non-standard return conventions.

        Hook signature::

            def hook(disassembler, jsr_binary_addr) -> int

        The hook returns the binary address where execution continues
        after the JSR. See :mod:`dasmos.hooks` for the bundled hooks
        (``stringhi_hook``, ``stringz_hook``, …) and the protocol
        details.

        Also registers ``name`` as an optional label at ``runtime_addr``
        so JSR operands resolve to the symbolic name in the rendered
        output. Mirrors py8dis's ``hook_subroutine`` behaviour.
        """
        self._raise_if_disassembled("hook_subroutine")
        self._labels.add_label(
            runtime_addr, name, is_optional=True,
        )
        self._subroutine_hooks[int(runtime_addr)] = hook

    # -- driver-script API: pointer-into-code helpers --------------------

    def code_ptr(
        self,
        runtime_addr_lo,
        runtime_addr_hi: int | None = None,
        *,
        offset: int = 0,
        label_name: str | None = None,
    ) -> None:
        """Mark two bytes of data as the address of a subroutine and
        seed the trace from the computed target.

        Reads the bytes at ``runtime_addr_lo`` (low half) and
        ``runtime_addr_hi`` (high half — defaults to ``runtime_addr_lo + 1``
        for the common adjacent-bytes case), computes the target as
        ``(hi << 8) | lo) + offset``, registers ``entry(target,
        name=label_name)``, and sets per-byte expression overrides so
        the source bytes render symbolically (``equw <label>`` or
        ``equb < (<label>)`` / ``equb > (<label>)``).

        Mirrors py8dis's ``code_ptr``. Used for jump tables where the
        low and high bytes of subroutine addresses are stored in
        separate parallel tables (see :meth:`rts_code_ptr` for the
        RTS-pop-and-INC variant).
        """
        self._raise_if_disassembled("code_ptr")
        if runtime_addr_hi is None:
            runtime_addr_hi = runtime_addr_lo + 1
        binary_lo = self._resolve_to_binary_addr(runtime_addr_lo, None)
        binary_hi = self._resolve_to_binary_addr(runtime_addr_hi, None)
        target = (
            self._memory.get_u8(binary_lo)
            | (self._memory.get_u8(binary_hi) << 8)
        ) + offset
        self.entry(target, name=label_name)
        # Resolve the label name actually registered (an explicit
        # one if label_name was given; otherwise auto-named at
        # disassemble() time — but we need a name NOW for the
        # expression. Fall back to literal hex if no name yet.)
        target_label = self._labels.get_label(target)
        if target_label is not None and target_label.explicit_name_texts():
            label_text = sorted(target_label.explicit_name_texts())[0]
        else:
            label_text = f"&{target:04x}"
        # The bytes contain target - offset, so the expression must
        # subtract the same offset from the label to evaluate to the
        # stored bytes. py8dis emits ``label-offset`` (e.g. "-1" for
        # the RTS variant).
        offset_str = "" if offset == 0 else f"-{offset}"
        expr = f"{label_text}{offset_str}"
        if int(binary_hi) == int(binary_lo) + 1:
            # Adjacent bytes — emit a single ``equw <expr>``.
            self.word(runtime_addr_lo)
            self.expr(runtime_addr_lo, expr)
        else:
            # Separate low/high tables — emit two equb lines with
            # beebasm's lo/hi byte operators.
            self.byte(runtime_addr_lo, 1)
            self.expr(runtime_addr_lo, f"< ({expr})")
            self.byte(runtime_addr_hi, 1)
            self.expr(runtime_addr_hi, f"> ({expr})")

    def rts_code_ptr(
        self,
        runtime_addr_lo,
        runtime_addr_hi: int | None = None,
        *,
        label_name: str | None = None,
    ) -> None:
        """Marks two bytes of data as the address of a subroutine
        targeted via RTS-pop-then-INC (so the bytes contain
        ``target - 1``). Equivalent to :meth:`code_ptr` with
        ``offset=1``.
        """
        self.code_ptr(
            runtime_addr_lo, runtime_addr_hi,
            offset=1, label_name=label_name,
        )

    def stringz(
        self,
        runtime_addr,
        *,
        move_id: int | None = None,
    ) -> int:
        """Classify a NUL-terminated string starting at
        ``runtime_addr``; returns the runtime address of the byte
        right after the NUL terminator.

        Mirrors py8dis's ``stringz()``. Scans forward through loaded
        memory until the first ``0`` byte; classifies the whole span
        (including the terminator) as a String. Driver scripts use
        the return value to chain through a sequence of strings::

            addr = d.stringz(0x9000)
            addr = d.stringz(addr)  # next string follows
        """
        self._raise_if_disassembled("stringz")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        scan = int(binary_addr)
        limit = self._cpu.address_space_size
        while scan < limit:
            if not self._memory.is_loaded(scan):
                raise DisassemblerError(
                    f"stringz at {int(runtime_addr):04x} ran into "
                    f"unloaded memory at binary {scan:04x} without "
                    f"finding a NUL terminator"
                )
            if self._memory.get_u8(scan) == 0:
                break
            scan += 1
        length = scan - int(binary_addr) + 1
        self.string(runtime_addr, length, move_id=move_id)
        return int(runtime_addr) + length

    # -- driver-script API: data classification -------------------------

    def byte(
        self,
        runtime_addr,
        length: int = 1,
        cols: int | None = None,
        *,
        move_id: int | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as raw bytes."""
        self._raise_if_disassembled("byte")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._classifications.add_classification(binary_addr, Byte(length, cols))

    def word(
        self,
        runtime_addr,
        length: int = 2,
        cols: int | None = None,
        *,
        move_id: int | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as 16-bit words."""
        self._raise_if_disassembled("word")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        self._classifications.add_classification(binary_addr, Word(length, cols))

    def fill(
        self,
        runtime_addr,
        length: int,
        value: int | None = None,
        *,
        move_id: int | None = None,
    ):
        """Mark a run of ``length`` identical bytes at ``runtime_addr``.

        ``value`` is the byte the fill should expand to. If omitted,
        it's inferred from the loaded memory (the byte at
        ``runtime_addr``) — matching py8dis's idiom of ``fill(addr, n)``
        for runs of the same value the binary already contains. If
        ``value`` is supplied AND disagrees with the loaded byte,
        raises :class:`DisassemblerError`.
        """
        self._raise_if_disassembled("fill")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
        if value is None:
            # Infer from memory; requires the byte to be loaded.
            value = self._memory.get_u8(binary_addr)
        elif self._memory.is_loaded(binary_addr):
            # If both value and a loaded byte are present, they must
            # agree — otherwise the rendered fill would re-assemble
            # to bytes that differ from the source.
            actual = self._memory.get_u8(binary_addr)
            if actual != value:
                raise DisassemblerError(
                    f"fill value mismatch at 0x{int(binary_addr):x}: "
                    f"loaded byte is 0x{actual:x}, requested 0x{value:x}"
                )
        self._classifications.add_classification(binary_addr, Fill(length, value))

    def string(
        self,
        runtime_addr,
        length: int,
        *,
        move_id: int | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as a string."""
        self._raise_if_disassembled("string")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move_id)
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
        on_entry: dict[str, str] | None = None,
        on_exit: dict[str, str] | None = None,
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
            Banner(
                title=title, description=description,
                on_entry=on_entry, on_exit=on_exit,
                align=align,
            ),
        )

    def subroutine(
        self,
        runtime_addr,
        name: str | None = None,
        *,
        title: str = "",
        description: str = "",
        on_entry: dict[str, str] | None = None,
        on_exit: dict[str, str] | None = None,
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
        if title or description or on_entry or on_exit:
            self._annotations.add(
                binary_addr,
                Banner(
                    title=title, description=description,
                    on_entry=on_entry, on_exit=on_exit,
                ),
            )

    # -- the trace + render entry point ---------------------------------

    def disassemble(self) -> IntermediateRepresentation:
        """Run the trace loop, classify leftovers, and return an IR.

        One-shot: calling twice raises :class:`DisassemblerError`.

        Pipeline:

        1. **Trace** — follow control flow from every registered entry
           point, classifying each instruction.
        2. **Leftover classification** — bytes loaded but not reached
           by trace (and not pre-classified by the user) become
           :class:`~dasmos.core.classification.Byte` 1-byte items.
        3. **Reference analysis** — walk every classified opcode and
           record use sites against any label at the operand target.
        4. **Auto-label generation** (when ``auto_labels_enabled``) —
           synthesise names for referenced addresses without explicit
           names. Names land in the LabelManager with
           ``is_autogenerated=True`` so renderers and other consumers
           see them as ordinary (optional) labels via the standard
           label-resolution paths.
        """
        if self._disassembled:
            raise DisassemblerError(
                "disassemble() has already been called on this Disassembler"
            )
        self._trace()
        self._classify_leftovers()
        refs_by_addr = self._compute_references()
        if self.auto_labels_enabled:
            self._generate_auto_labels(refs_by_addr)
            self._synthesise_offset_bases()
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
            #
            # Subroutine hooks: when this is a JSR whose target has a
            # registered hook, the hook decides where the trace
            # continues *instead of* the default fall-through. The
            # target (the called subroutine) is still queued.
            from dasmos.cpu import FlowControl as _FlowControl
            if (
                opcode.flow_control is _FlowControl.SUBROUTINE_CALL
                and self._subroutine_hooks
            ):
                target = opcode._compute_target(self._memory, addr)
                if target is not None and target in self._subroutine_hooks:
                    hook = self._subroutine_hooks[target]
                    continuation = hook(self, addr)
                    if (
                        continuation is not None
                        and 0 <= continuation < self._memory.address_space_size
                    ):
                        pending.append(continuation)
                    if 0 <= target < self._memory.address_space_size:
                        pending.append(target)
                    continue
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

    # -- internals: reference analysis + auto-label generation ----------

    def _compute_references(self) -> dict[int, list[int]]:
        """Walk every classified opcode, resolve operand → target,
        and record use sites against any label at the target.

        Returns ``{target_runtime_addr: [ref_binary_addr, …]}`` for
        the auto-label pass to consume — even targets that don't yet
        have a label appear here.
        """
        from dasmos.cpu import Opcode, OperandKind
        from dasmos.core.memory import BinaryLocation
        refs_by_addr: dict[int, list[int]] = {}
        for binary_addr, classification in self._classifications.iter_classified_starts():
            if not isinstance(classification, Opcode):
                continue
            target = self._operand_label_target(int(binary_addr), classification)
            if target is None:
                continue
            refs_by_addr.setdefault(target, []).append(int(binary_addr))
            label = self._labels.get_label(target)
            if label is not None:
                label.add_reference(BinaryLocation(int(binary_addr), 0))
        return refs_by_addr

    def _operand_label_target(self, binary_addr: int, opcode) -> int | None:
        """Return the runtime address an opcode's operand resolves to,
        or ``None`` for non-address operand kinds (immediate / no
        operand / overridden by user expression).
        """
        from dasmos.cpu import OperandKind
        operand_addr = binary_addr + 1
        if self._expressions.get_or_none(operand_addr) is not None:
            return None
        kind = opcode.addressing_mode.operand_kind
        if kind in (OperandKind.NONE, OperandKind.IMMEDIATE):
            return None
        if kind is OperandKind.ADDRESS_8:
            return self._memory.get_u8(operand_addr)
        if kind in (OperandKind.ADDRESS_16, OperandKind.ADDRESS_16_INDIRECT):
            return self._memory.get_u16_le(operand_addr)
        if kind is OperandKind.RELATIVE_OFFSET:
            offset = self._memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            return binary_addr + opcode.length() + offset
        return None

    def _generate_auto_labels(
        self, refs_by_addr: dict[int, list[int]],
    ) -> None:
        """For every referenced address with no explicit name,
        synthesise one and register it in the LabelManager with
        ``is_autogenerated=True``. Renderers see them via the standard
        label-resolution paths — no special auto-label code path
        downstream.

        Heuristics (py8dis-compatible defaults; each prefix is set on
        the Disassembler constructor):

        - ``<data_prefix><addr>``       — address has data classification
        - ``<code_prefix><addr>``       — address has code, no other
          heuristic matches
        - ``<subroutine_prefix><addr>`` — every reference is a JSR
        - ``<loop_prefix><addr>``       — single ref, backward branch
          within ``auto_label_loop_limit`` bytes
        """
        from dasmos.core.memory import BinaryLocation, RuntimeAddr
        for runtime_addr, ref_binary_addrs in refs_by_addr.items():
            existing = self._labels.get_label(runtime_addr)
            if existing is not None and existing.explicit_name_texts():
                continue
            name = self._synthesise_auto_label_name(
                runtime_addr, sorted(set(ref_binary_addrs)),
            )
            self._labels.add_label(
                runtime_addr, name,
                is_autogenerated=True, is_optional=True,
            )
            label = self._labels.get_label(runtime_addr)
            for ref in sorted(set(ref_binary_addrs)):
                label.add_reference(BinaryLocation(ref, 0))

    def _synthesise_auto_label_name(
        self, runtime_addr: int, ref_binary_addrs: list[int],
    ) -> str:
        """Pick a prefix per the py8dis heuristics and return the
        full ``<prefix><addr>`` name. ``ref_binary_addrs`` is
        deduplicated and sorted by the caller.
        """
        from dasmos.core.memory import RuntimeAddr
        from dasmos.cpu import FlowControl, Opcode
        addr_hex = f"{runtime_addr:04x}"

        binary_addr_loc, _ = self._moves.r2b(RuntimeAddr(runtime_addr))
        classification = None
        if binary_addr_loc is not None:
            classification = self._classifications.get_classification(
                int(binary_addr_loc),
            )
        is_code = isinstance(classification, Opcode)
        if not is_code:
            return f"{self.auto_label_data_prefix}{addr_hex}"

        # Look up each ref-site's opcode for the heuristics.
        ref_opcodes: list[Opcode | None] = []
        for ref_addr in ref_binary_addrs:
            c = self._classifications.get_classification(ref_addr)
            ref_opcodes.append(c if isinstance(c, Opcode) else None)

        if ref_opcodes and all(
            op is not None and op.flow_control is FlowControl.SUBROUTINE_CALL
            for op in ref_opcodes
        ):
            return f"{self.auto_label_subroutine_prefix}{addr_hex}"

        if (
            len(ref_binary_addrs) == 1
            and ref_opcodes[0] is not None
            and ref_opcodes[0].flow_control is FlowControl.CONDITIONAL_BRANCH
        ):
            ref_addr = ref_binary_addrs[0]
            if 0 <= ref_addr - runtime_addr < self.auto_label_loop_limit:
                return f"{self.auto_label_loop_prefix}{addr_hex}"

        return f"{self.auto_label_code_prefix}{addr_hex}"

    def _synthesise_offset_bases(self) -> None:
        """For every label at a *mid-instruction* runtime address,
        ensure the start of the containing classification has a label
        — synthesising an auto-label there if it doesn't.

        Lets the renderer express the mid-instruction label as an
        offset of the base (``nmi1_transfer_addr = sub_cfe15+1``)
        instead of as a literal hex equate. Mirrors py8dis's
        behaviour for in-range mid-instruction labels.

        Uses ``auto_label_subroutine_prefix`` for the synthesised
        base name (matches py8dis: the bases py8dis creates for this
        purpose use the ``sub_c`` form regardless of the actual flow
        control at the base address).
        """
        from dasmos.core.disassembly import INSIDE_A_CLASSIFICATION
        from dasmos.core.memory import BinaryAddr, RuntimeAddr
        bases_to_add: list[int] = []
        for runtime_addr, label in list(self._labels.items()):
            if not label.explicit_name_texts():
                continue
            binary_loc, _ = self._moves.r2b(RuntimeAddr(int(runtime_addr)))
            if binary_loc is None:
                continue
            binary_addr = int(binary_loc)
            # Skip mid-instruction labels inside moved regions: the
            # inline body walk visits those bytes at their MOVE-DEST
            # runtime (via b2r), so the natural-runtime label can't be
            # anchored inline. py8dis keeps these as literal hex
            # equates; we do the same.
            if int(self._moves.b2r(BinaryAddr(binary_addr))) != int(runtime_addr):
                continue
            c = self._classifications.get_classification(binary_addr)
            if c is not INSIDE_A_CLASSIFICATION:
                continue
            # Walk back to find the classification's start.
            start = binary_addr - 1
            while start >= 0:
                sc = self._classifications.get_classification(start)
                if sc is None:
                    start = -1
                    break
                if sc is not INSIDE_A_CLASSIFICATION:
                    break
                start -= 1
            if start < 0:
                continue
            start_runtime = int(self._moves.b2r(BinaryAddr(start)))
            existing = self._labels.get_label(start_runtime)
            if existing is not None and existing.explicit_name_texts():
                continue  # base already has a name
            if start_runtime not in bases_to_add:
                bases_to_add.append(start_runtime)
        for start_runtime in bases_to_add:
            name = f"{self.auto_label_subroutine_prefix}{start_runtime:04x}"
            self._labels.add_label(
                start_runtime, name,
                is_autogenerated=True, is_optional=True,
            )

    # -- internals ------------------------------------------------------

    def _raise_if_disassembled(self, op: str) -> None:
        if self._disassembled:
            raise DisassemblerError(
                f"{op}() called after disassemble(); the model is frozen"
            )
