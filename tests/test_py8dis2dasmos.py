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
        assert "d.label(0xE100, 'after')" in out

    def test_get_structured_with_json_dumps_collapses_to_str_render(self):
        # The canonical py8dis JSON-emit pattern is
        # ``structured = get_structured(); ...write_text(json.dumps(structured))...``.
        # The dasmos JSON renderer's StructuredOutput stringifies via
        # ``str(...)`` directly, so the porter collapses the
        # intermediate name + json.dumps into a single
        # ``str(ir.render('json'))`` expression. The ``structured``
        # name disappears (it was only used as plumbing), and
        # ``json.dumps`` is no longer called.
        out = port("""
            from py8dis.commands import *
            import json
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            structured = get_structured()
            json_filepath = _output_dirpath / "thing.json"
            json_filepath.write_text(json.dumps(structured), encoding="utf-8")
        """)
        assert "get_structured" not in out
        assert "structured" not in out
        assert "json.dumps" not in out
        assert "str(ir.render('json'))" in out
        # ``import json`` was only there for json.dumps; drop it.
        assert "import json" not in out

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
        assert "d.constant(0xFEA0, 'adlc_cr1')" in out
        assert "optional_label(0xFEA0, 'adlc_cr1')" not in out

    def test_move_renamed_to_add_move(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            move(0x100, 0x9324, 0x61)
        """)
        assert "d.add_move(0x100, 0x9324, 0x61)" in out
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
        # Load with file/addr swapped (py8dis order: addr, file). The
        # hex form survives unparse via the porter's literal-preserving
        # custom unparser.
        assert "d.load('rom.bin', 0xE000)" in out

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
        assert "d.load(_rom, 0xE000)" in out


class TestFreeFunctionToMethod:

    def test_label_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            label(0xE000, "reset")
        """)
        assert "d.label(0xE000, 'reset')" in out

    def test_entry_rewritten(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            entry(0xE000)
        """)
        assert "d.entry(0xE000)" in out

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
        assert "d.comment(0xE000, 'Initial comment')" in out

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
        assert "d.label(0xE100, 'table_x'" in out
        assert "d.banner(0xE100" in out
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

    def test_default_go_does_not_emit_string_detection_kwarg(self):
        # ``go()`` with no autostring/post_trace_steps overrides leaves
        # the dasmos default in place. The ctor doesn't need an
        # explicit ``string_detection_min_length=`` kwarg because the
        # default already matches py8dis (3).
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            go()
        """)
        assert "string_detection_min_length" not in out

    def test_autostring_min_length_threads_to_ctor(self):
        # ``go(autostring_min_length=5)`` sets dasmos's
        # ``string_detection_min_length=5`` on the ctor.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            go(autostring_min_length=5)
        """)
        assert "string_detection_min_length=5" in out

    def test_post_trace_steps_lambda_none_disables_string_detection(self):
        # The py8dis idiom ``post_trace_steps=lambda: None`` disables
        # autostring entirely. dasmos translation:
        # ``string_detection_min_length=None``.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            go(post_trace_steps=lambda: None)
        """)
        assert "string_detection_min_length=None" in out

    def test_post_trace_steps_lambda_autostring_threads_min_length(self):
        # The py8dis idiom
        # ``post_trace_steps=lambda: classification.autostring(K)``
        # is translated to ``string_detection_min_length=K``.
        out = port("""
            from py8dis.commands import *
            from py8dis import classification
            load(0xE000, "rom.bin", "6502")
            go(post_trace_steps=lambda: classification.autostring(7))
        """)
        assert "string_detection_min_length=7" in out

    def test_assigned_go_call_threads_string_detection(self):
        # The same translation applies when go() is the rhs of an
        # assignment (``output = go(autostring_min_length=4)``).
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output = go(autostring_min_length=4, print_output=False)
        """)
        assert "string_detection_min_length=4" in out


class TestGetStructuredConversion:
    """``get_structured()`` is py8dis-fork's hook that returns the
    structured-output dict. dasmos has a JSON renderer plug-in that
    emits the same shape via ``ir.render('json').data``. The porter
    rewrites ``get_structured()`` to that expression so JSON-emitting
    drivers continue to work after porting.

    The IR is shared between the asm and JSON render passes — calling
    ``d.disassemble()`` once. A driver that uses both ``go()`` and
    ``get_structured()`` therefore has exactly one
    ``d.disassemble()`` call in the ported output.
    """

    def test_get_structured_rewritten_to_json_render(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            structured = get_structured()
        """)
        assert "get_structured" not in out
        # The asm + json renders share one IR.
        assert "ir.render('beebasm'" in out
        assert "ir.render('json').data" in out

    def test_disassemble_called_once_when_both_renders_present(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            structured = get_structured()
        """)
        # Single d.disassemble() call shared by both renderers.
        assert out.count("d.disassemble()") == 1

    def test_get_structured_inside_try_except_rewritten(self):
        # py8dis drivers wrap their JSON write in a try/except so the
        # script still produces asm if the structured path raises. The
        # dasmos renderer is reliable enough that this defensive
        # wrapper just hides bugs — the porter unwraps the try/except,
        # collapses the json.dumps plumbing into ``str(ir.render('json'))``,
        # and lifts the body to module level.
        out = port("""
            from py8dis.commands import *
            import json
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            try:
                structured = get_structured()
                print(json.dumps(structured))
            except (AssertionError, Exception):
                pass
        """)
        assert "get_structured" not in out
        assert "structured" not in out
        assert "json.dumps" not in out
        assert "try:" not in out
        assert "except" not in out
        # The lifted print() now embeds the str(ir.render('json'))
        # expression directly.
        assert "print(str(ir.render('json')))" in out

    def test_render_kwargs_applied_only_to_asm(self):
        # The py8dis-compat render kwargs (boundary_label_prefix,
        # byte_column, …) are beebasm-specific and must NOT be passed
        # to the JSON render.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            structured = get_structured()
        """)
        # Find the json render call and confirm it has no extra kwargs.
        json_render_idx = out.find("ir.render('json'")
        assert json_render_idx >= 0
        # The substring up to the next ``)`` is the call parens.
        close_idx = out.find(")", json_render_idx)
        json_call = out[json_render_idx:close_idx + 1]
        assert "boundary_label_prefix" not in json_call
        assert "byte_column" not in json_call

    def test_canonical_json_emit_collapses_to_str_render(self):
        # The canonical py8dis pattern wraps the JSON emit in a
        # try/except and uses ``json.dumps(get_structured())``. The
        # dasmos JSON renderer's StructuredOutput is __str__-able
        # directly, so the porter collapses the whole pattern to a
        # single ``write_text(str(ir.render('json')), ...)`` line —
        # no try/except (it was hiding bugs), no .data extraction,
        # no json.dumps roundtrip.
        out = port("""
            from py8dis.commands import *
            import json
            import sys
            load(0xE000, "rom.bin", "6502")
            output = go(print_output=False)
            try:
                structured = get_structured()
                json_filepath = _output_dirpath / "foo.json"
                json_filepath.write_text(json.dumps(structured), encoding="utf-8")
                print(f"Wrote {json_filepath}", file=sys.stderr)
            except (AssertionError, Exception) as e:
                print(f"Warning: JSON output skipped: {e}", file=sys.stderr)
        """)
        # try/except dropped.
        assert "try:" not in out
        assert "except" not in out
        assert "AssertionError" not in out
        # ``structured`` assignment dropped — write_text uses the
        # str(ir.render(...)) form directly.
        assert "structured" not in out
        # Direct str(ir.render('json')) in the write_text call.
        assert "str(ir.render('json'))" in out
        # ``json.dumps`` no longer used.
        assert "json.dumps" not in out
        # ``import json`` dropped because nothing references json now.
        assert "import json" not in out
        # ``sys`` still used by the print(..., file=sys.stderr) line.
        assert "import sys" in out


# ---------------------------------------------------------------------------
# Output format: docstring preservation, hex literals, blank lines
# ---------------------------------------------------------------------------


class TestPorterOutputFormat:
    """The ported driver is the user-facing artefact of the
    migration. These tests pin the source-level shape that ``ast.unparse``
    on its own does not produce — preserving the original
    docstring, hex literals, multiline strings, and inserting
    blank lines between subroutine / label declarations so the
    output reads as a script, not a wall of text.
    """

    def test_dasmos_imports_appear_after_module_docstring(self):
        out = port('''
            """Module docstring on the first line.

            Multi-line."""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
        ''')
        # Module docstring must come BEFORE the ``import dasmos`` line
        # — otherwise it stops being a docstring.
        docstring_idx = out.find("Module docstring on the first line")
        import_idx = out.find("import dasmos")
        assert docstring_idx >= 0 and import_idx >= 0
        assert docstring_idx < import_idx

    def test_dasmos_imports_appear_after_stdlib_imports(self):
        out = port('''
            """Doc."""
            from py8dis.commands import *
            import os
            import sys
            from pathlib import Path
            load(0xE000, "rom.bin", "6502")
        ''')
        # Stdlib imports come first, dasmos imports after them.
        os_idx = out.find("import os")
        path_idx = out.find("from pathlib import Path")
        dasmos_idx = out.find("import dasmos")
        assert 0 <= os_idx < dasmos_idx
        assert 0 <= path_idx < dasmos_idx

    def test_module_docstring_preserved_as_triple_quoted(self):
        out = port('''
            """Disassembly driver for foo.

            This is line 3.
            And line 4."""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
        ''')
        # The triple-quoted multiline form survives — not the
        # \\n-escaped single-line form ``ast.unparse`` produces by
        # default.
        assert '"""' in out
        # The literal newline inside the docstring is preserved.
        assert "Disassembly driver for foo.\n\nThis is line 3." in out
        # And not the collapsed escape form.
        assert "Disassembly driver for foo.\\n\\nThis is line 3." not in out

    def test_hex_int_literal_preserved_in_addresses(self):
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            entry(0xE000)
            label(0xE450, "loop")
        """)
        # Decimal forms must NOT appear for the address-shaped values.
        assert "57344" not in out  # 0xE000
        assert "58448" not in out  # 0xE450
        # Hex forms ARE present (case-insensitive — porter preserves
        # whatever case the input used).
        assert "0xE000" in out or "0xe000" in out
        assert "0xE450" in out or "0xe450" in out

    def test_decimal_int_literal_preserved(self):
        # The porter only preserves hex when the source used hex —
        # decimal literals stay decimal.
        out = port("""
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            byte(0xFFF0, length=42)
        """)
        assert "length=42" in out

    def test_multiline_comment_string_preserved_as_triple_quoted(self):
        out = port('''
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, """First paragraph.

            Second paragraph with a [`link`](address:E100?hex)
            spanning lines.""")
        ''')
        # The literal newlines stay literal — no \\n escapes in the
        # ported call.
        assert "First paragraph.\\n" not in out
        # The triple-quoted form lands.
        assert "First paragraph." in out
        assert "Second paragraph" in out
        # And both fragments appear inside a single triple-quoted
        # string (the gap between them is a real newline).
        # Find ``First paragraph.`` and ``Second paragraph`` and
        # check they're separated by a literal newline.
        first = out.find("First paragraph.")
        second = out.find("Second paragraph")
        assert first >= 0 and second > first
        assert "\n" in out[first:second]

    def test_subroutine_call_preceded_by_two_blank_lines(self):
        out = port('''
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "first comment", inline=True)
            subroutine(0xE100, "frob", title="Frob the bus")
        ''')
        # Find the d.subroutine call and check what's right before it.
        sub_idx = out.find("d.subroutine(")
        assert sub_idx >= 0
        # Two blank lines = three consecutive ``\\n`` characters
        # immediately before the ``d.subroutine`` line (the first
        # ``\\n`` ends the previous line, the next two are the blanks).
        prefix = out[max(0, sub_idx - 6):sub_idx]
        assert prefix.endswith("\n\n\n"), prefix

    def test_label_call_preceded_by_one_blank_line(self):
        out = port('''
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "first comment", inline=True)
            label(0xE100, "loop")
        ''')
        # Find ``d.label(`` for our user-supplied label (skip the
        # one inserted by load/entry rewrites).
        idx = out.find("d.label(57600, 'loop')")
        if idx < 0:
            idx = out.find("d.label(0xE100")
            if idx < 0:
                idx = out.find("d.label(0xe100")
        assert idx >= 0
        # One blank line = two ``\\n`` immediately before.
        prefix = out[max(0, idx - 6):idx]
        assert prefix.endswith("\n\n"), prefix
        assert not prefix.endswith("\n\n\n"), prefix

    def test_label_then_subroutine_at_same_addr_two_blanks_on_label(self):
        # Common pattern: ``label(addr, name); subroutine(addr, name, ...)``.
        # The two blanks attach to the label so the pair reads as a
        # single header block (instead of having blanks between the
        # label and its subroutine).
        out = port('''
            from py8dis.commands import *
            load(0xE000, "rom.bin", "6502")
            comment(0xE000, "first comment", inline=True)
            label(0xE100, "frob")
            subroutine(0xE100, "frob", title="Frob the bus")
        ''')
        label_idx = out.find("d.label(")
        # Find the SECOND d.label call (the first is just-load
        # bookkeeping) — actually we expect only one user
        # ``d.label(`` for ``frob``. Skip past any ``d.label`` that
        # comes from load.
        # Easier: find specifically by name.
        label_idx = out.find("'frob')")
        sub_idx = out.find("d.subroutine(")
        assert label_idx >= 0 and sub_idx > label_idx
        # Two blanks before the label.
        # Walk back to find the start of the label line.
        line_start = out.rfind("\n", 0, label_idx) + 1
        prefix = out[max(0, line_start - 6):line_start]
        assert prefix.endswith("\n\n\n"), prefix
        # And NO extra blanks between label and subroutine.
        between = out[label_idx:sub_idx]
        assert "\n\n" not in between, between


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
