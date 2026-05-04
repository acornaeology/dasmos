"""Generic extension / plug-in machinery built on top of stevedore.

Extension classes are loaded via entry points. Each :class:`Extension`
subclass declares a ``kind`` (a short identifier such as ``"cpu"`` or
``"assembler"``) and is registered under a namespace of the form
``"dasmos.<kind>"`` in ``pyproject.toml``. Consumers then use
:func:`create_extension`, :func:`extension`, or :func:`list_extensions`
to load them.

Lifted from ``asyoulikeit.extension`` with light modification: the
namespace prefix in :meth:`Extension.entry_point_name` is ``"dasmos"``
rather than ``"asyoulikeit"``, and the base error type is
:class:`DasmosError`.
"""

import functools
import importlib.resources
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

import stevedore
import stevedore.exception

from dasmos._text import first_line, normalize_name, strip_lines
from dasmos.exceptions import DasmosError


logger = logging.getLogger(__name__)


class Extension(ABC):
    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self._name = name

    @classmethod
    def kind(cls) -> str:
        """The kind of extension.

        Used to distinguish extension points.
        """
        return cls._kind()

    @classmethod
    @abstractmethod
    def _kind(cls) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def dirpath(cls) -> Path:
        """The directory path to the extension package."""
        package_name = inspect.getmodule(cls).__package__
        return Path(importlib.resources.files(package_name))

    @classmethod
    def version(cls) -> str:
        """The extension version."""
        return "1.0.0"

    @classmethod
    def full_description(cls) -> str:
        """The complete, multi-paragraph description.

        Default implementation returns the cleaned class docstring.
        Override only if the description should come from somewhere
        other than the docstring (rare).

        Used by ``describe-<kind>`` CLI commands.
        """
        if cls.__doc__ is None:
            return "No description available."
        return strip_lines(inspect.cleandoc(cls.__doc__))

    @classmethod
    def brief_description(cls) -> str:
        """Pithy single-line summary, suitable for a table cell.

        Default implementation returns the first non-empty line of
        :meth:`full_description`. Override on the subclass when the
        docstring's first line would be too long for a list-style
        rendering — set this to a separately-authored, deliberately
        terse summary.

        Used by ``list-<kind>`` CLI commands.
        """
        return first_line(cls.full_description())

    @classmethod
    def describe(cls, *, single_line: bool = False) -> str:
        """Convenience wrapper around :meth:`brief_description` /
        :meth:`full_description`.

        Args:
            single_line: If True, return :meth:`brief_description`.
                Otherwise return :meth:`full_description`.
        """
        return cls.brief_description() if single_line else cls.full_description()

    @classmethod
    @functools.lru_cache(maxsize=None)
    def entry_point_name(cls) -> str:
        """Get the entry point name (key) for this extension class.

        This performs a reverse lookup from class to entry point name by searching
        through all extensions in the appropriate namespace. The result is cached
        indefinitely since entry point names are immutable.

        Returns:
            The entry point name for this extension class.

        Raises:
            ExtensionError: If this class is not registered as an extension.
        """
        namespace = f"dasmos.{cls.kind()}"
        return extension_name_from_class(namespace, cls)


class ExtensionError(DasmosError):
    pass


def create_extension(kind, namespace, name, exception_type=None, **kwargs) -> Extension:
    """Instantiate an extension.

    Args:
        kind: The kind of extension.
        namespace: The namespace for the extension.
        name: The name of the extension to be loaded.
        exception_type: The exception type to be raised if the extension couldn't be loaded.
        **kwargs: Keyword arguments forwarded to the extension constructor.

    Returns:
        An extension.
    """
    exception_type = exception_type or ExtensionError
    canonical = _resolve_canonical_name(namespace, name, kind, exception_type)
    ext = extension(kind, namespace, canonical, exception_type)
    # Always pass the canonical name to the constructor so the
    # instance's ``name`` attribute matches what's shown by
    # ``list-cpus`` / ``list-renderers`` / etc., regardless of the
    # case the caller used.
    obj = ext(name=canonical, **kwargs)
    return obj


def extension(
        kind: str,
        namespace: str,
        name: str,
        exception_type: BaseException,
) -> Type[Extension]:
    """Get the extension class without instantiating it.

    Lookup is case-insensitive: ``--cpu 65c02`` resolves to the
    registered ``65C02`` plug-in. Hyphens in the requested name are
    also normalised to underscores. The exact registered name is
    what's used to instantiate the extension.

    Args:
        kind: The kind of extension.
        namespace: The namespace for the extension.
        name: The name of the extension to be loaded.
        exception_type: The exception type to be raised if the extension couldn't be loaded.

    Returns:
        The type (i.e. class) of an extension.
    """
    exception_type = exception_type or ExtensionError
    canonical_name = _resolve_canonical_name(namespace, name, kind, exception_type)
    try:
        manager = stevedore.driver.DriverManager(
            namespace=namespace,
            name=canonical_name,
            invoke_on_load=False,
            on_load_failure_callback=load_failure_callback,
        )
    except stevedore.exception.NoMatches as no_matches:
        names = list_extensions(namespace)
        name_list = ", ".join(names)
        raise exception_type(
            f"No {kind} matching {name !r}. Available {kind}s: {name_list}"
        ) from no_matches
    driver = manager.driver
    return driver


def _resolve_canonical_name(
        namespace: str,
        requested: str,
        kind: str,
        exception_type: BaseException,
) -> str:
    """Resolve ``requested`` to the canonical registered name in
    ``namespace``, matching case-insensitively after the standard
    ``normalize_name`` (hyphen → underscore) pass.

    If exactly one registered name matches, return it. If none
    match, return the normalised request unchanged so the caller's
    DriverManager call raises ``NoMatches`` with the usual error
    surface. If two or more registered names case-fold to the same
    string, refuse the lookup — that's an authoring mistake on the
    extension publisher's part rather than something to silently
    pick from.
    """
    requested_normal = normalize_name(requested)
    available = list_extensions(namespace)
    if requested_normal in available:
        return requested_normal
    requested_lower = requested_normal.lower()
    matches = [n for n in available if n.lower() == requested_lower]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        joined = ", ".join(repr(n) for n in matches)
        raise exception_type(
            f"Ambiguous {kind} name {requested !r}: case-insensitive "
            f"match resolves to multiple registered plug-ins ({joined}). "
            f"Use the exact name to disambiguate."
        )
    return requested_normal


def describe_extension(kind, namespace, name, exception_type=None, *, single_line: bool = False) -> str:
    """Describe an extension by name.

    Args:
        kind: The kind of extension.
        namespace: The namespace for the extension.
        name: The name of the extension.
        exception_type: The exception type to be raised if the extension couldn't be loaded.
        single_line: If True, return only the first non-empty line of the description.

    Returns:
        A string describing the extension.
    """
    driver = extension(kind, namespace, name, exception_type)
    description = driver.describe(single_line=single_line)
    return description


def list_extensions(namespace) -> list[str]:
    """List the names of the extensions available in a given namespace."""
    extensions = stevedore.ExtensionManager(
        namespace=namespace,
        invoke_on_load=False,
        on_load_failure_callback=load_failure_callback,
    )
    return extensions.names()


def load_failure_callback(manager, entrypoint, exception):
    raise ExtensionError(
        f"Could not load extension {entrypoint.name!r} from plug-in manager {manager.namespace!r} because: {exception}"
    ) from exception


def list_dirpaths(namespace):
    """A mapping of extension names to extension package paths."""
    extensions = stevedore.ExtensionManager(
        namespace=namespace,
        invoke_on_load=False,
        on_load_failure_callback=load_failure_callback,
    )
    return {name: _extension_dirpath(ext) for name, ext in extensions.items()}


def _extension_dirpath(ext: stevedore.extension.Extension) -> Path:
    """Get the directory path to an extension package.

    Args:
        ext: A stevedore.extension.Extension instance.

    Returns:
        An absolute Path to the package containing the extension.
    """
    return Path(importlib.resources.files(ext.module_name))


def extension_name_from_class(namespace: str, extension_class: Type[Extension]) -> str:
    """Get the entry point name for an extension class.

    This performs a reverse lookup from class to entry point name by iterating through
    all extensions in the namespace until finding one whose plugin matches the given class.

    Args:
        namespace: The namespace to search (e.g., 'dasmos.cpu')
        extension_class: The extension class to find

    Returns:
        The entry point name (key) for the extension

    Raises:
        ExtensionError: If the extension class is not found in the namespace
    """
    manager = stevedore.ExtensionManager(
        namespace=namespace,
        invoke_on_load=False,
        on_load_failure_callback=load_failure_callback,
    )

    for ext in manager:
        if ext.plugin == extension_class:
            return ext.name

    raise ExtensionError(
        f"Extension class {extension_class.__name__} not found in namespace {namespace!r}"
    )
