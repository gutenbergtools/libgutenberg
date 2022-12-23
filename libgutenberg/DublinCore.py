#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

DublinCore.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

DublinCore metadata swiss army knife.

"""

from __future__ import unicode_literals

import datetime
import json
import re
import textwrap
import unicodedata
from gettext import gettext as _

import six
import lxml
from lxml.builder import ElementMaker

import pycountry

from . import GutenbergGlobals as gg
from .GutenbergGlobals import NS, Struct, xpath, ROLES
from .Logger import critical, debug, error, exception, info, warning



DCMITYPES = [
    ("Text","Text"),
    ("Sound","Sound"),
    ("Sound","Sound"),
    ("Sound","Sound"),
    ("Image","Image"),
    ("StillImage","Still Image"),
    ("Sound","Sound"),
    ("MovingImage","Moving Image"),
    ("Dataset","Data Set"),
    ("Collection","Collection")
]
title_splitter = re.compile(r'[\r\n:]+', flags=re.M)

class _HTML_Writer(object):
    """ Write metadata suitable for inclusion in HTML.

    Build a <meta> or <link> element and
    add it to self.metadata.

    """

    def __init__(self):
        self.metadata = [
            ElementMaker().link(rel="schema.dc", href="http://purl.org/dc/elements/1.1/"),
            ElementMaker().link(rel="schema.dcterms", href="http://purl.org/dc/terms/"),
        ]

    @staticmethod
    def _what(what):
        """ Transform DCTERMS:title to dcterms.title. """
        what = str(what).split(':')
        what[0] = what[0].lower()
        return '.'.join(what)

    def literal(self, what, literal, scheme = None):
        """ Write <meta name=what content=literal scheme=scheme> """
        if literal is None:
            return
        literal = re.sub(r'\s*[\r\n]+\s*', '&#10;', literal)
        params = {'name' : self._what(what), 'content': literal}
        self.metadata.append(ElementMaker().meta(**params))

    def uri(self, what, uri):
        """ Write <link rel=what href=uri> """
        if uri is None:
            return
        self.metadata.append(ElementMaker().link(
                rel = self._what(what), href = str(uri)))

class PubInfo(object):
    def __init__(self):
        self.publisher = ''
        self.years = []  #  list of (event_type, year)
        self.country = ''

    def __str__(self):
        info_str = ''
        if self.country:
            info_str += self.country + ': '
        if self.publisher:
            info_str += self.publisher
        if self.years:
            info_str += ', ' + self.first_year
        info_str = info_str.strip()
        return '' if info_str == '()' else info_str

    def __bool__(self):
        return bool(self.publisher or self.years or self.country)

    @property
    def first_year(self):
        if len(self.years) > 1:
            try:
                self.years.sort(key=lambda x: int(x[1]))
                return self.years[0][1]
            except ValueError:
                pass
        return self.years[0][1] if self.years else ''

    def marc(self):
        subc = ''
        if self.first_year:     #guarantees sort
            subc += self.years[0][1]
            for year in self.years[1:]:
                subc += ',%s %s' % year
        if self.country:
            country = pycountry.countries.get(alpha_2=self.country)
            country = country.name if country else self.country
        else:
            country = ''
        info_str = ('$a' + country + ' :') if country else ''
        if self.publisher:
            info_str += '$b' + self.publisher + ','
        if subc:
            info_str += '$c' + subc
        info_str = '  ' + info_str.strip(' ,:') + '.'
        return '' if info_str == '  .' else info_str


# file extension we hope to be able to parse
PARSEABLE_EXTENSIONS = 'txt html htm tex tei xml'.split()

RE_MARC_SUBFIELD = re.compile(r"\$[a-z]")
RE_MARC_SPSEP = re.compile(r"[\n ](,|:)([A-Za-z0-9])")
RE_UPDATE = re.compile(r'\s*updated?:\s*', re.I)


class DublinCore(object):
    """ Hold DublinCore attributes.

    Read and output them in various formats.

    """

    SI_prefixes = (
        (1024 ** 3, '%.2f GB'),
        (1024 ** 2, '%.1f MB'),
        (1024,      '%.0f kB'),
        )

    # load local role map as default
    role_map = ROLES
    inverse_role_map = {v.lower(): k for k, v in ROLES.items()}

    # load local language map as default
    language_map = gg.language_map


    def __init__(self):
        self.title = 'No title'
        self.alt_title = None
        self.title_file_as = self.title
        self.source = None
        self.languages = []
        self.created = None
        self.publisher = None
        self.rights = None
        self.authors = []
        self.subjects = []
        self.bookshelves = []
        self.loccs = []
        self.categories = []
        self.dcmitypes = [] # similar to categories but based on the DCMIType vocabulary
        self.release_date = datetime.date.min  # valid date for SQL, must not test for null!
        self.edition = None
        self.contents = None
        self.encoding = None
        self.notes = None
        self.downloads = 0
        self.score = 1
        self.credit = ''
        self.pubinfo = PubInfo()


    @staticmethod
    def format_author_date(author):
        """ Format: Twain, Mark, 1835-1910 """

        def format_dates(d1, d2):
            """ Format dates """
            # Hack to display 9999? if only d2 is set
            if d2 and not d1:
                if d2 < 0:
                    return "%d? BCE" % abs(d2)
                return "%d?" % d2
            if not d1:
                return ''
            if d2 and d1 != d2:
                d3 = max(d1, d2)
                if d3 < 0:
                    return "%d? BCE" % abs(d3)
                return "%d?" % d3
            if d1 < 0:
                return "%d BCE" % abs(d1)
            return str(d1)

        born = format_dates(author.birthdate, author.birthdate2)
        died = format_dates(author.deathdate, author.deathdate2)
        name = gg.normalize(author.name)

        if born or died:
            return "%s, %s-%s" % (name, born, died)

        return name


    @staticmethod
    def format_author_date_role(author):
        """ Format: Twain, Mark, 1835-1910 [Editor] """
        name = DublinCore.format_author_date(author)
        if author.marcrel not in ('cre', 'aut'):
            return "%s [%s]" % (name, _(author.role))
        return name


    @staticmethod
    def strip_marc_subfields(s):
        """ Strip MARC subfield markers. ($b) etc. """
        s = RE_MARC_SUBFIELD.sub('', s)
        s = RE_MARC_SPSEP.sub(r'\1 \2', s) # move space to behind the separator
        return s.strip()


    @staticmethod
    def make_pretty_name(name):
        """ Reverse author name components """
        rev = ' '.join(reversed(name.split(', ')))
        rev = re.sub(r'\(.*\)', '', rev)
        rev = re.sub(r'\s+', ' ', rev)
        return rev.strip()


    @staticmethod
    def strunk(list_):
        """ Join a list of terms with appropriate use of ',' and 'and'.

        Tom, Dick, and Harry

        """
        if len(list_) > 2:
            list_ = (', '.join(list_[:-1]) + ',', list_[-1])
        return _(' and ').join(list_)


    def human_readable_size(self, size):
        """ Return human readable string of filesize. """
        if size < 0:
            return ''
        for (threshold, format_string) in self.SI_prefixes:
            if size >= threshold:
                return format_string % (float(size) / threshold)
        return '%d B' % size


    def make_pretty_title(self, size = 80, cut_nonfiling = False):
        """ Generate a pretty title for ebook. """

        def cutoff(title, size):
            """ Cut string off after size characters. """
            return textwrap.wrap(title, size)[0]

        title = self.title_file_as if cut_nonfiling else self.title

        title = title.splitlines()[0]
        title = re.sub(r'\s*\$[a-z].*', '', title) # cut before first MARC subfield

        title_len = len(title)
        if title_len > size or not self.authors:
            return cutoff(title, size)

        creators = [author for author in self.authors if author.marcrel in ('aut', 'cre')]
        if not creators:
            creators = self.authors
        if not creators:
            return cutoff(title, size)

        fullnames = [self.make_pretty_name(author.name) for author in creators]
        surnames  = [author.name.split(', ')[0] for author in creators]

        for tail in (self.strunk(fullnames), self.strunk(surnames)):
            if len(tail) + title_len < size:
                return _('{title} by {authors}').format(title = title, authors = tail)

        for tail in (fullnames[0], surnames[0]):
            if len(tail) + title_len < size:
                return _('{title} by {authors} et al.').format(title = title, authors = tail)

        return cutoff(title, size)


    def feed_to_writer(self, writer):
        """ Pipe metadata into writer. """
        lit = writer.literal
        # uri = writer.uri

        lit('dc:title',      self.title)

        for language in self.languages:
            lit('dc:language', language.id, 'dcterms:RFC4646')

        lit('dcterms:source',     self.source)
        lit('dcterms:modified',
             datetime.datetime.now(gg.UTC()).isoformat(),
             'dcterms:W3CDTF')


    def to_html(self):
        """ Return a <html:head> element with DC metadata. """

        w = _HTML_Writer()
        self.feed_to_writer(w)

        e = ElementMaker()

        head = e.head(
            *w.metadata
            )

        return head

    def append_lang(self, lang):
        self.languages.append(lang)

    def add_lang_id(self, lang_id):
        """ Add language from language id. """
        language = Struct()
        language.id = lang_id
        language.language = self.language_map.get(lang_id)
        self.append_lang(language)


    def add_author(self, name, marcrel = 'cre'):
        """ Add author. """
        try:
            role = self.role_map[marcrel]
        except KeyError:
            return

        # debug("%s: %s" % (role, names))

        # lowercase De Le La
        for i in 'De Le La'.split():
            name = re.sub(r'\b%s\b' % i, i.lower(), name)

        name = name.replace('\\', '')   # remove \ (escape char in RST)
        name = re.sub(r'\s\s+', ' ', name)
        name = re.sub(r'\s*,\s*,', ',', name)
        name = re.sub(r',+', ',', name)
        name = name.replace(',M.D.', '')

        name = re.sub(r'\s*\[.*?\]\s*', ' ', name) # [pseud.]
        name = name.strip()
        if len(name) == 0:
            return

        # lastname, firstname middlename
        if ',' not in name:
            m = re.match(r'^(.+?)\s+([-\'\w]+)$', name, re.I)
            if m:
                name = "%s, %s" % (m.group(2), m.group(1))

        author = Struct()
        author.name = name
        author.marcrel = marcrel
        author.role = role
        author.name_and_dates = name
        self.authors.append(author)


    def add_credit(self, new_credit):
        ''' the updates field can contain both a production credit and update notations.
            Updates need to be more sophisticated - updates can be added, credits are singular.
        '''
        if not new_credit:
            return
        new_credit = new_credit.strip()
        if not self.credit:
            self.credit = new_credit
            return

        # parse out updates
        updates_in_dc = RE_UPDATE.split(self.credit)[1:]
        credit_in_dc = RE_UPDATE.split(self.credit)[0].strip()
        new_updates = RE_UPDATE.split(new_credit)[1:]
        new_credit = RE_UPDATE.split(new_credit)[0].strip()
        credit = credit_in_dc or new_credit
        credit = credit if credit else ''
        updates = set()
        for update in (new_updates + updates_in_dc):
            update = update.strip(' \n\r\t.;')
            if update and update not in updates:
                updates.add(update)
                credit = credit + '\nUpdated: ' + update + '.'
        self.credit = credit


    def load_from_parser(self, parser):
        """ Load Dublincore from html header. """

        # print(lxml.etree.tostring(parser.xhtml))
        try:
            for meta in xpath(parser.xhtml, "//xhtml:meta[@name='DC.Creator']"):
                author = Struct()
                author.name = gg.normalize(meta.get('content'))
                author.marcrel = 'cre'
                author.role = 'creator'
                author.name_and_dates = author.name
                self.authors.append(author)

            for meta in xpath(parser.xhtml, "//xhtml:meta[@name='DC.Contributor']"):
                author = Struct()
                author.name = gg.normalize(meta.get('content'))
                author.marcrel = 'ctb'
                author.role = 'contributor'
                author.name_and_dates = author.name
                self.authors.append(author)

            for title in xpath(parser.xhtml, "//xhtml:title"):
                self.title = self.title_file_as = gg.normalize(title.text)

            # DC.Title overrides <title>
            for meta in xpath(parser.xhtml, "//xhtml:meta[@name='DC.Title']"):
                self.title = self.title_file_as = gg.normalize(meta.get('content'))

            for elem in xpath(parser.xhtml, "/xhtml:html[@xml:lang]"):
                self.add_lang_id(elem.get(NS.xml.lang))
            if not self.languages:
                for elem in xpath(parser.xhtml, "/*[@lang]"):
                    self.add_lang_id(elem.get('lang'))

            for meta in xpath(parser.xhtml, "//xhtml:meta[@name='DC.Created']"):
                self.created = gg.normalize(meta.get('content'))

        except Exception as what:
            exception(what)

    def split_title(self):
        if not self.title:
            return ['', '']
        title = title_splitter.split(self.title, maxsplit=1)
        return title if len(title) > 1 else [title[0], '']

    @property
    def subtitle(self):
        return self.split_title()[1]

    @property
    def title_no_subtitle(self):
        return self.split_title()[0]

    # as you'd expect to see the names on a cover, last names last.
    def authors_short(self):
        num_auths = 0
        creators = []
        for author in self.authors:
            if author.marcrel in ('aut', 'cre', 'edt'):
                num_auths += 1
                creators.append(author)
        if num_auths == 1:
            return DublinCore.make_pretty_name(creators[0].name)
        if num_auths == 2:
            names = "%s and %s" % (
                DublinCore.make_pretty_name(creators[0].name),
                DublinCore.make_pretty_name(creators[1].name)
            )
            return names
        if num_auths > 2:
            return "%s et al." % DublinCore.make_pretty_name(creators[0].name)
        return ''


def handle_dc_languages(dc, text):
    """ Scan Language: line """
    reset = False
    text = text.replace(' and ', ',')
    for lang in text.lower().split(','):
        lang = lang.strip()
        if lang:
            try:
                language = Struct()
                # if language name not in our table, just keep it.
                language.id = dc.language_map.inverse(lang, default=lang)
                language.language = lang.title()
                if not reset:
                    dc.languages = []
                    reset = True
                try:
                    dc.append_lang(language)
                except ValueError:
                    error('could not use language %s', language)
            except KeyError:
                pass


class GutenbergDublinCore(DublinCore):
    """ Parse from PG files. """

    def __init__(self):
        DublinCore.__init__(self)
        self.project_gutenberg_title = None
        self.is_format_of = None
        self._project_gutenberg_id = None
        self.request_key = ''
        self.scan_urls = set()



    @property
    def project_gutenberg_id(self):
        return self._project_gutenberg_id

    @project_gutenberg_id.setter
    def project_gutenberg_id(self, ebook):
        try:
            self._project_gutenberg_id = int(ebook)
        except (ValueError, TypeError):
            self._project_gutenberg_id = 0
        self.is_format_of = str(NS.ebook) + str(ebook)
        self.canonical_url = re.sub(r'^http:', 'https:', self.is_format_of) + '/'


    def feed_to_writer(self, writer):
        """ Pipe metadata into writer. """

        DublinCore.feed_to_writer(self, writer)

        lit = writer.literal
        uri = writer.uri

        lit('dc:publisher',  self.publisher)
        lit('dc:rights',     self.rights)
        uri('dcterms:isFormatOf', self.is_format_of)

        for author in self.authors:
            if author.marcrel in ('aut', 'cre'):
                lit('dc:creator', author.name_and_dates)
            else:
                lit('marcrel:' + author.marcrel, author.name_and_dates)

        for subject in self.subjects:
            lit('dc:subject', subject.subject, 'dcterms:LCSH')

        if self.release_date != datetime.date.min:
            lit('dcterms:created', self.release_date.isoformat(),
                 'dcterms:W3CDTF')
        else:
            if self.created:
                lit('dcterms:created', self.created, 'dcterms:W3CDTF')


    def load_from_parser(self, parser):
        """ Load DublinCore from Project Gutenberg ebook.

        """
        super().load_from_parser(parser)

        ## Worst method. Use as last resort only.
        ## first strip markup, leaving only text

        for body in xpath(parser.xhtml, "//xhtml:body"):
            self.load_from_pgheader(lxml.etree.tostring(body,
                                                          encoding = six.text_type,
                                                          method = 'text'))


    def load_from_rstheader(self, data):
        """ Load DublinCore from RST Metadata.

        """

        self.publisher = 'Project Gutenberg'
        self.rights = 'Public Domain in the USA.'

        re_field = re.compile(r'^\s*:(.+?):\s+', re.UNICODE)
        re_end   = re.compile(r'^[^\s]', re.UNICODE)

        m = schema = name = None
        contents = ''

        for line in data.splitlines()[:100]:
            m = re_field.match(line)
            m2 = re_end.match(line)

            if name and (m is not None or m2 is not None):
                contents = contents.strip()
                # debug("Outputting: %s.%s => %s" % (schema, name, contents))

                if schema == 'pg':
                    if name == 'id':
                        try:
                            self.project_gutenberg_id = int(contents)
                            self.is_format_of = str(NS.ebook) + str(self.project_gutenberg_id)
                        except ValueError:
                            error('Invalid ebook no. in RST meta: %s', contents)
                            return False
                    elif name == 'title':
                        self.project_gutenberg_title = contents
                    elif name == 'released':
                        try:
                            self.release_date = datetime.datetime.strptime(
                                contents, '%Y-%m-%d').date()
                        except ValueError:
                            error('Invalid date in RST meta: %s', contents)
                    elif name == 'rights':
                        if contents.lower() == 'copyrighted':
                            self.rights = 'Copyrighted.'

                elif schema == 'dc':
                    if name == 'creator':
                        self.add_author(contents, 'cre')
                    elif name == 'title':
                        self.title = self.title_file_as = contents
                    elif name == 'language':
                        try:
                            self.add_lang_id(contents)
                        except KeyError:
                            error('Invalid language id RST meta: %s', contents)
                    elif name == 'created':
                        pass # published date

                elif schema == 'marcrel':
                    self.add_author(contents, name)

                contents = ''
                name = schema = None

            if name:
                contents += '\n' + line.strip()

            if m is not None:
                try:
                    schema, name = m.group(1).lower().split('.', 1)
                    contents = line[m.end():].strip()
                except ValueError:
                    schema = name = None
                    contents = ''

        if self.project_gutenberg_id is None:
            raise ValueError('This is not a Project Gutenberg RST file.')
        return True


    def load_from_pgheader(self, data):
        """ Load DublinCore from Project Gutenberg ebook file.

        When a parser is supplied, data from the parser is used

        """
        def handle_subtitle(self, key, value):
            self.title = self.title_no_subtitle + ': ' + value


        def handle_title(self, key, value):
            if self.subtitle:
                self.title = value + ': ' + self.subtitle
            else:
                self.title = value


        def handle_authors(self, role, names):
            """ Handle Author:, Illustrator: etc. line

            Examples of lines we handle are:

            Author: Lewis Carroll, Mark Twain and Chuck Norris
            Illustrator: Jack Tenniel

            """
            try:
                marcrel = self.inverse_role_map[role]
            except KeyError:
                warning('%s is not a supported marc role', role)
                return

            # replace 'and' with ',' and remove
            # superfluous white space around ','
            names = re.sub(r'\s*\n\s*',  ',', names)
            names = re.sub(r'[,\s]+and\b',   ',', names)
            names = re.sub(r'\bet\b',    ',', names)
            names = re.sub(r'\bund\b',   ',', names)
            # prevent authors names "Jr."
            names = re.sub(r'[\s,]+Jr\.?(\s+|$)', ' Jr. ', names)

            for name in names.split(','):
                self.add_author(name, marcrel)


        def handle_release_date(self, dummy_prefix, date):
            """ Scan Release date: line.
            NOTE this field is now ignored; """

            m = re.match(r'^(.*?)\s*\[', date)
            if m:
                date = m.group(1)
                date = date.strip()
                date = re.sub(r'[,\s]+', ' ', date)
                for f in ('%B %d %Y', '%B %Y', '%b %d %Y', '%b %Y', '%Y-%m-%d'):
                    try:
                        self.release_date = datetime.datetime.strptime(date, f).date()
                        break
                    except ValueError:
                        pass

                if self.release_date == datetime.date.min:
                    error("Cannot understand date: %s", date)
                    return


        def handle_ebook_no(self, key, text):
            """ Scan ebook no. """

            m = re.search(r'#(\d+)\]', text)
            m = m if m else re.match(r'(\d+)', text)
            if m and not self.project_gutenberg_id:
                self.project_gutenberg_id = int(m.group(1))


        def handle_languages(self, dummy_prefix, text):
            handle_dc_languages(self, text)


        def handle_subject(self, dummy_prefix, suffix):
            """ Handle subject. """
            subject = Struct()
            subject.id = None
            subject.subject = suffix
            self.subjects.append(subject)


        def handle_locc(self, dummy_prefix, suffix):
            """ Handle locc. """
            locc = Struct()
            locc.id = None
            locc.locc = suffix
            self.loccs.append(locc)


        def handle_creators(self, key, value):
            if isinstance(value, dict):
                value = [value]
            elif isinstance(value, list):
                pass
            else:
                error('%s is not a valid creator', value)
                return
            for creator in value:
                try:
                    marcrel = self.inverse_role_map[creator['role']]
                except KeyError:
                    warning('%s is not a supported marc role', creator['role'])
                    marcrel = 'cre'
                self.add_author(creator['name'], marcrel)


        def handle_scan_urls(self, key, value):
            if isinstance(value, str):
                value = [value]
            elif isinstance(value, list):
                pass
            else:
                error('%s is not a valid scanurl', value)
                return
            for scan_url in value:
                self.scan_urls.add(scan_url)


        def handle_pubinfo(self, key, value):
            if key == 'publisher':
                self.pubinfo.publisher = value
            elif key == 'publisher_country':
                self.pubinfo.country = value
            elif key == 'source_publication_years':
                value = [value] if isinstance(value, str) else value
                if not isinstance(value, list):
                    warning('%s is not a list of event:year pair', value)
                    return
                for event_year in value:
                    if ':' in event_year:
                        [event, year] = event_year.split(':')
                        self.pubinfo.years.append((event, year))
                    elif event_year:
                        warning('assuming %s is a copyright year', event_year)
                        self.pubinfo.years.append(('copyright', event_year))


        def nothandled(self, key, value):
            info('key %s, value %s not handled', key, value)


        def store(self, prefix, suffix):
            """ Store into attribute. """
            # debug("store: %s %s" % (prefix, suffix))
            setattr(self, prefix, suffix)


        def scan_txt(self, data):
            last_prefix = None
            buf = ''

            # only look in body; sometimes head is really long
            pos = data.find("<body")
            if pos > 0:
                data = data[pos:]

            for line in data.splitlines()[:300]:
                line = line.strip(' %') # TeX comments
                # debug("Line: %s" % line)

                if self.project_gutenberg_id is None:
                    handle_ebook_no(self, None, line.strip())

                if last_prefix and len(line) == 0:
                    dispatch(self, last_prefix, buf)
                    last_prefix = None
                    buf = ''
                    continue

                if re.search('START OF', line):
                    if last_prefix:
                        dispatch(self, last_prefix, buf)
                    break

                prefix, sep, suffix = line.partition(':')
                if sep:
                    if get_dispatcher(prefix) != nothandled:
                        if last_prefix:
                            dispatch(self, last_prefix, buf)
                        last_prefix = prefix
                        buf = suffix
                        continue

                buf += '\n' + line

                line = line.lower()
                if ('audiobooksforfree' in line or
                    'literalsystems' in line or
                    'librivox' in line or
                    'human reading of an ebook' in line):
                    if 'Sound' not in self.categories:
                        self.categories.append('Sound')

                if 'copyrighted project gutenberg' in line:
                    self.rights = 'Copyrighted.'


        def scan_json(self, data):
            pg_json = json.loads(data)
            record = pg_json['DATA']
            record = record[0] if isinstance(record, list) else record
            store(self, 'encoding', 'utf-8')
            for key, val in record.items():
                key = key.lower()
                dispatch(self, key, val)


        def get_dispatcher(key):
            key = key.lower().strip()
            key = 'creator_role' if key == "contributor" else key
            if key in aliases:
                key = aliases[key]
            dispatcher_method = dispatcher.get(key, None)
            if not dispatcher_method:
                dispatcher_method = aliases.get(key.strip('s'), nothandled)
            return key, dispatcher_method


        def dispatch(self, key, val):
            val = unicodedata.normalize('NFC', val).strip() if isinstance(val, str) else val
            key, dispatcher_method = get_dispatcher(key)
            try:
                dispatcher_method(self, key, val)
            except ValueError:
                warning('This is not a valid Project Gutenberg metadata key: %s' % key)


        dispatcher = {
            'title':        handle_title,
            'subtitle':     handle_subtitle,
            'author':       handle_authors,
            'release date': handle_release_date,
            'languages':    handle_languages,
            'subjects':     handle_subject,
            'loccs':        handle_locc,
            'edition':      store,
            'contents':     store,
            'notes':        store,
            'encoding':     store,
            'rights':       store,
            'alt_title':    store,
            'creator_role':  handle_creators,
            'scans_archive_url': handle_scan_urls,
            'credit':       store,
            'publisher':    handle_pubinfo,
            'publisher_country': handle_pubinfo,
            'source_publication_years': handle_pubinfo,
            'ebook_number': handle_ebook_no,
            "request_key":  store,
            }

        aliases = {
            'language':               'languages',
            'subject':                'subjects',
            'loc class':              'loccs',
            'loc classes':            'loccs',
            'content':                'contents',
            'note' :                  'notes',
            'character set encoding': 'encoding',
            'copyright':              'rights',
            'alternate title':        'alt_title',
            'created':                'source_publication_years',
            'produced by':            'credit',
            }

        for role in list(self.inverse_role_map.keys()):
            dispatcher[role] = handle_authors

        self.publisher = 'Project Gutenberg'
        self.rights = 'Public Domain in the USA.'

        if data and data[0] == '{':
            #assume json
            scan_json(self, data)
        else:
            # scan this text file
            scan_txt(self, data)

        if self.project_gutenberg_id is None:
            raise ValueError('This is not a Project Gutenberg ebook file.')


# use PGDCObject if you want a DublinCoreObject that uses a database if available
try:
    from .DublinCoreMapping import DublinCoreObject as PGDCObject
except ImportError:
    # no database
    PGDCObject = GutenbergDublinCore
