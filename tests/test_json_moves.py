"""The JSON says which move each piece of the listing belongs to (#56).

With moves, several pieces of code can share one run address (overlays),
and an item's stored address can equal another item's run address.
Consumers (the acornaeology site generator) need to tell the copies
apart: to anchor each row uniquely and to point links and come-from
references at the right copy. The JSON names each move — its name is its
public identifier — and tags what lives in it:

- ``meta.moves``: every move in declaration order;
- ``move`` on each item, subroutine and banner stored in a move;
- ``move`` on each reference made from code stored in a move;
- ``target_move`` on an operand whose target resolves into a move.
"""

import pytest

from dasmos.core.move import MoveManager
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.json import JsonRenderer

# Image at &2000:
#   &2000 JSR &0500 ; &2003 JSR &0400 ; &2006 RTS            (in place)
#   &2040 keyboard overlay, run &0400: LDA #1 ; BNE &0405 ; NOP ; RTS
#   &2060 joystick overlay, run &0400: the same code
#   &2080 unnamed move, run &0500:     JMP &2006
OVERLAY = bytes([0xA9, 0x01, 0xD0, 0x01, 0xEA, 0x60])


def _image():
    img = bytearray(0x90)
    img[0x00:0x07] = bytes([0x20, 0x00, 0x05, 0x20, 0x00, 0x04, 0x60])
    img[0x40:0x40 + len(OVERLAY)] = OVERLAY
    img[0x60:0x60 + len(OVERLAY)] = OVERLAY
    img[0x80:0x83] = bytes([0x4C, 0x06, 0x20])
    return bytes(img)


@pytest.fixture
def data(tmp_path):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(_image())
    d = Disassembler.create("6502")
    d.load(binpath, 0x2000)
    keyboard = d.add_move(0x0400, 0x2040, 0x20, name="keyboard")
    joystick = d.add_move(0x0400, 0x2060, 0x20, name="joystick")
    d.add_move(0x0500, 0x2080, 0x10)                    # unnamed
    d.entry(0x2000)
    with keyboard:
        d.entry(0x0400)
    d.subroutine(0x0400, "joystick_entry", move=joystick)
    d.banner(0x0400, title="Keyboard handler", move=keyboard)
    return d.disassemble().render(JsonRenderer()).data


def _item(data, binary_addr):
    return next(
        it for it in data["items"]
        if it.get("binary_addr", it["addr"]) == binary_addr
    )


class TestMoveList:

    def test_meta_lists_moves_in_declaration_order(self, data):
        assert data["meta"]["moves"] == [
            {"name": "keyboard", "dest": 0x0400, "src": 0x2040, "length": 0x20},
            {"name": "joystick", "dest": 0x0400, "src": 0x2060, "length": 0x20},
            {"name": "move_3", "dest": 0x0500, "src": 0x2080, "length": 0x10},
        ]

    def test_no_moves_gives_an_empty_list(self, tmp_path):
        binpath = tmp_path / "in.bin"
        binpath.write_bytes(bytes([0x60]))
        d = Disassembler.create("6502")
        d.load(binpath, 0x2000)
        d.entry(0x2000)
        assert d.disassemble().render(JsonRenderer()).data["meta"]["moves"] == []


class TestMembership:

    def test_items_in_a_move_name_it(self, data):
        assert _item(data, 0x2040)["move"] == "keyboard"
        assert _item(data, 0x2060)["move"] == "joystick"
        assert _item(data, 0x2080)["move"] == "move_3"

    def test_unmoved_items_have_no_move(self, data):
        assert "move" not in _item(data, 0x2000)

    def test_subroutines_name_their_move(self, data):
        sub = next(s for s in data["subroutines"] if s.get("name") == "joystick_entry")
        assert sub["move"] == "joystick"

    def test_banners_name_their_move(self, data):
        banner = next(b for b in data["banners"] if b.get("title") == "Keyboard handler")
        assert banner["move"] == "keyboard"


class TestReferences:

    def test_reference_names_the_referrers_move(self, data):
        # The joystick copy's RTS at run &0405 is the BNE's target.
        refs = _item(data, 0x2065)["references"]
        assert [(r["addr"], r.get("move")) for r in refs] == [(0x0402, "joystick")]

    def test_reference_from_unmoved_code_has_no_move(self, data):
        refs = _item(data, 0x2080)["references"]
        assert [(r["addr"], r.get("move")) for r in refs] == [(0x2000, None)]


class TestTargetMove:

    def test_branch_within_an_overlay_targets_that_overlay(self, data):
        assert _item(data, 0x2042)["target_move"] == "keyboard"
        assert _item(data, 0x2062)["target_move"] == "joystick"

    def test_jump_into_the_only_move_covering_the_target(self, data):
        assert _item(data, 0x2000)["target_move"] == "move_3"

    def test_target_shared_by_overlays_is_left_unnamed(self, data):
        # From unmoved code, &0400 could be either overlay.
        assert "target_move" not in _item(data, 0x2003)

    def test_target_running_in_place_has_no_move(self, data):
        assert "target_move" not in _item(data, 0x2080)


class TestUniqueNames:

    def test_generated_name_never_repeats_an_explicit_one(self):
        moves = MoveManager()
        first = moves.add_move(0x0400, 0x2000, 0x10, name="move_2")
        second = moves.add_move(0x0500, 0x2010, 0x10)
        assert first.name == "move_2"
        assert second.name != "move_2"
