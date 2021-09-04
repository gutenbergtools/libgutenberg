from sqlalchemy import not_
from sqlalchemy import select
from sqlalchemy.sql import func

from libgutenberg import Models
from libgutenberg import GutenbergDatabase as gdb
from libgutenberg.Logger import info, debug, warning, error, exception

if gdb.db_exists:
    OB = gdb.Objectbase(False)
else:
    OB = None

def managed_session(func):
    def sessionize(*args, session=None):
        new_session = session is None
        session = check_session(session)
        result = func(*args, session=session)
        if new_session:
            session.close()
        return result
    return sessionize

def check_session(session):
    if session is None:
        session = OB.get_session()
    return session

@managed_session
def ebook_exists(ebook, session=None):
    ebook = int(ebook)
    try:
        in_db = session.get(Models.Book, ebook)

    except Exception:
        exception("Error checking for book.")
        return False

    if in_db:
        return True
    info("No ebook #%d in database.", ebook)
    return False

@managed_session
def is_not_text(ebook, session=None):
    return session.query(Models.Book).filter(Models.Book.pk == ebook).first().categories

@managed_session
def remove_ebook(ebook, session=None):
    ebook = int(ebook)
    # need to explicitly delete its files because of ON DELETE = 'restrict'
    session.query(Models.File).where(Models.File.fk_books == ebook).delete()
    session.query(Models.Book).where(Models.Book.pk == ebook).delete()
    session.commit()

@managed_session
def remove_author(author, session=None):
    session.query(Models.Author).where(Models.Author.name == author).delete()
    session.commit()

@managed_session
def author_exists(author, session=None):
    return session.query(Models.Author).where(Models.Author.name == author).first()

@managed_session
def filetype_books(filetype, session=None):
    return session.execute(select(Models.File.fk_books).where(
            not_(Models.File.archive_path.regexp_match('^cache/')),
            Models.File.fk_filetypes == filetype ,
        ).distinct()).scalars().all()

@managed_session
def get_lang(language, session=None):
    """ get language object from db from Struct or str """
    language = language if isinstance(language, str) else language.language

    lang = session.get(Models.Lang, language)
    if lang:
        return lang
    # check for the language name
    lang = session.query(Models.Lang).where(Models.Lang.language == language).first()
    return lang

@managed_session
def last_ebook(session=None):
    last = session.execute(select(func.max(Models.Book.pk))).scalars().first()
    debug("Last ebook: #%d" % last)
    return last

@managed_session
def recent_books(interval, session=None):
    return session.execute(select(Models.File.fk_books).where(
            not_(Models.File.archive_path.regexp_match('^cache/')),
            Models.File.modified >= interval,
        ).distinct()).scalars().all()

@managed_session
def top_books(options_top, session=None):
    return session.execute(select(Models.Book.pk).order_by(
            Models.Book.downloads.desc()).limit(options_top)).scalars().all()

