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
class TestComments:
    """Driver feature: ``d.comment()`` — attach human commentary to
    a binary address. Comments don't affect the assembled bytes
    (beebasm strips them), so the round-trip property holds; we
    additionally assert that the comment text reaches the rendered
    output at the right relative position.
    """

    def test_before_label_comment_appears_above_line(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """
        from dasmos import Align

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(0x8000, "load the magic number")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; load the magic number" in text
        # Comment is on its own line above the label/code.
        comment_idx = text.index("; load the magic number")
        label_idx = text.index(".start")
        assert comment_idx < label_idx

    def test_inline_comment_appears_after_line(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """
        from dasmos import Align

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(0x8000, "magic number", align=Align.INLINE)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The inline comment lives on the same line as the LDA.
        for line in text.splitlines():
            if "lda #&42" in line:
                assert "; magic number" in line
                break
        else:
            raise AssertionError("LDA line not found in rendered output")

    def test_multiple_comments_at_same_address_preserve_order(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(0x8000, "first")
            d.comment(0x8000, "second")
            d.comment(0x8000, "third")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Three lines, in insertion order, before the .start label.
        first_idx = text.index("; first")
        second_idx = text.index("; second")
        third_idx = text.index("; third")
        label_idx = text.index(".start")
        assert first_idx < second_idx < third_idx < label_idx

    def test_after_label_comment_between_label_and_code(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """
        from dasmos import Align

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(0x8000, "between", align=Align.AFTER_LABEL)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The comment is between .start and lda.
        label_idx = text.index(".start")
        comment_idx = text.index("; between")
        lda_idx = text.index("lda #&42")
        assert label_idx < comment_idx < lda_idx

    def test_after_line_comment_below_code(self, roundtrip_via_beebasm):
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """
        from dasmos import Align

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(0x8000, "trailing block", align=Align.AFTER_LINE)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        lda_idx = text.index("lda #&42")
        comment_idx = text.index("; trailing block")
        rts_idx = text.index("rts")
        assert lda_idx < comment_idx < rts_idx

    def test_comments_at_different_addresses(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            lda #&42
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8005, "helper")
            d.comment(0x8000, "the entry point")
            d.comment(0x8002, "calls the helper")
            d.comment(0x8005, "the helper subroutine")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; the entry point" in text
        assert "; calls the helper" in text
        assert "; the helper subroutine" in text


@pytest.mark.beebasm
class TestExpressionOverrides:
    """Driver feature: ``d.expr(operand_addr, "expression")`` overrides
    the operand text with a user-supplied expression. The trace and
    the underlying bytes are unchanged; only the rendered text differs.
    """

    def test_expr_overrides_immediate_value(self, roundtrip_via_beebasm):
        # LDA #&05 — replace the rendered immediate operand with an
        # arithmetic expression that evaluates to the same value.
        source = """
            org &8000
        .start
            lda #&05
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.expr(0x8001, "&02 + &03")  # operand byte at &8001

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "lda #&02 + &03" in text

    def test_expr_overrides_absolute_address(self, roundtrip_via_beebasm):
        # LDA &1234 — replace the rendered absolute address with an
        # equivalent expression.
        source = """
            org &8000
        .start
            lda &1234
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.expr(0x8001, "&1230 + 4")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "lda &1230 + 4" in text

    def test_expr_overrides_with_label_arithmetic(
        self, roundtrip_via_beebasm,
    ):
        # An expression that does arithmetic on a defined label.
        # The data byte naturally lands at &8004 (after the 3-byte
        # LDA and the 1-byte RTS); reference it via expr arithmetic.
        source = """
            org &8000
        .start
            lda data
            rts
        .data
            equb &00
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "data")
            d.byte(0x8004, 1)
            # Operand byte at &8001 holds &04 (low of &8004).
            d.expr(0x8001, "data + 0")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "lda data + 0" in text

    def test_expr_wins_over_label_at_same_target(
        self, roundtrip_via_beebasm,
    ):
        # When a label exists at the target address AND an expression
        # is registered at the operand byte, the expression wins.
        source = """
            org &8000
        .start
            lda data
            rts
        .data
            equb &00
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "data")
            d.byte(0x8004, 1)
            d.expr(0x8001, "&8004")  # explicit hex; bypasses the label

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Operand is the literal "&8004", not "data".
        for line in text.splitlines():
            if "lda " in line and "data" not in line:
                assert "&8004" in line
                break
        else:
            raise AssertionError("LDA line with literal operand not found")

    def test_expr_with_indexed_addressing(self, roundtrip_via_beebasm):
        # LDA &1234,X — the expression replaces the address part;
        # the ,X suffix is added by the renderer as usual.
        source = """
            org &8000
        .start
            lda &1234,X
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.expr(0x8001, "&1230 + 4")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "lda &1230 + 4,X" in text


@pytest.mark.beebasm
class TestOptionalLabelsAndExternals:
    """Driver feature: ``d.label()`` and ``d.optional_label()`` for
    out-of-range addresses (zero-page workspace, OS calls, hardware
    registers). The renderer emits a ``name = &xxxx`` table at the
    top of the output for any label whose address has no loaded byte
    behind it.

    - Required labels (the default ``d.label()``) always appear in
      the table — they're documentation about the address-space layout.
    - Optional labels (``d.optional_label()``) appear only if the
      generated disassembly actually references them — keeping the
      output uncluttered.
    """

    def test_required_external_label_always_appears_in_table(
        self, roundtrip_via_beebasm,
    ):
        # Even if not referenced, a required label for an out-of-range
        # address (zero-page) shows up in the explicit-definition table.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # &70 is zero page — not in the loaded range.
            d.label(0x70, "userv")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "userv = &70" in text

    def test_optional_external_label_omitted_when_unused(
        self, roundtrip_via_beebasm,
    ):
        # The optional label is registered but the disassembly doesn't
        # reference it — so the renderer omits it.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.optional_label(0xFFEE, "oswrch")
            d.optional_label(0xFFE0, "osrdch")
            d.optional_label(0xFFF4, "osbyte")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "oswrch" not in text
        assert "osrdch" not in text
        assert "osbyte" not in text

    def test_optional_external_label_appears_when_used(
        self, roundtrip_via_beebasm,
    ):
        # The disassembled program calls JSR &FFEE; the label
        # registered there gets emitted in the table AND used as the
        # operand symbol.
        source = """
            org &8000
        .start
            jsr &ffee
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.optional_label(0xFFEE, "oswrch")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Table entry + operand both use the label name.
        assert "oswrch = &ffee" in text
        assert "jsr oswrch" in text

    def test_mixed_required_and_optional_externals(
        self, roundtrip_via_beebasm,
    ):
        import re

        source = """
            org &8000
        .start
            jsr &ffee     ; calls oswrch (used)
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Required: always emit.
            d.label(0x70, "userv")
            d.label(0xFC00, "fred")
            # Optional: emit only the ones referenced.
            d.optional_label(0xFFEE, "oswrch")  # referenced by JSR
            d.optional_label(0xFFE0, "osrdch")  # not referenced

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Required externals appear regardless of usage. The names are
        # padded for alignment so use a regex tolerant of whitespace.
        assert re.search(r"^userv\s*= &70\b", text, re.MULTILINE)
        assert re.search(r"^fred\s*= &fc00\b", text, re.MULTILINE)
        # Used optional appears.
        assert re.search(r"^oswrch\s*= &ffee\b", text, re.MULTILINE)
        # Unused optional doesn't.
        assert "osrdch" not in text

    def test_table_aligns_equals_signs_at_max_name_width(
        self, roundtrip_via_beebasm,
    ):
        # Multiple required externals with different name lengths get
        # their equals signs aligned in the table for readability.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x70, "a")
            d.label(0x71, "longer")
            d.label(0x72, "longest_one")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # All three lines have their `=` at the same column. Easiest
        # check: each line's `=` is at index >= 11 (longest name).
        for needle in ("a", "longer", "longest_one"):
            for line in text.splitlines():
                if line.startswith(needle + " ") or line.startswith(needle + "="):
                    eq_idx = line.index("=")
                    assert eq_idx == len("longest_one") + 1, (
                        f"line {line!r} has = at index {eq_idx}, "
                        f"expected {len('longest_one') + 1}"
                    )
                    break
            else:
                raise AssertionError(f"line for {needle!r} not found in:\n{text}")

    def test_in_range_label_does_not_appear_in_table(
        self, roundtrip_via_beebasm,
    ):
        # A label whose runtime address IS loaded is emitted inline
        # only — never in the explicit table.
        source = """
            org &8000
        .start
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "helper")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Inline form yes; explicit-definition form no.
        assert ".helper" in text
        assert "helper = " not in text


@pytest.mark.beebasm
class TestMoveContext:
    """Driver feature: ``d.add_move()`` + ``d.using_move()`` — tell
    the disassembler that some bytes loaded at one address actually
    execute at a different runtime address (e.g. ROM code copied to
    RAM at boot).

    For the simplest case — moved code that doesn't reference its
    own runtime addresses — the round-trip property holds without
    any pseudopc emission in the renderer. The byte sequence stays
    the same; only the names attached via ``with d.using_move(id):``
    change.

    A richer test (with code that DOES reference its own runtime
    address — branches, JSRs into the moved region) needs proper
    pseudopc-style rendering and lands when ADFS-style relocation
    drivers do (deferred per ADFS port plan).
    """

    def test_add_move_returns_move_id(self, tmp_path):
        # Pure API test — no beebasm round-trip needed.
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"\xa0\x00\x60")
        d = Disassembler.create(cpu="nmos6502")
        d.load(bin_path, 0x8000)
        move_id = d.add_move(
            dest_runtime_addr=0x100,
            src_binary_addr=0x8000,
            length=3,
        )
        # First non-base move id is 1.
        assert move_id == 1
        assert d.moves.is_valid_move_id(move_id)

    def test_using_move_pushes_and_pops(self, tmp_path):
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"\xa0\x00\x60")
        d = Disassembler.create(cpu="nmos6502")
        d.load(bin_path, 0x8000)
        move_id = d.add_move(0x100, 0x8000, 3)
        assert d.moves.active_move_ids == []
        with d.using_move(move_id):
            assert d.moves.active_move_ids == [move_id]
        assert d.moves.active_move_ids == []

    def test_label_inside_using_move_appears_at_moved_address(
        self, roundtrip_via_beebasm,
    ):
        # The simplest end-to-end move test:
        #   - bytes loaded at &8000 (the source address)
        #   - the driver claims they actually execute at &100 (e.g.
        #     zero-page-relative, or copied to RAM at boot)
        #   - using_move(...) wraps the entry registration so the
        #     trace seeds and labels resolve via the move
        #   - the LDY #0 / RTS contains no address references, so
        #     the rebuilt bytes are identical regardless of the
        #     label value.
        source = """
            org &8000
        .anywhere
            ldy #0
            rts
        save "step1.bin", anywhere, P%
        """

        def configure(d):
            # The label "zp_handler" exists at runtime &100; the move
            # tells dasmos that the bytes at binary &8000 are what
            # implements it.
            move_id = d.add_move(
                dest_runtime_addr=0x100,
                src_binary_addr=0x8000,
                length=3,
            )
            with d.using_move(move_id):
                d.entry(0x100, name="zp_handler")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The renderer surfaces the runtime-address label at the
        # binary classification's position.
        assert ".zp_handler" in text

    def test_label_via_using_move_with_explicit_move_id_kwarg(
        self, roundtrip_via_beebasm,
    ):
        # Same flow but with explicit move_id= passed to entry()
        # rather than going through the with-block context.
        # ADFS uses both forms — see commands-sweep memo §3.
        source = """
            org &8000
        .anywhere
            ldx #0
            rts
        save "step1.bin", anywhere, P%
        """

        def configure(d):
            move_id = d.add_move(
                dest_runtime_addr=0x200,
                src_binary_addr=0x8000,
                length=3,
            )
            # No 'with' block — pass move_id directly to label().
            d.entry(0x8000)  # entry seed at binary
            d.label(0x200, "explicit_handler", move_id=move_id)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".explicit_handler" in text

    def test_comment_inside_using_move_routes_to_moved_address(
        self, roundtrip_via_beebasm,
    ):
        # A comment registered inside a using_move block should attach
        # to the binary location corresponding to the runtime address.
        source = """
            org &8000
        .anywhere
            nop
            rts
        save "step1.bin", anywhere, P%
        """

        def configure(d):
            d.entry(0x8000)
            move_id = d.add_move(0x100, 0x8000, 2)
            with d.using_move(move_id):
                d.comment(0x100, "this code runs at zero-page-ish")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; this code runs at zero-page-ish" in text


@pytest.mark.beebasm
class TestSubroutineAndBanner:
    """Driver features: ``subroutine()`` (semantic — entry point +
    optional label + optional banner) and ``banner()`` (visual only —
    decorated comment block, no entry-point registration).

    These are the dasmos C2/C3 split of py8dis's overloaded
    ``subroutine(addr, name, ..., is_entry_point=False)`` idiom — see
    ``docs/design/commands-sweep-memo.md``.
    """

    def test_subroutine_registers_entry_and_label(
        self, roundtrip_via_beebasm,
    ):
        # subroutine() is the all-in-one for code entry points: it
        # always registers the trace seed, and it adds a label when
        # given a name.
        source = """
            org &8000
        .start
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            # Note: subroutine() seeds the trace from start AND from
            # helper. No explicit d.entry() needed.
            d.subroutine(0x8000, name="start")
            d.subroutine(0x8004, name="helper")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".start" in text
        assert ".helper" in text
        assert "jsr helper" in text

    def test_subroutine_with_title_emits_banner(
        self, roundtrip_via_beebasm,
    ):
        # A subroutine() call with title= produces a banner comment
        # block above the entry-point label.
        source = """
            org &8000
        .reset
            cli
            rts
        save "step1.bin", reset, P%
        """

        def configure(d):
            d.subroutine(
                0x8000, name="reset",
                title="reset — entry point on power-on",
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Banner separator line (87 asterisks).
        assert "; " + ("*" * 87) in text
        # Title text.
        assert "; reset — entry point on power-on" in text
        # Label still appears.
        assert ".reset" in text

    def test_subroutine_with_title_and_description(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .ram_test
            ldy #0
            rts
        save "step1.bin", ram_test, P%
        """

        def configure(d):
            d.subroutine(
                0x8000, name="ram_test",
                title="Scan pages from &1800 upward; record top of RAM",
                description=(
                    "Probes pages upward from &1800 by writing &AA and &55\n"
                    "patterns through mem_ptr_lo/mem_ptr_hi (&80/&81)."
                ),
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; Scan pages from &1800 upward" in text
        assert "; Probes pages upward from &1800" in text
        assert "; patterns through mem_ptr_lo/mem_ptr_hi" in text

    def test_banner_visual_only_no_entry_point(
        self, roundtrip_via_beebasm,
    ):
        # banner() does NOT register an entry point. Without an
        # entry, the trace doesn't run — but the leftover pass
        # classifies all loaded bytes as Byte. The banner should
        # still appear above the address.
        source = """
            org &8000
        .data
            equb &11, &22, &33, &44
        save "step1.bin", data, P%
        """

        def configure(d):
            d.label(0x8000, "data")
            d.byte(0x8000, 4)
            d.banner(
                0x8000,
                title="Lookup table",
                description="Four magic bytes used by the bootstrap.",
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; " + ("*" * 87) in text
        assert "; Lookup table" in text
        assert "; Four magic bytes used by the bootstrap." in text
        assert ".data" in text

    def test_banner_above_label_above_code(
        self, roundtrip_via_beebasm,
    ):
        # The banner sits above the label (BEFORE_LABEL alignment),
        # which itself sits above the code line.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.banner(0x8000, title="banner-text")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        banner_idx = text.index("; banner-text")
        label_idx = text.index(".start")
        rts_idx = text.index("rts")
        assert banner_idx < label_idx < rts_idx


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
