"""dasmos — a pluggable tracing disassembler.

The top-level package re-exports the public API. Consumers should import
from :mod:`dasmos` rather than reaching into sub-modules.
"""

__version__ = "0.1.0"

from dasmos.assembler import (
    Assembler,
    AssemblerExtensionError,
    assembler_names,
    create_assembler,
    describe_assembler,
)
from dasmos.cpu import (
    Cpu,
    CpuExtensionError,
    cpu_names,
    create_cpu,
    describe_cpu,
)
from dasmos.exceptions import DasmosError
from dasmos.extension import Extension, ExtensionError

__all__ = [
    "Assembler",
    "AssemblerExtensionError",
    "Cpu",
    "CpuExtensionError",
    "DasmosError",
    "Extension",
    "ExtensionError",
    "assembler_names",
    "cpu_names",
    "create_assembler",
    "create_cpu",
    "describe_assembler",
    "describe_cpu",
]
