# Extension points

dasmos is plug-in-based on three independent axes. Each axis is a
Stevedore namespace; each plug-in is a Python entry point under that
namespace. New plug-ins can ship in third-party packages without
modifying dasmos itself — install the package, dasmos sees them.

| Namespace | Purpose | Composition | Status |
|---|---|---|---|
| `dasmos.cpu` | An instruction set + addressing modes + per-instruction trace semantics. | Exactly one per `Disassembler`. | Base ported; first plug-in (`nmos6502`) pending. |
| `dasmos.renderer` | A way to turn the IR into output. | Zero or many per IR; chosen at render time. | Base ported; first plug-ins (`beebasm`, `json`) pending. |
| `dasmos.environment` | An assembly-time context: well-known addresses, memory regions, OS conventions. | Zero, one, or many per `Disassembler`; later-overrides-earlier. | Pending; design captured below. |

## The conventional plug-in layout

All three axes follow the same packaging convention (the
sixty-north-wide `ext/` pattern, mirrored from `asyoulikeit`):

```
src/dasmos/ext/<plural-kind>/<plug-in-name>/
    __init__.py         # `from .<module> import <ConcreteName> as <UniformSymbol>`
    <module>.py         # the concrete class
```

The entry point in `pyproject.toml` always references the leaf
package via the uniform symbol:

```toml
[project.entry-points."dasmos.<kind>"]
<plug-in-name> = "dasmos.ext.<plural-kind>.<plug-in-name>:<UniformSymbol>"
```

| Kind | Plural dir | Uniform symbol |
|---|---|---|
| `cpu` | `cpus` | `Cpu` |
| `renderer` | `renderers` | `Renderer` |
| `environment` | `environments` | `Environment` |

Built-in plug-ins live under `src/dasmos/ext/`. Third-party plug-ins
live in their own packages with the same pattern.

After adding or removing entry points in `pyproject.toml`, **re-run
`uv sync`** — Stevedore reads them from installed package metadata,
so the in-place install must be rebuilt before the new plug-in is
visible.

## CPU (`dasmos.cpu`)

The CPU plug-in describes a processor. It is **pure data + small
queries** — it does not own the trace loop. The trace loop is on
the orchestrator (`Disassembler`).

### Responsibilities

- The opcode table: a mapping from opcode byte to `Opcode` instance.
- Each `Opcode` describes its addressing mode, mnemonic, operand
  length, and the trace semantics (where control flow goes after this
  instruction).
- Per-instruction CPU-state update: how this instruction changes the
  optimistic CPU state used by post-trace label-naming.
- Small queries the orchestrator and the renderer need:
  - `is_subroutine_call(binary_addr) -> bool`
  - `is_branch_to(ref_binary_addr, target_runtime_addr) -> bool`
  - `make_cpu_state() -> CpuState` — factory for per-trace state
  - `label_maker(lmd)` — optional CPU-specific label-naming hook
- Concrete `CpuState` per CPU (not a generic dict) — strongly typed
  state catches mistakes at the plug-in boundary.

### Sketch

```python
class Cpu(Extension):
    @classmethod
    def _kind(cls) -> str: return "cpu"

    @abstractmethod
    def opcodes(self) -> dict[int, Opcode]: ...

    @abstractmethod
    def make_cpu_state(self) -> CpuState: ...

    def is_subroutine_call(self, binary_addr) -> bool: return False
    def is_branch_to(self, ref_binary_addr, target_runtime_addr) -> bool: return False
    def label_maker(self, lmd: LabelMakingData) -> None: pass
```

### First plug-in: `nmos6502`

Port of py8dis's `cpu6502.py` (1,495 lines). Carries:

- Full NMOS 6502 opcode table (0x00–0xFF, undocumented opcodes
  deliberately omitted matching py8dis)
- Addressing modes: implied, accumulator, immediate, zero-page,
  zero-page-X/Y, absolute, absolute-X/Y, indirect, indexed-indirect,
  indirect-indexed, branches
- Per-Opcode subclass: `OpcodeImplied`, `OpcodeUnconditionalBranch`,
  `OpcodeConditionalBranch`, `OpcodeAbs`, `OpcodeZp`,
  `OpcodeImmediate`, `OpcodeReturn`, …

The 65C02 plug-in is a thin extension on top — adds 16 new opcodes
and tweaks cycle counts.

## Renderer (`dasmos.renderer`)

A renderer consumes the IR and produces output. Renderers are
**chosen at render time**, not at `Disassembler` construction time —
this is what lets one trace feed multiple outputs.

### Responsibilities

- Take the IR
- Produce an `Output` subclass
- Subclasses of `Output`:
  - `TextOutput(text: str)` — for text-syntax renderers (Beebasm,
    ca65, acme, …). Has `.lines() -> list[str]`.
  - `StructuredOutput(data, *, indent=2)` — for data-emitting
    renderers (Json, …). `__str__` calls `json.dumps`. Exposes
    `.data` for structured access.

`Output` is the common base: every output is convertible to string
via `__str__`. Subclasses can expose richer accessors.

### Sketch

```python
class Renderer(Extension, Generic[T]):
    """T is the Output subclass this renderer produces."""

    @classmethod
    def _kind(cls) -> str: return "renderer"

    @abstractmethod
    def render(self, ir: IR) -> T: ...
```

### First plug-ins

- **`beebasm`** — port of py8dis's `beebasm.py` (333 lines). Returns
  `TextOutput`. The first-class assembler for the round-trip test
  because Beebasm is freely available, builds easily on every
  platform, and provides byte-identical reassembly — the round-trip
  oracle.
- **`json`** — port of py8dis's `structured.py` (451 lines). Returns
  `StructuredOutput`. Emits a richer document with subroutine
  descriptions, memory-map metadata, etc.

Future text-syntax renderers (`ca65`, `acme`, `xa`) will subclass
the same `Renderer[TextOutput]` base.

## Environment (`dasmos.environment`)

An environment plug-in is the **assembly-time context** — the
addresses, regions, and OS conventions of the world the disassembled
code runs in. Multiple environment plug-ins compose per disassembly
with **later-overrides-earlier** semantics.

### Why the name

"Machine" was the original working title and was rejected. An
environment is more than hardware: it bundles hardware addresses, OS
conventions, well-known vectors, and rules about how to interpret
parts of the address space. The word "environment" captures the
caller's intent better — *the world the code lives in*.

The user reads:

```python
d.use_environment("acorn-bbc-model-b")
d.use_environment("acorn-bbc-mos-1_20")  # later: overrides constants from earlier
```

### Composition rules

- Multiple environments stack. Later registrations override earlier
  ones for any conflicting addresses or labels.
- Each environment is responsible for its own slice (hardware,
  OS, language ROM, …); the user composes them per disassembly.
- No formal axes within "environment" — the user is responsible for
  composing sensibly. (We don't enforce one-hardware-plus-one-OS or
  similar.)

### Sketch (subject to change as the first plug-in lands)

```python
class Environment(Extension):
    @classmethod
    def _kind(cls) -> str: return "environment"

    def name(self) -> str: ...
    def mos_vectors(self) -> list[tuple[int, str]]: ...           # &0200+ vector labels
    def hardware_labels(self) -> list[tuple[int, str]]: ...       # MMIO register labels
    def entry_points(self) -> list[int]: ...                      # seed addresses for trace
    def subroutine_hooks(self) -> dict[int, tuple[str, Callable]]: ...   # OS call hooks
    def os_call_tables(self) -> dict[str, dict]: ...              # for hooks to consult
    def hardware_constants(self) -> dict[str, dict[int, str]]: ...
```

Composition is by address-keyed merge of the label / vector lists;
later-overrides-earlier on conflicts.

### Status

The Environment system is **deferred until after the first round-trip
test passes**. The first two test fixtures (Econet Bridge and Tube
Client) don't actually consume py8dis's `acorn.py` — both drivers
declare every label, vector, and hook inline. So the Environment
plug-in system is for *future* drivers, not the round-trip slice.

When we eventually port `acorn.py`, the right shape is multiple
plug-ins:

- `acorn-bbc-model-b` (hardware: Econet, FRED, SHEILA, JIM, VIA, CRTC)
- `acorn-bbc-master` (hardware: Master-specific ADC, NMI, internal expansion)
- `acorn-bbc-electron` (hardware: 2681 ACIA, no SID)
- `acorn-mos-1_20` (OS labels and vectors for MOS 1.20)
- `acorn-mos-3_20` (OS labels and vectors for MOS 3.20)
- `acorn-tube-6502sp` (6502 second processor — minimal tube I/O at &FEF8+)

The driver opts in by listing the relevant ones.
