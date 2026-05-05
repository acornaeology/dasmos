"""Acorn 1770 floppy disc controller environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_fdc_1770.environment import (
    AcornFdc1770Environment,
    AcornFdc1770Environment as Environment,
)

__all__ = ["AcornFdc1770Environment", "Environment"]
