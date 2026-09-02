Driver-script API
=================

A *driver script* is a Python file that builds up a disassembly by
calling methods on a :class:`~dasmos.Disassembler`. Where
``dasmos disassemble`` is one-shot, a driver is the long-lived
artefact: as you analyse a ROM you add labels, name subroutines,
attach comments, mark data regions, and re-run the script to get an
ever-improving listing. The driver is the single source of truth —
version it, diff it, share it.

This page walks through the API in roughly the order you'd reach for
each piece of it during a real analysis. See :doc:`api` for the full
reference.


The minimal driver
------------------

The smallest useful driver: load a ROM, declare its entry point,
disassemble, render. ``dasmos init`` writes essentially this:

.. code-block:: python

   from pathlib import Path

   import dasmos

   ROM_PATH = Path("nfs365.rom")
   LOAD_ADDR = 0x8000

   d = dasmos.Disassembler.create(cpu="6502")
   d.load(ROM_PATH, LOAD_ADDR)
   d.entry(LOAD_ADDR)

   ir = d.disassemble()
   print(str(ir.render("beebasm")))

Run with ``python driver.py`` and the rendered listing appears on
stdout. Every other thing in this guide is added between
:meth:`~dasmos.Disassembler.entry` and
:meth:`~dasmos.Disassembler.disassemble`.


Building the disassembler
-------------------------

:meth:`Disassembler.create <dasmos.Disassembler.create>` is the
classmethod that wires a CPU plug-in together with zero or more
*environment* plug-ins. The CPU defines the instruction set; the
environments contribute named labels, hardware-port names, OS-call
analysers, and subroutine hooks for a specific target system.

.. code-block:: python

   d = dasmos.Disassembler.create(
       cpu="6502",
       environments=["acorn_mos", "acorn_model_b_hardware", "acorn_fdc_8271"],
   )

With ``acorn_mos`` active, ``jsr &FFF4`` resolves to ``jsr osbyte``
without you having to declare the label yourself; with
``acorn_model_b_hardware`` active, reads of ``&FE40`` resolve to the
System VIA's ``via_system_orb`` instead of a bare hex literal; and
with ``acorn_fdc_8271`` active, accesses to ``&FE80-&FE84`` resolve
to the 8271 floppy-controller register names. Run
``dasmos list-environments`` to see what's installed.

Environment plug-ins are deliberately split along orthogonal axes:
the machine class (``acorn_model_b_hardware`` / ``acorn_master_hardware``),
the floppy-disc-controller variant (``acorn_fdc_8271`` /
``acorn_fdc_1770``), and so on. A retrofitted Model B with a 1770
upgrade is the combination ``acorn_model_b_hardware`` +
``acorn_fdc_1770``; a Master is ``acorn_master_hardware`` +
``acorn_fdc_1770``. Pick the combination that matches the system
the ROM you're disassembling targets.

Loading the binary:

.. code-block:: python

   d.load(ROM_PATH, LOAD_ADDR, md5sum="3a7f…")

The optional ``md5sum=`` argument pins the binary's hash; mismatched
binaries raise before any further analysis runs, catching the
ROM-version-skew bug at the earliest possible moment.


Seeding the trace
-----------------

Trace-driven classification needs at least one entry point. The
common case is a single entry at the load address:

.. code-block:: python

   d.entry(LOAD_ADDR)

But many ROMs have several entry points — service-ROM headers, IRQ
vectors, second-processor boot sequences. Declare each one:

.. code-block:: python

   d.entry(0x8000, "rom_init")
   d.entry(0x8003, "rom_service")
   d.entry(0x8006, "rom_workspace")

The optional second argument names the entry point, equivalent to a
:meth:`~dasmos.Disassembler.label` call at the same address. The
trace follows reachable code from each seed; bytes that no seed can
reach end up classified as data unless you intervene.


Naming things: labels and constants
-----------------------------------

Once you've identified what an address *means*, name it. *Dasmos*
has three flavours of name, corresponding to three different
commitments:

:meth:`~dasmos.Disassembler.label` — a *required* label at this
address. It always appears in the output, even if nothing references
it. Use this when you want the label as a human-facing waypoint
regardless of code-flow analysis.

.. code-block:: python

   d.label(0x9000, "main_dispatch")

:meth:`~dasmos.Disassembler.optional_label` — only emitted if some
piece of analysis ends up referencing the address. Use this when
you've named a candidate location but you're not yet sure it's
actually used; if it is, you get the named label, otherwise it stays
out of the way.

.. code-block:: python

   d.optional_label(0x9100, "maybe_unused_helper")

:meth:`~dasmos.Disassembler.constant` — names a *value*, not an
address. Hex literals like ``#&80`` get rewritten to the constant
name in the operand position, which is the right call for OSBYTE
action codes, magic numbers, bit masks, and the like:

.. code-block:: python

   d.constant(0x80, "osbyte_read_adc")

After which ``lda #&80 ; jsr osbyte`` renders as
``lda #osbyte_read_adc ; jsr osbyte`` — the intent jumps off the page.

For cases where the natural name involves arithmetic — most often
"the high byte of a vector pair" — use
:meth:`~dasmos.Disassembler.expr_label`, which stores an *expression*
as the address's label form:

.. code-block:: python

   from dasmos.expr import ref

   d.label(0x220, "irq1v")
   d.expr_label(0x221, ref(0x220) + 1)   # renders as ``irq1v+1``

After which a reference to ``&221`` renders as ``irq1v+1`` instead of
``l0221``. The argument is an *assembler-neutral expression* built with
the :mod:`dasmos.expr` DSL — the same expressions accepted by
:meth:`~dasmos.Disassembler.expr` for operands and data bytes. They are
the subject of the next section.


.. _expressions:

Assembler-neutral expressions
-----------------------------

Wherever a driver supplies an operand or data value that isn't a plain
label — a byte extracted from an address, an offset, a mask, a computed
constant — it does so with an :class:`~dasmos.core.expr.Expr` tree built
from the :mod:`dasmos.expr` DSL. dasmos renders that one tree into each
target assembler's own syntax: ``&`` vs ``$`` hex, ``AND`` vs ``&``,
``<(x)`` byte-select, and — crucially — the *correct parenthesisation*
for each assembler's operator precedence. You write the intent once; the
renderer gets the syntax right per backend.

The building blocks:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Builder
     - Meaning
   * - ``ref(addr)``
     - the label at a runtime address, resolved to its name at render
       time (falls back to a hex literal if unnamed)
   * - ``sym(name)``
     - a bare symbolic name, emitted verbatim (a constant, say)
   * - ``lo(e)`` / ``hi(e)``
     - low / high byte of ``e``
   * - ``hexlit(n)`` / ``declit(n)`` / ``char(n)``
     - an integer literal forced to hex / decimal / a character literal
   * - ``string(s)``
     - a string literal — index (``string("BRK")[0]``) or slice it
   * - Python operators
     - ``+ - * // & | ^ << >>`` and unary ``-`` / ``~`` compose sub-trees

``ref`` and integer literals cover the vast majority of cases. A bare
Python ``int`` is accepted anywhere and becomes a literal, so
``ref(0x8130) - 1`` just works.

.. code-block:: python

   from dasmos.expr import ref, sym, lo, hi

   d.constant(3, "num_lives")
   d.expr(0x8001, sym("num_lives") + 1)   # lda #num_lives + 1
   d.expr(0x8005, lo(ref(0x8130) - 1))    # lda #<(table - 1)

Backward compatibility: a plain string is still accepted and is parsed
from the beebasm/py8dis dialect (``"table-1"``, ``"HI(x)"``,
``"a AND &FF"``) into the same tree, so existing drivers need no changes.
Prefer the DSL in new code — it is checked at build time and renders
correctly to every backend.

The :doc:`cookbook <cookbook_expressions>` works through expressions
(and macros) from simple to advanced.


.. _indexed-base-addresses:

Indexed-base addresses and regions
----------------------------------

Some addresses are only ever the *base* of an indexed operand — the
byte the instruction touches is ``base + X`` (or ``base + Y``), and the
base itself is never read or written. The classic case is a per-channel
or per-control-block workspace pointer copied with ``lda base,X`` where
``X`` selects the block. Naming such a base with a plain
:meth:`~dasmos.Disassembler.label` is misleading: it appears on the
memory map as a location the ROM owns, and its cross-reference count
implies reads and writes that never happen at that exact byte.

:meth:`~dasmos.Disassembler.index_base` names a base *as a base*. It
keeps the name, description and group — so the ``,X`` operand still
resolves and stays documented — and asserts the **base** access flag, so
its cross-reference reads ``used as index base N times`` rather than
``referenced N times``:

.. code-block:: python

   d.index_base(0x0000, "zp_user_ptr_0", group="zero_page",
                description="Caller's zero-page pointer, byte 0; the "
                            "transfer copies base+0..+3 via lda ...,X.")

In the JSON renderer such a base is an ordinary ``memory_map`` row whose
``access`` array contains ``"b"`` (a ``["b"]``-only row: documented in
place, but the literal byte is never touched, only indexed through).
Access is modelled as orthogonal ``r`` / ``w`` / ``b`` flags, so an
address that is both read and used as a base comes out ``["r", "b"]``.

.. note::

   For a base (or any map entry) to sit *in place* within the
   surrounding workspace layout it needs a ``group=``, like every other
   entry. As an interim aid, the JSON renderer emits a ``UserWarning``
   naming any ``memory_map`` entries authored without one — add a
   ``group=`` to each to silence it. This stop-gap is removed once the
   per-driver grouping audit lands (``dasmos#43``).

When several bases cluster around a named anchor — reached via indexed
addressing with small displacements — declare an *indexing region*
instead of naming each byte. :meth:`~dasmos.Disassembler.index_region`
takes the anchor's address and name plus an inclusive offset
``window``; in-window neighbours then render relative to the anchor:

.. code-block:: python

   d.index_region(0x0E00, "fsm_sector0", window=(-6, 0),
                  description="Free-space-map sector 0; compaction "
                              "sweeps the notional entries just below it.")

An operand whose base falls three bytes below the anchor now renders as
``lda fsm_sector0-3,X`` — the ``anchor±k`` arithmetic reassembles to the
same bytes — instead of needing a hand-written ``fsm_s0_pre3`` label for
each slot. Pass ``named_slots=True`` to give each gap a distinct
identifier (``fsm_sector0_m3`` / ``fsm_sector0_p3``) rather than the
arithmetic form.

A region names only the *gaps*: an explicit
:meth:`~dasmos.Disassembler.label` you place inside the window always
wins (precedence: explicit label → region form → auto-label → hex), so
a region and individually-named locations coexist over the same address
range. Region windows must be disjoint; an overlapping declaration
raises at call time.

For the workflow and judgement of retrofitting these calls onto an
already-annotated driver — how to find candidates, which labels to
leave alone, and when *not* to reach for a region — see
:doc:`cookbook`.


Marking subroutines
-------------------

:meth:`~dasmos.Disassembler.subroutine` is the high-density combo:
it declares an entry point, a label, *and* a banner comment block in
one call. The ``title`` and ``description`` are the heart of a
self-documenting driver:

.. code-block:: python

   d.subroutine(
       0x9200,
       "send_packet",
       title="Send an Econet packet",
       description="""
   Sends a packet whose control byte, source/destination station, and
   payload are pre-loaded into the TX buffer at [tx_buffer](address:0E00).
   """,
       on_entry={
           "A": "packet length (bytes)",
           "X": "TX buffer page",
           "Y": "retry count",
       },
       on_exit={
           "C": "set on transmit failure, clear on success",
       },
   )

The ``on_entry`` and ``on_exit`` keywords are register-name → description
dictionaries. Renderers format them into a structured "On entry" /
"On exit" block beneath the title and description, so the calling
convention stays in machine-readable form for the JSON renderer
(downstream HTML can render it as a real table) and as a clean
labelled block in the asm output. Use them for register / flag
contracts; reserve ``description`` for free-form prose about what the
subroutine does and why.

Both ``title`` and ``description`` accept full Markdown — paragraphs,
bullet lists, tables, fenced code blocks, inline emphasis and code,
plus the custom ``[label](address:HEX)`` cross-reference URI scheme.
Asm renderers strip the markup down to plain text suitable for ``;``
comment lines; the JSON renderer keeps the source verbatim for
downstream HTML processors.


.. _driver-comments-are-markdown:

Comments
--------

**All driver-provided prose is Markdown.** Every piece of free text you
hand dasmos — :meth:`~dasmos.Disassembler.comment` bodies, subroutine /
banner descriptions (:meth:`~dasmos.Disassembler.subroutine`),
:meth:`~dasmos.Disassembler.label` descriptions,
:meth:`~dasmos.Disassembler.constant` comments, and the file header
(:meth:`~dasmos.Disassembler.set_file_header`) — is CommonMark + GFM,
plus the ``[label](address:…)`` cross-reference scheme below. dasmos
renders it *appropriately per output*: assembler renderers flatten it to
``;``-prefixed comment plaintext (emphasis, code spans, lists and tables
all reduced to readable text, paragraphs wrapped); the JSON renderer
keeps the **source Markdown verbatim** so a downstream HTML processor can
render it richly. Write Markdown once; each backend does the right thing.

:meth:`~dasmos.Disassembler.comment` attaches such text at an address.

.. code-block:: python

   d.comment(0x9210, "Set carry to signal failure", inline=True)
   d.comment(0x9220, """
   ## Reception loop

   Polls the [System VIA](address:FE40) for an SR interrupt; on each
   one, reads the byte, appends it to the buffer, and resets the
   interrupt latch.
   """)

The ``inline=True`` form (or ``align=Align.INLINE``) renders as a
trailing remark on the same line as the instruction. Plain comments
(default ``align=Align.BEFORE``) render as one or more ``;``-prefixed
lines preceding the instruction.

Cross-references in comment text use a custom URI scheme:

============================== ===========================================
Form                           Renders as
============================== ===========================================
``[foo](address:E000)``        ``foo`` (label-only)
``[foo](address:E000?hex)``    ``foo (&E000)`` (label and hex literal)
============================== ===========================================

In the asm renderer the link collapses to its visible text; in the
JSON renderer the URI is preserved so an HTML post-processor can turn
it into a real anchor.

Comment authoring conventions follow the same rules as the
acornaeology disassembly project — see ``AUTHORING.md`` in the
acornaeology.github.io repo for the in-depth treatment, including the
single-newline-is-a-soft-break CommonMark gotcha (use a blank line
between paragraphs to get separate ``;`` lines in the output).


Top-of-file preamble: header and build instructions
----------------------------------------------------

A generated listing can open with a **provenance header** — prose stating
what the disassembly is and where it came from. It is backend-agnostic:
you supply the text; each renderer applies only its own comment prefix.
Set it with :meth:`~dasmos.Disassembler.set_file_header`.

Like every driver comment, the ``title`` and ``description`` are
**Markdown** (see :ref:`the note below <driver-comments-are-markdown>`).
Assembler renderers flatten it to comment plaintext; the JSON renderer
keeps the source Markdown verbatim. So a single newline is a soft break
(a space) — use a blank line between paragraphs, or a Markdown list, to
get separate provenance lines:

.. code-block:: python

   d.set_file_header(
       title="Acorn BBC BASIC II",
       description=(
           "Annotated disassembly of the 16 kB BASIC II language ROM.\n"
           "\n"
           "- Source md5: `2cc6…`\n"
           "- Source sha256: `45bd…`"
       ),
   )

renders (beebasm, and identically on 64tass with its own prefix):

.. code-block:: text

   ; Acorn BBC BASIC II
   ;
   ; Annotated disassembly of the 16 kB BASIC II language ROM.
   ;
   ; - Source md5: 2cc6…
   ; - Source sha256: 45bd…

The header also surfaces in the JSON renderer's ``meta`` as optional
``title`` / ``description`` fields (the source Markdown, verbatim), so
structured consumers get it too. dasmos stores only your text — it
hardcodes no provenance, so the header stays reusable across projects.

Separately, a renderer can be asked to emit a **"how to assemble this
file"** command in its own tool's syntax — off by default, opt in with a
renderer keyword:

.. code-block:: python

   ir.render("beebasm", include_build_instructions=True,
             listing_filename="basic-2.asm")

.. code-block:: text

   ; Assemble with beebasm:
   ;   beebasm -i basic-2.asm

The command is the backend's own (64tass emits its
``64tass --nostart -o … …`` form); the driver only decides whether to
include it. ``listing_filename`` names the ``.asm`` the command reads (the
renderer doesn't otherwise know it). Both the header and the build block
are comment-only, so assembled bytes are unaffected and the round-trip
still holds.

.. note:: **Naming the output — and the beebasm** ``save`` **coupling.**

   How the concrete output name appears in the beebasm command depends on
   how the listing produces the binary, and the two interact:

   - :meth:`set_output_filename <dasmos.Disassembler>` makes the beebasm
     renderer emit a ``save "<file>", start, end`` directive; the command
     is then ``beebasm -i <listing>`` (the ``save`` writes the file).
     **But beebasm ignores** ``-o`` **when a** ``save`` **filename is
     present** — so an external harness that captures the binary via
     ``beebasm … -o out.rom`` (e.g. a verify/CI step) gets an empty
     capture and the round-trip check fails.
   - For an ``-o``-based harness, therefore, leave the output filename
     unset (the ``save`` stays filename-less) and pass ``build_output_name``
     to name the ``-o`` target *for the command comment only*, decoupled
     from the ``save`` directive::

        ir.render("beebasm", include_build_instructions=True,
                  listing_filename="basic-2.asm",
                  build_output_name="basic-2.rom")
        # →  ;   beebasm -i basic-2.asm -o basic-2.rom
        #    (and the emitted ``save`` remains filename-less)

   64tass has no in-source ``save``, so it always uses ``-o`` and this
   coupling doesn't arise; ``build_output_name`` simply names its target.


Load-and-run programs (exec / reload addresses)
-----------------------------------------------

A ROM lives at a fixed address, but a DFS ``*RUN`` program *loads* at
one address and may *begin execution* at another (its **exec** address),
with the filesystem recording a **reload** address distinct from where
the bytes sit. :meth:`~dasmos.Disassembler.program` declares that
metadata once, in the model, independent of any assembler syntax:

.. code-block:: python

   d.program(exec_addr=0x3906, reload_addr=0x1900)

Each renderer emits what it can express:

- the beebasm renderer folds them into its ``save`` directive —
  ``save "NAME", start, end, &3906, &1900`` — so the produced file is
  directly ``*RUN``-able and its DFS header matches the original;
- the JSON renderer surfaces them under ``meta.program``;
- 64tass, which saves via ``-o`` and has no exec/reload concept for a
  raw binary, warns and omits them. The raw payload — and so
  ``fantasm verify`` — is unaffected either way.

``reload_addr`` defaults to the loaded range's start when omitted; every
argument is optional.


Classifying data
----------------

Code that the trace can't reach — jump tables, parameter blocks, text
strings, unused space — needs to be told what shape it has, otherwise
the renderer emits raw bytes:

:meth:`~dasmos.Disassembler.byte` declares a run of bytes:

.. code-block:: python

   d.byte(0x9300, length=16)        # 16 raw bytes

:meth:`~dasmos.Disassembler.word` declares 16-bit words:

.. code-block:: python

   d.word(0x9400, length=8)         # 8 16-bit words = 16 bytes

:meth:`~dasmos.Disassembler.string` declares a run of text:

.. code-block:: python

   d.string(0x9500, length=12)      # "HELLO BEEB!\r"

:meth:`~dasmos.Disassembler.stringz` is the convenience for
zero-terminated strings (length is found by scanning to the
terminator):

.. code-block:: python

   d.stringz(0x9510)

:meth:`~dasmos.Disassembler.fill` marks a region as filler that
should render compactly (``equb &00 [* N]`` or similar):

.. code-block:: python

   d.fill(0x9F00, length=0x100)

For pointer tables that *do* contain code addresses but which the
trace can't follow (because they're indirect-dispatched via
``rts`` push tricks or table indexing), use
:meth:`~dasmos.Disassembler.code_ptr` and
:meth:`~dasmos.Disassembler.rts_code_ptr` to declare each pointer as
a code reference. Both also seed the trace at the pointed-to address,
which often unlocks large stretches of previously-unreachable code.


Automatic string detection
--------------------------

After tracing classifies code and the explicit ``d.byte`` /
``d.word`` / ``d.string`` calls run, *Dasmos* sweeps the leftover
unclassified bytes for runs of printable ASCII and promotes them to
:class:`~dasmos.core.classification.String` classifications. This
saves you from having to call :meth:`~dasmos.Disassembler.string`
on every text fragment hidden in the ROM — message tables, status
strings, error text, and the like surface as ``equs "..."`` rows
without manual annotation.

The threshold is the minimum run length that gets promoted, set on
:meth:`Disassembler.create` (or as a plain attribute on the
disassembler):

.. code-block:: python

   # Default — promote runs of 3 or more printable bytes.
   d = dasmos.Disassembler.create(cpu="6502")

   # Tighter — only runs of 5 or more, useful for ROMs where short
   # printable byte sequences are usually data, not text.
   d = dasmos.Disassembler.create(cpu="6502", string_detection_min_length=5)

   # Disabled — leave every printable run alone for the leftover
   # ``Byte`` aggregator to handle. Useful for binary-data ROMs
   # where the printable-ASCII heuristic would mostly misfire.
   d = dasmos.Disassembler.create(cpu="6502", string_detection_min_length=None)

Runs break at any of: a labelled address, a non-printable byte, an
already-classified byte, a move source-boundary, or a byte with any
attached annotation. So an explicit ``d.label(...)`` /
``d.comment(...)`` at a mid-string address splits the detection at
exactly the boundary you want, giving you per-segment control without
turning the heuristic off entirely.


Operand format hints
--------------------

Some operand bytes have a *semantic intent* the renderer can't infer
from the bytes alone. ``LDA #&41`` could be loading the ASCII code
for ``A``, a hex-format register flag, or a binary bit pattern — the
byte value is the same; the rendered form should differ. Format
hints declare the intent in the IR, and each renderer translates the
hint into its own assembler-syntax appropriate form.

The general form is :meth:`Disassembler.format_hint
<dasmos.Disassembler.format_hint>` taking a
:class:`~dasmos.core.format_hint.FormatHint` enum value:

.. code-block:: python

   from dasmos import FormatHint

   # Address is the OPERAND byte (one past the LDA opcode for a
   # single-byte-opcode CPU like the 6502). With LDA #&aa at &e016,
   # the operand is at &e017 — rendering it as %10101010 makes the
   # alternating-bit intent read.
   d.format_hint(0xe017, FormatHint.BINARY)

The current set of hints is ``CHAR``, ``DECIMAL``, ``HEX``,
``BINARY``, ``OCTAL`` and ``INKEY`` (BBC-specific keyboard scan
code). The beebasm renderer translates each into its native form
(``ASC("A")`` or ``'A'`` for ``CHAR``; ``%01010101`` for ``BINARY``;
``(255 - inkey_key_<name>) EOR 128`` for ``INKEY``). The JSON
renderer surfaces the hint in the per-operand record so downstream
tooling can choose its own syntax.

Two sugar methods cover the cases used most often:

.. code-block:: python

   # The byte at &9412 is intended as an ASCII character literal —
   # the renderer chooses ASC("c") / 'c' / similar by its
   # char_literal_style.
   d.char_literal(0x9412)

   # The byte at &a3c7 is the negative-X-form INKEY scan code an
   # OSBYTE &79 / &81 caller loads to scan for one specific key.
   # Renders as ``(255 - inkey_key_ctrl) EOR 128`` etc.
   d.inkey_code(0xa3c7)

When the ``acorn_mos`` env's OSBYTE analyser detects a recognisable
INKEY pattern (``A=&79`` or ``A=&81`` with ``X`` carrying a known
scan code), it registers ``FormatHint.INKEY`` automatically — call
:meth:`~dasmos.Disassembler.inkey_code` only when the analyser
can't infer the pattern (a scan code in a pre-computed table, or
loaded into ``X`` through an indirect path). Driver-supplied
expressions via :meth:`~dasmos.Disassembler.expr` always win over
hints, so ``d.expr(operand_addr, "my_text")`` overrides any analyser
or driver hint at the same address.


Putting it together: a fuller driver
------------------------------------

A more complete picture of how the pieces compose:

.. code-block:: python

   from pathlib import Path

   import dasmos
   from dasmos import Align

   ROM_PATH = Path("nfs365.rom")
   ROM_MD5 = "3a7f…"
   LOAD_ADDR = 0x8000

   d = dasmos.Disassembler.create(
       cpu="6502",
       environments=["acorn_mos", "acorn_model_b_hardware"],
   )
   d.load(ROM_PATH, LOAD_ADDR, md5sum=ROM_MD5)

   # Service-ROM header entry vectors.
   d.entry(0x8000, "service_rom_language")
   d.entry(0x8003, "service_rom_service")

   # Magic numbers.
   d.constant(0x0F, "osbyte_read_input_status")
   d.constant(0x80, "osbyte_read_adc")

   # A named subroutine with a Markdown description and a
   # cross-reference to a related routine.
   d.subroutine(
       0x9200,
       "send_packet",
       title="Send an Econet packet",
       description="""
   Sends a packet whose control byte and payload are pre-loaded into
   the TX buffer. See [recv_packet](address:9300?hex) for the matching
   receive path.
   """,
   )

   # An inline note at the trickiest line of the routine.
   d.comment(0x9215, "ACR mode 2: shift in under φ2", inline=True)

   # A jump table the trace can't follow on its own.
   for i in range(8):
       d.code_ptr(0x9F00 + 2 * i)

   # Zero-padded tail of the ROM.
   d.fill(0xBFE0, length=0x20)

   ir = d.disassemble()
   print(str(ir.render("beebasm")))


Switching renderers
-------------------

The same intermediate representation feeds every renderer. The two
that ship with *Dasmos*:

``beebasm``
   Re-assemblable assembly source. The default. Targets the
   `beebasm <https://github.com/stardot/beebasm>`_ syntax that's
   standard in the BBC Micro / Master ecosystem; the round-trip
   (binary → driver → beebasm-assembly → binary) is *Dasmos*'s
   correctness oracle.

``json``
   Structured representation: every label, instruction, comment, and
   cross-reference as JSON. Use this when you're feeding the
   disassembly into another tool — an HTML site generator, a diff
   utility, a parity-checker against a reference output.

To get both from one driver run, render twice:

.. code-block:: python

   ir = d.disassemble()
   Path("nfs365.asm").write_text(str(ir.render("beebasm")))
   Path("nfs365.json").write_text(str(ir.render("json")))

Third-party renderers register themselves via Stevedore entry points
under the ``dasmos.renderer`` namespace; once installed, a renderer
becomes available by name to every driver and to the
``--renderer`` flag of ``dasmos disassemble``.


Hooking subroutines
-------------------

When a ROM repeatedly calls a known subroutine and you'd like
context-aware analysis at every call site (e.g., recognising the A
register at the call as an OSBYTE action code and looking it up in
an enum), :meth:`~dasmos.Disassembler.hook_subroutine` registers a
Python callable that runs against the disassembler state at every
call site:

.. code-block:: python

   def my_hook(d, call_site, regs):
       # called once per JSR/JMP to the hooked address.
       ...

   d.hook_subroutine(0xFFF4, "osbyte", my_hook)

Most users won't write hooks directly — the ``acorn_mos`` environment
ships hooks for OSBYTE, OSWORD, OSFIND, OSFILE, OSGBPB, and OSEVEN
that already do A-register-action and X-register-secondary lookups
into the enums catalogued in :mod:`dasmos.ext.environments.acorn_mos`.
Reach for ``hook_subroutine`` when you need to encode call-site
conventions specific to your particular ROM.


Where to go next
----------------

- :doc:`cli` — the one-shot command and the ``init`` scaffolder.
- :doc:`api` — the full autodoc reference for every public symbol.
- ``acornaeology.github.io/AUTHORING.md`` — the comment-Markdown and
  memory-map metadata conventions used across the acornaeology
  disassembly project.
