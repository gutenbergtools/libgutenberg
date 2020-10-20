#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
DummyConnectionPool.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals

from . import GutenbergDatabase

class ConnectionPool(object):
    """A class that looks like a SQLAlchemy engine/connection pool. """
    dummy = True

    def connect(self):
        return GutenbergDatabase.DB.conn
