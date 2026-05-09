"""Round-trip tests against the real Acorn NFS 3.65 ROM.

The NFS (Network Filing System) ROM is the canonical Acorn Econet
file-server client; 8 KB sideways ROM mapped at &8000-&9FFF on a
BBC Micro / Master. Mirrors :mod:`tests.test_tube_client_roundtrip`
in shape:

- :class:`TestNfsPorterEndToEnd` — port the unmodified original
  py8dis driver, run it, capture the rendered beebasm source,
  re-assemble via beebasm, assert byte-identical with the original
  ROM.
- :class:`TestNfsPy8disParity` — vocabulary-coverage check against
  the vendored py8dis reference output. Marker ``py8dis_parity`` so
  it can be deselected wholesale once dasmos is intentionally
  allowed to diverge.

Exercises a beebasm-pass-mismatch scenario the smaller fixtures
don't: NFS registers four ``move()`` declarations (one ZP, three
page-aligned), and several of them overlap. The renderer's
moves-first emission ordering (mirroring py8dis) is what makes the
inline anchors for ZP labels precede their use sites.
"""

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


_FIXTURES = Path(__file__).parent / "fixtures" / "acorn-nfs"
ROM_PATH = _FIXTURES / "nfs-3.65.rom"
ORIGINAL_DRIVER_PATH = _FIXTURES / "disasm_nfs_365.py"
PY8DIS_REFERENCE_PATH = _FIXTURES / "py8dis_reference_nfs-3.65.asm"
PY8DIS_REFERENCE_JSON_PATH = _FIXTURES / "py8dis_reference_nfs-3.65.json"

ROM_SIZE = 8192
ROM_LOAD_ADDR = 0x8000
ROM_MD5 = "1e150e6bd53d22c15eb05302b6e5f167"
PY8DIS_REFERENCE_MD5 = "d115f1ce53c957d92044c113056b18a9"
PY8DIS_REFERENCE_JSON_MD5 = "a14492c612e66077f7762733b82785a8"

_PORTER_PATH = Path(__file__).parent.parent / "scripts" / "py8dis2dasmos.py"
_porter_spec = importlib.util.spec_from_file_location(
    "py8dis2dasmos", _PORTER_PATH,
)
_porter = importlib.util.module_from_spec(_porter_spec)
_porter_spec.loader.exec_module(_porter)


def _find_beebasm() -> str | None:
    env = os.environ.get("BEEBASM")
    if env and os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    found = shutil.which("beebasm")
    if found:
        return found
    fallback = "/Users/rjs/Code/beebasm/beebasm"
    if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
        return fallback
    return None


_BEEBASM = _find_beebasm()


@pytest.mark.beebasm
class TestNfsPorterEndToEnd:
    """Load-bearing acceptance test: the unmodified py8dis driver,
    ported through scripts/py8dis2dasmos.py and run against the NFS
    3.65 ROM, produces beebasm source that re-assembles byte-
    identical with the original ROM.
    """

    def test_full_driver_round_trips(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        rom = ROM_PATH.read_bytes()
        assert hashlib.md5(rom).hexdigest() == ROM_MD5
        assert len(rom) == ROM_SIZE

        ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"))
        ported_filepath = tmp_path / "ported_driver.py"
        ported_filepath.write_text(ported_src, encoding="utf-8")

        output_dirpath = tmp_path / "out"
        output_dirpath.mkdir()

        env = os.environ.copy()
        env["FANTASM_ROM"] = str(ROM_PATH)
        env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)

        result = subprocess.run(
            [sys.executable, str(ported_filepath)],
            capture_output=True, text=True, cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0, (
            f"ported driver failed (exit {result.returncode}):\n"
            f"=== stderr ===\n{result.stderr}"
        )

        asm_filepath = output_dirpath / "nfs-3.65.asm"
        assert asm_filepath.exists(), (
            f"expected rendered asm at {asm_filepath}, "
            f"stderr was:\n{result.stderr}"
        )

        rebuilt_filepath = tmp_path / "rebuilt.bin"
        result = subprocess.run(
            [_BEEBASM, "-i", str(asm_filepath), "-o", str(rebuilt_filepath)],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"beebasm failed to assemble ported output:\n"
            f"=== stderr ===\n{result.stderr}"
        )

        rebuilt = rebuilt_filepath.read_bytes()
        assert rebuilt == rom, (
            f"byte mismatch: {len(rebuilt)} rebuilt vs {len(rom)} "
            f"original bytes"
        )


# ---------------------------------------------------------------------------
# py8dis annotation-content parity (same approach as the Tube Client test)
# ---------------------------------------------------------------------------

# History (lower as fidelity gaps close):
#   29 — first measured value, after moves-first emission landed.
#   12 — after ``acorn_model_b_hardware`` Environment landed (closed
#        the BBC hardware label vocabulary; was named
#        ``acorn_bbc_hardware`` before the Master/Model B split).
#   32 — Phase 4.1 OSBYTE-hook port (backward-peek heuristic).
#   11 — Phase 4.2 full CPU-state tracker (held through 4.3-4.5).
#        Residual is generic comment-text words from py8dis
#        annotations dasmos doesn't yet generate.
# Stepped down: 11 → 5 (mid-class annotation fix) → 3 (bucket 1
# OSBYTE/OSWORD descriptions, 2026-05-06). Remaining residuals are
# stats-footer label-frequency entries (``dispatch_0_lo``,
# ``imm_op_dispatch_lo``) plus per-X-value lookup variants
# (``redefine`` from OSBYTE &14 with X=6).
MAX_COMMENT_TOKENS_DROPPED = 0

# JSON-parity ratchets. Lower as the JsonRenderer learns more of
# py8dis's emit_structured() schema. History:
#   Phase 1 (meta + items + external_labels skeleton):
#     constants 42, subroutines 239, external_labels 19, items 2.
#   Phase 2 (constants + subroutines via Disassembler.constant /
#   .subroutine, OS-call entries registered as is_entry_point=False
#   subs in acorn_mos):
#     constants 13 (the per-OSBYTE/OSWORD value constants live in
#     py8dis's ``acorn`` module — pending acorn_model_b_hardware and
#     the OS-call enum port).
#     subroutines 0 (every py8dis-emitted sub address is now also
#     emitted by dasmos).
#     external_labels 19 (BBC hardware gap unchanged).
#     items 2 py8dis-only addrs (different byte-aggregation: py8dis
#     groups consecutive constant bytes into one ``equb`` block).
MAX_CONSTANTS_MISSING = 0
MAX_SUBROUTINES_MISSING = 0
# After ``acorn_bbc_hardware`` Environment landed in Phase 3, only
# the boundary marker ``pydis_end`` (vs dasmos's ``dasmos_end``)
# remains as a name py8dis emits that dasmos doesn't.
MAX_EXTERNAL_LABELS_MISSING = 1
MAX_ITEM_ADDRS_MISSING = 2
# fall_through detection: py8dis emits 83 entries with the flag on
# NFS; dasmos currently emits some extras due to the "ALWAYS branch"
# heuristic py8dis uses but we've deferred (depends on cycle-count
# inline comments dasmos doesn't yet emit), plus subroutine-list
# growth from the OSBYTE-hook port.
MAX_EXTRA_FALL_THROUGHS = 25

# Per-item field-mismatch ratchets. Each bounds the count of items
# where the named field's value differs between dasmos and py8dis.
# Lower as gaps close. The dominant remaining differences:
# - ``operand`` (~137 after Phase 3+ formatting fixes): residual
#   label-preference tie-breaks where the same address has multiple
#   names, plus OSBYTE/OSWORD enum constants that need py8dis-style
#   hooks (``lda #osbyte_read_buffer`` vs ``lda #&80``), plus hi/lo
#   expression overrides not propagated.
# - ``target_label`` (~112): consequence of the same label-preference
#   differences.
# - ``expressions`` (~102): porter writes ``< (…)`` not ``<(…)``,
#   plus the porter doesn't always emit a label name in expr text.
# - ``references`` (~80): py8dis preserves trace-insertion order;
#   dasmos sorts numerically (a deliberate divergence — design
#   improvement).
# - ``comments_before``: ratchet removed in #16. Dasmos's per-align
#   split (comments_before_label / comments_after_label /
#   comments_before_line / comments_after_line / xref_summaries) no
#   longer maps cleanly to py8dis's conflated comments_before field.
#   A faithful comparison would need to reclassify py8dis's strings
#   back into per-align buckets — heuristic guesswork, and parity
#   is no longer load-bearing now that py8dis is decoupled.
MAX_PER_ITEM_OPERAND_MISMATCHES = 2
MAX_PER_ITEM_TARGET_LABEL_MISMATCHES = 0
# References are compared as SETS (sort-order divergence is
# deliberate — py8dis emits in trace-insertion order; dasmos picks
# its own deterministic order). The ratchet bounds items where the
# REFERENCE SETS differ (a real content gap, currently from the
# move-3/move-4 boundary BVC straddle).
MAX_PER_ITEM_REFERENCES_CONTENT_MISMATCHES = 2
MAX_PER_ITEM_EXPRESSIONS_MISMATCHES = 0

_COMMENT_TOKEN_RE = re.compile(r"[a-z_][a-z_0-9]{3,}")


def _comment_text(asm_text: str) -> str:
    """Keep EVERY ``;``-introduced chunk so the byte-column annotation
    contributes addresses/symbols to the parity corpus. Same shape as
    the tube_client / econet_bridge parity tests.
    """
    parts: list[str] = []
    for line in asm_text.splitlines():
        chunks = line.split(";")
        parts.extend(chunks[1:])
    return " ".join(parts).replace("`", "").lower()


def _comment_tokens(asm_text: str) -> set[str]:
    return set(_COMMENT_TOKEN_RE.findall(_comment_text(asm_text)))


def _run_dasmos_driver(tmp_path) -> Path:
    """Port the NFS driver via py8dis2dasmos, run it, return the
    output dir. Helper for both the asm and JSON parity tests.
    """
    ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"))
    ported_filepath = tmp_path / "ported_driver.py"
    ported_filepath.write_text(ported_src, encoding="utf-8")
    output_dirpath = tmp_path / "out"
    output_dirpath.mkdir()
    env = os.environ.copy()
    env["FANTASM_ROM"] = str(ROM_PATH)
    env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)
    result = subprocess.run(
        [sys.executable, str(ported_filepath)],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0, (
        f"ported driver failed:\n=== stderr ===\n{result.stderr}"
    )
    return output_dirpath


def _render_dasmos_json(tmp_path) -> dict:
    """Run dasmos with the JSON renderer against NFS and return the
    parsed dict. Re-uses the porter pipeline but swaps the renderer
    selection in the ported script's tail.
    """
    import re
    ported_src = _porter.port(ORIGINAL_DRIVER_PATH.read_text(encoding="utf-8"))
    # Swap the beebasm-renderer call for the json renderer. The porter
    # emits ``ir = d.disassemble()`` followed by
    # ``output = str(ir.render('beebasm', ...))`` at the tail;
    # replace just the renderer selection on the ``output =`` line.
    ported_src = re.sub(
        r"output = str\(ir\.render\([^\)]*\)\)",
        "output = str(ir.render('json'))",
        ported_src,
    )
    ported_filepath = tmp_path / "ported_driver_json.py"
    ported_filepath.write_text(ported_src, encoding="utf-8")
    output_dirpath = tmp_path / "out_json"
    output_dirpath.mkdir()
    env = os.environ.copy()
    env["FANTASM_ROM"] = str(ROM_PATH)
    env["FANTASM_OUTPUT_DIR"] = str(output_dirpath)
    result = subprocess.run(
        [sys.executable, str(ported_filepath)],
        capture_output=True, text=True, cwd=str(tmp_path), env=env,
    )
    assert result.returncode == 0, (
        f"ported driver (json) failed:\n=== stderr ===\n{result.stderr}"
    )
    # Driver writes to ``nfs-3.65.asm`` regardless of content.
    out_filepath = output_dirpath / "nfs-3.65.asm"
    import json as _json
    return _json.loads(out_filepath.read_text(encoding="utf-8"))


@pytest.mark.beebasm
@pytest.mark.py8dis_parity
class TestNfsPy8disParity:

    def test_reference_fixture_pinned(self):
        actual = hashlib.md5(PY8DIS_REFERENCE_PATH.read_bytes()).hexdigest()
        assert actual == PY8DIS_REFERENCE_MD5, (
            f"py8dis reference output md5 changed ({actual}); "
            f"either re-vendor and update PY8DIS_REFERENCE_MD5, or "
            f"investigate why the upstream output is different."
        )

    def test_reference_json_fixture_pinned(self):
        actual = hashlib.md5(
            PY8DIS_REFERENCE_JSON_PATH.read_bytes()
        ).hexdigest()
        assert actual == PY8DIS_REFERENCE_JSON_MD5, (
            f"py8dis reference JSON md5 changed ({actual}); re-vendor "
            f"with the py8dis fork's get_structured() output and "
            f"update PY8DIS_REFERENCE_JSON_MD5."
        )

    def test_comment_vocabulary_covers_py8dis(self, tmp_path):
        if _BEEBASM is None:
            pytest.skip("beebasm not found")

        output_dirpath = _run_dasmos_driver(tmp_path)
        candidate_filepath = output_dirpath / "nfs-3.65.asm"

        ref_tokens = _comment_tokens(PY8DIS_REFERENCE_PATH.read_text(encoding="utf-8"))
        das_tokens = _comment_tokens(candidate_filepath.read_text(encoding="utf-8"))

        missing = ref_tokens - das_tokens
        sample = sorted(missing)[:25]
        assert len(missing) <= MAX_COMMENT_TOKENS_DROPPED, (
            f"dasmos dropped {len(missing)} unique comment tokens "
            f"present in the py8dis reference (allowed: "
            f"{MAX_COMMENT_TOKENS_DROPPED}). Sample: {sample}. "
            f"If you've fixed a fidelity gap, lower "
            f"MAX_COMMENT_TOKENS_DROPPED to the new observed value."
        )

    # -- JSON structural parity (much richer oracle than asm tokens) --

    def test_json_meta_matches_py8dis(self, tmp_path):
        """meta is two integers; should match exactly. If this ever
        diverges it's a real bug (load-range computation error).
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        assert das["meta"] == ref["meta"]

    def test_json_constants_section_ratchet(self, tmp_path):
        """py8dis emits ~42 constant entries for NFS; dasmos's
        skeleton renderer emits 0 (no constants store yet). Ratchet
        down as the renderer learns this section.
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_names = {c["name"] for c in ref["constants"]}
        das_names = {c["name"] for c in das["constants"]}
        missing = ref_names - das_names
        assert len(missing) <= MAX_CONSTANTS_MISSING, (
            f"dasmos missing {len(missing)} constants from py8dis "
            f"output (allowed: {MAX_CONSTANTS_MISSING}). Sample: "
            f"{sorted(missing)[:10]}"
        )

    def test_json_subroutines_section_ratchet(self, tmp_path):
        """py8dis emits ~239 subroutine entries for NFS. After Phase
        2 wired up Disassembler.subroutine + acorn_mos OS-call subs,
        every py8dis-emitted address has a matching dasmos entry
        (MAX_SUBROUTINES_MISSING = 0).

        Note: py8dis-fork puts ``data_banner`` entries in the same
        ``subroutines`` array. dasmos splits them out into a separate
        ``banners`` array, so the parity check unions the two arrays
        on the dasmos side.
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_addrs = {s["addr"] for s in ref["subroutines"]}
        das_addrs = (
            {s["addr"] for s in das["subroutines"]}
            | {b["addr"] for b in das.get("banners", [])}
        )
        missing = ref_addrs - das_addrs
        assert len(missing) <= MAX_SUBROUTINES_MISSING, (
            f"dasmos missing {len(missing)} subroutines/banners from "
            f"py8dis output (allowed: {MAX_SUBROUTINES_MISSING})."
        )

    def test_json_subroutines_fall_through_ratchet(self, tmp_path):
        """py8dis flags some subs with ``fall_through: True`` when
        their last code item doesn't terminate (``RTS`` / ``JMP`` /
        ``BRK`` / ``RTI``). dasmos's algorithm matches structurally
        but currently flags more cases than py8dis — likely the
        "ALWAYS branch" inline-comment suppression py8dis applies
        and dasmos doesn't yet (it depends on cycle-count
        annotations dasmos doesn't emit).

        The ratchet bounds the EXTRA fall-throughs dasmos emits
        relative to py8dis. Lower it as the algorithm tightens.
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_ft = {s["addr"] for s in ref["subroutines"]
                  if s.get("fall_through")}
        das_ft = {s["addr"] for s in das["subroutines"]
                  if s.get("fall_through")}
        # py8dis-only fall-throughs would be a real miss
        # (functionally equivalent to "we missed annotating a
        # fall-through"). Currently zero, so the assert is strict.
        missing = ref_ft - das_ft
        assert len(missing) == 0, (
            f"dasmos missing {len(missing)} fall_through flags py8dis "
            f"emits. Sample: {sorted(missing)[:10]}"
        )
        # Extras we ratchet on.
        extras = das_ft - ref_ft
        assert len(extras) <= MAX_EXTRA_FALL_THROUGHS, (
            f"dasmos emits {len(extras)} extra fall_through flags vs "
            f"py8dis (allowed: {MAX_EXTRA_FALL_THROUGHS}). Sample: "
            f"{sorted(extras)[:10]}"
        )

    def test_json_external_labels_cover_py8dis(self, tmp_path):
        """external_labels: every label py8dis emits at an
        out-of-range address must also be present in dasmos's
        output. Extras on dasmos's side are tolerated (Phase 1
        includes auto-generated labels py8dis classifies differently).
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_names = set(ref["external_labels"])
        das_names = set(das["external_labels"])
        missing = ref_names - das_names
        sample = sorted(missing)[:15]
        assert len(missing) <= MAX_EXTERNAL_LABELS_MISSING, (
            f"dasmos missing {len(missing)} external labels py8dis "
            f"emits (allowed: {MAX_EXTERNAL_LABELS_MISSING}). "
            f"Sample: {sample}"
        )

    def test_json_item_addresses_cover_py8dis(self, tmp_path):
        """Every binary address py8dis classifies must also be
        classified by dasmos. Extras on dasmos's side reflect
        differences in byte-aggregation (py8dis groups consecutive
        constant bytes into one ``equb`` block where dasmos may
        emit several) — tolerated.
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_addrs = {it["addr"] for it in ref["items"]}
        das_addrs = {it["addr"] for it in das["items"]}
        missing = ref_addrs - das_addrs
        assert len(missing) <= MAX_ITEM_ADDRS_MISSING, (
            f"dasmos missing {len(missing)} item addresses py8dis "
            f"emits (allowed: {MAX_ITEM_ADDRS_MISSING}). Sample: "
            f"{sorted(missing)[:10]}"
        )

    @pytest.mark.parametrize("field, ratchet", [
        ("operand", MAX_PER_ITEM_OPERAND_MISMATCHES),
        ("target_label", MAX_PER_ITEM_TARGET_LABEL_MISMATCHES),
        ("expressions", MAX_PER_ITEM_EXPRESSIONS_MISMATCHES),
    ])
    def test_json_per_item_field_mismatches_ratchet(
        self, tmp_path, field, ratchet,
    ):
        """For each item address shared between dasmos and py8dis,
        count how many have a different value for ``<field>``. The
        ratchet bounds that count — lower as the gap closes.

        See ``MAX_PER_ITEM_*`` constants at the top of this file for
        the residual root causes of each gap.
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_by_addr = {it["addr"]: it for it in ref["items"]}
        das_by_addr = {it["addr"]: it for it in das["items"]}
        shared = set(ref_by_addr) & set(das_by_addr)
        mismatches = sum(
            1 for addr in shared
            if ref_by_addr[addr].get(field) != das_by_addr[addr].get(field)
        )
        assert mismatches <= ratchet, (
            f"dasmos per-item mismatches on '{field}': {mismatches} "
            f"(ratchet: {ratchet}). If you've closed a gap, lower "
            f"the ratchet."
        )

    def test_json_per_item_references_set_equivalence(self, tmp_path):
        """Reference content (the SET of addresses that reference
        each item) must match py8dis. Order divergence is deliberate
        — py8dis preserves trace-insertion order; dasmos may emit
        them in any deterministic order. Downstream consumers that
        need ordering should sort.

        The ratchet bounds items where the SET DIFFERS (a real
        content gap — currently 2, from the move-3/move-4 boundary
        BVC straddle whose reference-tracking is necessarily lossy).
        """
        import json as _json
        ref = _json.loads(PY8DIS_REFERENCE_JSON_PATH.read_text(encoding="utf-8"))
        das = _render_dasmos_json(tmp_path)
        ref_by_addr = {it["addr"]: it for it in ref["items"]}
        das_by_addr = {it["addr"]: it for it in das["items"]}
        shared = set(ref_by_addr) & set(das_by_addr)
        content_mismatches = sum(
            1 for addr in shared
            if set(ref_by_addr[addr].get("references") or [])
            != set(das_by_addr[addr].get("references") or [])
        )
        assert content_mismatches <= MAX_PER_ITEM_REFERENCES_CONTENT_MISMATCHES, (
            f"dasmos missing reference CONTENT (set-difference) on "
            f"{content_mismatches} items "
            f"(ratchet: {MAX_PER_ITEM_REFERENCES_CONTENT_MISMATCHES})."
        )
