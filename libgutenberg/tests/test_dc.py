#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase, GutenbergDatabaseDublinCore, DummyConnectionPool
from libgutenberg.CommonOptions import Options

options = Options()
options.config = None

@unittest.skipIf(not hasattr(GutenbergDatabase, 'psycopg2'), 'psycopg2 not installed')
class TestOldDC(unittest.TestCase):
    # "War and Peace"
    ebook = 2600
    title = "War and Peace"

    def setUp(self):
        GutenbergDatabase.DB = GutenbergDatabase.Database()
        GutenbergDatabase.DB.connect ()
        self.dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(
            DummyConnectionPool.ConnectionPool()
        )

        self.dc.load_from_database(self.ebook)


    def test_metadata(self):
        self.assertEqual(self.dc.project_gutenberg_id, 2600)
        self.assertEqual(self.dc.title, "War and Peace")

    def test_files(self):
        self.assertTrue(len(self.dc.files) > 5)

    def tearDown(self):
        pass

@unittest.skipIf(not hasattr(GutenbergDatabase, 'psycopg2'), 'psycopg2 not installed')
class TestNewDC(unittest.TestCase):
    # "War and Peace"
    ebook = 2600
    title = "War and Peace"
    
    # dummy object to be replaced by ORM object
    class DublinCoreObject(object):
        def __init__(self, ebook):
            self.project_gutenberg_id = ebook
            self.title = "War and Peace"
            self.files = range(1, 11)
    
    def setUp(self):
        self.dc = self.DublinCoreObject(2600)
        


    def test_metadata(self):
        self.assertEqual(self.dc.project_gutenberg_id, 2600)
        self.assertEqual(self.dc.title, "War and Peace")

    def test_files(self):
        self.assertTrue(len(self.dc.files) > 5)

    def tearDown(self):
        pass
