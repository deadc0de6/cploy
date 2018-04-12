"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
handle logging
"""

import sys
import os
import inspect
from datetime import datetime


class Log:

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    EMPH = '\033[33m'

    @classmethod
    def err(cls, string):
        ''' error '''
        cs = cls._color(cls.RED)
        ce = cls._color(cls.RESET)
        sys.stderr.write('{}\n[ERR] {} \n{}\n'.format(cs, string, ce))

    @classmethod
    def debug(cls, string):
        ''' debug '''
        cs = cls._color(cls.YELLOW)
        ce = cls._color(cls.RESET)
        now = datetime.now().strftime('%Y%m%d-%H:%M:%S')
        pre1 = '{}[{}]{}'.format(cls._color(cls.MAGENTA),
                                 now, cls._color(cls.RESET))
        pre2 = '{}[{}]{}'.format(cls._color(cls.GREEN),
                                 cls._where(), cls._color(cls.RESET))
        sys.stderr.write('{}{}{}[DEBUG] {} {}\n'.format(pre1, pre2,
                                                        cs, string, ce))

    @classmethod
    def log(cls, string):
        ''' normal log '''
        cs = cls._color(cls.BLUE)
        ce = cls._color(cls.RESET)
        sys.stdout.write('{}{}{}\n'.format(cs, string, ce))

    @classmethod
    def _where(cls):
        ''' get module and function '''
        method = inspect.stack()[2][3]
        frame = inspect.stack()[2]
        mod = inspect.getmodulename(frame[1])
        return '{}.{}'.format(mod, method)

    @classmethod
    def _color(cls, col):
        ''' return color if is tty '''
        if not sys.stdout.isatty():
            return ''
        return col
