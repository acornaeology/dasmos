# Architecture

## The shape in one sentence

A user (driver script or CLI) configures a `Disassembler` with a CPU
plug-in, loads one or more binaries, and registers labels / data
classifications / entry points. Calling `d.disassemble()` runs the
trace and returns an `IntermediateRepresentation` (IR). One or more
renderer plug-ins consume the IR and produce outputs (text assembly,
structured JSON, …).

```
                  ┌──────────────┐
   driver ──────► │ Disassembler │ ◄── cpu plug-in (e.g. NMOS 6502)
   script         └───────┬──────┘ ◄── environment plug-ins (zero or more)
                          │
                          │ d.disassemble()
                          ▼
                  ┌──────────────┐
                  │      IR      │  (live read-only wrapper over manager state)
                  └───────┬──────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐
        │ beebasm │ │  json   │ │   ca65  │   ← renderer plug-ins
        │ render  │ │ render  │ │  render │
        └────┬────┘ └────┬────┘ └────┬────┘
             ▼           ▼           ▼
        TextOutput  Structured-  TextOutput
                       Output
```

## Why this shape

py8dis tangled three concerns: a process-global mutable model, the
trace engine that builds it, and the rendering that consumes it. Each
sat on heavy module-level state, so a process could only ever
disassemble one binary against one assembler at a time. The dasmos
shape splits those concerns:

- **Disassembler** owns the per-disassembly state (memory, moves,
  labels, classifications, …) on instance attributes. Two
  disassemblers in one process don't interfere.
- **IR** is the read-only freeze-frame of that state after
  `disassemble()` returns. Renderers see the model but can't mutate
  it.
- **Renderer** plug-ins consume the IR. Several can run on the same
  IR — text assembly *and* structured JSON from one trace.

## The three extension axes

dasmos has three Stevedore-managed plug-in axes, each documented in
detail in [extension-points.md](extension-points.md).

| Axis | Namespace | What it provides |
|---|---|---|
| **CPU** | `dasmos.cpu` | The instruction set: opcode table, addressing modes, per-instruction trace semantics, optional label-naming heuristics. *Pure data + small queries.* |
| **Renderer** | `dasmos.renderer` | A way to consume the IR and produce output. Returns an `Output` subclass (always stringifiable). |
| **Environment** | `dasmos.environment` | An assembly-time context: well-known addresses, memory regions, OS conventions. Multiple instances compose per disassembly with later-overrides-earlier semantics. |

A driver-script use looks like:

```python
import dasmos

d = dasmos.Disassembler.create(cpu="nmos6502")
d.use_environment("acorn-bbc-master")
d.use_environment("acorn-mos-3_20")

d.load("rom.bin", 0x8000, md5sum="…")
d.label(0x8000, "start")
d.entry(0x8000)

ir = d.disassemble()
beebasm_text = str(ir.render("beebasm"))
json_doc    = ir.render("json").data
```

## Manager classes

The Disassembler owns several focused manager classes. Each owns a
slice of model state; together they make up everything the IR exposes.
Splitting the model this way keeps each class small and well-tested
(no god class).

| Class | Module | Responsibility | Status |
|---|---|---|---|
| `MemoryImage` | `dasmos.core.memory` | Loaded binary bytes, per-load range tracking | Ported |
| `MoveManager` | `dasmos.core.move` | Binary↔runtime address relocations, active-move stack | Ported |
| `LabelManager` | `dasmos.core.labels` | Per-runtime-address label registry, name validation | Ported |
| `ClassificationStore` | `dasmos.core.disassembly` | Per-binary-address classification (Byte / Word / Fill / String / Opcode) | Ported |
| `ExpressionRegistry` | `dasmos.core.classification` | Per-address operand expression overrides | Ported |
| `Config` | `dasmos.core.config` | Per-disassembly configuration knobs (formatting, layout) | Ported |
| `AnnotationStore` | (planned) | Comments and annotations indexed by `BinaryLocation` | Pending |
| `ConstantStore` | (planned) | Named constants for emission at the top of the disassembly | Pending |
| `OptionalLabelStore` | (planned) | Labels emitted only if referenced | Pending |
| `ReferenceStore` | (planned) | Backreferences from labels to use sites | Pending |

All of them follow the same patterns: instance state only (no
module-level globals), validation at the public-method boundary,
typed exceptions on misuse. See
[migration-from-py8dis.md](migration-from-py8dis.md) for the
patterns applied during port.

## Address-type machinery

Two distinct address namespaces, distinguished by type at compile
time:

- **`BinaryAddr`** — *where the bytes live in the loaded image*. The
  source of a byte. Always unique per byte.
- **`RuntimeAddr`** — *where the CPU sees the byte at execution
  time*. May not be unique — overlay programs map several binary
  spans to the same runtime address; the active-move stack
  disambiguates.

Both subclass `int`. Type-preserving arithmetic on the same type
(`BinaryAddr + int → BinaryAddr`); subtraction of two same-typed
addresses returns plain `int` (it's a delta, not an address).
Construction of one type from the other raises — caught at the
`BinaryAddr(...)` / `RuntimeAddr(...)` constructor.

`BinaryLocation` and `RuntimeLocation` pair an address with a
`move_id`, distinguishing which relocation a particular reference
belongs to.

Mixing types in raw arithmetic (`BinaryAddr + RuntimeAddr`) is
**permissive** — the constructors of `BinaryLocation` /
`RuntimeLocation` catch leaks downstream. Strict mixing was
considered and rejected; see [decisions.md](decisions.md).

## The IR

`d.disassemble()` returns an `IntermediateRepresentation` (IR). The
IR is a **live read-only wrapper** over the Disassembler's manager
classes — no deep copy. Renderers read from it via the wrapper's
read-only views; mutating the underlying state without going around
the wrapper is the engine's responsibility, not the renderer's.

The IR exposes:

- The classifications (and their order in binary-address space)
- All labels and their references
- All annotations, comments, constants
- The memory image (for hex-dump rendering)
- The move definitions (for `pseudopc` block emission)
- Per-address CPU state (post-trace; populated by the `Cpu`
  plug-in's analysis)

The IR is the contract between the trace engine and the renderers.
Once that contract is stable, new renderer plug-ins can be added
without touching the engine, and conversely the engine can be
re-implemented without touching renderers.

## Output types

Every renderer returns a subclass of `Output`. `Output` is always
convertible to string via `__str__`, but concrete subclasses can
expose richer accessors:

| Output type | Used by | Stringification | Richer access |
|---|---|---|---|
| `TextOutput` | text-syntax renderers (Beebasm, ca65, …) | the text itself | `.lines() -> list[str]` |
| `StructuredOutput` | data-emitting renderers (Json, …) | `json.dumps(data, indent=…)` | `.data` (dict / list / etc.) |

Driver scripts can write any output to a file with the same idiom:

```python
beebasm = ir.render("beebasm")           # TextOutput
json_out = ir.render("json")             # StructuredOutput

Path("out.asm").write_text(str(beebasm))
Path("out.json").write_text(str(json_out))

# Structured access where it exists
data: dict = json_out.data
```

The renderer base is generic over its output type — `Renderer[T]`
where `T` is bounded by `Output` — so type checkers see the right
return type at each render site.

## Construction

```python
# Direct construction with explicit instances:
from dasmos.ext.cpus.cpu6502 import Cpu as Nmos6502Cpu
d = dasmos.Disassembler(cpu=Nmos6502Cpu())

# Higher-level factory with string-based plug-in lookup:
d = dasmos.Disassembler.create(cpu="nmos6502")
```

The factory is the common path for driver scripts; the explicit
constructor is the escape hatch for tests and for callers that want
to subclass or pre-configure.

The constructor does NOT take a renderer — renderers are chosen at
render time, not construction time. This is what lets one trace feed
multiple outputs.

## Trace lifecycle

```python
d = Disassembler.create(cpu="nmos6502")

# Build the model
d.load("rom.bin", 0x8000)
d.label(0x8000, "start")
d.entry(0x8000)
# … all the user-side configuration (data classifications, comments,
# expressions, optional labels, constants, hooks, …)

# One-shot trace + classify-leftovers + post-process
ir = d.disassemble()

# Renderer dispatch
beebasm = ir.render("beebasm")   # TextOutput
json_out = ir.render("json")     # StructuredOutput
```

`disassemble()` is one-shot. Calling it twice raises (or is a no-op
for the second call — to be settled in test-first implementation).
Multiple renderings of the same IR are fine and cheap.

## What's deliberately not here

- **A trace engine on the CPU plug-in.** py8dis's `Cpu` owned the
  trace loop; dasmos's `Cpu` is pure data + small queries. The
  trace loop lives on `Disassembler`.
- **Process-global state.** Every concern that was a module-level
  global in py8dis (the memory array, the labels dict, the
  classifications array, the active-move stack, the configured
  assembler, …) is per-instance state on a manager class.
- **A god class.** The Disassembler delegates to manager classes
  rather than absorbing their state. Adding a new concern means a
  new manager class held by Disassembler, not adding methods to
  Disassembler itself.
- **Renderer-rendered model.** py8dis's `Label`, `Byte`, `Opcode` etc.
  had renderer methods baked in (calling into the configured
  assembler). dasmos's data classes are pure data — rendering moves
  to the renderer plug-in.
