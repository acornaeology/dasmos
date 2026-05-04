# Move subsystem redesign memo

**Status:** thinking-out-loud draft, 2026-05-04. Inputs to a future
decision-record entry in `decisions.md`. Surfaced by the ADFS-1.30
fixture vendoring (the multi-source-same-destination pattern that
beebasm currently rejects with "Symbol already defined").

---

## 1. Why moves matter on Acorn-class machines

A `move` describes a region of bytes that is *stored* at one address
in the binary image (its **ROM / source / binary** address) but is
intended to *execute* at a different address (its **RAM / runtime**
address) after some explicit copy operation at startup or on demand.

Move-aware disassembly is not a niche feature. The pattern recurs in
almost every Acorn ROM:

- **Filesystem ROMs (NFS, ADFS, DFS)** copy small DMA / serial /
  WD1770 stub routines from the high pages of the sideways ROM
  (`&BC..`) into the NMI/IRQ workspace at `&0D00-&0DFF`, where they
  can run with consistent timing and from RAM (the sideways-ROM page
  is not always the active sideways slot during interrupt service).
- **Tube clients** copy the inline-string-handler stubs (`stringhi`
  conventions) from ROM into low workspace before the ROM is
  switched out.
- **MOS itself** copies `ROMSEL` trampolines into low memory.

Two non-obvious complications:

1. **Multiple sources, same destination.** ADFS-1.30 registers three
   moves all targeting `&0D0A`:
   - `nmi_write_move_id     = move(&0D0A, &BCDF, 14)` — host transfer
   - `nmi_tube_write_move_id = move(&0D0A, &BCED, 8)`  — tube write
   - `nmi_tube_read_move_id  = move(&0D0A, &BCF5, 8)`  — tube read

   Different code paths copy *different* source spans into the *same*
   RAM region depending on transfer direction (filesystem op type and
   tube vs. main CPU). At any given moment of execution, only one of
   the three is "live" at `&0D0A`; statically all three are valid
   variants that could be there.

2. **Self-modification crossing move boundaries.** A `bne` whose
   target straddles the end of a moved block has different semantics
   in the source layout (where the *next* instruction is whatever
   followed in ROM) versus the runtime layout (where it falls out of
   the moved region into surrounding RAM). The trace engine needs
   to know which view it's tracing in.

The high-fidelity goal: a renderer should be able to emit, for every
byte covered by one or more moves, *both* its ROM-storage address
*and* its RAM-execution address with appropriate annotations.
Downstream consumers (HTML site generator, a future debugger
integration) should be able to present these views distinctly.

---

## 2. Where dasmos is today

### 2.1 Data model

`MoveDefinition` (in `src/dasmos/core/move.py`) holds the triple
`(dest_runtime_addr, src_binary_addr, length)`.

`MoveManager` owns:

- A `list[MoveDefinition]`, indexed by integer `move_id` (the index
  *is* the id).
- `_move_id_for_binary_addr: dict[int, int]` — reverse map for fast
  trace queries.
- `_active_move_ids: list[int]` — the active-move stack pushed /
  popped via `using(move_id)` (a `@contextmanager`).
- A `BASE_MOVE_ID` sentinel for "no move active".

`add_move(dest, src, length)` returns the `int` move-id. The same
int is what gets passed back as a `move_id=` kwarg on annotation
methods.

### 2.2 Where the bare-int handle leaks

Public API surface that takes `move_id: int`:
- `Disassembler.using_move(move_id)`
- `Disassembler.{label, optional_label, expr_label, byte, word,
  string, comment, banner, subroutine, ...}` — every annotation
  method that can be scoped to a move.

Driver scripts therefore stash the int and re-pass it:

```python
nmi_write_move_id = d.add_move(0x0D0A, 0xBCDF, 14)
with d.using_move(nmi_write_move_id):
    ...
d.comment(0x0D0A, "Read byte from transfer address",
          inline=True, move_id=nmi_write_move_id)
```

The int has no semantic content for the user — it's a positional
index leaked from MoveManager's internal list.

### 2.3 What's actually broken

**Renderer-layer:** the multi-source-same-dest case (ADFS) is what
prompted this memo. Currently `BeebasmRenderer` walks moves
independently and emits the destination label once per move, so a
RAM region with three sources gets three `.nmi_rw_code:` labels and
beebasm refuses to assemble. py8dis emits the destination label once
and inserts `copyblock` / `clear` / `org` directives between source
spans.

**API ergonomics:** the porter has to special-case the
`with foo_move_id:` pattern to wrap the int in `d.using_move(...)`;
driver authors writing native dasmos drivers have to remember to
type `with d.using_move(foo):` rather than the more natural
`with foo:`.

**Naming:** moves have no human-readable identity beyond the
variable name a driver assigns. There's no way to surface "this byte
belongs to the *tube-write variant* of `&0D0A`" in JSON output or
cross-references.

---

## 3. Proposed shape

### 3.1 The handle becomes a `Move` value

Replace the bare `int` move-id with a `Move` dataclass-or-class:

```python
class Move:
    """A region copied from ``src_binary`` to ``dest_runtime`` at
    runtime. Use the result of :meth:`Disassembler.add_move` as a
    context manager to scope annotations under it.
    """
    name: str | None        # optional human label — see 3.2
    dest_runtime_addr: RuntimeAddr
    src_binary_addr: BinaryAddr
    length: int

    def __enter__(self) -> "Move": ...
    def __exit__(self, *exc) -> None: ...
    # __hash__ / __eq__ by identity (Move objects are unique).
```

`add_move(...)` returns the `Move`. Every API site that used to take
`move_id: int` now takes `move: Move | None` (None = base / "no move
active"). Nothing internal needs to be an int — `MoveManager` can
keep a `list[Move]` if integer indexing is convenient, but it's
purely an implementation detail not exposed on the API.

Result:

```python
nmi_write = d.add_move(0x0D0A, 0xBCDF, 14)
with nmi_write:                         # ← natural context-manager usage
    d.byte(0x0D0A, length=14)
d.comment(0x0D0A, "Read byte ...", inline=True, move_id=nmi_write)
```

The porter no longer needs its `with`-rewrite (commit `8b3...`
becomes redundant); driver authors write the natural form.

### 3.2 Moves can carry a name

```python
nmi_write = d.add_move(0x0D0A, 0xBCDF, 14, name="nmi_host_write")
nmi_tube_w = d.add_move(0x0D0A, 0xBCED,  8, name="nmi_tube_write")
nmi_tube_r = d.add_move(0x0D0A, 0xBCF5,  8, name="nmi_tube_read")
```

Names enable:

- **JSON output:** each move emits a `{"name": ..., "dest": ...,
  "src": ..., "length": ...}` record. Downstream HTML can present a
  per-variant view selector ("Show: NMI host write / Tube write /
  Tube read") for an overlaid RAM region.
- **Cross-references:** `[reset_handler](address:0D0A@nmi_tube_read)`
  in comment markdown can point at *one specific variant* of a
  multi-source destination, distinct from the bare
  `[reset_handler](address:0D0A)` which points at the storage view.
- **Debugging:** a renderer's diagnostic for a straddle warning can
  identify the move by name rather than by index.

Names are optional. When omitted, dasmos generates one (e.g.
`move_<index>`) for diagnostic-only use. Two moves with the same
explicit name should raise — it's almost certainly an authoring
mistake.

### 3.3 Multi-source-same-dest renderer fix

The renderer fix is largely independent of the API rename. Sketch:

- **Group moves by destination address.** `MoveManager` exposes
  `moves_at_dest(addr) -> list[Move]` (or the renderer computes the
  grouping at emit time).
- **Emission strategy** for a destination with N sources (N ≥ 1):
  - Emit the destination label exactly once.
  - Emit the *first* source span's bytes inline at the destination
    address.
  - For each additional source, emit a `copyblock` / `clear` / `org`
    block that walks beebasm's pointer back over the dest region and
    then re-emits the next source variant.
  - Per-variant inline annotations (the `comment(addr, ...,
    move_id=)` calls) are sectioned under their respective source's
    block.
- **Trade-off vs. the single-source case.** Today's renderer has a
  fast path for "destination with one source"; that path stays.
  Multi-source paths take the slower "emit-with-copyblock-cycle"
  route. Switch on `len(moves_at_dest(addr)) > 1`.

py8dis already does this — the vendored `py8dis_reference_adfs-1.30
.asm` shows the exact directive sequence we need to mirror.

### 3.4 IR / JSON exposure

Right now an `Item` in the IR carries a `move_id: int | None`. This
becomes `move: Move | None`. The JSON renderer is the natural place
to surface moves directly:

```json
{
  "moves": [
    {"name": "nmi_host_write",
     "dest_runtime": "0x0D0A", "src_binary": "0xBCDF", "length": 14},
    ...
  ],
  "items": [
    {"addr": "0x0D0A", "move": "nmi_host_write", "mnemonic": "lda", ...},
    ...
  ]
}
```

The `move` field on items references the move's `name` — opaque to
JSON consumers but stable across runs. No leaking of internal
indices.

### 3.5 Cross-reference URI scheme

The Markdown-comment URI scheme `[label](address:HEX[@version])`
already accepts an `@version` suffix (used for
multi-version-of-same-ROM cross-references). The natural extension
for move variants:

```
[label](address:0D0A)               — bare; reader picks default view
[label](address:0D0A@nmi_tube_read) — specifically the tube_read variant
```

The asm renderer collapses both to `label`; the JSON renderer keeps
the raw URI; the HTML post-processor disambiguates. Already
mechanical given §3.2.

---

## 4. Open questions

1. **Default move when none is named?** If a driver does
   `d.add_move(d, s, l)` without `name=`, do we fabricate
   `move_<index>` (mostly invisible, used only in diagnostics) or
   refuse and force the user to pick a name? My lean: fabricate. A
   single-source move doesn't need a name; a multi-source set does
   if the user wants per-variant cross-refs.

2. **Should `Move` instances be comparable across `Disassembler`
   instances?** Probably not — a Move is bound to its manager. An
   ergonomic side-effect: passing a Move from one disassembler's
   `add_move` to another's `comment(move_id=...)` should error
   loudly. Identity-based equality + a back-reference to the manager
   handles this.

3. **What about moves that overlap but share neither dest nor src?**
   Today's "last add_move covering a binary address wins" semantic
   for source-byte stealing is a reasonable default; this redesign
   doesn't have to change it. Worth noting in the doc but not
   blocking.

4. **Static vs. dynamic move?** Acorn code occasionally has *only at
   runtime* moves — code that detects the live MOS version and
   chooses where to copy a routine. Today's `add_move` is static
   (declared once, fixed forever). Should the API ever express
   conditional moves? Probably not in the disassembler — that's
   beyond the static-disassembly remit; leave it as a comment-level
   concern. Worth a sentence in the docs.

5. **Beebasm directive choice.** py8dis uses `copyblock` + `clear` +
   `org` for multi-source-same-dest. Is that the only viable
   beebasm-syntax encoding, or could a different sequence yield a
   shorter / more readable output? Worth a quick survey of beebasm
   docs before locking the renderer's emission shape.

---

## 5. Sequencing proposal

Roughly in order of fall-out blast radius:

1. **`Move` type + API rename** (no semantic change to behaviour).
   Add `name` parameter to `add_move`. All existing tests pass with
   `move_id=` kwargs widened to `move: Move`. No int handles
   anywhere in the public API. Drop the porter's `with`-rewrite.
   Probably ~1 day including tests and the porter cleanup.

2. **Multi-source-same-dest renderer support.** The gating piece for
   ADFS round-trip. Renderer learns to group moves by destination
   and emit `copyblock`-cycle blocks. ADFS round-trip xfail flips to
   live. Probably 1-2 days plus parity-ratchet tuning.

3. **JSON exposure of moves.** Each item gains a `move: <name>`
   field; top-level `moves: [...]` array. Bumps the JSON parity
   ratchet down on NFS. Probably half a day.

4. **`@move-name` URI variant** in markdown comments.
   Mostly mechanical given (1)–(3); the markdown_asm regex already
   knows `@version`. Half a day.

(1) and (2) are the load-bearing pieces; (3) and (4) are useful
follow-ons that can land independently in any order.

---

## 6. What's NOT changing

- The trace engine's view of binary addresses (`b2r` / `r2b`
  conversion) is unchanged.
- The `using` context-stack discipline (push / pop on enter / exit)
  is unchanged in behaviour — just exposed through a more natural
  `with move:` syntax.
- The "last add_move wins" source-byte-stealing semantic is
  unchanged unless we deliberately revisit it.
- Existing fixtures (econet-bridge, tube-client, NFS) keep working;
  their drivers don't use multi-source-same-dest patterns.

---

## 7. Recommendation

Move forward with (1) — the API rename to a typed `Move` handle —
as a self-contained, low-risk improvement. It removes the porter
hack, simplifies driver-script ergonomics, and clears the way for
(2) to address the ADFS gating issue with a cleaner data model.

Nothing in this memo precludes shipping (1) before deciding the
final shape of (2). The renderer rework can happen after the API
shape is settled, with its own design pass if it turns out to be
fiddly.
