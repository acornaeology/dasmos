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
    """The dict has a stable top-level shape. Compared to py8dis-fork's
    schema, dasmos splits ``data_banner`` out into its own ``banners``
    array (so consumers can tell "subroutine entry point" from "data
    region with header"). All other keys mirror py8dis (see
    ``project_jsonrenderer_schema`` memory).
    """

    EXPECTED_KEYS = (
        "meta", "constants", "subroutines", "banners",
        "external_labels", "memory_map", "index_bases", "regions", "items",
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

    def test_meta_carries_schema_version(self, tiny_disassembler):
        from dasmos.ext.renderers.json.renderer import JSON_SCHEMA_VERSION
        out = tiny_disassembler.render(JsonRenderer())
        assert out.data["meta"]["schema_version"] == JSON_SCHEMA_VERSION
        assert JSON_SCHEMA_VERSION >= 2

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

    def test_format_hint_char_renders_quoted_and_surfaces_metadata(
        self, tmp_path,
    ):
        # ``FormatHint.CHAR`` declares "this byte is intended as an
        # ASCII character". The JSON renderer translates this into:
        # - operand text using a universal char-literal form (``'g'``
        #   — beebasm-style, also valid in most 6502 dialects);
        # - a ``format_hint: "char"`` field on the item, so consumers
        #   that want to render a different visual representation
        #   (e.g. an HTML page showing both the hex and the char) have
        #   the abstract semantic available.
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa0, 0x67, 0x60]))  # ldy #&67 ; rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.char_literal(0x8001)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        ldy = items[0]
        assert ldy["operand"] == "#'g'"
        assert ldy["format_hint"] == "char"

    def test_format_hint_char_quote_chars_match_beebasm(self, tmp_path):
        # The apostrophe (0x27) has no clean ``'c'`` form, so it renders
        # via the same ``ASC("'")`` cross-fallback the beebasm renderer
        # uses — no numeric degradation, no warning (#30). The
        # double-quote (0x22) renders unambiguously as ``'"'``.
        import warnings
        bin_path = tmp_path / "p.bin"
        # ldy #&27 ('), ldx #&22 ("), rts
        bin_path.write_bytes(bytes([0xa0, 0x27, 0xa2, 0x22, 0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.char_literal(0x8001)
        d.char_literal(0x8003)
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # any UserWarning fails the test
            items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["operand"] == '#ASC("\'")'
        assert items[0]["format_hint"] == "char"
        assert items[1]["operand"] == "#'\"'"
        assert items[1]["format_hint"] == "char"

    def test_format_hint_decimal_forces_base_10_in_operand(self, tmp_path):
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0xff, 0x60]))  # lda #&ff ; rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.format_hint(0x8001, FormatHint.DECIMAL)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["operand"] == "#255"
        assert items[0]["format_hint"] == "decimal"

    def test_format_hint_hex_overrides_small_int_decimal(self, tmp_path):
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0x07, 0x60]))  # lda #&07 ; rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.format_hint(0x8001, FormatHint.HEX)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["operand"] == "#&07"
        assert items[0]["format_hint"] == "hex"

    def test_format_hint_binary_produces_percent_form(self, tmp_path):
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0xaa, 0x60]))  # lda #&aa ; rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.format_hint(0x8001, FormatHint.BINARY)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["operand"] == "#%10101010"
        assert items[0]["format_hint"] == "binary"

    def test_format_hint_octal_warns_and_falls_back_in_json(self, tmp_path):
        # Like the beebasm renderer, JSON's operand syntax (modeled
        # on beebasm) has no octal sigil. Best-effort: emit decimal
        # and warn; the consumer still sees ``format_hint: "octal"``
        # in the metadata, so a sophisticated reader can render its
        # own octal form from the byte value.
        import warnings as _warnings
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0xff, 0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.format_hint(0x8001, FormatHint.OCTAL)
        ir = d.disassemble()
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            items = ir.render(JsonRenderer()).data["items"]
        assert items[0]["operand"] == "#255"
        assert items[0]["format_hint"] == "octal"
        warning_messages = [str(w.message) for w in caught]
        assert any("octal" in m.lower() for m in warning_messages)

    def test_no_format_hint_field_when_unset(self, tiny_disassembler):
        # Items without an explicit hint must NOT emit the field at
        # all (vs. emitting it with a null / placeholder value),
        # matching the schema-thrift convention used elsewhere in
        # the JSON output.
        items = tiny_disassembler.render(JsonRenderer()).data["items"]
        for item in items:
            assert "format_hint" not in item

    def test_format_hint_char_non_printable_falls_back_with_warning(
        self, tmp_path,
    ):
        import warnings as _warnings
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0x07, 0x60]))  # non-printable
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.char_literal(0x8001)
        ir = d.disassemble()
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            items = ir.render(JsonRenderer()).data["items"]
        # Operand fell back to plain decimal (small-int rule kicks in).
        assert items[0]["operand"] == "#7"
        # Hint metadata IS still surfaced — the consumer learns "the
        # user wanted a char here" even though no clean literal exists.
        assert items[0]["format_hint"] == "char"
        warning_messages = [str(w.message) for w in caught]
        assert any("char" in m.lower() and "&07" in m for m in warning_messages)

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


class TestByteWordFormatHints:
    """``format_hints`` parallel array on ``byte`` and ``word`` items.

    The opcode item's singular ``format_hint`` (operand byte) has
    been there since FormatHint was added; byte/word items only got
    the parallel-array form once the JSON path started carrying the
    hint set the beebasm renderer already understood (#14).
    """

    def test_byte_with_binary_hint_surfaces_in_format_hints(self, tmp_path):
        # The acorn_sideways_rom rom_type byte at &8006 is the
        # canonical case: d.format_hint(addr, FormatHint.BINARY) on
        # a single-byte d.byte() classification. The JSON consumer
        # picks up the hint and renders the bit-pattern form.
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x82]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.byte(0x8000, 1)
        d.format_hint(0x8000, FormatHint.BINARY)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["type"] == "byte"
        assert items[0]["values"] == [0x82]
        assert items[0]["format_hints"] == ["binary"]

    def test_byte_block_with_mixed_hints_uses_null_padding(self, tmp_path):
        # Heterogeneous hints across a multi-byte block: only the
        # bytes with hints set carry a string, others are None. Same
        # padding convention as the existing ``expressions`` array.
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x01, 0x02, 0x82, 0x04]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.byte(0x8000, 4)
        d.format_hint(0x8002, FormatHint.BINARY)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["values"] == [1, 2, 0x82, 4]
        assert items[0]["format_hints"] == [None, None, "binary", None]

    def test_byte_without_any_hint_omits_field(self, tmp_path):
        # No hints anywhere → field omitted entirely (schema-thrift
        # convention used elsewhere in the JSON output).
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x82]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.byte(0x8000, 1)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["type"] == "byte"
        assert "format_hints" not in items[0]

    def test_word_with_decimal_hint_per_word(self, tmp_path):
        # Word items group every two bytes into one value; format_hints
        # is parallel to ``values`` (one entry per word, not per byte).
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x10, 0x27, 0x20, 0x4e]))  # 10000, 20000
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.word(0x8000, 4)
        d.format_hint(0x8000, FormatHint.DECIMAL)
        d.format_hint(0x8002, FormatHint.HEX)
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["type"] == "word"
        assert items[0]["values"] == [10000, 20000]
        assert items[0]["format_hints"] == ["decimal", "hex"]

    def test_format_hints_coexists_with_expressions(self, tmp_path):
        # Both fields can appear on the same item; they're independent
        # parallel arrays.
        from dasmos.core.format_hint import FormatHint
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x82, 0x10]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.byte(0x8000, 2)
        d.format_hint(0x8000, FormatHint.BINARY)
        d.expr(0x8001, "version")
        items = d.disassemble().render(JsonRenderer()).data["items"]
        assert items[0]["values"] == [0x82, 0x10]
        assert items[0]["format_hints"] == ["binary", None]
        # Each expression is now an object carrying ready text plus a
        # structured tree; None where no expression exists.
        assert items[0]["expressions"] == [
            None,
            {"text": "version", "tree": {"sym": "version"}},
        ]

    def test_code_operand_carries_structured_expr(self, tmp_path):
        # lda #<value>; the operand expression is surfaced structurally
        # alongside the ready operand text.
        from dasmos.expr import lo, ref
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xA9, 0x00, 0x60]))  # lda #0 : rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        d.label(0x8002, "handler")
        d.expr(0x8001, lo(ref(0x8002) - 1))
        item = d.disassemble().render(JsonRenderer()).data["items"][0]
        assert item["operand"] == "#<(handler - 1)"      # ready text
        assert item["expr"] == {
            "text": "<(handler - 1)",
            "tree": {
                "op": "lowbyte",
                "operand": {
                    "op": "sub",
                    "left": {"ref": 0x8002, "name": "handler"},
                    "right": {"int": 1, "radix": "auto"},
                },
            },
        }


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

    def test_non_relocated_sub_omits_binary_addr(self, tmp_path):
        # When a subroutine sits at its natural binary address (no
        # ``move()`` redirects it), the JSON entry omits ``binary_addr``
        # — matching the per-item convention. The acornaeology site
        # generator uses ``(addr, binary_addr)`` as the key that joins
        # subroutine entries to item entries, so a stray ``binary_addr``
        # on the sub side breaks the lookup and the structured banner
        # falls back to plain-comment rendering.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(0x8000, "frob", title="Frob the bus")
        ir = d.disassemble()
        subs = ir.render(JsonRenderer()).data["subroutines"]
        assert subs[0]["addr"] == 0x8000
        assert "binary_addr" not in subs[0], subs[0]

    def test_standalone_banner_appears_in_banners_array(self, tmp_path):
        # d.banner() (without an accompanying d.subroutine()) is the
        # dasmos analogue of py8dis's data_banner — a visual section
        # header for a data region. dasmos's JSON schema gives these
        # their own ``banners`` array (parallel to ``subroutines``) so
        # downstream consumers can tell "subroutine entry point" from
        # "data region with header" without inspecting fields.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "table_x")
        d.banner(0x8000, title="Lookup table X",
                 description="32-entry sine table.")
        out = d.disassemble().render(JsonRenderer())
        # Not in subroutines (no entry-point semantics).
        assert all(s["addr"] != 0x8000 for s in out.data["subroutines"])
        # In banners.
        entry = next((b for b in out.data["banners"] if b["addr"] == 0x8000), None)
        assert entry is not None, out.data["banners"]
        assert entry["name"] == "table_x"
        assert entry["title"] == "Lookup table X"
        assert entry["description"] == "32-entry sine table."

    def test_subroutine_with_internal_banner_does_not_appear_in_banners(self, tmp_path):
        # d.subroutine() internally attaches a Banner annotation
        # (so the asm renderer can produce a banner block). The
        # subroutine's title/description are already on the
        # ``subroutines`` entry — the internal Banner must NOT
        # produce a duplicate ``banners`` entry at the same address.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(0x8000, "frob",
                     title="Frob the bus", description="Does things.")
        out = d.disassemble().render(JsonRenderer())
        # In subroutines.
        subs = [s for s in out.data["subroutines"] if s["addr"] == 0x8000]
        assert len(subs) == 1, subs
        assert subs[0]["name"] == "frob"
        # NOT in banners.
        banners = [b for b in out.data["banners"] if b["addr"] == 0x8000]
        assert banners == [], banners

    def test_banner_carries_on_entry_on_exit(self, tmp_path):
        # Banner annotations can carry register-usage tables too.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "table_y")
        d.banner(0x8000, title="Table Y",
                 description="...",
                 on_entry={"a": "index"},
                 on_exit={"a": "value"})
        out = d.disassemble().render(JsonRenderer())
        entry = next(b for b in out.data["banners"] if b["addr"] == 0x8000)
        assert entry["on_entry"] == {"a": "index"}
        assert entry["on_exit"] == {"a": "value"}

    def test_banner_without_label_uses_no_name(self, tmp_path):
        # Bannered addresses don't strictly need a label.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.banner(0x8000, title="Anonymous banner",
                 description="No label here.")
        out = d.disassemble().render(JsonRenderer())
        entry = next(b for b in out.data["banners"] if b["addr"] == 0x8000)
        assert "name" not in entry, entry
        assert entry["title"] == "Anonymous banner"

    def test_banners_present_as_empty_list_when_none_attached(self, tmp_path):
        # The top-level ``banners`` key is always present, as an
        # empty list when no Banner annotations exist. Downstream
        # consumers can iterate it unconditionally.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        out = d.disassemble().render(JsonRenderer())
        assert out.data["banners"] == []

    def test_banner_does_not_duplicate_into_per_item_comments(self, tmp_path):
        # A Banner annotation belongs only in the top-level ``banners[]``
        # array (or in ``subroutines[]`` for sub entries). It must NOT
        # also appear as a stringified separator+body in any of the
        # per-item ``comments_*_label`` / ``comments_*_line`` /
        # ``comment_inline`` fields — otherwise consumers have to
        # de-dupe by address (#15). All four banners surface in
        # ``banners[]`` per #18 (the previous "first wins" behaviour
        # silently dropped three of them); the goal of THIS test is
        # just the *absence* of duplication on the item.
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00, 0x00, 0x00, 0x00]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "table_x")
        d.byte(0x8000, 4)
        d.banner(0x8000, title="Before-label", description="x",
                 align=Align.BEFORE_LABEL)
        d.banner(0x8000, title="After-label", description="x",
                 align=Align.AFTER_LABEL)
        d.banner(0x8000, title="Before-line", description="x",
                 align=Align.BEFORE_LINE)
        d.banner(0x8000, title="After-line", description="x",
                 align=Align.AFTER_LINE)
        out = d.disassemble().render(JsonRenderer())
        item = next(it for it in out.data["items"] if it["addr"] == 0x8000)
        all_comment_text = "\n".join(
            "\n".join(item.get(field, []))
            for field in (
                "comments_before_label", "comments_after_label",
                "comments_before_line", "comments_after_line",
            )
        )
        for marker in ("Before-label", "After-label", "Before-line", "After-line"):
            assert marker not in all_comment_text, (
                f"banner content {marker!r} leaked into per-item comments"
            )
        assert "*" * 50 not in all_comment_text

    def test_multiple_banners_at_same_address_all_surface_in_banners(
        self, tmp_path,
    ):
        # Multiple Banner annotations at the same address (each at a
        # distinct align) must ALL appear in ``banners[]`` — the
        # previous "first wins" rule silently dropped every banner
        # past the first, breaking the acorn_sideways_rom case where
        # an env attaches both a BEFORE_LABEL section header and an
        # AFTER_LABEL bit-decode banner at &8006 (#18).
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "rom_type")
        d.banner(
            0x8000, title="ROM identification",
            description="Six descriptive fields ...",
            align=Align.BEFORE_LABEL,
        )
        d.banner(
            0x8000, title="ROM type byte",
            description="| Bit | Value | Meaning |\n|-|-|-|\n| 7 | 1 | x |",
            align=Align.AFTER_LABEL,
        )
        out = d.disassemble().render(JsonRenderer())
        at_addr = [b for b in out.data["banners"] if b["addr"] == 0x8000]
        assert len(at_addr) == 2, at_addr
        # Insertion order preserved.
        titles = [b["title"] for b in at_addr]
        assert titles == ["ROM identification", "ROM type byte"]
        # Each carries its own align field.
        aligns = [b["align"] for b in at_addr]
        assert aligns == ["before_label", "after_label"]

    def test_all_four_aligns_at_same_address_each_surface(self, tmp_path):
        # Stress test: a banner at every BEFORE / AFTER alignment on
        # the same address. All four must appear in ``banners[]``.
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "addr")
        for align, title in [
            (Align.BEFORE_LABEL, "before-label"),
            (Align.AFTER_LABEL, "after-label"),
            (Align.BEFORE_LINE, "before-line"),
            (Align.AFTER_LINE, "after-line"),
        ]:
            d.banner(0x8000, title=title, description="x", align=align)
        out = d.disassemble().render(JsonRenderer())
        at_addr = [b for b in out.data["banners"] if b["addr"] == 0x8000]
        assert len(at_addr) == 4
        assert {b["align"] for b in at_addr} == {
            "before_label", "after_label",
            "before_line", "after_line",
        }
        # All share the same name (the address's primary label) —
        # the issue notes ``name`` is per-address, not per-banner,
        # so it's safe to repeat.
        assert all(b.get("name") == "addr" for b in at_addr)

    def test_comments_split_by_align_into_distinct_fields(self, tmp_path):
        # The 5-way Align enum maps to per-align JSON fields (#16).
        # Each plain Comment lands in exactly the field matching its
        # align, with no conflation between label and line buckets.
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        d.comment(0x8000, "Before-label note", align=Align.BEFORE_LABEL)
        d.comment(0x8000, "After-label note", align=Align.AFTER_LABEL)
        d.comment(0x8000, "Before-line note", align=Align.BEFORE_LINE)
        d.comment(0x8000, "After-line note", align=Align.AFTER_LINE)
        d.comment(0x8000, "Inline note", align=Align.INLINE)
        out = d.disassemble().render(JsonRenderer())
        item = next(it for it in out.data["items"] if it["addr"] == 0x8000)
        assert item["comments_before_label"] == ["Before-label note"]
        assert item["comments_after_label"] == ["After-label note"]
        assert item["comments_before_line"] == ["Before-line note"]
        assert item["comments_after_line"] == ["After-line note"]
        assert item["comment_inline"] == "Inline note"
        # Old union field names are gone (clean break per #16).
        assert "comments_before" not in item
        assert "comments_after" not in item

    def test_per_align_fields_omitted_when_empty(self, tmp_path):
        # Per the schema-thrift convention used elsewhere in the
        # JSON output, empty per-align buckets are omitted entirely
        # rather than emitted as ``[]``.
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        d.comment(0x8000, "Only after-label", align=Align.AFTER_LABEL)
        out = d.disassemble().render(JsonRenderer())
        item = next(it for it in out.data["items"] if it["addr"] == 0x8000)
        assert item["comments_after_label"] == ["Only after-label"]
        for absent in (
            "comments_before_label", "comments_before_line",
            "comments_after_line", "comment_inline",
        ):
            assert absent not in item, f"{absent} should be omitted"

    def test_xref_summaries_field_separate_from_user_comments(self, tmp_path):
        # Xref summary text is auto-generated metadata (#16) and lives
        # in its own ``xref_summaries`` field rather than mixed into
        # the user-comment buckets the way it used to be in
        # ``comments_before``.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x20, 0x05, 0x80, 0xea, 0x60, 0x60]))
        # JSR &8005 from &8000; RTS at &8005. The labelled target
        # gets an xref summary citing the JSR.
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000, name="start")
        d.label(0x8005, "target")
        out = d.disassemble().render(JsonRenderer())
        target_item = next(it for it in out.data["items"] if it["addr"] == 0x8005)
        assert "xref_summaries" in target_item
        assert any(
            "referenced" in s and "&8005" in s
            for s in target_item["xref_summaries"]
        )
        # Xref text doesn't leak into user-comment fields.
        for field in (
            "comments_before_label", "comments_after_label",
            "comments_before_line", "comments_after_line",
        ):
            for entry in target_item.get(field, []):
                assert "referenced" not in entry, (
                    f"xref text leaked into {field}: {entry!r}"
                )

    def test_banner_record_carries_align_field(self, tmp_path):
        # banners[] records expose the banner's align so consumers
        # can render at the correct visual position (#16). Lowercase
        # enum value matching the format_hints convention.
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "table_x")
        d.banner(0x8000, title="Header card", description="...",
                 align=Align.AFTER_LABEL)
        out = d.disassemble().render(JsonRenderer())
        entry = next(b for b in out.data["banners"] if b["addr"] == 0x8000)
        assert entry["align"] == "after_label"

    def test_banner_record_align_default_is_before_label(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x00] * 4))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "table_x")
        d.banner(0x8000, title="Default-align banner", description="...")
        out = d.disassemble().render(JsonRenderer())
        entry = next(b for b in out.data["banners"] if b["addr"] == 0x8000)
        assert entry["align"] == "before_label"

    def test_relocated_sub_keeps_binary_addr(self, tmp_path):
        # When a subroutine is in a relocated region, the binary
        # address differs from the runtime address and BOTH must be
        # surfaced (the item-level emission also keeps both).
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xea, 0x60]))  # nop, rts
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.add_move(0x0400, 0x8000, 2)
        d.subroutine(0x0400, "moved")
        d.entry(0x0400)
        ir = d.disassemble()
        subs = ir.render(JsonRenderer()).data["subroutines"]
        assert subs[0]["addr"] == 0x0400
        assert subs[0]["binary_addr"] == 0x8000


class TestMemoryMapMetadata:
    """``memory_map`` entries describe out-of-load-range labels that
    document RAM / hardware locations. Driver scripts attach extra
    metadata via ``d.label(addr, name, length=, group=, access=,
    description=)``; the JSON renderer must surface every populated
    field so the site generator can render the access column,
    group-bucket the rows, and show address ranges.
    """

    def test_emits_length_group_access(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x0080, "mem_ptr", description="Indirect pointer.",
                length=2, group="zero_page", access="rw")
        out = d.disassemble().render(JsonRenderer())
        mm = out.data["memory_map"]
        entry = next(e for e in mm if e["name"] == "mem_ptr")
        assert entry["addr"] == 0x80
        assert entry["length"] == 2
        assert entry["group"] == "zero_page"
        assert entry["access"] == "rw"
        assert entry["description"] == "Indirect pointer."

    def test_label_with_metadata_but_no_description_still_emitted(self, tmp_path):
        # An author may want a memory-map row purely as a labelled
        # workspace location with a bus-access annotation, without
        # narrative description text. Skipping such labels would drop
        # them from the rendered memory-map page.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0xFE40, "system_via_orb",
                length=1, group="io", access="rw")
        out = d.disassemble().render(JsonRenderer())
        mm = out.data["memory_map"]
        entry = next(e for e in mm if e["name"] == "system_via_orb")
        assert entry["access"] == "rw"
        assert entry["group"] == "io"
        assert "description" not in entry

    def test_optional_fields_omitted_when_unset(self, tmp_path):
        # A label with only a description (no length/group/access)
        # emits just description — no spurious empty fields.
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x0070, "scratch", description="Scratch byte.")
        out = d.disassemble().render(JsonRenderer())
        mm = out.data["memory_map"]
        entry = next(e for e in mm if e["name"] == "scratch")
        assert entry["description"] == "Scratch byte."
        assert "length" not in entry
        assert "group" not in entry
        assert "access" not in entry

    def test_in_range_label_with_metadata_not_in_memory_map(self, tmp_path):
        # Labels INSIDE the loaded range describe code/data in the
        # ROM and should NOT appear in memory_map (which is about
        # out-of-ROM memory: zero page, workspace, hardware).
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.label(0x8000, "in_rom",
                length=1, group="rom", access="r",
                description="Inside ROM.")
        out = d.disassemble().render(JsonRenderer())
        mm = out.data["memory_map"]
        assert all(e["name"] != "in_rom" for e in mm), mm


class TestSetextHeadingNormalisation:
    """Driver-supplied Setext-style headings (``Title\\n====``) get
    normalised to ATX (``# Title``) in the JSON output so the rule
    can't wrap mid-line on downstream consumers (issue #3). The asm
    path strips heading markers entirely; this normalisation is a
    JSON-side concern.
    """

    def test_setext_in_comment_becomes_atx(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.comment(0x8000, "ANFS ROM 4.21\n=============\n\nbody.")
        out = d.disassemble().render(JsonRenderer())
        item = next(it for it in out.data["items"] if it["addr"] == 0x8000)
        joined = "\n".join(item.get("comments_before_label", []))
        assert "# ANFS ROM 4.21" in joined
        assert "=============" not in joined

    def test_setext_in_subroutine_description_becomes_atx(self, tmp_path):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.subroutine(
            0x8000, "main",
            description="Section\n=======\n\nDetail prose.",
        )
        out = d.disassemble().render(JsonRenderer())
        sub = next(s for s in out.data["subroutines"] if s.get("name") == "main")
        assert "# Section" in sub["description"]
        assert "=======" not in sub["description"]

    def test_setext_in_banner_description_becomes_atx(self, tmp_path):
        from dasmos.core.annotations import Align
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.banner(
            0x8000,
            title="Region",
            description="Heading\n=======\n\nbody.",
        )
        out = d.disassemble().render(JsonRenderer())
        banner = next(b for b in out.data["banners"] if b.get("title") == "Region")
        assert "# Heading" in banner["description"]
        assert "=======" not in banner["description"]

    def test_non_heading_markdown_unchanged_in_json(self, tmp_path):
        # Plain prose without setext rule chars must round-trip
        # byte-identical (fast-path early return).
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.comment(0x8000, "Just a single line of prose.")
        out = d.disassemble().render(JsonRenderer())
        item = next(it for it in out.data["items"] if it["addr"] == 0x8000)
        assert "Just a single line of prose." in item.get(
            "comments_before_label", [],
        )
