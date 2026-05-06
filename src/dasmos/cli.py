"""Command-line interface for dasmos.

The CLI is built on Click and uses :mod:`asyoulikeit` for report
output, so every introspection command supports
``--as / --report / --header / --detailed``.

Commands fall into three groups:

- **Discovery** — ``list-cpus`` / ``describe-cpu`` (and the renderer
  / environment equivalents). Read-only, useful for finding what's
  installed.
- **Disassemble** — the headline one-shot
  ``dasmos disassemble ROM --load-addr ADDR`` that exercises the
  whole pipeline without requiring a driver script.
- **Init** — ``dasmos init DRIVER --rom ROM --load-addr ADDR``
  scaffolds a starter driver file the user can edit and run with
  ``python DRIVER`` to get the same output as ``disassemble``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from asyoulikeit import (
    Report,
    Reports,
    ScalarContent,
    TableContent,
    report_output,
)

from dasmos import __version__
from dasmos.cpu import CPU_NAMESPACE, cpu_names, describe_cpu
from dasmos.environment import (
    ENVIRONMENT_NAMESPACE,
    describe_environment,
    environment_names,
)
from dasmos.renderer import (
    RENDERER_NAMESPACE,
    describe_renderer,
    renderer_names,
)


# ---------------------------------------------------------------------------
# Address parsing — accepts ``0x8000``, ``&8000``, ``$8000``, decimal.
# Hex prefixes match the conventions a 6502/Acorn user already knows
# (``&`` = beebasm; ``$`` = ca65/Apple; ``0x`` = C/Python).
# ---------------------------------------------------------------------------


def _parse_address(s: str) -> int:
    """Parse a CLI address argument.

    Accepts ``0x8000`` / ``&8000`` / ``$8000`` (hex) and bare decimal.
    Raises :class:`ValueError` on anything else so the click error
    path produces a clean usage message.
    """
    text = s.strip()
    if text.startswith(("0x", "0X")):
        try:
            return int(text, 16)
        except ValueError:
            pass
    elif text.startswith(("&", "$")):
        try:
            return int(text[1:], 16)
        except ValueError:
            pass
    else:
        try:
            return int(text)
        except ValueError:
            pass
    raise ValueError(
        f"{s!r} is not a valid address — use 0x1234, &1234, $1234, or decimal"
    )


class _AddressParam(click.ParamType):
    """Click parameter type for an address argument."""

    name = "ADDR"

    def convert(self, value, param, ctx):
        try:
            return _parse_address(value)
        except ValueError as exc:
            self.fail(str(exc), param, ctx)


ADDRESS = _AddressParam()


@click.group()
@click.version_option(__version__, prog_name="dasmos")
def cli() -> None:
    """An extensible tracing disassembler."""


@cli.command(name="list-cpus")
@report_output(reports={
    "cpus": "Registered CPU (processor) plug-ins with one-line descriptions.",
})
def list_cpus_command() -> Reports:
    """List the available CPU plug-ins."""
    table = (
        TableContent(title=f"CPUs registered under {CPU_NAMESPACE!r}")
        .add_column("name", "Name")
        .add_column("description", "Description")
    )
    for name in sorted(cpu_names()):
        table.add_row(
            name=name,
            description=describe_cpu(name, single_line=True),
        )
    return Reports(cpus=Report(data=table))


@cli.command(name="describe-cpu")
@click.argument("name")
@report_output(reports={
    "cpu": "The full description of one registered CPU plug-in.",
})
def describe_cpu_command(name: str) -> Reports:
    """Describe a specific CPU plug-in."""
    return Reports(cpu=Report(data=ScalarContent(
        value=describe_cpu(name),
        title=name,
    )))


@cli.command(name="list-renderers")
@report_output(reports={
    "renderers": "Registered renderer plug-ins with one-line descriptions.",
})
def list_renderers_command() -> Reports:
    """List the available renderer plug-ins."""
    table = (
        TableContent(title=f"Renderers registered under {RENDERER_NAMESPACE!r}")
        .add_column("name", "Name")
        .add_column("description", "Description")
    )
    for name in sorted(renderer_names()):
        table.add_row(
            name=name,
            description=describe_renderer(name, single_line=True),
        )
    return Reports(renderers=Report(data=table))


@cli.command(name="describe-renderer")
@click.argument("name")
@report_output(reports={
    "renderer": "The full description of one registered renderer plug-in.",
})
def describe_renderer_command(name: str) -> Reports:
    """Describe a specific renderer plug-in."""
    return Reports(renderer=Report(data=ScalarContent(
        value=describe_renderer(name),
        title=name,
    )))


@cli.command(name="list-environments")
@report_output(reports={
    "environments": "Registered environment plug-ins with one-line descriptions.",
})
def list_environments_command() -> Reports:
    """List the available environment plug-ins."""
    table = (
        TableContent(title=f"Environments registered under {ENVIRONMENT_NAMESPACE!r}")
        .add_column("name", "Name")
        .add_column("description", "Description")
    )
    for name in sorted(environment_names()):
        table.add_row(
            name=name,
            description=describe_environment(name, single_line=True),
        )
    return Reports(environments=Report(data=table))


@cli.command(name="describe-environment")
@click.argument("name")
@report_output(reports={
    "environment": "The full description of one registered environment plug-in.",
})
def describe_environment_command(name: str) -> Reports:
    """Describe a specific environment plug-in."""
    return Reports(environment=Report(data=ScalarContent(
        value=describe_environment(name),
        title=name,
    )))


# ---------------------------------------------------------------------------
# disassemble — the headline one-shot command
# ---------------------------------------------------------------------------


def _split_envs(env_options: tuple[str, ...]) -> list[str]:
    """Flatten the ``--env`` option list, accepting both repeated
    flags AND comma-separated values per flag (so ``--env a,b`` and
    ``--env a --env b`` are equivalent).
    """
    out: list[str] = []
    for value in env_options:
        for part in value.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


@cli.command(name="disassemble")
@click.argument("rom", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-a", "--load-addr", "load_addr", type=ADDRESS, required=True,
    help="Address where the binary is loaded (hex with 0x/&/$ prefix or decimal).",
)
@click.option(
    "-c", "--cpu", default="6502", show_default=True,
    help="CPU plug-in name (see ``dasmos list-cpus``).",
)
@click.option(
    "-r", "--renderer", default="beebasm", show_default=True,
    help="Renderer plug-in name (see ``dasmos list-renderers``).",
)
@click.option(
    "-e", "--env", "envs", multiple=True,
    help="Environment plug-in to activate. Repeat or comma-separate "
         "to activate several (see ``dasmos list-environments``).",
)
@click.option(
    "--entry", "entries", type=ADDRESS, multiple=True,
    help="Entry-point address to seed the trace from. Repeat for "
         "several. Defaults to the load address.",
)
@click.option(
    "-o", "--out", "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the rendered output to this file. Defaults to stdout.",
)
@click.option(
    "--md5", "md5_hash",
    help="Pin the ROM's MD5 hash. The disassembly fails (without "
         "writing output) if the actual hash differs.",
)
@click.option(
    "--encoding", "encoding", default="utf-8", show_default=True,
    help="Encoding for the rendered output written via --out. "
         "Default UTF-8. Reading the ROM is unaffected — ROMs are "
         "binary.",
)
def disassemble_command(
    rom: Path,
    load_addr: int,
    cpu: str,
    renderer: str,
    envs: tuple[str, ...],
    entries: tuple[int, ...],
    out_path: Path | None,
    md5_hash: str | None,
    encoding: str,
) -> None:
    """Disassemble ROM and write the rendered output.

    Single-shot: builds a Disassembler with the chosen CPU and
    environments, loads ROM at LOAD-ADDR, seeds the trace from each
    --entry (or LOAD-ADDR by default), runs the trace + classification
    + reference-analysis pipeline, and renders via the chosen
    renderer plug-in.

    Use ``dasmos init`` to scaffold a driver script you can edit
    instead of re-running this command with growing flag lists.
    """
    from dasmos.disassembler import Disassembler
    from dasmos.extension import ExtensionError

    env_list = _split_envs(envs)
    try:
        d = Disassembler.create(cpu=cpu, environments=env_list)
    except ExtensionError as exc:
        raise click.ClickException(str(exc)) from exc
    d.load(rom, load_addr, md5sum=md5_hash)
    seed_addrs = entries if entries else (load_addr,)
    for addr in seed_addrs:
        d.entry(addr)
    output = d.disassemble().render(renderer)
    text = str(output)
    if out_path is not None:
        out_path.write_text(text, encoding=encoding)
    else:
        click.echo(text, nl=False)


# ---------------------------------------------------------------------------
# init — scaffold a starter driver script
# ---------------------------------------------------------------------------


_DRIVER_TEMPLATE = '''\
"""Disassembly driver for {rom_name}.

Generated by ``dasmos init``. Edit this file to add labels,
comments, and classifications as you analyse the ROM. Run with::

    python {driver_name}

to produce the rendered listing on stdout. See the dasmos docs for
the full driver-script API and the acornaeology authoring guide
(``acornaeology.github.io/AUTHORING.md``) for the comment-markdown
+ memory-map metadata conventions.
"""

from pathlib import Path

import dasmos

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

ROM_PATH = Path({rom_path_repr})
LOAD_ADDR = {load_addr_hex}{md5_line}

# ---------------------------------------------------------------------
# Build the disassembler
# ---------------------------------------------------------------------

d = dasmos.Disassembler.create(
    cpu={cpu_repr},
    environments={envs_repr},
)
d.load(ROM_PATH, LOAD_ADDR{md5_kwarg})

# Entry points — addresses where the trace seeds. Add more as you
# discover them.
{entries_block}

# ---------------------------------------------------------------------
# Add your analysis below
# ---------------------------------------------------------------------
#
# As you discover labels, subroutines, and data regions, add them
# here. The driver-script API:
#
#   d.label(addr, "name")            — required label at addr
#   d.optional_label(addr, "name")   — optional (emits only if
#                                      referenced)
#   d.subroutine(addr, "name",       — entry point + label + banner
#                title="...",
#                description="...")  — descriptions are full Markdown
#   d.comment(addr, "text")          — comment (also Markdown);
#                                      pass align=Align.INLINE for
#                                      a trailing remark
#   d.byte(addr, length=N)           — classify N bytes as raw data
#   d.string(addr, length=N)         — classify N bytes as a string
#   d.constant(value, "name")        — name a value (e.g. magic
#                                      numbers, OSBYTE call IDs)
#
# Cross-reference links in comments / descriptions:
#
#   "see [foo](address:E000)"        — bare label link
#   "see [foo](address:E000?hex)"    — label + hex literal


# ---------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------

ir = d.disassemble()
print(str(ir.render({renderer_repr})))
'''


def _format_entries_block(entries: tuple[int, ...]) -> str:
    """Render the entry-point block of the generated driver."""
    if not entries:
        return "d.entry(LOAD_ADDR)"
    lines = [f"d.entry({entry:#06x})" for entry in entries]
    return "\n".join(lines)


@cli.command(name="init")
@click.argument(
    "driver_path", type=click.Path(dir_okay=False, path_type=Path),
)
@click.option(
    "--rom", "rom_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the ROM the driver will disassemble.",
)
@click.option(
    "-a", "--load-addr", "load_addr", type=ADDRESS, required=True,
    help="Address where the binary is loaded.",
)
@click.option(
    "-c", "--cpu", default="6502", show_default=True,
    help="CPU plug-in name.",
)
@click.option(
    "-r", "--renderer", default="beebasm", show_default=True,
    help="Renderer plug-in name to use in the generated driver.",
)
@click.option(
    "-e", "--env", "envs", multiple=True,
    help="Environment plug-in to activate (repeatable / comma-separated).",
)
@click.option(
    "--entry", "entries", type=ADDRESS, multiple=True,
    help="Entry-point address (repeatable). Defaults to LOAD_ADDR.",
)
@click.option(
    "--md5", "md5_hash",
    help="Pin the ROM's MD5 hash in the generated driver.",
)
@click.option(
    "--force", is_flag=True,
    help="Overwrite an existing driver file.",
)
@click.option(
    "--encoding", "encoding", default="utf-8", show_default=True,
    help="Encoding used to write the generated driver file. "
         "Default UTF-8.",
)
def init_command(
    driver_path: Path,
    rom_path: Path,
    load_addr: int,
    cpu: str,
    renderer: str,
    envs: tuple[str, ...],
    entries: tuple[int, ...],
    md5_hash: str | None,
    force: bool,
    encoding: str,
) -> None:
    """Scaffold a starter dasmos driver at DRIVER_PATH.

    The generated driver is FUNCTIONAL — running it with
    ``python DRIVER_PATH`` produces the same output as
    ``dasmos disassemble`` with the same flags. Edit the file to
    add labels, comments, classifications, and other analysis.
    """
    if driver_path.exists() and not force:
        raise click.ClickException(
            f"{driver_path} already exists; pass --force to overwrite."
        )
    env_list = _split_envs(envs)
    md5_line = (
        f"\nROM_MD5 = {md5_hash!r}" if md5_hash else ""
    )
    md5_kwarg = ", md5sum=ROM_MD5" if md5_hash else ""
    text = _DRIVER_TEMPLATE.format(
        rom_name=rom_path.name,
        driver_name=driver_path.name,
        # as_posix() so the embedded path is portable: forward slashes
        # work as a Path constructor argument on Windows and don't need
        # backslash-escaping in the str literal.
        rom_path_repr=repr(rom_path.as_posix()),
        load_addr_hex=f"{load_addr:#06x}",
        md5_line=md5_line,
        cpu_repr=repr(cpu),
        envs_repr=repr(env_list),
        md5_kwarg=md5_kwarg,
        entries_block=_format_entries_block(entries),
        renderer_repr=repr(renderer),
    )
    # Always write with an explicit encoding (default UTF-8). On
    # Windows the locale default is cp1252, which would mangle the
    # em-dashes in the template into \x97 bytes — Python would then
    # refuse to run the generated driver since source files must be
    # UTF-8.
    driver_path.write_text(text, encoding=encoding)
    click.echo(f"Wrote driver to {driver_path}", err=True)


if __name__ == "__main__":
    cli()
