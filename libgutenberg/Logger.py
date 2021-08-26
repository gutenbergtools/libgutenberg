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

class CustomFormatter(logging.Formatter):
    """ A custom formatter that adds ebook no. """

    def format(self, record):
        """ Add ebook no. to string format params. """
        try:
            myebook = int(ebook)
        except ValueError:
            myebook = 0
        record.ebook = myebook
        return logging.Formatter.format(self, record)

class NotificationHandler(logging.Handler):
    """ notifier is a callable with signature ebook, message"""

    def __init__(self, notifier=None):
        super(logging.Handler, self).__init__()
        self.setLevel(logging.CRITICAL)
        self.notifier = notifier
        
    def handle(self, record):
        ''' To activate message queueing, 
            and set a notifier callable in setup.
        '''
        if self.notifier :
            message = CustomFormatter(LOGFORMAT).format(record)
            self.notifier(ebook, message)



def setup(logformat, logfile=None, loglevel=logging.INFO, notifier=None):
    """ Setup logger. """

    # StreamHandler defaults to sys.stderr
    file_handler = logging.FileHandler(logfile) if logfile else logging.StreamHandler()
    file_handler.setFormatter(CustomFormatter(logformat))
    notify_handler = NotificationHandler(notifier=notifier)
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.addHandler(notify_handler)
    logger.setLevel(loglevel)
    return file_handler


def set_log_level(level):
    """ Set log level. """
    if level >= 1:
        logging.getLogger().setLevel(logging.INFO)
    if level >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


__all__ = 'debug info warning error critical exception'.split()
