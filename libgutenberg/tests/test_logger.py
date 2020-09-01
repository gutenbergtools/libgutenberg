#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg.Logger import info
from libgutenberg import Logger

class TestLoggger(unittest.TestCase):

    def setUp(self):
        Logger.setup(Logger.LOGFORMAT, 'test.log')        

    def test_noebook(self):
        info('test1')

    def test_intebook(self):
        Logger.ebook = 1
        info('test2')

    def test_strebook(self):
        Logger.ebook = 'one'
        info('test3')

