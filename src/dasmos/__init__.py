"""dasmos — an extensible tracing disassembler.

The top-level package re-exports the public API. Consumers should import
from :mod:`dasmos` rather than reaching into sub-modules.
"""

__version__ = "1.7.0"

from dasmos.core.annotations import Align, Annotation, AnnotationStore, Banner, Comment
from dasmos.core.format_hint import FormatHint
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
    "Align",
    "Annotation",
    "AnnotationStore",
    "Banner",
    "Comment",
    "Cpu",
    "CpuExtensionError",
    "DasmosError",
    "Disassembler",
    "DisassemblerError",
    "Extension",
    "ExtensionError",
    "FlowControl",
    "FormatHint",
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
