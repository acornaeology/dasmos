dasmos
======

A pluggable tracing disassembler for retro-CPU ROMs, with first-class
support for the 6502 and the BBC Micro / Master family.

dasmos has two surfaces. The :doc:`command line <cli>` runs the whole
pipeline against a binary in one shot — useful for triage, sanity
checks, and CI wiring. The :doc:`driver-script API <driver_api>` is
where serious analysis lives: a Python script declares labels,
subroutines, comments, data classifications, and cross-references, and
re-running the script regenerates the listing as the analysis evolves.

The CLI's ``dasmos init`` command bridges the two — it scaffolds a
runnable starter driver from the same options you'd pass to
``dasmos disassemble``.

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
