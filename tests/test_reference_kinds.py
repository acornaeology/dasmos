"""End-to-end tests for indexed-base reference classification.

A reference recorded against an operand's *base* address (``sta base,X``)
must be distinguishable from one that touches the address directly
(``sta base``). These tests exercise the whole path: the 6502 addressing
mode's ``reference_kind``, the reference recorded on the label, the
reworded cross-reference summaries, and the memory-map / ``index_bases``
split driven by ``d.index_base()``.

See ``docs/design/reference-kinds-memo.md``.
"""

from __future__ import annotations

from dasmos.core.memory import ReferenceKind
from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.json.renderer import JsonRenderer


def _program(tmp_path):
    """A 3-instruction program at &8000:

    - &8000  LDA &70      (a5 70)  — direct read of &70
    - &8002  STA &80,X    (95 80)  — &80 used only as an indexing base
    - &8004  RTS          (60)
    """
    binpath = tmp_path / "p.bin"
    binpath.write_bytes(bytes([0xA5, 0x70, 0x95, 0x80, 0x60]))
    d = Disassembler.create(cpu="6502")
    d.load(binpath, 0x8000)
    d.entry(0x8000)
    return d


class TestReferenceKindOnLabel:

    def test_direct_operand_records_direct_kind(self, tmp_path):
        d = _program(tmp_path)
        ir = d.disassemble()
        label = ir.labels.get_label(0x70)
        assert [r.kind for r in label.references] == [ReferenceKind.DIRECT]
        assert label.has_direct_reference()
        assert label.indexed_base_reference_count() == 0

    def test_indexed_operand_records_indexed_kind(self, tmp_path):
        d = _program(tmp_path)
        ir = d.disassemble()
        label = ir.labels.get_label(0x80)
        assert [r.kind for r in label.references] == [ReferenceKind.INDEXED]
        assert not label.has_direct_reference()
        assert label.indexed_base_reference_count() == 1


class TestBeebasmXrefWording:

    def _equates(self, tmp_path):
        d = _program(tmp_path)
        d.label(0x70, "zp_direct")
        d.index_base(0x80, "zp_base")
        return str(d.disassemble().render("beebasm"))

    def test_direct_reference_uses_referenced_wording(self, tmp_path):
        text = self._equates(tmp_path)
        assert "&70 referenced 1 time by &8000" in text

    def test_indexed_reference_uses_index_base_wording(self, tmp_path):
        text = self._equates(tmp_path)
        assert "&80 used as index base 1 time by &8002" in text
        # The base is never described as "referenced" — that would
        # imply the byte is touched.
        assert "&80 referenced" not in text


class TestMixedReferenceWording:

    def test_direct_and_indexed_to_same_address_are_reported_separately(self, tmp_path):
        # &8000 LDA &80 (direct); &8002 STA &80,X (indexed base).
        binpath = tmp_path / "m.bin"
        binpath.write_bytes(bytes([0xA5, 0x80, 0x95, 0x80, 0x60]))
        d = Disassembler.create(cpu="6502")
        d.load(binpath, 0x8000)
        d.entry(0x8000)
        d.label(0x80, "zp_mixed")
        text = str(d.disassemble().render("beebasm"))
        assert (
            "&80 referenced 1 time by &8000; "
            "also used as index base 1 time by &8002"
        ) in text


class TestMemoryMapSplit:

    def _render_json(self, tmp_path, *, mark_base):
        d = _program(tmp_path)
        d.label(0x70, "zp_direct", description="directly read", access="r")
        if mark_base:
            d.index_base(0x80, "zp_base", description="indexing base")
        else:
            d.label(0x80, "zp_base", description="indexing base", access="rw")
        return d.disassemble().render(JsonRenderer()).data

    def test_direct_location_appears_in_memory_map(self, tmp_path):
        data = self._render_json(tmp_path, mark_base=True)
        names = {row["name"] for row in data["memory_map"]}
        assert "zp_direct" in names
        assert "zp_base" not in names

    def test_indexed_base_appears_in_index_bases(self, tmp_path):
        data = self._render_json(tmp_path, mark_base=True)
        bases = {row["name"] for row in data["index_bases"]}
        assert bases == {"zp_base"}
        # Description is preserved so the base is still documented.
        row = next(r for r in data["index_bases"] if r["name"] == "zp_base")
        assert row["description"] == "indexing base"
        # The section is implicit; the redundant access value is dropped.
        assert "access" not in row

    def test_without_index_base_marker_base_falls_back_to_memory_map(self, tmp_path):
        # Author's choice: a base annotated with plain label()+access
        # still lands on the fixed-location map (no auto-suppression).
        data = self._render_json(tmp_path, mark_base=False)
        names = {row["name"] for row in data["memory_map"]}
        assert {"zp_direct", "zp_base"} <= names
        assert data["index_bases"] == []


class TestUnannotatedBaseStaysOffTheMap:

    def test_bare_indexed_base_is_not_a_memory_location(self, tmp_path):
        # &80 is referenced only as an index base and carries no
        # author metadata → it must not appear as an owned location.
        d = _program(tmp_path)
        data = d.disassemble().render(JsonRenderer()).data
        map_addrs = {row["addr"] for row in data["memory_map"]}
        base_addrs = {row["addr"] for row in data["index_bases"]}
        assert 0x80 not in map_addrs
        assert 0x80 not in base_addrs
