Command-line reference
======================

dasmos installs a single ``dasmos`` script, organised as a Click
command group. Three command families:

- **Discovery** — ``list-cpus``, ``list-renderers``, ``list-environments``
  and the matching ``describe-…`` commands. Read-only; useful for
  finding what's installed and for ``--help``-style introspection.
- **Disassemble** — ``dasmos disassemble`` is the one-shot that runs
  the whole pipeline against a binary without a driver script.
- **Init** — ``dasmos init`` scaffolds a runnable driver script
  pre-filled with the same configuration you'd pass to ``disassemble``.

Run ``dasmos --help`` to see them all, or ``dasmos COMMAND --help`` for
per-command flags.


Address syntax
--------------

Every option that takes an address — ``--load-addr``, ``--entry``, and
the equivalents on ``init`` — accepts four notations interchangeably:

============= ===================================================
Notation      Convention
============= ===================================================
``0x8000``    C / Python hex.
``&8000``     beebasm / BBC BASIC hex.
``$8000``     ca65 / Apple-II hex.
``32768``     bare decimal.
============= ===================================================

Hex parsing is case-insensitive: ``&FFEE`` and ``&ffee`` both work.
Anything else — a stray prefix, embedded whitespace, a typo — fails at
parse with Click's standard usage error rather than running with a
silently-wrong address.


``dasmos disassemble`` — one-shot
---------------------------------

.. code-block:: console

   dasmos disassemble ROM --load-addr ADDR [options]

Loads ``ROM`` at ``ADDR``, seeds the trace from each ``--entry`` (or
from the load address by default), runs the trace + classification +
reference-analysis pipeline, and renders the result via the chosen
renderer plug-in.

The minimum is a binary plus its load address:

.. code-block:: console

   dasmos disassemble nfs365.rom --load-addr '&8000'

Output goes to stdout by default, or to a file with ``--out``.

Options
~~~~~~~

``-a``, ``--load-addr`` *ADDR* (required)
   Address where the binary is loaded. Required because every other
   address in the run is interpreted relative to this one.

``-c``, ``--cpu`` *NAME* (default: ``nmos6502``)
   CPU plug-in name. Run ``dasmos list-cpus`` to see what's installed.

``-r``, ``--renderer`` *NAME* (default: ``beebasm``)
   Renderer plug-in. ``beebasm`` produces re-assemblable assembly
   source; ``json`` produces a structured representation suitable for
   downstream HTML generators or diff-based comparison tools. Run
   ``dasmos list-renderers`` to see the full list.

``-e``, ``--env`` *NAME*
   Activate an environment plug-in — a bundle of register names,
   subroutine hooks, OS-call analysers, and hardware-port labels for a
   target system. Repeatable, and comma-separated values are accepted
   per flag, so ``--env acorn_mos --env acorn_bbc_hardware`` and
   ``--env acorn_mos,acorn_bbc_hardware`` are equivalent. Run
   ``dasmos list-environments`` for the catalogue.

``--entry`` *ADDR*
   Entry-point address. Repeatable. Defaults to the load address. Use
   when the binary's true entry isn't its first byte — for example, a
   ROM image whose header bytes are data and whose code starts at
   ``load_addr + 9``.

``-o``, ``--out`` *PATH*
   Write the rendered output to this file instead of stdout.

``--md5`` *HASH*
   Pin the ROM's MD5 hash. The disassembly fails (without writing
   output) if the actual hash differs. Use to catch the
   wrong-binary-for-this-driver mistake early.

Worked example
~~~~~~~~~~~~~~

Disassemble a BBC Master Acorn NFS ROM with the MOS environment
active, seeding the trace from the standard service-ROM entry vectors:

.. code-block:: console

   dasmos disassemble nfs365.rom \
       --load-addr '&8000' \
       --env acorn_mos \
       --env acorn_bbc_hardware \
       --entry '&8000' \
       --entry '&8003' \
       --out nfs365.asm

The resulting ``nfs365.asm`` will resolve every ``jsr &FFxx`` to its
MOS entry-point name (``osbyte``, ``osword``, ``osfile``, …) and
every System/User VIA address to its hardware-port label.


``dasmos init`` — scaffold a driver
-----------------------------------

.. code-block:: console

   dasmos init DRIVER --rom ROM --load-addr ADDR [options]

Writes a starter Python driver to ``DRIVER`` configured against
``ROM``. The generated file is fully functional — running
``python DRIVER`` produces the same output as
``dasmos disassemble`` with the same flags. From there you edit the
driver to add labels, comments, and classifications as your analysis
evolves.

The flag set mirrors ``disassemble`` plus a couple of init-specific
extras:

``--rom`` *PATH* (required)
   ROM the generated driver will disassemble. Embedded into the file
   as a ``Path(...)`` literal.

``-a``, ``--load-addr`` *ADDR* (required)
   Embedded as ``LOAD_ADDR``.

``-c``, ``--cpu``, ``-r``, ``--renderer``, ``-e``, ``--env``, ``--entry``, ``--md5``
   Carry the same meanings as on ``disassemble`` and are baked into
   the generated ``Disassembler.create(...)`` / ``d.entry(...)``
   / ``d.load(..., md5sum=...)`` calls.

``--force``
   Overwrite an existing driver file. Without it, ``init`` refuses to
   clobber existing work and exits with an error.

Worked example
~~~~~~~~~~~~~~

Bootstrap a driver for the same ROM the ``disassemble`` example used:

.. code-block:: console

   dasmos init disasm_nfs365.py \
       --rom nfs365.rom \
       --load-addr '&8000' \
       --env acorn_mos \
       --env acorn_bbc_hardware \
       --entry '&8000' \
       --entry '&8003' \
       --md5 $(md5 -q nfs365.rom)

Then ``python disasm_nfs365.py`` reproduces the listing, and the file
is the editable canvas where you add ``d.label(...)``,
``d.subroutine(...)``, ``d.comment(...)``, and so on. See the
:doc:`driver-script API guide <driver_api>` for the full vocabulary.


Discovery commands
------------------

Three pairs of read-only commands enumerate and describe the plug-ins
the current installation knows about:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Lists / describes
   * - ``dasmos list-cpus``
     - Registered CPU plug-ins.
   * - ``dasmos describe-cpu NAME``
     - Full description of one CPU plug-in.
   * - ``dasmos list-renderers``
     - Registered renderer plug-ins.
   * - ``dasmos describe-renderer NAME``
     - Full description of one renderer plug-in.
   * - ``dasmos list-environments``
     - Registered environment plug-ins.
   * - ``dasmos describe-environment NAME``
     - Full description of one environment plug-in.

These commands are themselves :mod:`asyoulikeit`-decorated, so each
inherits ``--as / --report / --header / --detailed`` for free. Pipe
into ``jq``:

.. code-block:: console

   dasmos list-cpus --as json | jq '.reports.cpus.rows[].name'

or just run with no flags for a human-readable table.
