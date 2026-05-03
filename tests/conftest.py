"""Shared test helpers.

Locates the ``beebasm`` binary for round-trip tests; provides fixtures
that wrap the common assemble / disassemble / re-assemble dance.

Helpers are made available as pytest fixtures so test modules can opt
in by parameter name (no shared module-level state).
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer


def _find_beebasm() -> str | None:
    """Locate the ``beebasm`` binary, honouring the ``BEEBASM`` env
    var first (CI uses it), then ``PATH``, then a fallback path
    on the user's machine.
    """
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    found = shutil.which("beebasm")
    if found:
        return found
    fallback = "/Users/rjs/Code/beebasm/beebasm"
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return None


BEEBASM = _find_beebasm()


def pytest_configure(config):
    """Register the ``beebasm`` marker so tests can opt in via
    ``@pytest.mark.beebasm`` and have the runner auto-skip them when
    the binary isn't available.
    """
    config.addinivalue_line(
        "markers",
        "beebasm: requires the beebasm binary "
        "(set BEEBASM env var or put it in PATH)",
    )
    config.addinivalue_line(
        "markers",
        "py8dis_parity: asserts content fidelity against the legacy "
        "py8dis-fork reference output; deselect with "
        "`-m 'not py8dis_parity'` once dasmos is intentionally allowed "
        "to diverge.",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip ``@pytest.mark.beebasm`` tests when no beebasm binary
    is found.
    """
    if BEEBASM is not None:
        return
    skip = pytest.mark.skip(reason="beebasm binary not found")
    for item in items:
        if "beebasm" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def assemble_beebasm(tmp_path: Path):
    """Return a function that assembles beebasm source text to binary
    bytes.

    Usage:

    .. code-block:: python

        @pytest.mark.beebasm
        def test_thing(assemble_beebasm):
            binary = assemble_beebasm('''
                org &8000
                .start
                    lda #&42
                    rts
                save "out.bin", start, P%
            ''')
    """
    # Belt-and-braces: the @pytest.mark.beebasm marker triggers the
    # auto-skip in pytest_collection_modifyitems when beebasm isn't
    # available, but a test that uses this fixture without the marker
    # would otherwise pass None to subprocess.run and get a confusing
    # TypeError. Skip explicitly so the failure mode is clear.
    if BEEBASM is None:
        pytest.skip(
            "beebasm binary not found; mark the test with "
            "@pytest.mark.beebasm to opt into the auto-skip"
        )

    def _assemble(source: str, *, name: str = "in") -> bytes:
        asm = tmp_path / f"{name}.asm"
        asm.write_text(source)
        result = subprocess.run(
            [BEEBASM, "-i", str(asm)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        if result.returncode != 0:
            raise AssertionError(
                f"beebasm failed to assemble source:\n"
                f"=== source ===\n{source}\n"
                f"=== stderr ===\n{result.stderr}"
            )
        # Find the file the source asked beebasm to save. Beebasm
        # creates files relative to the source's directory.
        # We expect the source to have one ``save "name.bin", ...``
        # directive or to use the default output (which we don't set).
        for candidate in tmp_path.glob("*.bin"):
            if candidate.name != f"{name}.bin" and not candidate.name.startswith("step"):
                # Prefer files that aren't named after the input.
                return candidate.read_bytes()
        # Fall back: use the .bin matching the asm name.
        explicit = tmp_path / f"{name}.bin"
        if explicit.exists():
            return explicit.read_bytes()
        # Last resort — return the only .bin found.
        bins = list(tmp_path.glob("*.bin"))
        if len(bins) == 1:
            return bins[0].read_bytes()
        raise AssertionError(
            f"could not locate beebasm output. Files in {tmp_path}: "
            f"{list(tmp_path.iterdir())}"
        )
    return _assemble


@pytest.fixture
def disassemble_and_render(tmp_path: Path):
    """Return a function that disassembles binary bytes and renders
    via the Beebasm renderer, returning ``(text, ir)``.

    The caller passes a ``configure`` callable that runs against the
    Disassembler before ``disassemble()`` is called — this is where
    the driver-script API features under test get exercised.

    Usage:

    .. code-block:: python

        def test_thing(disassemble_and_render):
            text, ir = disassemble_and_render(
                binary=b"\\xa9\\x42\\x60",
                load_addr=0x8000,
                configure=lambda d: d.entry(0x8000, name="start"),
            )
    """
    def _disassemble(binary: bytes, load_addr: int, configure: Callable):
        bin_in = tmp_path / "input.bin"
        bin_in.write_bytes(binary)
        d = Disassembler.create(cpu="nmos6502")
        d.load(bin_in, load_addr)
        configure(d)
        ir = d.disassemble()
        renderer = BeebasmRenderer()
        text = str(ir.render(renderer))
        return text, ir
    return _disassemble


@pytest.fixture
def roundtrip_via_beebasm(tmp_path: Path):
    """Return a function performing the full round-trip:

    source → beebasm → binary → dasmos → renderer → beebasm → binary'

    Asserts that ``binary' == binary``. Returns the rendered dasmos
    text so the test can additionally assert on text properties
    (e.g. "label name X appears in operand").

    Usage:

    .. code-block:: python

        def test_thing(roundtrip_via_beebasm):
            text = roundtrip_via_beebasm(
                source='''
                    org &8000
                    .start
                        lda #&42
                        rts
                    save "out.bin", start, P%
                ''',
                load_addr=0x8000,
                configure=lambda d: d.entry(0x8000, name="start"),
            )
            assert ".start" in text
    """
    if BEEBASM is None:
        pytest.skip(
            "beebasm binary not found; mark the test with "
            "@pytest.mark.beebasm to opt into the auto-skip"
        )

    def _roundtrip(source: str, load_addr: int, configure: Callable) -> str:
        # Step 1: assemble the known source via beebasm.
        asm_in = tmp_path / "step1_in.asm"
        asm_in.write_text(source)
        result = subprocess.run(
            [BEEBASM, "-i", str(asm_in)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        if result.returncode != 0:
            raise AssertionError(
                f"beebasm failed to assemble the source:\n"
                f"=== source ===\n{source}\n"
                f"=== stderr ===\n{result.stderr}"
            )
        # Find the produced binary — the source's `save` directive
        # writes to a file named in the source. Convention for these
        # tests: name it ``step1.bin``.
        original = (tmp_path / "step1.bin").read_bytes()

        # Step 2: disassemble + render via dasmos.
        bin_in = tmp_path / "step2_input.bin"
        bin_in.write_bytes(original)
        d = Disassembler.create(cpu="nmos6502")
        d.load(bin_in, load_addr)
        configure(d)
        ir = d.disassemble()
        renderer = BeebasmRenderer()
        renderer.set_output_filename("step3.bin")
        text = str(ir.render(renderer))

        # Step 3: re-assemble the dasmos output via beebasm.
        asm_out = tmp_path / "step3.asm"
        asm_out.write_text(text)
        result = subprocess.run(
            [BEEBASM, "-i", str(asm_out)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        if result.returncode != 0:
            raise AssertionError(
                f"beebasm failed to re-assemble dasmos output:\n"
                f"=== dasmos source ===\n{text}\n"
                f"=== stderr ===\n{result.stderr}"
            )
        rebuilt = (tmp_path / "step3.bin").read_bytes()

        # Step 4: byte-equality is the load-bearing assertion.
        assert rebuilt == original, (
            f"round-trip binary mismatch ({len(rebuilt)} vs {len(original)} bytes):\n"
            f"=== original (hex) ===\n{original.hex()}\n"
            f"=== rebuilt (hex)  ===\n{rebuilt.hex()}\n"
            f"=== dasmos text ===\n{text}"
        )
        return text
    return _roundtrip
