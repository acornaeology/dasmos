"""Labels belong to the move they were declared for (#53).

Several moves can share one run range: alternative overlays of the same
RAM (the Dunjunz loader's keyboard and joystick images of &0400-&07FF,
ADFS's three NMI handlers at &0D0A). A label declared with ``move=M``
(or inside ``with M:``) names the run address *as M lays it out*, so it
must be rendered in M's section and not in another overlay's, and code
inside M that refers to the address should use M's name. Labels that
auto-labelling creates for references made by M's code belong to M too.

A label declared without a move at a shared address still belongs to no
particular overlay and is emitted once, in the first section that
reaches it (D-023).
"""

import os
import shutil
import subprocess

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


def _find(var, name):
    env = os.environ.get(var)
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which(name)


BEEBASM = _find("BEEBASM", "beebasm")
TASS64 = _find("TASS64", "64tass")

# Two 0x40-byte overlays of run range &0400-&043F, stored at &2000
# (keyboard) and &2040 (joystick), each with a handler at run &0420:
#   keyboard: LDA #2 ; JMP &0420
#   joystick: LDA #1 ; BNE &0425 ; NOP ; &0425: JMP &0420
KEYBOARD = bytes(0x20) + bytes([0xA9, 0x02, 0x4C, 0x20, 0x04])
KEYBOARD += bytes(0x40 - len(KEYBOARD))
JOYSTICK = bytes(0x20) + bytes([0xA9, 0x01, 0xD0, 0x01, 0xEA, 0x4C, 0x20, 0x04])
JOYSTICK += bytes(0x40 - len(JOYSTICK))
IMAGE = KEYBOARD + JOYSTICK + bytes([0x60])     # &2080: RTS (main code)


def _ir(tmp_path, *, labels=True, shared_label=False):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(IMAGE)
    d = Disassembler.create("6502")
    d.load(binpath, 0x2000)
    keyboard = d.add_move(0x0400, 0x2000, 0x40, name="low_keyboard")
    joystick = d.add_move(0x0400, 0x2040, 0x40, name="low_joystick")
    d.entry(0x2080)
    with keyboard:
        d.entry(0x0420)
    with joystick:
        d.entry(0x0420)
    if labels:
        d.label(0x0420, "keyboard_handler", move=keyboard)
        d.label(0x0420, "joystick_handler", move=joystick)
    if shared_label:
        d.label(0x0400, "low_block")
    return d.disassemble()


def _sections(text):
    """Map ``"Move N"`` (and ``None`` for main code) to its lines."""
    sections: dict = {None: []}
    current = None
    for ln in text.splitlines():
        if ln.startswith("; Move "):
            current = ln[2:].split(":")[0]
            sections.setdefault(current, [])
        elif ln.strip().startswith("org &2000 + (*"):
            sections[current].append(ln.strip())
            current = None
            continue
        sections[current].append(ln.strip())
    return sections


class TestBeebasmSections:

    def test_each_label_renders_in_its_own_move(self, tmp_path):
        s = _sections(str(_ir(tmp_path).render(BeebasmRenderer())))
        assert ".keyboard_handler" in s["Move 1"]
        assert ".joystick_handler" in s["Move 2"]
        assert ".joystick_handler" not in s["Move 1"]
        assert ".keyboard_handler" not in s["Move 2"]

    def test_references_inside_a_move_use_its_own_name(self, tmp_path):
        s = _sections(str(_ir(tmp_path).render(BeebasmRenderer())))
        assert "jmp keyboard_handler" in s["Move 1"]
        assert "jmp joystick_handler" in s["Move 2"]

    def test_auto_label_belongs_to_the_referencing_move(self, tmp_path):
        # The BNE target exists only in the joystick overlay: it is
        # anchored there, inline, and named as code.
        s = _sections(str(_ir(tmp_path).render(BeebasmRenderer())))
        assert ".code_0425" in s["Move 2"]
        assert not any("code_0425" in ln for ln in s["Move 1"])
        assert "bne code_0425" in s["Move 2"]

    def test_auto_label_belongs_to_its_move_without_explicit_labels(
        self, tmp_path,
    ):
        s = _sections(str(_ir(tmp_path, labels=False).render(BeebasmRenderer())))
        assert ".code_0425" in s["Move 2"]
        assert not any("0425" in ln for ln in s["Move 1"])

    def test_label_without_a_move_is_emitted_once(self, tmp_path):
        text = str(_ir(tmp_path, shared_label=True).render(BeebasmRenderer()))
        assert [ln.strip() for ln in text.splitlines()].count(".low_block") == 1


class TestJson:

    def test_items_carry_their_own_moves_labels(self, tmp_path):
        items = _ir(tmp_path).render(JsonRenderer()).data["items"]
        at_0420 = {
            it["binary_addr"]: it.get("labels", [])
            for it in items if it["addr"] == 0x0420
        }
        assert at_0420 == {
            0x2020: ["keyboard_handler"],
            0x2060: ["joystick_handler"],
        }


@pytest.mark.beebasm
@pytest.mark.parametrize("labels", [True, False], ids=["labels", "no-labels"])
def test_beebasm_round_trip(tmp_path, labels):
    text = str(_ir(tmp_path, labels=labels).render(BeebasmRenderer()))
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


@pytest.mark.tass64
@pytest.mark.parametrize("labels", [True, False], ids=["labels", "no-labels"])
def test_tass64_round_trip(tmp_path, labels):
    text = str(_ir(tmp_path, labels=labels).render(Tass64Renderer()))
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
    assert out_path.read_bytes() == IMAGE
