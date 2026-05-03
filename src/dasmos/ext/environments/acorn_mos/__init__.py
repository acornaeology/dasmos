"""Acorn MOS environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_mos.environment import (
    AcornMosEnvironment,
    AcornMosEnvironment as Environment,  # uniform symbol
)

__all__ = ["AcornMosEnvironment", "Environment"]
