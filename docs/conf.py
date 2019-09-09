extensions = ["sphinx.ext.autodoc", "sphinx_rtd_theme", "delfick_project.norms.sphinx.show_specs"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_css_files = ["css/extra.css"]

exclude_patterns = ["_build/**", ".sphinx-build/**", "README.rst"]

master_doc = "index"
source_suffix = ".rst"

pygments_style = "pastie"

copyright = "2019, delfick"
project = "delfick_project"

version = "0.1"
release = "0.1"
