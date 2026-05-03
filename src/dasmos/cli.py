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


if __name__ == "__main__":
    cli()
