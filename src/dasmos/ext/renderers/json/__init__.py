"""JSON structured-output renderer plug-in for dasmos.

Re-exports the concrete class under the uniform symbol :class:`Renderer`
expected by the ``dasmos.renderer`` Stevedore entry point per the
sixty-north ``ext/`` packaging convention.
"""

from dasmos.ext.renderers.json.renderer import (
    JsonRenderer,
    JsonRenderer as Renderer,
)

__all__ = [
    "JsonRenderer",
    "Renderer",
]
