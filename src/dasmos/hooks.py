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


def _scan_to_bit7_terminator(
    d: "Disassembler", string_start: int,
) -> tuple[int, bool]:
    """Walk forward from ``string_start`` to the first byte with bit 7
    set (the string terminator).

    Returns ``(stop_addr, terminated)`` where ``terminated`` is True iff
    the walk stopped on a real bit-7 terminator, and False if it ran off
    the loaded range or hit the address-space limit (an unterminated
    string). The walk is bounded by the address-space size as a safety
    net.
    """
    addr = string_start
    limit = d.cpu.address_space_size
    while addr < limit:
        if not d.memory.is_loaded(addr):
            return addr, False
        if d.memory.get_u8(addr) & 0x80:
            return addr, True
        addr += 1
    return addr, False


def _classify_string(d: "Disassembler", string_start: int, length: int) -> None:
    """Classify ``length`` bytes from ``string_start`` (binary addr) as
    a String, converting to the runtime address the public API expects.

    With no active move, b2r is the identity, but threading it through
    keeps the hook correct under relocation too.
    """
    from dasmos.core.memory import BinaryAddr
    runtime_start = int(d.moves.b2r(BinaryAddr(string_start)))
    d.string(runtime_start, length)


def stringhi_hook(d: "Disassembler", jsr_binary_addr: int) -> int:
    """Classify the bytes after a JSR as a string terminated by the
    first byte with bit 7 set; trace continues **at** the terminator.

    This is the *terminator-as-NOP* convention: the bit-7 terminator is
    a separate trailing byte that the print routine returns to, so it is
    *not* included in the string classification — it falls through to the
    trace loop as an opcode (typically a 1-byte NOP whose bit-7-set
    encoding makes it both a valid string terminator and a no-op).

    Suitable for the Acorn / BBC ``print_embedded_text`` idiom (called
    via ``JSR &FE98`` in the 6502 Tube Client ROM).

    Contrast :func:`stringhi_skip_hook`, which treats the terminator as
    the final character of the string and resumes *after* it. The two
    conventions are indistinguishable from the bytes alone, and picking
    the wrong one is *silent* — round-trip verification still passes
    because no bytes change; only the instruction boundaries shift. Pick
    by reading the print routine: does it return to the terminator or to
    terminator+1?
    """
    string_start = jsr_binary_addr + 3
    stop, _terminated = _scan_to_bit7_terminator(d, string_start)
    length = stop - string_start
    if length > 0:
        _classify_string(d, string_start, length)
    # Trace continues at the terminator address — it'll be classified
    # as an opcode by the normal trace loop.
    return stop


def stringhi_skip_hook(d: "Disassembler", jsr_binary_addr: int) -> int:
    """Classify the bytes after a JSR as a string terminated by the
    first byte with bit 7 set; trace continues **after** the terminator.

    This is the *terminator-as-final-character* convention: the bit-7
    terminator is the last character of the string (printed with bit 7
    stripped) and the print routine consumes it, returning to
    terminator+1. The terminator IS included in the string
    classification and is *skipped* by the trace.

    Acorn ADFS 1.30's ``print_inline_string`` (&92A0) uses this: its
    strings end in ``&8D`` (``&0D | &80``, a trailing CR), and the
    routine computes its return as ``ptr + Y`` (Y = terminator offset)
    then ``RTS``.

    The bit-7 analogue of :func:`stringz_hook` (which does the same for a
    NUL terminator). Contrast :func:`stringhi_hook`, which leaves the
    terminator in the instruction stream and resumes *at* it. The choice
    between the two is *silent* — see that function's note.
    """
    string_start = jsr_binary_addr + 3
    stop, terminated = _scan_to_bit7_terminator(d, string_start)
    if terminated:
        # Terminator is the final char: classify it as part of the
        # string and resume past it.
        _classify_string(d, string_start, stop - string_start + 1)
        return stop + 1
    # Unterminated: same best-effort fallback as stringhi_hook.
    length = stop - string_start
    if length > 0:
        _classify_string(d, string_start, length)
    return stop


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
