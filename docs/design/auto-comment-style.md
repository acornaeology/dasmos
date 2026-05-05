# Auto-comment style guide

**Status:** style guide; reviewed prose conventions for the
contextual inline-comment generation in environment plug-ins (e.g.
`acorn_mos/hooks.py`). Authoritative when extending those analyzers
or adding new ones.

This document covers *auto-generated* inline comments — strings
attached to instructions by environment-plug-in analyzers as a
side-effect of recognising an OS-call pattern. It does NOT cover
driver-script `comment()` calls (those are author voice; the author
chooses their own style) or block-banner descriptions
(multi-paragraph Markdown).

---

## 1. Where these comments live

In the assembly listing, in the inline-comment column at the right
of an instruction line:

```
    lda #&40                                 ; value to write
    jsr osfile                               ; open file for input
```

The column is narrow. Annotations have to compete with the byte
column, the optional address-suffix marker, and any user-supplied
inline comment. So our first principle:

> **Inline auto-comments are sentence fragments, not sentences.**

Lowercase, no trailing period, as few words as accurate.

---

## 2. Voice and tone

### 2.1 Lowercase fragments

```
GOOD: write byte to screen
BAD:  Write byte to screen.
BAD:  Writes a byte to the screen.
```

Title-cased annotations read like book chapter titles. Lowercase is
quieter and lets the reader's eye glide across many lines.

### 2.2 Drop the redundant register-name prefix at the source instruction

When the comment lands on an instruction whose operand *is* the
register the value is going into, the prefix is redundant:

```
GOOD: lda #&40                               ; value to write
BAD:  lda #&40                               ; A=value to be written
```

The `lda` already names A as the destination. The comment's job is
to say *what* the value is, not *that* it goes to A.

Keep the prefix only when the load is far from the JSR and the
reader might need a reminder of which register is in flight:

```
ACCEPTABLE (load on line 5, JSR on line 47):
    lda #&40                                 ; A: file open mode
    ...
    jsr osfind                               ; open file
```

### 2.3 Mark exit-state comments with `→`

When a comment describes the value a register holds *after* the OS
call returns, prefix it with `→` (U+2192). Entry-state comments are
unmarked:

```
GOOD entry-state:
    ldy #&00                                 ; offset from base
    jsr oswrch                               ; write byte to screen

GOOD exit-state:
    jsr osfind                               ; open file for input
    sta file_handle                          ; → file handle (0 = failed)
```

The arrow is unmissable in the column even when scanning quickly,
and avoids ambiguity about flow direction. It's a single character,
so the cost in column width is trivial.

### 2.4 Drop literal-value tails when the load is on the same / adjacent line

py8dis often appends `(A=64)` to its strings (`open file for input
(A=64)`). When the LDA is right above the JSR, this duplicates
information the reader already has. Drop it.

```
GOOD (load nearby):
    lda #&40
    jsr osfind                               ; open file for input

ACCEPTABLE (load very far from JSR):
    lda #&40
    ... (40 lines)
    jsr osfind                               ; open file for input (A=&40)
```

Use the renderer's distance heuristic if we have one; otherwise just
omit the tail and trust that the LDA above tells the same story.

### 2.5 Use `:` not `=` for named values

```
GOOD: generate event: vsync
BAD:  generate event Y='vsync'
```

Colons read as English ("the value, namely vsync") rather than as
the assignment operator. Single-quote-the-name patterns are noisy.

### 2.6 Spell out, then use established short forms

For names that are already established lower-case forms in the BBC
community — `osbyte`, `osword`, `osfile`, `osfind`, `vsync`,
`oswrch`, `crtc`, `via`, `irq`, `nmi`, `tube`, `econet`, `adlc` —
use them directly without expansion. They're shorter than their
expansions and mean the same thing to the audience reading these
listings.

For less-established or platform-specific terms, prefer the spelled
form on first or only use:

```
GOOD: paged ROM number             (rather than `ROMSEL number`)
GOOD: write byte to screen         (rather than `OSWRSC byte`)
```

Reserve abbreviations for the high-traffic call surface where
density matters.

---

## 3. Argument-passing patterns

### 3.1 Single-register input → call

```
GOOD:
    ldx #&30                                 ; lowest ADFS file handle
    jsr osfind                               ; open file
```

Comment on the LDX names what the value *means*; comment on the JSR
names what the call *does*. Both fragments. No register prefix on
the LDX (the operand makes it obvious).

### 3.2 Multi-register input → call

```
GOOD:
    lda #&40                                 ; mode: input
    ldy #fname                               ; → filename block
    jsr osfind                               ; open file
```

Each input register gets its own fragment. If the same call can
take different actions depending on register combinations (OSFIND,
OSFILE, OSGBPB are like this), the JSR comment specialises to the
recognised action — `open file for input` rather than the generic
`open or close file`.

### 3.3 Call → exit-state result

```
GOOD:
    jsr osfind                               ; open file for input
    sta handle                               ; → file handle (0 = failed)
```

The arrow signals the value moves *out* of the call. The error
encoding is named in parentheses without an `=` (which would imply
runtime equality, not "this is what the value means").

### 3.4 Conditional based on a known immediate

When the analyzer knows the immediate value, name the action
directly. When it doesn't, the comment stays silent (per §5.4 —
a generic placeholder reads worse than nothing):

```
KNOWN A=&40:    jsr osfind                   ; osfind: open file for input
KNOWN A=&80:    jsr osfind                   ; osfind: open file for output
KNOWN A=&C0:    jsr osfind                   ; osfind: open file for update
KNOWN A=&00:    jsr osfind                   ; osfind: close one or all files
UNKNOWN:        jsr osfind                   ; (no comment)
```

When emitted, every comment carries the call-name prefix (see
§3.5). The unknown case never needs an `(A=...)` literal because
there's nothing useful to say.

### 3.5 Call-name prefix anchors the action description

Every analyzer-generated inline comment starts with the call name
followed by `:`. The prefix is structural — without it a fragment
like `select input stream` or `read line` floats free of context
and could be misread as describing surrounding code. With it the
reader scans the column and immediately sees: this is an OS call,
specifically OSBYTE / OSWORD / OSFIND / etc.:

```
GOOD: jsr osbyte                             ; osbyte: select input stream
GOOD: jsr osword                             ; osword: read I/O memory
GOOD: jsr osfind                             ; osfind: open file for input
GOOD: jsr osfile                             ; osfile: save block of memory
GOOD: jsr osgbpb                             ; osgbpb: read filenames in current directory
GOOD: jsr oseven                             ; oseven: vsync
```

The prefix is consistent across all OS-call analyzers — even ones
where the body alone might already convey the call kind
(`osfind: open file for input` is mildly redundant since "file"
already implies filesystem). Consistency wins: the reader's eye
learns to skip the prefix and focus on the body, which is more
valuable than saving 8 characters per comment.

### 3.6 Enum-name lookup

When the call's argument is a value from a known enum (event
numbers, OSBYTE action codes), embed the enum name in the comment
body. The prefix-then-action shape replaces the older
``generate event: vsync`` form:

```
GOOD: oseven: vsync                          (Y=&04 → event_start_of_vertical_sync)
GOOD: oseven: paged-rom-changed              (a hypothetical event)
SILENT: jsr oseven                           ; (no comment when Y is dynamic)
```

If an enum entry is ambiguous about meaning ("`PCALL` — what does
that do?") the embedded name is still the right pick: a reader can
search for it; opening a paragraph of explanation in the inline
column would be wrong.

---

## 4. Worked examples for current Acorn analyzers

### OSWRSC (write byte to screen / paged ROM)

```
    lda #&41                                 ; value to write
    ldy #&00                                 ; offset from base
    jsr oswrsc                               ; oswrsc: write byte to screen
```

### OSRDSC (read byte from screen / paged ROM)

```
    ldy #&80                                 ; paged ROM number
    jsr osrdsc                               ; osrdsc: read byte from paged ROM
    sta tmp                                  ; → byte read
```

### OSEVEN (generate event)

```
KNOWN event:
    ldy #&04                                 ; event: vsync
    jsr oseven                               ; oseven: vsync

UNKNOWN event:
    jsr oseven                               ; (no comment)
```

When Y is statically known the JSR comment names the event; when Y
is dynamic the analyzer stays silent (per §5.4).

### OSFIND (open / close file)

| A         | LDA comment                        | JSR comment                       |
|-----------|------------------------------------|-----------------------------------|
| `&00`     | (no LDA comment — A=0)             | `osfind: close one or all files`  |
| `&40`     | (or just omit)                     | `osfind: open file for input`     |
| `&80`     | (or just omit)                     | `osfind: open file for output`    |
| `&C0`     | (or just omit)                     | `osfind: open file for update`    |
| unknown   | (no comment)                       | (no comment)                      |

Returns:

```
    sta file_handle                          ; → file handle (0 = failed)
```

### OSGBPB (transfer parameter-block read/write)

```
KNOWN A=&08:    jsr osgbpb                   ; osgbpb: read filenames in current directory
KNOWN A=&01:    jsr osgbpb                   ; osgbpb: write bytes (at given pointer)
UNKNOWN:        jsr osgbpb                   ; (no comment)
```

The OSGBPB calls take a parameter block addressed by XY. py8dis
attaches per-field comments inside the block; dasmos doesn't yet,
but when we do they should match the style:

```
.gbpb_block
    equb &00                                 ; file handle
    equb &00, &00, &00, &00                  ; data address (4 bytes)
    equb &00, &00, &00, &00                  ; transfer length (4 bytes)
    equb &00, &00, &00, &00                  ; sequential pointer (4 bytes)
```

The "(N bytes)" suffix marks multi-byte fields so the reader can
skip past them without counting; it's not redundant the way
`(A=64)` is — the field-byte count isn't visible on the line.

### OSBYTE / OSWORD (mechanically-derived bodies)

OSBYTE has ~150 actions and OSWORD ~16. Both use mechanical
derivation from the existing OSBYTE_ENUM / OSWORD_ENUM names:
strip the ``osbyte_`` / ``osword_`` prefix, replace underscores
with spaces, prepend ``osbyte: `` / ``osword: ``. Override tables
catch the few entries where the mechanical strip is awkward.

```
KNOWN A=&00:    jsr osbyte                   ; osbyte: read os version
KNOWN A=&02:    jsr osbyte                   ; osbyte: select input stream
KNOWN A=&7c:    jsr osbyte                   ; osbyte: clear escape
KNOWN A=&13:    jsr osbyte                   ; osbyte: wait for vsync
                                                       ↑ override (mech: "vsync")

KNOWN A=&00:    jsr osword                   ; osword: read line
KNOWN A=&05:    jsr osword                   ; osword: read I/O memory
                                                       ↑ override
KNOWN A=&0e:    jsr osword                   ; osword: read CMOS clock
                                                       ↑ override
```

The override table preserves a body's casing (acronyms stay
capitalised); the prefix is added uniformly.

---

## 5. Edge cases

### 5.1 Mid-instruction operand byte references

Sometimes the analyzer's "this load feeds register R" lookup
identifies an immediate-load byte that's *inside* another
instruction (operand byte being self-modified, or two instructions
that overlap via a jump). Don't attach a comment in those cases —
the byte's classification is uncertain, the comment would render in
the wrong column or duplicate. Skip silently.

### 5.2 Multiple analyzers fire on the same call

If both an OS-call analyzer and (say) a hardware-port analyzer
attach inline comments to the same JSR, the duplicate-annotation
warning we added in `AnnotationStore.add` will fire. That's
correct: it's almost always a real bug (two analyzers claiming the
same site). The right fix is for one analyzer to defer to the
other, not to silence the warning.

### 5.3 The driver registered an explicit comment first

A driver-supplied `d.comment(addr, text, inline=True)` always wins.
If our analyzer sees an existing inline comment at the address, it
should skip — the author has spoken. (Today that's not implemented;
relying on the duplicate-warning to surface conflicts. Worth
revisiting if the warnings get noisy.)

### 5.4 No good comment available

If the analyzer can't say anything specific, it should say nothing.
A bare `; OS call` is worse than no comment — it consumes column
width without informing.

---

## 6. Style as a quick checklist

When writing a new auto-comment, ask:

- [ ] Lowercase, no trailing period?
- [ ] Sentence fragment, not full sentence?
- [ ] Drop redundant register-name prefix when the comment is on
      the source instruction?
- [ ] Mark exit-state comments with `→`?
- [ ] No `(A=...)` tail when the load is nearby?
- [ ] `:` not `=` for embedded named values?
- [ ] Use established short forms (`osfind`, `vsync`) but spell
      out platform-specific terms (`paged ROM number`)?

If any answer is no, justify in a one-line code comment so reviewers
can see the deliberate divergence.

---

## 7. Open questions

### 7.1 Distance heuristic for the literal-value tail

§2.4 says drop `(A=64)` when the LDA is "nearby". What's the
threshold? Not yet resolved. Options:

- Always drop (simplest; the reader can scan up).
- Drop unless the LDA is more than `N` instructions before the JSR
  (analytics-time heuristic).
- Always include (matches py8dis; loses the brevity gain).

Lean: always drop, on the principle that the LDA above is
always at most a few lines away in practice.

### 7.2 Provenance flag on `Comment`

py8dis distinguishes `auto_generated=True` so a driver can
selectively suppress hook output via `no_automatic_comment(addr)`.
Dasmos doesn't expose this flag; the duplicate-annotation warning
covers the symmetric "driver wants to override" case. Decision:
**defer the flag** until a real driver asks for selective
suppression. Adding it later is a one-attribute extension.

### 7.3 Multi-paragraph context

Some calls (OSGBPB in particular) have arguments rich enough that a
short banner block above the call site would communicate more
cleanly than a stack of inline-column fragments. That's a renderer
concern — punt to the markdown-comment / banner machinery rather
than overloading inline comments.
