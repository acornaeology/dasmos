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
from dasmos.core.format_hint import FormatHint
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

        # rom_type byte is structurally a bitfield — render in binary
        # via the BINARY format hint (``%10000010``) and emit a
        # Markdown table below the equb naming each bit. Reads as a
        # per-bit commentary anchored on the byte's actual structure
        # rather than a paragraph of prose.
        if not d.is_auto_suppressed_at(0x8006):
            d.format_hint(0x8006, FormatHint.BINARY)
            d.comment(
                0x8006, "ROM type",
                align=Align.INLINE, auto_generated=True,
            )
            d.banner(
                0x8006,
                description=self._rom_type_table(rom_type_byte),
                align=Align.AFTER_LINE,
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
        # doesn't run off into the rest of the ROM. Split the
        # terminator into its own ``equb &00`` so the NUL is visible
        # in the listing rather than buried inside an EQUS.
        title_terminator = self._find_nul(d, 0x8009, copyright_addr)
        self._classify_nul_terminated_string(d, 0x8009, title_terminator)
        # If there's room between the title's NUL and the copyright
        # string, treat the gap as a NUL-terminated version string.
        version_start = title_terminator + 1
        if version_start < copyright_addr:
            d.label(version_start, "version")
            version_terminator = self._find_nul(
                d, version_start, copyright_addr,
            )
            self._classify_nul_terminated_string(
                d, version_start, version_terminator,
            )
        # Copyright field starts at &8000 + copyright_offset, with a
        # leading NUL byte (per Acorn convention — the copyright
        # offset POINTS AT this NUL), then the (C)-prefixed text,
        # then optionally a trailing NUL. Split into three
        # classifications so the leading NUL is a visible byte the
        # listing comments on, then the text under its own
        # ``copyright_string`` label, then (when present) the
        # trailing NUL via ``_classify_nul_terminated_string`` —
        # which predicates on the byte value, so ROMs whose
        # copyright text runs straight into the next field without
        # a trailing NUL (rare but valid) don't get a wrong
        # "NUL terminator" inline on their last text byte.
        d.label(copyright_addr, "copyright")
        d.byte(copyright_addr, 1)
        if not d.is_auto_suppressed_at(copyright_addr):
            d.comment(
                copyright_addr,
                "NUL preceding copyright string",
                align=Align.INLINE,
                auto_generated=True,
            )
        copyright_text_start = copyright_addr + 1
        load_end = self._load_end_after(d, copyright_text_start)
        copyright_terminator = self._find_nul(
            d, copyright_text_start, load_end,
        )
        d.label(copyright_text_start, "copyright_string")
        self._classify_nul_terminated_string(
            d, copyright_text_start, copyright_terminator,
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
        classify the 3 header bytes — splitting the &00 sentinel
        case into per-byte classifications so the listing reads each
        byte's role inline rather than burying it in a paragraph.

        Three observed shapes:

        - byte 0 = ``&4C`` (``JMP abs``) — register entry + handler.
        - byte 0 = ``&00`` (no-language sentinel) — emit as
          ``equb &00`` (sentinel) + ``equb &00, &00`` (padding) with
          per-byte inline notes.
        - anything else — single 3-byte ``equb`` block (the slot is
          non-standard; whatever's there is opaque, no per-byte
          structure to surface).
        """
        d.label(addr, f"{entry_type}_entry")
        byte0 = d.memory.get_u8(addr)
        if byte0 == _JMP_ABS_OPCODE:
            d.entry(addr)
            target = d.memory.get_u16_le(addr + 1)
            d.label(target, f"{entry_type}_handler")
        elif byte0 == 0x00:
            d.byte(addr, 1)
            d.byte(addr + 1, 2)
            if not d.is_auto_suppressed_at(addr):
                d.comment(
                    addr,
                    f"no-{entry_type} sentinel "
                    f"(rom_type bit "
                    f"{6 if entry_type == 'language' else 7} clear)",
                    align=Align.INLINE,
                    auto_generated=True,
                )
            if not d.is_auto_suppressed_at(addr + 1):
                d.comment(
                    addr + 1,
                    "unused padding",
                    align=Align.INLINE,
                    auto_generated=True,
                )
        else:
            d.byte(addr, 3)

    @staticmethod
    def _classify_nul_terminated_string(d, start: int, terminator: int) -> None:
        """Classify a NUL-terminated string region.

        When the byte at ``terminator`` really is ``&00``, split it off
        into its own ``equb &00`` with an inline "NUL terminator" note
        so the NUL is a visible byte the listing comments on rather
        than the last character of an EQUS.

        When it isn't (the field has no embedded NUL — its last byte
        is text or padding shared with the next field, e.g. NFS-style
        titles whose terminator IS the next field's leading byte),
        classify the whole region as a single ``equs`` with no NUL
        split or "NUL terminator" inline. Predicating on the byte
        value avoids the #12 regression where every NFS title
        (``"NET"`` followed directly by the copyright leading-NUL)
        had its trailing ``T`` byte mislabelled as a NUL terminator.

        ``start`` is the first text byte (or the NUL itself for an
        empty string); ``terminator`` is the address of either the
        real NUL or, when no NUL is embedded, the field's last byte.
        """
        is_real_nul = (
            d.memory.is_loaded(terminator)
            and d.memory.get_u8(terminator) == 0
        )
        if not is_real_nul:
            full_length = terminator - start + 1
            if full_length > 0:
                d.string(start, full_length)
            return
        text_length = terminator - start
        if text_length > 0:
            d.string(start, text_length)
        d.byte(terminator, 1)
        if not d.is_auto_suppressed_at(terminator):
            d.comment(
                terminator,
                "NUL terminator",
                align=Align.INLINE,
                auto_generated=True,
            )

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
          reason code in A. Reason codes rendered as a Markdown
          table for clarity.
        - ``&00`` — service-only ROM; per-byte detail lives on the
          bytes themselves (sentinel + padding inlines).
        - anything else — non-standard placeholder.
        """
        intro = "MOS dispatches ``JMP &8000`` on language startup."
        reason_table = (
            "Reason code in A on entry:\n"
            "\n"
            "| A | Meaning                                              |\n"
            "|---|------------------------------------------------------|\n"
            "| 1 | Normal startup                                       |\n"
            "| 0 | No language available — MOS calling Tube ROM         |\n"
            "| 2 | Request next byte of softkey expansion (Electron)    |\n"
            "| 3 | Request length of softkey expansion (Electron)       |"
        )
        if byte0 == _JMP_ABS_OPCODE:
            mode = (
                "Byte 0 is ``&4C`` so this ROM declares itself a language "
                "(``rom_type`` bit 6 set); the slot is a real ``JMP`` to "
                "``language_handler``."
            )
        elif byte0 == 0x00:
            mode = (
                "Service-only ROM (``rom_type`` bit 6 clear). Per-byte "
                "detail is inline."
            )
        else:
            mode = (
                f"Byte 0 is ``&{byte0:02x}`` (non-standard placeholder); "
                f"MOS would still execute ``JMP &8000`` on language "
                f"startup so this ROM relies on never being asked."
            )
        return f"{intro}\n\n{mode}\n\n{reason_table}"

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
            # JMP-mode is the universal case; no need to restate
            # what the next disassembly line shows.
            return intro
        mode = (
            f"Byte 0 is ``&{byte0:02x}`` (non-standard); a ROM that "
            f"never wants to handle service calls would set "
            f"``rom_type`` bit 7 clear and use a placeholder here."
        )
        return f"{intro}\n\n{mode}"

    @staticmethod
    def _rom_type_table(rom_type: int) -> str:
        """Markdown bit-table for the ``rom_type`` byte at &8006.

        Renders as a 3-column table (Bit / Value / Meaning) listing
        each flag bit's state plus the processor selected by the
        bottom four bits. The table sits in an ``AFTER_LINE`` banner
        below the ``equb`` so the byte's bitfield structure is
        visible alongside the per-bit decode.
        """
        rows: list[tuple[str, str, str]] = []
        for bit, mask, present, absent in [
            (7, _ROM_TYPE_SERVICE_ENTRY,
             "Service entry present", "No service entry"),
            (6, _ROM_TYPE_LANGUAGE_ENTRY,
             "Language entry present", "No language entry"),
            (5, _ROM_TYPE_TUBE_RELOC,
             "Tube relocation address present", "No Tube relocation"),
            (4, _ROM_TYPE_ELECTRON_FIRMKEY,
             "Electron firmkey support", "No Electron firmkey"),
        ]:
            value = "1" if rom_type & mask else "0"
            meaning = present if rom_type & mask else absent
            rows.append((str(bit), value, meaning))
        proc_code = rom_type & _ROM_TYPE_PROCESSOR_MASK
        proc_name = _PROCESSOR_TYPES.get(proc_code, f"processor &{proc_code:x}")
        rows.append(("3-0", f"{proc_code:04b}", f"Processor: {proc_name}"))
        bit_w = max(len(r[0]) for r in rows)
        val_w = max(len(r[1]) for r in rows)
        meaning_w = max(len(r[2]) for r in rows)
        lines = [
            f"| {'Bit'.ljust(bit_w)} | {'Value'.ljust(val_w)} | "
            f"{'Meaning'.ljust(meaning_w)} |",
            f"|{'-' * (bit_w + 2)}|{'-' * (val_w + 2)}|"
            f"{'-' * (meaning_w + 2)}|",
        ]
        for bit, value, meaning in rows:
            lines.append(
                f"| {bit.ljust(bit_w)} | {value.ljust(val_w)} | "
                f"{meaning.ljust(meaning_w)} |"
            )
        return "\n".join(lines)
