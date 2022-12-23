#!/usr/bin/env python
#
# libgutenberg setup.py
#

__version__ = '0.10.11'

from setuptools import setup

setup (
    name         = 'libgutenberg',
    version      = __version__,

    package_dir = {
        'libgutenberg': 'libgutenberg',
    },

    install_requires = [
        'lxml>=4.9.1',
        'pycountry',
        'six>=1.4.1',
        'sqlalchemy>=1.4.0',
    ],
    extras_require = {
        'postgres':  ['psycopg2',],
        'covers': ['cairocffi==0.8.0'],
    },
    packages = [
        'libgutenberg'
    ],

    # metadata for upload to PyPI

    author = "Marcello Perathoner",
    maintainer = "Eric Hellman",
    maintainer_email = "eric@hellman.net",
    description = "Common files used by Project Gutenberg python projects.",
    long_description = "Useless as standalone install. Used only as requirement for other packages.",
    license = "GPL v3",
    keywords = "project gutenberg",
    url = "https://github.com/gutenbergtools/libgutenberg/",

    classifiers = [
        "Intended Audience :: Other Audience",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],

    platforms = 'OS-independent',
)
