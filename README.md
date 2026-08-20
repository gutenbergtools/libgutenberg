# libgutenberg
Common files used by Project Gutenberg python projects.

# Installation

Install with the package manager of your choice -- `pipenv` or `pip`.

```bash
pip install libgutenberg
pip install 'libgutenberg[covers]'    # for cover generation
pip install 'libgutenberg[postgres]'  # for use with postgres
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

To run tests:
```bash
pipenv shell
source test_env.sh
pytest
```
