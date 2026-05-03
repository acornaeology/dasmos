# dasmos

A pluggable tracing disassembler for retro CPUs, version `0.1.0`.

<p align="center">
  <a href="https://pypi.org/project/dasmos/"><img src="https://img.shields.io/pypi/v/dasmos.svg" alt="PyPI"></a>
  <a href="https://github.com/acornaeology/dasmos/actions/workflows/release.yml"><img src="https://img.shields.io/github/actions/workflow/status/acornaeology/dasmos/release.yml?label=release" alt="Release"></a>
  <a href="https://github.com/acornaeology/dasmos/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/acornaeology/dasmos/ci.yml?branch=master&label=CI" alt="CI"></a>
  <a href="https://pypi.org/project/dasmos/"><img src="https://img.shields.io/pypi/pyversions/dasmos.svg" alt="Python versions"></a>
</p>

dasmos is a successor to the [py8dis fork][py8dis-fork] under the
[acornaeology][acornaeology] umbrella, rebuilt from the ground up around
Stevedore extension points so CPUs and renderers (assembler-syntax
back-ends) ship as plug-ins. Driver scripts written for the py8dis
fork can be ported with the bundled `scripts/py8dis2dasmos.py` AST
porter — the four sibling Acorn ROM disassembly projects use it
verbatim.

[py8dis-fork]: https://github.com/acornaeology/py8dis
[acornaeology]: https://github.com/acornaeology

## Install

```sh
pip install dasmos
```

`dasmos`'s round-trip / parity tests assemble back to bytes via
[beebasm](https://github.com/stardot/beebasm); `beebasm` on `PATH`
(or via the `BEEBASM` env var) activates them. CI builds beebasm
from source per matrix cell so the round-trip is part of the gate.

## CLI

```console
$ dasmos --help
Usage: dasmos [OPTIONS] COMMAND [ARGS]...

  A pluggable tracing disassembler.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  describe-cpu          Describe a specific CPU plug-in.
  describe-environment  Describe a specific environment plug-in.
  describe-renderer     Describe a specific renderer plug-in.
  list-cpus             List the available CPU plug-ins.
  list-environments     List the available environment plug-ins.
  list-renderers        List the available renderer plug-ins.
```

The CLI commands inherit a uniform `--as display | tsv | json` story
(plus `--report`, `--header`, `--detailed`) from
[asyoulikeit](https://github.com/sixty-north/asyoulikeit), so any
command's structured output drives downstream tooling cleanly.

### Discovering plug-ins

Two namespaces are populated by the bundled extensions; third-party
packages register additional entries the same way.

```console
$ dasmos list-cpus
                      CPUs registered under 'dasmos.cpu'                       
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name      ┃ Description                                                     ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ cmos65c02 │ The CMOS 65C02 — NMOS 6502 superset with 8 new mnemonics, 2 new │
│ nmos6502  │ The classic NMOS 6502.                                          │
└───────────┴─────────────────────────────────────────────────────────────────┘
```

```console
$ dasmos list-renderers
      Renderers registered under      
          'dasmos.renderer'           
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name    ┃ Description              ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ beebasm │ Beebasm-syntax renderer. │
└─────────┴──────────────────────────┘
```

```console
$ dasmos list-environments
    Environments registered under     
         'dasmos.environment'         
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name      ┃ Description            ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ acorn_mos │ Acorn MOS environment. │
└───────────┴────────────────────────┘
```

Environments layer onto a disassembler additively — a driver can
activate any number of them, in either the constructor's
``environments=[…]`` kwarg or via repeated
``d.use_environment(…)`` calls.

`describe-cpu` (and the matching `describe-renderer`) shows the full
docstring of a single plug-in:

```console
$ dasmos describe-cpu nmos6502
The classic NMOS 6502.

16-bit address space; the 56 documented mnemonics across 13
addressing modes; 151 documented opcodes (undocumented opcodes
deliberately omitted).
```

```console
$ dasmos list-cpus --help
Usage: dasmos list-cpus [OPTIONS]

  List the available CPU plug-ins.

  Produces reports:
    cpus  Registered CPU (processor) plug-ins with one-line descriptions.

Options:
  Report Output Options: 
    --no-reports              Suppress all report output. The handler still runs
                              (useful for action commands whose reports are
                              incidental); only rendering is skipped. Mutually
                              exclusive with --report and --all-reports.
    --all-reports             Render every report the handler returns,
                              regardless of the command's default_reports.
                              Useful for commands whose default is a subset (or
                              silent) but where you want the full picture this
                              time. Mutually exclusive with --report and --no-
                              reports.
    --report [cpus]           Report name(s) to display (can be specified
                              multiple times). Shows all if omitted. Valid
                              values: cpus.
    --header / --no-header    Include column headers in output. Overrides each
                              report's default. Format-specific: TSV prefixes
                              first cell with '#', display omits
                              headers/title/caption, JSON ignores this flag.
    --detailed / --essential  Include detailed columns or only essential
                              columns. Auto-detects based on output format if
                              not specified.
    --as [display|json|tsv]   Output format for tabular data. Defaults to
                              'display' for terminals, 'tsv' for pipes.
  --help                      Show this message and exit.
```

## Programmatic API

Every CLI capability is also reachable through the package. The
typical driver-script flow is: pick a CPU plug-in, load a binary,
register entry points / labels / classifications / annotations,
disassemble, then render via a renderer plug-in.

```python
from dasmos import Disassembler, Align

d = Disassembler.create(cpu="nmos6502")
d.load("rom.bin", 0x8000)
d.entry(0x8000, name="start")
d.label(0x8006, "show", description="Display routine")
d.comment(0x8000, "Entry point.")
d.comment(0x8000, "magic", align=Align.INLINE)

ir = d.disassemble()
print(str(ir.render("beebasm")))
```

That produces beebasm-assemblable source. Re-assembling it via the
real `beebasm` binary yields a binary byte-identical to the input
— the load-bearing **round-trip property** dasmos's test suite
exercises against real Acorn ROMs (the 8 KB Econet Bridge and the
2 KB-mapped 6502 Tube Client both round-trip end-to-end with full
py8dis annotation-content parity).

## Migrating a py8dis driver

`scripts/py8dis2dasmos.py` is an AST-based porter that translates a
py8dis driver script into the equivalent dasmos call shape:

```sh
uv run python scripts/py8dis2dasmos.py path/to/disasm_<rom>.py > ported.py
```

It rewrites the wildcard import, swaps `load(addr, file, cpu)` order,
maps `move()` → `d.add_move(...)`, threads `inline=True` →
`align=Align.INLINE`, recognises `subroutine(..., is_entry_point=False)`
as a label-plus-banner pair, expands `hook_subroutine` and the bundled
hooks (`stringhi_hook`, …) through `dasmos.hooks`, and configures the
`render()` call so the output matches py8dis's defaults
(`boundary_label_prefix='pydis_'`, `byte_column=True`).

Every transformation is covered by unit tests, plus a load-bearing
end-to-end test that ports the unmodified Econet Bridge driver and
asserts the resulting beebasm source re-assembles to the original ROM
bytes.

## Testing

`pytest -v` runs the suite. Tests marked `@pytest.mark.beebasm`
auto-skip when `beebasm` isn't on `PATH`; the rest run anywhere
Python and `uv` are installed. CI exercises the full matrix
(ubuntu/macos/windows × earliest+latest declared Python) **against
the installed wheel**, not the source tree, so packaging regressions
(missing entry points, omitted `py.typed` markers, unshipped
sub-packages) fail loud.

## Layout

```
src/dasmos/                 the package
src/dasmos/cli.py           Click entry point + asyoulikeit reports
src/dasmos/disassembler.py  Disassembler (driver-script API)
src/dasmos/core/            Memory / labels / moves / classifications
src/dasmos/cpu.py           Cpu base + Opcode shape
src/dasmos/renderer.py      Renderer base
src/dasmos/ext/cpus/        Bundled CPU plug-ins (nmos6502, cmos65c02)
src/dasmos/ext/renderers/   Bundled renderer plug-ins (beebasm)
src/dasmos/hooks.py         Subroutine hooks (stringhi_hook, …)
scripts/py8dis2dasmos.py    py8dis → dasmos AST porter
scripts/generate_readme.py  This README's generator
docs/design/                Architecture decisions & sweep memos
tests/                      Unit + round-trip + py8dis-parity tests
tests/fixtures/             Vendored ROM + driver + reference output
```

## Related projects

- [py8dis (fork)][py8dis-fork] — the predecessor dasmos is replacing.
  Driver scripts written against this fork port via
  `scripts/py8dis2dasmos.py`.
- The four sibling Acorn ROM disassembly repositories under the
  [acornaeology][acornaeology] umbrella that drive dasmos's
  round-trip / parity validation:
  `acorn-econet-bridge`, `acorn-6502-tube-client`, `acorn-nfs`,
  `acorn-adfs`.
- [beebasm](https://github.com/stardot/beebasm) — the BBC-Micro-style
  assembler used as the round-trip oracle.
- [asyoulikeit](https://github.com/sixty-north/asyoulikeit) — the
  CLI-output framework dasmos's reports are built on.

---

This README is generated from `scripts/readme_template.md.j2` by
`scripts/generate_readme.py`. **Do not edit it directly** — edit the
template (or the generator, or the source files whose output it
captures) and re-run `uv run python scripts/generate_readme.py`. The
pre-commit hook and the `readme-check` CI job both run the
generator's `--check` mode and will refuse stale READMEs.
