"""Unit tests for dasmos.core.config.

Covers the Config dataclass that replaces py8dis's ~25 module-level
get_/set_ pairs. The point of the rewrite is per-instance isolation;
the test of consequence is that two Configs are independent.
"""

from dasmos.core.config import Config


class TestConfig:

    def test_defaults_are_sensible(self):
        c = Config()
        # Just spot-check a few defaults — the full set is in the
        # dataclass definition.
        assert c.lower_case is True
        assert c.indent_string == "    "
        assert c.inline_comment_column == 70
        assert c.constants_are_decimal is True
        assert c.cmos is False

    def test_two_configs_are_independent(self):
        # The justification for the rewrite — module-level get_/set_
        # pairs in py8dis prevented this.
        a = Config()
        b = Config()
        a.lower_case = False
        a.indent_string = "\t"
        assert b.lower_case is True
        assert b.indent_string == "    "

    def test_construction_with_overrides(self):
        c = Config(lower_case=False, loop_limit=64)
        assert c.lower_case is False
        assert c.loop_limit == 64
        # Other fields keep their defaults.
        assert c.show_stats is True
