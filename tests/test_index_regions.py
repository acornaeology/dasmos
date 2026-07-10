"""End-to-end tests for indexing regions (Layer B).

A declared region renders in-window neighbours of its anchor as
``anchor±k`` (or named slots), yields to explicit labels inside the
window, and documents itself in the JSON ``regions`` section.

See ``docs/design/reference-kinds-memo.md``.
"""

from __future__ import annotations

import pytest

from dasmos.core.regions import RegionError
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.json.renderer import JsonRenderer


def _fsm_program(tmp_path):
    """Program at &8000 that sweeps the FSM workspace around &0E00:

    - &8000  LDA &0E00,X   (bd 00 0e)  — the anchor itself
    - &8003  LDA &0DFD,X   (bd fd 0d)  — anchor-3 (a gap)
    - &8006  STA &0E03,X   (9d 03 0e)  — anchor+3 (may be an explicit slot)
    - &8009  RTS           (60)
    """
    binpath = tmp_path / "fsm.bin"
    binpath.write_bytes(bytes([
        0xBD, 0x00, 0x0E,
        0xBD, 0xFD, 0x0D,
        0x9D, 0x03, 0x0E,
        0x60,
    ]))
    d = Disassembler.create(cpu="6502")
    d.load(binpath, 0x8000)
    d.entry(0x8000)
    return d


class TestArithmeticSlotRendering:

    def test_gap_renders_relative_to_anchor(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3),
                       description="FSM sector-0 table")
        text = str(d.disassemble().render("beebasm"))
        assert "lda fsm_sector0 - 3,x" in text
        # The gap must NOT get a bare auto-label like l0dfd.
        assert "l0dfd" not in text

    def test_anchor_renders_as_its_own_name(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3))
        text = str(d.disassemble().render("beebasm"))
        assert "lda fsm_sector0,x" in text

    def test_positive_offset_renders_with_plus(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3))
        text = str(d.disassemble().render("beebasm"))
        assert "sta fsm_sector0 + 3,x" in text


class TestExplicitLabelPrecedence:

    def test_explicit_label_inside_window_wins(self, tmp_path):
        d = _fsm_program(tmp_path)
        # &0E03 is inside the (-6, +3) window but explicitly named.
        d.label(0x0E03, "fsm_s0_start_1")
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3))
        text = str(d.disassemble().render("beebasm"))
        assert "sta fsm_s0_start_1,x" in text
        # The region form must not compete with the explicit name.
        assert "fsm_sector0 + 3" not in text


class TestNamedSlots:

    def test_named_slots_use_m_p_convention(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3),
                       named_slots=True)
        text = str(d.disassemble().render("beebasm"))
        assert "lda fsm_sector0_m3,x" in text
        assert "sta fsm_sector0_p3,x" in text


class TestDisjointnessValidation:

    def test_overlapping_regions_raise_at_declaration(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3))
        with pytest.raises(RegionError, match="disjoint"):
            d.index_region(0x0E02, "other", window=(-4, 4))


class TestJsonRegionsSection:

    def test_region_documented_in_json(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3),
                       description="FSM sector-0 table")
        data = d.disassemble().render(JsonRenderer()).data
        assert len(data["regions"]) == 1
        region = data["regions"][0]
        assert region["anchor"] == 0x0E00
        assert region["name"] == "fsm_sector0"
        assert region["window"] == [-6, 3]
        assert region["named_slots"] is False
        assert region["description"] == "FSM sector-0 table"

    def test_operand_uses_region_form_in_json(self, tmp_path):
        d = _fsm_program(tmp_path)
        d.index_region(0x0E00, "fsm_sector0", window=(-6, 3))
        data = d.disassemble().render(JsonRenderer()).data
        operands = [it.get("operand") for it in data["items"]]
        assert "fsm_sector0 - 3,x" in operands
