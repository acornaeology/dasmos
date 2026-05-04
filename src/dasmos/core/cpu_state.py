"""CPU register-state tracking for post-trace analysis.

A strongly-typed :class:`CpuState` per CPU plug-in, computed once by
the trace pipeline and read directly by hooks. The state is built by
an "optimistic" linear sweep — straight-line execution that ignores
branches.

Design points:

- **Explicit dataclass model** rather than an ad-hoc dict-of-dicts
  indexed by register name. Makes the state inspectable,
  type-checkable, and test-isolatable.
- **Per-CPU pluggable types**: each CPU plug-in owns its own
  :class:`CpuState` subclass and its own update rules; the
  Disassembler doesn't hard-code 6502 state shape.
- **State BEFORE the instruction is the snapshot** kept, which
  matches what hooks need: a JSR analyzer asks "what was A *just
  before* this JSR fired?".
- **Source-address tracking** on each register: a
  :class:`RegisterValue` carries both the value AND the binary
  address of the instruction that last set it (the LDA #imm),
  letting analyzers register an auto-expression at exactly the
  right operand byte without re-scanning.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CpuState(ABC):
    """Marker base class for CPU-specific register/flag state.

    Each CPU plug-in defines a concrete subclass (see
    :class:`dasmos.ext.cpus.cpu6502.cpu.State6502`). The
    :meth:`Cpu.initial_state` factory returns a fresh instance and
    :meth:`Cpu.update_state` mutates one in place to reflect
    executing a given instruction.
    """

    @abstractmethod
    def clone(self) -> "CpuState":
        """Return an independent copy. Used to snapshot per-instruction
        state without later updates leaking back into the snapshot.
        """
