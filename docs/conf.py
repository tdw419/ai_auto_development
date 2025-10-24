from __future__ import annotations

project = "VISTA Time Utilities"
author = "VISTA AI Systems"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

html_theme = "furo"

autodoc_typehints = "description"
templates_path = ["_templates"]
exclude_patterns = ["_build"]
