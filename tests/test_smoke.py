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


def test_cpu_base_is_abstract() -> None:
    # Cpu has at least one abstract method (address_space_size).
    import pytest
    with pytest.raises(TypeError):
        Cpu(name="oops")  # type: ignore[abstract]


def test_kind_strings() -> None:
    assert Cpu.kind() == "cpu"
    assert Renderer.kind() == "renderer"


def test_namespaces() -> None:
    assert CPU_NAMESPACE == "dasmos.cpu"
    assert RENDERER_NAMESPACE == "dasmos.renderer"


def test_nmos6502_cpu_plugin_is_registered() -> None:
    # The first concrete CPU plug-in. Test gets updated as more land.
    assert "6502" in cpu_names()


def test_beebasm_renderer_plugin_is_registered() -> None:
    # The first concrete renderer plug-in. Test gets updated as more land.
    assert "beebasm" in renderer_names()


def test_extension_errors_inherit_from_base() -> None:
    assert issubclass(CpuExtensionError, DasmosError)
    assert issubclass(RendererExtensionError, DasmosError)


def test_format_hint_reexported_from_top_level() -> None:
    # Driver scripts use the natural ``from dasmos import FormatHint``
    # alongside Disassembler / Align — reaching into the sub-module
    # would surprise. Lock the public-package exposure here.
    from dasmos import FormatHint
    # Every hint the driver-API surface advertises (CHAR / DECIMAL /
    # HEX / BINARY / OCTAL / INKEY) must be present.
    for name in ("CHAR", "DECIMAL", "HEX", "BINARY", "OCTAL", "INKEY"):
        assert hasattr(FormatHint, name), name
