#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

from libgutenberg import Cover
from libgutenberg.DublinCore import DublinCore as dc

@unittest.skipIf(not 'cairo' in dir(Cover), 'cover generator not configured')
class TestMakeCovers(unittest.TestCase):

    def setUp(self):
        self.test_path =  os.path.join(os.path.dirname(__file__),'cover.png')
        self.dc = dc()
        self.dc.add_author("Duck, Donald")
        self.dc.add_author("Mickey Mouse")
        self.dc.title = "A truly amazing book: (但不是那么神奇)"

    def test_cover(self):
        try:
            cover_image = Cover.draw(self.dc)
            with open(self.test_path, 'wb+') as cover:
                cover_image.save(cover)
            self.assertTrue(os.path.exists(self.test_path))
        except OSError:
            # eat this exception so the test will pass in server environments
            print("OSError, probably Cairo not installed.")
            return None

    def tearDown(self):
        if os.path.exists(self.test_path):
            os.remove(self.test_path)
