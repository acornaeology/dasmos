"""Driver-feature round-trip tests.

Each test exercises one driver-script API feature (or a small
combination of related features) against a hand-written beebasm
source. The pattern:

  1. Hand-write a tiny beebasm source naming the structure under test.
  2. Assemble it via the real beebasm to get a binary.
  3. Disassemble that binary in dasmos using the driver feature being
     tested (entry, label, byte classification, etc.).
  4. Render the dasmos IR back through the BeebasmRenderer.
  5. Re-assemble the rendered text via beebasm.
  6. Assert the re-assembled binary equals the original byte-for-byte.

Optionally also assert on the rendered text (e.g. "operand uses
label name X" — useful to confirm the driver's annotations actually
propagated through to the output).

The round-trip property is the load-bearing acceptance criterion.
The text assertions are nice-to-have verification of intent.

The shared fixtures (``roundtrip_via_beebasm``,
``disassemble_and_render``, ``assemble_beebasm``) live in
``conftest.py``.
"""

import pytest


# ---------------------------------------------------------------------------
# Wave 1 — basic entry + label
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestEntryAndLabel:
    """Driver features: ``entry()`` + ``label()`` — basic naming."""

    def test_entry_with_name_appears_inline(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """
        text = roundtrip_via_beebasm(
            source=source,
            load_addr=0x8000,
            configure=lambda d: d.entry(0x8000, name="start"),
        )
        # The label name reaches the rendered text.
        assert ".start" in text
        # And the literal hex address didn't leak as a label use.
        assert "lda #&42" in text

    def test_separate_label_call_creates_label_at_address(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .top
            jmp middle
            equb 0, 0, 0
        .middle
            rts
        save "step1.bin", top, P%
        """
        def configure(d):
            d.entry(0x8000, name="top")
            d.label(0x8006, "middle")  # JMP target

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".top" in text
        assert ".middle" in text
        # JMP operand should use the label, not the literal address.
        assert "jmp middle" in text


# ---------------------------------------------------------------------------
# Wave 2 — control-flow label resolution in operands
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestOperandLabelResolution:
    """Drivers expect address operands to use the friendly label name
    when one is registered at the target.
    """

    def test_jsr_uses_label_name_in_operand(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .main
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", main, P%
        """
        def configure(d):
            d.entry(0x8000, name="main")
            d.label(0x8004, "helper")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "jsr helper" in text

    def test_branch_uses_label_name_in_operand(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .top
            lda #0
            beq found
            rts
        .found
            nop
            rts
        save "step1.bin", top, P%
        """
        def configure(d):
            d.entry(0x8000, name="top")
            d.label(0x8005, "found")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "beq found" in text

    def test_absolute_load_uses_label_for_known_addr(
        self, roundtrip_via_beebasm,
    ):
        # An absolute LDA whose operand is a known label.
        source = """
            org &8000
        .start
            lda data
            rts
        .data
            equb &42
        save "step1.bin", start, P%
        """
        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "data")
            d.byte(0x8004, 1)  # explicitly classify the data byte

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "lda data" in text
        assert ".data" in text


# ---------------------------------------------------------------------------
# Wave 3 — explicit data classification
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestDataClassification:
    """Drivers can mix code with explicitly-classified data regions."""

    def test_byte_block(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            jmp code
        .data
            equb &01, &02, &03, &04, &05, &06, &07, &08
        .code
            rts
        save "step1.bin", start, P%
        """
        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8003, "data")
            d.label(0x800B, "code")
            d.byte(0x8003, 8)  # 8 bytes of data

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".data" in text
        # The data block should use equb for each byte.
        assert "equb" in text

    def test_word_block(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            jmp code
        .table
            equw &1234, &5678
        .code
            rts
        save "step1.bin", start, P%
        """
        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8003, "table")
            d.label(0x8007, "code")
            d.word(0x8003, 4)  # 2 words = 4 bytes

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".table" in text
        assert "equw" in text

    def test_fill_block(self, roundtrip_via_beebasm):
        # Sixteen 0xFF bytes between code and the RTS.
        source = """
            org &8000
        .start
            jmp finish
        .padding
            equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff
            equb &ff, &ff, &ff, &ff, &ff, &ff, &ff, &ff
        .finish
            rts
        save "step1.bin", start, P%
        """
        from dasmos.core.classification import Fill

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8003, "padding")
            d.label(0x8013, "finish")
            d.fill(0x8003, 16, 0xFF)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Beebasm's fill uses a FOR/NEXT loop in our renderer.
        assert "for _dasmos_fill%, 1, 16 : equb &ff : next" in text


# ---------------------------------------------------------------------------
# Wave 4 — addressing modes via known sources
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestAddressingModesViaSource:
    """Each addressing mode round-trips. Shorter than the binary-first
    version in test_beebasm.py — these start from human-readable
    sources, so the test reads as a behavioural spec.
    """

    def test_immediate_round_trips(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            lda #&12
            ldx #&34
            ldy #&56
            rts
        save "step1.bin", start, P%
        """
        text = roundtrip_via_beebasm(
            source, 0x8000,
            lambda d: d.entry(0x8000, name="start"),
        )
        assert "lda #&12" in text
        assert "ldx #&34" in text
        assert "ldy #&56" in text

    def test_zero_page_modes_round_trip(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            lda &10
            sta &20,X
            stx &30,Y
            rts
        save "step1.bin", start, P%
        """
        text = roundtrip_via_beebasm(
            source, 0x8000,
            lambda d: d.entry(0x8000, name="start"),
        )
        assert "lda &10" in text
        assert "sta &20,X" in text
        assert "stx &30,Y" in text

    def test_indirect_modes_round_trip(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            lda (&30,X)
            sta (&40),Y
            rts
        save "step1.bin", start, P%
        """
        text = roundtrip_via_beebasm(
            source, 0x8000,
            lambda d: d.entry(0x8000, name="start"),
        )
        assert "lda (&30,X)" in text
        assert "sta (&40),Y" in text

    def test_accumulator_mode_round_trips(self, roundtrip_via_beebasm):
        # All four shift/rotate ops in accumulator mode. Beebasm
        # requires the explicit ``A``.
        source = """
            org &8000
        .start
            asl A
            lsr A
            rol A
            ror A
            rts
        save "step1.bin", start, P%
        """
        text = roundtrip_via_beebasm(
            source, 0x8000,
            lambda d: d.entry(0x8000, name="start"),
        )
        for shift in ("asl A", "lsr A", "rol A", "ror A"):
            assert shift in text


# ---------------------------------------------------------------------------
# Wave 5 — multi-load
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestMultipleLoads:
    """A driver can load multiple binaries into one Disassembler."""

    def test_two_binaries_at_disjoint_addresses(self, tmp_path,
                                                 assemble_beebasm,
                                                 roundtrip_via_beebasm):
        # The round-trip helper currently does a single load; the
        # multi-load case is constructed manually here.
        from dasmos.disassembler import Disassembler

        # Two separate sources assembled into two binaries.
        binary_a = assemble_beebasm("""
            org &8000
        .top_a
            lda #&aa
            rts
        save "a.bin", top_a, P%
        """, name="a")
        binary_b = assemble_beebasm("""
            org &9000
        .top_b
            lda #&bb
            rts
        save "b.bin", top_b, P%
        """, name="b")

        path_a = tmp_path / "load_a.bin"
        path_a.write_bytes(binary_a)
        path_b = tmp_path / "load_b.bin"
        path_b.write_bytes(binary_b)

        d = Disassembler.create(cpu="nmos6502")
        d.load(path_a, 0x8000)
        d.load(path_b, 0x9000)
        d.entry(0x8000, name="top_a")
        d.entry(0x9000, name="top_b")
        ir = d.disassemble()

        # Two distinct loaded ranges visible in the IR.
        ranges = ir.memory.load_ranges
        assert len(ranges) == 2

        # Both classifications reached.
        from dasmos.cpu import Opcode
        assert isinstance(ir.classifications.get_classification(0x8000), Opcode)
        assert isinstance(ir.classifications.get_classification(0x9000), Opcode)
