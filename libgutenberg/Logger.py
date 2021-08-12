#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""
Logger.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Logging support.


"""

from __future__ import unicode_literals

import logging
from logging import debug, info, warning, error, critical, exception # pylint: disable=unused-import

LOGFORMAT = '%(asctime)s %(levelname)-8s  #%(ebook)-5d %(message)s'

ebook = 0 # global
notifier = None # a callable with signature ebook, message

class CustomFormatter (logging.Formatter):
    """ A custom formatter that adds ebook no. """

    def format (self, record):
        """ Add ebook no. to string format params. """
        try:
            myebook = int (ebook)
        except ValueError:
            myebook = 0
        record.ebook = myebook
        return logging.Formatter.format (self, record)


def q_message(record):
    ''' To activate message queueing, start log message with "Notify:" 
        and set a q_er callable in setup.
    '''
    if notifier and ebook and record.msg.startswith('Notify:'):
        message = CustomFormatter(LOGFORMAT).format(record)
        notifier(ebook, message)
    return 1


def setup (logformat, logfile=None):
    """ Setup logger. """

    # StreamHandler defaults to sys.stderr
    file_handler = logging.FileHandler (logfile) if logfile else logging.StreamHandler ()
    file_handler.setFormatter (CustomFormatter (logformat))
    logging.getLogger ().addHandler (file_handler)
    logging.getLogger ().setLevel (logging.INFO)
    logging.getLogger ().addFilter (q_message)


def set_log_level (level):
    """ Set log level. """
    if level >= 1:
        logging.getLogger ().setLevel (logging.INFO)
    if level >= 2:
        logging.getLogger ().setLevel (logging.DEBUG)


__all__ = 'debug info warning error critical exception'.split ()
