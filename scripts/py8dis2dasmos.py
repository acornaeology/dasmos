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
import sys
from pathlib import Path

# Map py8dis CPU names to dasmos plug-in names.
CPU_NAME_MAP: dict[str, str] = {
    "6502": "nmos6502",
    "65c02": "cmos65c02",  # when the 65C02 plug-in lands
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
})


# Free functions that the porter consumes specially (not rewritten as
# d.method calls — they fold into the constructor or output stage).
SPECIAL_FUNCTIONS: frozenset[str] = frozenset({"init", "load", "go"})


class Py8disToDasmosTransformer(ast.NodeTransformer):
    """Walks a py8dis driver AST and rewrites it as a dasmos driver.

    The transformer collects state about the load/init pair as it
    visits the module body, then emits an ``Disassembler.create()``
    constructor + ``d.load(...)`` call in their place.

    Per-call rewrites (``label(...)`` → ``d.label(...)``) happen via
    :meth:`visit_Call`; the load/init/go specials are handled in
    :meth:`visit_Module`.
    """

    def __init__(self):
        self.assembler_name = "beebasm"

    def visit_Module(self, node: ast.Module) -> ast.Module:
        new_body: list[ast.stmt] = []
        used_align_inline = False

        for stmt in node.body:
            # Drop ``from py8dis.commands import *`` — replaced by
            # the import block we prepend at the end.
            if isinstance(stmt, ast.ImportFrom) and stmt.module == "py8dis.commands":
                continue
            # Drop ``from py8dis.X import ...`` — anything py8dis
            # internal becomes invalid in a dasmos driver.
            if (
                isinstance(stmt, ast.ImportFrom)
                and stmt.module
                and stmt.module.startswith("py8dis")
            ):
                continue

            # Visit children first — rewrites Call nodes inside.
            stmt = self.visit(stmt)

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

            # Detect Align.INLINE usage anywhere in the rewritten
            # statement (so we can decide whether to import Align).
            if not used_align_inline and self._mentions_align_inline(stmt):
                used_align_inline = True

            new_body.append(stmt)

        # Build the import block to prepend.
        imports: list[ast.stmt] = [
            ast.Import(names=[ast.alias(name="dasmos", asname=None)]),
        ]
        if used_align_inline:
            imports.append(
                ast.ImportFrom(
                    module="dasmos",
                    names=[ast.alias(name="Align", asname=None)],
                    level=0,
                )
            )

        return ast.Module(body=imports + new_body, type_ignores=[])

    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Rewrite a free-function call into a ``d.method`` call when
        the function name is one we recognise.
        """
        self.generic_visit(node)  # transform children first

        if isinstance(node.func, ast.Name) and node.func.id in DASMOS_METHODS:
            method_name = node.func.id
            node.func = ast.Attribute(
                value=ast.Name(id="d", ctx=ast.Load()),
                attr=method_name,
                ctx=ast.Load(),
            )
            self._transform_kwargs(method_name, node)
        return node

    # -- specials --------------------------------------------------------

    def _consume_init(self, call: ast.Call) -> None:
        """Extract relevant settings from ``init(...)`` so we can use
        them later (e.g. the assembler name for the render call).
        """
        for kw in call.keywords:
            if kw.arg == "assembler_name" and isinstance(kw.value, ast.Constant):
                self.assembler_name = kw.value.value

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
            dasmos_cpu: ast.expr = ast.Constant(value="nmos6502")
        elif isinstance(cpu_arg, ast.Constant) and isinstance(cpu_arg.value, str):
            mapped = CPU_NAME_MAP.get(cpu_arg.value, cpu_arg.value)
            dasmos_cpu = ast.Constant(value=mapped)
        else:
            dasmos_cpu = cpu_arg

        # d = dasmos.Disassembler.create(cpu=...)
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
                keywords=[ast.keyword(arg="cpu", value=dasmos_cpu)],
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
        """Convert ``go(...)`` into ``ir = d.disassemble(); print(str(ir.render(...)))``.

        ``go()``'s arguments (``print_output``, ``post_trace_steps``,
        ``autostring_min_length``) are not yet honoured by the porter
        — the simple ``disassemble + render + print`` shape covers
        the surveyed drivers.
        """
        # ir = d.disassemble()
        disasm = ast.Assign(
            targets=[ast.Name(id="ir", ctx=ast.Store())],
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="d", ctx=ast.Load()),
                    attr="disassemble",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            ),
        )
        # print(str(ir.render("beebasm")))
        render_print = ast.Expr(
            value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[
                    ast.Call(
                        func=ast.Name(id="str", ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Name(id="ir", ctx=ast.Load()),
                                    attr="render",
                                    ctx=ast.Load(),
                                ),
                                args=[ast.Constant(value=self.assembler_name)],
                                keywords=[],
                            ),
                        ],
                        keywords=[],
                    ),
                ],
                keywords=[],
            ),
        )
        return [disasm, render_print]

    # -- per-method kwarg rewriting --------------------------------------

    def _transform_kwargs(self, method_name: str, node: ast.Call) -> None:
        """Apply per-method kwarg transformations after the
        ``foo(...)`` → ``d.foo(...)`` rewrite.

        Currently:

        - ``comment(..., inline=True)`` →
          ``comment(..., align=Align.INLINE)`` (sweep memo C1).
          ``inline=False`` is silently dropped — it was the default in
          py8dis and corresponds to the dasmos default
          ``align=Align.BEFORE_LABEL``.
        """
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

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _call_name(call: ast.Call) -> str | None:
        """The name of the called function, or ``None`` if it's not a
        plain ``foo(...)`` form.
        """
        if isinstance(call.func, ast.Name):
            return call.func.id
        return None

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


def port(source: str) -> str:
    """Translate ``source`` (a py8dis driver script) to dasmos form."""
    tree = ast.parse(source)
    transformer = Py8disToDasmosTransformer()
    new_tree = transformer.visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree) + "\n"


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
    args = parser.parse_args(argv)

    source = Path(args.input).read_text()
    ported = port(source)

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
