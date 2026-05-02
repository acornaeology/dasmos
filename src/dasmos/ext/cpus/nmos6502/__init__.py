"""NMOS 6502 CPU plug-in for dasmos.

Re-exports the concrete class under the uniform symbol :class:`Cpu`
expected by the ``dasmos.cpu`` Stevedore entry point per the
sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.cpus.nmos6502.cpu import (
    AddressingMode,
    Nmos6502Cpu,
    Nmos6502Cpu as Cpu,  # the uniform symbol the entry point references
    OPCODES,
    Operation,
)

__all__ = [
    "AddressingMode",
    "Cpu",
    "Nmos6502Cpu",
    "OPCODES",
    "Operation",
]
