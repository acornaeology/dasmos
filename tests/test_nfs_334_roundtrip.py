"""Round-trip tests against the real Acorn NFS 3.34 ROM.

NFS 3.34 is the earliest NFS variant in the acornaeology library —
8 KB sideways ROM mapped at &8000-&9FFF. Predates the 3.65 variant
we already vendor and exercises pre-3.65 driver patterns: a smaller
feature set, simpler MOS-call usage, and slightly different
state-machine layout.

The remaining test class ports the unmodified original py8dis
driver, runs it, asserts byte-identical reassembly, AND pins the
literal text of four overlapping-move sites that historically
rendered as ``equb`` bytes (a regression test for two distinct
tracer fixes — see ``test_overlapping_move_sites_classify_as_
instructions``). py8dis-parity tests that used to live alongside
were removed once the migration completed.
"""

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-nfs-3.34"
ROM_PATH = _FIXTURES / "nfs-3.34.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_nfs_334.py"

ROM_SIZE = 8192
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "d6761cb566cd87b0c1117b5b600cff16"

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
class TestNfs334PorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the NFS
    3.34 ROM, produces beebasm source that re-assembles
    byte-identical with the original ROM.
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

        asm_filepath = output_dirpath / "nfs-3.34.asm"
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


def _run_dasmos_driver(tmp_path) -> Path:
    """Port the NFS 3.34 driver via py8dis2dasmos, run it, return
    the output dir. Used by the overlapping-move regression test
    in :class:`TestNfs334PorterEndToEnd` to inspect the rendered
    asm independently of the byte-roundtrip pipeline.
    """
    ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"))
    ported_filepath = tmp_path / "ported_driver.py"
    ported_filepath.write_text(ported_src, encoding="utf-8")
    output_dirpath = tmp_path / "out_text"
    output_dirpath.mkdir()
    env = os.environ.copy()
    env["FANTASM_ROM"] = str(ROM_PATH)
    env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)
    result = subprocess.run(
        [sys.executable, str(ported_filepath)],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0, (
        f"ported driver failed:\n=== stderr ===\n{result.stderr}"
    )
    return output_dirpath


# Regression test for two distinct tracer fixes (overlapping-move
# straddle / runtime-aware target computation). Lives outside the
# class so the existing porter test stays focused on byte-identity;
# this test inspects rendered asm text instead.
@pytest.mark.beebasm
def test_overlapping_move_sites_classify_as_instructions(tmp_path):
    """The four NFS-3.34 sites historically rendered as ``equb``
    bytes (Bug A: declared-geometry straddle false-positive at
    &9367; Bug B: runtime-vs-binary tracer confusion at the
    moved-subroutine bytes &9508/&950c/&962a). After the
    effective-ownership straddle check + runtime-aware target
    computation, all four classify as proper instructions.

    Pinning these literal forms guards against regression of
    either fix — the round-trip oracle alone wouldn't catch
    a backslide because ``equb`` and the recovered instruction
    assemble to the same bytes.
    """
    if _BEEBASM is None:
        pytest.skip("beebasm not found")
    output_dirpath = _run_dasmos_driver(tmp_path)
    asm_text = (output_dirpath / "nfs-3.34.asm").read_text(encoding="utf-8")
    for expected in (
        "bcs accept_new_claim",
        "beq string_buf_done",
        "bne strnh",
        "sta tube_data_register_4",
    ):
        assert expected in asm_text, (
            f"expected `{expected}` in rendered asm — regression of "
            f"the overlapping-move tracer fix?"
        )
