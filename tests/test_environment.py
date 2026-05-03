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
            cpu="nmos6502", environments=["acorn_mos"],
        )
        # A handful of canonical names land in the LabelManager.
        assert "userv" in d.labels.get_label(0x0200).explicit_name_texts()
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()
        assert "osbyte" in d.labels.get_label(0xfff4).explicit_name_texts()

    def test_method_activates_after_construction(self):
        d = Disassembler.create(cpu="nmos6502")
        assert d.labels.get_label(0xffee) is None
        d.use_environment("acorn_mos")
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()

    def test_method_accepts_instance(self):
        d = Disassembler.create(cpu="nmos6502")
        d.use_environment(AcornMosEnvironment())
        assert "oswrch" in d.labels.get_label(0xffee).explicit_name_texts()

    def test_idempotent_second_activation(self):
        # Activating the same environment twice is a no-op — the
        # underlying LabelManager dedupes ExplicitName entries by
        # text. Verifies the layering story doesn't blow up on
        # re-application.
        d = Disassembler.create(cpu="nmos6502")
        d.use_environment("acorn_mos")
        d.use_environment("acorn_mos")
        names = d.labels.get_label(0xffee).explicit_name_texts()
        assert names == {"oswrch"}

    def test_unknown_environment_raises(self):
        from dasmos.environment import EnvironmentExtensionError
        with pytest.raises(EnvironmentExtensionError):
            create_environment("nonexistent")

    def test_use_environment_rejects_non_environment(self):
        d = Disassembler.create(cpu="nmos6502")
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

        d = Disassembler.create(cpu="nmos6502", environments=["acorn_mos"])
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

        d = Disassembler.create(cpu="nmos6502", environments=["acorn_mos"])
        d.use_environment(AliasEnv())
        names = d.labels.get_label(0xffee).explicit_name_texts()
        assert names == {"oswrch", "print_char"}


class TestAcornMosCoverage:
    """Spot-checks that the ported label set matches py8dis."""

    def setup_method(self):
        self.d = Disassembler.create(
            cpu="nmos6502", environments=["acorn_mos"],
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
        # Each vector occupies 2 bytes; both halves are named.
        for addr, name in [
            (0x0200, "userv"), (0x020e, "wrchv"),
            (0x0214, "argsv"), (0x0220, "evntv"),
        ]:
            label_lo = self.d.labels.get_label(addr)
            label_hi = self.d.labels.get_label(addr + 1)
            assert name in label_lo.explicit_name_texts()
            assert f"{name}_hi" in label_hi.explicit_name_texts()

    def test_os_call_entries(self):
        for addr, name in [
            (0xffe0, "osrdch"), (0xffee, "oswrch"),
            (0xfff1, "osword"), (0xfff4, "osbyte"),
            (0xfff7, "oscli"),
        ]:
            assert name in self.d.labels.get_label(addr).explicit_name_texts()

    def test_count_matches_expected(self):
        # 3 workspace + 27 vectors * 2 + 21 OS calls = 78 distinct
        # addresses with at least one name. Pinning the count guards
        # against accidental drift.
        named_addrs = sum(
            1 for label in self.d.labels._labels.values()
            if label.explicit_name_texts()
        )
        assert named_addrs == 3 + 27 * 2 + 21


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
        d = Disassembler.create(cpu="nmos6502")
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
        d = Disassembler.create(cpu="nmos6502")
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
