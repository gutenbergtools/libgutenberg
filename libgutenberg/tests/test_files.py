#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase
from libgutenberg import GutenbergFiles
from libgutenberg.DublinCoreMapping import DublinCoreObject 
from libgutenberg.DBUtils import check_session, ebook_exists
from libgutenberg.GutenbergFiles import store_file_in_database, PUBLIC, FILES, FTP

global db_exists
db_exists = GutenbergDatabase.db_exists

class TestGutenbergFiles(unittest.TestCase):

    @unittest.skipIf(not db_exists, 'database not configured')
    def test_guess_filetype(self):
        ft, enc = GutenbergFiles.guess_filetype("99999-0.txt")
        self.assertEqual(ft, 'txt')
        self.assertEqual(enc, 'utf-8')

    @unittest.skipIf(not db_exists, 'database not configured')
    def test_file_save_and_read(self):
        ''' Make sure there's a file at /Users/Shared/Documents/pg/dev/html/files//99999/99999.txt
            and that  FILES is set in .env '''
        dc = DublinCoreObject()
        self.assertEqual(FILES, '/Users/Shared/Documents/pg/dev/html/files/')
        book = dc.load_or_create_book(99999)
        store_file_in_database(99999,
            '/Users/Shared/Documents/pg/dev/html/files/99999/99999.txt', None, session=dc.session)
        self.assertEqual(book.files[0].archive_path, '99999/99999.txt')
        