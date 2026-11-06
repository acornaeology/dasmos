"""Labels that fall inside another item, and the bases they hang off (#50).

A label in the middle of a classification is rendered as an offset of
the classification's start (``name = base+N``), so the start needs a
name. Two things went wrong:

- The leftover pass ends a ``Byte`` run at every labelled address so the
  label gets a fresh line — but it runs before auto-labelling, so a data
  label created *by* auto-labelling (``LDA &0410`` into unclassified
  bytes) landed mid-run and was expressed as an offset instead.
- The synthesised base was always given the subroutine prefix
  (``sub_0404``), even at the start of a data run nobody calls.

Now leftover runs are split at labels added by auto-labelling, so such
labels get their own line, and a base that is still needed (a label
inside an instruction, or inside data the driver declared) is named by
the same rules as any other auto-label at that address.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("beebasm")


BEEBASM = _find_beebasm()

# &0400 LDA &0410 ; &0403 RTS ; &0404-&041F unclassified data.
LOAD_INTO_LEFTOVERS = bytes([0xAD, 0x10, 0x04, 0x60]) + bytes(range(1, 29))

# &0400 LDA &1234 ; &0403 STA &0401 (self-modifies the LDA operand) ; RTS
SELF_MODIFYING = bytes([0xAD, 0x34, 0x12, 0x8D, 0x01, 0x04, 0x60])


def _render(tmp_path, image, configure):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(image)
    d = Disassembler.create("6502")
    d.load(binpath, 0x0400)
    d.entry(0x0400)
    configure(d)
    return str(d.disassemble().render(BeebasmRenderer()))


def _lines(text):
    return [ln.strip() for ln in text.splitlines()]


class TestAutoLabelsInLeftoverData:

    def test_label_gets_its_own_line(self, tmp_path):
        lines = _lines(_render(tmp_path, LOAD_INTO_LEFTOVERS, lambda d: None))
        assert ".data_0410" in lines
        assert not any(ln.startswith("data_0410 =") for ln in lines)

    def test_no_base_is_synthesised(self, tmp_path):
        text = _render(tmp_path, LOAD_INTO_LEFTOVERS, lambda d: None)
        assert "sub_0404" not in text
        assert "data_0404" not in text


class TestBaseNaming:

    def test_base_of_driver_declared_data_uses_data_prefix(self, tmp_path):
        # The driver's own grouping of the data is kept, so the label
        # stays an offset — of a base named as data, not a subroutine.
        text = _render(
            tmp_path, LOAD_INTO_LEFTOVERS, lambda d: d.byte(0x0404, 28),
        )
        lines = _lines(text)
        assert ".data_0404" in lines
        assert "data_0410 = data_0404+12" in lines
        assert "sub_0404" not in text

    def test_base_of_instruction_uses_code_prefix(self, tmp_path):
        # &0401 is a label inside the LDA (its operand is written by the
        # STA); the LDA itself is never called, so it isn't a sub_.
        lines = _lines(_render(tmp_path, SELF_MODIFYING, lambda d: None))
        assert ".code_0400" in lines
        assert "data_0401 = code_0400+1" in lines


@pytest.mark.beebasm
@pytest.mark.parametrize("image, configure", [
    (LOAD_INTO_LEFTOVERS, lambda d: None),
    (LOAD_INTO_LEFTOVERS, lambda d: d.byte(0x0404, 28)),
    (SELF_MODIFYING, lambda d: None),
], ids=["leftover-data", "declared-data", "self-modifying"])
def test_round_trips(tmp_path, image, configure):
    text = _render(tmp_path, image, configure)
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
    assert out_path.read_bytes() == image
