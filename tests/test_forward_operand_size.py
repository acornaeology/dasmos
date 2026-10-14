"""Operand size of instructions that forward-reference their label (#48).

When an instruction's mnemonic has both a zero-page and an absolute
form, its size depends on the operand's value. If that operand is a
label defined *later* in the listing, the assembler must guess the size
on its first pass, and the guess can settle into a self-consistent but
wrong layout (the guessed size moves the label to the matching side of
``&100``), silently:

- 64tass assumes an undefined symbol is 16-bit, so a zero-page
  instruction referencing a later label near the top of zero page can
  come out absolute (``lda data_00ff`` -> ``ad 00 01``);
- beebasm substitutes the instruction's own address, so an absolute
  instruction running in zero page that references a later label just
  above ``&100`` can come out zero-page (``a5 ff``).

The renderer pins the size exactly when the assembler's first-pass
guess disagrees with the encoded size: 64tass ``@b`` / ``@w``; beebasm
as data (it has no size-forcing syntax). Ordinary code, where the guess
already matches, renders unchanged.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("beebasm")


def _find_tass64() -> str | None:
    env = os.environ.get("TASS64")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("64tass")


BEEBASM = _find_beebasm()
TASS64 = _find_tass64()


def _build(tmp_path, image, load_addr, configure):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(image)
    d = Disassembler.create("6502")
    d.load(binpath, load_addr)
    configure(d)
    return d.disassemble()


def _code_lines(text):
    return [ln.strip() for ln in text.splitlines() if ln.startswith("    ")]


def _beebasm(tmp_path, text):
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
    return out_path.read_bytes()


def _tass64(tmp_path, text):
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
    return out_path.read_bytes()


# -- the scenarios ------------------------------------------------------

# #48: &00F0 LDA &FF (zero page, forward ref) ; RTS ; pad ; &00FF data.
ZP_FORWARD_NEAR_TOP = bytes([0xA5, 0xFF, 0x60]) + bytes(12) + bytes([0x11])


def _zp_forward_near_top(d):
    d.entry(0x00F0)
    d.byte(0x00FF, 1)


# Mirror: &00F0 LDA &0100 (absolute, forward ref) ; RTS ; pad ; &0100 data.
ABS_FORWARD_FROM_ZP = bytes([0xAD, 0x00, 0x01, 0x60]) + bytes(12) + bytes([0x11])


def _abs_forward_from_zp(d):
    d.entry(0x00F0)
    d.byte(0x0100, 1)


# Zero-page forward ref from code above &100: move A (&2000 -> &9000)
# is LDA &80 then a labelled RTS; move B (&2004 -> &0080) defines the
# zero-page label later in the listing. beebasm's first pass assembles
# the LDA absolute, shifting ``later``, and it rejects the listing.
CROSS_MOVE = bytes([0xA5, 0x80, 0x60, 0xEA, 0xEA, 0x60])


def _cross_move(d):
    a = d.add_move(0x9000, 0x2000, 3)
    b = d.add_move(0x0080, 0x2003, 3)
    d.entry(0x9000, move=a)
    d.entry(0x9002, "later", move=a)
    d.entry(0x0080, "zp_code", move=b)


# Ordinary ROM-style code: forward reference to a table above &100.
ORDINARY_FORWARD = bytes([0xBD, 0x04, 0x20, 0x60, 0x11, 0x22])


def _ordinary_forward(d):
    d.entry(0x2000)
    d.byte(0x2004, 2)


# Zero-page forward reference well inside zero page.
ZP_FORWARD_LOW = bytes([0xA5, 0x60, 0x60]) + bytes(13) + bytes([0x11])


def _zp_forward_low(d):
    d.entry(0x0050)
    d.byte(0x0060, 1)


# Zero-page backward reference: the label is defined before its use.
ZP_BACKWARD = bytes([0x11]) + bytes(15) + bytes([0xA5, 0x50, 0x60])


def _zp_backward(d):
    d.byte(0x0050, 1)
    d.entry(0x0060)


class TestTass64Pinning:

    def test_zero_page_forward_reference_is_pinned_with_b(self, tmp_path):
        ir = _build(tmp_path, ZP_FORWARD_NEAR_TOP, 0x00F0, _zp_forward_near_top)
        assert "lda @b data_00ff" in _code_lines(str(ir.render(Tass64Renderer())))

    def test_backward_zero_page_reference_is_not_pinned(self, tmp_path):
        ir = _build(tmp_path, ZP_BACKWARD, 0x0050, _zp_backward)
        assert "lda data_0050" in _code_lines(str(ir.render(Tass64Renderer())))

    def test_absolute_forward_reference_is_not_pinned(self, tmp_path):
        # 64tass assumes 16-bit for an undefined symbol: already right.
        ir = _build(tmp_path, ABS_FORWARD_FROM_ZP, 0x00F0, _abs_forward_from_zp)
        assert "lda data_0100" in _code_lines(str(ir.render(Tass64Renderer())))

    def test_ordinary_forward_table_reference_is_not_pinned(self, tmp_path):
        ir = _build(tmp_path, ORDINARY_FORWARD, 0x2000, _ordinary_forward)
        assert "lda data_2004,x" in _code_lines(str(ir.render(Tass64Renderer())))


class TestBeebasmPinning:

    def test_absolute_forward_reference_from_zero_page_is_data(self, tmp_path):
        ir = _build(tmp_path, ABS_FORWARD_FROM_ZP, 0x00F0, _abs_forward_from_zp)
        lines = _code_lines(str(ir.render(BeebasmRenderer())))
        assert any(
            ln.startswith("equb &ad : equw data_0100") for ln in lines
        ), lines

    def test_zero_page_forward_reference_from_high_code_is_data(self, tmp_path):
        ir = _build(tmp_path, CROSS_MOVE, 0x2000, _cross_move)
        lines = _code_lines(str(ir.render(BeebasmRenderer())))
        forced = [ln for ln in lines if ln.startswith("equb &a5, zp_code")]
        assert forced, lines
        assert "lda zp_code (zero page)" in forced[0]

    def test_zero_page_forward_reference_from_zero_page_is_not_pinned(
        self, tmp_path,
    ):
        # beebasm guesses zero page for code below &100: already right.
        ir = _build(tmp_path, ZP_FORWARD_NEAR_TOP, 0x00F0, _zp_forward_near_top)
        assert "lda data_00ff" in _code_lines(str(ir.render(BeebasmRenderer())))

    def test_ordinary_forward_table_reference_is_not_pinned(self, tmp_path):
        ir = _build(tmp_path, ORDINARY_FORWARD, 0x2000, _ordinary_forward)
        text = str(ir.render(BeebasmRenderer()))
        assert "lda data_2004,x" in _code_lines(text)


@pytest.mark.tass64
class TestTass64RoundTrip:

    @pytest.mark.parametrize("image, load_addr, configure", [
        (ZP_FORWARD_NEAR_TOP, 0x00F0, _zp_forward_near_top),
        (ABS_FORWARD_FROM_ZP, 0x00F0, _abs_forward_from_zp),
        (CROSS_MOVE, 0x2000, _cross_move),
        (ORDINARY_FORWARD, 0x2000, _ordinary_forward),
        (ZP_FORWARD_LOW, 0x0050, _zp_forward_low),
        (ZP_BACKWARD, 0x0050, _zp_backward),
    ], ids=["zp-fwd-near-top", "abs-fwd-from-zp", "cross-move",
            "ordinary", "zp-fwd-low", "zp-backward"])
    def test_round_trips(self, tmp_path, image, load_addr, configure):
        ir = _build(tmp_path, image, load_addr, configure)
        assert _tass64(tmp_path, str(ir.render(Tass64Renderer()))) == image


@pytest.mark.beebasm
class TestBeebasmRoundTrip:

    @pytest.mark.parametrize("image, load_addr, configure", [
        (ZP_FORWARD_NEAR_TOP, 0x00F0, _zp_forward_near_top),
        (ABS_FORWARD_FROM_ZP, 0x00F0, _abs_forward_from_zp),
        (CROSS_MOVE, 0x2000, _cross_move),
        (ORDINARY_FORWARD, 0x2000, _ordinary_forward),
        (ZP_FORWARD_LOW, 0x0050, _zp_forward_low),
        (ZP_BACKWARD, 0x0050, _zp_backward),
    ], ids=["zp-fwd-near-top", "abs-fwd-from-zp", "cross-move",
            "ordinary", "zp-fwd-low", "zp-backward"])
    def test_round_trips(self, tmp_path, image, load_addr, configure):
        ir = _build(tmp_path, image, load_addr, configure)
        assert _beebasm(tmp_path, str(ir.render(BeebasmRenderer()))) == image
