# Sphinx configuration for the PyCdlib API reference.
#
# Build with "make docs" from the top of the repository, which runs:
#
#     sphinx-build -b html docs/_sphinx docs/api
#
# The generated HTML under docs/api is committed and served by GitHub
# Pages along with the rest of docs/.  This directory starts with an
# underscore so Jekyll does not publish the Sphinx sources themselves.
#
# Requires the sphinx and furo packages (on Fedora: python3-sphinx and
# python3-furo).

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

project = 'PyCdlib'
author = 'Chris Lalancette'
copyright = '2015-2026, Chris Lalancette'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']

html_theme = 'furo'
html_title = 'PyCdlib API reference'
html_static_path = ['_static']
html_css_files = ['pycdlib.css']
html_copy_source = False
html_show_sphinx = False
html_theme_options = {'top_of_page_buttons': []}

# Document members in source order, and only those with docstrings.
autodoc_member_order = 'bysource'
autodoc_default_options = {'members': True, 'undoc-members': False}
autodoc_typehints = 'signature'

# Show "class PyCdlib", not "class pycdlib.pycdlib.PyCdlib".
add_module_names = False
python_display_short_literal_types = True

# Long signatures get one parameter per line.
maximum_signature_line_length = 60

# List methods in the per-page table of contents, without the class prefix.
toc_object_entries = True
toc_object_entries_show_parents = 'hide'

napoleon_use_param = True
napoleon_use_rtype = False


def skip_instance_variables(app, what, name, obj, skip, options):
    """
    Hide plain data attributes on classes.  These are the __slots__
    entries, which autodoc represents with an opaque sentinel object;
    they are internal state, not part of the public API.
    """
    if what == 'class' and not callable(obj) and not isinstance(obj, property):
        return True
    return None


def setup(app):
    app.connect('autodoc-skip-member', skip_instance_variables)
