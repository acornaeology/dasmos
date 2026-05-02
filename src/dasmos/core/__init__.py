"""Internal core machinery for the dasmos disassembler.

Lifted from the py8dis fork with design-smell fixes applied per port:
module-level globals replaced with instance state, ``sys.exit``-style
failures replaced with raised exceptions, cyclic imports replaced with
injected dependencies. Consumers should import from the top-level
:mod:`dasmos` package — this sub-package is internal and may change.
"""
