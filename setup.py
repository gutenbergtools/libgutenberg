#!/usr/bin/env python
#
# libgutenberg setup.py
#

__version__ = '0.1.6'

from distutils.core import setup

setup (
    name         = 'libgutenberg',
    version      = __version__,

    package_dir = {
        'libgutenberg': 'libgutenberg',
    },

    install_requires = [
        'lxml',
        # We cannot make this package dependent on psycopg2 because
        # most users will not have postgres installed.  Thus all
        # packages that actually use the GutenbergDatabase module will
        # have to depend on psycopg2 themselves.
        # 'psycopg2',
    ],

    packages = [
        'libgutenberg'
    ],

    # metadata for upload to PyPI

    author = "Marcello Perathoner",
    author_email = "webmaster@gutenberg.org",
    description = "Common files used by Project Gutenberg python projects.",
    long_description = "Useless as standalone install. Used only as requirement for other packages.",
    license = "GPL v3",
    keywords = "project gutenberg",
    url = "http://pypi.python.org/pypi/libgutenberg/",

    classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Other Audience",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],

    platforms = 'OS-independent',
)
