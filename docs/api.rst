API reference
=============

The entire public API is re-exported from the top-level ``dasmos``
package, so ``from dasmos import Disassembler, Align`` is the
intended import path. The sub-module documentation below is for
readers who want the full picture.


Top-level package
-----------------

.. automodule:: dasmos
   :members:
   :imported-members:


The source-module sections below use ``:no-index:`` so the symbols
re-exported via ``dasmos`` (above) remain the canonical cross-reference
targets — the per-module pages exist purely to give readers a
module-by-module navigation aid.


The Disassembler
----------------

.. automodule:: dasmos.disassembler
   :members:
   :show-inheritance:
   :no-index:


Intermediate representation
---------------------------

.. automodule:: dasmos.ir
   :members:
   :show-inheritance:
   :no-index:


Annotations: comments and banners
---------------------------------

.. automodule:: dasmos.core.annotations
   :members:
   :show-inheritance:
   :no-index:


Output: text and structured
---------------------------

.. automodule:: dasmos.output
   :members:
   :show-inheritance:
   :no-index:


CPU extension point
-------------------

.. automodule:: dasmos.cpu
   :members:
   :show-inheritance:
   :no-index:


Renderer extension point
------------------------

.. automodule:: dasmos.renderer
   :members:
   :show-inheritance:
   :no-index:


Environment extension point
---------------------------

.. automodule:: dasmos.environment
   :members:
   :show-inheritance:
   :no-index:


Extension base
--------------

.. automodule:: dasmos.extension
   :members:
   :show-inheritance:
   :no-index:


Exceptions
----------

.. automodule:: dasmos.exceptions
   :members:
   :show-inheritance:
   :no-index:
