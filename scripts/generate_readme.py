"""Generate README.md from a Jinja2 template + captured CLI output.

Usage::

    uv run python scripts/generate_readme.py            # write README.md
    uv run python scripts/generate_readme.py --check    # verify; exit 1 (with diff) on drift

The generator invokes ``dasmos.cli.cli`` via ``click.testing.CliRunner``
to capture deterministic ``--help`` text and a few sample reports, then
renders them into the template at ``scripts/readme_template.md.j2``. The
``--check`` mode is what the pre-commit hook (and CI) run: it
regenerates into memory and exits non-zero with a unified diff if the
on-disk README.md has drifted.

Determinism: every CLI invocation runs inside ``isolated_filesystem``
so unrelated cwd content can't affect output, and the ``COLUMNS=80`` /
``NO_COLOR=1`` env vars pin Click's wrapping width and suppress colour.
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import sys
from pathlib import Path

from click.testing import CliRunner
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT_DIRPATH = Path(__file__).resolve().parent.parent
SCRIPTS_DIRPATH = ROOT_DIRPATH / "scripts"
TEMPLATE_FILENAME = "readme_template.md.j2"
README_FILEPATH = ROOT_DIRPATH / "README.md"

# CSI "m" sequences (colors / bold / italic). Stripped post-hoc as
# belt-and-braces in case a formatter ignores NO_COLOR.
ANSI_M_RE = re.compile(r"\x1b\[[0-9;]*m")

CAPTURE_ENV = {"COLUMNS": "80", "NO_COLOR": "1"}


def _strip_ansi(text: str) -> str:
    return ANSI_M_RE.sub("", text)


def _capture(args: list[str]) -> str:
    """Run ``dasmos`` with the given args inside an isolated filesystem.

    Returns the stripped, ANSI-cleaned stdout.
    """
    from dasmos.cli import cli

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, args, env=CAPTURE_ENV, prog_name="dasmos")
    if result.exit_code != 0:
        raise RuntimeError(
            f"dasmos {' '.join(args)} exited {result.exit_code}\n"
            f"stdout:\n{result.output}\n"
            f"exception: {result.exception}"
        )
    return _strip_ansi(result.output).rstrip()


def render() -> str:
    import dasmos

    env = Environment(
        loader=FileSystemLoader(SCRIPTS_DIRPATH),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    template = env.get_template(TEMPLATE_FILENAME)

    return template.render(
        version=dasmos.__version__,
        help_top=_capture(["--help"]),
        help_list_cpus=_capture(["list-cpus", "--help"]),
        list_cpus=_capture(["list-cpus", "--as", "display"]),
        list_renderers=_capture(["list-renderers", "--as", "display"]),
        list_environments=_capture(["list-environments", "--as", "display"]),
        describe_nmos6502=_capture(["describe-cpu", "nmos6502"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or verify README.md.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify README.md matches the generator's output; exit 1 (with diff) on drift.",
    )
    args = parser.parse_args()

    rendered = render()

    if args.check:
        existing = (
            README_FILEPATH.read_text(encoding="utf-8")
            if README_FILEPATH.exists()
            else ""
        )
        if rendered == existing:
            return 0
        sys.stderr.write("README.md is out of sync with the generator.\n")
        sys.stderr.write("Re-run: uv run python scripts/generate_readme.py\n\n")
        sys.stderr.writelines(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile="README.md (on disk)",
                tofile="README.md (generated)",
            )
        )
        return 1

    README_FILEPATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
