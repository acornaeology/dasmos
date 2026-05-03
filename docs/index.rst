Dasmos
======

   *From Ancient Greek* δασμός *(dasmós, "division"), from* δαίω
   *(daíō, "to divide, share").*

A pluggable tracing disassembler for retro-CPU ROMs, with first-class
support for the 6502 and the BBC Micro / Master family.

*Dasmos* has two surfaces. The :doc:`command line <cli>` runs the whole
pipeline against a binary in one shot — useful for triage, sanity
checks, and CI wiring. The :doc:`driver-script API <driver_api>` is
where serious analysis lives: a Python script declares labels,
subroutines, comments, data classifications, and cross-references, and
re-running the script regenerates the listing as the analysis evolves.

The CLI's ``dasmos init`` command bridges the two — it scaffolds a
runnable starter driver from the same options you'd pass to
``dasmos disassemble``.


Lineage and acknowledgements
----------------------------

*Dasmos* is a ground-up rewrite and reimagining of a heavily modified
`fork <https://github.com/acornaeology/py8dis>`_ of
`py8dis <https://github.com/ZornsLemma/py8dis>`_ — Steven Flintham's
original programmable tracing disassembler for the 6502 family. The
whole core idea — driver scripts, traced classification,
label / comment / banner annotations — comes from py8dis, and *Dasmos*
owes Steven a debt of gratitude for inventing and sharing it. This
rewrite restructures the same vocabulary around Stevedore extension
points so CPUs, renderers, and target environments ship as composable
plug-ins.

The acornaeology py8dis fork accumulated enough new capability
(JSON renderer, environment hooks, BBC Master coverage) that an
independent project became the right next step. Driver scripts
written for the fork port to *Dasmos* with the bundled
``scripts/py8dis2dasmos.py`` AST porter.


.. toctree::
   :maxdepth: 2
   :caption: Contents

   cli
   driver_api
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
