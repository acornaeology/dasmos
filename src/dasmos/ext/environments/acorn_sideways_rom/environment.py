"""Acorn sideways ROM environment — header layout, entry-point
detection, copyright/title strings.

A sideways ROM lives at &8000-&BFFF on the BBC Micro and starts with
a fixed-shape header that identifies the language/service entry
points and embeds a NUL-terminated title and copyright string. This
environment recognises that layout, registers the conventional names,
and seeds the trace from any entry point that's a ``JMP abs``.

Unlike :class:`AcornMosEnvironment` (which just registers labels)
this one **inspects loaded memory** at &8000 to decide what's where —
so it must be activated AFTER ``d.load(...)``::

    d = Disassembler.create(cpu="6502", environments=["acorn_mos"])
    d.load("rom.bin", 0x8000)
    d.use_environment("acorn_sideways_rom")    # NOT in the constructor
                                                # kwarg above

Layering: usually combined with ``acorn_mos`` (and eventually the
hardware environments). Calling order matters only when two
environments would otherwise overlap on the same address; otherwise
they compose freely.
"""

from typing import TYPE_CHECKING

from dasmos.environment import Environment
from dasmos.exceptions import DasmosError

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# 6502 ``JMP abs`` opcode — the magic byte at &8000 (and &8003) that
# tells the MOS the entry point is real code rather than 3 bytes of
# something else.
_JMP_ABS_OPCODE = 0x4c

# Fixed offsets from the ROM base address (&8000).
_LANGUAGE_ENTRY = 0x0000
_SERVICE_ENTRY = 0x0003
_ROM_TYPE = 0x0006
_COPYRIGHT_OFFSET = 0x0007
_BINARY_VERSION = 0x0008
_TITLE = 0x0009


class AcornSidewaysRomEnvironment(Environment):
    """Acorn sideways ROM environment.

    Recognises the standard sideways-ROM header at &8000:

    - ``rom_header``     (&8000)  — start of the header
    - ``language_entry`` (&8000)  — JMP to the language handler (if
                                    present); else 3 raw bytes
    - ``service_entry``  (&8003)  — JMP to the service handler (if
                                    present); else 3 raw bytes
    - ``rom_type``       (&8006)  — 1-byte ROM type bitmap
    - ``copyright_offset`` (&8007) — offset into the ROM at which the
                                     copyright string starts
                                     (rendered as ``copyright -
                                     rom_header``)
    - ``binary_version`` (&8008)  — 1-byte binary version
    - ``title``          (&8009)  — NUL-terminated ASCII title
    - ``version``        (after title, if there's room)
                                  — NUL-terminated ASCII version
    - ``copyright``      (&8000 + copyright_offset)
                                  — NUL-terminated copyright string

    Activated AFTER ``d.load(...)``::

        d.use_environment("acorn_sideways_rom")
    """

    def __init__(self, name: str = "acorn_sideways_rom", **kwargs):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        d = disassembler
        if not d.memory.is_loaded(0x8000):
            raise DasmosError(
                "acorn_sideways_rom needs ROM bytes loaded at &8000 "
                "— activate this environment AFTER d.load(...)"
            )
        d.label(0x8000, "rom_header")
        # Address-metadata comment, not user-authored content.
        # ``auto_generated=True`` keeps the dup-warning silent when a
        # driver attaches its own per-version banner at the same
        # address, and lets a driver fully replace this line by
        # attaching ``d.comment(0x8000, ..., suppresses_auto=True)``
        # *before* activating this env (see disassembler.comment docs).
        if not d.is_auto_suppressed_at(0x8000):
            d.comment(
                0x8000, "Sideways ROM header", auto_generated=True,
            )
        # Language and service entries: each is either a ``JMP abs``
        # (a real entry point) or 3 bytes of something else (some
        # ROMs use a placeholder if they don't implement that side).
        self._check_entry(d, 0x8000, "language")
        self._check_entry(d, 0x8003, "service")
        # rom_type is a 1-byte field; binary_version too. Leftover
        # classification will mark them as Byte(1).
        d.label(0x8006, "rom_type")
        d.label(0x8007, "copyright_offset")
        copyright_offset = d.memory.get_u8(0x8007)
        # Render the copyright_offset byte as the symbolic expression
        # ``copyright - rom_header`` rather than its literal hex
        # value. Reads more honestly: the byte's purpose is to point
        # at the copyright string; matching the symbolic form is the
        # whole reason for naming both ends.
        d.expr(0x8007, "copyright - rom_header")
        d.label(0x8008, "binary_version")
        d.label(0x8009, "title")
        # Title is NUL-terminated; scan for the terminator. Bound the
        # scan by the copyright offset so a missing terminator
        # doesn't run off into the rest of the ROM.
        copyright_addr = 0x8000 + copyright_offset
        title_terminator = self._find_nul(d, 0x8009, copyright_addr)
        title_length = title_terminator - 0x8009 + 1  # include the NUL
        if title_length > 0:
            d.string(0x8009, title_length)
        # If there's room between the title's NUL and the copyright
        # string, treat the gap as a NUL-terminated version string.
        version_start = title_terminator + 1
        if version_start < copyright_addr:
            d.label(version_start, "version")
            version_terminator = self._find_nul(
                d, version_start, copyright_addr,
            )
            d.string(
                version_start, version_terminator - version_start + 1,
            )
        # Copyright string starts at &8000 + copyright_offset, with a
        # leading NUL byte (per Acorn convention) followed by the
        # actual NUL-terminated text.
        d.label(copyright_addr, "copyright")
        copyright_text_start = copyright_addr + 1
        load_end = self._load_end_after(d, copyright_text_start)
        copyright_terminator = self._find_nul(
            d, copyright_text_start, load_end,
        )
        d.string(
            copyright_addr,
            copyright_terminator - copyright_addr + 1,
        )

    # ----- helpers ----------------------------------------------------

    @staticmethod
    def _check_entry(d, addr: int, entry_type: str) -> None:
        """If the byte at ``addr`` is ``JMP abs``, register an entry
        point and label both the entry and its handler. Otherwise
        classify the 3 header bytes as a Byte block."""
        d.label(addr, f"{entry_type}_entry")
        if d.memory.get_u8(addr) == _JMP_ABS_OPCODE:
            d.entry(addr)
            target = d.memory.get_u16_le(addr + 1)
            d.label(target, f"{entry_type}_handler")
        else:
            d.byte(addr, 3)

    @staticmethod
    def _find_nul(d, start: int, hard_limit: int) -> int:
        """Walk forward from ``start`` until the byte at the address
        is NUL or we hit ``hard_limit`` (exclusive). Returns the
        address of the NUL (or ``hard_limit - 1`` if we ran out).
        """
        addr = start
        while addr < hard_limit:
            if not d.memory.is_loaded(addr):
                return addr - 1
            if d.memory.get_u8(addr) == 0:
                return addr
            addr += 1
        return hard_limit - 1

    @staticmethod
    def _load_end_after(d, start: int) -> int:
        """First address ≥ ``start`` that's NOT loaded — bounds the
        copyright-string NUL scan when the copyright is the last
        thing in the ROM.
        """
        addr = start
        while addr < d.cpu.address_space_size and d.memory.is_loaded(addr):
            addr += 1
        return addr
