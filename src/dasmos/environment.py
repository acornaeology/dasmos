"""Environment extension point.

An *environment* supplies pre-existing knowledge about the platform a
ROM runs on — typically OS-call labels, hardware-register addresses,
vector positions, and (eventually) the comment-emitting hooks that
explain OS-call argument conventions. Environments factor knowledge
that's stable across many ROMs (e.g. "the BBC Micro's MOS provides
OSWRCH at &FFEE") out of every individual driver script.

Environments are **composable**: a Disassembler can have any number
of environments active at once, applied in order. Each
:meth:`Environment.setup` runs against the disassembler at the time
of activation; later environments see the cumulative state of all
earlier ones. Effects layer additively — registering the same label
twice is a harmless no-op (the LabelManager deduplicates), and
registering different names at the same address yields aliases.

This factoring lets per-platform knowledge be split into orthogonal
slices that drivers mix as needed:

- ``acorn-mos``           — MOS workspace + vectors + OS-call labels
- ``acorn-bbc-hardware``  — BBC Micro hardware addresses (Tube ULA, …)
- ``acorn-sideways-rom``  — sideways-ROM header convention

A driver targeting an Acorn sideways ROM that runs on the host BBC
Micro selects the union::

    d = Disassembler.create(
        cpu="6502",
        environments=["acorn-mos", "acorn-bbc-hardware", "acorn-sideways-rom"],
    )

Each environment is a Stevedore plug-in registered under the
``dasmos.environment`` entry-point namespace; third-party packages
register additional environments the same way the bundled ones do.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Type

from dasmos.extension import (
    Extension,
    ExtensionError,
    create_extension,
    describe_extension,
    extension,
    list_extensions,
)

if TYPE_CHECKING:
    from dasmos.disassembler import Disassembler


KIND = "environment"
ENVIRONMENT_NAMESPACE = f"dasmos.{KIND}"


class Environment(Extension):
    """Base class for environment plug-ins.

    Override :meth:`setup` to register the labels, comments, hooks,
    classifications, etc. that constitute the environment.

    Environments are usually parameterless — they act on a
    Disassembler by side effect rather than carrying their own state.
    Override the constructor only if your environment needs
    configuration that varies per use site.
    """

    @classmethod
    def _kind(cls) -> str:
        return KIND

    @abstractmethod
    def setup(self, disassembler: "Disassembler") -> None:
        """Apply this environment's effects to ``disassembler``.

        Called by :meth:`Disassembler.use_environment` (or by the
        Disassembler constructor when ``environments=`` is passed).
        Implementations register labels, classifications, comments,
        hooks, etc. via the public driver-script API on
        ``disassembler``.

        Idempotent in spirit: if the same environment is activated
        twice on the same disassembler, the second call should be a
        no-op (the underlying managers handle duplicate registrations
        cleanly — registering the same label twice is harmless).
        """
        raise NotImplementedError


class EnvironmentExtensionError(ExtensionError):
    pass


def create_environment(name: str, **kwargs) -> Environment:
    """Create an Environment instance by name.

    Args:
        name: The name of the environment to create (e.g. ``"acorn-mos"``).
        **kwargs: Forwarded to the Environment subclass constructor.

    Returns:
        An :class:`Environment` instance.

    Raises:
        EnvironmentExtensionError: If the environment cannot be loaded.
    """
    return create_extension(
        kind=KIND,
        namespace=ENVIRONMENT_NAMESPACE,
        name=name,
        exception_type=EnvironmentExtensionError,
        **kwargs,
    )


def describe_environment(name: str, *, single_line: bool = False) -> str:
    """Get the description of an environment plug-in."""
    return describe_extension(
        kind=KIND,
        namespace=ENVIRONMENT_NAMESPACE,
        name=name,
        exception_type=EnvironmentExtensionError,
        single_line=single_line,
    )


def environment_names() -> list[str]:
    """Get the names of all available environment plug-ins."""
    return list_extensions(ENVIRONMENT_NAMESPACE)


def environment_type(name: str) -> Type[Environment]:
    """Obtain the type of an environment plug-in by name."""
    return extension(
        kind=KIND,
        namespace=ENVIRONMENT_NAMESPACE,
        name=name,
        exception_type=EnvironmentExtensionError,
    )
