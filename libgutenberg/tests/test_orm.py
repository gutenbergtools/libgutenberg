#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from sqlalchemy import select
from sqlalchemy.sql import func

from libgutenberg import GutenbergDatabase

from libgutenberg.CommonOptions import Options
from libgutenberg.Models import Book

options = Options()
options.config = None
db_exists = GutenbergDatabase.db_exists

@unittest.skipIf(not db_exists, 'database not configured')
class TestORM(unittest.TestCase):

    def setUp(self):
        ob = GutenbergDatabase.Objectbase(False)
        self.session = ob.get_session()

    def test_query(self):
        num_books = self.session.query(Book).count()
        mx = self.session.execute(select(func.max(Book.pk))).scalars().first()
        print(mx)

    def tearDown(self):
        pass
