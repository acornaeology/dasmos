"""Acorn sideways ROM environment — header layout, entry-point
detection, copyright/title strings, plus auto-annotated explanations
of every header field synthesised from the ROM bytes.

A sideways ROM lives at &8000-&BFFF on the BBC Micro and starts with
a fixed-shape header that identifies the language/service entry
points and embeds a NUL-terminated title and copyright string. This
environment recognises that layout, registers the conventional names,
seeds the trace from any entry point that's a ``JMP abs``, and
synthesises the explanatory annotations every driver script would
otherwise hand-write (see ``d.banner`` / ``d.comment`` calls in
:meth:`AcornSidewaysRomEnvironment.setup`).

Unlike :class:`AcornMosEnvironment` (which just registers labels)
this one **inspects loaded memory** at &8000 to decide what's where —
so it must be activated AFTER ``d.load(...)``::

    d = Disassembler.create(cpu="6502", environments=["acorn_mos"])
    d.load("rom.bin", 0x8000)
    d.use_environment("acorn_sideways_rom",
                      rom_title="ANFS ROM 4.21 (variant 1)")

The ``rom_title`` kwarg supplies the human-friendly per-version
banner shown above the header. If omitted, the binary's title +
binary_version bytes are used.

Layering: usually combined with ``acorn_mos`` (and eventually the
hardware environments). Calling order matters only when two
environments would otherwise overlap on the same address; otherwise
they compose freely.
"""

from typing import TYPE_CHECKING

from dasmos.core.annotations import Align
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

# rom_type byte (&8006) layout: top four bits are flags, bottom four
# select the processor. Acorn Application Note 004 plus the BBC Master
# Reference Manual document the field.
_ROM_TYPE_SERVICE_ENTRY = 0x80
_ROM_TYPE_LANGUAGE_ENTRY = 0x40
_ROM_TYPE_TUBE_RELOC = 0x20
_ROM_TYPE_ELECTRON_FIRMKEY = 0x10
_ROM_TYPE_PROCESSOR_MASK = 0x0f

# Processor-type sub-field mapping for the bottom four bits of rom_type.
# Encodings outside this set fall through to "unknown processor" in
# the inline rendering.
_PROCESSOR_TYPES: dict[int, str] = {
    0x0: "6502 BASIC",
    0x2: "6502 (non-BASIC)",
    0x3: "65C12 (Master / Compact)",
    0x8: "Z80",
    0x9: "32016",
    0xb: "ARM",
    0xc: "80186",
    0xd: "80286",
}


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
    - ``tube_reloc_addr`` (after copyright NUL, if rom_type bit 5 set)
                                  — 4 bytes, 32-bit LE Tube relocation
                                    address

    Per-field auto-annotations explain every part of the header from
    the ROM bytes alone. Drivers can override any field by attaching
    a Comment with ``suppresses_auto=True`` at the field's address
    *before* activating this env — see :meth:`Disassembler.comment`.

    Activated AFTER ``d.load(...)``::

        d.use_environment("acorn_sideways_rom",
                          rom_title="ANFS ROM 4.21 (variant 1)")
    """

    def __init__(
        self,
        name: str = "acorn_sideways_rom",
        *,
        rom_title: str | None = None,
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)
        self._rom_title = rom_title

    def setup(self, disassembler: "Disassembler") -> None:
        d = disassembler
        if not d.memory.is_loaded(0x8000):
            raise DasmosError(
                "acorn_sideways_rom needs ROM bytes loaded at &8000 "
                "— activate this environment AFTER d.load(...)"
            )
        d.label(0x8000, "rom_header")
        # Read the header bytes upfront — every annotation derives
        # from them.
        rom_type_byte = d.memory.get_u8(0x8006)
        copyright_offset = d.memory.get_u8(0x8007)
        binary_version_byte = d.memory.get_u8(0x8008)
        copyright_addr = 0x8000 + copyright_offset

        # Top-of-header per-version banner. Driver supplies via
        # ``rom_title`` kwarg; fallback synthesises one from the title
        # and binary_version bytes ("Acorn ANFS 4.21" style). ATX
        # heading marker — the JSON renderer forwards markdown
        # verbatim and ATX is immune to consumer wrap (see #3).
        if not d.is_auto_suppressed_at(0x8000):
            title_text = (
                self._rom_title
                if self._rom_title is not None
                else self._fallback_rom_title(
                    d, copyright_addr, binary_version_byte,
                )
            )
            d.comment(
                0x8000, f"# {title_text}", auto_generated=True,
            )

        # Language-entry slot banner (AFTER_LABEL): mode-aware
        # description selecting JMP / &00 / non-standard from the
        # first byte of the slot. The "Sideways ROM header" prefix in
        # the title doubles as the structural marker that py8dis
        # emits as a bare comment at &8000 — keeps comment-vocabulary
        # parity with the upstream reference output and reads as the
        # natural section header for the whole header block.
        if not d.is_auto_suppressed_at(0x8000):
            d.banner(
                0x8000,
                title="Sideways ROM header — language-entry slot (3 bytes)",
                description=self._language_entry_description(
                    d.memory.get_u8(0x8000),
                ),
                align=Align.AFTER_LABEL,
                auto_generated=True,
            )

        # Language and service entries: each is either a ``JMP abs``
        # (a real entry point) or 3 bytes of something else (some
        # ROMs use a placeholder if they don't implement that side).
        self._check_entry(d, 0x8000, "language")
        self._check_entry(d, 0x8003, "service")

        # Service-entry slot banner. Always JMP in practice, but the
        # banner explains the dispatch contract regardless.
        if not d.is_auto_suppressed_at(0x8003):
            d.banner(
                0x8003,
                title="Service-entry slot (3 bytes)",
                description=self._service_entry_description(
                    d.memory.get_u8(0x8003),
                ),
                align=Align.AFTER_LABEL,
                auto_generated=True,
            )

        # rom_type is a 1-byte field; binary_version too. Leftover
        # classification will mark them as Byte(1).
        d.label(0x8006, "rom_type")
        d.label(0x8007, "copyright_offset")
        d.label(0x8008, "binary_version")
        d.label(0x8009, "title")

        # Inline decode of the rom_type bit field — the most
        # information-dense byte in the header.
        if not d.is_auto_suppressed_at(0x8006):
            d.comment(
                0x8006,
                self._rom_type_inline(rom_type_byte),
                align=Align.INLINE,
                auto_generated=True,
            )

        # Render the copyright_offset byte as the symbolic expression
        # ``copyright - rom_header`` rather than its literal hex
        # value. Reads more honestly: the byte's purpose is to point
        # at the copyright string; matching the symbolic form is the
        # whole reason for naming both ends.
        d.expr(0x8007, "copyright - rom_header")
        if not d.is_auto_suppressed_at(0x8007):
            d.comment(
                0x8007,
                f"Offset of NUL preceding copyright "
                f"(= &{copyright_offset:02x} → copyright at "
                f"&{copyright_addr:04x})",
                align=Align.INLINE,
                auto_generated=True,
            )

        if not d.is_auto_suppressed_at(0x8008):
            d.comment(
                0x8008,
                f"Binary version: &{binary_version_byte:02x} "
                f"(informational, not used by MOS)",
                align=Align.INLINE,
                auto_generated=True,
            )

        # Title is NUL-terminated; scan for the terminator. Bound the
        # scan by the copyright offset so a missing terminator
        # doesn't run off into the rest of the ROM.
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

        # Tube relocation address: present iff rom_type bit 5 is set.
        # Lives in the 4 bytes immediately after the copyright NUL.
        # Encoded as 32-bit LE — the address the ROM body wants to
        # be relocated to when running on a Tube co-processor.
        if rom_type_byte & _ROM_TYPE_TUBE_RELOC:
            tube_addr = copyright_terminator + 1
            if tube_addr + 4 <= load_end:
                d.label(tube_addr, "tube_reloc_addr")
                d.byte(tube_addr, 4)
                if not d.is_auto_suppressed_at(tube_addr):
                    d.comment(
                        tube_addr,
                        "Tube relocation address (32-bit LE) — where "
                        "the ROM body relocates on a Tube "
                        "co-processor",
                        align=Align.INLINE,
                        auto_generated=True,
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

    @staticmethod
    def _fallback_rom_title(d, copyright_addr: int, binary_version: int) -> str:
        """Synthesise a top-of-header title from the binary's title
        bytes plus binary_version when the driver didn't pass
        ``rom_title``.

        Walks the title bytes (NUL-terminated, bounded by the
        copyright offset) and renders ``"<title> v<binary_version>"``.
        Falls back to ``"Sideways ROM"`` if the title bytes are empty
        or unprintable.
        """
        chars: list[str] = []
        addr = 0x8009
        while addr < copyright_addr:
            if not d.memory.is_loaded(addr):
                break
            byte = d.memory.get_u8(addr)
            if byte == 0:
                break
            if 32 <= byte < 127:
                chars.append(chr(byte))
            addr += 1
        title = "".join(chars).strip() or "Sideways ROM"
        return f"{title} v&{binary_version:02x}"

    @staticmethod
    def _language_entry_description(byte0: int) -> str:
        """Mode-aware description for the language-entry slot at &8000.

        Three observed shapes for the first byte:

        - ``&4C`` (``JMP abs``) — ROM declares itself a language;
          MOS dispatches ``JMP &8000`` on language startup with a
          reason code in A.
        - ``&00`` — service-only ROM; byte 0 set to &00 per the
          Acorn header standard ("JMP language_entry, set to 0 if not
          a language") to inhibit the MOS dispatch path.
        - anything else — non-standard placeholder; MOS would still
          dispatch ``JMP &8000`` on language startup so the bytes
          must remain non-executable in any normal use of the ROM.
        """
        intro = (
            "MOS dispatches ``JMP &8000`` on language startup with a "
            "reason code in A (1 = normal start, 0 = no language "
            "available, 2/3 = Electron softkey query)."
        )
        if byte0 == _JMP_ABS_OPCODE:
            mode = (
                "Byte 0 is ``&4C`` so this ROM declares itself a language "
                "(``rom_type`` bit 6 set); the slot is a real ``JMP`` to "
                "``language_handler``."
            )
        elif byte0 == 0x00:
            mode = (
                "Byte 0 is ``&00`` (service-only ROM, ``rom_type`` bit 6 "
                "clear) — set to inhibit the MOS dispatch path per the "
                "Acorn header standard. Bytes 1-2 are unused padding."
            )
        else:
            mode = (
                f"Byte 0 is ``&{byte0:02x}`` (non-standard placeholder); "
                f"MOS would still execute ``JMP &8000`` on language "
                f"startup so this ROM relies on never being asked."
            )
        return f"{intro}\n\n{mode}"

    @staticmethod
    def _service_entry_description(byte0: int) -> str:
        """Description of the service-entry slot at &8003. Almost always
        ``JMP abs`` in practice — the slot is the universal entry
        point for MOS service-call dispatch.
        """
        intro = (
            "MOS calls ``JMP &8003`` for service-call dispatch — "
            "unrecognised ``*`` commands, OSWORDs, OSBYTEs, ``*HELP``, "
            "filing-system init / select, paged-ROM scans, and many "
            "other events. The reason code arrives in A."
        )
        if byte0 == _JMP_ABS_OPCODE:
            mode = (
                "Byte 0 is ``&4C`` (``JMP abs``) — slot dispatches to "
                "``service_handler``."
            )
        else:
            mode = (
                f"Byte 0 is ``&{byte0:02x}`` (non-standard); a ROM that "
                f"never wants to handle service calls would set "
                f"``rom_type`` bit 7 clear and use a placeholder here."
            )
        return f"{intro}\n\n{mode}"

    @staticmethod
    def _rom_type_inline(rom_type: int) -> str:
        """Inline-decoded text for the ``rom_type`` byte at &8006.

        Lists the upper-bit flags that are set, then names the
        processor selected by the bottom four bits. Reads e.g.
        ``ROM type: Service entry; Language entry; 6502 (non-BASIC)``.
        Unknown processor encodings render as ``processor &X``.
        """
        flags: list[str] = []
        if rom_type & _ROM_TYPE_SERVICE_ENTRY:
            flags.append("Service entry")
        if rom_type & _ROM_TYPE_LANGUAGE_ENTRY:
            flags.append("Language entry")
        if rom_type & _ROM_TYPE_TUBE_RELOC:
            flags.append("Tube relocation address present")
        if rom_type & _ROM_TYPE_ELECTRON_FIRMKEY:
            flags.append("Electron firmkey support")
        proc_code = rom_type & _ROM_TYPE_PROCESSOR_MASK
        proc_name = _PROCESSOR_TYPES.get(proc_code, f"processor &{proc_code:x}")
        flags.append(proc_name)
        return "ROM type: " + "; ".join(flags)
