"""The trace stops where code runs into bytes declared as data (#58).

A path that reaches bytes the driver has declared as data — with
``byte``, ``string`` and the like, or that a hook classified as inline
data — ends there. Those bytes are not an instruction, so nothing they
happen to look like is followed: no fall-through, no jump, branch or call
target, and no subroutine hook.
"""

import warnings

import pytest

from dasmos.cpu import Opcode
from dasmos.disassembler import Disassembler

# &2000: NOP NOP NOP, then "4C 10 20" (looks like JMP &2010), ten NOPs,
# then LDA #0 ; RTS at &2010.
ISSUE_IMAGE = bytes([0xEA] * 3 + [0x4C, 0x10, 0x20] + [0xEA] * 10 + [0xA9, 0x00, 0x60])


def _ir(tmp_path, image, configure):
    binpath = tmp_path / "in.bin"
    binpath.write_bytes(image)
    d = Disassembler.create("6502")
    d.load(binpath, 0x2000)
    configure(d)
    return d.disassemble()


def _is_code(ir, binary_addr):
    return isinstance(ir.classifications.get_classification(binary_addr), Opcode)


class TestDeclaredData:

    def test_jump_shaped_data_is_not_followed(self, tmp_path):
        def configure(d):
            d.byte(0x2003, 3)
            d.entry(0x2000)

        ir = _ir(tmp_path, ISSUE_IMAGE, configure)
        assert [_is_code(ir, a) for a in (0x2000, 0x2001, 0x2002)] == [True] * 3
        assert not _is_code(ir, 0x2010)
        assert not _is_code(ir, 0x2012)

    def test_declaration_order_makes_no_difference(self, tmp_path):
        def configure(d):
            d.entry(0x2000)
            d.byte(0x2003, 3)

        assert not _is_code(_ir(tmp_path, ISSUE_IMAGE, configure), 0x2010)

    def test_no_fall_through_past_data(self, tmp_path):
        # NOP ; "EA EA" (data) ; NOP ; RTS
        image = bytes([0xEA, 0xEA, 0xEA, 0xEA, 0x60])

        def configure(d):
            d.byte(0x2001, 2)
            d.entry(0x2000)

        ir = _ir(tmp_path, image, configure)
        assert not _is_code(ir, 0x2003)
        assert not _is_code(ir, 0x2004)

    def test_string_shaped_like_jmp_is_not_followed(self, tmp_path):
        # The Dunjunz case: "L. Code" begins 4C 2E 20, which reads as
        # JMP &202E.  &202E holds LDA #0 ; RTS.
        image = bytearray(0x30)
        image[0x00] = 0xEA
        image[0x01:0x08] = b"L. Code"
        image[0x2E:0x30] = bytes([0xA9, 0x00])
        image += bytes([0x60])

        def configure(d):
            d.string(0x2001, 7)
            d.entry(0x2000)

        ir = _ir(tmp_path, bytes(image), configure)
        assert not _is_code(ir, 0x202E)

    def test_branch_shaped_data_is_not_followed(self, tmp_path):
        # NOP ; "D0 02" (looks like BNE +2) ; BRK ; BRK ; LDA #0 ; RTS
        image = bytes([0xEA, 0xD0, 0x02, 0x00, 0x00, 0xA9, 0x00, 0x60])

        def configure(d):
            d.byte(0x2001, 2)
            d.entry(0x2000)

        ir = _ir(tmp_path, image, configure)
        assert not _is_code(ir, 0x2005)

    def test_call_shaped_data_fires_no_hook(self, tmp_path):
        # NOP ; "20 08 20" (looks like JSR &2008) ; RTS ; ... ; &2008 RTS
        image = bytes([0xEA, 0x20, 0x08, 0x20, 0x60, 0, 0, 0, 0x60])
        calls = []

        def configure(d):
            d.byte(0x2001, 3)
            d.hook_subroutine(0x2008, "sub", lambda dis, addr: calls.append(addr))
            d.entry(0x2000)

        ir = _ir(tmp_path, image, configure)
        assert calls == []
        assert not _is_code(ir, 0x2004)

    def test_instruction_whose_operand_is_data_is_not_followed(self, tmp_path):
        # NOP ; JMP &2010, but the JMP's operand bytes are declared data.
        def configure(d):
            d.byte(0x2004, 2)
            d.entry(0x2000)

        ir = _ir(tmp_path, ISSUE_IMAGE, configure)
        assert not _is_code(ir, 0x2003)
        assert not _is_code(ir, 0x2010)


class TestCodeStillFollowed:

    def test_code_reached_by_two_paths_is_followed_from_both(self, tmp_path):
        # &2000 BEQ &2004 ; &2002 BNE &2004... both reach &2004 RTS.
        image = bytes([0xF0, 0x02, 0xD0, 0x00, 0x60])

        def configure(d):
            d.entry(0x2000)

        ir = _ir(tmp_path, image, configure)
        assert all(_is_code(ir, a) for a in (0x2000, 0x2002, 0x2004))

    def test_overlapping_instructions_are_both_followed(self, tmp_path):
        # The BIT-skip idiom: &2000 LDA #1 ; &2002 BIT &02A9 hides
        # &2003 LDA #2, reached by the branch at &2008. Both paths fall
        # through to &2005 STA &70 ; RTS. Only the first decoding can be
        # classified, but the second is still code, not data, and its
        # path is followed.
        image = bytes([
            0xA9, 0x01,             # &2000 LDA #1
            0x2C, 0xA9, 0x02,       # &2002 BIT &02A9 / &2003 LDA #2
            0x85, 0x70,             # &2005 STA &70
            0x60,                   # &2007 RTS
            0xD0, 0xF9,             # &2008 BNE &2003
            0x60,                   # &200A RTS
        ])

        def configure(d):
            d.entry(0x2000)
            d.entry(0x2008)

        ir = _ir(tmp_path, image, configure)
        assert all(_is_code(ir, a) for a in (0x2000, 0x2002, 0x2005, 0x2007, 0x2008))


class TestEntryOntoData:

    def test_entry_onto_data_is_not_traced(self, tmp_path):
        def configure(d):
            d.byte(0x2003, 3)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                d.entry(0x2003)

        assert not _is_code(_ir(tmp_path, ISSUE_IMAGE, configure), 0x2010)

    def test_entry_onto_data_warns_that_it_has_no_effect(self, tmp_path):
        binpath = tmp_path / "in.bin"
        binpath.write_bytes(ISSUE_IMAGE)
        d = Disassembler.create("6502")
        d.load(binpath, 0x2000)
        d.byte(0x2003, 3)
        with pytest.warns(UserWarning, match="no effect"):
            d.entry(0x2003)
