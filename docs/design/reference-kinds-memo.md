# Reference kinds and indexed-base addresses

Status: Layer A and Layer B adopted.

## The problem

dasmos records every operand→address use site as a plain *reference*
against the label at the target address, with no record of **how** the
operand reached that address. A direct `STA &00` and an indexed
`STA zp_user_ptr_0,X` are recorded identically: both add a reference to
the label at `&00`.

That conflation is wrong, and it degrades the disassembly in two
concrete ways, both surfaced on the Stardot ADFS thread
(`viewtopic.php?p=487260`):

1. **False memory-map entries.** The memory map lists any out-of-range
   label carrying `description` / `length` / `group` / `access`
   metadata. When a driver author annotates a base like `&00`, it
   appears as a "location the ROM owns" — but ADFS never touches `&00`;
   every access is `zp_user_ptr_0,X` where `X` is a caller control-block
   pointer, never zero. The literal byte `&00` is never read or written.
   The only fix available was to *strip* the metadata by hand
   (acorn-adfs `0042f80`), which is manual, per-address, and lossy — the
   author loses the description/group they wrote.

2. **Misleading reference counts.** Even after stripping the metadata,
   the `; &00 referenced 9 times by …` annotation still fires, because
   it keys off the raw reference list regardless of kind. That count is
   false: `&00` is referenced zero times *as a location*; it is used
   nine times *as an indexing base*.

The signal needed to fix both already exists at classification time —
`opcode.addressing_mode` distinguishes `ZERO_PAGE` from `ZERO_PAGE_X` —
but it is discarded the moment the reference is recorded
(`_compute_references`, `disassembler.py`). Nothing downstream can
recover it.

## Reference-kind taxonomy (Layer A)

A CPU-agnostic `ReferenceKind` (in `dasmos.core`), derived per
addressing mode, classifies *what the operand's named address is to the
access*:

| Kind              | Meaning                                                        | 6502 modes                                   | Names an owned location? |
|-------------------|----------------------------------------------------------------|----------------------------------------------|--------------------------|
| `DIRECT`          | operand is the exact address accessed                          | `ZERO_PAGE`, `ABSOLUTE`, `RELATIVE`, control-flow `ABSOLUTE` | yes |
| `POINTER`         | operand names a location whose 2-byte **contents** are the target; the named location itself is read | `INDIRECT` (`JMP (a)`), `INDIRECT_INDEXED` (`(zp),Y`) | yes |
| `INDEXED`         | operand names a **base**; the location touched is base+register | `ZERO_PAGE_X/Y`, `ABSOLUTE_X/Y`              | no (only if reg==0)      |
| `INDEXED_POINTER` | operand names a **base**; the pointer is at base+X            | `INDEXED_INDIRECT` (`(zp,X)`)                | no (only if X==0)        |

The subtlety that rules out a naive "operand mode ends in `_X`"
heuristic: `(zp),Y` (`INDIRECT_INDEXED`) reads the named zero-page
location directly (to form the pointer) → **owned**, whereas `(zp,X)`
(`INDEXED_INDIRECT`) reads the pointer from `zp+X` → **base-only**. The
two look symmetric but classify oppositely.

The load-bearing predicate is `ReferenceKind.touches_named_address`
(`True` for `DIRECT`/`POINTER`, `False` for the two base-only kinds).
An address is a genuine location iff at least one reference to it
touches the named address.

### Why this is CPU-agnostic, not 6502-shaped

The four members are the orthogonal 2×2 of two yes/no questions any
load/store addressing mode answers, independent of ISA:

|                          | names the address | names a **base** (+ runtime index) |
|--------------------------|-------------------|-------------------------------------|
| location holds the datum | `DIRECT`          | `INDEXED`                           |
| location holds a pointer | `POINTER`         | `INDEXED_POINTER`                   |

Only the *contract* `touches_named_address` (a bool) is consumed
anywhere; the 4-way split is headroom for wording and future features.
The single ISA-specific artefact is the per-mode → kind mapping, which
lives in the CPU plug-in. The model degrades gracefully on very
different CPUs:

- **6809** (cleanest fit): `>addr`→`DIRECT`, `addr,X`→`INDEXED`,
  `[addr]`→`POINTER`, `[addr,X]`→`INDEXED_POINTER`; `,X+` names no
  address → no reference.
- **8086**: `[disp]`→`DIRECT`, `table[bx+si]`→`INDEXED`,
  `jmp [mem]`→`POINTER`. Segment/bank selection is an *orthogonal*
  dimension that belongs in the move/segment model, not here — it does
  not affect touches-vs-base.
- **Z80 / ARM**: register-relative loads (`(IX+d)`, `[r1,#off]`) name
  no memory symbol, so the upstream `OperandKind` yields no reference
  at all; symbolic loads (`(nn)`, PC-relative `ldr r0,label`) →
  `DIRECT`. The feature reduces to "`DIRECT` or nothing", which is
  correct for those ISAs.

Deliberate non-goals of `ReferenceKind`: it records *whether* there is
indexing, not how many index components (base+index+disp on 8086 is
still just `INDEXED`), and it does not model segment/bank selectors.
Both are outside the touches-vs-base contract by design.

### Where the kind is defined

Each CPU plug-in's `AddressingMode` enum carries the kind as a fourth
value-tuple element, e.g. `ZERO_PAGE_X = ("zero_page_x", 1,
ADDRESS_8, ReferenceKind.INDEXED)`. The `AddressingModeMember` protocol
gains `reference_kind: ReferenceKind`. The disassembler reads it via
`getattr(mode, "reference_kind", ReferenceKind.DIRECT)` so a
third-party CPU that predates the field still works (everything defaults
to `DIRECT`, i.e. today's behaviour).

### Threading the kind

- `Reference` (new, `dasmos.core`): a small frozen record wrapping a
  `BinaryLocation` plus a `ReferenceKind`, exposing `.binary_addr` /
  `.move_id` as delegating properties so existing consumers
  (`int(r.binary_addr)` in both renderers) keep working unchanged.
  `BinaryLocation` stays a generic slotted address+move type — the kind
  does not belong on it.
- `Label.references` becomes `list[Reference]`.
- `Label.add_reference(location, kind=ReferenceKind.DIRECT)` wraps and
  appends. The default keeps every existing caller correct.
- `_compute_references` passes
  `getattr(opcode.addressing_mode, "reference_kind", DIRECT)`.

## Rendering and map behaviour (Layer A)

### xref wording — automatic

Both renderers reword the summary from the reference kinds, no API:

- all `DIRECT`/`POINTER` → `; &XX referenced N times by …` (unchanged)
- all base-only → `; &XX used as index base N times by …`
- mixed → `; &XX referenced N times by … (M as index base)`

### memory-map eligibility

- **Automatic:** unchanged status quo — only author-supplied metadata
  puts an address on the map, so a bare indexed base with no metadata
  never appears. No auto-suppression of author metadata (too
  surprising).
- **Explicit directive:** `d.index_base(addr, name, description=…,
  group=…)` keeps the author's description/group but marks the label as
  a *base*, and the xref summary uses the base wording. This is the
  positive-intent counterpart to the "delete the metadata" hack: the
  author states "this is a base" once and keeps the prose.

Both are provided per the design decision ("infer the wording; let the
author pin the map treatment").

### Update — JSON schema v4: base as an orthogonal access flag

The original Layer A design (above) modelled a base as a *mutually
exclusive* `access='indexed_base'` value and split it out of `memory_map`
into a separate `index_bases` array. That collapsed a genuinely
orthogonal fact into an either/or: an address can be read/written by some
sites **and** used as a base by others — the very orthogonality this memo
establishes at the reference level (`touches_named_address`).

JSON schema **v4** (see `json-schema-v4.md`, issue #42) fixes this.
Memory access is an orthogonal set of flags `r` / `w` / `b`, emitted as
an ordered array on each `memory_map` row (`Label.access_flags()`):

- `r` / `w` stay **author-declared** — a `Reference` records only its
  `ReferenceKind` (touches-vs-base), never read-vs-write, so the touch
  mode cannot be derived and remains authored via `access=`.
- `b` is **derived** from the reference kinds (`b` whenever
  `indexed_base_reference_count() > 0`) and also author-assertable
  (`d.index_base`, which now asserts `b` rather than setting a sentinel).

A base is therefore an ordinary `memory_map` row carrying `b`; the
separate `index_bases` array is gone. A `["b"]`-only row is exactly the
old index base — documented in place, the `b` flag (not removal from the
map) saying the literal byte is untouched. The membership rule is
unchanged: only author metadata puts an address on the map, so a bare
derived base with no metadata still never appears.

## Layer B — base±displacement slot naming

jgharston's suggestion on the thread is a naming convention for the
*notional slots around a base*: a workspace at `&0E00` reached via
`,X` with small negative displacements reads better as `ws0E00-3`
(or a slot name) than as three individually-named bytes. acorn-adfs
already does the manual version — `fsm_s0_pre6/pre3/pre1` at
`&0DFA/&0DFD/&0DFF` are literally `&0E00-6/-3/-1`, named one byte at a
time.

### Goal

When an operand's base address falls just inside an author-declared
region window, render it relative to that region's anchor label, e.g.
`fsm_sector0-3,X`, instead of as a bare address or a scatter of
per-byte `_preN` labels.

### API

```python
d.index_region(anchor_addr, name, window=(lo, hi),
               description=…, group=…, access=…, named_slots=False)
```

- `anchor_addr` gets the explicit label `name` (a **required** label,
  so `name = &xxxx` is always emitted and the `anchor±k` arithmetic
  always resolves). Any `description`/`group`/`access` is attached to
  the anchor exactly like `d.label`, so the anchor takes its normal
  place on the memory map.
- `window=(lo, hi)` is an **inclusive offset range** relative to the
  anchor: the region owns runtime addresses `anchor+lo … anchor+hi`.
  `lo` is typically ≤ 0 and `hi` ≥ 0. Offset 0 is the anchor itself,
  not a gap.

### Decisions (resolved 2026-07-03)

1. **Author-declared only.** No inference of a region's extent from
   observed displacements — the window is stated explicitly. Inference
   is a possible later opt-in, out of scope here.

2. **Windows must be disjoint.** Two regions whose `[anchor+lo,
   anchor+hi]` ranges intersect are rejected at `index_region` call
   time with a clear error naming both regions and the overlap. This
   keeps `anchor±k` resolution deterministic (no "which anchor?"
   ambiguity) and matches the author-declared model. Nearest-anchor
   tie-breaking was considered and rejected as surprising.

3. **Precedence — a region is a naming lens for the *gaps*, not an
   override.** The whole point is that a region and explicit
   point-labels coexist over the same address space (the ADFS FSM
   table is exactly this: anchor `fsm_sector0` at `&0E00` **and** the
   explicitly-named, directly-accessed `fsm_s0_start_1` at `&0E03`
   *inside* the window). Operand-name resolution therefore has four
   tiers:

   1. **explicit label / expression at the exact address** — always
      wins (`lda fsm_s0_start_1,X`, never `lda fsm_sector0+3,X`);
   2. **region-relative form** `anchor±k` — for in-window addresses
      with no explicit name;
   3. **auto-generated label**;
   4. **bare hex**.

   This is enforced *by construction*, not by render-time tie-breaking:
   the region only contributes a name where no explicit name exists —
   the same yielding rule `_generate_auto_labels` already applies. So
   an explicit label inside a region range is respected in both
   rendering and name-generation; no warning, it's the normal case.

4. **Orthogonal to `ReferenceKind`.** Region membership decides the
   *spelling* (`anchor±k`); the kind decides *ownership/wording* (owned
   location vs. indexing base). Independent axes — so `lda anchor+3`
   (direct) and `lda anchor-3,X` (indexed base) can both render
   region-relative while Layer A still puts the first on the memory map
   and keeps the second off it.

5. **Runtime-space, move-agnostic.** Regions are declared against
   runtime addresses; membership and the `base − anchor` displacement
   are computed in runtime space (identical rule to the relative-branch
   arithmetic). A workspace at `&0E00` is at `&0E00` regardless of which
   move the accessing code runs under, and an absolute/zp operand
   literal is already a runtime address. If a region ever needs to live
   *inside* a relocated block, register its anchor under
   `using_move(...)` like any other label — no special region-move
   concept.

6. **Slot naming: inline arithmetic by default, named aliases
   opt-in.** The default inline form is arithmetic on the anchor —
   `fsm_sector0-3,X` — which beebasm evaluates to identical operand
   bytes, so it is **round-trip safe and needs no synthesised
   identifier.** With `named_slots=True`, in-window gaps instead get a
   named label using the convention `<name>_m<k>` / `<name>_p<k>`
   (e.g. `fsm_sector0_m3`, `fsm_sector0_p3`) — a distinct identifier
   usable in the equate table and prose cross-references. Per region
   it is one or the other, so there is no second precedence question.

### Implementation approach

Layer B rides on the existing **expression-label** machinery — the same
one drivers already use for `d.expr_label(addr, "dispatch_lo-1")`.
Both renderers resolve an operand address as *explicit name → expression
→ hex* (`BeebasmRenderer._addr_text`,
`JsonRenderer._first_registered_name`), so **no renderer changes are
needed for the inline form**:

- `d.index_region()` validates disjointness, stores the region, and
  registers the anchor label.
- During disassembly, in the same pass that generates auto-labels, each
  *referenced* in-window gap address with no explicit name gets either
  an `anchor±k` **expression** (default) or a `<name>_m/p<k>` **label**
  (`named_slots`) registered against it. The expression/label suppresses
  the auto-label exactly as an author-supplied expression does today,
  and carries the same `ReferenceKind`-tagged references so xref
  summaries stay honest.
- Regions are exposed on the IR (`ir.index_regions`); the JSON renderer
  adds a top-level `regions` array (`anchor`, `name`, `window`,
  `description`) documenting each declared region as a single row.

Layer B depends on Layer A only indirectly — it reuses the reference
walk (`refs_by_addr`) to find which in-window addresses are actually
used — but its rendering is driven by declared windows, not by the
reference kind.
