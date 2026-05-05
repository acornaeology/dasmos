"""Acorn BBC Master hardware environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_master_hardware.environment import (
    AcornMasterHardwareEnvironment,
    AcornMasterHardwareEnvironment as Environment,
)

__all__ = ["AcornMasterHardwareEnvironment", "Environment"]
