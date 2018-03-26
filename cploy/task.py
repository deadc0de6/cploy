"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Represent a task to sync
"""

import os
import shlex
from docopt import docopt

# local import
from . import __usage__ as USAGE
from cploy.exceptions import *


class Task:

    USER_SEP = '@'
    PORT_SEP = ':'

    def __init__(self, args):
        self._parse(args)

    def _norm(self, path):
        ''' normalize local path '''
        path = os.path.abspath(path)
        return os.path.expanduser(path)

    def _parse(self, args):
        ''' parse arguments to construct task '''
        args = docopt(USAGE, help=False, argv=shlex.split(args))
        self.force = args['--force']
        self.local = self._norm(args['<local_path>'])
        self.remote = args['<remote_path>']
        if not os.path.exists(self.local):
            err = 'local path \"{}\" does not exist'.format(self.local)
            raise SyncException(err)
        self.username = args['--user']
        self.hostname = args['<hostname>']
        self.port = int(args['--port'])
        if self.USER_SEP in self.hostname:
            self.username = self.hostname.split(self.USER_SEP)[0]
            self.hostname = self.hostname.split(self.USER_SEP)[1]
            if self.PORT_SEP in self.hostname:
                self.port = int(self.hostname.split(self.PORT_SEP)[1])
                self.hostname = self.hostname.split(self.PORT_SEP)[0]
        self.key = args['--key']
        self.keypass = args['--keypass']
        self.password = args['--pass']
        self.exclude = args['--exclude']
        self.command = args['--command']
