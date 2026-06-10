# libgutenberg
Common files used by Project Gutenberg python projects.

# installation

`pipenv install libgutenberg`
`pipenv install 'libgutenberg[covers]'` for cover generation
`pipenv install 'libgutenberg[postgres]'` for use with postgres

or 

`pip install libgutenberg`
`pip install 'libgutenberg[covers]'` for cover generation
`pip install 'libgutenberg[postgres]'` for use with postgres

Depending on your system configuration, you might need to use pip or pipenv to install
`pipenv install psycopg2-binary'

To run static checks, enter the following commands within the venv:
`ruff check .`
`mypy .`