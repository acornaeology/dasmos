"""64tass renderer plug-in for dasmos.

Re-exports the concrete class under the uniform symbol :class:`Renderer`
expected by the ``dasmos.renderer`` Stevedore entry point per the
sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.renderers.tass64.renderer import (
    Tass64Renderer,
    Tass64Renderer as Renderer,  # the uniform symbol the entry point references
)

__all__ = [
    "Tass64Renderer",
    "Renderer",
]
