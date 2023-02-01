#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from libgutenberg import GutenbergDatabase
from libgutenberg import GutenbergFiles
from libgutenberg.DublinCoreMapping import DublinCoreObject 
from libgutenberg.DBUtils import check_session, ebook_exists
from libgutenberg.GutenbergFiles import store_file_in_database, PUBLIC, FILES, FTP
from libgutenberg.Models import Book, File

global db_exists
db_exists = GutenbergDatabase.db_exists

class TestGutenbergFiles(unittest.TestCase):
    def setUp(self):
        self.dc = DublinCoreObject()
        self.dc.get_my_session()
        
    def test_guess_filetype(self):
        ft, enc = GutenbergFiles.guess_filetype("99999-0.txt")
        self.assertEqual(ft, 'txt')
        self.assertEqual(enc, 'utf-8')

    @unittest.skipIf(not db_exists, 'database not configured')
    def test_file_save_and_read(self):
        ''' Make sure there's a file at /Users/Shared/Documents/pg/dev/html/files/99999/99999.txt
            and that  FILES is set in .env '''
        
        self.assertEqual(FILES, '/Users/Shared/Documents/pg/dev/html/files/')
        book = self.dc.load_or_create_book(99999)
        store_file_in_database(99999,
            '/Users/Shared/Documents/pg/dev/html/files/99999/99999.txt', None,
            session=self.dc.session)
        self.assertEqual(book.files[0].archive_path, '99999/99999.txt')

    def tearDown(self):
        session = self.dc.session
        session.query(File).filter(File.archive_path == '99999/99999.txt').delete()
        session.query(Book).filter(Book.pk == 99999).delete()
        session.commit()
