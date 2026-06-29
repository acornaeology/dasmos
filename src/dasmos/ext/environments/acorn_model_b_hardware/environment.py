"""BBC Model B / B+ hardware-register Environment for dasmos.

The Model B family register set: the shared BBC-line memory-mapped
I/O block (see :mod:`dasmos.ext.environments._acorn_bbc_common`) —
CRTC, ACIA, video ULA, base ROMSEL, system VIA, user VIA, Econet
ADLC, Tube, CUBE Tube, Fred-bus SCSI — plus the Model-B/B+
placements that differ on the Master: the station-ID / NMI-control
latch at &FE18 and the μPD7002 ADC at &FEC0 (on the Master those
move — see ``acorn_master_hardware`` / #31). ACCCON (&FE34) is also
registered: the B+ has it (and the Master), though the plain
Model B does not — a plain-B ROM simply never references it, so the
optional label never emits.

The floppy-disc-controller registers are NOT included here. The
Model B can be fitted with either an Intel 8271 (Acorn's original
choice) or a WD1770 (B+, plus Acorn's Model B retrofit board and
various third-party upgrades), so the FDC is its own composable
axis. Activate :mod:`acorn_fdc_8271` or :mod:`acorn_fdc_1770`
alongside this env according to which chip the target system has.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the
disassembled code, so adding the environment doesn't pollute
output for ROMs that don't touch any hardware.

For the Master, use ``acorn_master_hardware`` instead — the Master
is a different machine class (ACCCON, extended ROMSEL semantics)
that shares this common register block but adds Master-only
registers on top.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment
from dasmos.ext.environments._acorn_bbc_common import (
    ACCCON_LABELS,
    MODEL_B_ONLY_LABELS,
    SHARED_LABELS,
)

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


_ALL_LABELS: list[tuple[int, str]] = (
    SHARED_LABELS + MODEL_B_ONLY_LABELS + ACCCON_LABELS
)


class AcornModelBHardwareEnvironment(Environment):
    """Acorn BBC Model B / B+ hardware-register Environment.

    Layered on top of (or instead of) :class:`AcornMosEnvironment`:
    the MOS env covers the OS / vector / workspace addresses, this
    one covers the memory-mapped hardware registers in &FE00-&FEFF
    (and the Fred-bus block in &FC40-&FC43). Pair with one of the
    floppy-controller envs (:mod:`acorn_fdc_8271` /
    :mod:`acorn_fdc_1770`) if the disassembled ROM touches the FDC.

    Activate via
    ``Disassembler.use_environment("acorn_model_b_hardware")`` or
    ``environments=["acorn_model_b_hardware"]``.
    """

    def __init__(
        self,
        name: str = "acorn_model_b_hardware",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, label_name in _ALL_LABELS:
            disassembler.optional_label(addr, label_name)
