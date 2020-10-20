#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase

db_exists = GutenbergDatabase.db_exists

options.config = None

@unittest.skipIf(not db_exists, 'database not configured')
class TestORM(unittest.TestCase):

    def setUp(self):
        ob = GutenbergDatabase.Objectbase()
        self.session = ob.get_session()

    def tearDown(self):
        pass
