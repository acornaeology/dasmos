# dasmos design documentation

This directory holds the load-bearing design rationale for dasmos —
the *why* behind the code shape. User-facing narrative documentation
lives elsewhere (under `docs/`, built with Sphinx); this directory is
written for contributors and is read alongside the source.

## Where to start

- **[architecture.md](architecture.md)** — the big picture. The
  `Disassembler → IR → Renderer` shape, the manager classes, the
  address-type machinery, where state lives.
- **[extension-points.md](extension-points.md)** — the three
  Stevedore-managed plug-in axes (`cpu`, `renderer`, `environment`),
  what each plug-in is responsible for, and how to write one.
- **[migration-from-py8dis.md](migration-from-py8dis.md)** — context
  on what we ported, what design smells we fixed on the way, and what
  parts of py8dis's surface area are deliberately left behind or
  reshaped.
- **[decisions.md](decisions.md)** — chronological log of architectural
  decisions, with the context and rationale for each. Read this when
  questioning a choice.
- **[commands-sweep-memo.md](commands-sweep-memo.md)** — input for the
  driver-script API design (task #19): the design-smell audit of
  py8dis's `commands.py` cross-referenced against real driver-script
  usage in `acorn-econet-bridge` and `acorn-6502-tube-client`.

## Status

The scaffolding and the foundational manager classes are in place.
The orchestration layer (`Disassembler`), the driver-script API, the
NMOS 6502 plug-in, the Beebasm renderer plug-in, and the
py8dis2dasmos porter are still ahead. See
[migration-from-py8dis.md](migration-from-py8dis.md) for the live
status.
