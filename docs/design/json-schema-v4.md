# dasmos JSON schema — v3 → v4

**`meta.schema_version` = `4`** (was `3`). This is the authoritative
contract for the shape change. Any consumer of the dasmos JSON must gate
on `meta.schema_version` and handle both formats — sibling projects
upgrade to the new dasmos on independent schedules, so v3 and v4
documents coexist in the wild.

Version signal, in order of reliability:

- `meta.schema_version == 4` → new format (this document).
- `meta.schema_version == 3` → previous format (scalar `access`,
  separate `index_bases` array; see `json-schema-v3.md`).
- lower / absent → older formats.

The v3 → v4 change is confined to the **memory map**. Everything else —
`expressions`/`expr` objects, the `macros` section, the `tree`
vocabulary — is unchanged from v3.

---

## Versioning policy

`schema_version` bumps on a **breaking** shape change — one that would
make an existing consumer misread the document. Both changes below are
breaking: `access` changed type (string → array) and the `index_bases`
array was removed.

---

## What changed (breaking)

### 1. `memory_map[].access`: scalar string → ordered array

Memory access is now modelled as an **orthogonal set** of flags rather
than one mutually-exclusive value. `access` is an **ordered array**
holding a subset of `["r", "w", "b"]`, in that canonical order.

```jsonc
// v3
{ "addr": 128, "name": "mem_ptr", "access": "rw" }

// v4
{ "addr": 128, "name": "mem_ptr", "access": ["r", "w"] }
```

Semantics:

- **`r`** — at least one site reads the named byte directly.
- **`w`** — at least one site writes it directly.
- **`b`** — at least one site uses it as an indexing **base** (`base,X`
  / `base,Y` and the pointer-indexed modes); the named byte itself is
  base-only for those sites.

The three axes are independent: an address touched by some sites and
indexed-through by others comes out `["r", "b"]` / `["r", "w", "b"]`.

`r` and `w` are **author-declared** (via `access=` on the driver's
`label()` call) — a reference records only *whether* it is a base, never
read-vs-write, so the touch mode stays authored as it always was. `b` is
**derived** from the reference kinds (see `reference-kinds-memo.md`), and
may also be author-asserted (`d.index_base()`, or `access` containing
`"b"`) for a base with no in-image references.

As in v3, `access` is present only when non-empty; a map row with no
declared or derived access omits the key.

### 2. Top-level `index_bases` array removed

v3 emitted indexing bases in a **separate** top-level `index_bases`
array, kept disjoint from `memory_map`. v4 folds them back in: a base is
an ordinary `memory_map` row carrying `b` in its `access`. A `["b"]`-only
row (no `r`/`w`) is exactly a v3 index base — documented in place within
the surrounding workspace/ZP layout, with the `b` flag (not physical
removal from the map) signalling that the literal byte is never touched.

```jsonc
// v3
"memory_map": [ ... ],
"index_bases": [ { "addr": 0, "name": "zp_user_ptr_0",
                   "group": "zero_page", "description": "..." } ]

// v4  (no index_bases key at all)
"memory_map": [ ...,
  { "addr": 0, "name": "zp_user_ptr_0", "group": "zero_page",
    "access": ["b"], "description": "..." } ]
```

Consumers must **remove** their `index_bases` code path and instead read
`b` from each `memory_map` row's `access`. A v3 consumer that only knew
`memory_map` will now also see the former bases there; the `access` array
is how it tells a base apart from an owned location.

Membership rule is unchanged: only author-supplied metadata
(`description` / `length` / `group` / `access`) puts an address on the
map. A bare indexing base with no metadata — `b` derived purely from its
references — still stays off the map, exactly as in v3.

---

## Additive fields since v4 (non-breaking)

Per the versioning policy above, `schema_version` bumps only on a
**breaking** shape change. The fields below are **additive** — they
appear only when the driver uses the corresponding feature, and a
consumer that doesn't know them ignores them and reads the rest of the
document unchanged. They do **not** bump the version.

### `meta.program` — load-and-run metadata

Present only when the driver called `d.program(...)`. An object holding
whichever of `load_addr` / `exec_addr` / `reload_addr` were declared
(each an integer runtime address); an undeclared address is omitted, and
the whole `program` key is absent when none were declared.

```jsonc
"meta": {
  "schema_version": 4,
  "load_addr": 6400,
  "end_addr": 14440,
  "program": { "exec_addr": 14598, "reload_addr": 6400 }
}
```

### `items[].type == "incbin"` — external binary include

A region declared via `d.include_binary(addr, length, path)`. Like the
other data items it carries `addr` (and `binary_addr` when moved) and
the owned `bytes`; its type-specific fields are:

```jsonc
{ "addr": 6934, "type": "incbin",
  "path": "keypad-basic.dat", "length": 7506,
  "bytes": [ 134, 0, 15, ... ] }
```

`path` is the include path as it appears in the assembler directive; the
owned `bytes` are the canonical payload
(`ir.write_included_binaries(dir)` writes them to `path`).

### `meta.images` and `items[].image` — loaded images

`meta.images` lists every file loaded with `d.load()`, in load order. A
disassembly can span several separately-loaded files (a game's DFS
files, traced together), each of which is saved as its own file:

```jsonc
"images": [
  { "name": "Dunjun4", "load_addr": 1024, "end_addr": 3328,
    "exec_addr": 1024 },
  { "name": "Dunjun7", "load_addr": 3328, "end_addr": 4352 }
]
```

`name` is the name declared to `d.load(name=...)`, else the loaded file's
own name. `exec_addr` / `reload_addr` appear only when declared. A
single-image disassembly has a one-entry list.

When more than one image is loaded, each item carries `image`: the index
into `meta.images` of the image holding its stored bytes (by
`binary_addr`). It is omitted when there is only one image.

### `meta.moves`, `move` and `target_move` — telling copies apart

With moves, several pieces of code can share one run address (overlays of
the same RAM), and an item's stored address can equal another item's run
address. These fields say which move each part of the listing belongs to.
A move's **name** is its public identifier: names are unique, and an
unnamed move gets a generated `move_<n>` that never repeats an explicit
name.

`meta.moves` lists every move in declaration order (empty when there are
none):

```jsonc
"moves": [
  { "name": "game_core",    "dest": 2240, "src": 12288, "length": 5952 },
  { "name": "low_keyboard", "dest": 1024, "src": 20912, "length": 1024 },
  { "name": "low_joystick", "dest": 1024, "src": 21936, "length": 1024 }
]
```

- **`move`** — on each item, subroutine and banner whose stored bytes lie
  in a move: that move's name. Omitted for unmoved code. `(addr, move)`
  identifies an item uniquely, so it serves as an anchor.
- **`references[].move`** — the move the referring code is stored in,
  omitted for unmoved code. `references[].move_id` is the same move's
  internal index, kept for existing consumers; prefer `move`.
- **`target_move`** — on an item with a `target`: the move the target
  resolves into, as the trace resolves it — the instruction's own move
  when that covers the target, else the one move that does. Omitted when
  the target runs in place, or when several moves overlay it and none is
  the instruction's own. When a link names no copy, a natural default is
  the unmoved code if any, otherwise the first move in `meta.moves`.
