"""Beebasm renderer plug-in for dasmos.

Re-exports the concrete class under the uniform symbol :class:`Renderer`
expected by the ``dasmos.renderer`` Stevedore entry point per the
sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.renderers.beebasm.renderer import (
    BeebasmRenderer,
    BeebasmRenderer as Renderer,  # the uniform symbol the entry point references
)

__all__ = [
    "BeebasmRenderer",
    "Renderer",
]
