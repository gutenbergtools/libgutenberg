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
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker

from . import DublinCore
from . import GutenbergGlobals as gg
from .GutenbergGlobals import Struct, PG_URL
from .Logger import info, warning, error
from .GutenbergDatabase import xl, DatabaseError, IntegrityError,get_sqlalchemy_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql
from sqlalchemy import MetaData, Table

RE_FIRST_AZ = re.compile (r"^[a-z]")




class GutenbergDatabaseDublinCore (DublinCore.GutenbergDublinCore):
    """ Augment GutenbergDublinCore class. """

    def __init__ (self, pool):
        DublinCore.GutenbergDublinCore.__init__ (self)

        self.new_filesystem = False
        self.mediatypes = set ()
        self.filetypes = set ()
        self.files = []
        self.generated_files = []

        self.pool = pool
        self.marcs = []


    def has_images (self):
        """ Return True if this book has images. """

        for file_ in self.files:
            if file_.filetype and file_.filetype.find ('.images') > -1:
                return True
        return False


    def load_from_database (self, ebook):
        """ Load DublinCore from PG database.

        Best method if direct database connection available.

        """

        # conn = self.pool.connect ()
        # c  = conn.cursor ()
        # c2 = conn.cursor ()
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
        # id, copyright and release date

        self.project_gutenberg_id = id_ = ebook

#         c.execute ("""
# select copyrighted, release_date, downloads from books where pk = %(ebook)s""",
#                    {'ebook': id_})
        Books=Table('Books', META_DATA, autoload=True, autoload_with=engine)
        result=session.query(Books).filter(Books.c.pk==id_)

        # for row in c.fetchall ():
        #     row = xl (c, row)
        #     self.release_date = row.release_date
        #     self.rights = ('Copyrighted. Read the copyright notice inside this book for details.'
        #                    if row.copyrighted
        #                    else 'Public domain in the USA.')
        #     self.downloads = row.downloads
        for book in result:
            self.release_date=book.release_date
            self.rights=('Copyrighted. Read the copyright notice inside this book for details.'
                           if book.copyrighted
                           else 'Public domain in the USA.')
            self.downloads=book.downloads

        # authors
        # for a list of relator codes see:
        # http://www.loc.gov/loc.terms/relators/

#         c.execute ("""
# SELECT authors.pk as pk, author, born_floor, born_ceil, died_floor, died_ceil, fk_roles, role
#    FROM mn_books_authors
#    JOIN authors ON mn_books_authors.fk_authors = authors.pk
#    JOIN roles   ON mn_books_authors.fk_roles   = roles.pk
# WHERE mn_books_authors.fk_books = %(ebook)s
# ORDER BY role, author""", {'ebook': id_})
        roles=Table('roles', META_DATA, autoload=True, autoload_with=engine)
        authors=Table('authors', META_DATA, autoload=True, autoload_with=engine)
        mn_books_authors=Table('mn_books_authors', META_DATA, autoload=True, autoload_with=engine)
        result=session.query(mn_books_authors).\
            join(authors,mn_books_authors.c.fk_authors == authors.c.pk).\
            join(roles,mn_books_authors.c.fk_roles == roles.c.pk).\
            filter(mn_books_authors.c.fk_books==id_).order_by(roles.c.role,authors.c.author)
        # for row in c.fetchall ():
        #     row = xl (c, row)

        #     author = Struct ()
        #     author.id             = row.pk
        #     author.name           = row.author
        #     author.marcrel        = row.fk_roles
        #     author.role           = row.role
        #     author.birthdate      = row.born_floor
        #     author.deathdate      = row.died_floor
        #     author.birthdate2     = row.born_ceil
        #     author.deathdate2     = row.died_ceil
        #     author.aliases        = []
        #     author.webpages       = []
        for res in result:
            author = Struct ()
            author.id             = res.authors.pk
            author.name           = res.authors.author
            author.marcrel        = res.mn_books_authors.fk_roles
            author.role           = res.roles.role
            author.birthdate      = res.authors.born_floor
            author.deathdate      = res.authors.died_floor
            author.birthdate2     = res.authors.born_ceil
            author.deathdate2     = res.authors.died_ceil
            author.aliases        = []
            author.webpages       = []
            author.name_and_dates = \
                DublinCore.GutenbergDublinCore.format_author_date (author)

            # used to link to authorlists on new PG site
            first_let_match = RE_FIRST_AZ.search (author.name_and_dates.lower ())
            author.first_lettter = first_let_match.group (0) if first_let_match  else  'other'
            
            aliases=Table('aliases', META_DATA, autoload=True, autoload_with=engine)
            # c2.execute ("SELECT alias, alias_heading from aliases where fk_authors = %d"
            #             % row.pk)
            aliases_res=session.query(aliases).filter(aliases.c.fk_authors==res.authors.pk)
            # for row2 in c2.fetchall ():
            #     row2 = xl (c2, row2)
            #     alias = Struct ()
            #     alias.alias = row2.alias
            #     alias.heading = row2.alias_heading
            #     author.aliases.append (alias)
            for row2 in aliases_res:
                alias = Struct ()
                alias.alias = row2.alias
                alias.heading = row2.alias_heading
                author.aliases.append (alias)

#             c2.execute ("""
# SELECT description, url from author_urls where fk_authors = %d""" % row.pk)
            author_urls=Table('author_urls', META_DATA, autoload=True, autoload_with=engine)
            url_res=session.query(author_urls).filter(url_res.c.fk_authors==res.authors.pk)
            # for row2 in c2.fetchall ():
            #     row2 = xl (c2, row2)
            #     webpage = Struct ()
            #     webpage.description = row2.description
            #     webpage.url = row2.url
            #     author.webpages.append (webpage)
            for row2 in url_res:
                webpage = Struct ()
                webpage.description = row2.description
                webpage.url = row2.url
                author.webpages.append (webpage)
            self.authors.append (author)


        # titles, notes

#         c.execute ("""
# select attributes.text, attributes.nonfiling,
#        attriblist.name, attriblist.caption
#   from attributes, attriblist
#  where attributes.fk_books = %(ebook)s
#    and attributes.fk_attriblist = attriblist.pk
#  order by attriblist.name""", {'ebook': id_})
        attributes=Table('attributes', META_DATA, autoload=True, autoload_with=engine)
        attriblist=Table('attriblist', META_DATA, autoload=True, autoload_with=engine)
        attr_result=session.query(attributes,attriblist).\
            filter(attributes.c.fk_books ==id_).\
            filter(attributes.c.fk_attriblist == attriblist.c.pk).\
            order_by(attriblist.c.name)
        for row in attr_result:

            marc = Struct ()
            marc.code = row.attriblist.c.name.split (' ')[0]
            marc.text = self.strip_marc_subfields (row.attributes.c.text)
            marc.caption = row.attriblist.c.caption
            self.marcs.append (marc)

            if marc.code == '245':
                self.title = marc.text
                self.title_file_as = marc.text[row.nonfiling:]
                self.title_file_as = self.title_file_as[0].upper () + self.title_file_as[1:]
                info ("Title: %s" % self.title)


        # languages (datatype)

#         c.execute ("""
# select pk, lang from langs, mn_books_langs
#   where langs.pk = mn_books_langs.fk_langs
#     and mn_books_langs.fk_books = %(ebook)s""", {'ebook': id_})
        langs=Table('langs', META_DATA, autoload=True, autoload_with=engine)
        mn_books_langs=Table('mn_books_langs', META_DATA, autoload=True, autoload_with=engine)
        lang_res=session.query(langs,mn_books_langs).\
            filter(langs.c.pk == mn_books_langs.c.fk_langs).\
            filter(mn_books_langs.c.fk_books ==id_)
        
        #not sure about whether append will work in ORM
        #if not how to modify this?
        if not lang_res:
            lang_res.append ( ('en', 'English' ) )

        for row in lang_res:
            language = Struct ()
            language.id = row.langs.c.pk
            language.language = row.langs.c.lang
            self.languages.append (language)


        # subjects (vocabulary)

#         c.execute ("""
# select pk, subject from subjects, mn_books_subjects
#   where subjects.pk = mn_books_subjects.fk_subjects
#     and mn_books_subjects.fk_books = %(ebook)s""", {'ebook': id_})
        mn_books_subjects=Table('mn_books_subjects', META_DATA, autoload=True, autoload_with=engine)
        subjects=Table('subjects', META_DATA, autoload=True, autoload_with=engine)
        lang_res=session.query(mn_books_subjects,subjects).\
            filter(subjects.c.pk == mn_books_subjects.c.fk_subjects).\
            filter(mn_books_subjects.c.fk_books ==id_)
        for row in lang_res:
            subject = Struct ()
            subject.id = row.subjects.c.pk
            subject.subject = row.subjects.c.subject
            self.subjects.append (subject)


        # bookshelves (PG private vocabulary)

#         c.execute ("""
# select pk, bookshelf from bookshelves, mn_books_bookshelves
#   where bookshelves.pk = mn_books_bookshelves.fk_bookshelves
#     and mn_books_bookshelves.fk_books = %(ebook)s""", {'ebook': id_})
        bookshelves=Table('bookshelves', META_DATA, autoload=True, autoload_with=engine)
        mn_books_bookshelves=Table('mn_books_bookshelves', META_DATA, autoload=True, autoload_with=engine)
        book_shelf_result=session.query(bookshelves,mn_books_bookshelves).\
            filter(bookshelves.c.pk == mn_books_bookshelves.c.fk_bookshelves).\
            filter(mn_books_bookshelves.c.fk_books ==id_)
        for row in book_shelf_result:
            bookshelf = Struct ()
            bookshelf.id = row.bookshelves.c.pk
            bookshelf.bookshelf = row.bookshelves.c.bookshelf
            self.bookshelves.append (bookshelf)


        # LoCC (vocabulary)

#         c.execute ("""
# select pk, locc from loccs, mn_books_loccs
#   where loccs.pk = mn_books_loccs.fk_loccs
#     and mn_books_loccs.fk_books = %(ebook)s""", {'ebook': id_})
        loccs=Table('loccs', META_DATA, autoload=True, autoload_with=engine)
        mn_books_loccs=Table('mn_books_loccs', META_DATA, autoload=True, autoload_with=engine)
        locc_res=session.query(loccs,mn_books_loccs).\
            filter(loccs.c.pk == mn_books_loccs.c.fk_loccs).\
            filter(mn_books_loccs.c.fk_books  ==id_)
        for row in locc_res:
            locc = Struct ()
            locc.id = row.loccs.c.pk
            locc.locc = row.loccs.c.locc
            self.loccs.append (locc)


        # categories (vocabulary)

#         c.execute ("""
# select dcmitype, description from dcmitypes, mn_books_categories
#   where dcmitypes.pk = mn_books_categories.fk_categories
#     and fk_books = %(ebook)s""", {'ebook': id_})
        dcmitypes=Table('dcmitypes', META_DATA, autoload=True, autoload_with=engine)
        mn_books_categories=Table('mn_books_categories', META_DATA, autoload=True, autoload_with=engine)
        dcm_result=session.query(dcmitypes,mn_books_categories).\
            filter(dcmitypes.c.pk == mn_books_categories.c.fk_categories).\
            filter(mn_books_categories.c.fk_categories==id_)
        if not dcm_result:
            dcm_result.append ( ('Text', 'Text') )

        for row in dcm_result:
            self.categories.append (row.dcmitypes.c.dcmitype)
            dcmitype = Struct ()
            dcmitype.id = row.dcmitypes.c.dcmitype
            dcmitype.description = row.dcmitypes.c.description
            self.dcmitypes.append (dcmitype)

        self.load_files_from_database (ebook)


    def load_files_from_database (self, id_):
        """ Load files from PG database.

        Files are not in DublinCore but useful to have here.

        """

        self.new_filesystem = False
        self.mediatypes = set ()
        self.filetypes = set ()
        self.files = []
        self.generated_files = []

        # conn = self.pool.connect ()
        # c  = conn.cursor ()
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
        # files (not strictly DublinCore but useful)

#         c.execute (
# """select files.pk as pk, filename, filetype, mediatype, filesize, filemtime,
#           fk_filetypes, fk_encodings, fk_compressions, generated
# from files
#   left join filetypes on (files.fk_filetypes = filetypes.pk)
#   left join encodings on (files.fk_encodings = encodings.pk)
# where fk_books = %(ebook)s
#   and obsoleted = 0
#   and diskstatus = 0
# order by filetypes.sortorder, encodings.sortorder, fk_filetypes,
#          fk_encodings, fk_compressions, filename""",  {'ebook': id_})
        files=Table('files', META_DATA, autoload=True, autoload_with=engine)
        filetypes=Table('filetypes', META_DATA, autoload=True, autoload_with=engine)
        encodings=Table('encodings', META_DATA, autoload=True, autoload_with=engine)
        file_result=session.query(files).\
            join(filetypes.c.pk == files.c.fk_filetypes).\
            join(encodings.c.pk==files.c.fk_encodings).\
            filter(files.c.fk_books==id_).\
            filter(files.c.obsoleted==0).\
            filter(files.c.diskstatus==0).\
            order_by(filetypes.c.sortorder, encodings.c.sortorder, files.c.fk_filetypes,\
                files.c.fk_encodings, files.c.fk_compressions, files.c.filename)
        for row in file_result:

            file_ = Struct ()
            fn = row.filename
            file_.archive_path = fn

            adir = gg.archive_dir (id_)
            if fn.startswith (adir):
                fn = fn.replace (adir, 'files/%d' % id_)
                self.new_filesystem = True
            ## elif fn.startswith ('dirs/%s' % adir):
            ##     fn = fn.replace ('dirs/%s' % adir, 'files/%d' % id_)
            ##     self.new_filesystem = True
            elif fn.startswith ('etext'):
                fn = 'dirs/' + fn

            file_.filename    = fn
            file_.url         = PG_URL + fn
            file_.id          = row.files.c.pk
            file_.extent      = row.files.c.filesize
            file_.hr_extent   = self.human_readable_size (row.files.c.filesize)
            file_.modified    = row.files.c.filemtime
            file_.filetype    = row.files.c.fk_filetypes
            file_.hr_filetype = row.filetypes.c.filetype
            file_.encoding    = row.files.c.fk_encodings
            file_.compression = row.files.c.fk_compressions
            file_.generated   = row.filetypes.c.generated

            if row.filetypes.c.filetype:
                self.filetypes.add (row.filetypes.c.filetype)

            # internet media type (vocabulary)

            file_.mediatypes = [gg.DCIMT (row.filetypes.c.mediatype, row.files.c.fk_encodings)]
            if file_.compression == 'zip':
                file_.mediatypes.append (gg.DCIMT ('application/zip'))

            if file_.generated and not row.files.c.fk_filetypes.startswith ('cover.'):
                file_.url = "%sebooks/%d.%s" % (PG_URL, id_, row.files.c.fk_filetypes)

            self.files.append (file_)

            if row.mediatype:
                self.mediatypes.add (row.filetypes.c.mediatype)


    def remove_filetype_from_database (self, id_, type_):
        """ Remove filetype from PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
#         conn = self.pool.connect ()
#         c  = conn.cursor ()

#         c.execute ('start transaction')
#         c.execute ("""delete from files where
# fk_books = %(id)s and
# fk_filetypes = %(fk_filetypes)s and
# filename ~ '^cache'""",
#                    { 'id': id_,
#                      'fk_filetypes': type_ })
#         c.execute ('commit')
        files=Table('files', META_DATA, autoload=True, autoload_with=engine).c
        session.query(files).filter(files.fk_books==id_).filter(files.fk_filetypes==type_).delete()
        session.commit()


    def remove_file_from_database (self, filename):
        """ Remove file from PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
        # conn = self.pool.connect ()
        # c  = conn.cursor ()

        # c.execute ('start transaction')
        # c.execute ("delete from files where filename = %(filename)s",
        #            { 'filename': filename })
        # c.execute ('commit')
        files=Table('files', META_DATA, autoload=True, autoload_with=engine).c
        session.query(files).filter(files.filename==filename).delete()
        session.commit()


    def store_file_in_database (self, id_, filename, type_):
        """ Store file in PG database. """
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
        encoding = None
        if type_ == 'txt':
            type_ = 'txt.utf-8'
            encoding = 'utf-8'

        try:
            statinfo = os.stat (filename)

            filename = re.sub ('^.*/cache/', 'cache/', filename)

            # conn = self.pool.connect ()
            # c  = conn.cursor ()

            # c.execute ('start transaction')
            # c.execute ("select * from filetypes where pk = %(type)s", {'type': type_} )
            filetypes=Table('filetypes', META_DATA, autoload=True, autoload_with=engine).c
            fresult=session.query(filetypes).filter(filetypes.pk==type_)
            for dummy_row in fresult: # if type_ found
                diskstatus = 0
                #if type_.startswith ('cover'):
                #    diskstatus = 1

#                 c.execute ("""
# delete from files where filename = %(filename)s""",
#                            { 'filename': filename,
#                              'id': id_,
#                              'fk_filetypes': type_ })
                files=Table('files', META_DATA, autoload=True, autoload_with=engine).c
                session.query(files).filter(filetypes.filename==filename).delete()
                session.commit()
                #files=Table('files', META_DATA, autoload=True, autoload_with=engine)
                new_data=files(fk_books=id_, filename=filename, filesize=statinfo.st_size, filemtime=datetime.datetime.fromtimestamp (
                                statinfo.st_mtime).isoformat (),
                   fk_filetypes=type_, fk_encodings=encoding, fk_compressions=None, diskstatus=diskstatus)
                session.add(new_data)
                session.commit()
#                 c.execute ("""
# insert into files (fk_books, filename, filesize, filemtime,
#                    fk_filetypes, fk_encodings, fk_compressions, diskstatus)
#   values (%(ebook)s, %(filename)s, %(filesize)s, %(filemtime)s,
#   %(fk_filetypes)s, %(fk_encodings)s, 'none', %(diskstatus)s)""",
#                            {'ebook':        id_,
#                             'filename':     filename,
#                             'filesize':     statinfo.st_size,
#                             'filemtime':    datetime.datetime.fromtimestamp (
#                                 statinfo.st_mtime).isoformat (),
#                             'fk_encodings': encoding,
#                             'fk_filetypes': type_,
#                             'diskstatus':   diskstatus})

#             c.execute ('commit')

        except OSError:
            error ("Cannot stat %s" % filename)

        except IntegrityError:
            error ("Book number %s is not in database." % id_)
            #c.execute ('rollback')
            session.rollback()


    def register_coverpage (self, id_, url, code = 901):
        """ Register a coverpage for this ebook. """
        engine = create_engine(get_sqlalchemy_url(), echo = True)
        META_DATA = MetaData(bind=engine, reflect=True)
        Session = sessionmaker(bind = engine)
        session = Session()
        #conn = self.pool.connect ()
        #c  = conn.cursor ()
        #c.execute ('commit')

        try:
            #c.execute ('start transaction')
            attributes=Table('attributes', META_DATA, autoload=True, autoload_with=engine).c
            new_attr=attributes(fk_books=id_, fk_attriblist=code, text=gg.archive2files (id_, url))
            session.add(new_attr)
#             c.execute ("""
# insert into attributes (fk_books, fk_attriblist, text) values (%(ebook)s, %(code)s, %(url)s)""",
#                        {'ebook': id_, 'code': code, 'url': gg.archive2files (id_, url)})

            session.commit()

        except IntegrityError: # Duplicate key
            session.rollback()

        except DatabaseError as what:
            warning ("Error updating coverpage in database: %s." % what)
            session.rollback()
