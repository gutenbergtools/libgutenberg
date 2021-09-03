#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase
from libgutenberg import GutenbergFiles

global db_exists
db_exists = GutenbergDatabase.db_exists

class TestGutenbergFiles(unittest.TestCase):

    @unittest.skipIf(not db_exists, 'database not configured')
    def test_guess_filetype(self):
        ft, enc = GutenbergFiles.guess_filetype("99999-0.txt")
        self.assertEqual(ft, 'txt')
        self.assertEqual(enc, 'utf-8')
