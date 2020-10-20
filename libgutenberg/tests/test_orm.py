#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase

from libgutenberg.CommonOptions import Options

options = Options()
options.config = None
db_exists = GutenbergDatabase.db_exists

@unittest.skipIf(not db_exists, 'database not configured')
class TestORM(unittest.TestCase):

    def setUp(self):
        ob = GutenbergDatabase.Objectbase()
        self.session = ob.get_session()

    def tearDown(self):
        pass
