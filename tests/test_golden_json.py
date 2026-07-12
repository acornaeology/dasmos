"""Golden snapshot of the JSON schema.

A compact synthetic disassembly exercises every top-level section and the
full v4 expression / macro vocabulary, rendered to JSON and pinned against
a committed golden (``tests/fixtures/golden_schema_v4.json``).

This freezes the *shape* and the ``meta.schema_version`` *together*: any
change to the emitted JSON — including forgetting to bump the version when
the shape changes — fails this test with a reviewable diff. That is
exactly the failure mode that mislabelled v3 output as v2. When a change
to the schema is intentional, regenerate with::

    UPDATE_GOLDEN=1 uv run pytest tests/test_golden_json.py

and, if the shape changed in a breaking way, bump ``JSON_SCHEMA_VERSION``
and update ``docs/design/json-schema-v4.md`` in the same commit.
"""

import json
import os
import tempfile
from pathlib import Path

from dasmos import Disassembler
from dasmos.expr import group, hexlit, hi, lo, param, ref, sym
from dasmos.ext.renderers.json import JsonRenderer


_GOLDEN = Path(__file__).parent / "fixtures" / "golden_schema_v4.json"


def _build_document() -> dict:
    """A small IR that populates every schema section and every v3
    expression / macro node kind, rendered to the JSON data dict."""
    # 12 bytes at 0x2000: lda #imm ; rts ; then a data run and a word.
    binary = bytes([0xA9, 0x00, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00])
    tmp = Path(tempfile.mktemp())
    tmp.write_bytes(binary)

    d = Disassembler.create(cpu="6502")
    d.load(tmp, 0x2000)
    d.entry(0x2000, name="start")
    d.subroutine(0x2000, name="start", title="Entry",
                 description="The entry point.")
    d.constant(0x0E, "osbyte_read_himem")
    d.label(0xFFEE, "oswrch")                 # external (out of load range)
    d.index_base(0x2003, "table")             # base row in memory_map (access ["b"])

    # A macro whose body uses string indexing, masks, arithmetic and a
    # group — covers macro_call/param/str_index/binary/group/int nodes.
    m = param("mnem")
    pack_lo = d.define_macro(
        "pack_lo", ["mnem"],
        group((m[0] & 0x1F) * 0x400 + (m[1] & 0x1F) * 0x20 + (m[2] & 0x1F))
        & 0xFF,
    )

    # Operand expression on the LDA (code-item ``expr``).
    d.expr(0x2001, sym("osbyte_read_himem"))

    # A data run exercising the remaining expression node kinds.
    d.byte(0x2003, 6)
    d.expr(0x2003, pack_lo("LDA"))                       # macro_call + str
    d.expr(0x2004, lo(ref(0x2000) - 1))                  # lowbyte + ref + int
    d.expr(0x2005, hi(ref(0xFFEE)))                      # highbyte + ref(name)
    d.expr(0x2006, (ref(0x2000) - ref(0x2003)) & 0xFF)   # group/binary + and
    d.expr(0x2007, hexlit(0x1F))                         # int, hex radix
    # 0x2008 left as a plain byte (no expression) — null in the array.
    d.word(0x200A)                                       # a Word item

    return d.disassemble().render(JsonRenderer()).data


def test_json_schema_matches_golden():
    doc = _build_document()
    rendered = json.dumps(doc, indent=2, sort_keys=False) + "\n"

    if os.environ.get("UPDATE_GOLDEN"):
        _GOLDEN.write_text(rendered, encoding="utf-8")
        import pytest
        pytest.skip(f"golden regenerated: {_GOLDEN}")

    assert _GOLDEN.exists(), (
        f"golden missing: {_GOLDEN}. Generate it with "
        f"UPDATE_GOLDEN=1 uv run pytest tests/test_golden_json.py"
    )
    expected = _GOLDEN.read_text(encoding="utf-8")
    assert rendered == expected, (
        "JSON schema output differs from the golden snapshot. If the change "
        "is intentional, regenerate with UPDATE_GOLDEN=1 — and if the shape "
        "changed in a breaking way, bump JSON_SCHEMA_VERSION and update "
        "docs/design/json-schema-v3.md in the same commit."
    )


def test_golden_is_stamped_v4():
    # A cheap independent guard: the pinned document is v4, and carries the
    # v4 hallmarks (object expressions and a macros section from v3; the
    # separate index_bases array folded away in v4).
    doc = json.loads(_GOLDEN.read_text(encoding="utf-8"))
    assert doc["meta"]["schema_version"] == 4
    assert "index_bases" not in doc
    assert isinstance(doc["macros"], list) and doc["macros"]
    byte_item = next(i for i in doc["items"] if i.get("type") == "byte")
    first = next(e for e in byte_item["expressions"] if e is not None)
    assert set(first) == {"text", "tree"}
