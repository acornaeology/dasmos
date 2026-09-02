"""Tests for program-level metadata (``d.program`` and ``ProgramInfo``).

Covers the model/declaration layer for issue #45 (exec/reload addresses
for load-and-run programs). Renderer behaviour is tested in the
per-backend renderer test modules.
"""

import pytest

from dasmos.core.program import ProgramError, ProgramInfo
from dasmos.disassembler import Disassembler, DisassemblerError


class TestProgramInfo:

    def test_defaults_are_all_none(self):
        info = ProgramInfo()
        assert info.load_addr is None
        assert info.exec_addr is None
        assert info.reload_addr is None

    def test_holds_declared_addresses(self):
        info = ProgramInfo(load_addr=0x1900, exec_addr=0x3906, reload_addr=0x1900)
        assert info.load_addr == 0x1900
        assert info.exec_addr == 0x3906
        assert info.reload_addr == 0x1900

    def test_is_frozen(self):
        info = ProgramInfo(exec_addr=0x3906)
        with pytest.raises(Exception):
            info.exec_addr = 0x1234  # type: ignore[misc]

    @pytest.mark.parametrize("bad", [-1, "x", 1.5, True])
    def test_rejects_invalid_addresses(self, bad):
        with pytest.raises(ProgramError):
            ProgramInfo(exec_addr=bad)


class TestProgramDeclaration:

    def _disassembler(self, tmp_path):
        binpath = tmp_path / "p.bin"
        binpath.write_bytes(b"\x60")
        d = Disassembler.create(cpu="6502")
        d.load(binpath, 0x1900)
        return d

    def test_program_defaults_to_none(self, tmp_path):
        d = self._disassembler(tmp_path)
        assert d.program_info is None

    def test_program_stores_declared_metadata(self, tmp_path):
        d = self._disassembler(tmp_path)
        d.program(exec_addr=0x3906, reload_addr=0x1900)
        assert d.program_info == ProgramInfo(exec_addr=0x3906, reload_addr=0x1900)

    def test_program_surfaced_on_ir(self, tmp_path):
        d = self._disassembler(tmp_path)
        d.entry(0x1900)
        d.program(exec_addr=0x1909)
        ir = d.disassemble()
        assert ir.program is not None
        assert ir.program.exec_addr == 0x1909

    def test_program_after_disassemble_raises(self, tmp_path):
        d = self._disassembler(tmp_path)
        d.entry(0x1900)
        d.disassemble()
        with pytest.raises(DisassemblerError):
            d.program(exec_addr=0x3906)

    def test_program_rejects_bad_address(self, tmp_path):
        d = self._disassembler(tmp_path)
        with pytest.raises(ProgramError):
            d.program(exec_addr=-5)
