"""Tests for the 64tass renderer.

Two layers:

- **Unit** — the lexical protocol and the 64tass-specific translation
  seams (``.byte``/``.word``/``.text``, ``$`` hex, ``.logical``/``.here``
  relocation, ``&HH`` → ``$HH`` and ``HI``/``LO``/``AND``/``EOR``
  expression rewriting). No assembler needed.
- **Round-trip oracle** — the load-bearing check that the interface is
  generic: the same real sibling-repo ROMs that round-trip through
  beebasm also disassemble → 64tass source → re-assemble → byte-match
  the original. That one IR survives two different backends back to
  identical bytes is the genericity proof. Gated by ``@pytest.mark.tass64``
  (auto-skips when the ``64tass`` binary is absent).
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.tass64 import Tass64Renderer
from dasmos.renderer import create_renderer


_FIXTURES = Path(__file__).parent / "fixtures"
_PORTER_PATH = Path(__file__).parent.parent / "scripts" / "py8dis2dasmos.py"

_porter_spec = importlib.util.spec_from_file_location(
    "py8dis2dasmos_tass64", _PORTER_PATH,
)
_porter = importlib.util.module_from_spec(_porter_spec)
_porter_spec.loader.exec_module(_porter)


def _find_tass64() -> str | None:
    env = os.environ.get("TASS64")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("64tass")


TASS64 = _find_tass64()


# ---------------------------------------------------------------------------
# Unit tests — no assembler required
# ---------------------------------------------------------------------------

class TestLexicalProtocol:
    def setup_method(self):
        self.r = Tass64Renderer()

    def test_hex_uses_dollar_sigil(self):
        assert self.r.hex2(0x7F) == "$7f"
        assert self.r.hex4(0xE000) == "$e000"

    def test_data_directives(self):
        assert self.r.byte_prefix() == ".byte "
        assert self.r.word_prefix() == ".word "
        assert self.r.string_prefix() == ".text "

    def test_inline_label_is_bare_name(self):
        assert self.r.inline_label("foo") == "foo"

    def test_explicit_label(self):
        assert self.r.explicit_label("foo", "$1234") == "foo = $1234"
        assert self.r.explicit_label("foo", "bar", offset=2) == "foo = bar+2"

    def test_comment_prefix(self):
        assert self.r.comment_prefix() == ";"

    def test_fill_is_native(self):
        assert self.r.fill_directive(0xEA, 5) == [".fill 5, $ea"]
        assert self.r.fill_directive(0, 0) == []

    def test_address_link_hex_uses_dollar(self):
        assert self.r.address_link_hex("E000") == "$E000"

    def test_registered_via_entry_point(self):
        assert isinstance(create_renderer("64tass"), Tass64Renderer)


class TestRelocationHooks:
    def setup_method(self):
        self.r = Tass64Renderer()

    def test_set_origin_uses_star_equals(self):
        assert self.r.set_origin(0xE000) == ["", "    * = $e000"]

    def test_pseudopc_start_is_logical(self):
        lines = self.r.pseudopc_start(
            dest=0x0100, src=0xF859, length=0x40, move_id=1,
            src_label="src", dest_label="dst",
        )
        assert "    .logical $0100" in lines

    def test_pseudopc_end_is_here_only(self):
        # The whole point: 64tass needs no copyblock/restore, just .here.
        lines = self.r.pseudopc_end(
            dest=0x0100, src=0xF859, length=0x40, move_id=1,
            src_label="src", dest_label="dst",
        )
        assert lines == ["    .here", ""]


class TestExpressionTranslation:
    def setup_method(self):
        self.r = Tass64Renderer()

    def test_ampersand_hex_becomes_dollar(self):
        assert self.r.translate_expression("label-&81") == "label-$81"
        assert self.r.translate_expression("&FFEE") == "$FFEE"

    def test_hi_lo_functions_become_operators(self):
        assert self.r.translate_expression("HI(star_run-1)") == ">(star_run-1)"
        assert self.r.translate_expression("LO(star_run-1)") == "<(star_run-1)"

    def test_bitwise_keywords(self):
        assert self.r.translate_expression("x AND &FF") == "x & $FF"
        assert self.r.translate_expression("(255 - k) EOR 128") == "(255 - k) ^ 128"

    def test_or_does_not_match_inside_eor(self):
        # \bOR\b must not corrupt EOR.
        assert self.r.translate_expression("a EOR b") == "a ^ b"


class TestStringDirective:
    def setup_method(self):
        self.r = Tass64Renderer()

    def test_mixed_byte_and_string_uses_text(self):
        # 64tass .byte rejects multi-char strings; a mixed line must use
        # .text even when it leads with a raw byte.
        assert self.r._string_line_directive(
            first_is_string=False, has_string=True,
        ) == ".text "

    def test_pure_bytes_use_byte(self):
        assert self.r._string_line_directive(
            first_is_string=False, has_string=False,
        ) == ".byte "


# ---------------------------------------------------------------------------
# Round-trip oracle — requires the 64tass binary
# ---------------------------------------------------------------------------

def _assemble_64tass(asm_text: str, tmp_path: Path) -> bytes:
    asm = tmp_path / "in.asm"
    asm.write_text(asm_text, encoding="utf-8")
    out = tmp_path / "out.bin"
    result = subprocess.run(
        [TASS64, "--nostart", "-o", str(out), str(asm)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    if result.returncode != 0:
        raise AssertionError(
            f"64tass failed to assemble:\n"
            f"=== source ===\n{asm_text}\n=== stderr ===\n{result.stderr}"
        )
    return out.read_bytes()


@pytest.mark.tass64
class TestTass64SyntheticRoundTrip:
    """Small hand-built inputs → 64tass → binary, byte-compared."""

    def _round_trip(self, binary: bytes, load_addr: int, configure, tmp_path):
        bin_in = tmp_path / "input.bin"
        bin_in.write_bytes(binary)
        d = Disassembler.create(cpu="6502")
        d.load(bin_in, load_addr)
        configure(d)
        ir = d.disassemble()
        text = str(ir.render(Tass64Renderer()))
        return _assemble_64tass(text, tmp_path)

    def test_lda_rts(self, tmp_path):
        original = bytes([0xA9, 0x42, 0x60])  # lda #$42 : rts
        produced = self._round_trip(
            original, 0x2000, lambda d: d.entry(0x2000, name="start"), tmp_path,
        )
        assert produced == original

    def test_jsr_and_data(self, tmp_path):
        # jsr $2006 : rts : <pad> : .byte "Hi", $0d
        original = bytes([0x20, 0x06, 0x20, 0x60, 0xEA, 0xEA,
                          ord("H"), ord("i"), 0x0D])

        def configure(d):
            d.entry(0x2000, name="start")
            d.string(0x2006, 3)

        produced = self._round_trip(original, 0x2000, configure, tmp_path)
        assert produced == original

    def test_indexed_and_zp(self, tmp_path):
        # lda $80,x : sta $2100 : rts
        original = bytes([0xB5, 0x80, 0x8D, 0x00, 0x21, 0x60])
        produced = self._round_trip(
            original, 0x2000, lambda d: d.entry(0x2000, name="start"), tmp_path,
        )
        assert produced == original


# Sibling-repo ROMs, driven through their full ported drivers.
# (subdir, driver, rom, emitted-asm). tube-client is xfail: its 4 KB
# region at $F800 crosses the 64 KB boundary ($F800+$1000 = $10800),
# which beebasm's linear 32-bit save handles but 64tass's 16-bit PC
# wraps at $FFFF — a genuine address-space-representation difference,
# not an interface gap.
_ROMS = [
    pytest.param(
        "acorn-6502-tube-client", "disasm_tube_6502_client_110.py",
        "tube-6502-client-1.10.rom", "tube-6502-client-1.10.asm",
        marks=pytest.mark.xfail(
            reason="4KB region at $F800 wraps the 64KB boundary; "
                   "64tass wraps its PC at $FFFF",
            strict=True,
        ),
        id="acorn-6502-tube-client",
    ),
    pytest.param("acorn-adfs", "disasm_adfs_130.py",
                 "adfs-1.30.rom", "adfs-1.30.asm", id="acorn-adfs"),
    pytest.param("acorn-anfs-4.18", "disasm_anfs_418.py",
                 "anfs-4.18.rom", "anfs-4.18.asm", id="acorn-anfs-4.18"),
    pytest.param("acorn-anfs-4.21", "disasm_anfs_421_variant_1.py",
                 "anfs-4.21_variant_1.rom", "anfs-4.21_variant_1.asm",
                 id="acorn-anfs-4.21"),
    pytest.param("acorn-econet-bridge", "disasm_econet_bridge_variant_1.py",
                 "econet-bridge-variant_1.rom", "econet-bridge-variant_1.asm",
                 id="acorn-econet-bridge"),
    pytest.param("acorn-nfs-3.34", "disasm_nfs_334.py",
                 "nfs-3.34.rom", "nfs-3.34.asm", id="acorn-nfs-3.34"),
    pytest.param("acorn-nfs", "disasm_nfs_365.py",
                 "nfs-3.65.rom", "nfs-3.65.asm", id="acorn-nfs-3.65"),
]


@pytest.mark.tass64
@pytest.mark.parametrize("subdir,driver,rom,asm", _ROMS)
def test_sibling_rom_round_trips_via_64tass(subdir, driver, rom, asm, tmp_path):
    """Port the driver targeting 64tass, run it, assemble the emitted
    64tass source, and assert byte-equality with the original ROM.
    """
    fixture_dirpath = _FIXTURES / subdir
    ported = _porter.port(
        (fixture_dirpath / driver).read_text(encoding="utf-8"),
        assembler_name="64tass",
    )
    ported_filepath = tmp_path / "ported_driver.py"
    ported_filepath.write_text(ported, encoding="utf-8")
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
        f"ported driver for {subdir} failed:\n{result.stderr}"
    )
    asm_text = (output_dirpath / asm).read_text(encoding="utf-8")
    rebuilt = _assemble_64tass(asm_text, tmp_path)
    original = (fixture_dirpath / rom).read_bytes()
    assert rebuilt == original, (
        f"64tass round-trip byte mismatch for {subdir}: "
        f"{len(rebuilt)} vs {len(original)} bytes"
    )
