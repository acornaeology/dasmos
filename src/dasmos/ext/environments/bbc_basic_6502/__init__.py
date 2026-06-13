"""BBC BASIC (6502) environment plug-in for dasmos.

Re-exports the concrete class under the uniform symbol
:class:`Environment` expected by the ``dasmos.environment`` Stevedore
entry point per the sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.environments.bbc_basic_6502.environment import (
    BbcBasic6502Environment,
    BbcBasic6502Environment as Environment,  # uniform symbol
)
from dasmos.ext.environments.bbc_basic_6502.floats import (
    BbcFloat5,
    decode_bbc_float5,
)

__all__ = [
    "BbcBasic6502Environment",
    "Environment",
    "BbcFloat5",
    "decode_bbc_float5",
]
