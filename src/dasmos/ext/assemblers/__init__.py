"""Built-in assembler-syntax (renderer) plug-ins.

Each leaf sub-package's ``__init__.py`` re-exports the concrete
assembler class under the uniform name ``Assembler``::

    from .beebasm import BeebasmAssembler as Assembler

The matching entry point in ``pyproject.toml`` then references
``dasmos.ext.assemblers.<name>:Assembler``.
"""
