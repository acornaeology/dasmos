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
from dasmos.core.memory import BinaryAddr
from dasmos.ext.environments.acorn_mos.enums import (
    EVENT_ENUM,
    OSBYTE_ENUM,
    OSBYTE_X_SECONDARY_ENUMS,
    OSFILE_ENUM,
    OSFIND_ENUM,
    OSGBPB_ENUM,
    OSWORD_ENUM,
)

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# -- Inline-comment tables (per docs/design/auto-comment-style.md) --

# OSFIND: action codes → terse JSR-site comment fragment.
OSFIND_INLINE: dict[int, str] = {
    0x00: "close one or all files",
    0x40: "open file for input",
    0x80: "open file for output",
    0xc0: "open file for update",
}

# OSFILE: action codes → terse JSR-site comment fragment.
OSFILE_INLINE: dict[int, str] = {
    0x00: "save block of memory",
    0x01: "write catalogue info",
    0x02: "write load address",
    0x03: "write execution address",
    0x04: "write attributes",
    0x05: "read catalogue info",
    0x06: "delete file",
    0x07: "create empty file",
    0xff: "load file",
}

# OSGBPB: action codes → terse JSR-site comment fragment.
OSGBPB_INLINE: dict[int, str] = {
    0x01: "write bytes (at given pointer)",
    0x02: "append bytes (at current pointer)",
    0x03: "read bytes (at given pointer)",
    0x04: "read bytes (at current pointer)",
    0x05: "read title, boot option, drive",
    0x06: "read current directory + drive",
    0x07: "read current library + drive",
    0x08: "read filenames in current directory",
}

# OSEVEN: terse human name for each event number, used to build
# ``generate event: <name>`` at the JSR site. Mirrors the long
# names in ``EVENT_ENUM`` but tighter for the inline column.
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
) -> dict[int, str]:
    """Build a value→inline-comment table from an OS-call enum.

    The default body is mechanically derived from the enum entry's
    name (strip ``<prefix>_``, underscores → spaces). Each entry is
    then prepended with ``<prefix>: `` so the rendered comment
    reads e.g. ``osbyte: select input stream`` — the call-name
    prefix anchors the action description in context (without it,
    a comment like "select input stream" floats free of the OS-
    call call-site and can be misread as part of surrounding code).

    The OSBYTE / OSWORD action vocabularies are large and varied
    enough that the prefix carries real information. Smaller
    enums whose action names are already self-anchored
    (``open file for input``, ``read filenames in current
    directory``) don't need this prefix and use a hand-crafted
    table instead.

    ``overrides`` takes precedence over the mechanical body, but
    the ``<prefix>: `` prepend still happens — write override
    bodies WITHOUT the prefix.
    """
    out: dict[int, str] = {}
    for value, name in enum.items():
        if value in overrides:
            body = overrides[value]
        else:
            body = _derive_inline_body_from_enum_name(name, prefix)
        out[value] = f"{prefix}: {body}"
    return out


OSBYTE_INLINE = _build_inline_table(
    OSBYTE_ENUM, "osbyte", OSBYTE_INLINE_OVERRIDES,
)
OSWORD_INLINE = _build_inline_table(
    OSWORD_ENUM, "osword", OSWORD_INLINE_OVERRIDES,
)


def _attach_inline_jsr_comment(
    disassembler: "Disassembler",
    jsr_binary_addr: int,
    text: str,
) -> None:
    """Attach a JSR-site inline comment if no existing inline
    annotation conflicts. Translates the binary address to runtime
    via the active-move stack so the comment routes to the right
    classification under relocation.

    The duplicate-annotation warning in :class:`AnnotationStore`
    will fire if the analyzer somehow attaches the same text twice
    or if a driver-supplied inline comment with the same text is
    already registered — both indicate a real authoring conflict.
    """
    runtime_addr = int(disassembler.moves.b2r(BinaryAddr(jsr_binary_addr)))
    # Skip if any inline comment is already at this address —
    # driver-supplied comments win over auto-generated ones.
    existing = disassembler.annotations.get_for_align(
        jsr_binary_addr, Align.INLINE,
    )
    for ann in existing:
        # Skip just for inline-comment duplicates; banner / xref
        # blocks at the same address are independent.
        from dasmos.core.annotations import Comment
        if isinstance(ann, Comment):
            return
    disassembler.comment(runtime_addr, text, align=Align.INLINE)


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
            # Inline auto-comment at the JSR site.
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


# OSEVEN takes an event number in Y. The JSR-site comment is
# ``generate event: <terse-name>`` per the style guide.
oseven_analyzer = _analyzer_for(
    EVENT_ENUM,
    reg="y",
    inline_for_value={
        n: f"generate event: {terse}"
        for n, terse in EVENT_NAMES_TERSE.items()
    },
)
