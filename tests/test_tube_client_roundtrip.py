"""Round-trip tests against the real Acorn 6502 Tube Client ROM.

The Tube Client ROM is a 4 KB physical chip whose upper 2 KB maps at
&F800-&FFFF on the second processor; the lower 2 KB is unused. Mirrors
:mod:`tests.test_econet_bridge_roundtrip` in shape:

- :class:`TestTubeClientPorterEndToEnd` — port the unmodified original
  py8dis driver, run it, capture the rendered beebasm source,
  re-assemble via beebasm, assert byte-identical with the upper 2 KB
  of the original ROM.
- :class:`TestTubeClientPy8disParity` — vocabulary-coverage check
  against the vendored py8dis reference output. Marker
  ``py8dis_parity`` so it can be deselected wholesale once dasmos is
  intentionally allowed to diverge.

Exercises three pieces of infrastructure absent from the Econet Bridge
test: the cmos65c02 CPU plug-in, the move-aware renderer (the &F859→
&0100 7-byte relocation), and subroutine hooks (the inline-string
idiom via JSR &FE98 / stringhi_hook).
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


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-6502-tube-client"
ROM_PATH = _FIXTURES / "tube-6502-client-1.10.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_tube_6502_client_110.py"
PY8DIS_REFERENCE_PATH = _FIXTURES / "py8dis_reference_tube-6502-client-1.10.asm"

# 4 KB physical ROM, only the upper 2 KB is mapped.
ROM_PHYSICAL_SIZE = 4096
MAPPED_SIZE = 2048
ROM_LOAD_ADDR = 0xF800
ROM_FULL_MD5 = "8c3b9252ac812c892aa21b9252abf94c"
PY8DIS_REFERENCE_MD5 = "a1c6cc8db04384133a3195f9d3874ed1"

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

        ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text())
        ported_filepath = tmp_path / "ported_driver.py"
        ported_filepath.write_text(ported_src)

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


# ---------------------------------------------------------------------------
# py8dis annotation-content parity (same approach as the Econet Bridge test)
# ---------------------------------------------------------------------------

# History (lower as fidelity gaps close):
#   55 — first run with move-aware renderer
#   42 — after adding the explanatory ``;`` comments around the
#        copyblock / clear / org block (mirroring py8dis).
#   37 — after auto-label generation (``l<addr>``, ``c<addr>``,
#        ``sub_c<addr>``, ``loop_c<addr>``) and the trailing
#        ``; Automatically generated labels:`` footer.
#   26 — after broadening the comment-text extractor to keep every
#        ``;``-introduced chunk and adding the ``"py8dis"`` byte-
#        column format.
#   12 — after multi-line equb/equw byte-column annotations and
#        configurable cols defaults (porter sets 12 / 6).
#    8 — after threading ``on_entry`` / ``on_exit`` through
#        ``Disassembler.subroutine`` / ``banner`` and rendering
#        them as ``; On Entry:`` / ``; On Exit:`` sub-blocks of the
#        banner (porter no longer drops these kwargs).
#    1 — after emitting xref summaries for mid-instruction labels
#        in the equate table (``; &xxxx referenced N times by …``
#        below each ``name = &xxxx`` whose label has references).
#
#    0 — after the offset-base synthesis: the Disassembler
#        synthesises an auto-label at the start of any classification
#        that contains a mid-instruction label (in non-moved
#        regions), and the renderer emits the mid-instruction labels
#        as ``<name> = <base>+<offset>`` inline under the base.
#        Mirrors py8dis's ``nmi1_transfer_addr = sub_cfe15+1``
#        idiom. The xref summary above each offset definition
#        contributes the binary-hex tokens that py8dis emits in the
#        same position. Inside moved regions the trick is skipped
#        (the body walk anchors labels at the move-DEST runtime, so
#        a +offset from there would resolve wrong) — those mid-
#        instruction labels stay as literal hex equates, matching
#        py8dis.
MAX_COMMENT_TOKENS_DROPPED = 0

_COMMENT_TOKEN_RE = re.compile(r"[a-z_][a-z_0-9]{3,}")


def _comment_text(asm_text: str) -> str:
    """See ``test_econet_bridge_roundtrip._comment_text`` — keeps
    EVERY ``;``-introduced chunk so the byte-column annotation
    contributes addresses/symbols to the parity corpus."""
    parts: list[str] = []
    for line in asm_text.splitlines():
        chunks = line.split(";")
        parts.extend(chunks[1:])
    return " ".join(parts).replace("`", "").lower()


def _comment_tokens(asm_text: str) -> set[str]:
    return set(_COMMENT_TOKEN_RE.findall(_comment_text(asm_text)))


@pytest.mark.beebasm
@pytest.mark.py8dis_parity
class TestTubeClientPy8disParity:

    def test_reference_fixture_pinned(self):
        actual = hashlib.md5(PY8DIS_REFERENCE_PATH.read_bytes()).hexdigest()
        assert actual == PY8DIS_REFERENCE_MD5, (
            f"py8dis reference output md5 changed ({actual}); "
            f"either re-vendor and update PY8DIS_REFERENCE_MD5, or "
            f"investigate why the upstream output is different."
        )

    def test_comment_vocabulary_covers_py8dis(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text())
        ported_filepath = tmp_path / "ported_driver.py"
        ported_filepath.write_text(ported_src)
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
        candidate_filepath = output_dirpath / "tube-6502-client-1.10.asm"

        ref_tokens = _comment_tokens(PY8DIS_REFERENCE_PATH.read_text())
        das_tokens = _comment_tokens(candidate_filepath.read_text())

        missing = ref_tokens - das_tokens
        sample = sorted(missing)[:25]
        assert len(missing) <= MAX_COMMENT_TOKENS_DROPPED, (
            f"dasmos dropped {len(missing)} unique comment tokens "
            f"present in the py8dis reference (allowed: "
            f"{MAX_COMMENT_TOKENS_DROPPED}). Sample: {sample}. "
            f"If you've fixed a fidelity gap, lower "
            f"MAX_COMMENT_TOKENS_DROPPED to the new observed value."
        )
