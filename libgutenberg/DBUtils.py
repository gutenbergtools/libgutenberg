from sqlalchemy import not_
from sqlalchemy import select
from sqlalchemy.sql import func

from libgutenberg import Models
from libgutenberg import GutenbergDatabase as gdb
from libgutenberg.Logger import info, debug, warning, error, exception


OB = gdb.Objectbase(False)
def check_session(session):
    if session is None:
        session = OB.get_session()
    return session

def ebook_exists(ebook, session=None):
    session = check_session(session)
    ebook = int(ebook)
    try:
        in_db = session.get(Models.Book, ebook)
        
    except Exception:
        exception("Error checking for book.")
        return False

    if in_db:
        return True
    else:
        info("No ebook #%d in database.", ebook)
        return False

def is_not_text(ebook, session=None):
    session = check_session(session)
    return session.query(Models.Book).filter(Models.Book.pk == ebook).first().categories
        
def remove_ebook(ebook, session=None):
    session = check_session(session)
    ebook = int(ebook)
    session.query(Models.Book).where(Models.Book.pk == ebook).delete()
    session.commit()

def remove_author(author, session=None):
    session = check_session(session)
    session.query(Models.Author).where(Models.Author.name == author).delete()
    session.commit()

def author_exists(author, session=None):
    session = check_session(session)
    return session.query(Models.Author).where(Models.Author.name == author).first()
    
def filetype_books(filetype, session=None):
    session = check_session(session)
    return session.execute(select(Models.File.fk_books).where(
            not_(Models.File.archive_path.regexp_match('^cache/')),
            Models.File.fk_filetypes == filetype ,
        ).distinct()).scalars().all()

def get_lang(language, session=None):
    """ get language object from db from Struct or str """
    session = check_session(session)
    lang_id = language if isinstance(language, str) else language.id
    language = language if isinstance(language, str) else language.language
    
    lang = session.get(Models.Lang, language)
    if lang:
        return lang
    # check for the language name
    lang = session.query(Models.Lang).where(Models.Lang.language == language).first()
    return lang
        
def last_ebook(session=None):
    session = check_session(session)
    last = session.execute(select(func.max(Models.Book.pk))).scalars().first()
    debug("Last ebook: #%d" % last)
    return last

def recent_books(interval, session=None):
    session = check_session(session)
    return session.execute(select(Models.File.fk_books).where(
            not_(Models.File.archive_path.regexp_match('^cache/')),
            Models.File.modified >= interval,
        ).distinct()).scalars().all()

def top_books(session=None):
    session = check_session(session)
    return session.execute(select(Models.Book.pk).order_by(
            Models.Book.downloads.desc()).limit(options.top)).scalars().all()
            
