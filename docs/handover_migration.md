# Migration handover: py8dis → dasmos

You are picking up a migration of five sibling repos from `py8dis` to
the new `dasmos` disassembler that lives in this directory. This
prompt is self-contained — read it carefully before touching anything.

## Mission

Migrate four BBC-Micro ROM-disassembly projects from the legacy
`py8dis` fork to `dasmos`, then run the static-site generator against
the new outputs and serve the result locally for the user's
inspection. Pause for the user at each project boundary; do not power
through silently.

Final ordered deliverable:

1. `dasmos` branch in each of the five repos, with the migration
   committed locally (do **not** push — the user will).
2. Regenerated `*.asm` + `*.json` per ROM version.
3. Site generator run locally; site served via
   `python -m http.server` from the output directory.

## Read these first (auto-memory)

`MEMORY.md` is auto-loaded into your context. Read these specific
entries before starting:

- `project_overview.md` — what dasmos is and how it relates to py8dis
- `reference_py8dis.md` — local path to the py8dis fork
- `reference_sibling_acorn_projects.md` — the four downstream consumers
- `project_rom_fdc_mapping.md` — which floppy-controller env per ROM
  family (DFS 0/1.x→8271, DFS 2.x/ADFS→1770, (A)NFS→none)
- `project_jsonrenderer_schema.md` — JSON schema is 1:1 with py8dis-fork
- `project_oscall_hooks.md` — OS-call analyzer rules
- `project_locked_design_decisions.md` — architectural choices
- `feedback_check_py8dis_first.md` — read py8dis source / reference
  output BEFORE designing fixes for ported features
- `feedback_critical_porting.md` — every lifted feature gets unit
  tests + a design-smell review

Update memory as you go. In particular, write a new
`project_migration_progress.md` entry when you start so a future
session can pick up if you don't finish.

## State of dasmos (as of this handover)

The dasmos repo at `/Users/rjs/Code/acornaeology/dasmos` is in good
shape. Recent rendering-quality work that matters for migration:

- Decimal for small ints (`lda #0`), hex otherwise.
- Markdown markers (backticks, bold, address-link URIs) flattened in
  banner descriptions and inline comments via `mistletoe`.
- HTML entities expanded (`&rarr;` → `→`).
- `lower_case` setting wired through mnemonic + register-suffix +
  accumulator marker.
- **`FormatHint` in IR** — `core/format_hint.py` defines a renderer-
  agnostic enum (`CHAR`, `DECIMAL`, `HEX`, `BINARY`, `OCTAL`); each
  renderer translates to its own syntax. `d.char_literal(addr)` and
  `d.format_hint(addr, FormatHint.X)` driver-API methods.
- **Conservative auto-detect**: the renderer NO LONGER auto-converts
  printable immediate bytes to `ASC("c")`. Only an explicit
  `d.char_literal(addr)` triggers operand replacement. Auto-detect
  only emits a safe trailing `; 'c'` informational comment.
- JSON renderer surfaces the hint as a `format_hint` field on items.

Round-trip oracle works for every vendored test fixture (NFS-3.34,
NFS-3.65, ADFS-1.30, ANFS-4.18, ANFS-4.21, Tube-6502-Client-1.10,
Econet-Bridge-variant-1) — binary → dasmos driver → beebasm →
identical binary.

**Pending in dasmos** (NOT migration blockers unless user disagrees):
- CPU-state hints in inline comments (`A=&xx,X=&yy`) — task #13
- Cycle counts in inline comments — task #13
- Both are absent from py8dis-fork's reference output for the bridge
  fixture, so probably not surfaced for these ROMs.

## The five repos

All under `/Users/rjs/Code/acornaeology/`:

| Repo | Drivers | FDC env | CPU | Notes |
|---|---|---|---|---|
| `acorn-econet-bridge` | 1 (variant_1) | none | 6502 | 8KB ROM at &E000, own 6502 — no MOS env |
| `acorn-6502-tube-client` | 1 (1.10) | none | 6502 | Tube second-processor client |
| `acorn-adfs` | 1 (1.30) | `acorn_fdc_1770` | 6502 | Sideways ROM at &8000 |
| `acorn-nfs` | 11 versions | none | 6502/65C02 | NFS = pure network FS, no FDC; 4.21 is Master-only (use `acorn_master_hardware`); others Model B (`acorn_model_b_hardware`) |
| `acornaeology.github.io` | site gen | — | — | Reads JSON from sibling repos via `data/sources.json`. Build: `uv run python -m generator.build`. Serve: `python -m http.server` from `output/`. |

NFS version-by-version FDC/machine mapping (no FDC needed for any —
NFS is network-only):

- `nfs-3.34`, `3.34B`, `3.35D`, `3.35K`, `3.40`, `3.60`, `3.62`,
  `3.65` — Model B → `acorn_model_b_hardware`
- `anfs-4.08.53`, `4.18` — Model B → `acorn_model_b_hardware`
- `anfs-4.21_variant_1` — Master only → `acorn_master_hardware`

Each project has a `fantasm.toml` describing the ROM layout. There's
no actual `fantasm` binary — driver scripts honour `FANTASM_ROM` and
`FANTASM_OUTPUT_DIR` env vars but otherwise fall back to convention
paths. Run a driver directly: `python <driver_path>`.

Driver script locations:
- `<repo>/versions/<version_id>/disassemble/disasm_*.py`
- `<repo>/versions/<version_id>/rom/<rom_filename>`

Each driver writes its output to `<repo>/versions/<version_id>/output/`.

## Per-project migration recipe

Do the projects in this exact order: bridge, tube-client, adfs, nfs,
site generator. Bridge is the smallest and most-familiar; nfs is the
biggest. The site generator only makes sense after the source repos
have new outputs.

For each repo:

### Step 1 — Branch

```bash
cd /Users/rjs/Code/acornaeology/<repo>
git status              # MUST be clean
git checkout -b dasmos
```

If the working tree isn't clean, **stop and ask the user**.

### Step 2 — Inspect the driver(s)

Read the driver(s) in `versions/*/disassemble/disasm_*.py`. Note any
unusual idioms — custom hooks, classification overrides, calls to
py8dis internals via `from py8dis.X import Y`. The porter handles the
common cases; unusual ones may need a one-off fix.

Compare against the equivalent fixture in
`/Users/rjs/Code/acornaeology/dasmos/tests/fixtures/<repo>/disasm_*.py`.
The fixture is a vendored snapshot; the upstream driver may have
diverged. If diverged, port the **upstream** version, not the fixture.

### Step 3 — Port via the dasmos porter

```bash
DASMOS=/Users/rjs/Code/acornaeology/dasmos
DRIVER=versions/<version_id>/disassemble/disasm_<name>.py

python $DASMOS/scripts/py8dis2dasmos.py $DRIVER > $DRIVER.new
```

Add the FDC env via `--env`:

```bash
# For ADFS only:
python $DASMOS/scripts/py8dis2dasmos.py --env acorn_fdc_1770 $DRIVER > $DRIVER.new
```

Compare `$DRIVER` and `$DRIVER.new`. The port should:
- Replace `from py8dis.commands import *` with `import dasmos`.
- Replace `init(...)`, `load(...)`, `go(...)` with `Disassembler.create(...)`,
  `d.load(...)`, `str(d.disassemble().render(...))`.
- Translate `acorn.bbc()` → `d.use_environment("acorn_mos")` +
  `d.use_environment("acorn_model_b_hardware")` (FDC opt-in is the
  caller's job).
- Translate every other top-level call (`label()`, `comment()`, etc.)
  to its `d.X(...)` equivalent.

If the port emits Python that doesn't run, the driver uses a py8dis
idiom the porter doesn't handle. **Do not patch the ported file by
hand.** Either extend the porter (`scripts/py8dis2dasmos.py`) with a
test, or stop and ask the user.

Move the ported file into place once it runs:

```bash
mv $DRIVER.new $DRIVER
```

### Step 4 — Swap the dependency

In the repo's `pyproject.toml`, replace:

```toml
dependencies = [
    "py8dis @ git+https://github.com/acornaeology/py8dis.git",
]
```

with a local-path dep on dasmos (until it's published):

```toml
dependencies = [
    "dasmos @ file:///Users/rjs/Code/acornaeology/dasmos",
]
```

Re-resolve the lock if the project uses `uv`:

```bash
uv lock
```

### Step 5 — Generate output

Run each driver. Convention:

```bash
cd <repo>
for V in versions/*/; do
    DRV=$(ls $V/disassemble/disasm_*.py)
    ROM=$(ls $V/rom/*.rom 2>/dev/null | head -1)
    [ -z "$DRV" ] || [ -z "$ROM" ] && continue
    mkdir -p $V/output
    FANTASM_ROM=$ROM FANTASM_OUTPUT_DIR=$V/output python $DRV
done
```

Each run should produce a `<rom-name>.asm` and a `<rom-name>.json`
(plus a `rom.json` describing metadata).

### Step 6 — Verify round-trip

For each generated `.asm`, re-assemble with `beebasm` and check the
output binary matches the original ROM byte-for-byte:

```bash
beebasm -i <output>.asm -o <rebuilt>.bin
md5sum <rom-name>.rom <rebuilt>.bin
# The two MD5s MUST match.
```

If they don't match, **stop and report**. Don't ship a non-round-tripping disassembly.

### Step 7 — Sanity-check the output

Open the generated `.asm` next to the previous `py8dis` output (find
it in the project's git history or vendored in
`dasmos/tests/fixtures/<repo>/py8dis_reference_*.asm`). Compare:

- File size — should be roughly comparable (within 20%).
- Comment-rendering quality — no Markdown leakage (no leftover
  backticks / bold / `[label](address:HEX)`), no HTML entities like
  `&rarr;` showing through.
- Operand text — `lda #0` for small immediates; `ASC(...)` should NOT
  appear unless an explicit `d.char_literal(addr)` was added.
- Byte column / hex dump — should still appear if the driver enables it.

If the output looks materially worse than py8dis-fork (subjective —
ask the user), **stop and report**. Don't power through.

### Step 8 — Commit

Stage and commit the changes on the `dasmos` branch:

```bash
git add -A
git status
git commit -m "Port disassembler driver to dasmos

- Replace py8dis dependency with local dasmos path dep.
- Port disasm driver(s) via scripts/py8dis2dasmos.py.
- <Any per-project notes — FDC env, manual format-hint additions,
  porter limitations encountered.>

Round-trip verified: dasmos → beebasm → identical bytes."
```

Do **not** push. The user will push.

### Step 9 — Pause

Tell the user: which repo finished, where the regenerated output is,
and any concerns you noted. Wait for their go-ahead before starting
the next project. They've explicitly asked for inspection at each
boundary.

## Site generator (after all four source repos)

Repo: `acornaeology.github.io`. Build command: `uv run python -m
generator.build`. The generator reads
`<repo>/versions/<version_id>/output/*.json` from each sibling repo
listed in `data/sources.json`.

Steps:

1. Branch the site repo: `git checkout -b dasmos`.
2. Run the build: `cd /Users/rjs/Code/acornaeology/acornaeology.github.io
   && uv run python -m generator.build`.
3. If it errors on a schema mismatch, the new dasmos JSON has fields
   the generator doesn't recognise. The new `format_hint` field is
   optional and only emitted when set — but the rest of the schema
   should be 1:1. If something else fails, **stop and report**.
4. Serve locally: `cd output && python -m http.server`.
5. Tell the user the URL (typically `http://localhost:8000`) and pause.

## Stop conditions — be loud, do not power through

Stop and report to the user if any of these happens:

- The dasmos porter produces Python that doesn't run.
- A round-trip diff is non-empty (`beebasm` output ≠ original ROM).
- Comment-token parity (when checked against py8dis reference output)
  is dramatically worse than the parity ratchets in the dasmos test
  suite (~10–30 dropped tokens per ROM).
- Output quality looks materially worse than py8dis-fork — Markdown
  leakage, missing comments, missing labels, wrong operand forms.
- Anything requires changing dasmos itself. The user has explicitly
  said: don't change dasmos without their authorization.
- Anything requires changing the site generator beyond a tiny tweak.
- A driver uses a py8dis idiom the porter doesn't handle. Surface it,
  don't paper over it.

## Things the user cares about

- **Conservative defaults**. The user pushed back hard on auto-detect
  rewriting `lda #&55` to `lda #ASC("U")` because `&55` was a memory-
  test bit pattern, not a character. Operand replacement now requires
  an explicit `d.char_literal(addr)`. Don't reintroduce auto-rewriting.
- **Semantic intent in the IR**, not renderer-specific text. If a
  byte should render as binary, use `d.format_hint(addr,
  FormatHint.BINARY)`, not `d.expr(addr, "%01010101")`. The same hint
  works for the JSON renderer too.
- **Comment quality**. The user's whole project is about producing
  high-quality annotated disassemblies. Markdown leakage, dropped
  paragraphs, broken cross-references — these are taken seriously.
- **No emojis** in commit messages or comments. (Global preference.)
- **No git push** without explicit authorisation.
- **Naming**: prefer `_filename` / `_filepath` / `_dirpath` over
  ambiguous `_dir` / `_file` suffixes.

## Manual format-hint additions (optional polish, not required)

Once a port works end-to-end, you might propose adding format hints
to specific drivers where the rendering is misleading. For example,
the bridge ROM's `ram_test` routine has bytes `&AA` and `&55` that
are bit patterns, not random data:

```python
# After d.entry(...) etc., before d.disassemble():
from dasmos.core.format_hint import FormatHint
d.format_hint(0xe016, FormatHint.BINARY)  # lda #&aa in ram_test
d.format_hint(0xe01e, FormatHint.BINARY)  # cmp #&aa
d.format_hint(0xe022, FormatHint.BINARY)  # lda #&55
d.format_hint(0xe02a, FormatHint.BINARY)  # cmp #&55
```

This is not required for the migration — propose it to the user and
let them decide whether to adopt it.

## Reference: minimum-viable dasmos driver shape

After the porter runs, a driver looks roughly like:

```python
import os
from pathlib import Path
import dasmos

_script_dirpath = Path(__file__).resolve().parent
_version_dirpath = _script_dirpath.parent
_rom_filepath = os.environ.get(
    "FANTASM_ROM",
    str(_version_dirpath / "rom" / "<name>.rom"),
)
_output_dirpath = Path(os.environ.get(
    "FANTASM_OUTPUT_DIR",
    str(_version_dirpath / "output"),
))

d = dasmos.Disassembler.create(cpu="6502")
d.use_environment("acorn_mos")
d.use_environment("acorn_model_b_hardware")
# d.use_environment("acorn_fdc_1770")  # for ADFS / similar
d.use_environment("acorn_sideways_rom")  # if the ROM is at &8000

d.load(_rom_filepath, 0x8000)

# ... d.label(), d.comment(), d.subroutine(), d.entry() etc.

ir = d.disassemble()
asm_filepath = _output_dirpath / "<name>.asm"
asm_filepath.write_text(str(ir.render("beebasm")), encoding="utf-8")

json_filepath = _output_dirpath / "<name>.json"
json_filepath.write_text(str(ir.render("json")), encoding="utf-8")
```

The exact shape varies — the porter preserves whatever idioms the
upstream driver uses for path resolution, hooks, etc. The key
mechanical change is `import py8dis.commands as *` becoming `import
dasmos` plus the `d.X()` rewrites.

## Where to find things

- dasmos repo: `/Users/rjs/Code/acornaeology/dasmos`
- py8dis fork (reference): `/Users/rjs/Code/acornaeology/py8dis`
- Porter: `/Users/rjs/Code/acornaeology/dasmos/scripts/py8dis2dasmos.py`
- Round-trip test fixtures (vendored py8dis snapshots):
  `/Users/rjs/Code/acornaeology/dasmos/tests/fixtures/`
- beebasm binary: typically on PATH (`which beebasm`); source at
  `/Users/rjs/Code/beebasm/` if needed
- Auto-memory: `/Users/rjs/.claude/projects/-Users-rjs-Code-acornaeology-dasmos/memory/`

## First action

1. Read `MEMORY.md` and the entries it references.
2. Verify all six repos exist and are clean (`git status`).
3. Verify dasmos's test suite passes:
   `/Users/rjs/Code/acornaeology/dasmos/.venv/bin/python -m pytest -q`
4. Tell the user you're ready, and start with `acorn-econet-bridge`.

Good luck.
