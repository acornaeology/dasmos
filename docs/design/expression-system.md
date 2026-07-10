# Design memo: assembler-neutral driver expressions

**Status**: implemented (see decision D-026). Supersedes the string-based
`expr` / `expr_label` / `code_ptr` text and the `translate_expression`
regex adapter introduced in D-024. One deviation from the plan below: the
dialect parser runs at *registration time* inside `Disassembler.expr` /
`expr_label` (`dasmos.core.expr_parse`) rather than in the porter, so
every existing string-based driver migrated with no edits and the porter
needed no changes.

## 1. Motivation

Today a driver authors an operand/data value as a **pre-formatted
string** in beebasm's dialect:

```python
expr_label(0x9A1A, "imm_op_dispatch_lo-&81")
expr(addr, "(syn_opt_dir - cmd_syntax_strings - 1) AND &FF")
code_ptr(...)                       # dasmos generates "<(name-1)" etc.
```

That string is stored verbatim in the IR (`ExpressionRegistry`,
`Label.expressions`) and emitted as-is by the beebasm and JSON
renderers. Because it embeds one assembler's syntax — `&HH` hex,
`HI`/`LO`, `AND`/`EOR` — the 64tass backend can only cope via a regex
rewrite (`Tass64Renderer.translate_expression`), which is a heuristic:
it works only because in the py8dis dialect `&` is *always* hex and the
operator set is small and closed. It cannot handle operator-precedence
differences between assemblers, radix intent, or structural analysis,
and every new backend needs another dialect-translation regex.

**Goal:** represent an expression as an assembler-neutral **tree**, give
drivers an ergonomic Python DSL to build it, and let each renderer emit
correct syntax — including correct parenthesisation for its own operator
precedence — from the one representation. beebasm, 64tass, and JSON all
render the same tree; a fourth backend (ca65, laxasm) just adds a token
table.

## 2. The vocabulary to cover (from the real drivers)

Every distinct shape found across the seven sibling-ROM drivers, plus
the forms tests pin:

| Concept | Examples in the wild |
|---|---|
| Label reference (→ name, late-bound) | `reset`, `default_vector_table` |
| Integer literal, hex | `&81`, `&FFEE`, `&FF` |
| Integer literal, decimal | `1`, `2`, `128`, `255` |
| Subtraction (label − int) | `dispatch_0_lo-1`, `imm_op_dispatch_lo-&81` |
| Difference of two labels | `msg_net_error - error_msg_table` |
| Difference minus literal | `syn_iam - cmd_syntax_strings - 2` |
| Addition | `evntv+1`, `&1230 + 4` |
| Low byte / high byte | `LO(star_run-1)`, `HI(...)`, `<(rx_imm_peek-1)`, `>(...)` |
| Bitwise AND (mask) | `(syn_opt_dir - cmd_syntax_strings - 1) AND &FF` |
| Bitwise XOR | `(255 - inkey_key_ctrl) EOR 128` |
| Bitwise OR | (operator present in the alphabet) |
| Grouping | any of the parenthesised forms above |

Note the two spellings for the same concept — `LO(x)` and `<(x)` both
mean "low byte" — collapse to **one** node; each renderer chooses a
spelling. That collapse is only possible with a tree.

## 3. Representation — the `Expr` AST

A small, immutable (`@dataclass(frozen=True)`) node set in a new module
`src/dasmos/core/expr.py`. Every node is renderer-agnostic; it carries
*intent*, never syntax.

```python
class Radix(Enum):
    AUTO = auto()   # renderer's default heuristic (0-9 decimal, else hex)
    DEC = auto()
    HEX = auto()
    BIN = auto()
    CHAR = auto()   # render as a character literal ('c')

class Expr:  # abstract base
    ...

@dataclass(frozen=True)
class Int(Expr):
    value: int
    radix: Radix = Radix.AUTO

@dataclass(frozen=True)
class Ref(Expr):
    """The label at a runtime address, resolved to its best name at
    render time (local-in-scope → explicit name → hex fallback), exactly
    like operand address resolution. Generalises the current
    `_deferred_expressions` late-binding."""
    runtime_addr: int

@dataclass(frozen=True)
class Sym(Expr):
    """A bare symbolic identifier not tied to a resolvable address — a
    constant name, or a name the porter recovered from a legacy string.
    Rendered verbatim (it is already an identifier in every assembler)."""
    name: str

@dataclass(frozen=True)
class Unary(Expr):
    op: UnaryOp          # NEG, POS, LOWBYTE, HIGHBYTE, BANKBYTE, NOT
    operand: Expr

@dataclass(frozen=True)
class Binary(Expr):
    op: BinOp            # ADD, SUB, MUL, DIV, MOD, AND, OR, XOR, SHL, SHR
    left: Expr
    right: Expr

@dataclass(frozen=True)
class Raw(Expr):
    """Escape hatch / back-compat: a pre-formatted string in the
    beebasm/py8dis dialect. Rendered via the existing
    `translate_expression` adapter; opaque to structural consumers
    (JSON emits `{"raw": "..."}`). Lets today's string-based drivers keep
    working unchanged while new drivers move to structured nodes."""
    text: str
```

`UnaryOp` / `BinOp` are enums of *semantic* operators, deliberately a
superset of what the ROMs use so the system is expressive (shifts,
mul/div, bank byte for 65816 later). Each carries a canonical precedence
and associativity used only as a default; **rendering precedence is
per-renderer** (§5).

## 4. Builder DSL — how drivers construct trees

A new public module `dasmos.expr` re-exports leaf factories plus
byte-select helpers, and every `Expr` overloads Python's arithmetic /
bitwise operators so trees read like arithmetic. Plain `int` operands
auto-wrap to `Int(_, AUTO)`.

```python
from dasmos.expr import ref, sym, lo, hi, hexlit, declit, char

ref(0x9A9B) - 1                       # Binary(SUB, Ref(0x9A9B), Int(1))
ref(a) - ref(b)                       # label difference
lo(ref(0x8130) - 1)                   # Unary(LOWBYTE, Binary(SUB, Ref, Int(1)))
(ref(syn_opt) - ref(cmd) - 1) & 0xFF  # mask
(255 - ref(inkey_key_ctrl)) ^ 128     # INKEY form, backend-neutral
hi(sym("star_run"))                   # high byte of a bare symbol
```

Operator overloads provided on `Expr`: `__add__/__radd__`,
`__sub__/__rsub__`, `__mul__`, `__and__/__rand__`, `__or__`, `__xor__`,
`__lshift__`, `__rshift__`, `__neg__`, `__invert__`. `__rsub__` etc.
handle `255 - ref(x)` (int on the left).

Radix intent is preserved without ceremony: `AUTO` defers to the
renderer's existing small-int heuristic (`_format_immediate_byte`:
`0-9` decimal, else hex), which already reproduces `-1` (decimal) and
`-&81` (hex) from the current drivers — so most code needs no radix
annotation. `hexlit(n)` / `declit(n)` / `char(n)` force a radix when it
matters. `char(0x0d)` unifies with `FormatHint.CHAR`.

Driver-facing API changes (all backward compatible — the second
argument becomes `Expr | str`, and a `str` is wrapped as `Raw`):

```python
def expr(self, runtime_addr, value: "Expr | str", *, move=None): ...
def expr_label(self, runtime_addr, value: "Expr | str", **kwargs): ...
# code_ptr / rts_code_ptr build trees internally instead of format strings:
#   adjacent word  → Ref(target) [- Int(offset)]
#   split lo/hi    → lo(Ref(target) - offset) / hi(Ref(target) - offset)
```

`code_ptr`'s late name resolution falls straight out of `Ref` — the
`_deferred_expressions` list and `_resolve_deferred_expressions()` pass
are **deleted**; a `Ref` resolves whenever it is rendered, which is
already after all labels exist.

## 5. Rendering — one tree, correct syntax per backend

Add to `AssemblerRenderer` a single walker:

```python
def render_expression(self, e: Expr, ir, *, active_move=None) -> str
```

It dispatches on node type and pulls every syntactic choice from
overridable seams — most of which already exist on `TextRenderer`:

| Node | Renderer seam | beebasm | 64tass |
|---|---|---|---|
| `Int(_, HEX)` | `hex2`/`hex4` | `&81` | `$81` |
| `Int(_, AUTO)` | `_format_immediate_byte` | `-1`, `&81` | `-1`, `$81` |
| `Int(_, CHAR)` | `char_literal` | `'A'` | `'A'` |
| `Ref(addr)` | `_addr_text` (reused) | `dispatch_lo` | `dispatch_lo` |
| `Sym(name)` | verbatim | `star_run` | `star_run` |
| `Binary(AND,…)` | `binary_operator_token` (exists) | `AND` | `&` |
| `Binary(XOR,…)` | `binary_operator_token` | `EOR` | `^` |
| `Unary(LOWBYTE,…)` | `render_lowbyte` | `<(x)` / `LO(x)` | `<x` |
| `Unary(HIGHBYTE,…)` | `render_highbyte` | `>(x)` / `HI(x)` | `>x` |

The existing `translate_binary_operator_names()` /
`translate_unary_operator_names()` policy hooks on `TextRenderer` are
exactly this token table — the design builds on them rather than adding
new machinery. `Raw` nodes route through the existing
`translate_expression` so the back-compat path is unchanged.

### 5.1 Precedence-aware parenthesisation (the correctness core)

Assemblers disagree on operator precedence. beebasm (from
`beebasm/src/expression.cpp`): byte-select/`HI`/`LO` 10, unary `± ` 8,
`^`(power) 7, `* / % << >>` 6, `+ -` 5, comparisons 4, `AND` 3,
`OR`/`EOR` 2. 64tass is C-like (`&` above `^` above `|`, all below
`+ -`). A single fixed parenthesisation cannot be correct for both.

So the walker parenthesises **per target**: each renderer supplies
`operator_precedence(op) -> int`, and a child sub-expression is wrapped
in parens iff its precedence is lower than the parent's (or equal, on
the associativity-sensitive side). This is the standard minimal-paren
pretty-printer, parameterised by the backend's own table. It guarantees
the emitted text evaluates to the tree's meaning **in that assembler's
grammar** — which the regex adapter cannot promise. A renderer may
return a "fully parenthesise everything" table as a trivially-correct
starting point and tighten later.

Worked example — `(255 - ref(inkey)) ^ 128` (XOR) with a masked
low-byte inside:
- beebasm: `(255 - inkey) EOR 128`  (EOR prec 2 < `-` prec 5 → the
  subtraction needs no parens under EOR, but the author's grouping is
  preserved where semantically required).
- 64tass: `(255 - inkey) ^ 128`.

Both come from the identical tree; each got its own tokens and its own
paren decisions.

## 6. JSON rendering — structured, not a string

`JsonRenderer` stops emitting the raw operand string and emits the
**tree** (dasmos's own schema — consistent with the JsonRenderer-owns-
its-schema principle), plus a human-readable canonical `text` field:

```json
{
  "expr": {
    "op": "lowbyte",
    "of": {"op": "sub",
           "l": {"ref": 39067, "name": "dispatch_0_lo"},
           "r": {"int": 1, "radix": "auto"}}
  },
  "text": "<(dispatch_0_lo-1)"
}
```

`Raw` → `{"raw": "imm_op_dispatch_lo-&81"}` during migration. Downstream
HTML/analysis consumers can now re-render an expression to any assembler
or compute its value symbolically — impossible with today's opaque
string. The existing parallel-array shape for data blocks
(`"expressions": [null, {...}, ...]`) is retained, elements upgraded
from string to object.

## 7. Storage & IR changes

- `ExpressionRegistry` value type: `str` → `Expr` (`add()` wraps a `str`
  argument as `Raw` for back-compat).
- `Label.expressions`: `dict[int, list[str]]` → `dict[int, list[Expr]]`,
  same wrapping. `LabelManager.add_expression`'s "must not be a bare
  identifier" guard applies only to `str` inputs (an `Expr` is always
  allowed; a bare `Sym` is the structured way to say "just this name").
- Delete `_deferred_expressions` / `_register_deferred_expression` /
  `_resolve_deferred_expressions` — subsumed by `Ref`.

## 8. Migration path

1. Land `dasmos.core.expr` + the DSL + `render_expression` + `Raw`
   back-compat. **No behaviour change**: every existing driver still
   passes strings, wrapped as `Raw`, rendered exactly as today (beebasm
   byte-identical — the golden snapshots hold; 64tass keeps its regex
   for `Raw`).
2. Convert `code_ptr` / `rts_code_ptr` and the INKEY renderer path to
   build trees. These are dasmos-generated, so no driver churn; the
   golden snapshots are regenerated once (text may shift equivalently;
   the round-trip **binary** oracle is the real gate).
3. Teach the porter (`scripts/py8dis2dasmos.py`) to **parse** the
   beebasm-dialect strings into trees (a ~100-line Pratt parser over the
   closed operator set), emitting `Sub(Sym("imm_op_dispatch_lo"),
   Int(0x81, HEX))` etc. The regex `translate_expression` in
   `Tass64Renderer` then becomes dead code and is removed. This is the
   endgame: driver strings become structure at port time, and the
   `translate_expression` seam is retired.
4. New/hand-written drivers use the DSL directly.

## 9. Open questions

- **`constant()` no longer registers a label** (noted during survey), so
  a constant name can't resolve via `Ref(addr)`. Either (a) reference
  constants with `Sym(name)`, or (b) restore `constant()`'s optional
  label registration so `Ref` works uniformly. Recommend (a) for
  purity — a constant is a name, not an address.
- **Radix default for `Ref ± int`**: `AUTO` reproduces current output
  via the small-int heuristic; confirm no driver relies on a large
  decimal offset that the heuristic would flip to hex (survey found
  none — offsets are `1`, `2`, or `&81`/`&83`).
- **65816 bank byte / `^` power**: included in the enum for
  expressiveness though unused by current 6502 ROMs; costs nothing and
  avoids a future schema change.

---

# Addendum: string operations and the path to backend-agnostic macros

Motivated by the BBC BASIC 2 inline-assembler mnemonic-hash tables, whose
driver renders each table byte as the *expression* that recomputes it
(low 5 bits of each of a mnemonic's three letters, packed MSB-first):

    (('L' AND &1F) * &400 + ('D' AND &1F) * &20 + ('A' AND &1F)) AND &FF   ; lo
    (...) DIV &100                                                         ; hi

## A. What already works (validated)

These now parse, render, and **assemble to the identical hash byte on
both backends** (`tests/test_mnemonic_hash.py`):

| Capability | beebasm | 64tass |
|---|---|---|
| low / high byte select | `<(x)` / `>(x)` (or `LO`/`HI`) | `<(x)` / `>(x)` |
| character literal | `'L'` | `'L'` |
| bitwise AND mask | `AND &1F` | `& $1f` |
| multiply / add | `*` / `+` | `*` / `+` |
| **integer** division | `DIV &100` | `/ $100` |
| grouping | `( … )` | `( … )` |

The key point: `DIV` (integer) is a *distinct semantic operator* from
real division, and its spelling differs per assembler — the neutral
`BinOp.DIV` renders `DIV` for beebasm, `/` for 64tass, and would render
`DIV` for acme. A regex could never get this right; a typed tree does.

## B. String operations *(implemented)*

Landed: `Str` / `StrIndex` / `StrSlice` / `StrLen` nodes, the `string()`
DSL with Python `[]` indexing/slicing, native per-backend rendering
(64tass `"BRK"[0]`, beebasm `ASC(MID$("BRK",1,1))`), and a `fold()` pass.
The hash tables are authored as `string("BRK")[0]`; **by default the
string stays visible** in the listing (readability first), rendering
natively and still assembling to the correct hash byte on both backends.
`fold_string_ops=True` collapses to `'B'` for terse output, and folding is
also the fallback for a backend with no string support
(`tests/test_mnemonic_hash.py`, `tests/test_expr.py::TestStringOps`).

Low/high byte extraction is one projection of a value; **string indexing
and slicing** are the same idea for text, and the hash example is the
canonical driver. The three neutral leaf/operator nodes:

- `Str(text)` — a string literal.
- `StrIndex(s, i)` — the byte of `s` at index `i` (0-based). Value is an
  integer (a character code), usable anywhere an `Int` is.
- `StrSlice(s, i, j)` — a substring (value is a `Str`).
- (plus `StrLen(s)` and an explicit `Ord`/`Chr` if needed.)

**Rendering: readable by default, fold as a fallback.** A disassembly
exists to be *read*, so the default keeps the string visible by rendering
the op in the backend's native syntax; folding to the bare value is a
fallback (unsupported backend) or an opt-in (terseness). Three cases:

1. **Native (the default).** Each backend renders its own string syntax so
   `"BRK"` stays in the listing:

   | | `StrIndex(s, i)` | `StrSlice(s, i, j)` |
   |---|---|---|
   | 64tass | `s[i]` | `s[i:j]` |
   | beebasm | `ASC(MID$(s, i+1, 1))` | `MID$(s, i+1, j-i)` |
   | ca65 | `.strat(s, i)` | — (build from `.strat`) |
   | acme | *(no native form → folds, see 3)* | — |

   beebasm's `MID$` is 1-based; a constant index folds to a clean literal
   position (`MID$("BRK", 1, 1)`, not `… 0 + 1 …`).

2. **Folded on request** — `TextRenderer(fold_string_ops=True)` folds
   constant string ops to their value (`'B'`) for terse output. Per
   *expression* control is already available: a driver can `fold()` a
   specific expression before registering it.

3. **Folded as a fallback** — when a backend has no native form for a
   string op, dasmos folds it (which requires the operands be constant);
   a non-constant string op an assembler can't express is a genuine
   error. This is the same graceful-degradation contract as §C, and is
   what lets acme/ca65 handle the constant hash tables even without full
   string support.

So the hash tables show `("BRK"[0] & $1f) …` on 64tass and
`(ASC(MID$("BRK",1,1)) AND &1f) …` on beebasm by default — the mnemonic is
right there in the listing — and still assemble to the correct hash byte
(`tests/test_mnemonic_hash.py`).

## C. Backend-agnostic macros

The hash expression is emitted ~100 times (once per mnemonic, two halves)
with the *same shape* and a different three-letter string. That is a
**macro**: `pack(mnem, half)`. Lifting it from a Python helper that emits
strings to a dasmos-level macro is the natural next step, and the
expression tree is already the macro *body language*.

### C.1 Two kinds, because assemblers split them

- **Value macro** — returns an expression, used where a value is expected
  (`equb pack_lo("LDA")`). 64tass spells this `.function`; ca65 has no
  true value-function; beebasm folds it into a data-emitting `MACRO`;
  acme has none.
- **Code macro** — emits statements (an instruction sequence). beebasm
  `MACRO…ENDMACRO`, 64tass `.macro….endmacro`, ca65 `.macro….endmacro`,
  acme `!macro`.

dasmos models both as one neutral `Macro` (name, params, body) plus an
`invoke(name, args)`; a `returns=` flag marks a value macro. The body is
a list of emit-items (for code macros) or a single `Expr` (for value
macros), authored with the same DSL and `Ref`/`Sym`/`StrIndex` nodes,
where a `Param(name)` node stands for a formal parameter.

### C.2 The load-bearing principle: native construct OR inline-expand

A macro renders one of two ways per backend, chosen by capability:

1. **Native**: emit the assembler's own macro/function definition once and
   an invocation at each call site — when the backend supports the needed
   construct *and* every operation in the body (e.g. non-constant string
   indexing) has a native form there.
2. **Inline-expanded**: substitute the arguments into the body tree,
   **constant-fold**, and emit the resulting expression/statements at each
   call site — with no definition at all.

Inline expansion is always available (it is just tree substitution +
folding), so **every macro works on every backend**, worst case by
expansion. This is what lets a macro "work with beebasm and 64tass today
and acme/ca65 in future" without per-backend authoring: a new backend
starts by inlining everything, and gains native macro/function emission
incrementally as its `TextRenderer` implements the hooks.

For the hash tables specifically, the mnemonic is always a constant, so
inline-expansion + folding reproduces today's output exactly on beebasm,
and the correct `$`/`&`//`DIV` forms on 64tass — while a driver *could*
opt into a native `.function` on 64tass for compactness.

### C.3 Renderer hooks (refines the D-025 sketch)

```
macro_supported(kind) -> bool          # value | code — does this backend
                                       #   have a native construct?
macro_define(macro) -> list[str]       # the definition block
macro_invoke(name, arg_texts) -> str   # a call site (value) or line(s)
param_ref(name) -> str                 # how a formal param is referenced
                                       #   in the body (beebasm by name,
                                       #   64tass \1 or name, …)
```

When `macro_supported` is False, the shared layer inline-expands instead
of calling these — so a backend implements *nothing* and still works,
then overrides the hooks to go native. The argument-reference divergence
(named vs `\1` vs `@1`) is owned entirely by `param_ref` + `macro_invoke`,
the same lesson as `translate_expression`.

### C.4 Recommended sequencing

1. `Str` / `StrIndex` / `StrSlice` nodes + **constant-folding** (a pure
   `fold(expr) -> expr` pass). Immediately lets the hash tables be
   authored as `pack(mnem, half)` in the DSL with no macro machinery —
   folding inlines them. Small, self-contained, no new renderer hooks.
2. Native non-constant string rendering per backend (the §B table) —
   needed only once a macro parameter feeds a string op.
3. The `Macro` abstraction with inline-expansion as the default and the
   §C.3 hooks for native emission — build against beebasm + 64tass, with
   acme/ca65 riding the inline-expansion path from day one.

Steps 1–2 are the "string indexing" capability; step 3 is macros proper.
Each is independently landable and gated by the assemble-and-verify
oracle.
