# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import re
import sys
from typing import Union

# -- Path setup --------------------------------------------------------------
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath("../proboards_scraper"))


# -- Project information -----------------------------------------------------

project = 'ProBoards Forum Scraper'
copyright = '2021, Najam R. Syed'
author = 'Najam R. Syed'
version = '1.0'

# The full version, including alpha/beta/rc tags
release = '1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]

# sphinx_autodoc_typehints options
typehints_fully_qualified = True
#autodoc_typehints = "signature"
autodoc_inherit_docstrings = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# Document class __init__ method
autoclass_content = 'both'


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

#html_css_files = [
#    'css/func_signature.css',
#]

def process_type(x: Union[dict, str]):
    ret = x
    if isinstance(x, str):
        type_expr = r"(.+?)\[(.+)]$"
        match = re.match(type_expr, x)

        if match:
            supertype_str, subtypes_str = match.groups()

            supertype = supertype_str.split("`")[1]
            supertype = process_type(supertype)

            subtypes = subtypes_str.split(",")
            subtypes = [process_type(subtype) for subtype in subtypes]
            joined_subtypes = ", ".join(subtypes)
            ret = f"{supertype}[{joined_subtypes}]"
        else:
            if "`" in x:
                ret = x.split("`")[1]

            module_map = {
                "selenium.webdriver.chrome.webdriver.WebDriver":
                    "selenium.webdriver.Chrome",
                "proboards_scraper.database.database.Database":
                    "proboards_scraper.database.Database",
                "proboards_scraper.database.schema":
                    "proboards_scraper.database",
                "proboards_scraper.scraper_manager.ScraperManager":
                    "proboards_scraper.ScraperManager",
                "typing.": "",
                "aiohttp.client": "aiohttp",
                "asyncio.queues": "asyncio",
            }

            for orig, target in module_map.items():
                ret = ret.replace(orig, target)
    return ret


def proc_docstring(app, what, name, obj, options, lines):
    for i, line in enumerate(lines):
        expr = r"(:.+:) (.*)"
        match = re.match(expr, line)

        if match and match.groups()[0].startswith((":type ", ":rtype:")):
            type_str = match.groups()[1]
            formatted_type = process_type(type_str)
            updated_line = f"{match.groups()[0]} :py:data:`{formatted_type}`"
            lines[i] = updated_line

def setup(app):
    app.connect("autodoc-process-docstring", proc_docstring)
