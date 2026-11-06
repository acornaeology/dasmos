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
