# py8dis `commands.py` design-smell sweep memo

Generated 2026-05-02 by an exploration agent. Reads the public surface of
`py8dis/commands.py` (1,172 lines) end-to-end and cross-references each
function against actual call sites in two driver scripts:

- `acorn-econet-bridge/versions/econet-bridge-variant_1/disassemble/disasm_econet_bridge_variant_1.py` (3,153 lines)
- `acorn-6502-tube-client/versions/tube-6502-client-1.10/disassemble/disasm_tube_6502_client_110.py` (2,247 lines)

This memo is the input for the dasmos driver-script API design (task
#19). It is not itself an architectural decision — every "needs split"
recommendation here is a proposal for the user to sign off before
implementation.

---

## 1. Public surface inventory

### Loading & initialization
- `load(binary_load_addr, filename, cpu_name, md5sum)` — load binary; set CPU; init tracing state.
- `init(assembler_name, lower_case, output_filepath)` — explicit init for programmatic use.
- `move(dest_runtime_addr, src_binary_addr, length)` — register runtime relocation block (called before label/entry for relocated code).

### Labelling
- `label(runtime_addr, name, move_id, description, length, group, access)` — define label, optional memory-map metadata.
- `optional_label(runtime_addr, name, base_runtime_addr, definable_inline)` — output only if referenced.
- `local_label(runtime_addr, name, start_addr, end_addr, move_id)` — label scoped to address range.
- `expr_label(runtime_addr, s)` — define label as evaluable expression.
- `addr(label_name)` — look up runtime address of label.

### Constants
- `constant(value, name, comment, align, format)` — define named constant for assembly.

### Comments & annotations
- `comment(runtime_addr, text, inline, indent, word_wrap, align, move_id)` — user comment (default word-wrapped).
- `formatted_comment(runtime_addr, text, inline, align, indent, move_id)` — user comment without word wrap.
- `auto_comment(runtime_addr, text, inline, align, indent, show_blank, word_wrap, move_id)` — internal auto-generated comment, gated by `no_automatic_comment()`.
- `no_automatic_comment(runtime_addr)` — suppress auto-generated comments at address.
- `annotate(runtime_addr, s, align, priority)` — raw assembly annotation.
- `blank(runtime_addr, align, priority)` — blank line in output.

### Subroutines & data banners
- `subroutine(runtime_addr, name, title, description, on_entry, on_exit, hook, move_id, is_entry_point, at_binary_addr)` — banner + entry-point + tracing decoration.
- `data_banner(runtime_addr, name, title, description, move_id)` — subroutine-style banner for data regions (calls `subroutine(..., hook=None, is_entry_point=False)`).

### Code tracing & entry points
- `entry(runtime_addr, label, warn)` — mark address as code entry point.
- `nonentry(runtime_addr)` — mark as non-tracing.
- `wordentry(runtime_addr, n)` — mark word table as code-address pointers.
- `code_ptr(runtime_addr, runtime_addr_high, offset, label_name)` — emit lo/hi bytes of code address.
- `rts_code_ptr(runtime_addr, runtime_addr_high)` — shorthand for `code_ptr(..., offset=1)`.
- `hook_subroutine(runtime_addr, name, hook, warn)` — custom hook for non-standard control flow.

### Data classification
- `byte / word / fill / string` and the string family (`stringterm / stringcr / stringz / stringhi / stringhiz / stringn`).

### Expressions & formatting
- `expr(runtime_addr, s)` — replace operand with expression (string OR dict mapping value→expr).
- `auto_expr(runtime_addr, s)` — internal; gated by `no_auto_comment_set`.
- `set_formatter(runtime_addr, n, formatter)` — custom byte-formatter.
- `char / binary / picture_binary / decimal / hexadecimal / uint / sint / padded_uint` — data formatting hints.

### Expression builders (DSL)
- `bracket / make_op1 / make_op2 / make_lo / make_hi / make_or / make_and / make_eor / make_xor / make_add / make_subtract / make_multiply / make_divide / make_modulo`, plus `is_simple_name`, `assembler_op_name`. Clean and orthogonal.

### Hooks
- `set_label_maker_hook(hook)` — register user function for auto-naming labels.

### Main entry
- `go(print_output, post_trace_steps, autostring_min_length)` — classify code/data; emit assembly. Asserts no active `move_id` context remains.
- `get_structured()` — fetch structured JSON output (must be after `go()`).

---

## 2. Per-function smell classification

### Clean — lift as-is
`label`, `optional_label`, `local_label`, `expr_label`, `constant`,
`entry`, `nonentry`, `wordentry`, `byte`, `word`, `fill`, the entire
string family, `code_ptr`, `rts_code_ptr`, `hook_subroutine`,
`set_label_maker_hook`, `addr`, `get_label`, `get_u8_binary`,
`get_u16_binary`, `get_u16_be_binary`, the expression-builder DSL,
`go`, `get_structured`, `is_assembler`, `substitute_constants`.

### Minor cleanup
- **`comment` / `formatted_comment` / `auto_comment`** — three near-identical functions sharing an `inline`↔`align` legacy shim. Unify into one.
- **`annotate` / `blank`** — `blank()` is a thin wrapper. Acceptable as a convenience; no change needed.
- **`set_formatter`** — loops `n` times calling `r2b_checked()` per byte. Mild inefficiency; not blocking.
- **`substitute_constants`** — accumulates global state with three-valued `define_all_constants` flag. Document order requirements.

### Structural smell — needs split

#### S1. `subroutine()` is two concerns in one

Conflates **semantic** registration (entry point, name, tracing control)
with **visual** output (banner comment, title/description,
`on_entry`/`on_exit` blocks). Uses `is_entry_point=True` and `hook=...`
as mode flags to switch behaviour.

**Proposed split** (the user already nominated this exact pattern):

```python
banner(runtime_addr, text, *, align=Align.BEFORE_LABEL)
    # Visual only. Emit a comment block at the address.

subroutine(runtime_addr, name=None, *, hook=False, move_id=None)
    # Semantic only. Register a code entry point (always); optionally
    # add a name label; optionally enable a hook.
```

Callers wanting both register both. A `subroutine_with_banner()`
convenience wrapper is acceptable but should not be the primary API.

#### S2. `comment` / `formatted_comment` / `auto_comment` are three near-identical functions

Three near-identical signatures sharing the `inline`/`align` shim,
with `auto_comment()` adding gating logic for "is this auto-generated".
Unify:

```python
comment(runtime_addr, text, *, word_wrap=True, align=Align.BEFORE_LABEL, move_id=None)
    # Public; user-supplied.

# Internal-only:
_auto_comment(runtime_addr, text, *, word_wrap=False, align=Align.BEFORE_LABEL, move_id=None)
    # Suppressible via no_automatic_comment(addr).
```

Drop the `inline=True` legacy parameter; `align=Align.INLINE` is the
explicit form.

#### S3. `expr()` overloads string and dict

`expr(addr, "expression")` and `expr(addr, {value: expression, ...})`
are different operations behind one signature. Split:

```python
expr(runtime_addr, expression: str)
expr_by_value(runtime_addr, value_to_expression: dict)
```

#### S4. `move_id` is a context manager, but few people know

`with move_id: ...` pushes onto a hidden stack. Unused in either
driver script we surveyed; `go()` asserts the stack is empty. If we
keep this, document it explicitly. We've already moved this concern
onto `MoveManager.using()` in the dasmos `core/move.py` port — driver
API surfaces `d.using_move(move_id)` instead.

---

## 3. Real-usage cross-reference

### S1 (subroutine/banner split)

- **econet-bridge**: 26+ calls of the form
  `subroutine(..., hook=None, is_entry_point=False, ...)` for data
  regions and named regions. Lines 116, 126, 152, 355–363, 395–406,
  422–431, 441–449, 703–723, 759–793, 835–853, 873–930, 945–1003,
  1004–1135, 1136–1148, 1149–1180, 1181–1204, 1205–1228, 1229–1362,
  …
- **tube-client**: 40+ similar calls (e.g. lines 494–501 for
  `rdline_control_block` — a data region marked with
  `is_entry_point=False`).

**Verdict: HIGH PRIORITY.** Both drivers heavily use the
data-banner idiom. The split is the single biggest API improvement.

### S2 (comment unification)

- **econet-bridge**: 1,123 `comment()` calls; ~104 use `inline=True`.
- **tube-client**: 851 `comment()` calls; ~267 use `inline=True`.

**Verdict: HIGH PRIORITY.** `comment()` is the most-called function
in the entire driver-script API; the legacy `inline` parameter must
become `align=Align.INLINE` for clarity.

### S3 (expr overload)

- **econet-bridge**: 2 `expr()` calls — both string form.
- **tube-client**: 5 `expr()` calls — all string form.

**Verdict: LOW PRIORITY.** Dict mode unused in surveyed drivers.
Split is still right but not blocking; could even be deferred until a
real use surfaces.

### S4 (move_id context manager)

Neither driver uses `with move_id: ...`.

**Verdict: LOW PRIORITY.** Not exposed in the dasmos primary API.

---

## 4. Driver-script idiom catalog

Top calls across both drivers (frequency drives priority for the new API):

| Rank | Function | Econet | Tube | Total |
|---|---|---:|---:|---:|
| 1 | `comment()` | 1,123 | 851 | **1,974** |
| 2 | `label()` | 185 | 226 | 411 |
| 3 | `subroutine()` | 48 | 84 | 132 |
| 4 | `entry()` | 2 | 58 | 60 |
| 5 | `byte()` | 1 | 12 | 13 |
| 6 | `word()` | 3 | 4 | 7 |
| 7 | `expr()` | 2 | 5 | 7 |
| 8 | `fill()` | 3 | 0 | 3 |
| 9 | `hook_subroutine()` | 0 | 1 | 1 |

**Insight:** `comment + label + subroutine` is ~80% of all driver
calls. The dasmos API should make those three first-class and
elegant. Explicit byte/word/fill classification is rare (auto-inference
covers most cases) — those should still exist but don't need to be
the first thing a new user sees.

---

## 5. Hidden state and ordering hazards

| # | Hazard | Current py8dis | Proposed dasmos |
|---|---|---|---|
| H1 | `load()` must come before any address-based command | Implicit; relies on user discipline | Raise on use-before-load (`memory_binary is None` is a clear error) |
| H2 | `move()` must come immediately after `load()` (before any address command for the moved range) | Documented in docstring, not enforced | Either enforce a setup phase, or detect "move registered after addresses on overlapping range" and warn |
| H3 | `init()` must come before `load()` if used | Auto-init from `sys.argv` papers over the issue | Fold into `load(...)` or `Disassembler.create(...)` |
| H4 | `set_label_maker_hook()` must come before `go()` | Not enforced | Property setter; assert `not self._disassembled` |
| H5 | `go()` asserts empty `move_id` stack | Bare `assert`; cryptic message | Raise a typed exception with a clear message naming the stuck context |
| H6 | Comment/expression/label state accumulates | First-call-wins for some, last-call-wins for others; inconsistent | Document and pick one policy per concern; expose via the manager classes consistently |

---

## 6. Recommended design changes for the dasmos driver-script API

| # | Change | Priority |
|---|---|---|
| C1 | Unify `comment` / `formatted_comment` / `auto_comment` into one `comment()` with `align=` (drop `inline=`) | **HIGH** |
| C2 | Split `subroutine()` into `subroutine()` (semantic) + `banner()` (visual) | **HIGH** |
| C3 | Replace `is_entry_point=False` data-banner idiom with explicit `banner()` calls | **HIGH** |
| C4 | Strengthen ordering hazards into typed exceptions with informative messages | **MEDIUM** |
| C5 | Fold `init()` + `load()` setup into a structured phase (`Disassembler.create(cpu=...)` then `d.load(...)`) | **MEDIUM** |
| C6 | Provide a clean `with d.using_move(id): ...` instead of `with move_id: ...` (already done in `MoveManager.using()`) | **MEDIUM** |
| C7 | Split `expr()` string vs dict overload into `expr()` + `expr_by_value()` | **LOW** |
| C8 | Mark `byte` / `word` / `fill` as advanced-use (auto-inference covers most cases) | **LOW** |
| C9 | Promote the expression-builder DSL (`make_lo`, `make_or`, etc.) in docs | **LOW** |
| C10 | Add `d.reset()` for test/batch use cases | **LOW** |

**Execution order for the driver-API port (#19):**

- **Phase 1 (foundation):** C1, C2, C3, C4. The high-priority items;
  affect the most user-visible parts of the API and clean up the
  dominant idioms.
- **Phase 2 (structure):** C5, C6. Make the lifecycle explicit.
- **Phase 3 (polish):** C7, C8, C9, C10. Defensible later.

Phase 1 alone delivers the bulk of the API improvement.
