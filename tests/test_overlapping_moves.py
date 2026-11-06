"""Moves whose stored (source) and run (destination) ranges overlap (#51).

beebasm assembles a move's body at its run address, then ``copyblock``
copies the bytes back to the stored range and ``clear`` frees the
scratch run range for reuse. ``CLEAR`` *zeroes* memory, so when the two
ranges overlap it must not touch the part of the run range that now
holds the stored copy — otherwise those bytes reassemble as zeros.
(``copyblock`` itself copies overlapping ranges safely.)

64tass relocates with ``.logical`` / ``.here`` and needs no copy-back;
its round trip is checked here as a guard.
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


def _moved_code(length):
    """``length`` bytes of code for the moved block: LDA #n ; STA &70 ;
    RTS, then distinct data bytes so a zeroed byte can't go unnoticed."""
    code = bytes([0xA9, 0x2A, 0x85, 0x70, 0x60])
    return code + bytes((i * 7 + 1) & 0xFF for i in range(length - len(code)))


# Run range below the stored range, overlapping it (the Dunjunz crack's
# shape): stored &0500-&06FF, run &0400-&05FF; a trailing RTS at &0700
# stays in place.
DEST_BELOW = dict(
    image=_moved_code(0x200) + bytes([0x60]),
    load_addr=0x0500, dest=0x0400, src=0x0500, length=0x200,
)

# Run range above the stored range, overlapping it: stored &0400-&05FF,
# run &0500-&06FF.
DEST_ABOVE = dict(
    image=_moved_code(0x200) + bytes([0x60]),
    load_addr=0x0400, dest=0x0500, src=0x0400, length=0x200,
)

SCENARIOS = [
    pytest.param(DEST_BELOW, id="run-range-below-stored"),
    pytest.param(DEST_ABOVE, id="run-range-above-stored"),
]


def _ir(tmp_path, s):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(s["image"])
    d = Disassembler.create("6502")
    d.load(binpath, s["load_addr"])
    move = d.add_move(s["dest"], s["src"], s["length"])
    d.entry(s["dest"], "moved_code", move=move)
    d.entry(s["load_addr"] + len(s["image"]) - 1)
    return d.disassemble()


def _clear_lines(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip().startswith("clear")]


class TestClearRange:

    def test_run_range_below_clears_only_below_the_stored_copy(self, tmp_path):
        # run &0400-&05FF minus stored &0500-&06FF leaves &0400-&04FF.
        text = str(_ir(tmp_path, DEST_BELOW).render(BeebasmRenderer()))
        assert _clear_lines(text) == ["clear moved_code, &0500"]

    def test_run_range_above_clears_only_above_the_stored_copy(self, tmp_path):
        # run &0500-&06FF minus stored &0400-&05FF leaves &0600-&06FF.
        text = str(_ir(tmp_path, DEST_ABOVE).render(BeebasmRenderer()))
        assert _clear_lines(text) == ["clear &0600, &0700"]

    @pytest.mark.parametrize("dest, src, expected", [
        (0x0400, 0x0500, (0x0400, 0x0500)),   # run range below, overlapping
        (0x0500, 0x0400, (0x0600, 0x0700)),   # run range above, overlapping
        (0x3000, 0x0500, (0x3000, 0x3200)),   # disjoint
        (0x0400, 0x0600, (0x0400, 0x0600)),   # adjacent: no overlap
        (0x0500, 0x0500, None),               # coincident: nothing to clear
    ])
    def test_scratch_range(self, dest, src, expected):
        assert BeebasmRenderer._scratch_range_to_clear(dest, src, 0x200) == expected

    def test_disjoint_move_still_clears_the_whole_run_range(self, tmp_path):
        s = dict(DEST_BELOW, dest=0x3000)
        text = str(_ir(tmp_path, s).render(BeebasmRenderer()))
        assert _clear_lines(text) == ["clear moved_code, &3200"]


@pytest.mark.beebasm
class TestBeebasmRoundTrip:

    @pytest.mark.parametrize("s", SCENARIOS)
    def test_round_trips(self, tmp_path, s):
        text = str(_ir(tmp_path, s).render(BeebasmRenderer()))
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
        assert out_path.read_bytes() == s["image"]


@pytest.mark.tass64
class TestTass64RoundTrip:

    @pytest.mark.parametrize("s", SCENARIOS)
    def test_round_trips(self, tmp_path, s):
        text = str(_ir(tmp_path, s).render(Tass64Renderer()))
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
        assert out_path.read_bytes() == s["image"]
