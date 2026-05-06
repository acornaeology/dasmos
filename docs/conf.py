"""Sphinx configuration for dasmos."""

from datetime import datetime
from importlib.metadata import version as get_version

# -- Project information -----------------------------------------------------

project = "dasmos"
author = "Robert Smallshire"
copyright = f"{datetime.now().year}, {author}"

# `release` is the full version string, `version` the short (major.minor).
release = get_version("dasmos")
version = ".".join(release.split(".")[:2])


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",       # Google / NumPy-style docstrings
    "sphinx.ext.viewcode",       # "[source]" links next to each documented object
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",         # copy-to-clipboard on code blocks
]

# Docstrings throughout the code use Google style.
napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "click": ("https://click.palletsprojects.com/en/stable/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "design"]


# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_logo = "_static/dasmos-logo.png"

html_theme_options = {
    "navigation_depth": 3,
    "collapse_navigation": False,
    # The logo's "Dasmos" identity comes from the column itself —
    # don't repeat the project name as text below it in the sidebar.
    "logo_only": True,
}
