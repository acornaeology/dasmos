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
