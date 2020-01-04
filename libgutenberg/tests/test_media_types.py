#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import MediaTypes

class TestMediaTypes(unittest.TestCase):

    def setUp(self):
        self.mediatypes = MediaTypes.mediatypes

    def test_xml(self):
        self.assertEqual('application/xml', MediaTypes.guess_type('sample.xml'))
        self.assertEqual('application/xml', self.mediatypes.xml)

    def test_bad(self):
        self.assertEqual('', MediaTypes.guess_type('aufbapiufbiuvb'))
        self.assertEqual('', MediaTypes.guess_type('aufbapiufbiuvb.bad'))
        self.assertEqual('', self.mediatypes.bad)

    def tearDown(self):
        pass
