"""CPU register-state tracking for post-trace analysis.

Where py8dis-fork carries an "optimistic" linear-sweep CPU state
(``cpu.cpu_state_optimistic[binary_addr]`` — straight-line state
ignoring branches), dasmos exposes a strongly-typed
:class:`CpuState` per-CPU that the trace pipeline computes ONCE and
hooks read directly.

What "exceeds py8dis" here:

- **Explicit dataclass model** instead of py8dis's ad-hoc dict-of-
  dicts indexed by ``"a"`` / ``"x"`` / etc. Makes the state
  inspectable, type-checkable, and test-isolatable.
- **Per-CPU pluggable types**: each CPU plug-in owns its own
  :class:`CpuState` subclass and its own update rules; the
  Disassembler doesn't hard-code 6502 state shape.
- **State BEFORE the instruction is the snapshot** kept (py8dis
  stores AFTER), which matches what hooks need: a JSR analyzer
  asks "what was A *just before* this JSR fired?".
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
