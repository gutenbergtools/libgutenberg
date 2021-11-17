""" functions to manage the Files table in the gutenberg database """

import datetime
import os
import re

from sqlalchemy.exc import OperationalError

from . import DBUtils
from .GutenbergDatabase import IntegrityError
from .Logger import info, warning, error
from .Models import Compression, File, Filetype

FTP   = '/public/ftp/pub/docs/books/gutenberg/'
EXTENSION_ALIASES = {
    'htm': 'html',
    'tif': 'tiff',
    'jpeg': 'jpg',
    'midi': 'mid',
    'epub': 'epub.dp' # hand-crafted
}
FILETYPES = []
ENC_CASES = {"": "us-ascii", "8": "iso-8859-1", "0": "utf-8", "5": "big5"}
COMPRESSIONS = []

def get_filetypes(session=None):
    @DBUtils.managed_session
    def fts(session=None):
        return [ft.pk for ft in session.query(Filetype.pk)]
    global FILETYPES
    if not FILETYPES:
        FILETYPES = fts(session=session)
    return FILETYPES

def get_compressions(session=None):
    @DBUtils.managed_session
    def comps(session=None):
        return [comp.pk for comp in session.query(Compression.pk)]
    global COMPRESSIONS
    if not COMPRESSIONS:
        COMPRESSIONS = comps(session=session)
    return COMPRESSIONS


def guess_filetype(filename):
    """ guesses filetype, encoding from filename only

    needs following hashes:
    usually loaded from the same tables in the database
    $filetypes:    'txt'   => 'Plain text'
    $encodings:    'us-ascii' """

    filetype = enc = None
    base =  ext = ""
    base_after_hyphen = ""

    matches = re.search(r'^(.*)\.(.*)$', filename)
    if matches:
        base = matches.group(1).lower()
        ext  = matches.group(2).lower()

    post10k = re.search(r'^\d{5}(-|$)', base)
    matches = re.search(r"-(.*)$", base)
    if matches:
        base_after_hyphen = matches.group(1)

    # guess filetype from file extension
    ext = EXTENSION_ALIASES.get(ext, ext)

    if ext in get_filetypes():
        filetype = ext
    if re.search(r'[-_]index\.html?$', filename, flags=re.I):
        filetype = "index"
    if re.search(r'readme\.txt$', filename, flags=re.I):
        filetype = "readme"
    if re.search(r'license\.txt$', filename, flags=re.I):
        filetype = "license"
    if re.search(r'page-images', filename, flags=re.I):
        filetype = "pageimages"

    # guess encoding from file name
    if ext == "txt":
        if post10k:
            enc = ENC_CASES.get(base_after_hyphen, enc)
        if enc is None:
            enc = "us-ascii"
            if re.search(r'^8\w.+\d\da?$', base):
                enc = "iso-8859-1"
            if re.search(r'^8\w.+\d\du$', base):
                enc = "utf-8"
    return filetype, enc


def get_diskstatus(id_, filedir, type_):
    """
    diskstatus determines whether a file is included in the listing of files on bibrecord page
    """
    diskstatus = 0

    # hide image files
    if '/%s-' % id_ in filedir:
        if (type_ in {"jpg", "png", "gif", "svg", "css", "xsl"}
                or "/images" in filedir or "/music" in filedir
                or "/files" in filedir or "/primefiles" in filedir):
            diskstatus = 1
    return diskstatus


def get_compression(filename):
    """ compression from filename.ext.zip """
    compression = 'none'

    compression_match = re.search(r"^(.*)\.(.*)$", filename)
    if compression_match and (compression_match.group(2).lower() in get_compressions()):
        compression = compression_match.group(2).lower()
    return compression


def get_obsoleted(filedir):
    return 1 if re.search("old(/|$)", filedir) else 0


@DBUtils.managed_session
def remove_file_from_database(filename, session=None):
    """ Remove file from PG database. """
    filedir, filename_nopath, archivepath = parse_filename(filename)

    session = DBUtils.check_session(session)
    with session.begin_nested():
        session.query(File).filter(File.archive_path == archivepath).\
                            delete(synchronize_session='fetch')
    session.commit()


def parse_filename(filename):
    filedir, filename_nopath = os.path.split(filename)
    filedir = os.path.realpath(filedir)
    # this introduces a restriction on CACHELOC and FTP; should consider deriving the patterns
    filedir = filedir.replace(FTP, '')
    filedir = re.sub(r'^.*/cache\d?/', 'cache/', filedir)
    archive_path = os.path.join(filedir, filename_nopath)
    return filedir, filename_nopath, archive_path


@DBUtils.managed_session
def store_file_in_database(id_, filename, type_, encoding=None, session=None):
    """ Store file in PG database. filename is a file system uri"""

    filedir, filename_nopath, archive_path = parse_filename(filename)

    if type_ == 'txt' and encoding is None:
        type_ = 'txt.utf-8'
        encoding = 'utf-8'
        check_type = False
    else:
        guess_type, guess_enc = guess_filetype(filename)
        type_, check_type = (type_, True) if type_ else (guess_type, False)
        encoding = encoding if encoding else guess_enc

    try:
        statinfo = os.stat(filename)

        # check good filetype if not from guesser
        try:
            if check_type and not session.query(Filetype).filter(Filetype.pk == type_).count():
                warning("%s is not a valid filetype, didn't store %s", type_, filename)
                return
        except OperationalError:
            error("network problem, didn't store %s", filename)
            return

        diskstatus = get_diskstatus(id_, filedir, type_)
        compression = get_compression(filename_nopath)
        obsoleted = get_obsoleted(filedir)

        # delete existing filename record
        session.query(File).filter(File.archive_path == archive_path).\
                            delete(synchronize_session='fetch')
        newfile = File(
            fk_books=id_, archive_path=archive_path,
            extent=statinfo.st_size,
            modified=datetime.datetime.fromtimestamp(statinfo.st_mtime).isoformat(),
            fk_filetypes=type_, fk_encodings=encoding,
            compression=compression, diskstatus=diskstatus, obsoleted=obsoleted
        )
        session.add(newfile)
        session.commit()

    except OSError:
        error("Cannot stat %s", filename)

    except IntegrityError:
        error("Book number %s is not in database.", id_)
        session.rollback()


@DBUtils.managed_session
def count_files(id_, session=None):
    """ count files in PG database. """
    return session.query(File.id).filter_by(fk_books=id_).count()
    