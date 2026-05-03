"""Acorn MOS environment — workspace + vectors + OS-call labels.

Mirrors the label-defining content of py8dis's ``mos_labels()`` from
``py8dis/acorn.py``: the conventional names for the BBC MOS's zero-
page workspace addresses, its vector table at &200, and the OS-call
entry points at &FFB9-&FFF7.

The hook side of py8dis's acorn module (the OSBYTE / OSWORD / OSFILE
hooks that emit per-call commentary) is **deliberately not** ported
here — those hooks are large and orthogonal. They'll land alongside
the markdown comment port (task #26) since the commentary they emit
is the natural consumer of richer comment rendering.

This environment is parameterless. Drivers activate it via either::

    d = Disassembler.create(cpu="nmos6502", environments=["acorn_mos"])

or, equivalently::

    d.use_environment("acorn_mos")

Layering: combining ``acorn-mos`` with future
``acorn-bbc-hardware`` / ``acorn-sideways-rom`` environments adds
non-overlapping label sets. Where overlaps would arise (e.g. two
environments both naming the OS-call addresses), the LabelManager
deduplicates — same name at the same address is a no-op.
"""

from typing import TYPE_CHECKING

from dasmos.environment import Environment

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


# Zero-page MOS workspace addresses commonly inspected from sideways
# ROMs and second-processor code. The names match py8dis (and the
# Acorn MOS source itself).
_WORKSPACE_LABELS = {
    0x00f2: "os_text_ptr",
    0x00f4: "romsel_copy",
    0x00f6: "osrdsc_ptr",
}


# MOS vectors at &200-&235. Each is a 16-bit word; conventionally the
# low byte gets the bare name and the high byte gets ``+1``. The +1
# convention works in dasmos via the offset-base-label feature for
# in-range labels, but for out-of-range vector addresses we just
# register both names directly — beebasm renders them as separate
# equates and operands resolve cleanly either way.
_MOS_VECTORS = [
    (0x0200, "userv"),
    (0x0202, "brkv"),
    (0x0204, "irq1v"),
    (0x0206, "irq2v"),
    (0x0208, "cliv"),
    (0x020a, "bytev"),
    (0x020c, "wordv"),
    (0x020e, "wrchv"),
    (0x0210, "rdchv"),
    (0x0212, "filev"),
    (0x0214, "argsv"),
    (0x0216, "bgetv"),
    (0x0218, "bputv"),
    (0x021a, "gbpbv"),
    (0x021c, "findv"),
    (0x021e, "fscv"),
    (0x0220, "evntv"),
    (0x0222, "uptv"),
    (0x0224, "netv"),
    (0x0226, "vduv"),
    (0x0228, "keyv"),
    (0x022a, "insv"),
    (0x022c, "remv"),
    (0x022e, "cnpv"),
    (0x0230, "ind1v"),
    (0x0232, "ind2v"),
    (0x0234, "ind3v"),
]


# OS-call entry points at &FFB9-&FFF7. py8dis registers each as an
# ``optional_label`` (the OS calls are out of range — they live in
# MOS ROM, not in the disassembled image — so the label only emits
# in the equate table when actually JSR'd to). The hooks py8dis
# attaches (osbyte_hook, oswrch_hook, …) are not ported in this
# minimal environment; see module docstring.
_OS_CALLS = {
    0xffb9: "osrdsc",
    0xffbc: "vduchr",
    0xffbf: "oseven",
    0xffc2: "gsinit",
    0xffc5: "gsread",
    0xffc8: "nvrdch",
    0xffcb: "nvwrch",
    0xffce: "osfind",
    0xffd1: "osgbpb",
    0xffd4: "osbput",
    0xffd7: "osbget",
    0xffda: "osargs",
    0xffdd: "osfile",
    0xffe0: "osrdch",
    0xffe3: "osasci",
    0xffe7: "osnewl",
    0xffec: "oswrcr",
    0xffee: "oswrch",
    0xfff1: "osword",
    0xfff4: "osbyte",
    0xfff7: "oscli",
}


class AcornMosEnvironment(Environment):
    """Acorn MOS environment.

    Registers the conventional names for the BBC MOS's zero-page
    workspace, the vector table at &200, and the OS-call entry
    points at &FFB9-&FFF7. Activated via
    ``Disassembler.use_environment("acorn_mos")`` or the
    ``environments=["acorn_mos"]`` constructor kwarg.

    All labels are registered with ``optional_label`` semantics —
    they appear in the rendered output only when actually
    referenced, so adding the environment to a driver doesn't
    pollute the output for ROMs that don't call any of these.
    """

    def __init__(self, name: str = "acorn_mos", **kwargs):
        super().__init__(name=name, **kwargs)

    def setup(self, disassembler: "Disassembler") -> None:
        for addr, name in _WORKSPACE_LABELS.items():
            disassembler.optional_label(addr, name)
        for addr, name in _MOS_VECTORS:
            disassembler.optional_label(addr, name)
            disassembler.optional_label(addr + 1, f"{name}_hi")
        for addr, name in _OS_CALLS.items():
            disassembler.optional_label(addr, name)
