"""Exception hierarchy for the dasmos package."""


class DasmosError(Exception):
    """Base class for all exceptions raised by the dasmos package."""
    pass


class MacroRenderError(DasmosError):
    """Raised when a macro cannot be rendered for the target assembler —
    e.g. a value-returning macro used as an operand on a backend that has
    no value functions (beebasm, acme)."""
    pass
