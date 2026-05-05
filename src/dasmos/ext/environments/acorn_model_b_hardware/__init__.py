"""Acorn BBC Model B hardware environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.acorn_model_b_hardware.environment import (
    AcornModelBHardwareEnvironment,
    AcornModelBHardwareEnvironment as Environment,
)

__all__ = ["AcornModelBHardwareEnvironment", "Environment"]
