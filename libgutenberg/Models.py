# coding: utf-8

import re

# initially generated by sqlacodegen
from sqlalchemy import (ARRAY, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index,
                        Integer, LargeBinary, String, Table, Text)
from sqlalchemy import text as sqltext
from sqlalchemy.sql.expression import select
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import backref, deferred, relationship, synonym
from sqlalchemy.orm import column_property
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from . import DublinCore
from .GutenbergGlobals import DCIMT

RE_FIRST_AZ = re.compile(r"^[a-z]")
SI_PREFIXES = (
    (1024 ** 3, '%.2f GB'),
    (1024 ** 2, '%.1f MB'),
    (1024,      '%.0f kB'),
    )

Base = declarative_base()
metadata = Base.metadata


class Attriblist(Base):
    __tablename__ = 'attriblist'
    __table_args__ = (
        CheckConstraint("(name)::text <> (''::character varying)::text"),
        CheckConstraint("(type)::text <> (''::character varying)::text")
    )

    pk = Column(Integer, primary_key=True)
    type = Column(String(10), nullable=False)
    name = Column(String(80), nullable=False, unique=True)
    caption = Column(String(40))


class Author(Base):
    __tablename__ = 'authors'
    __table_args__ = (
        CheckConstraint("(author)::text <> (''::character varying)::text"),
        Index('ix_authors_author_born_floor_died_floor', 'author', 'born_floor',
              'died_floor', unique=True)
    )

    id = Column('pk', Integer, primary_key=True,
                server_default=sqltext("nextval(('public.authors_pk_seq'::text)::regclass)"))
    name = Column('author', String(240), nullable=False)
    birthdate = Column('born_floor', Integer)
    deathdate = Column('died_floor', Integer)
    birthdate2 = Column('born_ceil', Integer)
    deathdate2 = Column('died_ceil', Integer)
    note = deferred(Column(Text))
    downloads = deferred(Column(Integer, nullable=False, index=True,
                       server_default=sqltext("0")))
    release_date = deferred(Column(Date, nullable=False, index=True,
                          server_default=sqltext("'1970-01-01'::date")))
    tsvec = deferred(Column(TSVECTOR, index=True))

    aliases = relationship('Alias', back_populates='author', lazy='joined')
    webpages = relationship('AuthorUrl', back_populates='author')
    books = association_proxy('books', 'book')

    @property
    def name_and_dates(self):
        return DublinCore.GutenbergDublinCore.format_author_date(self)

    @property
    def first_lettter(self):
        # used to link to authorlists on new PG site
        first_let_match = RE_FIRST_AZ.search(self.name_and_dates.lower())
        return first_let_match.group(0) if first_let_match else 'other'


class Book(Base):
    __tablename__ = 'books'
    __table_args__ = (
        Index('ix_books_release_date_pk', 'release_date', 'pk'),
    )

    pk = Column(Integer, primary_key=True)
    copyrighted = Column(Integer, nullable=False, server_default=sqltext("0"))
    updatemode = deferred(Column(Integer, nullable=False, server_default=sqltext("0")))
    release_date = Column(Date, nullable=False, index=True,
                          server_default=sqltext("('now'::text)::date"))
    filemask = deferred(Column(String(240)))
    gutindex = deferred(Column(Text))
    downloads = Column(Integer, nullable=False, index=True, server_default=sqltext("0"))
    title = deferred(Column(Text, index=True))
    tsvec = deferred(Column(TSVECTOR, index=True))
    nonfiling = deferred(Column(Integer, nullable=False, server_default=sqltext("0")))

    subjects = relationship('Subject', secondary='mn_books_subjects')
    categories = relationship('Category', secondary='mn_books_categories')
    bookshelves = relationship('Bookshelf', secondary='mn_books_bookshelves')
    loccs = relationship('Locc', secondary='mn_books_loccs')
    langs = relationship('Lang', secondary='mn_books_langs')
    attributes = relationship('Attribute', order_by='Attribute.fk_attriblist')
    authors = relationship('BookAuthor', order_by='BookAuthor.role, BookAuthor.name')
    files = relationship(
        'File', 
        primaryjoin='and_(File.fk_books == Book.pk, File.obsoleted == 0, File.diskstatus == 0)',
        order_by='File.ftsortorder, File.encsortorder, File.fk_filetypes,\
                  File.fk_encodings, File.compression, File.archive_path',
        )
    
    
    #dcmitypes = association_proxy('categories', 'dcmitype')

    @property
    def rights(self):
        if self.copyrighted:
            return 'Copyrighted. Read the copyright notice inside this book for details.'
        return 'Public domain in the USA.'



class Bookshelf(Base):
    __tablename__ = 'bookshelves'
    __table_args__ = (
        CheckConstraint("bookshelf <> ''::text"),
    )

    id = Column('pk', Integer, primary_key=True,
                server_default=sqltext("nextval('bookshelves_pk_seq'::regclass)"))
    bookshelf = Column(Text, nullable=False, unique=True)
    downloads = deferred(Column(Integer, nullable=False, index=True, server_default=sqltext("0")))
    release_date = deferred(Column(Date, nullable=False, index=True,
                          server_default=sqltext("'1970-01-01'::date")))
    tsvec = deferred(Column(TSVECTOR, index=True))


class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = (
        CheckConstraint("(category)::text <> (''::character varying)::text"),
    )
    # corresponds to DublinCore.DCMITYPES
    pk = Column(Integer, nullable=False, primary_key=True,)
    category = Column(String(240), nullable=False, unique=True)

    books = relationship('Book', secondary='mn_books_categories', back_populates="categories")

    # couldn't figure out how to make the db relation work
    @property
    def dcmitype(self):
        return  DublinCore.DCMITYPES[self.pk]

t_changelog = Table(
    'changelog', metadata,
    Column('time', DateTime, index=True),
    Column('login', String(80)),
    Column('sql', Text),
    Column('script', String(240)),
    Index('ix_changelog_login_time', 'login', 'time')
)


class Compression(Base):
    __tablename__ = 'compressions'
    __table_args__ = (
        CheckConstraint("(compression)::text <> (''::character varying)::text"),
    )

    pk = Column(String(10), primary_key=True)
    compression = Column(String(240), nullable=False, unique=True)


class Dcmitype(Base):
    __tablename__ = 'dcmitypes'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval('dcmitypes_pk_seq'::regclass)"))
    dcmitype = Column(Text)
    description = Column(Text)


class Dpid(Base):
    __tablename__ = 'dpid'

    fk_books = Column(Integer, primary_key=True, nullable=False)
    projectid = Column(Text, primary_key=True, nullable=False)


class Encoding(Base):
    __tablename__ = 'encodings'

    pk = Column(String(20), primary_key=True)
    sortorder = Column(Integer, server_default=sqltext("10"))


t_filecount = Table(
    'filecount', metadata,
    Column('count', Integer),
    Column('filename', String)
)


class Filetype(Base):
    __tablename__ = 'filetypes'
    __table_args__ = (
        CheckConstraint("(filetype)::text <> (''::character varying)::text"),
    )

    pk = Column(String(20), primary_key=True)
    filetype = Column(String(240), nullable=False)
    sortorder = Column(Integer, server_default=sqltext("10"))
    mediatype = Column(String(40))
    generated = Column(Boolean)


t_fts = Table(
    'fts', metadata,
    Column('array_to_string', Text)
)


class Lang(Base):
    __tablename__ = 'langs'
    __table_args__ = (
        CheckConstraint("(lang)::text <> (''::character varying)::text"),
    )

    id = Column('pk', String(10), primary_key=True)
    language = Column('lang', String(80), nullable=False, unique=True)


class Locc(Base):
    __tablename__ = 'loccs'
    __table_args__ = (
        CheckConstraint("(locc)::text <> (''::character varying)::text"),
    )

    id = Column('pk', String(10), primary_key=True)
    locc = Column(String(240), nullable=False)


class Mirror(Base):
    __tablename__ = 'mirrors'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.mirrors_pk_seq'::text)::regclass)"))
    continent = Column(String(80))
    nation = Column(String(80))
    location = Column(String(80))
    provider = Column(String(240), nullable=False)
    url = Column(String(240), nullable=False)
    note = Column(Text)


class Permission(Base):
    __tablename__ = 'permissions'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.permissions_pk_seq'::text)::regclass)"))
    permission = Column(String(80))
    note = Column(Text)

    users = relationship('User', secondary='mn_users_permissions')


class Role(Base):
    __tablename__ = 'roles'
    __table_args__ = (
        CheckConstraint("(role)::text <> (''::character varying)::text"),
    )

    pk = Column(String(10), primary_key=True)
    role = Column(String(240), nullable=False, unique=True)



class Subject(Base):
    __tablename__ = 'subjects'
    __table_args__ = (
        CheckConstraint("(subject)::text <> (''::character varying)::text"),
    )

    id = Column('pk', Integer, primary_key=True,
                server_default=sqltext("nextval(('public.subjects_pk_seq'::text)::regclass)"))
    subject = Column(String(240), nullable=False, unique=True)
    downloads = deferred(Column(Integer, nullable=False, index=True, server_default=sqltext("0")))
    release_date = deferred(Column(Date, nullable=False, index=True,
                          server_default=sqltext("'1970-01-01'::date")))
    tsvec = deferred(Column(TSVECTOR, index=True))


t_terms = Table(
    'terms', metadata,
    Column('word', Text, index=True),
    Column('ndoc', Integer),
    Column('nentry', Integer)
)


class User(Base):
    __tablename__ = 'users'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.users_pk_seq'::text)::regclass)"))
    login = Column(String(80))
    password = Column(String(80))
    note = Column(Text)
    user = Column(String(80))


t_v_appserver_books_4 = Table(
    'v_appserver_books_4', metadata,
    Column('pk', Integer),
    Column('title', Text),
    Column('filing', Text),
    Column('release_date', Date),
    Column('downloads', Integer),
    Column('tsvec', TSVECTOR),
    Column('author', ARRAY(String())),
    Column('fk_langs', ARRAY(String())),
    Column('fk_categories', ARRAY(Integer())),
    Column('coverpages', ARRAY(String()))
)


t_v_appserver_books_categories = Table(
    'v_appserver_books_categories', metadata,
    Column('pk', Integer),
    Column('title', Text),
    Column('release_date', Date),
    Column('downloads', Integer),
    Column('category', Boolean)
)


t_v_appserver_books_categories_2 = Table(
    'v_appserver_books_categories_2', metadata,
    Column('pk', Integer),
    Column('title', Text),
    Column('release_date', Date),
    Column('downloads', Integer),
    Column('tsvec', TSVECTOR),
    Column('author', ARRAY(String())),
    Column('fk_categories', ARRAY(Integer()))
)


t_v_appserver_books_categories_3 = Table(
    'v_appserver_books_categories_3', metadata,
    Column('pk', Integer),
    Column('title', Text),
    Column('release_date', Date),
    Column('downloads', Integer),
    Column('tsvec', TSVECTOR),
    Column('author', ARRAY(String())),
    Column('fk_categories', ARRAY(Integer())),
    Column('coverpages', ARRAY(String()))
)


t_v_books = Table(
    'v_books', metadata,
    Column('fk_books', Integer),
    Column('fk_authors', Integer),
    Column('author', String(240)),
    Column('born_floor', Integer),
    Column('born_ceil', Integer),
    Column('died_floor', Integer),
    Column('died_ceil', Integer),
    Column('role', String(240)),
    Column('fk_langs', String(10)),
    Column('lang', String(80)),
    Column('is_audio', Boolean),
    Column('is_music', Boolean),
    Column('title', Text),
    Column('fk_attriblist', Integer),
    Column('filing', Text)
)


t_v_books_authors = Table(
    'v_books_authors', metadata,
    Column('fk_books', Integer),
    Column('fk_authors', Integer),
    Column('author', String(240)),
    Column('heading', Integer),
    Column('born_floor', Integer),
    Column('born_ceil', Integer),
    Column('died_floor', Integer),
    Column('died_ceil', Integer),
    Column('role', String(240))
)


t_v_books_categories = Table(
    'v_books_categories', metadata,
    Column('fk_books', Integer),
    Column('is_audio', Boolean),
    Column('is_music', Boolean)
)


t_v_books_langs = Table(
    'v_books_langs', metadata,
    Column('fk_books', Integer),
    Column('fk_langs', String(10)),
    Column('lang', String(80))
)


class Alias(Base):
    __tablename__ = 'aliases'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.aliases_pk_seq'::text)::regclass)"))
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'),
                        nullable=False)
    alias = Column(String(240))
    heading = Column('alias_heading', Integer, server_default=sqltext("1"))

    author = relationship('Author', back_populates='aliases')


class Attribute(Base):
    __tablename__ = 'attributes'
    __table_args__ = (
        CheckConstraint("text <> ''::text"),
    )

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.attributes_pk_seq'::text)::regclass)"))
    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
                      nullable=False, index=True)
    fk_attriblist = Column(ForeignKey('attriblist.pk', ondelete='RESTRICT', onupdate='CASCADE'),
                           nullable=False)
    fk_langs = Column(ForeignKey('langs.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    text = Column(Text, nullable=False)
    nonfiling = Column(Integer, nullable=False, server_default=sqltext("0"))
    indicators = Column(String(2), server_default=sqltext("'  '::character varying"))
    tsvec = deferred(Column(TSVECTOR, index=True))

    attribute_type = relationship('Attriblist')
    book = relationship('Book', back_populates='attributes')
    lang = relationship('Lang')


class AuthorUrl(Base):
    __tablename__ = 'author_urls'

    pk = Column(Integer, primary_key=True,
                server_default=sqltext("nextval(('public.author_urls_pk_seq'::text)::regclass)"))
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'),
                        nullable=False)
    description = Column(String(240))
    url = Column(String(240), nullable=False)

    author = relationship('Author', back_populates='webpages')


class File(Base):
    __tablename__ = 'files'

    id = Column('pk', Integer, primary_key=True,
                server_default=sqltext("nextval(('public.files_pk_seq'::text)::regclass)"))
    fk_books = Column(ForeignKey('books.pk', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    fk_filetypes = Column(ForeignKey('filetypes.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    fk_encodings = Column(ForeignKey('encodings.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    compression = Column('fk_compressions',
                         ForeignKey('compressions.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    archive_path = Column('filename', String(240), nullable=False, unique=True)
    extent = Column('filesize', Integer)
    modified = Column('filemtime', DateTime, index=True)
    diskstatus = Column(Integer, nullable=False, server_default=sqltext("0"))
    obsoleted = Column(Integer, nullable=False, server_default=sqltext("0"))
    edition = deferred(Column(Integer))
    # drop these columns!
    download = deferred(Column(Integer, server_default=sqltext("0")))

    book = relationship('Book')
    compression_type = relationship('Compression')
    encoding_type = relationship('Encoding')
    file_type = relationship('Filetype', lazy='joined')

    filetype = synonym('fk_filetypes')
    encoding = synonym('fk_encodings')

    ftsortorder = column_property(select([Filetype.sortorder]).where(Filetype.pk == fk_filetypes))
    encsortorder = column_property(select([Encoding.sortorder]).where(Encoding.pk == fk_encodings))

    generated = association_proxy('file_type', 'generated')
    mediatype = association_proxy('file_type', 'mediatype')

    @property
    def hr_extent(self):
        """ Return human readable string of filesize. """
        if self.extent < 0:
            return ''
        for (threshold, format_string) in SI_PREFIXES:
            if self.extent >= threshold:
                return format_string % (float(self.extent) / threshold)
        return '%d B' % self.extent

    @property
    def hr_filetype(self):
        if hasattr(self, '_hr_filetype'):
            return self._hr_filetype
        return self.file_type.filetype if self.fk_filetypes else ''
    
    @hr_filetype.setter
    def hr_filetype(self, value):
        self._hr_filetype = value
    
    
    @property
    def mediatypes(self):
        if self.filetype:
            mts =  [DCIMT(self.file_type.mediatype, self.fk_encodings)]
        else:
            mts = ['application/octet-stream']
        if self.compression == 'zip':
            mts.append(DCIMT('application/zip'))
        return mts



class BookAuthor(Base):
    __tablename__ = 'mn_books_authors'

    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
                      primary_key=True, nullable=False)
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'),
                        primary_key=True, nullable=False, index=True)
    fk_roles = Column(ForeignKey('roles.pk', ondelete='RESTRICT', onupdate='CASCADE'),
                      primary_key=True, nullable=False,
                      server_default=sqltext("'cr'::character varying"))
    heading = Column(Integer, server_default=sqltext("1"))


    # for a list of relator codes see:
    # http://www.loc.gov/loc.terms/relators/
    role_type = relationship('Role', backref=backref("authors", cascade="all"), uselist=False)
    book = relationship(Book, back_populates="authors")
    author = relationship(Author, backref=backref("authorbooks", cascade="all, delete-orphan"), uselist=False)

    marcrel = synonym('fk_roles')
    role = column_property(select([Role.role]).where(Role.pk == fk_roles))
    #role = association_proxy('role_type', 'role')
    name = column_property(select([Author.name]).where(Author.id == fk_authors))
    @property
    def webpages(self):
        return self.author.webpages

    @property
    def aliases(self):
        return self.author.aliases

    def __getattr__(self, name):
        if name in {'id', 'birthdate', 'deathdate', 'birthdate2', 'deathdate2', 'note',
                    'downloads', 'release_date', 'tsvec', 'name_and_dates', 'first_lettter'}:
            return self.author.__getattribute__(name)
        raise AttributeError


t_mn_books_bookshelves = Table(
    'mn_books_bookshelves', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
            primary_key=True, nullable=False),
    Column('fk_bookshelves', ForeignKey('bookshelves.pk', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True, nullable=False, index=True)
)


t_mn_books_categories = Table(
    'mn_books_categories', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True, nullable=False),
    Column('fk_categories', ForeignKey('categories.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False, index=True)
)


t_mn_books_langs = Table(
    'mn_books_langs', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True, nullable=False),
    Column('fk_langs', ForeignKey('langs.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False, index=True)
)


t_mn_books_loccs = Table(
    'mn_books_loccs', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True, nullable=False),
    Column('fk_loccs', ForeignKey('loccs.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False, index=True)
)


t_mn_books_subjects = Table(
    'mn_books_subjects', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True, nullable=False),
    Column('fk_subjects', ForeignKey('subjects.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False, index=True)
)


t_mn_users_permissions = Table(
    'mn_users_permissions', metadata,
    Column('fk_users', ForeignKey('users.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False),
    Column('fk_permissions', ForeignKey('permissions.pk', ondelete='RESTRICT', onupdate='CASCADE'),
           primary_key=True, nullable=False)
)


class Tweet(Base):
    __tablename__ = 'tweets'

    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'),
                      primary_key=True, nullable=False)
    time = Column(DateTime(True), nullable=False)
    media = Column(Text, primary_key=True, nullable=False)

    book = relationship('Book')