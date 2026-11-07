"""An unmoved image is one of the layouts sharing a run address (#57).

Where an image loaded in place and a move both cover a run address, the
address has two occupants: the in-place bytes and the moved ones (the
Dunjunz Master side's loaders run at &2000-&2FFF, where the game file
``Dunj5`` later loads). The in-place image is a layout like a move's:

- an annotation that names no move, outside any ``with move:`` block,
  means the in-place bytes; ``move=`` or ``with move:`` means the move's;
- a trace path prefers its own layout; otherwise moves lie over the
  in-place image, so from a move a single covering move is preferred,
  and several are ambiguous, as between overlays;
- each layout sees its own labels, as overlays do (D-028, D-029).
"""

import os
import shutil
import subprocess
import warnings

import pytest

from dasmos.core.move import BASE_MOVE_ID, MoveManager
from dasmos.cpu import Opcode
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

# GAME, loaded in place at &2000-&20FF:
#   &2000 JMP &2090
#   &2090 LDA #1 ; RTS
GAME = bytearray(0x100)
GAME[0x00:0x03] = bytes([0x4C, 0x90, 0x20])
GAME[0x90:0x93] = bytes([0xA9, 0x01, 0x60])
GAME = bytes(GAME)

# LOADER, stored at &3000-&303F, run at &2080-&20BF (inside GAME's range):
#   &2080 LDX #2 ; BNE &2090
#   &2090 LDY #3 ; RTS
LOADER = bytearray(0x40)
LOADER[0x00:0x04] = bytes([0xA2, 0x02, 0xD0, 0x0C])
LOADER[0x10:0x13] = bytes([0xA0, 0x03, 0x60])
LOADER = bytes(LOADER)


def _disassembler(tmp_path, *, game_entry=True, loader_entry=True):
    (tmp_path / "GAME").write_bytes(GAME)
    (tmp_path / "LOADER").write_bytes(LOADER)
    d = Disassembler.create("6502")
    d.load(tmp_path / "GAME", 0x2000, name="GAME")
    d.load(tmp_path / "LOADER", 0x3000, name="LOADER")
    loader = d.add_move(0x2080, 0x3000, len(LOADER), name="loader")
    if game_entry:
        d.entry(0x2000)
    if loader_entry:
        with loader:
            d.entry(0x2080)
    return d, loader


def _is_code(ir, binary_addr):
    return isinstance(ir.classifications.get_classification(binary_addr), Opcode)


class TestResolution:

    def test_layouts_at_a_shared_run_address(self):
        loaded = set(range(0x2000, 0x2100))
        moves = MoveManager(is_loaded=loaded.__contains__)
        loader = moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        assert moves.layout_ids_for_runtime_addr(0x2090) == {
            BASE_MOVE_ID, loader.move_id,
        }
        assert moves.layout_ids_for_runtime_addr(0x2010) == {BASE_MOVE_ID}

    def test_no_move_named_resolves_in_place(self):
        loaded = set(range(0x2000, 0x2100))
        moves = MoveManager(is_loaded=loaded.__contains__)
        moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        assert moves.r2b(0x2090) == (0x2090, BASE_MOVE_ID)

    def test_active_move_resolves_into_the_move(self):
        loaded = set(range(0x2000, 0x2100))
        moves = MoveManager(is_loaded=loaded.__contains__)
        loader = moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        with loader:
            assert moves.r2b(0x2090) == (0x3010, loader.move_id)

    def test_a_run_address_not_loaded_in_place_resolves_into_the_move(self):
        moves = MoveManager(is_loaded=lambda addr: False)
        loader = moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        assert moves.r2b(0x2090) == (0x3010, loader.move_id)

    def test_overlays_not_loaded_in_place_stay_ambiguous(self):
        moves = MoveManager(is_loaded=lambda addr: False)
        moves.add_move(0x0400, 0x3000, 0x40, name="one")
        moves.add_move(0x0400, 0x3040, 0x40, name="two")
        assert moves.r2b(0x0410) == (None, None)

    def test_explicit_context_replaces_the_default(self):
        loaded = set(range(0x2000, 0x2100))
        moves = MoveManager(is_loaded=loaded.__contains__)
        loader = moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        other = moves.add_move(0x5000, 0x3040, 0x10, name="other")
        assert moves.r2b(0x2090, context=[BASE_MOVE_ID]) == (0x2090, BASE_MOVE_ID)
        assert moves.r2b(0x2090, context=[loader.move_id]) == (0x3010, loader.move_id)
        # Moves lie over the in-place image: seen from another move, the
        # moved copy is the one there.
        assert moves.r2b(0x2090, context=[other.move_id]) == (0x3010, loader.move_id)

    def test_several_moves_over_the_in_place_image_are_ambiguous_elsewhere(self):
        loaded = set(range(0x2000, 0x2100))
        moves = MoveManager(is_loaded=loaded.__contains__)
        moves.add_move(0x2080, 0x3000, 0x40, name="one")
        moves.add_move(0x2080, 0x3040, 0x40, name="two")
        other = moves.add_move(0x5000, 0x3080, 0x10, name="other")
        assert moves.r2b(0x2090) == (0x2090, BASE_MOVE_ID)
        assert moves.r2b(0x2090, context=[other.move_id]) == (None, None)

    def test_without_a_loaded_predicate_nothing_is_in_place(self):
        moves = MoveManager()
        loader = moves.add_move(0x2080, 0x3000, 0x40, name="loader")
        assert moves.r2b(0x2090) == (0x3010, loader.move_id)


class TestAnnotations:

    def test_byte_with_no_move_goes_in_place(self, tmp_path):
        # The issue's reproduction: 32 bytes from &20B0 run past the end
        # of LOADER's stored image (&3030 + 32 > &3040).
        d, _loader = _disassembler(tmp_path)
        d.byte(0x20B0, 0x20)
        ir = d.disassemble()
        assert ir.classifications.get_classification(0x20B0).length() == 0x20
        str(ir.render(BeebasmRenderer()))

    def test_byte_inside_the_move_goes_in_the_move(self, tmp_path):
        d, loader = _disassembler(tmp_path)
        with loader:
            d.byte(0x20B0, 4)
        d.byte(0x20A0, 4, move=loader)
        ir = d.disassemble()
        assert ir.classifications.get_classification(0x3030).length() == 4
        assert ir.classifications.get_classification(0x3020).length() == 4

    def test_label_with_no_move_names_only_the_in_place_copy(self, tmp_path):
        d, _loader = _disassembler(tmp_path)
        d.label(0x2090, "game_routine")
        data = d.disassemble().render(JsonRenderer()).data
        labelled = [
            it.get("binary_addr", it["addr"]) for it in data["items"]
            if "game_routine" in it.get("labels", [])
        ]
        assert labelled == [0x2090]

    def test_entry_with_no_move_runs_in_place(self, tmp_path):
        d, _loader = _disassembler(tmp_path, game_entry=False, loader_entry=False)
        d.entry(0x2090)
        ir = d.disassemble()
        assert _is_code(ir, 0x2090)
        assert not _is_code(ir, 0x3010)


class TestTrace:

    def test_in_place_code_jumps_to_the_in_place_copy(self, tmp_path):
        d, _loader = _disassembler(tmp_path, loader_entry=False)
        ir = d.disassemble()
        assert _is_code(ir, 0x2090)
        assert not _is_code(ir, 0x3010)

    def test_moved_code_branches_within_its_own_copy(self, tmp_path):
        d, _loader = _disassembler(tmp_path, game_entry=False)
        ir = d.disassemble()
        assert _is_code(ir, 0x3010)
        assert not _is_code(ir, 0x2090)

    def test_code_in_another_move_sees_the_moved_copy(self, tmp_path):
        # Code in a third move, run at &4000, jumps to &2090. Moves lie
        # over the in-place image, so from relocated code the loader's
        # copy is the one there (D-030's fall-through into another move).
        d, _loader = _disassembler(tmp_path, game_entry=False, loader_entry=False)
        (tmp_path / "OTHER").write_bytes(bytes([0x4C, 0x90, 0x20]))
        d.load(tmp_path / "OTHER", 0x5000, name="OTHER")
        other = d.add_move(0x4000, 0x5000, 3, name="other")
        with other:
            d.entry(0x4000)
        ir = d.disassemble()
        assert _is_code(ir, 0x3010)
        assert not _is_code(ir, 0x2090)


class TestLabels:

    def test_each_copy_gets_its_own_auto_label(self, tmp_path):
        d, _loader = _disassembler(tmp_path)
        ir = d.disassemble()
        names = ir.labels.get_label(0x2090).explicit_names
        assert set(names) == {BASE_MOVE_ID, d._moves.moves[0].move_id}

    def test_every_label_is_defined_once(self, tmp_path):
        d, _loader = _disassembler(tmp_path)
        text = str(d.disassemble().render(BeebasmRenderer()))
        defined = [ln.strip() for ln in text.splitlines() if ln.strip().startswith(".")]
        assert len(defined) == len(set(defined))


class TestJson:

    def test_in_place_jump_has_no_target_move(self, tmp_path):
        d, _loader = _disassembler(tmp_path)
        data = d.disassemble().render(JsonRenderer()).data
        jmp = next(it for it in data["items"] if it["addr"] == 0x2000)
        assert "target_move" not in jmp

    def test_moved_branch_targets_its_own_move(self, tmp_path):
        d, _loader = _disassembler(tmp_path)
        data = d.disassemble().render(JsonRenderer()).data
        bne = next(it for it in data["items"] if it.get("binary_addr") == 0x3002)
        assert bne["target_move"] == "loader"


def _assemble_beebasm(tmp_path, text):
    out_dirpath = tmp_path / "beebasm"
    out_dirpath.mkdir()
    (out_dirpath / "game.asm").write_text(text, encoding="utf-8")
    result = subprocess.run(
        [BEEBASM, "-i", "game.asm"],
        capture_output=True, text=True, cwd=str(out_dirpath),
    )
    assert result.returncode == 0, (
        f"beebasm failed:\n=== source ===\n{text}\n=== stderr ===\n{result.stderr}"
    )
    return out_dirpath


@pytest.mark.beebasm
def test_beebasm_round_trip(tmp_path):
    d, _loader = _disassembler(tmp_path)
    d.label(0x2090, "game_routine")
    d.label(0x2090, "loader_routine", move=_loader)
    d.byte(0x20B0, 0x20)
    out_dirpath = _assemble_beebasm(
        tmp_path, str(d.disassemble().render(BeebasmRenderer())),
    )
    assert (out_dirpath / "GAME").read_bytes() == GAME
    assert (out_dirpath / "LOADER").read_bytes() == LOADER


@pytest.mark.tass64
def test_tass64_round_trip(tmp_path):
    d, _loader = _disassembler(tmp_path)
    d.label(0x2090, "game_routine")
    d.label(0x2090, "loader_routine", move=_loader)
    d.byte(0x20B0, 0x20)
    ir = d.disassemble()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        text = str(ir.render(Tass64Renderer()))
    out_dirpath = tmp_path / "tass64"
    out_dirpath.mkdir()
    (out_dirpath / "game.asm").write_text(text, encoding="utf-8")
    result = subprocess.run(
        [TASS64, "--nostart", "-q",
         "--output-section=game", "-o", "GAME",
         "--output-section=loader", "-o", "LOADER", "game.asm"],
        capture_output=True, text=True, cwd=str(out_dirpath),
    )
    assert result.returncode == 0, (
        f"64tass failed:\n=== source ===\n{text}\n=== stderr ===\n{result.stderr}"
    )
    assert (out_dirpath / "GAME").read_bytes() == GAME
    assert (out_dirpath / "LOADER").read_bytes() == LOADER


def test_overlays_and_the_in_place_copy_each_take_their_own_annotations(tmp_path):
    # Two overlays and the in-place image all cover &20B0.
    d, loader = _disassembler(tmp_path)
    (tmp_path / "ALT").write_bytes(LOADER)
    d.load(tmp_path / "ALT", 0x3040, name="ALT")
    alt = d.add_move(0x2080, 0x3040, len(LOADER), name="alt")
    d.byte(0x20B0, 1)
    with loader:
        d.byte(0x20B1, 1)
    with alt:
        d.byte(0x20B2, 1)
    ir = d.disassemble()
    assert ir.classifications.get_classification(0x20B0).length() == 1
    assert ir.classifications.get_classification(0x3031).length() == 1
    assert ir.classifications.get_classification(0x3072).length() == 1
