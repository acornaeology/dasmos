"""Disassemblies of several separately-loaded files (#49).

A program can be several files loaded at different addresses (the
Dunjunz game is four DFS files at &0400, &0D00, &1100 and &6E80, with
the screen in the gap). Disassembling them together lets the trace
follow calls between the files; each file is still its own image with
its own name and, for a ``*RUN`` file, its own exec/reload addresses:

    d.load("Dunjun4", 0x0400, name="Dunjun4", exec_addr=0x0400)

``d.program()`` (#45) remains the shorthand for a single-image program.
"""

import pytest

from dasmos.core.program import ProgramError
from dasmos.disassembler import Disassembler, DisassemblerError
from dasmos.ext.renderers.json import JsonRenderer


def _write(tmp_path, filename, data):
    filepath = tmp_path / filename
    filepath.write_bytes(data)
    return filepath


# Two small images: A at &0400 calls into B at &1100.
#   A: &0400 JSR &1100 ; RTS
#   B: &1100 LDA #1 ; RTS
IMAGE_A = bytes([0x20, 0x00, 0x11, 0x60])
IMAGE_B = bytes([0xA9, 0x01, 0x60])


def _two_images(tmp_path, **kwargs_a):
    d = Disassembler.create("6502")
    d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400, **kwargs_a)
    d.load(_write(tmp_path, "GameB", IMAGE_B), 0x1100, name="Game B")
    d.entry(0x0400)
    return d


class TestImageModel:

    def test_load_still_returns_its_range(self, tmp_path):
        d = Disassembler.create("6502")
        start, end = d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400)
        assert (start, end) == (0x0400, 0x0404)

    def test_images_in_load_order_with_ranges(self, tmp_path):
        ir = _two_images(tmp_path).disassemble()
        assert [(i.start, i.end) for i in ir.images] == [
            (0x0400, 0x0404), (0x1100, 0x1103),
        ]

    def test_name_defaults_to_the_file_name(self, tmp_path):
        ir = _two_images(tmp_path).disassemble()
        assert [i.name for i in ir.images] == ["GameA", "Game B"]
        assert [i.name_declared for i in ir.images] == [False, True]

    def test_exec_and_reload_per_image(self, tmp_path):
        ir = _two_images(
            tmp_path, exec_addr=0x0400, reload_addr=0x2400,
        ).disassemble()
        a, b = ir.images
        assert (a.exec_addr, a.reload_addr) == (0x0400, 0x2400)
        assert (b.exec_addr, b.reload_addr) == (None, None)

    def test_invalid_exec_addr_is_rejected(self, tmp_path):
        d = Disassembler.create("6502")
        with pytest.raises(ProgramError):
            d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400, exec_addr=-1)


class TestSingleImageProgram:
    """#45's single-image API keeps working, from either spelling."""

    def test_exec_on_load_is_the_program(self, tmp_path):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400, exec_addr=0x0402)
        d.entry(0x0400)
        assert d.disassemble().program.exec_addr == 0x0402

    def test_program_declaration_still_works(self, tmp_path):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400)
        d.program(exec_addr=0x0402)
        d.entry(0x0400)
        assert d.disassemble().program.exec_addr == 0x0402

    def test_program_and_exec_on_load_conflict(self, tmp_path):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400, exec_addr=0x0402)
        with pytest.raises(DisassemblerError, match="exec_addr"):
            d.program(exec_addr=0x0400)

    def test_program_is_rejected_with_several_images(self, tmp_path):
        d = _two_images(tmp_path)
        with pytest.raises(DisassemblerError, match="d.load"):
            d.program(exec_addr=0x0400)

    def test_second_load_after_program_is_rejected(self, tmp_path):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400)
        d.program(exec_addr=0x0400)
        with pytest.raises(DisassemblerError, match="d.load"):
            d.load(_write(tmp_path, "GameB", IMAGE_B), 0x1100)

    def test_several_images_have_no_single_program(self, tmp_path):
        ir = _two_images(tmp_path, exec_addr=0x0400).disassemble()
        assert ir.program is None


class TestJson:

    def test_meta_lists_images(self, tmp_path):
        data = _two_images(tmp_path, exec_addr=0x0400).disassemble().render(
            JsonRenderer(),
        ).data
        assert data["meta"]["images"] == [
            {"name": "GameA", "load_addr": 0x0400, "end_addr": 0x0404,
             "exec_addr": 0x0400},
            {"name": "Game B", "load_addr": 0x1100, "end_addr": 0x1103},
        ]

    def test_items_say_which_image_they_belong_to(self, tmp_path):
        items = _two_images(tmp_path).disassemble().render(JsonRenderer()).data["items"]
        image_of = {it["addr"]: it.get("image") for it in items}
        assert image_of[0x0400] == 0
        assert image_of[0x1100] == 1

    def test_single_image_items_have_no_image_index(self, tmp_path):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "GameA", IMAGE_A), 0x0400)
        d.entry(0x0400)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert all("image" not in it for it in items)


# -- beebasm: one save per image ----------------------------------------

import os
import shutil
import subprocess
import warnings

from dasmos.ext.renderers.beebasm import BeebasmRenderer


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which("beebasm")


BEEBASM = _find_beebasm()

# Three images with the screen-sized gaps between them, as in Dunjunz:
#   Dunjun4 &0400: JSR &1100 ; JSR &6E80 ; RTS
#   Dunjun5 &1100: LDA #1 ; RTS
#   Dunjun6 &6E80: LDX #2 ; RTS
GAME = [
    ("Dunjun4", 0x0400, bytes([0x20, 0x00, 0x11, 0x20, 0x80, 0x6E, 0x60])),
    ("Dunjun5", 0x1100, bytes([0xA9, 0x01, 0x60])),
    ("Dunjun6", 0x6E80, bytes([0xA2, 0x02, 0x60])),
]


def _game(tmp_path, *, names=True):
    d = Disassembler.create("6502")
    for name, addr, data in GAME:
        filepath = _write(tmp_path, f"{name}.bin", data)
        kwargs = {"name": name} if names else {}
        if name == "Dunjun4":
            kwargs["exec_addr"] = 0x0400
        d.load(filepath, addr, **kwargs)
    d.entry(0x0400)
    return d.disassemble()


def _save_lines(text):
    return [ln.strip() for ln in text.splitlines() if ln.strip().startswith("save")]


class TestBeebasmSaves:

    def test_one_save_per_image(self, tmp_path):
        text = str(_game(tmp_path).render(BeebasmRenderer()))
        assert _save_lines(text) == [
            'save "Dunjun4", dasmos_dunjun4_start, dasmos_dunjun4_end, &0400, &0400',
            'save "Dunjun5", dasmos_dunjun5_start, dasmos_dunjun5_end',
            'save "Dunjun6", dasmos_dunjun6_start, dasmos_dunjun6_end',
        ]

    def test_boundary_labels_per_image(self, tmp_path):
        lines = [ln.strip() for ln in str(_game(tmp_path).render(BeebasmRenderer())).splitlines()]
        for name in ("dunjun4", "dunjun5", "dunjun6"):
            assert f".dasmos_{name}_start" in lines
            assert f".dasmos_{name}_end" in lines
        assert ".dasmos_start" not in lines

    def test_suppressed_boundary_labels_save_literal_ranges(self, tmp_path):
        text = str(_game(tmp_path).render(BeebasmRenderer(boundary_label_prefix="")))
        assert _save_lines(text)[1] == 'save "Dunjun5", &1100, &1103'

    def test_default_names_are_file_names(self, tmp_path):
        text = str(_game(tmp_path, names=False).render(BeebasmRenderer()))
        assert _save_lines(text)[1] == (
            'save "Dunjun5.bin", dasmos_dunjun5_bin_start, dasmos_dunjun5_bin_end'
        )

    def test_name_is_sanitised_for_labels_but_saved_verbatim(self, tmp_path):
        ir = _two_images(tmp_path).disassemble()
        text = str(ir.render(BeebasmRenderer()))
        assert 'save "Game B", dasmos_game_b_start, dasmos_game_b_end' in _save_lines(text)

    def test_output_filename_is_ignored_with_a_warning(self, tmp_path):
        r = BeebasmRenderer()
        r.set_output_filename("ALL")
        with pytest.warns(UserWarning, match="output_filename"):
            text = str(_game(tmp_path).render(r))
        assert not any('"ALL"' in ln for ln in _save_lines(text))

    def test_build_instructions_have_no_output_flag(self, tmp_path):
        text = str(_game(tmp_path).render(
            BeebasmRenderer(include_build_instructions=True, listing_filename="game.asm"),
        ))
        assert "beebasm -i game.asm" in text
        assert "-o" not in text.split("beebasm -i game.asm")[1].splitlines()[0]


class TestSingleImageSave:

    def _single(self, tmp_path, **kwargs):
        d = Disassembler.create("6502")
        d.load(_write(tmp_path, "KEYPAD.bin", IMAGE_A), 0x1900, **kwargs)
        d.entry(0x1900)
        return d.disassemble()

    def test_unnamed_single_image_is_unchanged(self, tmp_path):
        text = str(self._single(tmp_path).render(BeebasmRenderer()))
        assert _save_lines(text) == ["save dasmos_start, dasmos_end"]

    def test_declared_name_names_the_save(self, tmp_path):
        ir = self._single(tmp_path, name="KEYPAD", exec_addr=0x1902)
        assert _save_lines(str(ir.render(BeebasmRenderer()))) == [
            'save "KEYPAD", dasmos_start, dasmos_end, &1902, &1900',
        ]

    def test_output_filename_takes_precedence(self, tmp_path):
        r = BeebasmRenderer()
        r.set_output_filename("OTHER")
        text = str(self._single(tmp_path, name="KEYPAD").render(r))
        assert _save_lines(text) == ['save "OTHER", dasmos_start, dasmos_end']


@pytest.mark.beebasm
def test_beebasm_writes_each_image_as_its_own_file(tmp_path):
    text = str(_game(tmp_path).render(BeebasmRenderer()))
    out_dirpath = tmp_path / "out"
    out_dirpath.mkdir()
    asm_path = out_dirpath / "game.asm"
    asm_path.write_text(text, encoding="utf-8")
    result = subprocess.run(
        [BEEBASM, "-i", str(asm_path)],
        capture_output=True, text=True, cwd=str(out_dirpath),
    )
    assert result.returncode == 0, (
        f"beebasm failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    for name, _addr, data in GAME:
        assert (out_dirpath / name).read_bytes() == data, name


@pytest.mark.beebasm
def test_beebasm_saves_an_image_whose_bytes_are_relocated(tmp_path):
    # Loader at &0400 calls code stored in a second image at &2400 that
    # runs at &0900 (moved). The stored image is still saved as itself.
    loader = bytes([0x20, 0x00, 0x09, 0x60])          # JSR &0900 ; RTS
    stored = bytes([0xA9, 0x05, 0x60, 0xEA])          # LDA #5 ; RTS ; NOP
    d = Disassembler.create("6502")
    d.load(_write(tmp_path, "LOADER.bin", loader), 0x0400, name="LOADER")
    d.load(_write(tmp_path, "CODE.bin", stored), 0x2400, name="CODE")
    move = d.add_move(0x0900, 0x2400, len(stored))
    d.entry(0x0400)
    with move:
        d.entry(0x0900)
    text = str(d.disassemble().render(BeebasmRenderer()))
    out_dirpath = tmp_path / "out"
    out_dirpath.mkdir()
    (out_dirpath / "game.asm").write_text(text, encoding="utf-8")
    result = subprocess.run(
        [BEEBASM, "-i", "game.asm"],
        capture_output=True, text=True, cwd=str(out_dirpath),
    )
    assert result.returncode == 0, (
        f"beebasm failed:\n=== source ===\n{text}\n"
        f"=== stderr ===\n{result.stderr}"
    )
    assert (out_dirpath / "LOADER").read_bytes() == loader
    assert (out_dirpath / "CODE").read_bytes() == stored
