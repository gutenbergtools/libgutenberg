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
from .GutenbergGlobals import Struct, PG_URL
from .Logger import info, warning, error
from .GutenbergDatabase import DatabaseError, IntegrityError, Objectbase
from .Models import Attribute, Book, Encoding, File, Filetype


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
        self.release_date = book.release_date
        self.downloads = book.downloads
        self.rights = book.rights

        # authors
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
                info("Title: %s" % self.title)

        # languages (datatype)

        self.languages = book.langs if book.langs else [struct(id='en', language='English')]

        # subjects (vocabulary)

        self.subjects = book.subjects

        # bookshelves (PG private vocabulary)

        self.bookshelves = book.bookshelves

        # LoCC (vocabulary)

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
                order_by(File.ftsortorder, File.encsortorder,File.fk_filetypes,
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
                return

            filename = re.sub('^.*/cache/', 'cache/', filename)
            diskstatus = 0
            session.begin_nested()
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
            error("Cannot stat %s" % filename)

        except IntegrityError:
            error("Book number %s is not in database." % id_)
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
            warning("Error updating coverpage in database: %s." % what)
            session.rollback()
