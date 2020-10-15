#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import unittest

from libgutenberg.CommonOptions import Options
from libgutenberg import GutenbergDatabase, GutenbergDatabaseDublinCore, DummyConnectionPool

db_exists = GutenbergDatabase.db_exists

options = Options()
options.config = None

@unittest.skipIf(not db_exists, 'database not configured')
class TestDC(unittest.TestCase):
    ebook = 20050
    title = "Märchen der Gebrüder Grimm 1"
    ebook2 = 2600 # war and peace

    def setUp(self):
        GutenbergDatabase.DB = GutenbergDatabase.Database()
        GutenbergDatabase.DB.connect()
        dummypool = DummyConnectionPool.ConnectionPool()
        self.dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(dummypool)
        self.dc2 = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(dummypool)
        #self.dc2 = self.dc
        self.dc.load_from_database(self.ebook)
        self.dc2.load_from_database(self.ebook2)
        

    def test_metadata(self):
        self.assertEqual(self.dc.project_gutenberg_id, 20050)
        self.assertEqual(self.dc.title, self.title)
        self.assertEqual(self.dc.rights, 'Public domain in the USA.')
        self.assertEqual(str(self.dc.release_date), '2006-12-09')
        self.assertEqual(self.dc.languages[0].id, 'de')
        self.assertEqual(self.dc.marcs[0].code, '245')
        self.assertEqual(self.dc.marcs[0].caption, 'Title')
        self.assertEqual(self.dc.title, self.dc.title_file_as)
        self.assertEqual(len(self.dc.authors), 2)
        author = self.dc.authors[0]
        self.assertTrue(author.name.startswith("Grimm"))
        self.assertEqual(author.id, 971)
        self.assertEqual(author.marcrel, 'aut')
        self.assertEqual(author.role, 'Author')
        self.assertEqual(author.birthdate, 1785)
        self.assertEqual(author.deathdate, 1863)
        self.assertEqual(author.name_and_dates, 'Grimm, Jacob, 1785-1863')
        self.assertEqual(author.webpages[0].url, 'https://en.wikipedia.org/wiki/Jacob_Grimm')
        self.assertEqual(author.aliases[0].alias, 'Grimm, Jacob Ludwig Carl')
        self.assertEqual(len(self.dc.subjects), 1)
        self.assertEqual(self.dc.subjects[0].subject, 'Fairy tales -- Germany')
        self.assertEqual(len(self.dc.bookshelves), 1)
        self.assertEqual(self.dc.bookshelves[0].bookshelf, 'DE Kinderbuch')
        self.assertEqual(self.dc.loccs[0].locc, 'Geography, Anthropology, Recreation: Folklore')
        self.assertEqual(self.dc.dcmitypes[0].id, 'Sound')

        self.assertEqual(self.dc2.languages[0].id, 'en')
        self.assertEqual(len(self.dc2.bookshelves), 5)
        self.assertEqual(self.dc2.bookshelves[0].bookshelf, 'Napoleonic(Bookshelf)')
        self.assertEqual(self.dc2.dcmitypes[0].id, 'Text')


    def test_files(self):
        self.assertTrue(self.dc.new_filesystem)
        self.assertEqual(len(self.dc2.files) , 11)
        self.assertEqual(len(self.dc.files) , 159)
        self.assertEqual(self.dc.files[0].url, 'https://www.gutenberg.org/files/20050/20050-readme.txt')
        self.assertTrue(self.dc.files[0].extent, True)
        self.assertEqual(self.dc.files[0].hr_extent, '25\xa0kB')
        self.assertTrue(self.dc.files[0].modified, True)
        self.assertEqual(self.dc.files[0].hr_filetype, 'Readme')
        self.assertEqual(self.dc.files[0].encoding, None)
        self.assertEqual(self.dc2.files[0].encoding, 'utf-8')
        self.assertEqual(self.dc.files[0].compression, 'none')
        self.assertEqual(self.dc2.files[1].compression, 'zip')
        self.assertEqual(self.dc.files[0].generated, False)
        self.assertEqual(self.dc2.files[2].generated, True)
        self.assertEqual(self.dc2.files[2].url, 'https://www.gutenberg.org/ebooks/2600.epub.images')
        self.assertEqual(self.dc.files[0].filetype, 'readme')
        self.assertTrue('Readme' in self.dc.filetypes)
        self.assertEqual(self.dc.files[0].mediatypes[-1].mimetype, 'text/plain')
        self.assertEqual(len(self.dc.mediatypes), 6)
        self.assertTrue('audio/ogg' in self.dc.mediatypes)


    def exercise(self, ebook):
        dummypool = DummyConnectionPool.ConnectionPool()
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(dummypool)
        dc.load_from_database(ebook)
        test = '%s%s%s%s' % (dc.title, dc.title_file_as, dc.rights,dc.rights)
        test = [lang.id for lang in dc.languages]
        test = [marc.code for marc in dc.marcs]
        test = [[alias for alias in author.aliases] for author in dc.authors]
        test = [subject for subject in dc.subjects]

    def test_10k(self):
        start_time = datetime.datetime.now()

        for ebook in range(5, 60005, 60):
            self.exercise(ebook)
                
        end_time = datetime.datetime.now()
        print(' Finished 10,000 tests. Total time: %s' % (end_time - start_time))


    def tearDown(self):
        pass
