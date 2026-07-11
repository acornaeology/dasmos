"""File header (#40) and build-instructions (#41) preamble.

A driver-set provenance header renders as a comment block at the top of
every backend's listing (agnostic prose + the backend's comment prefix)
and surfaces in the JSON ``meta``. Separately, a renderer can be asked to
emit its own "how to assemble this file" command. Both are opt-in, comment
-only (round-trip safe), and off by default.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from dasmos import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _mk(data=b"\x60", load=0x2000):
    p = Path(tempfile.mktemp())
    p.write_bytes(data)
    d = Disassembler.create(cpu="6502")
    d.load(p, load)
    return d


# ---------------------------------------------------------------------------
# File header (#40)
# ---------------------------------------------------------------------------

class TestFileHeader:
    def _with_header(self):
        d = _mk()
        d.set_file_header(
            title="Acorn BBC BASIC II",
            description="Line one.\nmd5 2cc6; sha256 45bd.",
        )
        return d

    def test_absent_by_default(self):
        # No header set → no leading comment block; output unchanged.
        text = str(_mk().disassemble().render(
            BeebasmRenderer(boundary_label_prefix="")))
        assert not text.startswith(";")

    def test_beebasm_emits_header_block(self):
        text = str(self._with_header().disassemble().render(
            BeebasmRenderer(boundary_label_prefix="")))
        head = text.splitlines()[:4]
        assert head == [
            "; Acorn BBC BASIC II",
            ";",
            "; Line one.",
            "; md5 2cc6; sha256 45bd.",
        ]

    def test_description_line_breaks_preserved(self):
        # Provenance is line-oriented — a single newline is NOT reflowed.
        text = str(self._with_header().disassemble().render(
            BeebasmRenderer(boundary_label_prefix="")))
        assert "; Line one." in text
        assert "; md5 2cc6; sha256 45bd." in text

    def test_tass64_uses_same_prose_own_prefix(self):
        # Agnostic: identical text, each backend's own comment prefix
        # (both happen to be ``;`` here) — the point is dasmos hardcodes
        # no provenance.
        text = str(self._with_header().disassemble().render(Tass64Renderer()))
        assert text.startswith("; Acorn BBC BASIC II")

    def test_json_meta_carries_header(self):
        meta = self._with_header().disassemble().render(JsonRenderer()).data["meta"]
        assert meta["title"] == "Acorn BBC BASIC II"
        assert meta["description"] == "Line one.\nmd5 2cc6; sha256 45bd."

    def test_json_meta_omits_header_when_unset(self):
        meta = _mk().disassemble().render(JsonRenderer()).data["meta"]
        assert "title" not in meta and "description" not in meta

    def test_title_only(self):
        d = _mk()
        d.set_file_header(title="Just a title")
        text = str(d.disassemble().render(BeebasmRenderer(boundary_label_prefix="")))
        assert text.startswith("; Just a title")

    def test_set_after_disassemble_raises(self):
        d = _mk()
        d.disassemble()
        with pytest.raises(Exception):
            d.set_file_header(title="too late")


# ---------------------------------------------------------------------------
# Build instructions (#41)
# ---------------------------------------------------------------------------

class TestBuildInstructions:
    def test_off_by_default(self):
        text = str(_mk().disassemble().render(
            BeebasmRenderer(boundary_label_prefix="")))
        assert "Assemble with" not in text

    def test_beebasm_command_with_save_directive(self):
        # output_filename set → the save directive names the output, so
        # ``beebasm -i <listing>`` suffices (no -o, and never -do).
        r = BeebasmRenderer(boundary_label_prefix="",
                            include_build_instructions=True,
                            listing_filename="basic-2.asm")
        r.set_output_filename("basic-2.rom")
        text = str(_mk().disassemble().render(r))
        assert "; Assemble with beebasm:" in text
        assert ";   beebasm -i basic-2.asm" in text
        assert "-do" not in text

    def test_beebasm_command_without_save_filename_uses_o(self):
        r = BeebasmRenderer(boundary_label_prefix="",
                            include_build_instructions=True,
                            listing_filename="out.asm")
        text = str(_mk().disassemble().render(r))
        assert ";   beebasm -i out.asm -o <output.bin>" in text

    def test_tass64_command(self):
        r = Tass64Renderer(include_build_instructions=True,
                           listing_filename="basic-2.s")
        r.set_output_filename("basic-2.rom")
        text = str(_mk().disassemble().render(r))
        assert "; Assemble with 64tass:" in text
        assert ";   64tass --nostart -o basic-2.rom basic-2.s" in text

    def test_placeholder_when_listing_name_absent(self):
        r = Tass64Renderer(include_build_instructions=True)
        text = str(_mk().disassemble().render(r))
        assert "<listing>.asm" in text


# ---------------------------------------------------------------------------
# Round-trip: the preamble is comments only, so bytes are unaffected
# ---------------------------------------------------------------------------

_BEEBASM = os.environ.get("BEEBASM") or shutil.which("beebasm")


@pytest.mark.beebasm
def test_preamble_is_round_trip_safe():
    binary = bytes([0xA9, 0x42, 0x60])   # lda #&42 : rts
    d = _mk(binary)
    d.entry(0x2000, name="start")
    d.set_file_header(title="Test ROM", description="Provenance.\nmd5 abc.")
    r = BeebasmRenderer(include_build_instructions=True,
                        listing_filename="t.asm")
    r.set_output_filename("t.bin")
    text = str(d.disassemble().render(r))
    tmp = Path(tempfile.mkdtemp())
    (tmp / "t.asm").write_text(text)
    subprocess.run([_BEEBASM, "-i", str(tmp / "t.asm")],
                   capture_output=True, text=True, cwd=tmp)
    assert (tmp / "t.bin").exists()
    assert (tmp / "t.bin").read_bytes() == binary
