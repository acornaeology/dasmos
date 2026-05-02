"""Assembler-syntax (renderer) extension point.

Each assembler plug-in is a subclass of :class:`Assembler` registered
under the ``dasmos.assembler`` entry-point namespace. Concrete
assemblers render the disassembled trace into a particular textual
syntax — Beebasm, ca65, the JSON output ported from the py8dis fork,
and so on.
"""

from typing import Type

from dasmos.extension import (
    Extension,
    ExtensionError,
    create_extension,
    describe_extension,
    extension,
    list_extensions,
)

KIND = "assembler"
ASSEMBLER_NAMESPACE = f"dasmos.{KIND}"


class Assembler(Extension):
    """Base class for assembler-syntax (renderer) plug-ins.

    Concrete subclasses render disassembled output in a particular
    assembler-syntax dialect (Beebasm, ca65, machine-readable JSON, …).
    A given CPU may have several assemblers it can be rendered through
    — the user picks one at the CLI or via the API.
    """

    @classmethod
    def _kind(cls) -> str:
        return KIND


class AssemblerExtensionError(ExtensionError):
    """Exception raised when an assembler extension cannot be loaded."""
    pass


def create_assembler(assembler_name: str, **kwargs) -> Assembler:
    """Create an assembler instance by name.

    Args:
        assembler_name: The name of the assembler to create
            (e.g. ``"beebasm"``, ``"json"``).
        **kwargs: Forwarded to the assembler subclass constructor.

    Returns:
        An :class:`Assembler` instance.

    Raises:
        AssemblerExtensionError: If the assembler cannot be loaded.
    """
    return create_extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
        **kwargs,
    )


def describe_assembler(assembler_name: str, *, single_line: bool = False) -> str:
    """Get the description of an assembler plug-in.

    Args:
        assembler_name: The name of the assembler.
        single_line: If True, return only the first non-empty line of the description.

    Returns:
        Description string from the assembler class's docstring.

    Raises:
        AssemblerExtensionError: If the assembler cannot be loaded.
    """
    return describe_extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
        single_line=single_line,
    )


def assembler_names() -> list[str]:
    """Get the names of all available assembler plug-ins."""
    return list_extensions(ASSEMBLER_NAMESPACE)


def assembler_type(assembler_name: str) -> Type[Assembler]:
    """Obtain the type of an assembler plug-in by name.

    Args:
        assembler_name: The name of an assembler. Available names can be
            obtained from :py:func:`~assembler_names`.

    Returns:
        The class of the requested assembler.

    Raises:
        AssemblerExtensionError: If the requested assembler could not be found.
    """
    return extension(
        kind=KIND,
        namespace=ASSEMBLER_NAMESPACE,
        name=assembler_name,
        exception_type=AssemblerExtensionError,
    )
