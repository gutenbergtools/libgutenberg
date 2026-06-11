#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from sqlalchemy import select
from sqlalchemy.sql import func



from libgutenberg import GutenbergDatabase
from libgutenberg.CommonOptions import Options
from libgutenberg.Logger import warning
from libgutenberg.Models import Book

global db_exists

db_exists = GutenbergDatabase.db_exists
options = Options()
options.config = None
if db_exists:
    import psycopg2
    try:
        GutenbergDatabase.Database().connect()
    except psycopg2.OperationalError:
        db_exists = False
        Warning("can't connect to database")

@unittest.skipIf(not db_exists, 'database not configured')
class TestORM(unittest.TestCase):

    def setUp(self):
        ob = GutenbergDatabase.Objectbase(False)
        self.session = ob.get_session()

    def test_query(self):
        num_books = self.session.query(Book).count()
        mx = self.session.execute(select(func.max(Book.pk))).scalars().first()

    def tearDown(self):
        pass
