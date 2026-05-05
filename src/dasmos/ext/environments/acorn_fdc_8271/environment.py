"""Intel 8271 floppy-disc-controller register Environment.

The 8271 was Acorn's original FDC choice — fitted to early Model B
machines and used by the original DFS (Acorn 0.90 / 1.20). It can
also appear on later Model Bs that haven't been retrofitted with a
1770 board, and on systems running 8271-targeted DFSes.

Pair with whichever machine env applies (typically
``acorn_model_b_hardware``) — the FDC choice is independent of the
machine model, so this env is its own composable axis. For the
1770 (B+, Master, retrofitted Model B), use
``acorn_fdc_1770`` instead. The two are mutually exclusive: a
given system has one FDC chip, not both, and they share the
&FE80 / &FE84 addresses.

All registered as :meth:`Disassembler.optional_label` — they emit
in the equate table only when actually referenced by the
disassembled code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dasmos.environment import Environment

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# 8271 FDC: command/status (write/read), parameter/result port,
# reset register, data port. Addresses are the Acorn-standard
# &FE80-&FE84 mapping.
_FDC_8271_LABELS: list[tuple[int, str]] = [
    (0xfe80, "fdc_8271_command_or_status"),
    (0xfe81, "fdc_8271_parameter_or_result"),
    (0xfe82, "fdc_8271_reset"),
    (0xfe84, "fdc_8271_data"),
]


class AcornFdc8271Environment(Environment):
    """Acorn 8271 floppy-disc-controller Environment.

    Activate via ``Disassembler.use_environment("acorn_fdc_8271")``
    or ``environments=["acorn_fdc_8271"]`` for any DFS / disc-handling
    ROM that targets the 8271 (e.g. Acorn DFS 1.20).
    """

    def __init__(
        self,
        name: str = "acorn_fdc_8271",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, label_name in _FDC_8271_LABELS:
            disassembler.optional_label(addr, label_name)
