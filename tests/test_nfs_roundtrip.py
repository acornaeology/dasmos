"""Round-trip tests against the real Acorn NFS 3.65 ROM.

The NFS (Network Filing System) ROM is the canonical Acorn Econet
file-server client; 8 KB sideways ROM mapped at &8000-&9FFF on a
BBC Micro / Master.

The remaining test class (:class:`TestNfsPorterEndToEnd`) ports
the unmodified original py8dis driver, runs it, captures the
rendered beebasm source, re-assembles via beebasm, and asserts
byte-identical with the original ROM. py8dis-parity tests that
used to live alongside it (vocabulary-coverage diff, JSON schema
diffs and ratchets, fixture md5 pins) were removed once the
migration completed and py8dis stopped being authoritative.

Exercises a beebasm-pass-mismatch scenario the smaller fixtures
don't: NFS registers four ``move()`` declarations (one ZP, three
page-aligned), and several of them overlap. The renderer's
moves-first emission ordering is what makes the inline anchors for
ZP labels precede their use sites.
"""

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-nfs"
ROM_PATH = _FIXTURES / "nfs-3.65.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_nfs_365.py"

ROM_SIZE = 8192
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "1e150e6bd53d22c15eb05302b6e5f167"

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
class TestNfsPorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the NFS
    3.65 ROM, produces beebasm source that re-assembles byte-
    identical with the original ROM.
    """

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        rom = ROM_PATH.read_bytes()
        assert hashlib.md5(rom).hexdigest() == ROM_MD5
        assert len(rom) == ROM_SIZE

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

        asm_filepath = output_dirpath / "nfs-3.65.asm"
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
