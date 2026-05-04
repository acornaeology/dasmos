# Migration from py8dis

dasmos is the successor to the `acornaeology/py8dis` fork
(itself derived from upstream `py8dis`). Code is being lifted module
by module with design-smell fixes applied on the way. This document
captures what's done, what's left, the patterns we're applying, and
the deliberate decisions about what NOT to port directly.

## Migration philosophy

Two complementary rules:

- **Test-first for new architecture.** Every part of dasmos that
  departs from py8dis (the `Disassembler` orchestration class, the
  driver-script API, the `IR`, the `Renderer` plug-in surface, the
  `py8dis2dasmos` porter) is built test-first. The tests are the
  spec for the new shape.
- **Critical port for migration.** When lifting an existing py8dis
  module, every feature gets a small focused unit test as it's
  ported, *and* the original is reviewed for design smell before
  lifting. Hacks (the canonical example: `subroutine()` with
  `is_subroutine=False` reusing the banner-comment output for data
  blocks) are split into cleaner shapes before tests are written
  against them. The unit tests pin the cleaned shape.

The point is to avoid lifting py8dis's accumulated cruft into the
new project. The refactor window is *now*, while the surface area is
small enough that redesign is cheap.

## What's been ported

| py8dis module(s) | dasmos module | Status | Tests |
|---|---|---|---|
| `memorymanager.py`, `binaryaddrtype.py` | `dasmos.core.memory` | ✅ | 27 |
| `movemanager.py`, `movedefinition.py` | `dasmos.core.move` | ✅ | 35 |
| `labelmanager.py`, `label.py` (data only) | `dasmos.core.labels` | ✅ | 35 |
| `classification.py` (data classes + ExpressionRegistry) | `dasmos.core.classification` | ✅ | 30 |
| `disassembly.py` (ClassificationStore only — minimum slice) | `dasmos.core.disassembly` | ✅ | 16 |
| `assembler.py` (abstract protocol declared) | `dasmos.assembler` (will be renamed `dasmos.renderer`) | ✅ | 21 |
| `config.py` | `dasmos.core.config` | ✅ | 3 |

**Total so far:** 174 unit tests, all green; full suite runs in
under 0.1 s.

See `docs/design/decisions.md` for the architectural decisions that
shaped the ports.

## What's still ahead

| py8dis module | Plan |
|---|---|
| `mainformatter.py` (282 lines) | Port to `dasmos.core.formatter`, now unblocked by the renderer abstract base. Some functions move to the orchestration layer. |
| `markdown_asm.py` (333 lines) | Port to `dasmos.core.markdown`. mistletoe-based CommonMark + GFM tables → plaintext; handles the custom `[label](address:HEX[?hex])` link form. Used by `TextRenderer` (e.g. Beebasm) to flatten `d.comment()` markdown to asm text; `StructuredRenderer` (e.g. Json) keeps the markdown source intact. Adds `mistletoe` as a runtime dependency. |
| `comment.py` (67 lines) | The `Comment` and `Annotation` classes referenced by the disassembly engine. Port alongside the `AnnotationStore` manager class. |
| `cpu.py` (the abstract CPU base) | Reshape into a thinner `dasmos.core.cpu` base — pure data + small queries, no trace loop. |
| `cpu6502.py` (1,495 lines) | Port to `dasmos.ext.cpus.cpu6502`. Heaviest single port. |
| `cpu65C02.py` (143 lines) | Thin extension on top of `nmos6502`. |
| `beebasm.py` (333 lines) | Port to `dasmos.ext.renderers.beebasm`. |
| `structured.py` (451 lines) | Port to `dasmos.ext.renderers.json`. |
| `commands.py` (1,172 lines) | Drives the new driver-script API design (test-first). Subject to a per-function design-smell sweep before porting. |
| `acorn.py` (3,178 lines) | Decomposed into multiple `Environment` plug-ins (`acorn-bbc-model-b`, `acorn-mos-1_20`, …). Deferred until after the first round-trip — neither of the first two test fixtures uses any of it. |
| `comment.py`, `align.py`, `format.py`, `constant.py`, `subroutine.py`, `structured.py`, `markdown_asm.py`, `stats.py`, `utils.py` | Port piecemeal as the surrounding code that needs them lands. |

The new code (no direct py8dis equivalent) is also still ahead:

- **`Disassembler`** — the orchestration class
- **`IR`** — the read-only model wrapper
- **The driver-script API** — flat methods on `Disassembler`
- **`py8dis2dasmos`** — the AST-based porter

## Patterns applied during port

These came up in every port so far. They're worth knowing because
they tell you *why* a dasmos module looks different from its py8dis
ancestor.

### 1. Module-level state → instance state on a manager class

py8dis kept the loaded memory, the labels dict, the classifications
array, the active-move stack, the configured assembler, the
disassembly settings, and the pending assertions all as
module-level attributes. Two disassemblies in one process clobbered
each other.

dasmos puts each concern on a manager class with instance state:
`MemoryImage`, `MoveManager`, `LabelManager`, `ClassificationStore`,
`Config`, etc. The `Disassembler` orchestrator owns one of each.
Two `Disassembler` instances share nothing; this is regression-tested
in every manager's test file.

### 2. `utils.die()` (sys.exit) → typed exceptions

py8dis raised process-fatal `SystemExit` via `utils.die()` for
many error conditions — fine for a script, hostile for a library.

dasmos defines a small hierarchy under `DasmosError` and raises
specific subclasses (`MemoryAccessError`, `MoveError`, `LabelError`,
`ClassificationError`, …) with informative messages.

### 3. Renderer methods on data classes → moved to the renderer layer

py8dis's `Label`, `Byte`, `Opcode` etc. each had `as_string_list()`
or `gather_inline_label_definitions()` methods that reached into the
configured assembler to format hex / pick comment prefixes / etc.
The model and the renderer were tangled.

dasmos's data classes are pure data. Rendering lives on the
`Renderer` plug-in (or on the orchestration layer, which knows about
both the model and the renderer). The decision to use IR (see
`docs/design/architecture.md`) is the formal seal on this split.

### 4. Cyclic imports → injected dependencies

py8dis had several `from . import movemanager` lines *inside*
function bodies because top-level imports would have been circular.

dasmos surfaces the dependencies in constructors (`RuntimeView` takes
the runtime→binary resolver as a callable; `LabelManager` takes a
`MoveManager`). The orchestrator wires them together at
construction time. No cyclic imports.

### 5. Bare assertions → typed exceptions at the public boundary

py8dis used `assert` heavily for invariant checks at public-method
boundaries. Asserts get stripped under `python -O` and have
unhelpful failure modes.

dasmos uses asserts only for genuine internal invariants (e.g. "this
state must be true if we got here"). Public-method validation
raises the appropriate `DasmosError` subclass with a useful message.

### 6. Class-attribute mutable state → per-instance attrs

`Assembler.pending_assertions = {}` in py8dis was a *class*
attribute, so every Assembler instance shared one dict. Same for
`output_filename`. Both are now per-instance attrs initialised in
`__init__`.

### 7. Real bugs caught in passing

While porting, three real bugs were caught and pinned with regression
tests:

- `is_valid_binary_addr(allow_final_address=True)` referenced an
  undefined `runtime_addr` (typo) — would `NameError`.
- `RuntimeLocation.__eq__` compared `self.binary_addr` (an attribute
  that doesn't exist on `RuntimeLocation`) against `other.binary_addr`.
- `make_runloc()` did `RuntimeAddr(binary_loc)` instead of
  `RuntimeAddr(runtime_loc)` — would `NameError`.

## Deliberate departures from py8dis

These are choices that aren't bug fixes — they're shapes we picked
on purpose because the new architecture is better.

| In py8dis | In dasmos | Why |
|---|---|---|
| Module-level globals | Instance state on manager classes | Multi-disassembly in one process |
| `Cpu` owns the trace loop | `Disassembler` owns the trace loop; `Cpu` is pure data + small queries | Generic trace loop; CPU plug-ins are smaller |
| `Opcode.as_string_list(loc, annotations)` reaches into assembler | Opcode produces structured info; `Renderer` consumes the IR | Multiple renderers per IR; clean split |
| `Label.gather_inline_label_definitions()` does rendering | `LabelManager` is data only; renderer reads it | Same |
| `subroutine(addr, name, is_subroutine=False)` reuses the banner output | `banner(addr, text)` (visual) + `subroutine(addr, name)` (semantic), independent | Two concerns ≠ one function with a flag |
| `String.__init__` captures a callstack via `find_external_callstack()` | No callstack capture | Diagnostic-only, expensive, nobody read it |
| `assert utils.is_string_type(s)` etc. | `s.isidentifier()` and friends | Use the stdlib instead of a hand-rolled type-check zoo |
| `INSIDE_A_CLASSIFICATION = 0` (magic int) | `INSIDE_A_CLASSIFICATION = object()` (sentinel) | `is` comparisons unambiguous |
| Driver-script API: `from commands import *` | Driver-script API: `d = Disassembler.create(...)` then `d.label(...)`, `d.entry(...)`, … | No global state; the porter (py8dis2dasmos) translates between them |

## What's deliberately deferred (or won't be ported)

| py8dis surface | Status | Reason |
|---|---|---|
| `acorn.py` (3,178 lines) | Deferred | First two test fixtures don't use it. When ported, becomes multiple `Environment` plug-ins. |
| `markdown_asm.py` | Deferred | Used by structured/JSON renderer for description rendering; port with the renderer. |
| `commands.py`'s exact API | Reshaped | Driver-script API is test-first. Compat is via the `py8dis2dasmos` porter. |
| Function `init()` in `disassembly.py` | Dropped | Was a no-op (used local assignments without `global`). |
| `String._caller` callstack | Dropped | Diagnostic side-effect, not part of the port. |
| `pending_assertions` / `output_filename` as class attrs | Per-instance now | Bug surface in py8dis. |
| `MoveId` class | Replaced with plain `int` | The push/pop role moved to `MoveManager.using()`. |

## Round-trip as the correctness oracle

The acceptance criterion for the migration is the **binary →
disassembly → reassembled-binary round-trip** against the Econet
Bridge ROM. Beebasm provides the reassembler; CI builds it from
source.

```
econet-bridge-variant_1.rom            (original)
        │
        ▼  scripts/py8dis2dasmos.py + dasmos
beebasm assembly source                (regenerated each test run)
        │
        ▼  beebasm
binary                                 (must equal the original ROM byte-for-byte)
```

This catches anything that text-comparison wouldn't:
addressing-mode picks that differ but assemble identically, label
choice that's semantically equivalent but textually different, etc.
The original py8dis driver script for that ROM is vendored as a
fixture; the `py8dis2dasmos` porter regenerates the dasmos driver
each test run, exercising both the porter and the disassembler in
one shot.

See `docs/design/decisions.md` for the discussion that led here.
