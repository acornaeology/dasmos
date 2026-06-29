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
from dasmos.exceptions import DasmosError
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


class TestAcornMosOsbyteNameDeprecation:
    """The long-form OSBYTE names (``osbyte_read_write_*``,
    ``osbyte_select_main_or_shadow_memory_for_*`` …) were shortened
    in dasmos 1.7.0 per issue #23. Drivers that still spell the old
    names through ``d.constant()`` get a :class:`DeprecationWarning`
    pointing at the new short name; the constant still registers
    under the old name so rendered output remains valid.
    """

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="6502", environments=["acorn_mos"],
        )

    def test_old_long_name_emits_deprecation_warning(self):
        # OSBYTE &FF was ``osbyte_read_write_startup_options`` →
        # ``osbyte_startup_options``. A driver still using the old
        # name should be warned and pointed at the new one.
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.d.constant(0xFF, "osbyte_read_write_startup_options")
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecations) == 1
        msg = str(deprecations[0].message)
        assert "osbyte_read_write_startup_options" in msg
        assert "osbyte_startup_options" in msg

    def test_new_short_name_is_silent(self):
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.d.constant(0xFF, "osbyte_startup_options")
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecations == []

    def test_unrelated_name_is_silent(self):
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.d.constant(0x42, "completely_unrelated_constant")
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecations == []

    def test_deprecated_constant_still_registers_under_old_name(self):
        # The compatibility contract: drivers using the old name keep
        # getting valid output. The warning is the only behavioural
        # change.
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.d.constant(0xFF, "osbyte_read_write_startup_options")
        names = [c.name for c in self.d._constants]
        assert "osbyte_read_write_startup_options" in names

    def test_deprecated_aliases_table_targets_exist_in_enum(self):
        # Consistency check: every replacement name in the alias
        # table must actually be present as a current value in
        # OSBYTE_ENUM — otherwise the warning would steer drivers
        # toward a name dasmos no longer recognises.
        from dasmos.ext.environments.acorn_mos.enums import (
            OSBYTE_DEPRECATED_NAMES,
            OSBYTE_ENUM,
        )
        current_names = set(OSBYTE_ENUM.values())
        for old, new in OSBYTE_DEPRECATED_NAMES.items():
            assert new in current_names, (
                f"deprecated {old!r} points at {new!r}, which is not "
                f"a current OSBYTE_ENUM value"
            )
            assert old not in current_names, (
                f"{old!r} is in both OSBYTE_DEPRECATED_NAMES (as "
                f"deprecated) AND OSBYTE_ENUM (as current); pick one"
            )


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
        # language_entry at &8000 — sole structural label at the
        # header (the redundant ``rom_header`` alias was dropped in #17 §1).
        assert "language_entry" in d.labels.get_label(0x8000).explicit_name_texts()
        assert "rom_header" not in d.labels.get_label(0x8000).explicit_name_texts()
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
        # (``copyright - language_entry``, per #17 §1); the renderer
        # should emit that expression instead of the literal hex value.
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        text = str(d.disassemble().render("beebasm"))
        assert "copyright - language_entry" in text

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
        # Banner attaches at BEFORE_LABEL (#17 §2) so the heading
        # sits ABOVE the ``.language_entry`` label rather than
        # between the label and the data line.
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(
            tmp_path, self._build_rom(language_jmp=True),
        )
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8000, Align.BEFORE_LABEL)
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
            a for a in d.annotations.get_for_align(0x8000, Align.BEFORE_LABEL)
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
            a for a in d.annotations.get_for_align(0x8000, Align.BEFORE_LABEL)
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

    def test_rom_identification_section_banner_at_8006(self, tmp_path):
        # New BEFORE_LABEL banner introduces the descriptive-fields
        # section (rom_type / copyright_offset / binary_version /
        # title / version / copyright) — gives the same structural
        # separation the entry-slot banners give for the JMPs above
        # (#17 §4). Title is "ROM identification" — chosen to read
        # cleanly in the website TOC alongside the existing slot
        # banners.
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8006, Align.BEFORE_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners, "expected ROM-identification section banner at &8006"
        assert banners[0].title == "ROM identification"
        body = banners[0].description
        # Banner introduces the six fields by name.
        assert "ROM type flag byte" in body
        assert "copyright" in body
        # The pre-existing rom_type bit-decode banner (#13) still
        # attaches at AFTER_LABEL on the same address — both
        # coexist (one at BEFORE_LABEL, one at AFTER_LABEL).
        after_label = [
            a for a in d.annotations.get_for_align(0x8006, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        ]
        assert after_label and after_label[0].title == "ROM type byte"

    def test_service_entry_banner_at_8003(self, tmp_path):
        # JMP-mode service entry: banner gives the dispatch contract
        # without restating "byte 0 is &4C" (which would just echo
        # the next disassembly line). Banner attaches at BEFORE_LABEL
        # (#17 §3) so it sits ABOVE ``.service_entry``.
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8003, Align.BEFORE_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners
        body = banners[0].description
        assert "service-call" in body.lower()
        # §4: redundant "Byte 0 is &4C" line dropped from JMP-mode.
        assert "Byte 0 is" not in body

    def test_rom_type_inline_is_short_label(self, tmp_path):
        # The byte's inline is just "ROM type" — per-bit decode lives
        # in the AFTER_LABEL banner above the equb (#13).
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

    def test_rom_type_banner_attaches_after_label_with_title(self, tmp_path):
        # _build_rom sets rom_type = &82 (Service entry + 6502-non-BASIC).
        # The bit-decode banner attaches at AFTER_LABEL (between the
        # ``.rom_type`` label and the equb) so reading-order documents
        # the bits BEFORE their value, and so the JSON path serialises
        # it as a real banner record (which downstream consumers
        # render as a sub-header card with full Markdown processing)
        # rather than a comments_after row treated as plain text (#13).
        # The short title parallels the language-/service-entry banners
        # so the website TOC surfaces all three header sections.
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(tmp_path, self._build_rom())
        d.use_environment("acorn_sideways_rom")
        banners = [
            a for a in d.annotations.get_for_align(0x8006, Align.AFTER_LABEL)
            if isinstance(a, Banner)
        ]
        assert banners
        assert banners[0].title == "ROM type byte"
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
        # No competing AFTER_LINE banner left over from the previous
        # alignment (#13 explicitly moved the bit decode out of
        # comments_after so the JSON consumer can promote it).
        assert not [
            a for a in d.annotations.get_for_align(0x8006, Align.AFTER_LINE)
            if isinstance(a, Banner)
        ]

    def test_rom_type_table_decodes_all_flags_set(self, tmp_path):
        from dasmos.core.annotations import Align, Banner
        rom = bytearray(self._build_rom())
        rom[6] = 0xf8  # all four flags + Z80
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        body = next(
            a.description for a in d.annotations.get_for_align(0x8006, Align.AFTER_LABEL)
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
            a.description for a in d.annotations.get_for_align(0x8006, Align.AFTER_LABEL)
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

    def test_title_without_embedded_nul_renders_as_single_equs(
        self, tmp_path,
    ):
        # NFS-style ROMs have title "NET" (3 bytes) with copyright_offset
        # = &0C, so the byte at &800C is the copyright leading-NUL and
        # acts as the title's implicit terminator. The title field
        # itself contains no &00. The env must NOT split off the last
        # title byte as "NUL terminator" — that mislabels the 'T' byte
        # (#12 regression). Classify the whole title as a single
        # String with no NUL split or inline.
        from dasmos.core.annotations import Align, Comment
        from dasmos.core.classification import Byte, String
        # Hand-built ROM mirroring NFS layout: title "NET" at &8009-B,
        # copyright_offset = &0C so the implicit terminator is &800C.
        rom = bytearray()
        rom += bytes([0x00, 0x00, 0x00])      # &8000: language disabled
        rom += bytes([0x4c, 0x14, 0x80])      # &8003: service JMP &8014
        rom += bytes([0x82])                  # &8006: rom_type
        rom += bytes([0x0C])                  # &8007: copyright_offset
        rom += bytes([0x10])                  # &8008: binary_version
        rom += b"NET"                         # &8009-B: title (no NUL!)
        rom += b"\x00(C)X\x00"                # &800C: leading NUL +
                                              #        copyright + NUL
        while len(rom) < 0x14:
            rom += bytes([0xff])
        rom += bytes([0xea, 0xea, 0x60])      # service handler
        while len(rom) < 0x100:
            rom += bytes([0xff])
        d = self._make_loaded_disassembler(tmp_path, bytes(rom))
        d.use_environment("acorn_sideways_rom")
        ir = d.disassemble()
        # Title is a single String covering all 3 bytes, NOT split.
        title_class = ir.classifications.get_classification(0x8009)
        assert isinstance(title_class, String)
        assert title_class.length() == 3
        # &800B (the 'T') must NOT be a separate Byte classification.
        # It sits inside the title String above, so the store returns
        # the INSIDE_A_CLASSIFICATION sentinel rather than a fresh
        # classification object.
        from dasmos.core.disassembly import INSIDE_A_CLASSIFICATION
        assert (
            ir.classifications.get_classification(0x800b)
            is INSIDE_A_CLASSIFICATION
        )
        # &800B must NOT carry a "NUL terminator" inline — the 'T'
        # byte is text, not a NUL.
        inlines = [
            a.text for a in ir.annotations.get_for_align(0x800b, Align.INLINE)
            if isinstance(a, Comment)
        ]
        assert not any("NUL terminator" in t for t in inlines)
        # The actual copyright leading-NUL at &800C still gets its
        # own Byte + "NUL preceding copyright string" inline as
        # before — that field IS terminated correctly.
        cp_class = ir.classifications.get_classification(0x800c)
        assert isinstance(cp_class, Byte) and cp_class.length() == 1
        cp_inline = next(
            a.text for a in ir.annotations.get_for_align(0x800c, Align.INLINE)
            if isinstance(a, Comment)
        )
        assert "NUL preceding copyright" in cp_inline

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
        assert "language_entry" in d.labels.get_label(0x8000).explicit_name_texts()

    # --- inline-code entry slots: language_entry / service_entry kwargs (#26)

    @staticmethod
    def _build_inline_code_rom():
        """A ROM whose language entry is inline code, not a ``JMP abs``
        — the BBC BASIC II shape. &8000 = ``CMP #1 / BEQ +&1f / RTS /
        NOP``; ``rom_type`` = &40 (language bit set, service bit clear).
        The service slot at &8003 is therefore the *tail* of the
        language code, not a separate entry.
        """
        rom = bytearray(
            TestAcornSidewaysRom._build_rom(
                language_jmp=True, service_jmp=True,
            )
        )
        rom[0x0000:0x0006] = bytes([0xc9, 0x01, 0xf0, 0x1f, 0x60, 0xea])
        rom[0x0006] = 0x40  # language bit set, service + tube clear
        return bytes(rom)

    def test_language_entry_code_seeds_trace_and_renders_as_code(
        self, tmp_path,
    ):
        from dasmos.cpu import Opcode
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        d.use_environment(
            "acorn_sideways_rom",
            language_entry="code", service_entry="none",
        )
        ir = d.disassemble()
        # &8000 is a decoded instruction (CMP), not a 3-byte equb blob.
        assert isinstance(ir.classifications.get_classification(0x8000), Opcode)
        text = str(ir.render("beebasm"))
        assert "cmp #1" in text
        # The bytes are unchanged — still the language_entry label.
        assert "language_entry" in d.labels.get_label(0x8000).explicit_name_texts()

    def test_language_entry_code_adds_no_handler_label(self, tmp_path):
        # Inline code has no JMP target, so there is no
        # language_handler — that label only makes sense in JMP mode.
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        d.use_environment("acorn_sideways_rom", language_entry="code")
        for addr in range(0x8000, 0x8100):
            label = d.labels.get_label(addr)
            if label is not None:
                assert "language_handler" not in label.explicit_name_texts()

    def test_service_entry_none_skips_label_classify_and_banner(
        self, tmp_path,
    ):
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        d.use_environment(
            "acorn_sideways_rom",
            language_entry="code", service_entry="none",
        )
        # No service_entry label planted mid-instruction at &8003.
        label = d.labels.get_label(0x8003)
        if label is not None:
            assert "service_entry" not in label.explicit_name_texts()
        # No env service banner at &8003.
        assert not [
            a for a in d.annotations.get_for_align(0x8003, Align.BEFORE_LABEL)
            if isinstance(a, Banner)
        ]
        # The trace (from the language inline code) owns &8003 as part
        # of the BEQ instruction — the env did not force it to data.
        ir = d.disassemble()
        from dasmos.core.classification import Byte
        c8002 = ir.classifications.get_classification(0x8002)
        from dasmos.cpu import Opcode
        assert isinstance(c8002, Opcode)  # BEQ at 8002 covers 8002-8003

    def test_language_entry_code_banner_describes_inline_code(self, tmp_path):
        from dasmos.core.annotations import Align, Banner
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        d.use_environment("acorn_sideways_rom", language_entry="code")
        banner = next(
            a for a in d.annotations.get_for_align(0x8000, Align.BEFORE_LABEL)
            if isinstance(a, Banner)
        )
        body = banner.description.lower()
        assert "inline code" in body
        # Still carries the language reason-code contract.
        assert "normal startup" in body

    def test_invalid_entry_mode_raises(self, tmp_path):
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        with pytest.raises(DasmosError, match="language_entry"):
            d.use_environment("acorn_sideways_rom", language_entry="bogus")

    def test_default_auto_mode_unchanged_for_non_jmp_slot(self, tmp_path):
        # Regression guard: with the default "auto" mode, a non-JMP,
        # non-sentinel slot is still classified as a single 3-byte
        # data block (the pre-#26 behaviour), NOT seeded as code.
        from dasmos.core.classification import Byte
        d = self._make_loaded_disassembler(
            tmp_path, self._build_inline_code_rom(),
        )
        d.use_environment("acorn_sideways_rom")  # auto
        ir = d.disassemble()
        c = ir.classifications.get_classification(0x8000)
        assert isinstance(c, Byte) and c.length() == 3


class TestBbcBasic6502Environment:
    """BBC BASIC (6502) language environment: registers the packed
    5-byte floating-point data type (``bbc_float5``) used for BASIC's
    REAL constants. The decoder is verified against the real BBC
    BASIC II ROM constants.
    """

    # Real packed bytes from the BBC BASIC II ROM, with their known
    # mathematical values. (exponent + 4 mantissa bytes, big-endian.)
    _KNOWN = [
        (0xAAE4, bytes([0x82, 0x2d, 0xf8, 0x54, 0x58]), 2.718281828, "e"),
        (0xAA63, bytes([0x81, 0x49, 0x0f, 0xda, 0xa2]), 1.570796327, "pi/2"),
        (0xA86E, bytes([0x80, 0x31, 0x72, 0x17, 0xf8]), 0.6931471806, "ln2"),
        (0xA869, bytes([0x7f, 0x5e, 0x5b, 0xd8, 0xaa]), 0.4342944819, "log10e"),
        (0xAA59, bytes([0x81, 0xc9, 0x10, 0x00, 0x00]), -1.570800781, "-pi/2"),
    ]

    def test_registered_and_discoverable(self):
        from dasmos.environment import environment_names
        assert "bbc_basic_6502" in environment_names()

    def test_decode_matches_known_rom_constants(self):
        from dasmos.ext.environments.bbc_basic_6502 import decode_bbc_float5
        for _addr, raw, expected, label in self._KNOWN:
            got = decode_bbc_float5(raw)
            assert got == pytest.approx(expected, rel=1e-7), (
                f"{label}: decoded {got!r}, expected ~{expected}"
            )

    def test_decode_zero_exponent_is_zero(self):
        from dasmos.ext.environments.bbc_basic_6502 import decode_bbc_float5
        assert decode_bbc_float5(bytes([0, 0, 0, 0, 0])) == 0.0

    def test_decode_wrong_length_raises(self):
        from dasmos.ext.environments.bbc_basic_6502 import decode_bbc_float5
        with pytest.raises(ValueError, match="5 bytes"):
            decode_bbc_float5(bytes([0x82, 0x2d, 0xf8]))

    def test_use_environment_registers_named_type(self, tmp_path):
        # The driver activates the env and refers to the type by name —
        # never importing env internals.
        rom = tmp_path / "fp.bin"
        rom.write_bytes(bytes([0x82, 0x2d, 0xf8, 0x54, 0x58]))  # e
        d = Disassembler.create(cpu="6502")
        d.load(rom, 0x8000)
        d.use_environment("bbc_basic_6502")
        d.typed_data(0x8000, "bbc_float5", comment="e (Euler's number)")
        ir = d.disassemble()
        # Classified as 5 raw bytes for fidelity.
        from dasmos.core.classification import Byte
        c = ir.classifications.get_classification(0x8000)
        assert isinstance(c, Byte) and c.length() == 5
        # Decoded value surfaced as an annotation.
        from dasmos.core.annotations import Align, DecodedAnnotation
        decoded = [
            a for a in ir.annotations.get_for_align(0x8000, Align.INLINE)
            if isinstance(a, DecodedAnnotation)
        ]
        # Text is trimmed to the ~10 significant figures a 32-bit
        # mantissa actually distinguishes (#29); the exact stored value
        # stays full-precision in ``value``.
        assert decoded and decoded[0].decoded.text == "2.718281828"
        assert decoded[0].decoded.value == 2.718281827867031
        # Machine type id stays the registry key; display label differs.
        assert decoded[0].decoded.type_name == "bbc_float5"
        assert decoded[0].decoded.display_label == "float40"

    def test_beebasm_round_trips_and_shows_decoded(self, tmp_path):
        # The five raw bytes re-assemble byte-identical; the decoded
        # value rides along as an inline comment.
        import shutil, subprocess
        beebasm = shutil.which("beebasm")
        if beebasm is None:
            pytest.skip("beebasm not found")
        payload = bytes([0x82, 0x2d, 0xf8, 0x54, 0x58])  # e
        rom = tmp_path / "fp.bin"
        rom.write_bytes(payload)
        d = Disassembler.create(cpu="6502")
        d.load(rom, 0x8000)
        d.use_environment("bbc_basic_6502")
        d.typed_data(0x8000, "bbc_float5", comment="e")
        text = str(d.disassemble().render("beebasm"))
        assert "float40 2.718281828  e" in text
        # The rendered listing already carries org + save; assemble it.
        asm = tmp_path / "fp.asm"
        asm.write_text(text)
        out = tmp_path / "rebuilt.bin"
        r = subprocess.run(
            [beebasm, "-i", str(asm), "-o", str(out)],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        assert out.read_bytes() == payload


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
        # Model-B / B+ placement: &FE18 is the station-ID / NMI-control
        # latch (on the Master &FE18 is the ADC — see the Master tests).
        assert "station_id_disable_net_nmis" in (
            self.d.labels.get_label(0xfe18).explicit_name_texts()
        )

    def test_adc_labels_at_model_b_location(self):
        # The μPD7002 ADC is at &FEC0 on the Model B / B+ (it moves to
        # &FE18 on the Master).
        for addr, name in [
            (0xfec0, "adc_start_conversion_or_status"),
            (0xfec1, "adc_read_data_high_byte"),
            (0xfec2, "adc_read_data_low_byte"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing ADC label {name} at &{addr:04x}"
            )

    def test_acccon_label_present_for_bplus(self):
        # ACCCON (&FE34) exists on the B+ (and Master), not the plain
        # Model B; the combined B/B+ env registers it.
        assert "acccon" in self.d.labels.get_label(0xfe34).explicit_name_texts()

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

    def test_adc_at_master_location(self):
        # On the Master the ADC is at &FE18-&FE1A, NOT the Model-B &FEC0.
        for addr, name in [
            (0xfe18, "adc_start_conversion_or_status"),
            (0xfe19, "adc_read_data_high_byte"),
            (0xfe1a, "adc_read_data_low_byte"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing Master ADC label {name} at &{addr:04x}"
            )

    def test_fe18_is_not_station_id_on_master(self):
        # The Model-B station-ID label must NOT leak onto the Master,
        # where &FE18 is the ADC (#31).
        names = self.d.labels.get_label(0xfe18).explicit_name_texts()
        assert "station_id_disable_net_nmis" not in names

    def test_fec0_not_labelled_adc_on_master(self):
        # &FEC0 is the network interface on the Master, not the ADC;
        # it should carry no ``adc_`` label.
        label = self.d.labels.get_label(0xfec0)
        names = label.explicit_name_texts() if label is not None else []
        assert not any(n.startswith("adc_") for n in names)

    def test_econet_nmi_control_latches(self):
        # Master-dedicated INTOFF / INTON latches.
        assert "disable_net_nmis" in (
            self.d.labels.get_label(0xfe38).explicit_name_texts()
        )
        assert "enable_net_nmis" in (
            self.d.labels.get_label(0xfe3c).explicit_name_texts()
        )

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

    def test_onboard_1770_fdc_labels(self):
        # The Master's fixed onboard WD1770 is included directly in the
        # machine env: drive control at &FE24, chip registers at
        # &FE28-&FE2B (#31).
        for addr, name in [
            (0xfe24, "fdc_1770_drive_control"),
            (0xfe28, "fdc_1770_command_or_status"),
            (0xfe29, "fdc_1770_track"),
            (0xfe2a, "fdc_1770_sector"),
            (0xfe2b, "fdc_1770_data"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts(), (
                f"missing onboard 1770 label {name} at &{addr:04x}"
            )

    def test_does_not_use_fe80_fdc_window(self):
        # The Master 1770 is at &FE28, NOT the &FE80 window used by the
        # 8271 and the B+ / retrofit 1770.
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
    """WD1770 floppy-disc-controller Environment (&FE80 window):
    registers ``fdc_1770_drive_control`` (&FE80) and the four 1770
    chip registers — command/status, track, sector, data — at
    &FE84-&FE87. This is the B+ / Model-B-retrofit mapping; pair with
    :mod:`acorn_model_b_hardware`. The Master's onboard 1770 lives
    elsewhere — see :class:`TestAcornFdc1770MasterEnvironment`.
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

    def test_composes_with_model_b_hardware(self):
        # The &FE80-window 1770 is the B+ / retrofitted-Model-B mapping,
        # so it composes with the Model-B machine env.
        d = Disassembler.create(
            cpu="6502",
            environments=["acorn_model_b_hardware", "acorn_fdc_1770"],
        )
        assert "station_id_disable_net_nmis" in (
            d.labels.get_label(0xfe18).explicit_name_texts()
        )
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
        # &b0 → osbyte_cfs_timeout → "cfs timeout"
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
