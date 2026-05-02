"""Smoke tests verifying the package imports and the extension-point
wiring is reachable even with no plug-ins registered.
"""

import dasmos
from dasmos import (
    Assembler,
    AssemblerExtensionError,
    Cpu,
    CpuExtensionError,
    DasmosError,
    Extension,
    assembler_names,
    cpu_names,
)
from dasmos.assembler import ASSEMBLER_NAMESPACE
from dasmos.cpu import CPU_NAMESPACE


def test_version_is_a_string() -> None:
    assert isinstance(dasmos.__version__, str)
    assert dasmos.__version__.count(".") == 2


def test_extension_base_classes_are_distinct() -> None:
    assert issubclass(Cpu, Extension)
    assert issubclass(Assembler, Extension)
    assert Cpu is not Assembler


def test_kind_strings() -> None:
    assert Cpu.kind() == "cpu"
    assert Assembler.kind() == "assembler"


def test_namespaces() -> None:
    assert CPU_NAMESPACE == "dasmos.cpu"
    assert ASSEMBLER_NAMESPACE == "dasmos.assembler"


def test_no_built_in_cpus_yet() -> None:
    # The initial scaffold ships no concrete CPU plug-ins.
    assert cpu_names() == []


def test_no_built_in_assemblers_yet() -> None:
    # The initial scaffold ships no concrete assembler plug-ins.
    assert assembler_names() == []


def test_extension_errors_inherit_from_base() -> None:
    assert issubclass(CpuExtensionError, DasmosError)
    assert issubclass(AssemblerExtensionError, DasmosError)
