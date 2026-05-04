"""Subroutine hooks: trace-time callbacks attached to specific JSR
targets.

A *subroutine hook* is a callable a driver registers via
:meth:`dasmos.disassembler.Disassembler.hook_subroutine`. The trace
loop fires it whenever it processes a JSR whose target address has a
hook. The hook examines (and potentially classifies) the bytes
following the JSR and returns the binary address where execution
continues — often *not* the byte right after the JSR.

The canonical use case is the "inline string" calling convention,
where a subroutine prints a string laid out in the instruction
stream right after the JSR. Without a hook, the trace would attempt
to disassemble the string as instructions; with a hook, the bytes are
classified as a String classification and the trace resumes at the
right place.

Hook signature::

    def hook(disassembler, jsr_binary_addr) -> int

- ``disassembler`` is the active :class:`Disassembler` (so the hook
  can call ``d.string(...)``, ``d.byte(...)``, etc.).
- ``jsr_binary_addr`` is the binary address of the JSR opcode byte.
- The return value is the binary address where the trace continues.

This module ships the most common hooks; drivers can also register
their own callables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.core.classification import String

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


def stringhi_hook(d: "Disassembler", jsr_binary_addr: int) -> int:
    """Classify the bytes after a JSR as a string terminated by the
    first byte with bit 7 set; trace continues at the terminator.

    The terminator byte is *not* included in the string classification
    — it falls through to the trace loop as an opcode (typically a
    1-byte NOP whose bit-7-set encoding makes it both a valid string
    terminator and a no-op instruction).

    Suitable for the Acorn / BBC ``print_embedded_text`` idiom (called
    via ``JSR &FE98`` in the 6502 Tube Client ROM).
    """
    string_start = jsr_binary_addr + 3
    addr = string_start
    # Walk forward until we hit a byte with bit 7 set (the terminator)
    # or run off the loaded range. Bounded by the address space size as
    # a safety net.
    limit = d.cpu.address_space_size
    while addr < limit:
        if not d.memory.is_loaded(addr):
            break
        if d.memory.get_u8(addr) & 0x80:
            break
        addr += 1
    length = addr - string_start
    if length > 0:
        # Convert binary → runtime addr for the public API. With no
        # active move, b2r is the identity, but threading it through
        # keeps the hook correct under relocation too.
        from dasmos.core.memory import BinaryAddr
        runtime_start = int(d.moves.b2r(BinaryAddr(string_start)))
        d.string(runtime_start, length)
    # Trace continues at the terminator address — it'll be classified
    # as an opcode by the normal trace loop.
    return addr


def stringz_hook(d: "Disassembler", jsr_binary_addr: int) -> int:
    """Classify the bytes after a JSR as a NUL-terminated string;
    trace continues at the byte right after the NUL.

    Mirror of :func:`stringhi_hook` for the inline-NUL-terminated
    convention used by Acorn ANFS's error-message routines (e.g.
    ``JSR error_inline`` followed by ``"<text>", 0``). The NUL
    terminator IS included in the classified string region.
    """
    from dasmos.core.memory import BinaryAddr
    string_start = jsr_binary_addr + 3
    runtime_start = int(d.moves.b2r(BinaryAddr(string_start)))
    # ``d.stringz`` walks to the NUL inclusively and returns the
    # runtime address right after it. Convert back to a binary
    # address for the trace return value.
    next_runtime = d.stringz(runtime_start)
    return int(d.moves.r2b_checked(next_runtime).binary_addr)
