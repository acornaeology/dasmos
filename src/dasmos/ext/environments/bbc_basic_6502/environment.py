"""BBC BASIC (6502) environment plug-in.

Supplies knowledge specific to the BBC BASIC *language* ROM — as
distinct from the MOS (:mod:`...acorn_mos`) or the host hardware. The
first such piece is the packed **5-byte floating-point** data type used
for BASIC's REAL constants (e, π/2, ln 2, the trig-coefficient tables,
…); activating this environment registers it under the name
``"bbc_float5"`` so a driver can write::

    d.use_environment("bbc_basic_6502")
    d.typed_data(0xAAE4, "bbc_float5", comment="e (Euler's number)")

and have the five raw bytes emitted for byte-faithful reassembly with
the decoded value (``2.718281828``) surfaced as an annotation.

The decoder lives here, in the environment, rather than in core —
mirroring how the INKEY scan-code table lives in ``acorn_mos`` — so
core stays machine-agnostic. A driver that wants a one-off decode
without activating the env can instead pass the
:class:`~dasmos.ext.environments.bbc_basic_6502.floats.BbcFloat5`
instance (or a bare callable plus a length) directly to
:meth:`~dasmos.disassembler.Disassembler.typed_data`.
"""

from typing import TYPE_CHECKING

from dasmos.environment import Environment
from dasmos.ext.environments.bbc_basic_6502.floats import BbcFloat5

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


class BbcBasic6502Environment(Environment):
    """Registers BBC BASIC (6502) language-specific data types.

    Currently just the packed 5-byte floating-point type
    (``bbc_float5``). Unlike the sideways-ROM environment this one does
    not inspect loaded memory, so it can be activated at any point.
    """

    def __init__(self, name: str = "bbc_basic_6502", **kwargs):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        disassembler.register_data_type("bbc_float5", BbcFloat5())
