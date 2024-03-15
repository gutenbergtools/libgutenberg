#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import unittest


from libgutenberg.CommonOptions import Options
from libgutenberg import GutenbergDatabase, GutenbergDatabaseDublinCore, DummyConnectionPool
from libgutenberg import DBUtils, DublinCoreMapping
from libgutenberg.Logger import debug, warning
from libgutenberg.Models import Attribute, Book

global db_exists

db_exists = GutenbergDatabase.db_exists
options = Options()
options.config = None
if db_exists:
    import psycopg2
    try:
        GutenbergDatabase.Database().connect()
    except psycopg2.OperationalError:
        db_exists = False
        Warning("can't connect to database")


@unittest.skipIf(not db_exists, 'database not configured')
class TestDC(unittest.TestCase):
    ebook = 20050
    title = "Märchen der Gebrüder Grimm 1"
    ebook2 = 2600 # war and peace

    def setUp(self):
        GutenbergDatabase.DB = GutenbergDatabase.Database()
        GutenbergDatabase.DB.connect()
        self.dummypool = DummyConnectionPool.ConnectionPool()
        #self.dc2 = self.dc
        

    def test_metadata(self):
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        self.metadata_test1(dc)
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        self.metadata_test2(dc)

    def test_orm_metadata(self):
        dc = DublinCoreMapping.DublinCoreObject()
        self.metadata_test1(dc)
        dc = DublinCoreMapping.DublinCoreObject()
        self.metadata_test2(dc)

    def metadata_test1(self, dc):
        dc.load_from_database(self.ebook)
        self.assertEqual(dc.project_gutenberg_id, 20050)
        self.assertEqual(dc.title, self.title)
        self.assertEqual(dc.rights, 'Public domain in the USA.')
        self.assertEqual(str(dc.release_date), '2006-12-09')
        self.assertEqual(dc.languages[0].id, 'de')
        self.assertEqual(dc.marcs[0].code, '245')
        self.assertEqual(dc.marcs[0].caption, 'Title')
        self.assertEqual(dc.title, dc.title_file_as)
        self.assertEqual(len(dc.authors), 2)
        author = dc.authors[0]
        self.assertTrue(author.name.startswith("Grimm"))
        self.assertEqual(author.id, 971)
        self.assertEqual(author.marcrel, 'aut')
        self.assertEqual(author.role, 'Author')
        self.assertEqual(author.birthdate, 1785)
        self.assertEqual(author.deathdate, 1863)
        self.assertEqual(author.name_and_dates, 'Grimm, Jacob, 1785-1863')
        self.assertEqual(author.webpages[0].url, 'https://en.wikipedia.org/wiki/Jacob_Grimm')
        self.assertEqual(author.aliases[0].alias, 'Grimm, Jacob Ludwig Carl')
        self.assertEqual(len(dc.subjects), 1)
        self.assertEqual(dc.subjects[0].subject, 'Fairy tales -- Germany')
        self.assertEqual(len(dc.bookshelves), 1)
        self.assertEqual(dc.bookshelves[0].bookshelf, 'DE Kinderbuch')
        self.assertEqual(dc.loccs[0].locc, 'Geography, Anthropology, Recreation: Folklore')
        self.assertEqual(dc.dcmitypes[0].id, 'Sound')


    def metadata_test2(self, dc2):
        dc2.load_from_database(self.ebook2)
        self.assertEqual('en', dc2.languages[0].id)
        self.assertEqual(len(dc2.bookshelves), 5)
        self.assertEqual(dc2.bookshelves[0].bookshelf, 'Napoleonic(Bookshelf)')
        self.assertEqual(dc2.dcmitypes[0].id, 'Text')


    def test_files(self):
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        self.files_test1(dc)
        self.files_test2(dc)

    def test_orm_files(self):
        dc = DublinCoreMapping.DublinCoreObject()
        self.files_test1(dc)
        self.files_test2(dc)

    def files_test1(self, dc):
        dc.load_from_database(self.ebook)
        self.assertTrue(dc.new_filesystem)
        self.assertEqual(len(dc.files) , 159)
        self.assertEqual(dc.files[0].archive_path, '2/0/0/5/20050/20050-readme.txt')
        self.assertEqual(dc.files[0].url, 'https://www.gutenberg.org/files/20050/20050-readme.txt')
        self.assertTrue(dc.files[0].extent, True)
        self.assertEqual(dc.files[0].hr_extent, '25\xa0kB')
        self.assertTrue(dc.files[0].modified, True)
        self.assertEqual(dc.files[0].hr_filetype, 'Readme')
        self.assertEqual(dc.files[0].encoding, None)
        self.assertEqual(dc.files[0].compression, 'none')
        self.assertEqual(dc.files[0].generated, False)
        self.assertEqual(dc.files[0].filetype, 'readme')
        self.assertTrue('Readme' in dc.filetypes)
        self.assertEqual(dc.files[0].mediatypes[-1].mimetype, 'text/plain')
        self.assertEqual(len(dc.mediatypes), 6)
        self.assertTrue('audio/ogg' in dc.mediatypes)

    def files_test2(self, dc2):
        dc2.load_from_database(self.ebook2)
        self.assertEqual(len(dc2.files) , 18)
        for file_ in dc2.files:
            if file_.encoding:
                break
        self.assertEqual(file_.encoding, 'us-ascii')
        for file_ in dc2.files:
            if file_.compression != 'none':
                break
        self.assertEqual(file_.compression, 'zip')
        for file_ in dc2.files:
            if file_.filetype == 'epub.images':
                break
        self.assertEqual(file_.generated, True)
        self.assertEqual(file_.url, 'https://www.gutenberg.org/ebooks/2600.epub.images')


    def exercise(self, ebook, dc):
        dc.__init__(self.dummypool)
        dc.load_from_database(ebook)
        test = '%s%s%s%s' % (dc.title, dc.title_file_as, dc.rights,dc.rights)
        test = [lang.id for lang in dc.languages]
        test = [marc.code for marc in dc.marcs]
        test = [[alias for alias in author.aliases] for author in dc.authors]
        test = [subject for subject in dc.subjects]

    def test_10k(self):
        class DCCompat(DublinCoreMapping.DublinCoreObject):
            def __init__(self, pool):
                DublinCoreMapping.DublinCoreObject.__init__(self, session=None, pooled=True)
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        start_time = datetime.datetime.now()

        for ebook in range(5, 60005, 60):
            self.exercise(ebook, dc)
        end_time = datetime.datetime.now()
        print(' Finished 1000 dc tests. Total time: %s' % (end_time - start_time))

        start_time = datetime.datetime.now()

        for ebook in range(5, 60005, 60):
            dc = DCCompat(None)
            self.exercise(ebook, dc)
            dc.session.close()
        end_time = datetime.datetime.now()
        print(' Finished 1000 orm_dc tests. Total time: %s' % (end_time - start_time))

    def test_add_delete(self):
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        self.add_delete_files(dc)

    def test_add_delete_orm(self):
        dc = DublinCoreMapping.DublinCoreObject()
        self.add_delete_files(dc)

    def test_add_delete_orm_authors(self):
        dc = DublinCoreMapping.DublinCoreObject()
        adam = dc.get_or_create_author('Smith, Adamx')
        self.assertEqual(adam.name, 'Smith, Adamx')
        adam2 = dc.get_or_create_author('Smith, Adam')
        self.assertNotEqual(adam.id, adam2.id)
        adam3 = dc.get_or_create_author('Smith, adamx')
        self.assertEqual(adam.id, adam3.id)
        dc.session.delete(adam)

    def add_delete_files(self, dc):
        fn = 'README.md'
        saved = False
        dc.load_files_from_database(self.ebook2)
        numfiles = len(dc.files)
        dc.store_file_in_database(self.ebook2, fn, 'txt')
        dc.store_file_in_database(self.ebook2, fn, 'txt') # test over-writing
        dc.load_files_from_database(self.ebook2)
        for file_ in dc.files:
            if file_.archive_path.endswith(fn):
                saved = True
                break
        self.assertTrue(saved)
        dc.remove_file_from_database(fn) # filenames are unique!
        dc.load_files_from_database(self.ebook2)
        self.assertEqual(numfiles, len(dc.files))        

    def test_delete_types(self):
        fn = 'cache_for_test'  # command only remove filenames starting with 'cache'
        dc2 = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        dc2.load_files_from_database(self.ebook2)
        numfiles = len(dc2.files)
        dc2.store_file_in_database(self.ebook2, fn, 'qioo') # type is extinct
        dc2.load_files_from_database(self.ebook2)
        self.assertEqual(numfiles + 1, len(dc2.files))
        dc2.remove_filetype_from_database(self.ebook2, 'qioo')
        dc2.load_files_from_database(self.ebook2)
        self.assertEqual(numfiles, len(dc2.files))

    def test_register_coverpage(self):
        def get_cover(ebook, dc):
            dc.load_from_database(ebook)
            for marc in dc.marcs:
                if marc.code == '901':
                    return marc.text
        #ebook = 46     # tests the method, but there's no code to undo the test
        ebook = 199     # no ebook by that number
        dc = GutenbergDatabaseDublinCore.GutenbergDatabaseDublinCore(self.dummypool)
        dc.register_coverpage(ebook, 'new_cover')
        # does nothing to avoid violates foreign key constraint
        self.assertEqual(get_cover(ebook, dc), None) 
        
    def tearDown(self):
        pass

@unittest.skipIf(not db_exists, 'database not configured')
class TestDCLoader(unittest.TestCase):
    def setUp(self):
        self.test_fakebook = os.path.join(os.path.dirname(__file__),'99999-h.htm')

    def test_load_from_pgheader(self):
        dc = DublinCoreMapping.DublinCoreObject()
        with open(self.test_fakebook, 'r') as fakebook_file:
            dc.load_from_pgheader(fakebook_file.read())
        set_title = dc.title
        self.assertEqual(set_title, 'The Fake EBook of "Testing"')
        dc.title = "an extra long title, longer than 80 char, for The Fake EBook of \"Testing\", really we\'re not kidding"
        self.assertTrue(len(dc.make_pretty_title()) < 80)
        dc.title = set_title
        self.assertEqual(len(dc.authors), 6)
        dc.get_my_session()
        dc.save(updatemode=0)
        dc.session.flush()
        self.assertTrue(DBUtils.ebook_exists(99999, session=dc.session))
        self.assertEqual(len(dc.book.authors), 6)
        roles = [author.marcrel for author in dc.book.authors]
        self.assertTrue('trl' in roles)
        self.assertTrue('aui' in roles)
        self.assertTrue(DBUtils.author_exists('Lorem Ipsum Jr.', session=dc.session))
        self.assertTrue(DBUtils.author_exists('Hemingway, Ernest', session=dc.session))
        dc.load_from_database(99999)
        self.assertEqual(set_title, dc.title)
        self.assertEqual('A ChatPG Robot.', dc.credit)
        for cat in dc.dcmitypes:
            print(cat.id)
            self.assertEqual(cat.id, 'Text')
        dc.delete()
        dc = DublinCoreMapping.DublinCoreObject()
        dc.load_from_database(99999)
        self.assertFalse(dc.book)
        dc.session.flush()
        self.assertFalse(DBUtils.ebook_exists(99999))
        self.assertTrue(DBUtils.author_exists('Hemingway, Ernest'))
        self.assertTrue(DBUtils.author_exists('Lorem Ipsum Jr.'))
        DBUtils.remove_author('Lorem Ipsum Jr.', session=dc.session)
        self.assertFalse(DBUtils.author_exists('Lorem Ipsum Jr.'))

    def tearDown(self):
        session = DBUtils.check_session(None)
        
        #DBUtils.remove_author('Lorem Ipsum Jr.', session=session)
        session.query(Book).filter(Book.pk == 99999).delete()
        session.commit()
        

@unittest.skipIf(not db_exists, 'database not configured')
class TestDCJson(unittest.TestCase):
    def setUp(self):
        self.test_fakebook = os.path.join(os.path.dirname(__file__),'99999.json')

    def test_load_from_json(self):
        dc = DublinCoreMapping.DublinCoreObject()
        with open(self.test_fakebook, 'r') as fakebook_file:
            dc.load_from_pgheader(fakebook_file.read())
        set_title = dc.title
        set_subtitle = dc.subtitle
        self.assertEqual(set_title, "A Sagebrush's Cinderella: not a subtitle")
        self.assertEqual(set_subtitle, "a true story : second line")
        self.assertEqual(len(dc.authors), 2)
        self.assertEqual(len(dc.scan_urls), 2)
        self.assertEqual(dc.pubinfo.first_year, '1920')
        self.assertEqual(dc.credit, 'Roger Frank and Sue Clark.')
        dc.add_credit('Sue Frank and Roger Clark.\n')
        self.assertEqual(dc.credit, 'Roger Frank and Sue Clark.')
        dc.get_my_session()
        dc.save(updatemode=0)
        dc.session.flush()
        dc.credit = 'Added Credit'
        dc.save(updatemode=0)
        
        self.assertTrue(DBUtils.ebook_exists(99999, session=dc.session))
        self.assertEqual(len(dc.book.authors), 2)
        dc.load_from_database(99999)
        self.assertEqual(set_title, dc.title)
        self.assertEqual(set_subtitle, dc.subtitle)
        marc260 = dc.session.query(Attribute).filter_by(book=dc.book, fk_attriblist=260).first().text
        self.assertTrue('1920' in marc260)
        self.assertEqual(
            '  $aNew York, NY :$bFrank A. Munsey Company, $c1920, reprint 1955, reprint 1972.',
            marc260)
        self.assertEqual(
            'New York, NY: Frank A. Munsey Company, 1920, reprint 1955, reprint 1972.',
            dc.strip_marc_subfields(marc260))
        marc508s = dc.session.query(Attribute).filter_by(book=dc.book, fk_attriblist=508)
        self.assertEqual(len(marc508s.first().text), 12) #length of 'Added Credit'
        self.assertEqual(1, marc508s.count())
        self.assertEqual(
            len(dc.session.query(Attribute).filter_by(book=dc.book,
                fk_attriblist=904).all()),
            2)
        self.assertEqual(
            dc.session.query(Attribute).filter_by(book=dc.book, fk_attriblist=905).first().text,
            '20210623194947brand')
        self.assertEqual(1, marc508s.count())
        dc.delete()
        dc = DublinCoreMapping.DublinCoreObject()
        dc.load_from_database(99999)
        dc.session.flush()
        self.assertFalse(DBUtils.ebook_exists(99999))

    def tearDown(self):
        session = DBUtils.check_session(None)
        DBUtils.remove_author('Lorem Ipsum Jr.', session=session)
        session.query(Book).filter(Book.pk == 99999).delete()
        session.commit()
