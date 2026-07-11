"""Exception hierarchy for the dasmos package."""


class DasmosError(Exception):
    """Base class for all exceptions raised by the dasmos package."""
    pass


class MacroRenderError(DasmosError):
    """Raised when a macro invocation is malformed — the named macro is
    not defined, or the argument count does not match the definition's
    parameters. (A macro a backend can't render *natively* is not an
    error: dasmos falls back to inline-expanding it.)"""
    pass
