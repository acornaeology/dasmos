"""Unit tests for the JSON structured-output renderer.

Covers plug-in registration, the top-level schema shape (mirrors the
py8dis-fork ``emit_structured()`` keys), and per-classification item
emission. The full-ROM parity diff against py8dis lives in
``test_nfs_roundtrip.py`` — these tests are the focused unit-level
checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.output import StructuredOutput
from dasmos.renderer import create_renderer


@pytest.fixture
def tiny_disassembler(tmp_path):
    """A disassembler primed with a 6-byte program at &8000:

        &8000  ldy #&00
        &8002  jsr &fff4    ; OSBYTE
        &8005  rts

    Yields the IR after disassemble() so each test can render it
    however it wants.
    """
    bin_path = tmp_path / "p.bin"
    bin_path.write_bytes(bytes([0xa0, 0x00, 0x20, 0xf4, 0xff, 0x60]))
    d = Disassembler.create(cpu="6502")
    d.load(bin_path, 0x8000)
    d.entry(0x8000, name="start")
    d.label(0xfff4, "osbyte")
    return d.disassemble()


class TestPluginRegistration:

    def test_loadable_via_stevedore(self):
        r = create_renderer("json")
        assert isinstance(r, JsonRenderer)
        assert r.name == "json"

    def test_supports_nmos6502_and_cmos65c02(self):
        r = JsonRenderer()
        cpus = r.cpus_supported()
        assert "6502" in cpus
        assert "65C02" in cpus


class TestTopLevelSchema:
    """The dict has the same top-level keys py8dis-fork emits, in the
    same order. Downstream consumers depend on this shape (see
    ``project_jsonrenderer_schema`` memory).
    """

    EXPECTED_KEYS = (
        "meta", "constants", "subroutines",
        "external_labels", "memory_map", "items",
    )

    def test_render_returns_structured_output(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        assert isinstance(out, StructuredOutput)

    def test_top_level_keys_match_py8dis_schema(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        assert tuple(out.data.keys()) == self.EXPECTED_KEYS

    def test_meta_has_load_and_end_addrs(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        assert out.data["meta"]["load_addr"] == 0x8000
        assert out.data["meta"]["end_addr"] == 0x8006

    def test_str_round_trips_via_json(self, tiny_disassembler):
        # ``str(output)`` is canonical JSON; loading it back gives the
        # same dict. Confirms the StructuredOutput shape works.
        import json
        out = tiny_disassembler.render(JsonRenderer())
        assert json.loads(str(out)) == out.data


class TestItemEmission:

    def test_code_item_has_mnemonic_and_operand(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        items = out.data["items"]
        ldy = items[0]
        assert ldy["addr"] == 0x8000
        assert ldy["type"] == "code"
        assert ldy["mnemonic"] == "ldy"
        # py8dis-fork format: ``#0`` decimal for n < 10.
        assert ldy["operand"] == "#0"
        assert ldy["bytes"] == [0xa0, 0x00]

    def test_code_item_has_labels_when_present(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        ldy = out.data["items"][0]
        assert ldy["labels"] == ["start"]

    def test_code_item_has_target_and_target_label(self, tiny_disassembler):
        # The JSR resolves to ``osbyte`` at &fff4 (registered as an
        # external label).
        out = tiny_disassembler.render(JsonRenderer())
        jsr = out.data["items"][1]
        assert jsr["mnemonic"] == "jsr"
        assert jsr["target"] == 0xfff4
        assert jsr["target_label"] == "osbyte"
        assert jsr["operand"] == "osbyte"

    def test_immediate_uses_decimal_below_10_hex_above(self, tmp_path):
        # py8dis-fork ``mainformatter.uint_formatter`` rule: decimal
        # for n < 10, hex for n >= 10. The JsonRenderer mirrors this
        # so the parity diff against py8dis stays small.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0x00, 0xa9, 0x09, 0xa9, 0x0a, 0xa9, 0xff]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        items = ir.render(JsonRenderer()).data["items"]
        # LDA #0 .. LDA #9 → decimal; LDA #&0a, #&ff → hex.
        assert items[0]["operand"] == "#0"
        assert items[1]["operand"] == "#9"
        assert items[2]["operand"] == "#&0a"
        assert items[3]["operand"] == "#&ff"

    def test_index_register_letters_lowercase(self, tmp_path):
        # py8dis runs with ``lower_case=True`` so its operand text
        # uses ``,y`` / ``,x``. The JsonRenderer mirrors this.
        bin_path = tmp_path / "p.bin"
        # LDA $1234,X ; LDA $5678,Y ; LDA ($12,X) ; LDA ($34),Y
        bin_path.write_bytes(bytes([
            0xbd, 0x34, 0x12,
            0xb9, 0x78, 0x56,
            0xa1, 0x12,
            0xb1, 0x34,
        ]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        items = ir.render(JsonRenderer()).data["items"]
        assert items[0]["operand"].endswith(",x")
        assert items[1]["operand"].endswith(",y")
        assert items[2]["operand"].endswith(",x)")
        assert items[3]["operand"].endswith("),y")

    def test_implied_opcode_has_no_operand_field(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        rts = out.data["items"][2]
        assert rts["mnemonic"] == "rts"
        assert "operand" not in rts
        assert rts["bytes"] == [0x60]

    def test_byte_classification_emits_values(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x42, 0x43, 0x44]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.byte(0x8000, length=3)
        ir = d.disassemble()
        out = ir.render(JsonRenderer())
        bytes_item = out.data["items"][0]
        assert bytes_item["type"] == "byte"
        assert bytes_item["values"] == [0x42, 0x43, 0x44]
        assert bytes_item["bytes"] == [0x42, 0x43, 0x44]

    def test_string_classification_emits_text(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"hi!")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.string(0x8000, length=3)
        ir = d.disassemble()
        out = ir.render(JsonRenderer())
        s_item = out.data["items"][0]
        assert s_item["type"] == "string"
        assert s_item["string"] == "hi!"


class TestExternalLabels:
    """External labels (out-of-load-range) appear as a name → address
    mapping. py8dis schema is ``dict[str, int]``.
    """

    def test_external_labels_emitted_by_name(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        ext = out.data["external_labels"]
        assert ext["osbyte"] == 0xfff4

    def test_in_range_labels_not_external(self, tiny_disassembler):
        # ``start`` is at &8000 which IS loaded — it should appear in
        # an item's ``labels`` field, NOT in ``external_labels``.
        out = tiny_disassembler.render(JsonRenderer())
        assert "start" not in out.data["external_labels"]


class TestEmptySectionsArePresent:
    """A driver that doesn't register constants / subroutines /
    memory-map metadata still gets the keys, as empty lists.
    Downstream consumers may iterate them unconditionally.
    """

    def test_constants_present_as_empty_list(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        assert out.data["constants"] == []

    def test_subroutines_present_as_empty_list(self, tiny_disassembler):
        # tiny_disassembler uses d.entry(), not d.subroutine() — no
        # subroutines registered.
        out = tiny_disassembler.render(JsonRenderer())
        assert out.data["subroutines"] == []

    def test_memory_map_present_as_empty_list(self, tiny_disassembler):
        out = tiny_disassembler.render(JsonRenderer())
        assert out.data["memory_map"] == []


class TestConstantsSection:

    def test_emits_registered_constants(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.constant(0xFE60, "system_via_orb", "System VIA port B")
        d.constant(0xFE61, "system_via_ddrb")
        ir = d.disassemble()
        out = ir.render(JsonRenderer())
        assert out.data["constants"] == [
            {"name": "system_via_orb", "value": 0xFE60,
             "comment": "System VIA port B"},
            {"name": "system_via_ddrb", "value": 0xFE61},
        ]


class TestSubroutinesSection:

    def test_emits_registered_subroutines(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60, 0x60, 0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(0x8000, "init",
                     title="Init", description="Sets things up.")
        d.subroutine(0x8002, "tick")
        ir = d.disassemble()
        subs = ir.render(JsonRenderer()).data["subroutines"]
        assert subs[0]["addr"] == 0x8000
        assert subs[0]["name"] == "init"
        assert subs[0]["title"] == "Init"
        assert subs[0]["description"] == "Sets things up."
        assert subs[1]["addr"] == 0x8002
        assert subs[1]["name"] == "tick"

    def test_fall_through_detected_when_no_terminator(self, tmp_path):
        # Sub at &8000: nop nop (two instructions, neither RTS/JMP/
        # BRK/RTI) → falls through into &8002.
        # Sub at &8002: rts (terminates).
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xea, 0xea, 0x60]))  # nop nop rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(0x8000, "fall_in")
        d.subroutine(0x8002, "lands_here")
        ir = d.disassemble()
        subs = ir.render(JsonRenderer()).data["subroutines"]
        assert subs[0]["name"] == "fall_in"
        assert subs[0].get("fall_through") is True
        # Last sub in the region — no fall-through can be computed,
        # so the field is absent (not False).
        assert "fall_through" not in subs[1]

    def test_no_fall_through_when_terminator_present(self, tmp_path):
        # Sub at &8000: rts (terminates).  Sub at &8001: rts.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60, 0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(0x8000, "first")
        d.subroutine(0x8001, "second")
        ir = d.disassemble()
        subs = ir.render(JsonRenderer()).data["subroutines"]
        assert "fall_through" not in subs[0]
