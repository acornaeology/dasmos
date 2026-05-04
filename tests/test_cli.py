"""Tests for the ``dasmos`` CLI — discovery commands, the
``disassemble`` one-shot command, and the ``init`` driver-script
scaffolder.
"""

import json as _json
from pathlib import Path

import pytest
from click.testing import CliRunner

from dasmos.cli import _parse_address, cli


# ---------------------------------------------------------------------------
# Address parsing — accepts ``0x8000``, ``&8000``, ``8000``, and decimal.
# Hex and decimal both look natural to a 6502/Acorn user; the parser
# accepts both.
# ---------------------------------------------------------------------------


class TestParseAddress:

    def test_0x_hex(self):
        assert _parse_address("0x8000") == 0x8000

    def test_ampersand_hex(self):
        # Acorn / beebasm convention.
        assert _parse_address("&8000") == 0x8000

    def test_dollar_hex(self):
        # ca65 / Apple convention.
        assert _parse_address("$8000") == 0x8000

    def test_bare_decimal(self):
        assert _parse_address("32768") == 32768

    def test_uppercase_hex(self):
        assert _parse_address("0xFFEE") == 0xFFEE
        assert _parse_address("&FFEE") == 0xFFEE

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="not.*valid.*address"):
            _parse_address("hello")


# ---------------------------------------------------------------------------
# disassemble — the headline one-shot command
# ---------------------------------------------------------------------------


@pytest.fixture
def tiny_rom(tmp_path) -> Path:
    """A 6-byte test ROM: ``LDY #&00 ; JSR &FFF4 ; RTS``.
    Loaded at &1000 so it's clearly out of any ROM-area defaults.
    """
    rom = tmp_path / "tiny.rom"
    rom.write_bytes(bytes([0xa0, 0x00, 0x20, 0xf4, 0xff, 0x60]))
    return rom


class TestDisassemble:

    def test_writes_asm_to_stdout(self, tiny_rom):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
        ])
        assert result.exit_code == 0, result.output
        # The asm output mentions the load addr and the opcodes.
        assert "org &1000" in result.output
        assert "ldy" in result.output
        assert "jsr" in result.output
        assert "rts" in result.output

    def test_writes_to_out_file(self, tiny_rom, tmp_path):
        out = tmp_path / "out.asm"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--out", str(out),
        ])
        assert result.exit_code == 0, result.output
        # When --out is given, stdout is mostly silent (one progress
        # line is fine but the asm should NOT be in stdout).
        assert "ldy" not in result.output
        text = out.read_text(encoding="utf-8")
        assert "ldy" in text
        assert "jsr" in text

    def test_json_renderer_emits_structured_output(self, tiny_rom):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--renderer", "json",
        ])
        assert result.exit_code == 0, result.output
        data = _json.loads(result.output)
        assert data["meta"]["load_addr"] == 0x1000
        assert any(it.get("mnemonic") == "ldy" for it in data["items"])

    def test_explicit_entry_seeds_trace(self, tiny_rom):
        # Entry at &1002 (the JSR) instead of the default load-addr
        # &1000. The LDY at &1000 then becomes data, not code.
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--entry", "&1002",
        ])
        assert result.exit_code == 0, result.output
        # First two bytes (the LDY) should now appear as equb data.
        assert "equb" in result.output
        # The JSR / RTS at &1002+ are still code.
        assert "jsr" in result.output
        assert "rts" in result.output

    def test_environment_activates(self, tiny_rom):
        # acorn_mos registers ``osbyte`` at &FFF4 — with the env
        # active, the JSR resolves to the symbolic name instead of
        # the hex literal.
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--env", "acorn_mos",
        ])
        assert result.exit_code == 0, result.output
        assert "jsr osbyte" in result.output

    def test_multiple_environments_compose(self, tiny_rom):
        # acorn_mos + acorn_bbc_hardware — both should activate.
        # Tested via the listing emitting the osbyte name (mos) AND
        # being free of crashes (hardware compose-cleanly check).
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--env", "acorn_mos",
            "--env", "acorn_bbc_hardware",
        ])
        assert result.exit_code == 0, result.output
        assert "jsr osbyte" in result.output

    def test_unknown_cpu_errors(self, tiny_rom):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--cpu", "z80_doesnt_exist",
        ])
        assert result.exit_code != 0
        # Click error output mentions the bad value.
        assert "z80_doesnt_exist" in result.output or "z80_doesnt_exist" in (result.stderr or "")

    def test_md5_check_passes(self, tiny_rom):
        import hashlib
        md5 = hashlib.md5(tiny_rom.read_bytes()).hexdigest()
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--md5", md5,
        ])
        assert result.exit_code == 0, result.output

    def test_md5_check_fails(self, tiny_rom):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "disassemble", str(tiny_rom),
            "--load-addr", "&1000",
            "--md5", "0" * 32,
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# init — generate a starter driver script
# ---------------------------------------------------------------------------


class TestInit:

    def test_creates_driver_file(self, tiny_rom, tmp_path):
        driver = tmp_path / "driver.py"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
        ])
        assert result.exit_code == 0, result.output
        assert driver.exists()
        text = driver.read_text(encoding="utf-8")
        # It's a real Python file that can be imported / run.
        assert "import dasmos" in text
        # ROM path and load addr land in the file. We compare against
        # the as_posix form because that's what init embeds (forward
        # slashes are platform-portable; the str() form has
        # backslash-escaping issues on Windows).
        assert tiny_rom.as_posix() in text
        assert "0x1000" in text or "&1000" in text or "4096" in text
        # Default cpu / renderer applied.
        assert "6502" in text
        assert "beebasm" in text

    def test_running_generated_driver_produces_asm(self, tiny_rom, tmp_path):
        # The generated driver is FUNCTIONAL — running it with
        # ``python`` produces the same output as ``dasmos
        # disassemble``.
        import subprocess
        import sys

        driver = tmp_path / "driver.py"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
        ])
        assert result.exit_code == 0, result.output

        proc = subprocess.run(
            [sys.executable, str(driver)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "org &1000" in proc.stdout
        assert "ldy" in proc.stdout

    def test_includes_environments(self, tiny_rom, tmp_path):
        driver = tmp_path / "driver.py"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
            "--env", "acorn_mos",
            "--env", "acorn_bbc_hardware",
        ])
        assert result.exit_code == 0, result.output
        text = driver.read_text(encoding="utf-8")
        assert "acorn_mos" in text
        assert "acorn_bbc_hardware" in text

    def test_includes_entry_points(self, tiny_rom, tmp_path):
        driver = tmp_path / "driver.py"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
            "--entry", "&1002",
            "--entry", "&1004",
        ])
        assert result.exit_code == 0, result.output
        text = driver.read_text(encoding="utf-8")
        # Both entry points appear in the generated driver.
        assert "0x1002" in text or "&1002" in text or "4098" in text
        assert "0x1004" in text or "&1004" in text or "4100" in text

    def test_refuses_to_overwrite_existing_driver(self, tiny_rom, tmp_path):
        driver = tmp_path / "driver.py"
        driver.write_text("# pre-existing\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
        ])
        assert result.exit_code != 0
        # Existing content is untouched.
        assert driver.read_text(encoding="utf-8") == "# pre-existing\n"

    def test_force_overwrites_existing(self, tiny_rom, tmp_path):
        driver = tmp_path / "driver.py"
        driver.write_text("# pre-existing\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
            "--force",
        ])
        assert result.exit_code == 0, result.output
        assert "import dasmos" in driver.read_text(encoding="utf-8")
        assert "pre-existing" not in driver.read_text(encoding="utf-8")

    def test_md5_pinned_in_driver(self, tiny_rom, tmp_path):
        import hashlib
        md5 = hashlib.md5(tiny_rom.read_bytes()).hexdigest()
        driver = tmp_path / "driver.py"
        runner = CliRunner()
        result = runner.invoke(cli, [
            "init", str(driver),
            "--rom", str(tiny_rom),
            "--load-addr", "&1000",
            "--md5", md5,
        ])
        assert result.exit_code == 0, result.output
        text = driver.read_text(encoding="utf-8")
        assert md5 in text
