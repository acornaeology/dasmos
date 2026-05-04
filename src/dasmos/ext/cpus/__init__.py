"""Built-in CPU (processor) plug-ins.

Each leaf sub-package's ``__init__.py`` re-exports the concrete CPU
class under the uniform name ``Cpu``::

    from .cpu6502 import Nmos6502Cpu as Cpu

The matching entry point in ``pyproject.toml`` then references
``dasmos.ext.cpus.<name>:Cpu``.
"""
