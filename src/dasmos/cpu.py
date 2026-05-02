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
    """A 16-bit address (absolute, indirect, etc.)."""

    RELATIVE_OFFSET = "relative_offset"
    """A signed 8-bit offset added to the program counter at the
    next instruction (branches).
    """


@runtime_checkable
class AddressingModeMember(Protocol):
    """Protocol every CPU's :class:`~enum.Enum` ``AddressingMode``
    member must satisfy.

    Each member exposes the byte length of the operand (so the trace
    engine can advance the program counter) and the kind of the
    operand (so the trace engine and renderers know how to decode it).
    """

    name: str
    operand_length: int
    operand_kind: OperandKind


@dataclass(frozen=True)
class Opcode:
    """An entry in a CPU's instruction table.

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

    @property
    def length(self) -> int:
        """Total bytes consumed by this instruction (opcode byte +
        operand bytes).
        """
        return 1 + self.operand_length

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
        are deliberately omitted, matching py8dis.
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
