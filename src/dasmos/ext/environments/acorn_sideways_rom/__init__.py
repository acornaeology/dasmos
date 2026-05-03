"""Acorn sideways ROM environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_sideways_rom.environment import (
    AcornSidewaysRomEnvironment,
    AcornSidewaysRomEnvironment as Environment,  # uniform symbol
)

__all__ = ["AcornSidewaysRomEnvironment", "Environment"]
