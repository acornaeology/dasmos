"""Round-trip tests against the real Acorn ANFS 4.18 ROM.

ANFS 4.18 is a **BBC Model B** Acorn Network Filing System
variant (the 4.21 successor is Master-only — different machine
class, not just a later version). 16 KB sideways ROM mapped at
&8000-&BFFF, 13,990-line py8dis driver. Same Model-B feature
set as the older 4.08.53; together they exercise dasmos against
the Model-B ANFS code paths distinct from the Master-only 4.21.

The remaining test class ports the unmodified original py8dis
driver via ``scripts/py8dis2dasmos.py``, runs it, and asserts the
beebasm-reassembled output is byte-identical with the original
ROM. py8dis-parity tests that used to live alongside it were
removed once the migration completed.
"""

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-anfs-4.18"
ROM_PATH = _FIXTURES / "anfs-4.18.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_anfs_418.py"

ROM_SIZE = 16384
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "0926bcb6f47458f8c4aed5364ff1122d"

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
class TestAnfs418PorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the
    ANFS 4.18 ROM, produces beebasm source that re-assembles
    byte-identical with the original ROM.
    """

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        rom = ROM_PATH.read_bytes()
        assert hashlib.md5(rom).hexdigest() == ROM_MD5
        assert len(rom) == ROM_SIZE

        # ANFS is a pure network filing system — it doesn't touch
        # the floppy disc controller, so no FDC env is opted in.
        # (DFS / ADFS / DNFS ROMs would, depending on which chip
        # they target.)
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

        asm_filepath = output_dirpath / "anfs-4.18.asm"
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
        assert rebuilt == rom, (
            f"byte mismatch: {len(rebuilt)} rebuilt vs {len(rom)} "
            f"original bytes"
        )


