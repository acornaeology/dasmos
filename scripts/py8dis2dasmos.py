"""Translate a py8dis driver script into a dasmos driver script.

Usage::

    python scripts/py8dis2dasmos.py path/to/disasm_thing.py > ported.py
    python scripts/py8dis2dasmos.py --check path/to/disasm_thing.py

The translation is AST-based (per ``docs/design/decisions.md`` D-014):
the input is parsed with :mod:`ast`, the call sites are rewritten,
and the result is emitted with :func:`ast.unparse`.

Currently handles the rules surfaced by the smallest sample drivers
(``acorn-econet-bridge``); the rule set grows as larger drivers
(ADFS / NFS) bring new patterns. See
``docs/design/commands-sweep-memo.md`` for the full list of py8dis
patterns the porter eventually needs to cover.

The porter does not run the ported script — it only produces the
text. The CI's round-trip test runs the ported text through dasmos
and re-assembles via beebasm, validating both the porter and the
disassembler in one shot.
"""

import argparse
import ast
import difflib
import io
import sys
import tokenize
from pathlib import Path

# Map py8dis CPU names to dasmos plug-in names.
CPU_NAME_MAP: dict[str, str] = {
    "6502": "6502",
    "65c02": "65C02",
    "65C02": "65C02",  # py8dis drivers spell it uppercase
}

# py8dis's free functions that become methods on the Disassembler.
# The set grows as more rules land. Some need per-method kwarg
# transformations (see ``_transform_kwargs``).
DASMOS_METHODS: frozenset[str] = frozenset({
    "label",
    "optional_label",
    "local_label",
    "expr_label",
    "entry",
    "byte",
    "word",
    "fill",
    "string",
    "comment",
    "expr",
    "subroutine",
    "banner",
    "add_move",
    "hook_subroutine",
    "code_ptr",
    "rts_code_ptr",
    "stringz",
    "stringcr",
    "constant",
})


# py8dis free-function names that map to differently-named dasmos
# Disassembler methods. Applied before the DASMOS_METHODS check so the
# rewrite to ``d.<dasmos_name>(...)`` uses the right attr.
PY8DIS_FUNCTION_RENAMES: dict[str, str] = {
    # py8dis's ``move(binary_addr, runtime_addr, length)`` registers a
    # relocation; dasmos's equivalent is ``Disassembler.add_move``.
    "move": "add_move",
    # ``constant(value, name)`` is now a first-class dasmos method
    # too — it both registers a named-value record (surfaced as the
    # ``constants`` section in structured output) AND emits an
    # optional label so the asm equate is unchanged from when this
    # rule routed via ``optional_label``. ``comment=`` rewrite still
    # applies (the dasmos method takes ``comment`` directly).
}


# Top-level calls to these py8dis free functions are silently dropped
# by the porter — the corresponding dasmos feature isn't implemented
# yet. Drivers using these features may still round-trip byte-
# identically, but the rendered annotations will be poorer than
# py8dis's output. When the dropped call appears as the rhs of an
# assignment, the LHS name is also tracked in
# ``dropped_internal_names`` so the cascade drops any follow-up
# statement that uses the would-be-defined variable.
UNSUPPORTED_PY8DIS_FUNCTIONS: frozenset[str] = frozenset({
    # py8dis's auto-comment suppression hook. py8dis generates
    # automatic per-instruction comments and ``no_automatic_comment``
    # inhibits that at a given address. dasmos doesn't generate
    # auto-comments, so suppressing them is a no-op — drop the call.
    "no_automatic_comment",
})


# Name of the local variable the porter binds the IR to so the same
# trace is shared between the asm and JSON render passes. Both
# ``go(...)`` and ``get_structured()`` rewrites use this name; the
# porter emits a single ``<IR_VAR_NAME> = d.disassemble()`` line at
# the first point of use and reuses it.
IR_VAR_NAME = "ir"


# py8dis names that are part of ``py8dis.commands`` and now live in
# dasmos sub-modules. The porter prepends explicit imports for any of
# these that the ported driver references, so the wildcard
# ``from py8dis.commands import *`` we drop doesn't leave them
# undefined.
PY8DIS_COMMAND_RELOCATIONS: dict[str, str] = {
    # Subroutine hooks ported to ``dasmos.hooks``.
    "stringhi_hook": "dasmos.hooks",
    "stringz_hook": "dasmos.hooks",
}


# py8dis ``acorn.<func>()`` calls map to dasmos environment plug-ins.
# The porter rewrites each call into a ``d.use_environment("...")``
# call so the same effect is achieved through the composable
# environments axis. Where py8dis's function bundles knowledge that
# dasmos splits into multiple environments (``acorn.bbc()`` includes
# both MOS labels and BBC hardware addresses), only the environments
# we've actually ported are activated — the rest is a known gap that
# closes when more environments land.
PY8DIS_ACORN_FUNC_TO_ENVIRONMENTS: dict[str, list[str]] = {
    # ``acorn.bbc()`` registers MOS workspace + vectors + OS calls
    # (the ``acorn_mos`` env) and the Model B I/O register block
    # (``acorn_model_b_hardware``). The floppy-disc-controller envs
    # (``acorn_fdc_8271`` / ``acorn_fdc_1770``) are NOT auto-
    # activated: a BBC Micro shipped without a disc interface, and
    # the FDC was always an upgrade (8271 board, 1770 board, or a
    # third-party fit). Drivers for ROMs that touch the FDC opt in
    # explicitly via the porter's ``--env`` flag (or by adding a
    # ``d.use_environment(...)`` line in the ported script).
    "bbc": ["acorn_mos", "acorn_model_b_hardware"],
    # ``acorn.b_plus()`` is structurally the same — same I/O block,
    # same opt-in FDC stance. The B+ shipped with a 1770 from the
    # factory, but per the modular design the user pairs
    # ``acorn_fdc_1770`` with this env when the ROM warrants it.
    "b_plus": ["acorn_mos", "acorn_model_b_hardware"],
    # ``acorn.master()`` is the Master fit-out: MOS labels and the
    # Master hardware register block (ACCCON etc). The Master's
    # 1770 is, again, opt-in.
    "master": ["acorn_mos", "acorn_master_hardware"],
    # ``acorn.is_sideways_rom()`` recognises the &8000 header layout
    # — direct one-to-one map.
    "is_sideways_rom": ["acorn_sideways_rom"],
    # ``acorn.mos_labels()`` is the MOS-only subset of bbc()/master().
    "mos_labels": ["acorn_mos"],
    # ``acorn.hardware_bbc()`` and ``acorn.hardware_b_plus()`` are
    # the hardware-only subsets of bbc()/b_plus(): Model B I/O block,
    # FDC opt-in.
    "hardware_bbc": ["acorn_model_b_hardware"],
    "hardware_b_plus": ["acorn_model_b_hardware"],
    # ``acorn.hardware_master()`` is the hardware-only subset of
    # master() — Master I/O block, FDC opt-in.
    "hardware_master": ["acorn_master_hardware"],
}


# Free functions that the porter consumes specially (not rewritten as
# d.method calls — they fold into the constructor or output stage).
SPECIAL_FUNCTIONS: frozenset[str] = frozenset({"init", "load", "go"})


# py8dis's memory-read free functions become method calls on the
# Disassembler's MemoryImage. Map of py8dis name → dasmos method name
# on ``d.memory``.
MEMORY_ACCESSORS: dict[str, str] = {
    "get_u8_binary": "get_u8",
    "get_u16_binary": "get_u16_le",
    "get_u16_be_binary": "get_u16_be",
}


def _inject_encoding_kwarg(call: ast.Call) -> None:
    """Append ``encoding="utf-8"`` to ``call`` unless it already has
    an ``encoding=`` keyword.

    Used during porting to make ``foo_filepath.read_text()`` /
    ``write_text(...)`` calls explicit about their encoding instead
    of inheriting the platform's locale default (cp1252 on Windows,
    which mangles non-Latin-1 characters that show up in dasmos
    output — em-dash, arrows, Greek letters, etc.).
    """
    for kw in call.keywords:
        if kw.arg == "encoding":
            return
    call.keywords.append(
        ast.keyword(arg="encoding", value=ast.Constant(value="utf-8")),
    )


class Py8disToDasmosTransformer(ast.NodeTransformer):
    """Walks a py8dis driver AST and rewrites it as a dasmos driver.

    The transformer collects state about the load/init pair as it
    visits the module body, then emits an ``Disassembler.create()``
    constructor + ``d.load(...)`` call in their place.

    Per-call rewrites (``label(...)`` → ``d.label(...)``) happen via
    :meth:`visit_Call`; the load/init/go specials are handled in
    :meth:`visit_Module`.
    """

    def __init__(self, extra_envs: tuple[str, ...] = ()):
        self.assembler_name = "beebasm"
        # Opt-in environments the caller wants activated alongside
        # whatever the py8dis driver explicitly requests. Used for
        # axes the original driver took for granted but dasmos models
        # as separate composable envs — most commonly the FDC chip
        # (8271 vs 1770), which py8dis bundled into ``bbc()`` but
        # dasmos treats as an opt-in upgrade.
        self.extra_envs: tuple[str, ...] = tuple(extra_envs)
        # Tracks whether ``ir = d.disassemble()`` has already been
        # emitted into the rewritten module body. Set when the first
        # caller of the IR (``go()`` or ``get_structured()``) is
        # rewritten; checked subsequently to avoid emitting it twice.
        self._ir_var_emitted = False
        # Per-statement signal: visit_Call sets this when it rewrites
        # a ``get_structured()`` call to ``ir.render('json').data``,
        # so visit_Module knows to prepend the IR-var assignment to
        # the surrounding statement if it hasn't already been emitted.
        self._used_ir_in_visit = False
        # ``autostring_min_length`` value extracted from a top-level
        # ``go(...)`` (or ``output = go(...)``) call by the pre-scan in
        # :meth:`visit_Module`. ``None`` means "use py8dis's default
        # of 3" (so dasmos's matching default applies). A specific
        # integer or ``None`` (from ``post_trace_steps=lambda: None``)
        # threads through to ``string_detection_min_length=`` on the
        # ``Disassembler.create(...)`` constructor.
        self._string_detection_min_length: int | None = 3
        self._string_detection_explicit = False

    def visit_Module(self, node: ast.Module) -> ast.Module:
        # Pre-scan for top-level ``go(...)`` calls so any
        # ``autostring_min_length=`` / ``post_trace_steps=`` kwargs
        # threaded through to ``Disassembler.create(...)`` further
        # down. ``go()`` appears AFTER ``load()`` in py8dis driver
        # scripts, so without a pre-scan the ctor would already be
        # built without the right setting.
        self._prescan_go_kwargs(node)

        new_body: list[ast.stmt] = []
        used_align_inline = False
        # Names bound to py8dis internals via dropped ``from
        # py8dis.X import Y as Z`` statements. Any later statement
        # that references one of these is also dropped — drivers
        # occasionally reach into py8dis internals to override
        # classifications (e.g. NFS-3.65's copyright-string split),
        # and we'd rather drop the override silently than leave
        # broken references in the ported script.
        dropped_internal_names: set[str] = set()

        for stmt in node.body:
            # Drop ``from py8dis.commands import *`` — replaced by
            # the import block we prepend at the end.
            if isinstance(stmt, ast.ImportFrom) and stmt.module == "py8dis.commands":
                continue
            # Drop ``from py8dis.X import ...`` — anything py8dis
            # internal becomes invalid in a dasmos driver. Record
            # the bound names so any downstream statement that uses
            # them gets dropped too.
            if (
                isinstance(stmt, ast.ImportFrom)
                and stmt.module
                and stmt.module.startswith("py8dis")
            ):
                for alias in stmt.names:
                    dropped_internal_names.add(alias.asname or alias.name)
                continue
            # Drop ``import py8dis.X [as alias]`` — the porter
            # rewrites the alias.<func>() calls below into
            # ``d.use_environment(...)`` calls, so the import itself
            # is no longer needed. Record the bound aliases too, so
            # any non-handled downstream reference is dropped too.
            if isinstance(stmt, ast.Import) and any(
                alias.name.startswith("py8dis") for alias in stmt.names
            ):
                for alias in stmt.names:
                    if alias.name.startswith("py8dis"):
                        dropped_internal_names.add(
                            alias.asname or alias.name.split(".")[0],
                        )
                # Drop only the py8dis ones — split the names list
                # if other imports are mixed in (rare).
                kept = [
                    alias for alias in stmt.names
                    if not alias.name.startswith("py8dis")
                ]
                if not kept:
                    continue
                stmt.names = kept

            # Translate ``acorn.<func>()`` (or any aliased
            # ``<alias>.<func>()`` where the alias was bound to the
            # py8dis ``acorn`` module) into one or more
            # ``d.use_environment("...")`` calls. Runs BEFORE the
            # drop-references-to-internals check so calls through a
            # dropped alias (the typical case) get translated rather
            # than dropped.
            env_stmts = self._maybe_acorn_func_to_env_use(stmt)
            if env_stmts is not None:
                new_body.extend(env_stmts)
                continue

            # Drop any statement that references a name bound to a
            # py8dis internal we've dropped — usually
            # classification-override hacks like
            # ``_disasm.classifications[...] = _cls.String(...)``.
            # These leave the ported script syntactically valid
            # rather than referring to an undefined ``_cls``.
            if dropped_internal_names and self._references_any(
                stmt, dropped_internal_names,
            ):
                continue

            # Drop top-level calls to py8dis features dasmos doesn't
            # support yet. The ported script keeps running; the rendered
            # disassembly just loses whatever annotations the dropped
            # call would have contributed.
            if (
                UNSUPPORTED_PY8DIS_FUNCTIONS
                and isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and self._call_name(stmt.value) in UNSUPPORTED_PY8DIS_FUNCTIONS
            ):
                continue
            # Same for assignments: ``x = get_structured()`` drops the
            # whole assignment AND tracks ``x`` so any later statement
            # that uses ``x`` (e.g. ``json.dumps(x)``) cascades-drops.
            if (
                UNSUPPORTED_PY8DIS_FUNCTIONS
                and isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Call)
                and self._call_name(stmt.value) in UNSUPPORTED_PY8DIS_FUNCTIONS
            ):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        dropped_internal_names.add(target.id)
                continue

            # Detect ``subroutine(..., is_entry_point=False, ...)``
            # and ``data_banner(...)`` BEFORE visit_Call rewrites.
            # Both expand to the same two-statement form (label +
            # banner) so they can't be handled as a single Call
            # rewrite. ``data_banner`` is py8dis's syntactic sugar
            # for ``subroutine(..., is_entry_point=False)``: a
            # subroutine-style banner header on a data region that
            # MUST NOT register a code entry point (else the trace
            # would treat the data bytes as code).
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and (
                    (
                        self._call_name(stmt.value) == "subroutine"
                        and self._is_kw_constant(
                            stmt.value, "is_entry_point", False,
                        )
                    )
                    or self._call_name(stmt.value) == "data_banner"
                )
            ):
                expanded = self._convert_subroutine_to_label_banner(stmt.value)
                # Visit each new statement so its Call children are
                # rewritten too.
                for new_stmt in expanded:
                    new_stmt = self.visit(new_stmt)
                    new_body.append(new_stmt)
                continue

            # Visit children first — rewrites Call nodes inside.
            # ``_used_ir_in_visit`` is set by visit_Call when it
            # rewrites ``get_structured()`` to ``ir.render('json').data``
            # somewhere inside this statement; we use that signal to
            # decide whether to prepend ``ir = d.disassemble()`` to
            # the surrounding statement.
            self._used_ir_in_visit = False
            stmt = self.visit(stmt)
            stmt_used_ir = self._used_ir_in_visit

            # Top-level Expr(Call(...)) special-cases.
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                func_name = self._call_name(call)

                if func_name == "init":
                    self._consume_init(call)
                    continue
                if func_name == "load":
                    new_body.extend(self._convert_load(call))
                    continue
                if func_name == "go":
                    new_body.extend(self._convert_go(call))
                    continue

            # ``output = go(print_output=False)`` — go() used as a
            # value; rewrite RHS to the rendered-text expression and
            # emit ``ir = d.disassemble()`` first if not already
            # emitted.
            if (
                isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Call)
                and self._call_name(stmt.value) == "go"
            ):
                new_body.extend(self._maybe_emit_ir_assignment())
                stmt.value = self._render_text_expression()
                new_body.append(stmt)
                continue

            # If visit_Call rewrote a ``get_structured()`` somewhere
            # inside this statement (e.g. inside a try/except, or as
            # the rhs of an assignment), prepend the IR-var
            # assignment so the rewritten expression has a binding to
            # use.
            if stmt_used_ir:
                new_body.extend(self._maybe_emit_ir_assignment())

            # Detect Align.INLINE usage anywhere in the rewritten
            # statement (so we can decide whether to import Align).
            if not used_align_inline and self._mentions_align_inline(stmt):
                used_align_inline = True

            new_body.append(stmt)

        # Lift the canonical ``try: structured = get_structured(); ...
        # write_text(json.dumps(structured)) ...; except: ...`` pattern
        # into a flat write_text(str(ir.render('json'))) sequence.
        # The defensive try/except hides bugs, the .data + json.dumps
        # plumbing is redundant (StructuredOutput is already
        # __str__-able), and dropping both makes the ported driver
        # readable. Runs before extra-env injection so the lifted
        # statements participate normally in the rest of the body.
        new_body = _simplify_json_emit(new_body)

        # Inject any caller-requested opt-in envs as additional
        # ``d.use_environment(...)`` calls. Place them next to the
        # other use_environment calls (which came from py8dis acorn
        # function translations) so the activations group visibly in
        # the output. If the driver had no acorn function calls,
        # fall back to inserting right after the constructor / load
        # block so they execute before any labels or classifications.
        if self.extra_envs:
            insertion_index = self._extra_env_insertion_index(new_body)
            for env_name in self.extra_envs:
                new_body.insert(insertion_index, ast.Expr(value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="d", ctx=ast.Load()),
                        attr="use_environment",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=env_name)],
                    keywords=[],
                )))
                insertion_index += 1

        # Build the dasmos import block.
        dasmos_imports: list[ast.stmt] = [
            ast.Import(names=[ast.alias(name="dasmos", asname=None)]),
        ]
        if used_align_inline:
            dasmos_imports.append(
                ast.ImportFrom(
                    module="dasmos",
                    names=[ast.alias(name="Align", asname=None)],
                    level=0,
                )
            )

        # Detect names from py8dis.commands that have been relocated
        # to dasmos sub-modules (e.g. ``stringhi_hook`` →
        # ``dasmos.hooks``); add explicit imports for any actually
        # used by the ported body.
        relocations_needed = self._find_relocations_needed(new_body)
        for module, names in sorted(relocations_needed.items()):
            dasmos_imports.append(
                ast.ImportFrom(
                    module=module,
                    names=[ast.alias(name=n, asname=None) for n in sorted(names)],
                    level=0,
                )
            )

        # Splice the dasmos imports AFTER the leading docstring + any
        # existing imports (typically the driver's stdlib block:
        # json, os, sys, pathlib). Putting them at the very top would
        # demote the module docstring to a stranded string literal
        # and read against PEP 8's "stdlib first, third-party after"
        # convention.
        insertion_idx = self._import_insertion_index(new_body)
        new_body[insertion_idx:insertion_idx] = dasmos_imports

        return ast.Module(body=new_body, type_ignores=[])

    @staticmethod
    def _import_insertion_index(body: list[ast.stmt]) -> int:
        """Return the index in ``body`` where ``import dasmos`` (and
        its companions) should be inserted: after a leading docstring
        and any contiguous stdlib import block, but before the first
        non-import / non-docstring statement.
        """
        idx = 0
        # Leading module docstring is an Expr wrapping a string Constant.
        if (
            idx < len(body)
            and isinstance(body[idx], ast.Expr)
            and isinstance(body[idx].value, ast.Constant)
            and isinstance(body[idx].value.value, str)
        ):
            idx += 1
        # Then any contiguous block of imports.
        while idx < len(body) and isinstance(body[idx], (ast.Import, ast.ImportFrom)):
            idx += 1
        return idx

    @staticmethod
    def _extra_env_insertion_index(body: list[ast.stmt]) -> int:
        """Return the index in ``body`` where caller-requested
        opt-in env activations should be spliced. Right after the
        last existing ``d.use_environment(...)`` call (so all the
        env activations group together), or right after the
        ``d = dasmos.Disassembler.create(...)`` / ``d.load(...)``
        pair if no use_environment calls exist yet.
        """
        last_use_env = -1
        last_load = -1
        last_create = -1
        for i, stmt in enumerate(body):
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and isinstance(stmt.value.func.value, ast.Name)
                and stmt.value.func.value.id == "d"
                and stmt.value.func.attr == "use_environment"
            ):
                last_use_env = i
            elif (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and isinstance(stmt.value.func.value, ast.Name)
                and stmt.value.func.value.id == "d"
                and stmt.value.func.attr == "load"
            ):
                last_load = i
            elif (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id == "d"
            ):
                last_create = i
        if last_use_env >= 0:
            return last_use_env + 1
        if last_load >= 0:
            return last_load + 1
        if last_create >= 0:
            return last_create + 1
        return 0

    @staticmethod
    def _find_relocations_needed(
        body: list[ast.stmt],
    ) -> dict[str, set[str]]:
        """Walk ``body``; return a dict ``{module: {names}}`` of every
        :data:`PY8DIS_COMMAND_RELOCATIONS` name actually referenced.
        """
        result: dict[str, set[str]] = {}
        class NameVisitor(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                if node.id in PY8DIS_COMMAND_RELOCATIONS:
                    module = PY8DIS_COMMAND_RELOCATIONS[node.id]
                    result.setdefault(module, set()).add(node.id)
        visitor = NameVisitor()
        for stmt in body:
            visitor.visit(stmt)
        return result

    def visit_Call(self, node: ast.Call) -> ast.expr:
        """Rewrite a free-function call into a ``d.method`` call when
        the function name is one we recognise. ``get_structured()``
        is a special case: it returns a value (not a side-effecting
        method) and is replaced with the equivalent expression
        ``ir.render('json').data``.
        """
        self.generic_visit(node)  # transform children first

        if isinstance(node.func, ast.Name):
            name = node.func.id
            # ``get_structured()`` → ``ir.render('json').data``. The
            # caller (visit_Module) emits ``ir = d.disassemble()``
            # before this statement if the IR var hasn't been
            # introduced yet.
            if name == "get_structured" and not node.args and not node.keywords:
                self._used_ir_in_visit = True
                return self._json_render_data_expression()
            # Apply py8dis→dasmos renames (e.g. ``move`` →
            # ``add_move``) before the DASMOS_METHODS check.
            dasmos_name = PY8DIS_FUNCTION_RENAMES.get(name, name)
            if dasmos_name in DASMOS_METHODS:
                node.func = ast.Attribute(
                    value=ast.Name(id="d", ctx=ast.Load()),
                    attr=dasmos_name,
                    ctx=ast.Load(),
                )
                self._transform_kwargs(dasmos_name, node)
            elif name in MEMORY_ACCESSORS:
                # Memory accessors live on ``d.memory`` rather than
                # directly on ``d``.
                node.func = ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="d", ctx=ast.Load()),
                        attr="memory",
                        ctx=ast.Load(),
                    ),
                    attr=MEMORY_ACCESSORS[name],
                    ctx=ast.Load(),
                )
        elif isinstance(node.func, ast.Attribute):
            # ``something.read_text()`` / ``something.write_text(x)`` —
            # inject encoding="utf-8" so the ported driver doesn't
            # inherit the platform's locale default. py8dis drivers
            # commonly do ``output_filepath.write_text(output)`` at
            # the bottom; on Windows that uses cp1252 and chokes on
            # the U+2192 (→) and similar arrows the renderer emits.
            if node.func.attr in ("read_text", "write_text"):
                _inject_encoding_kwarg(node)
        return node


    # -- specials --------------------------------------------------------

    def _consume_init(self, call: ast.Call) -> None:
        """Extract relevant settings from ``init(...)`` so we can use
        them later (e.g. the assembler name for the render call).
        """
        for kw in call.keywords:
            if kw.arg == "assembler_name" and isinstance(kw.value, ast.Constant):
                self.assembler_name = kw.value.value

    def _prescan_go_kwargs(self, module: ast.Module) -> None:
        """Walk ``module.body`` looking for top-level ``go(...)``
        calls (either bare ``go(...)`` or ``output = go(...)``) and
        extract their ``autostring_min_length`` / ``post_trace_steps``
        kwargs into :attr:`_string_detection_min_length`.

        Recognised forms:

        - ``go()`` / ``go(print_output=False)`` — defaults apply
          (autostring runs with ``min_length=3``).
        - ``go(autostring_min_length=N)`` — sets the threshold to N.
        - ``go(post_trace_steps=lambda: None)`` — disables autostring
          (translates to ``string_detection_min_length=None``).
        - ``go(post_trace_steps=lambda: classification.autostring(K))``
          — disables py8dis's default and runs autostring with
          ``min_length=K``. Translates to
          ``string_detection_min_length=K``.

        Anything fancier (a real custom callable bound to
        ``post_trace_steps``) is reported as a porter limitation —
        the dasmos analogue is a per-address
        ``_post_trace_jsr_analyzers`` registration, not a generic
        post-trace hook, so blind translation isn't safe.
        """
        for stmt in module.body:
            call = self._extract_go_call(stmt)
            if call is None:
                continue
            for kw in call.keywords:
                if kw.arg == "autostring_min_length":
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                        self._string_detection_min_length = kw.value.value
                        self._string_detection_explicit = True
                elif kw.arg == "post_trace_steps":
                    self._consume_post_trace_steps_kwarg(kw.value)
            # First go() wins. Multiple go() calls in one driver
            # would be unusual; if encountered, the first sets the
            # ctor and the rest get the same translation.
            return

    @staticmethod
    def _extract_go_call(stmt: ast.stmt) -> ast.Call | None:
        """Return the :class:`ast.Call` for a top-level ``go(...)``
        call (bare or as the rhs of an assignment), or ``None`` if
        the statement isn't a ``go`` invocation.
        """
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
        elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            call = stmt.value
        else:
            return None
        if isinstance(call.func, ast.Name) and call.func.id == "go":
            return call
        return None

    def _consume_post_trace_steps_kwarg(self, value: ast.expr) -> None:
        """Translate the ``post_trace_steps=`` lambda from py8dis's
        ``go()`` into a setting on dasmos's
        :attr:`string_detection_min_length`. See
        :meth:`_prescan_go_kwargs` for the recognised shapes.
        """
        # post_trace_steps=lambda: None — disables autostring entirely.
        if (
            isinstance(value, ast.Lambda)
            and not value.args.args
            and isinstance(value.body, ast.Constant)
            and value.body.value is None
        ):
            self._string_detection_min_length = None
            self._string_detection_explicit = True
            return
        # post_trace_steps=lambda: classification.autostring(K) — set
        # the threshold to K.
        if (
            isinstance(value, ast.Lambda)
            and not value.args.args
            and isinstance(value.body, ast.Call)
            and isinstance(value.body.func, ast.Attribute)
            and value.body.func.attr == "autostring"
            and len(value.body.args) == 1
            and isinstance(value.body.args[0], ast.Constant)
            and isinstance(value.body.args[0].value, int)
        ):
            self._string_detection_min_length = value.body.args[0].value
            self._string_detection_explicit = True
            return
        # Anything else is too custom for a blind translation. Warn
        # the porter user via stderr; leave the default in place.
        print(
            "warning: post_trace_steps= kwarg on go() uses an unrecognised "
            "shape; the default string-detection setting "
            f"(min_length={self._string_detection_min_length}) is being "
            "preserved. Convert any custom post-trace work into per-address "
            "analyzers via Disassembler._post_trace_jsr_analyzers in the "
            "ported driver if needed.",
            file=sys.stderr,
        )

    def _convert_load(self, call: ast.Call) -> list[ast.stmt]:
        """Convert ``load(addr, file, cpu, md5=...)`` into:

        - ``d = dasmos.Disassembler.create(cpu="<mapped>")``
        - ``d.load(file, addr, md5sum=...)``

        py8dis's load argument order is ``(load_addr, filename,
        cpu_name, md5sum)``. dasmos's load takes
        ``(filepath, binary_addr, md5sum=...)`` — note the swapped
        first two args.
        """
        # Pull positional args defensively.
        if len(call.args) < 2:
            raise ValueError(
                f"load() needs at least (load_addr, filename); "
                f"got {len(call.args)} positional arg(s)"
            )
        load_addr = call.args[0]
        filename = call.args[1]
        cpu_arg: ast.expr | None = call.args[2] if len(call.args) > 2 else None
        md5_arg: ast.expr | None = call.args[3] if len(call.args) > 3 else None

        # Also check for md5sum= kwarg.
        for kw in call.keywords:
            if kw.arg == "md5sum":
                md5_arg = kw.value

        # Map the CPU name. If it's a string literal, translate;
        # otherwise pass through as-is (drivers occasionally compute
        # the CPU name dynamically).
        if cpu_arg is None:
            dasmos_cpu: ast.expr = ast.Constant(value="6502")
        elif isinstance(cpu_arg, ast.Constant) and isinstance(cpu_arg.value, str):
            mapped = CPU_NAME_MAP.get(cpu_arg.value, cpu_arg.value)
            dasmos_cpu = ast.Constant(value=mapped)
        else:
            dasmos_cpu = cpu_arg

        # d = dasmos.Disassembler.create(
        #     cpu=...,
        #     auto_label_data_prefix="l",      # py8dis defaults
        #     auto_label_code_prefix="c",
        #     auto_label_subroutine_prefix="sub_c",
        #     auto_label_loop_prefix="loop_c",
        # )
        # The auto-label prefixes match py8dis's defaults so ported
        # drivers produce textually-similar output to the original
        # (label names are the most-visible part of the diff between
        # py8dis-fork and dasmos output during the migration).
        # ``return_`` is dasmos's default and matches py8dis too —
        # no override needed.
        ctor_kwargs: list[ast.keyword] = [
            ast.keyword(arg="cpu", value=dasmos_cpu),
            ast.keyword(
                arg="auto_label_data_prefix",
                value=ast.Constant(value="l"),
            ),
            ast.keyword(
                arg="auto_label_code_prefix",
                value=ast.Constant(value="c"),
            ),
            ast.keyword(
                arg="auto_label_subroutine_prefix",
                value=ast.Constant(value="sub_c"),
            ),
            ast.keyword(
                arg="auto_label_loop_prefix",
                value=ast.Constant(value="loop_c"),
            ),
        ]
        # Thread an explicit ``string_detection_min_length=`` kwarg
        # through only when the source ``go(...)`` call set
        # ``autostring_min_length`` or ``post_trace_steps`` to a
        # non-default shape. Otherwise the default (3) on the dasmos
        # side already matches py8dis.
        if self._string_detection_explicit:
            ctor_kwargs.append(ast.keyword(
                arg="string_detection_min_length",
                value=ast.Constant(value=self._string_detection_min_length),
            ))
        ctor = ast.Assign(
            targets=[ast.Name(id="d", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id="dasmos", ctx=ast.Load()),
                        attr="Disassembler",
                        ctx=ast.Load(),
                    ),
                    attr="create",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=ctor_kwargs,
            ),
        )

        # d.load(filename, load_addr, md5sum=...)
        load_kwargs: list[ast.keyword] = []
        if md5_arg is not None:
            load_kwargs.append(ast.keyword(arg="md5sum", value=md5_arg))
        load_call = ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="d", ctx=ast.Load()),
                    attr="load",
                    ctx=ast.Load(),
                ),
                args=[filename, load_addr],
                keywords=load_kwargs,
            ),
        )

        return [ctor, load_call]

    def _convert_go(self, call: ast.Call) -> list[ast.stmt]:
        """Convert top-level ``go(...)`` into a (possibly empty)
        ``ir = d.disassemble()`` line followed by
        ``print(str(ir.render(...)))``.

        For an ``output = go(print_output=False)`` form (go used as a
        value), see the ``Assign`` branch in :meth:`visit_Module` —
        that uses :meth:`_render_text_expression` directly.

        ``go()``'s arguments (``print_output``, ``post_trace_steps``,
        ``autostring_min_length``) aren't yet honoured by the porter
        when used at the top level. The default behaviour (print to
        stdout) matches py8dis's default.
        """
        stmts: list[ast.stmt] = list(self._maybe_emit_ir_assignment())
        # print(str(ir.render("beebasm", **py8dis_compat_kwargs)))
        render_print = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[self._render_text_expression()],
                keywords=[],
            ),
        )
        stmts.append(render_print)
        return stmts

    def _render_text_expression(self) -> ast.Call:
        """Build the expression ``str(ir.render("<asm>", ...))``.

        Used as the RHS of ``output = go(print_output=False)`` and as
        the inner expression of the ``print(str(...))`` shape emitted
        by :meth:`_convert_go`. Always references the shared ``ir``
        variable; the caller is responsible for emitting
        ``ir = d.disassemble()`` first via
        :meth:`_maybe_emit_ir_assignment`.
        """
        return ast.Call(
            func=ast.Name(id="str", ctx=ast.Load()),
            args=[
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id=IR_VAR_NAME, ctx=ast.Load()),
                        attr="render",
                        ctx=ast.Load(),
                    ),
                    args=[ast.Constant(value=self.assembler_name)],
                    keywords=self._py8dis_compat_render_kwargs(),
                ),
            ],
            keywords=[],
        )

    def _json_render_data_expression(self) -> ast.Attribute:
        """Build the expression ``ir.render('json').data``.

        Used as the replacement for ``get_structured()``. The driver's
        downstream ``json.dumps(structured)`` continues to work
        because ``StructuredOutput.data`` is a plain dict — the same
        shape py8dis-fork's ``structured.py`` returned.
        """
        return ast.Attribute(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id=IR_VAR_NAME, ctx=ast.Load()),
                    attr="render",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value="json")],
                keywords=[],
            ),
            attr="data",
            ctx=ast.Load(),
        )

    def _maybe_emit_ir_assignment(self) -> list[ast.stmt]:
        """Return ``[ir = d.disassemble()]`` the first time this is
        called per port, ``[]`` thereafter. Lets multiple sites that
        depend on the IR (the asm render, the JSON render) share one
        trace.
        """
        if self._ir_var_emitted:
            return []
        self._ir_var_emitted = True
        return [
            ast.Assign(
                targets=[ast.Name(id=IR_VAR_NAME, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="d", ctx=ast.Load()),
                        attr="disassemble",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                ),
            ),
        ]

    @staticmethod
    def _py8dis_compat_render_kwargs() -> list[ast.keyword]:
        """Renderer kwargs that make dasmos's output match py8dis's
        defaults — what ported scripts expect by virtue of being
        ports. Boundary marker labels use the legacy ``pydis_``
        prefix; the byte-column inline annotation is enabled in
        py8dis flavour (bare binary hex with the
        ``:<runtime>[<move_id>]`` suffix inside relocated blocks).
        """
        return [
            ast.keyword(
                arg="boundary_label_prefix",
                value=ast.Constant(value="pydis_"),
            ),
            ast.keyword(
                arg="byte_column",
                value=ast.Constant(value=True),
            ),
            ast.keyword(
                arg="byte_column_format",
                value=ast.Constant(value="py8dis"),
            ),
            # py8dis chunks Byte / Word blocks more aggressively than
            # dasmos's defaults — 12 bytes / 6 words per row vs 8 / 4.
            # Match for parity.
            ast.keyword(
                arg="default_byte_cols",
                value=ast.Constant(value=12),
            ),
            ast.keyword(
                arg="default_word_cols",
                value=ast.Constant(value=6),
            ),
        ]

    # -- per-method kwarg rewriting --------------------------------------

    def _transform_kwargs(self, method_name: str, node: ast.Call) -> None:
        """Apply per-method kwarg transformations after the
        ``foo(...)`` → ``d.foo(...)`` rewrite.

        - ``move_id=`` → ``move=`` (universal). py8dis's ``move()``
          returned a context-manager-shaped value; dasmos's
          ``add_move()`` returns a typed :class:`~dasmos.core.move.Move`
          handle, and the kwarg name on every dasmos method is
          ``move=`` rather than ``move_id=``. ``move_id=None`` is
          dropped entirely (it was the redundant default).
        - ``comment(..., inline=True)`` →
          ``comment(..., align=Align.INLINE)`` (sweep memo C1).
          ``inline=False`` is silently dropped — it was the default in
          py8dis and corresponds to the dasmos default
          ``align=Align.BEFORE_LABEL``.
        - ``subroutine(...)`` and ``banner(...)`` get py8dis-specific
          kwargs stripped: ``hook=`` (no dasmos equivalent yet),
          ``is_entry_point=`` (the True case is the new default;
          the False case is rewritten upstream into a label + banner
          pair), ``on_entry=`` / ``on_exit=`` (py8dis register-usage
          docs not yet ported), ``at_binary_addr=`` (py8dis-specific).
        """
        # Universal: rewrite move_id= → move= and drop move_id=None.
        new_kwargs: list[ast.keyword] = []
        for kw in node.keywords:
            if (
                kw.arg == "move_id"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is None
            ):
                continue
            if kw.arg == "move_id":
                kw.arg = "move"
            new_kwargs.append(kw)
        node.keywords = new_kwargs

        if method_name == "comment":
            new_kwargs: list[ast.keyword] = []
            for kw in node.keywords:
                if kw.arg == "inline":
                    if (
                        isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        new_kwargs.append(
                            ast.keyword(
                                arg="align",
                                value=ast.Attribute(
                                    value=ast.Name(id="Align", ctx=ast.Load()),
                                    attr="INLINE",
                                    ctx=ast.Load(),
                                ),
                            )
                        )
                    # ``inline=False`` is the default; drop entirely.
                    continue
                new_kwargs.append(kw)
            node.keywords = new_kwargs

        elif method_name in ("subroutine", "banner"):
            # py8dis-specific kwargs that are either redundant in
            # dasmos (defaults) or not yet supported here.
            # ``on_entry`` / ``on_exit`` are STRUCTURED data (dicts of
            # register → description) — passed through to the dasmos
            # API so renderers can format them appropriately (the
            # beebasm renderer folds them into the banner block; a
            # JSON renderer would emit them as a real dict).
            DROPPED = {"hook", "is_entry_point", "at_binary_addr"}
            node.keywords = [
                kw for kw in node.keywords if kw.arg not in DROPPED
            ]

    def _convert_subroutine_to_label_banner(
        self, call: ast.Call,
    ) -> list[ast.stmt]:
        """Expand ``subroutine(addr, name, is_entry_point=False, ...)``
        into ``[label(addr, name), banner(addr, title=..., description=...)]``.

        The original idiom in py8dis combined the label and the
        decorated-comment block into one call; dasmos splits them per
        the C2/C3 sweep-memo recommendation. The porter materialises
        both statements; the label() call is harmless even if the
        driver also calls label() separately for the same address
        (LabelManager is idempotent on duplicate names).
        """
        if len(call.args) < 1:
            raise ValueError("subroutine() needs at least an address")
        addr = call.args[0]
        name: ast.expr | None = call.args[1] if len(call.args) > 1 else None

        # Pass through kwargs except the ones we explicitly consume.
        # ``move_id=`` is renamed to ``move=`` (and ``move_id=None``
        # dropped) by ``_transform_kwargs`` — that runs after this
        # method's caller substitutes the new node, so we apply the
        # same rule locally on the kwargs we forward.
        banner_kwargs: list[ast.keyword] = []
        for kw in call.keywords:
            if kw.arg in ("hook", "is_entry_point", "on_entry",
                          "on_exit", "at_binary_addr"):
                continue
            if (
                kw.arg == "move_id"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value is None
            ):
                continue
            if kw.arg == "move_id":
                kw.arg = "move"
            banner_kwargs.append(kw)

        # label(addr, name)  — only if a name was supplied.
        stmts: list[ast.stmt] = []
        if name is not None:
            stmts.append(
                ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="label", ctx=ast.Load()),
                        args=[addr, name],
                        keywords=[],
                    ),
                ),
            )

        # banner(addr, title=..., description=..., ...)
        stmts.append(
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="banner", ctx=ast.Load()),
                    args=[addr],
                    keywords=banner_kwargs,
                ),
            ),
        )
        return stmts

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _references_any(stmt: ast.stmt, names: set[str]) -> bool:
        """True iff the AST under ``stmt`` references any of the
        given top-level ``Name``s. Used to drop driver statements
        that touch py8dis internals via aliases the porter has
        already removed.
        """
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name) and node.id in names:
                return True
        return False

    @staticmethod
    def _maybe_acorn_func_to_env_use(stmt: ast.stmt) -> list[ast.stmt] | None:
        """If ``stmt`` is a top-level ``<alias>.<func>()`` expression
        whose ``<func>`` is one we map onto a dasmos environment,
        return the replacement ``d.use_environment(...)`` statements.
        Otherwise return ``None`` (caller falls through to the normal
        rewriting path).

        Recognises any ``<alias>.<func>()`` shape — we don't track
        which alias the import bound, since
        :data:`PY8DIS_ACORN_FUNC_TO_ENVIRONMENTS` keys are unique
        enough that a stray collision is implausible. Hardens against
        the original ``import py8dis.acorn as acorn`` *and* the
        equally common ``import py8dis.acorn`` (no alias).
        """
        if not isinstance(stmt, ast.Expr):
            return None
        call = stmt.value
        if not isinstance(call, ast.Call):
            return None
        if not isinstance(call.func, ast.Attribute):
            return None
        func_name = call.func.attr
        env_names = PY8DIS_ACORN_FUNC_TO_ENVIRONMENTS.get(func_name)
        if env_names is None:
            return None
        return [
            ast.Expr(value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="d", ctx=ast.Load()),
                    attr="use_environment",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=env_name)],
                keywords=[],
            ))
            for env_name in env_names
        ]

    @staticmethod
    def _call_name(call: ast.Call) -> str | None:
        """The name of the called function, or ``None`` if it's not a
        plain ``foo(...)`` form.
        """
        if isinstance(call.func, ast.Name):
            return call.func.id
        return None

    @staticmethod
    def _is_kw_constant(call: ast.Call, name: str, value) -> bool:
        """True iff ``call`` has a keyword arg ``name`` whose value is
        the literal constant ``value``.
        """
        for kw in call.keywords:
            if kw.arg == name and isinstance(kw.value, ast.Constant):
                return kw.value.value == value
        return False

    @staticmethod
    def _mentions_align_inline(stmt: ast.stmt) -> bool:
        """True iff the AST under ``stmt`` references ``Align.INLINE``."""
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "INLINE"
                and isinstance(node.value, ast.Name)
                and node.value.id == "Align"
            ):
                return True
        return False


def _annotate_int_literals(source: str, tree: ast.AST) -> None:
    """Stash the original token text of every integer literal in
    ``source`` onto its corresponding :class:`ast.Constant` node as
    ``_original_literal``.

    Python's ``ast`` module discards the lexical form of numeric
    literals — ``0xE000`` and ``57344`` parse to the same node. Driver
    scripts read by humans rely on the hex form for addresses, so we
    walk the source's tokens, record the original text of every
    integer-literal NUMBER token by ``(line, col)``, then attach that
    text to the matching Constant node. The custom unparser later
    uses ``_original_literal`` when present and falls back to
    ``repr(value)`` for nodes the porter synthesised.
    """
    by_pos: dict[tuple[int, int], str] = {}
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for tok in tokens:
            if tok.type == tokenize.NUMBER:
                by_pos[tok.start] = tok.string
    except tokenize.TokenizeError:
        return  # malformed source; bail rather than crash the porter
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        ):
            key = (node.lineno, node.col_offset)
            if key in by_pos:
                text = by_pos[key]
                # Only stash the original if it actually carries
                # information beyond ``repr(value)`` — i.e. a hex /
                # binary / octal prefix, or underscore separators.
                # Decimal literals round-trip fine through repr().
                if any(c in text for c in "_xXbBoO"):
                    node._original_literal = text


class _PortedDriverUnparser(ast._Unparser):  # noqa: SLF001 — stdlib-internal
    """Subclass of :class:`ast._Unparser` with three customisations
    needed by the dasmos porter:

    1. **Hex / binary / underscore-separated int literals** are
       preserved when the porter has stashed an ``_original_literal``
       on the Constant node (see :func:`_annotate_int_literals`).
    2. **Multiline string Constants** render as triple-quoted strings
       (literal newlines), matching the docstring path the base
       unparser already takes — comment / description text in driver
       scripts is meant to be readable.
    3. **Blank-line annotations**: statements with a
       ``_blank_lines_before`` attribute get that many extra
       newlines inserted before them, so subroutine and label
       declarations break up the otherwise-monolithic body.

    The ``ast._Unparser`` private API is stable across recent CPython
    releases and is what :func:`ast.unparse` itself uses.
    """

    def visit_Constant(self, node: ast.Constant) -> None:
        original = getattr(node, "_original_literal", None)
        if original is not None:
            self.write(original)
            return
        if isinstance(node.value, str) and "\n" in node.value:
            self._write_str_avoiding_backslashes(node.value)
            return
        super().visit_Constant(node)

    def traverse(self, node):
        if isinstance(node, ast.stmt):
            blanks = getattr(node, "_blank_lines_before", 0)
            for _ in range(blanks):
                self.write("\n")
        super().traverse(node)


def _is_ir_render_json_data(node: ast.expr | None) -> bool:
    """True iff ``node`` is the expression ``ir.render('json').data``
    (the rewritten form of py8dis ``get_structured()``).
    """
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "data"
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "render"
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == IR_VAR_NAME
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Constant)
        and node.value.args[0].value == "json"
    )


def _try_wraps_json_emit(stmt: ast.stmt) -> bool:
    """True iff ``stmt`` is a ``Try`` whose body contains the JSON-emit
    rewrite (``ir.render('json').data`` somewhere inside).
    """
    if not isinstance(stmt, ast.Try):
        return False
    for child in ast.walk(stmt):
        if _is_ir_render_json_data(child):
            return True
    return False


class _JsonDumpsToStrRender(ast.NodeTransformer):
    """Replace ``json.dumps(<var_name>)`` with ``str(ir.render('json'))``.

    Used after an ``<var_name> = ir.render('json').data`` assignment is
    detected — combined with dropping that assignment, this collapses
    the four-step py8dis JSON-emit pattern into a single
    ``write_text(str(ir.render('json')), ...)`` call.
    """

    def __init__(self, var_name: str):
        self.var_name = var_name
        self.count = 0

    def visit_Call(self, node: ast.Call) -> ast.expr:
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "dumps"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "json"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == self.var_name
        ):
            self.count += 1
            return ast.Call(
                func=ast.Name(id="str", ctx=ast.Load()),
                args=[
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id=IR_VAR_NAME, ctx=ast.Load()),
                            attr="render",
                            ctx=ast.Load(),
                        ),
                        args=[ast.Constant(value="json")],
                        keywords=[],
                    ),
                ],
                keywords=[],
            )
        return node


def _references_module(body: list[ast.stmt], module_name: str) -> bool:
    """True iff ``body`` contains any ``<module_name>.<...>`` attribute
    access (i.e. the import of ``module_name`` is still used).
    Imports themselves don't count as a reference — we're asking
    whether the body uses the module, not whether it imports it.
    """
    for stmt in body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            continue
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == module_name
            ):
                return True
            if (
                isinstance(node, ast.Name)
                and node.id == module_name
            ):
                return True
    return False


def _is_plain_import(stmt: ast.stmt, module_name: str) -> bool:
    """True iff ``stmt`` is ``import <module_name>`` (no ``from``,
    no ``as alias``) — the form the porter drops when the module
    becomes unused after JSON simplification.
    """
    return (
        isinstance(stmt, ast.Import)
        and len(stmt.names) == 1
        and stmt.names[0].name == module_name
        and stmt.names[0].asname is None
    )


def _simplify_json_emit(body: list[ast.stmt]) -> list[ast.stmt]:
    """Collapse the canonical py8dis JSON-emit shape into one
    ``write_text(str(ir.render('json')), ...)`` line.

    Three transformations, applied in order:

    1. Lift the body of any ``try:`` whose body contains an
       ``ir.render('json').data`` reference, dropping the try/except
       wrapper. The defensive wrapper was hiding bugs in the py8dis
       JSON path; the dasmos JSON renderer is reliable.
    2. Drop any ``<X> = ir.render('json').data`` assignment whose
       only downstream use is in a ``json.dumps(<X>)`` call, and
       replace each such call with ``str(ir.render('json'))``.
    3. If the body no longer references ``json`` (after step 2),
       drop ``import json``.
    """
    # 1. Lift try/except wrappers around the JSON emit.
    lifted: list[ast.stmt] = []
    for stmt in body:
        if _try_wraps_json_emit(stmt):
            lifted.extend(stmt.body)
        else:
            lifted.append(stmt)

    # 2. Find the ``<X> = ir.render('json').data`` assignment, drop it,
    # and replace ``json.dumps(<X>)`` with ``str(ir.render('json'))``.
    # The detection is intentionally conservative — only proceed if
    # there's exactly one such assignment and it's used only via
    # json.dumps.
    assign_idx: int | None = None
    var_name: str | None = None
    for i, stmt in enumerate(lifted):
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
            and _is_ir_render_json_data(stmt.value)
        ):
            assign_idx = i
            var_name = stmt.targets[0].id
            break

    if var_name is not None:
        replacer = _JsonDumpsToStrRender(var_name)
        for i, stmt in enumerate(lifted):
            if i == assign_idx:
                continue
            new_stmt = replacer.visit(stmt)
            ast.fix_missing_locations(new_stmt)
            lifted[i] = new_stmt
        if replacer.count > 0 and assign_idx is not None:
            del lifted[assign_idx]

    # 3. Drop ``import json`` if json is no longer referenced anywhere
    # in the body.
    if not _references_module(lifted, "json"):
        lifted = [s for s in lifted if not _is_plain_import(s, "json")]

    return lifted


def _annotate_blank_lines(body: list[ast.stmt]) -> None:
    """Tag top-level ``d.subroutine(...)`` and ``d.label(...)`` calls
    with ``_blank_lines_before`` so the unparser sets them off
    visually.

    - ``d.subroutine(...)`` gets two blank lines before it (a clear
      section break).
    - Standalone ``d.label(...)`` gets one blank line before it.
    - When a ``d.label(addr, ...)`` is immediately followed by a
      ``d.subroutine(addr, ...)`` at the same address, the label
      gets the two blanks and the subroutine gets none — the pair
      reads as a single header.
    """
    for i, stmt in enumerate(body):
        if _is_d_call(stmt, "subroutine"):
            if i > 0 and _is_d_call_at_same_addr(body[i - 1], "label", stmt):
                body[i - 1]._blank_lines_before = 2
                # Subroutine itself gets nothing — the label above
                # already carries the section break.
            else:
                stmt._blank_lines_before = 2
        elif _is_d_call(stmt, "label"):
            # Don't overwrite a 2-blank annotation a future iteration
            # set on this same node (label-followed-by-subroutine
            # pattern lifts blanks UP to the label).
            if not getattr(stmt, "_blank_lines_before", 0):
                stmt._blank_lines_before = 1


def _is_d_call(stmt: ast.stmt, attr: str) -> bool:
    """True iff ``stmt`` is ``d.<attr>(...)`` as a top-level call."""
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Attribute)
        and stmt.value.func.attr == attr
        and isinstance(stmt.value.func.value, ast.Name)
        and stmt.value.func.value.id == "d"
    )


def _is_d_call_at_same_addr(label_stmt, label_attr, ref_stmt) -> bool:
    """True iff ``label_stmt`` is ``d.<label_attr>(addr, ...)`` whose
    ``addr`` matches the first positional arg of ``ref_stmt`` (also
    a ``d.<...>(addr, ...)`` call).
    """
    if not _is_d_call(label_stmt, label_attr):
        return False
    if not (
        isinstance(ref_stmt, ast.Expr)
        and isinstance(ref_stmt.value, ast.Call)
        and ref_stmt.value.args
        and label_stmt.value.args
    ):
        return False
    return ast.dump(label_stmt.value.args[0]) == ast.dump(ref_stmt.value.args[0])


def port(source: str, extra_envs: tuple[str, ...] = ()) -> str:
    """Translate ``source`` (a py8dis driver script) to dasmos form.

    ``extra_envs`` is an optional list of dasmos environment names
    to activate alongside whatever the original driver requested via
    ``acorn.bbc()`` etc. Use this for axes the original driver took
    for granted but dasmos models as a separate composable env —
    most commonly the floppy-disc-controller chip
    (``acorn_fdc_8271`` / ``acorn_fdc_1770``), which py8dis bundled
    into ``bbc()`` but dasmos treats as an opt-in upgrade.
    """
    tree = ast.parse(source)
    _annotate_int_literals(source, tree)
    transformer = Py8disToDasmosTransformer(extra_envs=extra_envs)
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    if isinstance(new_tree, ast.Module):
        _annotate_blank_lines(new_tree.body)
    unparser = _PortedDriverUnparser()
    return unparser.visit(new_tree) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Port a py8dis driver script to dasmos.",
    )
    parser.add_argument("input", help="path to the py8dis driver to port")
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "verify the input is already in ported form; exit non-zero "
            "with a unified diff if it differs from what the porter "
            "would produce"
        ),
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help=(
            "encoding used to read the input driver (default UTF-8). "
            "Driver scripts are Python source and should normally be "
            "UTF-8; override only when porting a driver written in a "
            "different encoding."
        ),
    )
    parser.add_argument(
        "-e", "--env",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "activate an additional dasmos environment in the ported "
            "script. Repeatable. Use for axes the original py8dis "
            "driver took for granted but dasmos models as separate "
            "composable envs — typically the floppy-disc-controller "
            "chip (``acorn_fdc_8271`` / ``acorn_fdc_1770``), which "
            "was always an upgrade rather than standard hardware. "
            "Run ``dasmos list-environments`` to see the catalogue."
        ),
    )
    args = parser.parse_args(argv)

    extra_envs: list[str] = []
    for entry in args.env:
        # Accept comma-separated values per flag, matching the
        # ``dasmos disassemble --env`` shape.
        extra_envs.extend(part for part in entry.split(",") if part)

    source = Path(args.input).read_text(encoding=args.encoding)
    ported = port(source, extra_envs=tuple(extra_envs))

    if args.check:
        if source == ported:
            return 0
        diff = difflib.unified_diff(
            source.splitlines(keepends=True),
            ported.splitlines(keepends=True),
            fromfile=f"{args.input} (on disk)",
            tofile=f"{args.input} (would-be ported)",
        )
        sys.stderr.writelines(diff)
        return 1

    sys.stdout.write(ported)
    return 0


if __name__ == "__main__":
    sys.exit(main())
