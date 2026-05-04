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
directly. When it doesn't, the comment stays generic:

```
KNOWN A=&40:    jsr osfind                   ; open file for input
KNOWN A=&80:    jsr osfind                   ; open file for output
KNOWN A=&C0:    jsr osfind                   ; open file for update
KNOWN A=&00:    jsr osfind                   ; close one or all files
UNKNOWN:        jsr osfind                   ; open or close file
```

The unknown case never needs the `(A=...)` literal because there's
no known value to reference.

### 3.5 Enum-name lookup

When a register's value is a well-known enum (event numbers, OSBYTE
action codes), embed the enum name in the comment via `:`:

```
GOOD: generate event: vsync
GOOD: generate event: paged-rom-changed
GOOD: generate event (unknown)
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
    jsr oswrsc                               ; write byte to screen
```

### OSRDSC (read byte from screen / paged ROM)

```
    ldy #&80                                 ; paged ROM number
    jsr osrdsc                               ; read byte from paged ROM
    sta tmp                                  ; → byte read
```

### OSEVEN (generate event)

```
KNOWN event:
    ldy #&04                                 ; event: vsync
    jsr oseven                               ; generate event: vsync

UNKNOWN event:
    jsr oseven                               ; generate event Y
```

When Y is statically known the JSR comment names the event; when Y
is dynamic the call falls back to the generic form and there's no
LDY-side comment.

### OSFIND (open / close file)

| A         | LDA comment                        | JSR comment                |
|-----------|------------------------------------|----------------------------|
| `&00`     | (no LDA comment — A=0)             | `close one or all files`   |
| `&00`+Y=0 | (no LDA comment)                   | `close all files`          |
| `&40`     | `mode: input` *(or just omit)*     | `open file for input`      |
| `&80`     | `mode: output` *(or just omit)*    | `open file for output`     |
| `&C0`     | `mode: update` *(or just omit)*    | `open file for update`     |
| unknown   | `→ file open mode`                 | `open or close file`       |

Returns:

```
    sta file_handle                          ; → file handle (0 = failed)
```

### OSGBPB (transfer parameter-block read/write)

The OSGBPB calls take a parameter block addressed by XY. py8dis
attaches comments to *each field* of the parameter block. We do
the same but with our terser style:

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
