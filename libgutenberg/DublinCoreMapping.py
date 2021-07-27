#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

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
import os
import re
from sqlalchemy.exc import DBAPIError

from . import DublinCore
from . import GutenbergGlobals as gg
from . import GutenbergDatabase
from .DBUtils import get_lang
from .GutenbergGlobals import Struct, PG_URL
from .Logger import info, warning, error
from .GutenbergDatabase import DatabaseError, IntegrityError, Objectbase
from .Models import Attribute, Book, File, Filetype


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

    def load_from_database(self, ebook, load_files=True):
        def struct(**args):
            s = Struct()
            for key in args:
                setattr(s, key, args[key])
            return s

        """ Load DublinCore from PG database."""
        session = self.get_my_session()
        self.project_gutenberg_id = ebook

        book = session.query(Book).filter_by(pk=ebook).first()
        if not book:
            return
        self.book = book
        if not self.release_date:
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
                info("Title: %s", self.title)

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
        with session.begin_nested():
            session.query(File).filter(File.archive_path == filename).\
                                delete(synchronize_session='fetch')
        session.commit()

    def store_file_in_database(self, id_, filename, type_):
        """ Store file in PG database. """
        session = self.get_my_session()
        encoding = None
        if type_ == 'txt':
            type_ = 'txt.utf-8'
            encoding = 'utf-8'

        try:
            statinfo = os.stat(filename)

            # check good filetype
            if not session.query(Filetype).filter(Filetype.pk == type_).count():
                warning("%s is not a valid filetype, didn't store %s", type_, filename)
                return

            # this introduces a restriction on CACHELOC; should consider deriving the pattern
            filename = re.sub(r'^.*/cache\d?/', 'cache/', filename)
            diskstatus = 0

            # delete existing filename record
            session.query(File).filter(File.archive_path == filename).\
                                delete(synchronize_session='fetch')
            newfile = File(
                fk_books=id_, archive_path=filename,
                extent=statinfo.st_size,
                modified=datetime.datetime.fromtimestamp(statinfo.st_mtime).isoformat(),
                fk_filetypes=type_, fk_encodings=encoding,
                compression=None, diskstatus=diskstatus
            )
            session.add(newfile)
            session.commit()

        except OSError:
            error("Cannot stat %s", filename)

        except IntegrityError:
            error("Book number %s is not in database.", id_)
            self.session.rollback()


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
        if self.book and self.book.updatemode != updatemode:
            warning("ebook #%s not updated, already in database", self.book.pk)
            return
        session = self.get_my_session()
        if not self.book and self.project_gutenberg_id:
            # this has not been loaded from a database so get a book Objectbase
            self.book = session.query(Book).filter_by(pk=self.project_gutenberg_id).first()

            # if updatemode is 1, assume cataloguer knows what they're doing
            if self.book:
                if self.book.updatemode != updatemode:
                    warning("ebook #%s not updated, already in database", self.project_gutenberg_id)
                    return
                self.load_from_database(self.project_gutenberg_id)

            if not self.book:
                # a new book!
                self.book = Book(pk=self.project_gutenberg_id)
                self.add_authors(self.book)
                self.add_title(self.book, self.title)
                if self.alt_title:
                    self.add_title(self.book, self.alt_title, marc=246)
                if self.contents:
                    self.add_title(self.book, self.contents, marc=505)
                for language in self.languages:
                    lang = get_lang(language.id)
                    if lang and lang not in self.book.languages:
                        self.book.languages.append(lang)
                for locc in self.loccs:
                    locc = session.query(Locc).filter_by(locc=locc.locc).first()
                    if locc and locc not in self.book.loccs:
                        self.book.loccs.append(locc)
                for subject in self.subjects:
                    subject = session.query(Subject).filter_by(subject=subject.subject).first()
                    if subject and subject not in self.book.subjects:
                        self.book.subjects.append(subject)
                if self.notes:
                    att = session.query(Attribute).filter_by(book=book, fk_attriblist=500).first()
                    if not att:
                        self.book.attributes.append(Attribute(
                            fk_attriblist=500, nonfiling=nonfiling, text=self.notes))
                    
                self.book.copyrighted = 1 if 'Copyrighted' in self.rights else 0
                for category in self.categories:
                    # It appears that this is dead code
                    category = session.query(Category).filter_by(id=category.id).first()
                    if category and category not in self.book.categories:
                        self.book.categories.append(category)
                self.book.release_date = self.release_date
                
                self.book.updatemode = 1 # prevent non-cataloguer changes

            session.commit()
                        
                        
    def add_authors(self, book):
        if len(book.authors) > 0:
            warning("book already has authors. Not changing it.")
            return False
        session = self.get_my_session()
        for dc_author in self.authors:
            author = get_or_create_author(dc_author.name,
                dc_author.birthdate,
                dc_author.deathdate,)
            role_type = session.execute(select(Role).where(
                Role.role == dc_author.role)).first()
            if not role_type:
                error("%s is not a valid role.", role_type.role)
                continue
            book.authors.append(BookAuthor(author=author, role_type=role_type))
        return True

         
    def get_or_create_author(self, name, birthdate=None, deathdate=None):
        session = self.get_my_session()
        like_author = '%%%s%%' % name
        """ get an author by matching name """
        author = session.query(Author).where(
            Author.name.ilike(like_author)).order_by(Author.id).first()
        if not author:
            author = session.query(Author).join(Alias.author).where(
                Alias.alias.ilike(like_author)).order_by(Alias.fk_authors).first()
        if not author:
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
        session = self.get_my_session()
        att = session.query(Attribute).filter_by(book=book, fk_attriblist=marc).first()
        if att:
            att.nonfiling=nonfiling
            att.text=title
        else:
            self.book.attributes.append(Attribute(
                fk_attriblist=marc, nonfiling=nonfiling, text=title))
        
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
