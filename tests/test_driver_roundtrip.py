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
        # Pin operand SHAPE (`,X` / `,Y`); auto-label generation would
        # replace the literal hex with a synthesised symbol, so disable
        # it for clarity.
        source = """
            org &8000
        .start
            lda &10
            sta &20,X
            stx &30,Y
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.auto_labels_enabled = False
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
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

        def configure(d):
            d.auto_labels_enabled = False
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
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
        # Three comments at the SAME (address, alignment) — this
        # SHOULD trigger the duplicate-comment UserWarning (added
        # to help drivers spot accidental copy-paste). The behaviour
        # is still that all three comments are emitted in insertion
        # order, so the warning is informational, not an error.
        import warnings
        source = """
            org &8000
        .start
            lda #&42
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
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
class TestLocalLabels:
    """Driver feature: ``d.local_label(addr, name, start, end)`` —
    define a name at ``addr`` that's used as the operand symbol only
    when the using site falls within ``[start, end)``.

    Beebasm has no native local-label syntax, so we express scoped
    names as explicit ``name = &xxxx`` definitions in the table at
    the top of the output. The renderer's operand resolution prefers
    the local name when in scope; outside the scope, the explicit
    name (if any) or the literal hex appears instead.
    """

    def test_local_label_used_in_scope(self, roundtrip_via_beebasm):
        # JMP at &8000 jumps to &8003; local label "loop" at &8003 has
        # scope [&8000, &8003) — covers the JMP's using site.
        source = """
            org &8000
        .start
            jmp here
        .here
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Local label "loop" at &8003 valid in [&8000, &8003)
            # which includes the JMP's address.
            d.local_label(0x8003, "loop", 0x8000, 0x8003)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Local label gets an explicit definition in the table.
        assert "loop" in text
        # And the JMP operand uses the local name (in scope).
        assert "jmp loop" in text

    def test_local_label_out_of_scope_uses_other_name_or_hex(
        self, roundtrip_via_beebasm,
    ):
        # The local label is at &8003 with scope [&8005, &800A); the
        # JMP at &8000 is OUT of scope, so the local name is not used.
        # Without an explicit name at &8003 and with auto-labels off,
        # the operand falls back to the literal hex address. (With
        # auto-labels on it'd resolve to a synthesised name like
        # ``c8003``, which is also correct behaviour but not what
        # this test is pinning.)
        source = """
            org &8000
        .start
            jmp here
        .here
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.auto_labels_enabled = False
            d.entry(0x8000, name="start")
            # &8000 is NOT in [&8005, &800A).
            d.local_label(0x8003, "loop", 0x8005, 0x800A)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Local label still gets a table entry…
        assert "loop = &8003" in text
        # …but the JMP operand uses the literal hex (using site
        # &8000 is out of scope, auto-labels off).
        assert "jmp &8003" in text

    def test_local_label_overrides_explicit_name_in_scope(
        self, roundtrip_via_beebasm,
    ):
        # Two names at &8003: explicit "global_target" + local "loop"
        # in scope [&8000, &8003). The JMP within scope uses "loop";
        # an external reference (out of scope) would use "global_target".
        source = """
            org &8000
        .start
            jmp here
        .here
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8003, "global_target")
            d.local_label(0x8003, "loop", 0x8000, 0x8003)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # JMP in scope -> local name wins.
        assert "jmp loop" in text
        # The explicit name still appears at the inline classification
        # (not in the operand of this JMP).
        assert ".global_target" in text


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

    def test_external_label_description_renders_as_inline_comment(
        self, roundtrip_via_beebasm,
    ):
        """A ``description=`` passed to ``d.label()`` for an out-of-
        range address surfaces as an inline ``;`` comment trailing the
        ``name = &xxxx`` definition. Multi-line descriptions are
        collapsed to a single line.

        Mirrors py8dis's rendering of label descriptions — the load-
        bearing piece of annotation fidelity that distinguishes a
        memory-map listing from a bare equate table.
        """
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(
                0x70, "userv",
                description="User vector — JMPed through on OSBYTE 0.",
            )
            d.label(
                0x80, "mem_ptr_lo",
                description=(
                    "Low byte of the indirect pointer.\n"
                    "Paired with mem_ptr_hi."
                ),
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Description appears inline as a comment after the equate.
        # The description text shows up verbatim (newline collapsed
        # to space).
        assert "User vector — JMPed through on OSBYTE 0." in text
        assert (
            "Low byte of the indirect pointer. Paired with mem_ptr_hi."
            in text
        )
        # The description sits on the same line as the equate.
        for line in text.splitlines():
            if "userv" in line and "= &70" in line:
                assert "; User vector" in line, (
                    f"description not inline on equate line: {line!r}"
                )
                break
        else:
            raise AssertionError("userv equate line not found in output")

    def test_memory_locations_header_above_equate_table(
        self, roundtrip_via_beebasm,
    ):
        """When the equate table has at least one entry, a
        ``; Memory locations`` header sits above it. Mirrors py8dis's
        section header so the rendered output reads as a memory map
        rather than a bare equate dump."""
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x70, "userv")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Header appears, and appears BEFORE the equate.
        header_idx = text.index("; Memory locations")
        userv_idx = text.index("userv")
        assert header_idx < userv_idx

    def test_no_memory_locations_header_when_table_empty(
        self, roundtrip_via_beebasm,
    ):
        # Without any out-of-range labels, no equate table → no header.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "Memory locations" not in text

    def test_external_label_without_description_emits_bare_equate(
        self, roundtrip_via_beebasm,
    ):
        # No regression: labels without a description still emit the
        # bare ``name = &xxxx`` form (no trailing `;`).
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x70, "userv")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        for line in text.splitlines():
            if "userv" in line and "= &70" in line:
                # Bare equate — no comment after the value.
                assert ";" not in line, (
                    f"unexpected trailing comment: {line!r}"
                )
                break
        else:
            raise AssertionError("userv equate line not found")


@pytest.mark.beebasm
class TestCodePtr:
    """Driver feature: ``d.code_ptr(addr_lo, addr_hi=None, *, offset=0)``
    and the RTS-flavoured ``d.rts_code_ptr(addr_lo, addr_hi=None)``.

    Mark two bytes of data as the address of a subroutine: read the
    bytes, register an entry point at the computed target, classify
    the source bytes appropriately, and set per-byte expression
    overrides so the source bytes render symbolically.
    """

    def test_adjacent_bytes_emits_equw_with_label_expr(
        self, roundtrip_via_beebasm,
    ):
        # Two adjacent bytes (low at &8000, high at &8001) point to a
        # subroutine at &8002. Renderer should emit ``equw target``
        # for the pair and seed the trace from &8002.
        source = """
            org &8000
        .ptr_table
            equw target
        .target
            rts
        save "step1.bin", ptr_table, P%
        """

        def configure(d):
            d.code_ptr(0x8000, label_name="target")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "equw target" in text

    def test_non_adjacent_bytes_emits_lo_hi_expressions(
        self, roundtrip_via_beebasm,
    ):
        # Low byte at &8000, high byte separated at &8002 — emit
        # two ``equb`` lines with beebasm's lo/hi expression
        # operators.
        source = """
            org &8000
            equb &04   ; low half of &8004 (target)
            equb &00   ; filler between the halves
            equb &80   ; high half of &8004
        .target
            rts
        save "step1.bin", $8000, P%
        """

        def configure(d):
            d.code_ptr(0x8000, 0x8002, label_name="target")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Both halves render via the lo/hi operators on the label.
        # py8dis-fork format: ``<(target)`` / ``>(target)`` (no space —
        # standard 6502 lo/hi operator notation).
        assert "<(target)" in text
        assert ">(target)" in text

    def test_rts_flavour_subtracts_one(
        self, roundtrip_via_beebasm,
    ):
        # RTS-pop-then-INC means stored bytes contain target-1; the
        # rendered expression compensates.
        source = """
            org &8000
            equw target - 1   ; bytes 03 80 (target = &8004)
        .target
            rts
        save "step1.bin", $8000, P%
        """

        def configure(d):
            d.rts_code_ptr(0x8000, label_name="target")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Rendered expression includes the -1 offset.
        assert "equw target-1" in text


@pytest.mark.beebasm
class TestStringz:
    """Driver feature: ``d.stringz(addr)`` — classify a NUL-terminated
    string starting at addr; returns the runtime address of the byte
    after the terminator. Lifted from py8dis."""

    def test_classifies_string_through_nul(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            equs "Hi", &00, &60     ; "Hi\\0" + RTS-as-data
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.stringz(0x8000)  # classify "Hi\0" — 3 bytes inc. NUL

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The string text appears in the output as equs-or-equb.
        # Round-trip succeeds, which is the load-bearing assertion.
        assert ".start" in text

    def test_returns_address_after_terminator(self, tmp_path):
        # API check: stringz returns the runtime address of the byte
        # AFTER the NUL — so chained calls walk a sequence of
        # NUL-terminated strings.
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"abc\x00def\x00\x60")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        next_addr = d.stringz(0x8000)
        assert next_addr == 0x8004  # "abc\0" = 4 bytes, next at &8004
        next_addr = d.stringz(next_addr)
        assert next_addr == 0x8008  # "def\0" = 4 bytes, next at &8008

    def test_raises_on_unterminated_string(self, tmp_path):
        # No NUL byte before unloaded memory → diagnostic error.
        from dasmos.disassembler import Disassembler, DisassemblerError
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"abcdef")  # no NUL
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        with pytest.raises(DisassemblerError, match="without finding a NUL"):
            d.stringz(0x8000)


class TestStringcr:
    """Driver feature: ``d.stringcr(addr)`` — classify a CR-terminated
    string (terminator &0D, BBC OS line convention). Mirrors
    :class:`TestStringz` with the terminator byte changed.
    """

    def test_returns_address_after_terminator(self, tmp_path):
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"abc\x0ddef\x0d\x60")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        next_addr = d.stringcr(0x8000)
        assert next_addr == 0x8004  # "abc\r" = 4 bytes
        next_addr = d.stringcr(next_addr)
        assert next_addr == 0x8008  # "def\r" = 4 bytes

    def test_raises_on_unterminated_string(self, tmp_path):
        from dasmos.disassembler import Disassembler, DisassemblerError
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"abcdef")  # no CR
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        with pytest.raises(DisassemblerError, match="without finding a CR"):
            d.stringcr(0x8000)


@pytest.mark.beebasm
class TestMultiLineCommentRendering:
    """A ``d.comment(addr, text)`` whose text contains paragraph
    breaks (``\\n\\n``) should render as one ``;`` line per output
    line — not bare text on the second line that beebasm would
    choke on.

    Comment text is parsed as Markdown (CommonMark + GFM tables +
    the custom ``[label](address:HEX)`` URI scheme), so a SINGLE
    ``\\n`` is a soft break and joins with a space. Use ``\\n\\n``
    to start a new paragraph (and therefore a new ``;`` line in
    asm).
    """

    def test_each_paragraph_carries_comment_prefix(
        self, roundtrip_via_beebasm,
    ):
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(
                0x8000,
                "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Each paragraph is a separate ``;`` line in the output.
        assert "; First paragraph." in text
        assert "; Second paragraph." in text
        assert "; Third paragraph." in text

    def test_word_wrap_false_preserves_literal_layout(
        self, roundtrip_via_beebasm,
    ):
        # ``word_wrap=False`` skips Markdown parsing — the
        # source's literal layout (including raw single-newline
        # line breaks) is preserved. Use this for things like
        # banner separators where rows of punctuation would
        # otherwise be interpreted as Markdown structural markers.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(
                0x8000,
                "Literal first line\nLiteral second line",
                word_wrap=False,
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; Literal first line" in text
        assert "; Literal second line" in text

    def test_address_link_in_comment_collapses_to_label(
        self, roundtrip_via_beebasm,
    ):
        # Comment text uses the custom ``[label](address:HEX)``
        # cross-reference URI documented in
        # ``acornaeology.github.io/AUTHORING.md`` §1.1. The asm
        # output collapses to plain ``label`` (or ``label (&HEX)``
        # with the ``?hex`` flag); the structured JSON renderer
        # preserves the source markdown verbatim for downstream HTML
        # processors.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        from dasmos import Align

        def configure(d):
            d.entry(0x8000, name="start")
            d.comment(
                0x8000,
                "see [foo](address:E000) and [bar](address:F000?hex)",
                align=Align.INLINE,
            )

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The ``foo`` link strips to label-only; the ``bar`` link
        # appends the upper-cased hex.
        assert "see foo and bar (&F000)" in text
        # The raw markdown URI form is gone from the asm.
        assert "address:" not in text


@pytest.mark.beebasm
class TestSubroutineHooks:
    """Driver feature: ``d.hook_subroutine(addr, name, hook)`` registers
    a callable that the trace fires when it sees a JSR to ``addr``.

    The hook decides where the trace continues after the JSR — most
    commonly used for inline-string idioms where the bytes following
    the JSR are payload data rather than the next instruction.

    The bundled :func:`dasmos.hooks.stringhi_hook` ports py8dis's
    behaviour: classify the bytes after the JSR as a String terminated
    by a byte with bit 7 set; trace continues at the terminator (which
    typically executes as a 1-byte NOP opcode).
    """

    def test_stringhi_hook_classifies_inline_string(
        self, roundtrip_via_beebasm,
    ):
        # ``print_str`` is an out-of-range stub at &FE98 (mirrors the
        # tube-client driver). A JSR to it is followed by an ASCII
        # string terminated by &EA (NOP, bit 7 set), then code.
        # After the inline string, execution continues at the &EA
        # terminator (NOP, 1-byte opcode), then the rts.
        source = """
            org &8000
        .start
            jsr &fe98
            equs "Hi", &ea
            rts
        save "step1.bin", start, P%
        """

        from dasmos.hooks import stringhi_hook

        def configure(d):
            d.entry(0x8000, name="start")
            d.hook_subroutine(0xFE98, "print_str", stringhi_hook)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The "Hi" bytes are classified as a string (renders as equs).
        # The &EA terminator is then traced as an opcode (nop).
        assert "equs" in text and '"Hi"' in text
        assert "nop" in text
        assert "rts" in text

    def test_hook_subroutine_creates_optional_label(self):
        """The ``name`` argument registers an optional label at the
        target address — same as ``optional_label(addr, name)``. This
        means the JSR's operand resolves to the registered name."""
        from dasmos.disassembler import Disassembler
        from dasmos.hooks import stringhi_hook
        d = Disassembler.create(cpu="6502")
        d.hook_subroutine(0xFE98, "print_str", stringhi_hook)
        # Label appears in the label manager.
        label = d.labels.get_label(0xFE98)
        assert label is not None
        assert "print_str" in label.explicit_name_texts()


@pytest.mark.beebasm
class TestCrossReferences:
    """Driver feature: the renderer emits cross-reference annotations
    that record how each label is used by other instructions:

    - Inline summary above an in-range label:
      ``; &xxxx referenced N time(s) by &yyyy, &zzzz, …``
    - End-of-file frequency table:
      ``; Label references by decreasing frequency:`` followed by
      ``;     name:  N`` lines sorted by count descending.

    Both data sources are populated from operand resolution: every
    time an operand resolves to a label name, that use site is
    recorded against the label."""

    def test_inline_xref_summary_above_referenced_label(
        self, roundtrip_via_beebasm,
    ):
        # ``helper`` is jsr'd from one site → the renderer emits
        # ``; &<helper-addr> referenced 1 time by &<jsr-addr>``
        # immediately above the inline ``.helper`` label.
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
        # Find the .helper line and check what's right above it.
        lines = text.splitlines()
        helper_idx = next(
            i for i, line in enumerate(lines) if line.strip() == ".helper"
        )
        prev = lines[helper_idx - 1]
        # Singular: "1 time", not "1 times".
        assert "; &8004 referenced 1 time by &8000" == prev.strip(), (
            f"unexpected xref line above .helper: {prev!r}"
        )

    def test_inline_xref_plural_lists_all_sites(
        self, roundtrip_via_beebasm,
    ):
        # ``loop_top`` is branched to from two sites → the summary
        # uses "2 times" and lists both ref sites in address order.
        source = """
            org &8000
        .start
            ldx #5
        .loop_top
            dex
            beq done
            jmp loop_top
        .done
            jsr loop_top
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Layout (from beebasm): ldx #5 @8000(2), dex @8002(1),
            # beq done @8003(2), jmp loop_top @8005(3), jsr loop_top
            # @8008(3), rts @800b(1). Total 12 bytes.
            d.label(0x8002, "loop_top")
            d.label(0x8008, "done")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        lines = text.splitlines()
        loop_idx = next(
            i for i, line in enumerate(lines) if line.strip() == ".loop_top"
        )
        prev = lines[loop_idx - 1].strip()
        # Plural form: jmp at &8005 and jsr at &8008 both reference
        # loop_top.
        assert prev.startswith("; &8002 referenced 2 times by &"), (
            f"expected plural xref above .loop_top, got: {prev!r}"
        )
        assert "&8005" in prev
        assert "&8008" in prev

    def test_unreferenced_label_has_no_xref_summary(
        self, roundtrip_via_beebasm,
    ):
        # ``orphan`` is defined but no operand resolves to it; no
        # xref summary is emitted above it.
        source = """
            org &8000
        .start
            rts
        .orphan
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.entry(0x8001, name="orphan")  # so the trace covers it

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        lines = text.splitlines()
        orphan_idx = next(
            i for i, line in enumerate(lines) if line.strip() == ".orphan"
        )
        prev = lines[orphan_idx - 1].strip()
        assert "referenced" not in prev, (
            f"unexpected xref line above unreferenced .orphan: {prev!r}"
        )

    def test_end_of_file_frequency_table_descending(
        self, roundtrip_via_beebasm,
    ):
        # Two labels with different reference counts — the frequency
        # table at the end of the output sorts them in descending order.
        source = """
            org &8000
        .start
            jsr popular
            jsr popular
            jsr popular
            jsr quiet
            rts
        .popular
            rts
        .quiet
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x800d, "popular")
            d.label(0x800e, "quiet")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The frequency-table header appears.
        assert "; Label references by decreasing frequency:" in text
        # `popular` (3 refs) appears before `quiet` (1 ref).
        popular_pos = text.index("popular:")
        quiet_pos = text.index("quiet:")
        assert popular_pos < quiet_pos, (
            "frequency table should list popular before quiet"
        )
        # Counts present.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(";") and "popular:" in stripped:
                assert stripped.endswith(" 3"), (
                    f"expected popular count 3 in {stripped!r}"
                )
            elif stripped.startswith(";") and "quiet:" in stripped:
                assert stripped.endswith(" 1"), (
                    f"expected quiet count 1 in {stripped!r}"
                )

    def test_unreferenced_label_omitted_from_frequency_table(
        self, roundtrip_via_beebasm,
    ):
        # An unreferenced label doesn't pollute the frequency table.
        source = """
            org &8000
        .start
            jsr used
            rts
        .used
            rts
        .orphan
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.entry(0x8005, name="orphan")
            d.label(0x8004, "used")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Find the frequency table section.
        if "Label references by decreasing frequency" in text:
            table = text.split("Label references by decreasing frequency:")[1]
            assert "orphan" not in table, (
                "orphan should not appear in the frequency table"
            )

    def test_stats_block_emitted_at_end(self, roundtrip_via_beebasm):
        """End-of-file ``; Stats:`` block summarises the disassembly:
        total size, code/data split, instruction count, byte/word/
        string counts. Useful as a quick orientation when reviewing
        the output and as a parity marker against py8dis."""
        source = """
            org &8000
        .start
            lda #&42
            rts
        .data
            equb &01, &02
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8003, "data")
            d.byte(0x8003, 2)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Header line and at least one of the keyword summaries.
        assert "; Stats:" in text
        assert "Total size" in text
        assert "Code" in text
        assert "Data" in text
        assert "instructions" in text


@pytest.mark.beebasm
class TestAutoGeneratedLabels:
    """Driver feature: addresses that are referenced by the disassembled
    code but have no explicit name get a synthesised label name at
    render time. py8dis's scheme:

    - ``l<addr>``      — address has data classification (Byte/Word/etc.)
    - ``c<addr>``      — address has code, no other heuristic matches
    - ``sub_c<addr>``  — all references are JSR (subroutine calls)
    - ``loop_c<addr>`` — single ref, backward branch within loop_limit

    Each prefix is configurable on the renderer constructor so a domain
    label happening to start ``loop_`` (or any other prefix) doesn't
    collide. py8dis defaults are used when no override is supplied.

    Also: a trailing ``; Automatically generated labels:`` footer
    block lists every synthesised name so a reader can scan them at
    a glance.
    """

    def test_unnamed_data_target_gets_data_prefix(
        self, roundtrip_via_beebasm,
    ):
        # &8004 holds a data byte the LDA at &8000 reads; no explicit
        # label, so the renderer synthesises ``data_8004`` and uses
        # it as the operand symbol.
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
            d.byte(0x8004, 1)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Operand resolves to the auto-name.
        assert "lda data_8004" in text
        # Label gets emitted inline at &8004.
        assert ".data_8004" in text

    def test_unnamed_code_target_gets_code_prefix(
        self, roundtrip_via_beebasm,
    ):
        # &8005 is the target of a forward branch (BNE). It holds
        # NOP (not bare RTS) so the return-N rule doesn't fire and
        # the code-prefix heuristic kicks in.
        source = """
            org &8000
        .start
            lda #&00
            bne onwards
            nop
        .onwards
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Don't name &8005 (.onwards in source) so the auto-label
            # path fires.

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The branch operand resolves to the synthesised code_<addr> name.
        assert ".code_8005" in text
        assert "bne code_8005" in text

    def test_jsr_only_target_gets_sub_prefix(
        self, roundtrip_via_beebasm,
    ):
        # The helper is non-trivial (NOP + RTS) so its first byte is
        # NOT a bare RTS — that would trigger the ``return_N`` rule
        # instead. With a multi-instruction helper, JSR-only
        # references pick the ``sub_<addr>`` heuristic.
        source = """
            org &8000
        .start
            jsr helper
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".sub_8007" in text
        assert "jsr sub_8007" in text

    def test_jsr_to_bare_rts_gets_return_n_name(
        self, roundtrip_via_beebasm,
    ):
        # The helper is just RTS — single-byte 0x60. The return-N
        # rule fires (matching py8dis's
        # ``label_return_instructions_numerically``) and the auto-name
        # becomes ``return_1`` rather than the sub-prefix form.
        source = """
            org &8000
        .start
            jsr helper
            rts
        .helper
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".return_1" in text
        assert "jsr return_1" in text
        # The sub-prefix form does NOT appear.
        assert "sub_8004" not in text

    def test_return_n_counter_increments_per_unique_address(
        self, roundtrip_via_beebasm,
    ):
        # Two distinct bare-RTS targets get sequential ids; the
        # counter never reuses a number.
        source = """
            org &8000
        .start
            jsr first
            jsr second
            rts
        .first
            rts
        .second
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".return_1" in text
        assert ".return_2" in text

    def test_return_n_disabled_falls_back_to_code_prefix(
        self, tmp_path, assemble_beebasm,
    ):
        # Setting ``auto_label_return_prefix=None`` opts out of the
        # rule; bare-RTS targets get the standard sub-prefix shape.
        from dasmos.disassembler import Disassembler

        binary = assemble_beebasm("""
            org &8000
        .start
            jsr helper
            rts
        .helper
            rts
        save "step1.bin", start, P%
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)

        d = Disassembler.create(cpu="6502", auto_label_return_prefix=None)
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        text = str(d.disassemble().render("beebasm"))
        assert "return_" not in text
        assert "sub_8004" in text

    def test_backward_branch_target_gets_loop_prefix(
        self, roundtrip_via_beebasm,
    ):
        # A single backward branch (BNE) loops back to a target a few
        # bytes earlier — heuristic picks the ``loop_<addr>`` form.
        source = """
            org &8000
        .start
            ldx #&05
        .loop_start
            dex
            bne loop_start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # No explicit name for &8002 — the dex at the loop top.

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert ".loop_8002" in text
        assert "bne loop_8002" in text

    def test_explicit_label_takes_precedence_over_auto(
        self, roundtrip_via_beebasm,
    ):
        # Even though &8003 is JSR'd to and would otherwise get an
        # auto-name, the explicit ``d.label`` registration wins.
        source = """
            org &8000
        .start
            jsr helper
            rts
        .helper
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "helper")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "sub_8004" not in text
        assert "return_" not in text
        assert "jsr helper" in text

    def test_footer_lists_generated_names(
        self, roundtrip_via_beebasm,
    ):
        # Helper is non-trivial (NOP + RTS) so it picks the sub-prefix
        # form; bare-RTS would route through the return-N rule and
        # produce a different footer entry.
        source = """
            org &8000
        .start
            jsr helper
            lda data
            rts
        .helper
            nop
            rts
        .data
            equb &42
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.byte(0x8009, 1)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; Automatically generated labels:" in text
        # Both synthesised names appear under the footer.
        footer = text.split("Automatically generated labels:")[1]
        assert "sub_8007" in footer
        assert "data_8009" in footer

    def test_no_footer_when_no_labels_generated(
        self, roundtrip_via_beebasm,
    ):
        # Every reachable address has either an explicit label or no
        # references at all; no auto-labels → no footer block.
        source = """
            org &8000
        .start
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "Automatically generated labels" not in text

    def test_configurable_prefixes(self, tmp_path, assemble_beebasm):
        # Custom prefixes flow through to both the inline labels and
        # the operand text. Useful when domain labels happen to start
        # with the default ``data_`` / ``code_`` / ``sub_`` / ``loop_``.
        # Prefixes live on the Disassembler — they're a content
        # decision (analysis), not a rendering one. Helper is NOP+RTS
        # so the return-N rule doesn't intercept the sub-prefix path.
        from dasmos.disassembler import Disassembler

        binary = assemble_beebasm("""
            org &8000
        .start
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)

        d = Disassembler.create(
            cpu="6502",
            auto_label_subroutine_prefix="proc_",
        )
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        text = str(d.disassemble().render("beebasm"))
        assert ".proc_8004" in text
        assert "jsr proc_8004" in text
        # The default ``sub_`` form does NOT appear.
        assert ".sub_" not in text

    def test_porter_compat_prefixes_match_py8dis(
        self, tmp_path, assemble_beebasm,
    ):
        # Drivers ported from py8dis configure the legacy prefixes
        # (``l`` / ``c`` / ``sub_c`` / ``loop_c``) explicitly so the
        # ported output matches py8dis-fork output line-for-line
        # during migration validation.
        from dasmos.disassembler import Disassembler

        binary = assemble_beebasm("""
            org &8000
        .start
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)

        d = Disassembler.create(
            cpu="6502",
            auto_label_data_prefix="l",
            auto_label_code_prefix="c",
            auto_label_subroutine_prefix="sub_c",
            auto_label_loop_prefix="loop_c",
        )
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        text = str(d.disassemble().render("beebasm"))
        assert ".sub_c8004" in text
        assert "jsr sub_c8004" in text

    def test_disabled_emits_no_auto_labels(
        self, tmp_path, assemble_beebasm,
    ):
        # ``auto_labels_enabled=False`` on the Disassembler skips the
        # whole synthesis pass — no labels get added, so renderers see
        # bare addresses and resolve operands to literal hex. The
        # renderer's footer is also empty (no auto-labels to list).
        from dasmos.disassembler import Disassembler

        binary = assemble_beebasm("""
            org &8000
        .start
            jsr helper
            rts
        .helper
            rts
        save "step1.bin", start, P%
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)

        d = Disassembler.create(cpu="6502", auto_labels_enabled=False)
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        text = str(d.disassemble().render("beebasm"))
        assert ".sub_" not in text
        assert "return_" not in text
        assert "Automatically generated labels" not in text
        assert "jsr &8004" in text

    def test_renderer_can_suppress_footer(
        self, tmp_path, assemble_beebasm,
    ):
        # Generation is on (default) but the renderer chooses not to
        # surface the footer — useful for a clean listing where the
        # synthesised names appear inline but no trailing summary.
        # Use a NOP+RTS helper so the auto-name takes the sub-prefix
        # path (instead of the return-N rule).
        from dasmos.disassembler import Disassembler
        from dasmos.ext.renderers.beebasm import BeebasmRenderer

        binary = assemble_beebasm("""
            org &8000
        .start
            jsr helper
            rts
        .helper
            nop
            rts
        save "step1.bin", start, P%
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)

        d = Disassembler.create(cpu="6502")
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        ir = d.disassemble()
        text = str(ir.render(BeebasmRenderer(show_auto_label_footer=False)))
        # Auto-name still appears inline (analysis is unchanged) …
        assert ".sub_8004" in text
        assert "jsr sub_8004" in text
        # … but no footer.
        assert "Automatically generated labels" not in text


@pytest.mark.beebasm
class TestMoveContext:
    """Driver feature: ``d.add_move()`` + ``d.using_move()`` — tell
    the disassembler that some bytes loaded at one address actually
    execute at a different runtime address (e.g. ROM code copied to
    RAM at boot).

    For the simplest case — moved code that doesn't reference its
    own runtime addresses — the round-trip property holds without
    any pseudopc emission in the renderer. The byte sequence stays
    the same; only the names attached via ``with id:``
    change.

    A richer test (with code that DOES reference its own runtime
    address — branches, JSRs into the moved region) needs proper
    pseudopc-style rendering and lands when ADFS-style relocation
    drivers do (deferred per ADFS port plan).
    """

    def test_add_move_returns_move_handle(self, tmp_path):
        # Pure API test — no beebasm round-trip needed.
        from dasmos.disassembler import Disassembler
        from dasmos.core.move import Move
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"\xa0\x00\x60")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        move = d.add_move(
            dest_runtime_addr=0x100,
            src_binary_addr=0x8000,
            length=3,
            name="zp_overlay",
        )
        assert isinstance(move, Move)
        assert move.name == "zp_overlay"
        assert d.moves.is_valid_move_id(move._move_id)

    def test_move_pushes_and_pops_as_context_manager(self, tmp_path):
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"\xa0\x00\x60")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        move = d.add_move(0x100, 0x8000, 3)
        assert d.moves.active_move_ids == []
        with move:
            assert d.moves.active_move_ids == [move._move_id]
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
            with move_id:
                d.entry(0x100, name="zp_handler")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The renderer surfaces the runtime-address label at the
        # binary classification's position.
        assert ".zp_handler" in text

    def test_label_with_explicit_move_kwarg(
        self, roundtrip_via_beebasm,
    ):
        # Same flow but with explicit move= passed to label() rather
        # than going through the with-block context. ADFS uses both
        # forms — see commands-sweep memo §3.
        source = """
            org &8000
        .anywhere
            ldx #0
            rts
        save "step1.bin", anywhere, P%
        """

        def configure(d):
            move = d.add_move(
                dest_runtime_addr=0x200,
                src_binary_addr=0x8000,
                length=3,
            )
            # No 'with' block — pass move= directly to label().
            d.entry(0x8000)  # entry seed at binary
            d.label(0x200, "explicit_handler", move=move)

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
            with move_id:
                d.comment(0x100, "this code runs at zero-page-ish")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        assert "; this code runs at zero-page-ish" in text

    def test_instruction_straddling_move_boundary_renders_as_bytes(
        self, roundtrip_via_beebasm,
    ):
        """When the trace would classify a multi-byte instruction
        whose bytes straddle a move boundary, dasmos leaves the
        bytes for the leftover-classify pass — they render as
        ``equb`` lines, one per byte. Without this, the renderer
        would try to emit a single instruction but the bytes belong
        to two different runtime spaces (one each side of the
        boundary), and beebasm errors with "Trying to assemble over
        existing code".

        This is the NFS-3.65 case: BVC at &9564 has its operand
        byte at &9565, exactly the start of the page-6 move.
        """
        # Layout: 6-byte block at &8000 is moved to &0070; another
        # 6-byte block at &8006 is moved to &0080. The BNE at &8005
        # straddles &8005 (in move 1) → &8006 (in move 2).
        source = """
            org &8000
        .start
            jsr &0070
            ldx #&00     ; &8003-4
            bne after    ; &8005-6 — STRADDLES the &8006 move boundary
            nop : nop : nop : nop  ; &8007-a
        .after
            rts
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Move 1: &8003..&8005 → &0070..&0072
            m1 = d.add_move(0x70, 0x8003, 3)
            with m1:
                d.label(0x70, "page70")
            # Move 2: &8006..&800b → &0080..&0085 (BNE operand byte
            # at &8006 is the boundary)
            m2 = d.add_move(0x80, 0x8006, 6)
            with m2:
                d.label(0x80, "page80")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Both moves' org / copyblock present (round-trip succeeded).
        assert "org &70" in text
        assert "org &80" in text
        # The straddling instruction's bytes appear as equbs (the
        # trace declined to classify the BNE as a single Opcode
        # because its byte range crossed the move-2 boundary).
        # If the renderer DID try to emit the BNE as one
        # instruction, beebasm's "trying to assemble over existing
        # code" error would have failed the fixture's round-trip
        # assertion — so reaching this point already proves the
        # behaviour.

    def test_move_starting_mid_instruction_is_entered(
        self, roundtrip_via_beebasm,
    ):
        """A move whose source binary address is mid-instruction
        (not the start of any classification) still gets entered —
        the body walk re-evaluates the desired active move at every
        iteration, not just at classification starts. NFS-3.65's
        page-6 copy starts at &9565 which is the operand byte of a
        BVC at &9564; without per-iteration re-evaluation the move
        would never enter and references to its labels would resolve
        to wrong addresses.
        """
        # Layout:
        #   8000: jsr &0070       (3 bytes)
        #   8003: rts             (1 byte)
        #   8004: bne &8006       (2 bytes — operand at &8005)
        #   8006: nop : nop : nop : rts  (4 bytes — &8006..&8009)
        # Move src=&8005 (mid-BNE!), length=4, dest=&0070.
        source = """
            org &8000
        .start
            jsr &0070
            rts
            bne after
        .moved_src
        .after
            nop : nop : nop : rts  ; &8006..&8009 emitted under move
        save "step1.bin", start, P%
        moved_dest = &0070
        """

        def configure(d):
            d.entry(0x8000, name="start")
            # Move starts at &8005 — the BNE's operand byte.
            mid = d.add_move(0x0070, 0x8005, 5)
            with mid:
                d.label(0x70, "moved_dest")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The renderer entered the move (emitted org &70 and the
        # close-out directives) even though &8005 isn't a
        # classification start.
        assert "org &70" in text
        assert "copyblock" in text
        # Round-trip byte equality already asserted by the fixture.

    def test_moves_emitted_before_main_code(
        self, roundtrip_via_beebasm,
    ):
        """py8dis emits move regions FIRST in the output (in source-
        binary-address order), then the main loaded range. Mirrors
        py8dis_reference_nfs-3.65.asm where ``org &9324`` (move 1
        source) appears at line 269 and ``org &8000`` (main ROM) is
        at line 1164 — moves precede main code despite having higher
        binary addresses.

        Why: a zero-page label that lives in a moved region's
        destination must be defined before the first reference from
        main code, otherwise beebasm picks the wrong operand width on
        pass 1 and errors with "Assembled object code has changed
        between 1st and 2nd pass". Emitting the move's body FIRST
        makes the inline ``.<name>`` anchor naturally precede every
        reference from main code, no forward-declared equates needed.
        """
        # 5-byte block at binary &8005..&8009 moves to ZP &0070..&0074.
        # Main code at &8000 references zp_var (runtime &0072) BEFORE
        # the move's source position in binary order.
        source = """
            zp_var = &0072
            org &8000
        .start
            ldx #&00
            sta zp_var,X        ; references zp_var via sta zp,X (2 bytes)
            rts
        .moved_src
            nop : nop : nop : nop : nop  ; &8005..&8009 (5 bytes, runtime &70..&74)
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            mid = d.add_move(0x70, 0x8005, 5)
            with mid:
                d.label(0x70, "zp_base")
                d.label(0x72, "zp_var")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The move's body — including the inline ``.zp_var`` anchor —
        # appears in the output BEFORE the ``org &8000`` that opens
        # main code. (Both must exist; their relative order is what
        # matters.)
        zp_var_idx = text.index(".zp_var")
        main_org_idx = text.index("org &8000")
        assert zp_var_idx < main_org_idx, (
            "moved-region inline label .zp_var must appear before "
            "the main code's `org &8000` so beebasm sees the ZP "
            "definition before any forward reference to it"
        )
        # And the use site (sta zp_var) is in main code, after both.
        sta_idx = text.index("sta zp_var")
        assert main_org_idx < sta_idx

    def test_relative_branch_inside_move_resolves_to_runtime_target(
        self, roundtrip_via_beebasm,
    ):
        """A relative branch (BNE / BEQ / etc.) inside a moved region
        must have its target resolved to the RUNTIME address — not the
        binary address — so the auto-generated label name and the
        equate value both point to the runtime location.

        Bug surfaced by NFS-3.65: a BNE at binary ``&933E`` (runtime
        ``&0030`` in move 1) branches to ``&-9`` → binary ``&9337``,
        which is runtime ``&0029``. The earlier code computed the
        target as ``&9337`` and registered the auto-label there;
        beebasm then saw the equate ``loop_c9337 = &9337`` and tried
        to branch ~37 KB instead of 7 bytes, erroring with "Branch
        out of range".
        """
        # 6-byte block at binary &8003 moves to runtime &0070..&0075.
        # ldx #&00 ; .loop dex ; bne loop ; rts (the BNE branches
        # back inside the moved region).
        source = """
            org &8000
        .start
            jmp moved_src
        .moved_src
            ldx #&00            ; &8003: a2 00     (runtime &70)
        .loop
            dex                 ; &8005: ca        (runtime &72)
            bne loop            ; &8006: d0 fd     (runtime &73 -> &72)
            rts                 ; &8008: 60        (runtime &75)
        save "step1.bin", start, P%
        """

        def configure(d):
            d.entry(0x8000, name="start")
            move_id = d.add_move(0x0070, 0x8003, 6)
            d.label(0x8003, "moved_src")
            with move_id:
                d.entry(0x70)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Whatever auto-label name the loop entry point gets, its
        # equate must use the runtime address (zero page), NOT the
        # binary source address.
        assert "= &8005" not in text, (
            "loop entry's auto-label uses the binary address — should "
            "be the runtime address inside move 1"
        )

    def test_overlapping_moves_round_trip(
        self, roundtrip_via_beebasm,
    ):
        """When two moves' source ranges overlap, each move emits
        its FULL source range under its own runtime mapping (matches
        py8dis). beebasm's ``copyblock`` for the second move
        overwrites the overlap bytes the first move wrote — that's
        fine because both renderings of the same source byte produce
        identical opcode bytes (relative-branch arithmetic happens
        to be self-consistent regardless of PC, absolute operands
        are literal byte values).

        The Acorn NFS driver registers exactly this pattern: a ZP
        copy at ``move(0x16, 0x9324, 0x61)`` (97 bytes from &9324)
        and a page-4 copy at ``move(0x400, 0x9365, 0x100)`` (256
        bytes from &9365). The 32-byte overlap (&9365..&9384) is
        emitted under BOTH moves; the resulting binary still byte-
        matches the original ROM.
        """
        # Build a tiny ROM with two overlapping moves.
        # Layout: outer move src &8004..&8013 (16 bytes, dest &0070);
        # inner move src &800a..&8019 (16 bytes, dest &0080).
        # Overlap: &800a..&8013 (10 bytes).
        source = """
            org &8000
        .start
            jsr &0070       ; calls outer move's dest
            rts
        .outer_src
            nop : nop : nop : nop : nop : nop  ; &8004..&8009 (6 bytes — outer-only)
        .inner_src
            nop : nop : nop : nop : nop : nop  ; &800a..&800f (6 bytes — overlap)
            nop : nop : nop : nop              ; &8010..&8013 (4 bytes — overlap)
            nop : nop : nop : nop : nop : nop  ; &8014..&8019 (6 bytes — inner-only)
        .after
            rts
        save "step1.bin", start, P%
        outer_dest = &0070
        inner_dest = &0080
        """

        def configure(d):
            d.entry(0x8000, name="start")
            d.label(0x8004, "outer_src")
            d.label(0x800a, "inner_src")
            d.add_move(0x0070, 0x8004, 16)  # outer
            inner_id = d.add_move(0x0080, 0x800a, 16)  # inner (overlaps)
            with inner_id:
                d.label(0x80, "inner_dest")
            d.label(0x70, "outer_dest")

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # Both moves emit their full source range (each with its own
        # ``copyblock`` over its full 16 bytes).
        assert "copyblock outer_dest" in text
        assert "copyblock inner_dest" in text
        assert "org &70" in text
        assert "org &80" in text
        # If we got here, the round-trip already byte-matched (the
        # ``roundtrip_via_beebasm`` fixture asserts byte equality).

    def test_moved_block_emits_relocation_directives(
        self, roundtrip_via_beebasm,
    ):
        """A moved region must be rendered with beebasm's relocation
        idiom so cross-references between the dest-runtime addresses
        and the rest of the listing resolve correctly:

            org &<dest>           ; switch PC to destination
            ...moved bytes...
            copyblock <dest_label>, *, <src_label>
            clear <dest_label>, &<dest_end>
            org <src_label> + (* - <dest_label>)

        Without these directives, the moved bytes assemble at their
        SOURCE position (so labels at dest addresses get the wrong
        value), and any operand referencing the dest address
        resolves to the source address instead — which is what causes
        the byte-equality mismatch in the 6502 Tube Client round-trip
        before move-aware emission lands.
        """
        # Outer layout (binary addrs):
        #   8000: jsr moved_dest      ; calls into RAM where the moved
        #                             ; bytes live at runtime
        #   8003: rts
        #   8004-8007: 4 bytes that get copied to &0070-&0073 by the
        #              boot routine (we don't emit the copy code in
        #              this minimal test — we just declare the move).
        #   8008: rts                 ; back to outer flow
        source = """
            org &8000
        .start
            jsr moved_dest
            rts
        .moved_src
            nop
            nop
            nop
            rts
        .after
            rts
        save "step1.bin", start, P%
        moved_dest = &0070
        """

        def configure(d):
            d.entry(0x8000, name="start")
            move_id = d.add_move(
                dest_runtime_addr=0x70,
                src_binary_addr=0x8004,
                length=4,
            )
            d.label(0x8004, "moved_src")
            with move_id:
                d.label(0x70, "moved_dest")
                d.entry(0x70)

        text = roundtrip_via_beebasm(source, 0x8000, configure)
        # The renderer emits all four relocation directives.
        assert "org &70" in text or "org &0070" in text
        assert "copyblock moved_dest" in text
        assert "clear moved_dest" in text
        # And restores PC after the moved block.
        assert "org moved_src + (* - moved_dest)" in text
        # The source label appears inline at the source position.
        assert ".moved_src" in text
        # The dest label appears inline INSIDE the moved block.
        assert ".moved_dest" in text


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

        d = Disassembler.create(cpu="6502")
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
