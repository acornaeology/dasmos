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
    def describe(cls, *, single_line: bool = False) -> str:
        """A description of the extension.

        By default, this is the docstring of the extension class. Override it in the extension if
        you want something different.

        Args:
            single_line: If True, return only the first non-empty line of the description.
                Defaults to False for full description.

        Returns:
            A string describing the extension. If single_line is True, returns only the first
            non-empty line; otherwise returns the complete description.
        """
        if cls.__doc__ is None:
            return "No description available."
        full_description = strip_lines(inspect.cleandoc(cls.__doc__))
        if single_line:
            return first_line(full_description)
        return full_description

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
    ext = extension(kind, namespace, name, exception_type)
    obj = ext(name=normalize_name(name), **kwargs)
    return obj


def extension(
        kind: str,
        namespace: str,
        name: str,
        exception_type: BaseException,
) -> Type[Extension]:
    """Get the extension class without instantiating it.

    Args:
        kind: The kind of extension.
        namespace: The namespace for the extension.
        name: The name of the extension to be loaded.
        exception_type: The exception type to be raised if the extension couldn't be loaded.

    Returns:
        The type (i.e. class) of an extension.
    """
    exception_type = exception_type or ExtensionError
    normal_name = normalize_name(name)
    try:
        manager = stevedore.driver.DriverManager(
            namespace=namespace,
            name=normal_name,
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
