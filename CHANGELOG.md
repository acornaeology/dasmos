# Changelog

All notable changes to *dasmos* are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/) and the
project follows [SemVer](https://semver.org/) — though while pre-1.0,
minor bumps may carry small breaking changes alongside additive ones.

## [Unreleased]

### Added

- **Indexing regions (`d.index_region`).** Declares a window of
  addresses around an anchor label whose in-window neighbours render
  relative to the anchor — `lda fsm_sector0-3,X` instead of a scatter
  of per-byte `_preN` labels or a bare address. `window=(lo, hi)` is an
  inclusive offset range; the anchor keeps its normal
  `description`/`group`/`access` and memory-map row. A region is a
  naming *lens for the gaps*: an explicit label placed inside the
  window always wins (precedence: explicit → region → auto-label →
  hex), enforced by construction. The default inline form is arithmetic
  on the anchor (`anchor±k`), which reassembles to identical bytes;
  `named_slots=True` instead gives each gap a `name_m<k>` / `name_p<k>`
  identifier. Windows must be disjoint — an overlap raises `RegionError`
  at declaration. Regions are runtime-space and move-agnostic, exposed
  on the IR (`ir.index_regions`) and as a top-level `regions` array in
  JSON. Built on the existing expression-label machinery, so no renderer
  changes were needed for the inline form. See
  `docs/design/reference-kinds-memo.md`.

- **Indexed-base reference classification.** Every use site now records
  *how* an operand reaches its address via a
  `ReferenceKind` (`dasmos.core.memory`): `DIRECT`, `POINTER`,
  `INDEXED`, or `INDEXED_POINTER`. A CPU's `AddressingMode` carries the
  kind (6502 and 65C02 populated; the `(zp),Y` pointer classifies as
  owned while `(zp,X)` is base-only). Cross-reference summaries reword
  accordingly — an address used only as an indexing base now reads
  `used as index base N times by …` instead of the misleading
  `referenced N times …`, in both the beebasm and JSON renderers. New
  `d.index_base(addr, name, …)` (and the `access='indexed_base'` tag it
  sets) documents a base — keeping its description / group / length —
  while keeping it **off** the fixed-location memory map; the JSON
  renderer lists such bases under a new top-level `index_bases` array.
  This is the intention-revealing replacement for stripping metadata to
  hide a base. See `docs/design/reference-kinds-memo.md`, which also
  specifies the follow-up base±displacement slot-naming layer.

- **Pluggable custom data types.** `d.typed_data(addr, type)` marks an
  N-byte region as a domain-specific aggregate: it emits the **raw
  bytes** for byte-faithful reassembly and attaches the *decoded* value
  as an annotation (an asm inline comment; a structured `decoded`
  field — `{type, text, value, comment}` — in JSON output). A
  `DataType` (`dasmos.core.data_type`) owns its width, so the length is
  implied by the type, not repeated at the call site; `type` may be a
  registered name, a `DataType` instance, or a bare callable plus an
  explicit `length`. Decoding is eager (driver/env-side), so renderers
  need no per-type knowledge and the round-trip oracle is never at
  risk — many domain types (the BBC 5-byte float is the motivating
  case) have no assembler literal that reassembles to the same bytes.
  Environments contribute types via `d.register_data_type(name, type)`.
  (#27)
- **`bbc_basic_6502` environment.** Registers the `bbc_float5` data
  type — BBC BASIC's packed 5-byte floating-point format (excess-128
  exponent, implied leading 1, sign in the mantissa MSB). Decodes the
  REAL-constant pool (e, π/2, ln 2, …) to readable values while keeping
  the bytes exact. (#27)

- **Classification override.** A driver can now reclaim bytes an
  environment classified eagerly. `Disassembler.entry(addr,
  override=True)` clears any conflicting classification at the target
  before seeding the trace, so an explicit driver call made after
  `use_environment()` wins. `override=True` is also accepted by
  `byte` / `word` / `string` / `fill`. Backing this:
  `ClassificationStore.remove(addr)` (clears a whole span) and
  `remove_range(addr, length)`. Override only changes how bytes
  render — never the bytes — so the round-trip oracle is unaffected.
  (#25)
- **No more silent `entry()` no-op.** Calling `entry()` on an address
  already classified as data (without `override`) now emits a
  `UserWarning` instead of silently doing nothing — the trace cannot
  reclassify already-classified bytes. Accidental overlaps still
  raise. (#25)
- **`acorn_sideways_rom` entry-slot modes.** `use_environment(
  "acorn_sideways_rom", language_entry=..., service_entry=...)` accepts
  `"auto"` (default; unchanged `byte0` heuristic), `"code"` (the slot
  is inline code — seed an entry, let the trace own the bytes, no
  handler label), or `"none"` (the slot is not this ROM's entry —
  attach no label, classification, or banner). Unblocks inline-code
  language ROMs such as BBC BASIC II, whose `&8000` is
  `CMP #1 / BEQ / RTS` rather than a `JMP abs` and whose `&8003` is the
  tail of that code, not a service entry. (#26)
- `stringhi_skip_hook` — an inline-string subroutine hook for the Acorn
  convention where the bit-7 terminator is the final character of the
  string (consumed, trace resumes at terminator+1), as used by ADFS
  1.30's `print_inline_string` (&92A0). Complements `stringhi_hook`,
  which leaves the terminator in the instruction stream and resumes at
  it. (#24)

### Changed

- **Acorn SCSI host-adapter register names.** The shared Fred-bus
  labels at &FC40-&FC43 are renamed from the generic
  `fred_hard_drive_0..3` to the specific `scsi_data`, `scsi_status`,
  `scsi_select` and `scsi_irq_enable`, matching the Acorn SCSI /
  Winchester host adapter the addresses actually drive. Disassemblies
  using the `acorn_model_b_hardware` / `acorn_master_hardware`
  environments inherit the clearer names.

### Fixed

- **Duplicate equate when a constant shadows a label.** The beebasm
  renderer no longer emits a constant equate that exactly duplicates a
  label definition (same name at the same address). Previously a driver
  that registered, say, a `scsi_data` constant at an address an
  environment also labels `scsi_data` produced two `scsi_data = &xxxx`
  lines and beebasm rejected the second with "Symbol already defined".

## [0.2.0]

A substantial release. New driver-API surface for renderer-agnostic
operand formatting (the `FormatHint` family); a runtime-aware tracer
that correctly classifies instructions inside relocated (`add_move`)
regions; a much richer `acorn_mos` analyser suite; and a redesigned
move subsystem with typed `Move` handles. Every change preserves the
byte-for-byte round-trip oracle.

### Added

- **`FormatHint` API.** New `dasmos.FormatHint` enum (re-exported
  from the top-level package) declares operand-byte semantic intent
  separately from the assembler-specific syntax. Hints: `CHAR`,
  `DECIMAL`, `HEX`, `BINARY`, `OCTAL`, `INKEY` (BBC keyboard scan
  code). Used via `Disassembler.format_hint(addr, hint)` plus sugar
  methods `Disassembler.char_literal(addr)` and
  `Disassembler.inkey_code(addr)`. Each renderer translates a hint
  into its own grammar; the JSON renderer surfaces it on the
  per-operand record so downstream tooling can render appropriately.
- **`acorn_mos` INKEY analyser.** Recognises the BBC's negative-X
  scan-code pattern at `OSBYTE &79` / `OSBYTE &81` and registers
  `inkey_key_<name>` constants plus a `FormatHint.INKEY` at the
  `LDX`'s operand byte. The rendered listing reads
  `ldx #(255 - inkey_key_ctrl) EOR 128` instead of `ldx #&81`. The
  JSR-site inline comment names the specific key
  (`Test for ctrl key pressed`).
- **Declarative string detection.** `string_detection_min_length`
  ctor kwarg / property on `Disassembler` (default `3`; `None`
  disables). Replaces py8dis's closure-based `autostring` with a
  property the driver sets once. Runs break at labels, move-source
  boundaries, annotation addresses, and non-printable bytes.
- **Bucket-1 / -2 acorn_mos analysers.**
  - Long-form descriptions for OSBYTE / OSWORD (`OSBYTE_DESCRIPTIONS`,
    `OSWORD_DESCRIPTIONS` data tables — replaces py8dis's
    1500-line `osbyte_action` if/elif chain).
  - Per-X-value descriptions for OSBYTEs whose action varies by X
    (`OSBYTE_X_VALUE_DESCRIPTIONS`).
  - Post-call register-state descriptions
    (`OSBYTE_POST_CALL_DESCRIPTIONS` — `X is POS`, `Y is VPOS`, …)
    attached at the byte after the JSR.
  - Markdown post-call value tables (`OSBYTE_POST_CALL_TABLES`,
    `OSARGS_POST_CALL_TABLES`) — e.g. the OS-version table for
    `OSBYTE &00`, the FS-number table for `OSARGS A=0 Y=0`. Asm
    renderer flattens via mistletoe; JSON keeps the source markdown
    so the site generator can render real `<table>` elements.
- **OSARGS analyser.** Joint `(A, Y)` dispatch (`osargs_analyzer`
  registered at `&FFDA`). Stacks alongside driver-supplied inline
  comments via the `auto_generated` flag.
- **Environment-axis split.** The previous `acorn_bbc_hardware` env
  is now three orthogonal axes:
  - `acorn_model_b_hardware` / `acorn_master_hardware` (machine class)
  - `acorn_fdc_8271` / `acorn_fdc_1770` (FDC variant — opt-in)
  - `acorn_sideways_rom` (sideways-ROM header labels)
  Mix and match per ROM target.
- **`Move` typed handle.** `Disassembler.add_move(...)` returns a
  `Move` object that's also a context manager — `with move: ...`
  scopes annotations under it. Stable identity in diagnostics, JSON
  output, and `@move-name` URI variants in markdown comments.
- **Porter polish.** `scripts/py8dis2dasmos.py` now preserves hex
  literals, triple-quotes multiline strings, inserts blank lines
  before subroutines / labels, simplifies the JSON emit pipeline
  (drops the `try/except` plus the `json.dumps` plumbing), threads
  `encoding="utf-8"` into ported `read_text` / `write_text` calls,
  and rewrites `go(post_trace_steps=lambda: classification.autostring(K))`
  to the declarative `string_detection_min_length=K` form.
- **JSON `banners[]` array.** Standalone banners (driver's
  `d.banner(...)` calls separate from `d.subroutine(...)`) now
  appear in their own JSON array distinct from `subroutines[]`,
  so the site generator can render them as banner-only items
  rather than forcing a synthetic subroutine entry.
- **Auto-label heuristics.** Return-N convention, Fred-bus support,
  ergonomic prefixes (`l`, `c`, `sub_c`, `loop_c`).
- **Vendored ROM fixtures.** ANFS 4.18, ANFS 4.21 (variant 1), NFS
  3.34, ADFS 1.30 join the existing fixtures as round-trip oracles.
- **Documentation.**
  - Format hints + automatic string detection sections in the
    driver-API guide.
  - Auto-comment style guide for analyser-driven inline text
    (`docs/design/auto-comment-style.md`).
  - Move-subsystem redesign memo (`docs/design/move-redesign-memo.md`).
  - Migration handover document (`docs/handover_migration.md`).

### Changed

- **Tracer is runtime-aware.** Control-flow targets (JSR / JMP
  operands, branch offsets) are now computed in *runtime* address
  space and resolved back to binary via the move map. Previously
  the tracer treated operand values as binary addresses, which
  silently terminated trace paths into relocated regions. Recovers
  proper instruction classification at every JSR-into-moved-code
  site and at relative branches whose source byte sits inside a
  move. Mirrors py8dis's runtime-aware tracer (`py8dis/cpu6502.py`).
- **Move-boundary straddle check by effective ownership.**
  `_opcode_straddles_move_boundary` now consults `MoveManager`'s
  per-byte owner map (post-`add_move` last-wins) rather than every
  registered move's *declared* geometry. An opcode wholly inside a
  later overlapping move no longer false-positives as straddling
  (recovers NFS-3.34's BCS at `&9367`).
- **65C02 CPU state tracking.** `Cmos65C02Cpu` now inherits from
  `Nmos6502Cpu` plus 65C02-specific overrides for PHX/PHY/PLX/PLY/
  STZ/BRA/TRB/TSB. Previously the 65C02 inherited only the no-op
  default `update_state`, so OSBYTE/OSWORD analyser state-tracking
  silently never fired for any 65C02 ROM (Tube Client, ANFS 4.21).
- **Mid-classification annotations now render.** Comments and
  banners attached to bytes *inside* a multi-byte classification
  (operand bytes, mid-class labels) now appear in the rendered
  output. Inline comments are gathered across every covered byte
  and joined; mid-class label-equate lines emit any `BEFORE_LABEL`
  / `BEFORE_LINE` annotations attached at that mid-class address.
- **Leftover-byte aggregation.** `_classify_leftovers` now groups
  consecutive unclassified bytes into a single `Byte(N)` (matching
  py8dis), breaking only at labels, move boundaries, and annotated
  addresses. Avoids long `equb &ff [* 1]` runs in the output.
- **JSON schema additions.** Memory-map entries gain `length`,
  `group`, `access` columns; subroutines omit `binary_addr` when it
  equals `runtime_addr` (matches the per-item convention); banners
  appear in their own `banners[]` array; format hints surface on
  per-operand records.
- **Beebasm renderer.** `char_literal_style` setting (`ASC("c")` /
  `'c'` / quoted-comment / off); `lower_case` setting controls
  mnemonic and suffix case; small ints render as decimal by
  default; markdown stripped from banner title / description and
  equate-line comments via mistletoe; xref summaries use binary
  addresses on both sides for consistency; expression labels appear
  in operand text and in the stats footer; mid-instruction xref
  summaries use the inner binary address.
- **CPU plug-in names canonicalised** to `6502` and `65C02`
  (case-insensitive lookup retained).
- **Encoding.** Driver scripts and rendered output never rely on
  the locale default; `--encoding` CLI flag added; LF line endings
  pinned in fixtures.
- **README** restructured: dasmos introduced on its own merits;
  lineage paragraphs moved to a closing section.

### Fixed

- **Multi-source / same-destination moves** in the beebasm renderer
  (each move's source emits separately under its own `pseudopc`).
- **Auto-label generation suppressed at expression-alias addresses**
  so `irq1v+1` doesn't compete with synthetic `l0221`.
- **Porter `output = go(...)`** form handled the same as bare
  `go(...)`.

### Removed

- **`acorn_bbc_hardware`** env (replaced by the three-axis split
  above).

## [0.1.3] — 2026-05-04

Patch-level: porter encoding fix and small porter-output tweaks.
See `git log v0.1.2..v0.1.3` for the full picture.

## [0.1.2] — 2026-05-04

## [0.1.1] — 2026-05-03

First versioned release. Earlier history is in the git log.
