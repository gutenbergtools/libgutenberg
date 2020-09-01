import re
import os
import datetime

from sqlalchemy import create_engine  
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import MetaData, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker

try:
    engine = create_engine('postgresql://guser:!G.123@localhost:5432/gutenberg1',echo=False)
    META_DATA = MetaData(bind=engine, reflect=True)
except OSError:
    engine = None
    META_DATA = None
Session = sessionmaker(bind = engine)
session = Session()
# roles=Table('roles', META_DATA, autoload=True, autoload_with=engine)
# authors=Table('authors', META_DATA, autoload=True, autoload_with=engine)
# mn_books_authors=Table('mn_books_authors', META_DATA, autoload=True, autoload_with=engine)
# result=session.query(authors,mn_books_authors,roles).\
#             filter(mn_books_authors.c.fk_authors == authors.c.pk).\
#             filter(mn_books_authors.c.fk_roles == roles.c.pk).\
#             filter(mn_books_authors.c.fk_books==28961).order_by(roles.c.role,authors.c.author)
# print(result.column_descriptions )           
# for book in result[:1]:
#     print(book)
# aliases = Table('aliases', META_DATA, autoload=True,
#                             autoload_with=engine)
# aliases_res = session.query(aliases).\
#                 filter(aliases.c.fk_authors == 1896)
# for i in aliases_res:
#     print(i)
# author_urls = Table('author_urls', META_DATA, autoload=True,
#                     autoload_with=engine)
# url_res = session.query(author_urls).\
#     filter(author_urls.c.fk_authors == 1896)
# for i in url_res:
#     print(i)
# attributes = Table('attributes', META_DATA, autoload=True,
#                    autoload_with=engine)
# attriblist = Table('attriblist', META_DATA, autoload=True,
#                    autoload_with=engine)
# attr_result = session.query(attributes, attriblist).\
#     filter(attributes.c.fk_books == 1896).\
#     filter(attributes.c.fk_attriblist == attriblist.c.pk).\
#     order_by(attriblist.c.name)
# for i in attr_result:
#     print(i)
# langs = Table('langs', META_DATA, autoload=True, autoload_with=engine)
# mn_books_langs = Table('mn_books_langs', META_DATA, autoload=True,
#                        autoload_with=engine)
# lang_res = session.query(langs, mn_books_langs).\
#     filter(langs.c.pk == mn_books_langs.c.fk_langs).\
#     filter(mn_books_langs.c.fk_books == 1896)
# for i in lang_res:
#     print(i)
# mn_books_subjects = Table('mn_books_subjects', META_DATA,
#                           autoload=True, autoload_with=engine)
# subjects = Table('subjects', META_DATA, autoload=True,
#                  autoload_with=engine)
# subject_res = session.query(mn_books_subjects, subjects).\
#     filter(subjects.c.pk == mn_books_subjects.c.fk_subjects).\
#     filter(mn_books_subjects.c.fk_books == 1896)
# for i in subject_res:
#     print(i)
# loccs = Table('loccs', META_DATA, autoload=True, autoload_with=engine)
# mn_books_loccs = Table('mn_books_loccs', META_DATA, autoload=True,
#                        autoload_with=engine)
# dcmitypes = Table('dcmitypes', META_DATA, autoload=True,
#                   autoload_with=engine)
# mn_books_categories = Table('mn_books_categories', META_DATA,
#                             autoload=True, autoload_with=engine)
# print(1)
"""files = Table('files', META_DATA, autoload=True,
              autoload_with=engine)"""
# filetypes = Table('filetypes', META_DATA, autoload=True,
#                   autoload_with=engine)
# encodings = Table('encodings', META_DATA, autoload=True,
#                   autoload_with=engine)
# file_result = session.query(files,filetypes,encodings).\
#     join(filetypes, filetypes.c.pk == files.c.fk_filetypes).\
#     join(encodings, encodings.c.pk == files.c.fk_encodings).\
#     filter(files.c.fk_books == 1897).\
#     filter(files.c.obsoleted == 0).\
#     filter(files.c.diskstatus == 0).\
#     order_by(filetypes.c.sortorder, encodings.c.sortorder,
#              files.c.fk_filetypes, files.c.fk_encodings,
#              files.c.fk_compressions, files.c.filename)
# for i in file_result:
#     print(i)
# books = Table('books', META_DATA, autoload=True,
#               autoload_with=engine)
# session.query(books.c.title).filter(books.c.pk==62264).one()
# session.query(files).filter(files.c.fk_books == 1897).\
#     filter(files.c.fk_filetypes =='txt').delete(synchronize_session=False)
# session.query(files).filter(files.c.fk_books == 30052461).delete(synchronize_session=False)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
Base = automap_base()
Base.prepare(engine, reflect=True)
account=Base.classes.account
# session.add(account(username='aa',password ='tt',email ='434',created_on='Jan-08-1999'))
# session.commit()
# print(re)
print(session.query(account).count())
"""re = session.query(files).filter(files.c.fk_books==241).count()
print(re)
session.add(files(fk_books=241, 
            filename='cache/epub/1897/pg7.rdf',
            filesize=5464, diskstatus=2, obsoleted=0))
files.insert().values(fk_books=241, 
            filename='cache/epub/1897/pg7.rdf',
            filesize=5464, diskstatus=2, obsoleted=0)
re = session.query(files).filter(files.c.fk_books==241).count()
print(re)"""
"""mn_books_bookshelves=Table('mn_books_bookshelves', META_DATA,
                           autoload=True, autoload_with=engine)
bookshelves=Table('bookshelves', META_DATA, autoload=True,
                  autoload_with=engine)
books=Table('books', META_DATA, autoload=True, autoload_with=engine)

# attr_result=session.query(attributes,attriblist).\
#   filter(books.c.pk ==34159).\
#   filter(attributes.c.fk_attriblist == attriblist.c.pk).\
#   order_by(attriblist.c.name)

bookself_result = session.query(bookshelves.c.pk, bookshelves.c.bookshelf)  # .filter(bookshelves.c.pk == 26356)

 Need a list of bookshelves and query each bookshelf for books inside.
 Use bookshelf pk to find all the books in that bookshelves and display

for pk,bookshef in bookself_result:
    print(pk,bookshef)

for book in book_result:
    print("book title and PK")
    print(book.title, book.pk)
    shelf=session.query(bookshelves,mn_books_bookshelves).\
        filter(mn_books_bookshelves.c.fk_bookshelves==bookshelves.c.pk).\
        filter(mn_books_bookshelves.c.fk_books==book.pk)
    print("----------------------------------------")
    for sh in shelf:
        
        print(sh.bookshelf,sh.pk)"""

# result=session.query(mn_books_bookshelves).filter(mn_books_bookshelves.c.fk_bookshelves==76).all()
# for i in result[:10]:
#     print(i)
