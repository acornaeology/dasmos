"""dasmos — a pluggable tracing disassembler.

The top-level package re-exports the public API. Consumers should import
from :mod:`dasmos` rather than reaching into sub-modules.
"""

__version__ = "0.1.0"

from dasmos.cpu import (
    Cpu,
    CpuExtensionError,
    FlowControl,
    Opcode,
    OperandKind,
    cpu_names,
    create_cpu,
    describe_cpu,
)
from dasmos.disassembler import Disassembler, DisassemblerError
from dasmos.exceptions import DasmosError
from dasmos.extension import Extension, ExtensionError
from dasmos.ir import IntermediateRepresentation
from dasmos.output import Output, StructuredOutput, TextOutput
from dasmos.renderer import (
    Renderer,
    RendererExtensionError,
    StructuredRenderer,
    TextRenderer,
    create_renderer,
    describe_renderer,
    renderer_names,
)

__all__ = [
    "Cpu",
    "CpuExtensionError",
    "DasmosError",
    "Disassembler",
    "DisassemblerError",
    "Extension",
    "ExtensionError",
    "FlowControl",
    "IntermediateRepresentation",
    "Opcode",
    "OperandKind",
    "Output",
    "Renderer",
    "RendererExtensionError",
    "StructuredOutput",
    "StructuredRenderer",
    "TextOutput",
    "TextRenderer",
    "cpu_names",
    "create_cpu",
    "create_renderer",
    "describe_cpu",
    "describe_renderer",
    "renderer_names",
]
