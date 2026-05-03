"""Round-trip tests against the real Acorn Econet Bridge ROM.

The Econet Bridge ROM is an 8 KB binary mapped at &E000-&FFFF on a
custom 6502 board. Vendored from
``acorn-econet-bridge/versions/econet-bridge-variant_1/rom/`` into
this repo's ``tests/fixtures/acorn-econet-bridge/`` so the tests are
self-contained.

These tests build up from the simplest possible round-trip
(``load → leftover-classify → render → re-assemble → byte-compare``)
to progressively more annotated forms — the goal is to surface gaps
in the dasmos driver-script API by use rather than by spec.

The ROM is unaltered Acorn firmware; copyright remains with the
original authors. It's included here only as a test fixture for
correctness validation of the dasmos disassembler against a known-
good real-world binary.
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

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-econet-bridge"
ROM_PATH = _FIXTURES / "econet-bridge-variant_1.rom"
ROM_LOAD_ADDR = 0xE000
ROM_MD5 = "d5328f517902a4d2659e302acfc0882f"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_econet_bridge_variant_1.py"

# The reference output produced by running the original (unmodified)
# disasm driver under the legacy py8dis fork. Vendored here so the
# parity tests are self-contained. The md5 pin guards against silent
# fixture rot.
PY8DIS_REFERENCE_PATH = _FIXTURES / "py8dis_reference_econet-bridge-variant_1.asm"
PY8DIS_REFERENCE_MD5 = "4c696830830948a22d3a03caa5470f6b"

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


def _roundtrip_via_beebasm(
    tmp_path: Path,
    configure,
    *,
    expected_md5: str = ROM_MD5,
) -> tuple[bytes, str]:
    """Disassemble the Econet Bridge ROM, render via beebasm, and
    re-assemble. Returns ``(rebuilt_bytes, rendered_text)``.

    Asserts byte-equality against the original ROM as a side effect.
    """
    if _BEEBASM is None:  # pragma: no cover — gated by @pytest.mark.beebasm
        pytest.skip("beebasm not found")

    original = ROM_PATH.read_bytes()
    assert hashlib.md5(original).hexdigest() == expected_md5

    d = Disassembler.create(cpu="nmos6502")
    d.load(ROM_PATH, ROM_LOAD_ADDR, md5sum=expected_md5)
    configure(d)
    ir = d.disassemble()

    renderer = BeebasmRenderer()
    renderer.set_output_filename("rebuilt.bin")
    text = str(ir.render(renderer))

    asm_path = tmp_path / "econet.asm"
    asm_path.write_text(text, encoding="utf-8")

    result = subprocess.run(
        [_BEEBASM, "-i", str(asm_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    if result.returncode != 0:
        raise AssertionError(
            f"beebasm failed to assemble dasmos output:\n"
            f"=== first 2KB of source ===\n{text[:2048]}\n"
            f"=== stderr ===\n{result.stderr}"
        )
    rebuilt = (tmp_path / "rebuilt.bin").read_bytes()
    assert rebuilt == original, (
        f"round-trip byte mismatch: {len(rebuilt)} vs {len(original)} bytes"
    )
    return rebuilt, text


@pytest.mark.beebasm
class TestEconetBridgeRoundTrip:

    def test_pure_data_round_trip_no_entries(self, tmp_path):
        """No entry points → trace doesn't run → leftover pass
        classifies every byte as Byte(1) → render emits 8192 equb
        lines → beebasm assembles back to the original 8192 bytes.

        The simplest possible end-to-end check that dasmos can
        round-trip a real binary at all.
        """
        rebuilt, text = _roundtrip_via_beebasm(
            tmp_path, lambda d: None,
        )
        assert len(rebuilt) == 8192

    def test_traced_from_reset_vector(self, tmp_path):
        """Read the reset vector from the ROM and seed an entry there.

        The trace will follow control flow from the real reset
        handler; classifications switch from leftover-Byte to actual
        Opcode for every reachable byte.
        """
        # Read the reset vector before configuring (just for sanity).
        rom = ROM_PATH.read_bytes()
        reset_lo = rom[0xFFFC - ROM_LOAD_ADDR]
        reset_hi = rom[0xFFFD - ROM_LOAD_ADDR]
        reset_addr = reset_lo | (reset_hi << 8)
        # Sanity: should be in ROM range.
        assert ROM_LOAD_ADDR <= reset_addr < (ROM_LOAD_ADDR + 8192)

        def configure(d):
            d.subroutine(reset_addr, name="reset")

        rebuilt, text = _roundtrip_via_beebasm(tmp_path, configure)
        # Reset label appears in the rendered text.
        assert ".reset" in text

    def test_with_all_three_hardware_vector_entries(self, tmp_path):
        """The Econet Bridge ROM has three hardware vectors at the
        top of the ROM (NMI, RESET, IRQ/BRK at &FFFA-&FFFF). Mark all
        three as entries to maximise the trace coverage.
        """
        rom = ROM_PATH.read_bytes()
        nmi_addr = rom[0xFFFA - ROM_LOAD_ADDR] | (rom[0xFFFB - ROM_LOAD_ADDR] << 8)
        reset_addr = rom[0xFFFC - ROM_LOAD_ADDR] | (rom[0xFFFD - ROM_LOAD_ADDR] << 8)
        irq_addr = rom[0xFFFE - ROM_LOAD_ADDR] | (rom[0xFFFF - ROM_LOAD_ADDR] << 8)

        def configure(d):
            if ROM_LOAD_ADDR <= reset_addr < ROM_LOAD_ADDR + 8192:
                d.subroutine(reset_addr, name="reset")
            if ROM_LOAD_ADDR <= irq_addr < ROM_LOAD_ADDR + 8192:
                d.subroutine(irq_addr, name="self_test")
            if ROM_LOAD_ADDR <= nmi_addr < ROM_LOAD_ADDR + 8192:
                d.subroutine(nmi_addr, name="nmi_handler")

        rebuilt, text = _roundtrip_via_beebasm(tmp_path, configure)
        assert ".reset" in text

    def test_with_external_zp_labels(self, tmp_path):
        """A driver typically registers a bunch of zero-page workspace
        names via ``label()``. Verify the round-trip still works when
        we include external labels.
        """
        rom = ROM_PATH.read_bytes()
        reset_addr = rom[0xFFFC - ROM_LOAD_ADDR] | (rom[0xFFFD - ROM_LOAD_ADDR] << 8)

        def configure(d):
            d.subroutine(reset_addr, name="reset")
            # A small selection of zero-page names from the original
            # driver's first few `label()` calls.
            d.label(0x0000, "st_ptr_lo")
            d.label(0x0001, "st_ptr_hi")
            d.label(0x0002, "st_page_count")
            d.label(0x0080, "mem_ptr_lo")
            d.label(0x0081, "mem_ptr_hi")
            d.label(0x0082, "top_ram_page")

        rebuilt, text = _roundtrip_via_beebasm(tmp_path, configure)
        # Each label should appear in the explicit-definition table.
        for name in (
            "st_ptr_lo", "st_ptr_hi", "st_page_count",
            "mem_ptr_lo", "mem_ptr_hi", "top_ram_page",
        ):
            assert name in text


@pytest.mark.beebasm
class TestEconetBridgePorterEndToEnd:
    """The load-bearing acceptance test for the py8dis2dasmos porter:
    take the unmodified original py8dis driver for the Econet Bridge
    ROM, port it via ``scripts/py8dis2dasmos.py``, run the ported
    script, capture its rendered beebasm source, re-assemble via
    beebasm, verify byte-equality with the original ROM.

    This exercises the entire pipeline — porter rules, dasmos
    disassembly, beebasm renderer, and the round-trip oracle — against
    a real 3000+-line driver."""

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        original_driver_src = ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8")
        ported_src = _porter.port(original_driver_src)

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

        asm_filepath = output_dirpath / "econet-bridge-variant_1.asm"
        assert asm_filepath.exists(), (
            f"expected rendered asm at {asm_filepath}, "
            f"stderr was:\n{result.stderr}"
        )

        rebuilt_filepath = tmp_path / "rebuilt.bin"
        result = subprocess.run(
            [
                _BEEBASM,
                "-i", str(asm_filepath),
                "-o", str(rebuilt_filepath),
            ],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed to assemble ported output:\n"
            f"=== stderr ===\n{result.stderr}"
        )

        rebuilt = rebuilt_filepath.read_bytes()
        original = ROM_PATH.read_bytes()
        assert hashlib.md5(rebuilt).hexdigest() == ROM_MD5
        assert rebuilt == original, (
            f"byte mismatch: {len(rebuilt)} vs {len(original)} bytes"
        )


# ---------------------------------------------------------------------------
# Annotation-content parity with the legacy py8dis fork
# ---------------------------------------------------------------------------
#
# Byte-equality is necessary but not sufficient — a renderer that
# strips every comment would still round-trip cleanly. These tests
# guard against silent loss of *annotation content* by comparing the
# dasmos-rendered output against the vendored py8dis reference.
#
# The current strategy is a token-level "vocabulary coverage" check:
# extract every word from `;`-comment text in both files, and assert
# the dasmos output's vocabulary covers (most of) the reference's.
# This is robust to wrapping/formatting differences and surfaces
# *content* drops cleanly.
#
# ``MAX_COMMENT_TOKENS_DROPPED`` is a ratchet — start at the current
# observed gap and lower it as fidelity gaps close (label-definition
# comments, cross-reference summary lines, etc.). When dasmos is
# intentionally allowed to diverge, deselect this whole class with
# ``pytest -m 'not py8dis_parity'`` and eventually delete the marker.
#
# History (lower as fidelity gaps close):
#   458 — 2026-05-02 baseline (initial parity check)
#   417 — 2026-05-02 after rendering label `description=` as inline
#         comment on the equate.
#     9 — 2026-05-02 after adding inline xref summaries
#         (`; &xxxx referenced N time(s) by &yyyy, …`) and the
#         end-of-file label-frequency table.
#     0 — 2026-05-02 after byte-column inline annotation, ``; Memory
#         locations`` header, ``; Stats:`` block, boundary-label
#         entries in the frequency table, and the porter passing
#         ``boundary_label_prefix='pydis_'`` + ``byte_column=True``
#         to render. Full annotation-content parity.
#
# Note: dasmos's vocabulary is now a strict superset (extra tokens
# come from markdown we don't yet rewrite — see task #26). Once the
# markdown rewrite lands we'd expect dasmos == py8dis exactly.

MAX_COMMENT_TOKENS_DROPPED = 0

_COMMENT_TOKEN_RE = re.compile(r"[a-z_][a-z_0-9]{3,}")


def _comment_text(asm_text: str) -> str:
    """Extract every ``;``-comment fragment from a beebasm source,
    normalised: lowercased, backticks (markdown) stripped.

    Splits each line on ``;`` and keeps *every* chunk after the first,
    so a line like ``cli  ; f85c: 58 X  ; Enable IRQs`` contributes
    BOTH the byte-column ``f85c: 58 X`` AND the user comment ``Enable
    IRQs`` to the corpus. Catches addresses/symbols that py8dis writes
    into its inline byte column.
    """
    parts: list[str] = []
    for line in asm_text.splitlines():
        chunks = line.split(";")
        # chunks[0] is the pre-comment opcode/data text — drop it. All
        # remaining chunks are ``;``-introduced comment territory.
        parts.extend(chunks[1:])
    blob = " ".join(parts).replace("`", "").lower()
    return blob


def _comment_tokens(asm_text: str) -> set[str]:
    return set(_COMMENT_TOKEN_RE.findall(_comment_text(asm_text)))


@pytest.mark.beebasm
@pytest.mark.py8dis_parity
class TestEconetBridgePy8disParity:
    """Annotation-content parity with the legacy py8dis-fork output.

    Marked ``py8dis_parity``: deselect with ``pytest -m 'not
    py8dis_parity'`` once dasmos is intentionally allowed to diverge.
    """

    def test_reference_fixture_pinned(self):
        """Guard against silent updates to the vendored reference."""
        actual = hashlib.md5(PY8DIS_REFERENCE_PATH.read_bytes()).hexdigest()
        assert actual == PY8DIS_REFERENCE_MD5, (
            f"py8dis reference output md5 changed ({actual}); "
            f"either re-vendor and update PY8DIS_REFERENCE_MD5, or "
            f"investigate why the upstream output is different."
        )

    def test_comment_vocabulary_covers_py8dis(self, tmp_path):
        """The dasmos-rendered output's comment vocabulary should
        cover the py8dis reference's, modulo a small allowed gap that
        ratchets down as we close fidelity issues. A failure here means
        either (a) we lost more annotation content (bad — fix the gap),
        or (b) we closed a gap (good — lower the threshold)."""
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        # Run the porter end-to-end (same pipeline as the round-trip
        # test) to get the candidate output.
        original_driver_src = ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8")
        ported_src = _porter.port(original_driver_src)
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
        candidate_filepath = output_dirpath / "econet-bridge-variant_1.asm"

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
