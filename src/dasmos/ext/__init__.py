"""Built-in extensions packaged with dasmos.

Each extension *kind* lives in a sub-package named in the plural form
(``cpus/``, ``assemblers/``). Each individual extension within a kind
is a leaf sub-package whose ``__init__.py`` re-exports its concrete
class under the kind's uniform symbol — see
``ext/<plural-kind>/<name>/__init__.py``.
"""
