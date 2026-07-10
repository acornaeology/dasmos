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
