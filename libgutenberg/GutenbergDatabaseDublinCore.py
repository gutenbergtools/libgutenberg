#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

GutenbergDatabaseDublinCore.py

Copyright 2009-2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

DublinCore metadata swiss army knife augmented with PG database access.

"""

from __future__ import unicode_literals

import re
import os
import datetime

from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import MetaData, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

from . import DublinCore
from . import GutenbergGlobals as gg
from .GutenbergGlobals import Struct, PG_URL
from .Logger import info, warning, error
from .GutenbergDatabase import xl, DatabaseError, IntegrityError,\
     get_sqlalchemy_url

RE_FIRST_AZ = re.compile(r"^[a-z]")

# make libgutenberg usable without a database connenction
try:
    engine = create_engine(get_sqlalchemy_url(), echo=True)
    META_DATA = MetaData(bind=engine, reflect=True)
except OSError:
    warning('database not configured')
    engine = None
    META_DATA = None


Session = sessionmaker(bind=engine)
session = Session()


class GutenbergDatabaseDublinCore (DublinCore.GutenbergDublinCore):
    """ Augment GutenbergDublinCore class. """

    def __init__(self, pool):
        DublinCore.GutenbergDublinCore.__init__(self)

        self.new_filesystem = False
        self.mediatypes = set()
        self.filetypes = set()
        self.files = []
        self.generated_files = []

        self.pool = pool
        self.marcs = []

    def has_images(self):
        """ Return True if this book has images. """

        for file_ in self.files:
            if file_.filetype and file_.filetype.find('.images') > -1:
                return True
        return False

    def load_from_database(self, ebook):
        """ Load DublinCore from PG database.

        Best method if direct database connection available.

        """
        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        self.project_gutenberg_id = id_ = ebook

        Books = Table('books', META_DATA, autoload=True, autoload_with=engine)
        result = session.query(Books).filter(Books.c.pk == id_)

        for book in result:
            self.release_date = book.release_date
            self.rights = ('Copyrighted. Read the copyright notice\
            inside this book for details.'
                           if book.copyrighted
                           else 'Public domain in the USA.')
            self.downloads = book.downloads

        # authors
        # for a list of relator codes see:
        # http://www.loc.gov/loc.terms/relators/

        roles = Table('roles', META_DATA, autoload=True, autoload_with=engine)
        authors = Table('authors', META_DATA, autoload=True,
                        autoload_with=engine)
        mn_books_authors = Table('mn_books_authors', META_DATA,
                                 autoload=True, autoload_with=engine)
        result = session.query(authors,mn_books_authors,roles).\
            filter(mn_books_authors.c.fk_authors == authors.c.pk).\
            filter(mn_books_authors.c.fk_roles == roles.c.pk).\
            filter(mn_books_authors.c.fk_books == id_).\
            order_by(roles.c.role, authors.c.author)

        for res in result:
            author = Struct()
            author.id = res.pk
            author.name = res.author
            author.marcrel = res.fk_roles
            author.role = res.role
            author.birthdate = res.born_floor
            author.deathdate = res.died_floor
            author.birthdate2 = res.born_ceil
            author.deathdate2 = res.died_ceil
            author.aliases = []
            author.webpages = []
            author.name_and_dates = DublinCore.GutenbergDublinCore.\
                format_author_date(author)

            # used to link to authorlists on new PG site
            first_let_match = RE_FIRST_AZ.search(author.name_and_dates.lower())
            author.first_lettter = first_let_match.\
                group(0) if first_let_match else 'other'

            aliases = Table('aliases', META_DATA, autoload=True,
                            autoload_with=engine)

            aliases_res = session.query(aliases).\
                filter(aliases.c.fk_authors == res.pk)

            for row2 in aliases_res:
                alias = Struct()
                alias.alias = row2.alias
                alias.heading = row2.alias_heading
                author.aliases.append(alias)

            author_urls = Table('author_urls', META_DATA, autoload=True,
                                autoload_with=engine)
            url_res = session.query(author_urls).\
                filter(author_urls.c.fk_authors == res.pk)

            for row2 in url_res:
                webpage = Struct()
                webpage.description = row2.description
                webpage.url = row2.url
                author.webpages.append(webpage)
            self.authors.append(author)

        attributes = Table('attributes', META_DATA, autoload=True,
                           autoload_with=engine)
        attriblist = Table('attriblist', META_DATA, autoload=True,
                           autoload_with=engine)
        attr_result = session.query(attributes, attriblist).\
            filter(attributes.c.fk_books == id_).\
            filter(attributes.c.fk_attriblist == attriblist.c.pk).\
            order_by(attriblist.c.name)
        
        for row in attr_result:
            marc = Struct()
            marc.code = row.name.split(' ')[0]
            marc.text = self.strip_marc_subfields(row.text)
            marc.caption = row.caption
            self.marcs.append(marc)

            if marc.code == '245':
                self.title = marc.text
                self.title_file_as = marc.text[row.nonfiling:]
                self.title_file_as = self.title_file_as[0].upper() +\
                    self.title_file_as[1:]
                info("Title: %s" % self.title)

        # languages (datatype)

        langs = Table('langs', META_DATA, autoload=True, autoload_with=engine)
        mn_books_langs = Table('mn_books_langs', META_DATA, autoload=True,
                               autoload_with=engine)
        lang_res = session.query(langs, mn_books_langs).\
            filter(langs.c.pk == mn_books_langs.c.fk_langs).\
            filter(mn_books_langs.c.fk_books == id_)

        if not lang_res:
            lang_res.append(('en', 'English'))

        for row in lang_res:
            language = Struct()
            language.id = row.pk
            language.language = row.lang
            self.languages.append(language)

        # subjects(vocabulary)

        mn_books_subjects = Table('mn_books_subjects', META_DATA,
                                  autoload=True, autoload_with=engine)
        subjects = Table('subjects', META_DATA, autoload=True,
                         autoload_with=engine)
        subject_res = session.query(mn_books_subjects, subjects).\
            filter(subjects.c.pk == mn_books_subjects.c.fk_subjects).\
            filter(mn_books_subjects.c.fk_books == id_)
        for row in subject_res:
            subject = Struct()
            subject.id = row.pk
            subject.subject = row.subject
            self.subjects.append(subject)

        # bookshelves (PG private vocabulary)

        bookshelves = Table('bookshelves', META_DATA,
                            autoload=True, autoload_with=engine)
        mn_books_bookshelves = Table('mn_books_bookshelves', META_DATA,
                                     autoload=True, autoload_with=engine)
        book_shelf_result = session.query(bookshelves, mn_books_bookshelves).\
            filter(bookshelves.c.pk == mn_books_bookshelves.c.fk_bookshelves).\
            filter(mn_books_bookshelves.c.fk_books == id_)
        for row in book_shelf_result:
            bookshelf = Struct()
            bookshelf.id = row.pk
            bookshelf.bookshelf = row.bookshelf
            self.bookshelves.append(bookshelf)

        # LoCC(vocabulary)

        loccs = Table('loccs', META_DATA, autoload=True, autoload_with=engine)
        mn_books_loccs = Table('mn_books_loccs', META_DATA, autoload=True,
                               autoload_with=engine)
        locc_res = session.query(loccs, mn_books_loccs).\
            filter(loccs.c.pk == mn_books_loccs.c.fk_loccs).\
            filter(mn_books_loccs.c.fk_books == id_)
        for row in locc_res:
            locc = Struct()
            locc.id = row.pk
            locc.locc = row.locc
            self.loccs.append(locc)

        # categories(vocabulary)

        dcmitypes = Table('dcmitypes', META_DATA, autoload=True,
                          autoload_with=engine)
        mn_books_categories = Table('mn_books_categories', META_DATA,
                                    autoload=True, autoload_with=engine)
        dcm_result = session.query(dcmitypes, mn_books_categories).\
            filter(dcmitypes.c.pk == mn_books_categories.c.fk_categories).\
            filter(mn_books_categories.c.fk_categories == id_)
        if not dcm_result:
            dcm_result.append(('Text', 'Text'))

        for row in dcm_result:
            self.categories.append(row.dcmitypes.c.dcmitype)
            dcmitype = Struct()
            dcmitype.id = row.dcmitypes.c.dcmitype
            dcmitype.description = row.dcmitypes.c.description
            self.dcmitypes.append(dcmitype)
        self.load_files_from_database(ebook)

    def load_files_from_database(self, id_):
        """ Load files from PG database.

        Files are not in DublinCore but useful to have here.

        """

        self.new_filesystem = False
        self.mediatypes = set()
        self.filetypes = set()
        self.files = []
        self.generated_files = []

        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        # files(not strictly DublinCore but useful)

        files = Table('files', META_DATA, autoload=True,
                      autoload_with=engine)
        filetypes = Table('filetypes', META_DATA, autoload=True,
                          autoload_with=engine)
        encodings = Table('encodings', META_DATA, autoload=True,
                          autoload_with=engine)
        file_result = session.query(files).\
            join(filetypes.c.pk == files.c.fk_filetypes).\
            join(encodings.c.pk == files.c.fk_encodings).\
            filter(files.c.fk_books == id_).\
            filter(files.c.obsoleted == 0).\
            filter(files.c.diskstatus == 0).\
            order_by(filetypes.c.sortorder, encodings.c.sortorder,
                     files.c.fk_filetypes, files.c.fk_encodings,
                     files.c.fk_compressions, files.c.filename)
        for row in file_result:

            file_ = Struct()
            fn = row.filename
            file_.archive_path = fn

            adir = gg.archive_dir(id_)
            if fn.startswith(adir):
                fn = fn.replace(adir, 'files/%d' % id_)
                self.new_filesystem = True
            # elif fn.startswith ('dirs/%s' % adir):
            #     fn = fn.replace ('dirs/%s' % adir, 'files/%d' % id_)
            #     self.new_filesystem = True
            elif fn.startswith('etext'):
                fn = 'dirs/'+fn

            file_.filename = fn
            file_.url = PG_URL + fn
            file_.id = row.files.c.pk
            file_.extent = row.files.c.filesize
            file_.hr_extent = self.human_readable_size(row.files.c.filesize)
            file_.modified = row.files.c.filemtime
            file_.filetype = row.files.c.fk_filetypes
            file_.hr_filetype = row.filetypes.c.filetype
            file_.encoding = row.files.c.fk_encodings
            file_.compression = row.files.c.fk_compressions
            file_.generated = row.filetypes.c.generated

            if row.filetypes.c.filetype:
                self.filetypes.add(row.filetypes.c.filetype)

            # internet media type (vocabulary)

            file_.mediatypes = [gg.DCIMT(row.filetypes.c.mediatype,
                                         row.files.c.fk_encodings)]
            if file_.compression == 'zip':
                file_.mediatypes.append(gg.DCIMT('application/zip'))

            if file_.generated and not row.files.c.\
                    fk_filetypes.startswith('cover.'):
                file_.url = "%sebooks/%d.%s" % (PG_URL, id_,
                                                row.files.c.fk_filetypes)

            self.files.append(file_)

            if row.mediatype:
                self.mediatypes.add(row.filetypes.c.mediatype)

    def remove_filetype_from_database(self, id_, type_):
        """ Remove filetype from PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()

        files = Table('files', META_DATA, autoload=True,
                      autoload_with=engine).c
        session.query(files).filter(files.fk_books == id_).\
            filter(files.fk_filetypes == type_).delete()
        session.commit()

    def remove_file_from_database(self, filename):
        """ Remove file from PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()

        files = Table('files', META_DATA, autoload=True,
                      autoload_with=engine).c
        session.query(files).filter(files.filename == filename).delete()
        session.commit()

    def store_file_in_database(self, id_, filename, type_):
        """ Store file in PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()
        encoding = None
        if type_ == 'txt':
            type_ = 'txt.utf-8'
            encoding = 'utf-8'

        try:
            statinfo = os.stat(filename)

            filename = re.sub('^.*/cache/', 'cache/', filename)

            filetypes = Table('filetypes', META_DATA, autoload=True,
                              autoload_with=engine).c
            fresult = session.query(filetypes).filter(filetypes.pk == type_)
            for dummy_row in fresult:  # if type_ found
                diskstatus = 0
                # if type_.startswith ('cover'):
                #     diskstatus = 1

                files = Table('files', META_DATA, autoload=True,
                              autoload_with=engine).c
                session.query(files).filter(filetypes.filename == filename).\
                    delete()
                session.commit()
                new_data = files(fk_books=id_, filename=filename,
                                 filesize=statinfo.st_size,
                                 filemtime=datetime.datetime.
                                 fromtimestamp(statinfo.st_mtime).
                                 isoformat(), fk_filetypes=type_,
                                 fk_encodings=encoding, fk_compressions=None,
                                 diskstatus=diskstatus)
                session.add(new_data)
                session.commit()

        except OSError:
            error("Cannot stat %s" % filename)

        except IntegrityError:
            error("Book number %s is not in database." % id_)
            session.rollback()

    def register_coverpage(self, id_, url, code=901):
        """ Register a coverpage for this ebook. """
        engine = create_engine(get_sqlalchemy_url(), echo=True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            attributes = Table('attributes', META_DATA, autoload=True,
                               autoload_with=engine).c
            new_attr = attributes(fk_books=id_, fk_attriblist=code,
                                  text=gg.archive2files(id_, url))
            session.add(new_attr)
            session.commit()

        except IntegrityError:  # Duplicate key
            session.rollback()

        except DatabaseError as what:
            warning("Error updating coverpage in database: %s." % what)
            session.rollback()
