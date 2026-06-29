"""WD1770 floppy-disc-controller register Environment (&FE80 window).

This env covers the 1770 at the &FE80 / &FE84-&FE87 window — the
mapping used by the BBC B+ and by Model B machines retrofitted with
a 1770 board (Acorn's own upgrade plus various third-party boards),
which place the 1770 in the old 8271 SHEILA window for DFS
compatibility. Used by Acorn DFS 2.x and later, ADFS, and most
third-party DFSes targeting that mapping.

NOTE: the BBC **Master**'s onboard 1770 is NOT here — it lives at
&FE24 / &FE28-&FE2B and, being fixed Master hardware, is included
directly in :mod:`acorn_master_hardware` rather than as a separate
composable env (see #31).

Pair with ``acorn_model_b_hardware`` for B+ / retrofitted-Model-B
images. The FDC choice is independent of the machine model, so this
env is its own composable axis. For the original 8271, use
``acorn_fdc_8271`` instead. The chips are mutually exclusive: a
given system has one FDC, and the 8271 and the B+/retrofit 1770
share the &FE80 / &FE84 addresses.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the
disassembled code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# 1770 FDC: drive-control latch (Acorn-specific glue at &FE80,
# selecting drive number, density, side, master reset, etc.) plus
# the four memory-mapped 1770 chip registers (command/status,
# track, sector, data) at &FE84-&FE87.
_FDC_1770_LABELS: list[tuple[int, str]] = [
    (0xfe80, "fdc_1770_drive_control"),
    (0xfe84, "fdc_1770_command_or_status"),
    (0xfe85, "fdc_1770_track"),
    (0xfe86, "fdc_1770_sector"),
    (0xfe87, "fdc_1770_data"),
]


class AcornFdc1770Environment(Environment):
    """Acorn WD1770 floppy-disc-controller Environment.

    Activate via ``Disassembler.use_environment("acorn_fdc_1770")``
    or ``environments=["acorn_fdc_1770"]`` for any DFS / ADFS / disc-
    handling ROM that targets the 1770 (Acorn DFS 2.x, ADFS-1.30,
    DDFS, etc.).
    """

    def __init__(
        self,
        name: str = "acorn_fdc_1770",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, label_name in _FDC_1770_LABELS:
            disassembler.optional_label(addr, label_name)
