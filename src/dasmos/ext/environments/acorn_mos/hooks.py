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

The state-tracker design (see ``dasmos.core.cpu_state`` +
``Nmos6502Cpu.update_state``) preserves the previous-load-imm
chain across stores and other-register-touching instructions,
so patterns like ``LDA #imm ; STA somewhere ; LDX #other ; JSR
osbyte`` still resolve — strictly more capable than a simple
backward-peek heuristic.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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


def _analyzer_for(enum: dict[int, str], reg: str = "a"):
    """Build a post-trace JSR analyzer that reads ``state.<reg>``
    (the CPU state IMMEDIATELY BEFORE the JSR) to find the last
    immediate load to that register. If the value is in ``enum``
    AND we know the source-instruction address, register the
    constant + auto-expression.

    ``reg`` defaults to ``"a"`` (the OSBYTE / OSWORD / OSFIND /
    OSFILE / OSGBPB convention). Future analyzers for OS calls
    that take their argument in X or Y just pass ``reg="x"``.
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


osfind_analyzer = _analyzer_for(OSFIND_ENUM)
osfile_analyzer = _analyzer_for(OSFILE_ENUM)
osgbpb_analyzer = _analyzer_for(OSGBPB_ENUM)


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


# OSEVEN takes an event number in Y.
oseven_analyzer = _analyzer_for(EVENT_ENUM, reg="y")
