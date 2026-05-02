"""CMOS 65C02 CPU plug-in for dasmos.

Re-exports the concrete class under the uniform symbol :class:`Cpu`
expected by the ``dasmos.cpu`` Stevedore entry point per the
sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.cpus.cmos65c02.cpu import (
    AddressingMode,
    Cmos65C02Cpu,
    Cmos65C02Cpu as Cpu,  # the uniform symbol the entry point references
    OPCODES,
    Operation,
)

__all__ = [
    "AddressingMode",
    "Cmos65C02Cpu",
    "Cpu",
    "OPCODES",
    "Operation",
]
