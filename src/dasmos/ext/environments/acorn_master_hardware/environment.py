"""BBC Master hardware-register Environment for dasmos.

The BBC Master register set: shared BBC-line registers (see
:mod:`dasmos.ext.environments._acorn_bbc_common`) plus the
Master-specific additions:

- **ACCCON** at &FE34 — the access-control register (shadow RAM,
  internal/external ROM banking, IRQ steering). Shared with the
  B+; supplied here via the common ``ACCCON_LABELS`` block.
- **ADC** (μPD7002) at &FE18-&FE1A — on the Master the ADC lives
  here, NOT at the Model-B &FEC0 (which is the network interface
  on the Master). See #31.
- **Econet NMI control** at &FE38 (INTOFF, disable network NMIs)
  and &FE3C (INTON, enable network NMIs) — the Master's dedicated
  latches, replacing the Model-B trick of reading the station-ID
  register at &FE18 for the NMI-disable side effect.

The Master's 146818 Real-Time Clock / CMOS RAM is NOT directly
memory-mapped — it's accessed bit-banged through the System VIA
(port B for address/data, plus the CMOS_AS / CMOS_DS chip-enable
strobes off System VIA port B's upper bits via the IC32 latch).
There are no &FE3x byte-level mirror addresses to label, so the
RTC has no entries here; ROMs that talk to the clock will read
as accesses to the System VIA registers (already labelled by the
shared block).

The Master uses a 65C02 CPU and ships with the WD1770 floppy
controller as fixed, onboard hardware: drive control at &FE24 and
the four 1770 chip registers at &FE28-&FE2B. Unlike the Model B
(where the 8271-vs-1770 choice is a real hardware variable and so
lives in a composable :mod:`acorn_fdc_8271` / :mod:`acorn_fdc_1770`
env), the Master always has this one 1770 at these addresses — so
the registers are included directly here. They are still
``optional_label``, so ROMs that never touch the FDC (e.g. ANFS)
don't get them in their equate table. Note this is NOT the &FE80
window the B+ / Model-B-retrofit :mod:`acorn_fdc_1770` env uses.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the
disassembled code, so adding the environment doesn't pollute
output for ROMs that don't touch any hardware.

For the Model B / B+, use ``acorn_model_b_hardware`` instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment
from dasmos.ext.environments._acorn_bbc_common import (
    ACCCON_LABELS,
    SHARED_LABELS,
    adc_labels,
)

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# Master-specific additions on top of the shared register block.
# The 146818 RTC is NOT here: it's not memory-mapped; ROM code
# drives it through the System VIA (already labelled in the
# shared block). ACCCON comes from the shared ACCCON_LABELS block
# (B+/Master). See #31 for the ADC / NMI-control placement.
_MASTER_SPECIFIC: list[tuple[int, str]] = [
    # μPD7002 ADC at the Master location (&FE18-&FE1A), where the
    # Model B / B+ have the station-ID / NMI-control latch instead.
    *adc_labels(0xfe18),
    # Econet NMI control: dedicated INTOFF / INTON latches. The
    # Model B disables NMIs as a side effect of reading the
    # station-ID register; the Master has these instead.
    (0xfe38, "disable_net_nmis"),
    (0xfe3c, "enable_net_nmis"),
    # Onboard WD1770 floppy controller (fixed Master hardware): the
    # drive-control latch at &FE24 plus the four 1770 chip registers
    # at &FE28-&FE2B. NOT the &FE80 window the B+ / retrofit 1770
    # uses (see acorn_fdc_1770).
    (0xfe24, "fdc_1770_drive_control"),
    (0xfe28, "fdc_1770_command_or_status"),
    (0xfe29, "fdc_1770_track"),
    (0xfe2a, "fdc_1770_sector"),
    (0xfe2b, "fdc_1770_data"),
]


_ALL_LABELS: list[tuple[int, str]] = (
    SHARED_LABELS + ACCCON_LABELS + _MASTER_SPECIFIC
)


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
