"""Falling off the end of a move continues at the run address (#55).

When the last instruction of a moved block doesn't jump or return,
execution at run time continues at the *run* address just past the move
(``dest + length``) — in place, or inside another move. The trace used
to continue at the *stored* address just past the move's source
(``src + length``), decoding whatever follows it there (often zeros, as
``brk``) and missing the real continuation.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.cpu import Opcode
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _find(var, name):
    env = os.environ.get(var)
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which(name)


BEEBASM = _find("BEEBASM", "beebasm")
TASS64 = _find("TASS64", "64tass")


def _image(moved_code, *, extra=None):
    """A 0x30-byte image loaded at &2000:

    - &2000: ADC #1 ; RTS — runs in place;
    - &2010: ``moved_code`` (4 bytes), stored here, run at &1FFC-&1FFF,
      so falling off its end continues at run &2000;
    - &2014..: zeros, the stored bytes after the move's source;
    - ``extra``: ``{offset: bytes}`` to place elsewhere.
    """
    img = bytearray(0x30)
    img[0x00:0x03] = bytes([0x69, 0x01, 0x60])
    img[0x10:0x14] = moved_code
    for offset, data in (extra or {}).items():
        img[offset:offset + len(data)] = data
    return bytes(img)


FALLS_INTO_PLACE = _image(bytes([0x18, 0xEA, 0xEA, 0xEA]))   # CLC ; NOP x3
BRANCH_AT_END = _image(bytes([0x18, 0xEA, 0xD0, 0x02]))      # CLC ; NOP ; BNE &2002


def _disassemble(tmp_path, image, configure=None):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(image)
    d = Disassembler.create("6502")
    d.load(binpath, 0x2000)
    move = d.add_move(0x1FFC, 0x2010, 4, name="tail")
    with move:
        d.entry(0x1FFC)
    if configure is not None:
        configure(d)
    return d.disassemble()


def _code_at(ir, binary_addr):
    c = ir.classifications.get_classification(binary_addr)
    return c.default_mnemonic() if isinstance(c, Opcode) else None


class TestTrace:

    def test_continues_at_the_run_address_past_the_move(self, tmp_path):
        ir = _disassemble(tmp_path, FALLS_INTO_PLACE)
        assert _code_at(ir, 0x2000) == "adc"

    def test_does_not_decode_the_stored_bytes_after_the_source(self, tmp_path):
        ir = _disassemble(tmp_path, FALLS_INTO_PLACE)
        assert _code_at(ir, 0x2014) is None

    def test_conditional_branch_falls_through_to_the_run_address(self, tmp_path):
        ir = _disassemble(tmp_path, BRANCH_AT_END)
        assert _code_at(ir, 0x2000) == "adc"
        assert _code_at(ir, 0x2014) is None

    def test_falls_through_into_another_move(self, tmp_path):
        # Run &2000 is itself relocated: stored at &2020 (LDX #2 ; RTS).
        image = _image(
            bytes([0x18, 0xEA, 0xEA, 0xEA]),
            extra={0x20: bytes([0xA2, 0x02, 0x60])},
        )

        def configure(d):
            d.add_move(0x2000, 0x2020, 3, name="next")

        ir = _disassemble(tmp_path, image, configure)
        assert _code_at(ir, 0x2020) == "ldx"
        assert _code_at(ir, 0x2014) is None

    def test_within_a_move_falls_through_in_the_move(self, tmp_path):
        ir = _disassemble(tmp_path, FALLS_INTO_PLACE)
        assert [_code_at(ir, 0x2010 + i) for i in range(4)] == [
            "clc", "nop", "nop", "nop",
        ]


@pytest.mark.beebasm
def test_beebasm_round_trip(tmp_path):
    text = str(_disassemble(tmp_path, FALLS_INTO_PLACE).render(BeebasmRenderer()))
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
    assert out_path.read_bytes() == FALLS_INTO_PLACE


@pytest.mark.tass64
def test_tass64_round_trip(tmp_path):
    text = str(_disassemble(tmp_path, FALLS_INTO_PLACE).render(Tass64Renderer()))
    asm_path = tmp_path / "out.asm"
    asm_path.write_text(text, encoding="utf-8")
    out_path = tmp_path / "out.bin"
    result = subprocess.run(
        [TASS64, "--nostart", "-q", "-o", str(out_path), str(asm_path)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, (
        f"64tass failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    assert out_path.read_bytes() == FALLS_INTO_PLACE


class TestInPlaceExecutionOfMovedBytes:
    """A ROM can also run moved bytes *in place*, at their stored
    addresses — ANFS's initialisation routine is both the tail of a
    relocated page's source and the code that performs the copy. A trace
    path runs in the layout it was reached through: via the move's run
    address it is relocated; via the stored (ROM) address it is in place,
    with in-place branch targets and fall-through."""

    # Stored &2010, run at &1FFC:  BNE +2 ; NOP ; NOP
    #   relocated: &1FFC BNE -> run &2000 (ADC #1 ; RTS, in place)
    #   in place:  &2010 BNE -> &2014    (LDX #5 ; RTS, after the source)
    IMAGE = _image(
        bytes([0xD0, 0x02, 0xEA, 0xEA]),
        extra={0x14: bytes([0xA2, 0x05, 0x60])},
    )

    def _ir(self, tmp_path, *, in_place):
        binpath = tmp_path / "in.bin"
        binpath.write_bytes(self.IMAGE)
        d = Disassembler.create("6502")
        d.load(binpath, 0x2000)
        move = d.add_move(0x1FFC, 0x2010, 4, name="tail")
        if in_place:
            d.entry(0x2010)            # the ROM address: runs in place
        else:
            with move:
                d.entry(0x1FFC)        # the run address: relocated
        return d.disassemble()

    def test_relocated_path_branches_in_run_space(self, tmp_path):
        ir = self._ir(tmp_path, in_place=False)
        assert _code_at(ir, 0x2000) == "adc"
        assert _code_at(ir, 0x2014) is None

    def test_in_place_path_branches_and_falls_through_in_place(self, tmp_path):
        ir = self._ir(tmp_path, in_place=True)
        assert _code_at(ir, 0x2014) == "ldx"
        assert _code_at(ir, 0x2000) is None

    def test_relocated_code_jumping_to_its_own_stored_address_runs_in_place(
        self, tmp_path,
    ):
        # Relocated JMP &2013 (a ROM address inside its own source, the
        # NOP): the rest runs in place, falling through to &2014.
        image = _image(
            bytes([0x4C, 0x13, 0x20, 0xEA]),
            extra={0x14: bytes([0xA2, 0x05, 0x60])},
        )
        binpath = tmp_path / "in.bin"
        binpath.write_bytes(image)
        d = Disassembler.create("6502")
        d.load(binpath, 0x2000)
        move = d.add_move(0x1FFC, 0x2010, 4, name="tail")
        with move:
            d.entry(0x1FFC)
        ir = d.disassemble()
        assert _code_at(ir, 0x2014) == "ldx"
