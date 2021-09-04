#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""
GutenbergDatabase.py

Copyright 2009-2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals

import logging
import os


from .CommonOptions import Options
from .Logger import critical, debug, info, warning

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool.impl import QueuePool, NullPool
try:
    import psycopg2
    import psycopg2.extensions

    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
    DatabaseError  = psycopg2.DatabaseError
    IntegrityError = psycopg2.IntegrityError
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

    db_exists = True

except ImportError:
    db_exists = False
    class DatabaseError(Exception):
        pass
    class IntegrityError(Exception):
        pass
    info('Gutenberg Database is inactive because psycopg2 not installed')


options = Options()

DB = None
OB = None

class xl(object):
    """ Translate numeric indices into field names.

    >>> r = xl(cursor, row)
    >>> r.pk
    >>> r['pk']
    >>> r[0]
    """

    def __init__(self, cursor, row):
        self.row = row
        self.colname_to_index = dict([(x[1][0], x[0]) for x in enumerate(cursor.description)])

    def __getitem__(self, column):
        if isinstance(column, int):
            return self.row[column]
        return self.row[self.colname_to_index[column]]

    def __getattr__(self, colname):
        return self.row[self.colname_to_index[colname]]

    def get(self, colname, default = None):
        """ Get value from field in row. """
        if colname in self.colname_to_index:
            return self.row[self.colname_to_index [colname]]
        return default


def get_connection_params(args = None):
    """ Get connection parameters from environment. """

    if args is None:
        args = {}

    def _get(param):
        """ Get param either from args or environment or config. """
        if param in args:
            return args[param]
        param = param.upper()
        if param in os.environ:
            return os.environ[param]
        try:
            return getattr(options.config, param)
        except (NameError, AttributeError):
            return None

    host     = _get('pghost')
    port     = _get('pgport')
    database = _get('pgdatabase')
    user     = _get('pguser')

    params = { 'host': host,
               'port': int(port) if port else 5432,
               'database': database,
               'user': user }
    return params


def get_sqlalchemy_url():
    """ Build a connection string for SQLAlchemy. """

    params = get_connection_params()
    return "postgresql://%(user)s@%(host)s:%(port)d/%(database)s" % params


class Database(object):
    """ Class to connect to PG database. """

    def __init__(self, args = None):
        self.connection_params = get_connection_params(args)
        self.conn = None


    def connect(self):
        """ connect to database """

        try:
            vpncmd = getattr(options.config, 'PGVPNCMD', None)
            vpncmd = os.environ.get('PGVPNCMD', vpncmd)
            if vpncmd:
                debug("Starting VPN ...")
                os.system(vpncmd)

            debug("Connecting to database ...")

            self.conn = psycopg2.connect(**self.connection_params)

            debug("Connected to host %s database %s.",
                self.connection_params['host'],
                self.connection_params['database'])

        except psycopg2.DatabaseError as what:
            critical("Cannot connect to database server (%s)" % what)
            raise


    def get_cursor(self):
        """ Return database cursor. """
        return self.conn.cursor()

class Objectbase(object):
    def __init__(self, pooled):
        poolclass = QueuePool if pooled else NullPool
        self.engine = create_engine(get_sqlalchemy_url(), echo=False, poolclass=poolclass)

        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()
