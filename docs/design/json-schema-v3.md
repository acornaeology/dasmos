# dasmos JSON schema — v2 → v3

**`meta.schema_version` = `3`** (was `2`). This is the authoritative
contract for the shape change. Any consumer of the dasmos JSON must gate
on `meta.schema_version` and handle both formats — sibling projects
upgrade to the new dasmos on independent schedules, so v2 and v3
documents coexist in the wild.

Version signal, in order of reliability:

- `meta.schema_version == 3` → new format (this document).
- `meta.schema_version == 2` → old format (string `expressions`, no
  `macros`).
- key absent → the pre-1.14 pre-versioning format.

Do **not** sniff for the `macros` key as the primary tell — a v3 document
with no macros omits an empty `macros` array's contents but still carries
`schema_version: 3` and the reshaped `expressions`. The version is the
gate.

---

## Versioning policy

`schema_version` bumps on a **breaking** shape change — one that would
make an existing consumer misread the document (e.g. the v2→v3
`expressions` string→object reshape). **Additive** changes — a new
optional key that older consumers simply ignore — do *not* bump the
version; they are noted here as "additive in v3".

Additive in v3 (safe to ignore if you don't need them):

- `meta.title` / `meta.description` — the optional provenance header
  (`Disassembler.set_file_header`); present only when the driver set one.


## What changed (breaking)

### 1. `expressions[i]`: string → object

A driver-authored operand/data value used to be a **plain string**; it is
now an **object** with a ready-rendered `text` and a structured `tree`.

```jsonc
// v2
"expressions": [null, "copyright - language_entry"]

// v3
"expressions": [null, {
  "text": "copyright - language_entry",
  "tree": { "op": "sub",
            "left":  {"ref": 33028, "name": "copyright"},
            "right": {"ref": 32771, "name": "language_entry"} }
}]
```

- The array is still positional/parallel to `values`, `null` where an
  element has no expression. Only the element type changed
  (string → object).
- `text` is the ready rendering — **use this to restore existing
  behaviour**. It is beebasm-flavoured (`&` hex, `AND`/`EOR`/`DIV`,
  `<(…)`/`>(…)` byte-selects) and is now **precedence-safe**: it
  parenthesises correctly and spells integer division `DIV` (both were
  wrong in an earlier build; fixed).
- `tree` is the structured form (see the node vocabulary below) — use it
  to linkify names or re-render; ignore it if you only need text.

### 2. Code items gained an `expr` object

When an instruction operand came from a driver expression, the code item
now also carries a structured `expr` (the `operand` string field is
unchanged and still includes mode punctuation like `#` / `,X`):

```jsonc
{ "type": "code", "mnemonic": "lda",
  "operand": "#<(target - 1)",              // unchanged; full ready text
  "expr": { "text": "<(target - 1)",         // NEW: the expression only
            "tree": { "op": "lowbyte",
                      "operand": { "op": "sub",
                                   "left":  {"ref": 8196, "name": "target"},
                                   "right": {"int": 1, "radix": "auto"} } } } }
```

`expr` is present only when the operand is a driver expression; absent
otherwise. `operand` remains present as before.

### 3. New top-level `macros` section

```jsonc
"macros": [
  { "name": "pack_lo",
    "params": ["mnem"],
    "emit": "byte",                          // "byte" | "word"
    "body": { "text": "...", "tree": <node> } }  // params appear as {"param": name}
]
```

An **invocation** appears inside an `expressions[].tree` (or an
`expr.tree`) as a `{"macro_call": <name>, "args": [...]}` node; it refers
back to the definition **by `name`**. `macros` is always present in v3
(an empty list when the driver defined none).

---

## `tree` node vocabulary (v3)

Every node is a single-key-ish object; branch on the distinguishing key
(`op`, `ref`, `int`, `sym`, `str`, `raw`, `param`, `macro_call`,
`group`). Fields marked *(guaranteed)* are always present for that node
type.

### Leaves

| Node | Fields | Notes |
|---|---|---|
| integer | `{"int": int, "radix": str}` | `radix` *(guaranteed)* ∈ `auto`, `dec`, `hex`, `bin`, `char` |
| bare name | `{"sym": str}` | a symbolic identifier (constant, etc.), verbatim |
| label reference | `{"ref": int, "name": str\|null}` | `ref` is the runtime address *(guaranteed)*; `name` is the resolved label or `null` if unnamed |
| string literal | `{"str": str}` | |
| raw dialect string | `{"raw": str}` | a legacy string dasmos could not structure; render verbatim |
| macro parameter | `{"param": str}` | appears only inside a macro `body.tree` |

### Composites

| Node | Fields |
|---|---|
| binary op | `{"op": <binop>, "left": <node>, "right": <node>}` |
| unary op | `{"op": <unaryop>, "operand": <node>}` |
| grouping | `{"group": <node>}` — explicit parentheses the author wrote |
| macro call | `{"macro_call": str, "args": [<node>, ...]}` |
| string index | `{"op": "str_index", "string": <node>, "index": <node>}` |
| string slice | `{"op": "str_slice", "string": <node>, "start": <node>, "stop": <node>\|null}` |
| string length | `{"op": "str_len", "string": <node>}` |

- `<binop>` ∈ `add`, `sub`, `mul`, `div`, `mod`, `and`, `or`, `xor`,
  `shl`, `shr` (`div` is integer division).
- `<unaryop>` ∈ `neg`, `pos`, `invert`, `lowbyte`, `highbyte`,
  `bankbyte`.

A robust consumer should treat an unrecognised node kind as opaque and
fall back to the sibling `text` — new node kinds are additive and will
not bump the schema version on their own if they don't reshape existing
nodes.

---

## Minimal vs full consumption

- **Minimal (restores all output):** wherever you previously used the
  `expressions[i]` / operand string, read `expr["text"]` /
  `expressions[i]["text"]` under v3.
- **Full (recommended):** walk `tree` to linkify — a `ref`/`name` node
  links to the label at that address; a `macro_call` links to the
  `macros[]` entry of the same `name` — and render the `macros` section
  as its own block. The flat v2 string could support neither.
