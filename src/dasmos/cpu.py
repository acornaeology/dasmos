"""CPU (processor) extension point.

Each CPU plug-in is a subclass of :class:`Cpu` registered under the
``dasmos.cpu`` entry-point namespace. Concrete CPUs supply the
instruction set, addressing modes, and the per-instruction tracing
behaviour the disassembly core needs to follow control flow.

The initial target set is NMOS 6502, CMOS 65C02 and MC6809, with
ambitions to grow into the wider Acorn lineage (Z80, 80186, 32016,
ARM1/2/3/610/710).

Per ``docs/design/decisions.md`` D-006, the Cpu plug-in is **pure
data + small queries** — it does not own the trace loop. The
abstract methods declared here are the minimum the orchestrator
(:class:`~dasmos.disassembler.Disassembler`) needs to wire the model
together; the richer protocol (opcode tables, addressing modes,
per-instruction trace semantics, CpuState) lands when the first
concrete plug-in (NMOS 6502) is ported.
"""

from abc import abstractmethod
from typing import Type

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
    """Get the description of a CPU plug-in.

    Args:
        cpu_name: The name of the CPU.
        single_line: If True, return only the first non-empty line of the description.

    Returns:
        Description string from the CPU class's docstring.

    Raises:
        CpuExtensionError: If the CPU cannot be loaded.
    """
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
    """Obtain the type of a CPU plug-in by name.

    Args:
        cpu_name: The name of a CPU. Available names can be obtained from
            :py:func:`~cpu_names`.

    Returns:
        The class of the requested CPU.

    Raises:
        CpuExtensionError: If the requested CPU could not be found.
    """
    return extension(
        kind=KIND,
        namespace=CPU_NAMESPACE,
        name=cpu_name,
        exception_type=CpuExtensionError,
    )
