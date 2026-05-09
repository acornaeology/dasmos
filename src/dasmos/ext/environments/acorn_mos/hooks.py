"""OS-call analyzers for the ``acorn_mos`` Environment.

A post-trace JSR analyzer is a callable the Disassembler fires
AFTER trace + classification + CPU-state computation, when it
encounters a ``JSR`` whose target matches the registered runtime
address. For OS calls (``OSBYTE`` / ``OSWORD`` / …) the analyzer
inspects the CPU state IMMEDIATELY BEFORE the JSR — specifically
the ``previous_load_imm_addr`` for register A — to find the most-
recent ``LDA #imm`` that set up the call, then:

1. Registers a :meth:`Disassembler.constant` for the (value, name)
   pair so the JSON ``constants`` section + the asm equate table
   surface the symbolic name.
2. Registers an auto-expression (:meth:`Disassembler.expr`) at
   the LDA's immediate-operand byte so the rendered listing reads
   ``lda #osbyte_<name>`` instead of ``lda #&xx``.
3. Optionally attaches an inline auto-comment at the JSR call
   site naming what the call does (``open file for input``,
   ``generate event: vsync``, …). The wording follows the style
   guide at ``docs/design/auto-comment-style.md``.

The state-tracker design (see ``dasmos.core.cpu_state`` +
``Nmos6502Cpu.update_state``) preserves the previous-load-imm
chain across stores and other-register-touching instructions,
so patterns like ``LDA #imm ; STA somewhere ; LDX #other ; JSR
osbyte`` still resolve — strictly more capable than a simple
backward-peek heuristic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.core.annotations import Align
from dasmos.core.format_hint import FormatHint
from dasmos.core.memory import BinaryAddr
from dasmos.ext.environments.acorn_mos.enums import (
    EVENT_ENUM,
    INKEY_ENUM,
    OSARGS_INLINE,
    OSARGS_POST_CALL_TABLES,
    OSBYTE_DESCRIPTIONS,
    OSBYTE_ENUM,
    OSBYTE_POST_CALL_DESCRIPTIONS,
    OSBYTE_POST_CALL_TABLES,
    OSBYTE_X_SECONDARY_ENUMS,
    OSBYTE_X_VALUE_DESCRIPTIONS,
    OSFILE_ENUM,
    OSFIND_ENUM,
    OSGBPB_ENUM,
    OSWORD_DESCRIPTIONS,
    OSWORD_ENUM,
)


# OSBYTE actions that scan / wait for a specific physical key whose
# scan code arrives in X as ``(255 - inkey_key_<name>) EOR 128``:
#
#   &79  ``osbyte_scan_keyboard``   — scan keyboard for one key
#   &81  ``osbyte_inkey``           — INKEY (read keyboard with time-limit)
#
# Both have other modes too — &79 with X<&80 reads a key matrix
# row; &81 with X+Y as a positive 16-bit time limit waits for any
# key. The INKEY hint should only register when X has its high bit
# set, signalling "negative scan code".
OSBYTE_INKEY_DISPATCH_VALUES = frozenset({0x79, 0x81})


def _detect_inkey_pattern(a_value: int, state_before_jsr) -> tuple[str, int] | None:
    """If the call is an INKEY-mode keyboard scan / test, return
    ``(inkey_name, inkey_key_byte)`` — the named INKEY symbol the
    LDX byte decodes to plus the unsigned-byte form (e.g.
    ``("inkey_key_ctrl", 254)``). Returns ``None`` when this isn't
    an INKEY pattern.

    A pattern fires only for OSBYTE &79 / &81 when X has its high
    bit set AND ``(255 - X) EOR 128`` resolves to a named entry in
    :data:`INKEY_ENUM`. Anything else (mismatched action, X<&80,
    or a high-bit byte that doesn't decode) is left to the generic
    OSBYTE handling.
    """
    if a_value not in OSBYTE_INKEY_DISPATCH_VALUES:
        return None
    x = state_before_jsr.x
    if x.value is None or x.previous_load_imm_addr is None:
        return None
    if not (x.value & 0x80):
        return None
    inkey_key = (255 - x.value) ^ 0x80
    inkey_name = INKEY_ENUM.get(inkey_key)
    if inkey_name is None:
        return None
    return inkey_name, inkey_key


def _inkey_inline_text(inkey_name: str) -> str:
    """Build the JSR-site inline-comment text for an INKEY pattern.

    Strips the ``inkey_key_`` prefix and replaces underscores with
    spaces, keeping ``key`` in the phrase so the reading flows for
    every name in :data:`INKEY_ENUM`:

    - ``inkey_key_ctrl``           → ``Test for ctrl key pressed``
    - ``inkey_key_keypad_4``       → ``Test for keypad 4 key pressed``
    - ``inkey_key_left_square_bracket`` →
      ``Test for left square bracket key pressed``

    The phrasing matches py8dis-fork's ``"Test for ... key pressed"``
    so this contributes the same vocabulary tokens (``test``, ``key``,
    ``pressed``) to the comment-vocab parity oracle.
    """
    bare = inkey_name[len("inkey_key_"):].replace("_", " ")
    return f"Test for {bare} key pressed"

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# -- Inline-comment tables (per docs/design/auto-comment-style.md) --

# OSFIND / OSFILE / OSGBPB / OSEVEN inline-comment tables. Each
# entry's text is prefixed with the call name (``osfind: ``,
# ``osfile: ``, etc.) for the same reason OSBYTE / OSWORD comments
# carry their prefix: the prefix anchors the action description in
# the OS-call context. Without it, a fragment like "close one or
# all files" reads ambiguously when scanning the right-hand
# column; with it, the call name reads first and the action
# description grounds in that.
OSFIND_INLINE: dict[int, str] = {
    0x00: "osfind: close one or all files",
    0x40: "osfind: open file for input",
    0x80: "osfind: open file for output",
    0xc0: "osfind: open file for update",
}

OSFILE_INLINE: dict[int, str] = {
    0x00: "osfile: save block of memory",
    0x01: "osfile: write catalogue info",
    0x02: "osfile: write load address",
    0x03: "osfile: write execution address",
    0x04: "osfile: write attributes",
    0x05: "osfile: read catalogue info",
    0x06: "osfile: delete file",
    0x07: "osfile: create empty file",
    0xff: "osfile: load file",
}

OSGBPB_INLINE: dict[int, str] = {
    0x01: "osgbpb: write bytes (at given pointer)",
    0x02: "osgbpb: append bytes (at current pointer)",
    0x03: "osgbpb: read bytes (at given pointer)",
    0x04: "osgbpb: read bytes (at current pointer)",
    0x05: "osgbpb: read title, boot option, drive",
    0x06: "osgbpb: read current directory + drive",
    0x07: "osgbpb: read current library + drive",
    0x08: "osgbpb: read filenames in current directory",
}

# OSEVEN: terse human name for each event number, used to build
# ``oseven: <event-name>`` at the JSR site. The ``oseven: `` prefix
# already conveys "generate event"; the body just identifies which
# event.
EVENT_NAMES_TERSE: dict[int, str] = {
    0: "output buffer empty",
    1: "input buffer full",
    2: "character into input buffer",
    3: "ADC conversion complete",
    4: "vsync",
    5: "interval timer reached zero",
    6: "escape detected",
    7: "RS423 error",
    8: "network error",
    9: "user event",
}


# OSBYTE / OSWORD inline-comment overrides. The default strategy is
# to derive the inline-comment text mechanically from the enum name
# by stripping the ``osbyte_`` / ``osword_`` prefix and replacing
# underscores with spaces — most enum names produce a sensible
# reading-fragment that way (``osbyte_read_os_version`` →
# ``read os version``, ``osbyte_select_input_stream`` →
# ``select input stream``). The override table catches the few
# entries where the mechanical strip produces something awkward or
# misleading (e.g. ``osbyte_vsync`` mechanically becomes ``vsync``,
# but the action *waits for* vsync — the imperative reading is
# important).
OSBYTE_INLINE_OVERRIDES: dict[int, str] = {
    0x13: "wait for vsync",
}

OSWORD_INLINE_OVERRIDES: dict[int, str] = {
    0x05: "read I/O memory",
    0x06: "write I/O memory",
    0x0e: "read CMOS clock",
    0x0f: "write CMOS clock",
}


def _derive_inline_body_from_enum_name(
    enum_name: str,
    prefix: str,
) -> str:
    """Build the action-description body of an inline comment from
    an enum entry's name by stripping ``<prefix>_`` and replacing
    underscores with spaces. Returns just the body — the call-name
    prefix (``osbyte:`` / ``osword:``) is added separately by
    :func:`_build_inline_table`.
    """
    head = f"{prefix}_"
    body = enum_name[len(head):] if enum_name.startswith(head) else enum_name
    return body.replace("_", " ")


def _build_inline_table(
    enum: dict[int, str],
    prefix: str,
    overrides: dict[int, str],
    descriptions: dict[int, str] | None = None,
) -> dict[int, str]:
    """Build a value→inline-comment table from an OS-call enum.

    Three sources, applied in priority order (highest first):

    1. ``descriptions`` (when supplied): a long, self-anchored phrase
       like ``Read top of operating system RAM address (OSHWM)``.
       Used verbatim — the call name is already named on the
       preceding ``LDA #osbyte_<name>`` line via the registered
       constant, so a leading ``osbyte:`` prefix here would only
       duplicate context.
    2. ``overrides``: a short imperative phrase that doesn't match
       the mechanical strip (e.g. ``vsync`` → ``wait for vsync``).
       Prefixed with ``<prefix>: ``.
    3. Mechanical strip of the enum name (``osbyte_select_input_stream``
       → ``select input stream``). Prefixed with ``<prefix>: ``.

    Improvement over py8dis-fork: there, the OSBYTE descriptions
    live inside a 1500-line ``osbyte_action`` if/elif chain. dasmos
    expresses the same content as a pure data table
    (``OSBYTE_DESCRIPTIONS`` / ``OSWORD_DESCRIPTIONS`` in
    :mod:`enums`) — easier to scan, easier to test, and shared with
    future per-X-value lookup analysers.
    """
    out: dict[int, str] = {}
    for value, name in enum.items():
        if descriptions is not None and value in descriptions:
            out[value] = descriptions[value]
            continue
        if value in overrides:
            body = overrides[value]
        else:
            body = _derive_inline_body_from_enum_name(name, prefix)
        out[value] = f"{prefix}: {body}"
    return out


OSBYTE_INLINE = _build_inline_table(
    OSBYTE_ENUM, "osbyte", OSBYTE_INLINE_OVERRIDES,
    descriptions=OSBYTE_DESCRIPTIONS,
)
OSWORD_INLINE = _build_inline_table(
    OSWORD_ENUM, "osword", OSWORD_INLINE_OVERRIDES,
    descriptions=OSWORD_DESCRIPTIONS,
)


def _attach_inline_jsr_comment(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    text: str,
) -> None:
    """Attach an analyser-driven inline comment at a JSR/JMP site.

    Stacks alongside any driver-supplied inline comment at the same
    address — both render in the asm output (joined with two spaces
    by the renderer's per-classification gather). This matches
    py8dis-fork's behaviour where the driver writes a partial
    comment (``OSARGS: set file pointer``) and the OS-call
    auto-comment appends specifics (``Write sequential file
    pointer``) to land on one line.

    Skips when an annotation with the EXACT same text already exists
    (idempotent re-runs) or when any annotation at the address sets
    ``suppresses_auto=True`` (driver crowd-out).

    Marks the new comment ``auto_generated=True`` so the
    duplicate-comment warning in :class:`AnnotationStore` (intended
    to flag authoring bugs where one driver call overwrites another)
    suppresses for this case — analyser stacking is intentional.
    """
    if disassembler.annotations.is_auto_suppressed_at(jsr_binary_addr):
        return
    runtime_addr = int(disassembler.moves.b2r(BinaryAddr(jsr_binary_addr)))
    from dasmos.core.annotations import Comment
    existing = disassembler.annotations.get_for_align(
        jsr_binary_addr, Align.INLINE,
    )
    for ann in existing:
        if isinstance(ann, Comment) and ann.text == text:
            return  # already attached — idempotent re-run
    disassembler.annotations.add(
        BinaryAddr(jsr_binary_addr),
        Comment(text=text, align=Align.INLINE, auto_generated=True),
    )


def _analyzer_for(
    enum: dict[int, str],
    reg: str = "a",
    *,
    inline_for_value: dict[int, str] | None = None,
):
    """Build a post-trace JSR analyzer that reads ``state.<reg>``
    (the CPU state IMMEDIATELY BEFORE the JSR) to find the last
    immediate load to that register. If the value is in ``enum``
    AND we know the source-instruction address, register the
    constant + auto-expression.

    ``reg`` defaults to ``"a"`` (the OSBYTE / OSWORD / OSFIND /
    OSFILE / OSGBPB convention). Future analyzers for OS calls
    that take their argument in X or Y just pass ``reg="x"``.

    ``inline_for_value`` (optional) is a ``value → comment`` table.
    When the analyzer recognises the value AND the table has a
    matching entry, an inline auto-comment is attached at the JSR
    call site. Style is per
    ``docs/design/auto-comment-style.md``.
    """

    def analyzer(
        disassembler: "Disassembler",
        jsr_binary_addr: int,
        state_before_jsr,
    ) -> None:
        reg_state = getattr(state_before_jsr, reg, None)
        if reg_state is None:
            return
        value = reg_state.value
        load_imm_addr = reg_state.previous_load_imm_addr
        if value is None or load_imm_addr is None:
            return
        name = enum.get(value)
        if name is None:
            return
        if not any(
            c.name == name and c.value == value
            for c in disassembler.constants
        ):
            disassembler.constant(value, name)
        # Auto-expr at the LDA's immediate-operand byte (one past
        # the LDA opcode itself). Respect any pre-existing
        # expression (driver overrides win).
        operand_addr = load_imm_addr + 1
        if disassembler.expressions.get_or_none(operand_addr) is None:
            disassembler.expr(operand_addr, name)
        # Inline auto-comment at the JSR site, if the per-call
        # table provided one.
        if inline_for_value is not None:
            inline_text = inline_for_value.get(value)
            if inline_text is not None:
                _attach_inline_jsr_comment(
                    disassembler, jsr_binary_addr, inline_text,
                )

    return analyzer


def osword_analyzer(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    state_before_jsr,
) -> None:
    """OSWORD analyzer with XY parameter-block address recognition.

    Two substitutions:

    1. **A → OSWORD_ENUM** — same as the generic analyzer, turns
       ``lda #&05`` into ``lda #osword_read_io_memory``.
    2. **(X, Y) form a labelled address** — when X holds the lo
       byte and Y holds the hi byte of an address that's been
       given a name (typically the OSWORD parameter block), register
       ``<(label)`` / ``>(label)`` expressions at the LDX / LDY
       operand bytes so they render as ``ldx #<(myblock)`` /
       ``ldy #>(myblock)``.
    """
    # Primary: A → OSWORD_ENUM
    a = state_before_jsr.a
    if a.value is not None and a.previous_load_imm_addr is not None:
        a_name = OSWORD_ENUM.get(a.value)
        if a_name is not None:
            if not any(
                c.name == a_name and c.value == a.value
                for c in disassembler.constants
            ):
                disassembler.constant(a.value, a_name)
            a_operand = a.previous_load_imm_addr + 1
            if disassembler.expressions.get_or_none(a_operand) is None:
                disassembler.expr(a_operand, a_name)
            # Inline auto-comment at the JSR site.
            inline_text = OSWORD_INLINE.get(a.value)
            if inline_text is not None:
                _attach_inline_jsr_comment(
                    disassembler, jsr_binary_addr, inline_text,
                )

    # Secondary: (X, Y) → labelled address.
    _maybe_register_xy_address(disassembler, state_before_jsr)


def _format_value_table(
    register: str,
    intro: str,
    values: dict[int, str],
) -> str:
    """Render a value-table as Markdown.

    Output layout:
        <intro>:

        | <REG> | Meaning |
        |-------|---------|
        | 0     | …       |
        | 1     | …       |

    The asm renderer flattens the Markdown via mistletoe so the
    asm comment shows a padded pipe-table; the JSON renderer keeps
    the source markdown verbatim so the site generator can render
    a real HTML table.
    """
    rows = sorted(values.items())
    lines = [f"{intro}:", ""]
    lines.append(f"| {register.upper()} | Meaning |")
    lines.append("|---|---|")
    for value, desc in rows:
        lines.append(f"| {value} | {desc} |")
    return "\n".join(lines)


def _attach_post_call_table(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    table_specs: dict[str, tuple[str, dict[int, str]]],
) -> None:
    """Emit one or more value-table comments as a preamble to the
    JSR/JMP. Each spec maps a register letter to ``(intro, values)``;
    each becomes a separate standalone Markdown-table comment attached
    at the JSR site with ``Align.BEFORE_LINE`` (between any label and
    the call opcode), so the table reads as a top-down preamble:
    setup → "here's what comes back" → call → consumer.

    Driver-supplied annotations at the JSR site are respected. If any
    annotation at the JSR address has ``suppresses_auto=True``, the
    auto-table is skipped entirely (driver overrides win); otherwise
    duplicates of the exact same text are short-circuited so re-runs
    are idempotent.
    """
    from dasmos.core.annotations import Comment
    classification = disassembler.classifications.get_classification(
        jsr_binary_addr,
    )
    from dasmos.cpu import Opcode
    if not isinstance(classification, Opcode):
        return
    if disassembler.annotations.is_auto_suppressed_at(jsr_binary_addr):
        return
    existing = disassembler.annotations.get_for_align(
        jsr_binary_addr, Align.BEFORE_LINE,
    )
    existing_texts = {
        a.text for a in existing if isinstance(a, Comment)
    }
    for register, (intro, values) in sorted(table_specs.items()):
        if not values:
            continue
        text = _format_value_table(register, intro, values)
        if text in existing_texts:
            continue
        disassembler.annotations.add(
            BinaryAddr(jsr_binary_addr),
            Comment(text=text, align=Align.BEFORE_LINE, auto_generated=True),
        )
        existing_texts.add(text)


def _attach_post_call_descriptions(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    descriptions: dict[str, str],
) -> None:
    """Attach an inline comment at the binary address immediately
    after the JSR/JMP for each register named in ``descriptions``.

    For OSBYTE calls that return values in registers (e.g. OSBYTE
    &86 returns POS in X and VPOS in Y), py8dis attaches an inline
    comment at the next instruction that READS that register — its
    "next-use of X" tracker. dasmos's simplified rule attaches at
    the first byte after the call site, which is where py8dis's
    next-use almost always lands in real Acorn ROM code (the very
    next instruction typically consumes the returned register).

    Multiple register descriptions for one call get joined with
    ``" / "`` so they live on a single inline comment, e.g.
    ``X is the horizontal text position ('POS') / Y is the vertical
    text position ('VPOS')`` — readable as one annotation about
    "what the registers contain after the call".
    """
    # Compute the next-instruction binary address. JSR is 3 bytes
    # (opcode + abs16); JMP abs is also 3 bytes. The call site's
    # opcode at jsr_binary_addr is one of those.
    classification = disassembler.classifications.get_classification(
        jsr_binary_addr,
    )
    from dasmos.cpu import Opcode
    if not isinstance(classification, Opcode):
        return
    # Driver crowd-out: skip when a `suppresses_auto=True` annotation
    # exists at either the JSR site (where the driver thinks about
    # the call) or the consumer-instruction site (where this auto
    # comment would land).
    next_addr = jsr_binary_addr + classification.length()
    if (
        disassembler.annotations.is_auto_suppressed_at(jsr_binary_addr)
        or disassembler.annotations.is_auto_suppressed_at(next_addr)
    ):
        return
    # Skip if any inline comment is already there (driver-provided
    # comments win).
    existing = disassembler.annotations.get_for_align(
        next_addr, Align.INLINE,
    )
    from dasmos.core.annotations import Comment
    for ann in existing:
        if isinstance(ann, Comment):
            return
    # Stable ordering for joinery: A first (rare), then X, then Y.
    parts: list[str] = []
    for reg in ("a", "x", "y"):
        text = descriptions.get(reg)
        if text is not None:
            parts.append(text)
    if not parts:
        return
    runtime_addr = int(disassembler.moves.b2r(BinaryAddr(next_addr)))
    disassembler.comment(runtime_addr, " / ".join(parts), align=Align.INLINE)


def _maybe_register_xy_address(disassembler, state) -> None:
    """If (X, Y) immediately-loaded values form the address of a
    labelled location, register ``<(label)`` / ``>(label)`` at the
    LDX / LDY operand bytes. Used by OSWORD-style analyzers where
    XY carries a parameter-block address.
    """
    x = state.x
    y = state.y
    if x.value is None or x.previous_load_imm_addr is None:
        return
    if y.value is None or y.previous_load_imm_addr is None:
        return
    target = (y.value << 8) | x.value
    label = disassembler.labels.get_label(target)
    if label is None:
        return
    # Use the first explicitly-registered name (skip expression
    # aliases; they'd produce nested ``<(<(foo)>)`` mess).
    name = None
    for name_list in label.explicit_names.values():
        for explicit in name_list:
            name = explicit.text
            break
        if name is not None:
            break
    if name is None:
        return
    x_operand = x.previous_load_imm_addr + 1
    y_operand = y.previous_load_imm_addr + 1
    if disassembler.expressions.get_or_none(x_operand) is None:
        disassembler.expr(x_operand, f"<({name})")
    if disassembler.expressions.get_or_none(y_operand) is None:
        disassembler.expr(y_operand, f">({name})")


osfind_analyzer = _analyzer_for(OSFIND_ENUM, inline_for_value=OSFIND_INLINE)
osfile_analyzer = _analyzer_for(OSFILE_ENUM, inline_for_value=OSFILE_INLINE)
osgbpb_analyzer = _analyzer_for(OSGBPB_ENUM, inline_for_value=OSGBPB_INLINE)


def osbyte_analyzer(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    state_before_jsr,
) -> None:
    """OSBYTE analyzer with SECONDARY enum lookup on X.

    Same as the generic ``_analyzer_for(OSBYTE_ENUM)`` for the A-
    register substitution (``lda #&7c`` → ``lda #osbyte_clear_escape``),
    but ALSO checks if the OSBYTE action takes an enumerated value
    in X (event for &0D/&0E, buffer for &15/&8A/&91/&98/&99). When
    so, looks up X's previous-immediate-load address in the
    secondary enum and substitutes that too.
    """
    # Primary: A → OSBYTE_ENUM
    a = state_before_jsr.a
    if a.value is not None and a.previous_load_imm_addr is not None:
        a_value = a.value
        a_name = OSBYTE_ENUM.get(a_value)
        if a_name is not None:
            if not any(
                c.name == a_name and c.value == a_value
                for c in disassembler.constants
            ):
                disassembler.constant(a_value, a_name)
            a_operand = a.previous_load_imm_addr + 1
            if disassembler.expressions.get_or_none(a_operand) is None:
                disassembler.expr(a_operand, a_name)
            # Inline auto-comment at the JSR site. Precedence
            # (highest first):
            #   1. INKEY-aware phrasing for OSBYTE &79 / &81 when
            #      the X byte decodes to a named scan code — names
            #      the specific key (``Test for ctrl key pressed``).
            #   2. Per-X-value descriptions for OSBYTEs with a
            #      small enumerated X (``OSBYTE_X_VALUE_DESCRIPTIONS``).
            #   3. Generic OSBYTE description (``OSBYTE_INLINE``).
            inkey_pattern = _detect_inkey_pattern(a_value, state_before_jsr)
            inline_text = None
            if inkey_pattern is not None:
                inkey_name, _ = inkey_pattern
                inline_text = _inkey_inline_text(inkey_name)
            if inline_text is None:
                x_value_table = OSBYTE_X_VALUE_DESCRIPTIONS.get(a_value)
                if x_value_table is not None:
                    x = state_before_jsr.x
                    if x.value is not None:
                        inline_text = x_value_table.get(x.value)
            if inline_text is None:
                inline_text = OSBYTE_INLINE.get(a_value)
            if inline_text is not None:
                _attach_inline_jsr_comment(
                    disassembler, jsr_binary_addr, inline_text,
                )
            # Secondary: for OSBYTE actions with an X-register
            # enumerated argument, substitute that too.
            x_enum = OSBYTE_X_SECONDARY_ENUMS.get(a_value)
            if x_enum is not None:
                x = state_before_jsr.x
                if x.value is not None and x.previous_load_imm_addr is not None:
                    x_name = x_enum.get(x.value)
                    if x_name is not None:
                        if not any(
                            c.name == x_name and c.value == x.value
                            for c in disassembler.constants
                        ):
                            disassembler.constant(x.value, x_name)
                        x_operand = x.previous_load_imm_addr + 1
                        if disassembler.expressions.get_or_none(x_operand) is None:
                            disassembler.expr(x_operand, x_name)
            # Post-call: attach descriptive inline comments at the
            # next byte after the JSR/JMP for each register named in
            # OSBYTE_POST_CALL_DESCRIPTIONS[a_value]. py8dis tracks
            # "next-use of register" precisely; dasmos uses the
            # simpler "first opcode after the call" anchor (matches
            # py8dis's output for the cases in our migration since
            # the immediately-following instruction usually IS the
            # register-using consumer).
            post_call = OSBYTE_POST_CALL_DESCRIPTIONS.get(a_value)
            if post_call is not None:
                _attach_post_call_descriptions(
                    disassembler, jsr_binary_addr, post_call,
                )
            # Post-call value-tables: when the OSBYTE returns a
            # register from a small enumeration (OS-version, …),
            # emit a Markdown table at the byte after the call site
            # listing every possible value.
            post_call_table = OSBYTE_POST_CALL_TABLES.get(a_value)
            if post_call_table is not None:
                _attach_post_call_table(
                    disassembler, jsr_binary_addr, post_call_table,
                )
            # INKEY pattern registration: when the detection above
            # fired, register the unsigned-form constant (so the
            # equate table gets ``inkey_key_<name> = <unsigned>``)
            # and tag the LDX's immediate-operand byte with
            # FormatHint.INKEY so the renderer emits the symbolic
            # ``(255 - inkey_key_<name>) EOR 128`` form. The
            # unsigned constant value is what makes that expression
            # reduce cleanly to a single byte under beebasm's
            # evaluation — see ``_render_inkey_immediate`` for the
            # encoding rationale.
            if inkey_pattern is not None:
                inkey_name, inkey_key = inkey_pattern
                if not any(
                    c.name == inkey_name and c.value == inkey_key
                    for c in disassembler.constants
                ):
                    disassembler.constant(inkey_key, inkey_name)
                x_operand = state_before_jsr.x.previous_load_imm_addr + 1
                if disassembler.expressions.get_or_none(x_operand) is None:
                    disassembler.format_hint(x_operand, FormatHint.INKEY)


# OSEVEN takes an event number in Y. The JSR-site comment is
# ``oseven: <terse-name>`` — the prefix anchors the call name and
# the body identifies which event.
oseven_analyzer = _analyzer_for(
    EVENT_ENUM,
    reg="y",
    inline_for_value={
        n: f"oseven: {terse}"
        for n, terse in EVENT_NAMES_TERSE.items()
    },
)


def osargs_analyzer(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    state_before_jsr,
) -> None:
    """OSARGS analyzer with (A, Y) joint dispatch.

    OSARGS (&FFDA) takes the action in A and a file handle (or 0
    for "no file" / "all files") in Y. Most A values fork further
    on Y == 0 vs Y != 0 — e.g. A=0 Y=0 returns the filing-system
    number in A, while A=0 Y!=0 reads a sequential file pointer
    into the zero-page address X. The :data:`OSARGS_INLINE` table
    encodes the per-(A, Y) inline phrasing.

    Two side-effects when the dispatch resolves cleanly:

    1. **Inline auto-comment** at the JSR/JMP site — appends to any
       existing driver-supplied inline comment (the analyser-driven
       text is marked ``auto_generated`` so the duplicate-warning
       guard in :class:`AnnotationStore` is skipped).
    2. **Post-call value-table** at the byte after the call when
       the call's documented result is a small enum
       (only A=0 Y=0 → filing-system number for now).
    """
    a = state_before_jsr.a
    y = state_before_jsr.y
    if a.value is None:
        return
    a_table = OSARGS_INLINE.get(a.value)
    if a_table is None:
        return
    # Pick the most-specific Y match; fall back to None bucket.
    inline_text = None
    if y.value is not None:
        inline_text = a_table.get(y.value)
    if inline_text is None:
        inline_text = a_table.get(None)
    if inline_text is not None:
        _attach_inline_jsr_comment(
            disassembler, jsr_binary_addr, inline_text,
        )
    # Post-call value-tables (currently only the FS-number table
    # for A=0 Y=0).
    if y.value is not None:
        post_call_table = OSARGS_POST_CALL_TABLES.get((a.value, y.value))
        if post_call_table is not None:
            _attach_post_call_table(
                disassembler, jsr_binary_addr, post_call_table,
            )
