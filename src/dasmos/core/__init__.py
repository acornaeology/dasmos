"""Internal core machinery for the dasmos disassembler.

State lives on instances rather than module-level globals; failures
raise exceptions rather than calling ``sys.exit``; collaborators are
wired by dependency injection rather than module-level imports.
Consumers should import from the top-level :mod:`dasmos` package —
this sub-package is internal and may change.
"""
