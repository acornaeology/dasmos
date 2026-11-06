"""Byte-level driver methods accept a ``BinaryAddr`` (#52).

Driver methods take *runtime* addresses and resolve them to the stored
byte through the moves. Code that already holds a binary address — the
post-trace analysers, hooks — used to pass it in as if it were a
runtime address. That only works by accident: when a move's run range
overlaps its stored range, the binary address is *also* a runtime
address inside the move and resolves to a different byte. In the
Dunjunz case, the ``acorn_mos`` OSBYTE names for ``lda #&0f`` /
``lda #&ca`` landed on unrelated data bytes.

Methods that describe *bytes* (``expr``, ``byte``, ``comment``, …) now
accept a ``BinaryAddr``, meaning "exactly this stored byte", with no
move resolution. Methods that *name addresses* (labels, entries) stay
runtime-only.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.core.annotations import Align
from dasmos.core.memory import BinaryAddr
from dasmos.disassembler import Disassembler, DisassemblerError
from dasmos.ext.renderers.beebasm import BeebasmRenderer


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("beebasm")


BEEBASM = _find_beebasm()


# Stored &0500-&06FF, run &0400-&05FF: the move's stored and run ranges
# overlap, so binary &0501 is also runtime &0501 — which is the byte
# stored at binary &0601. The moved code at runtime &0400 is
#   LDA #&0F ; LDX #&01 ; JSR osbyte ; RTS
# followed by distinct data bytes; a trailing RTS at &0700 stays put.
MOVED_CODE = bytes([0xA9, 0x0F, 0xA2, 0x01, 0x20, 0xF4, 0xFF, 0x60])
IMAGE = (
    MOVED_CODE
    + bytes((i * 7 + 1) & 0xFF for i in range(0x200 - len(MOVED_CODE)))
    + bytes([0x60])
)


def _disassembler(tmp_path, environments=()):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(IMAGE)
    d = Disassembler.create("6502", environments=list(environments))
    d.load(binpath, 0x0500)
    move = d.add_move(0x0400, 0x0500, 0x200)
    d.entry(0x0400, "moved_code", move=move)
    d.entry(0x0700)
    return d, move


class TestBinaryAddrResolution:

    def test_expr_at_binary_addr_is_not_resolved_through_moves(self, tmp_path):
        d, _ = _disassembler(tmp_path)
        d.expr(BinaryAddr(0x0501), "15")
        assert d.expressions.get_or_none(0x0501) is not None
        assert d.expressions.get_or_none(0x0601) is None

    def test_runtime_addr_still_resolves_through_moves(self, tmp_path):
        # The same number as a plain int is a runtime address: &0501
        # runs at the stored byte &0601.
        d, _ = _disassembler(tmp_path)
        d.expr(0x0501, "15")
        assert d.expressions.get_or_none(0x0601) is not None
        assert d.expressions.get_or_none(0x0501) is None

    def test_comment_at_binary_addr(self, tmp_path):
        d, _ = _disassembler(tmp_path)
        d.comment(BinaryAddr(0x0502), "here", align=Align.INLINE)
        assert any(
            getattr(a, "text", None) == "here"
            for a in d.annotations.get_for_align(0x0502, Align.INLINE)
        )

    def test_byte_at_binary_addr(self, tmp_path):
        d, _ = _disassembler(tmp_path)
        d.byte(BinaryAddr(0x0650), 2)
        assert d.classifications.get_classification(0x0650).length() == 2

    def test_binary_addr_with_move_is_rejected(self, tmp_path):
        d, move = _disassembler(tmp_path)
        with pytest.raises(DisassemblerError, match="BinaryAddr"):
            d.expr(BinaryAddr(0x0501), "15", move=move)


class TestEnvironmentOperandNames:

    def _text(self, tmp_path):
        d, _ = _disassembler(tmp_path, environments=["acorn_mos"])
        return str(d.disassemble().render(BeebasmRenderer()))

    def test_osbyte_name_lands_on_the_instruction(self, tmp_path):
        lines = [ln.strip() for ln in self._text(tmp_path).splitlines()]
        assert any(
            ln.startswith("lda #osbyte_flush_buffer_class") for ln in lines
        ), lines

    def test_osbyte_name_does_not_land_on_unrelated_data(self, tmp_path):
        data_lines = [
            ln for ln in self._text(tmp_path).splitlines()
            if ln.strip().startswith("equb")
        ]
        assert not any("osbyte" in ln for ln in data_lines), data_lines


@pytest.mark.beebasm
def test_overlapping_move_with_environment_round_trips(tmp_path):
    d, _ = _disassembler(tmp_path, environments=["acorn_mos"])
    text = str(d.disassemble().render(BeebasmRenderer()))
    asm_path = tmp_path / "out.asm"
    asm_path.write_text(text, encoding="utf-8")
    out_path = tmp_path / "out.bin"
    result = subprocess.run(
        [BEEBASM, "-i", str(asm_path), "-o", str(out_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"beebasm failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    assert out_path.read_bytes() == IMAGE
