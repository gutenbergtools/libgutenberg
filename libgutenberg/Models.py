# coding: utf-8
from sqlalchemy import ARRAY, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Table, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

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
        Index('ix_authors_author_born_floor_died_floor', 'author', 'born_floor', 'died_floor', unique=True)
    )

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.authors_pk_seq'::text)::regclass)"))
    author = Column(String(240), nullable=False)
    born_floor = Column(Integer)
    died_floor = Column(Integer)
    born_ceil = Column(Integer)
    died_ceil = Column(Integer)
    note = Column(Text)
    downloads = Column(Integer, nullable=False, index=True, server_default=text("0"))
    release_date = Column(Date, nullable=False, index=True, server_default=text("'1970-01-01'::date"))
    tsvec = Column(TSVECTOR, index=True)


class Book(Base):
    __tablename__ = 'books'
    __table_args__ = (
        Index('ix_books_release_date_pk', 'release_date', 'pk'),
    )

    pk = Column(Integer, primary_key=True)
    copyrighted = Column(Integer, nullable=False, server_default=text("0"))
    updatemode = Column(Integer, nullable=False, server_default=text("0"))
    release_date = Column(Date, nullable=False, index=True, server_default=text("('now'::text)::date"))
    filemask = Column(String(240))
    gutindex = Column(Text)
    downloads = Column(Integer, nullable=False, index=True, server_default=text("0"))
    title = Column(Text, index=True)
    tsvec = Column(TSVECTOR, index=True)
    nonfiling = Column(Integer, nullable=False, server_default=text("0"))

    subjects = relationship('Subject', secondary='mn_books_subjects')
    categories = relationship('Category', secondary='mn_books_categories')
    bookshelves = relationship('Bookshelf', secondary='mn_books_bookshelves')
    loccs = relationship('Locc', secondary='mn_books_loccs')
    langs = relationship('Lang', secondary='mn_books_langs')


class Bookshelf(Base):
    __tablename__ = 'bookshelves'
    __table_args__ = (
        CheckConstraint("bookshelf <> ''::text"),
    )

    pk = Column(Integer, primary_key=True, server_default=text("nextval('bookshelves_pk_seq'::regclass)"))
    bookshelf = Column(Text, nullable=False, unique=True)
    downloads = Column(Integer, nullable=False, index=True, server_default=text("0"))
    release_date = Column(Date, nullable=False, index=True, server_default=text("'1970-01-01'::date"))
    tsvec = Column(TSVECTOR, index=True)


class Category(Base):
    __tablename__ = 'categories'
    __table_args__ = (
        CheckConstraint("(category)::text <> (''::character varying)::text"),
    )

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.categories_pk_seq'::text)::regclass)"))
    category = Column(String(240), nullable=False, unique=True)


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

    pk = Column(Integer, primary_key=True, server_default=text("nextval('dcmitypes_pk_seq'::regclass)"))
    dcmitype = Column(Text)
    description = Column(Text)


class Dpid(Base):
    __tablename__ = 'dpid'

    fk_books = Column(Integer, primary_key=True, nullable=False)
    projectid = Column(Text, primary_key=True, nullable=False)


class Encoding(Base):
    __tablename__ = 'encodings'

    pk = Column(String(20), primary_key=True)
    sortorder = Column(Integer, server_default=text("10"))


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
    sortorder = Column(Integer, server_default=text("10"))
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

    pk = Column(String(10), primary_key=True)
    lang = Column(String(80), nullable=False, unique=True)


class Locc(Base):
    __tablename__ = 'loccs'
    __table_args__ = (
        CheckConstraint("(locc)::text <> (''::character varying)::text"),
    )

    pk = Column(String(10), primary_key=True)
    locc = Column(String(240), nullable=False)


class Mirror(Base):
    __tablename__ = 'mirrors'

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.mirrors_pk_seq'::text)::regclass)"))
    continent = Column(String(80))
    nation = Column(String(80))
    location = Column(String(80))
    provider = Column(String(240), nullable=False)
    url = Column(String(240), nullable=False)
    note = Column(Text)


class Permission(Base):
    __tablename__ = 'permissions'

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.permissions_pk_seq'::text)::regclass)"))
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

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.subjects_pk_seq'::text)::regclass)"))
    subject = Column(String(240), nullable=False, unique=True)
    downloads = Column(Integer, nullable=False, index=True, server_default=text("0"))
    release_date = Column(Date, nullable=False, index=True, server_default=text("'1970-01-01'::date"))
    tsvec = Column(TSVECTOR, index=True)


t_terms = Table(
    'terms', metadata,
    Column('word', Text, index=True),
    Column('ndoc', Integer),
    Column('nentry', Integer)
)


class User(Base):
    __tablename__ = 'users'

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.users_pk_seq'::text)::regclass)"))
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

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.aliases_pk_seq'::text)::regclass)"))
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    alias = Column(String(240))
    alias_heading = Column(Integer, server_default=text("1"))

    author = relationship('Author')


class Attribute(Base):
    __tablename__ = 'attributes'
    __table_args__ = (
        CheckConstraint("text <> ''::text"),
    )

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.attributes_pk_seq'::text)::regclass)"))
    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), nullable=False, index=True)
    fk_attriblist = Column(ForeignKey('attriblist.pk', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    fk_langs = Column(ForeignKey('langs.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    text = Column(Text, nullable=False)
    nonfiling = Column(Integer, nullable=False, server_default=text("0"))
    indicators = Column(String(2), server_default=text("'  '::character varying"))
    tsvec = Column(TSVECTOR, index=True)

    attriblist = relationship('Attriblist')
    book = relationship('Book')
    lang = relationship('Lang')


class AuthorUrl(Base):
    __tablename__ = 'author_urls'

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.author_urls_pk_seq'::text)::regclass)"))
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'), nullable=False)
    description = Column(String(240))
    url = Column(String(240), nullable=False)

    author = relationship('Author')


class File(Base):
    __tablename__ = 'files'

    pk = Column(Integer, primary_key=True, server_default=text("nextval(('public.files_pk_seq'::text)::regclass)"))
    fk_books = Column(ForeignKey('books.pk', ondelete='RESTRICT', onupdate='CASCADE'), index=True)
    fk_filetypes = Column(ForeignKey('filetypes.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    fk_encodings = Column(ForeignKey('encodings.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    fk_compressions = Column(ForeignKey('compressions.pk', ondelete='RESTRICT', onupdate='CASCADE'))
    filename = Column(String(240), nullable=False, unique=True)
    filesize = Column(Integer)
    filemtime = Column(DateTime, index=True)
    diskstatus = Column(Integer, nullable=False, server_default=text("0"))
    obsoleted = Column(Integer, nullable=False, server_default=text("0"))
    edition = Column(Integer)
    md5hash = Column(LargeBinary)
    sha1hash = Column(LargeBinary)
    kzhash = Column(LargeBinary)
    ed2khash = Column(LargeBinary)
    tigertreehash = Column(LargeBinary)
    note = Column(Text)
    download = Column(Integer, server_default=text("0"))

    book = relationship('Book')
    compression = relationship('Compression')
    encoding = relationship('Encoding')
    filetype = relationship('Filetype')


class MnBooksAuthor(Base):
    __tablename__ = 'mn_books_authors'

    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False)
    fk_authors = Column(ForeignKey('authors.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
    fk_roles = Column(ForeignKey('roles.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, server_default=text("'cr'::character varying"))
    heading = Column(Integer, server_default=text("1"))

    author = relationship('Author')
    book = relationship('Book')
    role = relationship('Role')


t_mn_books_bookshelves = Table(
    'mn_books_bookshelves', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_bookshelves', ForeignKey('bookshelves.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
)


t_mn_books_categories = Table(
    'mn_books_categories', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_categories', ForeignKey('categories.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
)


t_mn_books_langs = Table(
    'mn_books_langs', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_langs', ForeignKey('langs.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
)


t_mn_books_loccs = Table(
    'mn_books_loccs', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_loccs', ForeignKey('loccs.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
)


t_mn_books_subjects = Table(
    'mn_books_subjects', metadata,
    Column('fk_books', ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_subjects', ForeignKey('subjects.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False, index=True)
)


t_mn_users_permissions = Table(
    'mn_users_permissions', metadata,
    Column('fk_users', ForeignKey('users.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False),
    Column('fk_permissions', ForeignKey('permissions.pk', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False)
)


class Tweet(Base):
    __tablename__ = 'tweets'

    fk_books = Column(ForeignKey('books.pk', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True, nullable=False)
    time = Column(DateTime(True), nullable=False)
    media = Column(Text, primary_key=True, nullable=False)

    book = relationship('Book')
