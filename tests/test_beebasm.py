"""Unit tests for the Beebasm renderer.

Covers lexical building blocks, the per-classification rendering of
opcodes / bytes / words / fills / strings, the per-addressing-mode
operand formatting, label use in operands, and — when the ``beebasm``
binary is available — a real round-trip: the rendered text is fed
through beebasm and the resulting binary is compared byte-for-byte
against the disassembler's input.

The round-trip property is the load-bearing acceptance criterion for
the dasmos disassembly path. Any future renderer change that breaks
it is a real defect.
"""

import os
import shutil
import subprocess

import pytest

from dasmos.disassembler import Disassembler
from dasmos.ext.renderers.beebasm import BeebasmRenderer
from dasmos.output import TextOutput
from dasmos.renderer import create_renderer


# ---------------------------------------------------------------------------
# Locating beebasm for the round-trip tests
# ---------------------------------------------------------------------------

def _find_beebasm() -> str | None:
    """Return a path to the ``beebasm`` binary if one can be found,
    else ``None``.

    Honours the ``BEEBASM`` environment variable (CI uses it), then
    falls back to ``PATH``, then to the user's known checkout at
    ``/Users/rjs/Code/beebasm/beebasm``.
    """
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    found = shutil.which("beebasm")
    if found:
        return found
    fallback = "/Users/rjs/Code/beebasm/beebasm"
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return None


BEEBASM = _find_beebasm()
needs_beebasm = pytest.mark.skipif(
    BEEBASM is None,
    reason="beebasm binary not found (set BEEBASM env var or put it in PATH)",
)


# ---------------------------------------------------------------------------
# Plug-in registration
# ---------------------------------------------------------------------------


class TestPluginRegistration:

    def test_loadable_via_stevedore(self):
        r = create_renderer("beebasm")
        assert isinstance(r, BeebasmRenderer)
        assert r.name == "beebasm"

    def test_supports_nmos6502(self):
        r = BeebasmRenderer()
        assert "6502" in r.cpus_supported()


# ---------------------------------------------------------------------------
# Lexical building blocks
# ---------------------------------------------------------------------------


class TestLexicalSyntax:

    def setup_method(self):
        self.r = BeebasmRenderer()

    def test_hex_uses_ampersand_prefix(self):
        assert self.r.hex2(0xab) == "&ab"
        assert self.r.hex4(0x1234) == "&1234"

    def test_byte_word_string_prefixes(self):
        assert self.r.byte_prefix() == "equb "
        assert self.r.word_prefix() == "equw "
        assert self.r.string_prefix() == "equs "

    def test_comment_prefix(self):
        assert self.r.comment_prefix() == ";"

    def test_inline_label_uses_dot_prefix(self):
        assert self.r.inline_label("foo") == ".foo"

    def test_explicit_label_uses_equals(self):
        assert self.r.explicit_label("foo", "&1234") == "foo = &1234"

    def test_explicit_label_with_offset(self):
        assert self.r.explicit_label("foo", "&1234", offset=2) == "foo = &1234+2"

    def test_explicit_label_alignment(self):
        out = self.r.explicit_label("foo", "&1234", align_column=10)
        assert out == "foo        = &1234"

    def test_explicit_a_for_accumulator(self):
        # Beebasm wants ``ROL A``, not just ``ROL``.
        assert BeebasmRenderer().explicit_a is True

    def test_fill_directive_emits_for_next_loop(self):
        out = BeebasmRenderer().fill_directive(0xAA, 16)
        assert out == ["for _dasmos_fill%, 1, 16 : equb &aa : next"]

    def test_boundary_labels_default_to_dasmos_prefix(self):
        r = BeebasmRenderer()
        assert r.boundary_start_label == "dasmos_start"
        assert r.boundary_end_label == "dasmos_end"
        assert r.emit_boundary_labels is True

    def test_boundary_labels_with_pydis_prefix_for_compat(self):
        # The legacy py8dis prefix lets dasmos produce text that
        # matches py8dis-fork output line-for-line — useful for
        # diffing during the migration.
        r = BeebasmRenderer(boundary_label_prefix="pydis_")
        assert r.boundary_start_label == "pydis_start"
        assert r.boundary_end_label == "pydis_end"

    def test_boundary_labels_are_derived_from_arbitrary_prefix(self):
        r = BeebasmRenderer(boundary_label_prefix="my_marker_")
        assert r.boundary_start_label == "my_marker_start"
        assert r.boundary_end_label == "my_marker_end"

    def test_empty_prefix_suppresses_boundary_labels(self):
        r = BeebasmRenderer(boundary_label_prefix="")
        assert r.emit_boundary_labels is False
        assert r.boundary_start_label is None
        assert r.boundary_end_label is None

    def test_save_directive_with_filename_renders_into_output(self, tmp_path):
        # The save directive lives in render() now (it depends on the
        # load range). Constructing the renderer and rendering a tiny
        # IR is the easiest way to verify the filename surfaces.
        from dasmos.disassembler import Disassembler
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(b"\x60")
        d = Disassembler.create(cpu="6502")
        d.load(bin_path, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        r = BeebasmRenderer()
        r.set_output_filename("output.bin")
        text = str(ir.render(r))
        assert 'save "output.bin", dasmos_start, dasmos_end' in text


# ---------------------------------------------------------------------------
# End-to-end rendering against a tiny program
# ---------------------------------------------------------------------------


def _make_disassembler_with_program(tmp_path, binary_bytes, load_addr=0x8000):
    binpath = tmp_path / "p.bin"
    binpath.write_bytes(binary_bytes)
    d = Disassembler.create(cpu="6502")
    d.load(binpath, load_addr)
    return d


class TestRenderTinyProgram:

    def test_empty_ir_produces_minimal_output(self, tmp_path):
        # Without any load(), the renderer has nothing to anchor a
        # save directive to (no load range, no marker labels), so it
        # emits the minimal empty disassembly. Better than emitting a
        # save directive that references undefined labels.
        d = Disassembler.create(cpu="6502")
        ir = d.disassemble()
        text = str(ir.render("beebasm"))
        assert "org" not in text   # nothing loaded
        assert "save" not in text  # no range to save

    def test_renders_org_and_save_around_loaded_range(self, tmp_path):
        d = _make_disassembler_with_program(tmp_path, b"\x60", 0x8000)
        d.entry(0x8000)
        text = str(ir := d.disassemble().render("beebasm")).strip()
        assert "org &8000" in text
        assert ".dasmos_start" in text
        assert ".dasmos_end" in text
        assert "save dasmos_start, dasmos_end" in text

    def test_pydis_compat_mode_renders_legacy_marker_labels(self, tmp_path):
        # Renderer instance configured for py8dis-output compatibility
        # produces .pydis_start / .pydis_end / save references — useful
        # for byte-for-byte text comparison against the original
        # py8dis fork's output during migration validation.
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        d = _make_disassembler_with_program(tmp_path, b"\x60", 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        renderer = BeebasmRenderer(boundary_label_prefix="pydis_")
        text = str(ir.render(renderer))
        assert ".pydis_start" in text
        assert ".pydis_end" in text
        assert "save pydis_start, pydis_end" in text
        assert ".dasmos_start" not in text  # default prefix not present

    def test_empty_prefix_omits_marker_labels_uses_literal_addresses(
        self, tmp_path,
    ):
        # An empty prefix suppresses the .start / .end marker labels.
        # The save directive then references literal hex addresses
        # for the loaded range — still round-trippable, just without
        # the symbolic anchors in the source.
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        d = _make_disassembler_with_program(tmp_path, b"\x60", 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        renderer = BeebasmRenderer(boundary_label_prefix="")
        text = str(ir.render(renderer))
        # No marker labels at all — and no stringified-None leak either.
        assert ".dasmos_start" not in text
        assert ".dasmos_end" not in text
        assert ".pydis_start" not in text
        assert ".None" not in text
        # Save uses literal addresses bracketing the loaded range.
        # 1-byte load at &8000 → range [&8000, &8001).
        assert "save &8000, &8001" in text

    def test_renders_simple_lda_rts(self, tmp_path):
        # 0x8000: LDA #$2A   (a9 2a)
        # 0x8002: RTS        (60)
        d = _make_disassembler_with_program(tmp_path, b"\xa9\x2a\x60", 0x8000)
        d.entry(0x8000)
        text = str(d.disassemble().render("beebasm"))
        assert "lda #&2a" in text
        assert "rts" in text

    def test_renders_label_at_inline_definition(self, tmp_path):
        d = _make_disassembler_with_program(tmp_path, b"\x60", 0x8000)
        d.entry(0x8000, name="start")
        text = str(d.disassemble().render("beebasm"))
        assert ".start" in text

    def test_label_used_in_operand(self, tmp_path):
        # 0x8000: JSR target  (20 04 80)
        # 0x8003: RTS         (60)
        # 0x8004: NOP target: (ea)
        # 0x8005: RTS         (60)
        d = _make_disassembler_with_program(
            tmp_path, b"\x20\x04\x80\x60\xea\x60", 0x8000,
        )
        d.entry(0x8000, name="start")
        d.label(0x8004, "target")
        text = str(d.disassemble().render("beebasm"))
        assert "jsr target" in text  # label used in operand
        assert ".target" in text     # label defined inline

    def test_branch_uses_label_when_available(self, tmp_path):
        # 0x8000: BNE +1 (d0 01) — target = 0x8003
        # 0x8002: RTS    (60)
        # 0x8003: NOP    (ea)
        # 0x8004: RTS    (60)
        d = _make_disassembler_with_program(
            tmp_path, b"\xd0\x01\x60\xea\x60", 0x8000,
        )
        d.entry(0x8000)
        d.label(0x8003, "skip")
        text = str(d.disassemble().render("beebasm"))
        assert "bne skip" in text


class TestByteColumnAnnotation:
    """``byte_column=True`` enables an inline annotation after each
    instruction line: ``; <addr>: <hex-bytes>  <ascii>``. Off by
    default (dasmos prefers a clean line); the porter and the py8dis-
    parity tests opt in.
    """

    def test_default_off_no_byte_column_emitted(self, tmp_path):
        # ``a9 2a 60`` = LDA #$2A; RTS at &8000.
        d = _make_disassembler_with_program(tmp_path, b"\xa9\x2a\x60", 0x8000)
        d.entry(0x8000)
        text = str(d.disassemble().render("beebasm"))
        # No address-then-hex-bytes annotation on the lda line.
        for line in text.splitlines():
            if "lda" in line:
                assert "8000:" not in line, (
                    f"unexpected byte column on default-off render: {line!r}"
                )
                break

    def test_byte_column_emits_addr_bytes_ascii(self, tmp_path):
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        d = _make_disassembler_with_program(tmp_path, b"\xa9\x2a\x60", 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()
        text = str(ir.render(BeebasmRenderer(byte_column=True)))
        # LDA #$2A is 2 bytes (a9 2a) at &8000; ASCII for 2A is '*'.
        # The byte-column annotation contains the address, bytes, and
        # an ASCII glyph for printable characters.
        lda_line = next(l for l in text.splitlines() if "lda" in l)
        assert "; &8000:" in lda_line
        assert "a9 2a" in lda_line
        assert "*" in lda_line  # 0x2A == '*' is printable ASCII
        # RTS is 1 byte (60) at &8002; 0x60 = '`' which is printable.
        rts_line = next(l for l in text.splitlines() if "rts" in l)
        assert "; &8002:" in rts_line
        assert "60" in rts_line

    def test_byte_column_renders_dot_for_non_printable(self, tmp_path):
        # 0x00, 0xFF, 0x1F are non-printable → ASCII column shows '.'.
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        # nop nop nop = 0xea 0xea 0xea (printable 'ê'? actually 0xea
        # is non-printable in 7-bit ASCII).
        d = _make_disassembler_with_program(tmp_path, b"\xea\xea\xea\x60", 0x8000)
        d.entry(0x8000)
        text = str(d.disassemble().render(BeebasmRenderer(byte_column=True)))
        nop_line = next(l for l in text.splitlines() if "nop" in l and "8000:" in l)
        # Single-byte non-printable opcode → ASCII '.' for it.
        assert "ea" in nop_line
        # The ASCII column should contain a '.' (the non-printable
        # placeholder); other dots may appear in surrounding text so
        # check the byte-column substring specifically.
        post_addr = nop_line.split("&8000:")[1]
        # Within the byte-annotation region there's one byte (ea) and
        # one ascii char ('.').
        assert "ea" in post_addr
        assert "." in post_addr

    def test_py8dis_format_uses_bare_binary_address(self, tmp_path):
        # ``byte_column_format="py8dis"`` switches the address column
        # to py8dis's convention: bare 4-digit hex (no ``&`` prefix),
        # binary address (not runtime), and inside a relocated region
        # an additional ``:<runtime>[<move_id>]`` suffix.
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        d = _make_disassembler_with_program(tmp_path, b"\xa9\x2a\x60", 0x8000)
        d.entry(0x8000)
        text = str(d.disassemble().render(BeebasmRenderer(
            byte_column=True, byte_column_format="py8dis",
        )))
        lda_line = next(l for l in text.splitlines() if "lda" in l)
        # Bare hex (no &), still the same address since no move active.
        assert "; 8000:" in lda_line
        assert "; &8000:" not in lda_line

    @pytest.mark.beebasm
    def test_py8dis_format_shows_move_suffix_inside_moved_block(
        self, tmp_path, assemble_beebasm,
    ):
        # Moved bytes get the py8dis suffix ``:<runtime>[<move_id>]``
        # appended to the byte column. Without a move the suffix is
        # omitted.
        from dasmos.disassembler import Disassembler
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        binary = assemble_beebasm("""
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
        """)
        bin_in = tmp_path / "in.bin"
        bin_in.write_bytes(binary)
        d = Disassembler.create(cpu="6502")
        d.load(bin_in, 0x8000)
        d.entry(0x8000, name="start")
        move_id = d.add_move(
            dest_runtime_addr=0x70,
            src_binary_addr=0x8004,
            length=4,
        )
        d.label(0x8004, "moved_src")
        with d.using_move(move_id):
            d.label(0x70, "moved_dest")
            d.entry(0x70)
        text = str(d.disassemble().render(BeebasmRenderer(
            byte_column=True, byte_column_format="py8dis",
        )))
        # First moved-byte instruction (a NOP) at binary &8004 / runtime
        # &0070 carries both addresses + the move id.
        moved_line = next(
            l for l in text.splitlines()
            if "8004:" in l and "nop" in l
        )
        assert ":0070[1]" in moved_line, (
            f"expected move suffix in moved-byte byte column: {moved_line!r}"
        )
        # An outside-move instruction has NO suffix.
        outside_line = next(
            l for l in text.splitlines()
            if "8000:" in l and "jsr" in l
        )
        assert ":" not in outside_line.split("8000:")[1].split(";")[0], (
            f"unexpected move-suffix on outside-move line: {outside_line!r}"
        )

    def test_byte_column_coexists_with_inline_user_comment(
        self, tmp_path,
    ):
        # When both byte_column AND a user inline comment are present,
        # the byte column comes first (closer to the instruction) and
        # the user comment trails.
        from dasmos.core.annotations import Align
        from dasmos.ext.renderers.beebasm import BeebasmRenderer
        d = _make_disassembler_with_program(tmp_path, b"\xa9\x2a\x60", 0x8000)
        d.entry(0x8000)
        d.comment(0x8000, "load magic", align=Align.INLINE)
        text = str(d.disassemble().render(BeebasmRenderer(byte_column=True)))
        lda_line = next(l for l in text.splitlines() if "lda" in l)
        # Byte column appears first (lower index); user comment after.
        bc_idx = lda_line.index("&8000:")
        user_idx = lda_line.index("load magic")
        assert bc_idx < user_idx


class TestPerAddressingModeFormatting:
    """Pin the operand syntax for each addressing mode the NMOS 6502
    plug-in produces. The shapes are conventional MOS-style; the
    BeebasmRenderer wraps them with `&` for hex.
    """

    def setup_method(self):
        # A common Disassembler is fine; we only render the operand text.
        self.d = Disassembler.create(cpu="6502")

    def _render(self, tmp_path, bytes_, opcode_addr=0x8000, load_addr=0x8000):
        binpath = tmp_path / "p.bin"
        binpath.write_bytes(bytes_)
        # These tests pin the addressing-mode operand SHAPE (`,X`, `,Y`,
        # parens, `#`); the auto-label feature would replace the
        # literal hex with a synthesised symbol, which would still be
        # the same shape but obscures what's under test. Disable it.
        d = Disassembler.create(cpu="6502", auto_labels_enabled=False)
        d.load(binpath, load_addr)
        d.entry(opcode_addr)
        ir = d.disassemble()
        return str(ir.render("beebasm"))

    def test_immediate(self, tmp_path):
        text = self._render(tmp_path, b"\xa9\x2a\x60")  # LDA #$2A; RTS
        assert "lda #&2a" in text

    def test_zero_page(self, tmp_path):
        text = self._render(tmp_path, b"\xa5\x42\x60")  # LDA &42; RTS
        assert "lda &42" in text

    def test_zero_page_x(self, tmp_path):
        text = self._render(tmp_path, b"\xb5\x42\x60")  # LDA &42,X; RTS
        assert "lda &42,X" in text

    def test_absolute(self, tmp_path):
        text = self._render(tmp_path, b"\xad\x34\x12\x60")  # LDA &1234; RTS
        assert "lda &1234" in text

    def test_absolute_x(self, tmp_path):
        text = self._render(tmp_path, b"\xbd\x34\x12\x60")
        assert "lda &1234,X" in text

    def test_absolute_y(self, tmp_path):
        text = self._render(tmp_path, b"\xb9\x34\x12\x60")
        assert "lda &1234,Y" in text

    def test_indirect_jmp(self, tmp_path):
        # JMP (&1234); ... — the trace reads a pointer it can't
        # follow (1234 not in loaded mem) but the renderer still
        # produces the right text.
        text = self._render(tmp_path, b"\x6c\x34\x12")
        assert "jmp (&1234)" in text

    def test_indexed_indirect(self, tmp_path):
        # LDA (&42,X); RTS
        text = self._render(tmp_path, b"\xa1\x42\x60")
        assert "lda (&42,X)" in text

    def test_indirect_indexed(self, tmp_path):
        # LDA (&42),Y; RTS
        text = self._render(tmp_path, b"\xb1\x42\x60")
        assert "lda (&42),Y" in text

    def test_implied(self, tmp_path):
        text = self._render(tmp_path, b"\x60")  # RTS
        assert "    rts" in text

    def test_accumulator_with_explicit_a(self, tmp_path):
        # Beebasm wants ``rol A``; explicit_a=True on BeebasmRenderer.
        text = self._render(tmp_path, b"\x2a\x60")  # ROL A; RTS
        assert "rol A" in text


# ---------------------------------------------------------------------------
# THE round-trip: render → beebasm → binary equality
# ---------------------------------------------------------------------------


@needs_beebasm
class TestBeebasmRoundTrip:
    """Real round-trip through the actual beebasm assembler. The
    rendered source is fed to ``beebasm``, the resulting binary is
    compared byte-for-byte to the disassembler's input. This is the
    correctness oracle for the whole disassembly path.
    """

    def _round_trip(self, tmp_path, original_bytes, load_addr=0x8000,
                    entries=None, labels=None, byte_classifications=None):
        """Disassemble ``original_bytes`` at ``load_addr``, render via
        BeebasmRenderer, run through beebasm, return the produced
        binary bytes.
        """
        binpath = tmp_path / "in.bin"
        binpath.write_bytes(original_bytes)

        d = Disassembler.create(cpu="6502")
        d.load(binpath, load_addr)
        for addr in (entries or [load_addr]):
            d.entry(addr)
        for addr, name in (labels or []):
            d.label(addr, name)
        for addr, length in (byte_classifications or []):
            d.byte(addr, length)
        ir = d.disassemble()

        renderer = BeebasmRenderer()
        renderer.set_output_filename(str(tmp_path / "out.bin"))
        text = str(ir.render(renderer))

        asm_path = tmp_path / "src.asm"
        asm_path.write_text(text, encoding="utf-8")

        result = subprocess.run(
            [BEEBASM, "-i", str(asm_path)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed:\n=== source ===\n{text}\n"
            f"=== stdout ===\n{result.stdout}\n=== stderr ===\n{result.stderr}"
        )

        out_path = tmp_path / "out.bin"
        return out_path.read_bytes()

    def test_lda_rts_round_trips(self, tmp_path):
        original = b"\xa9\x2a\x60"  # LDA #$2A; RTS
        produced = self._round_trip(tmp_path, original)
        assert produced == original

    def test_jsr_with_label_round_trips(self, tmp_path):
        # 0x8000: JSR &8004
        # 0x8003: RTS
        # 0x8004: NOP
        # 0x8005: RTS
        original = b"\x20\x04\x80\x60\xea\x60"
        produced = self._round_trip(
            tmp_path, original,
            labels=[(0x8004, "target")],
        )
        assert produced == original

    def test_branch_round_trips(self, tmp_path):
        # 0x8000: BNE +1; 0x8002: RTS; 0x8003: NOP; 0x8004: RTS
        original = b"\xd0\x01\x60\xea\x60"
        produced = self._round_trip(tmp_path, original)
        assert produced == original

    def test_data_bytes_round_trip(self, tmp_path):
        # 0x8000: RTS, then four arbitrary data bytes (leftover-pass
        # classifies as Byte(1)).
        original = b"\x60\x99\x00\xff\x42"
        produced = self._round_trip(tmp_path, original)
        assert produced == original

    def test_indirect_jmp_round_trips(self, tmp_path):
        # JMP (&1234) where the indirect target is outside loaded
        # memory — beebasm just assembles the bytes back as written.
        original = b"\x6c\x34\x12"
        produced = self._round_trip(tmp_path, original)
        assert produced == original

    def test_empty_prefix_round_trips_via_literal_addresses(self, tmp_path):
        # Round-trip with marker labels suppressed — the save directive
        # uses literal hex addresses; the resulting binary still
        # equals the original.
        binpath = tmp_path / "in.bin"
        original = b"\xa9\x42\x60"
        binpath.write_bytes(original)

        d = Disassembler.create(cpu="6502")
        d.load(binpath, 0x8000)
        d.entry(0x8000)
        ir = d.disassemble()

        renderer = BeebasmRenderer(boundary_label_prefix="")
        renderer.set_output_filename(str(tmp_path / "out.bin"))
        text = str(ir.render(renderer))

        # Sanity: no marker labels present — and no stringified-None
        # leak either (regression: a previous version emitted ".None"
        # when the prefix was empty).
        assert "_start" not in text
        assert "_end" not in text
        assert ".None" not in text

        asm_path = tmp_path / "src.asm"
        asm_path.write_text(text, encoding="utf-8")
        result = subprocess.run(
            [BEEBASM, "-i", str(asm_path)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed:\n=== source ===\n{text}\n"
            f"=== stderr ===\n{result.stderr}"
        )
        assert (tmp_path / "out.bin").read_bytes() == original

    def test_each_addressing_mode_round_trips(self, tmp_path):
        # A program that exercises every common 6502 addressing mode.
        # JMP skips past three byte-data bytes to the RTS at 0x8019.
        original = (
            b"\xa9\x42"          # 8000 LDA #$42
            b"\xa5\x10"          # 8002 LDA $10
            b"\xb5\x20"          # 8004 LDA $20,X
            b"\xad\x00\x90"      # 8006 LDA $9000
            b"\xbd\x00\x91"      # 8009 LDA $9100,X
            b"\xb9\x00\x92"      # 800c LDA $9200,Y
            b"\xa1\x30"          # 800f LDA ($30,X)
            b"\xb1\x40"          # 8011 LDA ($40),Y
            b"\x4c\x19\x80"      # 8013 JMP $8019 (skip the data)
            b"\x99\x99\x99"      # 8016-8018 unreached data
            b"\x60"              # 8019 RTS
        )
        produced = self._round_trip(tmp_path, original)
        assert produced == original
