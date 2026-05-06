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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dasmos.core.annotations import Align, AnnotationStore, Banner, Comment
from dasmos.core.classification import Byte, ExpressionRegistry, Fill, String, Word
from dasmos.core.format_hint import FormatHint, FormatHintRegistry
from dasmos.core.config import Config
from dasmos.core.disassembly import (
    ClassificationError,
    ClassificationStore,
)
from dasmos.core.labels import LabelManager
from dasmos.core.memory import BinaryAddr, MemoryImage
from dasmos.core.move import Move, MoveManager
from dasmos.cpu import Cpu, create_cpu
from dasmos.exceptions import DasmosError
from dasmos.ir import IntermediateRepresentation


class DisassemblerError(DasmosError):
    """Raised on misuse of the :class:`Disassembler` orchestration."""


def _is_printable_ascii(byte_value: int) -> bool:
    """True for bytes in the printable ASCII range 0x20..0x7E.

    Matches py8dis's ``utils.isprint``: excludes control characters
    (including DEL 0x7F) and high-bit bytes (0x80–0xFF). Used by the
    string-run heuristic to decide whether a byte could be part of a
    text string.
    """
    return 0x20 <= byte_value <= 0x7E


@dataclass
class Constant:
    """A named value registered via :meth:`Disassembler.constant`.

    Distinct from :class:`~dasmos.core.labels.Label` — constants are
    arbitrary named values (magic numbers, OSBYTE call numbers,
    hardware register addresses) that the driver wants to surface as a
    separate ``constants`` section in structured output. The
    :meth:`Disassembler.constant` method ALSO calls
    :meth:`Disassembler.optional_label` so the asm equate emission is
    unchanged from the legacy ``constant() → optional_label`` porter
    rename.
    """

    name: str
    value: int
    comment: str | None = None


@dataclass
class SubroutineEntry:
    """Subroutine metadata registered via :meth:`Disassembler.subroutine`.

    Holds the runtime address plus the kwargs the driver supplied;
    rendering computes fall-through and per-name fields at emission
    time.
    """

    runtime_addr: int
    binary_addr: int | None
    move_id: int | None
    name: str | None
    title: str
    description: str
    on_entry: dict[str, str] = field(default_factory=dict)
    on_exit: dict[str, str] = field(default_factory=dict)


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
        auto_label_data_prefix: str = "data_",
        auto_label_code_prefix: str = "code_",
        auto_label_subroutine_prefix: str = "sub_",
        auto_label_loop_prefix: str = "loop_",
        auto_label_loop_limit: int = 256,
        auto_label_return_prefix: str | None = "return_",
        string_detection_min_length: int | None = 3,
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
        # doesn't collide with a synthesised one.
        self.auto_labels_enabled = auto_labels_enabled
        self.auto_label_data_prefix = auto_label_data_prefix
        self.auto_label_code_prefix = auto_label_code_prefix
        self.auto_label_subroutine_prefix = auto_label_subroutine_prefix
        self.auto_label_loop_prefix = auto_label_loop_prefix
        self.auto_label_loop_limit = auto_label_loop_limit
        # Set to a string like ``"return_"`` to enable the
        # return-RTS rule: any autogenerated label whose target
        # address holds a single-byte ``RTS`` opcode is renamed
        # ``<prefix><sequential_N>`` (so a column of
        # ``code_8042`` / ``code_80a3`` / ``code_8157`` becomes
        # ``return_1`` / ``return_2`` / ``return_3``, conveying
        # "this is just an exit point" at a glance). Set to None
        # to opt out and use the standard code-prefix shape for
        # bare-RTS targets too.
        self.auto_label_return_prefix = auto_label_return_prefix
        # Sequential id assigned per unique RTS-target address, in
        # discovery order. Populated during _generate_auto_labels.
        self._return_label_id_for_addr: dict[int, int] = {}
        # Heuristic that promotes runs of unclassified printable ASCII
        # bytes to ``String`` classifications, so a run of N >= this
        # threshold renders as one ``equs "..."`` directive instead of
        # N individual ``equb`` rows. Set to ``None`` to disable
        # entirely. Read by :meth:`disassemble` between :meth:`_trace`
        # and :meth:`_classify_leftovers`. Default 3 matches py8dis's
        # ``autostring(min_length=3)``.
        self.string_detection_min_length = string_detection_min_length
        size = cpu.address_space_size
        self._memory = MemoryImage(address_space_size=size)
        self._moves = MoveManager(address_space_size=size)
        self._labels = LabelManager(self._moves)
        self._classifications = ClassificationStore()
        self._expressions = ExpressionRegistry()
        self._format_hints = FormatHintRegistry()
        self._annotations = AnnotationStore()
        self._entry_points: list[BinaryAddr] = []
        self._traced: set[int] = set()
        # Named values registered via :meth:`constant`. Distinct from
        # labels — these are arbitrary values (e.g. magic numbers,
        # hardware register addresses) the driver wants to give a name
        # AND surface as a separate ``constants`` section in
        # structured output. Internally :meth:`constant` ALSO calls
        # :meth:`optional_label` so the asm equate emission is
        # unchanged from the legacy ``constant() → optional_label``
        # porter rename.
        self._constants: list[Constant] = []
        # Subroutine metadata registered via :meth:`subroutine` —
        # name, banner content, fall-through computed at render time.
        self._subroutines: list[SubroutineEntry] = []
        # Per-binary-address CPU state, computed by the post-trace
        # ``_compute_cpu_states`` linear sweep. Maps the address of
        # each classified opcode to the CpuState IMMEDIATELY BEFORE
        # that instruction executes (so a JSR analyzer can ask
        # "what was A just before the JSR?"). Stays empty when the
        # CPU plug-in opts out of state tracking
        # (``Cpu.initial_state`` returns None).
        self._cpu_state_at: dict[int, object] = {}
        # Deferred expressions: a list of ``(binary_addr,
        # target_runtime_addr, build_text)`` triples registered by
        # ``code_ptr`` / ``rts_code_ptr`` (and any future caller that
        # wants to resolve the target's label name AFTER the trace
        # has filled out the auto-label store). Resolved by
        # :meth:`_resolve_deferred_expressions` after auto-label
        # generation.
        self._deferred_expressions: list[tuple[int, int, object]] = []
        # Post-trace JSR analyzers registered by Environment plug-ins
        # (or driver scripts). Each maps a target runtime address to
        # a callable ``analyzer(disassembler, jsr_binary_addr,
        # state_before_jsr)``. Fired in the post-trace state pass —
        # has full CPU state available, unlike ``_subroutine_hooks``
        # which fires during trace before state is computed.
        self._post_trace_jsr_analyzers: dict[int, object] = {}
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
    def format_hints(self) -> FormatHintRegistry:
        return self._format_hints

    @property
    def annotations(self) -> AnnotationStore:
        return self._annotations

    @property
    def config(self) -> Config:
        return self._config

    @property
    def constants(self) -> list[Constant]:
        """Named values registered via :meth:`constant`. The
        :class:`Constant` records here also appear as optional labels
        in :attr:`labels` (for asm equate emission).
        """
        return self._constants

    @property
    def subroutines(self) -> list[SubroutineEntry]:
        """Subroutine metadata records registered via
        :meth:`subroutine`. The label name (when given) also appears
        in :attr:`labels`.
        """
        return self._subroutines

    # -- driver-script API: setup ---------------------------------------

    def load(self, filepath, binary_addr, md5sum: str | None = None):
        """Load a binary file at ``binary_addr``. Delegates to
        :class:`~dasmos.core.memory.MemoryImage.load`.
        """
        self._raise_if_disassembled("load")
        return self._memory.load(filepath, binary_addr, md5sum=md5sum)

    def add_move(
        self,
        dest_runtime_addr,
        src_binary_addr,
        length: int,
        *,
        name: str | None = None,
    ) -> Move:
        """Register a relocation. Returns the :class:`Move` handle.

        The Move is itself a context manager — ``with move: ...``
        scopes annotations under it. Pass ``name=`` to give the move
        a stable identity in diagnostics, JSON output, and
        cross-references.
        """
        self._raise_if_disassembled("add_move")
        return self._moves.add_move(
            dest_runtime_addr, src_binary_addr, length, name=name,
        )

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
        self._shift_move_kwarg(kwargs)
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
        self._shift_move_kwarg(kwargs)
        return self._labels.add_label(
            runtime_addr, name, is_optional=True, **kwargs,
        )

    def constant(
        self,
        value: int,
        name: str,
        comment: str | None = None,
    ) -> None:
        """Register a named value (a constant).

        Conceptually distinct from a label: constants are arbitrary
        named values (magic numbers, OSBYTE call numbers, hardware
        register addresses) — not necessarily addresses of code or
        data the disassembler will reach. The structured-output
        renderers surface them as a dedicated ``constants`` section.

        Constants are tracked SEPARATELY from labels. Mixing them
        would cause the hook-registered OSBYTE constants (e.g.
        ``osbyte_clear_escape = &7c``) to pollute operand resolution
        at zero-page address ``&7c``: any unrelated code reading
        from ``&7c`` would suddenly render as
        ``lda osbyte_clear_escape`` — a false positive.

        The ``BeebasmRenderer`` emits constants as equates in their
        own block alongside the label-equate table.
        """
        self._raise_if_disassembled("constant")
        self._constants.append(
            Constant(name=name, value=int(value), comment=comment),
        )

    def local_label(self, runtime_addr, name: str, start_addr, end_addr, **kwargs):
        """Define a label scoped to ``[start_addr, end_addr)``."""
        self._raise_if_disassembled("local_label")
        self._shift_move_kwarg(kwargs)
        return self._labels.add_local_label(
            runtime_addr, name, start_addr, end_addr, **kwargs,
        )

    def expr_label(self, runtime_addr, expression: str, **kwargs):
        """Register an expression to be used as a label reference."""
        self._raise_if_disassembled("expr_label")
        self._shift_move_kwarg(kwargs)
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
        output.
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

        Used for jump tables where the low and high bytes of
        subroutine addresses are stored in separate parallel tables
        (see :meth:`rts_code_ptr` for the RTS-pop-and-INC variant).
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
        # Format: ``label-offset`` for adjacent equw,
        # ``<(label-offset)`` / ``>(label-offset)`` for split lo/hi
        # tables (no space — matches the standard 6502 lo/hi
        # operator notation). The label name is resolved LAZILY at
        # render time via :meth:`_register_deferred_expression` so
        # subroutines registered LATER in the driver script still
        # surface symbolically.
        offset_str = "" if offset == 0 else f"-{offset}"
        if int(binary_hi) == int(binary_lo) + 1:
            self.word(runtime_addr_lo)
            self._register_deferred_expression(
                int(binary_lo), target,
                lambda name: f"{name}{offset_str}",
            )
        else:
            self.byte(runtime_addr_lo, 1)
            self._register_deferred_expression(
                int(binary_lo), target,
                lambda name: f"<({name}{offset_str})",
            )
            self.byte(runtime_addr_hi, 1)
            self._register_deferred_expression(
                int(binary_hi), target,
                lambda name: f">({name}{offset_str})",
            )

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
        move: Move | None = None,
    ) -> int:
        """Classify a NUL-terminated string starting at
        ``runtime_addr``; returns the runtime address of the byte
        right after the NUL terminator.

        Scans forward through loaded memory until the first ``0``
        byte; classifies the whole span (including the terminator)
        as a String. Driver scripts use the return value to chain
        through a sequence of strings::

            addr = d.stringz(0x9000)
            addr = d.stringz(addr)  # next string follows
        """
        return self._string_terminated(
            runtime_addr, 0x00, "stringz", "a NUL", move=move,
        )

    def stringcr(
        self,
        runtime_addr,
        *,
        move: Move | None = None,
    ) -> int:
        """Classify a CR-terminated string starting at ``runtime_addr``;
        returns the runtime address of the byte right after the
        terminator. The CR convention (``0x0D``) is the BBC OS's
        standard line-terminator for OSWRCH and command-line input.

        Behaves like :meth:`stringz` but with ``0x0D`` as the
        terminator; the terminator byte is included in the classified
        span (use ``d.byte`` if you need to classify them
        differently).
        """
        return self._string_terminated(
            runtime_addr, 0x0D, "stringcr", "a CR (&0d)", move=move,
        )

    def _string_terminated(
        self,
        runtime_addr,
        terminator: int,
        op_name: str,
        terminator_desc: str,
        *,
        move: Move | None = None,
    ) -> int:
        """Shared scan-and-classify loop for terminator-based string
        primitives. Scans loaded memory forward until ``terminator``
        is found; classifies the whole span (including the terminator
        byte) as a String. Returns the address right after the span.
        """
        self._raise_if_disassembled(op_name)
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        scan = int(binary_addr)
        limit = self._cpu.address_space_size
        while scan < limit:
            if not self._memory.is_loaded(scan):
                raise DisassemblerError(
                    f"{op_name} at {int(runtime_addr):04x} ran into "
                    f"unloaded memory at binary {scan:04x} without "
                    f"finding {terminator_desc}"
                )
            if self._memory.get_u8(scan) == terminator:
                break
            scan += 1
        length = scan - int(binary_addr) + 1
        self.string(runtime_addr, length, move=move)
        return int(runtime_addr) + length

    # -- driver-script API: data classification -------------------------

    def byte(
        self,
        runtime_addr,
        length: int = 1,
        cols: int | None = None,
        *,
        move: Move | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as raw bytes."""
        self._raise_if_disassembled("byte")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        self._classifications.add_classification(binary_addr, Byte(length, cols))

    def word(
        self,
        runtime_addr,
        length: int = 2,
        cols: int | None = None,
        *,
        move: Move | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as 16-bit words."""
        self._raise_if_disassembled("word")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        self._classifications.add_classification(binary_addr, Word(length, cols))

    def fill(
        self,
        runtime_addr,
        length: int,
        value: int | None = None,
        *,
        move: Move | None = None,
    ):
        """Mark a run of ``length`` identical bytes at ``runtime_addr``.

        ``value`` is the byte the fill should expand to. If omitted,
        it's inferred from the loaded memory (the byte at
        ``runtime_addr``) — the natural shape for runs of the same
        value the binary already contains. If ``value`` is supplied
        AND disagrees with the loaded byte, raises
        :class:`DisassemblerError`.
        """
        self._raise_if_disassembled("fill")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
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
        move: Move | None = None,
    ):
        """Mark ``length`` bytes at ``runtime_addr`` as a string."""
        self._raise_if_disassembled("string")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        self._classifications.add_classification(binary_addr, String(length))

    # -- driver-script API: expressions ---------------------------------

    def expr(
        self,
        runtime_addr,
        expression: str,
        *,
        move: Move | None = None,
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

        For renderer-agnostic semantic markers (e.g. "render this byte
        as an ASCII character / decimal / hex / binary"), use
        :meth:`format_hint` or its sugars (:meth:`char_literal`)
        instead — those declare *intent* and let each renderer choose
        its own syntax.
        """
        self._raise_if_disassembled("expr")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        self._expressions.add(binary_addr, expression)

    def format_hint(
        self,
        runtime_addr,
        hint: FormatHint,
        *,
        move: Move | None = None,
    ):
        """Mark the operand byte at ``runtime_addr`` with a renderer-
        agnostic format hint — a semantic declaration of how the byte
        should be interpreted (ASCII character, decimal, hex, binary,
        octal). Each renderer translates the hint to its assembler-
        specific syntax.

        Hints are weaker than :meth:`expr`: ``expr`` substitutes a
        concrete text expression; ``format_hint`` declares intent and
        leaves the syntax to the renderer. When both are registered
        at the same address, ``expr`` wins (the user's explicit text
        is more specific than a category).

        See :class:`dasmos.core.format_hint.FormatHint` for the full
        set of hints. :meth:`char_literal` is a sugar for the
        ``CHAR`` case.
        """
        self._raise_if_disassembled("format_hint")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        self._format_hints.add(binary_addr, hint)

    def char_literal(
        self,
        runtime_addr,
        *,
        move: Move | None = None,
    ):
        """Sugar for ``format_hint(runtime_addr, FormatHint.CHAR)``.

        Declares that the operand byte at ``runtime_addr`` is intended
        as an ASCII character literal. Renderers express this in
        their target assembler's grammar — beebasm emits ``ASC("c")``
        or ``'c'`` (per the renderer's ``char_literal_style``); a
        future ACME or ca65 renderer would emit ``'c'``; the JSON
        renderer surfaces the hint in its structured output.
        """
        self.format_hint(runtime_addr, FormatHint.CHAR, move=move)

    def inkey_code(
        self,
        runtime_addr,
        *,
        move: Move | None = None,
    ):
        """Sugar for ``format_hint(runtime_addr, FormatHint.INKEY)``.

        Declares that the operand byte at ``runtime_addr`` is the
        negative-X form of an Acorn INKEY scan code (the byte loaded
        into X for ``OSBYTE &79`` / ``OSBYTE &81`` to scan for a
        specific key by its internal number). Renderers express the
        byte symbolically as ``(255 - inkey_key_<name>) EOR 128``
        when the value matches a named INKEY key in the BBC's
        scan-code table; bytes that don't match any named key fall
        back to a hex literal with a one-time warning.

        Use this when the analyser can't infer the pattern from a
        nearby ``JSR osbyte`` — for example when the scan code lives
        in a table of pre-computed values, or is loaded into X
        through a longer pipeline of stores and reads.
        """
        self.format_hint(runtime_addr, FormatHint.INKEY, move=move)

    # -- driver-script API: comments / annotations ----------------------

    def _resolve_to_binary_addr(
        self, runtime_addr, move: Move | None,
    ) -> BinaryAddr:
        """Resolve a runtime address to its binary address via the
        move manager.

        Without ``move``, uses the active-move stack
        (:meth:`MoveManager.r2b_checked`); with an explicit
        ``move``, requires the address to map under that specific
        move and raises :class:`DisassemblerError` on failure.

        Common to every driver method that takes a runtime address.
        """
        move_id = self._move_to_id(move)
        if move_id is None:
            return self._moves.r2b_checked(runtime_addr).binary_addr
        from dasmos.core.memory import RuntimeAddr
        binary_addr, _ = self._moves.r2b(
            RuntimeAddr(runtime_addr), specific_move_id=move_id,
        )
        if binary_addr is None:
            raise DisassemblerError(
                f"runtime address 0x{int(runtime_addr):x} "
                f"does not map under move {move.name!r}"
            )
        return BinaryAddr(binary_addr)

    def _move_to_id(self, move: Move | None) -> int | None:
        """Convert a public Move handle to its internal integer id.
        Returns None for None. Validates that the move belongs to
        this disassembler — passing a Move from a different
        Disassembler is a programming error.
        """
        if move is None:
            return None
        if move._manager is not self._moves:
            raise DisassemblerError(
                f"move {move.name!r} belongs to a different disassembler; "
                f"each Move is bound to the MoveManager that created it."
            )
        return move._move_id

    def _shift_move_kwarg(self, kwargs: dict) -> None:
        """Translate a public ``move=Move`` kwarg in ``kwargs`` to
        the internal ``move_id=int`` form, in place. Public driver
        methods that delegate via ``**kwargs`` to internal stores
        (LabelManager, AnnotationStore, …) call this so the stores
        can keep their integer-id internal API.
        """
        if "move" in kwargs:
            kwargs["move_id"] = self._move_to_id(kwargs.pop("move"))

    def comment(
        self,
        runtime_addr,
        text: str,
        *,
        align: Align = Align.BEFORE_LABEL,
        word_wrap: bool = True,
        indent: int = 0,
        move: Move | None = None,
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
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
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
        move: Move | None = None,
    ) -> None:
        """Attach a multi-line decorated comment block at
        ``runtime_addr`` — visual separation only; does not register
        an entry point.

        Use this for data regions you want to mark visually without
        the trace engine treating the address as code. See
        ``docs/design/commands-sweep-memo.md`` C2/C3 for the
        rationale.

        For a subroutine that needs both visual separation AND
        entry-point registration, call :meth:`subroutine` with the
        same ``title`` / ``description`` kwargs.
        """
        self._raise_if_disassembled("banner")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
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
        is_entry_point: bool = True,
        move: Move | None = None,
    ) -> None:
        """Register a subroutine entry at ``runtime_addr``.

        Always records a :class:`SubroutineEntry` (so structured
        renderers can surface it). When ``is_entry_point`` is True
        (the default), also seeds the trace AND registers the label
        as REQUIRED. When False — used by environments to document
        out-of-image OS calls (``osbyte``, ``osword``, …) that
        shouldn't seed tracing of unloaded memory — the trace is not
        seeded AND the label is registered as OPTIONAL (so it only
        emits when actually JSR'd to).

        If ``title`` or ``description`` (or ``on_entry`` / ``on_exit``)
        is given, also attaches a banner-style annotation.
        """
        self._raise_if_disassembled("subroutine")
        binary_addr = self._resolve_to_binary_addr(runtime_addr, move)
        move_id = self._move_to_id(move)
        if is_entry_point:
            self._entry_points.append(binary_addr)
        if name is not None:
            self._labels.add_label(
                runtime_addr, name,
                is_optional=not is_entry_point,
                move_id=move_id,
            )
        if title or description or on_entry or on_exit:
            self._annotations.add(
                binary_addr,
                Banner(
                    title=title, description=description,
                    on_entry=on_entry, on_exit=on_exit,
                ),
            )
        self._subroutines.append(SubroutineEntry(
            runtime_addr=int(runtime_addr),
            binary_addr=int(binary_addr),
            move_id=move_id,
            name=name,
            title=title,
            description=description,
            on_entry=dict(on_entry) if on_entry else {},
            on_exit=dict(on_exit) if on_exit else {},
        ))

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
        if self.string_detection_min_length is not None:
            self._classify_string_runs(self.string_detection_min_length)
        self._classify_leftovers()
        # Compute per-instruction CPU state via a linear sweep of
        # the now-classified code. Optional — the CPU plug-in opts
        # in by overriding ``Cpu.initial_state`` / ``update_state``.
        # Done BEFORE reference analysis so post-trace JSR analyzers
        # (e.g. OSBYTE / OSWORD decoders) can register additional
        # constants/expressions that the reference walk will see.
        self._compute_cpu_states()
        self._run_post_trace_jsr_analyzers()
        refs_by_addr = self._compute_references()
        if self.auto_labels_enabled:
            self._generate_auto_labels(refs_by_addr)
            self._synthesise_offset_bases()
        # Now that all labels are known (driver-supplied + auto-
        # generated), resolve the deferred expressions registered
        # earlier (by ``code_ptr`` / ``rts_code_ptr``).
        self._resolve_deferred_expressions()
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
            #
            # Move boundary: an opcode whose byte range straddles a
            # move boundary can't be rendered as a single instruction
            # — its bytes need to land in different runtime-address
            # spaces to satisfy each move's copyblock, and beebasm
            # assembles one instruction's bytes contiguously at one
            # PC. Leave the bytes for the leftover-classify pass to
            # mark individually as ``Byte(1)`` so each lands under
            # the right move at render time.
            #
            # Surface a warning so the driver author knows what the
            # rendered output WILL look like (split equbs rather
            # than the original instruction) — the scenario itself
            # is valid (NFS-3.65's BVC at &9564 straddling moves 3
            # and 4 reflects real ROM behaviour) but the rendering
            # is surprising enough to flag.
            if not self._classifications.is_classified(addr, opcode.length()):
                if self._opcode_straddles_move_boundary(addr, opcode.length()):
                    import warnings
                    warnings.warn(
                        f"opcode at &{addr:04x} ({opcode.default_mnemonic()}, "
                        f"{opcode.length()} bytes) straddles a move "
                        f"boundary; rendering each byte individually as "
                        f"``equb`` since one instruction can't span two "
                        f"runtime spaces.",
                        stacklevel=2,
                    )
                else:
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

    def _opcode_straddles_move_boundary(
        self, addr: int, length: int,
    ) -> bool:
        """True iff a multi-byte opcode at ``[addr, addr+length)``
        crosses any move's source-range start or end.

        Boundaries are at ``src_binary_addr`` and
        ``src_binary_addr + length`` for every registered move
        (excluding the base move). An instruction is "straddling" if
        a boundary falls strictly between its first and last byte.
        Pure-internal helper for :meth:`_trace`.
        """
        if length < 2:
            return False
        end = addr + length
        for mv in self._moves.all_moves[1:]:  # skip base move
            for boundary in (
                int(mv.src_binary_addr),
                int(mv.src_binary_addr) + mv.length,
            ):
                if addr < boundary < end:
                    return True
        return False

    def _classify_string_runs(self, min_length: int) -> None:
        """Promote runs of unclassified printable ASCII bytes to
        ``String`` classifications.

        Walks each loaded range left-to-right. A candidate run is a
        consecutive sequence of bytes that are loaded, unclassified,
        and printable (32–126 inclusive — matches py8dis's
        ``utils.isprint``). A run breaks at any of:

        - the next address that is already classified;
        - the next address that is not loaded;
        - the next address that is non-printable;
        - the next address with a label;
        - a binary address that is the start or end of any move
          (so a single ``String`` cannot straddle a move boundary —
          the asm renderer emits one classification at one runtime
          range);
        - a binary address that has any annotation attached (so
          per-byte comments / banners aren't lost — the renderer
          attaches annotations at the START of each classification
          only).

        If the run's length is at least ``min_length``, classify the
        whole run as :class:`~dasmos.core.classification.String`.
        Otherwise leave the bytes alone — :meth:`_classify_leftovers`
        sweeps them up afterwards into a ``Byte`` run.

        Mirrors py8dis-fork's ``classification.autostring`` but is
        invoked declaratively from :meth:`disassemble` based on
        :attr:`string_detection_min_length` rather than via a
        ``post_trace_steps`` closure on ``go()``.
        """
        if min_length < 2:
            raise DisassemblerError(
                f"string_detection_min_length must be >= 2 (got {min_length}); "
                f"single-character classifications would always trigger"
            )

        move_boundaries: set[int] = set()
        for move in self._moves.moves:
            move_boundaries.add(int(move.src_binary_addr))
            move_boundaries.add(int(move.src_binary_addr) + move.length)

        for start, end in self._memory.load_ranges:
            addr = int(start)
            range_end = int(end)
            while addr < range_end:
                if (
                    not self._memory.is_loaded(addr)
                    or self._classifications.is_classified(addr)
                    or not _is_printable_ascii(self._memory.get_u8(addr))
                ):
                    addr += 1
                    continue
                run_end = addr + 1
                while run_end < range_end:
                    if not self._memory.is_loaded(run_end):
                        break
                    if self._classifications.is_classified(run_end):
                        break
                    if not _is_printable_ascii(self._memory.get_u8(run_end)):
                        break
                    if run_end in move_boundaries:
                        break
                    runtime = self._moves.b2r(BinaryAddr(run_end))
                    if runtime in self._labels:
                        break
                    if BinaryAddr(run_end) in self._annotations:
                        break
                    run_end += 1
                length = run_end - addr
                if length >= min_length:
                    self._classifications.add_classification(
                        addr, String(length),
                    )
                addr = run_end

    def _classify_leftovers(self) -> None:
        """Aggregate every loaded-but-unclassified byte into ``Byte``
        runs.

        Walks each loaded range left-to-right. Consecutive
        unclassified bytes accumulate into a single
        :class:`~dasmos.core.classification.Byte` of the run's length.
        A run ends at any of:

        - the next address that is already classified;
        - the next address that is not loaded;
        - the next address with a label (so the label gets a fresh
          ``Byte`` it can anchor to);
        - the end of the load range.

        Mirrors py8dis-fork's ``classification.classify_leftovers``
        behaviour, so 33 unlabelled ``&FF`` filler bytes between two
        labels render as one ``equb &ff, &ff, …`` row instead of 33
        single-byte rows.
        """
        # Move-boundary set: every binary address at which a move
        # begins or ends. Aggregation breaks at these so a single
        # ``Byte`` classification never straddles a move boundary —
        # the asm renderer emits each classification at one runtime
        # range, and a straddler would write past the destination's
        # end (beebasm's "Trying to assemble over existing code").
        move_boundaries: set[int] = set()
        for move in self._moves.moves:
            move_boundaries.add(int(move.src_binary_addr))
            move_boundaries.add(int(move.src_binary_addr) + move.length)

        for start, end in self._memory.load_ranges:
            addr = int(start)
            range_end = int(end)
            while addr < range_end:
                if (
                    not self._memory.is_loaded(addr)
                    or self._classifications.is_classified(addr)
                ):
                    addr += 1
                    continue
                run_end = addr + 1
                while run_end < range_end:
                    if not self._memory.is_loaded(run_end):
                        break
                    if self._classifications.is_classified(run_end):
                        break
                    if run_end in move_boundaries:
                        break
                    runtime = self._moves.b2r(BinaryAddr(run_end))
                    if runtime in self._labels:
                        break
                    # Break at annotated bytes too. The renderer's
                    # per-classification emission attaches annotations
                    # at the START of each classification — if we
                    # aggregated through an annotated byte, its
                    # comment / banner would never be rendered.
                    if BinaryAddr(run_end) in self._annotations:
                        break
                    run_end += 1
                self._classifications.add_classification(
                    addr, Byte(run_end - addr),
                )
                addr = run_end

    # -- internals: deferred expressions -------------------------------

    def _register_deferred_expression(
        self, binary_addr: int, target_runtime_addr: int, build_text,
    ) -> None:
        """Record a callable that builds the expression text for
        ``binary_addr`` based on the label name at
        ``target_runtime_addr``. Resolved by
        :meth:`_resolve_deferred_expressions` after the trace +
        auto-label pass, so labels registered LATER in the driver
        script (e.g. ``rts_code_ptr`` at line 1769 referencing a
        ``subroutine`` at line 3087) still surface symbolically.

        ``build_text`` is a callable taking the resolved label name
        and returning the final expression text — see callers in
        :meth:`code_ptr` for the typical lambdas
        (``lambda n: f"<({n}-1)"`` etc.).
        """
        self._deferred_expressions.append(
            (int(binary_addr), int(target_runtime_addr), build_text),
        )

    def _resolve_deferred_expressions(self) -> None:
        """Iterate :attr:`_deferred_expressions`, resolve each
        target's label name (now that auto-label generation is done),
        and write the final text to :attr:`_expressions`. Falls back
        to the literal hex address only when no name exists at all
        for the target.
        """
        for binary_addr, target, build_text in self._deferred_expressions:
            label = self._labels.get_label(target)
            if label is not None:
                # Match the JsonRenderer's "first registered name"
                # tie-break (insertion order, NOT alphabetical) so
                # the deferred-expression text agrees with operand
                # rendering at the same target.
                name = None
                for name_list in label.explicit_names.values():
                    for explicit in name_list:
                        name = explicit.text
                        break
                    if name is not None:
                        break
                if name is None:
                    name = f"&{target:04x}"
            else:
                name = f"&{target:04x}"
            self._expressions.add(binary_addr, build_text(name))

    # -- internals: post-trace CPU-state pass ---------------------------

    def _compute_cpu_states(self) -> None:
        """Populate :attr:`_cpu_state_at` by walking classified code
        in binary order, advancing a CPU state through each opcode.

        This is an "optimistic" walk — straight-line, ignoring
        branches; state propagates linearly and resets only on data
        classifications. Despite the imprecision it's good enough for
        OSBYTE-style detection (the LDA #imm and the JSR osbyte are
        usually in the same straight-line block).

        Skipped silently when the CPU plug-in opts out (i.e.
        ``Cpu.initial_state`` returns None).
        """
        from dasmos.cpu import Opcode
        state = self._cpu.initial_state()
        if state is None:
            return
        for start, end in self._memory.load_ranges:
            # Reset state at the start of each loaded range — we
            # have no idea what state arrived from outside.
            state = self._cpu.initial_state()
            addr = int(start)
            while addr < int(end):
                c = self._classifications.get_classification(addr)
                if isinstance(c, Opcode):
                    # Snapshot state BEFORE the instruction so a JSR
                    # analyzer can ask "what was A just before the
                    # JSR?" — i.e. the LDA's effect is visible.
                    self._cpu_state_at[addr] = state.clone()
                    self._cpu.update_state(state, c, addr, self._memory)
                    addr += c.length()
                elif c is None:
                    # Unclassified-but-loaded — bytes that are
                    # neither code nor data. Reset state.
                    state = self._cpu.initial_state()
                    addr += 1
                else:
                    # Data classification (Byte / Word / String /
                    # Fill) — code execution doesn't continue
                    # through it, so reset state.
                    state = self._cpu.initial_state()
                    addr += c.length()

    def _run_post_trace_jsr_analyzers(self) -> None:
        """For each classified JSR whose target has a registered
        post-trace analyzer, call the analyzer with the CPU state
        immediately before the JSR fires.

        Distinct from :attr:`_subroutine_hooks` — those run during
        trace (they may change where the trace continues). This
        runs AFTER trace + state computation, so analyzers can read
        :attr:`_cpu_state_at` to find the previous LDA #imm. This
        is what makes OSBYTE / OSWORD decoders work for ``LDA #imm
        ; STA somewhere ; JSR osbyte`` patterns the simple peek-
        back-1 heuristic misses.
        """
        if not self._post_trace_jsr_analyzers:
            return
        from dasmos.cpu import FlowControl, Opcode
        # Fire on JSR (normal call) AND JMP (tail-call optimization
        # — common idiom is ``lda #X ; jmp osbyte`` instead of
        # ``lda #X ; jsr osbyte ; rts``). Both are control transfers
        # to the OS call so the analyzer should fire on either.
        for binary_addr, classification in self._classifications.iter_classified_starts():
            if not isinstance(classification, Opcode):
                continue
            if classification.flow_control not in (
                FlowControl.SUBROUTINE_CALL, FlowControl.JUMP,
            ):
                continue
            target = classification._compute_target(self._memory, int(binary_addr))
            if target is None:
                continue
            analyzer = self._post_trace_jsr_analyzers.get(int(target))
            if analyzer is None:
                continue
            state = self._cpu_state_at.get(int(binary_addr))
            if state is None:
                continue
            analyzer(self, int(binary_addr), state)

    # -- internals: reference analysis + auto-label generation ----------

    def _compute_references(self) -> dict[int, list[int]]:
        """Walk every classified opcode, resolve operand → target,
        and record use sites against any label at the target.

        Returns ``{target_runtime_addr: [ref_binary_addr, …]}`` for
        the auto-label pass to consume — even targets that don't yet
        have a label appear here.

        Each recorded reference carries the ref's ``move_id`` (the
        move under which the referencing opcode is executing) so
        downstream renderers can present the ref's address in the
        right runtime — e.g. ``&0030[1]`` for a JSR at binary &933E
        running at runtime &30 under move 1.
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
                ref_move_id = self._moves._move_id_for_binary_addr[int(binary_addr)]
                label.add_reference(
                    BinaryLocation(int(binary_addr), int(ref_move_id)),
                )
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
            # Do the branch-target arithmetic in runtime space so a
            # branch whose source byte is inside a moved region
            # resolves to the runtime address (matching where the
            # label was registered against ``with d.using_move(...)``),
            # not the binary source address. Outside any move b2r is
            # the identity, so non-moved code is unaffected.
            from dasmos.core.memory import BinaryAddr
            base_runtime = int(self._moves.b2r(BinaryAddr(binary_addr)))
            return base_runtime + opcode.length() + offset
        return None

    def _generate_auto_labels(
        self, refs_by_addr: dict[int, list[int]],
    ) -> None:
        """For every referenced address with no explicit name,
        synthesise one and register it in the LabelManager with
        ``is_autogenerated=True``. Renderers see them via the standard
        label-resolution paths — no special auto-label code path
        downstream.

        Heuristics (each prefix is set on the Disassembler constructor):

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
            if existing is not None and (
                existing.explicit_name_texts()
                # Also skip if an EXPRESSION is registered (e.g.
                # ``acorn_mos`` registers ``evntv+1`` at &0221 via
                # ``expr_label``). Synthesising ``l0221`` here
                # would compete with the expression and cause the
                # operand to render as ``sta l0221`` instead of
                # ``sta evntv+1``. Suppresses auto-label generation
                # at alias addresses.
                or any(existing.expressions.values())
            ):
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

    # Single-byte RTS opcode on the NMOS 6502 / CMOS 65C02 — used
    # by the return-N auto-label rule. The opcode value is the same
    # on every CPU plug-in we ship; if/when a future CPU diverges
    # this can move onto the Cpu base class.
    _OPCODE_RTS = 0x60

    def _synthesise_auto_label_name(
        self, runtime_addr: int, ref_binary_addrs: list[int],
    ) -> str:
        """Pick a prefix per the auto-label heuristics and return the
        full ``<prefix><addr>`` name. ``ref_binary_addrs`` is
        deduplicated and sorted by the caller.

        The return-N rule fires before any prefix selection: if the
        target address holds a single-byte ``RTS`` opcode and
        ``auto_label_return_prefix`` is set, the label gets a
        sequential ``<return_prefix><N>`` name where ``N`` is
        assigned in discovery order.
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

        # return-N rule: bare RTS at this address gets a numbered
        # name (matches the readability gain py8dis users are used
        # to). Fires regardless of code/data heuristics — an RTS
        # target is always code.
        if (
            self.auto_label_return_prefix is not None
            and binary_addr_loc is not None
            and isinstance(classification, Opcode)
            and self._memory.is_loaded(int(binary_addr_loc))
            and self._memory.get_u8(int(binary_addr_loc)) == self._OPCODE_RTS
        ):
            ba = int(binary_addr_loc)
            if ba not in self._return_label_id_for_addr:
                self._return_label_id_for_addr[ba] = (
                    len(self._return_label_id_for_addr) + 1
                )
            n = self._return_label_id_for_addr[ba]
            return f"{self.auto_label_return_prefix}{n}"

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
        instead of as a literal hex equate.

        Uses ``auto_label_subroutine_prefix`` for the synthesised
        base name regardless of the actual flow control at the base
        address — the ``sub_c`` form is the right shape for an offset
        target whether or not the byte happens to be a JSR target.
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
            # anchored inline — emit it as a literal hex equate
            # instead.
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
