"""Unit tests for the NMOS 6502 CPU plug-in.

Pins the load-bearing properties of the instruction table — specific
opcode bytes resolve to the right ``(operation, addressing_mode,
flow_control)`` triples; addressing-mode operand lengths are correct;
the table covers exactly the documented opcodes. Includes the
canonical ``(JMP, INDIRECT) → JMI`` test that motivates the
renderer-agnostic Opcode design (D-021).
"""

from dasmos.cpu import FlowControl, Opcode, OperandKind, create_cpu
from dasmos.ext.cpus.nmos6502 import (
    OPCODES,
    AddressingMode,
    Nmos6502Cpu,
    Operation,
)


class TestPluginRegistration:

    def test_loadable_via_stevedore(self):
        cpu = create_cpu("nmos6502")
        assert isinstance(cpu, Nmos6502Cpu)
        assert cpu.name == "nmos6502"

    def test_address_space_is_64k(self):
        cpu = Nmos6502Cpu()
        assert cpu.address_space_size == 0x10000


class TestOperationEnum:

    def test_has_56_documented_mnemonics(self):
        # The classic NMOS 6502 has 56 distinct mnemonics.
        assert len(Operation) == 56

    def test_member_values_are_lowercase_canonical(self):
        # The default_mnemonic() of an Opcode returns operation.value;
        # for the canonical MOS form it must be lowercase ASCII.
        for op in Operation:
            assert op.value == op.name.lower()


class TestAddressingModeEnum:

    def test_has_13_modes(self):
        assert len(AddressingMode) == 13

    def test_implied_and_accumulator_have_zero_operand_length(self):
        assert AddressingMode.IMPLIED.operand_length == 0
        assert AddressingMode.ACCUMULATOR.operand_length == 0

    def test_byte_modes_have_one_operand_byte(self):
        for mode in (
            AddressingMode.IMMEDIATE,
            AddressingMode.ZERO_PAGE,
            AddressingMode.ZERO_PAGE_X,
            AddressingMode.ZERO_PAGE_Y,
            AddressingMode.INDEXED_INDIRECT,
            AddressingMode.INDIRECT_INDEXED,
            AddressingMode.RELATIVE,
        ):
            assert mode.operand_length == 1, f"{mode.name} should be 1-byte"

    def test_word_modes_have_two_operand_bytes(self):
        for mode in (
            AddressingMode.ABSOLUTE,
            AddressingMode.ABSOLUTE_X,
            AddressingMode.ABSOLUTE_Y,
            AddressingMode.INDIRECT,
        ):
            assert mode.operand_length == 2, f"{mode.name} should be 2-byte"

    def test_operand_kinds_are_correct(self):
        assert AddressingMode.IMPLIED.operand_kind is OperandKind.NONE
        assert AddressingMode.ACCUMULATOR.operand_kind is OperandKind.NONE
        assert AddressingMode.IMMEDIATE.operand_kind is OperandKind.IMMEDIATE
        assert AddressingMode.ZERO_PAGE.operand_kind is OperandKind.ADDRESS_8
        assert AddressingMode.ABSOLUTE.operand_kind is OperandKind.ADDRESS_16
        assert AddressingMode.RELATIVE.operand_kind is OperandKind.RELATIVE_OFFSET

    def test_aliasing_hazard_does_not_recur(self):
        # Regression: ABSOLUTE / ABSOLUTE_X / ABSOLUTE_Y / INDIRECT
        # all share (operand_length=2, operand_kind=ADDRESS_16). Without
        # the leading label string in the value tuple, Python's Enum
        # collapses them into aliases of ABSOLUTE. The label fix
        # makes each member's value unique.
        assert AddressingMode.ABSOLUTE is not AddressingMode.INDIRECT
        assert AddressingMode.ABSOLUTE is not AddressingMode.ABSOLUTE_X
        assert AddressingMode.ABSOLUTE is not AddressingMode.ABSOLUTE_Y
        assert AddressingMode.ZERO_PAGE is not AddressingMode.ZERO_PAGE_X
        assert AddressingMode.ZERO_PAGE is not AddressingMode.ZERO_PAGE_Y
        assert AddressingMode.IMPLIED is not AddressingMode.ACCUMULATOR
        assert AddressingMode.INDEXED_INDIRECT is not AddressingMode.INDIRECT_INDEXED


class TestOpcodeTable:

    def test_has_151_documented_opcodes(self):
        assert len(OPCODES) == 151

    def test_all_keys_are_valid_byte_values(self):
        for key in OPCODES:
            assert isinstance(key, int)
            assert 0x00 <= key <= 0xFF

    def test_every_value_is_an_opcode(self):
        for key, value in OPCODES.items():
            assert isinstance(value, Opcode), f"0x{key:02x} -> {value!r}"


class TestSpotCheckedOpcodes:
    """Pin a representative selection of opcodes against the operation,
    addressing-mode and flow-control they should map to.
    """

    def test_lda_immediate(self):
        op = OPCODES[0xA9]
        assert op.operation is Operation.LDA
        assert op.addressing_mode is AddressingMode.IMMEDIATE
        assert op.flow_control is FlowControl.SEQUENTIAL
        assert op.length() == 2

    def test_lda_zero_page(self):
        op = OPCODES[0xA5]
        assert op.operation is Operation.LDA
        assert op.addressing_mode is AddressingMode.ZERO_PAGE
        assert op.length() == 2

    def test_lda_absolute(self):
        op = OPCODES[0xAD]
        assert op.operation is Operation.LDA
        assert op.addressing_mode is AddressingMode.ABSOLUTE
        assert op.length() == 3

    def test_lda_indirect_indexed(self):
        # (zp),Y form
        op = OPCODES[0xB1]
        assert op.operation is Operation.LDA
        assert op.addressing_mode is AddressingMode.INDIRECT_INDEXED

    def test_jmp_absolute(self):
        op = OPCODES[0x4C]
        assert op.operation is Operation.JMP
        assert op.addressing_mode is AddressingMode.ABSOLUTE
        assert op.flow_control is FlowControl.JUMP

    def test_jmp_indirect(self):
        # The motivating example from the second stardot thread:
        # MASM renders this as "JMI", Beebasm as "JMP". The IR
        # carries (JMP, INDIRECT, JUMP) and lets renderers decide.
        op = OPCODES[0x6C]
        assert op.operation is Operation.JMP
        assert op.addressing_mode is AddressingMode.INDIRECT
        assert op.flow_control is FlowControl.JUMP

    def test_jsr(self):
        op = OPCODES[0x20]
        assert op.operation is Operation.JSR
        assert op.addressing_mode is AddressingMode.ABSOLUTE
        assert op.flow_control is FlowControl.SUBROUTINE_CALL

    def test_rts(self):
        op = OPCODES[0x60]
        assert op.operation is Operation.RTS
        assert op.addressing_mode is AddressingMode.IMPLIED
        assert op.flow_control is FlowControl.RETURN

    def test_rti(self):
        op = OPCODES[0x40]
        assert op.operation is Operation.RTI
        assert op.flow_control is FlowControl.RETURN

    def test_brk_is_break_not_return(self):
        # py8dis modelled BRK as OpcodeReturn; dasmos has a distinct
        # FlowControl.BREAK to surface its semantics.
        op = OPCODES[0x00]
        assert op.operation is Operation.BRK
        assert op.flow_control is FlowControl.BREAK

    def test_bne_is_conditional_branch_relative(self):
        op = OPCODES[0xD0]
        assert op.operation is Operation.BNE
        assert op.addressing_mode is AddressingMode.RELATIVE
        assert op.flow_control is FlowControl.CONDITIONAL_BRANCH

    def test_nop(self):
        op = OPCODES[0xEA]
        assert op.operation is Operation.NOP
        assert op.addressing_mode is AddressingMode.IMPLIED
        assert op.flow_control is FlowControl.SEQUENTIAL


class TestStructuralProperties:
    """Properties that should hold across the table as a whole."""

    def test_every_relative_mode_opcode_is_conditional_branch(self):
        # All 8 NMOS 6502 conditional branches use RELATIVE addressing,
        # and no other opcode does. (BRA on 65C02 is added by the
        # 65C02 plug-in, not here.)
        for byte, op in OPCODES.items():
            if op.addressing_mode is AddressingMode.RELATIVE:
                assert op.flow_control is FlowControl.CONDITIONAL_BRANCH, (
                    f"0x{byte:02x} ({op.operation.name}) is RELATIVE but "
                    f"flow_control is {op.flow_control.name}"
                )
            if op.flow_control is FlowControl.CONDITIONAL_BRANCH:
                assert op.addressing_mode is AddressingMode.RELATIVE

    def test_every_jmp_is_jump_flow_control(self):
        for byte, op in OPCODES.items():
            if op.operation is Operation.JMP:
                assert op.flow_control is FlowControl.JUMP

    def test_jsr_is_the_only_subroutine_call(self):
        sub_calls = [
            (b, op) for b, op in OPCODES.items()
            if op.flow_control is FlowControl.SUBROUTINE_CALL
        ]
        assert len(sub_calls) == 1
        byte, op = sub_calls[0]
        assert byte == 0x20
        assert op.operation is Operation.JSR

    def test_rts_and_rti_are_the_returns(self):
        returns = {
            op.operation
            for op in OPCODES.values()
            if op.flow_control is FlowControl.RETURN
        }
        assert returns == {Operation.RTS, Operation.RTI}

    def test_brk_is_the_only_break(self):
        breaks = [
            (b, op) for b, op in OPCODES.items()
            if op.flow_control is FlowControl.BREAK
        ]
        assert len(breaks) == 1
        assert breaks[0][1].operation is Operation.BRK


class TestRendererMnemonicOverrideEndToEnd:
    """The (JMP, INDIRECT) -> JMI pin from D-021 / the second stardot
    thread, exercised against the real NMOS 6502 table to demonstrate
    that the renderer-agnostic shape works in practice.
    """

    def test_default_renderer_emits_jmp_for_jmp_indirect(self):
        op = OPCODES[0x6C]  # JMP (addr)
        assert op.default_mnemonic() == "jmp"

    def test_masm_style_lookup_emits_jmi_for_jmp_indirect(self):
        op = OPCODES[0x6C]
        masm_overrides = {
            (Operation.JMP, AddressingMode.INDIRECT): "JMI",
            (Operation.LDA, AddressingMode.IMMEDIATE): "LDAIM",
            (Operation.LDA, AddressingMode.INDEXED_INDIRECT): "LDAIX",
            (Operation.LDA, AddressingMode.INDIRECT_INDEXED): "LDAIY",
        }
        key = (op.operation, op.addressing_mode)
        chosen = masm_overrides.get(key, op.default_mnemonic())
        assert chosen == "JMI"

    def test_masm_style_lookup_falls_back_for_unspecified_pairs(self):
        # JSR/abs is not in the override table; falls back to default.
        op = OPCODES[0x20]
        masm_overrides = {
            (Operation.JMP, AddressingMode.INDIRECT): "JMI",
        }
        key = (op.operation, op.addressing_mode)
        chosen = masm_overrides.get(key, op.default_mnemonic())
        assert chosen == "jsr"


# ---------------------------------------------------------------------------
# CpuState tracking — A/X/Y register tracking via Cpu.update_state
# ---------------------------------------------------------------------------


class TestState6502:
    """The 6502 CPU state tracker. Records the previous immediate
    load address per register so post-trace analyzers (OSBYTE
    decoder etc.) can find the LDA #imm that set up a JSR call.
    """

    def _new(self):
        from dasmos.ext.cpus.nmos6502 import Nmos6502Cpu
        return Nmos6502Cpu(), Nmos6502Cpu().initial_state()

    def test_initial_state_is_unknown(self):
        cpu, state = self._new()
        assert state.a.value is None
        assert state.x.value is None
        assert state.y.value is None
        assert state.a.previous_load_imm_addr is None

    def test_lda_immediate_records_value_and_source(self, tmp_path):
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        # LDA #&7c at &1000
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0x7c]))
        memory.load(bin_path, 0x1000)
        opcode = OPCODES[0xa9]
        cpu.update_state(state, opcode, 0x1000, memory)
        assert state.a.value == 0x7c
        assert state.a.previous_load_imm_addr == 0x1000

    def test_lda_absolute_clears_immediate_marker(self, tmp_path):
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        bin_path = tmp_path / "p.bin"
        # LDA #&7c at &1000, then LDA &abcd at &1002 (3 bytes, ad cd ab)
        bin_path.write_bytes(bytes([0xa9, 0x7c, 0xad, 0xcd, 0xab]))
        memory.load(bin_path, 0x1000)
        cpu.update_state(state, OPCODES[0xa9], 0x1000, memory)
        cpu.update_state(state, OPCODES[0xad], 0x1002, memory)
        # Value unknown, no longer "previous load imm"
        assert state.a.value is None
        assert state.a.previous_load_imm_addr is None

    def test_sta_does_not_change_a(self, tmp_path):
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        bin_path = tmp_path / "p.bin"
        # LDA #&7c ; STA &abcd
        bin_path.write_bytes(bytes([0xa9, 0x7c, 0x8d, 0xcd, 0xab]))
        memory.load(bin_path, 0x1000)
        cpu.update_state(state, OPCODES[0xa9], 0x1000, memory)
        cpu.update_state(state, OPCODES[0x8d], 0x1002, memory)
        # STA preserves A — the immediate value and source survive.
        assert state.a.value == 0x7c
        assert state.a.previous_load_imm_addr == 0x1000

    def test_inc_a_clears_immediate_marker(self, tmp_path):
        # Not a 6502 instruction (INC A is 65C02), but tests the
        # general principle: any in-place modification of A clears
        # the previous-load-imm tracking. Use INX (which clears X)
        # as the equivalent test for an NMOS 6502.
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        bin_path = tmp_path / "p.bin"
        # LDX #&05 ; INX
        bin_path.write_bytes(bytes([0xa2, 0x05, 0xe8]))
        memory.load(bin_path, 0x1000)
        cpu.update_state(state, OPCODES[0xa2], 0x1000, memory)
        assert state.x.previous_load_imm_addr == 0x1000
        cpu.update_state(state, OPCODES[0xe8], 0x1002, memory)
        # X was incremented — value updates, but previous_load_imm
        # cleared (the LDX #imm is no longer the source of X's value).
        assert state.x.previous_load_imm_addr is None

    def test_lda_propagates_through_intermediate_sta(self, tmp_path):
        # The whole point of state tracking — an LDA #imm can be
        # detected several instructions before a JSR even when STA
        # / other-register-touching instructions sit between. py8dis
        # gets this; the previous dasmos heuristic missed it.
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        bin_path = tmp_path / "p.bin"
        # LDA #&fd ; STA &70 ; LDX #&00 ; STX &71
        bin_path.write_bytes(bytes([
            0xa9, 0xfd,             # LDA #&fd at &1000
            0x85, 0x70,             # STA &70 at &1002
            0xa2, 0x00,             # LDX #&00 at &1004
            0x86, 0x71,             # STX &71 at &1006
        ]))
        memory.load(bin_path, 0x1000)
        cpu.update_state(state, OPCODES[0xa9], 0x1000, memory)
        cpu.update_state(state, OPCODES[0x85], 0x1002, memory)
        cpu.update_state(state, OPCODES[0xa2], 0x1004, memory)
        cpu.update_state(state, OPCODES[0x86], 0x1006, memory)
        # A's immediate-load tracking survived all the stores.
        assert state.a.previous_load_imm_addr == 0x1000
        assert state.a.value == 0xfd
        # X also tracked.
        assert state.x.previous_load_imm_addr == 0x1004
        assert state.x.value == 0x00

    def test_clone_is_independent(self, tmp_path):
        from dasmos.core.memory import MemoryImage
        cpu, state = self._new()
        memory = MemoryImage(address_space_size=0x10000)
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(bytes([0xa9, 0x7c]))
        memory.load(bin_path, 0x1000)
        cpu.update_state(state, OPCODES[0xa9], 0x1000, memory)
        snapshot = state.clone()
        # Continuing to update the original doesn't mutate the snapshot.
        cpu.update_state(state, OPCODES[0xa9], 0x1000, memory)  # re-LDA
        assert snapshot.a.value == 0x7c
        # Setting the snapshot's A to something else doesn't affect
        # the original.
        snapshot.a.value = 0xff
        assert state.a.value == 0x7c
