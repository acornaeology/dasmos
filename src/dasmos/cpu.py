"""CPU (processor) extension point and the abstract opcode shape.

Each CPU plug-in is a subclass of :class:`Cpu` registered under the
``dasmos.cpu`` entry-point namespace. Concrete CPUs supply the
instruction set, addressing modes, and the per-instruction tracing
behaviour the disassembly core needs to follow control flow.

The initial target set is NMOS 6502, CMOS 65C02 and MC6809, with
ambitions to grow into the wider Acorn lineage (Z80, 80186, 32016,
ARM1/2/3/610/710).

Per ``docs/design/decisions.md`` D-006, the Cpu plug-in is **pure
data + small queries** — it does not own the trace loop. The abstract
methods declared here are the minimum the orchestrator
(:class:`~dasmos.disassembler.Disassembler`) needs.

The :class:`Opcode` shape is **renderer-agnostic by design** (per
the conclusion of the stardot.org.uk design discussion linked in
``docs/design/decisions.md`` D-021): an opcode in the IR carries
``operation`` and ``addressing_mode`` enum members from the
plug-in's own enums plus a CPU-agnostic :class:`FlowControl` for
the trace engine, but does **not** commit to a final mnemonic.
That choice belongs to the renderer — different assemblers spell
the same opcode differently (``LDA #imm`` in Beebasm vs ``LDAIM``
in Acorn MASM; ``JMP (...)`` vs ``JMI``).
"""

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Type, runtime_checkable

from dasmos.core.classification import Classification
from dasmos.core.memory import ReferenceKind
from dasmos.extension import (
    Extension,
    ExtensionError,
    create_extension,
    describe_extension,
    extension,
    list_extensions,
)

KIND = "cpu"
CPU_NAMESPACE = f"dasmos.{KIND}"


class FlowControl(Enum):
    """How an opcode affects the trace engine's notion of control flow.

    CPU-agnostic — the trace loop dispatches on this enum to decide
    where to follow next.
    """

    SEQUENTIAL = "sequential"
    """Falls through to the next instruction. Most opcodes."""

    JUMP = "jump"
    """Unconditional control transfer; no fall-through. e.g. JMP."""

    SUBROUTINE_CALL = "subroutine_call"
    """Calls a subroutine; control eventually returns to the next
    instruction. e.g. JSR. Both target and fall-through are reachable.
    """

    CONDITIONAL_BRANCH = "conditional_branch"
    """Conditionally transfers control; both target and fall-through
    are reachable. e.g. BNE / BEQ.
    """

    RETURN = "return"
    """Terminates the current trace path. e.g. RTS / RTI."""

    BREAK = "break"
    """Software interrupt or trap. Treated conservatively as a path
    terminator unless the plug-in says otherwise.
    """

    UNDEFINED = "undefined"
    """Undocumented or invalid opcode. Trace terminates here."""


class OperandKind(Enum):
    """The semantics of the byte(s) following the opcode byte.

    Used by the trace engine and by renderers to decode and present
    the operand correctly. CPU-agnostic for now; may grow as exotic
    addressing modes appear.
    """

    NONE = "none"
    """No operand bytes (implied / accumulator)."""

    IMMEDIATE = "immediate"
    """A literal value (e.g. ``LDA #$3`` — the operand is the value)."""

    ADDRESS_8 = "address_8"
    """An 8-bit address (zero-page)."""

    ADDRESS_16 = "address_16"
    """A 16-bit address (absolute)."""

    ADDRESS_16_INDIRECT = "address_16_indirect"
    """A 16-bit address that is itself a *pointer* — the actual target
    is found by reading two bytes at that address. Used by the 6502's
    ``JMP (addr)`` and the 65C02's ``JMP (addr,X)``.
    """

    RELATIVE_OFFSET = "relative_offset"
    """A signed 8-bit offset added to the program counter at the
    next instruction (branches).
    """


@runtime_checkable
class AddressingModeMember(Protocol):
    """Protocol every CPU's :class:`~enum.Enum` ``AddressingMode``
    member must satisfy.

    Each member exposes the byte length of the operand (so the trace
    engine can advance the program counter), the kind of the operand
    (so the trace engine and renderers know how to decode it), and the
    :class:`~dasmos.core.memory.ReferenceKind` (so use-site tracking
    knows whether the operand names the accessed address directly or
    merely an indexing base).
    """

    name: str
    operand_length: int
    operand_kind: OperandKind
    reference_kind: ReferenceKind


@dataclass(frozen=True)
class Opcode(Classification):
    """An entry in a CPU's instruction table — and itself a
    :class:`~dasmos.core.classification.Classification` so it can be
    stored in the :class:`~dasmos.core.disassembly.ClassificationStore`
    alongside :class:`~dasmos.core.classification.Byte`,
    :class:`~dasmos.core.classification.Word`, etc.

    Renderer-agnostic: carries the abstract ``operation`` and
    ``addressing_mode`` enum members plus a CPU-agnostic
    :class:`FlowControl`. Renderers translate
    ``(operation, addressing_mode)`` to their preferred mnemonic
    spelling — typically via a per-pair lookup table that falls
    back to :meth:`default_mnemonic`.

    Frozen and hashable: a single ``Opcode`` instance is shared
    across every binary address that uses this opcode byte.
    """

    operation: Enum
    addressing_mode: AddressingModeMember
    flow_control: FlowControl
    cycles: int = 0

    @property
    def operand_length(self) -> int:
        """Bytes consumed by the operand (delegates to the addressing
        mode).
        """
        return self.addressing_mode.operand_length

    def length(self) -> int:
        """Total bytes consumed by this instruction (opcode byte +
        operand bytes). Method form for parity with the other
        :class:`Classification` subclasses.
        """
        return 1 + self.operand_length

    def is_code(self, binary_addr=None) -> bool:
        """Opcodes always represent code."""
        return True

    def default_mnemonic(self) -> str:
        """Canonical mnemonic for this operation, used by ``__repr__``
        and as the fallback for renderers without a specific override
        for this ``(operation, addressing_mode)`` pair.

        Returns the operation enum member's ``value`` if it's a
        string; otherwise its ``name``. Plug-in authors should give
        their ``Operation`` enum members string values (the canonical
        lowercase MOS form for 6502: ``"lda"``, ``"jsr"``, …).
        """
        v = self.operation.value
        return v if isinstance(v, str) else self.operation.name

    def __repr__(self) -> str:
        return (
            f"Opcode({self.operation.name}, "
            f"{self.addressing_mode.name}, "
            f"{self.flow_control.name})"
        )

    def next_addresses(self, memory, binary_addr: int) -> list[int]:
        """Compute the next binary addresses to trace from this opcode
        located at ``binary_addr``.

        Returns one or two addresses according to flow control:

        - ``SEQUENTIAL`` → ``[fall_through]``.
        - ``JUMP`` → ``[target]`` if the target is computable;
          otherwise ``[]``.
        - ``SUBROUTINE_CALL`` → ``[fall_through, target]`` (target
          omitted if not computable; ``fall_through`` is where
          execution returns to after the called routine).
        - ``CONDITIONAL_BRANCH`` → ``[fall_through, target]``
          (target omitted if not computable).
        - ``RETURN`` / ``BREAK`` / ``UNDEFINED`` → ``[]`` (control
          terminates here).

        Targets that depend on memory the engine can't read
        (e.g. ``JMP (addr)`` where the pointer's bytes aren't
        loaded) are silently dropped — the trace path narrows but
        doesn't fail.

        ``memory`` is the :class:`~dasmos.core.memory.MemoryImage`;
        ``binary_addr`` is the binary address of the opcode byte
        (an ``int`` for ergonomics, internally interpreted as a
        :class:`~dasmos.core.memory.BinaryAddr`).
        """
        fall_through = binary_addr + self.length()

        flow = self.flow_control
        if flow is FlowControl.SEQUENTIAL:
            return [fall_through]
        if flow in (FlowControl.RETURN, FlowControl.BREAK, FlowControl.UNDEFINED):
            return []
        # All remaining flow kinds need the operand interpreted as a
        # control-flow target.
        target = self._compute_target(memory, binary_addr)
        if flow is FlowControl.JUMP:
            return [target] if target is not None else []
        # SUBROUTINE_CALL and CONDITIONAL_BRANCH both fall through.
        if target is not None:
            return [fall_through, target]
        return [fall_through]

    def _compute_target(self, memory, binary_addr: int) -> int | None:
        """Decode the operand into a control-flow target address.

        Returns ``None`` if the addressing mode doesn't yield a
        target (e.g. immediate operands on a misuse) or the bytes
        aren't loaded.
        """
        operand_addr = binary_addr + 1
        kind = self.addressing_mode.operand_kind

        if kind is OperandKind.RELATIVE_OFFSET:
            if not memory.is_loaded(operand_addr):
                return None
            offset = memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100  # two's-complement signed
            return binary_addr + self.length() + offset

        if kind is OperandKind.ADDRESS_16:
            if not memory.is_loaded(operand_addr, 2):
                return None
            return memory.get_u16_le(operand_addr)

        if kind is OperandKind.ADDRESS_8:
            if not memory.is_loaded(operand_addr):
                return None
            return memory.get_u8(operand_addr)

        if kind is OperandKind.ADDRESS_16_INDIRECT:
            # Operand is a pointer to the target.
            if not memory.is_loaded(operand_addr, 2):
                return None
            ptr = memory.get_u16_le(operand_addr)
            if not memory.is_loaded(ptr, 2):
                return None
            return memory.get_u16_le(ptr)

        # OperandKind.NONE / IMMEDIATE: no target to follow.
        return None

    def _compute_target_runtime(
        self, memory, binary_addr: int, b2r,
    ) -> int | None:
        """Decode the operand into a control-flow target as a RUNTIME
        address.

        Mirrors :meth:`_compute_target` for ABS-mode opcodes (whose
        operand bytes already encode a runtime address by the 6502's
        usual convention) but does branch-target arithmetic in
        runtime space: ``b2r(binary_addr) + length + offset``. A
        relative branch whose source byte sits inside a moved region
        produces a target in the move's destination runtime space —
        matching the runtime addresses where labels were registered
        — instead of a binary address that's only meaningful when
        runtime equals binary.

        Mirrors py8dis-fork's runtime-aware tracer (see
        ``py8dis/cpu6502.py:807-899`` for branches and JSR/JMP).

        ``b2r`` is the binary→runtime conversion function (typically
        ``MoveManager.b2r``). For non-moved code the conversion is
        identity, so callers that don't care about move-aware
        arithmetic can pass ``lambda x: x``; callers that want the
        full move-aware semantics pass ``moves.b2r``.

        Returns None when operand bytes aren't loaded or the
        addressing mode doesn't yield a target.
        """
        operand_addr = binary_addr + 1
        kind = self.addressing_mode.operand_kind

        if kind is OperandKind.RELATIVE_OFFSET:
            if not memory.is_loaded(operand_addr):
                return None
            offset = memory.get_u8(operand_addr)
            if offset >= 0x80:
                offset -= 0x100
            return int(b2r(binary_addr)) + self.length() + offset

        # ABS / ZP modes — operand bytes ARE the (runtime) target
        # address. Same as the legacy method.
        if kind is OperandKind.ADDRESS_16:
            if not memory.is_loaded(operand_addr, 2):
                return None
            return memory.get_u16_le(operand_addr)

        if kind is OperandKind.ADDRESS_8:
            if not memory.is_loaded(operand_addr):
                return None
            return memory.get_u8(operand_addr)

        if kind is OperandKind.ADDRESS_16_INDIRECT:
            # py8dis's OpcodeJmpInd.disassemble doesn't auto-trace
            # indirect JMPs at all. Match that conservatively: we
            # follow only when the operand-as-binary is loaded
            # (works for non-moved code, the common case); when the
            # pointer storage is in moved space we drop the trace
            # path. A future refactor could plumb r2b through here
            # to follow more cases.
            if not memory.is_loaded(operand_addr, 2):
                return None
            ptr = memory.get_u16_le(operand_addr)
            if not memory.is_loaded(ptr, 2):
                return None
            return memory.get_u16_le(ptr)

        return None


class Cpu(Extension):
    """Base class for CPU (processor) plug-ins.

    Concrete subclasses model a specific processor — its instruction
    encoding, addressing modes, register set, and the semantics the
    tracing disassembler needs to follow control flow.
    """

    @classmethod
    def _kind(cls) -> str:
        return KIND

    @property
    @abstractmethod
    def address_space_size(self) -> int:
        """The number of distinct addressable bytes for this CPU.

        ``0x10000`` for 16-bit address spaces (6502, 6809, Z80);
        larger for 32-bit CPUs to come (ARM, 32016). The orchestrator
        uses this when sizing its :class:`~dasmos.core.memory.MemoryImage`
        and :class:`~dasmos.core.move.MoveManager`.
        """

    @abstractmethod
    def opcodes(self) -> dict[int, Opcode]:
        """The CPU's instruction table.

        Maps opcode byte (``0x00``–``0xFF``) to an :class:`Opcode`.
        Bytes not in the dict are treated as undefined by the trace
        engine — for the NMOS 6502 plug-in the undocumented opcodes
        are deliberately omitted.
        """

    # -- optional CPU-state tracking ------------------------------------
    #
    # Plug-ins that override these enable post-trace register-state
    # analysis (used by JSR-state hooks like the OSBYTE / OSWORD
    # decoders). Default implementations return ``None`` so analyzers
    # that depend on state are skipped silently for CPUs without it.

    def initial_state(self):  # type: () -> "CpuState | None"
        """Return a fresh :class:`~dasmos.core.cpu_state.CpuState` for
        this CPU, or ``None`` to opt out of state tracking.

        The Disassembler calls this once at the start of its post-
        trace state-computation pass. Override in CPU plug-ins that
        want their state tracked.
        """
        return None

    def update_state(self, state, opcode: Opcode, addr: int, memory) -> None:
        """Advance ``state`` to reflect executing ``opcode`` at the
        binary address ``addr``. Mutates ``state`` in place.

        ``memory`` is the disassembler's :class:`MemoryImage` so the
        update can read the operand byte(s) when relevant (e.g.
        ``LDA #imm`` reads the immediate from ``addr + 1``).

        No-op default — CPU plug-ins override.
        """


class CpuExtensionError(ExtensionError):
    """Exception raised when a CPU extension cannot be loaded."""
    pass


def create_cpu(cpu_name: str, **kwargs) -> Cpu:
    """Create a CPU instance by name.

    Args:
        cpu_name: The name of the CPU to create (e.g. ``"6502"``, ``"65c02"``).
        **kwargs: Forwarded to the CPU subclass constructor.

    Returns:
        A :class:`Cpu` instance.

    Raises:
        CpuExtensionError: If the CPU cannot be loaded.
    """
    return create_extension(
        kind=KIND,
        namespace=CPU_NAMESPACE,
        name=cpu_name,
        exception_type=CpuExtensionError,
        **kwargs,
    )


def describe_cpu(cpu_name: str, *, single_line: bool = False) -> str:
    """Get the description of a CPU plug-in."""
    return describe_extension(
        kind=KIND,
        namespace=CPU_NAMESPACE,
        name=cpu_name,
        exception_type=CpuExtensionError,
        single_line=single_line,
    )


def cpu_names() -> list[str]:
    """Get the names of all available CPU plug-ins."""
    return list_extensions(CPU_NAMESPACE)


def cpu_type(cpu_name: str) -> Type[Cpu]:
    """Obtain the type of a CPU plug-in by name."""
    return extension(
        kind=KIND,
        namespace=CPU_NAMESPACE,
        name=cpu_name,
        exception_type=CpuExtensionError,
    )
