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
