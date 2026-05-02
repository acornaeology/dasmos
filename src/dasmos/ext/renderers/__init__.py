"""Built-in renderer plug-ins.

Each leaf sub-package's ``__init__.py`` re-exports the concrete
renderer class under the uniform name ``Renderer``::

    from .beebasm import BeebasmRenderer as Renderer

The matching entry point in ``pyproject.toml`` then references
``dasmos.ext.renderers.<name>:Renderer``.
"""
