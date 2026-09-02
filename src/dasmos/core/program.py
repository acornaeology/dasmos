"""Program-level metadata for a disassembled load-and-run file.

Some target programs are not position-fixed ROMs but *load-and-run*
files: a DFS ``*RUN`` program loads at one address and begins execution
at another (its **exec** address), and the filesystem records a
**reload** address distinct from where the bytes sit in the image.
These addresses are properties of the *program*, not of any particular
assembler syntax, so they live in the model and every renderer reads
what it can express (beebasm's ``save … , exec, reload``; a structural
field in JSON; a graceful no-op where the backend has no equivalent).

The load range itself is already known from the loaded image; a driver
only needs to declare the addresses the image can't imply.
"""

from __future__ import annotations

from dataclasses import dataclass

from dasmos.exceptions import DasmosError


class ProgramError(DasmosError):
    """Raised on invalid program-metadata declaration."""


def _validate_addr(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProgramError(
            f"{name} must be a non-negative integer address; got {value!r}"
        )
    return value


@dataclass(frozen=True)
class ProgramInfo:
    """Declared metadata for a load-and-run program.

    Every field is optional; ``None`` means 'not declared' (the
    renderer falls back to a sensible default or omits the datum). A
    plain-ROM disassembly never constructs one of these.

    - ``load_addr`` — where the program loads. Usually implied by the
      loaded image's range; declared only when a driver wants it
      recorded explicitly.
    - ``exec_addr`` — where execution begins (the DFS exec address),
      distinct from the load address for a driver whose entry point
      is not its first byte.
    - ``reload_addr`` — the address the filesystem reloads the file
      to. Defaults to the load-range start when a renderer needs it
      and it was not declared.
    """

    load_addr: int | None = None
    exec_addr: int | None = None
    reload_addr: int | None = None

    def __post_init__(self) -> None:
        _validate_addr("load_addr", self.load_addr)
        _validate_addr("exec_addr", self.exec_addr)
        _validate_addr("reload_addr", self.reload_addr)
