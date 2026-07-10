"""Golden-snapshot tests for rendered assembler output.

dasmos's load-bearing correctness check is byte-equality of the
*re-assembled* binary (see the ``@pytest.mark.beebasm`` round-trip
oracles). That is necessary but not sufficient for a renderer refactor:
two different source texts can assemble to identical bytes, so the
byte oracle would not catch an accidental change to the rendered text.

This module pins the *exact rendered text* of every fixture ROM's full
ported driver, so a refactor of the rendering layer that changes the
output — intentionally or not — is caught immediately. Rendering needs
no external assembler, so these tests always run (unlike the round-trip
oracles, which skip without the assembler binary).

To regenerate the goldens after an intentional output change, run::

    UPDATE_GOLDEN=1 uv run pytest tests/test_golden_asm.py

and review the diff before committing.
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures"
_PORTER_PATH = Path(__file__).parent.parent / "scripts" / "py8dis2dasmos.py"

_porter_spec = importlib.util.spec_from_file_location(
    "py8dis2dasmos", _PORTER_PATH,
)
_porter = importlib.util.module_from_spec(_porter_spec)
_porter_spec.loader.exec_module(_porter)


# (fixture subdir, driver filename, rom filename, emitted asm filename).
# One entry per real sibling-repo ROM vendored under tests/fixtures/.
_ROMS = [
    (
        "acorn-6502-tube-client",
        "disasm_tube_6502_client_110.py",
        "tube-6502-client-1.10.rom",
        "tube-6502-client-1.10.asm",
    ),
    (
        "acorn-adfs",
        "disasm_adfs_130.py",
        "adfs-1.30.rom",
        "adfs-1.30.asm",
    ),
    (
        "acorn-anfs-4.18",
        "disasm_anfs_418.py",
        "anfs-4.18.rom",
        "anfs-4.18.asm",
    ),
    (
        "acorn-anfs-4.21",
        "disasm_anfs_421_variant_1.py",
        "anfs-4.21_variant_1.rom",
        "anfs-4.21_variant_1.asm",
    ),
    (
        "acorn-econet-bridge",
        "disasm_econet_bridge_variant_1.py",
        "econet-bridge-variant_1.rom",
        "econet-bridge-variant_1.asm",
    ),
    (
        "acorn-nfs-3.34",
        "disasm_nfs_334.py",
        "nfs-3.34.rom",
        "nfs-3.34.asm",
    ),
    (
        "acorn-nfs",
        "disasm_nfs_365.py",
        "nfs-3.65.rom",
        "nfs-3.65.asm",
    ),
]


def _render_driver_asm(subdir: str, driver: str, rom: str, asm: str,
                       tmp_path: Path) -> str:
    """Port the driver, run it against the fixture ROM, and return the
    rendered beebasm source text (no external assembler involved)."""
    fixture_dirpath = _FIXTURES / subdir
    driver_src = (fixture_dirpath / driver).read_text(encoding="utf-8")
    ported_src = _porter.port(driver_src)

    ported_filepath = tmp_path / "ported_driver.py"
    ported_filepath.write_text(ported_src, encoding="utf-8")

    output_dirpath = tmp_path / "out"
    output_dirpath.mkdir()

    env = os.environ.copy()
    env["FANTASM_ROM"] = str(fixture_dirpath / rom)
    env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)

    result = subprocess.run(
        [sys.executable, str(ported_filepath)],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0, (
        f"ported driver for {subdir} failed (exit {result.returncode}):\n"
        f"=== stderr ===\n{result.stderr}"
    )
    asm_filepath = output_dirpath / asm
    assert asm_filepath.exists(), (
        f"expected rendered asm at {asm_filepath}, "
        f"stderr was:\n{result.stderr}"
    )
    return asm_filepath.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "subdir,driver,rom,asm",
    _ROMS,
    ids=[r[0] for r in _ROMS],
)
def test_rendered_asm_matches_golden(subdir, driver, rom, asm, tmp_path):
    rendered = _render_driver_asm(subdir, driver, rom, asm, tmp_path)
    golden_filepath = _FIXTURES / subdir / f"golden_{asm}"

    if os.environ.get("UPDATE_GOLDEN"):
        golden_filepath.write_text(rendered, encoding="utf-8")
        pytest.skip(f"golden regenerated: {golden_filepath}")

    assert golden_filepath.exists(), (
        f"golden missing: {golden_filepath}. Generate it with "
        f"UPDATE_GOLDEN=1 uv run pytest tests/test_golden_asm.py"
    )
    expected = golden_filepath.read_text(encoding="utf-8")
    assert rendered == expected, (
        f"rendered asm for {subdir} differs from golden "
        f"{golden_filepath.name}. If the change is intentional, "
        f"regenerate with UPDATE_GOLDEN=1 and review the diff."
    )
