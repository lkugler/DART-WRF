import os
import sys

# Configuration file for the Sphinx documentation builder.

# -- Project information

project = 'DART-WRF'
copyright = '2023, Lukas Kugler'
author = 'Lukas Kugler'
release = '2023.2.21'

# -- General configuration
sys.path.insert(0, os.path.abspath('../../'))

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'nbsphinx'
]

autodoc_mock_imports = ['numpy','scipy','xarray','pandas','netCDF4','osselyze']

napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

html_theme = 'sphinx_rtd_theme'

# -- Options for EPUB output
epub_show_urls = 'footnote'
