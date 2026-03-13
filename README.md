# libgutenberg
Common files used by Project Gutenberg python projects.

# installation

`pipenv install libgutenberg`
`pipenv install 'libgutenberg+covers'` for cover generation
`pipenv install 'libgutenberg+postgres'` for use with postgres

or 

`pip install libgutenberg`
`pip install 'libgutenberg+covers'` for cover generation
`pip install 'libgutenberg+postgres'` for use with postgres


Depending on your system configuration, you might need to use pip or pipenv to install

`psycopg2-binary`

cover generation may require some system packages; see

<https://doc.courtbouillon.org/cairocffi/stable/overview.html#installing-cffi>
