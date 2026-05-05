"""Tests for the py8dis2dasmos AST porter.

Each test gives the porter a tiny py8dis driver source and checks the
shape of the rewritten dasmos source. The end-to-end check
(``test_round_trip_via_dasmos``) ports a real driver, runs the
result through dasmos, and verifies a byte-identical round-trip
through beebasm — the load-bearing acceptance test.
"""

import importlib.util
import io
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest


def _find_beebasm() -> str | None:
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


_BEEBASM = _find_beebasm()

# Make the porter importable from `scripts/`. ``scripts/`` isn't a
# package; load the file directly.
_PORTER_PATH = Path(__file__).parent.parent / "scripts" / "py8dis2dasmos.py"
_spec = importlib.util.spec_from_file_location("py8dis2dasmos", _PORTER_PATH)
_porter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_porter)


def port(source: str, extra_envs: tuple[str, ...] = ()) -> str:
    """Convenience wrapper that dedents the input first."""
    return _porter.port(textwrap.dedent(source), extra_envs=extra_envs)


# ---------------------------------------------------------------------------
# Per-rule tests
# ---------------------------------------------------------------------------


class TestImports:

    def test_drops_py8dis_commands_star_import(self):
        out = port("from py8dis.commands import *\n")
        assert "py8dis" not in out
        assert "import dasmos" in out

    def test_drops_other_py8dis_imports(self):
        out = port("""
            from py8dis.utils import LazyString
            from py8dis.commands import *
        """)
        assert "py8dis" not in out

    def test_drops_aliased_py8dis_module_import(self):
        # ``import py8dis.acorn as acorn`` — the alias gets bound,
        # then later ``acorn.bbc()`` lines need rewriting. The
        # import statement itself is dropped.
        out = port("""
            from py8dis.commands import *
            import py8dis.acorn as acorn
            load(0xE000, "rom.bin", "6502")
        """)
        assert "import py8dis" not in out
        assert "import dasmos" in out

    def test_drops_statements_referencing_dropped_internals(self):
        # When ``from py8dis.X import Y as Z`` is dropped, any
        # statement referencing ``Z`` gets dropped too — drivers
        # occasionally reach into py8dis internals to override
        # classifications, and we'd rather drop the override
        # silently than leave broken references in the ported
        # script.
        out = port("""
            from py8dis.commands import *
            from py8dis import classification as _cls, disassembly as _disasm
            load(0xE000, "rom.bin", "6502")
            _disasm.classifications[0xE000] = _cls.String(7)
            label(0xE100, "after")
        """)
        # The classification-override line is gone (it referenced
        # both _cls and _disasm).
        assert "_cls" not in out
        assert "_disasm" not in out
        # But the unrelated label() call survives.
        assert "d.label(57600, 'after')" in out

    def test_drops_get_structured_assignment_and_cascade(self):
        # The py8dis fork's JSON-output hook ``get_structured()`` has
        # no dasmos equivalent yet (planned as a JSON-renderer
        # plug-in). The porter drops ``structured = get_structured()``
        # AND the follow-up ``json.dumps(structured)`` line that uses
        # the would-be-defined name, so the ported script doesn't
        # crash with NameError on the missing function.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            structured = get_structured()
            json_filepath = _output_dirpath / "thing.json"
            json_filepath.write_text(json.dumps(structured), encoding="utf-8")
        """)
        assert "get_structured" not in out
        # The cascade drops the line that references ``structured``.
        assert "json.dumps(structured)" not in out
        # The unrelated ``output = go(...)`` translation survives
        # (becomes the str(disassemble().render(...)) sequence).
        assert "d.disassemble().render(" in out

    def test_acorn_func_call_becomes_use_environment(self):
        # ``acorn.bbc()`` registers the MOS env (workspace + vectors
        # + OS calls) and the Model B I/O register block. The FDC
        # is NOT auto-activated: a BBC Micro shipped without disc
        # support, and the FDC was always an upgrade. Drivers that
        # need an FDC env opt in via the porter's ``--env`` flag.
        out = port("""
            from py8dis.commands import *
            import py8dis.acorn as acorn
            load(0x8000, "rom.bin", "6502")
            acorn.bbc()
            acorn.is_sideways_rom()
        """)
        assert "d.use_environment('acorn_mos')" in out
        assert "d.use_environment('acorn_model_b_hardware')" in out
        assert "d.use_environment('acorn_fdc_8271')" not in out
        assert "d.use_environment('acorn_fdc_1770')" not in out
        assert "d.use_environment('acorn_sideways_rom')" in out
        assert "acorn.bbc" not in out
        assert "acorn.is_sideways_rom" not in out

    def test_acorn_master_call_becomes_use_environment(self):
        # ``acorn.master()`` is the Master fit-out: MOS labels and
        # the Master hardware register block (ACCCON etc). FDC is
        # opt-in via ``extra_envs``.
        out = port("""
            from py8dis.commands import *
            import py8dis.acorn as acorn
            load(0x8000, "rom.bin", "6502")
            acorn.master()
        """)
        assert "d.use_environment('acorn_mos')" in out
        assert "d.use_environment('acorn_master_hardware')" in out
        assert "d.use_environment('acorn_fdc_1770')" not in out
        assert "d.use_environment('acorn_fdc_8271')" not in out
        assert "acorn.master" not in out

    def test_acorn_b_plus_call_becomes_use_environment(self):
        # ``acorn.b_plus()`` shares the Model B I/O register block.
        # Same opt-in FDC stance.
        out = port("""
            from py8dis.commands import *
            import py8dis.acorn as acorn
            load(0x8000, "rom.bin", "6502")
            acorn.b_plus()
        """)
        assert "d.use_environment('acorn_mos')" in out
        assert "d.use_environment('acorn_model_b_hardware')" in out
        assert "d.use_environment('acorn_fdc_1770')" not in out
        assert "d.use_environment('acorn_fdc_8271')" not in out
        assert "acorn.b_plus" not in out

    def test_extra_envs_kwarg_appends_use_environment_calls(self):
        # The ``extra_envs`` parameter on ``port()`` lets callers
        # opt in to envs that the original py8dis driver took for
        # granted (e.g. an FDC chip the source script never named).
        out = port(
            """
            from py8dis.commands import *
            import py8dis.acorn as acorn
            load(0x8000, "rom.bin", "6502")
            acorn.bbc()
            """,
            extra_envs=("acorn_fdc_1770",),
        )
        assert "d.use_environment('acorn_mos')" in out
        assert "d.use_environment('acorn_model_b_hardware')" in out
        assert "d.use_environment('acorn_fdc_1770')" in out

    def test_extra_envs_without_acorn_func_calls(self):
        # If the source driver doesn't call any ``acorn.<func>()``,
        # extra envs still get spliced in — right after the
        # ``d.load(...)`` call.
        out = port(
            """
            from py8dis.commands import *
            load(0x8000, "rom.bin", "6502")
            """,
            extra_envs=("acorn_fdc_8271",),
        )
        assert "d.use_environment('acorn_fdc_8271')" in out

    def test_constant_passes_through(self):
        # py8dis ``constant(value, name)`` now maps to dasmos's
        # first-class ``d.constant(value, name)`` (which records a
        # named-value entry surfaced in the JSON ``constants``
        # section AND an optional label for asm equate emission).
        # Earlier rule renamed it to ``optional_label`` — that's now
        # gone.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            constant(0xFEA0, "adlc_cr1")
        """)
        assert "d.constant(65184, 'adlc_cr1')" in out
        assert "optional_label(65184, 'adlc_cr1')" not in out

    def test_move_renamed_to_add_move(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            move(0x100, 0x9324, 0x61)
        """)
        assert "d.add_move(256, 37668, 97)" in out
        # No bare ``move(`` call survives (only the ``add_move(`` form
        # that contains the substring).
        import re
        assert not re.search(r"(?<![._a-zA-Z0-9])move\(", out)


class TestInitAndLoad:

    def test_load_becomes_constructor_plus_load(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
        """)
        # Constructor with the mapped CPU name and py8dis-compatible
        # auto-label prefixes (so ported drivers produce textually
        # similar output to the py8dis-fork original during
        # migration validation).
        assert "d = dasmos.Disassembler.create(" in out
        assert "cpu='6502'" in out
        assert "auto_label_data_prefix='l'" in out
        assert "auto_label_code_prefix='c'" in out
        assert "auto_label_subroutine_prefix='sub_c'" in out
        assert "auto_label_loop_prefix='loop_c'" in out
        # Load with file/addr swapped (py8dis order: addr, file).
        assert "d.load('rom.bin', 57344)" in out  # 0xE000 → 57344 via unparse

    def test_init_assembler_name_consumed(self):
        # init() doesn't survive — its assembler_name feeds into the
        # render() call generated by go().
        out = port("""
            from py8dis.commands import *
            init(assembler_name="beebasm", lower_case=True)
            load(0xE000, "rom.bin", "6502")
            go()
        """)
        assert "init(" not in out
        # The assembler name (default "beebasm") flows to render() —
        # the ported call also threads py8dis-compat kwargs through.
        assert "ir.render('beebasm'" in out

    def test_load_with_md5_kwarg(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502", md5sum="abc123")
        """)
        assert "md5sum='abc123'" in out

    def test_load_with_positional_md5(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502", "abc123")
        """)
        assert "md5sum='abc123'" in out

    def test_load_with_variable_filename(self):
        # Drivers often compute the filename — the porter passes the
        # expression through verbatim.
        out = port("""
            from py8dis.commands import *
            _rom = "/some/path/rom.bin"
            load(0xE000, _rom, "6502")
        """)
        assert "d.load(_rom, 57344)" in out


class TestFreeFunctionToMethod:

    def test_label_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            label(0xE000, "reset")
        """)
        assert "d.label(57344, 'reset')" in out

    def test_entry_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            entry(0xE000)
        """)
        assert "d.entry(57344)" in out

    def test_byte_word_fill_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            byte(0xFFF0)
            word(0xFFF1, 4)
            fill(0xFFF5, 8, 0xFF)
        """)
        assert "d.byte(" in out
        assert "d.word(" in out
        assert "d.fill(" in out

    def test_subroutine_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            subroutine(0xE000, "reset", title="Reset entry")
        """)
        assert "d.subroutine(" in out


class TestCommentRewriting:

    def test_plain_comment_unchanged(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "Initial comment")
        """)
        assert "d.comment(57344, 'Initial comment')" in out

    def test_inline_true_becomes_align_inline(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "trailing", inline=True)
        """)
        # The kwarg gets rewritten…
        assert "align=Align.INLINE" in out
        # …and the inline= is gone.
        assert "inline=" not in out
        # …and the Align import is added when needed.
        assert "from dasmos import Align" in out

    def test_inline_false_dropped(self):
        # py8dis's inline=False was the default; drop it entirely.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "above", inline=False)
        """)
        assert "inline=" not in out
        assert "align=" not in out

    def test_no_align_import_when_no_inline_used(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "plain")
        """)
        assert "from dasmos import Align" not in out


class TestDataBanner:

    def test_data_banner_expands_to_label_plus_banner(self):
        # py8dis's ``data_banner(addr, name, title=, description=)``
        # is sugar for ``subroutine(..., is_entry_point=False)`` —
        # it emits the title/description block but doesn't register
        # the address as a code entry point. The porter expands it
        # the same way as the subroutine variant: a label() at addr
        # + a banner() with the title and description.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            data_banner(0xE100, "table_x", title="Lookup table X",
                        description="32-entry sine table.")
        """)
        # No spurious entry point — never use the subroutine form.
        assert "d.subroutine" not in out
        # label() at the address, banner() carrying the title/desc.
        assert "d.label(57600, 'table_x'" in out
        assert "d.banner(57600" in out
        assert "title='Lookup table X'" in out
        assert "32-entry sine table." in out


class TestEncodingInjection:

    def test_write_text_gets_explicit_utf8_encoding(self):
        # py8dis drivers commonly end with
        # ``output_filepath.write_text(output)`` — that uses the
        # platform's locale default (cp1252 on Windows) and chokes
        # on the U+2192 (→) and similar Unicode characters dasmos
        # emits in comments / banners. The porter must inject an
        # explicit encoding="utf-8" so the ported driver runs
        # cross-platform.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output_filepath.write_text(output)
        """)
        assert "write_text(output, encoding='utf-8')" in out

    def test_read_text_gets_explicit_utf8_encoding(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            data = some_filepath.read_text()
        """)
        assert "read_text(encoding='utf-8')" in out

    def test_existing_encoding_kwarg_left_alone(self):
        # If the driver already specifies encoding= explicitly,
        # don't double up.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output_filepath.write_text(output, encoding='latin-1')
        """)
        assert "encoding='latin-1'" in out
        assert "encoding='utf-8'" not in out


class TestMoveContextManager:

    def test_with_move_passes_through_unchanged(self):
        # dasmos's ``add_move()`` returns a Move object that's itself
        # a context manager. The porter therefore leaves the
        # ``with foo_move_id:`` form alone — no rewrite needed.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            foo_move_id = move(0x0D00, 0xBC79, 0x49)
            with foo_move_id:
                label(0x0D00, "foo")
        """)
        # The assignment side becomes d.add_move(...).
        assert "foo_move_id = d.add_move" in out
        # The with form is unchanged: Move is itself a context manager.
        assert "with foo_move_id:" in out
        # The old wrapping shape is gone.
        assert "d.using_move" not in out

    def test_move_id_kwarg_renamed_to_move(self):
        # py8dis: ``label(addr, name, move_id=foo)``; dasmos:
        # ``d.label(addr, name, move=foo)``. Variable name unchanged.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            foo_move_id = move(0x0D00, 0xBC79, 0x49)
            label(0x0D00, "bar", move_id=foo_move_id)
        """)
        assert "move=foo_move_id" in out
        assert "move_id=foo_move_id" not in out


class TestGoConversion:

    def test_go_becomes_disassemble_render_print(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            go()
        """)
        assert "ir = d.disassemble()" in out
        # render() call carries py8dis-compat kwargs too.
        assert "ir.render('beebasm'" in out
        assert "boundary_label_prefix='pydis_'" in out
        assert "byte_column=True" in out
        assert "print(" in out


# ---------------------------------------------------------------------------
# End-to-end: port a tiny driver, run it, verify round-trip
# ---------------------------------------------------------------------------


@pytest.mark.beebasm
class TestPorterEndToEnd:

    def test_ported_tiny_driver_round_trips(self, tmp_path, assemble_beebasm):
        """Hand-write a tiny py8dis driver, port it, run the ported
        script, capture its output as a beebasm source, re-assemble,
        verify byte-identical with the original ROM.

        This is the porter's load-bearing acceptance test — exercises
        the entire AST rewrite + dasmos disassemble + beebasm pipeline
        in one shot.
        """
        # Step 1: build a tiny ROM via beebasm.
        original = assemble_beebasm(
            """
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
        )
        rom_path = tmp_path / "step1.bin"
        # assemble_beebasm wrote it under tmp_path already; verify.
        assert rom_path.exists()
        assert rom_path.read_bytes() == original

        # Step 2: hand-write a py8dis-style driver script targeting
        # that ROM.
        # ROM layout:
        #   8000-1: LDA #$42  (2 bytes)
        #   8002-4: JSR &8006 (3 bytes)
        #   8005:   RTS       (1 byte)
        #   8006:   NOP       (.helper — 1 byte)
        #   8007:   RTS       (1 byte)
        driver_src = textwrap.dedent("""
            from py8dis.commands import *

            load(0x8000, "step1.bin", "6502")
            entry(0x8000)
            label(0x8000, "start")
            label(0x8006, "helper")
            comment(0x8000, "load magic", inline=True)
            go()
        """)

        # Step 3: port it.
        ported = _porter.port(driver_src)

        # Sanity-check the ported source has the expected shape.
        assert "import dasmos" in ported
        assert "d = dasmos.Disassembler.create" in ported
        assert "d.load" in ported
        assert "d.entry" in ported
        assert "d.label" in ported
        assert "d.comment" in ported
        assert "align=Align.INLINE" in ported
        assert "ir = d.disassemble()" in ported

        # Step 4: run the ported driver in a subprocess and capture
        # its stdout (which is the beebasm source via go() →
        # print(str(ir.render(...)))).
        ported_path = tmp_path / "ported.py"
        ported_path.write_text(ported, encoding="utf-8")

        import subprocess
        result = subprocess.run(
            [sys.executable, str(ported_path)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"ported script failed:\n=== ported ===\n{ported}\n"
            f"=== stderr ===\n{result.stderr}"
        )
        beebasm_source = result.stdout
        assert ".start" in beebasm_source
        assert ".helper" in beebasm_source
        assert "; load magic" in beebasm_source
        assert "jsr helper" in beebasm_source  # label resolved in operand

        # Step 5: re-assemble the dasmos-rendered text via beebasm
        # and verify byte-equality with the original ROM. The
        # ported script's render() output uses ``save dasmos_start,
        # dasmos_end`` without an explicit filename, so we pass -o
        # to beebasm to specify the output binary.
        if _BEEBASM is None:
            pytest.skip("beebasm binary not found")
        rebuilt_asm = tmp_path / "rebuilt.asm"
        rebuilt_asm.write_text(beebasm_source, encoding="utf-8")
        rebuilt_bin = tmp_path / "rebuilt.bin"
        result = subprocess.run(
            [_BEEBASM, "-i", str(rebuilt_asm), "-o", str(rebuilt_bin)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed:\n=== source ===\n{beebasm_source}\n"
            f"=== stderr ===\n{result.stderr}"
        )
        rebuilt = rebuilt_bin.read_bytes()
        assert rebuilt == original
