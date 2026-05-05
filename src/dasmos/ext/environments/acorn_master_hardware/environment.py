"""BBC Master hardware-register Environment for dasmos.

The BBC Master register set: shared BBC-line registers (see
:mod:`dasmos.ext.environments._acorn_bbc_common`) plus the
Master-specific additions:

- **ACCCON** at &FE34 — the access-control register (shadow RAM,
  internal/external ROM banking, IRQ steering).

The Master's 146818 Real-Time Clock / CMOS RAM is NOT directly
memory-mapped — it's accessed bit-banged through the System VIA
(port B for address/data, plus the CMOS_AS / CMOS_DS chip-enable
strobes off System VIA port B's upper bits via the IC32 latch).
There are no &FE3x byte-level mirror addresses to label, so the
RTC has no entries here; ROMs that talk to the clock will read
as accesses to the System VIA registers (already labelled by the
shared block).

The Master uses a 65C02 CPU and ships with the WD1770 floppy
controller. Floppy-controller registers live in their own
composable env — pair :mod:`acorn_fdc_1770` with this env for
ROMs that touch the FDC (ADFS, DDFS, etc.). The 8271 was never
fitted to the Master, so :mod:`acorn_fdc_8271` is not relevant.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the
disassembled code, so adding the environment doesn't pollute
output for ROMs that don't touch any hardware.

For the Model B / B+, use ``acorn_model_b_hardware`` instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment
from dasmos.ext.environments._acorn_bbc_common import SHARED_LABELS

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# Master-specific additions on top of the shared register block.
# The 146818 RTC is NOT here: it's not memory-mapped; ROM code
# drives it through the System VIA (already labelled in the
# shared block).
_MASTER_SPECIFIC: list[tuple[int, str]] = [
    # Access-control register: shadow-RAM enable, internal/external
    # ROM steering, IRQ source enables.
    (0xfe34, "acccon"),
]


_ALL_LABELS: list[tuple[int, str]] = SHARED_LABELS + _MASTER_SPECIFIC


class AcornMasterHardwareEnvironment(Environment):
    """Acorn BBC Master hardware-register Environment.

    Layered on top of (or instead of) :class:`AcornMosEnvironment`:
    the MOS env covers the OS / vector / workspace addresses, this
    one covers the memory-mapped hardware registers in &FE00-&FEFF
    (and the Fred-bus block in &FC40-&FC43).

    The Master is a different machine class from the Model B / B+
    — it shares the bulk of the BBC-line register layout but adds
    ACCCON, RTC, and other Master-only hardware. Use this env for
    Master-targeted ROMs (e.g. ANFS 4.21); use
    ``acorn_model_b_hardware`` for Model B / B+ ROMs.

    Activate via
    ``Disassembler.use_environment("acorn_master_hardware")`` or
    ``environments=["acorn_master_hardware"]``.
    """

    def __init__(
        self,
        name: str = "acorn_master_hardware",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, label_name in _ALL_LABELS:
            disassembler.optional_label(addr, label_name)
