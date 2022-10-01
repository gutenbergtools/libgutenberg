#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""
GutenbergGlobals.py

Copyright 2009-2021 by Marcello Perathoner, and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.


"""

from __future__ import unicode_literals

import os
import re
import datetime

import pycountry

class Struct(object):
    """ handy class to pin attributes on

    usage: c = Struct()
           c.something = 1

    """
    pass

PG_CANONICAL_HOST = 'www.gutenberg.org'

PG_URL = 'https://' + PG_CANONICAL_HOST + '/'

NSMAP = {
    'atom':       'http://www.w3.org/2005/Atom',
    'bio':        'http://purl.org/vocab/bio/0.1/',
    'cc':         'http://web.resource.org/cc/',
    'dc':         'http://purl.org/dc/elements/1.1/',
    'dcam':       'http://purl.org/dc/dcam/',
    'dcmitype':   'http://purl.org/dc/dcmitype/',
    'dcterms':    'http://purl.org/dc/terms/',
    'ebook':      'http://' + PG_CANONICAL_HOST + '/ebooks/',             # for RDF only
    'epub':       'http://www.idpf.org/2007/ops',
    'foaf':       'http://xmlns.com/foaf/0.1/',
    'marcrel':    'http://id.loc.gov/vocabulary/relators/',
    'mathml':     'http://www.w3.org/1998/Math/MathML',
    'mbp':        'http://mobipocket.com/mbp',
    'ncx':        'http://www.daisy.org/z3986/2005/ncx/',
    'opds':       'http://opds-spec.org/2010/Catalog',
    'opf':        'http://www.idpf.org/2007/opf',
    'opensearch': 'http://a9.com/-/spec/opensearch/1.1/',
    'pg':         'http://' + PG_CANONICAL_HOST + '/',                    # for RDF only
    'pgagents':   'http://' + PG_CANONICAL_HOST + '/2009/agents/',        # for RDF only
    'pgtei':      'http://' + PG_CANONICAL_HOST + '/tei/marcello/0.5/ns', # for RDF only
    'pgterms':    'http://' + PG_CANONICAL_HOST + '/2009/pgterms/',       # for RDF only
    'py':         'http://genshi.edgewall.org/',
    'rdf':        'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':       'http://www.w3.org/2000/01/rdf-schema#',
    'svg':        'http://www.w3.org/2000/svg',
    'tei':        'http://www.tei-c.org/ns/1.0',
    'xhtml':      'http://www.w3.org/1999/xhtml',
    'xinclude':   'http://www.w3.org/2001/XInclude',
    'xml':        'http://www.w3.org/XML/1998/namespace',
    'xmlns':      'http://www.w3.org/2000/xmlns/',
    'xsd':        'http://www.w3.org/2001/XMLSchema#',
    'xsi':        'http://www.w3.org/2001/XMLSchema-instance',
    'xslfo':      'http://www.w3.org/1999/XSL/Format',
}

NONFILINGS = {'The ', 'A ', 'An ', 'Der ', 'Die ', 'Das ', 'Eine ', 'Ein ',
		      'La ', 'Le ', 'Les ', 'L\'', 'El '}
ROLES = {
    'adp': 'Adapter',
    'ann': 'Annotator',
    'arr': 'Arranger',
    'art': 'Artist',
    'aut': 'Author',
    'aft': 'Author of afterword, colophon, etc.',
    'aui': 'Author of introduction, etc.',
    'clb': 'Collaborator',
    'cmm': 'Commentator',
    'com': 'Compiler',
    'cmp': 'Composer',
    'cnd': 'Conductor',
    'ctb': 'Contributor',
    'cre': 'Creator',
    'dub': 'Dubious author',
    'edt': 'Editor',
    'egr': 'Engraver',
    'frg': 'Forger',
    'ill': 'Illustrator',
    'lbt': 'Librettist',
    'mrk': 'Markup editor',
    'mus': 'Musician',
    'oth': 'Other',
    'pat': 'Patron',
    'prf': 'Performer',
    'pht': 'Photographer',
    'prt': 'Printer',
    'pro': 'Producer',
    'prg': 'Programmer',
    'pfr': 'Proofreader',
    'res': 'Researcher',
    'rev': 'Reviewer',
    'sng': 'Singer',
    'spk': 'Speaker',
    'trc': 'Transcriber',
    'trl': 'Translator',
    'unk': 'Unknown role',
}



class language_map(object):
    alt_names = {
        'Bangla': 'bn',
        'Bhutani': 'dz',
        'Farsi': 'fa',
        'Fiji': 'fj',
        'Frisian': 'fy',
        'Interlingua': 'ia',
        'Inupiak': 'ik',
        'Greenlandic': 'kl',
        'Cambodian': 'km',
        'Laothian': 'lo',
        'Malay': 'ms',
        'Nepali': 'ne',
        'Occitan': 'oc',
        'Oriya': 'or',
        'Punjabi': 'pa',
        'Pashto': 'ps',
        'Rhaeto-Romance': 'rm',
        'Kurundi': 'rn',
        'Sangho': 'sg',
        'Singhalese': 'si',
        'Siswati': 'ss',
        'Sesotho': 'st',
        'Swahili': 'sw',
        'Setswana': 'tn',
        'Tonga': 'to',
        'Uigur': 'ug',
        'Volapuk': 'vo',
        'Greek': 'el',
        'Waray': 'war',
        'Nahuatl': 'nah',
        'Middle English': 'enm',
        'Old English': 'ang',
        'North American Indian': 'nai',
        'Mayan Languages': 'myn',
        'Iroquoian': 'iro',
        'Napoletano-Calabrese': 'nap',
        'Gaelic, Scottish': 'gla',
        'Gaelic, Irish': 'gle',
        'Greek, Ancient': 'grc',
        'Ojibwa, Western': 'ojw',
        'Bodo': 'brx',
    }

    @classmethod
    def get(cls, code, default=''):
        lang = None
        if not code:
            return default
        if len(code) == 2:
            lang = pycountry.languages.get(alpha_2=code)
        elif len(code) == 3:
            lang = pycountry.languages.get(alpha_3=code)
            if not lang:
                lang = pycountry.language_families.get(alpha_3=code)
        return lang.name if lang else default

    @classmethod
    def inverse(cls, name, default='en'):
        lang = None
        if not name:
            return default
        if name in cls.alt_names:
            return cls.alt_names[name]
        lang = pycountry.languages.get(name=name)
        if lang:
            if hasattr(lang, 'alpha_2'):
                return lang.alpha_2
            if hasattr(lang, 'alpha_3'):
                return lang.alpha_3
        return default


class NameSpaceClark(object):
    """ Build a tag name in Clark notation.

    ns = NameSpaceClark("http://example.com/")
    >>> ns.foo
    '{http://example.com/}foo'
    >>> ns['bar']
    '{http://example.com/}bar'

    """

    def __init__(self, root):
        self.root = root

    def __getitem__(self, local):
        return "{%s}%s" % (self.root, local)

    def __getattr__(self, local):
        return "{%s}%s" % (self.root, local)

    def __str__(self):
        return self.root


class NameSpaceURI(object):
    """ Build a URI.

    ns = NameSpaceURI("http://example.com/")
    >>> ns.foo
    'http://example.com/foo'
    >>> ns['bar']
    'http://example.com/bar'

    """

    def __init__(self, root):
        self.root = root

    def __getitem__(self, local):
        return "%s%s" % (self.root, local)

    def __getattr__(self, local):
        return "%s%s" % (self.root, local)

    def __str__(self):
        return self.root


def build_nsmap(prefixes = None):
    """ build a nsmap containing all namespaces for prefixes """

    if prefixes is None:
        prefixes = list(NSMAP.keys())
    if isinstance(prefixes, str):
        prefixes = prefixes.split() # pylint: disable=maybe-no-member

    ns = {}
    for prefix_ in prefixes:
        ns[prefix_] = NSMAP[prefix_]

    return ns


NS = Struct()
NSURI = Struct()

for prefix, uri in list(NSMAP.items()):
    setattr(NS, prefix, NameSpaceClark(uri))
    setattr(NSURI, prefix, NameSpaceURI(uri))

XML_DECLARATION = """<?xml version='1.0' encoding='UTF-8'?>"""

XHTML_DOCTYPE   = ("<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.1//EN' " +
                   "'http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd'>")

XHTML1_DOCTYPE   = ("<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Strict//EN' " +
                   "'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'>")

XHTML_RDFa_DOCTYPE = ("<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML+RDFa 1.1//EN' " +
                      "'http://www.w3.org/MarkUp/DTD/xhtml-rdfa-2.dtd'>")

NCX_DOCTYPE = ("<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' " +
               "'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>")

HTML5_DOCTYPE = "<!DOCTYPE html>"

def xmlspecialchars(s):
    """ Replace xml special chars & < > with escapes. """
    return (s.replace('&',  '&amp;')
             .replace('<',  '&lt;')
             .replace('>',  '&gt;'))

def insert_breaks(s, self_closing=True):
    """ Replace newlines with <br/>. """
    return s.replace('\n', '<br />' if self_closing else '<br>')

RE_NORMALIZE    = re.compile(r"\s+")

def normalize(s):
    """ Replace consecutive whitespace with one space. """
    s = RE_NORMALIZE.sub(' ', s)
    return s.strip()


def cut_at_newline(text):
    """ Cut the text at the first newline. """
    i = text.find('\n')
    if i > -1:
        return text[:i]
    return text

def archive_dir(ebook):
    """ build 1/2/3/4/12345 for 12345 """
    ebook = str(ebook)
    if len(ebook) == 1:
        return '0/' + ebook
    a = []
    for c in ebook:
        a.append(c)
    a[-1] = ebook
    return "/".join(a)

def archive2files(ebook, path):
    """ Replace dirs/1/2/3 with files/123. """
    adir = archive_dir(ebook)
    return path.replace('dirs/' + adir, 'files/%d' % ebook)


def xpath(node, path, **kwargs):
    """ xpath helper """
    return node.xpath(path, namespaces=NSMAP, **kwargs)


def mkdir_for_filename(fn):
    """ Make sure the directory for this file is present. """

    try:
        os.makedirs(os.path.dirname(fn))
    except os.error:
        pass


def make_url_relative(base_url, url):
    """ Make absolute url relative to base_url if possible. """

    if url.startswith(base_url):
        return url[len(base_url):]

    base_url = os.path.dirname(base_url) + '/'

    if url.startswith(base_url):
        return url[len(base_url):]

    return url


def normalize_path(path):
    """ Normalize a file path. """
    if path.startswith('file://'):
        path = path[7:]
    if re.search(r'^/[a-zA-Z]:', path):
        path = path[1:]
    return path


def is_same_path(path1, path2):
    """ Does path1 point to the same file as path2? """
    return os.path.realpath(normalize_path(path1)) == os.path.realpath(normalize_path(path2))


def string_to_filename(fn):
    """ Sanitize string so it can do as filename. """

    def escape(matchobj):
        """ Escape a char. """
        return '@%x' % ord(matchobj.group(0))

    fn = os.path.normpath(fn)
    fn = normalize(fn)
    fn = fn.replace(os.sep, '@')
    if os.altsep:
        fn = fn.replace(os.altsep, '@')
    fn = re.sub(r'[\|/:?"*<>\u0000-\u001F]', escape, fn)

    return fn


class DCIMT(object):
    """ encapsulates one dcterms internet mimetype

    """

    def __init__(self, mime, enc = None):
        if mime is None:
            self.mimetype = 'application/octet-stream'
        elif enc is not None and mime.startswith('text/'):
            self.mimetype = "%s; charset=%s" % (mime, enc)
        else:
            self.mimetype = mime

    def __str__(self):
        return self.mimetype


class UTC(datetime.tzinfo):
    """ UTC helper for datetime.datetime """

    def utcoffset(self, dummy_dt):
        return datetime.timedelta(0)

    def tzname(self, dummy_dt):
        return "UTC"

    def dst(self, dummy_dt):
        return datetime.timedelta(0)

# exceptions

class SkipOutputFormat(Exception):
    """ Raised to skip this output format. """
    pass

# Spider.py tries a topological sort on link rel=next
def topological_sort(pairlist):
    """Topologically sort a list of (parent, child) pairs.

    Return a list of the elements in dependency order (parent to child order).

    >>> print topsort( [(1,2), (3,4), (5,6), (1,3), (1,5), (1,6), (2,5)] )
    [1, 2, 3, 5, 4, 6]

    >>> print topsort( [(1,2), (1,3), (2,4), (3,4), (5,6), (4,5)] )
    [1, 2, 3, 4, 5, 6]

    >>> print topsort( [(1,2), (2,3), (3,2)] )
    Traceback (most recent call last):
    CycleError: ([1], {2: 1, 3: 1}, {2: [3], 3: [2]})

    """
    num_parents = {}  # element -> # of predecessors
    children = {}  # element -> list of successors
    for parent, child in pairlist:
        # Make sure every element is a key in num_parents.
        if parent not in num_parents:
            num_parents[parent] = 0
        if child not in num_parents:
            num_parents[child] = 0

        # Since child has a parent, increment child's num_parents count.
        num_parents[child] += 1

        # ... and parent gains a child.
        children.setdefault(parent, []).append(child)

    # Suck up everything without a parent.
    answer = [x for x in list(num_parents.keys()) if num_parents[x] == 0]

    # For everything in answer, knock down the parent count on its children.
    # Note that answer grows *in* the loop.
    for parent in answer:
        del num_parents[parent]
        if parent in children:
            for child in children[parent]:
                num_parents[child] -= 1
                if num_parents[child] == 0:
                    answer.append( child )
            # Following "del" isn't needed; just makes
            # CycleError details easier to grasp.
            del children[parent]

    if num_parents:
        # Everything in num_parents has at least one child ->
        # there's a cycle.
        raise Exception(answer, num_parents, children)
    return answer
