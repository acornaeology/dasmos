# Design decisions

A chronological log of architectural decisions, each with the context
that prompted it and the rationale for the choice. Read this when
questioning a choice — the *why* of any design call lives here.

## 2026-05-02 — initial design pass

### D-001: src/ project layout, mirroring `asyoulikeit`

**Status**: accepted, in place.

**Context**: dasmos is a Sixty-North-house-style Python project; we
have a canonical preferred layout (`asyoulikeit`).

**Decision**: Adopt the asyoulikeit layout: `src/dasmos/`, `tests/`,
`docs/`. `src/dasmos/ext/` holds Stevedore-managed plug-ins. Top-level
`pyproject.toml`. MIT licence. Three GitHub Actions workflows
(`test.yml`, `ci.yml`, `release.yml`) — atomic gating of PyPI +
GitHub Pages publication on `v*` tags.

**Consequences**:

- The `Extension` base class and surrounding plug-in machinery is
  lifted from `asyoulikeit` with light modification (namespace
  prefix becomes `dasmos.<kind>`).
- Tests run against the **installed wheel**, not the source tree, in
  CI — same as asyoulikeit. Catches packaging blunders.
- `bump-my-version` for version management; single source of truth in
  `src/dasmos/__init__.py`.

### D-002: Three extension axes — `cpu`, `renderer`, `environment`

**Status**: accepted; `cpu` and `renderer` (initially called
`assembler`) have base classes; `environment` is designed but
deferred.

**Context**: The user wants to support multiple CPUs (NMOS 6502, CMOS
65C02, MC6809 first; Z80, 80186, 32016, ARM1/2/3/610/710 later) and
multiple output syntaxes (Beebasm first; ca65, acme, JSON later).
Plug-in architecture from day one.

**Decision**: Three Stevedore-managed plug-in axes:

- `dasmos.cpu` — exactly one per Disassembler.
- `dasmos.renderer` — zero or many per IR (chosen at render time,
  not construction time).
- `dasmos.environment` — zero, one, or many per Disassembler.

See `extension-points.md` for full details.

### D-003: `dasmos.assembler` extension point renamed to `dasmos.renderer`

**Status**: accepted; rename pending.

**Context**: Initially we adopted "assembler" as the extension-point
name for output-syntax plug-ins (mirroring py8dis's terminology).
With the IR architecture (D-009) and the addition of structured
(JSON) output as a renderer, "assembler" became misleading — the JSON
output isn't text assembly source, and "an assembler" is what you
*assemble* assembly code with, the inverse of what dasmos does.

**Decision**: Rename `dasmos.assembler` to `dasmos.renderer`.
Concrete plug-ins become `BeebasmRenderer`, `JsonRenderer`,
`Ca65Renderer` (future).

**Consequences**:

- One cleanup commit reworking the Assembler abstract base into a
  Renderer abstract base (mostly a rename, since the abstract
  protocol methods are mostly already correctly named).
- Honest about what plug-ins do; clear that the JSON renderer is
  "just another renderer", not a special case.

### D-004: Manager classes for every model concern (no god class)

**Status**: accepted; manager classes ported one by one.

**Context**: py8dis's `disassembly.py` was ~1,000 lines mixing nine
distinct concerns (classifications, label aux, label-name suggestion,
comments, constants, output emission, optional labels, format hints,
annotations) all on module-level globals.

**Decision**: Each concern gets its own manager class held by the
`Disassembler`. So far: `MemoryImage`, `MoveManager`, `LabelManager`,
`ClassificationStore`, `ExpressionRegistry`, `Config`. Pending:
`AnnotationStore`, `ConstantStore`, `OptionalLabelStore`,
`ReferenceStore`.

**Consequences**: Each class is small enough to test in isolation;
two-instance-independence is a regression test on every manager (it's
the property that justifies the rewrite).

### D-005: Address types preserve type through arithmetic; permissive on mixing

**Status**: accepted; in `dasmos.core.memory`.

**Context**: py8dis's `BinaryAddr` and `RuntimeAddr` only wrapped
`__add__` — subtraction silently dropped the type. Mixing types in
arithmetic was permissive but undefined.

**Decision**: 

- `BinaryAddr + int → BinaryAddr` (and same for `RuntimeAddr`).
- `BinaryAddr - BinaryAddr → int` (a delta, not an address). Same for
  `RuntimeAddr`.
- Mixing types in raw arithmetic stays permissive — the
  `BinaryLocation` / `RuntimeLocation` constructors catch the leaks
  downstream. (Strict mixing was considered and rejected as more
  disruptive than helpful in practice.)

**Consequences**: Arithmetic just works in the common cases; type
errors surface where they matter (constructing a Location with the
wrong-typed address).

### D-006: Cpu plug-in is pure data + small queries; trace loop on orchestrator

**Status**: accepted; pending implementation in
`dasmos.ext.cpus.nmos6502`.

**Context**: py8dis's `Cpu` was a hybrid (opcode registry + trace
engine + state). Made the CPU plug-in unnecessarily large and
prevented adding tracing instrumentation without touching every CPU
plug-in.

**Decision**: The `Cpu` plug-in exposes `opcodes`,
`make_cpu_state()`, `is_subroutine_call`, `is_branch_to`,
`label_maker`. The trace loop lives on the orchestrator
(`Disassembler`) and is generic over the opcode interface.

**Consequences**: The trace loop can be instrumented (debug hooks,
partial traces) without changing CPU plug-ins. CPU plug-ins are
smaller and easier to write.

### D-007: `CpuState` is a per-CPU concrete class

**Status**: accepted; pending implementation.

**Context**: The "optimistic CPU state" feature in py8dis tracks
register values per binary address to enable label-name suggestions
from constants (`LDA #3 ; JSR ...` → suggest `num_lives = 3`).
Generic dict-state vs typed per-CPU state.

**Decision**: Per-CPU concrete `CpuState` classes (`Cpu6502State`,
`Cpu6809State`, …). Strongly typed.

**Consequences**: Mistakes at the CPU plug-in boundary are caught
at construction; dict-state would defer them to use-sites.

### D-008: Disassembler — instance constructor + string factory

**Status**: accepted; pending implementation.

**Decision**:

```python
d = Disassembler(cpu=Nmos6502Cpu())               # explicit instance
d = Disassembler.create(cpu="nmos6502")           # factory; Stevedore lookup
```

The constructor takes only `cpu=`. The renderer is chosen at render
time, not construction time, so it isn't a constructor argument.

The factory is the common path for driver scripts; the explicit
constructor is the escape hatch for tests and pre-configured callers.

### D-009: IR — `d.disassemble() → IR`, then `ir.render(renderer)`

**Status**: accepted; pending implementation.

**Context**: The original proposal was `d.go() → str` with the
assembler at construction time. The user pushed back: that's a god
class, and it doesn't accommodate the JSON renderer's existence
alongside Beebasm.

**Decision**: One-shot `d.disassemble() → IntermediateRepresentation`
(IR). Then `ir.render(renderer)` returns an `Output`. Multiple
renderers can run on the same IR.

**Consequences**:

- Clean split: `Disassembler` builds the model; `IR` exposes it;
  renderers consume it. Each component is small.
- Driver scripts can write text assembly *and* a structured JSON
  document from one trace, which is the actual use-case in the
  sibling projects.
- The IR is a **live read-only wrapper** over the manager state —
  no deep copy. Renderers can't mutate without going around the
  wrapper.
- Method named `disassemble()` (not `go()`, which was the working
  title) — the verb describes what it does.

### D-010: Multiple binaries per Disassembler

**Status**: accepted; in place via `MemoryImage.load()`.

**Context**: py8dis allows `load()` multiple times. Sideways ROM +
OS, multi-ROM programs.

**Decision**: Multiple `d.load()` calls per `Disassembler`. The
`MemoryImage` already supports this via its `load_ranges` list.

### D-011: Driver-script API — flat methods on `Disassembler`

**Status**: accepted; pending implementation.

**Context**: Two options: flat (`d.label(addr, name)`) mirroring
py8dis, or namespaced (`d.labels.add(addr, name)`).

**Decision**: Flat. The driver-script audience is the load-bearing
one and the porter's translations should be as close to identity as
possible.

**Consequences**: The Disassembler's surface area grows with the API,
but each method is a thin wrapper over a manager-class call. Refactor
later if the surface gets unwieldy.

### D-012: Hooks are property-style

**Status**: accepted; pending implementation.

**Context**: py8dis's hooks are registered via setter functions
(`set_user_label_maker_hook(fn)`).

**Decision**: Property-style: `d.label_maker_hook = my_hook`. Tests
can set/clear cleanly. Decorator-shorthand falls out of property
assignment for free.

### D-013: `subroutine()` flag-hack split into `banner()` + `subroutine()`

**Status**: accepted; canonical example of "critical port" design
review.

**Context**: py8dis's `subroutine(addr, name, is_subroutine=False)`
reuses the banner-comment output for data blocks. Two concerns (the
visual banner and the semantic "subroutine entry") are tangled into
one function with a mode switch.

**Decision**: Split into:

- `banner(addr, text)` — purely visual; can be used to mark any
  region.
- `subroutine(addr, name)` — purely semantic; marks an entry point.

Either can be used independently or together.

**Consequences**: This is the canonical example of the
"critical port" rule — every lifted feature gets reviewed for design
smell before tests are written against it. Other py8dis hacks of the
same shape get the same treatment as they're surfaced.

### D-014: Porter — AST-based, single file in/out

**Status**: accepted; pending implementation.

**Decision**: `scripts/py8dis2dasmos.py` parses with `ast`, walks,
rewrites, unparses. Single file in / single file out for now —
expand to project-mirror later if needed. `--check` flag for CI use,
mirroring the README generator.

**Consequences**: AST gives clean rewrites and the option to surface
"this construct can't be ported automatically" with line numbers.

### D-015: Renderer output is `Output` subclass, always stringifiable

**Status**: accepted; pending implementation.

**Decision**: Renderers return an `Output` subclass with `__str__`.
Concrete subclasses:

- `TextOutput(text: str)` for text-syntax renderers (Beebasm, ca65).
  Has `.lines() -> list[str]`.
- `StructuredOutput(data, *, indent=2)` for data-emitting renderers
  (Json). `__str__` calls `json.dumps`. Exposes `.data`.

`Renderer[T]` is generic over `T: Output` so type-checkers see the
right return type.

**Consequences**: Driver scripts can write any output to a file with
the same idiom (`Path("...").write_text(str(output))`); structured
access is preserved where it exists.

### D-016: `environment` is the right name (not `machine`, `target`, `platform`)

**Status**: accepted; `Environment` extension point design captured;
implementation deferred.

**Context**: Previously called `machine`, but a "machine" implies
hardware-only. The plug-in really bundles hardware addresses, OS
conventions, well-known vectors, and rules — *the world the code
runs in*.

**Decision**: Use `environment`. Driver scripts read as
`d.use_environment("acorn-bbc-master"); d.use_environment("acorn-mos-3_20")`.

**Rejected alternatives**:

- `machine` — too hardware-only.
- `target` — toolchain-jargon for the wrong direction (compilation
  *targets*; disassembly is the inverse).
- `platform` — vague; users assume hardware-only.
- `context` — too vague.

### D-017: Composable environment plug-ins, no formal axis discrimination

**Status**: accepted; implementation deferred.

**Context**: Should environment plug-ins be split into formal axes
(hardware vs OS vs language ROM) or should the user compose freely?

**Decision**: One extension point. Multiple plug-ins compose;
later-overrides-earlier on conflicting addresses or labels. No
enforcement of "one hardware + one OS"; the user composes sensibly.

**Consequences**: Less ceremony; more user responsibility. Splitting
into formal axes can come later if it's needed.

### D-018: Defer Acorn / Environment work until after first round-trip

**Status**: accepted (2026-05-02, after the survey of `acorn.py` and
the first two test fixtures).

**Context**: A survey of how `acorn-econet-bridge` and
`acorn-6502-tube-client` use py8dis revealed that **neither** driver
actually imports from `acorn.py` — both define labels, vectors, and
hooks inline. So the Environment plug-in system isn't blocking for
the first round-trip slice.

**Decision**: Defer the `acorn.py` port (and the full `Environment`
plug-in system) until after the first round-trip test (Econet
Bridge) is green. Focus the next phase on the orchestration layer,
the driver-script API, the NMOS 6502 plug-in, the Beebasm renderer,
and the porter.

**Consequences**: Saves ~3,000 lines of translation that wouldn't
be exercised by the first slice. The Environment design is captured
in `extension-points.md` so we don't have to redesign it when we
return to it.

### D-019: Round-trip via the porter is the test regime

**Status**: accepted; implementation pending.

**Context**: The user proposed using the round-trip
`original-py8dis-driver → porter → dasmos-driver → beebasm → binary`
as the CI test, where binary equality with the input ROM is the
acceptance criterion.

**Decision**: Adopt this. The original py8dis driver stays as the
source of truth; the porter regenerates the dasmos driver each test
run. Failures surface in three places: porter exits non-zero, dasmos
disassembler raises, or beebasm output differs from the original
binary.

**Consequences**:

- The porter is exercised on every test run.
- Driver-script API drift surfaces immediately as a porter or
  round-trip failure.
- Beebasm has to be available in CI (built from source on each
  platform).
- The first concrete CI fixture is `econet-bridge-variant_1.rom`
  (8 KB, NMOS 6502).

### D-020: Decompose deferred concerns into separate manager classes (not on `Disassembler` directly)

**Status**: accepted; implementation deferred.

**Context**: Several concerns from py8dis's `disassembly.py` have not
been ported yet (annotations, comments, constants, optional labels).
Should they each be a separate manager class held by `Disassembler`,
or collapse onto `Disassembler` as instance attributes?

**Decision**: Each is a separate manager class, consistent with the
existing `MemoryImage` / `MoveManager` / `LabelManager` /
`ClassificationStore` pattern.

**Consequences**: More classes, each less complicated. The
`Disassembler` is a delegating coordinator, not a god class.
