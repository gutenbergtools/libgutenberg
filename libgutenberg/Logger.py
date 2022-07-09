#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

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
notifier = None # global
base_logfile = None

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

    def __init__(self):
        super(logging.Handler, self).__init__()
        self.setLevel(logging.CRITICAL)
        
    def handle(self, record):
        ''' To activate message queueing, 
            and set a notifier callable in setup.
        '''
        if notifier :
            message = CustomFormatter(LOGFORMAT).format(record)
            notifier(ebook, message)



def setup(logformat, logfile=None, loglevel=logging.INFO):
    """ Setup logger. """

    # Setup logger. 
    logger = logging.getLogger()
    logger.setLevel(loglevel)

    # setup handlers
    if logger.hasHandlers():
        logger.handlers.clear()        

    # setup file_handlers
    if logfile: 
        file_handler = logging.FileHandler(logfile) 
        file_handler.setFormatter(CustomFormatter(logformat))
        logger.addHandler(file_handler)
    else:
        file_handler = None

    if base_logfile: 
        file_handler = logging.FileHandler(base_logfile) 
        file_handler.setFormatter(CustomFormatter(logformat))
        logger.addHandler(file_handler)


    # setup stream_handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomFormatter(LOGFORMAT))
    logger.addHandler(stream_handler)


    if notifier:
        notify_handler = NotificationHandler()
        logger.addHandler(notify_handler)
    return file_handler


def set_log_level(level):
    """ Set log level. """
    if level >= 1:
        logging.getLogger().setLevel(logging.INFO)
    if level >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


__all__ = 'debug info warning error critical exception'.split()
