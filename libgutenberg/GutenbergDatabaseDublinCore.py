#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

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

from . import DublinCore
from . import GutenbergGlobals as gg
from .GutenbergGlobals import Struct, PG_URL
from .Logger import debug, info, warning, error
from .GutenbergDatabase import xl, DatabaseError, IntegrityError

RE_FIRST_AZ = re.compile (r"^[a-z]")

class GutenbergDatabaseDublinCore(DublinCore.GutenbergDublinCore):
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

        conn = self.pool.connect()
        c  = conn.cursor()
        c2 = conn.cursor()

        # id, copyright and release date

        self.project_gutenberg_id = id_ = ebook

        c.execute("""
select copyrighted, release_date, downloads from books where pk = %(ebook)s""",
                   {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)
            self.release_date = row.release_date
            self.rights = ('Copyrighted. Read the copyright notice inside this book for details.'
                           if row.copyrighted
                           else 'Public domain in the USA.')
            self.downloads = row.downloads


        # authors
        # for a list of relator codes see:
        # http://www.loc.gov/loc.terms/relators/

        c.execute("""
SELECT authors.pk as pk, author, born_floor, born_ceil, died_floor, died_ceil, fk_roles, role
   FROM mn_books_authors
   JOIN authors ON mn_books_authors.fk_authors = authors.pk
   JOIN roles   ON mn_books_authors.fk_roles   = roles.pk
WHERE mn_books_authors.fk_books = %(ebook)s
ORDER BY role, author""", {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)

            author = Struct()
            author.id             = row.pk
            author.name           = row.author
            author.marcrel        = row.fk_roles
            author.role           = row.role
            author.birthdate      = row.born_floor
            author.deathdate      = row.died_floor
            author.birthdate2     = row.born_ceil
            author.deathdate2     = row.died_ceil
            author.aliases        = []
            author.webpages       = []

            author.name_and_dates = \
                DublinCore.GutenbergDublinCore.format_author_date(author)

            # used to link to authorlists on new PG site
            first_let_match = RE_FIRST_AZ.search(author.name_and_dates.lower())
            author.first_lettter = first_let_match.group(0) if first_let_match  else  'other'

            c2.execute("SELECT alias, alias_heading from aliases where fk_authors = %d"
                        % row.pk)
            for row2 in c2.fetchall():
                row2 = xl(c2, row2)
                alias = Struct()
                alias.alias = row2.alias
                alias.heading = row2.alias_heading
                author.aliases.append(alias)

            c2.execute("""
SELECT description, url from author_urls where fk_authors = %d""" % row.pk)
            for row2 in c2.fetchall():
                row2 = xl(c2, row2)
                webpage = Struct()
                webpage.description = row2.description
                webpage.url = row2.url
                author.webpages.append(webpage)

            self.authors.append(author)


        # titles, notes

        c.execute("""
select attributes.text, attributes.nonfiling,
       attriblist.name, attriblist.caption
  from attributes, attriblist
 where attributes.fk_books = %(ebook)s
   and attributes.fk_attriblist = attriblist.pk
 order by attriblist.name""", {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)

            marc = Struct()
            marc.code = row.name.split(' ')[0]
            marc.text = self.strip_marc_subfields(row.text)
            marc.caption = row.caption
            self.marcs.append(marc)

            if marc.code == '245':
                self.title = marc.text
                self.title_file_as = marc.text[row.nonfiling:]
                self.title_file_as = self.title_file_as[0].upper() + self.title_file_as[1:]


        # languages (datatype)

        c.execute("""
select pk, lang from langs, mn_books_langs
  where langs.pk = mn_books_langs.fk_langs
    and mn_books_langs.fk_books = %(ebook)s""", {'ebook': id_})

        rows = c.fetchall()

        if not rows:
            rows.append(('en', 'English' ) )

        for row in rows:
            row = xl(c, row)
            language = Struct()
            language.id = row.pk
            language.language = row.lang
            self.languages.append(language)


        # subjects (vocabulary)

        c.execute("""
select pk, subject from subjects, mn_books_subjects
  where subjects.pk = mn_books_subjects.fk_subjects
    and mn_books_subjects.fk_books = %(ebook)s""", {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)
            subject = Struct()
            subject.id = row.pk
            subject.subject = row.subject
            self.subjects.append(subject)


        # bookshelves (PG private vocabulary)

        c.execute("""
select pk, bookshelf from bookshelves, mn_books_bookshelves
  where bookshelves.pk = mn_books_bookshelves.fk_bookshelves
    and mn_books_bookshelves.fk_books = %(ebook)s""", {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)
            bookshelf = Struct()
            bookshelf.id = row.pk
            bookshelf.bookshelf = row.bookshelf
            self.bookshelves.append(bookshelf)


        # LoCC (vocabulary)

        c.execute("""
select pk, locc from loccs, mn_books_loccs
  where loccs.pk = mn_books_loccs.fk_loccs
    and mn_books_loccs.fk_books = %(ebook)s""", {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)
            locc = Struct()
            locc.id = row.pk
            locc.locc = row.locc
            self.loccs.append(locc)


        # categories (vocabulary)

        c.execute("""
select dcmitype, description from dcmitypes, mn_books_categories
  where dcmitypes.pk = mn_books_categories.fk_categories
    and fk_books = %(ebook)s""", {'ebook': id_})
        rows = c.fetchall()

        if not rows:
            rows.append(('Text', 'Text') )

        for row in rows:
            row = xl(c, row)
            self.categories.append(row.dcmitype)
            dcmitype = Struct()
            dcmitype.id = row.dcmitype
            dcmitype.description = row.description
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

        conn = self.pool.connect()
        c  = conn.cursor()

        # files (not strictly DublinCore but useful)

        c.execute(
"""select files.pk as pk, filename, filetype, mediatype, filesize, filemtime,
          fk_filetypes, fk_encodings, fk_compressions, generated
from files
  left join filetypes on (files.fk_filetypes = filetypes.pk)
  left join encodings on (files.fk_encodings = encodings.pk)
where fk_books = %(ebook)s
  and obsoleted = 0
  and diskstatus = 0
order by filetypes.sortorder, encodings.sortorder, fk_filetypes,
         fk_encodings, fk_compressions, filename""",  {'ebook': id_})

        for row in c.fetchall():
            row = xl(c, row)

            file_ = Struct()
            fn = row.filename
            file_.archive_path = fn

            adir = gg.archive_dir(id_)
            if fn.startswith(adir):
                fn = fn.replace(adir, 'files/%d' % id_)
                self.new_filesystem = True
            ## elif fn.startswith('dirs/%s' % adir):
            ##     fn = fn.replace('dirs/%s' % adir, 'files/%d' % id_)
            ##     self.new_filesystem = True
            elif fn.startswith('etext'):
                fn = 'dirs/' + fn

            file_.filename    = fn
            file_.url         = PG_URL + fn
            file_.id          = row.pk
            file_.extent      = row.filesize
            file_.hr_extent   = self.human_readable_size(row.filesize)
            file_.modified    = row.filemtime
            file_.filetype    = row.fk_filetypes
            file_.hr_filetype = row.filetype
            file_.encoding    = row.fk_encodings
            file_.compression = row.fk_compressions
            file_.generated   = row.generated

            if row.filetype:
                self.filetypes.add(row.filetype)

            # internet media type (vocabulary)

            file_.mediatypes = [gg.DCIMT(row.mediatype, row.fk_encodings)]
            if file_.compression == 'zip':
                file_.mediatypes.append(gg.DCIMT('application/zip'))

            if file_.generated and not row.fk_filetypes.startswith('cover.'):
                file_.url = "%sebooks/%d.%s" % (PG_URL, id_, row.fk_filetypes)

            self.files.append(file_)

            if row.mediatype:
                self.mediatypes.add(row.mediatype)


    def remove_filetype_from_database(self, id_, type_):
        """ Remove filetype from PG database. """

        conn = self.pool.connect()
        c  = conn.cursor()

        c.execute('start transaction')
        c.execute("""delete from files where
fk_books = %(id)s and
fk_filetypes = %(fk_filetypes)s and
filename ~ '^cache'""",
                   { 'id': id_,
                     'fk_filetypes': type_ })
        c.execute('commit')


    def remove_file_from_database(self, filename):
        """ Remove file from PG database. """

        conn = self.pool.connect()
        c  = conn.cursor()

        c.execute('start transaction')
        c.execute("delete from files where filename = %(filename)s",
                   { 'filename': filename })
        c.execute('commit')


    def store_file_in_database(self, id_, filename, type_):
        """ Store file in PG database. """

        encoding = None
        if type_ == 'txt':
            type_ = 'txt.utf-8'
            encoding = 'utf-8'

        try:
            statinfo = os.stat(filename)

            filename = re.sub('^.*/cache/', 'cache/', filename)

            conn = self.pool.connect()
            c  = conn.cursor()

            c.execute('start transaction')
            c.execute("select * from filetypes where pk = %(type)s", {'type': type_} )

            for dummy_row in c.fetchall(): # if type_ found
                diskstatus = 0
                #if type_.startswith('cover'):
                #    diskstatus = 1

                c.execute("""
delete from files where filename = %(filename)s""",
                           { 'filename': filename,
                             'id': id_,
                             'fk_filetypes': type_ })

                c.execute("""
insert into files (fk_books, filename, filesize, filemtime,
                   fk_filetypes, fk_encodings, fk_compressions, diskstatus)
  values (%(ebook)s, %(filename)s, %(filesize)s, %(filemtime)s,
  %(fk_filetypes)s, %(fk_encodings)s, 'none', %(diskstatus)s)""",
                           {'ebook':        id_,
                            'filename':     filename,
                            'filesize':     statinfo.st_size,
                            'filemtime':    datetime.datetime.fromtimestamp(
                                statinfo.st_mtime).isoformat(),
                            'fk_encodings': encoding,
                            'fk_filetypes': type_,
                            'diskstatus':   diskstatus})

            c.execute('commit')

        except OSError:
            error("Cannot stat %s", filename)

        except IntegrityError:
            error("Book number %s is not in database.", id_)
            c.execute('rollback')


    def register_coverpage(self, id_, url, code = 901):
        """ Register a coverpage for this ebook. """

        conn = self.pool.connect()
        c  = conn.cursor()
        c.execute('commit')

        try:
            c.execute('start transaction')

            c.execute("""
insert into attributes (fk_books, fk_attriblist, text) values (%(ebook)s, %(code)s, %(url)s)""",
                       {'ebook': id_, 'code': code, 'url': gg.archive2files(id_, url)})

            c.execute('commit')

        except IntegrityError: # Duplicate key
            c.execute('rollback')

        except DatabaseError as what:
            warning("Error updating coverpage in database: %s.", what)
            c.execute('rollback')
