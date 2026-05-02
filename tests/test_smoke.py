"""Smoke tests verifying the package imports and the extension-point
wiring is reachable even with no plug-ins registered.
"""

import dasmos
from dasmos import (
    Cpu,
    CpuExtensionError,
    DasmosError,
    Extension,
    Renderer,
    RendererExtensionError,
    cpu_names,
    renderer_names,
)
from dasmos.cpu import CPU_NAMESPACE
from dasmos.renderer import RENDERER_NAMESPACE


def test_version_is_a_string() -> None:
    assert isinstance(dasmos.__version__, str)
    assert dasmos.__version__.count(".") == 2


def test_extension_base_classes_are_distinct() -> None:
    assert issubclass(Cpu, Extension)
    assert issubclass(Renderer, Extension)
    assert Cpu is not Renderer


def test_kind_strings() -> None:
    assert Cpu.kind() == "cpu"
    assert Renderer.kind() == "renderer"


def test_namespaces() -> None:
    assert CPU_NAMESPACE == "dasmos.cpu"
    assert RENDERER_NAMESPACE == "dasmos.renderer"


def test_no_built_in_cpus_yet() -> None:
    # The initial scaffold ships no concrete CPU plug-ins.
    assert cpu_names() == []


def test_no_built_in_renderers_yet() -> None:
    # The initial scaffold ships no concrete renderer plug-ins.
    assert renderer_names() == []


def test_extension_errors_inherit_from_base() -> None:
    assert issubclass(CpuExtensionError, DasmosError)
    assert issubclass(RendererExtensionError, DasmosError)
