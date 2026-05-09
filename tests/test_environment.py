"""Tests for the Environment extension point + the bundled
``acorn_mos`` plug-in.

The Environment kind is the third extension axis (alongside
``cpu`` and ``renderer``) — it carries platform-knowledge a
driver wants to layer onto its disassembler. The tests below
exercise both the abstract plug-in plumbing and the concrete
``acorn_mos`` knowledge it ships.
"""

import pytest

from dasmos.disassembler import Disassembler
from dasmos.environment import (
    ENVIRONMENT_NAMESPACE,
    Environment,
    create_environment,
    describe_environment,
    environment_names,
    environment_type,
)
from dasmos.ext.environments.acorn_master_hardware import (
    AcornMasterHardwareEnvironment,
)
from dasmos.ext.environments.acorn_model_b_hardware import (
    AcornModelBHardwareEnvironment,
)
from dasmos.ext.environments.acorn_mos import AcornMosEnvironment


class TestPluginRegistration:

    def test_acorn_mos_listed(self):
        names = environment_names()
        assert "acorn_mos" in names

    def test_loadable_via_stevedore(self):
        env = create_environment("acorn_mos")
        assert isinstance(env, AcornMosEnvironment)

    def test_describe_returns_class_docstring(self):
        text = describe_environment("acorn_mos")
        assert "MOS" in text
        assert "OS-call" in text or "OS call" in text or "OSWRCH" in text

    def test_describe_single_line_first_line_only(self):
        single = describe_environment("acorn_mos", single_line=True)
        assert "\n" not in single
        # Class docstring's first line.
        assert single.startswith("Acorn MOS environment")

    def test_environment_type_returns_class(self):
        cls = environment_type("acorn_mos")
        assert cls is AcornMosEnvironment

    def test_namespace_constant_matches_pyproject(self):
        # ``dasmos.environment`` is the namespace pyproject's
        # ``[project.entry-points.dasmos.environment]`` registers
        # under; CPU and renderer follow the same shape.
        assert ENVIRONMENT_NAMESPACE == "dasmos.environment"


class TestActivation:

    def test_kwarg_activates_at_construction(self):
        d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )
        # A handful of canonical names land in the LabelManager.
        assert "userv" in d.labels.get_label(0x0200).explicit_name_texts()
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        assert "osbyte" in d.labels.get_label(0xfff4).explicit_name_texts()

    def test_method_activates_after_construction(self):
        d = Disassembler.create(cpu="6502")
        assert d.labels.get_label(0xffee) is None
        d.use_environment("acorn_mos")
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()

    def test_method_accepts_instance(self):
        d = Disassembler.create(cpu="6502")
        d.use_environment(AcornMosEnvironment())
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()

    def test_idempotent_second_activation(self):
        # Activating the same environment twice is a no-op — the
        # underlying LabelManager dedupes ExplicitName entries by
        # text. Verifies the layering story doesn't blow up on
        # re-application.
        d = Disassembler.create(cpu="6502")
        d.use_environment("acorn_mos")
        d.use_environment("acorn_mos")
        names = d.labels.get_label(0xffee).explicit_name_texts()
        assert names == {"oswrch"}

    def test_unknown_environment_raises(self):
        from dasmos.environment import EnvironmentExtensionError
        with pytest.raises(EnvironmentExtensionError):
            create_environment("nonexistent")

    def test_use_environment_rejects_non_environment(self):
        d = Disassembler.create(cpu="6502")
        with pytest.raises(TypeError):
            d.use_environment(42)


class TestComposability:
    """The whole point of environments-as-plug-ins is that drivers
    can layer multiple. These tests pin that contract.
    """

    def test_two_distinct_envs_layer_their_labels(self):
        # A custom in-process environment alongside the bundled one.
        # Both contribute non-overlapping labels; both end up active.
        class TestExtraEnv(Environment):
            def __init__(self, name="test_extra", **kwargs):
                super().__init__(name=name, **kwargs)

            def setup(self, d):
                d.optional_label(0x0070, "userworkspace")

        d = Disassembler.create(cpu="6502", environments=["acorn_mos"])
        d.use_environment(TestExtraEnv())
        # Both envs' labels are present.
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        assert "userworkspace" in d.labels.get_label(0x0070).explicit_name_texts()

    def test_two_envs_same_addr_different_names_both_present(self):
        # Aliases at a single address are an explicit feature of the
        # LabelManager — both get recorded.
        class AliasEnv(Environment):
            def __init__(self, name="alias", **kwargs):
                super().__init__(name=name, **kwargs)

            def setup(self, d):
                # Add a second name at &FFEE alongside ``oswrch``.
                d.optional_label(0xffee, "print_char")

        d = Disassembler.create(cpu="6502", environments=["acorn_mos"])
        d.use_environment(AliasEnv())
        names = d.labels.get_label(0xffee).explicit_name_texts()
        assert names == {"oswrch", "print_char"}


class TestAcornMosCoverage:
    """Spot-checks that the ported label set matches py8dis."""

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )

    def test_workspace_addresses(self):
        for addr, name in [
            (0x00f2, "os_text_ptr"),
            (0x00f4, "romsel_copy"),
            (0x00f6, "osrdsc_ptr"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing workspace label {name} at {addr:04x}"
            )

    def test_vector_table_pairs(self):
        # Each vector occupies 2 bytes. Only the BASE address is
        # registered as a label; the high byte gets rendered as
        # ``<name>+1`` via the renderer's base+offset fallback
        # (matches py8dis-fork's ``ol2`` convention).
        for addr, name in [
            (0x0200, "userv"), (0x020e, "wrchv"),
            (0x0214, "argsv"), (0x0220, "evntv"),
        ]:
            label_lo = self.d.labels.get_label(addr)
            assert name in label_lo.explicit_name_texts()
            # No ``<name>_hi`` label registered.
            label_hi = self.d.labels.get_label(addr + 1)
            assert label_hi is None or (
                f"{name}_hi" not in label_hi.explicit_name_texts()
            )

    def test_os_call_entries(self):
        for addr, name in [
            (0xffe0, "osrdch"), (0xffee, "oswrch"),
            (0xfff1, "osword"), (0xfff4, "osbyte"),
            (0xfff7, "oscli"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts()

    def test_count_matches_expected(self):
        # 3 workspace + 27 vectors (base only — high byte uses the
        # renderer's ``<base>+1`` fallback) + 21 OS calls = 51
        # distinct addresses with at least one name.
        named_addrs = sum(
            1 for label in self.d.labels._labels.values()
            if label.explicit_name_texts()
        )
        assert named_addrs == 3 + 27 + 21


class TestAcornSidewaysRom:
    """Sideways ROM environment: header layout + entry-point detection
    + copyright/title strings. Inspects loaded memory at &8000 so
    must be activated AFTER ``d.load(...)``.
    """

    @staticmethod
    def _make_loaded_disassembler(tmp_path, rom_bytes):
        """Helper: write ``rom_bytes`` to a file and load it at &8000."""
        rom = tmp_path / "rom.bin"
        rom.write_bytes(rom_bytes)
        d = Disassembler.create(cpu="6502")
        d.load(rom, 0x8000)
        return d

    @staticmethod
    def _build_rom(
        language_jmp=True, service_jmp=True,
        title=b"TestROM", version=b"1.00",
        copyright=b"(C) 2026",
    ):
        """Build a 256-byte fake sideways ROM with the standard
        header layout. Returns the bytes."""
        # Header: language entry (3 bytes) + service entry (3 bytes)
        # + rom_type + copyright_offset + binary_version + title +
        # NUL + version + NUL + ... copyright string at offset.
        header = bytearray()
        # &8000-2: language entry (JMP &80F0 if language_jmp else 3 NOPs)
        if language_jmp:
            header += bytes([0x4c, 0xf0, 0x80])  # JMP &80F0
        else:
            header += bytes([0xea, 0xea, 0xea])  # NOPs
        # &8003-5: service entry
        if service_jmp:
            header += bytes([0x4c, 0xf3, 0x80])  # JMP &80F3
        else:
            header += bytes([0xea, 0xea, 0xea])
        # &8006: rom_type
        header += bytes([0x82])
        # &8007: copyright_offset (we'll patch this after we know
        # where copyright lands)
        cp_off_pos = len(header)
        header += bytes([0])  # placeholder
        # &8008: binary_version
        header += bytes([0x10])
        # &8009: title + NUL
        header += title + b"\x00"
        # version + NUL
        header += version + b"\x00"
        # copyright leading NUL + text + NUL
        cp_addr = len(header)  # offset from &8000
        header += b"\x00" + copyright + b"\x00"
        # Patch copyright_offset
        header[cp_off_pos] = cp_addr
        # Pad to 256 bytes (so loading at &8000 doesn't run past the
        # 16-bit address space) and put NOP-RTS handlers at &80F0
        # (language) and &80F3 (service) so the trace has somewhere to
        # go.
        while len(header) < 0xf0:
            header += bytes([0xff])
        header += bytes([0xea, 0xea, 0x60])  # NOP NOP RTS at &80F0
        header += bytes([0xea, 0xea, 0x60])  # NOP NOP RTS at &80F3
        while len(header) < 0x100:
            header += bytes([0xff])
        return bytes(header)

    def test_raises_when_8000_not_loaded(self, tmp_path):
        # The environment's setup needs the ROM at &8000.
        d = Disassembler.create(cpu="6502")
        with pytest.raises(Exception):  # DasmosError or subclass
            d.use_environment("acorn_sideways_rom")

    def test_jmp_entry_registers_handler_label(self, tmp_path):
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(language_jmp=True),
        )
        d.use_environment("acorn_sideways_rom")
        # rom_header at &8000.
        assert "rom_header" in d.labels.get_label(0x8000).explicit_name_texts()
        # language_entry at &8000 (alias of rom_header).
        assert "language_entry" in d.labels.get_label(0x8000).explicit_name_texts()
        # JMP at &8000 → handler at &80F0.
        assert "language_handler" in d.labels.get_label(0x80f0).explicit_name_texts()

    def test_non_jmp_entry_classifies_as_byte(self, tmp_path):
        # No language entry (just NOPs) → classify the 3 bytes as
        # data and DON'T add a handler label.
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(language_jmp=False),
        )
        d.use_environment("acorn_sideways_rom")
        # Still labelled language_entry, but no language_handler
        # (because there's no JMP).
        assert "language_entry" in d.labels.get_label(0x8000).explicit_name_texts()
        # The trace shouldn't have an entry registered at &8000 for
        # the language side. Hard to assert directly without trace
        # access, but we can verify no language_handler label was
        # synthesised at any address.
        for addr in range(0x8000, 0x8100):
            label = d.labels.get_label(addr)
            if label is not None:
                assert "language_handler" not in label.explicit_name_texts()

    def test_header_field_labels(self, tmp_path):
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        for addr, expected in [
            (0x8006, "rom_type"),
            (0x8007, "copyright_offset"),
            (0x8008, "binary_version"),
            (0x8009, "title"),
        ]:
            assert expected in d.labels.get_label(addr).explicit_name_texts(), (
                f"missing label {expected} at {addr:04x}"
            )

    def test_copyright_offset_byte_renders_as_expression(
        self, tmp_path,
    ):
        # The byte at &8007 carries an expression override
        # (``copyright - rom_header``); the renderer should emit
        # that expression instead of the literal hex value.
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        text = str(d.disassemble().render("beebasm"))
        # The whole expression appears in the output (somewhere).
        assert "copyright - rom_header" in text

    def test_title_string_classification(self, tmp_path):
        title = b"MyROM"
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(title=title),
        )
        d.use_environment("acorn_sideways_rom")
        text = str(d.disassemble().render("beebasm"))
        # Title gets emitted (as a string literal or equs).
        assert ".title" in text

    def test_copyright_string_classification(self, tmp_path):
        copyright = b"(C) Acornaeology"
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(copyright=copyright),
        )
        d.use_environment("acorn_sideways_rom")
        text = str(d.disassemble().render("beebasm"))
        assert ".copyright" in text

    def test_header_annotations_are_auto_generated(self, tmp_path):
        # All env-attached header annotations at &8000 are address-
        # metadata, not user-authored content. They must carry
        # auto_generated=True so a driver-supplied banner at the same
        # address doesn't trigger the duplicate warning.
        from dasmos.core.annotations import Banner, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        bucket = d.annotations.get(0x8000)
        env_attached = [
            a for a in bucket if isinstance(a, (Comment, Banner))
        ]
        assert env_attached, "expected env to attach at least one annotation"
        assert all(getattr(a, "auto_generated", False) for a in env_attached)

    def test_driver_banner_no_dup_warning_with_env_header(self, tmp_path):
        # A driver-supplied per-version comment at &8000 stacks
        # alongside the env's auto-generated header annotations
        # without firing the AnnotationStore duplicate-comment warning
        # (the warning targets driver-authoring bugs, not env-driven
        # layering).
        import warnings
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            d.comment(0x8000, "NFS ROM 3.65 disassembly")

    def test_driver_can_suppress_env_header_via_suppresses_auto(
        self, tmp_path,
    ):
        # A driver attaching ``suppresses_auto=True`` at &8000
        # *before* activating the env causes the env to skip its
        # auto-attachments at that address — the driver's text
        # becomes the sole user-authored comment, and the env's
        # rom_title comment + language-entry banner are not emitted.
        from dasmos.core.annotations import Banner, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.comment(
            0x8000,
            "NFS ROM 3.65 — full driver banner here",
            suppresses_auto=True,
        )
        d.use_environment("acorn_sideways_rom")
        bucket = d.annotations.get(0x8000)
        comments = [a for a in bucket if isinstance(a, Comment)]
        banners = [a for a in bucket if isinstance(a, Banner)]
        # Driver comment present.
        assert any(
            "NFS ROM 3.65 — full driver banner here" in c.text
            for c in comments
        )
        # No env-attached auto comments or banners.
        assert not any(getattr(a, "auto_generated", False) for a in comments)
        assert not banners

    def test_rom_title_kwarg_renders_atx_heading_at_8000(self, tmp_path):
        from dasmos.core.annotations import Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment(
            "acorn_sideways_rom",
            rom_title="ANFS ROM 4.21 (variant 1)",
        )
        comments = [
            a for a in d.annotations.get(0x8000) if isinstance(a, Comment)
        ]
        # ATX heading marker — immune to consumer wrap (#3).
        assert any(
            c.text == "# ANFS ROM 4.21 (variant 1)" for c in comments
        )

    def test_rom_title_fallback_uses_title_bytes_and_version(self, tmp_path):
        # Without rom_title, the env synthesises one from the title
        # bytes + binary_version. _build_rom uses title=b"TestROM"
        # and a binary_version of &10.
        from dasmos.core.annotations import Comment
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(title=b"TestROM"),
        )
        d.use_environment("acorn_sideways_rom")
        comments = [
            a for a in d.annotations.get(0x8000) if isinstance(a, Comment)
        ]
        # ATX prefix + title text + version literal somewhere in there.
        assert any(c.text.startswith("# TestROM") for c in comments)

    def test_language_entry_banner_describes_jmp_mode(self, tmp_path):
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(language_jmp=True),
        )
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8000, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners, "expected language-entry banner at &8000"
        body = banners[0].description
        assert "ROM declares itself a language" in body
        assert "language_handler" in body

    def test_language_entry_banner_describes_service_only_mode(self, tmp_path):
        # Build a ROM with byte 0 = &00 to exercise the service-only
        # branch. Per-byte detail (&00 sentinel + padding) lives on
        # the inline comments of those bytes; the banner just notes
        # service-only mode.
        from dasmos.core.annotations import Align, Banner
        rom = bytearray(self._build_rom(language_jmp=False))
        rom[0] = 0x00
        rom[1] = 0x00
        rom[2] = 0x00
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8000, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners
        body = banners[0].description
        assert "service-only" in body.lower() or "Service-only" in body

    def test_language_entry_banner_carries_reason_code_table(self, tmp_path):
        # The reason-code A=0/1/2/3 mapping renders as a GFM table in
        # the banner description so downstream consumers see structured
        # rows (per #11 §1).
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banner = next(
            a for a in d.annotations.get_for_align(0x8000, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        )
        body = banner.description
        # Pipe-table header + at least one of each row.
        assert "| A |" in body
        assert "| Meaning" in body
        assert "Normal startup" in body
        assert "No language available" in body
        assert "softkey expansion" in body

    def test_disabled_language_slot_split_into_sentinel_and_padding(
        self, tmp_path,
    ):
        # When byte 0 = &00, _check_entry splits the 3-byte slot into
        # a 1-byte equb (sentinel) + 2-byte equb (padding) with
        # per-byte inline comments rather than a single 3-byte block.
        from dasmos.core.annotations import Align, Comment
        from dasmos.core.classification import Byte
        rom = bytearray(self._build_rom(language_jmp=False))
        rom[0:3] = [0x00, 0x00, 0x00]
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        ir = d.disassemble()
        # &8000 is now Byte(1), &8001 is Byte(2).
        c8000 = ir.classifications.get_classification(0x8000)
        c8001 = ir.classifications.get_classification(0x8001)
        assert isinstance(c8000, Byte) and c8000.length() == 1
        assert isinstance(c8001, Byte) and c8001.length() == 2
        # Per-byte inlines.
        sentinel_inline = next(
            a.text for a in ir.annotations.get_for_align(0x8000, Align.INLINE)
            if isinstance(a, Comment)
        )
        padding_inline = next(
            a.text for a in ir.annotations.get_for_align(0x8001, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert "no-language sentinel" in sentinel_inline
        assert "rom_type bit 6 clear" in sentinel_inline
        assert "unused padding" in padding_inline

    def test_service_entry_banner_at_8003(self, tmp_path):
        # JMP-mode service entry: banner gives the dispatch contract
        # without restating "byte 0 is &4C" (which would just echo
        # the next disassembly line).
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8003, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners
        body = banners[0].description
        assert "service-call" in body.lower()
        # §4: redundant "Byte 0 is &4C" line dropped from JMP-mode.
        assert "Byte 0 is" not in body

    def test_rom_type_inline_is_short_label(self, tmp_path):
        # The byte's inline is just "ROM type" — per-bit decode lives
        # in the AFTER_LINE banner below (per #11 §5).
        from dasmos.core.annotations import Align, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        inline = [
            a for a in d.annotations.get_for_align(0x8006, Align.INLINE)
            if isinstance(a, Comment)
        ]
        assert inline
        assert inline[0].text == "ROM type"

    def test_rom_type_byte_carries_binary_format_hint(self, tmp_path):
        # rom_type byte at &8006 gets FormatHint.BINARY so it renders
        # as %10000010 instead of &82 (per #11 §5).
        from dasmos.core.format_hint import FormatHint
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x8006) is FormatHint.BINARY

    def test_rom_type_after_line_banner_carries_bit_table(self, tmp_path):
        # _build_rom sets rom_type = &82 (Service entry + 6502-non-BASIC).
        # The AFTER_LINE banner below the equb decodes each bit as a
        # Markdown table row.
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8006, Align.AFTER_LINE)
            if isinstance(a, Banner)
        ]
        assert banners
        body = banners[0].description
        # Pipe-table header.
        assert "| Bit" in body
        assert "| Value" in body
        assert "| Meaning" in body
        # Each bit row appears with its value (1/0 for &82's pattern).
        assert "| 7" in body and "| 1" in body
        assert "| 6" in body and "| 0" in body
        # Service entry present + 6502 (non-BASIC) processor.
        assert "Service entry present" in body
        assert "6502 (non-BASIC)" in body
        assert "0010" in body  # processor sub-field rendered in binary

    def test_rom_type_table_decodes_all_flags_set(self, tmp_path):
        from dasmos.core.annotations import Align, Banner
        rom = bytearray(self._build_rom())
        rom[6] = 0xf8  # all four flags + Z80
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        body = next(
            a.description for a in d.annotations.get_for_align(0x8006, Align.AFTER_LINE)
            if isinstance(a, Banner)
        )
        assert "Service entry present" in body
        assert "Language entry present" in body
        assert "Tube relocation address present" in body
        assert "Electron firmkey support" in body
        assert "Z80" in body

    def test_rom_type_table_handles_unknown_processor(self, tmp_path):
        # Processor encoding &7 isn't in the table — falls back to
        # ``processor &7``.
        from dasmos.core.annotations import Align, Banner
        rom = bytearray(self._build_rom())
        rom[6] = 0x07
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        body = next(
            a.description for a in d.annotations.get_for_align(0x8006, Align.AFTER_LINE)
            if isinstance(a, Banner)
        )
        assert "processor &7" in body

    def test_copyright_split_into_three_byte_classifications(self, tmp_path):
        # The copyright field at copyright_addr now classifies as:
        # Byte(1) leading NUL + String(text) + Byte(1) trailing NUL,
        # with copyright_string label at copyright+1.
        from dasmos.core.annotations import Align, Comment
        from dasmos.core.classification import Byte, String
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(copyright=b"(C) 2026"),
        )
        d.use_environment("acorn_sideways_rom")
        ir = d.disassemble()
        copyright_label = next(
            (addr for addr in range(0x8000, 0x8100)
             if (lbl := ir.labels.get_label(addr)) is not None
             and "copyright" in lbl.explicit_name_texts())
        )
        # Leading NUL = Byte(1).
        leading = ir.classifications.get_classification(copyright_label)
        assert isinstance(leading, Byte) and leading.length() == 1
        # copyright_string label at copyright+1.
        text_label = ir.labels.get_label(copyright_label + 1)
        assert text_label is not None
        assert "copyright_string" in text_label.explicit_name_texts()
        # The text bytes classify as a String.
        text_class = ir.classifications.get_classification(copyright_label + 1)
        assert isinstance(text_class, String)
        # Inline notes on both NULs.
        leading_inline = next(
            a.text for a in ir.annotations.get_for_align(copyright_label, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert "NUL preceding copyright" in leading_inline

    def test_title_split_off_trailing_nul(self, tmp_path):
        # Title now classifies as String(text-only) + Byte(1) NUL,
        # with an inline "NUL terminator" on the NUL byte.
        from dasmos.core.annotations import Align, Comment
        from dasmos.core.classification import Byte, String
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(title=b"TestROM"),
        )
        d.use_environment("acorn_sideways_rom")
        ir = d.disassemble()
        title_class = ir.classifications.get_classification(0x8009)
        assert isinstance(title_class, String)
        # The byte right after the title text is the NUL.
        nul_addr = 0x8009 + len(b"TestROM")
        nul_class = ir.classifications.get_classification(nul_addr)
        assert isinstance(nul_class, Byte) and nul_class.length() == 1
        nul_inline = next(
            a.text for a in ir.annotations.get_for_align(nul_addr, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert "NUL terminator" in nul_inline

    def test_copyright_offset_inline_resolves_address(self, tmp_path):
        from dasmos.core.annotations import Align, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        inline = next(
            a.text for a in d.annotations.get_for_align(0x8007, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert "Offset of NUL preceding copyright" in inline
        assert "copyright at &80" in inline.lower()

    def test_binary_version_inline_emitted(self, tmp_path):
        from dasmos.core.annotations import Align, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        inline = next(
            a.text for a in d.annotations.get_for_align(0x8008, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert inline.startswith("Binary version:")

    def test_per_field_suppresses_auto_skips_only_that_field(self, tmp_path):
        # Driver suppresses the rom_type inline at &8006 only;
        # other auto-annotations (binary_version inline at &8008 etc.)
        # should still appear.
        from dasmos.core.annotations import Align, Comment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.comment(
            0x8006,
            "Custom rom_type explanation",
            align=Align.INLINE,
            suppresses_auto=True,
        )
        d.use_environment("acorn_sideways_rom")
        rom_type_inline = [
            a for a in d.annotations.get_for_align(0x8006, Align.INLINE)
            if isinstance(a, Comment)
        ]
        rom_type_texts = [c.text for c in rom_type_inline]
        # Driver text present; env's "ROM type:" auto-text absent.
        assert "Custom rom_type explanation" in rom_type_texts
        assert not any(t.startswith("ROM type: ") for t in rom_type_texts)
        # binary_version inline at &8008 is unaffected.
        bv_inline = [
            a for a in d.annotations.get_for_align(0x8008, Align.INLINE)
            if isinstance(a, Comment)
        ]
        assert any(c.text.startswith("Binary version:") for c in bv_inline)

    def test_tube_reloc_addr_labelled_when_rom_type_bit_5_set(self, tmp_path):
        # With rom_type bit 5 set, the env should label the 4 bytes
        # after the copyright NUL as ``tube_reloc_addr`` and attach
        # an inline note explaining the format.
        from dasmos.core.annotations import Align, Comment
        # Build a ROM with rom_type = &A2 (Service + Tube + 6502),
        # extra padding after copyright to fit the 4-byte field.
        rom = bytearray(self._build_rom())
        rom[6] = 0xa2
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        # tube_reloc_addr label should exist within the ROM range.
        found = False
        for addr in range(0x8000, 0x8100):
            label = d.labels.get_label(addr)
            if label is not None and "tube_reloc_addr" in label.explicit_name_texts():
                found = True
                # Inline note at the same address.
                inline = [
                    a for a in d.annotations.get_for_align(addr, Align.INLINE)
                    if isinstance(a, Comment)
                ]
                assert any("Tube relocation address" in c.text for c in inline)
                break
        assert found, "tube_reloc_addr label not registered"

    def test_tube_reloc_addr_skipped_when_bit_5_clear(self, tmp_path):
        # Default _build_rom has rom_type = &82 (no Tube bit) — no
        # tube_reloc_addr label should appear.
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        for addr in range(0x8000, 0x8100):
            label = d.labels.get_label(addr)
            if label is not None:
                assert "tube_reloc_addr" not in label.explicit_name_texts()

    def test_use_environment_kwargs_rejected_with_instance(self, tmp_path):
        # use_environment forwards kwargs to create_environment; only
        # valid with a string env name. Passing kwargs alongside an
        # already-constructed Environment instance must raise.
        from dasmos.environment import create_environment
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        instance = create_environment("acorn_sideways_rom")
        with pytest.raises(TypeError, match="forwarded"):
            d.use_environment(instance, rom_title="x")

    def test_layered_with_acorn_mos(self, tmp_path):
        # The two acorn environments compose: the labels from each
        # appear together. Sideways-rom needs activation AFTER load,
        # so it can't be in the constructor kwarg if mos is also.
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_mos")
        d.use_environment("acorn_sideways_rom")
        # acorn_mos contribution.
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        # acorn_sideways_rom contribution.
        assert "rom_header" in d.labels.get_label(0x8000).explicit_name_texts()


class TestAcornModelBHardwareEnvironment:
    """BBC Model B / B+ hardware-register Environment: registers the
    memory-mapped I/O label set for the Model B family — the shared
    BBC-line block (CRTC, ACIA, station ID, video ULA, ROMSEL, the
    two VIAs, Econet ADLC, ADC, Tube control, CUBE Tube, Fred-bus
    SCSI). FDC registers live in the orthogonal :mod:`acorn_fdc_8271`
    / :mod:`acorn_fdc_1770` envs and are NOT included here — a Model B
    can be fitted with either chip. Closes the per-operand resolution
    gap for any disassembled Model B ROM that touches hardware
    (NFS-3.65, Tube Client, Econet Bridge, …).
    """

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_model_b_hardware"],
        )

    def test_loadable_via_stevedore(self):
        env = create_environment("acorn_model_b_hardware")
        assert isinstance(env, AcornModelBHardwareEnvironment)

    def test_listed_among_environment_names(self):
        assert "acorn_model_b_hardware" in environment_names()

    def test_tube_register_labels(self):
        for addr, name in [
            (0xfee0, "tube_status_1_and_tube_control"),
            (0xfee1, "tube_data_register_1"),
            (0xfee3, "tube_data_register_2"),
            (0xfee7, "tube_data_register_4"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing tube label {name} at &{addr:04x}"
            )

    def test_system_via_register_pair(self):
        assert "system_via_orb_irb" in self.d.labels.get_label(0xfe40).explicit_name_texts()
        assert "system_via_acr" in self.d.labels.get_label(0xfe4b).explicit_name_texts()
        assert "system_via_ifr" in self.d.labels.get_label(0xfe4d).explicit_name_texts()
        assert "system_via_ier" in self.d.labels.get_label(0xfe4e).explicit_name_texts()

    def test_user_via_register_pair(self):
        assert "user_via_orb_irb" in self.d.labels.get_label(0xfe60).explicit_name_texts()
        assert "user_via_ier" in self.d.labels.get_label(0xfe6e).explicit_name_texts()

    def test_econet_adlc_labels(self):
        for addr, name in [
            (0xfea0, "econet_control1_or_status1"),
            (0xfea1, "econet_control23_or_status2"),
            (0xfea2, "econet_data_continue_frame"),
            (0xfea3, "econet_data_terminate_frame"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts()

    def test_video_ula_labels(self):
        assert "video_ula_control" in self.d.labels.get_label(0xfe20).explicit_name_texts()
        assert "video_ula_palette" in self.d.labels.get_label(0xfe21).explicit_name_texts()

    def test_romsel_label(self):
        assert "romsel" in self.d.labels.get_label(0xfe30).explicit_name_texts()

    def test_station_id_label(self):
        assert "station_id_disable_net_nmis" in (
            self.d.labels.get_label(0xfe18).explicit_name_texts()
        )

    def test_no_fdc_registers_present(self):
        # FDC choice is orthogonal — neither &FE80-&FE87 names nor
        # the 8271 reset at &FE82 should be registered by the bare
        # machine env. Activating ``acorn_fdc_8271`` /
        # ``acorn_fdc_1770`` is what supplies them. ``get_label``
        # returns ``None`` if no label has been registered, which is
        # equivalent to "no FDC name here" for our purposes.
        for addr in (0xfe80, 0xfe81, 0xfe82, 0xfe84, 0xfe85, 0xfe86, 0xfe87):
            label = self.d.labels.get_label(addr)
            if label is None:
                continue
            names = label.explicit_name_texts()
            assert not any(n.startswith("fdc_") for n in names), (
                f"Model B env unexpectedly registered an FDC label at "
                f"&{addr:04x}: {names}"
            )

    def test_composes_with_acorn_mos(self):
        d = Disassembler.create(
            cpu="6502",
            environments=["acorn_mos", "acorn_model_b_hardware"],
        )
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        assert "tube_data_register_1" in d.labels.get_label(0xfee1).explicit_name_texts()


class TestAcornMasterHardwareEnvironment:
    """BBC Master hardware-register Environment: the shared BBC-line
    register block plus the Master-only access-control register
    (ACCCON at &FE34: shadow RAM, ROM banking, IRQ steering). FDC
    registers live in the orthogonal :mod:`acorn_fdc_1770` env and
    are NOT included here. The 146818 RTC has no direct memory-mapped
    registers either; ROM code drives it through the System VIA
    (already labelled by the shared block).
    """

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_master_hardware"],
        )

    def test_loadable_via_stevedore(self):
        env = create_environment("acorn_master_hardware")
        assert isinstance(env, AcornMasterHardwareEnvironment)

    def test_listed_among_environment_names(self):
        assert "acorn_master_hardware" in environment_names()

    def test_acccon_label(self):
        assert "acccon" in self.d.labels.get_label(0xfe34).explicit_name_texts()

    def test_shared_register_labels_present(self):
        # The Master env should still register the shared BBC-line
        # block (CRTC, video ULA, system VIA, Tube, …).
        assert "crtc_address_register" in (
            self.d.labels.get_label(0xfe00).explicit_name_texts()
        )
        assert "video_ula_control" in (
            self.d.labels.get_label(0xfe20).explicit_name_texts()
        )
        assert "system_via_orb_irb" in (
            self.d.labels.get_label(0xfe40).explicit_name_texts()
        )
        assert "tube_data_register_1" in (
            self.d.labels.get_label(0xfee1).explicit_name_texts()
        )

    def test_no_fdc_registers_present(self):
        # The Master ships with the 1770, but the FDC is its own
        # composable env. The bare ``acorn_master_hardware`` env
        # does NOT label any &FE80-&FE87 address (``get_label``
        # returns ``None`` when no label is registered).
        for addr in (0xfe80, 0xfe81, 0xfe82, 0xfe84, 0xfe85, 0xfe86, 0xfe87):
            label = self.d.labels.get_label(addr)
            if label is None:
                continue
            names = label.explicit_name_texts()
            assert not any(n.startswith("fdc_") for n in names), (
                f"Master env unexpectedly registered an FDC label at "
                f"&{addr:04x}: {names}"
            )

    def test_composes_with_acorn_mos(self):
        d = Disassembler.create(
            cpu="6502",
            environments=["acorn_mos", "acorn_master_hardware"],
        )
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        assert "acccon" in d.labels.get_label(0xfe34).explicit_name_texts()


class TestAcornFdc8271Environment:
    """Intel 8271 floppy-disc-controller Environment: registers
    ``fdc_8271_command_or_status`` (&FE80), ``fdc_8271_parameter_or_result``
    (&FE81), ``fdc_8271_reset`` (&FE82) and ``fdc_8271_data`` (&FE84).
    Composable with any machine env — typically paired with
    :mod:`acorn_model_b_hardware` for original-fit Model B ROMs.
    """

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_fdc_8271"],
        )

    def test_listed_among_environment_names(self):
        assert "acorn_fdc_8271" in environment_names()

    def test_loadable_via_stevedore(self):
        env = create_environment("acorn_fdc_8271")
        # Imported lazily to avoid cluttering the module top with envs
        # that aren't asserted on elsewhere.
        from dasmos.ext.environments.acorn_fdc_8271 import (
            AcornFdc8271Environment,
        )
        assert isinstance(env, AcornFdc8271Environment)

    def test_8271_register_labels(self):
        for addr, name in [
            (0xfe80, "fdc_8271_command_or_status"),
            (0xfe81, "fdc_8271_parameter_or_result"),
            (0xfe82, "fdc_8271_reset"),
            (0xfe84, "fdc_8271_data"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing 8271 label {name} at &{addr:04x}"
            )

    def test_does_not_register_1770_labels(self):
        # &FE85-&FE87 are 1770-only; the 8271 env must not label them.
        for addr in (0xfe85, 0xfe86, 0xfe87):
            label = self.d.labels.get_label(addr)
            if label is None:
                continue
            names = label.explicit_name_texts()
            assert not any("1770" in n for n in names)

    def test_composes_with_model_b_hardware(self):
        d = Disassembler.create(
            cpu="6502",
            environments=["acorn_model_b_hardware", "acorn_fdc_8271"],
        )
        assert "fdc_8271_reset" in d.labels.get_label(0xfe82).explicit_name_texts()
        assert "tube_data_register_1" in d.labels.get_label(0xfee1).explicit_name_texts()


class TestAcornFdc1770Environment:
    """WD1770 floppy-disc-controller Environment: registers
    ``fdc_1770_drive_control`` (&FE80) and the four 1770 chip
    registers — command/status, track, sector, data — at
    &FE84-&FE87. Composable with any machine env: pair with
    :mod:`acorn_master_hardware` for Master / B+ ROMs, or
    :mod:`acorn_model_b_hardware` for retrofitted Model B images.
    """

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_fdc_1770"],
        )

    def test_listed_among_environment_names(self):
        assert "acorn_fdc_1770" in environment_names()

    def test_loadable_via_stevedore(self):
        env = create_environment("acorn_fdc_1770")
        from dasmos.ext.environments.acorn_fdc_1770 import (
            AcornFdc1770Environment,
        )
        assert isinstance(env, AcornFdc1770Environment)

    def test_1770_register_labels(self):
        for addr, name in [
            (0xfe80, "fdc_1770_drive_control"),
            (0xfe84, "fdc_1770_command_or_status"),
            (0xfe85, "fdc_1770_track"),
            (0xfe86, "fdc_1770_sector"),
            (0xfe87, "fdc_1770_data"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing 1770 label {name} at &{addr:04x}"
            )

    def test_does_not_register_8271_labels(self):
        # &FE81 / &FE82 are 8271-only; the 1770 env must not label them.
        for addr in (0xfe81, 0xfe82):
            label = self.d.labels.get_label(addr)
            if label is None:
                continue
            names = label.explicit_name_texts()
            assert not any("8271" in n for n in names)

    def test_composes_with_master_hardware(self):
        d = Disassembler.create(
            cpu="6502",
            environments=["acorn_master_hardware", "acorn_fdc_1770"],
        )
        assert "acccon" in d.labels.get_label(0xfe34).explicit_name_texts()
        assert "fdc_1770_command_or_status" in (
            d.labels.get_label(0xfe84).explicit_name_texts()
        )


class TestAcornMosOsCallHooks:
    """OSBYTE / OSWORD / OSFIND / OSFILE / OSGBPB hooks installed by
    the ``acorn_mos`` Environment. When the trace encounters a
    ``JSR <oscall>`` immediately preceded by ``LDA #imm`` (or
    ``LDX``/``LDY`` for OSGBPB / OSFILE etc.), the hook looks up
    the immediate in the call-specific enum table and:

      1. Registers a :meth:`Disassembler.constant` for the
         (value, name) pair (so it appears in the JSON
         ``constants`` section + the asm equate table).
      2. Registers an auto-expression at the LDA's operand byte
         so the rendered listing reads as ``lda #osbyte_<name>``
         instead of ``lda #&xx``.

    Mirrors py8dis-fork's ``osbyte_hook`` / ``osword_hook`` etc.
    """

    @staticmethod
    def _make(tmp_path, program: bytes, load_addr: int = 0x1000):
        """Helper: write ``program`` to a binary, load via dasmos
        with ``acorn_mos`` active, set entry at the load addr.
        """
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(program)
        d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )
        d.load(bin_path, load_addr)
        d.entry(load_addr)
        return d

    def test_osbyte_hook_installs_constant_and_expression(self, tmp_path):
        # LDA #&7c ; JSR osbyte ; RTS
        # &7c is osbyte_clear_escape
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x7c, 0x20, 0xf4, 0xff, 0x60]),
            load_addr=0x1000,
        )
        ir = d.disassemble()
        # The constant got registered.
        assert any(
            c.name == "osbyte_clear_escape" and c.value == 0x7c
            for c in ir.constants
        ), "osbyte hook did not register the constant"
        # The auto-expression at the LDA's operand byte resolves to
        # the constant name (so the rendered ``lda #&7c`` becomes
        # ``lda #osbyte_clear_escape``).
        assert ir.expressions.get_or_none(0x1001) == "osbyte_clear_escape"

    def test_osbyte_hook_unknown_value_does_nothing(self, tmp_path):
        # LDA #&20 (not in osbyte_enum) ; JSR osbyte ; RTS
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x20, 0x20, 0xf4, 0xff, 0x60]),
            load_addr=0x1000,
        )
        ir = d.disassemble()
        # No constant registered for &20.
        assert not any(c.value == 0x20 for c in ir.constants)
        # No expression at the LDA's operand byte.
        assert ir.expressions.get_or_none(0x1001) is None

    def test_osbyte_hook_no_preceding_lda_imm_does_nothing(self, tmp_path):
        # NOP ; NOP ; JSR osbyte (no LDA #imm before) ; RTS
        d = self._make(
            tmp_path,
            bytes([0xea, 0xea, 0x20, 0xf4, 0xff, 0x60]),
            load_addr=0x1000,
        )
        ir = d.disassemble()
        assert ir.constants == []

    def test_osword_hook_installs_constant_and_expression(self, tmp_path):
        # LDA #&05 ; JSR osword ; RTS
        # &05 is osword_read_io_memory
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x05, 0x20, 0xf1, 0xff, 0x60]),
            load_addr=0x1000,
        )
        ir = d.disassemble()
        assert any(
            c.name == "osword_read_io_memory" and c.value == 0x05
            for c in ir.constants
        )
        assert ir.expressions.get_or_none(0x1001) == "osword_read_io_memory"

    def test_osword_hook_recognises_xy_param_block_address(self, tmp_path):
        # OSWORD calling convention: LDA #call ; LDX #lo ; LDY #hi ;
        # JSR osword. (X,Y) form the parameter block address.
        # When the (X,Y) immediate values land at a labelled address,
        # the analyzer registers ``<(label)`` / ``>(label)`` expressions
        # at the LDX / LDY operand bytes so they render as
        # ``ldx #<(myblock)`` / ``ldy #>(myblock)`` (matches py8dis
        # ``xy_addr`` helper).
        # LDA #&00 ; LDX #&80 ; LDY #&12 ; JSR osword ; RTS
        # XY = &1280. We label &1280 as ``myblock``.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0xa2, 0x80, 0xa0, 0x12, 0x20, 0xf1, 0xff, 0x60]),
            load_addr=0x1000,
        )
        d.optional_label(0x1280, "myblock")
        ir = d.disassemble()
        # The LDX's operand at &1003 carries ``<(myblock)``.
        assert ir.expressions.get_or_none(0x1003) == "<(myblock)"
        # The LDY's operand at &1005 carries ``>(myblock)``.
        assert ir.expressions.get_or_none(0x1005) == ">(myblock)"

    def test_osword_hook_xy_no_label_does_nothing(self, tmp_path):
        # Same shape but no label at &1280 — the analyzer should
        # leave the LDX/LDY operands as literal hex (no
        # auto-expression registered).
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0xa2, 0x80, 0xa0, 0x12, 0x20, 0xf1, 0xff, 0x60]),
            load_addr=0x1000,
        )
        ir = d.disassemble()
        assert ir.expressions.get_or_none(0x1003) is None
        assert ir.expressions.get_or_none(0x1005) is None


class TestAcornMosInlineAutoComments:
    """Inline auto-comments at the JSR site for OSFIND / OSFILE /
    OSGBPB / OSEVEN. The analyzers translate the recognised action
    code to a terse description per the style guide at
    ``docs/design/auto-comment-style.md``.
    """

    @staticmethod
    def _make(tmp_path, program: bytes, load_addr: int = 0x1000):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(program)
        d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )
        d.load(bin_path, load_addr)
        d.entry(load_addr)
        return d

    @staticmethod
    def _inline_comment_at(ir, binary_addr: int) -> str | None:
        """Return the inline-comment text at ``binary_addr`` (or
        None). Multiple inline comments at the same address are not
        expected here.
        """
        from dasmos.core.annotations import Align, Comment
        anns = ir.annotations.get_for_align(binary_addr, Align.INLINE)
        for ann in anns:
            if isinstance(ann, Comment):
                return ann.text
        return None

    def test_osfind_open_for_input_attaches_inline_comment(self, tmp_path):
        # LDA #&40 ; JSR osfind ; RTS — A=&40 is osfind_open_input.
        # JSR opcode lands at binary &1002.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x40, 0x20, 0xce, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "osfind: open file for input"
        )

    def test_osfind_close_attaches_inline_comment(self, tmp_path):
        # LDA #&00 ; JSR osfind ; RTS — A=0 is osfind_close.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0x20, 0xce, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "osfind: close one or all files"
        )

    def test_osfile_save_attaches_inline_comment(self, tmp_path):
        # LDA #&00 ; JSR osfile ; RTS — A=0 is osfile_save.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0x20, 0xdd, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "osfile: save block of memory"
        )

    def test_osgbpb_read_filenames_attaches_inline_comment(self, tmp_path):
        # LDA #&08 ; JSR osgbpb ; RTS — A=8 is read filenames.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x08, 0x20, 0xd1, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "osgbpb: read filenames in current directory"
        )

    def test_oseven_known_event_attaches_inline_comment(self, tmp_path):
        # LDY #&04 ; JSR oseven ; RTS — Y=4 is vsync.
        d = self._make(
            tmp_path,
            bytes([0xa0, 0x04, 0x20, 0xbf, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == "oseven: vsync"

    def test_oseven_unknown_event_attaches_no_inline_comment(self, tmp_path):
        # LDY #&20 (not in EVENT_ENUM) ; JSR oseven ; RTS.
        # The analyzer skips entirely — no inline comment.
        d = self._make(
            tmp_path,
            bytes([0xa0, 0x20, 0x20, 0xbf, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) is None

    def test_unrecognised_a_value_attaches_no_inline_comment(self, tmp_path):
        # LDA #&55 (not in OSFIND_ENUM) ; JSR osfind ; RTS.
        # Style guide §5.4: when the analyzer can't say anything
        # specific, say nothing.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x55, 0x20, 0xce, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) is None

    def test_no_preceding_lda_attaches_no_inline_comment(self, tmp_path):
        # NOP ; NOP ; JSR osfind ; RTS — A is unknown at the JSR.
        d = self._make(
            tmp_path,
            bytes([0xea, 0xea, 0x20, 0xce, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) is None

    def test_osbyte_attaches_descriptive_inline_comment(self, tmp_path):
        # LDA #&7c ; JSR osbyte ; RTS — &7c is osbyte_clear_escape.
        # When ``OSBYTE_DESCRIPTIONS`` has an entry for the call
        # number, the analyzer uses that long descriptive phrase
        # verbatim — the call is already named on the preceding
        # ``LDA #osbyte_clear_escape`` line via the registered
        # constant, so a redundant "osbyte:" prefix here would just
        # repeat context the reader already has.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x7c, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "Clear escape condition (no further escape effects)"
        )

    def test_osword_attaches_descriptive_inline_comment(self, tmp_path):
        # LDA #&05 ; JSR osword ; RTS — &05 is osword_read_io_memory.
        # ``OSWORD_DESCRIPTIONS`` provides the long descriptive
        # phrase; same reasoning as the OSBYTE test above.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x05, 0x20, 0xf1, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "Read byte of I/O processor memory"
        )

    def test_osbyte_x_value_specific_inline_takes_precedence(self, tmp_path):
        # LDA #&14 ; LDX #&06 ; JSR osbyte ; RTS — A=&14 is OSBYTE
        # &14 (Implode/Explode chars), X=&06 selects the "six extra
        # pages" variant. The X-value-specific description is
        # strictly more specific than the bare OSBYTE description,
        # so the analyzer prefers it.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x14, 0xa2, 0x06, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        # JSR is at 0x1004 (after LDA #&14 at 0x1000 + LDX #&06 at 0x1002).
        comment = self._inline_comment_at(ir, 0x1004)
        assert comment is not None
        assert "six extra pages" in comment, comment
        assert "redefine all characters 32-255" in comment, comment

    def test_osbyte_x_unknown_falls_back_to_base_description(self, tmp_path):
        # LDA #&14 ; JSR osbyte ; RTS — X is unknown, so the per-X
        # table can't apply. Fall back to the base description.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x14, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) == (
            "Implode or Explode character definition RAM based on X"
        )

    def test_osbyte_post_call_description_attached_at_next_instruction(
        self, tmp_path,
    ):
        # LDA #&86 ; JSR osbyte ; STX foo ; RTS — OSBYTE &86 returns
        # POS in X / VPOS in Y. The post-call descriptions for X and
        # Y get joined and attached as an inline comment at the
        # instruction immediately after the JSR (the STX line).
        d = self._make(
            tmp_path,
            # LDA #&86      a9 86
            # JSR &fff4     20 f4 ff
            # STX foo       8e 00 20
            # RTS           60
            bytes([0xa9, 0x86, 0x20, 0xf4, 0xff, 0x8e, 0x00, 0x20, 0x60]),
        )
        ir = d.disassemble()
        # The post-call comment goes on the STX line at 0x1005.
        comment = self._inline_comment_at(ir, 0x1005)
        assert comment is not None
        assert "horizontal text position" in comment, comment
        assert "vertical text position" in comment, comment

    def test_osbyte_post_call_does_not_clobber_driver_inline(self, tmp_path):
        # If the driver has already attached an inline comment at the
        # next instruction, the post-call description must NOT
        # overwrite it. Driver-supplied annotations always win.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x86, 0x20, 0xf4, 0xff, 0x8e, 0x00, 0x20, 0x60]),
        )
        # Pre-register an inline comment at 0x1005 (the STX) BEFORE
        # disassemble.
        from dasmos.core.annotations import Align
        d.comment(0x1005, "Driver-owned comment", align=Align.INLINE)
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1005) == "Driver-owned comment"

    def test_osbyte_zero_emits_post_call_x_value_table(self, tmp_path):
        # LDA #&00 ; LDX #&01 ; JSR osbyte ; STX foo ; RTS — OSBYTE
        # &00 reads the OS version into X. The post-call table
        # documents every possible X-value (OS 1.00 / 1.20 /
        # 2.00 / 3.2 / 4.0 / 5.0). Renders as a Markdown table
        # attached as a preamble (BEFORE_LINE) at the JSR site so
        # the call and its return-value mapping read together as one
        # top-down block.
        d = self._make(
            tmp_path,
            # LDA #&00      a9 00
            # LDX #&01      a2 01
            # JSR &fff4     20 f4 ff
            # STX foo       8e 00 20
            # RTS           60
            bytes([0xa9, 0x00, 0xa2, 0x01, 0x20, 0xf4, 0xff,
                   0x8e, 0x00, 0x20, 0x60]),
        )
        ir = d.disassemble()
        # The post-call table now anchors at the JSR site itself
        # (0x1004) with Align.BEFORE_LINE — preamble to the call.
        from dasmos.core.annotations import Align, Comment
        bucket = ir.annotations.get_for_align(0x1004, Align.BEFORE_LINE)
        comments = [a for a in bucket if isinstance(a, Comment)]
        assert comments, "expected a post-call value-table comment"
        # The Markdown table includes every X-value description.
        joined = "\n".join(c.text for c in comments)
        assert "American" in joined
        assert "Master 128" in joined
        assert "Master Compact" in joined
        assert "On return, X is the OS version number" in joined
        # Markdown header row present.
        assert "| X | Meaning |" in joined

    def test_osargs_per_a_y_inline_text(self, tmp_path):
        # LDA #&01 ; LDY #&05 ; JSR osargs ; RTS — A=1, Y!=0:
        # "Write sequential file pointer ...".
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x01, 0xa0, 0x05, 0x20, 0xda, 0xff, 0x60]),
        )
        # Register osargs at &FFDA.
        d.label(0xffda, "osargs")
        ir = d.disassemble()
        comment = self._inline_comment_at(ir, 0x1004)
        assert comment is not None
        assert "Write sequential file pointer" in comment

    def test_osargs_a0_y0_emits_fs_number_table(self, tmp_path):
        # LDA #&00 ; LDY #&00 ; JSR osargs ; STA foo ; RTS — A=0
        # Y=0 returns the filing-system number in A. Post-call table
        # is the FS-number list, attached as a preamble (BEFORE_LINE)
        # at the JSR site.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0xa0, 0x00, 0x20, 0xda, 0xff,
                   0x8d, 0x00, 0x20, 0x60]),
        )
        d.label(0xffda, "osargs")
        ir = d.disassemble()
        from dasmos.core.annotations import Align, Comment
        bucket = ir.annotations.get_for_align(0x1004, Align.BEFORE_LINE)
        comments = [a for a in bucket if isinstance(a, Comment)]
        assert comments
        joined = "\n".join(c.text for c in comments)
        assert "On return, A is the filing system number" in joined
        assert "Network filing system" in joined
        assert "Teletext filing system" in joined
        assert "IEEE filing system" in joined
        assert "Videodisc filing system" in joined
        assert "1200 baud" in joined

    def test_post_call_table_suppressed_by_driver_authoritative_comment(
        self, tmp_path,
    ):
        # When the driver attaches a Comment at the JSR site with
        # suppresses_auto=True, the env's auto post-call table must
        # not be emitted — the driver is asserting authority over
        # this call's documentation.
        from dasmos.core.annotations import Align, Comment
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x00, 0xa2, 0x01, 0x20, 0xf4, 0xff,
                   0x8e, 0x00, 0x20, 0x60]),
        )
        # Driver's authoritative note crowds out the auto-generated
        # OS-version table. The note can sit at any align — the
        # suppression check is align-agnostic at the JSR address.
        d.comment(
            0x1004,
            "version handled inline below",
            align=Align.BEFORE_LINE,
            suppresses_auto=True,
        )
        ir = d.disassemble()
        bucket = ir.annotations.get_for_align(0x1004, Align.BEFORE_LINE)
        comments = [a for a in bucket if isinstance(a, Comment)]
        texts = [c.text for c in comments]
        # Driver comment present, env auto-table absent.
        assert "version handled inline below" in texts
        assert not any(
            "On return, X is the OS version number" in t for t in texts
        )

    def test_post_call_descriptions_suppressed_by_driver_at_jsr(
        self, tmp_path,
    ):
        # OSBYTE &7F (read EOF) ships an inline post-call description
        # ("X=0 means EOF reached, X=&FF means data remaining")
        # attached to the consumer instruction. The driver suppresses
        # it by putting suppresses_auto=True at the JSR address.
        from dasmos.core.annotations import Align, Comment
        d = self._make(
            tmp_path,
            # LDA #&7f ; LDY #&05 ; JSR osbyte ; STX foo ; RTS
            bytes([0xa9, 0x7f, 0xa0, 0x05, 0x20, 0xf4, 0xff,
                   0x8e, 0x00, 0x20, 0x60]),
        )
        d.comment(
            0x1004,
            "EOF check inlined",
            align=Align.BEFORE_LINE,
            suppresses_auto=True,
        )
        ir = d.disassemble()
        # Auto inline description would normally land at 0x1007 (the
        # STX consumer); with the driver's crowd-out it must not.
        bucket = ir.annotations.get_for_align(0x1007, Align.INLINE)
        texts = [a.text for a in bucket if isinstance(a, Comment)]
        assert not any("EOF reached" in t for t in texts)

    def test_analyser_inline_stacks_alongside_driver_inline(self, tmp_path):
        # The OSARGS analyser's "Write sequential file pointer ..."
        # text should stack alongside a driver-supplied inline
        # comment at the same address. Both get emitted by the
        # renderer (joined with "  ").
        from dasmos.core.annotations import Align
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x01, 0xa0, 0x05, 0x20, 0xda, 0xff, 0x60]),
        )
        d.label(0xffda, "osargs")
        d.comment(0x1004, "OSARGS: set file pointer", align=Align.INLINE)
        ir = d.disassemble()
        # Both annotations should be present at 0x1004.
        from dasmos.core.annotations import Comment
        bucket = ir.annotations.get_for_align(0x1004, Align.INLINE)
        comments = [a for a in bucket if isinstance(a, Comment)]
        texts = [c.text for c in comments]
        assert "OSARGS: set file pointer" in texts
        assert any("Write sequential file pointer" in t for t in texts)

    def test_osbyte_falls_back_to_prefix_when_no_description(self, tmp_path):
        # When ``OSBYTE_DESCRIPTIONS`` has no entry for the call,
        # the analyzer falls back to the mechanical
        # ``osbyte: <name-stripped>`` form. OSBYTE &b0 has an enum
        # entry but no description — exercises the fallback.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0xb0, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        # &b0 → osbyte_read_write_cfs_timeout → "read write cfs timeout"
        comment = self._inline_comment_at(ir, 0x1002)
        assert comment is not None and comment.startswith("osbyte:")

    def test_osbyte_unknown_value_attaches_no_inline_comment(self, tmp_path):
        # LDA #&20 (not in OSBYTE_ENUM) ; JSR osbyte ; RTS — same
        # silent-on-unknown rule as the smaller analyzers.
        d = self._make(
            tmp_path,
            bytes([0xa9, 0x20, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1002) is None


class TestAcornMosInkeyHint:
    """OSBYTE &79 / &81 INKEY auto-detection: when X's high bit is
    set AND ``(255 - X) EOR 128`` matches a named INKEY scan code,
    the analyser registers an ``inkey_key_<name>`` constant and
    tags the LDX operand with :class:`FormatHint.INKEY` so the
    renderer emits ``(255 - inkey_key_<name>) EOR 128``.
    """

    @staticmethod
    def _make(tmp_path, program: bytes, load_addr: int = 0x1000):
        bin_path = tmp_path / "p.bin"
        bin_path.write_bytes(program)
        d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )
        d.load(bin_path, load_addr)
        d.entry(load_addr)
        return d

    @staticmethod
    def _inline_comment_at(ir, binary_addr: int) -> str | None:
        from dasmos.core.annotations import Align, Comment
        anns = ir.annotations.get_for_align(binary_addr, Align.INLINE)
        for ann in anns:
            if isinstance(ann, Comment):
                return ann.text
        return None

    def test_osbyte_81_with_ctrl_attaches_inkey_aware_inline(self, tmp_path):
        # When the INKEY pattern fires, the JSR-site inline replaces
        # the bare ``osbyte: inkey`` description with one that names
        # the specific key — strictly more informative.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x81, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        # JSR is at 0x1004 (LDX at 0x1000 + LDA at 0x1002).
        assert self._inline_comment_at(ir, 0x1004) == (
            "Test for ctrl key pressed"
        )

    def test_osbyte_79_with_keypad_4_uses_spaced_bare_name(self, tmp_path):
        # The bare-name strip replaces underscores with spaces so
        # multi-token names read as English.
        # X = (255 - 123) EOR 128 = 132 ^ 128 = 4 — wait, recompute:
        # inkey_key_keypad_4 = -123 & 0xff = 133. X byte =
        # (255 - 133) EOR 128 = 122 EOR 128 = 0xfa.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0xfa, 0xa9, 0x79, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert self._inline_comment_at(ir, 0x1004) == (
            "Test for keypad 4 key pressed"
        )

    def test_osbyte_81_with_low_x_falls_back_to_bare_inline(self, tmp_path):
        # Without the high bit on X, the call ISN'T an INKEY scan;
        # the inline must be the generic OSBYTE description, not
        # the INKEY-aware override.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x20, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        comment = self._inline_comment_at(ir, 0x1004)
        # Whatever the OSBYTE-&81 bare description says, it must
        # NOT name a specific INKEY key.
        assert comment is not None
        assert "Test for" not in comment
        assert "key pressed" not in comment

    def test_osbyte_81_with_ctrl_registers_hint_and_constant(self, tmp_path):
        # LDX #&81 ; LDA #&81 ; JSR osbyte ; RTS
        # X=&81 decodes to inkey_key_ctrl: (255 - 0x81) EOR 0x80 =
        # 0xfe = 254 (the unsigned form of -2 from py8dis's
        # inkey_enum). LDX's operand byte is at 0x1001.
        from dasmos.core.format_hint import FormatHint
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x81, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        # FormatHint.INKEY was attached at the LDX operand.
        assert ir.format_hints.get_or_none(0x1001) is FormatHint.INKEY
        # Constant registered with the unsigned-form value (254) so
        # the equate `inkey_key_ctrl = 254` makes
        # `(255 - inkey_key_ctrl) EOR 128` reduce to byte &81.
        names = [(c.name, c.value) for c in d.constants]
        assert ("inkey_key_ctrl", 254) in names

    def test_osbyte_79_with_shift_registers_hint(self, tmp_path):
        # LDX #&80 ; LDA #&79 ; JSR osbyte ; RTS
        # X=&80 → inkey_key = (255 - 0x80) EOR 0x80 = 0x7f EOR 0x80
        # = 0xff = 255 = inkey_key_shift (-1 & 0xff).
        from dasmos.core.format_hint import FormatHint
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x80, 0xa9, 0x79, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x1001) is FormatHint.INKEY
        names = [(c.name, c.value) for c in d.constants]
        assert ("inkey_key_shift", 255) in names

    def test_osbyte_81_with_x_low_bit_no_inkey_hint(self, tmp_path):
        # LDX #&20 ; LDA #&81 ; JSR osbyte ; RTS — X<&80 is the
        # "wait for any key with timeout" mode, NOT the negative-
        # scan-code mode. Analyser must NOT register an INKEY hint.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x20, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x1001) is None

    def test_unrelated_osbyte_does_not_trigger_inkey_hint(self, tmp_path):
        # LDX #&81 ; LDA #&7c ; JSR osbyte ; RTS — A=&7c is
        # osbyte_clear_escape, not in {&79, &81}. The X value
        # happens to look like an INKEY byte but the call isn't
        # one, so no hint must be attached.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x81, 0xa9, 0x7c, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x1001) is None

    def test_osbyte_81_with_unmapped_high_bit_value_no_hint(self, tmp_path):
        # X=&ff decodes to inkey_key = (255 - 0xff) EOR 0x80 = 0x80
        # = 128, which has no named INKEY entry (the BBC's INKEY
        # table runs -1..-125; -128 is outside the range). Analyser
        # must skip silently — better to leave the operand as a
        # plain hex literal than to emit a misleading symbol.
        d = self._make(
            tmp_path,
            bytes([0xa2, 0xff, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x1001) is None

    def test_driver_expr_wins_over_inkey_auto_detection(self, tmp_path):
        # If a driver has already registered an explicit expression
        # at the LDX operand byte, the INKEY analyser must NOT
        # override it — driver intent wins.
        from dasmos.core.format_hint import FormatHint
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x81, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        d.expr(0x1001, "my_special_key_byte")
        ir = d.disassemble()
        # Driver expression preserved; no FormatHint registered.
        assert ir.format_hints.get_or_none(0x1001) is None

    def test_renderer_emits_symbolic_inkey_form(self, tmp_path):
        # End-to-end: the rendered LDX line should read
        # ``ldx #(255 - inkey_key_ctrl) EOR 128`` (modulo case).
        from dasmos.ext.renderers.beebasm.renderer import BeebasmRenderer
        d = self._make(
            tmp_path,
            bytes([0xa2, 0x81, 0xa9, 0x81, 0x20, 0xf4, 0xff, 0x60]),
        )
        ir = d.disassemble()
        renderer = BeebasmRenderer()
        text = str(renderer.render(ir))
        assert "(255 - inkey_key_ctrl) EOR 128" in text, text

    def test_inkey_code_sugar_attaches_hint(self, tmp_path):
        # d.inkey_code(addr) is the explicit driver hook for cases
        # where the analyser can't infer the pattern (e.g. byte in
        # a table, indirect load through ZP). It must register the
        # hint without any nearby JSR osbyte context.
        from dasmos.core.format_hint import FormatHint
        d = self._make(
            tmp_path,
            # LDX #&81 ; RTS — no surrounding OSBYTE call.
            bytes([0xa2, 0x81, 0x60]),
        )
        d.inkey_code(0x1001)
        ir = d.disassemble()
        assert ir.format_hints.get_or_none(0x1001) is FormatHint.INKEY

    def test_format_hint_inkey_unmapped_byte_falls_back_with_warning(
        self, tmp_path,
    ):
        # When a driver registers FormatHint.INKEY at a byte that
        # doesn't decode to any named INKEY key, the renderer must
        # emit a warning and fall back to a hex literal — never
        # produce a broken or misleading symbolic form.
        import warnings as _warnings
        from dasmos.ext.renderers.beebasm.renderer import BeebasmRenderer
        d = self._make(
            tmp_path,
            # LDX #&55 ; RTS — &55 has high bit clear so it's
            # outside the INKEY domain entirely; with the explicit
            # hint, the renderer warns + falls back.
            bytes([0xa2, 0x55, 0x60]),
        )
        d.inkey_code(0x1001)
        ir = d.disassemble()
        renderer = BeebasmRenderer()
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            text = str(renderer.render(ir))
        assert any(
            "FormatHint.INKEY" in str(w.message) for w in caught
        ), [str(w.message) for w in caught]
        # Falls back to a hex literal — &55 appears verbatim in the
        # rendered LDX line.
        assert "ldx #&55" in text.lower(), text
