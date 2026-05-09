"""Round-trip tests against the real Acorn 6502 Tube Client ROM.

The Tube Client ROM is a 4 KB physical chip whose upper 2 KB maps at
&F800-&FFFF on the second processor; the lower 2 KB is unused.

The remaining test class ports the unmodified original py8dis
driver, runs it, captures the rendered beebasm source, re-assembles
via beebasm, and asserts byte-identical with the upper 2 KB of the
original ROM. py8dis-parity tests that used to live alongside it
were removed once the migration completed.

Exercises three pieces of infrastructure absent from the Econet Bridge
test: the 65C02 CPU plug-in, the move-aware renderer (the &F859→
&0100 7-byte relocation), and subroutine hooks (the inline-string
idiom via JSR &FE98 / stringhi_hook).
"""

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-6502-tube-client"
ROM_PATH = _FIXTURES / "tube-6502-client-1.10.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_tube_6502_client_110.py"

# 4 KB physical ROM, only the upper 2 KB is mapped.
ROM_PHYSICAL_SIZE = 4096
MAPPED_SIZE = 2048
ROM_LOAD_ADDR = 0xF800
ROM_FULL_MD5 = "8c3b9252ac812c892aa21b9252abf94c"

_PORTER_PATH = Path(__file__).parent.parent / "scripts" / "py8dis2dasmos.py"
_porter_spec = importlib.util.spec_from_file_location(
    "py8dis2dasmos", _PORTER_PATH,
)
_porter = importlib.util.module_from_spec(_porter_spec)
_porter_spec.loader.exec_module(_porter)


def _find_beebasm() -> str | None:
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


_BEEBASM = _find_beebasm()


@pytest.mark.beebasm
class TestTubeClientPorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the upper
    2 KB of the Tube Client ROM, produces beebasm source that
    re-assembles byte-identical with the original mapped bytes.
    """

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        # Pin the upstream ROM (full 4 KB).
        full_rom = ROM_PATH.read_bytes()
        assert hashlib.md5(full_rom).hexdigest() == ROM_FULL_MD5
        assert len(full_rom) == ROM_PHYSICAL_SIZE
        mapped = full_rom[ROM_PHYSICAL_SIZE - MAPPED_SIZE:]

        ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"))
        ported_filepath = tmp_path / "ported_driver.py"
        ported_filepath.write_text(ported_src, encoding="utf-8")

        output_dirpath = tmp_path / "out"
        output_dirpath.mkdir()

        env = os.environ.copy()
        env["FANTASM_ROM"] = str(ROM_PATH)
        env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)

        result = subprocess.run(
            [sys.executable, str(ported_filepath)],
            capture_output=True, text=True, cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0, (
            f"ported driver failed (exit {result.returncode}):\n"
            f"=== stderr ===\n{result.stderr}"
        )

        asm_filepath = output_dirpath / "tube-6502-client-1.10.asm"
        assert asm_filepath.exists(), (
            f"expected rendered asm at {asm_filepath}, "
            f"stderr was:\n{result.stderr}"
        )

        rebuilt_filepath = tmp_path / "rebuilt.bin"
        result = subprocess.run(
            [_BEEBASM, "-i", str(asm_filepath), "-o", str(rebuilt_filepath)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed to assemble ported output:\n"
            f"=== stderr ===\n{result.stderr}"
        )

        rebuilt = rebuilt_filepath.read_bytes()
        assert rebuilt == mapped, (
            f"byte mismatch: {len(rebuilt)} rebuilt vs {len(mapped)} "
            f"original-mapped bytes"
        )
