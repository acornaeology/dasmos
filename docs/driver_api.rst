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

   d = dasmos.Disassembler.create(cpu="nmos6502")
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
       cpu="nmos6502",
       environments=["acorn_mos", "acorn_bbc_hardware"],
   )

With ``acorn_mos`` active, ``jsr &FFF4`` resolves to ``jsr osbyte``
without you having to declare the label yourself; with
``acorn_bbc_hardware`` active, reads of ``&FE40`` resolve to the
System VIA's ``via_system_orb`` instead of a bare hex literal. Run
``dasmos list-environments`` to see what's installed.

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

Once you've identified what an address *means*, name it. dasmos has
three flavours of name, corresponding to three different commitments:

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

   d.label(0x220, "irq1v")
   d.expr_label(0x221, "irq1v+1")

After which a reference to ``&221`` renders as ``irq1v+1`` instead of
``l0221``.


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


Comments
--------

:meth:`~dasmos.Disassembler.comment` attaches free-form text at an
address. Like subroutine descriptions, comment text is full Markdown.

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
       cpu="nmos6502",
       environments=["acorn_mos", "acorn_bbc_hardware"],
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
that ship with dasmos:

``beebasm``
   Re-assemblable assembly source. The default. Targets the
   `beebasm <https://github.com/stardot/beebasm>`_ syntax that's
   standard in the BBC Micro / Master ecosystem; the round-trip
   (binary → driver → beebasm-assembly → binary) is dasmos's
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
