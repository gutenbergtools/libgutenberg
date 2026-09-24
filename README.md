# libgutenberg
Common files used by Project Gutenberg python projects.

# Installation

Install with the package manager of your choice -- `pipenv` or `pip`.

```bash
pipenv install libgutenberg
pipenv install 'libgutenberg[covers]'    # for cover generation
pipenv install 'libgutenberg[postgres]'  # for use with postgres
```

Depending on your system configuration, you might need to install `psycopg2-binary'.

Cover generation with `cairocffi` may require some system packages, see:
https://doc.courtbouillon.org/cairocffi/stable/overview.html#installing-cffi

`cffi` depends on `pycparser` which should be installed as a dependency, but if
it isn't for some reason: `pip install pycparser` will fix it.

# Development

`pipenv` will install the package as an editable package and is the easiest
way to get it set up:

```bash
pipenv install --python $(which python3)
pipenv shell
```

To run tests, you will need a Postgres running with a copy of the `gutenberg`
database. Configure an `.env` file with database connection parameters, for
example:

```bash
PGHOST='127.0.0.1'
PGDATABASE='gutenberg'
PGUSER='postgres'
PGPORT='5432'
```

Then, to run tests:
```bash
pipenv shell
python -m unittest discover
```
