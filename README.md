# dasmos

A pluggable tracing disassembler with CPU and assembler-syntax extension points.

> Status: pre-alpha scaffolding. The README will be generated from runnable
> examples once the first concrete CPU and assembler plug-ins land — see
> `scripts/generate_readme.py` (to be added).

## What it is

dasmos is a tracing disassembler designed from the ground up to be:

- usable as both a command-line tool and an importable Python library;
- thoroughly plug-in based, with separate extension points for **processors**
  (`dasmos.cpu`) and **assembler syntaxes** (`dasmos.assembler`);
- the spiritual successor to the `acornaeology/py8dis` fork — driver scripts
  written for that fork should port to dasmos with minimal change.

## Installation

```bash
uv sync
```

## License

MIT. See `LICENSE`.
