"""Tests for external binary include regions (``d.include_binary``).

Covers issue #44: rendering an owned data region as an assembler
include directive (beebasm ``incbin`` / 64tass ``.binary``) instead of
a wall of ``equb`` lines, plus writing the canonical payload so the
round-trip stays self-consistent.
"""

import pytest

from dasmos.core.classification import ClassificationError, IncludedBinary
from dasmos.core.disassembly import ClassificationError as StoreClassificationError
from dasmos.disassembler import Disassembler, DisassemblerError
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.ext.renderers.json import JsonRenderer
from dasmos.ext.renderers.tass64 import Tass64Renderer


class TestIncludedBinaryClassification:

    def test_holds_length_and_path(self):
        c = IncludedBinary(16, "basic.dat")
        assert c.length() == 16
        assert c.path() == "basic.dat"

    def test_rejects_empty_path(self):
        with pytest.raises(ClassificationError):
            IncludedBinary(16, "")

    def test_rejects_non_positive_length(self):
        with pytest.raises(ClassificationError):
            IncludedBinary(0, "basic.dat")


def _disassembler(tmp_path, data=b"\x60\x01\x02\x03\x04\x05", load_addr=0x1900):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(data)
    d = Disassembler.create(cpu="6502")
    d.load(binpath, load_addr)
    return d


class TestIncludeBinaryDeclaration:

    def test_region_owns_bytes_and_is_not_traced(self, tmp_path):
        # RTS at 0x1900, then a 5-byte include region. The tracer must
        # not enter the region (it's data), and every byte is accounted
        # for (no leftover classification pass needed to cover them).
        d = _disassembler(tmp_path)
        d.entry(0x1900)
        d.include_binary(0x1901, 5, "payload.dat")
        ir = d.disassemble()
        c = ir.classifications.get_classification(0x1901)
        assert isinstance(c, IncludedBinary)
        assert c.length() == 5
        assert c.path() == "payload.dat"

    def test_overlap_raises_without_override(self, tmp_path):
        d = _disassembler(tmp_path)
        d.byte(0x1901, 2)
        with pytest.raises(StoreClassificationError):
            d.include_binary(0x1901, 5, "payload.dat")

    def test_override_clears_conflict(self, tmp_path):
        d = _disassembler(tmp_path)
        d.byte(0x1901, 2)
        d.include_binary(0x1901, 5, "payload.dat", override=True)
        d.entry(0x1900)
        ir = d.disassemble()
        assert isinstance(
            ir.classifications.get_classification(0x1901), IncludedBinary
        )

    def test_after_disassemble_raises(self, tmp_path):
        d = _disassembler(tmp_path)
        d.entry(0x1900)
        d.disassemble()
        with pytest.raises(DisassemblerError):
            d.include_binary(0x1901, 5, "payload.dat")


class TestRendererDirectives:

    def _ir(self, tmp_path):
        d = _disassembler(tmp_path)
        d.entry(0x1900)
        d.include_binary(0x1901, 5, "basic.dat")
        return d.disassemble()

    def test_beebasm_emits_incbin(self, tmp_path):
        text = str(self._ir(tmp_path).render(BeebasmRenderer()))
        assert 'incbin "basic.dat"' in text
        # The opaque bytes must NOT be emitted as equb data.
        assert "equb" not in text.split('incbin "basic.dat"')[1]

    def test_beebasm_org_precedes_incbin(self, tmp_path):
        # An org that positions the PC must precede the include so
        # beebasm places the bytes at the right address. When the region
        # abuts preceding code the load-range org (&1900) suffices; a
        # gap would emit an explicit org at the region start.
        text = str(self._ir(tmp_path).render(BeebasmRenderer()))
        lines = [ln.strip() for ln in text.splitlines()]
        i = lines.index('incbin "basic.dat"')
        assert any(ln.startswith("org ") for ln in lines[:i])

    def test_tass64_emits_binary_directive(self, tmp_path):
        text = str(self._ir(tmp_path).render(Tass64Renderer()))
        assert '.binary "basic.dat"' in text

    def test_stats_footer_counts_included_bytes(self, tmp_path):
        text = str(self._ir(tmp_path).render(BeebasmRenderer()))
        assert "Number of included bytes = 5 bytes" in text
        assert "Number of includes       = 1" in text

    def test_stats_footer_omits_include_lines_when_none(self, tmp_path):
        d = _disassembler(tmp_path)
        d.entry(0x1900)
        text = str(d.disassemble().render(BeebasmRenderer()))
        assert "included bytes" not in text

    def test_json_emits_incbin_item(self, tmp_path):
        data = self._ir(tmp_path).render(JsonRenderer()).data
        incbin = [it for it in data["items"] if it.get("type") == "incbin"]
        assert len(incbin) == 1
        assert incbin[0]["path"] == "basic.dat"
        assert incbin[0]["length"] == 5
        assert incbin[0]["addr"] == 0x1901

    def test_base_default_raises_helpful_error(self, tmp_path):
        # A backend that doesn't override the seam must fail loudly with
        # an actionable message rather than mis-render the region.
        from dasmos.asm_renderer import AssemblerRenderer
        with pytest.raises(NotImplementedError, match="include_binary"):
            AssemblerRenderer.included_binary_directive(
                BeebasmRenderer(), "basic.dat"
            )


class TestWriteIncludedBinaries:

    def test_writes_owned_bytes_to_path(self, tmp_path):
        d = _disassembler(tmp_path, data=b"\x60\xde\xad\xbe\xef")
        d.entry(0x1900)
        d.include_binary(0x1901, 4, "payload.dat")
        ir = d.disassemble()
        outdir = tmp_path / "listing"
        written = ir.write_included_binaries(outdir)
        assert written == [outdir / "payload.dat"]
        assert (outdir / "payload.dat").read_bytes() == b"\xde\xad\xbe\xef"

    def test_no_regions_writes_nothing(self, tmp_path):
        d = _disassembler(tmp_path)
        d.entry(0x1900)
        ir = d.disassemble()
        assert ir.write_included_binaries(tmp_path) == []

    def test_creates_nested_parent_dirs(self, tmp_path):
        d = _disassembler(tmp_path, data=b"\x60\x01\x02")
        d.entry(0x1900)
        d.include_binary(0x1901, 2, "data/nested/payload.dat")
        ir = d.disassemble()
        written = ir.write_included_binaries(tmp_path)
        assert written[0].read_bytes() == b"\x01\x02"
