"""Round-trip tests against the real Acorn ANFS 4.21 (variant 1) ROM.

ANFS (Advanced Network Filing System) is the BBC Master-era
successor to NFS. 16 KB sideways ROM, mapped at &8000-&BFFF, with
substantially larger and more deeply annotated code than the 8 KB
NFS 3.x family — Master features, richer command vector dispatch,
and the largest py8dis driver in the four sibling projects (~17,500
lines of source).

Mirrors :mod:`tests.test_adfs_roundtrip` in shape:

- :class:`TestAnfs421PorterEndToEnd` — port the unmodified original
  py8dis driver, run it, capture the rendered beebasm source,
  re-assemble via beebasm, assert byte-identical with the original
  ROM.
- :class:`TestAnfs421Py8disParity` — vocabulary-coverage check
  against the vendored py8dis reference output. Marker
  ``py8dis_parity`` so it can be deselected wholesale once dasmos
  is intentionally allowed to diverge.

Distinctive vs. the existing fixtures:

- Largest driver in the sibling set; surfaces porter / renderer
  scaling issues that smaller fixtures don't.
- Master-era OS-call patterns (some calls absent from BBC Micro
  MOS) exercise environment-extension corners not hit by NFS-3.65.
- Heavy use of ``data_banner(...)`` for table / hardware-vector
  block headers; the porter expands these into label + banner
  pairs the same way it handles ``subroutine(..., is_entry_point=
  False)``.
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


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-anfs-4.21"
ROM_PATH = _FIXTURES / "anfs-4.21_variant_1.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_anfs_421_variant_1.py"
PY8DIS_REFERENCE_PATH = _FIXTURES / "py8dis_reference_anfs-4.21_variant_1.asm"
PY8DIS_REFERENCE_JSON_PATH = _FIXTURES / "py8dis_reference_anfs-4.21_variant_1.json"

ROM_SIZE = 16384
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "03371d224a8f048c129335682434d025"
PY8DIS_REFERENCE_MD5 = "7728e8c3c4a9db2374ad60f0829eb78e"
PY8DIS_REFERENCE_JSON_MD5 = "42d833acde66da8e73866aa7dc2d2328"

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
class TestAnfs421PorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the ANFS
    4.21 ROM, produces beebasm source that re-assembles
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

        asm_filepath = output_dirpath / "anfs-4.21_variant_1.asm"
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

# Initial measurement was 8. Closing the return-N rule in
# 2026-05-04 work brought it to 3 — only ``eeprom``, ``sync``,
# ``vertical`` remain as free-text words from py8dis comment
# annotations dasmos doesn't emit.
MAX_COMMENT_TOKENS_DROPPED = 3

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
    """Port the ANFS 4.21 driver via py8dis2dasmos, run it, return
    the output dir.
    """
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
        f"ported driver failed:\n=== stderr ===\n{result.stderr}"
    )
    return output_dirpath


@pytest.mark.beebasm
@pytest.mark.py8dis_parity
class TestAnfs421Py8disParity:

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
        candidate_filepath = output_dirpath / "anfs-4.21_variant_1.asm"

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
