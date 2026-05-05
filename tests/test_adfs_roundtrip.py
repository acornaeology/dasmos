"""Round-trip tests against the real Acorn ADFS 1.30 ROM.

ADFS (Advanced Disc Filing System) is the canonical Acorn winchester
/ floppy filesystem ROM; 16 KB sideways ROM mapped at &8000-&BFFF.
Mirrors :mod:`tests.test_nfs_roundtrip` in shape:

- :class:`TestAdfsPorterEndToEnd` — port the unmodified original
  py8dis driver, run it, capture the rendered beebasm source,
  re-assemble via beebasm, assert byte-identical with the original
  ROM.
- :class:`TestAdfsPy8disParity` — vocabulary-coverage check against
  the vendored py8dis reference output. Marker ``py8dis_parity`` so
  it can be deselected wholesale once dasmos is intentionally
  allowed to diverge.

ADFS is the largest sibling fixture (16 KB ROM, 12,553-line driver)
and exercises filesystem-state-machine code paths absent from the
network-state-machine NFS fixture: heavy OSGBPB / OSFILE / OSFIND
use, disc geometry constants, and a richer command-vector dispatch.
"""

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-adfs"
ROM_PATH = _FIXTURES / "adfs-1.30.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_adfs_130.py"
PY8DIS_REFERENCE_PATH = _FIXTURES / "py8dis_reference_adfs-1.30.asm"
PY8DIS_REFERENCE_JSON_PATH = _FIXTURES / "py8dis_reference_adfs-1.30.json"

ROM_SIZE = 16384
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "831ee90ac5d49ba5507252faf0c12536"
PY8DIS_REFERENCE_MD5 = "d540e4b2ba260360961464318ad14e0a"
PY8DIS_REFERENCE_JSON_MD5 = "02f3aaf786641b3db5babfc159544b26"

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
class TestAdfsPorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the ADFS
    1.30 ROM, produces beebasm source that re-assembles byte-identical
    with the original ROM.
    """

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        rom = ROM_PATH.read_bytes()
        assert hashlib.md5(rom).hexdigest() == ROM_MD5
        assert len(rom) == ROM_SIZE

        # ADFS-1.30 targets the WD1770 — opt the FDC env in. The
        # py8dis driver calls ``acorn.bbc()``, which in dasmos
        # doesn't auto-activate any FDC (the chip was always an
        # upgrade, never standard hardware), so the FDC choice is
        # the caller's explicit decision.
        ported_src = _porter.port(
            ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"),
            extra_envs=("acorn_fdc_1770",),
        )
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

        asm_filepath = output_dirpath / "adfs-1.30.asm"
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


# ---------------------------------------------------------------------------
# py8dis annotation-content parity
# ---------------------------------------------------------------------------

# Initial measurement was 67; closing two gaps in 2026-05-04 work
# dropped it to 14:
# - The return-N rule (autogenerated labels at bare-RTS targets get
#   sequential ``return_<N>`` names, matching py8dis) closed 49.
# - Adding the Fred-bus floppy controller registers (&FC40-&FC43)
#   to the BBC hardware env's vocabulary closed 4 (the env was
#   ``acorn_bbc_hardware`` at the time, since split into
#   ``acorn_model_b_hardware`` and ``acorn_master_hardware``).
# Residual 14 is mostly free-text words from py8dis's auto-comment
# generator (``baud``, ``ieee``, ``paged``, ``teletext``, …) plus
# 2 mid-instruction hex addresses (``bc7e``, ``bcad``).
MAX_COMMENT_TOKENS_DROPPED = 14

_COMMENT_TOKEN_RE = re.compile(r"[a-z_][a-z_0-9]{3,}")


def _comment_text(asm_text: str) -> str:
    """Keep EVERY ``;``-introduced chunk so the byte-column annotation
    contributes addresses/symbols to the parity corpus.
    """
    parts: list[str] = []
    for line in asm_text.splitlines():
        chunks = line.split(";")
        parts.extend(chunks[1:])
    return " ".join(parts).replace("`", "").lower()


def _comment_tokens(asm_text: str) -> set[str]:
    return set(_COMMENT_TOKEN_RE.findall(_comment_text(asm_text)))


def _run_dasmos_driver(tmp_path) -> Path:
    """Port the ADFS driver via py8dis2dasmos, run it, return the
    output dir.
    """
    # ADFS-1.30 targets the WD1770 — opt the FDC env in. The
    # py8dis driver calls ``acorn.bbc()``, which in dasmos doesn't
    # auto-activate any FDC (the chip was always an upgrade,
    # never standard hardware), so the FDC choice is the caller's
    # explicit decision.
    ported_src = _porter.port(
        ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"),
        extra_envs=("acorn_fdc_1770",),
    )
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
        f"ported driver failed:\n=== stderr ===\n{result.stderr}"
    )
    return output_dirpath


@pytest.mark.beebasm
@pytest.mark.py8dis_parity
class TestAdfsPy8disParity:

    def test_reference_fixture_pinned(self):
        actual = hashlib.md5(PY8DIS_REFERENCE_PATH.read_bytes()).hexdigest()
        assert actual == PY8DIS_REFERENCE_MD5, (
            f"py8dis reference output md5 changed ({actual}); "
            f"either re-vendor and update PY8DIS_REFERENCE_MD5, or "
            f"investigate why the upstream output is different."
        )

    def test_reference_json_fixture_pinned(self):
        actual = hashlib.md5(
            PY8DIS_REFERENCE_JSON_PATH.read_bytes()
        ).hexdigest()
        assert actual == PY8DIS_REFERENCE_JSON_MD5, (
            f"py8dis reference JSON md5 changed ({actual}); re-vendor "
            f"with the py8dis fork's get_structured() output and "
            f"update PY8DIS_REFERENCE_JSON_MD5."
        )

    def test_comment_vocabulary_covers_py8dis(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        output_dirpath = _run_dasmos_driver(tmp_path)
        candidate_filepath = output_dirpath / "adfs-1.30.asm"

        ref_tokens = _comment_tokens(PY8DIS_REFERENCE_PATH.read_text(encoding="utf-8"))
        das_tokens = _comment_tokens(candidate_filepath.read_text(encoding="utf-8"))

        missing = ref_tokens - das_tokens
        sample = sorted(missing)[:25]
        assert len(missing) <= MAX_COMMENT_TOKENS_DROPPED, (
            f"dasmos dropped {len(missing)} unique comment tokens "
            f"present in the py8dis reference (allowed: "
            f"{MAX_COMMENT_TOKENS_DROPPED}). Sample: {sample}. "
            f"If you've fixed a fidelity gap, lower "
            f"MAX_COMMENT_TOKENS_DROPPED to the new observed value."
        )
