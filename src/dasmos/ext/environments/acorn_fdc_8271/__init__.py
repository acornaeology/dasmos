"""Acorn 8271 floppy disc controller environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_fdc_8271.environment import (
    AcornFdc8271Environment,
    AcornFdc8271Environment as Environment,
)

__all__ = ["AcornFdc8271Environment", "Environment"]
