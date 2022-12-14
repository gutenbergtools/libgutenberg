#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

DublinCoreMapping.py

Copyright 2009-2020 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

API-compatable ORM version of GutenbergDatabaseDublin core.
Main difference is how connections are managed. In a multithreading environment, use
pooled=True and be sure to close the session when done with a thread.

"""

from __future__ import unicode_literals

import datetime
import unicodedata
from sqlalchemy.exc import DBAPIError

from . import DublinCore
from . import GutenbergGlobals as gg
from . import GutenbergDatabase
from . import GutenbergFiles
from .DBUtils import get_lang
from .GutenbergGlobals import Struct, PG_URL
from .Logger import debug, error, info, warning
from .GutenbergDatabase import DatabaseError, IntegrityError, Objectbase
from .Models import (Alias, Attribute, Author, Book, BookAuthor, Category, File, Locc,
    Role, Subject)


class DublinCoreObject(DublinCore.GutenbergDublinCore):
    """ Augment GutenbergDublinCore class. """

    def __init__(self, session=None, pooled=False):
        DublinCore.GutenbergDublinCore.__init__ (self)

        self.new_filesystem = False
        self.mediatypes = set()
        self.filetypes = set()
        self.files = []
        self.generated_files = []
        self.book = None
        self.pooled = pooled

        self.marcs = []
        self.session = session


    def append_lang(self, lang):
        if isinstance(lang, (Struct, str)):
            tried_lang = lang if isinstance(lang, str) else lang.language
            lang = get_lang(lang, session=self.session)
            if not lang:
                error("%s is not a recognizable language", tried_lang)
                raise ValueError()
        self.languages.append(lang)


    def get_my_session(self):
        if not GutenbergDatabase.OB:
            GutenbergDatabase.OB = Objectbase(self.pooled)
        if not self.session:
            self.session = GutenbergDatabase.OB.get_session()
        return self.session


    def has_images(self):
        """ Return True if this book has images. """

        for file_ in self.files:
            if file_.filetype and file_.filetype.find('.images') > -1:
                return True
        return False

    def load_book(self, ebook):
        self.project_gutenberg_id = ebook
        session = self.get_my_session()
        book = session.query(Book).filter_by(pk=ebook).first()
        self.book = book
        if not book:
            warning('no book for %s', ebook)
        return book

    def load_or_create_book(self, ebook):
        self.project_gutenberg_id = ebook
        if not self.load_book(ebook):
            session = self.get_my_session()
            self.book = Book(pk=ebook)
            session.add(self.book)
            session.commit()
        return self.book

    def load_from_database(self, ebook, load_files=True):
        """ loads book, then configure dc to match the legacy DublinCore API """
        def struct(**args):
            s = Struct()
            for key in args:
                setattr(s, key, args[key])
            return s

        book = self.load_book(ebook)
        if not book:
            return

        # Load DublinCore from PG database.
        if self.release_date == datetime.date.min:
            self.release_date = book.release_date
        self.downloads = book.downloads
        if not self.rights:
            self.rights = book.rights

        # authors
        if not self.authors:
            self.authors = book.authors

        for attrib in book.attributes:
            marc = Struct()
            marc.code = attrib.attribute_type.name.split(' ')[0]
            marc.text = self.strip_marc_subfields(attrib.text)
            marc.caption = attrib.attribute_type.caption
            self.marcs.append(marc)

            if marc.code == '245':
                self.title = marc.text
                self.title_file_as = marc.text[attrib.nonfiling:]
                self.title_file_as = self.title_file_as[0].upper() +\
                    self.title_file_as[1:]
                debug("Title: %s", self.title)
            elif marc.code == '206':
                self.alt_title = marc.text
            elif marc.code == '260':
                self.pubinfo.years = [('copyright', marc.text)]
            elif marc.code == '500':
                self.notes = marc.text
            elif marc.code == '505':
                self.contents = marc.text
            elif marc.code == '508':
                self.credit = marc.text
            elif marc.code == '904':
                self.scan_urls = marc.text
            elif marc.code == '905':
                self.request_key = marc.text
            elif marc.code == '906':
                if '$b' in attrib.text:
                    publisher = attrib.text.split('$b')[1]
                    publisher = publisher.split(',')[0]
                    self.pubinfo.publisher = publisher
            elif marc.code == '907':
                self.pubinfo.country = marc.text

        # languages (datatype)
        if not self.languages:
            self.languages = book.langs if book.langs else [struct(id='en', language='English')]

        # subjects (vocabulary)
        if not self.subjects:
            self.subjects = book.subjects

        # bookshelves (PG private vocabulary)
        if not self.bookshelves:
            self.bookshelves = book.bookshelves

        # LoCC (vocabulary)
        if not self.loccs:
            self.loccs = book.loccs

        # categories(text, audiobook, etc)
        if book.categories:
            self.dcmitypes = [struct(id=cat.dcmitype[0], description=cat.dcmitype[1])
                              for cat in book.categories]
        else:
            self.dcmitypes = [struct(id='Text', description='Text')]

        if load_files:
            self.load_files_from_database(ebook)


    def load_files_from_database(self, ebook):
        """ Load files from PG database.

        Files are not in DublinCore but useful to have here.

        """

        self.new_filesystem = False
        self.mediatypes = set()
        self.filetypes = set()
        self.generated_files = []

        session = self.get_my_session()

        # files(not strictly DublinCore but useful)
        if self.book:
            self.files = self.book.files
        else:
            #only files wanted
            self.files = session.query(File).filter_by(fk_books=ebook, obsoleted=0, diskstatus=0).\
                order_by(File.ftsortorder, File.encsortorder, File.fk_filetypes,
                        File.fk_encodings, File.compression, File.archive_path).all()

        for file_ in self.files:
            fn = file_.archive_path
            adir = gg.archive_dir(ebook)
            if fn.startswith(adir):
                fn = fn.replace(adir, 'files/%d' % ebook)
                self.new_filesystem = True
            elif fn.startswith('etext'):
                fn = 'dirs/' + fn
            file_.filename = fn

            if file_.filetype:
                self.filetypes.add(file_.hr_filetype)

            url = PG_URL + file_.filename
            if file_.generated and not file_.fk_filetypes.startswith('cover.'):
                url = "%sebooks/%d.%s" % (PG_URL, ebook, file_.fk_filetypes)
            file_.url = url

            if hasattr(file_, 'mediatype'):
                self.mediatypes.add(file_.mediatype)
        #session.commit()

    def remove_filetype_from_database(self, id_, type_):
        """ Remove filetype from PG database. """
        session = self.get_my_session()
        with session.begin_nested():
            session.query(File).filter(File.fk_books == id_).filter(File.fk_filetypes == type_).\
                filter(File.archive_path.startswith('cache')).\
                delete(synchronize_session='fetch')
        session.commit()

    def remove_file_from_database(self, filename):
        """ Remove file from PG database. """
        session = self.get_my_session()
        GutenbergFiles.remove_file_from_database(filename, session=session)

    def store_file_in_database(self, id_, filename, type_):
        """ Store file in PG database. """
        session = self.get_my_session()
        GutenbergFiles.store_file_in_database(id_, filename, type_, session=session)

    def register_coverpage(self, id_, url, code=901):
        """ Register a coverpage for this ebook. """
        session = self.get_my_session()
        try:
            session.begin_nested()
            session.add(Attribute(fk_books=id_, fk_attriblist=code,
                                  text=gg.archive2files(id_, url)))
            session.commit()

        except IntegrityError:  # Duplicate key
            session.rollback()

        except (DatabaseError, DBAPIError) as what:
            warning("Error updating coverpage in database: %s.", what)
            session.rollback()

    def save(self, updatemode=0):
        """
            updatemode = 0 : initial metadata creation; won't change an existing book
            updatemode = 1 : change metadata for an existing book
        """
        if not self.project_gutenberg_id:
            error("can't save without a project gutenberg id")
            return

        if not self.book:
            # this has not yet been loaded from a database or pre-assigned an id
            info("loading book for project gutenberg id %s", self.project_gutenberg_id)
            self.load_or_create_book(self.project_gutenberg_id)


        session = self.get_my_session()
        if self.book.updatemode != updatemode:
            # updated files, mostly don't change metadata
            info("ebook #%s already in database, marking update.", self.book.pk)
            if datetime.date.today() - self.book.release_date > datetime.timedelta(days=14):
                self.add_credit('Updated: ' + str(datetime.date.today()))
                self.add_attribute(self.book, [self.credit], marc=508)
                session.commit()
            return

        # either 0=0 for fresh book updatemode or 1=1 for re-editing old book

        self.add_authors(self.book)
        self.add_title(self.book, self.title)
        if self.alt_title:
            self.add_title(self.book, self.alt_title, marc=246)

        if self.contents:
            self.add_title(self.book, self.contents, marc=505)

        for language in self.languages:
            lang = get_lang(language.id, session=session)
            if lang and lang not in self.book.langs:
                self.book.langs.append(lang)

        for locc in self.loccs:
            locc = session.query(Locc).filter_by(locc=locc.locc).first()
            if locc and locc not in self.book.loccs:
                self.book.loccs.append(locc)

        for subject in self.subjects:
            subject = session.query(Subject).filter_by(subject=subject.subject).first()
            if subject and subject not in self.book.subjects:
                self.book.subjects.append(subject)

        if self.notes:
            att = session.query(Attribute).filter_by(book=self.book, fk_attriblist=500).first()
            if not att:
                self.book.attributes.append(Attribute(fk_attriblist=500, text=self.notes))

        self.book.copyrighted = 1 if 'Copyrighted' in self.rights else 0

        for category in self.categories:
            # It appears that this is dead code
            category = session.query(Category).filter_by(id=category.id).first()
            if category and category not in self.book.categories:
                self.book.categories.append(category)

        if self.book.release_date == datetime.date.min:
            # new release without release_date set; should not happen
            self.book.release_date = datetime.date.today()

        if self.pubinfo.publisher:
            self.add_attribute(self.book, self.pubinfo.marc(), marc=260)

        if self.pubinfo.first_year:
            self.add_attribute(self.book, self.pubinfo.first_year, marc=906)

        if self.pubinfo.country:
            self.add_attribute(self.book, self.pubinfo.country, marc=907)

        if self.credit:
            self.add_attribute(self.book, [self.credit], marc=508)

        if self.scan_urls:
            self.add_attribute(self.book, self.scan_urls, marc=904)

        if self.request_key:
            self.add_attribute(self.book, self.request_key, marc=905)

        self.book.updatemode = 1 # prevent non-cataloguer changes

        session.commit()


    def add_authors(self, book):
        if len(book.authors) > 0:
            info("book already has authors.")
            if len(self.authors) == 0:
                return False
            if self.authors is book.authors:
                return False
            warning("replacing existing authors.")
            book.authors[:] = []

        session = self.get_my_session()
        for dc_author in self.authors:
            author = self.get_or_create_author(dc_author.name)
            if hasattr(dc_author, 'birthdate'):
                author.birthdate = dc_author.birthdate
            if hasattr(dc_author, 'deathdate'):
                author.deathdate = dc_author.deathdate
            role_type = session.query(Role).where(
                Role.role == dc_author.role).first()
            if not role_type:
                error("%s is not a valid role.", role_type.role)
                continue
            book.authors.append(BookAuthor(author=author, role_type=role_type))
        return True


    def get_or_create_author(self, name, birthdate=None, deathdate=None):
        ''' look for author in db matching name '''

        def is_good_match(db_str, name):
            ''' make sure we're not matching in the middle of a name '''
            if name not in db_str:
                return False
            [before, after] = db_str.split(name, 1)
            if len(before) > 0 and unicodedata.category(before[-1])[0] == 'L':
                return False
            if len(after) > 0 and unicodedata.category(after[0])[0] == 'L':
                return False
            return True

        session = self.get_my_session()
        like_author = '%%%s%%' % name
        # get an author by matching name
        match_authors = session.query(Author).where(
            Author.name.ilike(like_author)).order_by(Author.id).all()

        for author in match_authors:
            if is_good_match(author.name, name):
                return author

        if len(match_authors) == 0:
            match_aliases = session.query(Alias).where(
                Alias.alias.ilike(like_author)).order_by(Alias.pk).all()

            for alias in match_aliases:
                if is_good_match(alias.alias, name):
                    return alias.author

        # no match in database
        author = Author(name=name, birthdate=birthdate, deathdate=deathdate)
        session.add(author)
        return author


    def add_title(self, book, title, marc=245):
        """ set the appropriate marc attribute.
        book.title gets generated by a database function. """

        if not title:
            error("no title %s found for etext#%s", marc, self.project_gutenberg_id)
            return
        nonfiling = 0
        for nonfiling_str in gg.NONFILINGS:
            if title.startswith(nonfiling_str):
                nonfiling = len(nonfiling_str)
                break
        title = title.replace('--', '—')
        title = title.replace(' *_ *', '\n')
        self.add_attribute(book, title, nonfiling=nonfiling, marc=marc)

    def add_attribute(self, book, attr, nonfiling=0, marc=0):
        if not attr:
            return
        session = self.get_my_session()
        attq = session.query(Attribute).filter_by(book=book, fk_attriblist=marc)
        if isinstance(attr, set):
            attr = list(attr)
        if isinstance(attr, list):
            # append instead of replace
            for text_item in attr:
                if text_item:
                    for att in attq.all():
                        if att.text == text_item:
                            return
                    book.attributes.append(Attribute(
                        fk_attriblist=marc, nonfiling=nonfiling, text=text_item))
        else:
            att = attq.first()
            if att:
                att.nonfiling=nonfiling
                att.text=attr
            else:
                book.attributes.append(Attribute(
                    fk_attriblist=marc, nonfiling=nonfiling, text=attr))

    def delete(self):
        """ only delete the book! """
        session = self.get_my_session()
        if self.book:
            session.delete(self.book)
            session.commit()
            return
        if self.project_gutenberg_id:
            self.book = session.query(Book).filter_by(pk=self.project_gutenberg_id).delete()
            session.commit()
