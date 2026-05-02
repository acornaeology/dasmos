"""Command-line interface for dasmos.

The CLI is built on Click and uses :mod:`asyoulikeit` for report
output, so every introspection command supports
``--as / --report / --header / --detailed``.
"""

import click
from asyoulikeit import (
    Report,
    Reports,
    ScalarContent,
    TableContent,
    report_output,
)

from dasmos import __version__
from dasmos.assembler import (
    ASSEMBLER_NAMESPACE,
    assembler_names,
    describe_assembler,
)
from dasmos.cpu import CPU_NAMESPACE, cpu_names, describe_cpu


@click.group()
@click.version_option(__version__, prog_name="dasmos")
def cli() -> None:
    """A pluggable tracing disassembler."""


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


@cli.command(name="list-assemblers")
@report_output(reports={
    "assemblers": "Registered assembler-syntax plug-ins with one-line descriptions.",
})
def list_assemblers_command() -> Reports:
    """List the available assembler-syntax plug-ins."""
    table = (
        TableContent(title=f"Assemblers registered under {ASSEMBLER_NAMESPACE!r}")
        .add_column("name", "Name")
        .add_column("description", "Description")
    )
    for name in sorted(assembler_names()):
        table.add_row(
            name=name,
            description=describe_assembler(name, single_line=True),
        )
    return Reports(assemblers=Report(data=table))


@cli.command(name="describe-assembler")
@click.argument("name")
@report_output(reports={
    "assembler": "The full description of one registered assembler plug-in.",
})
def describe_assembler_command(name: str) -> Reports:
    """Describe a specific assembler plug-in."""
    return Reports(assembler=Report(data=ScalarContent(
        value=describe_assembler(name),
        title=name,
    )))


if __name__ == "__main__":
    cli()
