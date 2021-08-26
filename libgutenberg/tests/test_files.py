#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergFiles

class TestGutenbergFiles(unittest.TestCase):

    def test_guess_filetype(self):
        ft, enc = GutenbergFiles.guess_filetype("99999-0.txt")
        self.assertEqual(ft, 'txt')
        self.assertEqual(enc, 'utf-8')
